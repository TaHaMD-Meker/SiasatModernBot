# -*- coding: utf-8 -*-
"""رابط کاربری بازیکن برای تورنومنت فصلی سیاست مدرن."""

from __future__ import annotations

import datetime
import html
from zoneinfo import ZoneInfo

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

import database as db
import tournament_system as tournament

try:
    IRAN_TZ = ZoneInfo("Asia/Tehran")
except Exception:
    IRAN_TZ = datetime.timezone(datetime.timedelta(hours=3, minutes=30))


CATEGORY_LABELS = tournament.CATEGORY_LABELS


def _format_dt(raw: str | None) -> str:
    value = tournament._parse_dt(raw)
    if not value:
        return "—"
    return value.astimezone(IRAN_TZ).strftime("%Y/%m/%d - %H:%M")


def _status_label(status: str) -> str:
    return {
        tournament.DRAFT: "📝 پیش‌نویس و آماده ثبت‌نام",
        tournament.ACTIVE: "🟢 فعال",
        tournament.PAUSED: "⏸ متوقف موقت",
        tournament.ENDED: "🏁 پایان‌یافته",
    }.get(status, status or "نامشخص")


def _kb(rows):
    return InlineKeyboardMarkup(rows)


def _season_header(season: dict) -> str:
    return (
        f"🏆 <b>{html.escape(season.get('title', 'تورنومنت سیاست مدرن'))}</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"وضعیت: <b>{_status_label(season.get('status'))}</b>\n"
        f"🎁 جایزه: {html.escape(season.get('prize_text') or 'طبق اطلاعیه مدیریت')}\n"
        f"👥 شرکت‌کنندگان: <b>{tournament.get_participant_count(season['id'])}</b>\n"
    )


async def _send_or_edit(update: Update, text: str, reply_markup=None, parse_mode="HTML"):
    if update.message:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)


async def _require_country(update: Update):
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)
    if country:
        return country
    message = "❌ برای ورود به تورنومنت ابتدا باید یک کشور داشته باشید. دستور /start را ارسال کنید."
    if update.message:
        await update.message.reply_text(message, parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.answer(message, show_alert=True)
    return None


def _menu_markup(season: dict, entry: dict | None):
    rows = []
    if entry:
        rows.extend([
            [InlineKeyboardButton("📊 جدول رتبه‌بندی", callback_data="tour:rank:0")],
            [InlineKeyboardButton("🧮 جزئیات امتیاز من", callback_data="tour:detail")],
            [InlineKeyboardButton("🎯 اهداف و روش کسب امتیاز", callback_data="tour:objectives")],
        ])
    elif season.get("status") in (tournament.DRAFT, tournament.ACTIVE):
        rows.append([InlineKeyboardButton("🚀 مشاهده شرایط و ثبت‌نام", callback_data="tour:join")])

    rows.extend([
        [InlineKeyboardButton("📜 قوانین تورنومنت", callback_data="tour:rules")],
        [InlineKeyboardButton("🔄 بروزرسانی وضعیت", callback_data="tour:refresh")],
        [InlineKeyboardButton("🔙 بازگشت به کشور", callback_data="country:back_profile")],
    ])
    return _kb(rows)


async def tournament_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    country = await _require_country(update)
    if not country:
        return

    season = tournament.get_open_season() or tournament.get_latest_season()
    if not season:
        text = (
            "🏆 <b>تورنومنت سیاست مدرن</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "در حال حاضر فصل فعالی برای ثبت‌نام وجود ندارد.\n\n"
            "به‌محض ایجاد و فعال‌سازی فصل جدید، اطلاعیه رسمی برای بازیکنان ارسال خواهد شد."
        )
        await _send_or_edit(update, text, _kb([[InlineKeyboardButton("🔙 بازگشت به کشور", callback_data="country:back_profile")]]))
        return

    entry = tournament.get_player_entry(season["id"], player_id=country["player_id"])
    if entry and season["status"] == tournament.ACTIVE:
        tournament.refresh_player(season["id"], player_id=country["player_id"], force=False)
        entry = tournament.get_player_entry(season["id"], player_id=country["player_id"]) or entry

    text = _season_header(season)
    if entry:
        rank = tournament.get_rank_for_player(season["id"], country["player_id"])
        text += (
            f"\n🌍 کشور شما: {html.escape(country.get('flag', '🏳️'))} <b>{html.escape(country.get('name', 'کشور'))}</b>\n"
            f"🏅 رتبه فعلی: <b>{rank or '—'}</b>\n"
            f"⭐ امتیاز فصل: <b>{tournament.format_score(entry.get('score'))}</b>\n"
            f"🕐 آخرین محاسبه: {_format_dt(entry.get('last_snapshot_at'))}\n"
        )
        if entry.get("status") == "disqualified":
            text += f"\n🚫 وضعیت: حذف‌شده — {html.escape(entry.get('disqualified_reason') or 'نقض قوانین')}\n"
    else:
        text += (
            "\nشما هنوز در این فصل ثبت‌نام نکرده‌اید.\n"
            "امتیازدهی از لحظه ثبت‌نام/شروع فصل طبق قوانین انجام می‌شود.\n"
        )

    await _send_or_edit(update, text, _menu_markup(season, entry))


async def _join_prompt(query, season: dict, country: dict):
    text = (
        _season_header(season)
        + "\n<b>شرایط شرکت:</b>\n"
        "• هر بازیکن فقط با یک کشور در فصل شرکت می‌کند.\n"
        "• امتیازها بر اساس رشد، عملکرد و فعالیت تأییدشده ثبت می‌شوند.\n"
        "• خرید VIP یا تزریق ادمین مستقیماً امتیاز نمی‌دهد.\n"
        "• ثبت‌نام به کشور فعال فعلی شما متصل خواهد شد.\n\n"
        "آیا می‌خواهید در این فصل شرکت کنید؟"
    )
    await query.edit_message_text(
        text,
        reply_markup=_kb([
            [InlineKeyboardButton("✅ تأیید و ثبت‌نام", callback_data="tour:join_confirm")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="tour:menu")],
        ]),
        parse_mode="HTML",
    )


