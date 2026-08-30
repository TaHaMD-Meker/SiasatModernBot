# -**- coding: utf-8 -**-
"""
ماژول کامل سیستم دیپلماسی، پیام‌رسانی دیپلماتیک، قراردادهای تجاری، اتحاد، تحریم و کمک‌های خارجی
(Diplomacy, Trade Contracts, Alliances, Sanctions & Foreign Aid System)
"""

import datetime
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

import database as db
import config
import news_engine
from utils import format_money, format_number, format_oil, get_main_keyboard


async def check_and_alert_anti_cheat(context, proposer_c, recipient_c, amount_val, tx_type_label):
    """ارسال هوشمند هشدار احتمال تقلب/مولتی‌اکانت به ادمین."""
    for admin_id in config.ADMIN_IDS:
        try:
            p_user = f"@{proposer_c.get('username')}" if proposer_c.get('username') else "بدون_آیدی"
            r_user = f"@{recipient_c.get('username')}" if recipient_c.get('username') else "بدون_آیدی"

            alert_text = (
                "🚨 **هشدار هوشمند آنتی‌چیت (احتمال مولتی‌اکانت / تقلب)**\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"• **فرستنده:** {proposer_c['flag']} {proposer_c['name']} (کاربر: {p_user} | ID: `{proposer_c['player_id']}`)\n"
                f"• **گیرنده:** {recipient_c['flag']} {recipient_c['name']} (کاربر: {r_user} | ID: `{recipient_c['player_id']}`)\n\n"
                f"• **نوع تراکنش:** {tx_type_label}\n"
                f"• **حجم/ارزش:** {amount_val}\n\n"
                "⚠️ **توضیحات:** حجم جابه‌جایی منابع/تسلیحات از آستانه هشدار گذشته است."
            )
            kb = [[InlineKeyboardButton(f"🔍 بررسی کشور فرستنده ({proposer_c['name']})", callback_data=f"admin:c:{proposer_c['id']}")]]
            await context.bot.send_message(chat_id=admin_id, text=alert_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except Exception:
            pass


async def require_country(update: Update):
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        pending = db.get_pending_request_by_player(user_id)
        if pending:
            p_key = pending.get("country_key", "")
            p_info = config.COUNTRIES.get(p_key, {})
            flag = p_info.get("flag", "🏳️")
            name = p_info.get("name", p_key)
            msg = (
                f"⏳ **درخواست رهبری کشور {flag} {name} در صف بررسی ادمین است.**\n\n"
                "به محض تأیید ادمین اصلی بازی، سامانه دیپلماسی و روابط بین‌الملل فعال خواهد شد."
            )
            alert_text = f"درخواست کشور {name} در انتظار تأیید ادمین است!"
        else:
            msg = "❌ **شما هنوز کشوری در بازی ندارید!**\n\nجهت شروع بازی و انتخاب کشور، دستور /start را ارسال کنید."
            alert_text = "هنوز کشوری نساختی! برای شروع /start بزن."

        if update.message:
            await update.message.reply_text(msg, parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.answer(alert_text, show_alert=True)
        return None
    return country


# ==================== منوی اصلی دیپلماسی ====================

async def diplomacy_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = await require_country(update)
    if not c:
        return

    text = (
        f"🌐 **اتاق دیپلماسی و روابط بین‌الملل {c['flag']} {c['name']}**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "لطفاً یک بخش را انتخاب کنید:\n\n"
        "• **یادداشت دیپلماتیک:** ارسال پیام رسمی به سایر کشورها\n"
        "• **قرارداد تجاری:** مبادله نفت، غلات، طلا و پول با معاهده رسمی\n"
        "• **انتقال/فروش تسلیحات:** انتقال تجهیزات نظامی از دارایی‌های کشوری\n"
        "• **محاصره دریایی:** مسدودسازی بنادر و خطوط مواصلاتی کشور هدف\n"
        "• **کمک خارجی:** ارسال کمک‌های انسان‌دوستانه بدون مابه‌ازا\n"
        "• **روابط و تحریم‌ها:** مدیریت اتحادها و تحریم‌های یک‌طرفه"
    )

    keyboard = [
        [InlineKeyboardButton("📈 بازار بورس بین‌المللی کالاها (طلا، نفت، غلات)", callback_data="market:menu")],
        [InlineKeyboardButton("📋 معاهدات و قراردادهای من (پیگیری و لغو)", callback_data="dip:my_contracts")],
        [InlineKeyboardButton("📜 پیشنهاد قرارداد تجاری", callback_data="dip:trade_start")],
        [InlineKeyboardButton("🎖️ انتقال/فروش تسلیحات نظامی", callback_data="dip:mil_start")],
        [InlineKeyboardButton("✉️ ارسال یادداشت دیپلماتیک", callback_data="dip:msg_start")],
        [InlineKeyboardButton("⚓ محاصره دریایی بین‌المللی", callback_data="dip:blockade_start")],
        [InlineKeyboardButton("🌊 مدیریت و انسداد تنگه‌ها", callback_data="dip:strait_menu")],
        [InlineKeyboardButton("🕊️ کمک خارجی و انسان‌دوستانه", callback_data="dip:aid_start")],
        [InlineKeyboardButton("🤝 اتحادها و تحریم‌ها", callback_data="dip:rel_start")],
    ]

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


def _clean_persian_str(s: str) -> str:
    """استانداردسازی متن فارسی/انگلیسی جهت جستجوی دقیق."""
    if not s:
        return ""
    t = str(s).strip().lower()
    t = t.replace("_", " ")
    trans = {
        "ي": "ی", "ى": "ی", "ك": "ک", "ؤ": "و",
        "إ": "ا", "أ": "ا", "آ": "ا", "ة": "ه",
        "ئ": "ی", "ـ": ""
    }
    for k, v in trans.items():
        t = t.replace(k, v)
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def build_dip_continent_selector(action_type: str, header_title: str):
    continents = getattr(config, "CONTINENTS", {})
    text = (
        f"{header_title}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "جهت انتخاب سریع‌تر، **قاره کشور مقصد را انتخاب فرمایید** یا از **جستجوی متنی** استفاده کنید:"
    )
    buttons = []
    row = []
    for c_key, c_info in continents.items():
        row.append(InlineKeyboardButton(c_info["name"], callback_data=f"dip:pickcont:{c_key}:{action_type}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("🔎 جستجوی نام کشور مقصد (تایپی)", callback_data=f"dip:search_start:{action_type}")])
    buttons.append([InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")])
    return text, InlineKeyboardMarkup(buttons)


def build_dip_continent_countries_keyboard(cont_key: str, action_type: str, current_cid: int):
    continents = getattr(config, "CONTINENTS", {})
    cont_info = continents.get(cont_key, {})
    keys = cont_info.get("keys", [])

    all_countries = db.get_all_countries()
    c_map = {c["country_key"]: c for c in all_countries if c.get("country_key")}

    buttons = []
    row = []
    cb_prefix_map = {
        "msg": "dip:msg_target:",
        "trade": "dip:trade_target:",
        "mil": "dip:mil_target:",
        "aid": "dip:aid_target:",
        "blockade": "dip:blockade_target:"
    }
    prefix = cb_prefix_map.get(action_type, "dip:target:")

    for k in keys:
        if k in c_map:
            c = c_map[k]
            if c["id"] == current_cid:
                continue
            is_sanc = db.are_sanctioned(current_cid, c["id"])
            if is_sanc and action_type in ("trade", "mil", "aid"):
                btn_label = f"🚫 {c['name']} (تحریم)"
            else:
                btn_label = f"{c['flag']} {c['name']}"

            row.append(InlineKeyboardButton(btn_label, callback_data=f"{prefix}{c['id']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton("🔎 جستجو", callback_data=f"dip:search_start:{action_type}"),
        InlineKeyboardButton("🔙 لیست قاره‌ها", callback_data=f"dip:back_continents:{action_type}")
    ])
    return f"{cont_info.get('name', 'قاره')}\n\nکشور مورد نظر را انتخاب فرمایید:", InlineKeyboardMarkup(buttons)


# ==================== 1. یادداشت دیپلماتیک ====================

async def dip_message_start(query, context, country):
    if db.get_setting("diplomatic_notes_locked") == "1":
        await query.edit_message_text("🔒 **ارسال پیام‌های دیپلماتیک موقتاً قفل است.**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:menu")]]), parse_mode="Markdown")
        return

    text, kb = build_dip_continent_selector("msg", "✉️ **ارسال یادداشت دیپلماتیک رسمی**")
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")


# ==================== 2. قراردادهای تجاری ====================

async def dip_trade_start(query, context, country):
    if db.get_setting("trade_contracts_locked") == "1":
        await query.edit_message_text("🔒 **انعقاد قراردادهای تجاری موقتاً قفل است.**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:menu")]]), parse_mode="Markdown")
        return

    text, kb = build_dip_continent_selector("trade", "📜 **پیشنهاد قرارداد تجاری رسمی**")
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")


# ==================== 2.5. انتقال و فروش تسلیحات نظامی ====================

async def dip_military_start(query, context, country):
    text, kb = build_dip_continent_selector("mil", "🎖️ **انتقال / فروش تسلیحات نظامی**")
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")


async def dip_aid_start(query, context, country):
    text, kb = build_dip_continent_selector("aid", "🕊️ **ارسال کمک‌های خارجی و انسان‌دوستانه**")
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")


# ==================== 2.7. محاصره دریایی بین‌المللی ====================

async def dip_blockade_start(query, context, country):
    if db.get_setting("naval_blockade_locked") == "1":
        await query.edit_message_text("🔒 **اجرای محاصره دریایی موقتاً قفل است.**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:menu")]]), parse_mode="Markdown")
        return

    # گارد واقع‌گرایی: کشورهای بدون دسترسی به آب‌های آزاد نمی‌توانند محاصره دریایی اجرا کنند
    if not db.has_open_sea_access(country.get("country_key")):
        await query.edit_message_text(
            "⚓ **عدم امکان اجرای محاصره دریایی**\n━━━━━━━━━━━━━━━━━━\n\n"
            "کشور شما به آب‌های آزاد و اقیانوس دسترسی ندارد (محصور در خشکی یا دریای بسته). "
            "بنابراین امکان اعزام ناوگان برای محاصره دریایی کشورهای دیگر وجود ندارد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
            parse_mode="Markdown"
        )
        return

    active_blks = db.get_active_blockades_for_country(country["id"])
    im_blockaded = db.is_country_blockaded(country["id"])

    keyboard = []

    if im_blockaded:
        keyboard.append([InlineKeyboardButton("💥 شکستن محاصره دریایی (نبرد موشکی/دریایی)", callback_data="dip:break_blk")])

    my_blockades = [b for b in active_blks if b["blockader_id"] == country["id"]]
    for b in my_blockades:
        t_c = db.get_country_by_id(b["target_id"])
        if t_c:
            keyboard.append([InlineKeyboardButton(f"🔓 لغو محاصره دریایی کشور {t_c['name']}", callback_data=f"dip:lift_blk:{t_c['id']}")])
            keyboard.append([InlineKeyboardButton(f"🤝 دعوت متحدین به ائتلاف محاصره {t_c['name']}", callback_data=f"dip:blk_invite:{t_c['id']}")])

    # نمایش محاصره‌های فعال متحدین برای امکان پیوستن
    allied_countries = db.get_allied_countries_for_blockade(country["id"])
    allied_ids = [a["id"] for a in allied_countries]
    for b in db.get_all_active_blockades():
        if b["blockader_id"] in allied_ids and b["target_id"] != country["id"] and b["blockader_id"] != country["id"]:
            lead_c = db.get_country_by_id(b["blockader_id"])
            target_c = db.get_country_by_id(b["target_id"])
            if lead_c and target_c:
                try:
                    coalition = json.loads(b.get("coalition_json") or "[]")
                except Exception:
                    coalition = []
                is_in = any(c.get("country_id") == country["id"] for c in coalition)
                if is_in:
                    keyboard.append([InlineKeyboardButton(f"🚪 خروج از ائتلاف محاصره {target_c['name']} (به رهبری {lead_c['name']})", callback_data=f"dip:blk_leave:{lead_c['id']}:{target_c['id']}")])
                else:
                    keyboard.append([InlineKeyboardButton(f"⚓ پیوستن به محاصره {target_c['name']} (به رهبری {lead_c['name']})", callback_data=f"dip:blk_join:{lead_c['id']}:{target_c['id']}")])

    qualified, units, val = db.check_strait_navy_qualification(country["id"])
    if not qualified and not im_blockaded and not my_blockades:
        await query.edit_message_text(
            "⚓ **عدم توانایی عملیاتی ناوگان:**\n━━━━━━━━━━━━━━━━━━\n\n"
            "برای اعزام ناودسته‌ها و اجرای محاصره دریایی، کشور شما باید حداقل دارای "
            "**۵ شناور رزمی فعال** با ارزش مجموع حداقل **۱۰,۰۰۰,۰۰۰ دلار** در نیروی دریایی باشد.\n\n"
            f"📊 **ناوگان فعلی شما:** {units} فروند شناور (ارزش کل: {format_money(val)})\n\n"
            "💡 جهت ارتقا و تجهیز ناوگان، از بخش **فروشگاه → نیروی دریایی** اقدام به ساخت شناورهای رزمی فرمایید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:menu")]]),
            parse_mode="Markdown"
        )
        return

    countries = db.get_all_countries()
    other_countries = [
        c for c in countries
        if c["id"] != country["id"] and db.has_open_sea_access(c.get("country_key"))
    ]

    text = (
        f"⚓ **عملیات محاصره دریایی بین‌المللی — ناوگان {country['flag']} {country['name']}**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "⚠️ **شرایط و هزینه‌های استقرار محاصره دریایی:**\n"
        f"• **هزینه اولیه اعزام ناوگان:** {format_money(10_000_000)}\n"
        f"• **سوخت اولیه ناوگان:** {format_oil(500_000)}\n"
        "• **سقف مجاز روزانه:** ۱ عملیات محاصره جدید در هر روز (۲۴ ساعت)\n"
        "• **برتری نظامی:** قدرت رزمی ناوگان شما باید حداقل ۱۲۰٪ ناوگان هدف باشد.\n\n"
        "لطفاً کشور هدف جهت مسدودسازی بنادر و خطوط دریایی را انتخاب کنید:"
    )

    row = []
    for c in other_countries:
        is_blk = db.is_country_blockaded(c["id"])
        lbl = f"⚓ {c['name']} (تحت محاصره)" if is_blk else f"{c['flag']} {c['name']}"
        btn = InlineKeyboardButton(lbl, callback_data=f"dip:blk_target:{c['id']}")
        row.append(btn)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== 4. مدیریت روابط و تحریم‌ها ====================

async def dip_relations_menu(query, context, country):
    # نمایش انتخاب قاره برای مدیریت اتحاد و تحریم (جلوگیری از لیست ۱۰۰+ کشوری یکجا)
    text, kb = build_dip_continent_selector("rel", f"🤝 **مدیریت روابط دیپلماتیک و تحریم‌ها — {country['flag']} {country['name']}**")
    await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")


def build_dip_rel_continent_keyboard(cont_key: str, current_cid: int):
    continents = getattr(config, "CONTINENTS", {})
    cont_info = continents.get(cont_key, {})
    keys = cont_info.get("keys", [])

    all_countries = db.get_all_countries()
    c_map = {c["country_key"]: c for c in all_countries if c.get("country_key")}

    lines = [f"{cont_info.get('name', 'قاره')} — **وضعیت روابط**\n━━━━━━━━━━━━━━━━━━\n"]
    keyboard = []

    for k in keys:
        if k not in c_map:
            continue
        c = c_map[k]
        if c["id"] == current_cid:
            continue

        rel = db.get_diplomatic_relation(current_cid, c["id"])
        st = rel.get("status", "normal")
        s_by = rel.get("sanctioned_by", 0)

        if st == "allied":
            status_emoji = "🟢"
            status_text = "متحد"
            act_btn = InlineKeyboardButton(f"💔 لغو اتحاد {c['name']}", callback_data=f"dip:rel_act:break:{c['id']}")
        elif st == "sanctioned":
            status_emoji = "🔴"
            if s_by == current_cid:
                status_text = "تحریم توسط شما"
                act_btn = InlineKeyboardButton(f"🔓 لغو تحریم {c['name']}", callback_data=f"dip:rel_act:unsanction:{c['id']}")
            else:
                status_text = "شما را تحریم کرده"
                act_btn = InlineKeyboardButton(f"🚫 تحریم متقابل {c['name']}", callback_data=f"dip:rel_act:sanction:{c['id']}")
        else:
            status_emoji = "⚪"
            status_text = "عادی"
            act_btn = InlineKeyboardButton(f"🤝 اتحاد با {c['name']}", callback_data=f"dip:rel_act:propose_alliance:{c['id']}")

        lines.append(f"{status_emoji} {c['flag']} {c['name']} — {status_text}")

        # دکمه‌های اقدام
        btn_row = [act_btn]
        if st != "sanctioned" and st != "allied":
            btn_row.append(InlineKeyboardButton(f"🚫 تحریم {c['name']}", callback_data=f"dip:rel_act:sanction:{c['id']}"))
        keyboard.append([InlineKeyboardButton(f"{c['flag']} {c['name']} ({status_text})", callback_data="ignore")])
        keyboard.append(btn_row)

    if len(keyboard) == 0:
        lines.append("در این قاره کشور بازیکن‌دار دیگری نیست.")

    keyboard.append([
        InlineKeyboardButton("🔎 جستجو", callback_data="dip:search_start:rel"),
        InlineKeyboardButton("🔙 لیست قاره‌ها", callback_data="dip:back_continents:rel")
    ])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")])

    return "\n".join(lines), InlineKeyboardMarkup(keyboard)


# ==================== Callback Handler دیپلماسی ====================

