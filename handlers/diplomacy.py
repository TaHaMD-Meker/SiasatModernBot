# -*- coding: utf-8 -*-
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


async def require_country(update: Update):
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        if update.message:
            await update.message.reply_text("هنوز کشوری نساختی! برای شروع /start رو بزن.")
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
        "• **کمک خارجی:** ارسال کمک‌های انسان‌دوستانه بدون مابه‌ازا\n"
        "• **روابط و تحریم‌ها:** مدیریت اتحادها و تحریم‌های یک‌طرفه"
    )

    keyboard = [
        [InlineKeyboardButton("✉️ ارسال یادداشت دیپلماتیک", callback_data="dip:msg_start")],
        [InlineKeyboardButton("📜 پیشنهاد قرارداد تجاری", callback_data="dip:trade_start")],
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
        await query.edit_message_text("❌ هیچ کشور دیگری در بازی ثبت نشده است.")
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
        await query.edit_message_text("❌ هیچ کشور دیگری در بازی برای معامله وجود ندارد.")
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


# ==================== 3. کمک خارجی ====================

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

    elif data.startswith("dip:msg_target:"):
        target_id = int(data.split(":")[2])
        target_c = db.get_country_by_id(target_id)
        context.user_data["diplomacy_input"] = {"type": "send_msg", "target_id": target_id}
        await query.edit_message_text(
            f"✉️ **ارسال یادداشت دیپلماتیک به {target_c['flag']} {target_c['name']}**\n\n"
            "لطفاً متن یادداشت رسمی خود را ارسال فرمایید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]])
        )

    elif data == "dip:trade_start":
        await dip_trade_start(query, context, country)

    elif data.startswith("dip:trade_target:"):
        target_id = int(data.split(":")[2])
        if db.are_sanctioned(country["id"], target_id):
            await query.edit_message_text(
                "🚫 **امکان معامله وجود ندارد:** یکی از دو کشور دیگری را تحریم کرده است.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:trade_start")]])
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
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]])
        )

    elif data.startswith("dip:trade_req:"):
        req_type = data.split(":")[2]
        context.user_data["trade_draft"]["requested_type"] = req_type
        context.user_data["diplomacy_input"] = {"type": "trade_req_amount"}
        
        type_labels = {"treasury": "دلار", "gold": "شمش طلا", "oil": "بشکه نفت", "grain": "تن غلات"}
        await query.edit_message_text(
            f"🎯 **مقدار درخواستی مابه‌ازا ({type_labels.get(req_type, req_type)})** را به عدد وارد فرمایید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]])
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
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به دیپلماسی", callback_data="dip:menu")]])
        )

    elif data.startswith("dip:trade_accept:"):
        contract_id = int(data.split(":")[2])
        succ, msg = db.execute_trade_contract_transaction(contract_id)

        if not succ:
            await query.edit_message_text(f"❌ **اجرای قرارداد ناموفق بود:**\n\n{msg}")
            return

        c_data = db.get_trade_contract(contract_id)
        p_c = db.get_country_by_id(c_data["proposer_id"])
        r_c = db.get_country_by_id(c_data["recipient_id"])

        type_map = {"treasury": "دلار", "gold": "شمش طلا", "oil": "بشکه نفت", "grain": "تن غلات"}

        # Send Financial Receipt to both sides
        receipt_text = (
            f"📄 **فیش مالی نهایی قرارداد تجاری بین‌المللی**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• **طرف اول:** {p_c['flag']} {p_c['name']}\n"
            f"• **طرف دوم:** {r_c['flag']} {r_c['name']}\n\n"
            f"• **کالای مبادله‌شده:** {c_data['offered_amount']:,} {type_map.get(c_data['offered_type'])}\n"
            f"• **مابه‌ازای دریافتی:** {c_data['requested_amount']:,} {type_map.get(c_data['requested_type'])}\n"
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
                    await context.bot.send_message(chat_id=p_c["player_id"], text=f"❌ **پیشنهاد قرارداد تجاری شما توسط کشور {country['name']} رد شد.**")
                except Exception:
                    pass
        await query.edit_message_text("❌ قرارداد تجاری رد شد.")

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
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="dip:menu")]])
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
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:rel_start")]])
            )

        elif act == "break":
            db.set_diplomatic_relation(country["id"], target_id, "normal", 0)
            if target_c and target_c.get("player_id"):
                try:
                    await context.bot.send_message(chat_id=target_c["player_id"], text=f"💔 **کشور {country['name']} پیمان اتحاد را لغو نمود.**")
                except Exception:
                    pass
            await query.edit_message_text("💔 پیمان اتحاد لغو گردید.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:rel_start")]]))

        elif act == "sanction":
            db.set_diplomatic_relation(country["id"], target_id, "sanctioned", country["id"])
            if target_c and target_c.get("player_id"):
                try:
                    await context.bot.send_message(chat_id=target_c["player_id"], text=f"🚫 **کشور {country['name']} کشور شما را زیر تحریم‌های یک‌طرفه قرار داد.**")
                except Exception:
                    pass
            await query.edit_message_text("🚫 تحریم یک‌طرفه علیه کشور مخاطب اعمال شد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:rel_start")]]))

        elif act == "unsanction":
            db.set_diplomatic_relation(country["id"], target_id, "normal", 0)
            if target_c and target_c.get("player_id"):
                try:
                    await context.bot.send_message(chat_id=target_c["player_id"], text=f"🔓 **کشور {country['name']} تحریم‌های یک‌طرفه علیه شما را لغو کرد.**")
                except Exception:
                    pass
            await query.edit_message_text("🔓 تحریم یک‌طرفه لغو گردید.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="dip:rel_start")]]))

    elif data.startswith("dip:alliance_accept:"):
        proposer_id = int(data.split(":")[2])
        db.set_diplomatic_relation(country["id"], proposer_id, "allied", 0)
        p_c = db.get_country_by_id(proposer_id)
        if p_c and p_c.get("player_id"):
            try:
                await context.bot.send_message(chat_id=p_c["player_id"], text=f"🤝 **کشور {country['name']} پیشنهاد اتحاد شما را پذیرفت! هم‌اکنون دو کشور متحد رسمی هستند.**")
            except Exception:
                pass
        await query.edit_message_text("🤝 **پیمان اتحاد رسمی به امضا رسید.**")

    elif data.startswith("dip:alliance_reject:"):
        proposer_id = int(data.split(":")[2])
        p_c = db.get_country_by_id(proposer_id)
        if p_c and p_c.get("player_id"):
            try:
                await context.bot.send_message(chat_id=p_c["player_id"], text=f"❌ **کشور {country['name']} پیشنهاد اتحاد شما را رد کرد.**")
            except Exception:
                pass
        await query.edit_message_text("❌ پیشنهاد اتحاد رد شد.")


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
                await update.message.reply_text(f"✅ یادداشت دیپلماتیک رسمی با موفقیت به کشور {target_c['name']} تحویل گردید.")
            except Exception as e:
                await update.message.reply_text(f"❌ ارسال پیام ناموفق بود: {e}")

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
            await update.message.reply_text("❌ عدد وارد شده نامعتبر بود. عملیات لغو شد.")

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
            await update.message.reply_text("❌ عدد وارد شده نامعتبر بود. عملیات لغو شد.")

    elif input_type == "aid_amount":
        try:
            amt = int(clean_num)
            if amt <= 0: raise ValueError
            draft = context.user_data.get("aid_draft", {})
            target_id = draft["target_id"]
            res_type = draft["resource_type"]

            succ, msg_res = db.execute_foreign_aid_transaction(country["id"], target_id, res_type, amt)

            if not succ:
                await update.message.reply_text(f"❌ **ارسال کمک ناموفق بود:**\n\n{msg_res}")
                return

            target_c = db.get_country_by_id(target_id)
            type_labels = {"treasury": "دلار", "gold": "شمش طلا", "oil": "بشکه نفت", "grain": "تن غلات"}

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
            await update.message.reply_text("❌ عدد وارد شده نامعتبر بود. عملیات لغو شد.")
