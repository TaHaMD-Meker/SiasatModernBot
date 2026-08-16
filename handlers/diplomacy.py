# -**- coding: utf-8 -**-
"""
ماژول کامل سیستم دیپلماسی، پیام‌رسانی دیپلماتیک، قراردادهای تجاری، اتحاد، تحریم و کمک‌های خارجی
(Diplomacy, Trade Contracts, Alliances, Sanctions & Foreign Aid System)
"""

import datetime
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
        if update.message:
            await update.message.reply_text("هنوز کشوری نساختی! برای شروع /start رو بزن.", parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.answer("هنوز کشوری نساختی!", show_alert=True)
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
        [InlineKeyboardButton("✉️ ارسال یادداشت دیپلماتیک", callback_data="dip:msg_start")],
        [InlineKeyboardButton("📜 پیشنهاد قرارداد تجاری", callback_data="dip:trade_start")],
        [InlineKeyboardButton("🎖️ انتقال/فروش تسلیحات نظامی", callback_data="dip:mil_start")],
        [InlineKeyboardButton("⚓ محاصره دریایی بین‌المللی", callback_data="dip:blockade_start")],
        [InlineKeyboardButton("🌊 مدیریت و انسداد تنگه‌ها", callback_data="dip:strait_menu")],
        [InlineKeyboardButton("🕊️ کمک خارجی و انسان‌دوستانه", callback_data="dip:aid_start")],
        [InlineKeyboardButton("🤝 اتحادها و تحریم‌ها", callback_data="dip:rel_start")],
    ]

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== 1. یادداشت دیپلماتیک ====================

async def dip_message_start(query, context, country):
    if db.get_setting("diplomatic_notes_locked") == "1":
        await query.edit_message_text("🔒 **ارسال پیام‌های دیپلماتیک موقتاً قفل است.**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:menu")]]), parse_mode="Markdown")
        return

    countries = db.get_all_countries()
    other_countries = [c for c in countries if c["id"] != country["id"]]

    if not other_countries:
        await query.edit_message_text("❌ هیچ کشور دیگری در بازی ثبت نشده است.", parse_mode="Markdown")
        return

    text = "✉️ **ارسال یادداشت دیپلماتیک رسمی**\n\nلطفاً کشور مقصد را انتخاب فرمایید:"
    keyboard = []
    row = []
    for c in other_countries:
        btn = InlineKeyboardButton(f"{c['flag']} {c['name']}", callback_data=f"dip:msg_target:{c['id']}")
        row.append(btn)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی دیپلماسی", callback_data="dip:menu")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== 2. قراردادهای تجاری ====================

async def dip_trade_start(query, context, country):
    if db.get_setting("trade_contracts_locked") == "1":
        await query.edit_message_text("🔒 **انعقاد قراردادهای تجاری موقتاً قفل است.**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:menu")]]), parse_mode="Markdown")
        return

    countries = db.get_all_countries()
    other_countries = [c for c in countries if c["id"] != country["id"]]

    if not other_countries:
        await query.edit_message_text("❌ هیچ کشور دیگری در بازی برای معامله وجود ندارد.", parse_mode="Markdown")
        return

    text = "📜 **پیشنهاد قرارداد تجاری رسمی**\n\nلطفاً طرف دوم قرارداد (کشور مخاطب) را انتخاب کنید:"
    keyboard = []
    row = []
    for c in other_countries:
        if db.are_sanctioned(country["id"], c["id"]):
            btn_label = f"🚫 {c['name']} (تحریم)"
        else:
            btn_label = f"{c['flag']} {c['name']}"
        btn = InlineKeyboardButton(btn_label, callback_data=f"dip:trade_target:{c['id']}")
        row.append(btn)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی دیپلماسی", callback_data="dip:menu")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== 2.5. انتقال و فروش تسلیحات نظامی ====================

