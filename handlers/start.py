# -*- coding: utf-8 -*-
"""
دستور /start : انتخاب کشور از بین لیست، با دکمه شیشه‌ای.
پس از انتخاب کشور، کیبورد اصلی دکمه‌های پایین صفحه (Reply Keyboard) برای کاربر فعال می‌شود.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

import database as db
import config
from utils import get_main_keyboard


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
    user = update.effective_user
    player_id = user.id

    if not user.username:
        await update.message.reply_text(
            "⛔ **خطا در ساخت کشور (احراز هویت تلگرام):**\n\n"
            "جهت حفظ امنیت بازی و جلوگیری از حساب‌های ناشناس و فیک، حساب تلگرام شما باید دارای **آیدی / یوزرنیم (@username)** باشد.\n\n"
            "لطفاً در تنظیمات تلگرام خود یک آیدی (Username) تنظیم فرموده و سپس مجدداً دستور /start را ارسال کنید.",
            parse_mode="Markdown"
        )
        return

    existing = db.get_country_by_player(player_id)

    if existing:
        await update.message.reply_text(
            f"{existing['flag']} کشور {existing['name']} تو از قبل ثبت شده.\n"
            "از دکمه‌های پایین صفحه برای مدیریت کشورت استفاده کن 👇",
            reply_markup=get_main_keyboard(player_id)
        )
        return

    buttons = build_country_keyboard()
    if not buttons:
        await update.message.reply_text("متأسفانه همه‌ی کشورها قبلاً انتخاب شدن!")
        return

    await update.message.reply_text(
        "🎮 به بازی «سیاست مدرن» خوش اومدی!\n\nلطفاً کشورت رو از بین گزینه‌های زیر انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def pick_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    player_id = user.id

    if not user.username:
        await query.edit_message_text(
            "⛔ **حساب تلگرام شما فاقد یوزرنیم (@username) است.**\nلطفاً ابتدا در تنظیمات تلگرام آیدی ست کرده و سپس /start بزنید.",
            parse_mode="Markdown"
        )
        return

    existing = db.get_country_by_player(player_id)
    if existing:
        await query.edit_message_text(f"تو از قبل کشور {existing['flag']} {existing['name']} رو داری!")
        await context.bot.send_message(
            chat_id=player_id,
            text="از دکمه‌های پایین صفحه استفاده کن 👇",
            reply_markup=get_main_keyboard(player_id)
        )
        return

    key = query.data.split(":", 1)[1]
    info = config.COUNTRIES.get(key)
    if not info:
        await query.edit_message_text("این کشور دیگه در دسترس نیست.")
        return

    # جلوگیری از انتخاب همزمان کشور توسط دو کاربر
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

    db.create_country(player_id, info["name"], info["flag"], key, user.username)
    db.add_log(actor=str(player_id), action="create_country", details=key)

    await query.edit_message_text(
        f"✅ کشور {info['flag']} {info['name']} با موفقیت برای شما ثبت شد!\n\n"
        "منوی اصلی بازی در پایین صفحه قرار گرفت 👇"
    )

    # ارسال کیبورد دکمه‌های اصلی پایین صفحه
    await context.bot.send_message(
        chat_id=player_id,
        text=f"👑 رهبر عزیز کشور {info['name']}، خوش آمدید!\nبرای مدیریت کشور از دکمه‌های زیر استفاده کنید:",
        reply_markup=get_main_keyboard(player_id)
    )


async def reset_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور تست: کشور خودتو پاک می‌کنه تا بتونی دوباره از /start شروع کنی."""
    player_id = update.effective_user.id
    deleted = db.delete_country_by_player(player_id)
    if deleted:
        await update.message.reply_text("✅ کشورت پاک شد. حالا می‌تونی دوباره /start رو بزنی.")
    else:
        await update.message.reply_text("کشوری برای پاک کردن نداری.")


def get_start_handlers():
    return [
        CommandHandler("start", start),
        CommandHandler("resetme", reset_me),
        CallbackQueryHandler(pick_country, pattern=r"^pickcountry:"),
    ]
