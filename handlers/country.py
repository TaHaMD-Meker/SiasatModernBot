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
        pending = db.get_pending_request_by_player(user_id)
        if pending:
            p_key = pending.get("country_key", "")
            p_info = config.COUNTRIES.get(p_key, {})
            flag = p_info.get("flag", "🏳️")
            name = p_info.get("name", p_key)
            msg = (
                f"⏳ **درخواست رهبری کشور {flag} {name} در صف بررسی ادمین است.**\n\n"
                "به محض تأیید ادمین اصلی بازی، دسترسی کامل شما به مدیریت کشور و تمام دکمه‌ها فعال خواهد شد."
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

    vip_tier = c.get("vip_tier") or ""
    tier_badges = {
        "diamond": "💎 <b>اشتراک الماس (Diamond Supreme)</b>",
        "gold": "🥇 <b>اشتراک طلایی (Gold Leader)</b>",
        "silver": "🥈 <b>اشتراک نقره‌ای (Silver Leader)</b>",
        "bronze": "🥉 <b>اشتراک برنزی (Bronze Leader)</b>"
    }
    vip_badge = f"<b>سطح رهبری:</b> {tier_badges.get(vip_tier, '⭐ <b>اشتراک طلایی VIP</b>')}\n" if c.get("is_vip") else ""

    maint_info = db.calculate_country_maintenance_cost(c["id"])
    tax_val = c.get("tax_income", 0) or 0
    daily_val = c.get("daily_income", 0) or 0
    gross_val = daily_val + tax_val
    total_maint = maint_info.get("total_maint", 0) or 0
    net_val = gross_val - total_maint
    net_quarter = int(net_val / 4)
    net_sign = "+" if net_val >= 0 else ""
    net_color = "🟢" if net_val >= 0 else "🔴"

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
        f"• {pe('money', '📈')} <b>درآمد ناخالص روزانه:</b> {format_money(gross_val)} (پایه: {format_money(daily_val)} | مالیات: {format_money(tax_val)})\n"
        f"• {pe('shield', '🪖')} <b>هزینه نگهداری ارتش:</b> -{format_money(total_maint)}/روز\n"
        f"• {net_color} <b>درآمد خالص روزانه:</b> {net_sign}{format_money(net_val)}/روز (واریز هر ۶ ساعت: {net_sign}{format_money(net_quarter)})\n"
        f"• {pe('gold', '🪙')} <b>پشتوانه طلا:</b> {format_number(c['gold'])} شمش\n\n"
        f"<b>انرژی، غلات و صنایع استراتژیک</b>\n"
        f"• {pe('oil', '🛢️')} <b>ذخایر نفت:</b> {format_oil(c['oil_reserves'])} (تولید: {format_oil(c['oil_production'])}/روز)\n"
        f"• {pe('grain', '🌾')} <b>ذخایر غلات:</b> {format_number(c['grain'])} تن (+{format_number(c.get('grain_daily') or 0)} تن/روز)\n"
        f"• ⛏️ <b>سنگ آهن و فولاد:</b> {format_number(c.get('iron_ore') or 0)} تن (+{format_number(c.get('iron_ore_daily') or 0)} تن/روز)\n"
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
        [
            InlineKeyboardButton("⭐️ بتل‌پس فصلی (/pass)", callback_data="bp:menu"),
            InlineKeyboardButton("👑 خدمات VIP", callback_data="vip:menu")
        ],
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

    entities = db.get_player_all_entities(c["player_id"])
    if len(entities) >= 2:
        other_e = next((e for e in entities if e["id"] != c["id"]), None)
        if other_e:
            inline_keyboard.insert(0, [InlineKeyboardButton(f"🔄 سوییچ فرماندهی به {other_e['flag']} {other_e['name']}", callback_data="country:switch_active_entity")])
    elif not (c.get("country_key") or "").startswith("faction_"):
        inline_keyboard.insert(0, [InlineKeyboardButton("🏴‍☠️ تاسیس بازوی نیابتی / ارتش خصوصی (۱۰۰k ت)", callback_data="vip:militia_wizard_start")])

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

    elif data == "country:switch_active_entity":
        user_id = update.effective_user.id
        ok, msg, target = db.switch_player_active_entity(user_id)
        if ok:
            await query.answer(f"✅ {msg}", show_alert=True)
            await country_profile(update, context)
        else:
            await query.answer(msg, show_alert=True)


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
from handlers.guide import guide_main_menu

async def army(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """هدایت دستور وضعیت ارتش به کاتالوگ دارایی‌های نظامی (/assets)."""
    await show_assets_menu(update, context)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await guide_main_menu(update, context)