async def dip_military_start(query, context, country):
    countries = db.get_all_countries()
    other_countries = [c for c in countries if c["id"] != country["id"]]

    if not other_countries:
        await query.edit_message_text("❌ هیچ کشور دیگری در بازی وجود ندارد.", parse_mode="Markdown")
        return

    text = "🎖️ **انتقال / فروش تسلیحات نظامی**\n\nلطفاً کشور دریافت‌کننده تسلیحات را انتخاب بفرمایید:"
    keyboard = []
    row = []
    for c in other_countries:
        if db.are_sanctioned(country["id"], c["id"]):
            btn_label = f"🚫 {c['name']} (تحریم)"
        else:
            btn_label = f"{c['flag']} {c['name']}"
        btn = InlineKeyboardButton(btn_label, callback_data=f"dip:mil_target:{c['id']}")
        row.append(btn)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی دیپلماسی", callback_data="dip:menu")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== 2.7. محاصره دریایی بین‌المللی ====================

async def dip_blockade_start(query, context, country):
    if db.get_setting("naval_blockade_locked") == "1":
        await query.edit_message_text("🔒 **اجرای محاصره دریایی موقتاً قفل است.**", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:menu")]]), parse_mode="Markdown")
        return

    assets = db.get_country_assets(country["id"], category="Navy")
    naval_count = sum(a["amount"] for a in assets)

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

    if naval_count < 1 and not im_blockaded and not my_blockades:
        await query.edit_message_text(
            "⚓ **عدم توانایی عملیاتی:** کشور شما در حال حاضر فاقد یگان‌های ناوشکن، ناوچه یا ناوهای رزمی در دیتابیس برای اجرای محاصره دریایی است.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:menu")]]),
            parse_mode="Markdown"
        )
        return

    countries = db.get_all_countries()
    other_countries = [c for c in countries if c["id"] != country["id"]]

    text = f"⚓ **عملیات محاصره دریایی بین‌المللی — ناوگان {country['flag']} {country['name']}**\n\nلطفاً کشور هدف جهت مسدودسازی بنادر و خطوط دریایی را انتخاب کنید:"

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

async def dip_aid_start(query, context, country):
    countries = db.get_all_countries()
    other_countries = [c for c in countries if c["id"] != country["id"]]

    text = "🕊️ **ارسال کمک‌های خارجی و انسان‌دوستانه**\n\nلطفاً کشور دریافت‌کننده کمک را انتخاب کنید:"
    keyboard = []
    row = []
    for c in other_countries:
        btn = InlineKeyboardButton(f"{c['flag']} {c['name']}", callback_data=f"dip:aid_target:{c['id']}")
        row.append(btn)
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی دیپلماسی", callback_data="dip:menu")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== 4. مدیریت روابط و تحریم‌ها ====================

