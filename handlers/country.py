# -*- coding: utf-8 -*-
"""
دستورات نمایش وضعیت کشور: /country /treasury /oil /army /help
پشتیبانی از دکمه‌های پایین صفحه (ReplyKeyboard)
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database as db
import config
import approval_system
from utils import format_money, format_number, format_oil, get_main_keyboard


async def require_country(update: Update):
    """اگر بازیکن کشور نداشت پیام مناسب می‌دهد و None برمی‌گرداند."""
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        if update.message:
            await update.message.reply_text("هنوز کشوری نساختی! برای شروع /start رو بزن.", parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.answer("هنوز کشوری نساختی!", show_alert=True)
        return None
    return country


async def country_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = await require_country(update)
    if not c:
        return

    app_val = c.get('approval_rating', 80)
    app_icon = "🟢" if app_val >= 75 else ("🟡" if app_val >= 50 else ("🟠" if app_val >= 40 else "🔴"))
    readiness_val = c.get('combat_readiness', 70)

    badges = approval_system.get_country_badges(c)
    badges_str = ("\n\n🏆 **نشان‌های افتخار و دستاوردهای ملی:**\n" + "\n".join(badges)) if badges else ""

    ms = db.get_today_missions(c["id"])
    ms_parts = []
    for mk, (mlabel, mreward) in config.DAILY_MISSIONS.items():
        mark = "✅" if ms.get(mk) else "⬜"
        ms_parts.append(f"{mark} {mlabel} (+{format_money(mreward)})")
    missions_str = ("\n\n🎯 **مأموریت‌های روزانه:**\n" + "\n".join(ms_parts)) if ms_parts else ""

    text = (
        f"**شناسنامه و وضعیت جامع کشور**\n"
        f"> **کشور:** {c['flag']} {c['name']}\n"
        f"> **رضایت عمومی:** {app_icon} {app_val}٪ (/approval)\n"
        f"> **آمادگی رزمی نیروها:** ⚔️ {readiness_val}٪\n\n"
        f"**اقتصاد و خزانه ملی**\n"
        f"• **خزانه کشور:** {format_money(c['treasury'])}\n"
        f"• **درآمد روزانه کل:** {format_money(c['daily_income'])}\n"
        f"• **درآمد مالیاتی:** {format_money(c['tax_income'])}\n"
        f"• **پشتوانه طلا:** {format_number(c['gold'])} شمش\n\n"
        f"**انرژی، غلات و صنایع استراتژیک**\n"
        f"• **ذخایر نفت:** {format_oil(c['oil_reserves'])} (تولید: {format_oil(c['oil_production'])}/روز)\n"
        f"• **ذخایر غلات:** {format_number(c['grain'])} تن (تولید: +{format_number(c.get('grain_daily') or 0)} تن/روز)\n"
        f"• **میکروچیپ و نیمه‌هادی:** {format_number(c.get('microchips') or 0)} عدد (+{format_number(c.get('microchips_daily') or 0)}/روز)\n"
        f"• **کیک زرد اورانیوم:** {format_number(c.get('uranium_ore') or 0)} تن\n"
        f"• **سوخت هسته‌ای (۳.۵٪):** {format_number(c.get('nuclear_fuel') or 0)} کیلوگرم\n"
        + (f"• **ایزوتوپ پزشکی (۲۰٪):** {format_number(c.get('medical_isotopes') or 0)} کیلوگرم\n" if (c.get('medical_isotopes') or 0) > 0 else "")
        + (f"• **کلاهک‌های بازدارنده:** {format_number(c.get('warheads') or 0)} عدد\n" if (c.get('warheads') or 0) > 0 else "") +
        f"• **پوشش شبکه برق:** {c['electricity']}٪\n\n"
        f"**نیروی انسانی و توان نظامی**\n"
        f"• **جمعیت کل:** {format_number(c['population'])} نفر\n"
        f"• **پرسنل فعال ارتش:** {format_number(c['active_personnel'])} نفر\n"
        f"• **نیروهای ذخیره:** {format_number(c['reserve_personnel'])} نفر{badges_str}"
    )

    text += missions_str

    inline_keyboard = [
        [InlineKeyboardButton("📊 مشاهده کامل وضعیت رضایت عمومی", callback_data="country:approval_details")],
        [
            InlineKeyboardButton("🔬 مرکز تحقیق و توسعه (R&D)", callback_data="research:menu"),
            InlineKeyboardButton("☢️ برنامه هسته‌ای", callback_data="nuc:menu"),
        ],
        [
            InlineKeyboardButton("🏪 بورس کالا", callback_data="market:menu"),
            InlineKeyboardButton("🎖️ دارایی‌ها", callback_data="assets_back"),
            InlineKeyboardButton("🤝 دیپلماسی", callback_data="dip:menu"),
        ]
    ]

    if update.message:
        await update.message.reply_text(
            text,
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(update.effective_user.id)
        )
        await update.message.reply_text(
            "👇 جهت مشاهده تحلیل دقیق منابع و تحلیل رضایت عمومی کلیک کنید:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard)
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard),
            parse_mode="Markdown"
        )


async def country_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == "country:approval_details":
        c = await require_country(update)
        if not c:
            return
        msg = approval_system.get_approval_status_message(c)
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به وضعیت کشور", callback_data="country:back_profile")]]
        await query.edit_message_text(msg, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "country:back_profile":
        await country_profile(update, context)


async def approval_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = await require_country(update)
    if not c:
        return

    msg = approval_system.get_approval_status_message(c)
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=get_main_keyboard(update.effective_user.id))


async def treasury(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = await require_country(update)
    if not c:
        return
    await update.message.reply_text(
        f"🏦 خزانه {c['name']}: {format_money(c['treasury'])}\n"
        f"🪙 طلا: {format_number(c['gold'])}",
        reply_markup=get_main_keyboard(update.effective_user.id)
    )


async def oil(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = await require_country(update)
    if not c:
        return
    await update.message.reply_text(
        f"🛢️ ذخیره نفت {c['name']}: {format_oil(c['oil_reserves'])}\n"
        f"🛢️ تولید روزانه: {format_oil(c['oil_production'])}",
        reply_markup=get_main_keyboard(update.effective_user.id)
    )


from handlers.assets import show_assets_menu

async def army(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هدایت دستور وضعیت ارتش به کاتالوگ دارایی‌های نظامی (/assets)."""
    await show_assets_menu(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    is_adm = user_id in config.ADMIN_IDS

    text = (
        "📜 راهنمای بازی «سیاست مدرن»\n\n"
        "شما می‌توانید از دکمه‌های ثابت پایین صفحه یا دستورات زیر استفاده کنید:\n\n"
        "🌐 *وضعیت کشور* (`/country`)\n"
        "🎯 *ستاد توسعه و اقدامات راهبردی* (`/movements` یا `/nuclear`)\n"
        "🎯 *عملیات‌های نظامی* (`/role`)\n"
        "🏦 *خزانه و طلا* (`/treasury`)\n"
        "🛢️ *وضعیت نفت* (`/oil`)\n"
        "🎖️ *دارایی‌های نظامی* (`/assets`)\n"
        "🏪 *فروشگاه* (`/shop`)\n"
        "📜 *راهنما* (`/help`)"
    )

    if is_adm:
        text += "\n\n👑 *پنل مدیریت:* فقط برای ادمین اصلی بازی فعال است."

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))