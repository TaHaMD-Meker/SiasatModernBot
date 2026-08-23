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
from premium_emojis import pe


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

    vip_badge = f"<b>سطح رهبری:</b> ⭐ <b>اشتراک طلایی VIP</b>\n" if c.get("is_vip") else ""

    text = (
        f"{pe('globe', '🌐')} <b>شناسنامه و وضعیت جامع کشور</b>\n"
        f"<blockquote>"
        f"<b>کشور:</b> {c['flag']} {c['name']}\n"
        f"{vip_badge}"
        f"<b>رضایت عمومی:</b> {app_icon} {app_val}٪ (/approval)\n"
        f"<b>آمادگی رزمی نیروها:</b> {pe('shield', '⚔️')} {readiness_val}٪\n"
        f"</blockquote>\n"
        f"<b>اقتصاد و خزانه ملی</b>\n"
        f"• {pe('bank', '🏦')} <b>خزانه کشور:</b> {format_money(c['treasury'])}\n"
        f"• {pe('money', '📈')} <b>درآمد روزانه کل:</b> {format_money(c['daily_income'])}\n"
        f"• {pe('gold', '🪙')} <b>پشتوانه طلا:</b> {format_number(c['gold'])} شمش\n"
        f"• {pe('money', '💰')} <b>درآمد مالیاتی:</b> {format_money(c['tax_income'])}\n\n"
        f"<b>انرژی، غلات و صنایع استراتژیک</b>\n"
        f"• {pe('oil', '🛢️')} <b>ذخایر نفت:</b> {format_oil(c['oil_reserves'])} (تولید: {format_oil(c['oil_production'])}/روز)\n"
        f"• {pe('grain', '🌾')} <b>ذخایر غلات:</b> {format_number(c['grain'])} تن (+{format_number(c.get('grain_daily') or 0)} تن/روز)\n"
        f"• {pe('chip', '💻')} <b>میکروچیپ و نیمه‌هادی:</b> {format_number(c.get('microchips') or 0)} عدد (+{format_number(c.get('microchips_daily') or 0)}/روز)\n"
        f"• {pe('nuclear', '☢️')} <b>کیک زرد اورانیوم:</b> {format_number(c.get('uranium_ore') or 0)} تن\n"
        f"• {pe('atom', '🟢')} <b>سوخت هسته‌ای (۳.۵٪):</b> {format_number(c.get('nuclear_fuel') or 0)} کیلوگرم\n"
        + (f"• {pe('hospital', '🟡')} <b>ایزوتوپ پزشکی (۲۰٪):</b> {format_number(c.get('medical_isotopes') or 0)} کیلوگرم\n" if (c.get('medical_isotopes') or 0) > 0 else "")
        + (f"• {pe('rocket', '🚀')} <b>کلاهک‌های بازدارنده:</b> {format_number(c.get('warheads') or 0)} عدد\n" if (c.get('warheads') or 0) > 0 else "") +
        f"• {pe('lightning', '⚡')} <b>پوشش شبکه برق:</b> {c['electricity']}٪\n\n"
        f"<b>نیروی انسانی و توان نظامی</b>\n"
        f"• {pe('globe', '👥')} <b>جمعیت کل:</b> {format_number(c['population'])} نفر\n"
        f"• {pe('medal', '🪖')} <b>پرسنل فعال ارتش:</b> {format_number(c['active_personnel'])} نفر\n"
        f"• {pe('medal', '🎖️')} <b>نیروهای ذخیره:</b> {format_number(c['reserve_personnel'])} نفر{badges_str}"
    )

    text += missions_str

    inline_keyboard = [
        [InlineKeyboardButton("👑 خدمات و اشتراک طلایی VIP", callback_data="vip:menu")],
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
            parse_mode="HTML",
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
            parse_mode="HTML"
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
    from handlers.guide import guide_main_menu
    await guide_main_menu(update, context)