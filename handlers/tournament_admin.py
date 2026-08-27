# -*- coding: utf-8 -*-
"""پنل ادمین برای ساخت، تنظیم، فعال‌سازی و پایان تورنومنت."""

from __future__ import annotations

import html
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import tournament_system as tournament


def _kb(rows):
    return InlineKeyboardMarkup(rows)


def _fmt(value):
    return tournament.format_score(value)


def _status_label(status: str) -> str:
    return {
        tournament.DRAFT: "📝 پیش‌نویس",
        tournament.ACTIVE: "🟢 فعال",
        tournament.PAUSED: "⏸ متوقف",
        tournament.ENDED: "🏁 پایان‌یافته",
    }.get(status, status or "نامشخص")


def _season_text(season: dict, notice: str = "") -> str:
    top = tournament.get_rankings(season["id"], limit=3)
    top_lines = "\n".join(
        f"{row['rank']}. {row.get('country_flag', '🏳️')} {row.get('country_name', 'کشور')} — {_fmt(row.get('score'))}"
        for row in top
    ) or "هنوز امتیازی ثبت نشده است."
    return (
        (f"✅ {html.escape(notice)}\n\n" if notice else "")
        + f"🏆 <b>مدیریت تورنومنت</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"📌 <b>{html.escape(season.get('title', 'فصل'))}</b>\n"
        f"وضعیت: <b>{_status_label(season.get('status'))}</b>\n"
        f"👥 شرکت‌کنندگان: <b>{tournament.get_participant_count(season['id'])}</b>\n"
        f"⏱ مدت: <b>{season.get('duration_days', 7)} روز</b>\n"
        f"🟢 شروع: <code>{season.get('starts_at') or 'پس از فعال‌سازی'}</code>\n"
        f"🏁 پایان: <code>{season.get('ends_at') or 'پس از فعال‌سازی'}</code>\n"
        f"🎁 جایزه: {html.escape(season.get('prize_text') or 'طبق اطلاعیه مدیریت')}\n\n"
        f"🥇 <b>سه رتبه اول فعلی:</b>\n{top_lines}"
    )


