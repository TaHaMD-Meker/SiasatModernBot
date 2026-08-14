# -*- coding: utf-8 -*-
"""
سیستم دارایی‌های اختصاصی کشورها (Country Assets System)
دستور /assets و مدیریت نمایش تجهیزات نظامی به صورت تفکیک‌شده با دکمه‌های شیشه‌ای.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

import database as db
import config
from utils import format_number, get_main_keyboard


async def show_assets_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)

    if not country:
        await update.message.reply_text("هنوز کشوری نساختی! برای شروع /start رو بزن.")
        return

    # تضمین وجود دارایی‌های اولیه
    db.seed_country_assets(country["id"], country["country_key"])

    text = f"{country['flag']} **{country['name']} — دارایی‌های نظامی اختصاصی**\n\nبرای مشاهده تجهیزات موجود، دسته مورد نظر را انتخاب کنید:"

    buttons = [
        [
            InlineKeyboardButton("✈️ نیروی هوایی", callback_data="assets_cat:Aircraft"),
            InlineKeyboardButton("🚀 موشکی", callback_data="assets_cat:Missiles"),
        ],
        [
            InlineKeyboardButton("🛡️ پدافند هوایی", callback_data="assets_cat:Air Defense"),
            InlineKeyboardButton("🚢 نیروی دریایی", callback_data="assets_cat:Navy"),
        ],
        [
            InlineKeyboardButton("🚛 نیروی زمینی", callback_data="assets_cat:Ground Forces"),
            InlineKeyboardButton("🛩️ پهپادها", callback_data="assets_cat:UAV"),
        ],
        [
            InlineKeyboardButton("🎯 توپخانه", callback_data="assets_cat:Artillery"),
            InlineKeyboardButton("📊 آمار کلی دارایی‌ها", callback_data="assets_cat:all"),
        ],
    ]

    if update.message:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )


async def assets_category_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    country = db.get_country_by_player(user_id)

    if not country:
        await query.edit_message_text("کشور شما یافت نشد!")
        return

    category = query.data.split(":", 1)[1]
    assets = db.get_country_assets(country["id"], category)

    if category == "all":
        cat_title = "📊 آمار کلی دارایی‌های نظامی"
    else:
        cat_info = config.ASSET_CATEGORIES.get(category, (category, "عدد"))
        cat_title = cat_info[0]

    lines = [f"{country['flag']} **{country['name']} — {cat_title}**\n"]

    if not assets:
        lines.append("هیچ تجهیزی در این دسته یافت نشد.")
    else:
        current_cat = ""
        for item in assets:
            cat_code = item["category"]
            unit = config.ASSET_CATEGORIES.get(cat_code, ("", "عدد"))[1]

            if category == "all" and cat_code != current_cat:
                current_cat = cat_code
                cat_label = config.ASSET_CATEGORIES.get(cat_code, (cat_code, ""))[0]
                lines.append(f"\n{cat_label}:")

            lines.append(f"• **{item['equipment_name']}**: {format_number(item['amount'])} {unit}")

    keyboard = [[InlineKeyboardButton("🔙 بازگشت به دسته‌بندی‌ها", callback_data="assets_back")]]

    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def assets_back_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    country = db.get_country_by_player(user_id)

    if not country:
        await query.edit_message_text("کشور شما یافت نشد!")
        return

    text = f"{country['flag']} **{country['name']} — دارایی‌های نظامی اختصاصی**\n\nبرای مشاهده تجهیزات موجود، دسته مورد نظر را انتخاب کنید:"

    buttons = [
        [
            InlineKeyboardButton("✈️ نیروی هوایی", callback_data="assets_cat:Aircraft"),
            InlineKeyboardButton("🚀 موشکی", callback_data="assets_cat:Missiles"),
        ],
        [
            InlineKeyboardButton("🛡️ پدافند هوایی", callback_data="assets_cat:Air Defense"),
            InlineKeyboardButton("🚢 نیروی دریایی", callback_data="assets_cat:Navy"),
        ],
        [
            InlineKeyboardButton("🚛 نیروی زمینی", callback_data="assets_cat:Ground Forces"),
            InlineKeyboardButton("🛩️ پهپادها", callback_data="assets_cat:UAV"),
        ],
        [
            InlineKeyboardButton("🎯 توپخانه", callback_data="assets_cat:Artillery"),
            InlineKeyboardButton("📊 آمار کلی دارایی‌ها", callback_data="assets_cat:all"),
        ],
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


def get_assets_handlers():
    return [
        CommandHandler("assets", show_assets_menu),
        CallbackQueryHandler(assets_category_callback, pattern=r"^assets_cat:"),
        CallbackQueryHandler(assets_back_callback, pattern=r"^assets_back$"),
    ]
