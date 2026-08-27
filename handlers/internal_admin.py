# -*- coding: utf-8 -*-
"""پنل ادمین: مدیریت بحران و سیاست داخلی کشورها."""

from __future__ import annotations

import html
import re

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import database as db
import internal_affairs as ia
from utils import format_money, format_number

PAGE_SIZE = 8
_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٬،", "0123456789  ")


def _kb(rows):
    return InlineKeyboardMarkup(rows)


def _home_row():
    return [InlineKeyboardButton("🔙 مدیریت بحران", callback_data="admin:dom")]


def _parse_int(text: str):
    raw = re.sub(r"[^0-9-]", "", str(text).translate(_DIGITS))
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _stage_fa(stage: str) -> str:
    return {"warning": "هشدار", "impact": "در جریان", "recovery": "بازسازی", "ended": "پایان‌یافته"}.get(stage, stage)


def _root_text() -> str:
    enabled = ia.is_enabled()
    random_on = ia.random_crises_enabled()
    at_risk = len(ia.countries_at_risk(limit=100))
    active = len([c for c in ia.get_crisis_history(limit=100) if c["stage"] != "ended"])
    return (
        "🚨 <b>مدیریت بحران و سیاست داخلی</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"سیستم جمعیت/مالیات/بحران: <b>{'🟢 فعال' if enabled else '🔴 غیرفعال'}</b>\n"
        f"بحران‌های تصادفی: <b>{'🟢 فعال' if random_on else '🔴 غیرفعال'}</b>\n"
        f"بحران‌های در جریان: <b>{active}</b>\n"
        f"کشورهای در معرض خطر: <b>{at_risk}</b>\n\n"
        "<i>تا وقتی کلید اصلی خاموش است، هیچ تغییری روی جمعیت، مالیات یا خزانه‌ی "
        "کشورها اعمال نمی‌شود.</i>"
    )


def _root_keyboard():
    enabled = ia.is_enabled()
    random_on = ia.random_crises_enabled()
    return _kb([
        [InlineKeyboardButton(
            f"{'🛑 غیرفعال‌کردن سیستم' if enabled else '▶️ فعال‌سازی سیستم'}",
            callback_data="admin:dom_toggle_system",
        )],
        [InlineKeyboardButton(
            f"{'🛡️ توقف بحران تصادفی' if random_on else '🎲 فعال‌سازی بحران تصادفی'}",
            callback_data="admin:dom_toggle_random",
        )],
        [InlineKeyboardButton("🌍 وضعیت داخلی کشورها", callback_data="admin:dom_overview:0")],
        [InlineKeyboardButton("🚨 بحران‌های فعال", callback_data="admin:dom_active")],
        [InlineKeyboardButton("➕ ایجاد بحران دستی", callback_data="admin:dom_new:0")],
        [InlineKeyboardButton("🏁 کشورهای در معرض سقوط", callback_data="admin:dom_risk")],
        [InlineKeyboardButton("📊 تاریخچه بحران‌ها", callback_data="admin:dom_hist")],
        [InlineKeyboardButton("🔙 پنل مدیریت", callback_data="admin:menu")],
    ])


async def _show_root(query, notice: str = ""):
    text = (f"✅ {html.escape(notice)}\n\n" if notice else "") + _root_text()
    await query.edit_message_text(text, reply_markup=_root_keyboard(), parse_mode="HTML")


async def _overview(query, page: int):
    rows = ia.overview(limit=200)
    total_pages = max(1, (len(rows) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    chunk = rows[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    lines = ["🌍 <b>وضعیت داخلی کشورها</b>", "━━━━━━━━━━━━━━━━━━"]
    if not chunk:
        lines.append("کشوری ثبت نشده است.")
    for row in chunk:
        lines.append(
            f"\n{row.get('country_flag', '🏳️')} <b>{html.escape(row.get('country_name', ''))}</b>\n"
            f"👥 {format_number(row.get('population'))} | 😊 {int(row.get('approval_rating') or 0)}٪ | "
            f"💵 {format_money(row.get('tax_income'))}\n"
            f"{ia.tax_policy_label(row.get('tax_policy'))} | {ia.stage_label(row.get('unrest_stage'))} "
            f"({int(float(row.get('unrest') or 0))}) | 🚨 {row.get('active_crises', 0)}"
            + ("\n⚫️ <b>خطر سقوط</b>" if row.get("collapse_risk") else "")
        )
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"admin:dom_overview:{page - 1}"))
    nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"admin:dom_overview:{page + 1}"))
    await query.edit_message_text("\n".join(lines), reply_markup=_kb([nav, _home_row()]), parse_mode="HTML")


