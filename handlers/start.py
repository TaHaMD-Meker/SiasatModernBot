# -*- coding: utf-8 -*-
"""
دستور /start : انتخاب کشور از بین لیست، با دکمه شیشه‌ای.
هر کشور فقط یک‌بار قابل انتخابه؛ وقتی گرفته شد از لیست حذف میشه.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

import database as db
import config


def build_country_keyboard():
    """دکمه‌های کشورهایی که هنوز کسی انتخابشون نکرده رو می‌سازه."""
    taken = db.get_taken_country_keys()
    buttons = []
    row = []
    for key, info in config.COUNTRIES.items():
        if key in taken:
            continue
        row.append(InlineKeyboardButton(f"{info['flag']} {info['name']}", callback_data=f"pickcountry:{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return buttons


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    player_id = update.effective_user.id
    existing = db.get_country_by_player(player_id)

    if existing:
        await update.message.reply_text(
            f"{existing['flag']} کشور {existing['name']} تو از قبل ثبت شده.\n"
            "برای دیدن وضعیت از /country استفاده کن."
        )
        return

    buttons = build_country_keyboard()
    if not buttons:
        await update.message.reply_text("متأسفانه همه‌ی کشورها قبلاً انتخاب شدن!")
        return

    await update.message.reply_text(
        "🎮 به «سیاست مدرن» خوش اومدی!\n\nکشورت رو از بین گزینه‌های زیر انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def pick_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    player_id = update.effective_user.id
    existing = db.get_country_by_player(player_id)
    if existing:
        await query.edit_message_text(f"تو از قبل کشور {existing['flag']} {existing['name']} رو داری!")
        return

    key = query.data.split(":", 1)[1]
    info = config.COUNTRIES.get(key)
    if not info:
        await query.edit_message_text("این کشور دیگه در دسترس نیست.")
        return

    # ===== جلوگیری از تقلب: بررسی نهایی که کشور توسط بازیکن دیگه گرفته نشده باشه =====
    if db.get_country_by_key(key):
        buttons = build_country_keyboard()
        if not buttons:
            await query.edit_message_text("این کشور همین الان گرفته شد و دیگه کشوری باقی نمونده!")
            return
        await query.edit_message_text(
            "این کشور همین الان توسط یه بازیکن دیگه انتخاب شد! یکی دیگه رو انتخاب کن:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    db.create_country(player_id, info["name"], info["flag"], key)
    db.add_log(actor=str(player_id), action="create_country", details=key)

    await query.edit_message_text(
        f"✅ کشور {info['flag']} {info['name']} با موفقیت انتخاب شد!\n\n"
        "برای دیدن وضعیت کشورت از /country استفاده کن.\n"
        "برای دیدن راهنما /help رو بزن."
    )


def get_start_handlers():
    return [
        CommandHandler("start", start),
        CallbackQueryHandler(pick_country, pattern=r"^pickcountry:"),
    ]
