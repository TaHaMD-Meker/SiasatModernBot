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
from utils import get_main_keyboard


async def require_country(update: Update):
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        if update.message:
            await update.message.reply_text("هنوز کشوری نساختی! برای شروع /start رو بزن.")
        elif update.callback_query:
            await update.callback_query.answer("هنوز کشوری نساختی!", show_alert=True)
        return None
    return country


# ==================== منوی اصلی بیانیه‌ها و توییت‌ها ====================

async def statements_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = await require_country(update)
    if not c:
        return

    text = (
        f"📢 **سامانه بیانیه‌ها و تریبون رسمی کشور {c['flag']} {c['name']}**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "لطفاً یک بخش را انتخاب کنید:\n\n"
        "• **📢 ثبت بیانیه رسمی:** ثبت بیانیه رسمی با پوستر تصویری و ارسال به کانال\n"
        "• **✍️ رسمی‌سازی متن (AI):** تبدیل متون محاوره‌ای به بیانیه‌های فاخر دیپلماتیک جهت کپی\n"
        "• **🐦 ثبت توییت:** انتشار توییت‌های کوتاه واکنش سریع در کانال بازی"
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
            f"📢 **ثبت بیانیه رسمی کشور {country['flag']} {country['name']}**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "⚠️ **قوانین ثبت بیانیه:**\n"
            "۱. ارسال **پوستر / عکس رسمی** همراه با متن الزامی است (بدون عکس تایید نمی‌شود).\n"
            "۲. متن بیانیه باید رسمی و **حداقل دارای ۳ سطر** باشد.\n\n"
            "لطفاً **عکس بیانیه را همراه با زیرنویس (Caption)** ارسال فرمایید:"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="stmt:menu")]]), parse_mode="Markdown")

    elif data == "stmt:mode:rewrite":
        context.user_data["statement_input"] = {"type": "ai_rewrite"}
        text = (
            f"✍️ **سامانه رسمی‌سازی هوشمند متون (AI Rewriter)**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً متن ساده، محاوره‌ای یا خامی که می‌خواهید به یک بیانیه رسمی فاخر تبدیل شود را ارسال بفرمایید:\n\n"
            "*(ربات متن شما را به یک بیانیه ۳ سطری سنگین دیپلماتیک تبدیل کرده و جهت کپی در یک پیام برای شما می‌فرستد)*"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="stmt:menu")]]), parse_mode="Markdown")

    elif data == "stmt:mode:tweet":
        context.user_data["statement_input"] = {"type": "official_tweet"}
        text = (
            f"🐦 **ثبت توییت کشوری — {country['flag']} {country['name']}**\n"
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
            "⚠️ **ثبت بیانیه انجام نشد:**\n\nارسال **پوستر / تصویر رسمی** الزامی است! لطفاً بیانیه خود را به‌صورت عکس همراه با متن زیرنویس (Caption) ارسال فرمایید.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(update.effective_user.id)
        )
        return

    caption = update.message.caption.strip() if update.message.caption else ""
    lines = [l.strip() for l in caption.splitlines() if l.strip()]

    if len(lines) < 3 or len(caption) < 40:
        await update.message.reply_text(
            "⚠️ **متن بیانیه کوتاه است:**\n\nمتن بیانیه رسمی باید **حداقل دارای ۳ سطر کامل** و رسمی باشد. لطفاً متن را اصلاح نموده و مجدداً با تصویر ارسال بفرمایید.",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(update.effective_user.id)
        )
        return

    photo_file_id = update.message.photo[-1].file_id
    user_name_str = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name

    # Build exact channel statement card matching requested layout
    channel_card = (
        "📑 «سازمان جهانی بیانیه»\n"
        f"🪐 کشور: {country['flag']} {country['name']}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f'> "{caption}"\n\n'
        "━━━━━━━━━━━━━━━━━━\n"
        f"📌 صادرکننده: {user_name_str} | تاریخ: {datetime.date.today().isoformat()}"
    )

    # Post to Channel
    posted_to_channel = False
    try:
        await context.bot.send_photo(
            chat_id=config.CHANNEL_ID,
            photo=photo_file_id,
            caption=channel_card,
            parse_mode="Markdown"
        )
        posted_to_channel = True
    except Exception as e:
        print(f"Channel post error: {e}")

    # Confirm to player
    conf_msg = f"✅ **بیانیه رسمی کشور {country['flag']} {country['name']} با موفقیت ثبت شد!**\n\n"
    if posted_to_channel:
        conf_msg += "📢 این بیانیه مستقیماً در کانال رسمی بازی منتشر گردید."
    else:
        conf_msg += "📋 بیانیه شما در سیستم ثبت گردید."

    await update.message.reply_text(conf_msg, parse_mode="Markdown", reply_markup=get_main_keyboard(update.effective_user.id))


