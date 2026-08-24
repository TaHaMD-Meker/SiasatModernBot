# -*- coding: utf-8 -*-
"""
ماژول کامل سیستم بیانیه‌ها، توییت‌های کشوری و رسمیت‌بخشی هوشمند متن (Statements & Tweets Module)
شامل ثبت بیانیه رسمی با پوستر/تصویر، رسمی‌سازی خودکار متن محاوره‌ای و ثبت توییت با ارسال مستقیم به کانال.
"""

import os
import datetime
import urllib.request
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

import database as db
import config
from utils import format_money, format_number, format_oil, get_main_keyboard


async def require_country(update: Update):
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        pending = db.get_pending_request_by_player(user_id)
        if pending:
            p_key = pending.get("country_key", "")
            p_info = config.COUNTRIES.get(p_key, {})
            flag = p_info.get("flag", "🏳️")
            name = p_info.get("name", p_key)
            msg = (
                f"⏳ **درخواست رهبری کشور {flag} {name} در صف بررسی ادمین است.**\n\n"
                "به محض تأیید ادمین اصلی بازی، ثبت بیانیه و تمام امکانات فعال خواهند شد."
            )
            alert_text = f"درخواست کشور {name} در انتظار تأیید ادمین است!"
        else:
            msg = "❌ **شما هنوز کشوری در بازی ندارید!**\n\nجهت شروع بازی و انتخاب کشور، دستور /start را ارسال کنید."
            alert_text = "هنوز کشوری نساختی! برای شروع /start بزن."

        if update.message:
            await update.message.reply_text(msg, parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.answer(alert_text, show_alert=True)
        return None
    return country


# ==================== منوی اصلی بیانیه‌ها و توییت‌ها ====================

async def statements_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = await require_country(update)
    if not c:
        return

    today_count = db.get_country_statement_count_today(c["id"])
    req_stmts = getattr(config, "REQUIRED_DAILY_STATEMENTS", 2)
    if today_count >= req_stmts:
        status_text = f"✅ *وضعیت فعالیت امروز:* `{today_count} از {req_stmts}` بیانیه ثبت شده (تکمیل شده)"
    else:
        status_text = f"⚠️ *وضعیت فعالیت امروز:* `{today_count} از {req_stmts}` بیانیه ثبت شده (نیاز به {req_stmts - today_count} بیانیه دیگر تا ۰۰:۰۰)"

    text = (
        f"📢 *سامانه بیانیه‌ها و تریبون رسمی کشور {c['flag']} {c['name']}*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{status_text}\n"
        f"💡 *قانون حاکمیت:* ثبت روزانه حداقل ۲ بیانیه یا توییت رسمی برای حفظ مالکیت کشور الزامی است (بررسی در ساعت ۰۰:۰۰ بامداد).\n\n"
        "لطفاً یک بخش را انتخاب کنید:\n\n"
        "• *📢 ثبت بیانیه رسمی:* ثبت بیانیه رسمی با پوستر تصویری و ارسال به کانال\n"
        "• *✍️ رسمی‌سازی متن (AI):* تبدیل متون محاوره‌ای به بیانیه‌های فاخر دیپلماتیک جهت کپی\n"
        "• *🐦 ثبت توییت:* انتشار توییت‌های کوتاه واکنش سریع در کانال بازی"
    )

    keyboard = [
        [InlineKeyboardButton("📢 ثبت بیانیه رسمی (عکس + متن)", callback_data="stmt:mode:statement")],
        [InlineKeyboardButton("✍️ رسمی‌سازی متن (دستیار AI)", callback_data="stmt:mode:rewrite")],
        [InlineKeyboardButton("🐦 ثبت توییت (آزاد / واکنش سریع)", callback_data="stmt:mode:tweet")],
    ]

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== Callback Handler بیانیه‌ها ====================

async def statements_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    country = db.get_country_by_player(user_id)

    if not country:
        await query.answer("هنوز کشوری نساختی!", show_alert=True)
        return

    await query.answer()

    if data == "stmt:menu":
        await statements_menu(update, context)

    elif data == "stmt:mode:statement":
        context.user_data["statement_input"] = {"type": "official_statement"}
        text = (
            f"📢 *ثبت بیانیه رسمی کشور {country['flag']} {country['name']}*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ *قوانین ثبت بیانیه:*\n"
            "۱. ارسال *پوستر / عکس رسمی* همراه با متن الزامی است (بدون عکس تایید نمی‌شود).\n"
            "۲. متن بیانیه باید رسمی و *حداقل دارای ۳ سطر* باشد.\n\n"
            "لطفاً *عکس بیانیه را همراه با زیرنویس (Caption)* ارسال فرمایید:"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="stmt:menu")]]), parse_mode="Markdown")

    elif data == "stmt:mode:rewrite":
        context.user_data["statement_input"] = {"type": "ai_rewrite"}
        text = (
            f"✍️ *سامانه رسمی‌سازی هوشمند متون (AI Rewriter)*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً متن ساده، محاوره‌ای یا خامی که می‌خواهید به یک بیانیه رسمی فاخر تبدیل شود را ارسال بفرمایید:\n\n"
            "*(ربات متن شما را به یک بیانیه ۳ سطری سنگین دیپلماتیک تبدیل کرده و جهت کپی در یک پیام برای شما می‌فرستد)*"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="stmt:menu")]]), parse_mode="Markdown")

    elif data == "stmt:mode:tweet":
        context.user_data["statement_input"] = {"type": "official_tweet"}
        text = (
            f"🐦 *ثبت توییت کشوری — {country['flag']} {country['name']}*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً متن توییت یا واکنش سریع کوتاه خود را جهت انتشار در کانال ارسال فرمایید:"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="stmt:menu")]]), parse_mode="Markdown")


