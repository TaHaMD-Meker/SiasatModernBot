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
        [InlineKeyboardButton("💥 مدیریت تلفات تجهیزات", callback_data="ls:menu")],
        [InlineKeyboardButton("🔐 سیستم قفل‌ها و محدودیت‌ها", callback_data="admin:locks_menu")],
        [InlineKeyboardButton("📝 رول‌های دریافتی (تاییدنشده)", callback_data="admin:pending_roles")],
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
    role_lock = db.get_setting("role_submit_locked") == "1"

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
        [InlineKeyboardButton("🔓 باز کردن ارسال رول" if role_lock else "🔒 قفل کردن ارسال رول", callback_data="admin:toggle_lock:role_submit_locked")],
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
            InlineKeyboardButton("⚙️ اقتصاد و وضعیت داخلی", callback_data=f"admin:cstatmenu:{c['id']}"),
            InlineKeyboardButton("📜 تراکنش‌ها", callback_data=f"admin:c_tx_logs:{c['id']}"),
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
    """فهرست دسته‌بندی‌های دارایی‌های نظامی (دکمه‌های شیشه‌ای به تفکیک نیرو)."""
    c = db.get_country_by_id(country_id)
    if not c:
        return

    assets = db.get_country_assets(country_id)
    by_cat = {}
    for a in assets:
        by_cat.setdefault(a['category'], []).append(a)

    text = f"🎖️ *مدیریت دارایی‌های نظامی {c['flag']} {c['name']}*\n\nیکی از نیروها/دسته‌ها را انتخاب کنید:"

    keyboard = []
    row = []
    for cat, (label, unit) in config.ASSET_CATEGORIES.items():
        items = by_cat.get(cat)
        if not items:
            continue
        row.append(InlineKeyboardButton(f"{label} ({len(items)})", callback_data=f"admin:asset_cat:{country_id}:{cat}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    for cat in [c_ for c_ in by_cat if c_ not in config.ASSET_CATEGORIES]:
        keyboard.append([InlineKeyboardButton(f"📦 {cat} ({len(by_cat[cat])})", callback_data=f"admin:asset_cat:{country_id}:{cat}")])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:c:{c['id']}")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def menu_assets_category(query, country_id: int, category: str):
    """فهرست تجهیزات یک دسته برای ویرایش."""
    c = db.get_country_by_id(country_id)
    if not c:
        return

    cat_label, unit = config.ASSET_CATEGORIES.get(category, (category, "عدد"))
    assets = [a for a in db.get_country_assets(country_id) if a['category'] == category]
    total = sum((a.get("amount", 0) or 0) for a in assets)

    text = (
        f"🎖️ *{cat_label} — {c['flag']} {c['name']}*\n"
        f"قلم‌ها: {len(assets)} | مجموع: {format_number(total)} {unit}\n\n"
        "تجهیز مورد نظر را برای تغییر تعداد انتخاب کنید:"
    )

    keyboard = []
    for a in assets:
        prod_mark = "✅" if a.get("producible", 1) == 1 else "🌐"
        keyboard.append([InlineKeyboardButton(f"{a['equipment_name']} ({format_number(a['amount'])}) {prod_mark}", callback_data=f"admin:asset_item:{country_id}:{a['equipment_key']}")])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت به دسته‌ها", callback_data=f"admin:menu_assets:{country_id}")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")




# ==================== ویرایش اقتصاد و وضعیت داخلی کشور ====================

COUNTRY_STAT_FIELDS = {
    "daily_income":     ("📈 درآمد روزانه", "دلار", 1_000_000, "money"),
    "tax_income":       ("💰 درآمد مالیاتی", "دلار", 500_000, "money"),
    "approval_rating":  ("😀 رضایت عمومی", "٪", 5, "pct"),
    "combat_readiness": ("⚔️ آمادگی رزمی", "٪", 5, "pct"),
    "population":       ("👥 جمعیت", "نفر", 1_000_000, "num"),
    "active_personnel": ("🪖 نیروی فعال", "نفر", 10_000, "num"),
    "reserve_personnel":("🎖 نیروی ذخیره", "نفر", 10_000, "num"),
    "tech_level":       ("🔬 سطح فناوری", "سطح", 1, "num"),
    "electricity":      ("⚡ برق", "واحد", 10, "num"),
    "grain":            ("🌾 غلات", "تن", 10_000, "num"),
    "gold_daily":       ("🪙 تولید روزانه طلا", "سکه", 10, "num"),
    "oil_production":   ("🛢️ تولید روزانه نفت", "بشکه", 100_000, "num"),
}

_CSTAT_LIMITS = {"approval_rating": (0, 100), "combat_readiness": (0, 100), "tech_level": (1, 10)}


def _fmt_stat(value, kind):
    if kind == "money":
        return format_money(value)
    return f"{format_number(value)}"


async def menu_country_stats(query, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return
    rows = []
    row = []
    for field, (label, unit, step, kind) in COUNTRY_STAT_FIELDS.items():
        val = _fmt_stat(c.get(field, 0) or 0, kind)
        row.append(InlineKeyboardButton(f"{label}: {val}", callback_data=f"admin:cstat:{country_id}:{field}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("🔙 بازگشت به داشبورد کشور", callback_data=f"admin:c:{country_id}")])
    text = (
        f"⚙️ *اقتصاد و وضعیت داخلی — {c['flag']} {c['name']}*\n\n"
        "مورد مورد نظر را برای ویرایش انتخاب کنید:"
    )
    from telegram import InlineKeyboardMarkup as _IKM
    await query.edit_message_text(text, reply_markup=_IKM(rows), parse_mode="Markdown")


async def menu_cstat_adjust(query, country_id: int, field: str):
    c = db.get_country_by_id(country_id)
    info = COUNTRY_STAT_FIELDS.get(field)
    if not c or not info:
        return
    label, unit, step, kind = info
    current = c.get(field, 0) or 0
    note = ""
    if field in ("daily_income", "tax_income"):
        note = "\n\n⚠️ _این دو مورد با هر ری‌استارت بر اساس کانفیگ و ساختمان‌ها بازسازی می‌شوند._"
    from telegram import InlineKeyboardMarkup as _IKM
    rows = [
        [InlineKeyboardButton(f"➖ {step*10:,}", callback_data=f"admin:cstatadj:{country_id}:{field}:-10"),
         InlineKeyboardButton(f"➖ {step*5:,}", callback_data=f"admin:cstatadj:{country_id}:{field}:-5"),
         InlineKeyboardButton(f"➖ {step:,}", callback_data=f"admin:cstatadj:{country_id}:{field}:-1")],
        [InlineKeyboardButton(f"➕ {step:,}", callback_data=f"admin:cstatadj:{country_id}:{field}:1"),
         InlineKeyboardButton(f"➕ {step*5:,}", callback_data=f"admin:cstatadj:{country_id}:{field}:5"),
         InlineKeyboardButton(f"➕ {step*10:,}", callback_data=f"admin:cstatadj:{country_id}:{field}:10")],
        [InlineKeyboardButton("✏️ وارد کردن مقدار دقیق", callback_data=f"admin:cstatset:{country_id}:{field}")],
        [InlineKeyboardButton("🔙 بازگشت به وضعیت داخلی", callback_data=f"admin:cstatmenu:{country_id}")],
    ]
    await query.edit_message_text(
        f"{label} — {c['flag']} {c['name']}\n\nمقدار فعلی: *{_fmt_stat(current, kind)}*{note}",
        reply_markup=_IKM(rows), parse_mode="Markdown")


def apply_cstat_delta(country_id: int, field: str, mult: int):
    info = COUNTRY_STAT_FIELDS.get(field)
    if not info:
        return None, "فیلد نامعتبر"
    _, unit, step, kind = info
    c = db.get_country_by_id(country_id)
    if not c:
        return None, "کشور یافت نشد"
    new_val = (c.get(field, 0) or 0) + mult * step
    lo, hi = _CSTAT_LIMITS.get(field, (0, 10**15))
    new_val = max(lo, min(hi, new_val))
    db.update_country_field(country_id, field, new_val)
    return new_val, None


def apply_cstat_value(country_id: int, field: str, value: int):
    info = COUNTRY_STAT_FIELDS.get(field)
    if not info:
        return None, "فیلد نامعتبر"
    lo, hi = _CSTAT_LIMITS.get(field, (0, 10**15))
    value = max(lo, min(hi, value))
    db.update_country_field(country_id, field, value)
    return value, None


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
            InlineKeyboardButton("🔙 دسته‌ها", callback_data=f"admin:menu_assets:{country_id}"),
            InlineKeyboardButton("📂 همین دسته", callback_data=f"admin:asset_cat:{country_id}:{asset['category']}"),
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
            f"👑 *کشور {c_name}:* طرح عملیاتی شما توسط ستاد مدیریت تایید و در دستور کار قرار گرفت."
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

    elif data.startswith("admin:cstatadj:"):
        parts = data.split(":")
        if len(parts) == 5:
            cid_, field_, mult_ = int(parts[2]), parts[3], int(parts[4])
            new_val, err = apply_cstat_delta(cid_, field_, mult_)
            if err:
                await query.answer(f"❌ {err}", show_alert=True)
                return
            info = COUNTRY_STAT_FIELDS.get(field_)
            await query.answer(f"✅ {info[0]} → {_fmt_stat(new_val, info[3])}", show_alert=True)
            await menu_cstat_adjust(query, cid_, field_)
        return

    elif data.startswith("admin:cstatset:"):
        parts = data.split(":")
        if len(parts) == 4:
            context.user_data["admin_awaiting_input"] = {"type": "cstat_set", "country_id": int(parts[2]), "field": parts[3]}
            c = db.get_country_by_id(int(parts[2]))
            info = COUNTRY_STAT_FIELDS.get(parts[3])
            await query.edit_message_text(
                f"✏️ *مقدار جدید برای {info[0]}* — {c['flag']} {c['name']}\n\nمقدار فعلی: {_fmt_stat(c.get(parts[3], 0) or 0, info[3])}\n\nلطفاً عدد را ارسال کنید (اعداد فارسی هم قابل قبول است):",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data=f"admin:cstatmenu:{parts[2]}")]]),
                parse_mode="Markdown",
            )
        return

    elif data.startswith("admin:cstatmenu:"):
        await menu_country_stats(query, int(data.split(":")[2]))
        return

    elif data.startswith("admin:cstat:"):
        parts = data.split(":")
        if len(parts) == 4:
            await menu_cstat_adjust(query, int(parts[2]), parts[3])
        return

    elif data.startswith("admin:asset_cat:"):
        parts = data.split(":")
        if len(parts) >= 4:
            await menu_assets_category(query, int(parts[2]), ":".join(parts[3:]))
        return

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

    if input_type == "cstat_set":
        import re as _re
        raw = _re.sub(r"[^0-9]", "", str(text).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")))
        if not raw:
            await update.message.reply_text("❌ لطفاً فقط یک عدد صحیح بفرست.", parse_mode="Markdown")
            return
        cid_ = input_state["country_id"]; field_ = input_state["field"]
        new_val, err = apply_cstat_value(cid_, field_, int(raw))
        c = db.get_country_by_id(cid_)
        info = COUNTRY_STAT_FIELDS.get(field_)
        context.user_data["admin_awaiting_input"] = None
        if err:
            await update.message.reply_text(f"❌ {err}", parse_mode="Markdown")
            return
        await update.message.reply_text(
            f"✅ *{info[0]}* کشور {c['flag']} {c['name']} به *{_fmt_stat(new_val, info[3])}* تغییر یافت.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ بازگشت به وضعیت داخلی", callback_data=f"admin:cstatmenu:{cid_}")],
                [InlineKeyboardButton("🔙 داشبورد کشور", callback_data=f"admin:c:{cid_}")],
            ]),
            parse_mode="Markdown",
        )
        return

    if input_type and str(input_type).startswith("ls_"):
        from handlers.losses import handle_losses_input
        await handle_losses_input(update, context, user_id, input_state)
        return

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