async def _active_crises(query):
    crises = [c for c in ia.get_crisis_history(limit=100) if c["stage"] != "ended"]
    if not crises:
        await query.edit_message_text(
            "🚨 <b>بحران‌های فعال</b>\n━━━━━━━━━━━━━━━━━━\nهیچ بحرانی در جریان نیست.",
            reply_markup=_kb([_home_row()]), parse_mode="HTML",
        )
        return
    lines = ["🚨 <b>بحران‌های فعال</b>", "━━━━━━━━━━━━━━━━━━"]
    rows = []
    for crisis in crises[:20]:
        spec = ia.CRISIS_CATALOG.get(crisis["crisis_key"], {})
        lines.append(
            f"\n#{crisis['id']} {crisis.get('country_flag', '🏳️')} "
            f"<b>{html.escape(crisis.get('country_name', ''))}</b>\n"
            f"{spec.get('label', '')} | {ia.SEVERITY_LABELS.get(crisis['severity'], '')} | "
            f"{_stage_fa(crisis['stage'])} | مهار {int(float(crisis.get('mitigation') or 0) * 100)}٪ | "
            f"منشأ: {crisis.get('origin')}"
            + ("\n⏳ <i>هنوز خسارتی اعمال نشده — منتظر چرخه‌ی روزانه</i>" if crisis['stage'] == 'warning' else "")
        )
        rows.append([InlineKeyboardButton(
            f"⚙️ #{crisis['id']} {spec.get('label', '')}", callback_data=f"admin:dom_crisis:{crisis['id']}"
        )])
    rows.append(_home_row())
    await query.edit_message_text("\n".join(lines), reply_markup=_kb(rows), parse_mode="HTML")


