# -*- coding: utf-8 -*-
"""
ماژول خدمات ویژه، اشتراک‌های تومانی و مجوزهای غیردولتی (VIP & Monetization Module).
شامل اشتراک رهبر ویژه (VIP Leader Pass) و سیستم تعاملی تاسیس گروه‌های شبه‌نظامی غیردولتی (Non-State Factions) برای بازیکنان فاقد کشور.
طراحی شده بر اساس مدل Non-P2W (ارائه امکانات راحتی کاربری، نشان‌های افتخاری، تحلیل‌های ویژه و اولویت بررسی بدون تخریب بالانس بازی).
"""

import html
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

import database as db
import config
from utils import format_money, format_number, get_main_keyboard


# ==================== منوی اصلی خدمات VIP و ارتقای رهبری ====================

async def vip_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش پکیج‌ها و تعرفه‌های خدمات ویژه تومانی به بازیکن."""
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)

    is_vip = bool(country.get("is_vip") or 0) if country else False
    vip_exp = country.get("vip_expires_at") if country else None

    if is_vip and vip_exp:
        try:
            exp_date_str = vip_exp[:10]
            status_header = f"⭐ **وضعیت رهبری شما: اشتراک VIP فعال (تا {exp_date_str})**"
        except Exception:
            status_header = "⭐ **وضعیت رهبری شما: اشتراک VIP فعال**"
    elif is_vip:
        status_header = "⭐ **وضعیت رهبری شما: اشتراک VIP فعال**"
    elif country:
        status_header = f"▫️ **وضعیت رهبری شما: اشتراک عادی ({country['flag']} {country['name']})**"
    else:
        status_header = "▫️ **وضعیت فعلی شما: فاقد کشور رسمی**"

    text = (
        "👑 **مرکز اشتراک ویژه رهبری (VIP Leader Pass)**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{status_header}\n\n"
        "💎 **مزایای اشتراک رهبر ویژه (VIP):**\n"
        "• ⭐ **نشان طلایی VIP:** درج تگ و بج رسمی VIP در پروفایل کشور، بیانیه‌ها و توییت‌ها\n"
        "• ⚡ **اولویت صف بررسی رول‌ها:** تحلیل سریع‌تر و ارزیابی اختصاصی رول‌های نظامی و عملیات‌ها\n"
        "• 🎯 **رزمایش اضافه:** امکان انجام **۱ رزمایش نظامی اضافه** در هر روز جهت افزایش آمادگی رزمی ارتش\n"
        "• 🛡️ **دسترسی به رادار امنیتی:** مشاهده هشدارهای پیشرفته اطلاعاتی و تحرکات منطقه‌ای\n"
        "• 🏆 **جایگاه ممتاز در رنکینگ:** نمایش نشان ستاره‌دار در فهرست رهبران جهان\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "لطفاً دوره اشتراک مورد نظر را جهت مشاهده فاکتور و واریز انتخاب فرمایید:"
    )

    p_vip1 = getattr(config, "VIP_PASS_PRICE_TOMAN", 79_000)
    p_vip3 = getattr(config, "VIP_PASS_3MONTH_PRICE_TOMAN", 199_000)

    keyboard = [
        [InlineKeyboardButton(f"👑 اشتراک VIP یک‌ماهه — {p_vip1:,} تومان", callback_data="vip:plan:vip_1month")],
        [InlineKeyboardButton(f"💎 اشتراک VIP سه‌ماهه (با تخفیف ویژه) — {p_vip3:,} تومان", callback_data="vip:plan:vip_3month")],
    ]

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== ویزارد تعاملی تاسیس گروه شبه‌نظامی غیردولتی ====================

async def start_militia_wizard(query, context, user_id: int):
    """آغاز فرآیند گام‌به‌گام ساخت گروه غیردولتی."""
    country = db.get_country_by_player(user_id)
    if country:
        text = (
            f"⚠️ **شما در حال حاضر هدایت کشور {country['flag']} {country['name']} را بر عهده دارید.**\n\n"
            "مجوز تاسیس گروه غیردولتی ویژه بازیکنانی است که کشوری ندارند. در صورتی که تمایل دارید کشور فعلی شما لغو و گروه جدید جایگزین شود، می‌توانید مراحل را ادامه دهید."
        )
    else:
        text = (
            "🏴‍☠️ **سامانه هوشمند تاسیس گروه / شبه‌نظامی غیردولتی (گام ۱ از ۴)**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "در این بخش می‌توانید سازمان، جنبش چریکی یا شرکت نظامی خصوصی (PMC) اختصاصی خود را بسازید.\n\n"
            "لطفاً **نام رسمی گروه یا سازمان** خود را ارسال فرمایید:\n\n"
            "*(مثال: سازمان نظامی واگنر، انصارالحق، کارتل گوادالاخارا، ارتش آزاد، نیروهای مقاومت ملی)*"
        )

    context.user_data["militia_wiz"] = {"step": "name"}
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="vip:menu")]]),
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


async def militia_wizard_checkout(query, context, doctrine_key: str):
    """صدور فاکتور نهایی و اطلاعات پرداخت برای گروه اختصاصی."""
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
        "🏴‍☠️ **پیش‌نمایش پرونده و فاکتور مجوز گروه غیردولتی**\n"
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
        "💳 **اطلاعات حساب جهت کارت به کارت:**\n"
        f"• **شماره کارت:** `{card_num}`\n"
        f"• **به نام:** **{card_holder}**\n"
        f"• **بانک:** {bank_name}\n\n"
        "⚠️ پس از واریز، روی دکمه زیر کلیک کرده و تصویر فیش یا کد پیگیری را بفرستید تا گروه شما فوراً تاسیس شود:"
    )

    kb = [
        [InlineKeyboardButton("📸 ارسال تصویر فیش واریزی", callback_data="vip:upload:militia")],
        [InlineKeyboardButton("✍️ ثبت با کد پیگیری (متنی)", callback_data="vip:code:militia")],
        [InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data="vip:menu")],
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


# ==================== صفحه پرداخت و صدور فاکتور VIP ====================

PLANS_METADATA = {
    "vip_1month": {
        "title": "👑 اشتراک ۱ ماهه رهبر ویژه (VIP Leader Pass)",
        "price": getattr(config, "VIP_PASS_PRICE_TOMAN", 79_000),
        "desc": "فعال‌سازی ۳۰ روزه نشان طلایی، اولویت بررسی رول‌ها، رزمایش اضافه روزانه و رادار پیشرفته."
    },
    "vip_3month": {
        "title": "💎 اشتراک ۳ ماهه رهبر ویژه (VIP Leader Pass - ویژه)",
        "price": getattr(config, "VIP_PASS_3MONTH_PRICE_TOMAN", 199_000),
        "desc": "فعال‌سازی ۹۰ روزه خدمات VIP همراه با تخفیف ویژه دوره ۳ ماهه."
    },
    "militia": {
        "title": "🏴‍☠️ مجوز رسمی تاسیس گروه شبه‌نظامی غیردولتی",
        "price": getattr(config, "MILITIA_LICENSE_PRICE_TOMAN", 50_000),
        "desc": "صدور مجوز ایجاد گروه نظامی اختصاصی، نماد سفارشی و کاتالوگ تسلیحاتی اختصاصی."
    }
}


async def vip_checkout_screen(query, context, plan_key: str, country: dict = None):
    """نمایش فاکتور و اطلاعات کارت بانکی جهت واریز VIP."""
    if plan_key == "militia":
        await start_militia_wizard(query, context, query.from_user.id)
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
        await start_militia_wizard(query, context, user_id)

    elif data.startswith("vip:doc:"):
        doc_key = data.split(":", 2)[2]
        await militia_wizard_checkout(query, context, doc_key)

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
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="vip:menu")]]), parse_mode="Markdown")

    elif data.startswith("vip:code:"):
        plan_key = data.split(":", 2)[2]
        context.user_data["vip_input"] = {"step": "awaiting_code", "plan_key": plan_key}
        text = (
            "✍️ **ثبت با کد پیگیری بانکی**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً **کد پیگیری تراکنش + ۴ رقم آخر شماره کارت واریزکننده** را به صورت یک پیام متنی ارسال فرمایید:"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="vip:menu")]]), parse_mode="Markdown")


# ==================== هاندر دریافت ورودی‌های متنی و تصویری ویزارد و فیش ====================

async def vip_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """پردازش مراحل ویزارد ساخت گروه و دریافت فیش بانکی."""
    user = update.effective_user
    user_id = user.id

    # 1. بررسی مراحل ویزارد ساخت گروه
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
    if plan_key == "militia" and "militia_wiz" in context.user_data:
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