async def diplomacy_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    country = db.get_country_by_player(user_id)

    if not country:
        await query.answer("هنوز کشوری نساختی!", show_alert=True)
        return

    await query.answer()

    if data == "dip:menu":
        await diplomacy_menu(update, context)

    elif data.startswith("dip:pickcont:"):
        _, _, cont_key, action_type = data.split(":")
        if action_type == "rel":
            text, kb = build_dip_rel_continent_keyboard(cont_key, country["id"])
        else:
            text, kb = build_dip_continent_countries_keyboard(cont_key, action_type, country["id"])
        await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

    elif data.startswith("dip:back_continents:"):
        action_type = data.split(":")[2]
        action_titles = {
            "msg": "✉️ **ارسال یادداشت دیپلماتیک رسمی**",
            "trade": "📜 **پیشنهاد قرارداد تجاری رسمی**",
            "mil": "🎖️ **انتقال / فروش تسلیحات نظامی**",
            "aid": "🕊️ **ارسال کمک‌های خارجی و انسان‌دوستانه**",
            "blockade": "⚓ **عملیات محاصره دریایی بین‌المللی**",
            "rel": "🤝 **مدیریت روابط دیپلماتیک و تحریم‌ها**"
        }
        title = action_titles.get(action_type, "دیپلماسی بین‌المللی")
        text, kb = build_dip_continent_selector(action_type, title)
        await query.edit_message_text(text, reply_markup=kb, parse_mode="Markdown")

    elif data.startswith("dip:search_start:"):
        action_type = data.split(":")[2]
        context.user_data["diplomacy_input"] = {"type": "dip_search_country", "action_type": action_type}
        text = (
            "🔎 **جستجوی کشور مقصد**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً **نام کشور مورد نظر** را تایپ و ارسال فرمایید:\n"
            "*(مثال: آلمان، روسیه، چین، قطر، عربستان)*"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به لیست قاره‌ها", callback_data=f"dip:back_continents:{action_type}")]]), parse_mode="Markdown")

    elif data == "dip:my_contracts":
        sent = db.get_country_pending_sent_contracts(country["id"])
        recv = db.get_country_pending_received_contracts(country["id"])
        
        type_map = {"treasury": "دلار", "gold": "شمش طلا", "oil": "بشکه نفت", "grain": "تن غلات", "iron_ore": "تن آهن و فولاد", "microchips": "عدد میکروچیپ", "uranium_ore": "تن کیک زرد", "nuclear_fuel": "کیلوگرم سوخت هسته‌ای", "military_asset": "سلاح نظامی"}
        
        lines = [
            f"📋 **قراردادها و معاهدات دیپلماتیک — {country['flag']} {country['name']}**\n",
            "━━━━━━━━━━━━━━━━━━\n"
        ]
        
        keyboard = []
        
        # 1. پیشنهادات دریافتی معلق
        if recv:
            lines.append("📥 **پیشنهادات دریافتی (منتظر امضا و تصمیم شما):**\n")
            for r in recv:
                off_str = f"{r['offered_amount']:,} {type_map.get(r['offered_type'], r['offered_type'])}"
                req_str = f"{r['requested_amount']:,} {type_map.get(r['requested_type'], r['requested_type'])}"
                lines.append(f"• **از طرف:** {r['sender_flag']} {r['sender_name']}")
                lines.append(f"  تحویلی به شما: `{off_str}` | درخواستی از شما: `{req_str}`\n")
                keyboard.append([
                    InlineKeyboardButton(f"✅ قبول از {r['sender_name']}", callback_data=f"dip:trade_accept:{r['id']}"),
                    InlineKeyboardButton(f"❌ رد", callback_data=f"dip:trade_reject:{r['id']}")
                ])
            lines.append("━━━━━━━━━━━━━━━━━━\n")
            
        # 2. پیشنهادات ارسالی معلق
        if sent:
            lines.append("📤 **پیشنهادات ارسالی شما (در انتظار پاسخ طرف مقابل):**\n")
            for s in sent:
                off_str = f"{s['offered_amount']:,} {type_map.get(s['offered_type'], s['offered_type'])}"
                req_str = f"{s['requested_amount']:,} {type_map.get(s['requested_type'], s['requested_type'])}"
                lines.append(f"• **به مقصد:** {s['target_flag']} {s['target_name']}")
                lines.append(f"  پیشنهادی شما: `{off_str}` | درخواستی شما: `{req_str}`\n")
                keyboard.append([
                    InlineKeyboardButton(f"❌ لغو پیشنهاد به {s['target_name']}", callback_data=f"dip:cancel_contract:{s['id']}")
                ])
            lines.append("━━━━━━━━━━━━━━━━━━\n")
            
        if not sent and not recv:
            lines.append("✅ در حال حاضر هیچ معاهده یا قرارداد معلقی ندارید.\n")
            lines.append("💡 برای ثبت پیشنهاد جدید از دکمه‌های «پیشنهاد قرارداد تجاری» یا «انتقال تسلیحات» استفاده فرمایید.")
            
        keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی دیپلماسی", callback_data="dip:menu")])
        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("dip:cancel_contract:"):
        contract_id = int(data.split(":")[2])
        ok, msg = db.cancel_pending_contract_by_proposer(country["id"], contract_id)
        if ok:
            await query.answer("✅ پیشنهاد قرارداد لغو و ابطال شد!", show_alert=True)
            sent = db.get_country_pending_sent_contracts(country["id"])
            recv = db.get_country_pending_received_contracts(country["id"])
            type_map = {"treasury": "دلار", "gold": "شمش طلا", "oil": "بشکه نفت", "grain": "تن غلات", "iron_ore": "تن آهن و فولاد", "microchips": "عدد میکروچیپ", "uranium_ore": "تن کیک زرد", "nuclear_fuel": "کیلوگرم سوخت هسته‌ای", "military_asset": "سلاح نظامی"}
            lines = [f"📋 **قراردادها و معاهدات دیپلماتیک — {country['flag']} {country['name']}**\n", "━━━━━━━━━━━━━━━━━━\n"]
            keyboard = []
            if recv:
                lines.append("📥 **پیشنهادات دریافتی (منتظر امضا و تصمیم شما):**\n")
                for r in recv:
                    off_str = f"{r['offered_amount']:,} {type_map.get(r['offered_type'], r['offered_type'])}"
                    req_str = f"{r['requested_amount']:,} {type_map.get(r['requested_type'], r['requested_type'])}"
                    lines.append(f"• **از طرف:** {r['sender_flag']} {r['sender_name']}")
                    lines.append(f"  تحویلی به شما: `{off_str}` | درخواستی از شما: `{req_str}`\n")
                    keyboard.append([
                        InlineKeyboardButton(f"✅ قبول از {r['sender_name']}", callback_data=f"dip:trade_accept:{r['id']}"),
                        InlineKeyboardButton(f"❌ رد", callback_data=f"dip:trade_reject:{r['id']}")
                    ])
                lines.append("━━━━━━━━━━━━━━━━━━\n")
            if sent:
                lines.append("📤 **پیشنهادات ارسالی شما (در انتظار پاسخ طرف مقابل):**\n")
                for s in sent:
                    off_str = f"{s['offered_amount']:,} {type_map.get(s['offered_type'], s['offered_type'])}"
                    req_str = f"{s['requested_amount']:,} {type_map.get(s['requested_type'], s['requested_type'])}"
                    lines.append(f"• **به مقصد:** {s['target_flag']} {s['target_name']}")
                    lines.append(f"  پیشنهادی شما: `{off_str}` | درخواستی شما: `{req_str}`\n")
                    keyboard.append([
                        InlineKeyboardButton(f"❌ لغو پیشنهاد به {s['target_name']}", callback_data=f"dip:cancel_contract:{s['id']}")
                    ])
                lines.append("━━━━━━━━━━━━━━━━━━\n")
            if not sent and not recv:
                lines.append("✅ در حال حاضر هیچ معاهده یا قرارداد معلقی ندارید.\n")
            keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی دیپلماسی", callback_data="dip:menu")])
            await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await query.answer(f"❌ {msg}", show_alert=True)

    elif data == "dip:msg_start":
        await dip_message_start(query, context, country)

    elif data == "dip:mil_start":
        await dip_military_start(query, context, country)

    elif data == "dip:blockade_start":
        await dip_blockade_start(query, context, country)

    elif data == "dip:strait_menu":
        c_key = country.get("country_key")
        strait_info = db.get_strait_info_by_country_key(c_key)

        if not strait_info:
            text = (
                f"🌊 **مدیریت تنگه‌های استراتژیک بین‌المللی**\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"📍 کشور شما (**{country['flag']} {country['name']}**) موقعیت تسلط مستقیم بر تنگه‌های اصلی بین‌المللی در دیتابیس را ندارد.\n\n"
                "📌 **تنگه‌های استراتژیک بازی:**\n"
                "• **تنگه هرمز:** تحت تسلط 🇮🇷 ایران\n"
                "• **کانال سوئز:** تحت تسلط 🇪🇬 مصر\n"
                "• **تنگه باب‌المندب:** تحت تسلط 🇾🇪 یمن (کشور غیرقابل بازی فعلاً — قابل انسداد نیست)\n"
                "• **تنگه بسفر (مونترو):** تحت تسلط 🇹🇷 ترکیه\n"
                "• **تنگه مالاکا:** تحت تسلط 🇮🇩 اندونزی\n"
                "• **تنگه تایوان:** تحت تسلط 🇨🇳 چین و 🇹🇼 تایوان"
            )
            kb = [[InlineKeyboardButton("🔙 بازگشت به منوی دیپلماسی", callback_data="dip:menu")]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
            return

        st_data = db.get_strait_status(strait_info["strait_key"])
        st_status = st_data["status"]
        st_toll = st_data["toll"]

        status_map = {
            "open": "🟢 باز و ترانزیت آزاد",
            "blocked": "🔴 مسدودسازی کامل آبراه",
            "toll": f"🟡 فعال بودن عوارض ترانزیت ({format_money(st_toll)}/عبور)"
        }

        text = (
            f"🌊 **ستاد مدیریت و کنترل {strait_info['name']} — {country['flag']} {country['name']}**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• **توصیف ژئوپلیتیک:** {strait_info['desc']}\n"
            f"• **وضعیت فعلی آبراه:** {status_map.get(st_status, st_status)}\n\n"
            "لطفاً اقدام مد نظر جهت اعمال بر تنگه را انتخاب فرمایید:"
        )

        kb = [
            [InlineKeyboardButton("🔴 مسدودسازی کامل تنگه", callback_data="dip:strait_act:block")],
            [InlineKeyboardButton("🟡 دریافت عوارض ترانزیت (حق عبور)", callback_data="dip:strait_act:toll")],
            [InlineKeyboardButton("🟢 بازگشایی کامل و ترانزیت آزاد", callback_data="dip:strait_act:open")],
            [InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data.startswith("dip:strait_act:"):
        act = data.split(":")[2]
        c_key = country.get("country_key")
        strait_info = db.get_strait_info_by_country_key(c_key)

        if not strait_info:
            await query.edit_message_text("❌ شما تسلطی بر تنگه‌های استراتژیک ندارید.", parse_mode="Markdown")
            return

        s_key = strait_info["strait_key"]
        s_name = strait_info["name"]

        # گارد واقع‌گرایی: برای انسداد یا عوارض، داشتن نیروی دریایی فعال الزامی است
        if act in ("block", "toll"):
            qualified, units, val = db.check_strait_navy_qualification(country["id"])
            if not qualified:
                await query.edit_message_text(
                    "❌ **امکان اعمال اقتدار و کنترل نظامی بر تنگه وجود ندارد.**\n\n"
                    "برای مسدودسازی یا اخذ عوارض از این آبراه استراتژیک، کشور شما باید حداقل "
                    "**۵ شناور رزمی فعال** با ارزش مجموع حداقل **۱۰,۰۰۰,۰۰۰ دلار** در نیروی دریایی خود داشته باشد.\n\n"
                    f"📊 **ناوگان فعلی شما:** {units} فروند شناور (ارزش: {format_money(val)})\n\n"
                    "💡 جهت بازپس‌گیری کنترل آبراه، از بخش **فروشگاه → نیروی دریایی** اقدام به ساخت و تقویت ناوگان فرمایید.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                    parse_mode="Markdown"
                )
                return

        if act == "block":
            # گام تایید و اخطار هزینه عملیاتی قبل از انسداد تنگه
            treasury_val = country.get("treasury", 0) or 0
            oil_val = country.get("oil_reserves", 0) or 0
            block_prompt = (
                f"⚠️ **تأییدیه عملیات نظامی و مسدودسازی تنگه بین‌المللی**\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"🌊 **آبراه هدف:** {s_name}\n"
                f"👑 **کشور کنترل‌کننده:** {country['flag']} {country['name']}\n\n"
                "💸 **هزینه‌های نگهداری و گشت رزمی روزانه ناوگان:**\n"
                f"• 💵 **هزینه مالی:** **۲.۵ میلیون دلار / روز** (موجودی خزانه شما: {format_money(treasury_val)})\n"
                f"• 🛢️ **سوخت مصرفی:** **۱۰۰,۰۰۰ بشکه نفت / روز** (ذخایر نفت شما: {format_oil(oil_val)})\n\n"
                "⚠️ **نکات مهم ژئوپلیتیک:**\n"
                "۱. مسدودسازی آبراه کلیه خطوط ترانزیت دریایی مرتبط را مختل می‌کند.\n"
                "۲. در صورت اتمام سوخت یا کسری بودجه، تنگه **به‌صورت خودکار بازگشایی** خواهد شد.\n\n"
                f"❓ **آیا از اعزام ناوگان جنگی و مسدودسازی کامل {s_name} اطمینان دارید؟**"
            )
            confirm_kb = [
                [InlineKeyboardButton("🔴 بله، تنگه مسدود شود (اعزام ناوگان)", callback_data="dip:strait_block_confirm")],
                [InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data="dip:strait_menu")],
            ]
            await query.edit_message_text(block_prompt, reply_markup=InlineKeyboardMarkup(confirm_kb), parse_mode="Markdown")
            return
        elif act == "toll":
            toll_text = (
                f"🟡 **تعیین عوارض ترانزیت (حق عبور) — {s_name}**\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "لطفاً مبلغ عوارض دریافتی از هر ترانزیت دریایی عبوری از این آبراه را تعیین فرمایید:\n\n"
                f"📌 **حداکثر سقف مجاز:** {format_money(1_000_000)} (۱ میلیون دلار)\n"
                f"📌 **حداقل کف مجاز:** {format_money(50_000)} (۵۰ هزار دلار)\n\n"
                "می‌توانید یکی از مبالغ آماده زیر را انتخاب کرده یا مبلغ دلخواه خود را تایپ نمایید:"
            )
            toll_kb = [
                [
                    InlineKeyboardButton("💰 ۲۵۰,۰۰۰ $", callback_data="dip:strait_toll_val:250000"),
                    InlineKeyboardButton("💰 ۵۰۰,۰۰۰ $", callback_data="dip:strait_toll_val:500000"),
                ],
                [
                    InlineKeyboardButton("💰 ۷۵۰,۰۰۰ $", callback_data="dip:strait_toll_val:750000"),
                    InlineKeyboardButton("💰 ۱,۰۰۰,۰۰۰ $ (سقف)", callback_data="dip:strait_toll_val:1000000"),
                ],
                [
                    InlineKeyboardButton("✍️ وارد کردن مبلغ دلخواه (تا ۱M $)", callback_data="dip:strait_toll_custom"),
                ],
                [InlineKeyboardButton("🔙 بازگشت به منوی تنگه", callback_data="dip:strait_menu")],
            ]
            await query.edit_message_text(toll_text, reply_markup=InlineKeyboardMarkup(toll_kb), parse_mode="Markdown")
        elif act == "open":
            db.set_strait_status(s_key, "open")
            await news_engine.trigger_strait_news(context.bot, country, s_name, "open")
            await query.edit_message_text(
                f"🟢 **{s_name} بازگشایی شد و ترانزیت آزاد برقرار گردید.**\n\n📢 خبر رسمی در کانال منتشر گردید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )

    elif data == "dip:strait_block_confirm":
        c_key = country.get("country_key")
        strait_info = db.get_strait_info_by_country_key(c_key)
        if not strait_info:
            await query.edit_message_text("❌ شما تسلطی بر تنگه‌های استراتژیک ندارید.", parse_mode="Markdown")
            return

        s_key = strait_info["strait_key"]
        s_name = strait_info["name"]

        qualified, units, val = db.check_strait_navy_qualification(country["id"])
        if not qualified:
            await query.edit_message_text("❌ حداقل توان رزمی دریایی جهت انسداد تنگه احراز نشد.", parse_mode="Markdown")
            return

        treasury_val = country.get("treasury", 0) or 0
        oil_val = country.get("oil_reserves", 0) or 0
        if treasury_val < 2_500_000 or oil_val < 100_000:
            await query.edit_message_text(
                f"❌ **کسری منابع جهت آغاز عملیات انسداد:**\n\n"
                f"برای آغاز انسداد و اعزام ناوگان، حداقل **۲.۵ میلیون دلار** در خزانه و **۱۰۰,۰۰۰ بشکه نفت** در ذخایر کشور الزامی است.\n\n"
                f"• خزانه شما: {format_money(treasury_val)}\n"
                f"• ذخایر نفت شما: {format_oil(oil_val)}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منوی تنگه", callback_data="dip:strait_menu")]]),
                parse_mode="Markdown"
            )
            return

        db.set_strait_status(s_key, "blocked")
        await news_engine.trigger_strait_news(context.bot, country, s_name, "block")
        await query.edit_message_text(
            f"🔴 **{s_name} به طور کامل مسدود گردید.**\n\n"
            f"• ناوگان جنگی در دهانه آبراه مستقر شد.\n"
            f"• هزینه روزانه عملیات و گشت رزمی (۲.۵M دلار + ۱۰۰k بشکه نفت) در چرخه‌های روزانه از خزانه و ذخایر شما کسر می‌گردد.\n\n"
            f"📢 خبر فوری انسداد آبراه در کانال رسمی بازی منتشر گردید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
            parse_mode="Markdown"
        )


    elif data.startswith("dip:strait_toll_val:"):
        toll_val = int(data.split(":")[2])
        toll_val = max(10_000, min(1_000_000, toll_val))
        c_key = country.get("country_key")
        strait_info = db.get_strait_info_by_country_key(c_key)
        if not strait_info:
            await query.edit_message_text("❌ شما تسلطی بر تنگه‌های استراتژیک ندارید.", parse_mode="Markdown")
            return
        s_key = strait_info["strait_key"]
        s_name = strait_info["name"]

        db.set_strait_status(s_key, "toll", toll_val)
        await news_engine.trigger_strait_news(context.bot, country, s_name, "toll", format_money(toll_val))
        await query.edit_message_text(
            f"🟡 **عوارض ترانزیت ({format_money(toll_val)}) برای عبور از {s_name} برقرار گردید.**\n\n📢 خبر رسمی در کانال منتشر گردید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
            parse_mode="Markdown"
        )

    elif data == "dip:strait_toll_custom":
        context.user_data["diplomacy_input"] = {"type": "strait_custom_toll"}
        await query.edit_message_text(
            "✍️ **لطفاً مبلغ عوارض ترانزیت مد نظر خود را به عدد انگلیسی ارسال فرمایید:**\n\n"
            "📌 **سقف مجاز:** حداکثر ۱,۰۰۰,۰۰۰ دلار (۱ میلیون دلار)\n"
            "📌 **کف مجاز:** حداقل ۱۰,۰۰۰ دلار",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="dip:strait_menu")]]),
            parse_mode="Markdown"
        )

    elif data == "dip:break_blk":
        # گارد: فقط زمانی که واقعاً تحت محاصره باشی، امکان شکستن وجود دارد
        if not db.is_country_blockaded(country["id"]):
            await query.edit_message_text(
                "❌ **کشور شما در حال حاضر تحت محاصره دریایی نیست.**\n\nمحاصره‌ای برای شکستن وجود ندارد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
            return

        active_blks = db.get_active_blockades_for_country(country["id"])
        blockaders = [db.get_country_by_id(b["blockader_id"]) for b in active_blks if b["target_id"] == country["id"]]
        blockaders = [c for c in blockaders if c]
        if not blockaders:
            await query.edit_message_text(
                "❌ اطلاعات ناوگان محاصره‌کننده یافت نشد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
            return

        # قوی‌ترین ناوگان محاصره‌کننده ملاک نبرد است
        blockader_c = max(blockaders, key=lambda c: db.calculate_naval_power(c["id"]))

        navy_assets = db.get_country_assets(country["id"], category="Navy")
        has_navy = any(n["amount"] > 0 for n in navy_assets)
        antiship_stock = db.get_antiship_missile_stock(country["id"])

        if not has_navy and antiship_stock < 1:
            await query.edit_message_text(
                "💥 **شکستن محاصره ناموفق بود!**\n\nکشور شما فاقد موشک‌های کروز ضدکشتی یا یگان‌های دریایی آماده به رزم در دیتابیس برای عقب راندن ناوگان محاصره‌کننده است.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:blockade_start")]]),
                parse_mode="Markdown"
            )
            return

        # موازنه قدرت نبرد دریایی: ناوگان مدافع + موشک‌های ضدکشتی در برابر ناوگان مهاجم و متحدین ائتلاف
        defender_navy, antiship_power, defender_power = db.calculate_blockade_break_power(country["id"])
        total_blk_power, coalition_details = db.calculate_blockade_defense_power(country["id"])
        blockader_power = total_blk_power if total_blk_power > 0 else db.calculate_naval_power(blockader_c["id"])
        required_power = max(blockader_power, 1)

        coalition_names = " + ".join([f"{p['flag']} {p['name']}" for p in coalition_details]) if coalition_details else f"{blockader_c['flag']} {blockader_c['name']}"

        if defender_power < required_power:
            spent = db.consume_antiship_missiles(country["id"], max(1, min(antiship_stock, max(1, int(antiship_stock * 0.15)))))
            await query.edit_message_text(
                f"💥 **شکستن محاصره ناموفق بود!**\n━━━━━━━━━━━━━━━━━━\n\n"
                f"📊 **تراز عملیات رزمی نبرد دریایی:**\n"
                f"• ⚓ **قدرت یگان‌های سطحی/زیرسطحی مدافع:** {defender_navy:,} امتیاز\n"
                f"• 🛡️ **قدرت آتش موشک‌های ضدکشتی مدافع ({antiship_stock:,} فروند):** {antiship_power:,} امتیاز\n"
                f"• ⚔️ **مجموع توان رزمی مدافع:** {defender_power:,} امتیاز\n"
                f"• 🛑 **قدرت ائتلاف محاصره‌کننده ({coalition_names}):** {blockader_power:,} امتیاز\n"
                f"• 🎯 **حداقل توان لازم جهت درهم شکستن خطوط محاصره (۱۰۰٪):** {required_power:,} امتیاز\n"
                f"• 💥 **مهمات مصرف‌شده در آتشباری ناموفق:** {spent:,} فروند\n\n"
                f"⚠️ ناوگان محاصره‌کننده با تکیه بر سامانه‌های پدافند لایه‌ای ایجیس و برتری تناژ دریایی، آتش موشکی شما را دفع کرده و خطوط محاصره بنادر را حفظ نمود.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:blockade_start")]]),
                parse_mode="Markdown"
            )
            return

        spent = db.consume_antiship_missiles(country["id"], max(1, min(antiship_stock, max(1, int(antiship_stock * 0.30)))))
        db.break_naval_blockade(country["id"])

        # بازیابی رضایت عمومی ازدست‌رفته در اثر محاصره
        new_app = min(100, (country.get("approval_rating") or 80) + 15)
        db.update_country_field(country["id"], "approval_rating", new_app)

        if blockader_c.get("player_id"):
            try:
                await context.bot.send_message(
                    chat_id=blockader_c["player_id"],
                    text=f"💥 **محاصره دریایی شما درهم شکسته شد!**\n\nنیروهای مدافع کشور {country['flag']} {country['name']} با شلیک متراکم موشک‌های ضدکشتی و یگان‌های دریایی، ناوگان محاصره‌گر شما را عقب راندند.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

        await news_engine.trigger_unblockade_news(context.bot, blockader_c, country, is_broken=True)

        await query.edit_message_text(
            f"💥 **پیروزی رزمی! محاصره دریایی بنادر کشور {country['name']} با موفقیت شکسته شد.**\n━━━━━━━━━━━━━━━━━━\n\n"
            f"• ⚓ **قدرت ناوگان مدافع:** {defender_navy:,} امتیاز\n"
            f"• 🛡️ **آتش موشکی مصرف‌شده:** {spent:,} فروند\n"
            f"• 🛑 **ائتلاف عقب‌رانده‌شده:** {coalition_names} ({blockader_power:,} امتیاز)\n\n"
            f"📈 شاخص رضایت عمومی به سطح پیش از محاصره بازگشت (بازیابی ۱۵٪).",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
            parse_mode="Markdown"
        )

    elif data.startswith("dip:lift_blk:"):
        target_id = int(data.split(":")[2])
        target_c = db.get_country_by_id(target_id)
        db.lift_naval_blockade(country["id"], target_id)

        if target_c:
            # بازیابی رضایت عمومی هدف پس از پایان کامل محاصره
            if not db.is_country_blockaded(target_id):
                new_app = min(100, (target_c.get("approval_rating") or 80) + 15)
                db.update_country_field(target_id, "approval_rating", new_app)
            await news_engine.trigger_unblockade_news(context.bot, country, target_c, is_broken=False)
            if target_c.get("player_id"):
                try:
                    await context.bot.send_message(
                        chat_id=target_c["player_id"],
                        text=f"🔓 **پایان محاصره دریایی**\n\nکشور {country['flag']} {country['name']} محاصره دریایی بنادر کشور شما را لغو کرد و رضایت عمومی به حالت عادی بازگشت.",
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass

        await query.edit_message_text(
            f"🔓 **محاصره دریایی علیه کشور {target_c['name'] if target_c else 'هدف'} با موفقیت لغو گردید.**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
            parse_mode="Markdown"
        )

    elif data.startswith("dip:blk_target:"):
        target_id = int(data.split(":")[2])

        if target_id == country["id"]:
            await query.edit_message_text("❌ امکان محاصره دریایی کشور خودتان وجود ندارد.", parse_mode="Markdown")
            return

        target_c = db.get_country_by_id(target_id)

        if not target_c:
            await query.edit_message_text("❌ کشور هدف پیدا نشد.", parse_mode="Markdown")
            return

        # گارد واقع‌گرایی: کشور بدون دسترسی به آب‌های آزاد قابل محاصره دریایی نیست
        if not db.has_open_sea_access(target_c.get("country_key")):
            await query.edit_message_text(
                "❌ **امکان محاصره دریایی این کشور وجود ندارد.**\n\nاین کشور به آب‌های آزاد و اقیانوس دسترسی ندارد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:blockade_start")]]),
                parse_mode="Markdown"
            )
            return

        # دریافت تازه از دیتابیس برای جلوگیری از استفاده از داده‌های کهنه (خزانه/نفت)
        country = db.get_country_by_id(country["id"]) or country

        qualified, units, val = db.check_strait_navy_qualification(country["id"])
        if not qualified:
            await query.edit_message_text(
                "⚓ **ناوگان شما شرایط عملیاتی لازم جهت محاصره را ندارد.**\n━━━━━━━━━━━━━━━━━━\n\n"
                "حداقل نیاز: **۵ شناور فعال** و **۱۰ میلیون دلار** ارزش کل ناوگان.\n"
                f"📊 **ناوگان فعلی شما:** {units} فروند (ارزش: {format_money(val)})\n\n"
                "💡 از بخش **فروشگاه → نیروی دریایی** اقدام به ساخت شناورهای رزمی فرمایید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:blockade_start")]]),
                parse_mode="Markdown"
            )
            return

        # بررسی وجود محاصره قبلی توسط همین کشور
        active_blks = db.get_active_blockades_for_country(country["id"])
        already_blockading = any(b["blockader_id"] == country["id"] and b["target_id"] == target_id for b in active_blks)
        if already_blockading:
            await query.edit_message_text(
                f"⚓ **کشور شما در حال حاضر {target_c['flag']} {target_c['name']} را تحت محاصره دریایی دارد.**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:blockade_start")]]),
                parse_mode="Markdown"
            )
            return

        today_str = datetime.date.today().isoformat()
        if country.get("last_blockade_date") == today_str:
            await query.edit_message_text(
                "⏳ **سقف مجاز روزانه عملیات دریایی:**\n━━━━━━━━━━━━━━━━━━\n\n"
                "کشور شما امروز یک بار اقدام به اجرای محاصره دریایی نموده است.\n"
                "جهت حفظ تعادل ژئوپلیتیک و جلوگیری از اسپم عملیاتی، هر کشور در هر روز تنها **۱ بار** مجاز به آغاز محاصره جدید دریایی می‌باشد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
            return

        BLOCKADE_MONEY_COST = 10_000_000
        BLOCKADE_OIL_COST = 500_000

        if country.get("treasury", 0) < BLOCKADE_MONEY_COST:
            await query.edit_message_text(
                f"💰 **عدم تکافوی تمکن مالی:**\n━━━━━━━━━━━━━━━━━━\n\n"
                f"• **هزینه اولیه اعزام ناوگان محاصره:** {format_money(BLOCKADE_MONEY_COST)}\n"
                f"• **موجودی خزانه شما:** {format_money(country.get('treasury', 0))}\n\n"
                "برای استقرار ناودسته‌ها و پشتیبانی لجستیک، خزانه شما کافی نمی‌باشد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
            return

        if country.get("oil_reserves", 0) < BLOCKADE_OIL_COST:
            await query.edit_message_text(
                f"🛢️ **عدم تکافوی ذخایر سوخت و نفت:**\n━━━━━━━━━━━━━━━━━━\n\n"
                f"• **سوخت اولیه مورد نیاز ناوگان:** {format_oil(BLOCKADE_OIL_COST)}\n"
                f"• **ذخایر نفت فعلی شما:** {format_oil(country.get('oil_reserves', 0))}\n\n"
                "برای سوخت‌رسانی سنگین به ناوشکن‌ها و شناورهای ناوگان محاصره‌کننده، به ذخایر نفت بیشتری نیاز دارید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
            return

        blockader_power = db.calculate_naval_power(country["id"])
        target_power = db.calculate_naval_power(target_id)
        required_power = max(int(target_power * 1.2), 1)

        if blockader_power < required_power:
            await query.edit_message_text(
                f"⚓ **عدم برتری دریایی لازم جهت محاصره!**\n━━━━━━━━━━━━━━━━━━\n\n"
                f"• **قدرت رزمی ناوگان شما ({country['name']}):** {blockader_power:,} امتیاز\n"
                f"• **قدرت رزمی ناوگان هدف ({target_c['name']}):** {target_power:,} امتیاز\n"
                f"• **حداقل قدرت لازم جهت محاصره (۱۲۰٪):** {required_power:,} امتیاز\n\n"
                f"⚠️ ناوگان دریایی کشور شما قدرت کافی برای مسدودسازی بنادر {target_c['name']} را ندارد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
            return

        # نمایش پیام تأییدیه دو مرحله‌ای قبل از اجرای عملیات
        confirm_text = (
            f"⚓ **تأیید نهایی عملیات محاصره دریایی بین‌المللی**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"آیا از اعزام ناودسته‌ها و استقرار محاصره کامل دریایی علیه {target_c['flag']} **{target_c['name']}** اطمینان دارید؟\n\n"
            f"📊 **برآورد هزینه و تراز عملیات:**\n"
            f"• 💵 **هزینه اولیه اعزام:** {format_money(BLOCKADE_MONEY_COST)}\n"
            f"• 🛢️ **سوخت اولیه ناوگان:** {format_oil(BLOCKADE_OIL_COST)}\n"
            f"• ⚓ **قدرت ناوگان شما ({country['name']}):** {blockader_power:,} امتیاز\n"
            f"• 🛡️ **قدرت ناوگان هدف ({target_c['name']}):** {target_power:,} امتیاز (حداقل لازم: {required_power:,})\n\n"
            f"⚠️ **پیامدهای ژئوپلیتیک عملیات:**\n"
            f"• تمامی بنادر تجاری و مسیرهای ترانزیت دریایی {target_c['name']} مسدود خواهند شد.\n"
            f"• ۱۵٪ از رضایت عمومی کشور هدف بلافاصله کسر می‌گردد.\n"
            f"• خبر فوری محاصره در کانال رسمی اخبار منتشر خواهد شد.\n"
            f"• سقف روزانه شما مصرف شده و تا ۲۴ ساعت آینده امکان محاصره جدید نخواهید داشت.\n"
        )

        confirm_keyboard = [
            [InlineKeyboardButton(f"⚓ تأیید و آغاز محاصره دریایی {target_c['name']}", callback_data=f"dip:blk_confirm:{target_id}")],
            [InlineKeyboardButton("❌ انصراف و بازگشت", callback_data="dip:blockade_start")]
        ]

        await query.edit_message_text(confirm_text, reply_markup=InlineKeyboardMarkup(confirm_keyboard), parse_mode="Markdown")

    elif data.startswith("dip:blk_confirm:"):
        target_id = int(data.split(":")[2])

        if target_id == country["id"]:
            await query.edit_message_text("❌ امکان محاصره دریایی کشور خودتان وجود ندارد.", parse_mode="Markdown")
            return

        target_c = db.get_country_by_id(target_id)
        if not target_c:
            await query.edit_message_text("❌ کشور هدف پیدا نشد.", parse_mode="Markdown")
            return

        if not db.has_open_sea_access(target_c.get("country_key")):
            await query.edit_message_text(
                "❌ **امکان محاصره دریایی این کشور وجود ندارد.**\n\nاین کشور به آب‌های آزاد و اقیانوس دسترسی ندارد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:blockade_start")]]),
                parse_mode="Markdown"
            )
            return

        country = db.get_country_by_id(country["id"]) or country

        qualified, units, val = db.check_strait_navy_qualification(country["id"])
        if not qualified:
            await query.edit_message_text(
                "❌ **ناوگان شما شرایط عملیاتی لازم جهت محاصره را ندارد.**\n\nحداقل نیاز: ۵ شناور فعال و ۱۰ میلیون دلار ارزش کل ناوگان.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:blockade_start")]]),
                parse_mode="Markdown"
            )
            return

        today_str = datetime.date.today().isoformat()
        if country.get("last_blockade_date") == today_str:
            await query.edit_message_text(
                "⏳ **سقف مجاز روزانه عملیات دریایی:**\n━━━━━━━━━━━━━━━━━━\n\n"
                "کشور شما امروز یک بار اقدام به اجرای محاصره دریایی نموده است.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
            return

        BLOCKADE_MONEY_COST = 10_000_000
        BLOCKADE_OIL_COST = 500_000

        if country.get("treasury", 0) < BLOCKADE_MONEY_COST:
            await query.edit_message_text(
                f"💰 **عدم تکافوی تمکن مالی:**\n━━━━━━━━━━━━━━━━━━\n\n"
                f"• **هزینه اولیه اعزام ناوگان محاصره:** {format_money(BLOCKADE_MONEY_COST)}\n"
                f"• **موجودی خزانه شما:** {format_money(country.get('treasury', 0))}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
            return

        if country.get("oil_reserves", 0) < BLOCKADE_OIL_COST:
            await query.edit_message_text(
                f"🛢️ **عدم تکافوی ذخایر سوخت و نفت:**\n━━━━━━━━━━━━━━━━━━\n\n"
                f"• **سوخت اولیه مورد نیاز ناوگان:** {format_oil(BLOCKADE_OIL_COST)}\n"
                f"• **ذخایر نفت فعلی شما:** {format_oil(country.get('oil_reserves', 0))}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
            return

        blockader_power = db.calculate_naval_power(country["id"])
        target_power = db.calculate_naval_power(target_id)
        required_power = max(int(target_power * 1.2), 1)

        if blockader_power < required_power:
            await query.edit_message_text(
                f"⚓ **عملیات محاصره دریایی ناموفق بود!**\n━━━━━━━━━━━━━━━━━━\n\n"
                f"• **قدرت رزمی ناوگان شما ({country['name']}):** {blockader_power:,} امتیاز\n"
                f"• **قدرت رزمی ناوگان هدف ({target_c['name']}):** {target_power:,} امتیاز\n"
                f"• **حداقل قدرت لازم جهت محاصره:** {required_power:,} امتیاز",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
            return

        # Deduct deployment costs & log
        db.adjust_treasury(country["id"], -BLOCKADE_MONEY_COST)
        db.adjust_oil(country["id"], -BLOCKADE_OIL_COST)
        db.add_transaction(country["id"], "blockade_deploy", f"هزینه اولیه اعزام ناوگان و سوخت محاصره بنادر {target_c['name']}", -BLOCKADE_MONEY_COST)

        # Update last blockade date
        db.update_country_field(country["id"], "last_blockade_date", today_str)

        # Execute naval blockade
        was_blockaded = db.is_country_blockaded(target_id)
        db.create_naval_blockade(country["id"], target_id)

        # کسر رضایت عمومی فقط بار اول (نه برای هر محاصره‌کننده جدید)
        if not was_blockaded:
            new_app = max(0, (target_c.get("approval_rating") or 80) - 15)
            db.update_country_field(target_id, "approval_rating", new_app)

        await news_engine.trigger_blockade_news(context.bot, country, target_c)

        if target_c.get("player_id"):
            try:
                await context.bot.send_message(
                    chat_id=target_c["player_id"],
                    text=(
                        f"⚓ **هشدار اضطراری — محاصره دریایی!**\n\n"
                        f"ناوگان دریایی قدرتمند کشور {country['flag']} {country['name']} تمامی بنادر و خطوط مواصلاتی دریایی شما را تحت محاصره کامل قرار داد!\n"
                        f"📉 این امر موجب کسر ۱۵٪ از رضایت عمومی و توقف درآمد بنادر تجاری گردیده است."
                    ),
                    parse_mode="Markdown"
                )
            except Exception:
                pass

        await query.edit_message_text(
            f"⚓ **عملیات محاصره دریایی علیه کشور {target_c['flag']} {target_c['name']} با موفقیت اجرا شد.**\n━━━━━━━━━━━━━━━━━━\n\n"
            f"• **هزینه پرداختی خزانه:** {format_money(BLOCKADE_MONEY_COST)}\n"
            f"• **سوخت مصرفی ناوگان:** {format_oil(BLOCKADE_OIL_COST)}\n"
            f"• **قدرت ناوگان شما:** {blockader_power:,} امتیاز\n"
            f"• **قدرت ناوگان هدف:** {target_power:,} امتیاز\n\n"
            "📢 خبر فوری این حادثه ژئوپلیتیک در کانال رسمی منتشر گردید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
            parse_mode="Markdown"
        )

    elif data.startswith("dip:blk_invite:"):
        target_id = int(data.split(":")[2])
        target_c = db.get_country_by_id(target_id)
        allies = db.get_allied_countries_for_blockade(country["id"])
        if not allies:
            await query.edit_message_text(
                "🤝 **متحد نظامی واجد شرایطی یافت نشد!**\n\n"
                "فقط کشورهایی که پیمان اتحاد نظامی رسمی (Allied) با شما دارند و به آب‌های آزاد دسترسی دارند می‌توانند به ائتلاف محاصره دعوت شوند.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:blockade_start")]]),
                parse_mode="Markdown"
            )
            return

        text = (
            "🤝 **دعوت از متحدین نظامی به ائتلاف محاصره دریایی**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"کشور هدف محاصره: {target_c['flag'] if target_c else ''} **{target_c['name'] if target_c else ''}**\n\n"
            "برای ارسال پیام دعوت به ائتلاف محاصره، کشور متحد مورد نظر را انتخاب فرمایید:"
        )
        keyboard = []
        for a in allies:
            keyboard.append([InlineKeyboardButton(f"{a['flag']} {a['name']}", callback_data=f"dip:blk_send_inv:{target_id}:{a['id']}")])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="dip:blockade_start")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("dip:blk_send_inv:"):
        _, _, target_id_s, ally_id_s = data.split(":")
        target_id = int(target_id_s)
        ally_id = int(ally_id_s)
        target_c = db.get_country_by_id(target_id)
        ally_c = db.get_country_by_id(ally_id)

        if ally_c and ally_c.get("player_id"):
            inv_msg = (
                f"⚓ **دعوت‌نامه رسمی پیوستن به ائتلاف محاصره دریایی**\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"متحد نظامی شما ({country['flag']} **{country['name']}**) از شما دعوت کرده است تا با اعزام ناوگروه رزمی، به ائتلاف محاصره بنادر کشور {target_c['flag'] if target_c else ''} **{target_c['name'] if target_c else ''}** ملحق شوید.\n\n"
                "آیا با اعزام ناوگروه و پیوستن به این محاصره مشترک موافقت می‌فرمایید؟"
            )
            inv_kb = [
                [InlineKeyboardButton("⚓ قبول و پیوستن به ائتلاف محاصره", callback_data=f"dip:blk_join:{country['id']}:{target_id}")],
                [InlineKeyboardButton("❌ رد دعوت", callback_data="dip:blockade_start")],
            ]
            try:
                await context.bot.send_message(chat_id=ally_c["player_id"], text=inv_msg, reply_markup=InlineKeyboardMarkup(inv_kb), parse_mode="Markdown")
            except Exception:
                pass

        await query.edit_message_text(
            f"✅ **دعوت‌نامه پیوستن به ائتلاف محاصره با موفقیت برای رهبر کشور {ally_c['flag'] if ally_c else ''} {ally_c['name'] if ally_c else ''} ارسال شد.**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:blockade_start")]]),
            parse_mode="Markdown"
        )

    elif data.startswith("dip:blk_join:"):
        _, _, lead_id_s, target_id_s = data.split(":")
        lead_id = int(lead_id_s)
        target_id = int(target_id_s)
        lead_c = db.get_country_by_id(lead_id)
        target_c = db.get_country_by_id(target_id)

        ok, msg = db.join_naval_blockade(lead_id, target_id, country["id"])
        if not ok:
            await query.edit_message_text(
                f"❌ **عدم امکان پیوستن:**\n\n{msg}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:blockade_start")]]),
                parse_mode="Markdown"
            )
            return

        if lead_c and lead_c.get("player_id"):
            try:
                await context.bot.send_message(
                    chat_id=lead_c["player_id"],
                    text=f"🤝 **پیوستن متحد به ائتلاف محاصره!**\n\nکشور {country['flag']} **{country['name']}** با ناوگروه دریایی خود به ائتلاف محاصره شما علیه {target_c['name'] if target_c else 'هدف'} پیوست.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

        await query.edit_message_text(
            f"⚓ **پیوستن به ائتلاف محاصره موفقیت‌آمیز بود!**\n━━━━━━━━━━━━━━━━━━\n\n"
            f"• 👑 **رهبر ائتلاف:** {lead_c['flag'] if lead_c else ''} {lead_c['name'] if lead_c else ''}\n"
            f"• 🎯 **کشور تحت محاصره:** {target_c['flag'] if target_c else ''} {target_c['name'] if target_c else ''}\n"
            f"• 🤝 **عضو جدید ائتلاف:** {country['flag']} {country['name']}\n\n"
            "توان دریایی ناوگروه شما به قدرت بازدارندگی محاصره اضافه گردید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
            parse_mode="Markdown"
        )

    elif data.startswith("dip:blk_leave:"):
        _, _, lead_id_s, target_id_s = data.split(":")
        lead_id = int(lead_id_s)
        target_id = int(target_id_s)
        ok, msg = db.leave_naval_blockade(lead_id, target_id, country["id"])
        await query.edit_message_text(
            f"🚪 **خروج از ائتلاف محاصره:**\n\n{msg}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:blockade_start")]]),
            parse_mode="Markdown"
        )

    elif data.startswith("dip:mil_target:"):
        target_id = int(data.split(":")[2])
        if db.are_sanctioned(country["id"], target_id):
            await query.edit_message_text(
                "🚫 **امکان معامله یا انتقال تسلیحات وجود ندارد:** یکی از دو کشور دیگری را تحریم کرده است.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:mil_start")]], parse_mode="Markdown")
            )
            return

        context.user_data["mil_draft"] = {"target_id": target_id}
        target_c = db.get_country_by_id(target_id)

        assets = db.get_country_assets(country["id"])
        owned_cats = sorted(list({a["category"] for a in assets if a["amount"] > 0}))

        if not owned_cats:
            await query.edit_message_text(
                "❌ کشور شما در حال حاضر هیچ تجهیزات نظامی قابل انتقالی ندارد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:menu")]], parse_mode="Markdown")
            )
            return

        text = f"🎖️ **انتقال تسلیحات نظامی به {target_c['flag']} {target_c['name']}**\n\nلطفاً دسته‌بندی تجهیزات ارسالی را انتخاب کنید:"
        keyboard = []
        cat_labels = {
            "Aircraft": "✈️ نیروی هوایی", "UAV": "🛩️ پهپادها", "Ground Forces": "🚛 نیروی زمینی",
            "Artillery": "🎯 توپخانه", "Navy": "🚢 نیروی دریایی", "Missiles": "🚀 توان موشکی", "Air Defense": "🛡️ پدافند هوایی"
        }
        for cat in owned_cats:
            keyboard.append([InlineKeyboardButton(cat_labels.get(cat, cat), callback_data=f"dip:mil_cat:{cat}")])
        keyboard.append([InlineKeyboardButton("🔙 انصراف", callback_data="dip:menu")])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("dip:mil_cat:"):
        cat = data.split(":")[2]
        assets = db.get_country_assets(country["id"], category=cat)
        available_assets = [a for a in assets if a["amount"] > 0]

        if not available_assets:
            await query.edit_message_text(
                "❌ در این دسته‌بندی تجهیزات موجودی ندارید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:mil_start")]], parse_mode="Markdown")
            )
            return

        text = "🎖️ **انتخاب تجهیز نظامی جهت انتقال:**\n\nلطفاً سلاح مد نظر را انتخاب فرمایید:"
        keyboard = []
        for a in available_assets:
            keyboard.append([InlineKeyboardButton(f"{a['equipment_name']} (موجودی: {a['amount']:,})", callback_data=f"dip:mil_asset:{a['equipment_key']}")])
        keyboard.append([InlineKeyboardButton("🔙 انصراف", callback_data="dip:menu")])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("dip:mil_asset:"):
        eq_key = data.split(":")[2]
        asset = db.get_asset_by_key(country["id"], eq_key)
        if not asset or asset["amount"] <= 0:
            await query.edit_message_text("❌ تجهیز مورد نظر موجود نیست.", parse_mode="Markdown")
            return

        if "mil_draft" not in context.user_data or not context.user_data["mil_draft"].get("target_id"):
            await query.edit_message_text(
                "⚠️ **نشست دیپلماتیک شما منقضی شده است.** لطفاً مجدداً از منوی دیپلماسی اقدام فرمایید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
            return

        my_ckey = country.get("country_key")
        orig_key = config.detect_weapon_origin(eq_key, asset["equipment_name"], my_ckey)
        is_light = config.is_light_weapon(asset["category"], eq_key, asset["equipment_name"])
        is_self_produced = (orig_key == my_ckey)

        context.user_data["mil_draft"]["equipment_key"] = eq_key
        context.user_data["mil_draft"]["equipment_name"] = asset["equipment_name"]
        context.user_data["mil_draft"]["max_amount"] = asset["amount"]
        context.user_data["mil_draft"]["origin_key"] = orig_key
        context.user_data["mil_draft"]["is_light"] = is_light
        context.user_data["mil_draft"]["is_self_produced"] = is_self_produced
        context.user_data["mil_draft"]["is_smuggled"] = 0

        orig_info = config.COUNTRIES.get(orig_key, {})
        orig_flag = orig_info.get("flag", "🌐")
        orig_name = orig_info.get("name", orig_key)

        if not is_self_produced and is_light:
            text = (
                f"🎖️ **انتقال {asset['equipment_name']}**\n"
                f"🏷️ **کشور سازنده اصلی:** {orig_flag} {orig_name}\n"
                f"📦 موجودی انبار شما: {asset['amount']:,} واحد\n\n"
                "💡 این جنگ‌افزار یک **سلاح سبک/دوش‌پرتاب** است. نحوه انتقال را انتخاب فرمایید:\n\n"
                f"• 📜 **معاهده رسمی بین‌المللی:** انتقال قانونی با استعلام مجوز صادرات (End-User License) از کشور سازنده ({orig_name})\n"
                "• 🕵️ **قاچاق از بازار سیاه:** ارسال مخفیانه بدون نیاز به مجوز سازنده (۱.۵ برابر هزینه ترانزیت + ۲۵٪ ریسک رهگیری امنیتی)"
            )
            kb = [
                [InlineKeyboardButton("📜 معاهده رسمی (با استعلام مجوز سازنده)", callback_data="dip:mil_set_mode:official")],
                [InlineKeyboardButton("🕵️ قاچاق مخفیانه بازار سیاه (بدون مجوز)", callback_data="dip:mil_set_mode:smuggle")],
                [InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
            return

        context.user_data["diplomacy_input"] = {"type": "mil_asset_qty"}
        max_amt = asset["amount"]
        possible_qtys = [1, 5, 10, 25, 50, 100]
        qty_buttons = []
        row = []

        for q in possible_qtys:
            if q < max_amt:
                row.append(InlineKeyboardButton(f"📦 {q:,} واحد", callback_data=f"dip:mil_qty:{q}"))
                if len(row) == 3:
                    qty_buttons.append(row)
                    row = []
        if max_amt > 0:
            row.append(InlineKeyboardButton(f"📦 کل موجودی ({max_amt:,})", callback_data=f"dip:mil_qty:{max_amt}"))
            qty_buttons.append(row)

        qty_buttons.append([InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")])

        heavy_note = ""
        if not is_self_produced and not is_light:
            heavy_note = f"\n🔒 **سلاح سنگین:** ساخت {orig_flag} {orig_name} (منوط به صدور مجوز صادرات)"

        await query.edit_message_text(
            f"🎖️ **انتقال {asset['equipment_name']}**{heavy_note}\n📦 موجودی فعلی کشور شما: {asset['amount']:,} واحد\n\n"
            "لطفاً **تعداد ارسالی** را از دکمه‌های زیر انتخاب کرده یا عدد مد نظر خود را تایپ فرمایید:",
            reply_markup=InlineKeyboardMarkup(qty_buttons),
            parse_mode="Markdown"
        )

    elif data.startswith("dip:mil_set_mode:"):
        mode_type = data.split(":")[2]
        draft = context.user_data.get("mil_draft", {})
        draft["is_smuggled"] = 1 if mode_type == "smuggle" else 0
        context.user_data["diplomacy_input"] = {"type": "mil_asset_qty"}

        eq_name = draft.get("equipment_name", "سلاح")
        max_amt = draft.get("max_amount", 1)
        possible_qtys = [1, 5, 10, 25, 50, 100]
        qty_buttons = []
        row = []
        for q in possible_qtys:
            if q < max_amt:
                row.append(InlineKeyboardButton(f"📦 {q:,} واحد", callback_data=f"dip:mil_qty:{q}"))
                if len(row) == 3:
                    qty_buttons.append(row)
                    row = []
        if max_amt > 0:
            row.append(InlineKeyboardButton(f"📦 کل موجودی ({max_amt:,})", callback_data=f"dip:mil_qty:{max_amt}"))
            qty_buttons.append(row)
        qty_buttons.append([InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")])

        mode_badge = "🕵️ **کانال ارسال: قاچاق مخفیانه بازار سیاه**" if draft["is_smuggled"] else "📜 **کانال ارسال: معاهده رسمی بین‌المللی**"
        await query.edit_message_text(
            f"🎖️ **انتقال {eq_name}**\n{mode_badge}\n📦 موجودی فعلی: {max_amt:,} واحد\n\n"
            "لطفاً **تعداد ارسالی** را انتخاب کرده یا عدد مورد نظر را تایپ فرمایید:",
            reply_markup=InlineKeyboardMarkup(qty_buttons),
            parse_mode="Markdown"
        )

    elif data.startswith("dip:mil_qty:"):
        qty_str = data.split(":")[2]
        draft = context.user_data.get("mil_draft", {})
        if not draft.get("target_id"):
            await query.edit_message_text(
                "⚠️ **نشست دیپلماتیک منقضی شده است.** لطفاً مجدداً اقدام فرمایید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
            return

        max_amt = draft.get("max_amount", 1)
        try:
            qty = int(qty_str)
        except ValueError:
            qty = max_amt

        qty = max(1, min(qty, max_amt))
        draft["offered_amount"] = qty
        context.user_data["mil_draft"] = draft
        context.user_data["diplomacy_input"] = {"type": "mil_asset_price"}

        price_buttons = [
            [InlineKeyboardButton("🎁 اهدای رایگان (۰ $)", callback_data="dip:mil_price:0")],
            [InlineKeyboardButton("💰 ۱,۰۰۰,۰۰۰ $", callback_data="dip:mil_price:1000000"), InlineKeyboardButton("💰 ۵,۰۰۰,۰۰۰ $", callback_data="dip:mil_price:5000000")],
            [InlineKeyboardButton("💰 ۱۰,۰۰۰,۰۰۰ $", callback_data="dip:mil_price:10000000"), InlineKeyboardButton("💰 ۵۰,۰۰۰,۰۰۰ $", callback_data="dip:mil_price:50000000")],
            [InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]
        ]

        await query.edit_message_text(
            f"🎖️ **انتقال {draft.get('equipment_name', 'تجهیز')} (تعداد: {qty:,} واحد)**\n\n"
            "لطفاً **قیمت درخواستی برای فروش (به دلار)** را از دکمه‌های زیر انتخاب کرده یا عدد مد نظر را تایپ فرمایید:",
            reply_markup=InlineKeyboardMarkup(price_buttons),
            parse_mode="Markdown"
        )

    elif data.startswith("dip:mil_price:"):
        price_str = data.split(":")[2]
        draft = context.user_data.get("mil_draft", {})
        if not draft.get("target_id"):
            await query.edit_message_text(
                "⚠️ **نشست دیپلماتیک منقضی شده است.** لطفاً مجدداً اقدام فرمایید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
            return

        try:
            price = int(price_str)
        except ValueError:
            price = 0

        draft["requested_amount"] = price
        context.user_data["mil_draft"] = draft

        text = (
            f"🎖️ **معاهده نظامی — {draft.get('equipment_name', 'تجهیز')} (تعداد: {draft.get('offered_amount', 1):,} واحد | قیمت: {format_money(price)})**\n\n"
            "پرداخت‌کننده هزینه ترانزیت و حمل‌ونقل نظامی را مشخص بفرمایید:"
        )
        kb = [
            [InlineKeyboardButton("فروشنده (پیشنهاددهنده)", callback_data="dip:mil_payer:seller")],
            [InlineKeyboardButton("خریدار (کشور مخاطب)", callback_data="dip:mil_payer:buyer")],
            [InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")

    elif data.startswith("dip:mil_payer:"):
        payer = data.split(":")[2]
        draft = context.user_data.get("mil_draft", {})
        draft["transport_payer"] = payer
        target_c = db.get_country_by_id(draft.get("target_id", 0))

        my_key = country.get("country_key")
        t_key = target_c.get("country_key") if target_c else ""
        has_sea = db.has_open_sea_access(my_key) and db.has_open_sea_access(t_key)

        sea_reason = ""
        if not has_sea:
            if not db.has_open_sea_access(my_key):
                sea_reason = f"کشور شما ({country['flag']} {country['name']}) محصور در خشکی است و به آب‌های آزاد دسترسی ساحلی ندارد."
            else:
                t_name = target_c['name'] if target_c else 'مقصد'
                t_flag = target_c.get('flag', '') if target_c else ''
                sea_reason = f"کشور مقصد ({t_flag} {t_name}) محصور در خشکی است و به آب‌های آزاد دسترسی ساحلی ندارد."

        strait_analysis = db.get_trade_route_strait_analysis(my_key, t_key)
        is_strait_blocked = strait_analysis["is_blocked"]
        has_strait_tolls = strait_analysis["has_tolls"]
        strait_toll_total = strait_analysis["total_toll"]

        sea_used, sea_cap = db.get_trade_mode_budget(country["id"], "sea")
        air_used, air_cap = db.get_trade_mode_budget(country["id"], "air")
        land_used, land_cap = db.get_trade_mode_budget(country["id"], "land")

        if not has_sea:
            sea_line = f"• 🚫 **ترابری دریایی:** غیرفعال ({sea_reason})"
            sea_btn = None
        elif is_strait_blocked:
            blocked_str = "، ".join([s["name"] for s in strait_analysis["blocked_straits"]])
            sea_line = f"• ⛔ **ترابری دریایی:** مسدود ({blocked_str})"
            sea_btn = InlineKeyboardButton(f"⛔ دریایی (مسدود: {blocked_str})", callback_data=f"dip:mil_finish:sea:{payer}")
        elif has_strait_tolls:
            toll_str = "، ".join([f"{s['name']} ({s['toll_amount']:,} $)" for s in strait_analysis["toll_straits"]])
            total_sea_cost = 300_000 + strait_toll_total
            sea_line = f"• 🚢 **ترابری دریایی:** ۳۰۰,۰۰۰ دلار + {strait_toll_total:,} دلار عوارض تنگه‌ها ({toll_str}) = **{total_sea_cost:,} دلار** (سقف امروز: {sea_used}/{sea_cap})"
            sea_btn = InlineKeyboardButton(f"🚢 ترابری دریایی ({total_sea_cost:,} $ با عوارض)", callback_data=f"dip:mil_finish:sea:{payer}")
        else:
            sea_line = f"• 🚢 **ترابری دریایی:** ۳۰۰,۰۰۰ دلار (سقف امروز: {sea_used}/{sea_cap})"
            sea_btn = InlineKeyboardButton(f"🚢 ترابری دریایی ({sea_used}/{sea_cap})", callback_data=f"dip:mil_finish:sea:{payer}")

        has_land = db.has_land_trade_route(my_key, t_key)
        if has_land:
            land_line = f"• **🚛 ترابری زمینی:** ۱,۰۰۰,۰۰۰ دلار (سقف امروز: {land_used}/{land_cap})"
            land_btn = InlineKeyboardButton(f"🚛 ترابری زمینی ({land_used}/{land_cap})", callback_data=f"dip:mil_finish:land:{payer}")
        else:
            land_line = "• 🚫 **ترابری زمینی:** غیرفعال — مسیر خشکی پیوسته‌ای بین دو کشور وجود ندارد"
            land_btn = None

        text = (
            "🌐 **انتخاب روش ترابری و ترانزیت محموله نظامی**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً روش ارسال تجهیزات را انتخاب بفرمایید:\n\n"
            f"⚖️ **ظرفیت هر محموله (تن):** کشتی **{db.transfer_weight_capacity('sea'):,}** | قطار/کامیون **{db.transfer_weight_capacity('land'):,}** | هواپیما **{db.transfer_weight_capacity('air'):,}**\n"
            "*(جنگنده ≈ ۲۰ تن | تانک ≈ ۳۰ تن | پدافند ≈ ۱۵ تن | موشک ≈ ۲ تن | پهپاد ≈ ۰.۴ تن)*\n\n"
            f"• **✈️ ترابری هوایی:** ۲,۰۰۰,۰۰۰ دلار (سقف امروز: {air_used}/{air_cap})\n"
            f"{land_line}\n"
            f"{sea_line}"
        )
        keyboard = [
            [InlineKeyboardButton(f"✈️ ترابری هوایی ({air_used}/{air_cap})", callback_data=f"dip:mil_finish:air:{payer}")],
        ]
        if land_btn:
            keyboard.append([land_btn])
        if sea_btn:
            keyboard.append([sea_btn])
        keyboard.append([InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("dip:mil_finish:") or data.startswith("dip:mil_finish_confirm:"):
        is_confirmed = data.startswith("dip:mil_finish_confirm:")
        parts = data.split(":")
        mode = parts[2]
        payer = parts[3]
        draft = context.user_data.get("mil_draft", {})
        target_c = db.get_country_by_id(draft.get("target_id", 0))

        if not target_c:
            await query.edit_message_text(
                "⚠️ **نشست دیپلماتیک منقضی شده است.** لطفاً مجدداً اقدام فرمایید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
            return

        # بررسی سقف تجارت روزانه برای روش ترابری انتخاب‌شده
        can_trade, limit_msg = db.check_trade_mode_limit(country["id"], mode)
        if not can_trade:
            await query.edit_message_text(
                limit_msg,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏪 احداث زیرساخت در فروشگاه", callback_data="shopcat:transport")],
                    [InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]
                ]),
                parse_mode="Markdown"
            )
            return

        p_key = country.get("country_key")
        t_key = target_c.get("country_key")
        strait_analysis = db.get_trade_route_strait_analysis(p_key, t_key)

        if mode == "sea":
            if not db.has_open_sea_access(p_key) or not db.has_open_sea_access(t_key):
                no_sea_c = country if not db.has_open_sea_access(p_key) else target_c
                await query.edit_message_text(
                    f"⚓ **ترابری دریایی غیرمجاز است!**\n\n"
                    f"کشور {no_sea_c['flag']} **{no_sea_c['name']}** محصور در خشکی است و به آب‌های آزاد دسترسی ساحلی ندارد.\n\n"
                    "لطفاً برای این معاهده از ترابری هوایی یا زمینی استفاده فرمایید.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✈️ ترابری هوایی (۲,۰۰۰,۰۰۰ دلار)", callback_data=f"dip:mil_finish:air:{payer}")],
                        [InlineKeyboardButton("🚛 ترابری زمینی (۱,۰۰۰,۰۰۰ دلار)", callback_data=f"dip:mil_finish:land:{payer}")],
                        [InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]
                    ]),
                    parse_mode="Markdown"
                )
                return

            if db.is_country_blockaded(country["id"]) or db.is_country_blockaded(draft["target_id"]):
                await query.edit_message_text(
                    "⚓ **ترابری دریایی مسدود است!**\n\nکشور شما یا کشور مقصد در حال حاضر تحت محاصره کامل دریایی است. لطفاً برای این معاهده از ترابری هوایی یا زمینی استفاده فرمایید.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✈️ ترابری هوایی (۲,۰۰۰,۰۰۰ دلار)", callback_data=f"dip:mil_finish:air:{payer}")],
                        [InlineKeyboardButton("🚛 ترابری زمینی (۱,۰۰۰,۰۰۰ دلار)", callback_data=f"dip:mil_finish:land:{payer}")],
                        [InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]
                    ]),
                    parse_mode="Markdown"
                )
                return

            if strait_analysis["is_blocked"]:
                blocked_details = "\n".join([f"• ⛔ **{s['name']}** (تحت مسدودسازی کشور {s['owner_flag']} **{s['owner_name']}**)" for s in strait_analysis["blocked_straits"]])
                await query.edit_message_text(
                    f"⚓ **ترابری دریایی مسدود است!**\n\n"
                    f"مسیر ترانزیت دریایی به دلیل مسدود بودن آبراه‌های استراتژیک قطع می‌باشد:\n\n"
                    f"{blocked_details}\n\n"
                    f"💡 لطفاً برای این معاهده از ترابری هوایی یا زمینی استفاده فرمایید.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✈️ ترابری هوایی (۲,۰۰۰,۰۰۰ دلار)", callback_data=f"dip:mil_finish:air:{payer}")],
                        [InlineKeyboardButton("🚛 ترابری زمینی (۱,۰۰۰,۰۰۰ دلار)", callback_data=f"dip:mil_finish:land:{payer}")],
                        [InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]
                    ]),
                    parse_mode="Markdown"
                )
                return

            if strait_analysis["has_tolls"] and not is_confirmed:
                toll_lines = "\n".join([f"• 🌊 **{s['name']}** (تحت کنترل {s['owner_flag']} **{s['owner_name']}**): `{s['toll_amount']:,} $`" for s in strait_analysis["toll_straits"]])
                total_toll = strait_analysis["total_toll"]
                total_transport = 300_000 + total_toll
                payer_label = "فروشنده (پیشنهاددهنده)" if payer == "seller" else f"خریدار ({target_c['name']})"

                text = (
                    f"🌊 **هشدار و تأییدیه عوارض ترانزیت تنگه‌های دریایی (معاهده نظامی)**\n"
                    f"━━━━━━━━━━━━━━━━━━\n\n"
                    f"کشور محترم، ناوگان ترابری دریایی حامل تسلیحات برای رسیدن به مقصد ({target_c['flag']} **{target_c['name']}**) باید از تنگه‌های دارای **عوارض حق عبور** عبور نماید:\n\n"
                    f"{toll_lines}\n\n"
                    f"💰 **تفکیک هزینه‌های ترانزیت دریایی:**\n"
                    f"• **کرایه پایه ناوگان دریایی:** `۳۰۰,۰۰۰ $`\n"
                    f"• **مجموع عوارض تنگه‌ها:** `{total_toll:,} $`\n"
                    f"• **مجموع کل هزینه ترابری:** **`{total_transport:,} $`**\n"
                    f"• **پرداخت‌کننده هزینه:** **{payer_label}**\n\n"
                    f"⚠️ *مبلغ عوارض هنگام امضا و اجرای معاهده مستقیماً به خزانه کشورهای کنترل‌کننده تنگه واریز خواهد شد.*\n\n"
                    f"آیا با صدور و ارسال این معاهده تسلیحاتی موافقید؟"
                )
                keyboard = [
                    [InlineKeyboardButton(f"✅ تأیید و ارسال معاهده ({total_transport:,} $)", callback_data=f"dip:mil_finish_confirm:sea:{payer}")],
                    [InlineKeyboardButton("✈️ تغییر به ترابری هوایی (۲,۰۰۰,۰۰۰ $)", callback_data=f"dip:mil_finish:air:{payer}")],
                    [InlineKeyboardButton("🚛 تغییر به ترابری زمینی (۱,۰۰۰,۰۰۰ $)", callback_data=f"dip:mil_finish:land:{payer}")],
                    [InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]
                ]
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
                return

        if mode == "land" and not db.has_land_trade_route(p_key, t_key):
            await query.edit_message_text(
                f"🚛 **ترابری زمینی غیرمجاز است!**\n\n"
                f"هیچ مسیر خشکی پیوسته‌ای (مرز مشترک یا ترانزیت زمینی) بین {country['flag']} **{country['name']}** و {target_c['flag']} **{target_c['name']}** وجود ندارد.\n\n"
                "لطفاً برای این معاهده از ترابری دریایی یا هوایی استفاده فرمایید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✈️ ترابری هوایی (۲,۰۰۰,۰۰۰ دلار)", callback_data=f"dip:mil_finish:air:{payer}")],
                    [InlineKeyboardButton("🚢 ترابری دریایی (۳۰۰,۰۰۰ دلار)", callback_data=f"dip:mil_finish:sea:{payer}")],
                    [InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]
                ]),
                parse_mode="Markdown"
            )
            return

        is_smuggled = draft.get("is_smuggled", 0)
        orig_key = draft.get("origin_key", country.get("country_key"))
        orig_c = db.get_country_by_key(orig_key)
        is_self = (orig_key == country.get("country_key"))

        cost_map = {"air": 2_000_000, "land": 1_000_000, "sea": 300_000}
        mode_labels = {"air": "✈️ ترابری هوایی", "land": "🚛 ترابری زمینی", "sea": "🚢 ترابری دریایی"}
        t_cost = cost_map.get(mode, 300_000)
        if is_smuggled:
            t_cost = int(t_cost * 1.5)

        # بررسی مجوز صادرات و بلوک‌های ژئوپلیتیک
        lic_cid = None
        lic_status = "approved"

        if not is_self and not is_smuggled:
            if orig_c and orig_c.get("player_id") and orig_c["id"] != country["id"]:
                lic_cid = orig_c["id"]
                lic_status = "pending"
            else:
                # NPC manufacturer: بررسی بلوک‌های ژئوپلیتیک
                t_ckey = target_c.get("country_key", "")
                orig_info = config.COUNTRIES.get(orig_key, {})
                if orig_key in config.WESTERN_NATO_BLOC and t_ckey in config.RESISTANCE_EASTERN_BLOC:
                    await query.edit_message_text(
                        f"⛔ **وتوی خودکار کشور سازنده (تحریم تسلیحاتی بین‌المللی):**\n\n"
                        f"کشور سازنده این جنگ‌افزار ({orig_info.get('flag', '🌐')} **{orig_info.get('name', orig_key)}**) "
                        f"به دلیل قوانین عدم اشاعه و تحریم‌های امنیتی بلوک غرب، اجازه فروش و انتقال این سلاح به کشورهای محور مقاومت را نمی‌دهد.\n\n"
                        "💡 *راهکار:* فقط سلاح‌های سبک از طریق بازار سیاه قابل قاچاق هستند.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                        parse_mode="Markdown"
                    )
                    return
                elif orig_key in config.RESISTANCE_EASTERN_BLOC and t_ckey in config.WESTERN_NATO_BLOC:
                    await query.edit_message_text(
                        f"⛔ **وتوی خودکار کشور سازنده (تحریم تسلیحاتی بین‌المللی):**\n\n"
                        f"کشور سازنده این جنگ‌افزار ({orig_info.get('flag', '🌐')} **{orig_info.get('name', orig_key)}**) "
                        f"اجازه فروش و انتقال تسلیحات خود به کشورهای عضو ناتو و هم‌پیمانان غربی را نمی‌دهد.",
                        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                        parse_mode="Markdown"
                    )
                    return

        contract_id = db.create_trade_contract(
            proposer_id=country["id"],
            recipient_id=draft["target_id"],
            offered_type="military_asset",
            offered_amount=draft["offered_amount"],
            requested_type="treasury",
            requested_amount=draft["requested_amount"],
            transport_payer=payer,
            transport_cost=t_cost,
            offered_key=draft["equipment_key"],
            transport_mode=mode,
            is_smuggled=is_smuggled,
            origin_country_key=orig_key,
            license_country_id=lic_cid,
            license_status=lic_status
        )

        strait_toll_msg = ""
        if mode == "sea" and strait_analysis["has_tolls"]:
            toll_names = "، ".join([f"{s['name']} ({s['toll_amount']:,} $)" for s in strait_analysis["toll_straits"]])
            strait_toll_msg = f"\n• 🌊 **عوارض ترانزیت تنگه‌ها:** {strait_analysis['total_toll']:,} $ ({toll_names})"

        total_trans_cost = t_cost + (strait_analysis["total_toll"] if mode == "sea" else 0)

        if lic_status == "pending":
            orig_msg = (
                f"📜 **درخواست صدور مجوز صادرات تسلیحات (End-User Export License)**\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"کشور {country['flag']} **{country['name']}** قصد دارد جنگ‌افزار ساخت کشور شما ({orig_c['flag']} **{orig_c['name']}**) را به {target_c['flag']} **{target_c['name']}** واگذار/فروش کند:\n\n"
                f"• 🎖️ **سلاح:** {draft['equipment_name']}\n"
                f"• 📦 **تعداد:** {draft['offered_amount']:,} واحد\n"
                f"• 💰 **مبلغ معامله:** {format_money(draft['requested_amount'])}\n"
                f"• ✈️ **روش ترابری:** {mode_labels.get(mode, mode)}{strait_toll_msg}\n\n"
                f"⚠️ *طبق حقوق بین‌الملل و قوانین ITAR، انتقال این سلاح مشروط به تأیید شما به عنوان کشور سازنده اصلی است.*\n\n"
                f"آیا با صدور مجوز صادرات و انتقال این سلاح به مقصد موافقت می‌فرمایید؟"
            )
            orig_kb = [
                [InlineKeyboardButton("✅ صدور مجوز صادرات (Approve License)", callback_data=f"dip:lic_app:{contract_id}")],
                [InlineKeyboardButton("🚫 وتو و لغو معاهده (Veto Export)", callback_data=f"dip:lic_veto:{contract_id}")],
            ]
            if orig_c.get("player_id"):
                try:
                    await context.bot.send_message(chat_id=orig_c["player_id"], text=orig_msg, reply_markup=InlineKeyboardMarkup(orig_kb), parse_mode="Markdown")
                except Exception:
                    pass

            await query.edit_message_text(
                f"⏳ **معاهده تسلیحاتی در انتظار مجوز کشور سازنده:**\n\n"
                f"سلاح انتخابی شما ساخت کشور {orig_c['flag']} **{orig_c['name']}** است.\n"
                f"درخواست صدور مجوز صادرات (End-User License) برای رهبر این کشور ارسال شد. به محض موافقت ایشان، معاهده جهت امضا برای کشور خریدار ({target_c['name']}) فرستاده خواهد شد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
            return

        # Direct proposal to Recipient
        if is_smuggled:
            recip_msg = (
                f"🕵️ **پیشنهاد محموله قاچاق تسلیحاتی از بازار سیاه از طرف {country['flag']} {country['name']}**\n\n"
                f"• **جنگ‌افزار:** {draft['equipment_name']} (قاچاق مخفیانه)\n"
                f"• **تعداد تحویلی:** {draft['offered_amount']:,} واحد\n"
                f"• **مبلغ پرداختی درخواستی از شما:** {format_money(draft['requested_amount'])}\n"
                f"• **روش ترابری:** {mode_labels.get(mode, mode)} (کاروان مخفی){strait_toll_msg}\n"
                f"• **پرداخت‌کننده هزینه ترانزیت ({format_money(total_trans_cost)}):** {'فروشنده' if payer == 'seller' else 'خریدار (شما)'}\n\n"
                f"⚠️ *هشدار اطلاعاتی:* این محموله بدون مجوز سازنده ارسال می‌شود و ۲۵٪ ریسک رهگیری و توقیف مرزی دارد.\n\n"
                "آیا با دریافت و پذیرش این محموله قاچاق موافقید؟"
            )
        else:
            recip_msg = (
                f"🎖️ **پیشنهاد معاهده تحویل/فروش تسلیحات نظامی از طرف {country['flag']} {country['name']}**\n\n"
                f"• **سلاح ارسالی:** {draft['equipment_name']}\n"
                f"• **تعداد تحویلی:** {draft['offered_amount']:,} واحد\n"
                f"• **مبلغ پرداختی درخواستی از شما:** {format_money(draft['requested_amount'])}\n"
                f"• **روش ترابری:** {mode_labels.get(mode, mode)}{strait_toll_msg}\n"
                f"• **پرداخت‌کننده هزینه ترانزیت ({format_money(total_trans_cost)}):** {'فروشنده' if payer == 'seller' else 'خریدار (شما)'}\n\n"
                "آیا با دریافت و امضای این معاهده تسلیحاتی موافقید؟"
            )

        recip_kb = [
            [InlineKeyboardButton("✅ قبول و تحویل تسلیحات", callback_data=f"dip:trade_accept:{contract_id}")],
            [InlineKeyboardButton("❌ رد معاهده نظامی", callback_data=f"dip:trade_reject:{contract_id}")],
        ]

        if target_c and target_c.get("player_id"):
            try:
                await context.bot.send_message(chat_id=target_c["player_id"], text=recip_msg, reply_markup=InlineKeyboardMarkup(recip_kb), parse_mode="Markdown")
            except Exception:
                pass

        await query.edit_message_text(
            f"✅ **پیشنهاد معاهده نظامی با موفقیت به کشور {target_c['name']} ارسال شد.**\nپس از تایید و امضای طرف مقابل، تجهیزات منتقل می‌گردد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
            parse_mode="Markdown"
        )
    elif data.startswith("dip:msg_target:"):
        target_id = int(data.split(":")[2])
        target_c = db.get_country_by_id(target_id)
        context.user_data["diplomacy_input"] = {"type": "send_msg", "target_id": target_id}
        await query.edit_message_text(
            f"✉️ **ارسال یادداشت دیپلماتیک به {target_c['flag']} {target_c['name']}**\n\n"
            "لطفاً متن یادداشت رسمی خود را ارسال فرمایید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]]),
            parse_mode="Markdown"
        )

    elif data == "dip:trade_start":
        await dip_trade_start(query, context, country)

    elif data.startswith("dip:trade_target:"):
        target_id = int(data.split(":")[2])
        if db.are_sanctioned(country["id"], target_id):
            await query.edit_message_text(
                "🚫 **امکان معامله وجود ندارد:** یکی از دو کشور دیگری را تحریم کرده است.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:trade_start")]]),
                parse_mode="Markdown"
            )
            return

        context.user_data["trade_draft"] = {"target_id": target_id}
        text = f"📜 **قرارداد تجاری با کشور {db.get_country_by_id(target_id)['name']}**\n\n**مرحله ۱:** نوع کالای ارسالی (پیشنهادی شما) را انتخاب کنید:"
        keyboard = [
            [InlineKeyboardButton("💰 پول (خزانه)", callback_data="dip:trade_off:treasury"), InlineKeyboardButton("🪙 طلا", callback_data="dip:trade_off:gold")],
            [InlineKeyboardButton("🛢️ نفت", callback_data="dip:trade_off:oil"), InlineKeyboardButton("🌾 غلات", callback_data="dip:trade_off:grain")],
            [InlineKeyboardButton("⛏️ آهن و فولاد", callback_data="dip:trade_off:iron_ore"), InlineKeyboardButton("💻 میکروچیپ", callback_data="dip:trade_off:microchips")],
            [InlineKeyboardButton("☢️ کیک زرد اورانیوم", callback_data="dip:trade_off:uranium_ore"), InlineKeyboardButton("🧪 سوخت هسته‌ای", callback_data="dip:trade_off:nuclear_fuel")],
            [InlineKeyboardButton("🔙 انصراف", callback_data="dip:menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("dip:trade_off:"):
        off_type = data.split(":")[2]
        if "trade_draft" not in context.user_data:
            context.user_data["trade_draft"] = {}
        context.user_data["trade_draft"]["offered_type"] = off_type
        context.user_data["diplomacy_input"] = {"type": "trade_off_amount"}
        
        type_labels = {"treasury": "دلار", "gold": "شمش طلا", "oil": "بشکه نفت", "grain": "تن غلات", "iron_ore": "تن آهن و فولاد", "microchips": "عدد میکروچیپ", "uranium_ore": "تن کیک زرد", "nuclear_fuel": "کیلوگرم سوخت هسته‌ای"}
        await query.edit_message_text(
            f"💰 **مقدار پیشنهادی ({type_labels.get(off_type, off_type)})** را به عدد وارد فرمایید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]]),
            parse_mode="Markdown"
        )

    elif data.startswith("dip:trade_req:"):
        req_type = data.split(":")[2]
        if "trade_draft" not in context.user_data:
            context.user_data["trade_draft"] = {}
        context.user_data["trade_draft"]["requested_type"] = req_type
        context.user_data["diplomacy_input"] = {"type": "trade_req_amount"}
        
        type_labels = {"treasury": "دلار", "gold": "شمش طلا", "oil": "بشکه نفت", "grain": "تن غلات", "iron_ore": "تن آهن و فولاد", "microchips": "عدد میکروچیپ", "uranium_ore": "تن کیک زرد", "nuclear_fuel": "کیلوگرم سوخت هسته‌ای"}
        await query.edit_message_text(
            f"🎯 **مقدار درخواستی مابه‌ازا ({type_labels.get(req_type, req_type)})** را به عدد وارد فرمایید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]]),
            parse_mode="Markdown"
        )

    elif data.startswith("dip:trade_payer:"):
        payer = data.split(":")[2] # 'seller' or 'buyer'
        draft = context.user_data.get("trade_draft", {})
        draft["transport_payer"] = payer
        target_c = db.get_country_by_id(draft.get("target_id", 0))

        my_key = country.get("country_key")
        t_key = target_c.get("country_key") if target_c else ""
        has_sea = db.has_open_sea_access(my_key) and db.has_open_sea_access(t_key)

        sea_reason = ""
        if not has_sea:
            if not db.has_open_sea_access(my_key):
                sea_reason = f"کشور شما ({country['flag']} {country['name']}) محصور در خشکی است و به آب‌های آزاد دسترسی ساحلی ندارد."
            else:
                t_name = target_c['name'] if target_c else 'مقصد'
                t_flag = target_c.get('flag', '') if target_c else ''
                sea_reason = f"کشور مقصد ({t_flag} {t_name}) محصور در خشکی است و به آب‌های آزاد دسترسی ساحلی ندارد."

        strait_analysis = db.get_trade_route_strait_analysis(my_key, t_key)
        is_strait_blocked = strait_analysis["is_blocked"]
        has_strait_tolls = strait_analysis["has_tolls"]
        strait_toll_total = strait_analysis["total_toll"]

        sea_used, sea_cap = db.get_trade_mode_budget(country["id"], "sea")
        air_used, air_cap = db.get_trade_mode_budget(country["id"], "air")
        land_used, land_cap = db.get_trade_mode_budget(country["id"], "land")

        if not has_sea:
            sea_line = f"• 🚫 **ترابری دریایی:** غیرفعال ({sea_reason})"
            sea_btn = None
        elif is_strait_blocked:
            blocked_str = "، ".join([s["name"] for s in strait_analysis["blocked_straits"]])
            sea_line = f"• ⛔ **ترابری دریایی:** مسدود ({blocked_str})"
            sea_btn = InlineKeyboardButton(f"⛔ دریایی (مسدود: {blocked_str})", callback_data=f"dip:trade_finish:sea:{payer}")
        elif has_strait_tolls:
            toll_str = "، ".join([f"{s['name']} ({s['toll_amount']:,} $)" for s in strait_analysis["toll_straits"]])
            total_sea_cost = 300_000 + strait_toll_total
            sea_line = f"• 🚢 **ترابری دریایی:** ۳۰۰,۰۰۰ دلار + {strait_toll_total:,} دلار عوارض تنگه‌ها ({toll_str}) = **{total_sea_cost:,} دلار** (سقف امروز: {sea_used}/{sea_cap})"
            sea_btn = InlineKeyboardButton(f"🚢 ترابری دریایی ({total_sea_cost:,} $ با عوارض)", callback_data=f"dip:trade_finish:sea:{payer}")
        else:
            sea_line = f"• 🚢 **ترابری دریایی:** ۳۰۰,۰۰۰ دلار (سقف امروز: {sea_used}/{sea_cap})"
            sea_btn = InlineKeyboardButton(f"🚢 ترابری دریایی ({sea_used}/{sea_cap})", callback_data=f"dip:trade_finish:sea:{payer}")

        has_land = db.has_land_trade_route(my_key, t_key)
        if has_land:
            land_line = f"• **🚛 ترابری زمینی:** ۱,۰۰۰,۰۰۰ دلار (سقف امروز: {land_used}/{land_cap})"
            land_btn = InlineKeyboardButton(f"🚛 ترابری زمینی ({land_used}/{land_cap})", callback_data=f"dip:trade_finish:land:{payer}")
        else:
            land_line = "• 🚫 **ترابری زمینی:** غیرفعال — مسیر خشکی پیوسته‌ای بین دو کشور وجود ندارد"
            land_btn = None

        text = (
            "🌐 **انتخاب روش ترابری و ترانزیت محموله تجاری**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً روش ارسال کالاهای تجاری را انتخاب بفرمایید:\n\n"
            f"⚖️ **ظرفیت هر محموله (تن):** کشتی **{db.transfer_weight_capacity('sea'):,}** | قطار/کامیون **{db.transfer_weight_capacity('land'):,}** | هواپیما **{db.transfer_weight_capacity('air'):,}**\n"
            "*(جنگنده ≈ ۲۰ تن | تانک ≈ ۳۰ تن | پدافند ≈ ۱۵ تن | موشک ≈ ۲ تن | پهپاد ≈ ۰.۴ تن)*\n\n"
            f"• **✈️ ترابری هوایی:** ۲,۰۰۰,۰۰۰ دلار (سقف امروز: {air_used}/{air_cap})\n"
            f"{land_line}\n"
            f"{sea_line}"
        )
        keyboard = [
            [InlineKeyboardButton(f"✈️ ترابری هوایی ({air_used}/{air_cap})", callback_data=f"dip:trade_finish:air:{payer}")],
        ]
        if land_btn:
            keyboard.append([land_btn])
        if sea_btn:
            keyboard.append([sea_btn])
        keyboard.append([InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("dip:trade_finish:") or data.startswith("dip:trade_finish_confirm:"):
        is_confirmed = data.startswith("dip:trade_finish_confirm:")
        parts = data.split(":")
        mode = parts[2]
        payer = parts[3]
        draft = context.user_data.get("trade_draft", {})
        target_c = db.get_country_by_id(draft.get("target_id", 0))

        if not target_c:
            await query.edit_message_text(
                "⚠️ **نشست دیپلماتیک منقضی شده است.** لطفاً مجدداً اقدام فرمایید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
            return

        # بررسی سقف تجارت روزانه برای روش ترابری انتخاب‌شده
        can_trade, limit_msg = db.check_trade_mode_limit(country["id"], mode)
        if not can_trade:
            await query.edit_message_text(
                limit_msg,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🏪 احداث زیرساخت در فروشگاه", callback_data="shopcat:transport")],
                    [InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]
                ]),
                parse_mode="Markdown"
            )
            return

        p_key = country.get("country_key")
        t_key = target_c.get("country_key")
        strait_analysis = db.get_trade_route_strait_analysis(p_key, t_key)

        if mode == "sea":
            if not db.has_open_sea_access(p_key) or not db.has_open_sea_access(t_key):
                no_sea_c = country if not db.has_open_sea_access(p_key) else target_c
                await query.edit_message_text(
                    f"⚓ **ترابری دریایی غیرمجاز است!**\n\n"
                    f"کشور {no_sea_c['flag']} **{no_sea_c['name']}** محصور در خشکی است و به آب‌های آزاد دسترسی ساحلی ندارد.\n\n"
                    "لطفاً برای این معاهده از ترابری هوایی یا زمینی استفاده فرمایید.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✈️ ترابری هوایی (۲,۰۰۰,۰۰۰ دلار)", callback_data=f"dip:trade_finish:air:{payer}")],
                        [InlineKeyboardButton("🚛 ترابری زمینی (۱,۰۰۰,۰۰۰ دلار)", callback_data=f"dip:trade_finish:land:{payer}")],
                        [InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]
                    ]),
                    parse_mode="Markdown"
                )
                return

            if db.is_country_blockaded(country["id"]) or db.is_country_blockaded(draft["target_id"]):
                await query.edit_message_text(
                    "⚓ **ترابری دریایی مسدود است!**\n\nکشور شما یا کشور مقصد در حال حاضر تحت محاصره کامل دریایی است. لطفاً برای این معاهده از ترابری هوایی یا زمینی استفاده فرمایید.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✈️ ترابری هوایی (۲,۰۰۰,۰۰۰ دلار)", callback_data=f"dip:trade_finish:air:{payer}")],
                        [InlineKeyboardButton("🚛 ترابری زمینی (۱,۰۰۰,۰۰۰ دلار)", callback_data=f"dip:trade_finish:land:{payer}")],
                        [InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]
                    ]),
                    parse_mode="Markdown"
                )
                return

            if strait_analysis["is_blocked"]:
                blocked_details = "\n".join([f"• ⛔ **{s['name']}** (تحت مسدودسازی کشور {s['owner_flag']} **{s['owner_name']}**)" for s in strait_analysis["blocked_straits"]])
                await query.edit_message_text(
                    f"⚓ **ترابری دریایی مسدود است!**\n\n"
                    f"مسیر ترانزیت دریایی بین دو کشور به دلیل مسدود بودن آبراه‌های استراتژیک قطع می‌باشد:\n\n"
                    f"{blocked_details}\n\n"
                    f"💡 لطفاً برای این معاهده از ترابری هوایی یا زمینی استفاده فرمایید.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✈️ ترابری هوایی (۲,۰۰۰,۰۰۰ دلار)", callback_data=f"dip:trade_finish:air:{payer}")],
                        [InlineKeyboardButton("🚛 ترابری زمینی (۱,۰۰۰,۰۰۰ دلار)", callback_data=f"dip:trade_finish:land:{payer}")],
                        [InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]
                    ]),
                    parse_mode="Markdown"
                )
                return

            if strait_analysis["has_tolls"] and not is_confirmed:
                toll_lines = "\n".join([f"• 🌊 **{s['name']}** (تحت کنترل {s['owner_flag']} **{s['owner_name']}**): `{s['toll_amount']:,} $`" for s in strait_analysis["toll_straits"]])
                total_toll = strait_analysis["total_toll"]
                total_transport = 300_000 + total_toll
                payer_label = "فروشنده (پیشنهاددهنده)" if payer == "seller" else f"خریدار ({target_c['name']})"

                text = (
                    f"🌊 **هشدار و تأییدیه عوارض ترانزیت تنگه‌های دریایی**\n"
                    f"━━━━━━━━━━━━━━━━━━\n\n"
                    f"کشور محترم، ناوگان ترابری دریایی این معاهده برای رسیدن به مقصد ({target_c['flag']} **{target_c['name']}**) باید از تنگه‌های دارای **عوارض حق عبور** عبور نماید:\n\n"
                    f"{toll_lines}\n\n"
                    f"💰 **تفکیک هزینه‌های ترانزیت دریایی:**\n"
                    f"• **کرایه پایه ناوگان دریایی:** `۳۰۰,۰۰۰ $`\n"
                    f"• **مجموع عوارض تنگه‌ها:** `{total_toll:,} $`\n"
                    f"• **مجموع کل هزینه ترابری:** **`{total_transport:,} $`**\n"
                    f"• **پرداخت‌کننده هزینه:** **{payer_label}**\n\n"
                    f"⚠️ *مبلغ عوارض هنگام تأیید معاهده مستقیماً به خزانه کشورهای کنترل‌کننده تنگه واریز خواهد شد.*\n\n"
                    f"آیا با صدور و ارسال این معاهده تجاری موافقید؟"
                )
                keyboard = [
                    [InlineKeyboardButton(f"✅ تأیید و ارسال معاهده ({total_transport:,} $)", callback_data=f"dip:trade_finish_confirm:sea:{payer}")],
                    [InlineKeyboardButton("✈️ تغییر به ترابری هوایی (۲,۰۰۰,۰۰۰ $)", callback_data=f"dip:trade_finish:air:{payer}")],
                    [InlineKeyboardButton("🚛 تغییر به ترابری زمینی (۱,۰۰۰,۰۰۰ $)", callback_data=f"dip:trade_finish:land:{payer}")],
                    [InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]
                ]
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
                return

        if mode == "land" and not db.has_land_trade_route(p_key, t_key):
            await query.edit_message_text(
                f"🚛 **ترابری زمینی غیرمجاز است!**\n\n"
                f"هیچ مسیر خشکی پیوسته‌ای (مرز مشترک یا ترانزیت زمینی) بین {country['flag']} **{country['name']}** و {target_c['flag']} **{target_c['name']}** وجود ندارد.\n\n"
                "لطفاً برای این معاهده از ترابری دریایی یا هوایی استفاده فرمایید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✈️ ترابری هوایی (۲,۰۰۰,۰۰۰ دلار)", callback_data=f"dip:trade_finish:air:{payer}")],
                    [InlineKeyboardButton("🚢 ترابری دریایی (۳۰۰,۰۰۰ دلار)", callback_data=f"dip:trade_finish:sea:{payer}")],
                    [InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]
                ]),
                parse_mode="Markdown"
            )
            return

        cost_map = {"air": 2_000_000, "land": 1_000_000, "sea": 300_000}
        mode_labels = {"air": "✈️ ترابری هوایی", "land": "🚛 ترابری زمینی", "sea": "🚢 ترابری دریایی"}
        t_cost = cost_map.get(mode, 300_000)

        contract_id = db.create_trade_contract(
            proposer_id=country["id"],
            recipient_id=draft["target_id"],
            offered_type=draft["offered_type"],
            offered_amount=draft["offered_amount"],
            requested_type=draft["requested_type"],
            requested_amount=draft["requested_amount"],
            transport_payer=payer,
            transport_cost=t_cost,
            transport_mode=mode
        )

        type_map = {"treasury": "دلار", "gold": "شمش طلا", "oil": "بشکه نفت", "grain": "تن غلات", "iron_ore": "تن آهن و فولاد", "microchips": "عدد میکروچیپ", "uranium_ore": "تن کیک زرد", "nuclear_fuel": "کیلوگرم سوخت هسته‌ای"}

        strait_toll_msg = ""
        if mode == "sea" and strait_analysis["has_tolls"]:
            toll_names = "، ".join([f"{s['name']} ({s['toll_amount']:,} $)" for s in strait_analysis["toll_straits"]])
            strait_toll_msg = f"\n• 🌊 **عوارض ترانزیت تنگه‌ها:** {strait_analysis['total_toll']:,} $ ({toll_names})"

        total_trans_cost = t_cost + (strait_analysis["total_toll"] if mode == "sea" else 0)

        recip_msg = (
            f"📜 **پیشنهاد قرارداد تجاری رسمی از طرف {country['flag']} {country['name']}**\n\n"
            f"• **کالای تحویلی به شما:** {draft['offered_amount']:,} {type_map.get(draft['offered_type'])}\n"
            f"• **مابه‌ازای درخواستی از شما:** {draft['requested_amount']:,} {type_map.get(draft['requested_type'])}\n"
            f"• **روش ترابری:** {mode_labels.get(mode, mode)}{strait_toll_msg}\n"
            f"• **پرداخت‌کننده هزینه ترانزیت ({format_money(total_trans_cost)}):** {'فروشنده (پیشنهاددهنده)' if payer == 'seller' else 'خریدار (شما)'}\n\n"
            "آیا با انعقاد و اجرای این معاهده تجاری موافقید؟"
        )
        recip_kb = [
            [InlineKeyboardButton("✅ قبول و امضای قرارداد", callback_data=f"dip:trade_accept:{contract_id}")],
            [InlineKeyboardButton("❌ رد قرارداد", callback_data=f"dip:trade_reject:{contract_id}")],
        ]

        if target_c and target_c.get("player_id"):
            try:
                await context.bot.send_message(chat_id=target_c["player_id"], text=recip_msg, reply_markup=InlineKeyboardMarkup(recip_kb), parse_mode="Markdown")
            except Exception:
                pass

        await query.edit_message_text(
            f"✅ **پیشنهاد قرارداد تجاری با موفقیت به کشور {target_c['name']} ارسال شد.**\n\n💡 *توجه:* دارایی‌های شما تا زمان امضای طرف مقابل در حساب شما باقی می‌ماند و هر زمان می‌توانید از بخش «📋 قراردادهای من» پیشنهاد را لغو فرمایید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
            parse_mode="Markdown"
        )
    elif data.startswith("dip:trade_accept:"):
        contract_id = int(data.split(":")[2])
        succ, msg = db.execute_trade_contract_transaction(contract_id, actor_country_id=country["id"])

        if not succ:
            await query.edit_message_text(f"❌ **اجرای قرارداد ناموفق بود:**\n\n{msg}", parse_mode="Markdown")
            return

        c_data = db.get_trade_contract(contract_id)
        if not c_data:
            await query.edit_message_text("❌ قرارداد یافت نشد.", parse_mode="Markdown")
            return

        p_c = db.get_country_by_id(c_data["proposer_id"])
        r_c = db.get_country_by_id(c_data["recipient_id"])

        if not p_c or not r_c:
            await query.edit_message_text("❌ اطلاعات طرفین قرارداد یافت نشد.", parse_mode="Markdown")
            return

        try:
            db.add_battle_pass_xp(p_c["id"], 200)
            db.add_battle_pass_xp(r_c["id"], 200)
            db.progress_battle_pass_challenge(p_c["id"], "trade", 1)
            db.progress_battle_pass_challenge(r_c["id"], "trade", 1)

            # چالش «صادرات انرژی» طبق توضیحش شامل معاهده هم می‌شود، نه فقط بورس.
            # پیشنهاددهنده کالا را تحویل می‌دهد، پس صادرکننده اوست.
            if c_data["offered_type"] in ("oil", "grain"):
                exported_qty = int(c_data["offered_amount"] or 0)
                if exported_qty > 0:
                    db.progress_battle_pass_challenge(p_c["id"], "export", exported_qty)
        except Exception:
            pass

        if str(msg).startswith("INTERCEPTED:"):
            _, lost_str, deliv_str, eq_name, orig_k = msg.split(":")
            lost_num = int(lost_str)
            deliv_num = int(deliv_str)
            orig_c = db.get_country_by_key(orig_k)

            inter_text = (
                f"🚨 **هشدار امنیتی: ردگیری و توقیف کاروان قاچاق سلاح!**\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"سرویس‌های ضدجاسوسی و گارد مرزی محموله قاچاق اسلحه را ردگیری کردند!\n"
                f"• 📦 تعداد ارسالی: {c_data['offered_amount']:,} واحد {eq_name}\n"
                f"• 💥 تعداد توقیف و منهدم‌شده: **{lost_num:,} واحد**\n"
                f"• 📥 تعداد تحویل‌شده به خریدار: **{deliv_num:,} واحد**\n"
                f"• ⚠️ رضایت عمومی فروشنده ({p_c['name']}) ۳٪ کاهش یافت.\n\n"
                "📢 خبر فوری این حادثه امنیتی در کانال رسمی منتشر گردید."
            )
            await query.edit_message_text(inter_text, parse_mode="Markdown")
            if p_c and p_c.get("player_id"):
                try:
                    await context.bot.send_message(chat_id=p_c["player_id"], text=inter_text, parse_mode="Markdown")
                except Exception:
                    pass
            await news_engine.trigger_smuggling_intercepted_news(context.bot, p_c, r_c, orig_c, eq_name, lost_num)
            return

        elif str(msg).startswith("SMUGGLED_SAFE:"):
            _, deliv_str, eq_name = msg.split(":")
            safe_text = (
                f"🕵️ **انتقال موفقیت‌آمیز محموله قاچاق از بازار سیاه!**\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"تعداد **{int(deliv_str):,} واحد {eq_name}** به صورت کاملاً مخفیانه و بدون اطلاع کشور سازنده وارد زرادخانه کشور شد."
            )
            await query.edit_message_text(safe_text, parse_mode="Markdown")
            if p_c and p_c.get("player_id"):
                try:
                    await context.bot.send_message(chat_id=p_c["player_id"], text=safe_text, parse_mode="Markdown")
                except Exception:
                    pass
            return

        type_map = {"treasury": "دلار", "gold": "شمش طلا", "oil": "بشکه نفت", "grain": "تن غلات", "iron_ore": "تن آهن و فولاد", "microchips": "عدد میکروچیپ", "uranium_ore": "تن کیک زرد", "nuclear_fuel": "کیلوگرم سوخت هسته‌ای"}

        if c_data["offered_type"] == "military_asset":
            off_asset = db.get_asset_by_key(p_c["id"], c_data.get("offered_key"))
            off_name = off_asset["equipment_name"] if off_asset else c_data.get("offered_key", "تجهیز نظامی")
            offered_str = f"{off_name} (تعداد: {c_data['offered_amount']:,} واحد)"
        else:
            offered_str = f"{c_data['offered_amount']:,} {type_map.get(c_data['offered_type'], c_data['offered_type'])}"

        if c_data["requested_type"] == "military_asset":
            req_asset = db.get_asset_by_key(r_c["id"], c_data.get("requested_key"))
            req_name = req_asset["equipment_name"] if req_asset else c_data.get("requested_key", "تجهیز نظامی")
            requested_str = f"{req_name} (تعداد: {c_data['requested_amount']:,} واحد)"
        else:
            requested_str = f"{c_data['requested_amount']:,} {type_map.get(c_data['requested_type'], c_data['requested_type'])}"

        # Send Financial Receipt to both sides
        receipt_text = (
            f"📄 **فیش مالی نهایی قرارداد تجاری بین‌المللی**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• **طرف اول:** {p_c['flag']} {p_c['name']}\n"
            f"• **طرف دوم:** {r_c['flag']} {r_c['name']}\n\n"
            f"• **کالای مبادله‌شده:** {offered_str}\n"
            f"• **مابه‌ازای دریافتی:** {requested_str}\n"
            f"• **وضعیت معاهده:** 🟢 ثبت و امضا شد (تراکنش اتمیک موفق)\n\n"
            "❓ **انتشار در اخبار رسمی:** آیا تمایل دارید خبر ترانزیت این معاهده در کانال رسمی اخبار تلگرام منتشر شود؟"
        )

        keyboard = [
            [
                InlineKeyboardButton("📢 بله، انتشار در کانال اخبار", callback_data=f"dip:pub_news:{contract_id}:yes"),
                InlineKeyboardButton("🔕 خیر، معاهده محرمانه بماند", callback_data=f"dip:pub_news:{contract_id}:no")
            ]
        ]

        await query.edit_message_text(receipt_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        if p_c and p_c.get("player_id"):
            try:
                await context.bot.send_message(chat_id=p_c["player_id"], text=receipt_text, parse_mode="Markdown")
            except Exception:
                pass

    elif data.startswith("dip:lic_app:"):
        contract_id = int(data.split(":")[2])
        ok, msg, c_data = db.approve_export_license(contract_id, country["id"])
        if not ok:
            await query.edit_message_text(f"❌ {msg}", parse_mode="Markdown")
            return

        p_c = db.get_country_by_id(c_data["proposer_id"])
        r_c = db.get_country_by_id(c_data["recipient_id"])
        asset_dict = db.get_asset_by_key(p_c["id"], c_data["offered_key"]) or {"equipment_name": c_data.get("offered_key", "سلاح")}

        await query.edit_message_text(
            f"✅ **مجوز صادرات صادر شد.**\nمعاهده انتقال {asset_dict['equipment_name']} بین {p_c['name']} و {r_c['name']} با تأیید کشور شما معتبر گردید.",
            parse_mode="Markdown"
        )

        # اطلاع به فروشنده
        if p_c and p_c.get("player_id"):
            try:
                await context.bot.send_message(
                    chat_id=p_c["player_id"],
                    text=f"✅ **مجوز صادرات صادر شد!**\nکشور سازنده ({country['flag']} {country['name']}) با انتقال {asset_dict['equipment_name']} موافقت کرد. معاهده اکنون جهت امضا برای کشور خریدار ({r_c['name']}) ارسال شد.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

        # ارسال معاهده به خریدار
        mode_labels = {"air": "✈️ ترابری هوایی", "land": "🚛 ترابری زمینی", "sea": "🚢 ترابری دریایی"}
        recip_msg = (
            f"🎖️ **پیشنهاد معاهده تحویل/فروش تسلیحات نظامی از طرف {p_c['flag']} {p_c['name']}**\n\n"
            f"• **سلاح ارسالی:** {asset_dict['equipment_name']} (✅ دارای مجوز رسمی صادرات از {country['name']})\n"
            f"• **تعداد تحویلی:** {c_data['offered_amount']:,} واحد\n"
            f"• **مبلغ پرداختی درخواستی از شما:** {format_money(c_data['requested_amount'])}\n"
            f"• **روش ترابری:** {mode_labels.get(c_data.get('transport_mode', 'sea'), 'ترابری')}\n"
            f"• **پرداخت‌کننده هزینه ترانزیت ({format_money(c_data.get('transport_cost', 0))}):** {'فروشنده' if c_data.get('transport_payer') == 'seller' else 'خریدار (شما)'}\n\n"
            "آیا با دریافت و امضای این معاهده تسلیحاتی موافقید؟"
        )
        recip_kb = [
            [InlineKeyboardButton("✅ قبول و تحویل تسلیحات", callback_data=f"dip:trade_accept:{contract_id}")],
            [InlineKeyboardButton("❌ رد معاهده نظامی", callback_data=f"dip:trade_reject:{contract_id}")],
        ]
        if r_c and r_c.get("player_id"):
            try:
                await context.bot.send_message(chat_id=r_c["player_id"], text=recip_msg, reply_markup=InlineKeyboardMarkup(recip_kb), parse_mode="Markdown")
            except Exception:
                pass

    elif data.startswith("dip:lic_veto:"):
        contract_id = int(data.split(":")[2])
        ok, msg, c_data = db.veto_export_license(contract_id, country["id"])
        if not ok:
            await query.edit_message_text(f"❌ {msg}", parse_mode="Markdown")
            return

        p_c = db.get_country_by_id(c_data["proposer_id"])
        r_c = db.get_country_by_id(c_data["recipient_id"])
        asset_dict = db.get_asset_by_key(p_c["id"], c_data["offered_key"]) or {"equipment_name": c_data.get("offered_key", "سلاح")}

        await query.edit_message_text(
            f"🚫 **معاهده تسلیحاتی وتو شد.**\nشما به عنوان کشور سازنده اصلی از انتقال {asset_dict['equipment_name']} به {r_c['name']} ممانعت فرمودید.",
            parse_mode="Markdown"
        )

        if p_c and p_c.get("player_id"):
            try:
                await context.bot.send_message(
                    chat_id=p_c["player_id"],
                    text=f"🚫 **معاهده تسلیحاتی وتو شد!**\nکشور سازنده ({country['flag']} {country['name']}) با صدور مجوز صادرات مخالفت کرد و معاهده انتقال {asset_dict['equipment_name']} به {r_c['name']} لغو گردید.",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

    elif data.startswith("dip:pub_news:"):
        parts = data.split(":")
        contract_id = int(parts[2])
        choice = parts[3] if len(parts) > 3 else "no"

        c_data = db.get_trade_contract(contract_id)
        if not c_data:
            await query.answer("قرارداد یافت نشد.", show_alert=True)
            return
        if country["id"] not in (c_data["proposer_id"], c_data["recipient_id"]):
            await query.answer("فقط طرفین این قرارداد می‌توانند درباره انتشار خبر تصمیم بگیرند.", show_alert=True)
            return
        if choice not in {"yes", "no"}:
            await query.answer("انتخاب انتشار خبر نامعتبر است.", show_alert=True)
            return

        if choice == "yes":
            p_c = db.get_country_by_id(c_data["proposer_id"])
            r_c = db.get_country_by_id(c_data["recipient_id"])
            t_mode = c_data.get("transport_mode", "sea") or "sea"
            try:
                await news_engine.trigger_trade_news(context.bot, p_c, r_c, transport_mode=t_mode)
                await query.edit_message_text(
                    f"{query.message.text}\n\n📢 **خبر ترانزیت این معاهده با موفقیت در کانال رسمی اخبار منتشر شد.**",
                    parse_mode="Markdown"
                )
            except Exception as e:
                await query.edit_message_text(f"{query.message.text}\n\n❌ خطا در انتشار خبر: {e}", parse_mode="Markdown")
        else:
            await query.edit_message_text(
                f"{query.message.text}\n\n🔕 **این معاهده کاملاً محرمانه باقی ماند و هیچ خبری در کانال رسمی منتشر نگردید.**",
                parse_mode="Markdown"
            )

    elif data.startswith("dip:trade_reject:"):
        contract_id = int(data.split(":")[2])
        rejected, reject_msg = db.reject_trade_contract(contract_id, country["id"])
        if not rejected:
            await query.answer(f"❌ {reject_msg}", show_alert=True)
            return

        c_data = db.get_trade_contract(contract_id)
        if c_data:
            p_c = db.get_country_by_id(c_data["proposer_id"])
            if p_c and p_c.get("player_id"):
                try:
                    await context.bot.send_message(chat_id=p_c["player_id"], text=f"❌ **پیشنهاد قرارداد تجاری شما توسط کشور {country['name']} رد شد.**", parse_mode="Markdown")
                except Exception:
                    pass
        await query.edit_message_text("❌ قرارداد تجاری رد شد.", parse_mode="Markdown")

    elif data == "dip:aid_start":
        await dip_aid_start(query, context, country)

    elif data.startswith("dip:aid_target:"):
        target_id = int(data.split(":")[2])
        context.user_data["aid_draft"] = {"target_id": target_id}
        target_c = db.get_country_by_id(target_id)

        text = f"🕊️ **ارسال کمک‌های انسان‌دوستانه به {target_c['flag']} {target_c['name']}**\n\nنوع کمک را انتخاب کنید:"
        keyboard = [
            [InlineKeyboardButton("💰 کمک مالی (دلار)", callback_data="dip:aid_type:treasury"), InlineKeyboardButton("🪙 طلا", callback_data="dip:aid_type:gold")],
            [InlineKeyboardButton("🛢️ کمک سوخت (نفت)", callback_data="dip:aid_type:oil"), InlineKeyboardButton("🌾 کمک غذایی (غلات)", callback_data="dip:aid_type:grain")],
            [InlineKeyboardButton("⛏️ آهن و فولاد", callback_data="dip:aid_type:iron_ore"), InlineKeyboardButton("💻 کمک فناوری و تراشه", callback_data="dip:aid_type:microchips")],
            [InlineKeyboardButton("☢️ کیک زرد", callback_data="dip:aid_type:uranium_ore"), InlineKeyboardButton("🧪 سوخت هسته‌ای", callback_data="dip:aid_type:nuclear_fuel")],
            [InlineKeyboardButton("🔙 انصراف", callback_data="dip:menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("dip:aid_type:"):
        res_type = data.split(":")[2]
        if "aid_draft" not in context.user_data:
            context.user_data["aid_draft"] = {}
        context.user_data["aid_draft"]["resource_type"] = res_type
        context.user_data["diplomacy_input"] = {"type": "aid_amount"}

        type_labels = {"treasury": "دلار", "gold": "شمش طلا", "oil": "بشکه نفت", "grain": "تن غلات", "iron_ore": "تن آهن و فولاد", "microchips": "عدد میکروچیپ", "uranium_ore": "تن کیک زرد", "nuclear_fuel": "کیلوگرم سوخت هسته‌ای"}
        
        sea_limits = getattr(config, "TRANSPORT_CAPACITY_LIMITS", {}).get("sea", {}).get("limits", {})
        aid_max = 20_000_000 if res_type == "treasury" else sea_limits.get(res_type, 100_000)

        col_map = {"treasury": "treasury", "gold": "gold", "oil": "oil_reserves", "grain": "grain", "iron_ore": "iron_ore", "microchips": "microchips", "uranium_ore": "uranium_ore", "nuclear_fuel": "nuclear_fuel"}
        user_avail = country.get(col_map.get(res_type, "treasury"), 0) or 0

        await query.edit_message_text(
            f"🕊️ **ارسال کمک اهدایی ({type_labels.get(res_type, res_type)})**\n\n"
            f"• موجودی کشور شما: `{user_avail:,} {type_labels.get(res_type, res_type)}`\n"
            f"• 📦 حداکثر سقف مجاز دریایی: `{aid_max:,} {type_labels.get(res_type, res_type)}`\n\n"
            f"لطفاً میزان مورد نظر را به عدد وارد فرمایید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]]),
            parse_mode="Markdown"
        )

    elif data.startswith("dip:aid_finish:") or data.startswith("dip:aid_finish_confirm:"):
        is_confirmed = data.startswith("dip:aid_finish_confirm:")
        mode = data.split(":")[2]
        draft = context.user_data.get("aid_draft")
        if not draft or "target_id" not in draft or "amount" not in draft:
            await query.edit_message_text("❌ اطلاعات ارسال کمک منقضی شده است.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:menu")]]), parse_mode="Markdown")
            return

        target_id = draft["target_id"]
        res_type = draft["resource_type"]
        amt = draft["amount"]
        target_c = db.get_country_by_id(target_id)
        if not target_c:
            await query.edit_message_text("❌ کشور مقصد یافت نشد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:menu")]]), parse_mode="Markdown")
            return

        my_key = country.get("country_key")
        t_key = target_c.get("country_key")
        strait_analysis = db.get_trade_route_strait_analysis(my_key, t_key)

        if mode == "sea":
            if strait_analysis["is_blocked"]:
                blocked_details = "\n".join([f"• ⛔ **{s['name']}** (تحت مسدودسازی کشور {s['owner_flag']} **{s['owner_name']}**)" for s in strait_analysis["blocked_straits"]])
                await query.edit_message_text(
                    f"⚓ **ترابری دریایی مسدود است!**\n\n"
                    f"مسیر ترانزیت دریایی بین دو کشور به دلیل مسدود بودن آبراه‌های استراتژیک قطع می‌باشد:\n\n"
                    f"{blocked_details}\n\n"
                    f"💡 لطفاً برای ارسال این کمک از ترابری هوایی یا زمینی استفاده فرمایید.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("✈️ ترابری هوایی (۲,۰۰۰,۰۰۰ دلار)", callback_data="dip:aid_finish:air")],
                        [InlineKeyboardButton("🚛 ترابری زمینی (۱,۰۰۰,۰۰۰ دلار)", callback_data="dip:aid_finish:land")],
                        [InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]
                    ]),
                    parse_mode="Markdown"
                )
                return

            if strait_analysis["has_tolls"] and not is_confirmed:
                toll_lines = "\n".join([f"• 🌊 **{s['name']}** (تحت کنترل {s['owner_flag']} **{s['owner_name']}**): `{s['toll_amount']:,} $`" for s in strait_analysis["toll_straits"]])
                total_toll = strait_analysis["total_toll"]
                total_transport = 300_000 + total_toll

                text = (
                    f"🌊 **هشدار و تأییدیه عوارض ترانزیت تنگه‌های دریایی (کمک خارجی)**\n"
                    f"━━━━━━━━━━━━━━━━━━\n\n"
                    f"کشور محترم، ناوگان حامل محموله انسان‌دوستانه برای رسیدن به مقصد ({target_c['flag']} **{target_c['name']}**) باید از تنگه‌های دارای **عوارض حق عبور** عبور نماید:\n\n"
                    f"{toll_lines}\n\n"
                    f"💰 **تفکیک هزینه‌های ترانزیت دریایی:**\n"
                    f"• **کرایه پایه ناوگان دریایی:** `۳۰۰,۰۰۰ $`\n"
                    f"• **مجموع عوارض تنگه‌ها:** `{total_toll:,} $`\n"
                    f"• **مجموع کل هزینه ترابری از خزانه شما:** **`{total_transport:,} $`**\n\n"
                    f"⚠️ *مبلغ عوارض مستقیماً به خزانه کشورهای کنترل‌کننده تنگه واریز خواهد شد.*\n\n"
                    f"آیا با ارسال کمک با پرداخت عوارض موافقید؟"
                )
                keyboard = [
                    [InlineKeyboardButton(f"✅ تأیید و ارسال کمک ({total_transport:,} $)", callback_data="dip:aid_finish_confirm:sea")],
                    [InlineKeyboardButton("✈️ تغییر به ترابری هوایی (۲,۰۰۰,۰۰۰ $)", callback_data="dip:aid_finish:air")],
                    [InlineKeyboardButton("🚛 تغییر به ترابری زمینی (۱,۰۰۰,۰۰۰ $)", callback_data="dip:aid_finish:land")],
                    [InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]
                ]
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
                return

        if mode == "land" and not db.has_land_trade_route(my_key, t_key):
            await query.edit_message_text(
                f"🚛 **ترابری زمینی غیرمجاز است!**\n\n"
                f"هیچ مسیر خشکی پیوسته‌ای (مرز مشترک یا ترانزیت زمینی) بین {country['flag']} **{country['name']}** و {target_c['flag']} **{target_c['name']}** وجود ندارد.\n\n"
                "لطفاً برای ارسال این کمک از ترابری دریایی یا هوایی استفاده فرمایید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✈️ ترابری هوایی (۲,۰۰۰,۰۰۰ دلار)", callback_data="dip:aid_finish:air")],
                    [InlineKeyboardButton("🚢 ترابری دریایی (۳۰۰,۰۰۰ دلار)", callback_data="dip:aid_finish:sea")],
                    [InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]
                ]),
                parse_mode="Markdown"
            )
            return

        succ, msg_res = db.execute_foreign_aid_transaction(country["id"], target_id, res_type, amt, transport_mode=mode)
        if not succ:
            await query.edit_message_text(f"❌ **ارسال کمک ناموفق بود:**\n\n{msg_res}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:menu")]]), parse_mode="Markdown")
            return

        type_labels = {"treasury": "دلار", "gold": "شمش طلا", "oil": "بشکه نفت", "grain": "تن غلات", "iron_ore": "تن آهن و فولاد", "microchips": "عدد میکروچیپ", "uranium_ore": "تن کیک زرد", "nuclear_fuel": "کیلوگرم سوخت هسته‌ای"}
        mode_labels = {"sea": "🚢 ترابری دریایی", "land": "🚛 ترابری زمینی (۱M $)", "air": "✈️ ترابری هوایی (۲M $)"}
        sea_label = f"🚢 ترابری دریایی (۳۰۰k $ + {strait_analysis['total_toll']:,} $ عوارض)" if (mode == "sea" and strait_analysis["has_tolls"]) else "🚢 ترابری دریایی (۳۰۰k $)"

        # Trigger Anti-cheat Alert
        if amt >= 5_000_000 or res_type in ["gold", "oil"]:
            await check_and_alert_anti_cheat(context, country, target_c, f"{amt:,} {type_labels.get(res_type, res_type)}", f"کمک خارجی اهدایی ({mode})")

        aid_receipt = (
            f"📄 **فیش اهدای کمک‌های خارجی و انسان‌دوستانه**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• **اهداکننده:** {country['flag']} {country['name']}\n"
            f"• **دریافت‌کننده:** {target_c['flag']} {target_c['name']}\n"
            f"• **نوع و مقدار کمک:** {amt:,} {type_labels.get(res_type, res_type)}\n"
            f"• **روش ترابری ناوگان:** {sea_label if mode == 'sea' else mode_labels.get(mode, mode)}\n\n"
            "✅ محموله با موفقیت بارگیری و تحویل کشور مقصد گردید."
        )

        await query.edit_message_text(aid_receipt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]), parse_mode="Markdown")

        if target_c and target_c.get("player_id"):
            try:
                await context.bot.send_message(chat_id=target_c["player_id"], text=aid_receipt, parse_mode="Markdown")
            except Exception:
                pass

    elif data == "dip:rel_start":
        await dip_relations_menu(query, context, country)

    elif data.startswith("dip:rel_act:"):
        _, _, act, target_id_str = data.split(":")
        target_id = int(target_id_str)
        target_c = db.get_country_by_id(target_id)

        if act == "propose_alliance":
            # Send alliance offer
            offer_msg = (
                f"🤝 **پیشنهاد رسمی معاهده اتحاد استراتژیک از طرف {country['flag']} {country['name']}**\n\n"
                "آیا با تشکیل پیمان اتحاد نظامی و سیاسی موافقید؟"
            )
            kb = [
                [InlineKeyboardButton("✅ پذیرش و امضای پیمان اتحاد", callback_data=f"dip:alliance_accept:{country['id']}")],
                [InlineKeyboardButton("❌ رد پیشنهاد اتحاد", callback_data=f"dip:alliance_reject:{country['id']}")],
            ]
            if target_c and target_c.get("player_id"):
                try:
                    await context.bot.send_message(chat_id=target_c["player_id"], text=offer_msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
                except Exception:
                    pass
            await query.edit_message_text(
                f"✅ **پیشنهاد اتحاد با موفقیت برای کشور {target_c['name']} ارسال شد.**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:rel_start")]]),
                parse_mode="Markdown"
            )

        elif act == "break":
            db.set_diplomatic_relation(country["id"], target_id, "normal", 0)
            if target_c and target_c.get("player_id"):
                try:
                    await context.bot.send_message(chat_id=target_c["player_id"], text=f"💔 **کشور {country['name']} پیمان اتحاد را لغو نمود.**", parse_mode="Markdown")
                except Exception:
                    pass
            await query.edit_message_text("💔 **پیمان اتحاد لغو گردید.**", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:rel_start")]]))

        elif act == "sanction":
            db.set_diplomatic_relation(country["id"], target_id, "sanctioned", country["id"])
            if target_c and target_c.get("player_id"):
                try:
                    await context.bot.send_message(chat_id=target_c["player_id"], text=f"🚫 **کشور {country['name']} کشور شما را زیر تحریم‌های یک‌طرفه قرار داد.**", parse_mode="Markdown")
                except Exception:
                    pass
            await query.edit_message_text("🚫 **تحریم یک‌طرفه علیه کشور مخاطب اعمال شد.**", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:rel_start")]]))

        elif act == "unsanction":
            db.set_diplomatic_relation(country["id"], target_id, "normal", 0)
            if target_c and target_c.get("player_id"):
                try:
                    await context.bot.send_message(chat_id=target_c["player_id"], text=f"🔓 **کشور {country['name']} تحریم‌های یک‌طرفه علیه شما را لغو کرد.**", parse_mode="Markdown")
                except Exception:
                    pass
            await query.edit_message_text("🔓 **تحریم یک‌طرفه لغو گردید.**", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:rel_start")]]))

    elif data.startswith("dip:alliance_accept:"):
        proposer_id = int(data.split(":")[2])
        db.set_diplomatic_relation(country["id"], proposer_id, "allied", 0)
        p_c = db.get_country_by_id(proposer_id)
        if p_c and p_c.get("player_id"):
            try:
                await context.bot.send_message(chat_id=p_c["player_id"], text=f"🤝 **کشور {country['name']} پیشنهاد اتحاد شما را پذیرفت! هم‌اکنون دو کشور متحد رسمی هستند.**", parse_mode="Markdown")
            except Exception:
                pass
        await query.edit_message_text("🤝 **پیمان اتحاد رسمی به امضا رسید.**", parse_mode="Markdown")

    elif data.startswith("dip:alliance_reject:"):
        proposer_id = int(data.split(":")[2])
        p_c = db.get_country_by_id(proposer_id)
        if p_c and p_c.get("player_id"):
            try:
                await context.bot.send_message(chat_id=p_c["player_id"], text=f"❌ **کشور {country['name']} پیشنهاد اتحاد شما را رد کرد.**", parse_mode="Markdown")
            except Exception:
                pass
        await query.edit_message_text("❌ **پیشنهاد اتحاد رد شد.**", parse_mode="Markdown")


# ==================== Text Input Handler برای دیپلماسی ====================

async def diplomacy_text_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        return

    dip_input = context.user_data.get("diplomacy_input")
    if not dip_input:
        return

    text = (update.message.text or update.message.caption or "").strip()
    if not text:
        await update.message.reply_text("لطفاً متن پیام را بفرست.")
        return
    input_type = dip_input.get("type")
    del context.user_data["diplomacy_input"]

    clean_num = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١۲٣٤٥٦٧٨٩", "01234567890123456789")).replace(",", "").replace("_", "")

    if input_type == "dip_search_country":
        action_type = dip_input.get("action_type", "msg")
        user_query = text.strip()
        clean_q = _clean_persian_str(user_query)

        all_countries = db.get_all_countries()
        matches = []
        for c in all_countries:
            if c["id"] == country["id"]:
                continue
            c_name = c.get("name", "")
            c_key = c.get("country_key", "")
            if clean_q in _clean_persian_str(c_name) or clean_q in _clean_persian_str(c_key):
                matches.append(c)

        if not matches:
            text_res = f"❌ **کشوری با عنوان «{user_query}» یافت نشد.**"
            kb_res = [
                [InlineKeyboardButton("🔁 جستجوی مجدد", callback_data=f"dip:search_start:{action_type}")],
                [InlineKeyboardButton("🔙 لیست قاره‌ها", callback_data=f"dip:back_continents:{action_type}")],
            ]
            await update.message.reply_text(text_res, reply_markup=InlineKeyboardMarkup(kb_res), parse_mode="Markdown")
            return

        if action_type == "rel":
            # نمایش وضعیت روابط برای نتایج جستجو
            lines = [f"🔎 نتایج جستجو «{user_query}» — **وضعیت روابط**\n━━━━━━━━━━━━━━━━━━\n"]
            buttons = []
            for c in matches:
                rel = db.get_diplomatic_relation(country["id"], c["id"])
                st = rel.get("status", "normal")
                s_by = rel.get("sanctioned_by", 0)
                if st == "allied":
                    status_text = "🟢 متحد"
                    act_btn = InlineKeyboardButton(f"💔 لغو اتحاد {c['name']}", callback_data=f"dip:rel_act:break:{c['id']}")
                elif st == "sanctioned":
                    status_text = "🔴 تحریم"
                    if s_by == country["id"]:
                        act_btn = InlineKeyboardButton(f"🔓 لغو تحریم {c['name']}", callback_data=f"dip:rel_act:unsanction:{c['id']}")
                    else:
                        act_btn = InlineKeyboardButton(f"🚫 تحریم متقابل {c['name']}", callback_data=f"dip:rel_act:sanction:{c['id']}")
                else:
                    status_text = "⚪ عادی"
                    act_btn = InlineKeyboardButton(f"🤝 اتحاد {c['name']}", callback_data=f"dip:rel_act:propose_alliance:{c['id']}")
                lines.append(f"{c['flag']} {c['name']} — {status_text}")
                buttons.append([InlineKeyboardButton(f"{c['flag']} {c['name']} ({status_text})", callback_data="ignore")])
                btn_row = [act_btn]
                if st != "sanctioned" and st != "allied":
                    btn_row.append(InlineKeyboardButton(f"🚫 تحریم {c['name']}", callback_data=f"dip:rel_act:sanction:{c['id']}"))
                buttons.append(btn_row)
            buttons.append([
                InlineKeyboardButton("🔁 جستجوی مجدد", callback_data=f"dip:search_start:{action_type}"),
                InlineKeyboardButton("🔙 لیست قاره‌ها", callback_data=f"dip:back_continents:{action_type}")
            ])
            await update.message.reply_text(
                "\n".join(lines),
                reply_markup=InlineKeyboardMarkup(buttons),
                parse_mode="Markdown"
            )
            return

        cb_prefix_map = {
            "msg": "dip:msg_target:",
            "trade": "dip:trade_target:",
            "mil": "dip:mil_target:",
            "aid": "dip:aid_target:",
            "blockade": "dip:blockade_target:"
        }
        prefix = cb_prefix_map.get(action_type, "dip:target:")

        buttons = []
        row = []
        for c in matches:
            is_sanc = db.are_sanctioned(country["id"], c["id"])
            btn_label = f"🚫 {c['name']} (تحریم)" if is_sanc and action_type in ("trade", "mil", "aid") else f"{c['flag']} {c['name']}"
            row.append(InlineKeyboardButton(btn_label, callback_data=f"{prefix}{c['id']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)

        buttons.append([
            InlineKeyboardButton("🔁 جستجوی مجدد", callback_data=f"dip:search_start:{action_type}"),
            InlineKeyboardButton("🔙 لیست قاره‌ها", callback_data=f"dip:back_continents:{action_type}")
        ])

        await update.message.reply_text(
            f"🔎 **نتایج جستجو برای «{user_query}» ({len(matches)} کشور):**\n━━━━━━━━━━━━━━━━━━\nروی کشور مورد نظر کلیک کنید:",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )
        return

    if input_type == "send_msg":
        target_id = dip_input["target_id"]
        target_c = db.get_country_by_id(target_id)

        memo = (
            f"✉️ **یادداشت دیپلماتیک رسمی از طرف {country['flag']} {country['name']}**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f'"{text}"\n\n'
            "━━━━━━━━━━━━━━━━━━"
        )
        reply_kb = [[InlineKeyboardButton("✉️ پاسخ به پیام دیپلماتیک", callback_data=f"dip:msg_target:{country['id']}")]]

        if target_c and target_c.get("player_id"):
            try:
                await context.bot.send_message(chat_id=target_c["player_id"], text=memo, reply_markup=InlineKeyboardMarkup(reply_kb), parse_mode="Markdown")
                await update.message.reply_text(f"✅ یادداشت دیپلماتیک رسمی با موفقیت به کشور {target_c['name']} تحویل گردید.", parse_mode="Markdown")
            except Exception as e:
                await update.message.reply_text(f"❌ ارسال پیام ناموفق بود: {e}", parse_mode="Markdown")

    elif input_type == "trade_off_amount":
        try:
            amt = int(clean_num)
            if amt <= 0: raise ValueError
            context.user_data["trade_draft"]["offered_amount"] = amt
            
            # Ask for requested resource type
            msg = "📜 **قرارداد تجاری**\n\n**مرحله ۲:** کالایی که در مابه‌ازای معامله از طرف مقابل می‌خواهید را انتخاب کنید:"
            kb = [
                [InlineKeyboardButton("💰 پول (خزانه)", callback_data="dip:trade_req:treasury"), InlineKeyboardButton("🪙 طلا", callback_data="dip:trade_req:gold")],
                [InlineKeyboardButton("🛢️ نفت", callback_data="dip:trade_req:oil"), InlineKeyboardButton("🌾 غلات", callback_data="dip:trade_req:grain")],
                [InlineKeyboardButton("⛏️ آهن و فولاد", callback_data="dip:trade_req:iron_ore"), InlineKeyboardButton("💻 میکروچیپ", callback_data="dip:trade_req:microchips")],
                [InlineKeyboardButton("☢️ کیک زرد اورانیوم", callback_data="dip:trade_req:uranium_ore"), InlineKeyboardButton("🧪 سوخت هسته‌ای", callback_data="dip:trade_req:nuclear_fuel")],
                [InlineKeyboardButton("🔙 انصراف", callback_data="dip:menu")]
            ]
            await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("❌ عدد وارد شده نامعتبر بود. عملیات لغو شد.", parse_mode="Markdown")

    elif input_type == "trade_req_amount":
        try:
            amt = int(clean_num)
            if amt <= 0: raise ValueError
            context.user_data["trade_draft"]["requested_amount"] = amt

            # Ask for transport payer
            msg = "📜 **قرارداد تجاری**\n\n**مرحله ۳:** پرداخت‌کننده هزینه ترانزیت و حمل‌ونقل را مشخص کنید:"
            kb = [
                [InlineKeyboardButton("فروشنده (پیشنهاددهنده)", callback_data="dip:trade_payer:seller")],
                [InlineKeyboardButton("خریدار (کشور مخاطب)", callback_data="dip:trade_payer:buyer")],
            ]
            await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("❌ عدد وارد شده نامعتبر بود. عملیات لغو شد.", parse_mode="Markdown")

    elif input_type == "mil_asset_qty":
        try:
            qty = int(clean_num)
            max_qty = context.user_data.get("mil_draft", {}).get("max_amount", 1)
            if qty <= 0 or qty > max_qty:
                await update.message.reply_text(f"❌ تعداد وارد شده باید بین ۱ تا {max_qty:,} باشد.", parse_mode="Markdown")
                return

            context.user_data["mil_draft"]["offered_amount"] = qty
            context.user_data["diplomacy_input"] = {"type": "mil_asset_price"}

            price_buttons = [
                [InlineKeyboardButton("🎁 اهدای رایگان (۰ $)", callback_data="dip:mil_price:0")],
                [InlineKeyboardButton("💰 ۱,۰۰۰,۰۰۰ $", callback_data="dip:mil_price:1000000"), InlineKeyboardButton("💰 ۵,۰۰۰,۰۰۰ $", callback_data="dip:mil_price:5000000")],
                [InlineKeyboardButton("💰 ۱۰,۰۰۰,۰۰۰ $", callback_data="dip:mil_price:10000000"), InlineKeyboardButton("💰 ۵۰,۰۰۰,۰۰۰ $", callback_data="dip:mil_price:50000000")],
                [InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]
            ]

            await update.message.reply_text(
                f"🎖️ **انتقال تجهیز نظامی (تعداد: {qty:,} واحد)**\n\nلطفاً **قیمت درخواستی برای فروش (به دلار)** را انتخاب کرده یا عدد مد نظر را تایپ فرمایید:",
                reply_markup=InlineKeyboardMarkup(price_buttons),
                parse_mode="Markdown"
            )
        except ValueError:
            await update.message.reply_text("❌ عدد وارد شده نامعتبر بود.", parse_mode="Markdown")

    elif input_type == "mil_asset_price":
        try:
            price = int(clean_num)
            if price < 0:
                raise ValueError
            context.user_data["mil_draft"]["requested_amount"] = price

            msg = "🎖️ **معاهده نظامی**\n\nپرداخت‌کننده هزینه ترانزیت و حمل‌ونقل نظامی را مشخص بفرمایید:"
            kb = [
                [InlineKeyboardButton("فروشنده (پیشنهاددهنده)", callback_data="dip:mil_payer:seller")],
                [InlineKeyboardButton("خریدار (کشور مخاطب)", callback_data="dip:mil_payer:buyer")],
            ]
            await update.message.reply_text(msg, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("❌ عدد وارد شده نامعتبر بود.", parse_mode="Markdown")

    elif input_type == "strait_custom_toll":
        try:
            toll_val = int(clean_num)
            if toll_val < 10_000 or toll_val > 1_000_000:
                await update.message.reply_text(
                    "⛔ **مبلغ نامعتبر:** عوارض ترانزیت باید بین ۱۰,۰۰۰ دلار تا سقف ۱,۰۰۰,۰۰۰ دلار باشد.",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                    parse_mode="Markdown"
                )
                return

            c_key = country.get("country_key")
            strait_info = db.get_strait_info_by_country_key(c_key)
            if not strait_info:
                await update.message.reply_text("❌ شما تسلطی بر تنگه‌های استراتژیک ندارید.", parse_mode="Markdown")
                return

            s_key = strait_info["strait_key"]
            s_name = strait_info["name"]

            db.set_strait_status(s_key, "toll", toll_val)
            await news_engine.trigger_strait_news(context.bot, country, s_name, "toll", format_money(toll_val))
            await update.message.reply_text(
                f"🟡 **عوارض ترانزیت ({format_money(toll_val)}) برای عبور از {s_name} با موفقیت برقرار گردید.**\n\n📢 خبر رسمی در کانال منتشر شد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
        except ValueError:
            await update.message.reply_text("❌ عدد وارد شده نامعتبر بود. عملیات لغو شد.", parse_mode="Markdown")

    elif input_type == "aid_amount":
        try:
            amt = int(clean_num)
            if amt <= 0: raise ValueError
            draft = context.user_data.get("aid_draft", {})
            target_id = draft["target_id"]
            res_type = draft["resource_type"]
            draft["amount"] = amt

            target_c = db.get_country_by_id(target_id)
            type_labels = {"treasury": "دلار", "gold": "شمش طلا", "oil": "بشکه نفت", "grain": "تن غلات", "iron_ore": "تن آهن و فولاد", "microchips": "عدد میکروچیپ", "uranium_ore": "تن کیک زرد", "nuclear_fuel": "کیلوگرم سوخت هسته‌ای"}

            my_key = country.get("country_key")
            t_key = target_c.get("country_key") if target_c else ""
            has_sea = db.has_open_sea_access(my_key) and db.has_open_sea_access(t_key)
            strait_analysis = db.get_trade_route_strait_analysis(my_key, t_key)

            kb = []
            if has_sea:
                if strait_analysis["is_blocked"]:
                    blocked_str = "، ".join([s["name"] for s in strait_analysis["blocked_straits"]])
                    kb.append([InlineKeyboardButton(f"⛔ ترابری دریایی (مسدود: {blocked_str})", callback_data="dip:aid_finish:sea")])
                elif strait_analysis["has_tolls"]:
                    total_sea = 300_000 + strait_analysis["total_toll"]
                    kb.append([InlineKeyboardButton(f"🚢 ترابری دریایی ({total_sea:,} $ با عوارض)", callback_data="dip:aid_finish:sea")])
                else:
                    kb.append([InlineKeyboardButton("🚢 ترابری دریایی (۳۰۰,۰۰۰ دلار)", callback_data="dip:aid_finish:sea")])

            has_land = db.has_land_trade_route(my_key, t_key)
            if has_land:
                kb.append([InlineKeyboardButton("🚛 ترابری زمینی (۱,۰۰۰,۰۰۰ دلار)", callback_data="dip:aid_finish:land")])
            kb.append([InlineKeyboardButton("✈️ ترابری هوایی (۲,۰۰۰,۰۰۰ دلار)", callback_data="dip:aid_finish:air")])
            kb.append([InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")])

            text = (
                f"🕊️ **ارسال کمک‌های انسان‌دوستانه — انتخاب ناوگان و روش ترابری**\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"• **کشور مقصد:** {target_c['flag']} {target_c['name']}\n"
                f"• **محموله ارسالی:** {amt:,} {type_labels.get(res_type, res_type)}\n\n"
                "لطفاً روش ترابری و لجستیک انتقال این کمک را انتخاب فرمایید:\n"
                "*(هزینه ترانزیت و عوارض احتمالی از خزانه کشور اهداکننده کسر می‌شود)*"
                + ("" if has_land else "\n🚫 **ترابری زمینی:** غیرفعال — مسیر خشکی پیوسته‌ای بین دو کشور وجود ندارد.")
            )

            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("❌ عدد وارد شده نامعتبر بود. عملیات لغو شد.", parse_mode="Markdown")