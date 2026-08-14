# -*- coding: utf-8 -*-
"""
فروشگاه: نمایش دسته‌ها با دکمه شیشه‌ای، انتخاب کالا، تأیید خرید، اجرای تراکنش.
استفاده از buy_item_transaction برای پیشگیری از Race Condition و خرید منفی.
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
    """وقتی کاربر روی یک کالا کلیک می‌کنه، تأیید نهایی گرفته میشه."""
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
        "برای خرید ۱ عدد تأیید کن:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def execute_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    if len(parts) != 3:
        await query.edit_message_text("داده‌های درخواست نامعتبر است.")
        return

    item_key = parts[1]
    quantity = int(parts[2])

    country = db.get_country_by_player(update.effective_user.id)
    item = config.ALL_SHOP_ITEMS.get(item_key)
    if not country or not item:
        await query.edit_message_text("خطا در انجام خرید.")
        return

    total_price = item["price"] * quantity

    # اجرای تراکنش اتومیک در دیتابیس
    success, msg = db.buy_item_transaction(country["id"], item_key, quantity, total_price, item["name"])

    if not success:
        await query.edit_message_text(f"❌ خرید انجام نشد:\n{msg}")
        return

    db.add_log(actor=str(update.effective_user.id), action="purchase", details=f"{item_key} x{quantity}")

    # دریافت اطلاعات به‌روز کشور پس از خرید
    updated_country = db.get_country_by_player(update.effective_user.id)

    await query.edit_message_text(
        f"✅ خرید با موفقیت انجام شد!\n\n"
        f"🛒 {item['name']} x{quantity}\n"
        f"💰 مبلغ کسر شده: {format_money(total_price)}\n"
        f"🏦 موجودی جدید خزانه: {format_money(updated_country['treasury'])}"
    )
