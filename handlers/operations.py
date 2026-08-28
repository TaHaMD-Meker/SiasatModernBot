# -*- coding: utf-8 -*-
"""
ماژول ثبت و ابلاغ عملیات‌ها و رول‌های نظامی توسط بازیکنان (Player Roleplay Submission)
همراه با سامانه جدید برگزاری مانورهای نظامی و ارتقای آمادگی رزمی نیروها.
"""

import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

import database as db
import config
import news_engine
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
                "به محض تأیید ادمین اصلی بازی، دسترسی شما و تمام دکمه‌های کشور فعال خواهند شد."
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


# ==================== منوی عملیات ====================

def get_country_max_drills(country: dict) -> int:
    """محاسبه سقف روزانه مجاز مانورهای نظامی بر اساس سطح اشتراک VIP."""
    if not country or not country.get("is_vip"):
        return 1
    vt = country.get("vip_tier") or ""
    if vt == "diamond":
        return 999
    elif vt == "gold":
        return 4
    elif vt == "silver":
        return 3
    elif vt == "bronze":
        return 2
    return 2


async def operations_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = await require_country(update)
    if not c:
        return

    today_str = datetime.date.today().isoformat()
    daily_count = db.get_daily_roleplay_count(c["id"], today_str)
    remaining_roles = max(0, 2 - daily_count)

    readiness = c.get("combat_readiness", 70)
    last_drill_date = c.get("last_drill_date")
    daily_drill_count = c.get("daily_drill_count", 0) if last_drill_date == today_str else 0
    
    max_drills = get_country_max_drills(c)
    max_drill_str = "نامحدود (الماس)" if max_drills >= 999 else str(max_drills)
    rem_drill_str = "نامحدود" if max_drills >= 999 else str(max(0, max_drills - daily_drill_count))

    text = (
        f"🎯 *ستاد فرماندهی و ابلاغ عملیات {c['flag']} {c['name']}*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🪖 *شاخص آمادگی رزمی نیروها:* ⚔️ `{readiness}٪`\n"
        f"• *رول‌های نظامی ثبت‌شده امروز:* {daily_count} از ۲ (باقی‌مانده: {remaining_roles})\n"
        f"• *مانورهای رزمی برگزارشده امروز:* {daily_drill_count} از {max_drill_str} (باقی‌مانده: {rem_drill_str})\n\n"
        "لطفاً یکی از بخش‌های زیر را انتخاب کنید:"
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

    elif data == "op:military_drill":
        today_str = datetime.date.today().isoformat()
        last_drill_date = country.get("last_drill_date")
        daily_drill_count = country.get("daily_drill_count", 0) if last_drill_date == today_str else 0
        readiness = country.get("combat_readiness", 70)

        max_drills = get_country_max_drills(country)
        max_drill_str = "نامحدود (الماس)" if max_drills >= 999 else str(max_drills)
        rem_drill_str = "نامحدود" if max_drills >= 999 else str(max(0, max_drills - daily_drill_count))

        DRILL_MONEY_COST = 1_000_000
        DRILL_OIL_COST = 100_000

        text = (
            f"🪖 *ستاد برگزاری مانور و تمرینات رزمی — {country['flag']} {country['name']}*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• *شاخص آمادگی رزمی فعلی:* ⚔️ `{readiness}٪`\n"
            f"• *تعداد مانورهای برگزارشده امروز:* `{daily_drill_count} از {max_drill_str}` (باقی‌مانده: {rem_drill_str})\n\n"
            "⚠️ **هزینه‌ها و دستاوردهای برگزاری مانور رزمی:**\n"
            f"💵 **هزینه پشتیبانی و لجستیک:** {format_money(DRILL_MONEY_COST)}\n"
            f"🛢️ **سوخت مصرفی ناودسته‌ها و یگان‌ها:** {format_oil(DRILL_OIL_COST)}\n\n"
            "🏆 **دستاوردهای مانور:**\n"
            "📈 **ارتقای آمادگی رزمی نیروها:** +۴٪ (افزایش کارایی و روحیه دفاعی)\n"
            "📊 **افزایش رضایت عمومی و روحیه ملی:** +۲٪\n"
            f"⭐ **سقف روزانه مجاز:** {max_drill_str}\n\n"
            "آیا مایل به آغاز مانور رزمی نیروهای مسلح هستید؟"
        )

        keyboard = [
            [InlineKeyboardButton("✅ آغاز و اجرای مانور رزمی", callback_data="op:do_military_drill")],
            [InlineKeyboardButton("🔙 بازگشت به ستاد توسعه", callback_data="mv:menu")]
        ]

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "op:do_military_drill":
        today_str = datetime.date.today().isoformat()
        last_drill_date = country.get("last_drill_date")
        daily_drill_count = country.get("daily_drill_count", 0) if last_drill_date == today_str else 0

        max_drills = get_country_max_drills(country)
        drill_tickets = country.get("drill_tickets", 0) or 0

        DRILL_MONEY_COST = 1_000_000
        DRILL_OIL_COST = 100_000

        if daily_drill_count >= max_drills:
            if drill_tickets > 0:
                # استفاده خودکار از بلیط مانور اضافه
                db.update_country_field(country["id"], "drill_tickets", max(0, drill_tickets - 1))
                # ادامه به اجرای مانور با بلیط
                pass
            else:
                await query.edit_message_text(
                    f"⛔ **سقف روزانه مانور رزمی پر شده است!**\n\nشما امروز حداکثر مانورهای نظامی مجاز خود را برگزار کرده‌اید ({daily_drill_count}/{max_drills}).\n"
                    f"🎫 بلیط اضافه نداری. می‌تونی از فروشگاه VIP بسته مانور بخری:\n`/vip` → خدمات دیده شدن + بلیط‌ها",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به ستاد توسعه", callback_data="mv:menu")]]),
                    parse_mode="Markdown"
                )
                return

        if country.get("treasury", 0) < DRILL_MONEY_COST:
            await query.edit_message_text(
                f"❌ **عدم تکافوی منابع مالی:**\n\nبرای برگزاری مانور نیاز به {format_money(DRILL_MONEY_COST)} دارید. خزانه شما کافی نمی‌باشد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به ستاد توسعه", callback_data="mv:menu")]]),
                parse_mode="Markdown"
            )
            return

        if country.get("oil_reserves", 0) < DRILL_OIL_COST:
            await query.edit_message_text(
                f"❌ **عدم تکافوی سوخت:**\n\nبرای سوخت‌رسانی به یگان‌های زرهی و هوایی مانور نیاز به {format_oil(DRILL_OIL_COST)} نفت دارید.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به ستاد توسعه", callback_data="mv:menu")]]),
                parse_mode="Markdown"
            )
            return

        # Deduct costs
        db.adjust_treasury(country["id"], -DRILL_MONEY_COST)
        db.adjust_oil(country["id"], -DRILL_OIL_COST)
        db.add_transaction(country["id"], "military_drill", "هزینه لجستیک و سوخت برگزاری مانور نظامی", -DRILL_MONEY_COST)

        # Increment readiness and approval
        curr_readiness = country.get("combat_readiness", 70)
        new_readiness = min(100, curr_readiness + 4)
        db.update_country_field(country["id"], "combat_readiness", new_readiness)

        curr_app = country.get("approval_rating", 80)
        new_app = min(100, curr_app + 2)
        db.update_country_field(country["id"], "approval_rating", new_app)

        # Update drill counts
        new_drill_count = daily_drill_count + 1
        db.update_country_field(country["id"], "last_drill_date", today_str)
        db.update_country_field(country["id"], "daily_drill_count", new_drill_count)

        # Trigger Breaking News
        await news_engine.post_breaking_news(
            context.bot,
            f"برگزاری مانور اقتدار رزمی نیروهای مسلح {country['name']}",
            f"یگان‌های زرهی، هوایی، موشکی و پدافندی کشور {country['flag']} {country['name']} با موفقیت مانور رزمی اقتدار را برگزار نمودند. شاخص آمادگی رزمی این کشور به {new_readiness}٪ ارتقا یافت.",
            "اقتدار دفاعی"
        )

        rem_str = "نامحدود" if max_drills >= 999 else f"{max(0, max_drills - new_drill_count)} از {max_drills}"

        await query.edit_message_text(
            f"🪖 **مانور نظامی کشور {country['flag']} {country['name']} با موفقیت کامل برگزار شد!**\n━━━━━━━━━━━━━━━━━━\n\n"
            f"• **شاخص آمادگی رزمی جدید:** ⚔️ `{new_readiness}٪` (+۴٪ افزایش)\n"
            f"• **رضایت عمومی:** `{new_app}٪` (+۲٪ افزایش)\n"
            f"• **هزینه پرداختی خزانه:** {format_money(DRILL_MONEY_COST)}\n"
            f"• **سوخت مصرفی:** {format_oil(DRILL_OIL_COST)}\n"
            f"• **مانورهای باقی‌مانده امروز:** `{rem_str}`\n\n"
            "📢 خبر موفقیت مانور نظامی در کانال رسمی بازی منتشر گردید.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به ستاد توسعه", callback_data="mv:menu")]]),
            parse_mode="Markdown"
        )
        try:
            _mok, _mrw = db.complete_daily_mission(country["id"], "drill")
            if _mok:
                await context.bot.send_message(chat_id=user_id, text=f"🎯 *مأموریت روزانه کامل شد!* +{format_money(_mrw)} به خزانه.", parse_mode="Markdown")
            db.add_battle_pass_xp(country["id"], 150)
            if new_readiness >= 85:
                db.progress_battle_pass_challenge(country["id"], "drill", 1)
            db.sync_and_check_all_challenges(country["id"])
        except Exception:
            pass

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

        if db.get_setting("role_submit_locked") == "1":
            await query.edit_message_text(
                "🔒 **ارسال رول در حال حاضر قفل است.**\n\n"
                "برای ارسال رول می‌توانید به این آیدی پیام دهید:\n"
                "@vfvvx",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="op:menu")]]),
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

    text = (update.message.text or update.message.caption or "").strip()
    if not text:
        await update.message.reply_text("متن رول را به‌صورت پیام متنی بفرست.")
        return
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