# ==================== هاندر دریافت ورودی‌های متنی و تصویری ====================

async def process_official_statement_input(update: Update, context: ContextTypes.DEFAULT_TYPE, country: dict):
    """پردازش بیانیه رسمی (عکس + متن حداقل ۳ سطر)."""
    
    # Check photo attachment
    if not update.message.photo:
        await update.message.reply_text(
            "⚠️ *ثبت بیانیه انجام نشد:*\n\nارسال *پوستر / تصویر رسمی* الزامی است! لطفاً بیانیه خود را به‌صورت عکس همراه با متن زیرنویس (Caption) ارسال فرمایید.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(update.effective_user.id)
        )
        return

    caption = update.message.caption.strip() if update.message.caption else ""
    lines = [l.strip() for l in caption.splitlines() if l.strip()]

    if len(lines) < 3 or len(caption) < 40:
        await update.message.reply_text(
            "⚠️ *متن بیانیه کوتاه است:*\n\nمتن بیانیه رسمی باید *حداقل دارای ۳ سطر کامل* و رسمی باشد. لطفاً متن را اصلاح نموده و مجدداً با تصویر ارسال بفرمایید.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(update.effective_user.id)
        )
        return

    photo_file_id = update.message.photo[-1].file_id
    user_name_str = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name

    # ارسال مستقیم متن بیانیه بازیکن بدون قالب اضافی + حفظ فرمت‌بندی خود بازیکن
    # (بولد، ایتالیک، نقل‌قول، اسپویلر، خط خوردن و... از entity های پیام اصلی بازیکن)
    try:
        channel_card_md = update.message.caption_html or caption
    except Exception:
        channel_card_md = caption
    channel_card_plain = caption

    # Multi-tier resilient post to Channel
    posted_to_channel = False
    channel_err_str = ""
    channel_id = config.get_channel_id()

    if channel_id:
        try:
            await context.bot.send_photo(
                chat_id=channel_id,
                photo=photo_file_id,
                caption=channel_card_md,
                parse_mode="HTML"
            )
            posted_to_channel = True
        except Exception as e1:
            print(f"Channel statement send_photo Markdown error: {e1}")
            try:
                await context.bot.send_photo(
                    chat_id=channel_id,
                    photo=photo_file_id,
                    caption=channel_card_plain
                )
                posted_to_channel = True
            except Exception as e2:
                print(f"Channel statement send_photo Plain error: {e2}")
                channel_err_str = str(e2)

    # Confirm to player
    conf_msg = f"✅ *بیانیه رسمی کشور {country['flag']} {country['name']} با موفقیت ثبت شد!*\n\n"
    if posted_to_channel:
        conf_msg += "📢 این بیانیه مستقیماً در کانال رسمی بازی منتشر گردید."
    else:
        conf_msg += (
            "📋 **بیانیه در سیستم ثبت گردید.**\n\n"
            "⚠️ *توجه:* انتشار مستقیم در کانال تلگرام انجام نشد! "
            "لطفاً مطمئن شوید ربات در کانال تلگرام عضو و دارای دسترسی ادمین است."
        )
        try:
            for admin_id in config.ADMIN_IDS:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"⚠️ **خطای عدم انتشار بیانیه در کانال تلگرام:**\n\n"
                        f"• **کشور:** {country['flag']} {country['name']}\n"
                        f"• **شناسه کانال:** `{channel_id}`\n"
                        f"• **جزئیات خطا:** `{channel_err_str or 'عدم دسترسی مدیریت ربات در کانال'}`\n\n"
                        "💡 لطفاً ربات را به‌عنوان ادمین با دسترسی ارسال پیام در کانال اضافه فرمایید."
                    ),
                    parse_mode="Markdown"
                )
        except Exception as adm_e:
            print(f"Failed to notify admin of statement channel error: {adm_e}")

    db.record_country_statement(country["id"], update.effective_user.id, "statement", caption)
    today_cnt = db.get_country_statement_count_today(country["id"])
    req_stmts = getattr(config, "REQUIRED_DAILY_STATEMENTS", 2)
    conf_msg += f"\n\n📊 *مجموع بیانیه‌ها و توییت‌های امروز شما:* `{today_cnt} از {req_stmts}`"
    if today_cnt >= req_stmts:
        conf_msg += " (✅ سهمیه فعالیت امروز تکمیل شد)"
    else:
        conf_msg += f" (⚠️ نیاز به {req_stmts - today_cnt} بیانیه دیگر تا ساعت ۰۰:۰۰)"

    try:
        _mok, _mrw = db.complete_daily_mission(country["id"], "statement")
        if _mok:
            await update.message.reply_text(f"🎯 *مأموریت روزانه کامل شد!* +{format_money(_mrw)} به خزانه.", parse_mode="Markdown")
        db.add_battle_pass_xp(country["id"], 150)
        db.progress_battle_pass_challenge(country["id"], "statement", 1)
    except Exception:
        pass

    await update.message.reply_text(conf_msg, parse_mode="Markdown", reply_markup=get_main_keyboard(update.effective_user.id))