async def process_ai_rewrite_input(update: Update, context: ContextTypes.DEFAULT_TYPE, country: dict):
    """رسمی‌سازی هوشمند متن محاوره‌ای به بیانیه ۳ سطری دیپلماتیک."""
    
    raw_text = update.message.text.strip()
    await update.message.reply_text("✍️ **در حال رسمی‌سازی متن و نگارش بیانیه فاخر دیپلماتیک...**\nلطفاً شکیبا باشید...")

    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("AI_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    polished_text = None

    if api_key:
        try:
            prompt = f"""شما یک دیپلمات ارشد بین‌المللی و سخنگوی دولت {country['name']} هستید.
متن خام/محاوره‌ای زیر را به یک بیانیه رسمی، فاخر، سنگین و کارشناسی (حداقل در ۳ سطر) تبدیل کن.

متن خام:
"{raw_text}"

نکته مهم: فقط و فقط متن رسمی بازنویسی‌شده را بازگردان بدون هیچ توضیحات اضافی یا کلمات مقدماتی.
"""
            url = "https://api.openai.com/v1/chat/completions"
            data = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "system", "content": "You are a senior diplomatic speechwriter."}, {"role": "user", "content": prompt}],
                "temperature": 0.7
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=10) as response:
                res = json.loads(response.read().decode("utf-8"))
                polished_text = res["choices"][0]["message"]["content"].strip()
        except Exception as e:
            print(f"AI Rewriter error: {e}")

    if not polished_text:
        # Fallback Algorithmic Diplomatic Speechwriter
        polished_text = (
            f"دولت و وزارت امور خارجه کشور {country['name']} بدین‌وسیله مواضع رسمی خود را در قبال تحرکات اخیر اعلام می‌دارد.\n"
            f"بر اساس تصمیمات عالی شورای امنیت ملی، {raw_text} به‌صورت ویژه در دستور کار دیپلماتیک و اجرایی قرار گرفته است.\n"
            "اراده صریح کشور بر حفظ اقتدار ملی، ثبات منطقه‌ای و پاسخ قاطع به هرگونه تحرک ناهمگون استوار خواهد بود."
        )

    # Output ONLY polished text in 1 message for easy copying
    await update.message.reply_text(
        f"`{polished_text}`",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(update.effective_user.id)
    )


async def process_official_tweet_input(update: Update, context: ContextTypes.DEFAULT_TYPE, country: dict):
    """ثبت و انتشار توییت سریع کشوری."""
    
    tweet_text = update.message.text.strip()
    user_name_str = f"@{update.effective_user.username}" if update.effective_user.username else update.effective_user.first_name

    # Build Tweet Card
    tweet_card = (
        "🐦 «توییت رسمی کشوری»\n"
        f"🪐 کشور: {country['flag']} {country['name']}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f'> "{tweet_text}"\n\n'
        "━━━━━━━━━━━━━━━━━━\n"
        f"📌 صادرکننده: {user_name_str} | تاریخ: {datetime.date.today().isoformat()}"
    )

    # Post to Channel
    posted_to_channel = False
    try:
        await context.bot.send_message(
            chat_id=config.CHANNEL_ID,
            text=tweet_card,
            parse_mode="Markdown"
        )
        posted_to_channel = True
    except Exception as e:
        print(f"Channel tweet error: {e}")

    conf_msg = f"✅ **توییت رسمی کشور {country['flag']} {country['name']} منتشر گردید!**\n\n"
    if posted_to_channel:
        conf_msg += "📢 توییت شما در کانال رسمی بازی قرار گرفت."
    else:
        conf_msg += "📋 توییت در سیستم ثبت گردید."

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
