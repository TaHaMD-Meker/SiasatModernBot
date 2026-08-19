# -*- coding: utf-8 -*-
"""
پنل ادمین پیشرفته و تعاملی با دکمه‌های شیشه‌ای (Inline Buttons).
مدیریت کامل کشورها، خزانه، طلا، نفت، تجهیزات، دارایی‌های اختصاصی نظامی (Country Assets) و همگام‌سازی کاتالوگ.
"""

import math
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

import database as db
import config
import asyncio
import war_analyzer
from utils import format_money, format_number, format_oil, get_main_keyboard


ACTIVE_WAR_ANALYSES = {}
LATEST_WAR_ANALYSIS = {}


# ==================== خط تولید تحلیل دستی (کپی-پیست هوشمند) ====================

WAR_CAPS = {"att_mil": 400, "def_mil": 800, "civ": 150}


def _war_catalog_assets(key):
    out = []
    for it in config.COUNTRY_EQUIPMENT_CATALOG.get(key, []):
        out.append({
            "equipment_key": it.get("key"), "equipment_name": it.get("name"),
            "amount": it.get("initial", 50), "category": it.get("category", "Ground Forces"),
            "price": it.get("price", 1_000_000),
        })
    return out


def _war_assets(key):
    c = db.get_country_by_key(key)
    if c:
        db.seed_country_assets(c["id"], key)
        return db.get_country_assets(c["id"]) or []
    return _war_catalog_assets(key)


_CAT_SHORT = {
    "Missiles": "موشک", "UAV": "پهپاد", "Aircraft": "هواپیما", "Ground Forces": "زرهی",
    "Artillery": "توپ", "Navy": "دریا", "Air Defense": "پدافند",
}


def _stock_lines(key, limit=9):
    items = sorted(_war_assets(key), key=lambda a: -(a.get("amount", 0) or 0))
    lines = []
    for a in items[:limit]:
        cat = _CAT_SHORT.get(a.get("category", ""), "")
        lines.append(f"- {a.get('equipment_name')} ×{max(1, (a.get('amount', 0) or 0)):,}" + (f" [{cat}]" if cat else ""))
    return "\n".join(lines) if lines else "- (بدون موجودی)"


def _ad_lines(key):
    import war_stats as _ws
    _cls_fa = {"rocket": "راکت", "drone": "پهپاد", "cruise": "کروز", "ballistic": "بالستیک", "aircraft": "هواپیما"}
    ads = [a for a in _war_assets(key) if a.get("category") == "Air Defense" and (a.get("amount", 0) or 0) > 0]
    ads.sort(key=lambda a: -((a.get("amount", 0) or 0) * (a.get("buy_price", a.get("price", 0)) or 0)))
    lines = []
    for a in ads[:3]:
        rates = _ws.ad_rates_for(a.get("equipment_key") or "", a.get("equipment_name") or "")
        top = sorted(rates.items(), key=lambda kv: -kv[1])[:3]
        r = " ".join(f"{_cls_fa.get(k, k)}{int(v*100)}٪" for k, v in top)
        lines.append(f"- {a.get('equipment_name')} ×{a['amount']:,}: {r}")
    return "\n".join(lines) if lines else "- (پدافند قابل توجهی ندارد)"


def build_war_prompt(att_key, def_key, att_role, def_role):
    a = config.COUNTRIES.get(att_key, {})
    d = config.COUNTRIES.get(def_key, {})
    return f"""نبرد زیر را واقع‌گرایانه تحلیل کن و فقط بلوک نتیجه را با همین قالب برگردان.

⚔️ {a.get('flag','')} {a.get('name', att_key)} (مهاجم) علیه {d.get('flag','')} {d.get('name', def_key)} (مدافع)

📦 انبار مهاجم:
{_stock_lines(att_key)}

📦 انبار مدافع:
{_stock_lines(def_key)}

🛡️ پدافند مدافع:
{_ad_lines(def_key)}

📝 رول مهاجم:
{(att_role or "رولی نفرستاده؛ حمله متوسط فرض کن.")[:1200]}

🛡️ رول مدافع:
{(def_role or "رولی نفرستاده؛ دفاع متعارف فرض کن.")[:600]}

⚖️ قوانین: تلفات مهاجم حداکثر {WAR_CAPS['att_mil']}، مدافع حداکثر {WAR_CAPS['def_mil']}، غیرنظامی حداکثر {WAR_CAPS['civ']}. تجهیزاتِ انهدام‌شده فقط از فهرست‌های بالا، حداکثر ۳۰٪ موجودی هر آیتم. موشک/پهپاد شلیک‌شده مهاجم کاملاً مصرف می‌شود (در ATT_LOSS بیاور).

قالب خروجی (بدون هیچ متن دیگر):
#WAR
ATT_MIL: عدد
ATT_CIV: عدد
DEF_MIL: عدد
DEF_CIV: عدد
ATT_LOSS: نام تجهیز=تعداد
DEF_LOSS: نام تجهیز=تعداد
NOTE: یک جمله روایت
#END"""


def _norm_war_text(t):
    import re as _re
    t = str(t).lower().replace("\u200c", " ").replace("_", " ").strip()
    return _re.sub(r"\s+", " ", t)


def match_equipment(query, assets):
    """تطبیق نام تجهیز در بلوک نتیجه با موجودی واقعی (بلندترین تطبیق برنده)."""
    q = _norm_war_text(query)
    if len(q) < 2:
        return None
    best, best_len = None, 0
    for a in assets:
        for field in (a.get("equipment_name") or "", a.get("equipment_key") or ""):
            f = _norm_war_text(field)
            if not f:
                continue
            if (q in f or f in q) and len(f) > best_len:
                best, best_len = a, len(f)
    return best


def parse_war_block(text):
    """پارس بلوک نتیجه #WAR ... #END — خروجی: (result, error)."""
    import re as _re
    t = war_analyzer.convert_farsi_digits(str(text))
    if "#WAR" not in t:
        return None, "بلوک #WAR پیدا نشد. مطمئن شو کل خروجی هوش مصنوعی را کپی کرده‌ای."
    res = {"att_mil": 0, "att_civ": 0, "def_mil": 0, "def_civ": 0, "att_losses": [], "def_losses": [], "note": ""}
    got_any = False
    for line in t.splitlines():
        line = line.strip()
        m = _re.match(r"^ATT_MIL\s*:\s*(\d+)", line, _re.I)
        if m:
            res["att_mil"] = int(m.group(1)); got_any = True; continue
        m = _re.match(r"^ATT_CIV\s*:\s*(\d+)", line, _re.I)
        if m:
            res["att_civ"] = int(m.group(1)); got_any = True; continue
        m = _re.match(r"^DEF_MIL\s*:\s*(\d+)", line, _re.I)
        if m:
            res["def_mil"] = int(m.group(1)); got_any = True; continue
        m = _re.match(r"^DEF_CIV\s*:\s*(\d+)", line, _re.I)
        if m:
            res["def_civ"] = int(m.group(1)); got_any = True; continue
        m = _re.match(r"^(ATT|DEF)_LOSS\s*:\s*(.+?)\s*=\s*(\d+)$", line, _re.I)
        if m:
            side = "att_losses" if m.group(1).upper() == "ATT" else "def_losses"
            res[side].append((m.group(2).strip(), int(m.group(3))))
            got_any = True; continue
        m = _re.match(r"^NOTE\s*:\s*(.*)$", line, _re.I)
        if m:
            res["note"] = m.group(1).strip()[:500]; continue
    if not got_any:
        return None, "هیچ خط قابل شناسایی در بلوک نبود. قالب را دقیقاً مثل نمونه رعایت کن."
    return res, None


def build_losses_from_block(parsed, att_key, def_key):
    """تبدیل بلوک پارس‌شده به ساختار تلفات معتبر (کلیپ به سقف‌ها و موجودی)."""
    att_assets = _war_assets(att_key)
    def_assets = _war_assets(def_key)
    notes = []

    att_mil = min(WAR_CAPS["att_mil"], max(0, parsed["att_mil"]))
    def_mil = min(WAR_CAPS["def_mil"], max(0, parsed["def_mil"]))
    att_civ = min(WAR_CAPS["civ"], max(0, parsed["att_civ"]))
    def_civ = min(WAR_CAPS["civ"], max(0, parsed["def_civ"]))
    if (att_mil, def_mil, att_civ, def_civ) != (parsed["att_mil"], parsed["def_mil"], parsed["att_civ"], parsed["def_civ"]):
        notes.append("تلفات خارج از سقف بازی به سقف تنظیم شد.")

    def resolve(entries, assets, side_label):
        out, unmatched = [], []
        for name, qty in entries:
            a = match_equipment(name, assets)
            if not a:
                unmatched.append(name)
                continue
            stock = a.get("amount", 0) or 0
            cap = max(1, int(stock * 0.30)) if stock >= 3 else max(1, stock)
            k = min(max(1, qty), cap)
            out.append({
                "equipment_key": a.get("equipment_key") or a.get("key"),
                "equipment_name": a.get("equipment_name") or name,
                "amount": k, "category": a.get("category", ""),
                "price": a.get("buy_price", a.get("price", 1_000_000)) or 1_000_000,
            })
        return out, unmatched

    att_losses, un1 = resolve(parsed["att_losses"], att_assets, "مهاجم")
    def_losses, un2 = resolve(parsed["def_losses"], def_assets, "مدافع")
    if un1 or un2:
        notes.append("تجهیزات نامعتبر حذف شدند: " + ", ".join(un1 + un2))

    losses = {
        "att_losses": att_losses, "def_losses": def_losses,
        "att_fired": [], "def_fired": [],
        "att_military_loss": att_mil, "att_civilian_loss": att_civ,
        "def_military_loss": def_mil, "def_civilian_loss": def_civ,
    }
    return losses, notes



def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