# ---------- موتور بیانیه‌ساز دیپلماتیک نسخه ۲ (بدون تکرار) ----------

import random

_INFORMAL_MAP = {
    "می‌خوایم": "می‌خواهیم", "می‌خوام": "می‌خواهم", "می‌خوید": "می‌خواهید",
    "می‌خواد": "می‌خواهد", "بخواد": "بخواهد", "می‌خویم": "می‌خواهیم",
    "بذار": "بگذار", "بذارید": "بگذارید", "بذارن": "بگذارند", "اینطوری": "بدین‌گونه",
    "اونها": "آن‌ها", "اونا": "آنان", "حتماً": "قطعاً",
    "میشه": "می‌شود", "می‌شه": "می‌شود", "کنن": "کنند", "هستن": "هستند",
    "بزنن": "بزنند", "بگیرن": "بگیرند", "بدن": "دهند",
}

def _formalize(text: str) -> str:
    for k, v in _INFORMAL_MAP.items():
        text = text.replace(k, v)
    return text.strip()

_STMT_OPENERS = [
    "دفتر مطبوعاتی و مرکز ارتباطات دولت {c} بیانیه ذیل را به اطلاع افکار عمومی جهان می‌رساند:",
    "وزارت امور خارجه {c} بدین‌وسیله مواضع رسمی و مصوب شورای عالی امنیت ملی را اعلام می‌دارد:",
    "سخنگوی رسمی دولت {c} در پی ارزیابی‌های کارشناسی و نشست فوری شورای امنیت، ابلاغیه ذیل را صادر نمود:",
    "حکومت {c} در بیانیه‌ای رسمی، ضمن تجدید تأکید بر اصول منشور ملل متحد، مواضع خود را چنین اعلام کرد:",
    "مرکز راهبری دیپلماسی {c} با صدور اطلاعیه‌ای فوری، نکات ذیل را مورد توجه جامعه جهانی قرار داد:",
    "قصر ریاست‌جمهوری {c} در پیگیری حقوق مشروع ملت خود، مواضع قطعی دولت را بدین شرح اعلام نمود:",
    "شورای هماهنگی راهبردی {c} پس از بررسی همه‌جانبهرفتارهای اخیر، متن ذیل را سند رسمی مواضع کشور قرار داد:",
]

_STMT_BODY_FRAMES = [
    "محور اصلی این اعلامیه {t} است؛ موضوعی که از این پس در رأس دستور کار دیپلماتیک و اجرایی دولت قرار می‌گیرد.",
    "بر پایه مصوبات جدید کابینه، رسماً اعلام می‌گردد: «{t}»",
    "متن کامل موضع رسمی دولت بدین شرح ابلاغ می‌شود: «{t}»",
    "در پی رصد دقیق تحولات جاری، {c} رسماً موضوع {t} را در چارچوب منافع راهبردی خود محور قرار داده است.",
    "بر اساس ارزیابی مشترک ستاد مشترک و وزارت خارجه، محور {t} با حساسیت تمام پیگیری و ابلاغ گردید.",
    "دولت {c} رسماً حاکمیت و عزم خود را در خصوص {t} به تمامی طرف‌های ذی‌ربط اعلام می‌دارد.",
]