async def _rankings_page(query, season: dict, page: int):
    tournament.refresh_active_tournament(force=False)
    per_page = 8
    total = tournament.get_participant_count(season["id"])
    total_pages = max(1, (total + per_page - 1) // per_page)
    page = max(0, min(page, total_pages - 1))
    rows = tournament.get_rankings(season["id"], limit=per_page, offset=page * per_page)

    lines = [
        f"🏆 <b>جدول رتبه‌بندی — {html.escape(season.get('title', 'فصل'))}</b>",
        f"صفحه {page + 1} از {total_pages} | بروزرسانی امتیازها دوره‌ای است",
        "━━━━━━━━━━━━━━━━━━",
    ]
    if not rows:
        lines.append("هنوز شرکت‌کننده‌ای در جدول وجود ندارد.")
    else:
        for row in rows:
            lines.append(
                f"<b>{row['rank']}.</b> {html.escape(row.get('country_flag', '🏳️'))} "
                f"<b>{html.escape(row.get('country_name', 'کشور'))}</b> — "
                f"<code>{tournament.format_score(row.get('score'))}</code> امتیاز"
            )
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"tour:rank:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"tour:rank:{page + 1}"))
    keyboard = [nav] if nav else []
    keyboard.extend([
        [InlineKeyboardButton("🧮 جزئیات امتیاز من", callback_data="tour:detail")],
        [InlineKeyboardButton("🔙 بازگشت به تورنومنت", callback_data="tour:menu")],
    ])
    await query.edit_message_text("\n".join(lines), reply_markup=_kb(keyboard), parse_mode="HTML")


async def _details_page(query, season: dict, country: dict):
    if season["status"] == tournament.ACTIVE:
        tournament.refresh_player(season["id"], player_id=country["player_id"], force=False)
    details = tournament.get_score_details(season["id"], country["player_id"])
    if not details:
        await query.edit_message_text(
            "شما هنوز در این فصل ثبت‌نام نکرده‌اید.",
            reply_markup=_kb([[InlineKeyboardButton("🚀 ثبت‌نام", callback_data="tour:join")]]),
            parse_mode="HTML",
        )
        return

    lines = [
        f"🧮 <b>جزئیات امتیاز {html.escape(details.get('country_flag', '🏳️'))} {html.escape(details.get('country_name', 'کشور'))}</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"🏅 رتبه: <b>{details.get('rank') or '—'}</b>",
        f"⭐ مجموع امتیاز: <b>{tournament.format_score(details.get('score'))}</b>",
        "",
    ]
    for key in ("economy", "military", "diplomacy", "activity", "objectives", "stability"):
        lines.append(f"• {CATEGORY_LABELS[key]}: <b>{tournament.format_score(details.get(f'{key}_score'))}</b>")
    lines.extend([
        f"• امتیاز رویدادهای مدیریتی: <b>{tournament.format_score(details.get('manual_score'))}</b>",
        "",
        "امتیاز سقف نهایی ندارد و با عملکرد معتبر در طول فصل افزایش پیدا می‌کند.",
    ])
    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=_kb([
            [InlineKeyboardButton("📊 جدول رتبه‌بندی", callback_data="tour:rank:0")],
            [InlineKeyboardButton("🎯 روش کسب امتیاز", callback_data="tour:objectives")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="tour:menu")],
        ]),
        parse_mode="HTML",
    )