# ==================== منوی اصلی ادمین ====================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ این بخش فقط برای ادمین اصلی بازی مجاز است.", parse_mode="Markdown")
        return

    admin_c = db.get_country_by_player(user_id)
    un_btn = [InlineKeyboardButton("🇺🇳 اتاق ویژه دبیرکل سازمان ملل متحد", callback_data="un:menu")] if (admin_c and admin_c.get("country_key") == "un") else [InlineKeyboardButton("🇺🇳 فعال‌سازی کشور / نقش سازمان ملل", callback_data="admin:claim_un")]

    pending_reqs = db.get_all_pending_country_requests()
    pending_count = len(pending_reqs)

    text = "👑 *پنل مدیریت بازی «سیاست مدرن»*\n\nلطفاً یک گزینه را انتخاب کنید:"
    keyboard = [
        un_btn,
        [InlineKeyboardButton(f"📥 درخواست‌های معلق کشورها ({pending_count})", callback_data="admin:pending_countries")],
        [InlineKeyboardButton("📋 مدیریت و لیست کشورها", callback_data="admin:list:0")],
        [InlineKeyboardButton("🔐 سیستم قفل‌ها و محدودیت‌ها", callback_data="admin:locks_menu")],
        [InlineKeyboardButton("📝 رول‌های دریافتی (تاییدنشده)", callback_data="admin:pending_roles")],
        [InlineKeyboardButton("⚔️ تحلیل نبرد (خط تولید دستی هوشمند)", callback_data="admin:war_start")],
        [InlineKeyboardButton("🔎 رصد و پایش فعالیت بازیکنان", callback_data="admin:monitor_menu")],
        [InlineKeyboardButton("📢 تنظیم آیدی کانال تلگرام", callback_data="admin:set_channel_prompt")],
        [InlineKeyboardButton("🏆 رتبه‌بندی ثروت و قدرتمندترین کشورها", callback_data="admin:rankings")],
        [InlineKeyboardButton("📊 آمار کلی بازی", callback_data="admin:stats")],
        [InlineKeyboardButton("🔄 همگام‌سازی کاتالوگ تمام کشورها", callback_data="admin:sync_catalog")],
        [InlineKeyboardButton("⚡ توزیع فوری درآمد روزانه", callback_data="admin:daily_income")],
        [InlineKeyboardButton("📢 ارسال پیام همگانی (Broadcast)", callback_data="admin:broadcast_prompt")],
        [InlineKeyboardButton("❌ بستن پنل", callback_data="admin:close")],
    ]

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def admin_locks_menu(query, context):
    country_lock = db.get_setting("country_creation_locked") == "1"
    blockade_lock = db.get_setting("naval_blockade_locked") == "1"
    trade_lock = db.get_setting("trade_contracts_locked") == "1"
    notes_lock = db.get_setting("diplomatic_notes_locked") == "1"

    text = (
        "🔐 **سیستم قفل‌ها و کنترل محدودیت‌های بازی**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "از این بخش می‌توانید بخش‌های مختلف بازی را به‌صورت لحظه‌ای قفل یا آزاد فرمایید:\n"
    )

    keyboard = [
        [InlineKeyboardButton("🔓 باز کردن ثبت‌نام کشورها" if country_lock else "🔒 قفل کردن ثبت‌نام کشورها", callback_data="admin:toggle_lock:country_creation_locked")],
        [InlineKeyboardButton("🔓 باز کردن محاصره دریایی" if blockade_lock else "🔒 قفل کردن محاصره دریایی", callback_data="admin:toggle_lock:naval_blockade_locked")],
        [InlineKeyboardButton("🔓 باز کردن قراردادهای تجاری" if trade_lock else "🔒 قفل کردن قراردادهای تجاری", callback_data="admin:toggle_lock:trade_contracts_locked")],
        [InlineKeyboardButton("🔓 باز کردن پیام‌های دیپلماتیک" if notes_lock else "🔒 قفل کردن پیام‌های دیپلماتیک", callback_data="admin:toggle_lock:diplomatic_notes_locked")],
        [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")],
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== لیست کشورها با صفحه‌بندی ====================

async def show_countries_list(query, context, page: int = 0):
    countries = db.get_all_countries()
    if not countries:
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]]
        await query.edit_message_text("❌ هنوز هیچ کشوری در بازی ساخته نشده است.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    per_page = 5
    total_pages = math.ceil(len(countries) / per_page)
    page = max(0, min(page, total_pages - 1))

    start_idx = page * per_page
    page_countries = countries[start_idx:start_idx + per_page]

    keyboard = []
    for c in page_countries:
        btn_text = f"{c['flag']} {c['name']} | 🏦 {format_money(c['treasury'])} (ID: {c['player_id']})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"admin:c:{c['id']}")])

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:list:{page - 1}"))
    nav_row.append(InlineKeyboardButton(f"صفحه {page + 1} از {total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:list:{page + 1}"))

    keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data="admin:menu")])

    text = f"📋 *لیست کشورهای فعال (تعداد کل: {len(countries)})*\n\nبرای مشاهده یا تغییر جزئیات، روی کشور مورد نظر کلیک کنید:"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== داشبورد اختصاصی مدیریت یک کشور ====================

