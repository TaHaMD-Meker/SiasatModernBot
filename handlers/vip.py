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
from handlers.battlepass import battlepass_menu


# ==================== منوی اصلی اشتراک‌های VIP ====================

async def vip_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش هاب اصلی فروشگاه خدمات ویژه با دسته‌بندی‌های تفکیک‌شده."""
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
            status_header = f"⭐ **اشتراک رهبری شما: {tier_labels.get(vip_tier, 'VIP فعال')} (تا {exp_date_str})**"
        except Exception:
            status_header = f"⭐ **اشتراک رهبری شما: {tier_labels.get(vip_tier, 'VIP فعال')}**"
    elif is_vip:
        status_header = f"⭐ **اشتراک رهبری شما: {tier_labels.get(vip_tier, 'VIP فعال')}**"
    elif country:
        status_header = f"▫️ **وضعیت رهبری: اشتراک عادی ({country['flag']} {country['name']})**"
    else:
        status_header = "▫️ **وضعیت فعلی: فاقد کشور رسمی**"

    text = (
        "👑 **مرکز خدمات ویژه و فروشگاه حاکمیتی «سیاست مدرن»**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{status_header}\n\n"
        "تمامی خدمات و امکانات ویژه بازی در ۵ بخش تفکیک‌شده در دسترس هستند:\n\n"
        "👑 **۱. اشتراک‌های ویژه رهبری (VIP Passes):**\n"
        "• تخفیف‌های ۵ تا ۲۵ درصدی در نگهداری ارتش، سهمیه رزمایش اضافه، اولویت صف رول‌ها و نشان‌های طلایی و الماس.\n\n"
        "⭐️ **۲. بتل‌پس استراتژیک فصلی (Battle Pass):**\n"
        "• ۲۰ لول جوایز کلان اقتصادی (تا ۷۰M$ پول، ۲۰M نفت، طلا و میکروچیپ) با انجام ماموریت‌ها و لول‌آپ.\n\n"
        "🏴‍☠️ **۳. تاسیس و مجوز گروه‌های غیردولتی (Militia Licenses):**\n"
        "• دریافت مجوز رسمی هدایت گروه‌های مقاومت و ارتش‌های خصوصی با کاتالوگ تسلیحات نامتقارن.\n\n"
        "📦 **۴. بسته‌های بقا و لجستیک (مصرفی - چند بار خرید):**\n"
        "• نفت، غلات، آهن، چیپ و دلار فوری برای بحران انرژی و تولید نظامی.\n\n"
        "🎨 **۵. خدمات دیده شدن و تشریفاتی (غیر P2W + کمی P2W):**\n"
        "• بیانیه طلایی، پین گروه، عنوان تشریفاتی، قاب طلایی + بلیط‌های مانور و بیانیه.\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "👇 لطفاً بخش مورد نظر خود را انتخاب فرمایید:"
    )

    keyboard = [
        [InlineKeyboardButton("👑 ۱. اشتراک‌های ویژه رهبری", callback_data="vip:cat:vip_passes")],
        [InlineKeyboardButton("⭐️ ۲. بتل‌پس استراتژیک فصلی", callback_data="bp:menu")],
        [InlineKeyboardButton("🏴‍☠️ ۳. گروه‌های غیردولتی", callback_data="vip:cat:militia")],
        [InlineKeyboardButton("📦 ۴. بسته‌های بقا و لجستیک (مصرفی)", callback_data="vip:cat:survival")],
        [InlineKeyboardButton("🎨 ۵. خدمات دیده شدن + بلیط‌ها", callback_data="vip:cat:visibility")],
        [InlineKeyboardButton("🔙 بازگشت به کشور", callback_data="country:back_profile")],
    ]

    if update.message:
        await update.message.reply_text("👑 **فروشگاه خدمات ویژه «سیاست مدرن»**", reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        except Exception:
            pass


async def vip_passes_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش تعرفه‌ها و سطوح ۴ گانه اشتراک رهبری VIP."""
    user_id = update.effective_user.id
    text = (
        "👑 **اشتراک‌های ۴ سطحی رهبری ویژه (VIP Leader Passes)**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🥉 **۱. اشتراک برنز ({price_label('vip_bronze')}):**\n"
        "• 📉 تخفیف ۵٪ در هزینه نگهداری ارتش\n"
        "• 🎯 +۱ رزمایش نظامی اضافه روزانه\n"
        "• 📜 ۴ اسلات قرارداد تجاری همزمان\n\n"
        f"🥈 **۲. اشتراک نقره ({price_label('vip_silver')}):**\n"
        "• 📉 تخفیف ۱۰٪ در هزینه نگهداری ارتش\n"
        "• ⚡ اولویت رده ۲ در صف بررسی رول‌ها\n"
        "• 🎯 +۲ رزمایش نظامی اضافه روزانه\n"
        "• 🛡️ رادار پایش امنیتی تحرکات مرزی\n"
        "• 📜 ۶ اسلات قرارداد تجاری\n\n"
        f"🥇 **۳. اشتراک طلا ({price_label('vip_gold')}):**\n"
        "• 📉 تخفیف ۱۵٪ در هزینه نگهداری ارتش\n"
        "• 🚀 اولویت فوری VIP در بررسی رول‌ها و جنگ‌ها\n"
        "• 🎯 +۳ رزمایش نظامی اضافه روزانه\n"
        "• 🚢 ۱۵٪ تخفیف ترانزیت لجستیک معاهدات\n"
        "• 🛡️ تقویت ضداطلاعات و امنیت سایبری\n"
        "• 📜 ۸ اسلات قرارداد تجاری\n\n"
        f"💎 **۴. اشتراک الماس ({price_label('vip_diamond')}):**\n"
        "• 📉 تخفیف ۲۵٪ در کل هزینه نگهداری ارتش و زرادخانه‌ها\n"
        "• ⚡⚡ بررسی آنی و اختصاصی رول‌ها (اولویت صفر)\n"
        "• 🎯 رزمایش نامحدود روزانه (آمادگی رزمی ۱۰۰٪ همیشگی)\n"
        "• 🏢 ۵۰٪ تخفیف نگهداری و اجاره پایگاه‌های راهبردی\n"
        "• 📜 قراردادهای تجاری نامحدود\n"
        "• 👑 مشاوره مستقیم تنظیم دکترین نظامی با تحلیلگر ارشد\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "پلن اشتراک مورد نظر را جهت دریافت فاکتور انتخاب فرمایید:"
    )

    keyboard = [
        [InlineKeyboardButton(f"🥉 اشتراک برنز — {price_label('vip_bronze')}", callback_data="vip:plan:vip_bronze")],
        [InlineKeyboardButton(f"🥈 اشتراک نقره — {price_label('vip_silver')}", callback_data="vip:plan:vip_silver")],
        [InlineKeyboardButton(f"🥇 اشتراک طلا — {price_label('vip_gold')}", callback_data="vip:plan:vip_gold")],
        [InlineKeyboardButton(f"💎 اشتراک الماس — {price_label('vip_diamond')}", callback_data="vip:plan:vip_diamond")],
        [InlineKeyboardButton("🔙 بازگشت به فروشگاه ویژه", callback_data="vip:menu")],
    ]

    if update.message:
        await update.message.reply_text("👑 **فروشگاه خدمات ویژه «سیاست مدرن»**", reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        except Exception:
            pass


async def survival_packs_menu(query, context):
    text = (
        "📦 **بسته‌های بقا و لجستیک - مصرفی (چند بار خرید)**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "با بحران نفت اروپا (ذخایر ۱-۳ روزه) و نیاز آهن برای تولید تانک/ناو، این بسته‌ها همیشه نیاز میشن. هر بسته مصرفیه و روزی تا ۳ بار قابل خریده. هر کدوم رو بزنی توضیح کاملش تو فاکتور میاد:\n\n"
        f"🟤 **بسته کوچک ({price_label('survival_small')}):**\n"
        "• 🛢️ ۴۰۰,۰۰۰ بشکه نفت (سوخت ۴ روز ارتش) + 🌾 ۱۵,۰۰۰ تن غلات (جلوگیری از قحطی و افت رضایت) + 💵 ۳M دلار نقد\n\n"
        f"🟠 **بسته متوسط ({price_label('survival_medium')}):**\n"
        "• 🛢️ ۹۰۰,۰۰۰ بشکه نفت + 🌾 ۳۰,۰۰۰ تن غلات + ⛏️ ۸,۰۰۰ تن آهن (ساخت ۳۲۰ تانک) + 💻 ۳۰۰ چیپ (پهپاد و موشک) + 💵 ۶M دلار\n\n"
        f"🔴 **بسته بزرگ ({price_label('survival_large')}):**\n"
        "• 🛢️ ۱.۸M بشکه نفت (سوخت پایگاه‌ها و ناوگان) + 🌾 ۶۰,۰۰۰ تن غلات + ⛏️ ۱۵,۰۰۰ تن آهن + 💻 ۸۰۰ چیپ + 💵 ۱۰M دلار\n\n"
        f"💎 **بسته فوق‌سنگین ({price_label('survival_ultra')}):**\n"
        "• 🛢️ ۳M بشکه نفت + 🌾 ۱۰۰,۰۰۰ تن غلات + ⛏️ ۳۰,۰۰۰ تن آهن + 💻 ۱,۵۰۰ چیپ + 🪙 ۵۰ طلا + 💵 ۱۸M دلار → وقتی تحت محاصره‌ای و بورس بسته‌ست\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "بسته مورد نظر رو انتخاب کن:"
    )
    kb = [
        [InlineKeyboardButton(f"🟤 بقا کوچک - {price_label('survival_small', short=True)}", callback_data="vip:plan:survival_small")],
        [InlineKeyboardButton(f"🟠 بقا متوسط - {price_label('survival_medium', short=True)}", callback_data="vip:plan:survival_medium")],
        [InlineKeyboardButton(f"🔴 بقا بزرگ - {price_label('survival_large', short=True)}", callback_data="vip:plan:survival_large")],
        [InlineKeyboardButton(f"💎 بقا فوق‌سنگین - {price_label('survival_ultra', short=True)}", callback_data="vip:plan:survival_ultra")],
        [InlineKeyboardButton("🔙 بازگشت به فروشگاه", callback_data="vip:menu")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


async def visibility_services_menu(query, context):
    text = (
        "🎨 **خدمات دیده شدن، تشریفاتی و بلیط‌های مصرفی**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "این بخش فقط کمی P2W ـه و بیشتر برای دیده شدن و فعالیت بیشتره (مصرفی/موقتی). هر چی می‌زنی روش توضیحش تو فاکتور میاد که به چه دردی میخوره:\n\n"
        "⭐️ **بوستر بتل‌پس (سرعت لول‌آپ):**\n"
        f"• ۳ روزه ۲x XP - {price_label('bp_booster_3d')} → تمام XP (بیانیه، تجارت، مانور، بورس) دو برابر میشه، پله‌های بتل‌پس سریع‌تر باز میشه\n"
        f"• ۷ روزه ۲x XP - {price_label('bp_booster_7d')} → یه هفته کامل XP دو برابر، برای رسوندن از پله ۱۰ به ۲۰\n"
        f"• ۳۰ روزه ۲x XP - {price_label('bp_booster_30d')} → کل فصل بوست، برای هاردکورها\n\n"
        "🎫 **بلیط اقدام فوری (جلوگیری از توقف):**\n"
        f"• ۱ مانور اضافه - {price_label('ticket_drill')} → وقتی سقف روزانه مانورت پر شده و میخوای آمادگی رو به ۸۵٪+ برسونی\n"
        f"• پک ۳ مانور - {price_label('ticket_drill_3')} → ۳ مانور ذخیره، خودکار مصرف میشه\n"
        f"• ۱ بیانیه اضافه - {price_label('ticket_statement')} → اگه امروز وقت نداری بیانیه بدی، جلوی سلب مالکیت ۰۰:۰۰ رو میگیره\n"
        f"• پک ۵ بیانیه - {price_label('ticket_statement_5')} → ۵ روز مصونیت خودکار از سلب مالکیت\n"
        f"• بوست اسلات قرارداد ۳ روزه - {price_label('ticket_contract_3d')} → ۳ روز قرارداد نامحدود به جای ۴/۶/۸ تایی VIP\n"
        f"• بوست اسلات قرارداد ۷ روزه - {price_label('ticket_contract_7d')} → هفته کامل تجارت نامحدود، برای بحران نفت\n\n"
        "🎨 **دیده شدن و تشریفاتی (غیر P2W):**\n"
        f"• بیانیه طلایی ۱ عدد - {price_label('golden_stmt_1')} → بیانیه‌ت با کادر طلایی 👑 تو کانال @SiasatModern میره، همه می‌بینن\n"
        f"• بیانیه طلایی ۳ عدد - {price_label('golden_stmt_3')} → ۳ روز خبر اول کانال میشی\n"
        f"• بیانیه طلایی ۱۰ عدد - {price_label('golden_stmt_10')} → بسته رسانه‌ای ماهانه\n"
        f"• پین گروه ۱ عدد (۱۲ ساعت) - {price_label('pin_1')} → پیامت ۱۲ ساعت بالای گروه پین میمونه\n"
        f"• پین گروه ۳ عدد - {price_label('pin_3')} → ۳۶ ساعت پین تضمینی\n"
        f"• عنوان تشریفاتی ۷ روزه - {price_label('title_7d')} → لقب دلخواه (سلطان نفت) کنار اسم کشورت تو رنکینگ و اخبار\n"
        f"• عنوان تشریفاتی ۳۰ روزه - {price_label('title_30d')} → یه ماه لقب میمونه\n"
        f"• قاب طلایی ۷ روزه - {price_label('frame_7d')} → پروفایل کشورت تو /country با قاب طلایی\n"
        f"• قاب طلایی ۳۰ روزه - {price_label('frame_30d')} → یه ماه قاب طلایی\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "سرویس مورد نظر رو انتخاب کن:"
    )
    kb = [
        [InlineKeyboardButton(f"⭐️ بوستر ۳ روزه - {price_short_k('bp_booster_3d')}", callback_data="vip:plan:bp_booster_3d"), InlineKeyboardButton(f"⭐️ بوستر ۷ روزه - {price_short_k('bp_booster_7d')}", callback_data="vip:plan:bp_booster_7d")],
        [InlineKeyboardButton(f"⭐️ بوستر ماهانه - {price_short_k('bp_booster_30d')}", callback_data="vip:plan:bp_booster_30d")],
        [InlineKeyboardButton(f"🎫 ۱ مانور - {price_short_k('ticket_drill')}", callback_data="vip:plan:ticket_drill"), InlineKeyboardButton(f"🎫 پک ۳ مانور - {price_short_k('ticket_drill_3')}", callback_data="vip:plan:ticket_drill_3")],
        [InlineKeyboardButton(f"📝 ۱ بیانیه - {price_short_k('ticket_statement')}", callback_data="vip:plan:ticket_statement"), InlineKeyboardButton(f"📝 پک ۵ بیانیه - {price_short_k('ticket_statement_5')}", callback_data="vip:plan:ticket_statement_5")],
        [InlineKeyboardButton(f"📜 اسلات قرارداد ۳ روزه - {price_short_k('ticket_contract_3d')}", callback_data="vip:plan:ticket_contract_3d"), InlineKeyboardButton(f"📜 اسلات ۷ روزه - {price_short_k('ticket_contract_7d')}", callback_data="vip:plan:ticket_contract_7d")],
        [InlineKeyboardButton(f"📢 بیانیه طلایی ۱ - {price_short_k('golden_stmt_1')}", callback_data="vip:plan:golden_stmt_1"), InlineKeyboardButton(f"📢 طلایی ۳ - {price_short_k('golden_stmt_3')}", callback_data="vip:plan:golden_stmt_3")],
        [InlineKeyboardButton(f"📢 طلایی ۱۰ - {price_short_k('golden_stmt_10')}", callback_data="vip:plan:golden_stmt_10")],
        [InlineKeyboardButton(f"📌 پین ۱ - {price_short_k('pin_1')}", callback_data="vip:plan:pin_1"), InlineKeyboardButton(f"📌 پین ۳ - {price_short_k('pin_3')}", callback_data="vip:plan:pin_3")],
        [InlineKeyboardButton(f"🏷️ عنوان ۷ روزه - {price_short_k('title_7d')}", callback_data="vip:plan:title_7d"), InlineKeyboardButton(f"🏷️ عنوان ۳۰ روزه - {price_short_k('title_30d')}", callback_data="vip:plan:title_30d")],
        [InlineKeyboardButton(f"🖼️ قاب ۷ روزه - {price_short_k('frame_7d')}", callback_data="vip:plan:frame_7d"), InlineKeyboardButton(f"🖼️ قاب ۳۰ روزه - {price_short_k('frame_30d')}", callback_data="vip:plan:frame_30d")],
        [InlineKeyboardButton("🔙 بازگشت به فروشگاه", callback_data="vip:menu")],
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


# ==================== فهرست سازمان‌ها و گروه‌های شبه‌نظامی غیردولتی ====================

async def show_predefined_factions_menu(query, context, user_id: int):
    """نمایش لیست گروه‌های آماده معتبر به همراه گزینه سفارشی و ارزیابی انطباق ژئوپلیتیک با کشور کاربر."""
    factions = getattr(config, "PREDEFINED_MILITIA_FACTIONS", {})
    taken_keys = db.get_taken_militia_faction_keys()
    country = db.get_country_by_player(user_id)
    c_key = country.get("country_key") if country else None

    price, _militia_pct = militia_price()

    if country and not (c_key or "").startswith("faction_"):
        header_text = (
            f"🏴‍☠️ **تاسیس بازوی نیابتی / ارتش خصوصی برای دولت {country['flag']} {country['name']}**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "به عنوان رهبر کشور، می‌توانید یکی از یگان‌های هم‌پیمان زیر را به عنوان **«بازوی نیابتی و نیروی نامتقارن»** کشور خود فعال فرمایید:\n\n"
            "• 💰 **۲۵ میلیون دلار** بودجه و خزانه اولیه سازمانی\n"
            "• 🪖 **۶۰,۰۰۰ رزمنده** آماده‌باش\n"
            "• 🎖️ **تسلیحات و ادوات تخصصی بومی**\n"
            f"• 💵 **تعرفه صدور مجوز:** {militia_price_label()} (یک‌بار پرداخت)\n\n"
            "*(یگان‌های ناسازگار با دکترین سیاسی کشور شما قفل هستند؛ ساخت گروه سفارشی برای همه آزاد است)*"
        )
    else:
        header_text = (
            "🏴‍☠️ **فهرست سازمان‌ها و گروه‌های شبه‌نظامی غیردولتی معتبر جهان**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "یکی از گروه‌های آماده زیر را جهت هدایت انتخاب فرمایید، یا در انتها گروه سفارشی با مشخصات دلخواه خود بسازید:\n\n"
            "• 💰 **۲۵ میلیون دلار** خزانه و بودجه اولیه\n"
            "• 🪖 **۶۰,۰۰۰ رزمنده** آماده‌باش\n"
            "• 🎖️ **تسلیحات و تجهیزات واقعی و تخصصی**\n"
            f"• 💵 **تعرفه صدور مجوز:** {militia_price_label()} (یک‌بار پرداخت)\n"
        )

    keyboard = []
    row = []
    for f_key, f_info in factions.items():
        is_taken = f_key in taken_keys
        allowed_allies = f_info.get("allowed_countries", [])
        
        is_compatible = True
        if country and c_key and not c_key.startswith("faction_") and allowed_allies:
            is_compatible = c_key in allowed_allies

        if is_taken:
            btn_label = f"🔒 {f_info['short_name']}"
            cb_data = "ignore"
        elif not is_compatible:
            btn_label = f"🔒 {f_info['short_name']} (نامنطبق)"
            cb_data = f"vip:f_incompat:{f_key}"
        else:
            btn_label = f"{f_info['flag']} {f_info['short_name']}"
            cb_data = f"vip:fpick:{f_key}"

        row.append(InlineKeyboardButton(btn_label, callback_data=cb_data))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # دکمه گروه سفارشی با نام دلخواه
    keyboard.append([InlineKeyboardButton("✨ ساخت گروه سفارشی (نام و نماد دلخواه)", callback_data="vip:fpick:custom")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به فروشگاه ویژه", callback_data="vip:menu")])

    await query.edit_message_text(header_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


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

    price, _militia_pct = militia_price()

    text = (
        f"🏴‍☠️ **پرونده و فاکتور هدایت {f_info['flag']} {f_info['name']}**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"• **مقر فرماندهی:** {f_info['hq']}\n"
        f"• **دکترین:** {f_info['doctrine']}\n"
        f"• **شرح فعالیت:** {f_info['desc']}\n\n"
        f"🎖️ **تجهیزات و تسلیحات سازمانی:** {item_count} قلم جنگ‌افزار بومی و اختصاصی\n"
        "• 💰 خزانه اولیه: **۲۵ میلیون دلار**\n"
        "• 🪖 رزمندگان آماده‌باش: **۶۰,۰۰۰ نفر**\n"

        "━━━━━━━━━━━━━━━━━━\n"
        f"💵 **مبلغ مجوز:** **{price:,} تومان**{militia_price_note()}\n\n"
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

    price, _militia_pct = militia_price()

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

        "━━━━━━━━━━━━━━━━━━\n"
        f"💵 **مبلغ قابل پرداخت:** **{price:,} تومان**{militia_price_note()}\n\n"
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
        "desc": "تخفیف ۵٪ نگهداری ارتش، ۱ مانور اضافه روزانه، ۴ اسلات قرارداد تجاری و نشان برنزی."
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
        "price": 100_000,
        "desc": "صدور مجوز ایجاد گروه نظامی اختصاصی، نماد سفارشی و کاتالوگ تسلیحاتی اختصاصی."
    },
    "battle_pass": {
        "title": "⭐️ بتل‌پس فصلی استراتژیک (Season 1 Pass)",
        "price": 300_000,
        "desc": "دسترسی به ۲۰ لول جوایز کلان اقتصادی (۷۰M$ + ۲۰M نفت + طلا و چیپ) + ۲۵٪ بوست XP."
    },
    "pass": {
        "title": "⭐️ بتل‌پس فصلی استراتژیک (Season 1 Pass)",
        "price": 300_000,
        "desc": "دسترسی به ۲۰ لول جوایز کلان + ۲۵٪ بوست XP."
    },
    # ===== بسته‌های بقا و لجستیک (مصرفی - چند بار خرید) =====
    "survival_small": {"title": "🟤 بسته بقا کوچک", "price": 149_000, "desc": "برای وقتی که نفت و غلاتت ته کشیده و رضایت عمومی داره میفته. ۴۰۰k نفت (مصرف ارتش و کارخانجات) + ۱۵k غلات (جلوگیری از قحطی) + ۳M دلار نقد. مصرفیه و روزی ۳ بار میتونی بخری."},
    "survival_medium": {"title": "🟠 بسته بقا متوسط (محبوب)", "price": 249_000, "desc": "پرطرفدارترین بسته برای بحران اروپا. ۹۰۰k نفت (سوخت ۹ روز ارتش متوسط) + ۳۰k غلات + ۸k آهن (برای ساخت تانک و ناو) + ۳۰۰ چیپ + ۶M دلار. جلو رضایت منفی و توقف کارخونه رو میگیره."},
    "survival_large": {"title": "🔴 بسته بقا بزرگ", "price": 389_000, "desc": "برای ابرقدرت‌ها و جنگ طولانی. ۱.۸M نفت (سوخت ناوگان و پایگاه‌ها) + ۶۰k غلات + ۱۵k آهن (ساخت ۶۰۰ تانک یا ۳۰ ناوچه) + ۸۰۰ چیپ + ۱۰M دلار. خزانه و ذخایر رو یکجا شارژ می‌کنه."},
    "survival_ultra": {"title": "💎 بسته بقا فوق‌سنگین", "price": 590_000, "desc": "بسته اضطراری جنگ تمام‌عیار. ۳M نفت + ۱۰۰k غلات (۱۰۰ روز مصرف) + ۳۰k آهن + ۱۵۰۰ چیپ (برای موشک و پدافند) + ۵۰ شمش طلا + ۱۸M دلار. وقتی تحت محاصره‌ای و بورس بسته‌ست نجاتت میده."},
    # ===== بلیط اقدام فوری =====
    "ticket_drill": {"title": "🎫 بلیط ۱ مانور اضافه", "price": 79_000, "desc": "سقف روزانه مانورت پر شده؟ این بلیط ۱ مانور فوری بهت میده: +۴٪ آمادگی رزمی +۲٪ رضایت عمومی. برای رسوندن آمادگی به ۸۵٪ و گرفتن XP بتل‌پس لازمه. مصرفیه."},
    "ticket_drill_3": {"title": "🎫 پک ۳ تایی مانور", "price": 189_000, "desc": "۳ مانور فوری با تخفیف. هر مانور +۴٪ آمادگی، برای وقتی که میخوای سریع به ۱۰۰٪ برسی یا تسک بتل‌پس (آمادگی ۸۵٪) رو پر کنی. ۳ بلیط ذخیره میشه و خودکار مصرف میشه."},
    "ticket_statement": {"title": "📝 بلیط ۱ بیانیه اضافه", "price": 49_000, "desc": "امروز وقت نداری بیانیه بدی؟ این بلیط ۱ بیانیه به حساب فعالیت روزانه‌ت اضافه می‌کنه تا ساعت ۰۰:۰۰ سلب مالکیت نشی. برای روزای شلوغ و مسافرت. مصرفیه و خودکار استفاده میشه."},
    "ticket_statement_5": {"title": "📝 پک ۵ تایی بیانیه", "price": 189_000, "desc": "۵ بلیط بیانیه با تخفیف. ۵ روز مصونیت از سلب مالکیت بدون نیاز به تایپ. برای کسایی که میخوان کشورشون همیشه امن بمونه. هر شب ۰۰:۰۰ خودکار ۱ دونه مصرف میشه اگه بیانیه کم داشته باشی."},
    "ticket_contract_3d": {"title": "📜 بوست اسلات قرارداد ۳ روزه", "price": 99_000, "desc": "۳ روز قرارداد تجاری نامحدود (بدون سقف ۴/۶/۸ تایی VIP). برای وقتی که میخوای همزمان با ۱۰ کشور نفت و آهن معامله کنی. بعد ۳ روز خودکار برمیگرده به حالت عادی."},
    "ticket_contract_7d": {"title": "📜 بوست اسلات قرارداد ۷ روزه", "price": 179_000, "desc": "۷ روز قرارداد نامحدود با تخفیف. برای تاجرهای حرفه‌ای که بازار رو قبضه می‌کنن. مناسب برای هفته بحران نفت اروپا."},
    # ===== بوستر بتل‌پس =====
    "bp_booster_3d": {"title": "⭐️ بوستر بتل‌پس ۳ روزه ۲x", "price": 129_000, "desc": "۳ روز تمام XP بتل‌پست ۲ برابر میشه (بیانیه، تجارت، مانور، بورس). برای رسوندن سریع از پله ۱۰ به ۲۰ و گرفتن جایزه ۱۵M دلاری تایتان. فقط برای دارندگان بتل‌پس پرمیوم کار می‌کنه."},
    "bp_booster_7d": {"title": "⭐️ بوستر بتل‌پس ۷ روزه ۲x", "price": 229_000, "desc": "۷ روز XP دو برابر با تخفیف. اگه بتل‌پس رو تازه خریدی و میخوای تو یه هفته تمومش کنی، این بهترین گزینه‌ست. تا ۷ روز هر فعالیتی ۲x حساب میشه."},
    "bp_booster_30d": {"title": "⭐️ بوستر بتل‌پس ماهانه ۲x", "price": 590_000, "desc": "۳۰ روز کامل XP دو برابر. برای فصل جدید. با این بوستر کل ۲۰ پله بتل‌پس (۷۰M دلار + ۲۰M نفت) رو تقریبا ۲ برابر سریع‌تر باز می‌کنی. به درد پلیرهای هاردکور میخوره."},
    # ===== خدمات دیده شدن =====
    "golden_stmt_1": {"title": "📢 بیانیه طلایی ۱ عدد", "price": 59_000, "desc": "بیانیه‌ت با کادر طلایی 👑 و عنوان تشریفاتی تو کانال @SiasatModern منتشر میشه. همه پلیرها می‌بینن. قدرت نمیده ولی پرستیژ و دیده شدن میده. ۱ اعتبار مصرفی."},
    "golden_stmt_3": {"title": "📢 پک ۳ تایی بیانیه طلایی", "price": 149_000, "desc": "۳ بیانیه طلایی با تخفیف. برای ۳ روز پشت سر هم خبر اول کانال میشی. مناسب برای جنگ روانی و اعلام اتحادها. هر ارسال ۱ اعتبار کم میشه."},
    "golden_stmt_10": {"title": "📢 پک ۱۰ تایی بیانیه طلایی", "price": 399_000, "desc": "۱۰ بیانیه طلایی - بسته رسانه‌ای ماهانه. کل ماه هر بیانیه مهمت طلایی میره کانال. برای رهبرای فعال که میخوان همیشه صدر اخبار باشن."},
    "pin_1": {"title": "📌 پین گروه ۱۲ ساعته", "price": 79_000, "desc": "بیانیه یا توییتت ۱۲ ساعت تو گروه اصلی بازی پین میشه (بالای چت می‌مونه). همه اعضا می‌بینن. برای اعلام جنگ یا اتحاد خیلی جواب میده. ۱ اعتبار مصرفی."},
    "pin_3": {"title": "📌 پک ۳ تایی پین گروه", "price": 189_000, "desc": "۳ پین ۱۲ ساعته با تخفیف. ۳۶ ساعت دیده شدن تضمینی تو گروه. برای بحران‌ها و کمپین‌های سیاسی."},
    "title_7d": {"title": "🏷️ عنوان تشریفاتی ۷ روزه", "price": 99_000, "desc": "یه لقب دلخواه (مثلا سلطان نفت، امپراتور شرق) ۷ روز کنار اسم کشورت تو /country و رنکینگ و اخبار نشون داده میشه. قدرت نمیده ولی همه می‌بینن کیه. بعد ۷ روز منقضی میشه و باید تمدید کنی."},
    "title_30d": {"title": "🏷️ عنوان تشریفاتی ۳۰ روزه", "price": 289_000, "desc": "عنوان تشریفاتی ۳۰ روزه با تخفیف ماهانه. یه ماه کامل لقبت می‌مونه و تو تمام فیش‌های تجاری و اخبار هم نمایش داده میشه. برای پرستیژ بلندمدت."},
    "frame_7d": {"title": "🖼️ قاب طلایی ۷ روزه", "price": 79_000, "desc": "پروفایل کشورت تو /country با قاب طلایی 👑 نمایش داده میشه. همه می‌فهمن VIP تشریفاتی هستی. ۷ روزه و بعدش باید تمدید کنی. قدرت نمیده، فقط ظاهریه."},
    "frame_30d": {"title": "🖼️ قاب طلایی ۳۰ روزه", "price": 249_000, "desc": "قاب طلایی ماهانه با تخفیف. ۳۰ روز پروفایلت طلایی می‌مونه و تو لیست کشورها هم با افکت خاص نشون داده میشه. برای کسایی که میخوان همیشه متمایز باشن."},
    # نام‌های مستعار جهت سازگاری کامل
    "bronze": {"title": "🥉 اشتراک برنز رهبری", "tier": "bronze", "price": 79_000, "desc": ""},
    "silver": {"title": "🥈 اشتراک نقره‌ای رهبری", "tier": "silver", "price": 179_000, "desc": ""},
    "gold": {"title": "🥇 اشتراک طلایی رهبری", "tier": "gold", "price": 349_000, "desc": ""},
    "diamond": {"title": "💎 اشتراک الماس", "tier": "diamond", "price": 650_000, "desc": ""},
    "vip_1month": {"title": "🥇 اشتراک طلایی رهبری", "tier": "gold", "price": 349_000, "desc": ""},
}


# ==================== قیمت پویا و تخفیف فروشگاه ویژه ====================
# ادمین از پنل مدیریت، درصد تخفیف هر آیتم را تعیین می‌کند؛ این توابع همه‌ی
# منوها و فاکتورها را با همان تخفیف هماهنگ می‌کنند (بدون تغییر قیمت پایه در کد).


_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _toman(num: int) -> str:
    """۷۹۰۰۰ → «۷۹٬۰۰۰» با ارقام فارسی و جداکننده‌ی هزارگان فارسی."""
    s = f"{int(num or 0):,}".replace(",", "٬")
    return s.translate(_FA_DIGITS)


def effective_price(plan_key: str) -> int:
    """قیمت نهایی آیتم با اعمال تخفیف جاری (تومان)."""
    plan = PLANS_METADATA.get(plan_key)
    base = int((plan or {}).get("price") or 0)
    pct = db.get_vip_discount(plan_key)
    if pct <= 0:
        return base
    return int(round(base * (100 - pct) / 100))


def discount_of(plan_key: str) -> int:
    """درصد تخفیف جاری آیتم (۰ = بدون تخفیف)."""
    return db.get_vip_discount(plan_key)


def price_label(plan_key: str, short: bool = False) -> str:
    """برچسب قیمت برای دکمه/متن؛ اگر تخفیف دارد درصدش را هم نشان می‌دهد."""
    base = int((PLANS_METADATA.get(plan_key) or {}).get("price") or 0)
    eff = effective_price(plan_key)
    pct = discount_of(plan_key)
    if short:
        if pct > 0:
            return f"{_toman(eff)} ت ({_toman(pct)}٪-)"
        return f"{_toman(eff)} ت"
    if pct > 0:
        return f"{_toman(eff)} تومان ({_toman(pct)}٪ تخفیف از {_toman(base)})"
    return f"{_toman(eff)} تومان"


def price_short_k(plan_key: str) -> str:
    """برچسب کوتاه برای دکمه‌ها: «۱۲۹k» و با تخفیف «۱۰۳k (۱۰٪-)»."""
    eff = effective_price(plan_key)
    pct = discount_of(plan_key)
    txt = f"{_toman(eff // 1000)}k" if eff >= 1000 else f"{_toman(eff)} ت"
    if pct > 0:
        txt += f" ({_toman(pct)}٪-)"
    return txt


def price_note(plan_key: str) -> str:
    """خط توضیح تخفیف برای فاکتور؛ خالی اگر تخفیفی نیست."""
    pct = discount_of(plan_key)
    if pct <= 0:
        return ""
    base = int((PLANS_METADATA.get(plan_key) or {}).get("price") or 0)
    return f"\n🎉 **{_toman(pct)}٪ تخفیف اعمال شد** — قیمت قبلی: {_toman(base)} تومان"


def militia_price() -> tuple[int, int]:
    """قیمت مجوز گروهک با تخفیف جاری. برمی‌گرداند: (قیمت نهایی, درصد تخفیف)."""
    base = int((PLANS_METADATA.get("militia") or {}).get("price") or 100_000)
    pct = db.get_vip_discount("militia")
    if pct <= 0:
        return base, 0
    return int(round(base * (100 - pct) / 100)), int(pct)


def militia_price_label() -> str:
    """برچسب قیمت گروهک؛ «۱۰۰٬۰۰۰ تومان» یا «۸۰٬۰۰۰ تومان (۲۰٪ تخفیف از ۱۰۰٬۰۰۰)»."""
    eff, pct = militia_price()
    if pct <= 0:
        return f"{_toman(eff)} تومان"
    base = int((PLANS_METADATA.get("militia") or {}).get("price") or 100_000)
    return f"{_toman(eff)} تومان ({_toman(pct)}٪ تخفیف از {_toman(base)})"


def militia_price_note() -> str:
    """خط توضیح تخفیف مجوز گروهک؛ خالی اگر تخفیفی نیست."""
    _eff, pct = militia_price()
    if pct <= 0:
        return ""
    base = int((PLANS_METADATA.get("militia") or {}).get("price") or 100_000)
    return f"\n🎉 **{_toman(pct)}٪ تخفیف اعمال شد** — قیمت قبلی: {_toman(base)} تومان"


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
        f"💵 **مبلغ قابل پرداخت:** **{effective_price(plan_key):,} تومان**{price_note(plan_key)}\n"
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

    elif data == "vip:cat:vip_passes":
        await vip_passes_menu(update, context)

    elif data in ("vip:cat:militia", "vip:militia_wizard_start", "vip:plan:militia"):
        await show_predefined_factions_menu(query, context, user_id)

    elif data == "vip:cat:survival":
        await survival_packs_menu(query, context)

    elif data == "vip:cat:visibility":
        await visibility_services_menu(query, context)

    elif data == "vip:cat:battle_pass":
        await battlepass_menu(update, context)

    elif data.startswith("vip:fpick:"):
        f_key = data.split(":", 2)[2]
        if f_key == "custom":
            await start_custom_militia_wizard(query, context)
        else:
            await preview_predefined_faction_checkout(query, context, f_key)

    elif data.startswith("vip:f_incompat:"):
        f_key = data.split(":", 2)[2]
        f_info = getattr(config, "PREDEFINED_MILITIA_FACTIONS", {}).get(f_key, {})
        c_name = country['name'] if country else "کشور شما"
        await query.answer(
            f"⛔ یگان «{f_info.get('name', f_key)}» با جبهه سیاسی و دکترین {c_name} هم‌پوشانی ندارد.\n\n💡 لطفاً یگان‌های هم‌پیمان یا «ساخت گروه سفارشی» را انتخاب فرمایید.",
            show_alert=True
        )

    elif data.startswith("vip:doc:"):
        doc_key = data.split(":", 2)[2]
        await custom_militia_checkout(query, context, doc_key)

    elif data.startswith("vip:plan:"):
        plan_key = data.split(":", 2)[2]
        # خدمات نیازمند ورودی متنی دلخواه قبل از فاکتور
        if plan_key.startswith("title_"):
            context.user_data["vip_pending_plan"] = plan_key
            context.user_data["vip_input"] = {"step": "awaiting_custom_title", "plan_key": plan_key}
            await query.edit_message_text(
                "🏷️ **عنوان تشریفاتی دلخواه**\n━━━━━━━━━━━━━━━━━━\n\nلطفا عنوانی که میخوای کنار اسم کشورت نمایش داده بشه رو بفرست (حداکثر ۳۰ کاراکتر):\nمثلا: `امپراتور بزرگ`، `سلطان نفت`، `تایتان اقتصادی`",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="vip:cat:visibility")]]),
                parse_mode="Markdown"
            )
            return
        # تغییر نام و پرچم حذف شد - غیر واقعی
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

    # 1.5 بررسی ورودی‌های خدمات دیده شدن (عنوان، نام، پرچم)
    vip_state = context.user_data.get("vip_input")
    if vip_state and update.message.text:
        step = vip_state.get("step")
        plan_key = vip_state.get("plan_key")
        txt_in = update.message.text.strip()
        if step == "awaiting_custom_title":
            if len(txt_in) < 2 or len(txt_in) > 30:
                await update.message.reply_text("❌ عنوان باید ۲ تا ۳۰ کاراکتر باشه، دوباره بفرست:")
                return True
            # ذخیره عنوان و برو به صفحه پرداخت
            context.user_data["vip_custom_payload"] = {"custom_title": txt_in, "title": txt_in}
            # نگه داشتن plan_key برای فاکتور
            context.user_data["vip_input"] = {"step": "awaiting_checkout", "plan_key": plan_key}
            country = db.get_country_by_player(user_id)
            # ساخت یک query ساختگی برای نمایش فاکتور - از vip_checkout_screen استفاده می‌کنیم via message
            # برای سادگی، مستقیم فاکتور رو به صورت پیام می‌فرستیم
            plan = PLANS_METADATA.get(plan_key)
            card_info = getattr(config, "PAYMENT_CARD_INFO", {"card_number": "۵۸۹۲-۱۰۱۴-۶۷۲۲-۷۲۲۵", "card_holder": "زینب فیاضی", "bank_name": "بانک سپه"})
            card_num = card_info.get("card_number", "۵۸۹۲-۱۰۱۴-۶۷۲۲-۷۲۲۵")
            card_holder = card_info.get("card_holder", "زینب فیاضی")
            bank_name = card_info.get("bank_name", "بانک سپه")
            text = (
                f"💳 **فاکتور پرداخت - {plan['title']}**\n"
                f"🏷️ عنوان انتخابی: **{txt_in}**\n"
                f"💵 مبلغ: **{effective_price(plan_key):,} تومان**{price_note(plan_key)}\n\n"
                f"💳 کارت: `{card_num}` به نام {card_holder} ({bank_name})\n\n"
                "بعد از واریز، فیش رو بفرست:"
            )
            kb = [
                [InlineKeyboardButton("📸 ارسال فیش", callback_data=f"vip:upload:{plan_key}")],
                [InlineKeyboardButton("✍️ کد پیگیری", callback_data=f"vip:code:{plan_key}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="vip:cat:visibility")],
            ]
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
            return True
        # تغییر نام و پرچم حذف شد
        elif step == "awaiting_checkout":
            # کاربر فاکتور رو دیده و الان میخواد فیش بفرسته - اجازه بده ادامه پیدا کنه به مرحله بعد
            # این پیام متنی نیست فیش، پس نگه دار
            context.user_data["vip_input"] = {"step": "awaiting_photo", "plan_key": plan_key, "custom_payload": context.user_data.get("vip_custom_payload", {})}
            # ادامه به بخش فیش
            pass

    # 2. بررسی دریافت فیش یا کد واریز
    vip_state = context.user_data.get("vip_input")
    if not vip_state:
        return False

    # اگر مرحله checkout بود و الان عکس/کپشن اومده، custom_payload رو بردار
    custom_payload_from_state = vip_state.get("custom_payload") or context.user_data.get("vip_custom_payload") or {}

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

    # پیلود سفارشی برای گروه شبه‌نظامی و خدمات دیده شدن
    custom_payload = ""
    if custom_payload_from_state:
        try:
            custom_payload = json.dumps(custom_payload_from_state, ensure_ascii=False)
        except Exception:
            custom_payload = str(custom_payload_from_state)
    if plan_key == "militia" and "militia_wiz" in context.user_data:
        custom_payload = json.dumps(context.user_data["militia_wiz"], ensure_ascii=False)

    # ثبت در دیتابیس
    req_id = db.create_payment_request(
        player_id=user_id,
        country_id=c_id,
        item_type=plan_key,
        plan_title=plan["title"],
        amount_toman=effective_price(plan_key),
        receipt_photo_id=photo_id,
        tracking_code=tracking_code,
        custom_payload=custom_payload
    )

    # پیام تایید به کاربر
    conf_user = (
        f"✅ **فیش واریزی شما با موفقیت ثبت شد! (شماره درخواست: #{req_id})**\n\n"
        f"📌 **سفارش:** {plan['title']}\n"
        f"💵 **مبلغ:** {effective_price(plan_key):,} تومان{price_note(plan_key)}\n\n"
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
    # پاکسازی پیلود خدمات دیده شدن
    if "vip_custom_payload" in context.user_data:
        try:
            del context.user_data["vip_custom_payload"]
        except Exception:
            pass
    if "vip_pending_plan" in context.user_data:
        try:
            del context.user_data["vip_pending_plan"]
        except Exception:
            pass

    admin_text = (
        f"💳 <b>«درخواست جدید پرداخت تومانی» — شماره #{req_id}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"👤 <b>کاربر:</b> {html.escape(user.full_name or '')} (@{user.username or 'ندارد'})\n"
        f"🆔 <b>شناسه کاربری:</b> <code>{user_id}</code>\n"
        f"🌐 <b>وضعیت کشور:</b> {c_name}\n"
        f"{militia_extra}\n"
        f"📌 <b>پلن:</b> {plan['title']}\n"
        f"💵 <b>مبلغ:</b> <b>{effective_price(plan_key):,} تومان</b>{price_note(plan_key)}\n"
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