async def _rules_page(query, season: dict):
    text = (
        f"📜 <b>قوانین {html.escape(season.get('title', 'تورنومنت'))}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "• هر بازیکن فقط با یک کشور در جدول رسمی شرکت می‌کند.\n"
        "• امتیاز بر اساس رشد کشور نسبت به نقطه شروع خودش محاسبه می‌شود.\n"
        "• اقتصاد، ارتش، دیپلماسی، فعالیت، اهداف و ثبات هم‌زمان اثر دارند.\n"
        "• خرید VIP، بسته حمایتی و کمک ادمین مستقیماً امتیاز ندارد.\n"
        "• قرارداد صوری، مولتی‌اکانت، اسپم و سوءاستفاده از باگ ممنوع است.\n"
        "• امتیازهای نظامی و رول‌های ویژه فقط پس از تأیید مدیریت معتبر هستند.\n"
        "• جدول در پایان فصل قفل و نتیجه نهایی توسط مدیریت بررسی می‌شود.\n\n"
        f"🎁 <b>جایزه:</b> {html.escape(season.get('prize_text') or 'طبق اطلاعیه رسمی مدیریت')}"
    )
    await query.edit_message_text(
        text,
        reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت", callback_data="tour:menu")]]),
        parse_mode="HTML",
    )


async def _objectives_page(query):
    text = (
        "🎯 <b>روش کسب امتیاز در تورنومنت</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "💰 <b>اقتصاد و توسعه:</b> رشد خزانه و درآمد، ساخت زیرساخت و تحقیق.\n"
        "🪖 <b>قدرت نظامی:</b> رشد قدرت مؤثر، آمادگی رزمی، فرماندهی و عملکرد نبرد.\n"
        "🤝 <b>دیپلماسی:</b> قراردادهای تکمیل‌شده، اتحادهای پایدار و کمک خارجی.\n"
        "📢 <b>فعالیت:</b> بیانیه‌های روزانه، رول‌های تأییدشده و مأموریت‌ها.\n"
        "🎯 <b>اهداف استراتژیک:</b> فناوری، پایگاه‌ها و دستاوردهای فصلی.\n"
        "🛡️ <b>ثبات:</b> رضایت عمومی، منابع حیاتی، خزانه سالم و توان نگهداری ارتش.\n\n"
        "امتیاز کل سقف ندارد؛ اما اسپم و فعالیت تکراری بدون ارزش، امتیاز کامل ایجاد نمی‌کند."
    )
    await query.edit_message_text(
        text,
        reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت", callback_data="tour:menu")]]),
        parse_mode="HTML",
    )


async def tournament_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    country = await _require_country(update)
    if not country:
        return
    await query.answer()

    data = query.data or ""
    season = tournament.get_open_season() or tournament.get_latest_season()
    if data == "tour:menu":
        await tournament_menu(update, context)
        return
    if not season:
        await tournament_menu(update, context)
        return

    if data == "tour:join":
        entry = tournament.get_player_entry(season["id"], player_id=country["player_id"])
        if entry:
            await query.answer("شما قبلاً در این فصل ثبت‌نام کرده‌اید.", show_alert=True)
            return
        await _join_prompt(query, season, country)
    elif data == "tour:join_confirm":
        _ok, message, _entry = tournament.join_tournament(country["player_id"], country["id"])
        await query.answer(message, show_alert=True)
        await tournament_menu(update, context)
    elif data.startswith("tour:rank:"):
        try:
            page = int(data.split(":")[2])
        except (IndexError, ValueError):
            page = 0
        await _rankings_page(query, season, page)
    elif data == "tour:detail":
        await _details_page(query, season, country)
    elif data == "tour:rules":
        await _rules_page(query, season)
    elif data == "tour:objectives":
        await _objectives_page(query)
    elif data == "tour:refresh":
        tournament.refresh_active_tournament(force=False)
        await query.answer("وضعیت تورنومنت به‌روزرسانی شد.", show_alert=False)
        await tournament_menu(update, context)


def get_tournament_handlers():
    return [
        CommandHandler(["tournament", "tour", "competition"], tournament_menu),
        CallbackQueryHandler(tournament_callback_handler, pattern=r"^tour:"),
    ]
