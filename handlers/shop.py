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
        [InlineKeyboardButton("📈 بازار بورس بین‌المللی کالاها (طلا، نفت، غلات، اورانیوم)", callback_data="market:menu")],
        [InlineKeyboardButton("🏗️ ساخت‌وسازها و پروژه‌های من", callback_data="shopcat:my_constructions")],
        [InlineKeyboardButton("🪖 ساخت/خرید تسلیحات نظامی بومی", callback_data="shopcat:military_assets")],
        [InlineKeyboardButton("🏠 ساختمان‌ها", callback_data="shopcat:buildings"), InlineKeyboardButton("🏭 صنعت و کارخانجات", callback_data="shopcat:factories")],
        [InlineKeyboardButton("⚡ نیروگاه‌های انرژی", callback_data="shopcat:power"), InlineKeyboardButton("🚢 حمل‌ونقل و ترابری", callback_data="shopcat:transport")],
        [InlineKeyboardButton("⛏️ منابع و معادن", callback_data="shopcat:mines"), InlineKeyboardButton("🌾 کشاورزی و غلات", callback_data="shopcat:agriculture")],
        [InlineKeyboardButton("🚀 مرکز تسلیحات راهبردی و کلاهک بازدارنده", callback_data="shopcat:warheads")],
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
        lines.append("💡 می‌توانید از بخش‌های مختلف فروشگاه اقدام به احداث کارخانجات، نیروگاه‌ها، بنادر، فرودگاه‌ها، مزارع و معادن فرمایید.")
    else:
        lines.append("📋 **لیست پروژه‌ها و زیرساخت‌های فعال شما:**\n")
        total_income_add = 0
        total_elec_add = 0
        total_grain_daily_add = 0
        total_gold_daily_add = 0
        total_oil_prod_add = 0
        total_chips_daily_add = 0

        for item_key, qty in civilian_items.items():
            item_data = config.ALL_SHOP_ITEMS[item_key]
            name = item_data["name"]
            inc = item_data.get("income_add", 0) * qty
            if item_key == "oil_refinery":
                inc = config.get_refinery_effect(country.get("country_key")).get("income", inc) * qty
            elif item_key == "chip_fab":
                inc = config.get_chip_fab_effect(country.get("country_key")).get("income", inc) * qty
            elec = item_data.get("elec_add", 0) * qty
            grain = item_data.get("grain_daily_add", 0) * qty
            gold = item_data.get("gold_daily_add", 0) * qty
            oil = item_data.get("oil_prod_add", 0) * qty
            chips = item_data.get("chips_daily_add", 0) * qty
            if item_key == "oil_refinery":
                oil = config.get_refinery_effect(country.get("country_key")).get("oil_prod", oil) * qty
            elif item_key == "chip_fab":
                chips = config.get_chip_fab_effect(country.get("country_key")).get("chips_daily", 25) * qty

            total_income_add += inc
            total_elec_add += elec
            total_grain_daily_add += grain
            total_gold_daily_add += gold
            total_oil_prod_add += oil
            total_chips_daily_add += chips

            extra_info = []
            if inc > 0: extra_info.append(f"+{format_money(inc)}/روز")
            if elec > 0: extra_info.append(f"+{elec}٪ برق")
            if grain > 0: extra_info.append(f"+{format_number(grain)} تن غلات/روز")
            if gold > 0: extra_info.append(f"+{gold} شمش طلا/روز")
            if oil > 0: extra_info.append(f"+{format_oil(oil)}")
            if chips > 0: extra_info.append(f"+{format_number(chips)} تراشه/روز")
            info_str = f" ({' | '.join(extra_info)})" if extra_info else ""

            lines.append(f"• **{name}:** {qty:,} واحد{info_str}")

        lines.append("\n━━━━━━━━━━━━━━━━━━\n")
        lines.append("📊 **مجموع عواید پروژه‌های احداث‌شده:**")
        lines.append(f"• **درآمد روزانه زیرساخت‌ها:** +{format_money(total_income_add)}/روز")
        if total_elec_add > 0:
            lines.append(f"• **تولید برق کل نیروگاه‌ها:** +{total_elec_add}٪")
        if total_grain_daily_add > 0:
            lines.append(f"• **تولید غلات کل مزارع:** +{format_number(total_grain_daily_add)} تن/روز")
        if total_gold_daily_add > 0:
            lines.append(f"• **تولید طلا کل معادن:** +{total_gold_daily_add} شمش/روز")
        if total_oil_prod_add > 0:
            lines.append(f"• **تولید نفت کل پالایشگاه‌ها:** +{format_oil(total_oil_prod_add)}")
        if total_chips_daily_add > 0:
            lines.append(f"• **تولید تراشه کل کارخانجات فب:** +{format_number(total_chips_daily_add)} عدد/روز")

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

    if cat_key == "warheads":
        await show_warheads_menu(query, country)
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
        equipment = db.get_equipment(country["id"])
        buttons = []
        for item_key, item in items.items():
            curr_qty = equipment.get(item_key, 0)
            max_limit = item.get("max_limit", 10)
            status_str = f"({curr_qty}/{max_limit})"
            if curr_qty >= max_limit:
                btn_label = f"🔒 {item['name']} — {status_str} [تکمیل سقف]"
            else:
                btn_label = f"{item['name']} — {format_money(item['price'])} {status_str}"

            buttons.append([InlineKeyboardButton(btn_label, callback_data=f"buyciv:{item_key}")])

        buttons.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی فروشگاه", callback_data="shopback")])
        await query.edit_message_text(f"🏪 *{label}*\n\nکالای مورد نظر جهت احداث را انتخاب کنید (تعداد احداث‌شده در پرانتز مشخص است):", reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


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
    chips_req = config.get_equipment_chips_req(asset)
    chips_line = ""
    if chips_req > 0:
        curr_chips = country.get("microchips", 0) or 0
        status_c = "✅" if curr_chips >= chips_req else "⚠️ کسری"
        chips_line = f"\n💻 *تراشه پردازشی مورد نیاز:* {chips_req} عدد/واحد ({status_c} موجودی شما: {format_number(curr_chips)})"

    text = (
        f"🛒 *سفارش ساخت تجهیز نظامی بومی:* {asset['equipment_name']}\n"
        f"💰 *هزینه تولید هر واحد:* {format_money(asset['buy_price'])}{chips_line}\n"
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

    country = db.get_country_by_player(update.effective_user.id)
    if country:
        equipment = db.get_equipment(country["id"])
        curr_qty = equipment.get(item_key, 0)
        max_limit = item.get("max_limit", 10)
        if curr_qty >= max_limit:
            await query.edit_message_text(
                f"🔒 **سقف مجاز احداث این پروژه پر شده است!**\n\n"
                f"• **پروژه:** {item['name']}\n"
                f"• **سقف مجاز:** {max_limit} واحد\n"
                f"• **احداث‌شده شما:** {curr_qty} واحد\n\n"
                "شما نمی‌توانید بیش از سقف تعیین‌شده اقدام به احداث این پروژه بفرمایید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به فروشگاه", callback_data="shopback")]]),
                parse_mode="Markdown"
            )
            return

    buttons = [
        [InlineKeyboardButton("✅ تأیید و احداث پروژه (۱ عدد)", callback_data=f"docivbuy:{item_key}:1")],
        [InlineKeyboardButton("🔙 بازگشت به فروشگاه", callback_data="shopback")],
    ]

    desc_text = item.get("desc", f"🏗️ *پروژه:* {item['name']}\n\n💰 *هزینه احداث:* {format_money(item['price'])}")
    if item_key == "oil_refinery" and country and not config.is_oil_country(country.get("country_key")):
        desc_text += (
            "\n\n⚠️ *توجه — کشور غیرنفتی:* به دلیل نداشتن میدان نفتی، در کشور شما هر پالایشگاه "
            "*+۲۵,۰۰۰ بشکه/روز* تولید نفت و *+۶۰۰,۰۰۰ دلار/روز* درآمد دارد "
            "(به‌جای +۱۰۰,۰۰۰ بشکه و +۷۵۰,۰۰۰ دلار برای کشورهای نفتی)."
        )
    elif item_key == "chip_fab" and country:
        fab_eff = config.get_chip_fab_effect(country.get("country_key", ""))
        desc_text += (
            f"\n\n💻 *بازدهی فب برای کشور شما ({country['flag']} {country['name']}):*\n"
            f"• *تولید روزانه تراشه:* +{fab_eff['chips_daily']:,} عدد/روز به ازای هر کارخانه\n"
            f"• *درآمد روزانه:* +{format_money(fab_eff['income'])}/روز"
        )
    desc_text += f"\n📊 *تعداد احداث‌شده فعلی شما:* {curr_qty}/{max_limit} واحد"

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

    equipment = db.get_equipment(country["id"])
    curr_qty = equipment.get(item_key, 0)
    max_limit = item.get("max_limit", 10)

    if curr_qty + quantity > max_limit:
        await query.answer("❌ سقف مجاز احداث این پروژه پر شده است!", show_alert=True)
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به فروشگاه", callback_data="shopback")]]
        await query.edit_message_text(
            f"🔒 **سقف مجاز احداث این پروژه پر شده است!**\n\n"
            f"• **نام پروژه:** {item['name']}\n"
            f"• **سقف مجاز احداث:** {max_limit} واحد\n"
            f"• **تعداد احداث‌شده فعلی شما:** {curr_qty} واحد\n\n"
            f"شما نمی‌توانید بیش از {max_limit} واحد از این پروژه را در کشور خود احداث فرمایید.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
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
    gold_daily_add = item.get("gold_daily_add", 0) * quantity
    oil_prod_add = item.get("oil_prod_add", 0) * quantity
    grain_daily_add = item.get("grain_daily_add", 0) * quantity
    grain_bonus = item.get("grain_bonus", 0) * quantity

    if item_key == "oil_refinery" and country.get("country_key"):
        eff = config.get_refinery_effect(country["country_key"])
        income_add = eff["income"] * quantity
        oil_prod_add = eff["oil_prod"] * quantity

    benefit_lines = []
    if income_add > 0:
        benefit_lines.append(f"💵 *افزایش درآمد روزانه:* +{format_money(income_add)}/روز")
    if elec_add > 0:
        benefit_lines.append(f"⚡ *تولید انرژی افزوده‌شده:* +{elec_add}٪")
    if grain_daily_add > 0:
        benefit_lines.append(f"🌾 *تولید روزانه غلات افزوده‌شده:* +{format_number(grain_daily_add)} تن/روز")
    if grain_bonus > 0:
        benefit_lines.append(f"🌾 *ذخیره فوری غلات:* +{format_number(grain_bonus)} تن")
    if gold_daily_add > 0:
        benefit_lines.append(f"🪙 *تولید روزانه طلا افزوده‌شده:* +{gold_daily_add} شمش/روز")
    if oil_prod_add > 0:
        benefit_lines.append(f"🛢️ *تولید روزانه نفت افزوده‌شده:* +{format_oil(oil_prod_add)}")
    if item_key == "chip_fab" and country.get("country_key"):
        chips_add = config.get_chip_fab_effect(country["country_key"]).get("chips_daily", 25) * quantity
        benefit_lines.append(f"💻 *تولید روزانه تراشه افزوده‌شده:* +{format_number(chips_add)} عدد/روز")
    if oil_req > 0:
        benefit_lines.append(f"🛢️ *سوخت مصرفی ساخت:* -{format_oil(oil_req)}")

    benefits_str = "\n".join(benefit_lines) if benefit_lines else "✅ پروژه با موفقیت در دیتابیس ثبت شد."

    status_lines = [
        f"🏦 *موجودی جدید خزانه:* {format_money(updated_country['treasury'])}",
        f"⚡ *تراز جدید برق:* {updated_country['electricity']}٪",
        f"📈 *درآمد روزانه جدید:* {format_money(updated_country['daily_income'])}",
    ]
    if (updated_country.get("grain_daily") or 0) > 0:
        status_lines.append(f"🌾 *تولید روزانه غلات:* +{format_number(updated_country.get('grain_daily'))} تن/روز")
    if (updated_country.get("gold_daily") or 0) > 0:
        status_lines.append(f"🪙 *تولید روزانه طلا:* +{updated_country.get('gold_daily')} شمش/روز")
    if (updated_country.get("microchips_daily") or 0) > 0:
        status_lines.append(f"💻 *تولید روزانه تراشه:* +{format_number(updated_country.get('microchips_daily'))} عدد/روز")

    text = (
        f"✅ *پروژه با موفقیت ساخته و ثبت شد!*\n\n"
        f"🏗️ *نام پروژه:* {item['name']} (تعداد: {quantity} واحد)\n"
        f"💰 *مبلغ کسر شده از خزانه:* {format_money(total_price)}\n\n"
        f"📊 *دستاوردها و عواید:* \n"
        f"{benefits_str}\n\n" +
        "\n".join(status_lines)
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

async def show_warheads_menu(query, country):
    """منوی مرکز تسلیحات راهبردی و کلاهک بازدارنده هسته‌ای."""
    tech_lvl = country.get("tech_level", 1) or 1
    warheads_count = country.get("warheads", 0) or 0
    u_ore = country.get("uranium_ore", 0) or 0
    chips = country.get("microchips", 0) or 0
    gold = country.get("gold", 0) or 0
    treasury = country.get("treasury", 0) or 0

    equipment = db.get_equipment(country["id"])
    has_enrichment = (equipment.get("enrichment_facility", 0) or 0) > 0
    is_p5 = country.get("country_key") in ("usa", "russia", "china", "france", "uk", "pakistan", "india", "israel", "north_korea")

    text = (
        f"🚀 **مرکز تسلیحات راهبردی و بازدارندگی هسته‌ای — {country['flag']} {country['name']}**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"• **تعداد کلاهک‌های راهبردی مستقر:** ☢️ **{warheads_count:,} عدد**\n"
        f"• **هزینه نگهداری فعلی زرادخانه:** {format_money(warheads_count * 5_000_000)}/روز + {warheads_count * 2} میکروچیپ/روز\n\n"
        "🔬 **شرایط و الزامات مونتاژ کلاهک جدید:**\n"
        f"• سطح فناوری: **سطح ۵** ({'✅' if tech_lvl >= 5 else '❌ سطح فعلی: ' + str(tech_lvl)})\n"
        f"• مجتمع غنی‌سازی سانتریفیوژ: **حداقل ۱ واحد** ({'✅' if has_enrichment or is_p5 else '❌ فاقد مجتمع غنی‌سازی'})\n"
        f"• هزینه مالی: **۱۵۰ میلیون دلار** ({'✅' if treasury >= 150_000_000 else '❌ موجودی: ' + format_money(treasury)})\n"
        f"• شمش طلا: **۱۰۰ شمش** ({'✅' if gold >= 100 else '❌ موجودی: ' + str(gold)})\n"
        f"• تراشه میکروچیپ: **۵۰۰ عدد** ({'✅' if chips >= 500 else '❌ موجودی: ' + str(chips)})\n"
        f"• کیک زرد اورانیوم: **۵۰۰ تن** ({'✅' if u_ore >= 500 else '❌ موجودی: ' + str(u_ore)})\n\n"
        "⚠️ **قوانین بازدارندگی و ایمنی بین‌المللی:**\n"
        "۱. هرگونه مونتاژ کلاهک هسته‌ای با هشدار اطلاعاتی بین‌المللی همراه خواهد بود.\n"
        "۲. نگهداری کلاهک روزانه ۵ میلیون دلار و ۲ تراشه هزینه مستقیم دارد.\n"
        "۳. سقف نگهداری برای کشورهای غیرابرقدرت حداکثر ۵ کلاهک بازدارنده است."
    )

    buttons = [
        [InlineKeyboardButton("☢️ مونتاژ و مسلح‌سازی ۱ کلاهک راهبردی", callback_data="shop:do_assemble_warhead")],
        [InlineKeyboardButton("🔙 بازگشت به فروشگاه", callback_data="shopback")],
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def execute_warhead_assembly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    country = db.get_country_by_player(update.effective_user.id)
    if not country:
        return

    ok, msg = db.assemble_nuclear_warhead_transaction(country["id"])
    if not ok:
        await query.edit_message_text(
            f"❌ **عدم امکان مونتاژ کلاهک هسته‌ای:**\n\n{msg}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="shopcat:warheads")]]),
            parse_mode="Markdown"
        )
        return

    # Broadcast intelligence alert if appropriate
    try:
        import news_engine
        await news_engine.trigger_general_broadcast(
            context.bot,
            f"🚨 **گزارش محرمانه اطلاعاتی و هشدار آژانس بین‌المللی انرژی اتمی**\n\n"
            f"کشور {country['flag']} **{country['name']}** یک کلاهک راهبردی هسته‌ای جدید را با موفقیت مونتاژ و در سیلوهای راهبردی خود مستقر کرد."
        )
    except Exception:
        pass

    await query.edit_message_text(
        f"{msg}\n\n🌐 کلاهک در زرادخانه استراتژیک کشور مستقر گردید.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به مرکز راهبردی", callback_data="shopcat:warheads")]]),
        parse_mode="Markdown"
    )