async def _crisis_panel(query, crisis_id: int, notice: str = ""):
    crisis = ia.get_crisis(crisis_id)
    if not crisis:
        await query.answer("بحران یافت نشد.", show_alert=True)
        return
    country = db.get_country_by_id(crisis["country_id"]) or {}
    spec = ia.CRISIS_CATALOG.get(crisis["crisis_key"], {})
    actions = ia.get_crisis_actions(crisis_id)

    lines = [
        (f"✅ {html.escape(notice)}\n" if notice else "") + f"⚙️ <b>بحران #{crisis_id}</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"کشور: {country.get('flag', '🏳️')} <b>{html.escape(country.get('name', ''))}</b>",
        f"نوع: <b>{spec.get('label', '')}</b>",
        f"شدت: <b>{ia.SEVERITY_LABELS.get(crisis['severity'], '')}</b>",
        f"مرحله: <b>{_stage_fa(crisis['stage'])}</b>",
        f"مدت: <b>{crisis['duration_days']} روز</b>",
        f"منشأ: <b>{crisis['origin']}</b>",
        f"مهار: <b>{int(float(crisis.get('mitigation') or 0) * 100)}٪</b>",
        f"تشدید خودکار تاکنون: <b>{crisis.get('escalations', 0)} بار</b>",
    ]
    if crisis["stage"] in ("warning", "impact") and float(crisis.get("mitigation") or 0) < ia.ESCALATION_MITIGATION_THRESHOLD:
        if crisis["severity"] != ia.SEVERITY_ORDER[-1]:
            lines.append("\n⚠️ <b>رسیدگی نشده — امشب یک سطح تشدید می‌شود.</b>")
        else:
            lines.append("\n⚠️ <b>رسیدگی نشده، اما در بالاترین سطح است.</b>")

    if crisis["stage"] == "warning":
        lines.append(
            "\n⏳ <b>هنوز هیچ خسارتی اعمال نشده است.</b>\n"
            "این بحران در اولین چرخه‌ی روزانه (بعد از ۰۰:۰۰ به وقت تهران) وارد "
            "مرحله‌ی وقوع می‌شود. اگر رویداد زنده اجرا می‌کنید، از دکمه‌ی "
            "«⚡ اعمال فوری خسارت» استفاده کنید."
        )
        preview = ia.estimate_damage(crisis)
        if preview:
            lines.append("\n<b>📉 برآورد خسارت در زمان وقوع:</b>")
            if preview.get("population"):
                lines.append(f"• جمعیت: {format_number(preview['population'])} نفر")
            if preview.get("treasury"):
                lines.append(f"• خزانه: {format_money(preview['treasury'])}")
            if preview.get("daily_income"):
                lines.append(f"• درآمد روزانه: {format_money(preview['daily_income'])}")
            if preview.get("grain"):
                lines.append(f"• غلات: {format_number(preview['grain'])} تن")
            if preview.get("oil_reserves"):
                lines.append(f"• نفت: {format_number(preview['oil_reserves'])} بشکه")
            if preview.get("electricity"):
                lines.append(f"• برق: {preview['electricity']} واحد")
            if preview.get("approval"):
                lines.append(f"• رضایت عمومی: {preview['approval']}")
            if preview.get("unrest"):
                lines.append(f"• ناآرامی: +{preview['unrest']}")
    else:
        damage = ia._json_load(crisis.get("damage_json"), {})
        if damage:
            lines.append("\n<b>📉 خسارت اعمال‌شده:</b>")
            if damage.get("population"):
                lines.append(f"• جمعیت: {format_number(damage['population'])} نفر")
            if damage.get("treasury"):
                lines.append(f"• خزانه: {format_money(damage['treasury'])}")
            if damage.get("daily_income"):
                lines.append(f"• درآمد روزانه: {format_money(damage['daily_income'])}")
            if damage.get("grain"):
                lines.append(f"• غلات: {format_number(damage['grain'])} تن")
            if damage.get("approval"):
                lines.append(f"• رضایت عمومی: {damage['approval']}")

    if actions:
        lines.append("\n<b>واکنش‌های بازیکن:</b>")
        for action in actions:
            label = ia.CRISIS_ACTIONS.get(action["action_key"], {}).get("label", action["action_key"])
            lines.append(f"• {label} — {format_money(action['cost'])}")

    rows = []
    if crisis["stage"] == "warning":
        rows.append([InlineKeyboardButton("⚡ اعمال فوری خسارت", callback_data=f"admin:dom_impact:{crisis_id}")])
    if crisis["stage"] != "ended":
        rows.append([
            InlineKeyboardButton("⬆️ تشدید یک سطح", callback_data=f"admin:dom_up:{crisis_id}"),
            InlineKeyboardButton("⬇️ تخفیف یک سطح", callback_data=f"admin:dom_down:{crisis_id}"),
        ])
    rows.extend([
        [InlineKeyboardButton("⚙️ تنظیم مستقیم شدت", callback_data=f"admin:dom_sev:{crisis_id}")],
        [InlineKeyboardButton("⏱️ تنظیم مدت", callback_data=f"admin:dom_dur:{crisis_id}")],
        [InlineKeyboardButton("📢 ارسال خبر بحران", callback_data=f"admin:dom_news:{crisis_id}")],
    ])
    if crisis["stage"] != "ended":
        rows.append([InlineKeyboardButton("🛑 پایان‌دادن به بحران", callback_data=f"admin:dom_end:{crisis_id}")])
    rows.append([InlineKeyboardButton("🔙 بحران‌های فعال", callback_data="admin:dom_active")])
    await query.edit_message_text("\n".join(lines), reply_markup=_kb(rows), parse_mode="HTML")



