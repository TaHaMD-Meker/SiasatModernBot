# -*- coding: utf-8 -*-
"""
فروشگاه: نمایش دسته‌ها با دکمه شیشه‌ای، انتخاب کالا، تأیید خرید، اجرای تراکنش.
طبق سند: قبل از خرید موجودی چک میشه و برای خرید تأییدیه گرفته میشه.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database as db
import config
from utils import format_money

CATEGORIES = {
    "buildings": ("🏠 ساختمان‌ها", config.BUILDINGS),
    "factories": ("🏭 صنعت", config.FACTORIES),
    "power": ("⚡ انرژی", config.POWER_PLANTS),
    "military": ("🪖 نظامی", config.MILITARY_EQUIPMENT),
}


async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    country = db.get_country_by_player(update.effective_user.id)
    if not country:
        await update.message.reply_text("هنوز کشوری نساختی! برای شروع /start رو بزن.")
        return

    buttons = [
        [InlineKeyboardButton(label, callback_data=f"shopcat:{key}")]
        for key, (label, _) in CATEGORIES.items()
    ]
    await update.message.reply_text(
        f"🏪 فروشگاه\n🏦 موجودی خزانه: {format_money(country['treasury'])}\n\nیک دسته رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_key = query.data.split(":", 1)[1]
    label, items = CATEGORIES[cat_key]

    buttons = []
    for item_key, item in items.items():
        buttons.append([InlineKeyboardButton(
            f"{item['name']} — {format_money(item['price'])}",
            callback_data=f"buyitem:{item_key}"
        )])
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="shopback")])

    await query.edit_message_text(f"{label}\n\nکالای موردنظر رو انتخاب کن:", reply_markup=InlineKeyboardMarkup(buttons))


async def back_to_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    country = db.get_country_by_player(update.effective_user.id)
    buttons = [
        [InlineKeyboardButton(label, callback_data=f"shopcat:{key}")]
        for key, (label, _) in CATEGORIES.items()
    ]
    await query.edit_message_text(
        f"🏪 فروشگاه\n🏦 موجودی خزانه: {format_money(country['treasury'])}\n\nیک دسته رو انتخاب کن:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def confirm_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وقتی کاربر رو یه کالا کلیک می‌کنه، تعداد ۱ پیشنهاد میشه و تأیید نهایی گرفته میشه."""
    query = update.callback_query
    await query.answer()
    item_key = query.data.split(":", 1)[1]
    item = config.ALL_SHOP_ITEMS.get(item_key)
    if not item:
        await query.edit_message_text("این کالا دیگه در دسترس نیست.")
        return

    buttons = [
        [InlineKeyboardButton("✅ تأیید خرید (۱ عدد)", callback_data=f"confirmbuy:{item_key}:1")],
        [InlineKeyboardButton("❌ لغو", callback_data="shopback")],
    ]
    await query.edit_message_text(
        f"خرید: {item['name']}\n💰 قیمت واحد: {format_money(item['price'])}\n\n"
        "برای خرید ۱ عدد تأیید کن (برای تعداد بیشتر، این نسخه اولیه رو بعداً توسعه می‌دیم).",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def execute_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    _, item_key, qty_str = query.data.split(":")
    quantity = int(qty_str)

    country = db.get_country_by_player(update.effective_user.id)
    item = config.ALL_SHOP_ITEMS.get(item_key)
    if not country or not item:
        await query.edit_message_text("خطا در انجام خرید.")
        return

    total_price = item["price"] * quantity

    # ===== جلوگیری از تقلب: بررسی موجودی کافی =====
    if country["treasury"] < total_price:
        await query.edit_message_text(
            f"❌ موجودی کافی نیست.\n"
            f"قیمت: {format_money(total_price)}\n"
            f"موجودی خزانه: {format_money(country['treasury'])}"
        )
        return

    db.adjust_treasury(country["id"], -total_price)
    db.add_equipment(country["id"], item_key, quantity)
    db.add_transaction(country["id"], "purchase", f"خرید {item['name']} x{quantity}", -total_price)
    db.add_log(actor=str(update.effective_user.id), action="purchase", details=f"{item_key} x{quantity}")

    await query.edit_message_text(
        f"✅ خرید موفق!\n\n"
        f"🛒 {item['name']} x{quantity}\n"
        f"💰 مبلغ کسر شده: {format_money(total_price)}\n"
        f"🏦 موجودی جدید: {format_money(country['treasury'] - total_price)}"
  )