_STMT_ELABS = [
    "هرگونه اقدام مغایر با منافع ملت {c}، پاسخ متناسب و قاطع خواهد داشت و مسئولیت پیامدهای آن بر عهده طرف مقابل است.",
    "{c} بر تعهد خود به منشور ملل متحد، حسن همجواری و حل مسالمت‌آمیز اختلافات پاینده است و از هیچ تلاش دیپلماتیک مشارکتی دریغ نخواهد ورزید.",
    "حفظ ثبات، امنیت و آرامش منطقه، خط قرمز و اصل ثابت سیاست خارجی {c} است.",
    "دولت {c} آمادگی کامل خود را برای گفت‌وگو در چارچوب عزت و منافع ملی اعلام می‌دارد.",
    "نیروهای مسلح {c} در بالاترین سطح آمادگی دفاعی، پشتیبان تمام‌عیار این موضع رسمی هستند.",
    "این مواضع با نظر کامل نهادهای راهبردی و رأی شورای عالی امنیت {c} تدوین و ابلاغ گردیده است.",
    "پنجره دیپلماسی همچنان گشوده است؛ هرچند مشروط به حسن‌نیت و اقدام عملی طرف‌های مقابل خواهد بود.",
    "ملت {c} در پشتیبانی از این موضع، یکپارچه و هم‌صدا ایستاده‌اند و هیچ اختلافی در ارکان دولت مشاهده نمی‌شود.",
]

_STMT_CLOSERS = [
    "این بیانیه رسماً به دبیرخانه سازمان ملل متحد، سفارت‌های ذی‌ربط و نهادهای بین‌المللی ابلاغ گردید.",
    "نسخه کامل این سند در بایگانی دیپلماتیک {c} ثبت شده و مبنای رسمی مذاکرات آینده خواهد بود.",
    "تا اطلاع ثانوی، این متن تنها مرجع رسمی اعلام مواضع {c} در این موضوع به شمار می‌رود.",
    "جهان باید بداند که ملت {c} در دفاع از این موضع، یکپارچه و مصمم است.",
    "روابط عمومی {c} جزئیات تکمیلی را در نشست خبری پیش‌رو اعلام خواهد کرد.",
    "پیروندهای این موضع به‌طور مستمر از سوی دستگاه دیپلماسی {c} رصد و گزارش می‌شود.",
]

_RECENT_STMT_SIGS = []

def generate_diplomatic_statement(country_name: str, raw_text: str) -> str:
    """ساخت بیانیه رسمی متنوع از متن خام؛ ترکیب تصادفی گشایش/بدنه/توضیح/اختتام بدون تکرار اخیر."""
    formal = _formalize(raw_text)

    def fill(t: str) -> str:
        return t.replace("{c}", country_name).replace("{t}", formal)

    for _ in range(4):
        o = random.choice(_STMT_OPENERS)
        b = random.choice(_STMT_BODY_FRAMES)
        e1 = random.choice(_STMT_ELABS)
        e2 = random.choice(_STMT_ELABS)
        cl = random.choice(_STMT_CLOSERS)
        if e1 != e2 and (o, b, e1, cl) not in _RECENT_STMT_SIGS:
            break

    _RECENT_STMT_SIGS.append((o, b, e1, cl))
    if len(_RECENT_STMT_SIGS) > 40:
        _RECENT_STMT_SIGS.pop(0)

    lines = [fill(o), fill(b), fill(e1)]
    if e2 != e1 and random.random() < 0.45:
        lines.append(fill(e2))
    lines.append(fill(cl))
    return "\n".join(lines)


async def process_ai_rewrite_input(update: Update, context: ContextTypes.DEFAULT_TYPE, country: dict):
    """رسمی‌سازی هوشمند متن محاوره‌ای به بیانیه ۳ سطری دیپلماتیک."""
    
    raw_text = update.message.text.strip()
    polished_text = generate_diplomatic_statement(country['name'], raw_text)


    # Output ONLY polished text in 1 message for easy copying
    if "`" not in polished_text:
        await update.message.reply_text(
            f"`{polished_text}`",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(update.effective_user.id)
        )
    else:
        await update.message.reply_text(
            polished_text,
            reply_markup=get_main_keyboard(update.effective_user.id)
        )