async def _country_picker(query, page: int):
    countries = [c for c in db.get_all_countries() if (c.get("player_id") or 0) > 0]
    total_pages = max(1, (len(countries) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    chunk = countries[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]
    rows = [[InlineKeyboardButton(
        f"{c.get('flag', '🏳️')} {c.get('name')}", callback_data=f"admin:dom_pick:{c['id']}"
    )] for c in chunk]
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"admin:dom_new:{page - 1}"))
    nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"admin:dom_new:{page + 1}"))
    rows.extend([nav, _home_row()])
    await query.edit_message_text(
        "➕ <b>ایجاد بحران دستی</b>\n━━━━━━━━━━━━━━━━━━\nکشور هدف را انتخاب کنید:",
        reply_markup=_kb(rows), parse_mode="HTML",
    )


async def _crisis_type_picker(query, country_id: int):
    country = db.get_country_by_id(country_id)
    if not country:
        await query.answer("کشور یافت نشد.", show_alert=True)
        return
    rows = [[InlineKeyboardButton(spec["label"], callback_data=f"admin:dom_type:{country_id}:{key}")]
            for key, spec in ia.CRISIS_CATALOG.items()]
    rows.append([InlineKeyboardButton("🔙 انتخاب کشور", callback_data="admin:dom_new:0")])
    await query.edit_message_text(
        f"➕ <b>ایجاد بحران برای {country.get('flag', '🏳️')} {html.escape(country.get('name', ''))}</b>\n"
        "━━━━━━━━━━━━━━━━━━\nنوع بحران را انتخاب کنید:",
        reply_markup=_kb(rows), parse_mode="HTML",
    )


async def _severity_picker(query, country_id: int, crisis_key: str):
    spec = ia.CRISIS_CATALOG.get(crisis_key, {})
    rows = [[InlineKeyboardButton(
        f"{ia.SEVERITY_LABELS[sev]}", callback_data=f"admin:dom_make:{country_id}:{crisis_key}:{sev}:0"
    )] for sev in ("light", "medium", "severe")]
    rows.append([InlineKeyboardButton(
        "⚡ اعمال فوری بدون هشدار (رویداد داستانی)",
        callback_data=f"admin:dom_make:{country_id}:{crisis_key}:medium:1",
    )])
    rows.append([InlineKeyboardButton("🔙 نوع بحران", callback_data=f"admin:dom_pick:{country_id}")])
    await query.edit_message_text(
        f"➕ <b>{spec.get('label', '')}</b>\n━━━━━━━━━━━━━━━━━━\n"
        "شدت بحران را انتخاب کنید.\n\n"
        "<i>حالت عادی از مرحله‌ی هشدار شروع می‌شود و بازیکن فرصت واکنش دارد. "
        "«اعمال فوری» فقط برای رویداد داستانی است.</i>",
        reply_markup=_kb(rows), parse_mode="HTML",
    )


async def _risk_page(query):
    rows = ia.countries_at_risk(limit=30)
    lines = ["🏁 <b>کشورهای در معرض سقوط</b>", "━━━━━━━━━━━━━━━━━━"]
    if not rows:
        lines.append("هیچ کشوری در وضعیت بحرانی نیست. 🟢")
    for row in rows:
        lines.append(
            f"\n{row.get('country_flag', '🏳️')} <b>{html.escape(row.get('country_name', ''))}</b>\n"
            f"😊 {int(row.get('approval_rating') or 0)}٪ | {ia.stage_label(row.get('unrest_stage'))} "
            f"({int(float(row.get('unrest') or 0))}) | روزهای بحرانی: {row.get('critical_days', 0)}"
            + ("\n⚫️ <b>خطر سقوط دولت</b>" if row.get("collapse_risk") else "")
        )
    lines.append(
        "\n\n<i>سیستم هرگز خودش کشوری را حذف یا آزاد نمی‌کند؛ تصمیم نهایی با مدیریت است.</i>"
    )
    await query.edit_message_text("\n".join(lines), reply_markup=_kb([_home_row()]), parse_mode="HTML")


