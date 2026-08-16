# -*- coding: utf-8 -*-
"""
فروشگاه بازی (Shop): خرید غیرنظامی (ساختمان، صنعت، نیروگاه) و خرید اختصاصی تجهیزات نظامی بومی هر کشور (Country Assets).
فقط تجهیزاتی که دارای خط تولید بومی (producible=1) هستند در فروشگاه نمایش داده می‌شوند.
شامل بخش ساخت‌وسازهای من و پیام تایید خرید.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database as db
import config
from utils import format_money, format_number, format_oil

CIVILIAN_CATEGORIES = {
    "buildings":   ("🏠 ساختمان‌ها", config.BUILDINGS),
    "factories":   ("🏭 صنعت و کارخانجات", config.FACTORIES),
    "power":       ("⚡ نیروگاه‌های انرژی", config.POWER_PLANTS),
    "transport":   ("🚢 حمل‌ونقل و ترابری", config.TRANSPORTATION),
    "mines":       ("⛏️ منابع و معادن", config.MINES_AND_RESOURCES),
    "agriculture": ("🌾 کشاورزی و غلات", config.AGRICULTURE),
}


async def shop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        await update.message.reply_text("هنوز کشوری نساختی! برای شروع /start رو بزن.", parse_mode="Markdown")
        return

    # تضمین وجود دارایی‌های نظامی اختصاصی کشور
    if country.get("country_key"):
        db.seed_country_assets(country["id"], country["country_key"])

    buttons = [
        [InlineKeyboardButton("🏗️ ساخت‌وسازها و پروژه‌های من", callback_data="shopcat:my_constructions")],
        [InlineKeyboardButton("🪖 ساخت/خرید تسلیحات نظامی بومی", callback_data="shopcat:military_assets")],
        [InlineKeyboardButton("🏠 ساختمان‌ها", callback_data="shopcat:buildings"), InlineKeyboardButton("🏭 صنعت و کارخانجات", callback_data="shopcat:factories")],
        [InlineKeyboardButton("⚡ نیروگاه‌های انرژی", callback_data="shopcat:power"), InlineKeyboardButton("🚢 حمل‌ونقل و ترابری", callback_data="shopcat:transport")],
        [InlineKeyboardButton("⛏️ منابع و معادن", callback_data="shopcat:mines"), InlineKeyboardButton("🌾 کشاورزی و غلات", callback_data="shopcat:agriculture")],
        [InlineKeyboardButton("🔬 مرکز تحقیق و توسعه فناوری (R&D)", callback_data="research:menu")],
    ]

    text = (
        f"🏪 *فروشگاه ملی کشور {country['flag']} {country['name']}*\n"
        f"🏦 موجودی خزانه: *{format_money(country['treasury'])}*\n\n"
        "لطفاً دسته مورد نظر را جهت خرید انتخاب کنید:"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def show_my_constructions(query, country):
    """نمایش لیست پروژه‌ها و زیرساخت‌های غیرنظامی احداث‌شده کشور."""
    equipment = db.get_equipment(country["id"])

    lines = [
        f"🏗️ **ساخت‌وسازها و زیرساخت‌های کشور {country['flag']} {country['name']}**\n",
        "━━━━━━━━━━━━━━━━━━\n"
    ]

    civilian_items = {}
    for item_key, qty in equipment.items():
        if qty > 0 and item_key in config.ALL_SHOP_ITEMS:
            civilian_items[item_key] = qty

    if not civilian_items:
        lines.append("❌ هنوز هیچ پروژه زیرساختی یا ساخت‌وسازی احداث نکرده‌اید.\n")
        lines.append("💡 می‌توانید از بخش‌های مختلف فروشگاه اقدام به احداث کارخانجات، نیروگاه‌ها، بنادر، فرودگاه‌ها و معادن فرمایید.")
    else:
        lines.append("📋 **لیست پروژه‌ها و زیرساخت‌های فعال شما:**\n")
        total_income_add = 0
        total_elec_add = 0

        for item_key, qty in civilian_items.items():
            item_data = config.ALL_SHOP_ITEMS[item_key]
            name = item_data["name"]
            inc = item_data.get("income_add", 0) * qty
            elec = item_data.get("elec_add", 0) * qty

            total_income_add += inc
            total_elec_add += elec

            extra_info = []
            if inc > 0: extra_info.append(f"+{format_money(inc)}/روز")
            if elec > 0: extra_info.append(f"+{elec}٪ برق")
            info_str = f" ({' | '.join(extra_info)})" if extra_info else ""

            lines.append(f"• **{name}:** {qty:,} واحد{info_str}")

        lines.append("\n━━━━━━━━━━━━━━━━━━\n")
        lines.append("📊 **مجموع عواید پروژه‌های احداث‌شده:**")
        lines.append(f"• **درآمد روزانه زیرساخت‌ها:** +{format_money(total_income_add)}/روز")
        lines.append(f"• **تولید برق کل نیروگاه‌ها:** +{total_elec_add}٪")

    keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی اصلی فروشگاه", callback_data="shopback")]]
    await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def show_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    cat_key = query.data.split(":", 1)[1]

    user_id = query.from_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        await query.answer("کشور یافت نشد.", show_alert=True)
        return

    await query.answer()

    if cat_key == "my_constructions":
        await show_my_constructions(query, country)
        return

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
        text = f"🪖 *خط تولید تسلیحات نظامی بومی کشور {country['flag']} {country['name']}*\n\nیک دسته‌بندی نظامی را انتخاب کنید (فقط سلاح‌های دارای خط تولید بومی قابل خرید هستند):"
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
        return

    if cat_key in CIVILIAN_CATEGORIES:
        label, items = CIVILIAN_CATEGORIES[cat_key]
        buttons = []
        for item_key, item in items.items():
            buttons.append([InlineKeyboardButton(
                f"{item['name']} — {format_money(item['price'])}",
                callback_data=f"buyciv:{item_key}"
            )])
        buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="shopback")])

        await query.edit_message_text(f"🏪 {label}\n\nکالای مورد نظر رو انتخاب کن:", reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def show_military_asset_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    category = query.data.split(":", 1)[1]

    user_id = query.from_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        await query.edit_message_text("کشور یافت نشد.", parse_mode="Markdown")
        return

    # فقط سلاح‌های دارای خط تولید بومی (producible_only=True)
    assets = db.get_country_assets(country["id"], category, producible_only=True)
    cat_info = config.ASSET_CATEGORIES.get(category, (category, "عدد"))

    buttons = []
    if not assets:
        text = f"{country['flag']} *تسلیحات {cat_info[0]} بومی {country['name']}*\n\n❌ کشور شما خط تولید بومی برای تسلیحات این دسته ندارد (تجهیزات موجود شما وارداتی هستند)."
    else:
        for item in assets:
            btn_label = f"{item['equipment_name']} — {format_money(item['buy_price'])} (موجودی: {format_number(item['amount'])})"
            buttons.append([InlineKeyboardButton(btn_label, callback_data=f"confirm_asset_buy:{item['equipment_key']}")])
        text = f"{country['flag']} *خط تولید تسلیحات {cat_info[0]} بومی {country['name']}*\n\nبرای سفارش و ساخت، روی سلاح مورد نظر کلیک کنید:"

    buttons.append([InlineKeyboardButton("🔙 بازگشت به دسته‌های نظامی", callback_data="shopcat:military_assets")])
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
        await query.edit_message_text("کشور یافت نشد.", parse_mode="Markdown")
        return

    asset = db.get_asset_by_key(country["id"], equipment_key)
    if not asset:
        await query.edit_message_text("این تجهیز برای کشور شما تعریف نشده است.", parse_mode="Markdown")
        return

    if asset.get("producible", 1) != 1:
        await query.edit_message_text("⚠️ این تجهیز وارداتی است و کشور شما خط تولید بومی برای ساخت مجدد آن را ندارد.", parse_mode="Markdown")
        return

    unit = config.ASSET_CATEGORIES.get(asset["category"], ("", "عدد"))[1]

    text = (
        f"🛒 *سفارش ساخت تجهیز نظامی بومی:* {asset['equipment_name']}\n"
        f"💰 *هزینه تولید هر واحد:* {format_money(asset['buy_price'])}\n"
        f"📦 *موجودی فعلی کشور شما:* {format_number(asset['amount'])} {unit}\n"
        f"🏦 *موجودی خزانه:* {format_money(country['treasury'])}\n\n"
        "تعداد مورد نظر برای تولید را انتخاب کنید:"
    )

    buttons = [
        [
            InlineKeyboardButton("تولید ۱ عدد", callback_data=f"do_asset_buy:{equipment_key}:1"),
            InlineKeyboardButton("تولید ۵ عدد", callback_data=f"do_asset_buy:{equipment_key}:5"),
            InlineKeyboardButton("تولید ۱۰ عدد", callback_data=f"do_asset_buy:{equipment_key}:10"),
        ],
        [
            InlineKeyboardButton("❌ انصراف و بازگشت", callback_data="shopcat:military_assets"),
        ]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def execute_asset_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split(":")
    if len(parts) != 3:
        await query.answer("درخواست نامعتبر است.", show_alert=True)
        return

    equipment_key = parts[1]
    quantity = int(parts[2])

    user_id = query.from_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        await query.answer("کشور یافت نشد.", show_alert=True)
        return

    success, msg, updated_asset = db.buy_country_asset_transaction(country["id"], equipment_key, quantity)

    if not success:
        await query.answer("❌ تولید انجام نشد!", show_alert=True)
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به فروشگاه", callback_data="shopcat:military_assets")]]
        await query.edit_message_text(f"❌ **تولید انجام نشد:**\n\n{msg}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    # Popup Alert Banner Notification
    await query.answer("✅ ساخت و تولید بومی با موفقیت انجام شد!", show_alert=True)

    db.add_log(actor=str(user_id), action="asset_purchase", details=f"{equipment_key} x{quantity}")

    updated_country = db.get_country_by_player(user_id)
    unit = config.ASSET_CATEGORIES.get(updated_asset["category"], ("", "عدد"))[1]
    total_cost = updated_asset["buy_price"] * quantity

    text = (
        f"✅ *تولید با موفقیت انجام شد!*\n\n"
        f"🛒 *تجهیز بومی:* {updated_asset['equipment_name']} (تعداد: {quantity} {unit})\n"
        f"💰 *مبلغ کسر شده از خزانه:* {format_money(total_cost)}\n"
        f"📦 *موجودی جدید کشور شما:* {format_number(updated_asset['amount'])} {unit}\n"
        f"🏦 *موجودی جدید خزانه:* {format_money(updated_country['treasury'])}"
    )

    keyboard = [
        [InlineKeyboardButton("🛍️ ادامه تولید نظامی", callback_data="shopcat:military_assets")],
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
        await query.edit_message_text("این پروژه در دسترس نیست.", parse_mode="Markdown")
        return

    buttons = [
        [InlineKeyboardButton("✅ تأیید و احداث پروژه (۱ عدد)", callback_data=f"docivbuy:{item_key}:1")],
        [InlineKeyboardButton("🔙 بازگشت به فروشگاه", callback_data="shopback")],
    ]

    desc_text = item.get("desc", f"🏗️ *پروژه:* {item['name']}\n\n💰 *هزینه احداث:* {format_money(item['price'])}")

    await query.edit_message_text(
        desc_text,
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown"
    )


async def execute_civilian_purchase(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    parts = query.data.split(":")
    if len(parts) != 3:
        await query.answer("داده‌های درخواست نامعتبر است.", show_alert=True)
        return

    item_key = parts[1]
    quantity = int(parts[2])

    country = db.get_country_by_player(update.effective_user.id)
    item = config.ALL_SHOP_ITEMS.get(item_key)
    if not country or not item:
        await query.answer("خطا در انجام عملیات.", show_alert=True)
        return

    total_price = item["price"] * quantity
    success, msg = db.buy_item_transaction(country["id"], item_key, quantity, total_price, item["name"])

    if not success:
        await query.answer("❌ عملیات احداث انجام نشد!", show_alert=True)
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به فروشگاه", callback_data="shopback")]]
        await query.edit_message_text(
            f"❌ *عملیات احداث انجام نشد:*\n\n{msg}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return

    # Popup Alert Banner Notification
    await query.answer("✅ پروژه با موفقیت احداث و خریداری گردید!", show_alert=True)

    db.add_log(actor=str(update.effective_user.id), action="civilian_purchase", details=f"{item_key} x{quantity}")
    updated_country = db.get_country_by_player(update.effective_user.id)

    oil_req = item.get("oil_req", 0) * quantity
    income_add = item.get("income_add", 0) * quantity
    elec_add = item.get("elec_add", 0) * quantity

    benefit_lines = []
    if oil_req > 0:
        benefit_lines.append(f"🛢️ *نفت کسرشده:* {format_oil(oil_req)}")
    if income_add > 0:
        benefit_lines.append(f"💵 *افزایش درآمد روزانه:* +{format_money(income_add)}/روز")
    if elec_add > 0:
        benefit_lines.append(f"⚡ *تولید انرژی افزوده‌شده:* +{elec_add}٪")

    benefits_str = "\n".join(benefit_lines) if benefit_lines else "✅ پروژه با موفقیت در دیتابیس ثبت شد."

    text = (
        f"✅ *پروژه با موفقیت ساخته و ثبت شد!*\n\n"
        f"🏗️ *نام پروژه:* {item['name']}\n"
        f"💰 *مبلغ کسر شده از خزانه:* {format_money(total_price)}\n"
        f"{benefits_str}\n\n"
        f"🏦 *موجودی جدید خزانه:* {format_money(updated_country['treasury'])}\n"
        f"⚡ *تراز جدید برق:* {updated_country['electricity']}٪\n"
        f"📈 *درآمد روزانه جدید:* {format_money(updated_country['daily_income'])}"
    )

    keyboard = [
        [InlineKeyboardButton("🏗️ مشاهده ساخت‌وسازهای من", callback_data="shopcat:my_constructions")],
        [InlineKeyboardButton("🏪 بازگشت به فروشگاه", callback_data="shopback")],
    ]

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )