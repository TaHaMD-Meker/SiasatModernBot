# -*- coding: utf-8 -*-
"""
ماژول سازمان ملل متحد (United Nations Module)
امکانات ویژه دبیرکل سازمان ملل (انحصاری ادمین اصلی):
صدور قطعنامه‌های شورای امنیت، سیستم رای‌گیری بین‌المللی با حق وتو،
استقرار نیروهای صلح‌بان کلاه‌آبی، تحریم‌های جامع، و صندوق امداد بشردوستانه.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

import database as db
import config
from utils import format_money, format_number, format_oil, get_main_keyboard


async def require_un_or_admin(update: Update):
    user_id = update.effective_user.id
    if user_id not in config.ADMIN_IDS:
        if update.message:
            await update.message.reply_text("⛔ این بخش فقط برای دبیرکل سازمان ملل متحد مجاز است.", parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.answer("⛔ عدم دسترسی!", show_alert=True)
        return None, None

    country = db.get_country_by_player(user_id)
    if not country or country.get("country_key") != "un":
        if update.message:
            await update.message.reply_text(
                "🇺🇳 **اتاق مدیریت سازمان ملل متحد**\n\n"
                "جهت استفاده از اختیارات دبیرکل سازمان ملل، ابتدا باید نقش سازمان ملل را از پنل مدیریت (`/admin`) فعال فرمایید.",
                parse_mode="Markdown"
            )
        elif update.callback_query:
            await update.callback_query.answer("ابتدا نقش سازمان ملل را از پنل ادمین فعال کنید.", show_alert=True)
        return None, None

    return user_id, country


# ==================== اتاق دیپلماسی دبیرکل سازمان ملل ====================

async def un_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id, c = await require_un_or_admin(update)
    if not c:
        return

    text = (
        f"🇺🇳 **ستاد دبیرکل سازمان ملل متحد (United Nations Headquarters)**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🏦 *صندوق امداد سازمان ملل:* **{format_money(c['treasury'])}**\n"
        f"🌾 *ذخیره استراتژیک غلات:* **{format_number(c['grain'])} تن**\n"
        f"👤 *یگان صلح‌بانان کلاه‌آبی:* **{format_number(c['active_personnel'])} نفر**\n\n"
        "جهت اعمال اختیارات دیپلماتیک و صلح بین‌المللی، بخش مورد نظر را انتخاب بفرمایید:"
    )

    keyboard = [
        [InlineKeyboardButton("📜 صدور قطعنامه و رای‌گیری شورای امنیت", callback_data="un:create_res")],
        [InlineKeyboardButton("📋 قطعنامه‌ها و رای‌گیری‌های فعال", callback_data="un:res_list")],
        [InlineKeyboardButton("🕊️ اعزام نیروهای صلح‌بان کلاه‌آبی", callback_data="un:peacekeeper_start")],
        [InlineKeyboardButton("📦 ارسال کمک‌های بشردوستانه سازمان ملل", callback_data="un:relief_start")],
        [InlineKeyboardButton("📢 بیانیه رسمی دبیرکل سازمان ملل", callback_data="un:statement_start")],
        [InlineKeyboardButton("🔙 بازگشت به پنل مدیریت", callback_data="admin:menu")],
    ]

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== Callback Handler سازمان ملل ====================

async def un_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    await query.answer()

    if data == "un:menu":
        await un_main_menu(update, context)

    elif data == "un:create_res":
        user_id, c = await require_un_or_admin(update)
        if not c:
            return

        context.user_data["un_draft"] = {"step": "res_title"}
        text = (
            "📜 **صدور قطعنامه جدید شورای امنیت سازمان ملل (UN Resolution)**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً **عنوان و شماره قطعنامه** (مانند: `قطعنامه ۲۲۳۱ — الزام به اعلام آتش‌بس فوری`) را ارسال فرمایید:"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="un:menu")]]), parse_mode="Markdown")

    elif data == "un:res_list":
        resolutions = db.get_un_resolutions("active")

        lines = ["📋 **قطعنامه‌ها و رای‌گیری‌های فعال شورای امنیت سازمان ملل**\n━━━━━━━━━━━━━━━━━━\n"]
        keyboard = []

        if not resolutions:
            lines.append("در حال حاضر هیچ قطعنامه فعالی در شورای امنیت در حال رای‌گیری نیست.")
        else:
            for res in resolutions:
                r_id = res["id"]
                r_title = res["title"]
                r_desc = res["description"]
                votes = db.get_un_resolution_votes(r_id)

                yes_count = len(votes["yes"])
                no_count = len(votes["no"])
                abs_count = len(votes["abstain"])

                lines.append(f"• **قطعنامه #{r_id}: {r_title}**")
                lines.append(f"  _{r_desc}_")
                lines.append(f"  آراء تا کنون: ✅ {yes_count} موافق | ❌ {no_count} مخالف | ⚪ {abs_count} ممتنع\n")

                if user_id in config.ADMIN_IDS:
                    keyboard.append([
                        InlineKeyboardButton(f"✅ تصویب #{r_id}", callback_data=f"un:close_res:{r_id}:passed"),
                        InlineKeyboardButton(f"⛔ وتو/رد #{r_id}", callback_data=f"un:close_res:{r_id}:vetoed")
                    ])

        keyboard.append([InlineKeyboardButton("🔙 بازگشت به ستاد سازمان ملل", callback_data="un:menu")])
        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("un_vote:"):
        # رای‌گیری توسط بازیکنان عادی
        parts = data.split(":")
        res_id = int(parts[1])
        vote_opt = parts[2] # 'yes', 'no', 'abstain'

        voter_c = db.get_country_by_player(user_id)
        if not voter_c:
            await query.answer("شما هنوز کشوری ندارید!", show_alert=True)
            return

        success, msg = db.cast_un_vote(res_id, voter_c["id"], vote_opt)

        if success:
            opt_labels = {"yes": "✅ موافق", "no": "❌ مخالف", "abstain": "⚪ ممتنع"}
            await query.answer(f"رای {opt_labels[vote_opt]} کشور {voter_c['name']} در شورای امنیت ثبت گردید!", show_alert=True)
        else:
            await query.answer(f"❌ {msg}", show_alert=True)

    elif data.startswith("un:close_res:"):
        parts = data.split(":")
        res_id = int(parts[2])
        final_status = parts[3] # 'passed' or 'vetoed'

        res = db.get_un_resolution_by_id(res_id)
        if not res:
            await query.answer("قطعنامه یافت نشد.", show_alert=True)
            return

        db.close_un_resolution(res_id, final_status)
        votes = db.get_un_resolution_votes(res_id)

        yes_str = ", ".join([f"{v['flag']} {v['name']}" for v in votes["yes"]]) or "هیچ"
        no_str = ", ".join([f"{v['flag']} {v['name']}" for v in votes["no"]]) or "هیچ"

        status_text = "✅ **تصویب و لازم‌الاجرا شد**" if final_status == "passed" else "⛔ **وتو / رد شد**"

        broadcast_msg = (
            f"🇺🇳 **نتیجه رسمی رای‌گیری شورای امنیت سازمان ملل**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• **قطعنامه #{res_id}:** {res['title']}\n"
            f"• **وضعیت نهایی:** {status_text}\n\n"
            f"📊 **تفکیک آراء کشورها:**\n"
            f"• **کشورهای موافق ({len(votes['yes'])}):** {yes_str}\n"
            f"• **کشورهای مخالف ({len(votes['no'])}):** {no_str}\n"
            f"• **آراء ممتنع:** {len(votes['abstain'])} کشور\n\n"
            f"📌 _طبق منشور ملل متحد، مفاد قطعنامه‌های تصویب‌شده شورای امنیت برای کلیه دول عضو لازم‌الاجرا می‌باشد._"
        )

        # Broadcast to all players
        all_countries = db.get_all_countries()
        for c_item in all_countries:
            p_id = c_item.get("player_id")
            if p_id:
                try:
                    await context.bot.send_message(chat_id=p_id, text=broadcast_msg, parse_mode="Markdown")
                except Exception:
                    pass

        await query.edit_message_text(
            f"✅ **نتیجه قطعنامه #{res_id} رسماً اعلام و به تمام بازیکنان برودکست گردید.**\n\n{broadcast_msg}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به سازمان ملل", callback_data="un:menu")]]),
            parse_mode="Markdown"
        )

    elif data == "un:peacekeeper_start":
        user_id, c = await require_un_or_admin(update)
        if not c:
            return

        context.user_data["un_draft"] = {"step": "peacekeeper"}
        text = (
            "🕊️ **استقرار نیروهای صلح‌بان کلاه‌آبی سازمان ملل (UN Peacekeepers)**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً **نام کشور یا منطقه حائل هدف** و **جزئیات ماموریت صلح‌بانی** را ارسال فرمایید:"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="un:menu")]]), parse_mode="Markdown")

    elif data == "un:relief_start":
        user_id, c = await require_un_or_admin(update)
        if not c:
            return

        context.user_data["un_draft"] = {"step": "relief"}
        text = (
            "📦 **صندوق امداد و کمک‌های بشردوستانه سازمان ملل (UN Relief Fund)**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً **نام کشور دریافت‌کننده** و **مبلغ یا میزان غلات اهدایی** را ارسال فرمایید:"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="un:menu")]]), parse_mode="Markdown")

    elif data == "un:statement_start":
        user_id, c = await require_un_or_admin(update)
        if not c:
            return

        context.user_data["un_draft"] = {"step": "statement"}
        text = (
            "📢 **بیانیه رسمی دبیرکل سازمان ملل متحد**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً **متن بیانیه رسمی دبیرکل** را ارسال فرمایید (این پیام مستقیماً برای تمامی بازیکنان برودکست خواهد شد):"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="un:menu")]]), parse_mode="Markdown")


# ==================== Text Input Handler سازمان ملل ====================

async def un_text_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    draft = context.user_data.get("un_draft")
    if not draft:
        return

    text = update.message.text.strip()
    step = draft.get("step")

    if step == "res_title":
        draft["res_title"] = text
        draft["step"] = "res_desc"
        await update.message.reply_text(
            f"✅ **عنوان ثبت شد:** `{text}`\n\nحال لطفاً **متن کامل و مفاد قطعنامه شورای امنیت** را ارسال فرمایید:",
            parse_mode="Markdown"
        )

    elif step == "res_desc":
        res_title = draft.get("res_title", "قطعنامه شورای امنیت")
        res_desc = text
        del context.user_data["un_draft"]

        res_id = db.create_un_resolution(res_title, res_desc, user_id)

        broadcast_msg = (
            f"📜 **قطعنامه جدید شورای امنیت سازمان ملل متحد (قطعنامه #{res_id})**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• **عنوان:** {res_title}\n\n"
            f"📋 **مفاد قطعنامه:**\n"
            f'"{res_desc}"\n\n'
            f"📌 _از کلیه دول عضو دعوت می‌شود رای رسمی خود را در خصوص این قطعنامه ثبت نمایند:_"
        )

        vote_keyboard = [
            [
                InlineKeyboardButton("✅ موافق", callback_data=f"un_vote:{res_id}:yes"),
                InlineKeyboardButton("❌ مخالف", callback_data=f"un_vote:{res_id}:no"),
                InlineKeyboardButton("⚪ ممتنع", callback_data=f"un_vote:{res_id}:abstain"),
            ]
        ]

        # Broadcast resolution to all players
        all_countries = db.get_all_countries()
        sent_count = 0
        for c_item in all_countries:
            p_id = c_item.get("player_id")
            if p_id:
                try:
                    await context.bot.send_message(
                        chat_id=p_id,
                        text=broadcast_msg,
                        reply_markup=InlineKeyboardMarkup(vote_keyboard),
                        parse_mode="Markdown"
                    )
                    sent_count += 1
                except Exception:
                    pass

        await update.message.reply_text(
            f"✅ **قطعنامه #{res_id} با موفقیت صادر و رای‌گیری آنلاین آن برای {sent_count} کشور فعال گردید.**",
            reply_markup=get_main_keyboard(user_id),
            parse_mode="Markdown"
        )

    elif step == "peacekeeper":
        del context.user_data["un_draft"]
        msg = (
            f"🕊️ **دستور دبیرکل سازمان ملل متحد — ماموریت صلح‌بانی**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f'"{text}"\n\n'
            f"📌 _یگان صلح‌بانان کلاه‌آبی سازمان ملل متحد (UN Peacekeepers) به منطقه اعزام شدند._"
        )
        all_countries = db.get_all_countries()
        for c_item in all_countries:
            p_id = c_item.get("player_id")
            if p_id:
                try: await context.bot.send_message(chat_id=p_id, text=msg, parse_mode="Markdown")
                except Exception: pass

        await update.message.reply_text("✅ دستور اعزام صلح‌بانان ابلاغ گردید.", reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")

    elif step == "relief":
        del context.user_data["un_draft"]
        msg = (
            f"📦 **ابلاغیه کمک‌های بشردوستانه سازمان ملل متحد**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f'"{text}"\n\n'
            f"📌 _کمک‌های غذایی و مالی از محل صندوق امداد سازمان ملل تخصیص یافت._"
        )
        all_countries = db.get_all_countries()
        for c_item in all_countries:
            p_id = c_item.get("player_id")
            if p_id:
                try: await context.bot.send_message(chat_id=p_id, text=msg, parse_mode="Markdown")
                except Exception: pass

        await update.message.reply_text("✅ کمک‌های بشردوستانه صادر و ابلاغ گردید.", reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")

    elif step == "statement":
        del context.user_data["un_draft"]
        msg = (
            f"📢 **بیانیه رسمی دبیرکل سازمان ملل متحد (UN Secretary-General)**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f'"{text}"\n\n'
            f"📌 _نیویورک — مقر اصلی سازمان ملل متحد_"
        )
        all_countries = db.get_all_countries()
        for c_item in all_countries:
            p_id = c_item.get("player_id")
            if p_id:
                try: await context.bot.send_message(chat_id=p_id, text=msg, parse_mode="Markdown")
                except Exception: pass

        await update.message.reply_text("✅ بیانیه رسمی دبیرکل با موفقیت برای تمامی بازیکنان برودکست شد.", reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")


def get_un_handlers():
    return [
        CommandHandler("un", un_main_menu),
        CallbackQueryHandler(un_callback_handler, pattern=r"^(un:|un_vote:)"),
    ]
