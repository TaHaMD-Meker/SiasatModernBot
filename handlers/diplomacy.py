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
        "• **کمک خارجی:** ارسال کمک‌های انسان‌دوستانه بدون مابه‌ازا\n"
        "• **روابط و تحریم‌ها:** مدیریت اتحادها و تحریم‌های یک‌طرفه"
    )

    keyboard = [
        [InlineKeyboardButton("✉️ ارسال یادداشت دیپلماتیک", callback_data="dip:msg_start")],
        [InlineKeyboardButton("📜 پیشنهاد قرارداد تجاری", callback_data="dip:trade_start")],
        [InlineKeyboardButton("🎖️ انتقال/فروش تسلیحات نظامی", callback_data="dip:mil_start")],
        [InlineKeyboardButton("🕊️ کمک خارجی و انسان‌دوستانه", callback_data="dip:aid_start")],
        [InlineKeyboardButton("🤝 اتحادها و تحریم‌ها", callback_data="dip:rel_start")],
    ]

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== 1. یادداشت دیپلماتیک ====================

async def dip_message_start(query, context, country):
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
    countries = db.get_all_countries()
    other_countries = [c for c in countries if c["id"] != country["id"]]

    if not other_countries:
        await query.edit_message_text("❌ هیچ کشور دیگری در بازی برای معامله وجود ندارد.", parse_mode="Markdown")
        return

    text = "📜 **پیشنهاد قرارداد تجاری رسمی**\n\nلطفاً طرف دوم قرارداد (کشور مخاطب) را انتخاب کنید:"
    keyboard = []
    row = []
    for c in other_countries:
        # Check if sanctioned
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

        context.user_data["mil_draft"]["equipment_key"] = eq_key
        context.user_data["mil_draft"]["equipment_name"] = asset["equipment_name"]
        context.user_data["mil_draft"]["max_amount"] = asset["amount"]
        context.user_data["diplomacy_input"] = {"type": "mil_asset_qty"}

        await query.edit_message_text(
            f"🎖️ **انتقال {asset['equipment_name']}**\n📦 موجودی فعلی کشور شما: {asset['amount']:,} واحد\n\nلطفاً **تعداد ارسالی** را به عدد وارد فرمایید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]], parse_mode="Markdown")
        )

    elif data.startswith("dip:mil_payer:"):
        payer = data.split(":")[2]
        draft = context.user_data.get("mil_draft", {})
        draft["transport_payer"] = payer
        draft["transport_cost"] = 500_000

        target_c = db.get_country_by_id(draft["target_id"])

        contract_id = db.create_trade_contract(
            proposer_id=country["id"],
            recipient_id=draft["target_id"],
            offered_type="military_asset",
            offered_amount=draft["offered_amount"],
            requested_type="treasury",
            requested_amount=draft["requested_amount"],
            transport_payer=payer,
            transport_cost=500_000,
            offered_key=draft["equipment_key"]
        )

        recip_msg = (
            f"🎖️ **پیشنهاد معاهده تحویل/فروش تسلیحات نظامی از طرف {country['flag']} {country['name']}**\n\n"
            f"• **سلاح ارسالی:** {draft['equipment_name']}\n"
            f"• **تعداد تحویلی:** {draft['offered_amount']:,} واحد\n"
            f"• **مبلغ پرداختی درخواستی از شما:** {format_money(draft['requested_amount'])}\n"
            f"• **پرداخت‌کننده هزینه ترانزیت (۵۰۰ هزار دلار):** {'فروشنده' if payer == 'seller' else 'خریدار (شما)'}\n\n"
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
            f"✅ **پیشنهاد معاهده نظامی با موفقیت به کشور {target_c['name']} ارسال شد.**\nپس از تایید و امضای طرف مقابل، تجهیزات به کشور مقصد منتقل می‌گردد.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]], parse_mode="Markdown")
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
        # Choose offered resource type
        text = f"📜 **قرارداد تجاری با کشور {db.get_country_by_id(target_id)['name']}**\n\n**مرحله ۱:** نوع کالای ارسالی (پیشنهادی شما) را انتخاب کنید:"
        keyboard = [
            [InlineKeyboardButton("💰 پول (خزانه)", callback_data="dip:trade_off:treasury"), InlineKeyboardButton("🪙 طلا", callback_data="dip:trade_off:gold")],
            [InlineKeyboardButton("🛢️ نفت", callback_data="dip:trade_off:oil"), InlineKeyboardButton("🌾 غلات", callback_data="dip:trade_off:grain")],
            [InlineKeyboardButton("🔙 انصراف", callback_data="dip:menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("dip:trade_off:"):
        off_type = data.split(":")[2]
        context.user_data["trade_draft"]["offered_type"] = off_type
        context.user_data["diplomacy_input"] = {"type": "trade_off_amount"}
        
        type_labels = {"treasury": "دلار", "gold": "شمش طلا", "oil": "بشکه نفت", "grain": "تن غلات"}
        await query.edit_message_text(
            f"💰 **مقدار پیشنهادی ({type_labels.get(off_type, off_type)})** را به عدد وارد فرمایید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]], parse_mode="Markdown")
        )

    elif data.startswith("dip:trade_req:"):
        req_type = data.split(":")[2]
        context.user_data["trade_draft"]["requested_type"] = req_type
        context.user_data["diplomacy_input"] = {"type": "trade_req_amount"}
        
        type_labels = {"treasury": "دلار", "gold": "شمش طلا", "oil": "بشکه نفت", "grain": "تن غلات"}
        await query.edit_message_text(
            f"🎯 **مقدار درخواستی مابه‌ازا ({type_labels.get(req_type, req_type)})** را به عدد وارد فرمایید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]], parse_mode="Markdown")
        )

    elif data.startswith("dip:trade_payer:"):
        payer = data.split(":")[2] # 'seller' or 'buyer'
        draft = context.user_data.get("trade_draft", {})
        draft["transport_payer"] = payer
        draft["transport_cost"] = 500_000 # Standard flat transport fee

        target_c = db.get_country_by_id(draft["target_id"])

        # Create pending contract
        contract_id = db.create_trade_contract(
            proposer_id=country["id"],
            recipient_id=draft["target_id"],
            offered_type=draft["offered_type"],
            offered_amount=draft["offered_amount"],
            requested_type=draft["requested_type"],
            requested_amount=draft["requested_amount"],
            transport_payer=payer,
            transport_cost=500_000
        )

        type_map = {"treasury": "دلار", "gold": "شمش طلا", "oil": "بشکه نفت", "grain": "تن غلات"}

        # Send contract offer to recipient player
        recip_msg = (
            f"📜 **پیشنهاد قرارداد تجاری رسمی از طرف {country['flag']} {country['name']}**\n\n"
            f"• **کالای تحویلی به شما:** {draft['offered_amount']:,} {type_map.get(draft['offered_type'])}\n"
            f"• **مابه‌ازای درخواستی از شما:** {draft['requested_amount']:,} {type_map.get(draft['requested_type'])}\n"
            f"• **پرداخت‌کننده هزینه ترانزیت (۵۰۰ هزار دلار):** {'فروشنده (پیشنهاددهنده)' if payer == 'seller' else 'خریدار (شما)'}\n\n"
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
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]], parse_mode="Markdown")
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
            msg = "📜 **قرارداد تجاری**\n\n**مرحله ۳:** پرداخت‌کننده هزینه ترانزیت و حمل‌ونقل (۵۰۰ هزار دلار) را مشخص کنید:"
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
            max_qty = context.user_data["mil_draft"]["max_amount"]
            if qty <= 0 or qty > max_qty:
                await update.message.reply_text(f"❌ تعداد وارد شده باید بین ۱ تا {max_qty:,} باشد.", parse_mode="Markdown")
                return

            context.user_data["mil_draft"]["offered_amount"] = qty
            context.user_data["diplomacy_input"] = {"type": "mil_asset_price"}

            await update.message.reply_text(
                "💰 **قیمت درخواستی برای فروش (به دلار)** را وارد فرمایید:\n**(در صورت اهدا/انتقال رایگان عدد ۰ را وارد نمایید)**",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]], parse_mode="Markdown")
            )
        except ValueError:
            await update.message.reply_text("❌ عدد وارد شده نامعتبر بود.", parse_mode="Markdown")

    elif input_type == "mil_asset_price":
        try:
            price = int(clean_num)
            if price < 0:
                raise ValueError
            context.user_data["mil_draft"]["requested_amount"] = price

            msg = "🎖️ **معاهده نظامی**\n\nپرداخت‌کننده هزینه ترانزیت و حمل‌ونقل نظامی (۵۰۰ هزار دلار) را مشخص کنید:"
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