async def _history_page(query):
    crises = ia.get_crisis_history(limit=25)
    lines = ["📊 <b>تاریخچه بحران‌ها</b>", "━━━━━━━━━━━━━━━━━━"]
    if not crises:
        lines.append("هنوز بحرانی ثبت نشده است.")
    for crisis in crises:
        spec = ia.CRISIS_CATALOG.get(crisis["crisis_key"], {})
        lines.append(
            f"• #{crisis['id']} {crisis.get('country_flag', '')} {html.escape(crisis.get('country_name', ''))} — "
            f"{spec.get('label', '')} | {_stage_fa(crisis['stage'])} | مهار {int(float(crisis.get('mitigation') or 0) * 100)}٪"
        )
    await query.edit_message_text("\n".join(lines), reply_markup=_kb([_home_row()]), parse_mode="HTML")


# ─────────────────────────────────────────────────────────────────────────────
# روتر callback (از handlers/admin.py صدا زده می‌شود؛ احراز ادمین آنجا انجام شده)
# ─────────────────────────────────────────────────────────────────────────────
async def _post_severity_news(context, crisis: dict, damage: dict | None = None):
    """خبر مخصوص سطح جدید بحران؛ هر سطح فقط یک‌بار منتشر می‌شود."""
    if not crisis:
        return
    flag = f"escalated_{crisis.get('severity')}"
    if ia.news_already_sent(crisis, flag):
        return
    country = db.get_country_by_id(crisis["country_id"])
    news = ia.build_news(country or {}, crisis, "escalated", damage)
    if not news:
        return
    try:
        import news_engine
        await news_engine.post_breaking_news(context.bot, news[0], news[1], "بحران داخلی")
        ia.mark_news_sent(crisis["id"], flag)
    except Exception:
        pass


