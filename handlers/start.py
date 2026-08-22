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
    """دکمه‌های کشورهایی که هنوز کسی انتخاب یا درخواست نداده رو می‌سازه."""
    taken = db.get_taken_and_pending_country_keys()
    buttons = []
    row = []
    for key, info in config.COUNTRIES.items():
        if key in taken or key == "un":
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
            "⛔ *خطا در ساخت کشور (احراز هویت تلگرام):*\n\n"
            "جهت حفظ امنیت بازی و جلوگیری از حساب‌های ناشناس و فیک، حساب تلگرام شما باید دارای *آیدی / یوزرنیم (@username)* باشد.\n\n"
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

    # Check lock status
    is_adm = player_id in config.ADMIN_IDS
    if not is_adm and db.get_setting("country_creation_locked") == "1":
        await update.message.reply_text(
            f"🔒 **ثبت‌نام و انتخاب کشورها موقتاً قفل است!**\n\n"
            "بازی «سیاست مدرن» در حال حاضر در فاز آماده‌سازی نهایی قبل از افتتاحیه قرار دارد.\n"
            "زمان شروع رسمی به‌زودی در کانال تلگرام اعلام خواهد شد.\n\n"
            f"📢 **کانال رسمی بازی:** {config.get_channel_id()}",
            parse_mode="Markdown"
        )
        return

    buttons = build_country_keyboard()
    if not buttons:
        await update.message.reply_text("متأسفانه همه‌ی کشورها قبلاً انتخاب شدن!", parse_mode="Markdown")
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
            "⛔ *حساب تلگرام شما فاقد یوزرنیم (@username) است.*\nلطفاً ابتدا در تنظیمات تلگرام آیدی ست کرده و سپس /start بزنید.",
            parse_mode="Markdown"
        )
        return

    # Check lock status
    is_adm = player_id in config.ADMIN_IDS
    if not is_adm and db.get_setting("country_creation_locked") == "1":
        await query.edit_message_text(
            f"🔒 **ثبت‌نام و انتخاب کشورها موقتاً قفل است!**\n\n"
            "زمان شروع رسمی به‌زودی در کانال تلگرام اعلام خواهد شد.\n\n"
            f"📢 **کانال رسمی بازی:** {config.get_channel_id()}",
            parse_mode="Markdown"
        )
        return

    existing = db.get_country_by_player(player_id)
    if existing:
        await query.edit_message_text(f"تو از قبل کشور {existing['flag']} {existing['name']} رو داری!", parse_mode="Markdown")
        await context.bot.send_message(
            chat_id=player_id,
            text="از دکمه‌های پایین صفحه استفاده کن 👇",
            reply_markup=get_main_keyboard(player_id)
        )
        return

    # Check if user already has a pending request
    pending_req = db.get_pending_request_by_player(player_id)
    if pending_req:
        await query.edit_message_text(
            "⏳ *شما یک درخواست معلق فعال دارید.*\nلطفاً منتظر بررسی و تایید ادمین اصلی بازی بمانید.",
            parse_mode="Markdown"
        )
        return

    key = query.data.split(":", 1)[1]
    info = config.COUNTRIES.get(key)
    if not info:
        await query.edit_message_text("این کشور دیگه در دسترس نیست.", parse_mode="Markdown")
        return

    # جلوگیری از انتخاب همزمان کشور توسط دو کاربر
    if key in db.get_taken_and_pending_country_keys():
        buttons = build_country_keyboard()
        if not buttons:
            await query.edit_message_text("این کشور همین الان توسط کاربر دیگری درخواست شد!", parse_mode="Markdown")
            return
        await query.edit_message_text(
            "این کشور همین الان توسط یه بازیکن دیگه درخواست شد! یکی دیگه رو انتخاب کن:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    # Save pending request
    req_id = db.create_pending_country_request(
        player_id=player_id,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        username=user.username,
        country_key=key
    )

    db.add_log(actor=str(player_id), action="request_country", details=key)

    # Send approval request to Admin
    u_name_display = f"@{user.username}" if user.username else "ندارد"
    user_url = f"https://t.me/{user.username}" if user.username else f"tg://user?id={player_id}"
    admin_msg = (
        "📥 *درخواست جدید انتخاب کشور*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"• *کشور درخواستی:* {info['flag']} {info['name']} (`{key}`)\n"
        f"• *نام کاربر:* {user.first_name or ''} {user.last_name or ''}\n"
        f"• *یوزرنیم تلگرام:* {u_name_display}\n"
        f"• *شناسه عددی (ID):* `{player_id}`\n\n"
        f"🔍 برای بررسی هویت و پیام دادن به بازیکن، روی دکمه زیر کلیک کنید:"
    )

    admin_kb = [
        [InlineKeyboardButton("👤 مشاهده پروفایل / چت با متقاضی در پیوی", url=user_url)],
        [
            InlineKeyboardButton("✅ تایید و واگذاری کشور", callback_data=f"admin:approve_country:{req_id}"),
            InlineKeyboardButton("❌ رد درخواست", callback_data=f"admin:reject_country:{req_id}")
        ],
    ]

    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_msg,
                reply_markup=InlineKeyboardMarkup(admin_kb),
                parse_mode="Markdown"
            )
        except Exception:
            pass

    await query.edit_message_text(
        f"⏳ *درخواست انتخاب کشور ثبت گردید!*\n\n"
        f"درخواست شما برای دریافت کشور {info['flag']} {info['name']} جهت تایید برای ادمین اصلی بازی ارسال شد.\n"
        "پس از بررسی و تایید ادمین، کشور شما فعال گردیده و اطلاع‌رسانی خواهد شد.",
        parse_mode="Markdown"
    )


async def reset_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور تست: کشور خودتو پاک می‌کنه تا بتونی دوباره از /start شروع کنی."""
    player_id = update.effective_user.id
    deleted = db.delete_country_by_player(player_id)
    if deleted:
        await update.message.reply_text("✅ کشورت پاک شد. حالا می‌تونی دوباره /start رو بزنی.", parse_mode="Markdown")
    else:
        await update.message.reply_text("کشوری برای پاک کردن نداری.", parse_mode="Markdown")


def get_start_handlers():
    return [
        CommandHandler("start", start),
        CommandHandler("resetme", reset_me),
        CallbackQueryHandler(pick_country, pattern=r"^pickcountry:"),
    ]