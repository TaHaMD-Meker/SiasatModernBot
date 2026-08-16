# -*- coding: utf-8 -*-
"""
ماژول ثبت و ابلاغ عملیات‌ها و رول‌های نظامی توسط بازیکنان (Player Roleplay Submission)
سقف مجاز روزانه ۲ رول (تهاجمی/پدافندی) و ارسال مستقیم به ستاد ادمین.
"""

import datetime
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
            await update.message.reply_text("هنوز کشوری نساختی! برای شروع /start رو بزن.", parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.answer("هنوز کشوری نساختی!", show_alert=True)
        return None
    return country


# ==================== منوی عملیات ====================

async def operations_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = await require_country(update)
    if not c:
        return

    today_str = datetime.date.today().isoformat()
    daily_count = db.get_daily_roleplay_count(c["id"], today_str)
    remaining_roles = max(0, 2 - daily_count)

    text = (
        f"🎯 *ستاد فرماندهی و ابلاغ عملیات {c['flag']} {c['name']}*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "شما می‌توانید طرح‌ها و رول‌های نظامی خود را ثبت و جهت بررسی ادمین ارسال فرمایید.\n\n"
        f"• *سقف مجاز روزانه:* ۲ رول (استفاده‌شده امروز: {daily_count} از ۲)\n"
        f"• *امکان ثبت باقی‌مانده:* {remaining_roles} رول\n\n"
        "نوع رول مد نظر خود را انتخاب کنید:"
    )

    keyboard = [
        [InlineKeyboardButton("📝 ثبت رول تهاجمی (حمله)", callback_data="op:submit:attack"), InlineKeyboardButton("🛡️ ثبت رول پدافندی (دفاع)", callback_data="op:submit:defense")],
        [InlineKeyboardButton("📋 مشاهده رول‌های ثبت‌شده من", callback_data="op:my_roles")],
    ]

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== Callback Handler عملیات ====================

async def operations_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    country = db.get_country_by_player(user_id)

    if not country:
        await query.answer("هنوز کشوری نساختی!", show_alert=True)
        return

    await query.answer()

    if data == "op:menu":
        await operations_menu(update, context)

    elif data.startswith("op:submit:"):
        role_type = data.split(":")[2] # 'attack' or 'defense'
        today_str = datetime.date.today().isoformat()
        daily_count = db.get_daily_roleplay_count(country["id"], today_str)

        if daily_count >= 2:
            await query.edit_message_text(
                "⛔ *سقف مجاز روزانه پر شده است!*\n\nشما امروز سقف ۲ رول نظامی خود را ثبت کرده‌اید. فردا مجدداً می‌توانید رول جدید ثبت بفرمایید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منوی عملیات", callback_data="op:menu")]]),
                parse_mode="Markdown"
            )
            return

        context.user_data["role_submit_draft"] = {"role_type": role_type}
        context.user_data["roleplay_text_input"] = True

        type_label = "📝 رول تهاجمی (حمله)" if role_type == "attack" else "🛡️ رول پدافندی (دفاع)"

        await query.edit_message_text(
            f"🎯 *ثبت {type_label} — کشور {country['flag']} {country['name']}*\n\nلطفاً *متن کامل طرح، جزئیات عملیات و دستورات نظامی* خود را در پیام بعدی ارسال فرمایید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="op:menu")]]),
            parse_mode="Markdown"
        )

    elif data == "op:my_roles":
        roles = db.get_country_roleplays(country["id"])
        lines = [f"📋 *لیست رول‌های ثبت‌شده اخیر کشور {country['flag']} {country['name']}*\n━━━━━━━━━━━━━━━━━━\n"]

        if not roles:
            lines.append("هنوز هیچ رول نظامی ثبت نکرده‌اید.")
        else:
            type_labels = {"attack": "📝 تهاجمی (حمله)", "defense": "🛡️ پدافندی (دفاع)"}
            status_labels = {
                "pending": "⏳ معلق در انتظار تایید ادمین",
                "approved": "✅ تایید شده توسط ادمین",
                "rejected": "❌ رد شده توسط ادمین"
            }

            for r in roles:
                dt_str = r.get("created_at", "")[:10]
                t_lbl = type_labels.get(r["role_type"], r["role_type"])
                s_lbl = status_labels.get(r["status"], r["status"])
                short_text = r["role_text"][:60] + "..." if len(r["role_text"]) > 60 else r["role_text"]

                lines.append(f"• *تاریخ {dt_str}* | *نوع:* {t_lbl}")
                lines.append(f"  *وضعیت:* {s_lbl}")
                lines.append(f'  _"{short_text}"_\n')

        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی عملیات", callback_data="op:menu")]]
        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== Text Input Handler رول‌ها ====================

async def operations_text_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        return

    if not context.user_data.get("roleplay_text_input"):
        return

    text = update.message.text.strip()
    draft = context.user_data.get("role_submit_draft", {})
    role_type = draft.get("role_type", "attack")

    del context.user_data["roleplay_text_input"]

    role_id = db.create_pending_roleplay(
        country_id=country["id"],
        player_id=user_id,
        role_type=role_type,
        role_text=text
    )

    type_label = "📝 رول تهاجمی (حمله)" if role_type == "attack" else "🛡️ رول پدافندی (دفاع)"
    user_name_str = f"@{update.effective_user.username}" if update.effective_user.username else "بدون یوزرنیم"

    admin_msg = (
        "📝 *رول نظامی جدید دریافتی جهت بررسی و تایید!*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"• *کشور:* {country['flag']} {country['name']}\n"
        f"• *بازیکن:* {user_name_str} (ID: `{user_id}`)\n"
        f"• *نوع رول:* {type_label}\n"
        f"• *شناسه رول:* `{role_id}`\n\n"
        f"📋 *متن کامل رول:*\n"
        f'"{text}"'
    )

    admin_kb = [
        [InlineKeyboardButton("✅ تایید رول و اطلاع‌رسانی", callback_data=f"admin:app_role:{role_id}")],
        [InlineKeyboardButton("❌ رد رول", callback_data=f"admin:rej_role:{role_id}")],
    ]

    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_msg,
                reply_markup=InlineKeyboardMarkup(admin_kb),
                parse_mode="Markdown"
            )
        except Exception:
            pass

    await update.message.reply_text(
        f"✅ *{type_label} شما با موفقیت ثبت شد.*\n\n"
        "طرح عملیاتی شما جهت بررسی برای ستاد مدیریت ارسال گردید. پس از تایید ادمین، اطلاع‌رسانی خواهد شد.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(user_id)
    )