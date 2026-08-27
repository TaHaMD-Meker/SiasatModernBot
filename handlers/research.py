# -*- coding: utf-8 -*-
"""
ماژول سیستم تحقیق و توسعه و لول فناوری بومی (R&D & Tech Level System)
ارتقای سطح فناوری کشور، کاهش درصد هزینه نگهداری روزانه تسلیحات و افزایش کارایی اقتصادی.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

import database as db
import config
from utils import format_money, format_number, get_main_keyboard

TECH_UPGRADES = {
    1: {"cost_money": 15_000_000, "cost_gold": 50, "cost_chips": 50, "discount": 10, "label": "سطح ۲ (فناوری پیشرفته ۱)"},
    2: {"cost_money": 35_000_000, "cost_gold": 100, "cost_chips": 200, "discount": 20, "label": "سطح ۳ (فناوری پیشرفته ۲)"},
    3: {"cost_money": 75_000_000, "cost_gold": 200, "cost_chips": 500, "discount": 30, "label": "سطح ۴ (فناوری راهبردی)"},
    4: {"cost_money": 150_000_000, "cost_gold": 400, "cost_chips": 1000, "discount": 40, "label": "سطح ۵ (فناوری فوق‌پیشرفته بومی)"},
}

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
            msg = f"⏳ **درخواست رهبری کشور {flag} {name} در صف بررسی ادمین است.**\n\nپس از تایید ادمین، مرکز تحقیق و توسعه فعال می‌شود."
            alert_text = f"درخواست کشور {name} در انتظار تأیید ادمین است!"
        else:
            msg = "❌ شما هنوز کشوری در بازی ندارید! برای شروع /start را بزنید."
            alert_text = "هنوز کشوری نساختی! برای شروع /start بزن."

        if update.message:
            await update.message.reply_text(msg, parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.answer(alert_text, show_alert=True)
        return None
    return country


async def research_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = await require_country(update)
    if not c:
        return

    tech_lvl = c.get("tech_level", 1)
    disc_pct = min(40, (tech_lvl - 1) * 10)

    maint_info = db.calculate_country_maintenance_cost(c["id"])

    text = (
        f"🔬 *مرکز تحقیق، توسعه و فناوری کشور {c['flag']} {c['name']}*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"• *سطح فناوری فعلی:* *سطح {tech_lvl}*\n"
        f"• *تخفیف در هزینه نگهداری تسلیحات:* *{disc_pct}٪*\n"
        f"• *هزینه نگهداری فعلی تجهیزات:* {format_money(maint_info['assets_maint'])}/روز\n"
        f"• *هزینه نگهداری پرسنل ارتش:* {format_money(maint_info['personnel_maint'])}/روز\n\n"
    )

    # برنامه‌ی واکسن: پروژه‌ی تحقیقاتی-تولیدی، جایش همین‌جاست
    try:
        import internal_affairs as ia
        doses = int(c.get("vaccine_doses") or 0)
        active = ia.get_active_vaccine_project(c["id"])
        text += "💉 *برنامه واکسن*\n"
        if active:
            ready = ia._parse_dt(active["ready_at"])
            hours = max(0, int((ready - ia._now()).total_seconds() // 3600)) if ready else 0
            text += f"• 🏭 در حال تولید: *{active['doses']:,} دُز* — {hours} ساعت تا تحویل\n"
        else:
            text += f"• 📦 دُز آماده در انبار: *{doses:,}*\n"
        if tech_lvl < ia.VACCINE_MIN_TECH_LEVEL:
            text += f"• 🔒 برای شروع تولید، سطح فناوری *{ia.VACCINE_MIN_TECH_LEVEL}* لازم است\n"
        text += "\n"
        vaccine_row = [InlineKeyboardButton("💉 برنامه واکسن", callback_data="dom:vaccine")]
    except Exception:
        vaccine_row = None

    if tech_lvl < 5:
        up_info = TECH_UPGRADES[tech_lvl]
        text += (
            f"🚀 *شرایط ارتقا به {up_info['label']}:*\n"
            f"• 💰 هزینه ارتقا: {format_money(up_info['cost_money'])}\n"
            f"• 🪙 طلا مورد نیاز: {up_info['cost_gold']} شمش طلا\n"
            f"• 💻 میکروچیپ مورد نیاز: {up_info['cost_chips']} عدد تراشه\n"
            f"• 📈 تخفیف نگهداری پس از ارتقا: *{up_info['discount']}٪*\n"
        )
        keyboard = [
            [InlineKeyboardButton(f"🚀 ارتقا به {up_info['label']}", callback_data="research:do_upgrade")],
        ]
    else:
        text += "🌟 *کشور شما در بالاترین سطح فناوری بومی (سطح ۵ - ۴۰٪ تخفیف) قرار دارد.*"
        keyboard = []

    if vaccine_row:
        keyboard.append(vaccine_row)
    keyboard.append([InlineKeyboardButton("🏛️ سیاست داخلی و بحران‌ها", callback_data="dom:menu")])

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def research_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    country = db.get_country_by_player(user_id)

    if not country:
        await query.answer("هنوز کشوری نساختی!", show_alert=True)
        return

    await query.answer()

    if data == "research:menu":
        await research_menu(update, context)

    elif data == "research:do_upgrade":
        tech_lvl = country.get("tech_level", 1)
        if tech_lvl >= 5:
            await query.edit_message_text("🌟 کشور شما در بالاترین سطح فناوری قرار دارد.")
            return

        up_info = TECH_UPGRADES[tech_lvl]
        money_needed = up_info["cost_money"]
        gold_needed = up_info["cost_gold"]
        chips_needed = up_info.get("cost_chips", 0)

        if country["treasury"] < money_needed:
            await query.edit_message_text(
                f"❌ *ارتقای فناوری انجام نشد:*\n\nموجودی خزانه کافی نیست!\n💰 هزینه: {format_money(money_needed)} | موجودی فعلی: {format_money(country['treasury'])}",
                parse_mode="Markdown"
            )
            return

        if country["gold"] < gold_needed:
            await query.edit_message_text(
                f"❌ *ارتقای فناوری انجام نشد:*\n\nطلا کافی نیست!\n🪙 طلا مورد نیاز: {gold_needed} شمش | موجودی فعلی: {country['gold']} شمش",
                parse_mode="Markdown"
            )
            return

        curr_chips = country.get("microchips", 0) or 0
        if curr_chips < chips_needed:
            await query.edit_message_text(
                f"❌ *ارتقای فناوری انجام نشد:*\n\nتراشه نیمه‌هادی کافی نیست!\n💻 میکروچیپ مورد نیاز: {chips_needed:,} عدد | موجودی فعلی: {curr_chips:,} عدد\n\n💡 می‌توانید تراشه را از بورس کالا (/market) یا قراردادهای تجاری (/trade) تهیه فرمایید.",
                parse_mode="Markdown"
            )
            return

        # Deduct & Upgrade
        db.adjust_treasury(country["id"], -money_needed)
        db.adjust_gold(country["id"], -gold_needed)
        db.adjust_microchips(country["id"], -chips_needed)
        db.update_country_field(country["id"], "tech_level", tech_lvl + 1)

        db.add_log(actor=str(user_id), action="upgrade_tech", details=f"Level {tech_lvl + 1}")

        updated_c = db.get_country_by_player(user_id)
        maint_info = db.calculate_country_maintenance_cost(country["id"])

        text = (
            f"🎉 *ارتقای سطح فناوری با موفقیت انجام شد!*\n\n"
            f"🔬 *سطح فناوری جدید:* *سطح {tech_lvl + 1} ({up_info['label']})*\n"
            f"📉 *تخفیف نگهداری جدید:* *{up_info['discount']}٪*\n"
            f"💰 *صرفه‌جویی روزانه در هزینه‌ها:* {format_money(maint_info['assets_maint'])}\n\n"
            f"🏦 *موجودی جدید خزانه:* {format_money(updated_c['treasury'])}\n"
            f"🪙 *موجودی جدید طلا:* {format_number(updated_c['gold'])} شمش\n"
            f"💻 *موجودی جدید میکروچیپ:* {format_number(updated_c.get('microchips') or 0)} عدد"
        )

        await query.edit_message_text(text, parse_mode="Markdown")
