# -*- coding: utf-8 -*-
"""رابط بازیکن برای صف انتظار کشور، بازپس‌گیری و پذیرش پیشنهاد."""

from __future__ import annotations

import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

import country_queue as cq
import database as db


def _kb(rows):
    return InlineKeyboardMarkup(rows)


async def queue_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """وضعیت صف و کشور قرنطینه‌شده‌ی بازیکن."""
    user = update.effective_user
    player_id = user.id
    send = update.message.reply_text if update.message else update.callback_query.edit_message_text

    country = db.get_country_by_player(player_id)
    if country:
        await send(
            f"شما هم‌اکنون رهبر {country.get('flag', '')} <b>{html.escape(country.get('name', ''))}</b> هستید.",
            parse_mode="HTML",
        )
        return

    # کشور در قرنطینه؟
    reclaimable = _reclaimable_country(player_id)
    if reclaimable:
        remaining = cq._parse(reclaimable.get("quarantine_until"))
        hours = max(0, int((remaining - cq._now()).total_seconds() // 3600)) if remaining else 0
        await send(
            f"⏳ <b>کشور شما در قرنطینه است</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{reclaimable.get('flag', '')} <b>{html.escape(reclaimable.get('name', ''))}</b>\n\n"
            f"تمام تجهیزات، ساختمان‌ها و ذخایر کشور دست‌نخورده باقی مانده‌اند.\n"
            f"⏰ مهلت بازپس‌گیری: <b>{hours} ساعت</b>\n\n"
            f"<i>بعد از پایان مهلت، کشور به نفر اول صف انتظار واگذار می‌شود.</i>",
            reply_markup=_kb([[InlineKeyboardButton("♻️ بازپس‌گیری کشورم", callback_data="q:reclaim")]]),
            parse_mode="HTML",
        )
        return

    entry = cq.get_queue_entry(player_id)
    stats = cq.queue_stats()

    if entry and entry["status"] == "offered":
        offered = db.get_country_by_id(entry["offered_country_id"])
        expires = cq._parse(entry.get("offer_expires_at"))
        hours = max(0, int((expires - cq._now()).total_seconds() // 3600)) if expires else 0
        await send(
            f"🎉 <b>نوبت شما رسید!</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"کشور پیشنهادی: {offered.get('flag', '')} <b>{html.escape(offered.get('name', ''))}</b>\n"
            f"⏰ مهلت پاسخ: <b>{hours} ساعت</b>\n\n"
            f"<i>اگر رد کنید، به صف برمی‌گردید و کشور به نفر بعدی پیشنهاد می‌شود.</i>",
            reply_markup=_kb([
                [InlineKeyboardButton("✅ قبول می‌کنم", callback_data="q:accept")],
                [InlineKeyboardButton("❌ رد می‌کنم", callback_data="q:decline")],
            ]),
            parse_mode="HTML",
        )
        return

    if entry and entry["status"] == "waiting":
        position = cq.queue_position(player_id)
        await send(
            f"⏳ <b>شما در صف انتظار هستید</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"جایگاه شما: <b>نفر {position}</b>\n"
            f"👥 کل صف: {stats['waiting']} نفر\n"
            f"🌍 کشور آزاد: {stats['free_countries']}\n"
            f"⏳ در قرنطینه: {stats['quarantined']}\n\n"
            f"<i>به‌محض آزاد شدن کشوری، به شما اطلاع داده می‌شود و "
            f"{cq.OFFER_HOURS} ساعت برای پاسخ فرصت دارید.</i>",
            reply_markup=_kb([[InlineKeyboardButton("🚪 خروج از صف", callback_data="q:leave")]]),
            parse_mode="HTML",
        )
        return

    await send(
        f"🌍 <b>صف انتظار کشور</b>\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"👥 در صف: {stats['waiting']} نفر\n"
        f"🌍 کشور آزاد: {stats['free_countries']}\n"
        f"⏳ در قرنطینه: {stats['quarantined']}\n\n"
        f"<i>با پیوستن به صف، به‌محض آزاد شدن کشوری به شما پیشنهاد می‌شود.</i>",
        reply_markup=_kb([[InlineKeyboardButton("➕ پیوستن به صف", callback_data="q:join")]]),
        parse_mode="HTML",
    )


def _reclaimable_country(player_id: int):
    conn = db.get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM countries WHERE previous_player_id = ? AND player_id = 0"
            " AND quarantine_until IS NOT NULL",
            (player_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


async def queue_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    data = query.data

    if data == "q:join":
        ok, message, _entry = cq.join_queue(
            user.id, first_name=user.first_name or "", username=user.username or ""
        )
        await query.answer(message, show_alert=not ok)
        if ok:
            # ضد «کشور خالی می‌ماند»: موتور صف همین حالا اجرا شود تا اگر کشور
            # آزادی موجود است فوراً به همین بازیکن پیشنهاد شود، نه تا جاب ۱۰دقیقه‌ای.
            try:
                cq.process_queue()
            except Exception:
                pass
            await queue_status(update, context)  # رندر مجدد: پیشنهاد یا جایگاه صف
    elif data == "q:leave":
        cq.leave_queue(user.id)
        await query.answer("از صف خارج شدید.")
        try:
            cq.process_queue()  # جا باز شد؛ کشور پیشنهادی هم آزاد بماند
        except Exception:
            pass
        await queue_status(update, context)
    elif data == "q:reclaim":
        ok, message, _country = cq.reclaim_country(user.id)
        await query.answer(message, show_alert=True)
    elif data == "q:accept":
        ok, message, country = cq.accept_offer(user.id)
        await query.answer(message, show_alert=True)
        if ok and country:
            await query.edit_message_text(
                f"🎉 <b>تبریک!</b>\n\nشما رهبر {country.get('flag', '')} "
                f"<b>{html.escape(country.get('name', ''))}</b> شدید.\n\n"
                f"با /start وارد بازی شوید.",
                parse_mode="HTML",
            )
            return
    elif data == "q:decline":
        cq.decline_offer(user.id)
        try:
            cq.process_queue()  # کشور ردشده فوراً به نفر بعدی پیشنهاد شود
        except Exception:
            pass
        await query.answer("پیشنهاد رد شد و به صف بازگشتید.")

    await queue_status(update, context)


async def reclaim_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ok, message, country = cq.reclaim_country(update.effective_user.id)
    if ok and country:
        await update.message.reply_text(
            f"♻️ <b>{html.escape(message)}</b>\n\n"
            f"تمام تجهیزات، ساختمان‌ها و ذخایر شما دست‌نخورده بازگشتند.\n"
            f"فراموش نکنید روزانه حداقل ۲ بیانیه ثبت کنید.",
            parse_mode="HTML",
        )
    else:
        await update.message.reply_text(f"❌ {message}")


def get_queue_handlers():
    return [
        CommandHandler(["queue", "saf"], queue_status),
        CommandHandler("reclaim", reclaim_command),
        CallbackQueryHandler(queue_callback_handler, pattern=r"^q:"),
    ]
