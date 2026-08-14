# -*- coding: utf-8 -*-
"""
دستور /start : ثبت‌نام کشور تازه.
از یک ConversationHandler ساده استفاده می‌کنیم که اسم کشور رو از بازیکن بپرسه.
"""

from telegram import Update, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters, CommandHandler

import database as db

ASK_NAME = 1


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    player_id = update.effective_user.id
    existing = db.get_country_by_player(player_id)

    if existing:
        await update.message.reply_text(
            f"{existing['flag']} کشور {existing['name']} تو از قبل ثبت شده.\n"
            "برای دیدن وضعیت از /country استفاده کن."
        )
        return ConversationHandler.END

    await update.message.reply_text(
        "🎮 به «سیاست مدرن» خوش اومدی!\n\n"
        "اول از همه، اسم کشورت رو بفرست (مثلاً: ایران، آلمان و ...)"
    )
    return ASK_NAME


async def receive_country_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    player_id = update.effective_user.id
    name = update.message.text.strip()

    if len(name) < 2 or len(name) > 30:
        await update.message.reply_text("اسم باید بین ۲ تا ۳۰ کاراکتر باشه. دوباره بفرست:")
        return ASK_NAME

    db.create_country(player_id, name)
    db.add_log(actor=str(player_id), action="create_country", details=name)

    await update.message.reply_text(
        f"✅ کشور «{name}» با موفقیت ثبت شد!\n\n"
        "برای دیدن وضعیت کشورت از /country استفاده کن.\n"
        "برای دیدن راهنما /help رو بزن.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ثبت‌نام لغو شد.")
    return ConversationHandler.END


def get_start_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            ASK_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_country_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
