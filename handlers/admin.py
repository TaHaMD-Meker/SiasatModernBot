# -*- coding: utf-8 -*-
"""
پنل ادمین پیشرفته و تعاملی با دکمه‌های شیشه‌ای (Inline Buttons).
مدیریت کامل کشورها، خزانه، طلا، نفت، تجهیزات و دارایی‌های اختصاصی نظامی (Country Assets).
"""

import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

import database as db
import config
from utils import format_money, format_number, format_oil


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


# ==================== منوی اصلی ادمین ====================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ این بخش فقط برای ادمین اصلی بازی مجاز است.")
        return

    text = "👑 **پنل مدیریت بازی «سیاست مدرن»**\n\nلطفاً یک گزینه را انتخاب کنید:"
    keyboard = [
        [InlineKeyboardButton("📋 مدیریت و لیست کشورها", callback_data="admin:list:0")],
        [InlineKeyboardButton("📊 آمار کلی بازی", callback_data="admin:stats")],
        [InlineKeyboardButton("⚡ توزیع فوری درآمد روزانه", callback_data="admin:daily_income")],
        [InlineKeyboardButton("📢 ارسال پیام همگانی (Broadcast)", callback_data="admin:broadcast_prompt")],
        [InlineKeyboardButton("❌ بستن پنل", callback_data="admin:close")],
    ]

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== لیست کشورها با صفحه‌بندی ====================

async def show_countries_list(query, context, page: int = 0):
    countries = db.get_all_countries()
    if not countries:
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]]
        await query.edit_message_text("❌ هنوز هیچ کشوری در بازی ساخته نشده است.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    per_page = 5
    total_pages = math.ceil(len(countries) / per_page)
    page = max(0, min(page, total_pages - 1))

    start_idx = page * per_page
    page_countries = countries[start_idx:start_idx + per_page]

    keyboard = []
    for c in page_countries:
        btn_text = f"{c['flag']} {c['name']} | 🏦 {format_money(c['treasury'])} (ID: {c['player_id']})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"admin:c:{c['id']}")])

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:list:{page - 1}"))
    nav_row.append(InlineKeyboardButton(f"صفحه {page + 1} از {total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:list:{page + 1}"))

    keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data="admin:menu")])

    text = f"📋 **لیست کشورهای فعال (تعداد کل: {len(countries)})**\n\nبرای مشاهده یا تغییر جزئیات، روی کشور مورد نظر کلیک کنید:"
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== داشبورد اختصاصی مدیریت یک کشور ====================