def _season_keyboard(season: dict):
    status = season.get("status")
    sid = season["id"]
    rows = []
    if status == tournament.DRAFT:
        rows.extend([
            [InlineKeyboardButton("✏️ تغییر عنوان فصل", callback_data=f"admin:tour_edit_title:{sid}")],
            [InlineKeyboardButton("💵 تنظیم توضیح جایزه", callback_data=f"admin:tour_edit_prize:{sid}")],
            [InlineKeyboardButton("⏱ تنظیم مدت فصل", callback_data=f"admin:tour_edit_duration:{sid}")],
            [InlineKeyboardButton("👥 شرکت‌کنندگان ثبت‌شده", callback_data=f"admin:tour_participants:{sid}")],
            [InlineKeyboardButton("📊 جدول پیش‌نمایش", callback_data=f"admin:tour_rank:{sid}:0")],
            [InlineKeyboardButton("▶️ فعال‌سازی فصل", callback_data=f"admin:tour_start:{sid}")],
            [InlineKeyboardButton("🗑 حذف پیش‌نویس", callback_data=f"admin:tour_delete:{sid}")],
        ])
    elif status == tournament.ACTIVE:
        rows.extend([
            [InlineKeyboardButton("📊 جدول زنده", callback_data=f"admin:tour_rank:{sid}:0")],
            [InlineKeyboardButton("🔄 محاسبه و بروزرسانی امتیازها", callback_data=f"admin:tour_refresh:{sid}")],
            [InlineKeyboardButton("➕ امتیاز/رویداد مدیریتی", callback_data=f"admin:tour_event_country:{sid}")],
            [InlineKeyboardButton("🚫 مدیریت شرکت‌کنندگان", callback_data=f"admin:tour_participants:{sid}")],
            [InlineKeyboardButton("⏸ توقف موقت امتیازدهی", callback_data=f"admin:tour_pause:{sid}")],
            [InlineKeyboardButton("🏁 پایان فصل", callback_data=f"admin:tour_end:{sid}")],
        ])
    elif status == tournament.PAUSED:
        rows.extend([
            [InlineKeyboardButton("📊 جدول فعلی", callback_data=f"admin:tour_rank:{sid}:0")],
            [InlineKeyboardButton("▶️ ادامه امتیازدهی", callback_data=f"admin:tour_resume:{sid}")],
            [InlineKeyboardButton("➕ امتیاز/رویداد مدیریتی", callback_data=f"admin:tour_event_country:{sid}")],
            [InlineKeyboardButton("🏁 پایان فصل", callback_data=f"admin:tour_end:{sid}")],
        ])
    else:
        rows.extend([
            [InlineKeyboardButton("🏆 جدول نهایی", callback_data=f"admin:tour_rank:{sid}:0")],
            [InlineKeyboardButton("📋 سوابق رویدادها", callback_data=f"admin:tour_events:{sid}")],
            [InlineKeyboardButton("➕ ساخت فصل بعدی", callback_data="admin:tour_create")],
        ])
    rows.append([InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")])
    return _kb(rows)


async def tournament_admin_menu(query, context, notice: str = ""):
    season = tournament.get_open_season()
    if not season:
        seasons = tournament.list_seasons(limit=1)
        if seasons:
            season = seasons[0]
        else:
            await query.edit_message_text(
                "🏆 <b>مدیریت تورنومنت</b>\n\nهنوز فصلی ساخته نشده است.",
                reply_markup=_kb([
                    [InlineKeyboardButton("➕ ساخت پیش‌نویس فصل جدید", callback_data="admin:tour_create")],
                    [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")],
                ]),
                parse_mode="HTML",
            )
            return
    await query.edit_message_text(_season_text(season, notice), reply_markup=_season_keyboard(season), parse_mode="HTML")


async def _participants_page(query, season_id: int, page: int = 0):
    per_page = 8
    rows = tournament.get_rankings(season_id, limit=per_page, offset=page * per_page)
    text = [f"👥 <b>شرکت‌کنندگان فصل #{season_id}</b>", "━━━━━━━━━━━━━━━━━━"]
    keyboard = []
    if not rows:
        text.append("شرکت‌کننده‌ای پیدا نشد.")
    else:
        for row in rows:
            text.append(f"{row['rank']}. {row.get('country_flag', '🏳️')} {html.escape(row.get('country_name', 'کشور'))} — {_fmt(row.get('score'))}")
            if row.get("status") != "disqualified":
                keyboard.append([
                    InlineKeyboardButton(
                        f"➕ امتیاز به {row.get('country_name', 'کشور')}",
                        callback_data=f"admin:tour_event:{season_id}:{row['country_id']}",
                    ),
                    InlineKeyboardButton(
                        "🚫 حذف",
                        callback_data=f"admin:tour_disqualify:{season_id}:{row['country_id']}",
                    ),
                ])
    total = tournament.get_participant_count(season_id)
    pages = max(1, (total + per_page - 1) // per_page)
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:tour_participants:{season_id}:{page - 1}"))
    if page < pages - 1:
        nav.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:tour_participants:{season_id}:{page + 1}"))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("🔙 مدیریت تورنومنت", callback_data="admin:tournament")])
    await query.edit_message_text("\n".join(text), reply_markup=_kb(keyboard), parse_mode="HTML")


async def _rank_page(query, season_id: int, page: int = 0):
    per_page = 10
    total = tournament.get_participant_count(season_id)
    pages = max(1, (total + per_page - 1) // per_page)
    page = max(0, min(page, pages - 1))
    rows = tournament.get_rankings(season_id, limit=per_page, offset=page * per_page)
    lines = [f"📊 <b>جدول تورنومنت #{season_id}</b>", f"صفحه {page + 1} از {pages}", "━━━━━━━━━━━━━━━━━━"]
    for row in rows:
        lines.append(f"<b>{row['rank']}.</b> {row.get('country_flag', '🏳️')} {html.escape(row.get('country_name', 'کشور'))} — <code>{_fmt(row.get('score'))}</code>")
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:tour_rank:{season_id}:{page - 1}"))
    if page < pages - 1:
        nav.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:tour_rank:{season_id}:{page + 1}"))
    keyboard = [nav] if nav else []
    keyboard.append([InlineKeyboardButton("🔙 مدیریت تورنومنت", callback_data="admin:tournament")])
    await query.edit_message_text("\n".join(lines) or "جدول خالی است.", reply_markup=_kb(keyboard), parse_mode="HTML")


async def _event_country_prompt(query, context, season_id: int):
    rows = []
    current = tournament.get_rankings(season_id, limit=50, offset=0)
    for row in current:
        rows.append([InlineKeyboardButton(
            f"{row.get('country_flag', '🏳️')} {row.get('country_name', 'کشور')}",
            callback_data=f"admin:tour_event:{season_id}:{row['country_id']}",
        )])
    rows.append([InlineKeyboardButton("🔙 مدیریت تورنومنت", callback_data="admin:tournament")])
    await query.edit_message_text(
        "➕ <b>ثبت رویداد امتیازی مدیریتی</b>\n\nکشور موردنظر را انتخاب کنید. سپس مقدار امتیاز و توضیح را ارسال کنید.",
        reply_markup=_kb(rows), parse_mode="HTML",
    )


async def tournament_admin_callback(query, context, data: str) -> bool:
    """پردازش callbackهای admin:* مربوط به تورنومنت."""
    if data == "admin:tournament":
        await tournament_admin_menu(query, context)
        return True
    if data == "admin:tour_create":
        ok, message, _season = tournament.create_draft()
        await tournament_admin_menu(query, context, message)
        return True

    parts = data.split(":")
    try:
        if data.startswith("admin:tour_edit_title:"):
            sid = int(parts[2])
            context.user_data["admin_awaiting_input"] = {"type": "tournament_title", "season_id": sid}
            await query.edit_message_text("✏️ عنوان جدید فصل را ارسال کنید:", reply_markup=_kb([[InlineKeyboardButton("❌ انصراف", callback_data="admin:tournament")]]), parse_mode="HTML")
            return True
        if data.startswith("admin:tour_edit_prize:"):
            sid = int(parts[2])
            context.user_data["admin_awaiting_input"] = {"type": "tournament_prize", "season_id": sid}
            await query.edit_message_text("💵 متن یا مبلغ جایزه را ارسال کنید:", reply_markup=_kb([[InlineKeyboardButton("❌ انصراف", callback_data="admin:tournament")]]), parse_mode="HTML")
            return True
        if data.startswith("admin:tour_edit_duration:"):
            sid = int(parts[2])
            context.user_data["admin_awaiting_input"] = {"type": "tournament_duration", "season_id": sid}
            await query.edit_message_text("⏱ مدت فصل را به تعداد روز، بین ۱ تا ۳۰، ارسال کنید:", reply_markup=_kb([[InlineKeyboardButton("❌ انصراف", callback_data="admin:tournament")]]), parse_mode="HTML")
            return True
        if data.startswith("admin:tour_start:"):
            sid = int(parts[2])
            await query.edit_message_text(
                "⚠️ <b>تأیید فعال‌سازی فصل</b>\n\nبا فعال‌سازی، snapshot اولیه‌ی بازیکنان ثبت و امتیازدهی شروع می‌شود. ادامه می‌دهید؟",
                reply_markup=_kb([
                    [InlineKeyboardButton("▶️ بله، فصل را فعال کن", callback_data=f"admin:tour_start_confirm:{sid}")],
                    [InlineKeyboardButton("❌ انصراف", callback_data="admin:tournament")],
                ]), parse_mode="HTML",
            )
            return True
        if data.startswith("admin:tour_start_confirm:"):
            sid = int(parts[2])
            ok, message, started_season = tournament.start_season(sid)
            if ok and started_season:
                for participant in tournament.get_participants(sid):
                    player_id = participant.get("player_id")
                    if not player_id:
                        continue
                    try:
                        await context.bot.send_message(
                            chat_id=player_id,
                            text=(
                                f"🏆 <b>تورنومنت شروع شد!</b>\n\n"
                                f"فصل: <b>{html.escape(started_season['title'])}</b>\n"
                                f"⏳ پایان: <code>{started_season.get('ends_at')}</code>\n"
                                f"🎁 جایزه: {html.escape(started_season.get('prize_text') or 'طبق اطلاعیه مدیریت')}\n\n"
                                "از منوی اصلی وارد بخش 🏆 تورنومنت فصل شوید."
                            ),
                            parse_mode="HTML",
                        )
                    except Exception:
                        pass
            await tournament_admin_menu(query, context, message)
            return True
        if data.startswith("admin:tour_pause:"):
            sid = int(parts[2])
            ok, message, _season = tournament.pause_season(sid)
            await tournament_admin_menu(query, context, message)
            return True
        if data.startswith("admin:tour_resume:"):
            sid = int(parts[2])
            ok, message, _season = tournament.resume_season(sid)
            await tournament_admin_menu(query, context, message)
            return True
        if data.startswith("admin:tour_end:"):
            sid = int(parts[2])
            await query.edit_message_text(
                "⚠️ <b>پایان فصل و قفل‌شدن جدول</b>\n\nبعد از پایان، امتیازهای بازیکنان تغییر نمی‌کند. مطمئن هستید؟",
                reply_markup=_kb([
                    [InlineKeyboardButton("🏁 بله، فصل را تمام کن", callback_data=f"admin:tour_end_confirm:{sid}")],
                    [InlineKeyboardButton("❌ انصراف", callback_data="admin:tournament")],
                ]), parse_mode="HTML",
            )
            return True
        if data.startswith("admin:tour_end_confirm:"):
            sid = int(parts[2])
            ok, message, ended_season = tournament.end_season(sid)
            if ok and ended_season:
                winners = tournament.get_rankings(sid, limit=3, offset=0)
                winner_lines = "\n".join(
                    f"{row['rank']}. {row.get('country_flag', '🏳️')} {html.escape(row.get('country_name', 'کشور'))} — {_fmt(row.get('score'))}"
                    for row in winners
                ) or "جدول خالی است."
                final_message = (
                    f"🏁 <b>تورنومنت {html.escape(ended_season['title'])} به پایان رسید!</b>\n\n"
                    f"🏆 <b>رتبه‌های برتر:</b>\n{winner_lines}\n\n"
                    f"🎁 جایزه: {html.escape(ended_season.get('prize_text') or 'طبق اطلاعیه مدیریت')}\n"
                    "نتیجه پرداخت جوایز توسط مدیریت اعلام خواهد شد."
                )
                for participant in tournament.get_participants(sid):
                    player_id = participant.get("player_id")
                    if player_id:
                        try:
                            await context.bot.send_message(chat_id=player_id, text=final_message, parse_mode="HTML")
                        except Exception:
                            pass
            await tournament_admin_menu(query, context, message)
            return True
        if data.startswith("admin:tour_delete:"):
            sid = int(parts[2])
            ok, message = tournament.delete_draft(sid)
            await tournament_admin_menu(query, context, message)
            return True
        if data.startswith("admin:tour_refresh:"):
            sid = int(parts[2])
            count = tournament.refresh_season(sid, force=True)
            await tournament_admin_menu(query, context, f"امتیاز {count} شرکت‌کننده بروزرسانی شد.")
            return True
        if data.startswith("admin:tour_rank:"):
            sid, page = int(parts[2]), int(parts[3]) if len(parts) > 3 else 0
            await _rank_page(query, sid, page)
            return True
        if data.startswith("admin:tour_participants:"):
            sid, page = int(parts[2]), int(parts[3]) if len(parts) > 3 else 0
            await _participants_page(query, sid, page)
            return True
        if data.startswith("admin:tour_event_country:"):
            sid = int(parts[2])
            await _event_country_prompt(query, context, sid)
            return True
        if data.startswith("admin:tour_event:"):
            sid, cid = int(parts[2]), int(parts[3])
            context.user_data["admin_awaiting_input"] = {"type": "tournament_points", "season_id": sid, "country_id": cid}
            await query.edit_message_text(
                "➕ مقدار امتیاز و توضیح را در یک پیام بفرستید.\n\nفرمت: <code>50 توضیح رویداد</code>\nبرای جریمه از عدد منفی استفاده کنید.",
                reply_markup=_kb([[InlineKeyboardButton("❌ انصراف", callback_data="admin:tournament")]]), parse_mode="HTML",
            )
            return True
        if data.startswith("admin:tour_disqualify:"):
            sid, cid = int(parts[2]), int(parts[3])
            await query.edit_message_text(
                "⚠️ آیا این شرکت‌کننده از فصل حذف شود؟",
                reply_markup=_kb([
                    [InlineKeyboardButton("🚫 بله، حذف شود", callback_data=f"admin:tour_disqualify_confirm:{sid}:{cid}")],
                    [InlineKeyboardButton("❌ انصراف", callback_data=f"admin:tour_participants:{sid}:0")],
                ]), parse_mode="HTML",
            )
            return True
        if data.startswith("admin:tour_disqualify_confirm:"):
            sid, cid = int(parts[2]), int(parts[3])
            ok, message = tournament.disqualify_player(sid, cid)
            await _participants_page(query, sid, 0)
            return True
        if data.startswith("admin:tour_events:"):
            sid = int(parts[2])
            events = tournament.get_event_history(sid, limit=30)
            lines = [f"📋 <b>سوابق رویدادهای فصل #{sid}</b>", "━━━━━━━━━━━━━━━━━━"]
            lines.extend(
                f"• {e.get('country_flag', '🏳️')} {html.escape(e.get('country_name', 'کشور'))}: <b>{_fmt(e.get('points'))}</b> — {html.escape(e.get('description') or e.get('event_type', 'رویداد'))}"
                for e in events
            )
            await query.edit_message_text("\n".join(lines), reply_markup=_kb([[InlineKeyboardButton("🔙 مدیریت تورنومنت", callback_data="admin:tournament")]]), parse_mode="HTML")
            return True
    except (IndexError, TypeError, ValueError):
        await query.answer("اطلاعات دکمه نامعتبر است.", show_alert=True)
        return True
    return False


async def handle_tournament_admin_input(update, context, input_type: str, text: str, input_state: dict) -> bool:
    """پردازش ورودی‌های تایپی پنل تورنومنت؛ خروجی یعنی ورودی متعلق به ما بود."""
    if input_type not in {"tournament_title", "tournament_prize", "tournament_duration", "tournament_points"}:
        return False
    sid = int(input_state["season_id"])
    if input_type == "tournament_title":
        ok, message, _ = tournament.update_draft(sid, title=text)
    elif input_type == "tournament_prize":
        ok, message, _ = tournament.update_draft(sid, prize_text=text)
    elif input_type == "tournament_duration":
        match = re.fullmatch(r"\s*([0-9۰-۹]+)\s*", text)
        if not match:
            ok, message = False, "مدت فصل باید یک عدد بین ۱ تا ۳۰ باشد."
        else:
            raw = match.group(1).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
            ok, message, _ = tournament.update_draft(sid, duration_days=int(raw))
    else:
        match = re.match(r"^\s*(-?[0-9۰-۹]+)(?:\s+(.+))?\s*$", text)
        if not match:
            ok, message = False, "فرمت صحیح: عدد امتیاز و سپس توضیح؛ مثل <code>50 حمله موفق</code>."
        else:
            points = match.group(1).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
            description = match.group(2) or "رویداد ثبت‌شده توسط مدیریت"
            ok, message = tournament.add_manual_event(
                sid, int(input_state["country_id"]), update.effective_user.id, float(points), description
            )
            if ok:
                tournament.refresh_player(sid, country_id=int(input_state["country_id"]), force=True)
    context.user_data["admin_awaiting_input"] = None
    await update.message.reply_text(
        f"{'✅' if ok else '❌'} {message}",
        reply_markup=_kb([[InlineKeyboardButton("🏆 مدیریت تورنومنت", callback_data="admin:tournament")]]),
        parse_mode="HTML",
    )
    return True