async def dip_relations_menu(query, context, country):
    countries = db.get_all_countries()
    other_countries = [c for c in countries if c["id"] != country["id"]]

    lines = [f"🤝 **مدیریت روابط دیپلماتیک و تحریم‌های کشور {country['flag']} {country['name']}**\n"]
    keyboard = []

    for c in other_countries:
        rel = db.get_diplomatic_relation(country["id"], c["id"])
        st = rel.get("status", "normal")
        s_by = rel.get("sanctioned_by", 0)

        if st == "allied":
            status_text = "🟢 **متحد رسمی**"
            act_btn = InlineKeyboardButton("💔 لغو اتحاد", callback_data=f"dip:rel_act:break:{c['id']}")
        elif st == "sanctioned":
            if s_by == country["id"]:
                status_text = "🔴 **تحریم‌شده توسط شما**"
                act_btn = InlineKeyboardButton("🔓 لغو تحریم", callback_data=f"dip:rel_act:unsanction:{c['id']}")
            else:
                status_text = "🔴 **شما را تحریم کرده**"
                act_btn = InlineKeyboardButton("🚫 تحریم متقابل", callback_data=f"dip:rel_act:sanction:{c['id']}")
        else:
            status_text = "⚪ **روابط عادی**"
            act_btn = InlineKeyboardButton("🤝 پیشنهاد اتحاد", callback_data=f"dip:rel_act:propose_alliance:{c['id']}")

        sanc_btn = InlineKeyboardButton("🚫 تحریم", callback_data=f"dip:rel_act:sanction:{c['id']}") if st != "sanctioned" else None

        row = [InlineKeyboardButton(f"{c['flag']} {c['name']} ({status_text})", callback_data="ignore")]
        btn_row = [act_btn]
        if sanc_btn and st != "allied":
            btn_row.append(sanc_btn)

        keyboard.append(row)
        keyboard.append(btn_row)

    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی دیپلماسی", callback_data="dip:menu")])

    await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


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
                "• **تنگه باب‌المندب:** تحت تسلط 🇾🇪 حزب‌الله و جبهه مقاومت\n"
                "• **تنگه بسفر (مونترو):** تحت تسلط 🇹🇷 ترکیه\n"
                "• **تنگه مالاکا:** تحت تسلط 🇮🇳 هند\n"
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

        if act == "block":
            db.set_strait_status(s_key, "blocked")
            await news_engine.trigger_strait_news(context.bot, country, s_name, "block")
            await query.edit_message_text(
                f"🔴 **{s_name} به طور کامل مسدود گردید.**\n\n📢 خبر فوری انسداد آبراه در کانال اصلی بازی منتشر شد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
        elif act == "toll":
            toll_val = 1_000_000
            db.set_strait_status(s_key, "toll", toll_val)
            await news_engine.trigger_strait_news(context.bot, country, s_name, "toll", format_money(toll_val))
            await query.edit_message_text(
                f"🟡 **عوارض ترانزیت ({format_money(toll_val)}) برای عبور از {s_name} برقرار گردید.**\n\n📢 خبر رسمی در کانال منتشر گردید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
        elif act == "open":
            db.set_strait_status(s_key, "open")
            await news_engine.trigger_strait_news(context.bot, country, s_name, "open")
            await query.edit_message_text(
                f"🟢 **{s_name} بازگشایی شد و ترانزیت آزاد برقرار گردید.**\n\n📢 خبر رسمی در کانال منتشر گردید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )

    elif data == "dip:break_blk":
        msl_assets = db.get_country_assets(country["id"], category="Missiles")
        navy_assets = db.get_country_assets(country["id"], category="Navy")

        has_antiship = any(
            "antiship" in a["equipment_key"] or "cruise" in a["equipment_key"] or "harpoon" in a["equipment_key"] or "exocet" in a["equipment_key"] or "noor" in a["equipment_key"] or "qader" in a["equipment_key"] or "yakhont" in a["equipment_key"]
            for a in msl_assets if a["amount"] > 0
        )
        has_navy = any(n["amount"] > 0 for n in navy_assets)

        if not has_antiship and not has_navy:
            await query.edit_message_text(
                "💥 **شکستن محاصره ناموفق بود!**\n\nکشور شما فاقد موشک‌های کروز ضدکشتی یا یگان‌های دریایی آماده به رزم در دیتابیس برای عقب راندن ناوگان محاصره‌کننده است.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:blockade_start")]]),
                parse_mode="Markdown"
            )
            return

        active_blks = db.get_active_blockades_for_country(country["id"])
        blockader_c = None
        for b in active_blks:
            if b["target_id"] == country["id"]:
                blockader_c = db.get_country_by_id(b["blockader_id"])
                break

        db.break_naval_blockade(country["id"])
        new_app = min(100, country.get("approval_rating", 80) + 10)
        db.update_country_field(country["id"], "approval_rating", new_app)

        if blockader_c:
            await news_engine.trigger_unblockade_news(context.bot, blockader_c, country, is_broken=True)
        else:
            await news_engine.post_breaking_news(
                context.bot,
                f"شکستن محاصره دریایی بنادر {country['name']}",
                f"نیروهای مدافع کشور {country['flag']} {country['name']} با شلیک موشک‌های ضدکشتی و یگان‌های دریایی، محاصره دریایی تحمیل‌شده را با موفقیت درهم شکستند.",
                "نبرد و اقتدار دریایی"
            )

        await query.edit_message_text(
            f"💥 **پیروزی رزمی! محاصره دریایی بنادر کشور {country['name']} با موفقیت شکسته شد.**\n\n📈 شاخص رضایت عمومی به میزان ۱۰٪ افزایش یافت.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
            parse_mode="Markdown"
        )

    elif data.startswith("dip:lift_blk:"):
        target_id = int(data.split(":")[2])
        target_c = db.get_country_by_id(target_id)
        db.lift_naval_blockade(country["id"], target_id)

        if target_c:
            await news_engine.trigger_unblockade_news(context.bot, country, target_c, is_broken=False)

        await query.edit_message_text(
            f"🔓 **محاصره دریایی علیه کشور {target_c['name'] if target_c else 'هدف'} با موفقیت لغو گردید.**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
            parse_mode="Markdown"
        )

    elif data.startswith("dip:blk_target:"):
        target_id = int(data.split(":")[2])
        target_c = db.get_country_by_id(target_id)

        if not target_c:
            await query.edit_message_text("❌ کشور هدف پیدا نشد.", parse_mode="Markdown")
            return

        blockader_power = db.calculate_naval_power(country["id"])
        target_power = db.calculate_naval_power(target_id)
        required_power = int(target_power * 1.2)

        if blockader_power < required_power:
            await query.edit_message_text(
                f"⚓ **عملیات محاصره دریایی ناموفق بود!**\n━━━━━━━━━━━━━━━━━━\n\n"
                f"• **قدرت رزمی ناوگان شما ({country['name']}):** {blockader_power:,} امتیاز\n"
                f"• **قدرت رزمی ناوگان هدف ({target_c['name']}):** {target_power:,} امتیاز\n"
                f"• **حداقل قدرت لازم جهت محاصره:** {required_power:,} امتیاز\n\n"
                f"⚠️ **توضیحات:** ناوگان دریایی برتر کشور {target_c['name']} اجازه مسدودسازی بنادر خود را نداد!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
            return

        db.create_naval_blockade(country["id"], target_id)

        new_app = max(0, target_c.get("approval_rating", 80) - 15)
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
            f"⚓ **عملیات محاصره دریایی علیه کشور {target_c['flag']} {target_c['name']} با موفقیت اجرا شد.**\n\n"
            f"• **قدرت ناوگان شما:** {blockader_power:,} امتیاز\n"
            f"• **قدرت ناوگان هدف:** {target_power:,} امتیاز\n\n"
            "📢 خبر فوری این حادثه ژئوپلیتیک در کانال رسمی منتشر گردید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
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

        context.user_data["mil_draft"]["equipment_key"] = eq_key
        context.user_data["mil_draft"]["equipment_name"] = asset["equipment_name"]
        context.user_data["mil_draft"]["max_amount"] = asset["amount"]
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

        await query.edit_message_text(
            f"🎖️ **انتقال {asset['equipment_name']}**\n📦 موجودی فعلی کشور شما: {asset['amount']:,} واحد\n\n"
            "لطفاً **تعداد ارسالی** را از دکمه‌های زیر انتخاب کرده یا عدد مد نظر خود را تایپ فرمایید:",
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

        text = (
            "🌐 **انتخاب روش ترابری و ترانزیت محموله نظامی**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً روش ارسال تجهیزات را انتخاب بفرمایید:\n\n"
            "• **✈️ ترابری هوایی:** ۲,۰۰۰,۰۰۰ دلار (سریع‌ترین / فعال در زمان محاصره)\n"
            "• **🚛 ترابری زمینی:** ۱,۰۰۰,۰۰۰ دلار (ترانزیت زمینی / فعال)\n"
            "• **🚢 ترابری دریایی:** ۳۰۰,۰۰۰ دلار (ارزان‌ترین / مسدود در زمان محاصره دریایی)"
        )
        keyboard = [
            [InlineKeyboardButton("✈️ ترابری هوایی (۲,۰۰۰,۰۰۰ دلار)", callback_data=f"dip:mil_finish:air:{payer}")],
            [InlineKeyboardButton("🚛 ترابری زمینی (۱,۰۰۰,۰۰۰ دلار)", callback_data=f"dip:mil_finish:land:{payer}")],
            [InlineKeyboardButton("🚢 ترابری دریایی (۳۰۰,۰۰۰ دلار)", callback_data=f"dip:mil_finish:sea:{payer}")],
            [InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("dip:mil_finish:"):
        _, _, mode, payer = data.split(":")
        draft = context.user_data.get("mil_draft", {})
        target_c = db.get_country_by_id(draft.get("target_id", 0))

        if not target_c:
            await query.edit_message_text(
                "⚠️ **نشست دیپلماتیک منقضی شده است.** لطفاً مجدداً اقدام فرمایید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
            return

        if mode == "sea" and (db.is_country_blockaded(country["id"]) or db.is_country_blockaded(draft["target_id"])):
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

        cost_map = {"air": 2_000_000, "land": 1_000_000, "sea": 300_000}
        mode_labels = {"air": "✈️ ترابری هوایی", "land": "🚛 ترابری زمینی", "sea": "🚢 ترابری دریایی"}
        t_cost = cost_map.get(mode, 300_000)

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
            transport_mode=mode
        )

        recip_msg = (
            f"🎖️ **پیشنهاد معاهده تحویل/فروش تسلیحات نظامی از طرف {country['flag']} {country['name']}**\n\n"
            f"• **سلاح ارسالی:** {draft['equipment_name']}\n"
            f"• **تعداد تحویلی:** {draft['offered_amount']:,} واحد\n"
            f"• **مبلغ پرداختی درخواستی از شما:** {format_money(draft['requested_amount'])}\n"
            f"• **روش ترابری:** {mode_labels.get(mode, mode)}\n"
            f"• **پرداخت‌کننده هزینه ترانزیت ({format_money(t_cost)}):** {'فروشنده' if payer == 'seller' else 'خریدار (شما)'}\n\n"
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
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]], parse_mode="Markdown")
        )

    elif data == "dip:trade_start":
        await dip_trade_start(query, context, country)

    elif data.startswith("dip:trade_target:"):
        target_id = int(data.split(":")[2])
        if db.are_sanctioned(country["id"], target_id):
            await query.edit_message_text(
                "🚫 **امکان معامله وجود ندارد:** یکی از دو کشور دیگری را تحریم کرده است.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:trade_start")]], parse_mode="Markdown")
            )
            return

        context.user_data["trade_draft"] = {"target_id": target_id}
        text = f"📜 **قرارداد تجاری با کشور {db.get_country_by_id(target_id)['name']}**\n\n**مرحله ۱:** نوع کالای ارسالی (پیشنهادی شما) را انتخاب کنید:"
        keyboard = [
            [InlineKeyboardButton("💰 پول (خزانه)", callback_data="dip:trade_off:treasury"), InlineKeyboardButton("🪙 طلا", callback_data="dip:trade_off:gold")],
            [InlineKeyboardButton("🛢️ نفت", callback_data="dip:trade_off:oil"), InlineKeyboardButton("🌾 غلات", callback_data="dip:trade_off:grain")],
            [InlineKeyboardButton("🔙 انصراف", callback_data="dip:menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("dip:trade_off:"):
        off_type = data.split(":")[2]
        if "trade_draft" not in context.user_data:
            context.user_data["trade_draft"] = {}
        context.user_data["trade_draft"]["offered_type"] = off_type
        context.user_data["diplomacy_input"] = {"type": "trade_off_amount"}
        
        type_labels = {"treasury": "دلار", "gold": "شمش طلا", "oil": "بشکه نفت", "grain": "تن غلات"}
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
        
        type_labels = {"treasury": "دلار", "gold": "شمش طلا", "oil": "بشکه نفت", "grain": "تن غلات"}
        await query.edit_message_text(
            f"🎯 **مقدار درخواستی مابه‌ازا ({type_labels.get(req_type, req_type)})** را به عدد وارد فرمایید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]]),
            parse_mode="Markdown"
        )

    elif data.startswith("dip:trade_payer:"):
        payer = data.split(":")[2] # 'seller' or 'buyer'
        draft = context.user_data.get("trade_draft", {})
        draft["transport_payer"] = payer

        text = (
            "🌐 **انتخاب روش ترابری و ترانزیت محموله تجاری**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً روش ارسال کالاهای تجاری را انتخاب بفرمایید:\n\n"
            "• **✈️ ترابری هوایی:** ۲,۰۰۰,۰۰۰ دلار (سریع‌ترین / فعال در زمان محاصره)\n"
            "• **🚛 ترابری زمینی:** ۱,۰۰۰,۰۰۰ دلار (ترانزیت زمینی / فعال)\n"
            "• **🚢 ترابری دریایی:** ۳۰۰,۰۰۰ دلار (ارزان‌ترین / مسدود در زمان محاصره دریایی)"
        )
        keyboard = [
            [InlineKeyboardButton("✈️ ترابری هوایی (۲,۰۰۰,۰۰۰ دلار)", callback_data=f"dip:trade_finish:air:{payer}")],
            [InlineKeyboardButton("🚛 ترابری زمینی (۱,۰۰۰,۰۰۰ دلار)", callback_data=f"dip:trade_finish:land:{payer}")],
            [InlineKeyboardButton("🚢 ترابری دریایی (۳۰۰,۰۰۰ دلار)", callback_data=f"dip:trade_finish:sea:{payer}")],
            [InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("dip:trade_finish:"):
        _, _, mode, payer = data.split(":")
        draft = context.user_data.get("trade_draft", {})
        target_c = db.get_country_by_id(draft.get("target_id", 0))

        if not target_c:
            await query.edit_message_text(
                "⚠️ **نشست دیپلماتیک منقضی شده است.** لطفاً مجدداً اقدام فرمایید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
                parse_mode="Markdown"
            )
            return

        if mode == "sea" and (db.is_country_blockaded(country["id"]) or db.is_country_blockaded(draft["target_id"])):
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

        type_map = {"treasury": "دلار", "gold": "شمش طلا", "oil": "بشکه نفت", "grain": "تن غلات"}

        recip_msg = (
            f"📜 **پیشنهاد قرارداد تجاری رسمی از طرف {country['flag']} {country['name']}**\n\n"
            f"• **کالای تحویلی به شما:** {draft['offered_amount']:,} {type_map.get(draft['offered_type'])}\n"
            f"• **مابه‌ازای درخواستی از شما:** {draft['requested_amount']:,} {type_map.get(draft['requested_type'])}\n"
            f"• **روش ترابری:** {mode_labels.get(mode, mode)}\n"
            f"• **پرداخت‌کننده هزینه ترانزیت ({format_money(t_cost)}):** {'فروشنده (پیشنهاددهنده)' if payer == 'seller' else 'خریدار (شما)'}\n\n"
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
            f"✅ **پیشنهاد قرارداد تجاری با موفقیت به کشور {target_c['name']} ارسال شد.**\nپس از تایید طرف مقابل، معاهده به طور خودکار اجرا می‌گردد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]]),
            parse_mode="Markdown"
        )
    elif data.startswith("dip:trade_accept:"):
        contract_id = int(data.split(":")[2])
        succ, msg = db.execute_trade_contract_transaction(contract_id)

        if not succ:
            await query.edit_message_text(f"❌ **اجرای قرارداد ناموفق بود:**\n\n{msg}", parse_mode="Markdown")
            return

        c_data = db.get_trade_contract(contract_id)
        p_c = db.get_country_by_id(c_data["proposer_id"])
        r_c = db.get_country_by_id(c_data["recipient_id"])

        type_map = {"treasury": "دلار", "gold": "شمش طلا", "oil": "بشکه نفت", "grain": "تن غلات"}

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
            f"• **وضعیت معاهده:** 🟢 ثبت و امضا شد (تراکنش اتمیک موفق)"
        )

        try:
            t_mode = c_data.get("transport_mode", "sea") or "sea"
            await news_engine.trigger_trade_news(context.bot, p_c, r_c, transport_mode=t_mode)
        except Exception:
            pass

        await query.edit_message_text(receipt_text, parse_mode="Markdown")
        if p_c and p_c.get("player_id"):
            try:
                await context.bot.send_message(chat_id=p_c["player_id"], text=receipt_text, parse_mode="Markdown")
            except Exception:
                pass

    elif data.startswith("dip:trade_reject:"):
        contract_id = int(data.split(":")[2])
        db.update_contract_status(contract_id, "rejected")
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
            [InlineKeyboardButton("🔙 انصراف", callback_data="dip:menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("dip:aid_type:"):
        res_type = data.split(":")[2]
        if "aid_draft" not in context.user_data:
            context.user_data["aid_draft"] = {}
        context.user_data["aid_draft"]["resource_type"] = res_type
        context.user_data["diplomacy_input"] = {"type": "aid_amount"}

        type_labels = {"treasury": "دلار", "gold": "شمش طلا", "oil": "بشکه نفت", "grain": "تن غلات"}
        await query.edit_message_text(
            f"🕊️ **میزان کمک اهدایی ({type_labels.get(res_type, res_type)})** را وارد فرمایید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]], parse_mode="Markdown")
        )

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
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:rel_start")]], parse_mode="Markdown")
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

    text = update.message.text.strip()
    input_type = dip_input.get("type")
    del context.user_data["diplomacy_input"]

    clean_num = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١۲٣٤٥٦٧٨٩", "01234567890123456789")).replace(",", "").replace("_", "")

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

    elif input_type == "aid_amount":
        try:
            amt = int(clean_num)
            if amt <= 0: raise ValueError
            draft = context.user_data.get("aid_draft", {})
            target_id = draft["target_id"]
            res_type = draft["resource_type"]

            succ, msg_res = db.execute_foreign_aid_transaction(country["id"], target_id, res_type, amt)

            if not succ:
                await update.message.reply_text(f"❌ **ارسال کمک ناموفق بود:**\n\n{msg_res}", parse_mode="Markdown")
                return

            target_c = db.get_country_by_id(target_id)
            type_labels = {"treasury": "دلار", "gold": "شمش طلا", "oil": "بشکه نفت", "grain": "تن غلات"}

            # Trigger Anti-cheat Alert
            if amt >= 5_000_000 or res_type in ["gold", "oil"]:
                await check_and_alert_anti_cheat(context, country, target_c, f"{amt:,} {type_labels.get(res_type, res_type)}", "کمک خارجی اهدایی")

            # Send receipt to recipient
            aid_receipt = (
                f"📄 **فیش اهدای کمک‌های خارجی و انسان‌دوستانه**\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"• **اهداکننده:** {country['flag']} {country['name']}\n"
                f"• **دریافت‌کننده:** {target_c['flag']} {target_c['name']}\n"
                f"• **نوع و مقدار کمک:** {amt:,} {type_labels.get(res_type, res_type)}\n\n"
                "تراکنش مالی و انتقال منابع با موفقیت ثبت شد."
            )

            await update.message.reply_text(aid_receipt, parse_mode="Markdown")

            if target_c and target_c.get("player_id"):
                try:
                    await context.bot.send_message(chat_id=target_c["player_id"], text=aid_receipt, parse_mode="Markdown")
                except Exception:
                    pass

        except ValueError:
            await update.message.reply_text("❌ عدد وارد شده نامعتبر بود. عملیات لغو شد.", parse_mode="Markdown")