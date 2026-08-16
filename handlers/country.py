# -*- coding: utf-8 -*-
"""
دستورات نمایش وضعیت کشور: /country /treasury /oil /army /help
پشتیبانی از دکمه‌های پایین صفحه (ReplyKeyboard)
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database as db
import config
import approval_system
from utils import format_money, format_number, format_oil, get_main_keyboard


async def require_country(update: Update):
    """اگر بازیکن کشور نداشت پیام مناسب می‌دهد و None برمی‌گرداند."""
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        if update.message:
            await update.message.reply_text("هنوز کشوری نساختی! برای شروع /start رو بزن.")
        elif update.callback_query:
            await update.callback_query.answer("هنوز کشوری نساختی!", show_alert=True)
        return None
    return country


async def country_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = await require_country(update)
    if not c:
        return

    app_val = c.get('approval_rating', 80)
    app_icon = "🟢" if app_val >= 75 else ("🟡" if app_val >= 50 else ("🟠" if app_val >= 40 else "🔴"))

    text = (
        f"{c['flag']} **وضعیت کشور {c['name']}**\n\n"
        f"📊 رضایت عمومی: {app_icon} {app_val}٪ (/approval)\n"
        f"👥 جمعیت: {format_number(c['population'])}\n"
        f"💰 درآمد مالیاتی: {format_money(c['tax_income'])}\n"
        f"🏦 خزانه: {format_money(c['treasury'])}\n"
        f"🪙 طلا: {format_number(c['gold'])}\n"
        f"📈 درآمد روزانه: {format_money(c['daily_income'])}\n\n"
        f"🛢️ ذخیره نفت: {format_oil(c['oil_reserves'])}\n"
        f"🛢️ تولید نفت: {format_oil(c['oil_production'])} در روز\n\n"
        f"🌾 غلات: {format_number(c['grain'])}\n"
        f"⚡ برق: {c['electricity']}٪\n\n"
        f"👤 نیروی فعال: {format_number(c['active_personnel'])}\n"
        f"👤 نیروی ذخیره: {format_number(c['reserve_personnel'])}"
    )

    inline_keyboard = [[InlineKeyboardButton("📊 مشاهده کامل وضعیت رضایت عمومی", callback_data="country:approval_details")]]

    if update.message:
        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(update.effective_user.id)
        )
        await update.message.reply_text(
            "👇 جهت مشاهده تحلیل دقیق منابع و تحلیل رضایت عمومی کلیک کنید:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard)
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard),
            parse_mode="Markdown"
        )


async def country_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == "country:approval_details":
        c = await require_country(update)
        if not c:
            return
        msg = approval_system.get_approval_status_message(c)
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به وضعیت کشور", callback_data="country:back_profile")]]
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "country:back_profile":
        await country_profile(update, context)


async def approval_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = await require_country(update)
    if not c:
        return

    msg = approval_system.get_approval_status_message(c)
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard(update.effective_user.id))


async def treasury(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = await require_country(update)
    if not c:
        return
    await update.message.reply_text(
        f"🏦 خزانه {c['name']}: {format_money(c['treasury'])}\n"
        f"🪙 طلا: {format_number(c['gold'])}",
        reply_markup=get_main_keyboard(update.effective_user.id)
    )


async def oil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = await require_country(update)
    if not c:
        return
    await update.message.reply_text(
        f"🛢️ ذخیره نفت {c['name']}: {format_oil(c['oil_reserves'])}\n"
        f"🛢️ تولید روزانه: {format_oil(c['oil_production'])}",
        reply_markup=get_main_keyboard(update.effective_user.id)
    )


async def army(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = await require_country(update)
    if not c:
        return

    equipment = db.get_equipment(c["id"])
    lines = [
        f"🪖 {c['name']} — وضعیت نظامی\n",
        f"👤 نیروی فعال: {format_number(c['active_personnel'])}",
        f"👤 نیروی ذخیره: {format_number(c['reserve_personnel'])}\n",
    ]

    if not equipment:
        lines.append("هنوز تجهیزاتی خریداری نکردی. از /shop استفاده کن.")
    else:
        for key, qty in equipment.items():
            item = config.ALL_SHOP_ITEMS.get(key)
            name = item["name"] if item else key
            lines.append(f"{name}: {qty}")

    await update.message.reply_text("\n".join(lines), reply_markup=get_main_keyboard(update.effective_user.id))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_adm = user_id in config.ADMIN_IDS

    text = (
        "📜 راهنمای بازی «سیاست مدرن»\n\n"
        "شما می‌توانید از دکمه‌های ثابت پایین صفحه یا دستورات زیر استفاده کنید:\n\n"
        "🌐 **وضعیت کشور** (`/country`)\n"
        "🏦 **خزانه و طلا** (`/treasury`)\n"
        "🛢️ **وضعیت نفت** (`/oil`)\n"
        "🪖 **وضعیت ارتش** (`/army`)\n"
        "🏪 **فروشگاه** (`/shop`)\n"
        "📜 **راهنما** (`/help`)"
    )

    if is_adm:
        text += "\n\n👑 **پنل مدیریت:** فقط برای ادمین اصلی بازی فعال است."

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))