async def show_country_dashboard(query, context, country_id: int, notice: str = ""):
    c = db.get_country_by_id(country_id)
    if not c:
        await query.edit_message_text("❌ این کشور پیدا نشد یا قبلاً حذف شده است.",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:list:0")]]))
        return

    # تضمین وجود دارایی‌های نظامی کشور
    if c.get("country_key"):
        db.seed_country_assets(c["id"], c["country_key"])

    assets = db.get_country_assets(country_id)
    asset_summary = []
    for a in assets[:5]: # ۵ دارایی اول
        unit = config.ASSET_CATEGORIES.get(a['category'], ("", "عدد"))[1]
        asset_summary.append(f"  • {a['equipment_name']}: {format_number(a['amount'])} {unit}")

    if len(assets) > 5:
        asset_summary.append(f"  • ... و {len(assets) - 5} تجهیز دیگر")

    eq_text = "\n".join(asset_summary) if asset_summary else "  • بدون دارایی نظامی"

    text = (
        f"{notice}\n\n" if notice else ""
    ) + (
        f"🌐 **مدیریت کشور {c['flag']} {c['name']}**\n"
        f"👤 شناسه تلگرام بازیکن: `{c['player_id']}`\n"
        f"🔑 کلید کشور: `{c['country_key'] or 'نامشخص'}`\n\n"
        f"👥 جمعیت: {format_number(c['population'])}\n"
        f"🏦 خزانه: {format_money(c['treasury'])}\n"
        f"🪙 طلا: {format_number(c['gold'])}\n"
        f"📈 درآمد روزانه: {format_money(c['daily_income'])}\n\n"
        f"🛢️ ذخایر نفت: {format_oil(c['oil_reserves'])}\n"
        f"🛢️ نرخ تولید نفت: {format_oil(c['oil_production'])}/روز\n\n"
        f"🎖️ خلاصه دارایی‌های نظامی اختصاصی:\n{eq_text}"
    )

    keyboard = [
        [
            InlineKeyboardButton("🏦 ویرایش خزانه", callback_data=f"admin:menu_treasury:{c['id']}"),
            InlineKeyboardButton("🪙 ویرایش طلا", callback_data=f"admin:menu_gold:{c['id']}"),
        ],
        [
            InlineKeyboardButton("🛢️ ویرایش نفت", callback_data=f"admin:menu_oil:{c['id']}"),
            InlineKeyboardButton("🎖️ مدیریت دارایی‌های نظامی", callback_data=f"admin:menu_assets:{c['id']}"),
        ],
        [
            InlineKeyboardButton("✉️ ارسال پیام مستقیم به بازیکن", callback_data=f"admin:msg_prompt:{c['id']}"),
        ],
        [
            InlineKeyboardButton("🗑️ حذف کامل کشور", callback_data=f"admin:delconfirm:{c['id']}"),
        ],
        [
            InlineKeyboardButton("🔙 بازگشت به لیست کشورها", callback_data="admin:list:0"),
        ]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== زیرمنوهای تغییر خزانه، طلا، نفت و دارایی‌های نظامی ====================

async def menu_treasury(query, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return
    text = f"🏦 **تغییر خزانه کشور {c['flag']} {c['name']}**\nموجودی فعلی: {format_money(c['treasury'])}\n\nیکی از مقادیر زیر را انتخاب کنید یا مقدار دلخواه تایپ کنید:"

    keyboard = [
        [
            InlineKeyboardButton("➕ ۱۰ میلیون", callback_data=f"admin:adj:{c['id']}:treasury:10000000"),
            InlineKeyboardButton("➕ ۵۰ میلیون", callback_data=f"admin:adj:{c['id']}:treasury:50000000"),
            InlineKeyboardButton("➕ ۱۰۰ میلیون", callback_data=f"admin:adj:{c['id']}:treasury:100000000"),
        ],
        [
            InlineKeyboardButton("➖ ۱۰ میلیون", callback_data=f"admin:adj:{c['id']}:treasury:-10000000"),
            InlineKeyboardButton("➖ ۵۰ میلیون", callback_data=f"admin:adj:{c['id']}:treasury:-50000000"),
            InlineKeyboardButton("➖ ۱۰۰ میلیون", callback_data=f"admin:adj:{c['id']}:treasury:-100000000"),
        ],
        [
            InlineKeyboardButton("✏️ تنظیم دقیق عدد خزانه (تایپی)", callback_data=f"admin:prompt:{c['id']}:treasury"),
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:c:{c['id']}"),
        ]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def menu_gold(query, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return
    text = f"🪙 **تغییر طلای کشور {c['flag']} {c['name']}**\nطلای فعلی: {format_number(c['gold'])}\n\nیک گزینه را انتخاب کنید:"

    keyboard = [
        [
            InlineKeyboardButton("➕ ۵۰ طلا", callback_data=f"admin:adj:{c['id']}:gold:50"),
            InlineKeyboardButton("➕ ۲۰۰ طلا", callback_data=f"admin:adj:{c['id']}:gold:200"),
            InlineKeyboardButton("➕ ۱,۰۰۰ طلا", callback_data=f"admin:adj:{c['id']}:gold:1000"),
        ],
        [
            InlineKeyboardButton("➖ ۵۰ طلا", callback_data=f"admin:adj:{c['id']}:gold:-50"),
            InlineKeyboardButton("➖ ۲۰۰ طلا", callback_data=f"admin:adj:{c['id']}:gold:-200"),
            InlineKeyboardButton("➖ ۱,۰۰۰ طلا", callback_data=f"admin:adj:{c['id']}:gold:-1000"),
        ],
        [
            InlineKeyboardButton("✏️ تنظیم دقیق عدد طلا (تایپی)", callback_data=f"admin:prompt:{c['id']}:gold"),
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:c:{c['id']}"),
        ]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def menu_oil(query, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return
    text = (
        f"🛢️ **تغییر وضعیت نفت کشور {c['flag']} {c['name']}**\n"
        f"ذخایر فعلی: {format_oil(c['oil_reserves'])}\n"
        f"تولید روزانه فعلی: {format_oil(c['oil_production'])}/روز"
    )

    keyboard = [
        [
            InlineKeyboardButton("➕ ۱ میلیون بشکه ذخیره", callback_data=f"admin:adj:{c['id']}:oil_reserves:1000000"),
            InlineKeyboardButton("➕ ۱۰ میلیون بشکه ذخیره", callback_data=f"admin:adj:{c['id']}:oil_reserves:10000000"),
        ],
        [
            InlineKeyboardButton("➖ ۱ میلیون بشکه ذخیره", callback_data=f"admin:adj:{c['id']}:oil_reserves:-1000000"),
            InlineKeyboardButton("➖ ۱۰ میلیون بشکه ذخیره", callback_data=f"admin:adj:{c['id']}:oil_reserves:-10000000"),
        ],
        [
            InlineKeyboardButton("✏️ تنظیم عددی ذخایر نفت", callback_data=f"admin:prompt:{c['id']}:oil_reserves"),
            InlineKeyboardButton("✏️ تنظیم نرخ تولید روزانه", callback_data=f"admin:prompt:{c['id']}:oil_production"),
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:c:{c['id']}"),
        ]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def menu_assets(query, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return

    assets = db.get_country_assets(country_id)
    text = f"🎖️ **مدیریت دارایی‌های نظامی اختصاصی {c['flag']} {c['name']}**\n\nیک سلاح/تجهیز را برای تغییر تعداد انتخاب کنید:"

    keyboard = []
    for a in assets:
        unit = config.ASSET_CATEGORIES.get(a['category'], ("", "عدد"))[1]
        btn_label = f"{a['equipment_name']} ({format_number(a['amount'])} {unit})"
        keyboard.append([InlineKeyboardButton(btn_label, callback_data=f"admin:asset_item:{c['id']}:{a['equipment_key']}")])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:c:{c['id']}")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def menu_single_asset_item(query, country_id: int, equipment_key: str):
    c = db.get_country_by_id(country_id)
    asset = db.get_asset_by_key(country_id, equipment_key)
    if not c or not asset:
        return

    unit = config.ASSET_CATEGORIES.get(asset['category'], ("", "عدد"))[1]
    text = (
        f"⚙️ **ویرایش دارایی نظامی:** {asset['equipment_name']}\n"
        f"کشور: {c['flag']} {c['name']}\n"
        f"تعداد فعلی: `{format_number(asset['amount'])} {unit}`\n"
        f"قیمت خرید واحد: {format_money(asset['buy_price'])}"
    )

    keyboard = [
        [
            InlineKeyboardButton("➕ ۱۰", callback_data=f"admin:adj_asset:{country_id}:{equipment_key}:10"),
            InlineKeyboardButton("➕ ۱۰۰", callback_data=f"admin:adj_asset:{country_id}:{equipment_key}:100"),
            InlineKeyboardButton("➕ ۱,۰۰۰", callback_data=f"admin:adj_asset:{country_id}:{equipment_key}:1000"),
        ],
        [
            InlineKeyboardButton("➖ ۱۰", callback_data=f"admin:adj_asset:{country_id}:{equipment_key}:-10"),
            InlineKeyboardButton("➖ ۱۰۰", callback_data=f"admin:adj_asset:{country_id}:{equipment_key}:-100"),
            InlineKeyboardButton("➖ ۱,۰۰۰", callback_data=f"admin:adj_asset:{country_id}:{equipment_key}:-1000"),
        ],
        [
            InlineKeyboardButton("✏️ تنظیم عدد دقیق (تایپی)", callback_data=f"admin:prompt_asset:{country_id}:{equipment_key}"),
            InlineKeyboardButton("🗑️ صفر کردن", callback_data=f"admin:set_asset:{country_id}:{equipment_key}:0"),
        ],
        [
            InlineKeyboardButton("🔙 بازگشت به لیست دارایی‌ها", callback_data=f"admin:menu_assets:{country_id}"),
        ]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== پردازش CallbackQuery های پنل ادمین ====================

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("⛔ شما ادمین نیستید!", show_alert=True)
        return

    data = query.data
    await query.answer()

    if data == "ignore":
        return

    if data == "admin:menu":
        await admin_panel(update, context)

    elif data == "admin:close":
        await query.delete_message()

    elif data.startswith("admin:list:"):
        page = int(data.split(":")[2])
        await show_countries_list(query, context, page)

    elif data.startswith("admin:c:"):
        c_id = int(data.split(":")[2])
        await show_country_dashboard(query, context, c_id)

    elif data == "admin:stats":
        stats = db.get_game_stats()
        text = (
            "📊 **آمار کلی بازی «سیاست مدرن»**\n\n"
            f"🌐 تعداد کشورهای ساخته شده: `{stats['countries_count']}`\n"
            f"🏦 مجموع کل ثروت خزانه کشورها: {format_money(stats['total_treasury'])}\n"
            f"🪙 مجموع طلا در گردش: {format_number(stats['total_gold'])}\n"
            f"🛢️ مجموع ذخایر نفت: {format_oil(stats['total_oil'])}\n"
            f"🪖 مجموع کل تجهیزات و تسلیحات نظامی: {format_number(stats['total_equipment'])} عدد"
        )
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:daily_income":
        from main import daily_income_job
        await daily_income_job(context)
        await query.edit_message_text(
            "⚡ **درآمد روزانه تمام کشورها به صورت دستی واریز شد!**",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:menu")]])
        )

    # منوهای ویرایش
    elif data.startswith("admin:menu_treasury:"):
        c_id = int(data.split(":")[2])
        await menu_treasury(query, c_id)

    elif data.startswith("admin:menu_gold:"):
        c_id = int(data.split(":")[2])
        await menu_gold(query, c_id)

    elif data.startswith("admin:menu_oil:"):
        c_id = int(data.split(":")[2])
        await menu_oil(query, c_id)

    elif data.startswith("admin:menu_assets:"):
        c_id = int(data.split(":")[2])
        await menu_assets(query, c_id)

    elif data.startswith("admin:asset_item:"):
        _, _, c_id, equipment_key = data.split(":", 3)
        await menu_single_asset_item(query, int(c_id), equipment_key)

    # تغییر نسبی فیلدها
    elif data.startswith("admin:adj:"):
        _, _, c_id_str, field, delta_str = data.split(":")
        c_id, delta = int(c_id_str), int(delta_str)

        if field == "treasury":
            db.adjust_treasury(c_id, delta)
        elif field == "gold":
            db.adjust_gold(c_id, delta)
        elif field == "oil_reserves":
            db.adjust_oil(c_id, delta)

        c = db.get_country_by_id(c_id)
        field_names = {"treasury": "خزانه", "gold": "طلا", "oil_reserves": "ذخیره نفت"}
        notice = f"✅ {field_names.get(field, field)} کشور {c['name']} تغییر یافت."
        await show_country_dashboard(query, context, c_id, notice=notice)

    elif data.startswith("admin:adj_asset:"):
        _, _, c_id_str, equipment_key, delta_str = data.split(":")
        c_id, delta = int(c_id_str), int(delta_str)
        asset = db.get_asset_by_key(c_id, equipment_key)
        if asset:
            db.set_asset_amount(c_id, equipment_key, asset["amount"] + delta)
        await menu_single_asset_item(query, c_id, equipment_key)

    elif data.startswith("admin:set_asset:"):
        _, _, c_id_str, equipment_key, qty_str = data.split(":")
        c_id, qty = int(c_id_str), int(qty_str)
        db.set_asset_amount(c_id, equipment_key, qty)
        await menu_single_asset_item(query, c_id, equipment_key)

    # درخواست ورودی متنی
    elif data.startswith("admin:prompt:"):
        _, _, c_id_str, field = data.split(":")
        c_id = int(c_id_str)
        c = db.get_country_by_id(c_id)
        context.user_data["admin_awaiting_input"] = {"type": "field", "country_id": c_id, "field": field}

        field_names = {
            "treasury": "خزانه (دلار)",
            "gold": "طلا",
            "oil_reserves": "ذخایر نفت (بشکه)",
            "oil_production": "نرخ تولید روزانه نفت (بشکه)"
        }

        await query.edit_message_text(
            f"✏️ **تنظیم سفارشی {field_names.get(field, field)} برای کشور {c['name']}**\n\n"
            f"لطفاً عدد جدید مورد نظر را در یک پیام بفرستید (مثلاً `250000000`):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data=f"admin:c:{c_id}")]])
        )

    elif data.startswith("admin:prompt_asset:"):
        _, _, c_id_str, equipment_key = data.split(":")
        c_id = int(c_id_str)
        c = db.get_country_by_id(c_id)
        asset = db.get_asset_by_key(c_id, equipment_key)
        context.user_data["admin_awaiting_input"] = {"type": "asset_amount", "country_id": c_id, "equipment_key": equipment_key}

        await query.edit_message_text(
            f"✏️ **تنظیم تعداد {asset['equipment_name']} برای کشور {c['name']}**\n\n"
            f"لطفاً تعداد جدید مورد نظر را ارسال کنید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data=f"admin:asset_item:{c_id}:{equipment_key}")]])
        )

    elif data.startswith("admin:msg_prompt:"):
        c_id = int(data.split(":")[2])
        c = db.get_country_by_id(c_id)
        context.user_data["admin_awaiting_input"] = {"type": "direct_msg", "country_id": c_id, "player_id": c["player_id"]}

        await query.edit_message_text(
            f"✉️ **ارسال پیام مستقیم به رهبر {c['flag']} {c['name']}**\n\n"
            f"متن پیام خود را بنویسید تا مستقیماً برای بازیکن ارسال شود:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data=f"admin:c:{c_id}")]])
        )

    elif data == "admin:broadcast_prompt":
        context.user_data["admin_awaiting_input"] = {"type": "broadcast"}
        await query.edit_message_text(
            "📢 **ارسال پیام همگانی به تمام بازیکنان**\n\n"
            "متن پیام اعلان بازی را ارسال کنید تا برای تمام رهبران کشورها فرستاده شود:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="admin:menu")]])
        )

    # تأیید و اجرای حذف کشور
    elif data.startswith("admin:delconfirm:"):
        c_id = int(data.split(":")[2])
        c = db.get_country_by_id(c_id)
        text = (
            f"⚠️ **آیا از حذف کامل کشور {c['flag']} {c['name']} مطمئن هستید؟**\n\n"
            f"• شناسه بازیکن: `{c['player_id']}`\n"
            f"• تمام ثروت، طلا، نفت و تجهیزات این کشور حذف خواهد شد و بازیکن می‌تواند دوباره /start بزند.\n"
            f"این عمل غیرقابل بازگشت است!"
        )
        keyboard = [
            [InlineKeyboardButton("🔥 بله، حذف کن!", callback_data=f"admin:delfinal:{c_id}")],
            [InlineKeyboardButton("❌ انصراف", callback_data=f"admin:c:{c_id}")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("admin:delfinal:"):
        c_id = int(data.split(":")[2])
        c = db.get_country_by_id(c_id)
        if c:
            name = c["name"]
            db.delete_country_by_id(c_id)
            await query.edit_message_text(
                f"✅ کشور **{name}** با موفقیت و به‌طور کامل حذف شد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 بازگشت به لیست کشورها", callback_data="admin:list:0")]])
            )


# ==================== دریافت ورودی‌های تایپی ادمین ====================

async def admin_input_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    input_state = context.user_data.get("admin_awaiting_input")
    if not input_state:
        return

    text = update.message.text.strip()
    input_type = input_state.get("type")

    del context.user_data["admin_awaiting_input"]

    clean_text = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١۲٣٤٥٦٧٨٩", "01234567890123456789")).replace(",", "").replace("_", "")

    if input_type == "field":
        c_id = input_state["country_id"]
        field = input_state["field"]
        try:
            val = int(clean_text)
            db.update_country_field(c_id, field, val)
            c = db.get_country_by_id(c_id)
            await update.message.reply_text(f"✅ مقدار {field} برای کشور {c['name']} با موفقیت به {format_number(val)} تغییر یافت.\nبرای ادامه /admin را بزنید.")
        except ValueError:
            await update.message.reply_text("❌ عدد وارد شده نامعتبر بود. عملیات لغو شد. برای مدیریت /admin را بزنید.")

    elif input_type == "asset_amount":
        c_id = input_state["country_id"]
        eq_key = input_state["equipment_key"]
        try:
            val = int(clean_text)
            db.set_asset_amount(c_id, eq_key, val)
            c = db.get_country_by_id(c_id)
            asset = db.get_asset_by_key(c_id, eq_key)
            await update.message.reply_text(f"✅ تعداد {asset['equipment_name']} برای کشور {c['name']} به {format_number(val)} تغییر یافت.\nبرای ادامه /admin را بزنید.")
        except ValueError:
            await update.message.reply_text("❌ عدد وارد شده نامعتبر بود. عملیات لغو شد. برای مدیریت /admin را بزنید.")

    elif input_type == "direct_msg":
        player_id = input_state["player_id"]
        c_id = input_state["country_id"]
        c = db.get_country_by_id(c_id)
        try:
            await context.bot.send_message(
                chat_id=player_id,
                text=f"📩 **پیام مستقیم از طرف ادمین بازی:**\n\n{text}",
                parse_mode="Markdown"
            )
            await update.message.reply_text(f"✅ پیام شما با موفقیت برای رهبر کشور {c['name']} ارسال شد.")
        except Exception as e:
            await update.message.reply_text(f"❌ ارسال پیام به بازیکن ناموفق بود:\n{e}")

    elif input_type == "broadcast":
        countries = db.get_all_countries()
        success_count = 0
        fail_count = 0
        msg_text = f"📢 **اطلاعیه همگانی ادمین بازی:**\n\n{text}"

        for c in countries:
            try:
                await context.bot.send_message(chat_id=c["player_id"], text=msg_text, parse_mode="Markdown")
                success_count += 1
            except Exception:
                fail_count += 1

        await update.message.reply_text(
            f"📢 **نتیجه ارسال پیام همگانی:**\n\n"
            f"✅ ارسال موفق به: {success_count} کشور\n"
            f"❌ ناموفق: {fail_count} کشور"
        )


# ==================== دستورات متنی قدیمی ادمین جهت سازگاری ====================

async def addmoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ این دستور فقط برای ادمین‌هاست.")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text("کاربرد: /addmoney <player_id> <amount>")
        return

    try:
        player_id, amount = int(args[0]), int(args[1])
    except ValueError:
        await update.message.reply_text("مقادیر باید عدد باشند.")
        return

    country = db.get_country_by_player(player_id)
    if not country:
        await update.message.reply_text("کشوری پیدا نشد.")
        return

    db.adjust_treasury(country["id"], amount)
    await update.message.reply_text(f"✅ مبلغ {format_money(amount)} به خزانه {country['name']} اضافه شد.")


async def removemoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ این دستور فقط برای ادمین‌هاست.")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text("کاربرد: /removemoney <player_id> <amount>")
        return

    try:
        player_id, amount = int(args[0]), int(args[1])
    except ValueError:
        await update.message.reply_text("مقادیر باید عدد باشند.")
        return

    country = db.get_country_by_player(player_id)
    if not country:
        await update.message.reply_text("کشوری پیدا نشد.")
        return

    db.adjust_treasury(country["id"], -amount)
    await update.message.reply_text(f"✅ مبلغ {format_money(amount)} از خزانه {country['name']} کم شد.")


async def listcountries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ این دستور فقط برای ادمین‌هاست.")
        return

    countries = db.get_all_countries()
    if not countries:
        await update.message.reply_text("هنوز هیچ کشوری ثبت نشده.")
        return

    lines = ["📋 لیست کشورها:\n"]
    for c in countries:
        lines.append(f"{c['flag']} {c['name']} — player_id: `{c['player_id']}` — خزانه: {format_money(c['treasury'])}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