async def show_country_dashboard(query, context, country_id: int, notice: str = ""):
    c = db.get_country_by_id(country_id)
    if not c:
        await query.edit_message_text("❌ این کشور پیدا نشد یا قبلاً حذف شده است.",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:list:0")]]))
        return

    if c.get("country_key"):
        db.seed_country_assets(c["id"], c["country_key"])

    assets = db.get_country_assets(country_id)
    asset_summary = []
    for a in assets[:5]:
        unit = config.ASSET_CATEGORIES.get(a['category'], ("", "عدد"))[1]
        asset_summary.append(f"  • {a['equipment_name']}: {format_number(a['amount'])} {unit}")

    if len(assets) > 5:
        asset_summary.append(f"  • ... و {len(assets) - 5} تجهیز دیگر")

    eq_text = "\n".join(asset_summary) if asset_summary else "  • بدون دارایی نظامی"

    text = (
        f"{notice}\n\n" if notice else ""
    ) + (
        f"🌐 *مدیریت کشور {c['flag']} {c['name']}*\n"
        f"👤 شناسه تلگرام بازیکن: `{c['player_id']}`\n"
        f"🔑 کلید کشور: `{c['country_key'] or 'نامشخص'}`\n\n"
        f"👥 جمعیت: {format_number(c['population'])}\n"
        f"🏦 خزانه: {format_money(c['treasury'])}\n"
        f"🪙 طلا: {format_number(c['gold'])}\n"
        f"📈 درآمد روزانه: {format_money(c['daily_income'])}\n\n"
        f"🛢️ ذخایر نفت: {format_oil(c['oil_reserves'])}\n"
        f"🛢️ نرخ تولید نفت: {format_oil(c['oil_production'])}/روز\n\n"
        f"🎖️ خلاصه دارایی‌های نظامی اختصاصی:\n{eq_text}"
    )

    keyboard = [
        [
            InlineKeyboardButton("🏦 ویرایش خزانه", callback_data=f"admin:menu_treasury:{c['id']}"),
            InlineKeyboardButton("🪙 ویرایش طلا", callback_data=f"admin:menu_gold:{c['id']}"),
        ],
        [
            InlineKeyboardButton("🛢️ ویرایش نفت", callback_data=f"admin:menu_oil:{c['id']}"),
            InlineKeyboardButton("🎖️ مدیریت دارایی‌های نظامی", callback_data=f"admin:menu_assets:{c['id']}"),
        ],
        [
            InlineKeyboardButton("📜 تراکنش‌ها و فعالیت‌های اخیر این کشور", callback_data=f"admin:c_tx_logs:{c['id']}"),
        ],
        [
            InlineKeyboardButton("✉️ ارسال پیام مستقیم به بازیکن", callback_data=f"admin:msg_prompt:{c['id']}"),
        ],
        [
            InlineKeyboardButton("🗑️ حذف کامل کشور", callback_data=f"admin:delconfirm:{c['id']}"),
        ],
        [
            InlineKeyboardButton("🔙 بازگشت به لیست کشورها", callback_data="admin:list:0"),
        ]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== زیرمنوهای تغییر خزانه، طلا، نفت و دارایی‌های نظامی ====================

async def menu_treasury(query, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return
    text = f"🏦 *تغییر خزانه کشور {c['flag']} {c['name']}*\nموجودی فعلی: {format_money(c['treasury'])}\n\nیکی از مقادیر زیر را انتخاب کنید یا مقدار دلخواه تایپ کنید:"

    keyboard = [
        [
            InlineKeyboardButton("➕ ۱۰ میلیون", callback_data=f"admin:adj:{c['id']}:treasury:10000000"),
            InlineKeyboardButton("➕ ۵۰ میلیون", callback_data=f"admin:adj:{c['id']}:treasury:50000000"),
            InlineKeyboardButton("➕ ۱۰۰ میلیون", callback_data=f"admin:adj:{c['id']}:treasury:100000000"),
        ],
        [
            InlineKeyboardButton("➖ ۱۰ میلیون", callback_data=f"admin:adj:{c['id']}:treasury:-10000000"),
            InlineKeyboardButton("➖ ۵۰ میلیون", callback_data=f"admin:adj:{c['id']}:treasury:-50000000"),
            InlineKeyboardButton("➖ ۱۰۰ میلیون", callback_data=f"admin:adj:{c['id']}:treasury:-100000000"),
        ],
        [
            InlineKeyboardButton("✏️ تنظیم دقیق عدد خزانه (تایپی)", callback_data=f"admin:prompt:{c['id']}:treasury"),
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:c:{c['id']}"),
        ]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def menu_gold(query, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return
    text = f"🪙 *تغییر طلای کشور {c['flag']} {c['name']}*\nطلای فعلی: {format_number(c['gold'])}\n\nیک گزینه را انتخاب کنید:"

    keyboard = [
        [
            InlineKeyboardButton("➕ ۵۰ طلا", callback_data=f"admin:adj:{c['id']}:gold:50"),
            InlineKeyboardButton("➕ ۲۰۰ طلا", callback_data=f"admin:adj:{c['id']}:gold:200"),
            InlineKeyboardButton("➕ ۱,۰۰۰ طلا", callback_data=f"admin:adj:{c['id']}:gold:1000"),
        ],
        [
            InlineKeyboardButton("➖ ۵۰ طلا", callback_data=f"admin:adj:{c['id']}:gold:-50"),
            InlineKeyboardButton("➖ ۲۰۰ طلا", callback_data=f"admin:adj:{c['id']}:gold:-200"),
            InlineKeyboardButton("➖ ۱,۰۰۰ طلا", callback_data=f"admin:adj:{c['id']}:gold:-1000"),
        ],
        [
            InlineKeyboardButton("✏️ تنظیم دقیق عدد طلا (تایپی)", callback_data=f"admin:prompt:{c['id']}:gold"),
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:c:{c['id']}"),
        ]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def menu_oil(query, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return
    text = (
        f"🛢️ *تغییر وضعیت نفت کشور {c['flag']} {c['name']}*\n"
        f"ذخایر فعلی: {format_oil(c['oil_reserves'])}\n"
        f"تولید روزانه فعلی: {format_oil(c['oil_production'])}/روز"
    )

    keyboard = [
        [
            InlineKeyboardButton("➕ ۱ میلیون بشکه ذخیره", callback_data=f"admin:adj:{c['id']}:oil_reserves:1000000"),
            InlineKeyboardButton("➕ ۱۰ میلیون بشکه ذخیره", callback_data=f"admin:adj:{c['id']}:oil_reserves:10000000"),
        ],
        [
            InlineKeyboardButton("➖ ۱ میلیون بشکه ذخیره", callback_data=f"admin:adj:{c['id']}:oil_reserves:-1000000"),
            InlineKeyboardButton("➖ ۱۰ میلیون بشکه ذخیره", callback_data=f"admin:adj:{c['id']}:oil_reserves:-10000000"),
        ],
        [
            InlineKeyboardButton("✏️ تنظیم عددی ذخایر نفت", callback_data=f"admin:prompt:{c['id']}:oil_reserves"),
            InlineKeyboardButton("✏️ تنظیم نرخ تولید روزانه", callback_data=f"admin:prompt:{c['id']}:oil_production"),
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:c:{c['id']}"),
        ]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def menu_assets(query, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return

    assets = db.get_country_assets(country_id)
    text = f"🎖️ *مدیریت دارایی‌های نظامی اختصاصی {c['flag']} {c['name']}*\n\nیک سلاح/تجهیز را برای تغییر تعداد انتخاب کنید:"

    keyboard = []
    for a in assets:
        unit = config.ASSET_CATEGORIES.get(a['category'], ("", "عدد"))[1]
        prod_mark = "✅" if a.get("producible", 1) == 1 else "🌐وارداتی"
        btn_label = f"{a['equipment_name']} ({format_number(a['amount'])} {unit}) [{prod_mark}]"
        keyboard.append([InlineKeyboardButton(btn_label, callback_data=f"admin:asset_item:{c['id']}:{a['equipment_key']}")])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:c:{c['id']}")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def menu_single_asset_item(query, country_id: int, equipment_key: str):
    c = db.get_country_by_id(country_id)
    asset = db.get_asset_by_key(country_id, equipment_key)
    if not c or not asset:
        return

    unit = config.ASSET_CATEGORIES.get(asset['category'], ("", "عدد"))[1]
    prod_str = "بومی (قابل خرید در فروشگاه)" if asset.get("producible", 1) == 1 else "وارداتی (غیرقابل خرید در فروشگاه)"

    text = (
        f"⚙️ *ویرایش دارایی نظامی:* {asset['equipment_name']}\n"
        f"کشور: {c['flag']} {c['name']}\n"
        f"نوع: `{prod_str}`\n"
        f"تعداد فعلی: `{format_number(asset['amount'])} {unit}`\n"
        f"قیمت واحد: {format_money(asset['buy_price'])}"
    )

    keyboard = [
        [
            InlineKeyboardButton("➕ ۱۰", callback_data=f"admin:adj_asset:{country_id}:{equipment_key}:10"),
            InlineKeyboardButton("➕ ۱۰۰", callback_data=f"admin:adj_asset:{country_id}:{equipment_key}:100"),
            InlineKeyboardButton("➕ ۱,۰۰۰", callback_data=f"admin:adj_asset:{country_id}:{equipment_key}:1000"),
        ],
        [
            InlineKeyboardButton("➖ ۱۰", callback_data=f"admin:adj_asset:{country_id}:{equipment_key}:-10"),
            InlineKeyboardButton("➖ ۱۰۰", callback_data=f"admin:adj_asset:{country_id}:{equipment_key}:-100"),
            InlineKeyboardButton("➖ ۱,۰۰۰", callback_data=f"admin:adj_asset:{country_id}:{equipment_key}:-1000"),
        ],
        [
            InlineKeyboardButton("✏️ تنظیم عدد دقیق (تایپی)", callback_data=f"admin:prompt_asset:{country_id}:{equipment_key}"),
            InlineKeyboardButton("🗑️ صفر کردن", callback_data=f"admin:set_asset:{country_id}:{equipment_key}:0"),
        ],
        [
            InlineKeyboardButton("🔙 بازگشت به لیست دارایی‌ها", callback_data=f"admin:menu_assets:{country_id}"),
        ]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== پردازش CallbackQuery های پنل ادمین ====================

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("⛔ شما ادمین نیستید!", show_alert=True)
        return

    data = query.data
    await query.answer()

    if data == "ignore":
        return

    if data == "admin:menu":
        await admin_panel(update, context)

    elif data == "admin:close":
        await query.delete_message()

    elif data == "admin:claim_un":
        admin_c = db.get_country_by_player(user_id)
        if admin_c:
            if admin_c.get("country_key") == "un":
                await query.edit_message_text(
                    "🇺🇳 **نقش سازمان ملل متحد از قبل برای شما فعال می‌باشد.**",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🇺🇳 ورود به اتاق ویژه دبیرکل سازمان ملل", callback_data="un:menu")],
                        [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]
                    ]),
                    parse_mode="Markdown"
                )
                return

            text = (
                f"⚠️ **فعال‌سازی نقش سازمان ملل متحد (🇺🇳)**\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"شما در حال حاضر هدایت کشور {admin_c['flag']} **{admin_c['name']}** را بر عهده دارید.\n\n"
                "جهت فعال‌سازی و دریافت کشور/نقش سازمان ملل، ابتدا باید کشور فعلی خود را لغو بفرمایید تا بدون کشور شوید."
            )
            keyboard = [
                [InlineKeyboardButton("❌ حذف کشور فعلی و فعال‌سازی سازمان ملل", callback_data="admin:reset_and_claim_un")],
                [InlineKeyboardButton("🔙 انصراف و بازگشت به پنل ادمین", callback_data="admin:menu")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return

        success, msg = db.claim_un_country(user_id)
        keyboard = [
            [InlineKeyboardButton("🇺🇳 ورود به اتاق ویژه دبیرکل سازمان ملل", callback_data="un:menu")],
            [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]
        ]
        await query.edit_message_text(f"{msg}\n\nاز این پس می‌توانید از تمام امکانات دبیرکل سازمان ملل استفاده بفرمایید.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:reset_and_claim_un":
        db.delete_country_by_player(user_id)
        success, msg = db.claim_un_country(user_id)
        keyboard = [
            [InlineKeyboardButton("🇺🇳 ورود به اتاق ویژه دبیرکل سازمان ملل", callback_data="un:menu")],
            [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]
        ]
        await query.edit_message_text(f"✅ کشور قبلی شما لغو شد.\n\n{msg}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:locks_menu":
        await admin_locks_menu(query, context)

    elif data.startswith("admin:toggle_lock:"):
        lock_key = data.split(":")[2]
        curr_val = db.get_setting(lock_key) == "1"
        new_val = "0" if curr_val else "1"
        db.set_setting(lock_key, new_val)
        await query.answer("وضعیت قفل با موفقیت تغییر یافت!", show_alert=True)
        await admin_locks_menu(query, context)

    elif data.startswith("admin:list:"):
        page = int(data.split(":")[2])
        await show_countries_list(query, context, page)

    elif data.startswith("admin:c:"):
        c_id = int(data.split(":")[2])
        await show_country_dashboard(query, context, c_id)

    elif data == "admin:stats":
        stats = db.get_game_stats()
        text = (
            "📊 *آمار کلی بازی «سیاست مدرن»*\n\n"
            f"🌐 تعداد کشورهای ساخته شده: `{stats['countries_count']}`\n"
            f"🏦 مجموع کل ثروت خزانه کشورها: {format_money(stats['total_treasury'])}\n"
            f"🪙 مجموع طلا در گردش: {format_number(stats['total_gold'])}\n"
            f"🛢️ مجموع ذخایر نفت: {format_oil(stats['total_oil'])}\n"
            f"🪖 مجموع کل تجهیزات و تسلیحات نظامی: {format_number(stats['total_equipment'])} عدد"
        )
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:monitor_menu":
        text = (
            "🔎 **رصد و پایش فعالیت بازیکنان**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "جهت مشاهده آخرین فعالیت‌ها، تراکنش‌ها و پیام‌های دیپلماتیک بازیکنان، بخش مورد نظر را انتخاب بفرمایید:"
        )
        keyboard = [
            [InlineKeyboardButton("✉️ رصد معاهدات و پیام‌های دیپلماتیک", callback_data="admin:dip_logs")],
            [InlineKeyboardButton("📜 رصد فعالیت‌ها و لاگ‌های سیستم", callback_data="admin:activity_logs")],
            [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:activity_logs":
        logs = db.get_recent_logs(20)
        lines = ["📜 *رصد آخرین فعالیت‌ها و لاگ‌های سیستم*\n━━━━━━━━━━━━━━━━━━\n"]
        if not logs:
            lines.append("هیچ لاگی در سیستم ثبت نشده است.")
        else:
            for lg in logs:
                dt_str = lg.get("created_at", "")[:19].replace("T", " ")
                actor_id = lg.get("actor", "")
                c = db.get_country_by_player(int(actor_id)) if (actor_id and actor_id.isdigit()) else None
                c_str = f"{c['flag']} {c['name']}" if c else f"`{actor_id}`"
                act_str = str(lg.get("action", "")).replace("_", "\\_")
                det_str = str(lg.get("details", "")).replace("_", "\\_")
                lines.append(f"• `{dt_str}` | *کاربر:* {c_str} | *عملیات:* `{act_str}` | {det_str}\n")
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به رصد بازیکنان", callback_data="admin:monitor_menu")]]
        try:
            await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        except Exception:
            try:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))
            except Exception:
                pass

    elif data == "admin:dip_logs":
        txs = db.get_recent_diplomatic_logs(20)
        lines = ["✉️ *رصد آخرین معاهدات و تراکنش‌های دیپلماتیک*\n━━━━━━━━━━━━━━━━━━\n"]
        if not txs:
            lines.append("هیچ معاهده یا تراکنش دیپلماتیکی ثبت نشده است.")
        else:
            for tx in txs:
                dt_str = tx.get("created_at", "")[:19].replace("T", " ")
                c = db.get_country_by_id(tx["country_id"])
                c_name = f"{c['flag']} {c['name']}" if c else "نامشخص"
                lines.append(f"• `{dt_str}` | *{c_name}:* {tx.get('description')} | *مبلغ/حجم:* {tx.get('amount')}\n")
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به رصد بازیکنان", callback_data="admin:monitor_menu")]]
        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:rankings":
        rankings = db.get_country_rankings()
        lines = ["🏆 *رتبه‌بندی ثروت و قدرتمندترین کشورها*\n━━━━━━━━━━━━━━━━━━\n"]
        if not rankings:
            lines.append("هیچ کشوری ساخته نشده است.")
        else:
            for idx, c in enumerate(rankings, 1):
                lines.append(f"{idx}. {c['flag']} *{c['name']}* | 🏦 خزانه: {format_money(c['treasury'])} | 🪙 طلا: {c['gold']} | 🛢️ نفت: {format_oil(c['oil_reserves'])}\n")
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:menu")]]
        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:pending_countries":
        pending_reqs = db.get_all_pending_country_requests()
        text = "📥 **درخواست‌های معلق انتخاب کشور (در انتظار تایید ادمین)**\n━━━━━━━━━━━━━━━━━━\n\n"

        keyboard = []
        if not pending_reqs:
            text += "✅ هیچ درخواست معلقی در حال حاضر وجود ندارد."
        else:
            text += "لطفاً برای بررسی و تعیین تکلیف، درخواست مد نظر را انتخاب بفرمایید:\n"
            for req in pending_reqs:
                c_info = config.COUNTRIES.get(req["country_key"], {})
                flag = c_info.get("flag", "🏴")
                c_name = c_info.get("name", req["country_key"])
                u_name = f"@{req['username']}" if req.get("username") else f"ID: {req['player_id']}"

                keyboard.append([
                    InlineKeyboardButton(f"✅ تایید {flag} {c_name} ({u_name})", callback_data=f"admin:approve_country:{req['id']}"),
                    InlineKeyboardButton("❌ رد", callback_data=f"admin:reject_country:{req['id']}")
                ])

        keyboard.append([InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:pending_roles":
        roles = db.get_pending_roleplays()
        text = "📝 *مدیریت رول‌های نظامی معلق (تاییدنشده)*\n━━━━━━━━━━━━━━━━━━\n\n"

        if not roles:
            text += "✅ در حال حاضر هیچ رول تاییدنشده‌ای در انتظار بررسی وجود ندارد."
            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:menu")]]
        else:
            text += "لطفاً برای بررسی و تایید، رول مد نظر را انتخاب کنید:"
            keyboard = []
            type_labels = {"attack": "📝 تهاجمی (حمله)", "defense": "🛡️ پدافندی (دفاع)"}
            for r in roles:
                c = db.get_country_by_id(r["country_id"])
                c_name = f"{c['flag']} {c['name']}" if c else "نامشخص"
                t_lbl = type_labels.get(r["role_type"], r["role_type"])
                btn_text = f"{c_name} | {t_lbl}"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"admin:show_role:{r['id']}")])
            keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="admin:menu")])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("admin:show_role:"):
        role_id = int(data.split(":")[2])
        r = db.get_roleplay_by_id(role_id)
        if not r or r["status"] != "pending":
            await query.edit_message_text("❌ این رول قبلاً تعیین تکلیف شده است.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:pending_roles")]]), parse_mode="Markdown")
            return

        c = db.get_country_by_id(r["country_id"])
        c_name = f"{c['flag']} {c['name']}" if c else "نامشخص"
        type_label = "📝 رول تهاجمی (حمله)" if r["role_type"] == "attack" else "🛡️ رول پدافندی (دفاع)"

        text = (
            f"📝 *بررسی رول نظامی — کشور {c_name}*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• *نوع رول:* {type_label}\n"
            f"• *تاریخ ثبت:* `{r.get('created_at', '')[:19].replace('T', ' ')}`\n"
            f"• *شناسه عددی کاربر:* `{r['player_id']}`\n\n"
            "📋 *متن کامل رول:*\n"
            f'"{r["role_text"]}"'
        )

        keyboard = [
            [InlineKeyboardButton("✅ تایید رول و ارسال پیام تایید به بازیکن", callback_data=f"admin:app_role:{role_id}")],
            [InlineKeyboardButton("❌ رد رول", callback_data=f"admin:rej_role:{role_id}")],
            [InlineKeyboardButton("🔙 بازگشت به لیست رول‌ها", callback_data="admin:pending_roles")]
        ]

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("admin:app_role:"):
        role_id = int(data.split(":")[2])
        r = db.get_roleplay_by_id(role_id)
        if not r:
            await query.edit_message_text("❌ رول یافت نشد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:pending_roles")]]), parse_mode="Markdown")
            return

        db.update_roleplay_status(role_id, "approved")
        c = db.get_country_by_id(r["country_id"])
        c_name = f"{c['flag']} {c['name']}" if c else "کشور"

        p_id = r["player_id"]
        type_label = "تهاجمی (حمله)" if r["role_type"] == "attack" else "پدافندی (دفاع)"
        player_msg = (
            f"✅ *رول نظامی {type_label} شما توسط مدیریت بازی تایید شد!*\n\n"
            f"👑 *کشور {c_name}:* طرح عملیاتی شما جهت ارزیابی و شبیه‌سازی نبرد وارد ستاد فرماندهی گردید."
        )
        try:
            await context.bot.send_message(chat_id=p_id, text=player_msg, parse_mode="Markdown")
        except Exception:
            pass

        keyboard = [[InlineKeyboardButton("🔙 بازگشت به لیست رول‌های معلق", callback_data="admin:pending_roles")]]
        await query.edit_message_text(f"✅ **رول کشور {c_name} با موفقیت تایید و از لیست معوقات حذف گردید.**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("admin:rej_role:"):
        role_id = int(data.split(":")[2])
        r = db.get_roleplay_by_id(role_id)
        if not r:
            await query.edit_message_text("❌ رول یافت نشد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:pending_roles")]]), parse_mode="Markdown")
            return

        db.update_roleplay_status(role_id, "rejected")
        c = db.get_country_by_id(r["country_id"])
        c_name = f"{c['flag']} {c['name']}" if c else "کشور"

        p_id = r["player_id"]
        type_label = "تهاجمی (حمله)" if r["role_type"] == "attack" else "پدافندی (دفاع)"
        player_msg = (
            f"❌ *رول نظامی {type_label} شما توسط مدیریت بازی رد شد.*\n\n"
            f"👑 *کشور {c_name}:* می‌توانید با اصلاح جزئیات، رول جدیدی از بخش 🎯 عملیات ثبت نمایید."
        )
        try:
            await context.bot.send_message(chat_id=p_id, text=player_msg, parse_mode="Markdown")
        except Exception:
            pass

        keyboard = [[InlineKeyboardButton("🔙 بازگشت به لیست رول‌های معلق", callback_data="admin:pending_roles")]]
        await query.edit_message_text(f"❌ **رول کشور {c_name} رد شد و از لیست معوقات حذف گردید.**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("admin:c_tx_logs:"):
        c_id = int(data.split(":")[2])
        c = db.get_country_by_id(c_id)
        txs = db.get_country_transactions(c_id, 20)
        lines = [f"📜 *تراکنش‌ها و فعالیت‌های اخیر کشور {c['flag']} {c['name']}*\n━━━━━━━━━━━━━━━━━━\n"]
        if not txs:
            lines.append("هیچ تراکنشی برای این کشور ثبت نشده است.")
        else:
            for tx in txs:
                dt_str = tx.get("created_at", "")[:19].replace("T", " ")
                lines.append(f"• `{dt_str}` | *شرح:* {tx.get('description')} | *نوع:* `{tx.get('type')}`\n")
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به داشبورد کشور", callback_data=f"admin:c:{c['id']}")]]
        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:war_start":
        text = "⚔️ *بخش تحلیل نبرد — خط تولید دستی هوشمند*\n\nرول‌ها را می‌گیری، پرامپت آماده را به هوش مصنوعی دلخواه می‌دهی و بلوک نتیجه را برمی‌گردانی.\n\nلطفاً *کشور مهاجم* را انتخاب کنید:"
        keyboard = []
        row = []
        for k, c in config.COUNTRIES.items():
            btn = InlineKeyboardButton(f"{c['flag']} {c['name']}", callback_data=f"admin:war_att:{k}")
            row.append(btn)
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("admin:war_att:"):
        att_key = data.split(":")[2]
        c_info = config.COUNTRIES.get(att_key, {})
        flag = c_info.get("flag", "")
        name = c_info.get("name", att_key)

        war_data = {"attacker_key": att_key}
        ACTIVE_WAR_ANALYSES[user_id] = war_data
        context.user_data["war_analysis"] = war_data
        context.user_data["admin_awaiting_input"] = {"type": "war_role_att", "attacker_key": att_key}

        text = (
            f"📝 *رول و برنامه عملیاتی کشور مهاجم ({flag} {name})*\n\n"
            "لطفاً *رول / نقشه عملیاتی و توضیحات تهاجمی* ارسال‌شده توسط بازیکن مهاجم را ارسال فرمایید:"
        )
        keyboard = [[InlineKeyboardButton("❌ انصراف و بازگشت", callback_data="admin:menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("admin:war_def_select:"):
        def_key = data.split(":")[2]
        c_info = config.COUNTRIES.get(def_key, {})
        flag = c_info.get("flag", "")
        name = c_info.get("name", def_key)

        war_data = ACTIVE_WAR_ANALYSES.get(user_id) or context.user_data.get("war_analysis", {})
        war_data["defender_key"] = def_key
        ACTIVE_WAR_ANALYSES[user_id] = war_data
        context.user_data["war_analysis"] = war_data
        context.user_data["admin_awaiting_input"] = {"type": "war_role_def", "defender_key": def_key}

        text = (
            f"🛡️ *طرح و رول دفاعی / پدافندی کشور مدافع ({flag} {name})*\n\n"
            "لطفاً *رول یا طرح دفاع هوایی / پدافندی* ارسال‌شده توسط بازیکن مدافع را ارسال فرمایید:\n"
            "*(در صورت عدم ارسال رول توسط بازیکن مدافع، عدد ۰ یا کلمه 'هیچ' را بفرستید)*"
        )
        keyboard = [[InlineKeyboardButton("❌ انصراف و بازگشت", callback_data="admin:menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("admin:war_def:"):
        def_key = data.split(":")[2]
        c_info = config.COUNTRIES.get(def_key, {})
        flag = c_info.get("flag", "")
        name = c_info.get("name", def_key)

        war_data = ACTIVE_WAR_ANALYSES.get(user_id) or context.user_data.get("war_analysis", {})
        war_data["defender_key"] = def_key
        ACTIVE_WAR_ANALYSES[user_id] = war_data
        context.user_data["war_analysis"] = war_data
        context.user_data["admin_awaiting_input"] = {"type": "war_role_def", "defender_key": def_key}

        text = (
            f"🛡️ *طرح و رول دفاعی / پدافندی کشور مدافع ({flag} {name})*\n\n"
            "لطفاً *رول یا طرح دفاع هوایی / پدافندی* ارسال‌شده توسط بازیکن مدافع را ارسال فرمایید:\n"
            "*(در صورت عدم ارسال رول توسط بازیکن مدافع، عدد ۰ یا کلمه 'هیچ' را بفرستید)*"
        )
        keyboard = [[InlineKeyboardButton("❌ انصراف و بازگشت", callback_data="admin:menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:war_manual_prompt":
        war_data = ACTIVE_WAR_ANALYSES.get(user_id) or context.user_data.get("war_analysis", {})
        att_key = war_data.get("attacker_key")
        def_key = war_data.get("defender_key")
        if not att_key or not def_key:
            await query.edit_message_text("❌ اطلاعات نبرد یافت نشد. از /admin شروع کنید.", parse_mode="Markdown")
            return
        prompt = war_data.get("war_prompt") or build_war_prompt(att_key, def_key, war_data.get("attacker_role", ""), war_data.get("defender_role", ""))
        war_data["war_prompt"] = prompt
        context.user_data["admin_awaiting_input"] = {"type": "war_manual_paste", "attacker_key": att_key, "defender_key": def_key}
        await query.edit_message_text("🧠 *پرامپت تحلیل (مجدداً ارسال شد)*\n\nکپی کن → به هوش مصنوعی بده → بلوک #WAR تا #END را همین‌جا بفرست.", parse_mode="Markdown")
        for i in range(0, len(prompt), 3800):
            await context.bot.send_message(chat_id=user_id, text=f"```\n{prompt[i:i+3800]}\n```", parse_mode="Markdown")

    elif data == "admin:war_manual_apply":
        war_data = ACTIVE_WAR_ANALYSES.get(user_id) or context.user_data.get("war_analysis") or LATEST_WAR_ANALYSIS
        if war_data.get("applied"):
            await query.answer("⚠️ تلفات این نبرد قبلاً اعمال شده است!", show_alert=True)
            return
        att_key = war_data.get("attacker_key")
        def_key = war_data.get("defender_key")
        losses = war_data.get("losses")
        if not att_key or not def_key or not losses:
            await query.edit_message_text("❌ داده نبرد ناقص است. از /admin شروع کنید.", parse_mode="Markdown")
            return

        note = war_data.get("targets_text", "")
        ok = war_analyzer.apply_war_losses_to_db(att_key, def_key, losses, note)
        war_data["applied"] = True

        a_info = config.COUNTRIES.get(att_key, {})
        d_info = config.COUNTRIES.get(def_key, {})
        report = (
            f"⚔️ *گزارش رسمی نبرد*\n"
            f"{a_info.get('flag','')} *{a_info.get('name', att_key)}* علیه {d_info.get('flag','')} *{d_info.get('name', def_key)}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"• تلفات نظامی مهاجم: {losses['att_military_loss']:,} نفر\n"
            f"• تلفات نظامی مدافع: {losses['def_military_loss']:,} نفر\n"
            f"• تلفات غیرنظامی: مهاجم {losses['att_civilian_loss']:,} | مدافع {losses['def_civilian_loss']:,}\n"
            f"• تجهیزات مهاجم: {len(losses['att_losses'])} قلم | مدافع: {len(losses['def_losses'])} قلم"
        )
        if note:
            report += f"\n\n■ *ارزیابی:*\n> {note}"
        war_data["report_text"] = report
        ACTIVE_WAR_ANALYSES[user_id] = war_data
        context.user_data["war_analysis"] = war_data
        LATEST_WAR_ANALYSIS.update(war_data)

        receipt_att = war_analyzer.build_detailed_loss_receipt(
            att_key, losses.get("att_losses", []), losses.get("att_military_loss", 0), losses.get("att_civilian_loss", 0),
            "عملیات تهاجمی اخیر", is_attacker=True
        )
        receipt_def = war_analyzer.build_detailed_loss_receipt(
            def_key, losses.get("def_losses", []), losses.get("def_military_loss", 0), losses.get("def_civilian_loss", 0),
            "عملیات دفاعی اخیر", is_attacker=False
        )
        war_data["receipt_att"] = receipt_att
        war_data["receipt_def"] = receipt_def

        keyboard = [
            [InlineKeyboardButton("📢 برودکست گزارش به بازیکنان", callback_data="admin:war_broadcast")],
            [InlineKeyboardButton("📄 ارسال فاکتور تلفات به بازیکنان", callback_data="admin:war_broadcast_receipts")],
            [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")],
        ]
        await query.edit_message_text(
            ("✅ *تلفات با موفقیت از دیتابیس کسر شد!*\n\n" if ok else "⚠️ *خطا در کسر تلفات — لاگ را بررسی کن.*\n\n") + report,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        await context.bot.send_message(chat_id=user_id, text=receipt_att, parse_mode="Markdown")
        await context.bot.send_message(chat_id=user_id, text=receipt_def, parse_mode="Markdown")

    elif data == "admin:war_apply":
        war_data = ACTIVE_WAR_ANALYSES.get(user_id) or context.user_data.get("war_analysis") or LATEST_WAR_ANALYSIS
        if war_data.get("applied"):
            await query.answer("⚠️ تلفات این نبرد قبلاً اعمال شده است!", show_alert=True)
            return
        att_key = war_data.get("attacker_key")
        def_key = war_data.get("defender_key")
        losses = war_data.get("losses", {})
        targets_text = war_data.get("targets_text", "")

        if att_key and def_key and losses:
            # 1. Deduct losses from DB & apply strategic target impacts
            war_analyzer.apply_war_losses_to_db(att_key, def_key, losses, targets_text)
            war_data["applied"] = True  # قفل اعمال مجدد (جلوگیری از کسر دوباره تلفات)

            # 2. Build detailed loss receipts
            receipt_att = war_analyzer.build_detailed_loss_receipt(
                att_key, losses.get("att_losses", []),
                losses.get("att_military_loss", 0), losses.get("att_civilian_loss", 0),
                "عملیات تهاجمی اخیر", is_attacker=True
            )
            receipt_def = war_analyzer.build_detailed_loss_receipt(
                def_key, losses.get("def_losses", []),
                losses.get("def_military_loss", 0), losses.get("def_civilian_loss", 0),
                "عملیات دفاعی اخیر", is_attacker=False
            )

            war_data["receipt_att"] = receipt_att
            war_data["receipt_def"] = receipt_def
            ACTIVE_WAR_ANALYSES[user_id] = war_data
            context.user_data["war_analysis"] = war_data
            LATEST_WAR_ANALYSIS.update(war_data)

            keyboard = [
                [InlineKeyboardButton("📢 برودکست فاکتور تلفات به بازیکنان", callback_data="admin:war_broadcast_receipts")],
                [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]
            ]

            confirm_msg = (
                "✅ *تلفات و خسارات فوق با موفقیت در دیتابیس ثبت و کسر گردید.*\n\n"
                "📋 *فاکتورهای دقیق قبل/تلفات/بعد هر دو کشور در زیر ارائه گردید:*"
            )

            try:
                await query.edit_message_text(confirm_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            except Exception:
                try: await query.message.reply_text(confirm_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
                except Exception: pass

            async def send_safe_receipt(receipt_text):
                if not receipt_text:
                    return
                try:
                    if len(receipt_text) > 3800:
                        await context.bot.send_message(chat_id=user_id, text=receipt_text[:3800], parse_mode="Markdown")
                        await context.bot.send_message(chat_id=user_id, text=receipt_text[3800:], parse_mode="Markdown")
                    else:
                        await context.bot.send_message(chat_id=user_id, text=receipt_text, parse_mode="Markdown")
                except Exception:
                    try:
                        if len(receipt_text) > 3800:
                            await context.bot.send_message(chat_id=user_id, text=receipt_text[:3800])
                            await context.bot.send_message(chat_id=user_id, text=receipt_text[3800:])
                        else:
                            await context.bot.send_message(chat_id=user_id, text=receipt_text)
                    except Exception as ex:
                        print(f"Failed to send receipt: {ex}")

            await send_safe_receipt(receipt_att)
            await send_safe_receipt(receipt_def)
        else:
            await query.edit_message_text("❌ داده‌های سناریو پیدا نشد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:menu")]]), parse_mode="Markdown")

    elif data == "admin:war_broadcast_receipts":
        war_data = ACTIVE_WAR_ANALYSES.get(user_id) or context.user_data.get("war_analysis") or LATEST_WAR_ANALYSIS
        receipt_att = war_data.get("receipt_att")
        receipt_def = war_data.get("receipt_def")

        if receipt_att and receipt_def:
            users = db.get_all_countries()
            sent_count = 0
            for u in users:
                p_id = u.get("player_id")
                if p_id:
                    try:
                        await context.bot.send_message(chat_id=p_id, text=receipt_att, parse_mode="Markdown")
                        await context.bot.send_message(chat_id=p_id, text=receipt_def, parse_mode="Markdown")
                        sent_count += 1
                    except Exception:
                        pass
            await query.answer(f"📢 فاکتورها به {sent_count} بازیکن ارسال شد!", show_alert=True)
            keyboard = [
                [InlineKeyboardButton("📢 ارسال مجدد فاکتور تلفات به بازیکنان", callback_data="admin:war_broadcast_receipts")],
                [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]
            ]
            await query.message.reply_text(
                f"📢 *فاکتورهای دقیق تلفات با موفقیت به {sent_count} بازیکن ارسال شد.*",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )

    elif data == "admin:war_broadcast":
        war_data = ACTIVE_WAR_ANALYSES.get(user_id) or context.user_data.get("war_analysis") or LATEST_WAR_ANALYSIS
        report_text = war_data.get("report_text")
        try:
            war_id = int(war_data.get("war_id", 0))
        except (TypeError, ValueError):
            war_id = 0

        player_nav_keyboard = None
        if war_id > 0:
            player_nav_keyboard = InlineKeyboardMarkup([
                [
                    InlineKeyboardButton("📋 گاه‌شماری نبرد", callback_data=f"war_view:timeline:{war_id}"),
                    InlineKeyboardButton("💥 آسیب‌های زیرساختی", callback_data=f"war_view:targets:{war_id}"),
                ],
                [
                    InlineKeyboardButton("🗺️ وضعیت خطوط مرزی", callback_data=f"war_view:territory:{war_id}"),
                    InlineKeyboardButton("📊 فاکتور تلفات و تجهیزات", callback_data=f"war_view:losses:{war_id}"),
                ],
                [InlineKeyboardButton("🌐 خلاصه ارزیابی نبرد", callback_data=f"war_view:summary:{war_id}")],
            ])

        if report_text:
            users = db.get_all_countries()
            sent_count = 0
            for u in users:
                p_id = u.get("player_id")
                if p_id:
                    try:
                        if len(report_text) > 4000:
                            await context.bot.send_message(chat_id=p_id, text=report_text[:3800], parse_mode="Markdown")
                            await context.bot.send_message(chat_id=p_id, text=report_text[3800:], reply_markup=player_nav_keyboard, parse_mode="Markdown")
                        else:
                            await context.bot.send_message(chat_id=p_id, text=report_text, reply_markup=player_nav_keyboard, parse_mode="Markdown")
                        sent_count += 1
                    except Exception:
                        pass
            await query.answer(f"📢 گزارش نبرد به {sent_count} بازیکن ارسال گردید!", show_alert=True)
            keyboard = [
                [InlineKeyboardButton("✅ تایید و کسر آنی تلفات از دیتابیس", callback_data="admin:war_apply")],
                [InlineKeyboardButton("📢 ارسال مجدد برودکست به بازیکنان", callback_data="admin:war_broadcast")],
                [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]
            ]
            if len(report_text) > 3500:
                await query.message.reply_text(
                    f"📢 *گزارش نبرد با موفقیت به {sent_count} کشور/بازیکن برودکست شد.*",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
            else:
                await query.edit_message_text(
                    f"{report_text}\n\n━━━━━━━━━━━━━━━━━━\n📢 *گزارش نبرد با موفقیت به {sent_count} کشور/بازیکن برودکست شد.*",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )

    elif data == "admin:sync_catalog":
        db.sync_all_country_assets_to_catalog()
        text = "⚡ *همگام‌سازی کامل انجام شد!*\nتمام کشورهای دیتابیس با آمار و تجهیزات کاتالوگ جدید به‌روزرسانی شدند."
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:daily_income":
        from main import daily_income_job
        count = await daily_income_job(context, force=True)
        await query.edit_message_text(
            f"⚡ *درآمد روزانه و گزارش کشورها با موفقیت برای {count} کشور واریز و ارسال شد!*",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:menu")]]),
            parse_mode="Markdown"
        )

    elif data.startswith("admin:approve_country:"):
        req_id = int(data.split(":")[2])
        req = db.get_pending_country_request(req_id)
        if not req:
            await query.edit_message_text("❌ این درخواست قبلاً تعیین تکلیف یا لغو شده است.", parse_mode="Markdown")
            return

        c_key = req["country_key"]
        c_info = config.COUNTRIES.get(c_key, {})

        if db.get_country_by_key(c_key):
            db.delete_pending_country_request(req_id)
            await query.edit_message_text(f"❌ کشور {c_info.get('name', c_key)} قبلاً به کاربر دیگری واگذار شده است.", parse_mode="Markdown")
            return

        c_id = db.create_country(
            player_id=req["player_id"],
            name=c_info["name"],
            flag=c_info["flag"],
            country_key=c_key,
            username=req["username"]
        )
        db.delete_pending_country_request(req_id)
        db.add_log(actor=str(user_id), action="approve_country", details=f"{c_key} to {req['player_id']}")

        await query.edit_message_text(
            f"✅ *کشور {c_info['flag']} {c_info['name']} با موفقیت به کاربر @{req['username']} (ID: `{req['player_id']}`) واگذار گردید.*",
            parse_mode="Markdown"
        )

        p_id = req["player_id"]
        congratulations_msg = (
            f"🎉 *تبریک! درخواست انتخاب کشور شما توسط مدیریت عالی بازی تایید گردید.*\n\n"
            f"👑 *رهبر گرامی، کشور {c_info['flag']} {c_info['name']} با موفقیت به شما واگذار شد.*\n\n"
            "آرزوی موفقیت، اقتدار و سربلندی برای دولت و ملت شما در عرصه بین‌المللی داریم.\n"
            "هم‌اکنون کیبورد مدیریت کشور در پایین صفحه برای شما فعال گردید 👇"
        )
        try:
            await context.bot.send_message(
                chat_id=p_id,
                text=congratulations_msg,
                reply_markup=get_main_keyboard(p_id),
                parse_mode="Markdown"
            )
        except Exception as e:
            print(f"Error sending approval message to player {p_id}: {e}")

    elif data.startswith("admin:reject_country:"):
        req_id = int(data.split(":")[2])
        req = db.get_pending_country_request(req_id)
        if not req:
            await query.edit_message_text("❌ این درخواست قبلاً تعیین تکلیف شده است.", parse_mode="Markdown")
            return

        c_key = req["country_key"]
        c_info = config.COUNTRIES.get(c_key, {})
        p_id = req["player_id"]

        db.delete_pending_country_request(req_id)
        db.add_log(actor=str(user_id), action="reject_country", details=f"{c_key} for {p_id}")

        await query.edit_message_text(
            f"❌ *درخواست کشور {c_info.get('flag', '')} {c_info.get('name', c_key)} برای کاربر @{req['username']} رد شد.*",
            parse_mode="Markdown"
        )

        try:
            await context.bot.send_message(
                chat_id=p_id,
                text=(
                    f"❌ *درخواست شما برای انتخاب کشور {c_info.get('flag', '')} {c_info.get('name', c_key)} توسط ادمین بازی رد شد.*\n\n"
                    "می‌توانید با ارسال دستور /start کشور دیگری را انتخاب نمایید."
                ),
                parse_mode="Markdown"
            )
        except Exception:
            pass

    # منوهای ویرایش
    elif data.startswith("admin:menu_treasury:"):
        c_id = int(data.split(":")[2])
        await menu_treasury(query, c_id)

    elif data.startswith("admin:menu_gold:"):
        c_id = int(data.split(":")[2])
        await menu_gold(query, c_id)

    elif data.startswith("admin:menu_oil:"):
        c_id = int(data.split(":")[2])
        await menu_oil(query, c_id)

    elif data.startswith("admin:menu_assets:"):
        c_id = int(data.split(":")[2])
        await menu_assets(query, c_id)

    elif data.startswith("admin:asset_item:"):
        _, _, c_id, equipment_key = data.split(":", 3)
        await menu_single_asset_item(query, int(c_id), equipment_key)

    # تغییر نسبی فیلدها
    elif data.startswith("admin:adj:"):
        _, _, c_id_str, field, delta_str = data.split(":")
        c_id, delta = int(c_id_str), int(delta_str)

        if field == "treasury":
            db.adjust_treasury(c_id, delta)
        elif field == "gold":
            db.adjust_gold(c_id, delta)
        elif field == "oil_reserves":
            db.adjust_oil(c_id, delta)

        c = db.get_country_by_id(c_id)
        field_names = {"treasury": "خزانه", "gold": "طلا", "oil_reserves": "ذخیره نفت"}
        notice = f"✅ {field_names.get(field, field)} کشور {c['name']} تغییر یافت."
        await show_country_dashboard(query, context, c_id, notice=notice)

    elif data.startswith("admin:adj_asset:"):
        _, _, c_id_str, equipment_key, delta_str = data.split(":")
        c_id, delta = int(c_id_str), int(delta_str)
        asset = db.get_asset_by_key(c_id, equipment_key)
        if asset:
            db.set_asset_amount(c_id, equipment_key, asset["amount"] + delta)
        await menu_single_asset_item(query, c_id, equipment_key)

    elif data.startswith("admin:set_asset:"):
        _, _, c_id_str, equipment_key, qty_str = data.split(":")
        c_id, qty = int(c_id_str), int(qty_str)
        db.set_asset_amount(c_id, equipment_key, qty)
        await menu_single_asset_item(query, c_id, equipment_key)

    # درخواست ورودی متنی
    elif data.startswith("admin:prompt:"):
        _, _, c_id_str, field = data.split(":")
        c_id = int(c_id_str)
        c = db.get_country_by_id(c_id)
        context.user_data["admin_awaiting_input"] = {"type": "field", "country_id": c_id, "field": field}

        field_names = {
            "treasury": "خزانه (دلار)",
            "gold": "طلا",
            "oil_reserves": "ذخایر نفت (بشکه)",
            "oil_production": "نرخ تولید روزانه نفت (بشکه)"
        }

        await query.edit_message_text(
            f"✏️ *تنظیم سفارشی {field_names.get(field, field)} برای کشور {c['name']}*\n\n"
            f"لطفاً عدد جدید مورد نظر را در یک پیام بفرستید (مثلاً `250000000`):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data=f"admin:c:{c_id}")]])
        )

    elif data.startswith("admin:prompt_asset:"):
        _, _, c_id_str, equipment_key = data.split(":")
        c_id = int(c_id_str)
        c = db.get_country_by_id(c_id)
        asset = db.get_asset_by_key(c_id, equipment_key)
        context.user_data["admin_awaiting_input"] = {"type": "asset_amount", "country_id": c_id, "equipment_key": equipment_key}

        await query.edit_message_text(
            f"✏️ *تنظیم تعداد {asset['equipment_name']} برای کشور {c['name']}*\n\n"
            f"لطفاً تعداد جدید مورد نظر را ارسال کنید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data=f"admin:asset_item:{c_id}:{equipment_key}")]])
        )

    elif data.startswith("admin:msg_prompt:"):
        c_id = int(data.split(":")[2])
        c = db.get_country_by_id(c_id)
        context.user_data["admin_awaiting_input"] = {"type": "direct_msg", "country_id": c_id, "player_id": c["player_id"]}

        await query.edit_message_text(
            f"✉️ *ارسال پیام مستقیم به رهبر {c['flag']} {c['name']}*\n\n"
            f"متن پیام خود را بنویسید تا مستقیماً برای بازیکن ارسال شود:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data=f"admin:c:{c_id}")]])
        )

    elif data == "admin:broadcast_prompt":
        context.user_data["admin_awaiting_input"] = {"type": "broadcast"}
        await query.edit_message_text(
            "📢 *ارسال پیام همگانی به تمام بازیکنان*\n\n"
            "متن پیام اعلان بازی را ارسال کنید تا برای تمام رهبران کشورها فرستاده شود:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="admin:menu")]])
        )

    elif data == "admin:set_channel_prompt":
        context.user_data["admin_awaiting_input"] = {"type": "set_channel"}
        curr_ch = config.get_channel_id()
        await query.edit_message_text(
            f"📢 *تنظیم آیدی کانال تلگرام جهت انتشار بیانیه‌ها و توییت‌ها*\n━━━━━━━━━━━━━━━━━━\n\n"
            f"• *آیدی کانال فعلی:* `{curr_ch}`\n\n"
            "لطفاً *آیدی یا شناسه عددی کانال تلگرام* خود را ارسال فرمایید (مثلاً: `@ModernWarFarChannel` یا `-1001234567890`):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="admin:menu")]]),
            parse_mode="Markdown"
        )

    # تأیید و اجرای حذف کشور
    elif data.startswith("admin:delconfirm:"):
        c_id = int(data.split(":")[2])
        c = db.get_country_by_id(c_id)
        text = (
            f"⚠️ *آیا از حذف کامل کشور {c['flag']} {c['name']} مطمئن هستید؟*\n\n"
            f"• شناسه بازیکن: `{c['player_id']}`\n"
            f"• تمام ثروت، طلا، نفت و تجهیزات این کشور حذف خواهد شد و بازیکن می‌تواند دوباره /start بزند.\n"
            f"این عمل غیرقابل بازگشت است!"
        )
        keyboard = [
            [InlineKeyboardButton("🔥 بله، حذف کن!", callback_data=f"admin:delfinal:{c_id}")],
            [InlineKeyboardButton("❌ انصراف", callback_data=f"admin:c:{c_id}")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("admin:delfinal:"):
        c_id = int(data.split(":")[2])
        c = db.get_country_by_id(c_id)
        if c:
            name = c["name"]
            db.delete_country_by_id(c_id)
            await query.edit_message_text(
                f"✅ کشور *{name}* با موفقیت و به‌طور کامل حذف شد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 بازگشت به لیست کشورها", callback_data="admin:list:0")]])
            )


# ==================== دریافت ورودی‌های تایپی ادمین ====================

async def admin_input_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    input_state = context.user_data.get("admin_awaiting_input")
    if not input_state:
        return

    text = update.message.text.strip()
    input_type = input_state.get("type")

    del context.user_data["admin_awaiting_input"]

    clean_text = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١۲٣٤٥٦٧٨٩", "01234567890123456789")).replace(",", "").replace("_", "")

    if input_type == "field":
        c_id = input_state["country_id"]
        field = input_state["field"]
        try:
            val = int(clean_text)
            db.update_country_field(c_id, field, val)
            c = db.get_country_by_id(c_id)
            await update.message.reply_text(f"✅ مقدار {field} برای کشور {c['name']} با موفقیت به {format_number(val)} تغییر یافت.\nبرای ادامه /admin را بزنید.", parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("❌ عدد وارد شده نامعتبر بود. عملیات لغو شد. برای مدیریت /admin را بزنید.", parse_mode="Markdown")

    elif input_type == "asset_amount":
        c_id = input_state["country_id"]
        eq_key = input_state["equipment_key"]
        try:
            val = int(clean_text)
            db.set_asset_amount(c_id, eq_key, val)
            c = db.get_country_by_id(c_id)
            asset = db.get_asset_by_key(c_id, eq_key)
            await update.message.reply_text(f"✅ تعداد {asset['equipment_name']} برای کشور {c['name']} به {format_number(val)} تغییر یافت.\nبرای ادامه /admin را بزنید.", parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("❌ عدد وارد شده نامعتبر بود. عملیات لغو شد. برای مدیریت /admin را بزنید.", parse_mode="Markdown")

    elif input_type == "direct_msg":
        player_id = input_state["player_id"]
        c_id = input_state["country_id"]
        c = db.get_country_by_id(c_id)
        try:
            await context.bot.send_message(
                chat_id=player_id,
                text=f"📩 *پیام مستقیم از طرف ادمین بازی:*\n\n{text}",
                parse_mode="Markdown"
            )
            await update.message.reply_text(f"✅ پیام شما با موفقیت برای رهبر کشور {c['name']} ارسال شد.", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ ارسال پیام به بازیکن ناموفق بود:\n{e}", parse_mode="Markdown")

    elif input_type == "war_role_att":
        att_key = input_state["attacker_key"]
        role_text = update.message.text.strip()

        if "war_analysis" not in context.user_data:
            context.user_data["war_analysis"] = {}
        context.user_data["war_analysis"]["attacker_key"] = att_key
        context.user_data["war_analysis"]["attacker_role"] = role_text

        c_info = config.COUNTRIES.get(att_key, {})
        flag = c_info.get("flag", "")
        name = c_info.get("name", att_key)

        text_msg = (
            f"🎯 *رول و برنامه عملیاتی کشور {flag} {name} دریافت گردید.*\n\n"
            "اکنون *کشور مدافع* را جهت ارزیابی و شبیه‌سازی نبرد انتخاب فرمایید:"
        )

        keyboard = []
        row = []
        for k, c in config.COUNTRIES.items():
            if k == att_key:
                continue
            btn = InlineKeyboardButton(f"{c['flag']} {c['name']}", callback_data=f"admin:war_def_select:{k}")
            row.append(btn)
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data="admin:menu")])

        await update.message.reply_text(text_msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif input_type == "war_manual_paste":
        parsed, err = parse_war_block(text)
        if err or not parsed:
            await update.message.reply_text(
                f"❌ *بلوک نامعتبر است:* {err or 'خطای ناشناخته'}\n\n"
                "بلوک کامل (از #WAR تا #END) را دوباره بفرستید، یا از دکمه پرامپت مجدد استفاده کنید.",
                parse_mode="Markdown"
            )
            return

        war_data = ACTIVE_WAR_ANALYSES.get(user_id) or context.user_data.get("war_analysis", {})
        att_key = war_data.get("attacker_key")
        def_key = war_data.get("defender_key")
        if not att_key or not def_key:
            await update.message.reply_text("❌ اطلاعات نبرد یافت نشد. از /admin شروع کنید.", parse_mode="Markdown")
            return

        losses, notes = build_losses_from_block(parsed, att_key, def_key)
        war_data["losses"] = losses
        war_data["targets_text"] = parsed.get("note", "")
        ACTIVE_WAR_ANALYSES[user_id] = war_data
        context.user_data["war_analysis"] = war_data

        a_info = config.COUNTRIES.get(att_key, {})
        d_info = config.COUNTRIES.get(def_key, {})
        prev = (
            f"📋 *پیش‌نمایش تحلیل نبرد*\n"
            f"{a_info.get('flag','')} *{a_info.get('name', att_key)}* ⚔️ {d_info.get('flag','')} *{d_info.get('name', def_key)}*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"• تلفات نظامی مهاجم: *{losses['att_military_loss']:,}*\n"
            f"• تلفات نظامی مدافع: *{losses['def_military_loss']:,}*\n"
            f"• غیرنظامی: مهاجم {losses['att_civilian_loss']:,} | مدافع {losses['def_civilian_loss']:,}\n"
        )
        if losses["att_losses"]:
            prev += "\n🔻 *تجهیزات مهاجم (مصرف/تلفات):*\n" + "\n".join(
                f"  • {x['equipment_name']} → {x['amount']:,}" for x in losses["att_losses"][:12])
        if losses["def_losses"]:
            prev += "\n\n🔻 *تجهیزات مدافع (منهدم‌شده):*\n" + "\n".join(
                f"  • {x['equipment_name']} → {x['amount']:,}" for x in losses["def_losses"][:12])
        if parsed.get("note"):
            prev += f"\n\n📝 _{parsed['note']}_"
        if notes:
            prev += "\n\n⚠️ " + "\n⚠️ ".join(notes)
        prev += "\n\n✅ در صورت تایید، تلفات از دیتابیس کسر می‌شود."

        keyboard = [
            [InlineKeyboardButton("✅ تایید و کسر تلفات", callback_data="admin:war_manual_apply")],
            [InlineKeyboardButton("🔁 دریافت مجدد پرامپت", callback_data="admin:war_manual_prompt")],
            [InlineKeyboardButton("❌ انصراف", callback_data="admin:menu")],
        ]
        await update.message.reply_text(prev, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    elif input_type == "war_role_def":
        def_key = input_state["defender_key"]
        def_role_raw = update.message.text.strip()
        def_role = "" if def_role_raw in ["0", "۰", "هیچ", "ندارد"] else def_role_raw

        war_data = ACTIVE_WAR_ANALYSES.get(user_id) or context.user_data.get("war_analysis", {})
        att_key = war_data.get("attacker_key")
        att_role = war_data.get("attacker_role", "")

        if att_key and def_key == att_key:
            await update.message.reply_text("❌ **خطا:** کشور مهاجم و مدافع نمی‌توانند یکسان باشند!", parse_mode="Markdown")
            return

        war_data["defender_key"] = def_key
        war_data["defender_role"] = def_role
        ACTIVE_WAR_ANALYSES[user_id] = war_data
        context.user_data["war_analysis"] = war_data

        # خط تولید دستی: پرامپت آماده برای هوش مصنوعی خارجی
        prompt = build_war_prompt(att_key, def_key, att_role, def_role)
        war_data["war_prompt"] = prompt
        context.user_data["admin_awaiting_input"] = {"type": "war_manual_paste", "attacker_key": att_key, "defender_key": def_key}

        await update.message.reply_text(
            "🧠 *خط تولید دستی:* پرامپت زیر را به هر هوش مصنوعی‌ای بده؛ بلوک `#WAR تا #END` که برگرداند را همین‌جا بفرست تا اعمال شود.",
            parse_mode="Markdown"
        )
        for i in range(0, len(prompt), 3800):
            await update.message.reply_text(f"```\n{prompt[i:i+3800]}\n```", parse_mode="Markdown")

    elif input_type == "set_channel":
        db.set_setting("channel_id", text)
        await update.message.reply_text(
            f"✅ *آیدی کانال تلگرام با موفقیت بروزرسانی شد!*\n\n"
            f"• *کانال جدید:* `{text}`\n\n"
            "کافیست ربات را در این کانال به‌عنوان ادمین با دسترسی ارسال پیام اضافه فرمایید تا بیانیه‌ها و توییت‌ها مستقیماً در آن منتشر شوند.",
            parse_mode="Markdown"
        )

    elif input_type == "broadcast":
        countries = db.get_all_countries()
        success_count = 0
        fail_count = 0
        msg_text = f"📢 *اطلاعیه همگانی ادمین بازی:*\n\n{text}"

        for c in countries:
            try:
                await context.bot.send_message(chat_id=c["player_id"], text=msg_text, parse_mode="Markdown")
                success_count += 1
            except Exception:
                fail_count += 1

        await update.message.reply_text(
            f"📢 *نتیجه ارسال پیام همگانی:*\n\n"
            f"✅ ارسال موفق به: {success_count} کشور\n"
            f"❌ ناموفق: {fail_count} کشور"
        )


# ==================== دستورات متنی قدیمی ادمین جهت سازگاری ====================

async def addmoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ این دستور فقط برای ادمین‌هاست.", parse_mode="Markdown")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text("کاربرد: /addmoney <player_id> <amount>", parse_mode="Markdown")
        return

    try:
        player_id, amount = int(args[0]), int(args[1])
    except ValueError:
        await update.message.reply_text("مقادیر باید عدد باشند.", parse_mode="Markdown")
        return

    country = db.get_country_by_player(player_id)
    if not country:
        await update.message.reply_text("کشوری پیدا نشد.", parse_mode="Markdown")
        return

    db.adjust_treasury(country["id"], amount)
    await update.message.reply_text(f"✅ مبلغ {format_money(amount)} به خزانه {country['name']} اضافه شد.", parse_mode="Markdown")


async def removemoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ این دستور فقط برای ادمین‌هاست.", parse_mode="Markdown")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text("کاربرد: /removemoney <player_id> <amount>", parse_mode="Markdown")
        return

    try:
        player_id, amount = int(args[0]), int(args[1])
    except ValueError:
        await update.message.reply_text("مقادیر باید عدد باشند.", parse_mode="Markdown")
        return

    country = db.get_country_by_player(player_id)
    if not country:
        await update.message.reply_text("کشوری پیدا نشد.", parse_mode="Markdown")
        return

    db.adjust_treasury(country["id"], -amount)
    await update.message.reply_text(f"✅ مبلغ {format_money(amount)} از خزانه {country['name']} کم شد.", parse_mode="Markdown")


async def listcountries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ این دستور فقط برای ادمین‌هاست.", parse_mode="Markdown")
        return

    countries = db.get_all_countries()
    if not countries:
        await update.message.reply_text("هنوز هیچ کشوری ثبت نشده.", parse_mode="Markdown")
        return

    lines = ["📋 لیست کشورها:\n"]
    for c in countries:
        lines.append(f"{c['flag']} {c['name']} — player_id: `{c['player_id']}` — خزانه: {format_money(c['treasury'])}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def war_view_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پردازش کلیک روی دکمه‌های شیشه‌ای تعاملی گزارش نبرد."""
    query = update.callback_query
    await query.answer()

    parts = query.data.split(":")
    if len(parts) != 3:
        return

    section = parts[1]
    war_id = int(parts[2])

    war_data = db.get_war_result_by_id(war_id)
    if not war_data:
        await query.answer("❌ اطلاعات سناریوی این نبرد در دیتابیس یافت نشد.", show_alert=True)
        return

    user_id = query.from_user.id
    user_is_adm = is_admin(user_id)

    nav_keyboard = [
        [
            InlineKeyboardButton("📋 گاه‌شماری نبرد", callback_data=f"war_view:timeline:{war_id}"),
            InlineKeyboardButton("💥 آسیب‌های زیرساختی", callback_data=f"war_view:targets:{war_id}"),
        ],
        [
            InlineKeyboardButton("🗺️ وضعیت خطوط مرزی", callback_data=f"war_view:territory:{war_id}"),
            InlineKeyboardButton("📊 فاکتور تلفات و تجهیزات", callback_data=f"war_view:losses:{war_id}"),
        ],
        [InlineKeyboardButton("🌐 خلاصه ارزیابی نبرد", callback_data=f"war_view:summary:{war_id}")],
    ]

    if user_is_adm:
        nav_keyboard.append([InlineKeyboardButton("✅ تایید و کسر آنی تلفات از دیتابیس", callback_data="admin:war_apply")])
        nav_keyboard.append([InlineKeyboardButton("📢 برودکست گزارش به بازیکنان", callback_data="admin:war_broadcast")])
        nav_keyboard.append([InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")])

    if section == "timeline":
        display_text = war_data["timeline_text"]
    elif section == "targets":
        display_text = war_data["targets_text"]
    elif section == "territory":
        display_text = war_data["territory_text"]
    elif section == "losses":
        try:
            losses_meta = json.loads(war_data["losses_json"])
            receipt_att = losses_meta.get("receipt_att", "")
            receipt_def = losses_meta.get("receipt_def", "")

            # Fallback on-the-fly generation if receipts were not pre-stored
            if not receipt_att or not receipt_def:
                att_k = losses_meta.get("att_key") or war_data.get("att_key")
                def_k = losses_meta.get("def_key") or war_data.get("def_key")
                losses_dict = losses_meta.get("losses", {})
                op_t = losses_meta.get("op_type") or war_data.get("operation_type", "air_missile")

                if att_k and losses_dict:
                    receipt_att = war_analyzer.build_detailed_loss_receipt(
                        att_k, losses_dict.get("att_losses", []),
                        losses_dict.get("att_military_loss", 0), losses_dict.get("att_civilian_loss", 0),
                        "عملیات تهاجمی اخیر", is_attacker=True, op_type=op_t
                    )
                if def_k and losses_dict:
                    receipt_def = war_analyzer.build_detailed_loss_receipt(
                        def_k, losses_dict.get("def_losses", []),
                        losses_dict.get("def_military_loss", 0), losses_dict.get("def_civilian_loss", 0),
                        "عملیات دفاعی اخیر", is_attacker=False, op_type=op_t
                    )

            if receipt_att or receipt_def:
                display_text = f"{receipt_att}\n\n━━━━━━━━━━━━━━━━━━\n\n{receipt_def}".strip()
            else:
                display_text = "📋 اطلاعات فاکتورهای تلفات در دسترس نمی‌باشد."
        except Exception as e:
            display_text = f"📋 اطلاعات فاکتورهای تلفات در دسترس نمی‌باشد. ({e})"
    else:
        display_text = war_data["summary_text"]

    try:
        await query.edit_message_text(display_text, reply_markup=InlineKeyboardMarkup(nav_keyboard), parse_mode="Markdown")
    except Exception:
        try:
            await query.edit_message_text(display_text, reply_markup=InlineKeyboardMarkup(nav_keyboard))
        except Exception as ex:
            print(f"Failed to edit message in war_view_callback_handler: {ex}")

    try:
        await query.edit_message_text(display_text, reply_markup=InlineKeyboardMarkup(nav_keyboard), parse_mode="Markdown")
    except Exception:
        try:
            await query.edit_message_text(display_text, reply_markup=InlineKeyboardMarkup(nav_keyboard))
        except Exception:
            pass