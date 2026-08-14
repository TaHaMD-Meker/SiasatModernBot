# -*- coding: utf-8 -*-
"""
دستورات نمایش وضعیت کشور: /country /treasury /oil /army /help
"""

from telegram import Update
from telegram.ext import ContextTypes

import database as db
import config
from utils import format_money, format_number, format_oil


async def require_country(update: Update):
    """اگر بازیکن کشور نداشت پیام مناسب می‌دهد و None برمی‌گرداند."""
    country = db.get_country_by_player(update.effective_user.id)
    if not country:
        await update.message.reply_text("هنوز کشوری نساختی! برای شروع /start رو بزن.")
        return None
    return country


async def country_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = await require_country(update)
    if not c:
        return

    text = (
        f"{c['flag']} {c['name']}\n\n"
        f"👥 جمعیت: {format_number(c['population'])}\n"
        f"💰 درآمد مالیاتی: {format_money(c['tax_income'])}\n"
        f"🏦 خزانه: {format_money(c['treasury'])}\n"
        f"🪙 طلا: {format_number(c['gold'])}\n"
        f"📈 درآمد روزانه: {format_money(c['daily_income'])}\n\n"
        f"🛢️ ذخیره نفت: {format_oil(c['oil_reserves'])}\n"
        f"🛢️ تولید نفت: {format_oil(c['oil_production'])} در روز\n\n"
        f"🌾 غلات: {format_number(c['grain'])}\n"
        f"⚡ برق: {c['electricity']}\n\n"
        f"👤 نیروی فعال: {format_number(c['active_personnel'])}\n"
        f"👤 نیروی ذخیره: {format_number(c['reserve_personnel'])}"
    )
    await update.message.reply_text(text)


async def treasury(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = await require_country(update)
    if not c:
        return
    await update.message.reply_text(
        f"🏦 خزانه {c['name']}: {format_money(c['treasury'])}\n"
        f"🪙 طلا: {format_number(c['gold'])}"
    )


async def oil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = await require_country(update)
    if not c:
        return
    await update.message.reply_text(
        f"🛢️ ذخیره نفت {c['name']}: {format_oil(c['oil_reserves'])}\n"
        f"🛢️ تولید روزانه: {format_oil(c['oil_production'])}"
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

    await update.message.reply_text("\n".join(lines))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_adm = user_id in config.ADMIN_IDS

    text = (
        "📜 راهنمای دستورات بازی «سیاست مدرن»\n\n"
        "/start — شروع بازی و ساخت کشور\n"
        "/country — نمایش وضعیت کامل کشور\n"
        "/treasury — نمایش خزانه و طلا\n"
        "/oil — نمایش وضعیت نفت\n"
        "/army — نمایش وضعیت نظامی\n"
        "/shop — فروشگاه (خرید تجهیزات و ساختمان)\n"
        "/help — همین راهنما"
    )

    if is_adm:
        text += "\n\n👑 **دستورات ادمین:**\n/admin یا /panel — پنل دکمه‌ای و پیشرفته مدیریت"

    await update.message.reply_text(text)
