# -*- coding: utf-8 -*-
"""
ماژول خدمات ویژه، اشتراک‌های تومانی و مجوزهای غیردولتی (VIP & Monetization Module).
شامل اشتراک رهبر ویژه (VIP Leader Pass) و مجوز رسمی تاسیس گروه‌های شبه‌نظامی غیردولتی (Non-State Faction).
طراحی شده بر اساس مدل Non-P2W (ارائه امکانات راحتی کاربری، نشان‌های افتخاری، تحلیل‌های ویژه و اولویت بررسی بدون تخریب بالانس بازی).
"""

import html
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

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
    else:
        status_header = "▫️ **وضعیت رهبری شما: اشتراک عادی**"

    text = (
        "👑 **مرکز خدمات ویژه و اشتراک‌های حاکمیتی (VIP)**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{status_header}\n\n"
        "💎 **مزایای اشتراک رهبر ویژه (VIP Leader Pass):**\n"
        "• ⭐ **نشان طلایی VIP:** درج تگ و بج رسمی VIP در پروفایل کشور، بیانیه‌ها و توییت‌ها\n"
        "• ⚡ **اولویت صف بررسی رول‌ها:** تحلیل سریع‌تر و ارزیابی اختصاصی رول‌های نظامی و عملیات‌ها\n"
        "• 🎯 **رزمایش اضافه:** امکان انجام **۱ رزمایش نظامی اضافه** در هر روز جهت افزایش آمادگی رزمی ارتش\n"
        "• 🛡️ **دسترسی به رادار امنیتی:** مشاهده هشدارهای پیشرفته اطلاعاتی و تحرکات منطقه‌ای\n"
        "• 🏆 **جایگاه ممتاز در رنکینگ:** نمایش نشان ستاره‌دار در فهرست رهبران جهان\n\n"
        "🏴‍☠️ **مجوز تاسیس گروه / شبه‌نظامی غیردولتی (Non-State Faction):**\n"
        "• ثبت سازمان یا گروه مسلح مستقل (مشابه واگنر، انصارالله، پیشمرگه، کارتل و...)\n"
        "• انتخاب نام دلخواه، پرچم/نماد اختصاصی، مقر فرماندهی و کاتالوگ تسلیحات سفارشی\n"
        "• استقلال کامل ساختاری و رول‌پلی نامحدود در معادلات منطقه‌ای\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "لطفاً خدمت مورد نظر را جهت مشاهده شرایط و واریز انتخاب فرمایید:"
    )

    p_vip1 = getattr(config, "VIP_PASS_PRICE_TOMAN", 79_000)
    p_vip3 = getattr(config, "VIP_PASS_3MONTH_PRICE_TOMAN", 199_000)
    p_militia = getattr(config, "MILITIA_LICENSE_PRICE_TOMAN", 50_000)

    keyboard = [
        [InlineKeyboardButton(f"👑 خرید VIP یک‌ماهه — {p_vip1:,} تومان", callback_data="vip:plan:vip_1month")],
        [InlineKeyboardButton(f"💎 خرید VIP سه‌ماهه (ویژه) — {p_vip3:,} تومان", callback_data="vip:plan:vip_3month")],
        [InlineKeyboardButton(f"🏴‍☠️ مجوز تاسیس گروه غیردولتی — {p_militia:,} تومان", callback_data="vip:plan:militia")],
        [InlineKeyboardButton("🏪 بازگشت به فروشگاه", callback_data="shopback")],
    ]

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== صفحه پرداخت و صدور فاکتور ====================

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
    """نمایش فاکتور و اطلاعات کارت بانکی جهت واریز."""
    plan = PLANS_METADATA.get(plan_key)
    if not plan:
        await query.answer("پلن انتخابی نامعتبر است.", show_alert=True)
        return

    card_info = getattr(config, "PAYMENT_CARD_INFO", {
        "card_number": "۵۰۴۱-۷۲۱۱-۱۲۳۴-۵۶۷۸",
        "card_holder": "مدیریت بازی سیاست مدرن",
        "bank_name": "بانک رسالت / ملی"
    })

    card_num = card_info.get("card_number", "—")
    card_holder = card_info.get("card_holder", "مدیریت بازی")
    bank_name = card_info.get("bank_name", "بانک عضو شتاب")

    context.user_data["toman_payment_draft"] = {
        "plan_key": plan_key,
        "plan_title": plan["title"],
        "amount": plan["price"],
        "country_id": country["id"] if country else None
    }

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

    elif data == "vip:setup_militia":
        context.user_data["militia_setup"] = {"step": "name"}
        text = (
            "🏴‍☠️ **فرم ثبت سازمان / گروه شبه‌نظامی غیردولتی**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "۱. لطفاً **نام رسمی گروه یا سازمان خود** را ارسال فرمایید:\n\n"
            "*(مثال: «سپاه مدافعان آزادی»، «لشکر سرخ کارتل»، «سازمان نظامی واگنر»)*"
        )
        if query.message:
            await query.message.reply_text(text, parse_mode="Markdown")
        else:
            await query.edit_message_text(text, parse_mode="Markdown")


