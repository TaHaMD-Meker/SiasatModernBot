# -*- coding: utf-8 -*-
"""
فروشگاه بازی (Shop): خرید غیرنظامی (ساختمان، صنعت، نیروگاه) و خرید اختصاصی تجهیزات نظامی هر کشور (Country Assets).
بررسی موجودی خزانه و خرید اتومیک جهت پیشگیری از منفی شدن خزانه.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database as db
import config
from utils import format_money, format_number

CIVILIAN_CATEGORIES = {
    "buildings": ("🏠 ساختمان‌ها", config.BUILDINGS),
    "factories": ("🏭 صنعت", config.FACTORIES),
    "power":     ("⚡ انرژی", config.POWER_PLANTS),
}


async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        await update.message.reply_text("هنوز کشوری نساختی! برای شروع /start رو بزن.")
        return

    # تضمین وجود دارایی‌های نظامی اختصاصی کشور
    db.seed_country_assets(country["id"], country["country_key"])

    buttons = [
        [InlineKeyboardButton("🪖 تجهیزات و تسلیحات نظامی اختصاصی", callback_data="shopcat:military_assets")],
        [InlineKeyboardButton("🏠 ساختمان‌ها", callback_data="shopcat:buildings")],
        [InlineKeyboardButton("🏭 صنعت و کارخانجات", callback_data="shopcat:factories")],
        [InlineKeyboardButton("⚡ نیروگاه‌های انرژی", callback_data="shopcat:power")],
    ]

    text = (
        f"🏪 **فروشگاه ملی کشور {country['flag']} {country['name']}**\n"
        f"🏦 موجودی خزانه: **{format_money(country['treasury'])}**\n\n"
        "لطفاً دسته مورد نظر را جهت خرید انتخاب کنید:"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    cat_key = query.data.split(":", 1)[1]

    user_id = query.from_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        await query.edit_message_text("کشور یافت نشد.")
        return

    # اگر انتخاب تجهیزات نظامی اختصاصی کشور باشد
    if cat_key == "military_assets":
        buttons = [
            [
                InlineKeyboardButton("✈️ نیروی هوایی", callback_data="shop_asset_cat:Aircraft"),
                InlineKeyboardButton("🚀 موشکی", callback_data="shop_asset_cat:Missiles"),
            ],
            [
                InlineKeyboardButton("🛡️ پدافند هوایی", callback_data="shop_asset_cat:Air Defense"),
                InlineKeyboardButton("🚢 نیروی دریایی", callback_data="shop_asset_cat:Navy"),
            ],
            [
                InlineKeyboardButton("🚛 نیروی زمینی", callback_data="shop_asset_cat:Ground Forces"),
                InlineKeyboardButton("🛩️ پهپادها", callback_data="shop_asset_cat:UAV"),
            ],
            [
                InlineKeyboardButton("🎯 توپخانه", callback_data="shop_asset_cat:Artillery"),
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی اصلی فروشگاه", callback_data="shopback")],
        ]
        text = f"🪖 **تجهیزات و تسلیحات نظامی اختصاصی کشور {country['flag']} {country['name']}**\n\nیک دسته‌بندی نظامی را انتخاب کنید:"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
        return

    # خریدهای غیرنظامی (ساختمان، صنعت، نیروگاه)
    if cat_key in CIVILIAN_CATEGORIES:
        label, items = CIVILIAN_CATEGORIES[cat_key]
        buttons = []
        for item_key, item in items.items():
            buttons.append([InlineKeyboardButton(
                f"{item['name']} — {format_money(item['price'])}",
                callback_data=f"buyciv:{item_key}"
            )])
        buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="shopback")])

        await query.edit_message_text(f"🏪 {label}\n\nکالای مورد نظر رو انتخاب کن:", reply_markup=InlineKeyboardMarkup(buttons))


async def show_military_asset_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data.split(":", 1)[1]

    user_id = query.from_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        await query.edit_message_text("کشور یافت نشد.")
        return

    assets = db.get_country_assets(country["id"], category)
    cat_info = config.ASSET_CATEGORIES.get(category, (category, "عدد"))

    buttons = []
    for item in assets:
        btn_label = f"{item['equipment_name']} — {format_money(item['buy_price'])} (موجود: {format_number(item['amount'])})"
        buttons.append([InlineKeyboardButton(btn_label, callback_data=f"confirm_asset_buy:{item['equipment_key']}")])

    buttons.append([InlineKeyboardButton("🔙 بازگشت به دسته‌های نظامی", callback_data="shopcat:military_assets")])

    text = f"{country['flag']} **تسلیحات {cat_info[0]} اختصاصی {country['name']}**\n\nبرای خرید، روی سلاح مورد نظر کلیک کنید:"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def back_to_shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await shop(update, context)


async def confirm_asset_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    equipment_key = query.data.split(":", 1)[1]

    user_id = query.from_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        await query.edit_message_text("کشور یافت نشد.")
        return

    asset = db.get_asset_by_key(country["id"], equipment_key)
    if not asset:
        await query.edit_message_text("این تجهیز برای کشور شما تعریف نشده است.")
        return

    unit = config.ASSET_CATEGORIES.get(asset["category"], ("", "عدد"))[1]

    text = (
        f"🛒 **خرید تجهیز نظامی:** {asset['equipment_name']}\n"
        f"💰 **قیمت هر واحد:** {format_money(asset['buy_price'])}\n"
        f"📦 **موجودی فعلی کشور شما:** {format_number(asset['amount'])} {unit}\n"
        f"🏦 **موجودی خزانه:** {format_money(country['treasury'])}\n\n"
        "تعداد مورد نظر برای خرید را انتخاب کنید:"
    )

    buttons = [
        [
            InlineKeyboardButton("خرید ۱ عدد", callback_data=f"do_asset_buy:{equipment_key}:1"),
            InlineKeyboardButton("خرید ۵ عدد", callback_data=f"do_asset_buy:{equipment_key}:5"),
            InlineKeyboardButton("خرید ۱۰ عدد", callback_data=f"do_asset_buy:{equipment_key}:10"),
        ],
        [
            InlineKeyboardButton("❌ انصراف و بازگشت", callback_data="shopcat:military_assets"),
        ]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def execute_asset_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split(":")
    if len(parts) != 3:
        await query.edit_message_text("درخواست نامعتبر است.")
        return

    equipment_key = parts[1]
    quantity = int(parts[2])

    user_id = query.from_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        await query.edit_message_text("کشور یافت نشد.")
        return

    # اجرای خرید اتومیک
    success, msg, updated_asset = db.buy_country_asset_transaction(country["id"], equipment_key, quantity)

    if not success:
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به فروشگاه", callback_data="shopcat:military_assets")]]
        await query.edit_message_text(f"❌ **خرید انجام نشد:**\n\n{msg}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    db.add_log(actor=str(user_id), action="asset_purchase", details=f"{equipment_key} x{quantity}")

    updated_country = db.get_country_by_player(user_id)
    unit = config.ASSET_CATEGORIES.get(updated_asset["category"], ("", "عدد"))[1]
    total_cost = updated_asset["buy_price"] * quantity

    text = (
        f"✅ **خرید با موفقیت انجام شد!**\n\n"
        f"🛒 **تجهیز:** {updated_asset['equipment_name']} (تعداد: {quantity} {unit})\n"
        f"💰 **مبلغ کسر شده:** {format_money(total_cost)}\n"
        f"📦 **موجودی جدید شما:** {format_number(updated_asset['amount'])} {unit}\n"
        f"🏦 **موجودی جدید خزانه:** {format_money(updated_country['treasury'])}"
    )

    keyboard = [
        [InlineKeyboardButton("🛍️ ادامه خرید نظامی", callback_data="shopcat:military_assets")],
        [InlineKeyboardButton("🏪 بازگشت به منوی اصلی فروشگاه", callback_data="shopback")],
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ---------- خریدهای غیرنظامی ----------

async def confirm_civilian_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    item_key = query.data.split(":", 1)[1]
    item = config.ALL_SHOP_ITEMS.get(item_key)
    if not item:
        await query.edit_message_text("این کالا در دسترس نیست.")
        return

    buttons = [
        [InlineKeyboardButton("✅ تأیید خرید (۱ عدد)", callback_data=f"docivbuy:{item_key}:1")],
        [InlineKeyboardButton("❌ لغو", callback_data="shopback")],
    ]
    await query.edit_message_text(
        f"خرید: {item['name']}\n💰 قیمت واحد: {format_money(item['price'])}\n\n"
        "برای خرید ۱ عدد تأیید کنید:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )


async def execute_civilian_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    success, msg = db.buy_item_transaction(country["id"], item_key, quantity, total_price, item["name"])

    if not success:
        await query.edit_message_text(f"❌ خرید انجام نشد:\n{msg}")
        return

    db.add_log(actor=str(update.effective_user.id), action="purchase", details=f"{item_key} x{quantity}")
    updated_country = db.get_country_by_player(update.effective_user.id)

    await query.edit_message_text(
        f"✅ خرید غیرنظامی با موفقیت انجام شد!\n\n"
        f"🛒 {item['name']} x{quantity}\n"
        f"💰 مبلغ کسر شده: {format_money(total_price)}\n"
        f"🏦 موجودی جدید خزانه: {format_money(updated_country['treasury'])}"
    )
