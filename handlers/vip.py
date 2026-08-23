# -*- coding: utf-8 -*-
"""
ماژول خدمات ویژه، اشتراک‌های تومانی و فهرست گروه‌های غیردولتی معتبر (VIP & Militia Module).
شامل اشتراک رهبر ویژه (VIP Leader Pass) و فهرست سازمان‌ها و گروه‌های شبه‌نظامی واقعی به همراه گزینه سفارشی.
"""

import html
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

import database as db
import config
from utils import format_money, format_number, get_main_keyboard


# ==================== منوی اصلی اشتراک‌های VIP ====================

async def vip_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش تعرفه‌های اشتراک ۴ سطحی VIP به بازیکن."""
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)

    is_vip = bool(country.get("is_vip") or 0) if country else False
    vip_exp = country.get("vip_expires_at") if country else None
    vip_tier = country.get("vip_tier") if country else ""

    tier_labels = {
        "diamond": "💎 الماس (Diamond Supreme)",
        "gold": "🥇 طلا (Gold Leader)",
        "silver": "🥈 نقره (Silver Leader)",
        "bronze": "🥉 برنز (Bronze Leader)"
    }

    if is_vip and vip_exp:
        try:
            exp_date_str = vip_exp[:10]
            status_header = f"⭐ **وضعیت رهبری شما: {tier_labels.get(vip_tier, 'اشتراک VIP فعال')} (تا {exp_date_str})**"
        except Exception:
            status_header = f"⭐ **وضعیت رهبری شما: {tier_labels.get(vip_tier, 'اشتراک VIP فعال')}**"
    elif is_vip:
        status_header = f"⭐ **وضعیت رهبری شما: {tier_labels.get(vip_tier, 'اشتراک VIP فعال')}**"
    elif country:
        status_header = f"▫️ **وضعیت رهبری شما: اشتراک عادی ({country['flag']} {country['name']})**"
    else:
        status_header = "▫️ **وضعیت فعلی شما: فاقد کشور رسمی**"

    text = (
        "👑 **مرکز خدمات ویژه و اشتراک‌های حاکمیتی (VIP)**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{status_header}\n\n"
        "🔹 **سطوح اشتراک ماهانه (۳۰ روزه):**\n\n"
        "🥉 **۱. اشتراک برنز (۷۹,۰۰۰ ت):**\n"
        "• 📉 تخفیف ۵٪ در هزینه نگهداری ارتش\n"
        "• 🎯 +۱ رزمایش نظامی اضافه روزانه\n"
        "• 📜 ۴ اسلات قرارداد تجاری همزمان\n\n"
        "🥈 **۲. اشتراک نقره (۱۷۹,۰۰۰ ت):**\n"
        "• 📉 تخفیف ۱۰٪ در هزینه نگهداری ارتش\n"
        "• ⚡ اولویت رده ۲ در صف بررسی رول‌ها\n"
        "• 🎯 +۲ رزمایش نظامی اضافه روزانه\n"
        "• 🛡️ رادار پایش امنیتی تحرکات مرزی\n"
        "• 📜 ۶ اسلات قرارداد تجاری\n\n"
        "🥇 **۳. اشتراک طلا (۳۴۹,۰۰۰ ت):**\n"
        "• 📉 تخفیف ۱۵٪ در هزینه نگهداری ارتش\n"
        "• 🚀 اولویت فوری VIP در بررسی رول‌ها و جنگ‌ها\n"
        "• 🎯 +۳ رزمایش نظامی اضافه روزانه\n"
        "• 🚢 ۱۵٪ تخفیف ترانزیت لجستیک معاهدات\n"
        "• 🛡️ تقویت ضداطلاعات و امنیت سایبری\n"
        "• 📜 ۸ اسلات قرارداد تجاری\n\n"
        "💎 **۴. اشتراک الماس (۶۵۰,۰۰۰ ت):**\n"
        "• 📉 تخفیف ۲۵٪ در کل هزینه نگهداری ارتش و زرادخانه‌ها\n"
        "• ⚡⚡ بررسی آنی و اختصاصی رول‌ها (اولویت صفر)\n"
        "• 🎯 رزمایش نامحدود روزانه (آمادگی رزمی ۱۰۰٪ همیشگی)\n"
        "• 🏢 ۵۰٪ تخفیف نگهداری و اجاره پایگاه‌های راهبردی\n"
        "• 📜 قراردادهای تجاری نامحدود\n"
        "• 👑 مشاوره مستقیم تنظیم دکترین نظامی با تحلیلگر ارشد\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "سطح اشتراک مورد نظر را انتخاب فرمایید:"
    )

    keyboard = [
        [InlineKeyboardButton("🥉 اشتراک برنز — ۷۹,۰۰۰ تومان", callback_data="vip:plan:vip_bronze")],
        [InlineKeyboardButton("🥈 اشتراک نقره — ۱۷۹,۰۰۰ تومان", callback_data="vip:plan:vip_silver")],
        [InlineKeyboardButton("🥇 اشتراک طلا — ۳۴۹,۰۰۰ تومان", callback_data="vip:plan:vip_gold")],
        [InlineKeyboardButton("💎 اشتراک الماس — ۶۵۰,۰۰۰ تومان", callback_data="vip:plan:vip_diamond")],
    ]

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== فهرست سازمان‌ها و گروه‌های شبه‌نظامی غیردولتی ====================

async def show_predefined_factions_menu(query, context, user_id: int):
    """نمایش لیست گروه‌های آماده معتبر به همراه گزینه سفارشی."""
    factions = getattr(config, "PREDEFINED_MILITIA_FACTIONS", {})
    taken_keys = db.get_taken_militia_faction_keys()

    text = (
        "🏴‍☠️ **فهرست سازمان‌ها و گروه‌های شبه‌نظامی غیردولتی معتبر جهان**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "یکی از گروه‌های آماده زیر را جهت هدایت انتخاب فرمایید، یا در انتها گروه سفارشی با مشخصات دلخواه خود بسازید:\n\n"
        "📊 **بسته آغازین هر گروه:**\n"
        "• 💰 **۲۵ میلیون دلار** خزانه و بودجه اولیه\n"
        "• 🪖 **۶۰,۰۰۰ رزمنده** آماده‌باش\n"
        "• 🎖️ **+۴۰ قلم تسلیحات و تجهیزات واقعی و تخصصی**\n"
        "• ⭐ **اشتراک طلایی VIP هدیه به رهبر گروه**\n"
        "• 💵 **تعرفه صدور مجوز:** ۵۰,۰۰۰ تومان (یک‌بار پرداخت)\n"
    )

    keyboard = []
    row = []
    for f_key, f_info in factions.items():
        is_taken = f_key in taken_keys
        status_icon = "🔒 " if is_taken else f"{f_info['flag']} "
        btn_label = f"{status_icon}{f_info['short_name']}"
        cb_data = "ignore" if is_taken else f"vip:fpick:{f_key}"
        row.append(InlineKeyboardButton(btn_label, callback_data=cb_data))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # دکمه گروه سفارشی با نام دلخواه
    keyboard.append([InlineKeyboardButton("✨ ساخت گروه سفارشی (نام و نماد دلخواه)", callback_data="vip:fpick:custom")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به صفحه اصلی", callback_data="vip:menu")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def preview_predefined_faction_checkout(query, context, faction_key: str):
    """نمایش پیش‌فاکتور و اطلاعات گروه آماده برای پرداخت."""
    factions = getattr(config, "PREDEFINED_MILITIA_FACTIONS", {})
    f_info = factions.get(faction_key)
    if not f_info:
        await query.answer("گروه یافت نشد.", show_alert=True)
        return

    militia_cats = getattr(config, "MILITIA_EQUIPMENT_CATALOG", {})
    roster = militia_cats.get(faction_key, [])
    item_count = len(roster)

    context.user_data["militia_wiz"] = {
        "faction_key": faction_key,
        "name": f_info["name"],
        "flag": f_info["flag"],
        "hq": f_info["hq"],
        "doctrine": f_info["doctrine"],
    }

    card_info = getattr(config, "PAYMENT_CARD_INFO", {
        "card_number": "۵۸۹۲-۱۰۱۴-۶۷۲۲-۷۲۲۵",
        "card_holder": "زینب فیاضی",
        "bank_name": "بانک سپه"
    })
    card_num = card_info.get("card_number", "۵۸۹۲-۱۰۱۴-۶۷۲۲-۷۲۲۵")
    card_holder = card_info.get("card_holder", "زینب فیاضی")
    bank_name = card_info.get("bank_name", "بانک سپه")

    price = getattr(config, "MILITIA_LICENSE_PRICE_TOMAN", 50_000)

    text = (
        f"🏴‍☠️ **پرونده و فاکتور هدایت {f_info['flag']} {f_info['name']}**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"• **مقر فرماندهی:** {f_info['hq']}\n"
        f"• **دکترین:** {f_info['doctrine']}\n"
        f"• **شرح فعالیت:** {f_info['desc']}\n\n"
        f"🎖️ **تجهیزات و تسلیحات سازمانی:** {item_count} قلم جنگ‌افزار بومی و اختصاصی\n"
        "• 💰 خزانه اولیه: **۲۵ میلیون دلار**\n"
        "• 🪖 رزمندگان آماده‌باش: **۶۰,۰۰۰ نفر**\n"
        "• ⭐ اشتراک طلایی VIP هدیه به رهبر\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"💵 **مبلغ مجوز:** **{price:,} تومان**\n\n"
        "💳 **مشخصات حساب جهت کارت به کارت:**\n"
        f"• **شماره کارت:** `{card_num}`\n"
        f"• **به نام:** **{card_holder}**\n"
        f"• **بانک:** {bank_name}\n\n"
        "⚠️ پس از واریز، روی دکمه زیر کلیک کرده و تصویر فیش یا کد پیگیری را ارسال فرمایید:"
    )

    kb = [
        [InlineKeyboardButton("📸 ارسال تصویر فیش واریزی", callback_data="vip:upload:militia")],
        [InlineKeyboardButton("✍️ ثبت با کد پیگیری (متنی)", callback_data="vip:code:militia")],
        [InlineKeyboardButton("🔙 بازگشت به لیست گروه‌ها", callback_data="vip:militia_wizard_start")],
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


# ==================== ویزارد ساخت گروه سفارشی ====================

async def start_custom_militia_wizard(query, context):
    """گام اول گروه سفارشی: دریافت نام."""
    context.user_data["militia_wiz"] = {"step": "name", "faction_key": None}
    text = (
        "✨ **ساخت گروه و سازمان شبه‌نظامی سفارشی (گام ۱ از ۴)**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "لطفاً **نام رسمی گروه یا سازمان اختصاصی** خود را ارسال فرمایید:\n\n"
        "*(نام باید رسمی، جدی و با فضای ژئوپلیتیک بازی همخوانی داشته باشد)*"
    )
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="vip:militia_wizard_start")]]),
        parse_mode="Markdown"
    )


async def militia_wizard_step_flag(message, context):
    """گام ۲: دریافت پرچم / ایموجی نمادین."""
    text = (
        "🚩 **انتخاب نماد یا پرچم گروه (گام ۲ از ۴)**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "لطفاً یک **ایموجی یا نماد اختصاصی** برای گروه خود تایپ و ارسال کنید:\n\n"
        "*(نمادهای پیشنهادی: 🏴‍☠️, ⚔️, 🐺, 🦅, 🟡, 🛡️, 🦁, ⚡, 🔴, 💀, 🎯)*"
    )
    context.user_data["militia_wiz"]["step"] = "flag"
    await message.reply_text(text, parse_mode="Markdown")


async def militia_wizard_step_hq(message, context):
    """گام ۳: دریافت مقر فرماندهی."""
    text = (
        "📍 **مقر فرماندهی و منطقه عملیاتی (گام ۳ از ۴)**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "لطفاً **موقعیت استقرار و پایگاه اصلی فرماندهی** گروه خود را تعیین فرمایید:\n\n"
        "*(مثال: صحرای سینا، شمال حلب و ادلب، شرق اوکراین، کوهستان‌های مرزی، حوزه نفتی دیرالزور)*"
    )
    context.user_data["militia_wiz"]["step"] = "hq"
    await message.reply_text(text, parse_mode="Markdown")


async def militia_wizard_step_doctrine(message, context):
    """گام ۴: انتخاب دکترین با دکمه شیشه‌ای."""
    text = (
        "🎯 **تعیین دکترین و ساختار سازمانی (گام ۴ از ۴)**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "لطفاً جهت‌گیری و دکترین نظامی گروه خود را انتخاب فرمایید:"
    )
    kb = [
        [InlineKeyboardButton("⚔️ جنگ نامتقارن و چریکی", callback_data="vip:doc:guerilla")],
        [InlineKeyboardButton("🛡️ شرکت نظامی و امنیتی خصوصی (PMC)", callback_data="vip:doc:pmc")],
        [InlineKeyboardButton("🚀 یگان واکنش سریع موشکی و پهپادی", callback_data="vip:doc:rapid_strike")],
        [InlineKeyboardButton("🏴‍☠️ جنبش آزادی‌بخش و مقاومت منطقه‌ای", callback_data="vip:doc:resistance")],
    ]
    await message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


async def custom_militia_checkout(query, context, doctrine_key: str):
    """صدور فاکتور نهایی گروه سفارشی."""
    wiz = context.user_data.get("militia_wiz", {})
    doc_labels = {
        "guerilla": "جنگ نامتقارن و چریکی",
        "pmc": "شرکت نظامی خصوصی (PMC)",
        "rapid_strike": "یگان واکنش سریع موشکی و پهپادی",
        "resistance": "جنبش مقاومت منطقه‌ای"
    }
    wiz["doctrine"] = doc_labels.get(doctrine_key, "نظامی نامتقارن")

    card_info = getattr(config, "PAYMENT_CARD_INFO", {
        "card_number": "۵۸۹۲-۱۰۱۴-۶۷۲۲-۷۲۲۵",
        "card_holder": "زینب فیاضی",
        "bank_name": "بانک سپه"
    })
    card_num = card_info.get("card_number", "۵۸۹۲-۱۰۱۴-۶۷۲۲-۷۲۲۵")
    card_holder = card_info.get("card_holder", "زینب فیاضی")
    bank_name = card_info.get("bank_name", "بانک سپه")

    price = getattr(config, "MILITIA_LICENSE_PRICE_TOMAN", 50_000)

    text = (
        "🏴‍☠️ **پیش‌نمایش پرونده و فاکتور گروه غیردولتی سفارشی**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🏷️ **نام سازمان:** {wiz.get('name', 'گروه اختصاصی')}\n"
        f"🚩 **پرچم/نماد:** {wiz.get('flag', '🏴‍☠️')}\n"
        f"📍 **مقر فرماندهی:** {wiz.get('hq', 'نامشخص')}\n"
        f"🎯 **دکترین:** {wiz.get('doctrine')}\n\n"
        "📊 **منابع و بسته آغازین پس از تایید:**\n"
        "• 💰 خزانه اولیه: **۲۵ میلیون دلار**\n"
        "• 🪖 رزمندگان آماده‌باش: **۶۰,۰۰۰ نفر**\n"
        "• 🎖️ کاتالوگ تسلیحات: ۶۰۰ تویوتا دوشکا، ۱۸۰ BTR، ۸۰ راکت‌انداز گراد، ۲۰۰ پهپاد ابابیل، پدافند زو-۲۳ و قایق‌های تندرو\n"
        "• ⭐ اشتراک طلایی VIP هدیه به رهبر گروه\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"💵 **مبلغ قابل پرداخت:** **{price:,} تومان**\n\n"
        "💳 **مشخصات حساب جهت کارت به کارت:**\n"
        f"• **شماره کارت:** `{card_num}`\n"
        f"• **به نام:** **{card_holder}**\n"
        f"• **بانک:** {bank_name}\n\n"
        "⚠️ پس از واریز، روی دکمه زیر کلیک کرده و تصویر فیش یا کد پیگیری را ارسال فرمایید:"
    )

    kb = [
        [InlineKeyboardButton("📸 ارسال تصویر فیش واریزی", callback_data="vip:upload:militia")],
        [InlineKeyboardButton("✍️ ثبت با کد پیگیری (متنی)", callback_data="vip:code:militia")],
        [InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data="vip:militia_wizard_start")],
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


# ==================== صفحه پرداخت VIP ====================

PLANS_METADATA = {
    "vip_bronze": {
        "title": "🥉 اشتراک برنز رهبری (Bronze Leader)",
        "tier": "bronze",
        "price": 79_000,
        "desc": "تخفیف ۵٪ نگهداری ارتش، ۱ مانور اضافه روزانه، ۴ اسلات معاهده تجاری و نشان برنزی."
    },
    "vip_silver": {
        "title": "🥈 اشتراک نقره‌ای رهبری (Silver Leader)",
        "tier": "silver",
        "price": 179_000,
        "desc": "تخفیف ۱۰٪ نگهداری ارتش، اولویت رده ۲ بررسی رول‌ها، ۲ مانور اضافه، رادار امنیتی و ۶ اسلات قرارداد."
    },
    "vip_gold": {
        "title": "🥇 اشتراک طلایی رهبری (Gold Leader)",
        "tier": "gold",
        "price": 349_000,
        "desc": "تخفیف ۱۵٪ نگهداری ارتش، اولویت فوری VIP بررسی رول‌ها، ۳ مانور اضافه، ۱۵٪ تخفیف ترانزیت، ضداطلاعات و ۸ اسلات قرارداد."
    },
    "vip_diamond": {
        "title": "💎 اشتراک الماس (Diamond Supreme Pass)",
        "tier": "diamond",
        "price": 650_000,
        "desc": "تخفیف ۲۵٪ نگهداری ارتش، بررسی آنی اختصاصی رول‌ها، مانور نامحدود، ۵۰٪ تخفیف پایگاه‌ها، قراردادهای نامحدود و نشان درخشان الماس."
    },
    "militia": {
        "title": "🏴‍☠️ مجوز رسمی تاسیس گروه شبه‌نظامی غیردولتی",
        "price": 50_000,
        "desc": "صدور مجوز ایجاد گروه نظامی اختصاصی، نماد سفارشی و کاتالوگ تسلیحاتی اختصاصی."
    },
    # نام‌های مستعار جهت سازگاری کامل
    "bronze": {"title": "🥉 اشتراک برنز رهبری", "tier": "bronze", "price": 79_000, "desc": ""},
    "silver": {"title": "🥈 اشتراک نقره‌ای رهبری", "tier": "silver", "price": 179_000, "desc": ""},
    "gold": {"title": "🥇 اشتراک طلایی رهبری", "tier": "gold", "price": 349_000, "desc": ""},
    "diamond": {"title": "💎 اشتراک الماس", "tier": "diamond", "price": 650_000, "desc": ""},
    "vip_1month": {"title": "🥇 اشتراک طلایی رهبری", "tier": "gold", "price": 349_000, "desc": ""},
}


async def vip_checkout_screen(query, context, plan_key: str, country: dict = None):
    """نمایش فاکتور و اطلاعات کارت بانکی جهت واریز VIP."""
    if plan_key == "militia":
        await show_predefined_factions_menu(query, context, query.from_user.id)
        return

    plan = PLANS_METADATA.get(plan_key)
    if not plan:
        await query.answer("پلن انتخابی نامعتبر است.", show_alert=True)
        return

    card_info = getattr(config, "PAYMENT_CARD_INFO", {
        "card_number": "۵۸۹۲-۱۰۱۴-۶۷۲۲-۷۲۲۵",
        "card_holder": "زینب فیاضی",
        "bank_name": "بانک سپه"
    })

    card_num = card_info.get("card_number", "۵۸۹۲-۱۰۱۴-۶۷۲۲-۷۲۲۵")
    card_holder = card_info.get("card_holder", "زینب فیاضی")
    bank_name = card_info.get("bank_name", "بانک سپه")

    text = (
        f"💳 **فاکتور پرداخت و اطلاعات واریز وجه**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"📌 **سفارش شما:** {plan['title']}\n"
        f"💵 **مبلغ قابل پرداخت:** **{plan['price']:,} تومان**\n"
        f"📝 **توضیحات:** {plan['desc']}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "💳 **مشخصات حساب بانکی جهت کارت به کارت:**\n\n"
        f"• **شماره کارت:** `{card_num}`\n"
        f"• **به نام:** **{card_holder}**\n"
        f"• **بانک:** {bank_name}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "⚠️ **مراحل فعال‌سازی:**\n"
        "۱. مبلغ دقیق را به شماره کارت فوق واریز فرمایید.\n"
        "۲. بر روی دکمه **«📸 ارسال تصویر فیش واریزی»** کلیک کنید.\n"
        "۳. تصویر فیش یا کد پیگیری واریز را بفرستید تا فوراً توسط مدیریت تایید و سرویس شما فعال شود."
    )

    keyboard = [
        [InlineKeyboardButton("📸 ارسال تصویر فیش واریزی", callback_data=f"vip:upload:{plan_key}")],
        [InlineKeyboardButton("✍️ ثبت با کد پیگیری (متنی)", callback_data=f"vip:code:{plan_key}")],
        [InlineKeyboardButton("🔙 بازگشت به منوی VIP", callback_data="vip:menu")],
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== Callback Router ====================

async def vip_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    country = db.get_country_by_player(user_id)

    await query.answer()

    if data == "vip:menu":
        await vip_main_menu(update, context)

    elif data in ("vip:militia_wizard_start", "vip:plan:militia"):
        await show_predefined_factions_menu(query, context, user_id)

    elif data.startswith("vip:fpick:"):
        f_key = data.split(":", 2)[2]
        if f_key == "custom":
            await start_custom_militia_wizard(query, context)
        else:
            await preview_predefined_faction_checkout(query, context, f_key)

    elif data.startswith("vip:doc:"):
        doc_key = data.split(":", 2)[2]
        await custom_militia_checkout(query, context, doc_key)

    elif data.startswith("vip:plan:"):
        plan_key = data.split(":", 2)[2]
        await vip_checkout_screen(query, context, plan_key, country)

    elif data.startswith("vip:upload:"):
        plan_key = data.split(":", 2)[2]
        context.user_data["vip_input"] = {"step": "awaiting_photo", "plan_key": plan_key}
        text = (
            "📸 **ارسال تصویر فیش واریزی**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً **تصویر فیش یا اسکرین‌شات واریزی** خود را در قالب یک عکس ارسال فرمایید:\n\n"
            "*(شماره پیگیری و تاریخ در تصویر مشخص باشد)*"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="vip:militia_wizard_start" if plan_key == "militia" else "vip:menu")]]), parse_mode="Markdown")

    elif data.startswith("vip:code:"):
        plan_key = data.split(":", 2)[2]
        context.user_data["vip_input"] = {"step": "awaiting_code", "plan_key": plan_key}
        text = (
            "✍️ **ثبت با کد پیگیری بانکی**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً **کد پیگیری تراکنش + ۴ رقم آخر شماره کارت واریزکننده** را به صورت یک پیام متنی ارسال فرمایید:"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="vip:militia_wizard_start" if plan_key == "militia" else "vip:menu")]]), parse_mode="Markdown")


# ==================== هاندر دریافت ورودی‌های متنی و تصویری ویزارد و فیش ====================

async def vip_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """پردازش مراحل ویزارد ساخت گروه و دریافت فیش بانکی."""
    user = update.effective_user
    user_id = user.id

    # 1. بررسی مراحل ویزارد ساخت گروه سفارشی
    militia_wiz = context.user_data.get("militia_wiz")
    if militia_wiz and update.message.text:
        wiz_step = militia_wiz.get("step")
        txt = update.message.text.strip()

        if wiz_step == "name":
            militia_wiz["name"] = txt
            await militia_wizard_step_flag(update.message, context)
            return True

        elif wiz_step == "flag":
            militia_wiz["flag"] = txt[:8]
            await militia_wizard_step_hq(update.message, context)
            return True

        elif wiz_step == "hq":
            militia_wiz["hq"] = txt
            await militia_wizard_step_doctrine(update.message, context)
            return True

    # 2. بررسی دریافت فیش یا کد واریز
    vip_state = context.user_data.get("vip_input")
    if not vip_state:
        return False

    del context.user_data["vip_input"]
    plan_key = vip_state.get("plan_key")
    plan = PLANS_METADATA.get(plan_key, PLANS_METADATA["vip_1month"])

    country = db.get_country_by_player(user_id)
    c_id = country["id"] if country else None
    c_name = f"{country['flag']} {country['name']}" if country else "فاقد کشور رسمی"

    photo_id = None
    tracking_code = ""

    if update.message.photo:
        photo_id = update.message.photo[-1].file_id
        tracking_code = update.message.caption or "ارسال شده با تصویر فیش"
    elif update.message.text:
        tracking_code = update.message.text.strip()
    else:
        await update.message.reply_text("❌ لطفاً یک پیام متنی یا تصویر فیش معتبر ارسال فرمایید.")
        return True

    # پیلود سفارشی برای گروه شبه‌نظامی
    custom_payload = ""
    if plan_key == "militia" and "militia_wiz" in context.user_data:
        custom_payload = json.dumps(context.user_data["militia_wiz"], ensure_ascii=False)

    # ثبت در دیتابیس
    req_id = db.create_payment_request(
        player_id=user_id,
        country_id=c_id,
        item_type=plan_key,
        plan_title=plan["title"],
        amount_toman=plan["price"],
        receipt_photo_id=photo_id,
        tracking_code=tracking_code,
        custom_payload=custom_payload
    )

    # پیام تایید به کاربر
    conf_user = (
        f"✅ **فیش واریزی شما با موفقیت ثبت شد! (شماره درخواست: #{req_id})**\n\n"
        f"📌 **سفارش:** {plan['title']}\n"
        f"💵 **مبلغ:** {plan['price']:,} تومان\n\n"
        "⏳ پرونده شما برای مدیریت ارسال گردید. به محض تایید حسابداری، گروه/خدمت شما فعال و پیام تایید برایتان ارسال خواهد شد."
    )
    await update.message.reply_text(conf_user, reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")

    # ارسال اعلان به ادمین‌های بازی
    militia_extra = ""
    is_militia = plan_key == "militia" and "militia_wiz" in context.user_data
    if is_militia:
        wiz = context.user_data["militia_wiz"]
        militia_extra = (
            f"\n🏴‍☠️ <b>مشخصات گروه درخواستی:</b>\n"
            f"• <b>نام گروه:</b> {html.escape(wiz.get('name', ''))}\n"
            f"• <b>نماد:</b> {html.escape(wiz.get('flag', ''))}\n"
            f"• <b>مقر:</b> {html.escape(wiz.get('hq', ''))}\n"
            f"• <b>دکترین:</b> {html.escape(wiz.get('doctrine', ''))}\n"
        )
        del context.user_data["militia_wiz"]

    admin_text = (
        f"💳 <b>«درخواست جدید پرداخت تومانی» — شماره #{req_id}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>کاربر:</b> {html.escape(user.full_name or '')} (@{user.username or 'ندارد'})\n"
        f"🆔 <b>شناسه کاربری:</b> <code>{user_id}</code>\n"
        f"🌐 <b>وضعیت کشور:</b> {c_name}\n"
        f"{militia_extra}\n"
        f"📌 <b>پلن:</b> {plan['title']}\n"
        f"💵 <b>مبلغ:</b> <b>{plan['price']:,} تومان</b>\n"
        f"📝 <b>کد پیگیری:</b> <code>{html.escape(tracking_code)}</code>\n"
    )

    admin_kb = [
        [
            InlineKeyboardButton("✅ تایید و ساخت فوری", callback_data=f"admin:pay_app:{req_id}"),
            InlineKeyboardButton("✏️ ویرایش نام و تایید", callback_data=f"admin:pay_rename:{req_id}"),
        ],
        [
            InlineKeyboardButton("❌ رد فیش", callback_data=f"admin:pay_rej:{req_id}"),
        ]
    ] if is_militia else [
        [
            InlineKeyboardButton("✅ تایید و فعال‌سازی فوری", callback_data=f"admin:pay_app:{req_id}"),
            InlineKeyboardButton("❌ رد فیش", callback_data=f"admin:pay_rej:{req_id}"),
        ]
    ]

    for adm in config.ADMIN_IDS:
        try:
            if photo_id:
                await context.bot.send_photo(
                    chat_id=adm,
                    photo=photo_id,
                    caption=admin_text,
                    reply_markup=InlineKeyboardMarkup(admin_kb),
                    parse_mode="HTML"
                )
            else:
                await context.bot.send_message(
                    chat_id=adm,
                    text=admin_text,
                    reply_markup=InlineKeyboardMarkup(admin_kb),
                    parse_mode="HTML"
                )
        except Exception as e:
            print(f"Failed to send payment alert to admin {adm}: {e}")

    return True


def get_vip_handlers():
    """ثبت دستورات و کال‌بک‌های ماژول VIP."""
    return [
        CommandHandler(["vip", "premium"], vip_main_menu),
        CallbackQueryHandler(vip_callback_handler, pattern=r"^vip:"),
    ]