async def internal_admin_callback(query, context, data: str) -> bool:
    admin_id = query.from_user.id

    if data == "admin:dom":
        await _show_root(query)
    elif data == "admin:dom_toggle_system":
        new_value = not ia.is_enabled()
        ia.set_enabled(new_value)
        db.add_log(f"admin:{admin_id}", "internal_affairs_toggle", f"enabled={new_value}")
        await _show_root(query, "سیستم سیاست داخلی فعال شد." if new_value else "سیستم سیاست داخلی غیرفعال شد.")
    elif data == "admin:dom_toggle_random":
        new_value = not ia.random_crises_enabled()
        ia.set_random_crises(new_value)
        db.add_log(f"admin:{admin_id}", "internal_random_toggle", f"enabled={new_value}")
        await _show_root(query, "بحران‌های تصادفی فعال شد." if new_value else "بحران‌های تصادفی متوقف شد.")
    elif data.startswith("admin:dom_overview:"):
        await _overview(query, int(data.split(":")[2]))
    elif data == "admin:dom_active":
        await _active_crises(query)
    elif data.startswith("admin:dom_crisis:"):
        await _crisis_panel(query, int(data.split(":")[2]))
    elif data.startswith("admin:dom_new:"):
        await _country_picker(query, int(data.split(":")[2]))
    elif data.startswith("admin:dom_pick:"):
        await _crisis_type_picker(query, int(data.split(":")[2]))
    elif data.startswith("admin:dom_type:"):
        _, _, country_id, crisis_key = data.split(":", 3)
        await _severity_picker(query, int(country_id), crisis_key)
    elif data.startswith("admin:dom_make:"):
        _, _, country_id, crisis_key, severity, instant = data.split(":", 5)
        ok, message, crisis = ia.create_crisis(
            int(country_id), crisis_key, severity=severity, origin="admin",
            admin_id=admin_id, skip_warning=instant == "1", force=instant == "1",
        )
        if not ok:
            await query.answer(message, show_alert=True)
            await _show_root(query)
        else:
            await _crisis_panel(query, crisis["id"], notice=message)
    elif data.startswith("admin:dom_impact:"):
        crisis_id = int(data.split(":")[2])
        ok, message, _applied = ia.force_impact(crisis_id, admin_id=admin_id)
        await query.answer(message, show_alert=not ok)
        await _crisis_panel(query, crisis_id, notice=message if ok else "")
    elif data.startswith("admin:dom_up:") or data.startswith("admin:dom_down:"):
        crisis_id = int(data.split(":")[2])
        direction = 1 if ":dom_up:" in data else -1
        ok, message, crisis, extra = ia.change_severity(crisis_id, direction, admin_id=admin_id)
        await query.answer(message, show_alert=not ok)
        if ok:
            await _post_severity_news(context, crisis, extra)
        await _crisis_panel(query, crisis_id, notice=message if ok else "")
    elif data.startswith("admin:dom_end:"):
        crisis_id = int(data.split(":")[2])
        ok, message = ia.end_crisis(crisis_id, admin_id=admin_id)
        await query.answer(message, show_alert=not ok)
        await _crisis_panel(query, crisis_id, notice=message if ok else "")
    elif data.startswith("admin:dom_sev:"):
        crisis_id = int(data.split(":")[2])
        rows = [[InlineKeyboardButton(
            ia.SEVERITY_LABELS[sev], callback_data=f"admin:dom_setsev:{crisis_id}:{sev}"
        )] for sev in ("light", "medium", "severe")]
        rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:dom_crisis:{crisis_id}")])
        await query.edit_message_text("⚙️ شدت جدید بحران را انتخاب کنید:", reply_markup=_kb(rows))
    elif data.startswith("admin:dom_setsev:"):
        _, _, crisis_id, severity = data.split(":", 3)
        ok, message = ia.update_crisis(int(crisis_id), severity=severity, admin_id=admin_id)
        await query.answer(message, show_alert=not ok)
        if ok:
            await _post_severity_news(context, ia.get_crisis(int(crisis_id)))
        await _crisis_panel(query, int(crisis_id), notice=message if ok else "")
    elif data.startswith("admin:dom_dur:"):
        crisis_id = int(data.split(":")[2])
        context.user_data["admin_awaiting_input"] = {"type": "dom_duration", "crisis_id": crisis_id}
        await query.edit_message_text(
            "⏱️ مدت جدید بحران را به روز بفرستید (عدد بین ۱ تا ۱۴).",
            reply_markup=_kb([[InlineKeyboardButton("🔙 انصراف", callback_data=f"admin:dom_crisis:{crisis_id}")]]),
        )
    elif data.startswith("admin:dom_news:"):
        crisis_id = int(data.split(":")[2])
        crisis = ia.get_crisis(crisis_id)
        country = db.get_country_by_id(crisis["country_id"]) if crisis else None
        sent = False
        if crisis and country:
            stage_event = {"warning": "warning", "impact": "impact", "recovery": "recovery", "ended": "ended"}.get(crisis["stage"])
            news = ia.build_news(country, crisis, stage_event)
            if news:
                try:
                    import news_engine
                    sent = await news_engine.post_breaking_news(context.bot, news[0], news[1], "بحران داخلی")
                except Exception:
                    sent = False
        await query.answer("خبر منتشر شد." if sent else "ارسال خبر ناموفق بود (کانال تنظیم نشده؟).", show_alert=True)
        await _crisis_panel(query, crisis_id)
    elif data == "admin:dom_risk":
        await _risk_page(query)
    elif data == "admin:dom_hist":
        await _history_page(query)
    else:
        return False
    return True


async def handle_internal_admin_input(update, context, input_type: str, text: str, input_state: dict) -> bool:
    """ورودی متنی ادمین برای این بخش."""
    if input_type != "dom_duration":
        return False
    crisis_id = int(input_state.get("crisis_id") or 0)
    value = _parse_int(text)
    if value is None:
        await update.message.reply_text("❌ لطفاً فقط یک عدد صحیح بفرست.")
        return True
    ok, message = ia.update_crisis(crisis_id, duration_days=value, admin_id=update.effective_user.id)
    context.user_data["admin_awaiting_input"] = None
    await update.message.reply_text(("✅ " if ok else "❌ ") + message)
    return True
