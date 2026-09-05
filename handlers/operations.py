# -*- coding: utf-8 -*-
"""
ماژول ثبت و ابلاغ عملیات‌ها و رول‌های نظامی توسط بازیکنان (Player Roleplay Submission)
همراه با سامانه جدید برگزاری مانورهای نظامی و ارتقای آمادگی رزمی نیروها.
"""

import datetime
import json
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

    top_tension = ""
    try:
        t_rows = db.get_tension_rows(c["id"])
        if t_rows and t_rows[0]["value"] > 0:
            top_tension = f"🌡 *بالاترین تنش فعال:* {t_rows[0]['other_name']} — `{t_rows[0]['value']}/۱۰۰`\n"
    except Exception:
        pass

    text = (
        f"🎯 *ستاد فرماندهی و ابلاغ عملیات {c['flag']} {c['name']}*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🪖 *شاخص آمادگی رزمی نیروها:* ⚔️ `{readiness}٪`\n"
        f"• *رول‌های نظامی ثبت‌شده امروز:* {daily_count} از ۲ (باقی‌مانده: {remaining_roles})\n"
        f"{top_tension}"
        f"• *مانورهای رزمی برگزارشده امروز:* {daily_drill_count} از {max_drill_str} (باقی‌مانده: {rem_drill_str})\n\n"
        "لطفاً یکی از بخش‌های زیر را انتخاب کنید:"
    )

    keyboard = [
        [InlineKeyboardButton("📝 ثبت رول تهاجمی (حمله)", callback_data="op:submit:attack"), InlineKeyboardButton("🛡️ ثبت رول پدافندی (دفاع)", callback_data="op:submit:defense")],
        [InlineKeyboardButton("🌡 وضعیت تنش من", callback_data="op:tension"), InlineKeyboardButton("📋 رول‌های ثبت‌شده من", callback_data="op:my_roles")],
        [InlineKeyboardButton("📖 راهنمای عملیات", callback_data="op:guide")],
        [InlineKeyboardButton("⚔️ جنگ‌های من", callback_data="op:wars")],
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

    elif data == "op:wars":
        wars = db.list_active_wars(country["id"])
        if not wars:
            await query.edit_message_text(
                "🕊 *جنگ فعالی نداری.*\n\nجنگ با اولین عملیات محدودِ پذیرفته‌شده باز می‌شود.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="op:menu")]]),
                parse_mode="Markdown")
            return
        lines = ["⚔️ *جنگ‌های فعال تو*\n━━━━━━━━━━━━━━━━━━"]
        buttons = []
        for w in wars:
            other_id = w["defender_id"] if w["attacker_id"] == country["id"] else w["attacker_id"]
            other = db.get_country_by_id(other_id)
            oname = f"{other['flag']} {other['name']}" if other else "؟"
            front = w["front"] if w["attacker_id"] == country["id"] else -w["front"]
            bar = "▓" * (abs(front) // 10) + "░" * (10 - abs(front) // 10)
            side = "پیشروی ✅" if front > 0 else ("عقب‌نشینی ⚠️" if front < 0 else "خط مقدم ثابت")
            lines.append(f"🔥 {oname} — جبهه: `{bar}` ({front:+d}) {side}")
            lines.append(f"   امتیاز جنگ: {w['warscore']}")
            if w.get("ceasefire_requested_by") and w["ceasefire_requested_by"] == other_id:
                lines.append("   🕊 طرف مقابل آتش‌بس خواسته — تصمیم تو:")
                buttons.append([
                    InlineKeyboardButton(f"🕊 پذیرش ({other['name']})", callback_data=f"op:cfacc:{w['id']}"),
                    InlineKeyboardButton("❌ رد", callback_data=f"op:cfdec:{w['id']}"),
                ])
            elif front >= config.WAR_PEACE_FRONT_THRESHOLD and w["attacker_id"] == country["id"]:
                lines.append(f"   💰 حق مطالبه‌ی غرامت داری (جبهه ≥ {config.WAR_PEACE_FRONT_THRESHOLD})")
                buttons.append([InlineKeyboardButton(f"💰 صلح با غرامت از {other['name']}", callback_data=f"op:rep:{w['id']}")])
            if not (w.get("ceasefire_requested_by") and w["ceasefire_requested_by"] != country["id"]):
                buttons.append([
                    InlineKeyboardButton(f"🕊 درخواست آتش‌بس ({other['name']})", callback_data=f"op:cfreq:{w['id']}"),
                    InlineKeyboardButton("🏳 خروج یک‌طرفه", callback_data=f"op:wdraw:{w['id']}"),
                ])
            lines.append("")
        buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="op:menu")])
        await query.edit_message_text("\n".join(lines),
            reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

    elif data.startswith("op:cfreq:"):
        war = db.get_war_by_id(int(data.split(":")[2]))
        if not war or country["id"] not in (war["attacker_id"], war["defender_id"]):
            await query.answer("یافت نشد!", show_alert=True)
            return
        other_id = war["defender_id"] if war["attacker_id"] == country["id"] else war["attacker_id"]
        ok, msg = db.request_ceasefire(war["id"], country["id"])
        other = db.get_country_by_id(other_id)
        if ok and other and other.get("player_id"):
            try:
                kb = InlineKeyboardMarkup([[
                    InlineKeyboardButton(f"🕊 پذیرش آتش‌بس ({country['name']})", callback_data=f"op:cfacc:{war['id']}"),
                    InlineKeyboardButton("❌ ادامه‌ی جنگ", callback_data=f"op:cfdec:{war['id']}"),
                ]])
                await context.bot.send_message(chat_id=other["player_id"],
                    text=f"🕊 *{country['flag']} {country['name']} پیشنهاد آتش‌بس داده.*\nپذیرش یا ادامه‌ی جنگ؟",
                    reply_markup=kb, parse_mode="Markdown")
            except Exception:
                pass
        await query.answer(msg, show_alert=True)
        await operations_menu(update, context)

    elif data.startswith("op:cfacc:"):
        war = db.get_war_by_id(int(data.split(":")[2]))
        if not war or country["id"] not in (war["attacker_id"], war["defender_id"]):
            await query.answer("یافت نشد!", show_alert=True)
            return
        ok, msg = db.accept_ceasefire(war["id"], country["id"])
        await query.answer(msg, show_alert=True)
        await operations_menu(update, context)

    elif data.startswith("op:cfdec:"):
        war = db.get_war_by_id(int(data.split(":")[2]))
        if not war or country["id"] not in (war["attacker_id"], war["defender_id"]):
            await query.answer("یافت نشد!", show_alert=True)
            return
        ok, msg = db.decline_ceasefire(war["id"], country["id"])
        await query.answer("جنگ ادامه دارد.", show_alert=True)
        await operations_menu(update, context)

    elif data.startswith("op:rep:"):
        war = db.get_war_by_id(int(data.split(":")[2]))
        if not war or war["status"] != "active":
            await query.answer("یافت نشد!", show_alert=True)
            return
        loser_id = war["defender_id"] if war["attacker_id"] == country["id"] else war["attacker_id"]
        ok, msg = db.end_war_with_reparations(war["id"], winner_id=country["id"], loser_id=loser_id)
        loser = db.get_country_by_id(loser_id)
        if ok and loser and loser.get("player_id"):
            try:
                await context.bot.send_message(chat_id=loser["player_id"],
                    text=f"💰 *صلح غرامتی امضا شد.*\n{msg}", parse_mode="Markdown")
            except Exception:
                pass
        await query.answer(msg, show_alert=True)
        await operations_menu(update, context)

    elif data.startswith("op:wdraw:"):
        war = db.get_war_by_id(int(data.split(":")[2]))
        if not war or country["id"] not in (war["attacker_id"], war["defender_id"]):
            await query.answer("یافت نشد!", show_alert=True)
            return
        ok, msg = db.withdraw_from_war(war["id"], country_id=country["id"])
        await query.answer(msg, show_alert=True)
        await operations_menu(update, context)

    elif data == "op:guide":
        guide = (
            "📖 *راهنمای عملیات نظامی*\n━━━━━━━━━━━━━━━━━━\n\n"
            f"⚔️ حمله به هر کشوری *تنش* می‌خواهد — جنگ از آسمان نمی‌آید!\n"
            f"حداقل تنش برای حمله: *{config.TENSION_ATTACK_THRESHOLD} از ۱۰۰*\n\n"
            "🌡 *تنش را چطور بسازم؟*\n"
            f"• بیانیه تند یا اولتیماتوم ← +{config.TENSION_STATEMENT_DELTA}\n"
            f"• عملیات اطلاعات/سایبری موفق ← +{config.TENSION_INTEL_SUCCESS_DELTA}\n"
            f"• تحریم تجاری ← +{config.TENSION_SANCTION_DELTA}\n"
            f"• حمله‌ی محدود موفق ← +{config.TENSION_AUTO_ATTACK_DELTA}\n"
            f"⚠️ تنش هر روز {config.TENSION_DAILY_DECAY} واحد سرد می‌شود — سریع عمل کن!\n\n"
            "⚙️ *عملیات عادی* (مهمات ≤۲۵، تک‌هدف، بدون هدف راهبردی) به‌صورت "
            "خودکار اجرا می‌شود: تلفات، خبر و گزارش همه توسط ستاد بات.\n\n"
            "📤 *عملیات گسترده* (موج سنگین، هدف راهبردی مثل نفت/برق/غلات/طلا، "
            "اعلان جنگ، ائتلاف چندکشوری) به مدیریت ارجاع می‌شود و با داوری دستی اجرا می‌شود.\n\n"
            "📦 مهمات از *انبار واقعی خودت* کسر می‌شود؛ چیزی که نداری کسر نمی‌شود.\n"
            "🔥 هر موشک/پهپاد تراشه می‌سوزاند (کروز ۱۵، هایپرسونیک ۳۰، پهپاد رزمی ۳). "
            "هل‌فایر و راکت سبک رایگان است.\n\n"
            "🛡️ *طرح دفاعی:* هر کشور یک طرح پدافندی ثبت می‌کند؛ هزینه‌ی روزانه‌اش "
            "(پول/نفت/تراشه/غلات) کسر می‌شود و در عملیات‌های خودکار به فریب و "
            "میان‌یابی مدافع کمک می‌کند."
        )
        await query.edit_message_text(
            guide,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منوی عملیات", callback_data="op:menu")]]),
            parse_mode="Markdown"
        )

    elif data == "op:tension":
        rows = db.get_tension_rows(country["id"])
        lines = [f"🌡 *وضعیت تنش {country['flag']} {country['name']}*\n━━━━━━━━━━━━━━━━━━\n"]
        if not rows:
            lines.append("با هیچ کشوری تنش فعالی نداری — آسوده‌حال باش.")
        else:
            for r in rows[:15]:
                bar = "▓" * (r["value"] // 10) + "░" * (10 - r["value"] // 10)
                hot = "🔥" if r["value"] >= config.TENSION_ATTACK_THRESHOLD else ""
                lines.append(f"{hot} {r['other_name']} — {r['value']}/۱۰۰ `{bar}`")
                if r.get("reason"):
                    lines.append(f"   _آخرین علت: {r['reason'][:50]}_")
            lines.append("")
            lines.append(f"حداقل تنش برای حمله: {config.TENSION_ATTACK_THRESHOLD}/۱۰۰")
        await query.edit_message_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به منوی عملیات", callback_data="op:menu")]]),
            parse_mode="Markdown"
        )

    elif data == "op:search":
        context.user_data["role_submit_draft"] = context.user_data.get("role_submit_draft") or {"role_type": "attack"}
        context.user_data["op_target_search"] = True
        await query.edit_message_text(
            "🔎 *جستجوی تایپی کشور هدف*\n\nنام کشور مقصد را بفرست:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="op:submit:attack")]]),
            parse_mode="Markdown"
        )

    elif data.startswith("op:cont:"):
        cont_key = data.split(":")[2]
        cont_info = config.CONTINENTS.get(cont_key, {})
        keys = cont_info.get("keys", [])
        all_countries = db.get_all_countries()
        by_key = {}
        for c in all_countries:
            if c.get("country_key"):
                by_key[c["country_key"]] = c
        targets = [by_key[k] for k in keys if k in by_key]
        if not targets:
            await query.edit_message_text(
                "در این قاره کشور بازیکن‌داری نیست.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لیست قاره‌ها", callback_data="op:submit:attack")]]),
                parse_mode="Markdown"
            )
            return
        buttons = []
        row = []
        for c in targets:
            row.append(InlineKeyboardButton(f"{c['flag']} {c['name']}", callback_data=f"op:pick:{c['id']}"))
            if len(row) == 2:
                buttons.append(row)
                row = []
        if row:
            buttons.append(row)
        buttons.append([InlineKeyboardButton("🔎 جستجوی تایپی", callback_data="op:search"),
                        InlineKeyboardButton("🔙 لیست قاره‌ها", callback_data="op:submit:attack")])
        await query.edit_message_text(
            f"{cont_info.get('short_name', 'قاره')}\n\nکشور هدف را انتخاب کن:",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode="Markdown"
        )

    elif data.startswith("op:pick:"):
        target_id = int(data.split(":")[2])
        target_c = db.get_country_by_id(target_id)
        if not target_c:
            await query.answer("کشور یافت نشد!", show_alert=True)
            return
        if target_c["id"] == country["id"]:
            await query.answer("نمی‌توانی به خودت حمله کنی!", show_alert=True)
            return
        draft = context.user_data.get("role_submit_draft") or {"role_type": "attack"}
        draft["target_id"] = target_id
        context.user_data["role_submit_draft"] = draft
        context.user_data["roleplay_text_input"] = True
        await query.edit_message_text(
            f"🎯 *هدف:* {target_c['flag']} {target_c['name']}\n\n"
            "حالا *متن کامل طرح عملیاتی* را بفرست (تجهیزات را با تعداد بنویس — از انبار واقعی تو کسر می‌شود):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="op:menu")]]),
            parse_mode="Markdown"
        )

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
        if role_type == "attack":
            context.user_data["role_submit_draft"] = {"role_type": "attack"}
            # 🌍 انتخابگر هدف: قاره‌ها (برچسب متنی بدون ایموجی) + جستجوی تایپی
            from handlers.auto_ops import build_plain_continent_selector
            text, kb = build_plain_continent_selector("op")
            await query.edit_message_text(
                f"🎯 *ثبت رول حمله — کشور {country['flag']} {country['name']}*\n\n{text}",
                reply_markup=kb,
                parse_mode="Markdown"
            )
            return

        context.user_data["role_submit_draft"] = {"role_type": "defense"}
        context.user_data["defense_text_input"] = True
        await query.edit_message_text(
            f"🛡️ *ثبت طرح دفاعی — کشور {country['flag']} {country['name']}*\n\n"
            "متن طرح پدافندی خود را بفرست (مثال: «۶ آتشبار پاتریوت آماده، ۲۰ جنگنده در آماده‌باش هوایی، رادارها روشن»).\n\n"
            "⚠️ طرح جدید جای طرح قبلی را می‌گیرد و *هزینه‌ی روزانه* بر اساس تجهیزات نام‌برده‌شده از بیت‌المال کسر می‌شود (پول، نفت، تراشه، غلات).\n\n"
            "⛔ اگر حتی یکی از منابع روز کم بیاید، طرح تا روز بعد غیرفعال می‌شود.",
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
                "pending": "📤 پیش مدیریت (داوری دستی)",
                "approved": "✅ تایید شده توسط ادمین",
                "rejected": "❌ رد شد — دلیل در پیام ثبت فرستاده شد",
                "auto_executed": "⚙️ خودکار اجرا شد",
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

    text = (update.message.text or update.message.caption or "").strip()
    if not text:
        await update.message.reply_text("متن را به‌صورت پیام متنی بفرست.")
        return

    # ── جستجوی تایپی هدف ──
    if context.user_data.get("op_target_search"):
        context.user_data.pop("op_target_search", None)
        from handlers.losses import match_country_by_name
        target_c = match_country_by_name(text)
        if not target_c:
            await update.message.reply_text("❌ کشوری با این نام پیدا نشد. دوباره تلاش کن یا از لیست قاره‌ها انتخاب کن.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لیست قاره‌ها", callback_data="op:submit:attack")]]))
            return
        if target_c["id"] == country["id"]:
            await update.message.reply_text("❌ نمی‌توانی به کشور خودت حمله کنی!")
            return
        draft = context.user_data.get("role_submit_draft") or {"role_type": "attack"}
        draft["target_id"] = target_c["id"]
        context.user_data["role_submit_draft"] = draft
        context.user_data["roleplay_text_input"] = True
        await update.message.reply_text(
            f"🎯 *هدف:* {target_c['flag']} {target_c['name']}\n\n"
            "حالا *متن کامل طرح عملیاتی* را بفرست (تجهیزات را با تعداد بنویس):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="op:menu")]]),
            parse_mode="Markdown"
        )
        return

    # ── ثبت طرح دفاعی ──
    if context.user_data.get("defense_text_input"):
        context.user_data.pop("defense_text_input", None)
        await _register_defense_plan(update, context, country, text)
        return

    # ── متن رول حمله ──
    if not context.user_data.get("roleplay_text_input"):
        return
    context.user_data.pop("roleplay_text_input", None)
    draft = context.user_data.get("role_submit_draft", {})
    target_id = draft.get("target_id")
    if not target_id:
        await update.message.reply_text("اول کشور هدف را انتخاب کن.", parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 انتخاب هدف", callback_data="op:submit:attack")]]))
        return
    target_c = db.get_country_by_id(target_id)
    if not target_c:
        await update.message.reply_text("کشور هدف یافت نشد — دوباره انتخاب کن.")
        return

    from handlers.auto_ops import process_attack_submission
    result = process_attack_submission(country, target_c, text, bot=context.bot)

    if result["verdict"] == "rejected":
        await update.message.reply_text(
            f"⛔ *رول شما پذیرفته نشد.*\n\n{result['reason']}",
            parse_mode="Markdown",
            reply_markup=get_main_keyboard(user_id)
        )
        return

    if result["verdict"] == "escalated":
        # اطلاع‌رسانی ادمین مثل روال قبل + علت ارجاع
        user_name_str = f"@{update.effective_user.username}" if update.effective_user.username else "بدون یوزرنیم"
        admin_msg = (
            "📤 *رول نظامی ارجاعی (گسترده/مبهم) — نیازمند داوری!*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• *کشور:* {country['flag']} {country['name']}\n"
            f"• *بازیکن:* {user_name_str} (ID: `{user_id}`)\n"
            f"• *هدف:* {target_c['flag']} {target_c['name']}\n"
            f"• *علت ارجاع:* {'؛ '.join(result.get('reasons', []))}\n\n"
            f"📋 *متن کامل رول:*\n\"{text}\""
        )
        admin_kb = [
            [InlineKeyboardButton("✅ تایید رول و اطلاع‌رسانی", callback_data=f"admin:app_role:{result['role_id']}")],
            [InlineKeyboardButton("❌ رد رول", callback_data=f"admin:rej_role:{result['role_id']}")],
        ]
        for admin_id in config.ADMIN_IDS:
            try:
                await context.bot.send_message(chat_id=admin_id, text=admin_msg,
                    reply_markup=InlineKeyboardMarkup(admin_kb), parse_mode="Markdown")
            except Exception:
                pass
        await update.message.reply_text(result["player_msg"], parse_mode="Markdown",
            reply_markup=get_main_keyboard(user_id))
        return

    # خودکار اجرا شد
    res = result["resolution"]
    human = result["human"]
    await update.message.reply_text(
        "⚙️ *رول شما وارد چرخه‌ی اجرای خودکار شد.*\n━━━━━━━━━━━━━━━━━━\n\n"
        f"🎯 هدف: {target_c['flag']} {target_c['name']}\n"
        f"🌡 تنش: ✅\n"
        f"🛬 تلفات هوایی تو: {sum(res['attacker_aircraft_losses'].values())} جنگنده\n"
        f"🎖 تلفات مدافع: {result['defender_units_lost']} تجهیز | {human['mil_kia']} کشته | {human['wounded']} مجروح\n\n"
        "📰 خبر فوری منتشر شد و گزارش رسمی به دو طرف ارسال گردید.",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard(user_id)
    )


async def _register_defense_plan(update: Update, context: ContextTypes.DEFAULT_TYPE, country: dict, text: str):
    """ثبت/جایگزینی طرح دفاعی + محاسبه‌ی هزینه‌ی روزانه از تجهیزات نام‌برده."""
    assets = db.get_country_assets(country["id"])
    from handlers.auto_ops import extract_munitions, extract_targets
    committed, unmatched = extract_munitions(text, assets)
    if not committed:
        await update.message.reply_text(
            "❌ هیچ تجهیز شناخته‌شده‌ای در طرح پیدا نشد.\n"
            "تجهیزات را با نام واقعی انبار و تعداد بنویس (مثال: «۶ آتشبار پاتریوت، ۱۲ جنگنده تایفون»).",
            parse_mode="Markdown"
        )
        return

    f = config.DEFENSE_PLAN_COST_FACTORS
    money = oil = chips = grain = 0
    n_air = n_sam = 0
    plan_units = []
    for (key, name, qty, kind) in committed:
        row = next((a for a in assets if a["equipment_key"] == key), None)
        qty = min(qty, int(row["amount"] or 0) if row else qty)
        if qty <= 0:
            continue
        unit_maint = int((row or {}).get("maintenance_cost") or 0)
        money += int(unit_maint * qty * f["money"])
        import combat_model as _cm
        sam_cls = _cm.classify_sam(name, key)
        air_cls = _cm.classify_aircraft(name, key)
        if sam_cls:
            oil += int(config.DEFENSE_PLAN_OIL_PER_SAM * qty * f["oil"])
            chips += int(config.DEFENSE_PLAN_CHIPS_PER_SAM * qty * f["microchips"])
            n_sam += qty
        elif air_cls or kind == "aircraft":
            oil += int(config.DEFENSE_PLAN_OIL_PER_AIRCRAFT * qty * f["oil"])
            chips += int((qty // 4) * f["microchips"])
            n_air += qty
        else:
            n_sam += 0
        grain += int(config.DEFENSE_PLAN_GRAIN_PER_UNIT * qty * f["grain"])
        plan_units.append(f"{name} ×{qty}")

    costs = {"money": money, "oil": oil, "microchips": chips, "grain": grain}
    db.save_defense_plan(country["id"], text, costs)

    breakdown = (
        f"🛡️ *طرح دفاعی کشور {country['flag']} {country['name']} ثبت شد.*\n━━━━━━━━━━━━━━━━━━\n\n"
        f"📦 تجهیزات طرح: {'، '.join(plan_units[:8])}\n\n"
        f"💸 *هزینه‌ی روزانه:*\n"
        f"• پول: {format_money(money)}\n"
        f"• نفت: {oil:,} بشکه\n"
        f"• تراشه: {chips:,}\n"
        f"• غلات: {grain:,} تن\n\n"
        "✅ طرح فعال است؛ در عملیات‌های خودکار به فریب و میان‌یابی مدافع کمک می‌کند.\n"
        "⛔ کمبود هر منبع در چرخه‌ی روزانه = غیرفعال شدن طرح تا روز بعد."
    )
    await update.message.reply_text(breakdown, parse_mode="Markdown", reply_markup=get_main_keyboard(update.effective_user.id))