# ==================== هاندر دریافت ورودی فیش و فرم گروه ====================

async def vip_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """دریافت فیش یا تکمیل فرم ثبت گروه غیردولتی."""
    # ۱. پردازش فرم ساخت گروه غیردولتی
    if context.user_data.get("militia_setup"):
        state = context.user_data["militia_setup"]
        step = state.get("step")
        user = update.effective_user
        user_id = user.id

        if step == "name":
            name = update.message.text.strip() if update.message.text else ""
            if not name or len(name) < 3 or len(name) > 40:
                await update.message.reply_text("❌ لطفاً نامی معتبر (بین ۳ تا ۴۰ حرف) وارد فرمایید:")
                return True
            context.user_data["militia_setup"] = {"step": "flag", "name": name}
            await update.message.reply_text(
                f"✅ **نام گروه ثبت شد:** {name}\n\n"
                "۲. لطفاً **یک ایموجی یا نماد** به عنوان پرچم گروه خود ارسال فرمایید:\n\n"
                "*(مثال: 🏴 یا ⚔️ یا 🦅 یا 🐺 یا 🛡️)*",
                parse_mode="Markdown"
            )
            return True

        elif step == "flag":
            flag = update.message.text.strip() if update.message.text else "🏴"
            if len(flag) > 4:
                flag = flag[:4]
            name = state["name"]
            del context.user_data["militia_setup"]

            # ایجاد سازمان غیردولتی در دیتابیس
            cid = db.create_custom_militia_faction(user_id, name, flag, user.username)

            succ_text = (
                f"🎉 **سازمان غیردولتی {flag} {name} با موفقیت تاسیس شد!**\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "🪖 **تجهیزات و تسلیحات سازمانی فعال‌شده:**\n"
                "• ۵۰۰ دستگاه تویوتا تکنیکال مسلح به دوشکا و زو-۲۳\n"
                "• ۳۰۰ تیم ضدزره مجهز به موشک‌های کورنت\n"
                "• ۲۰۰ فروند پهپاد انتحاری نقطه‌زن و ۵۰ فروند هدهد\n"
                "• ۲۰۰ آتشبار دوش‌پرتاب پدافندی میثاق\n"
                "• ۲۵۰ فروند راکت فجر-۵ و ۳۰ تیر بالستیک فاتح-۱۱۰\n"
                "• ۴۰ فروند قایق تندرو راکت‌انداز عاشورا\n\n"
                "🌐 هم‌اکنون می‌توانید با دکمه‌های پایین صفحه کشور/گروه خود را هدایت فرمایید."
            )
            await update.message.reply_text(succ_text, reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")
            return True

    # ۲. پردازش ارسال فیش واریزی
    vip_state = context.user_data.get("vip_input")
    if not vip_state:
        return False

    del context.user_data["vip_input"]
    step = vip_state.get("step")
    plan_key = vip_state.get("plan_key")
    plan = PLANS_METADATA.get(plan_key, PLANS_METADATA["vip_1month"])

    user = update.effective_user
    user_id = user.id
    country = db.get_country_by_player(user_id)
    c_id = country["id"] if country else None
    c_name = f"{country['flag']} {country['name']}" if country else "فاقد کشور فعال"

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

    # ثبت در دیتابیس
    req_id = db.create_payment_request(
        player_id=user_id,
        country_id=c_id,
        item_type=plan_key,
        plan_title=plan["title"],
        amount_toman=plan["price"],
        receipt_photo_id=photo_id,
        tracking_code=tracking_code
    )

    # پیام تایید به کاربر
    conf_user = (
        f"✅ **فیش واریزی شما با موفقیت ثبت شد! (کد پیگیری درخواست: #{req_id})**\n\n"
        f"📌 **سفارش:** {plan['title']}\n"
        f"💵 **مبلغ:** {plan['price']:,} تومان\n\n"
        "⏳ فیش شما برای تیم مدیریت ارسال گردید و پس از بررسی حساب، سرویس شما فعال و پیام تایید برایتان ارسال خواهد شد."
    )
    await update.message.reply_text(conf_user, reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")

    # ارسال اعلان فوری به ادمین‌های بازی
    admin_text = (
        f"💳 <b>«درخواست جدید پرداخت تومانی» — شماره #{req_id}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>کاربر:</b> {html.escape(user.full_name or '')} (@{user.username or 'ندارد'})\n"
        f"🆔 <b>شناسه کاربری:</b> <code>{user_id}</code>\n"
        f"🌐 <b>کشور فعلی:</b> {c_name}\n\n"
        f"📌 <b>پلن درخواستی:</b> {plan['title']}\n"
        f"💵 <b>مبلغ فاکتور:</b> <b>{plan['price']:,} تومان</b>\n"
        f"📝 <b>کد پیگیری / توضیحات:</b> <code>{html.escape(tracking_code)}</code>\n"
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