async def process_official_tweet_input(update: Update, context: ContextTypes.DEFAULT_TYPE, country: dict):
    """ثبت و انتشار توییت سریع کشوری."""
    
    tweet_text = update.message.text.strip()
    user_name_str = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name

    # قالب استاندارد توییت + حفظ فرمت‌بندی خود بازیکن (بولد/نقل‌قول/اسپویلر و...)
    user_handle = f"@{update.effective_user.username}" if update.effective_user.username else (update.effective_user.first_name or "حساب رسمی")
    try:
        body_html = update.message.text_html or tweet_text
    except Exception:
        body_html = tweet_text

    tweet_card_md = (
        "🐦 <b>«توییت رسمی کشوری»</b>\n"
        f"🪐 کشور: {country['flag']} {country['name']}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{body_html}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🔹 {user_handle} | حساب رسمی"
    )
    tweet_card_plain = (
        "🐦 «توییت رسمی کشوری»\n"
        f"🪐 کشور: {country['flag']} {country['name']}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{tweet_text}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"🔹 {user_handle} | حساب رسمی"
    )

    # Multi-tier resilient post to Channel
    posted_to_channel = False
    channel_err_str = ""
    channel_id = config.get_channel_id()

    if channel_id:
        try:
            await context.bot.send_message(
                chat_id=channel_id,
                text=tweet_card_md,
                parse_mode="HTML"
            )
            posted_to_channel = True
        except Exception as e1:
            print(f"Channel tweet Markdown error: {e1}")
            try:
                await context.bot.send_message(
                    chat_id=channel_id,
                    text=tweet_card_plain
                )
                posted_to_channel = True
            except Exception as e2:
                print(f"Channel tweet Plain error: {e2}")
                channel_err_str = str(e2)

    conf_msg = f"✅ *توییت رسمی کشور {country['flag']} {country['name']} منتشر گردید!*\n\n"
    if posted_to_channel:
        conf_msg += "📢 توییت شما مستقیماً در کانال رسمی بازی منتشر گردید."
    else:
        conf_msg += (
            "📋 **توییت در سیستم ثبت گردید.**\n\n"
            "⚠️ *توجه:* انتشار مستقیم در کانال تلگرام انجام نشد! "
            "لطفاً مطمئن شوید ربات در کانال تلگرام عضو و دارای دسترسی ادمین است."
        )
        try:
            for admin_id in config.ADMIN_IDS:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"⚠️ **خطای عدم انتشار توییت در کانال تلگرام:**\n\n"
                        f"• **کشور:** {country['flag']} {country['name']}\n"
                        f"• **شناسه کانال:** `{channel_id}`\n"
                        f"• **جزئیات خطا:** `{channel_err_str or 'عدم دسترسی مدیریت ربات در کانال'}`\n\n"
                        "💡 لطفاً ربات را به‌عنوان ادمین با دسترسی ارسال پیام در کانال اضافه فرمایید."
                    ),
                    parse_mode="Markdown"
                )
        except Exception as adm_e:
            print(f"Failed to notify admin of tweet channel error: {adm_e}")

    db.record_country_statement(country["id"], update.effective_user.id, "tweet", tweet_text)
    today_cnt = db.get_country_statement_count_today(country["id"])
    req_stmts = getattr(config, "REQUIRED_DAILY_STATEMENTS", 2)
    conf_msg += f"\n\n📊 *مجموع بیانیه‌ها و توییت‌های امروز شما:* `{today_cnt} از {req_stmts}`"
    if today_cnt >= req_stmts:
        conf_msg += " (✅ سهمیه فعالیت امروز تکمیل شد)"
    else:
        conf_msg += f" (⚠️ نیاز به {req_stmts - today_cnt} بیانیه دیگر تا ساعت ۰۰:۰۰)"

    try:
        _mok, _mrw = db.complete_daily_mission(country["id"], "statement")
        if _mok:
            await update.message.reply_text(f"🎯 *مأموریت روزانه کامل شد!* +{format_money(_mrw)} به خزانه.", parse_mode="Markdown")
        db.add_battle_pass_xp(country["id"], 150)
        db.progress_battle_pass_challenge(country["id"], "statement", 1)
    except Exception:
        pass

    await update.message.reply_text(conf_msg, parse_mode="Markdown", reply_markup=get_main_keyboard(update.effective_user.id))


# ==================== Router ورودی‌های متنی بیانیه‌ها ====================

async def statements_text_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        return

    stmt_input = context.user_data.get("statement_input")
    if not stmt_input:
        return

    input_type = stmt_input.get("type")
    del context.user_data["statement_input"]

    if input_type == "official_statement":
        await process_official_statement_input(update, context, country)
    elif input_type == "ai_rewrite":
        await process_ai_rewrite_input(update, context, country)
    elif input_type == "official_tweet":
        await process_official_tweet_input(update, context, country)