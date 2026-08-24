# -*- coding: utf-8 -*-
"""
سیستم دارایی‌های اختصاصی کشورها (Country Assets System)
دستور /assets و مدیریت نمایش تجهیزات نظامی به صورت تفکیک‌شده به زیرگروه‌های تخصصی.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

import database as db
import config
from utils import format_number, get_main_keyboard


def subcategorize_assets(category, assets):
    """دسته‌بندی و مرتب‌سازی هوشمند تجهیزات نظامی هر بخش به زیرگروه‌های تخصصی بدون تداخل."""
    grouped = {}

    for item in assets:
        eq_name = item["equipment_name"].lower()
        eq_cat = item["category"]

        if eq_cat == "Aircraft":
            if any(h in eq_name for h in ["heli", "apache", "black hawk", "blackhawk", "chinook", "viper", "osprey", "seahawk", "بالگرد", "شینوک", "طوفان", "شاهد-۲۸۵", "بل ", "میل ", "ka-52", "mi-28", "mi-35", "mi-171", "t129", "atak", "gokbey", "tiger", "caracal", "panther"]):
                sub_title = "🚁 *بالگردها (هجومی و ترابری)*"
                sort_order = 104
            elif any(b in eq_name for b in ["bomber", "بمب‌افکن", "b-1b", "b-2", "b-52", "b-21", "tu-160", "tu-95", "tu-22", "h-6", "h-20"]):
                sub_title = "💣 *بمب‌افکن‌های استراتژیک*"
                sort_order = 102
            elif any(s in eq_name for s in ["awacs", "آواکس", "tanker", "سوخت‌رسان", "c-130", "c-17", "c-5", "c-2", "c-390", "a400m", "e-3", "e-2", "e-7", "rc-135", "u-2", "poseidon", "p-8", "p-3", "p-1", "ترابری", "گشت دریایی"]):
                sub_title = "✈️ *هواپیماهای پشتیبانی، آواکس و ترابری*"
                sort_order = 103
            else:
                sub_title = "✈️ *جنگنده‌ها و رهگیرهای رزمی*"
                sort_order = 101

        elif eq_cat == "Missiles":
            sub_title = "🚀 *توان موشکی و بالستیک*"
            sort_order = 201

        elif eq_cat == "Air Defense":
            sub_title = "🛡️ *سامانه‌های پدافند هوایی و رادارها*"
            sort_order = 301

        elif eq_cat == "Navy":
            if any(c in eq_name for c in ["carrier", "ford", "nimitz", "fujian", "shandong", "liaoning", "kuznetsov", "charles de gaulle", "queen elizabeth", "anadolu", "lha", "lhd", "هواپیمابر", "بالگردبر"]):
                sub_title = "⚓ *ناوهای هواپیمابر و تهاجمی*"
                sort_order = 401
            elif any(d in eq_name for d in ["destroyer", "burke", "zumwalt", "type 055", "type 052", "type 45", "visakhapatnam", "kirov", "gorshkov", "maya", "atago", "kongo", "ناوشکن"]):
                sub_title = "🚀 *ناوشکن‌ها و رزم‌پناوها*"
                sort_order = 402
            elif any(s in eq_name for s in ["sub", "ssn", "ssbn", "virginia", "ohio", "yasen", "borei", "type 094", "astute", "vanguard", "suffren", "type 212", "dolphin", "kilo", "fateh", "ghadir", "زیردریایی"]):
                sub_title = "🌊 *زیردریایی‌های تهاجمی و استراتژیک*"
                sort_order = 404
            else:
                sub_title = "🚢 *ناوچه‌ها، ناوچه‌های سبک و شناورها*"
                sort_order = 403

        elif eq_cat == "Ground Forces":
            if any(t in eq_name for t in ["tank", "تانک", "abrams", "armata", "leopard", "challenger", "leclerc", "merkava", "karrar", "zulfiqar", "altay", "t-90", "t-80", "t-72", "type 99", "type 10", "type 90"]):
                sub_title = "🛡️ *تانک‌های اصلی میدان نبرد*"
                sort_order = 501
            elif any(i in eq_name for i in ["ifv", "apc", "نفربر", "bradley", "bmp", "btr", "stryker", "puma", "marder", "boxer", "guarani", "rabdan", "pars", "boragh"]):
                sub_title = "🚛 *خودروهای رزمی پیاده‌نظام و نفربرها*"
                sort_order = 502
            else:
                sub_title = "🚙 *خودروهای زرهی تاکتیکی و ضدکمین (MRAP)*"
                sort_order = 503

        elif eq_cat == "UAV":
            sub_title = "🛩️ *پهپادهای رزمی و شناسایی*"
            sort_order = 601

        elif eq_cat == "Artillery":
            sub_title = "🎯 *توپخانه و راکت‌اندازها*"
            sort_order = 701

        else:
            cat_name = config.ASSET_CATEGORIES.get(eq_cat, (eq_cat, ""))[0]
            sub_title = f"📦 *{cat_name}*"
            sort_order = 801

        grouped.setdefault(sort_order, {"title": sub_title, "items": []})["items"].append(item)

    return grouped


async def show_assets_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)

    if not country:
        pending = db.get_pending_request_by_player(user_id)
        if pending:
            p_key = pending.get("country_key", "")
            p_info = config.COUNTRIES.get(p_key, {})
            flag = p_info.get("flag", "🏳️")
            name = p_info.get("name", p_key)
            msg = f"⏳ **درخواست رهبری کشور {flag} {name} در صف بررسی ادمین است.**\n\nپس از تایید ادمین، دارایی‌های نظامی فعال می‌شوند."
        else:
            msg = "❌ شما هنوز کشوری در بازی ندارید! برای شروع /start را بزنید."
        if update.message:
            await update.message.reply_text(msg, parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.answer("هنوز کشوری نساختی!", show_alert=True)
        return

    if country.get("country_key"):
        db.seed_country_assets(country["id"], country["country_key"])

    text = f"{country['flag']} *{country['name']} — دارایی‌های نظامی اختصاصی*\n\nبرای مشاهده تجهیزات موجود، دسته مورد نظر را انتخاب کنید:"

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
        await query.edit_message_text("کشور شما یافت نشد!", parse_mode="Markdown")
        return

    if country.get("country_key"):
        db.seed_country_assets(country["id"], country["country_key"])

    category = query.data.split(":", 1)[1]
    assets = db.get_country_assets(country["id"], category)

    if category == "all":
        cat_title = "آمار کلی دارایی‌های نظامی"
    else:
        cat_info = config.ASSET_CATEGORIES.get(category, (category, "عدد"))
        cat_title = cat_info[0]

    lines = [f"{country['flag']} *{country['name']} — {cat_title}*\n"]

    if not assets:
        lines.append("هیچ تجهیزی در این دسته یافت نشد.")
    else:
        grouped = subcategorize_assets(category, assets)
        for sort_key in sorted(grouped.keys()):
            sub_group = grouped[sort_key]
            sub_title = sub_group["title"]
            sub_items = sub_group["items"]

            lines.append(f"{sub_title}:")

            for item in sub_items:
                unit = config.ASSET_CATEGORIES.get(item["category"], ("", "عدد"))[1]
                lines.append(f"• *{item['equipment_name']}*: {format_number(item['amount'])} {unit}")

            lines.append("") # Blank line spacing between subcategories

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
        await query.edit_message_text("کشور شما یافت نشد!", parse_mode="Markdown")
        return

    text = f"{country['flag']} *{country['name']} — دارایی‌های نظامی اختصاصی*\n\nبرای مشاهده تجهیزات موجود، دسته مورد نظر را انتخاب کنید:"

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
        CallbackQueryHandler(assets_back_callback, pattern=r"^(?:assets_back|assets:menu)$"),
    ]