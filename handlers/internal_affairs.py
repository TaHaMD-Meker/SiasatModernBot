# -*- coding: utf-8 -*-
"""رابط بازیکن برای سیاست داخلی: جمعیت، مالیات، ناآرامی و بحران‌ها."""

from __future__ import annotations

import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

import database as db
import internal_affairs as ia
from utils import format_money, format_number


def _kb(rows):
    return InlineKeyboardMarkup(rows)


def _back_row():
    return [InlineKeyboardButton("🔙 بازگشت", callback_data="dom:menu")]


async def _require_country(update: Update):
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        target = update.callback_query.message if update.callback_query else update.message
        await target.reply_text("شما هنوز کشوری ندارید. ابتدا با /start کشور خود را انتخاب کنید.")
        return None
    return country


def _disabled_text() -> str:
    return (
        "🏛 <b>سیاست داخلی</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "این بخش هنوز توسط مدیریت فعال نشده است.\n"
        "به‌زودی جمعیت، مالیات و بحران‌های داخلی کشور شما زنده خواهند شد."
    )


def _trend_arrow(delta: int) -> str:
    if delta > 0:
        return "🔼"
    if delta < 0:
        return "🔽"
    return "➖"


# ─────────────────────────────────────────────────────────────────────────────
# منوی اصلی
# ─────────────────────────────────────────────────────────────────────────────
def _menu_keyboard(active_crises: int):
    crisis_label = f"🚨 بحران‌های فعال ({active_crises})" if active_crises else "🚨 بحران‌های فعال"
    return _kb([
        [InlineKeyboardButton("👥 گزارش جمعیت", callback_data="dom:population")],
        [InlineKeyboardButton("💰 سیاست مالیاتی", callback_data="dom:tax")],
        [InlineKeyboardButton("📉 رضایت و ناآرامی", callback_data="dom:unrest")],
        [InlineKeyboardButton(crisis_label, callback_data="dom:crises")],
        [InlineKeyboardButton("🛠️ اقدامات اضطراری", callback_data="dom:actions")],
        [InlineKeyboardButton("📈 روند تغییرات کشور", callback_data="dom:trend")],
        [InlineKeyboardButton("📜 تاریخچه اتفاقات", callback_data="dom:history")],
        [InlineKeyboardButton("🔙 بازگشت به کشور", callback_data="country:back_profile")],
    ])


def _menu_text(country: dict, state: dict, active: list[dict]) -> str:
    approval = int(country.get("approval_rating") or 0)
    stage = int(state.get("unrest_stage") or 0)
    lines = [
        "🏛 <b>سیاست داخلی و وضعیت کشور</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"{country.get('flag', '🏳️')} <b>{html.escape(country.get('name', 'کشور'))}</b>",
        f"👥 جمعیت: <b>{format_number(country.get('population'))}</b>",
        f"😊 رضایت عمومی: <b>{approval}٪</b>",
        f"💰 سیاست مالیاتی: <b>{ia.tax_policy_label(state.get('tax_policy'))}</b>",
        f"💵 درآمد مالیاتی روزانه: <b>{format_money(country.get('tax_income'))}</b>",
        f"⚖️ وضعیت داخلی: <b>{ia.stage_label(stage)}</b> ({int(float(state.get('unrest') or 0))}/100)",
    ]
    if state.get("collapse_risk"):
        lines.append("\n⚫️ <b>هشدار: کشور شما در آستانه‌ی بحران حکومتی است.</b>")
    if active:
        lines.append(f"\n🚨 بحران‌های فعال: <b>{len(active)}</b>")
        for crisis in active[:3]:
            spec = ia.CRISIS_CATALOG.get(crisis["crisis_key"], {})
            lines.append(
                f"• {spec.get('label', crisis['crisis_key'])} — "
                f"{ia.SEVERITY_LABELS.get(crisis['severity'], '')} / {_stage_fa(crisis['stage'])}"
            )
    return "\n".join(lines)


def _stage_fa(stage: str) -> str:
    return {"warning": "هشدار", "impact": "در جریان", "recovery": "بازسازی", "ended": "پایان‌یافته"}.get(stage, stage)


async def domestic_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    country = await _require_country(update)
    if not country:
        return
    query = update.callback_query

    if not ia.is_enabled():
        markup = _kb([[InlineKeyboardButton("🔙 بازگشت به کشور", callback_data="country:back_profile")]])
        if query:
            await query.edit_message_text(_disabled_text(), reply_markup=markup, parse_mode="HTML")
        else:
            await update.message.reply_text(_disabled_text(), reply_markup=markup, parse_mode="HTML")
        return

    state = ia.get_state(country["id"]) or {}
    active = ia.get_active_crises(country["id"])
    text = _menu_text(country, state, active)
    markup = _menu_keyboard(len(active))
    if query:
        await query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="HTML")


# ─────────────────────────────────────────────────────────────────────────────
# صفحه‌ها
# ─────────────────────────────────────────────────────────────────────────────
async def _population_page(query, country: dict, state: dict):
    history = ia.get_history(country["id"], days=7)
    today = history[0] if history else None
    lines = [
        "👥 <b>گزارش جمعیت</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"جمعیت فعلی: <b>{format_number(country.get('population'))}</b>",
    ]
    if today:
        delta = int(today.get("population_delta") or 0)
        lines.append(f"تغییر آخرین چرخه: <b>{_trend_arrow(delta)} {format_number(abs(delta))}</b>")
        lines.append(f"روند: <b>{html.escape(today.get('notes') or '—')}</b>")
    else:
        lines.append("هنوز چرخه‌ی روزانه‌ای برای کشور شما ثبت نشده است.")

    if len(history) > 1:
        lines.append("\n📊 <b>روند هفت روز اخیر</b>")
        for row in history[:7]:
            delta = int(row.get("population_delta") or 0)
            lines.append(f"• {row['log_date']}: {_trend_arrow(delta)} {format_number(abs(delta))} نفر")

    lines.append("\n<b>عوامل مؤثر:</b>")
    lines.append("• رضایت عمومی، تأمین غلات و برق، سیاست مالیاتی")
    lines.append("• ناآرامی داخلی، بحران‌های فعال و تلفات غیرنظامی")
    lines.append(f"\nℹ️ جمعیت هرگز زیر {format_number(ia.POPULATION_FLOOR)} نفر نمی‌رود.")
    await query.edit_message_text("\n".join(lines), reply_markup=_kb([_back_row()]), parse_mode="HTML")


async def _tax_page(query, country: dict, state: dict):
    policy = state.get("tax_policy") or ia.DEFAULT_TAX_POLICY
    approval = int(country.get("approval_rating") or 0)
    compliance = ia.compliance_for(approval)
    locked = bool(int(state.get("policy_locked") or 0))
    lines = [
        "💰 <b>سیاست مالیاتی</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"سیاست فعلی: <b>{ia.tax_policy_label(policy)}</b>",
        f"💵 <b>درآمد مالیاتی فعلی (هم‌اکنون در حال پرداخت): {format_money(country.get('tax_income'))}</b>",
        "",
        f"👥 جمعیت مشمول: {format_number(country.get('population'))}",
        f"😊 رضایت عمومی: {approval}٪",
        f"🧾 نرخ تمکین مالیاتی: {int(compliance * 100)}٪",
        f"🕳 فرار مالیاتی برآوردی: {max(0, 100 - int(compliance * 100))}٪",
        f"⚖️ اثر ناآرامی: {int(ia.UNREST_TAX_MULT.get(int(state.get('unrest_stage') or 0), 1.0) * 100)}٪",
        "",
        "📌 هرچه رضایت عمومی پایین‌تر بیاید، مردم کمتر مالیات می‌پردازند.",
        "ممکن است نرخ را بالا ببرید اما وصولی واقعی کمتر شود.",
        "",
        "<b>اگر سیاست را عوض کنید، درآمد شما این می‌شود:</b>",
    ]
    rows = []
    for key, spec in ia.TAX_POLICIES.items():
        projected = ia.project_tax_income(country, state, key)
        if key == policy:
            lines.append(f"• {spec['label']}: {format_money(projected)} ✅ <i>(فعال)</i>")
            continue
        current = int(country.get("tax_income") or 0)
        diff = projected - current
        sign = "🔼" if diff > 0 else ("🔽" if diff < 0 else "➖")
        lines.append(f"• {spec['label']}: {format_money(projected)} {sign}")
        if not locked:
            rows.append([InlineKeyboardButton(
                f"تغییر به {spec['label']}", callback_data=f"dom:setpolicy:{key}"
            )])

    if locked:
        lines.append(
            "\n🔒 <b>شما امروز یک‌بار سیاست را تغییر داده‌اید.</b>\n"
            "تغییر بعدی از چرخه‌ی روزانه‌ی بعد ممکن است."
        )
    else:
        lines.append(
            "\n⚡ تغییر سیاست <b>بلافاصله</b> روی درآمد مالیاتی اعمال می‌شود.\n"
            "⚠️ اما هزینه‌ی آن (رضایت و ناآرامی) در چرخه‌ی روزانه‌ی بعد کسر می‌شود، "
            "و تا آن موقع نمی‌توانید دوباره سیاست را عوض کنید."
        )
    rows.append(_back_row())
    await query.edit_message_text("\n".join(lines), reply_markup=_kb(rows), parse_mode="HTML")



async def _unrest_page(query, country: dict, state: dict):
    stage = int(state.get("unrest_stage") or 0)
    unrest = float(state.get("unrest") or 0)
    filled = int(round(unrest / 10))
    bar = "█" * filled + "░" * (10 - filled)
    lines = [
        "📉 <b>رضایت و ناآرامی</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"رضایت عمومی: <b>{int(country.get('approval_rating') or 0)}٪</b>",
        f"شاخص ناآرامی: <code>[{bar}]</code> <b>{int(unrest)}/100</b>",
        f"مرحله: <b>{ia.stage_label(stage)}</b>",
        f"<i>{ia.UNREST_STAGES.get(stage, {}).get('desc', '')}</i>",
        "",
        "<b>مراحل ناآرامی:</b>",
    ]
    for level in range(5):
        marker = "◀️" if level == stage else "　"
        lines.append(f"{marker} {ia.UNREST_STAGES[level]['label']}")
    if state.get("collapse_risk"):
        lines.append("\n⚫️ <b>کشور شما چند روز است در بحران حکومتی قرار دارد. کنترل اوضاع فوری است.</b>")
    lines.append("\n<b>راه‌های کاهش ناآرامی:</b>")
    lines.append("• کاهش مالیات • تأمین غلات و برق • بازسازی زیرساخت")
    lines.append("• بیانیه رسمی • کمک اضطراری • (در نهایت) نیروهای امنیتی")
    await query.edit_message_text("\n".join(lines), reply_markup=_kb([
        [InlineKeyboardButton("💰 تغییر سیاست مالیاتی", callback_data="dom:tax")],
        [InlineKeyboardButton("🛠️ اقدامات اضطراری", callback_data="dom:actions")],
        _back_row(),
    ]), parse_mode="HTML")


async def _crises_page(query, country: dict):
    active = ia.get_active_crises(country["id"])
    if not active:
        await query.edit_message_text(
            "🚨 <b>بحران‌های فعال</b>\n━━━━━━━━━━━━━━━━━━\nهم‌اکنون هیچ بحرانی در کشور شما فعال نیست. 🟢",
            reply_markup=_kb([_back_row()]), parse_mode="HTML",
        )
        return
    lines = ["🚨 <b>بحران‌های فعال</b>", "━━━━━━━━━━━━━━━━━━"]
    rows = []
    for crisis in active:
        spec = ia.CRISIS_CATALOG.get(crisis["crisis_key"], {})
        remaining = "—"
        ends = ia._parse_dt(crisis.get("ends_at"))
        if ends:
            hours = max(0, int((ends - ia._now()).total_seconds() // 3600))
            remaining = f"{hours} ساعت"
        lines.append(
            f"\n{spec.get('label', crisis['crisis_key'])}\n"
            f"• شدت: <b>{ia.SEVERITY_LABELS.get(crisis['severity'], '')}</b>\n"
            f"• مرحله: <b>{_stage_fa(crisis['stage'])}</b>\n"
            f"• زمان باقی‌مانده: <b>{remaining}</b>\n"
            f"• کاهش خسارت با اقدامات شما: <b>{int(float(crisis.get('mitigation') or 0) * 100)}٪</b>"
        )
        rows.append([InlineKeyboardButton(
            f"🛠️ واکنش به {spec.get('label', '')}", callback_data=f"dom:crisis:{crisis['id']}"
        )])
    rows.append(_back_row())
    await query.edit_message_text("\n".join(lines), reply_markup=_kb(rows), parse_mode="HTML")


async def _crisis_detail(query, country: dict, crisis_id: int, notice: str = ""):
    crisis = ia.get_crisis(crisis_id)
    if not crisis or crisis["country_id"] != country["id"]:
        await query.answer("بحران یافت نشد.", show_alert=True)
        return
    spec = ia.CRISIS_CATALOG.get(crisis["crisis_key"], {})
    done = {action["action_key"] for action in ia.get_crisis_actions(crisis_id)}
    treasury = int(country.get("treasury") or 0)

    lines = [
        (f"✅ {html.escape(notice)}\n" if notice else "") + f"{spec.get('label', '')} — <b>{ia.SEVERITY_LABELS.get(crisis['severity'], '')}</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"مرحله: <b>{_stage_fa(crisis['stage'])}</b>",
        f"کاهش خسارت فعلی: <b>{int(float(crisis.get('mitigation') or 0) * 100)}٪</b>",
    ]
    damage = ia._json_load(crisis.get("damage_json"), {})
    if damage:
        lines.append("\n<b>خسارت ثبت‌شده:</b>")
        if damage.get("population"):
            lines.append(f"• جمعیت: {format_number(damage['population'])} نفر")
        if damage.get("treasury"):
            lines.append(f"• خزانه: {format_money(damage['treasury'])}")
        if damage.get("grain"):
            lines.append(f"• غلات: {format_number(damage['grain'])}")
        if damage.get("electricity"):
            lines.append(f"• برق: {format_number(damage['electricity'])} واحد")
        if damage.get("daily_income"):
            lines.append(f"• درآمد روزانه: {format_money(damage['daily_income'])}")
    elif crisis["stage"] == "warning":
        lines.append(f"\n<i>{spec.get('warning', '')}</i>")
        lines.append("\n⏳ هنوز فرصت آماده‌سازی دارید.")

    lines.append("\n<b>اقدامات در دسترس:</b>")
    rows = []
    for action_key in ia.available_actions(crisis):
        action = ia.CRISIS_ACTIONS[action_key]
        cost = max(int(action.get("min_cost", 0)), int(max(0, treasury) * float(action.get("cost_pct", 0))))
        if action_key in done:
            lines.append(f"• {action['label']} — ✅ انجام شد")
            continue
        cost_text = "رایگان" if cost == 0 else format_money(cost)
        lines.append(f"• {action['label']} — {cost_text}\n  <i>{action['desc']}</i>")
        rows.append([InlineKeyboardButton(
            f"{action['label']} ({cost_text})", callback_data=f"dom:act:{crisis_id}:{action_key}"
        )])
    rows.append([InlineKeyboardButton("🔙 بحران‌ها", callback_data="dom:crises")])
    await query.edit_message_text("\n".join(lines), reply_markup=_kb(rows), parse_mode="HTML")


async def _actions_page(query, country: dict):
    active = ia.get_active_crises(country["id"])
    if not active:
        await query.edit_message_text(
            "🛠️ <b>اقدامات اضطراری</b>\n━━━━━━━━━━━━━━━━━━\n"
            "اقدامات اضطراری فقط هنگام وجود بحران فعال در دسترس هستند.\n"
            "هم‌اکنون بحرانی در کشور شما فعال نیست. 🟢",
            reply_markup=_kb([_back_row()]), parse_mode="HTML",
        )
        return
    await _crises_page(query, country)


async def _trend_page(query, country: dict):
    history = ia.get_history(country["id"], days=10)
    if not history:
        await query.edit_message_text(
            "📈 <b>روند تغییرات کشور</b>\n━━━━━━━━━━━━━━━━━━\nهنوز داده‌ای ثبت نشده است.",
            reply_markup=_kb([_back_row()]), parse_mode="HTML",
        )
        return
    lines = ["📈 <b>روند تغییرات کشور</b>", "━━━━━━━━━━━━━━━━━━"]
    for row in history:
        delta = int(row.get("population_delta") or 0)
        lines.append(
            f"\n<b>{row['log_date']}</b>\n"
            f"• جمعیت: {_trend_arrow(delta)} {format_number(abs(delta))}\n"
            f"• مالیات: {format_money(row.get('tax_after'))}\n"
            f"• رضایت: {int(row.get('approval') or 0)}٪ | ناآرامی: {int(float(row.get('unrest') or 0))}"
        )
    await query.edit_message_text("\n".join(lines), reply_markup=_kb([_back_row()]), parse_mode="HTML")


async def _history_page(query, country: dict):
    crises = ia.get_crisis_history(country["id"], limit=12)
    if not crises:
        await query.edit_message_text(
            "📜 <b>تاریخچه اتفاقات</b>\n━━━━━━━━━━━━━━━━━━\nتاکنون بحرانی برای کشور شما ثبت نشده است.",
            reply_markup=_kb([_back_row()]), parse_mode="HTML",
        )
        return
    lines = ["📜 <b>تاریخچه اتفاقات</b>", "━━━━━━━━━━━━━━━━━━"]
    for crisis in crises:
        spec = ia.CRISIS_CATALOG.get(crisis["crisis_key"], {})
        mitigation = int(float(crisis.get("mitigation") or 0) * 100)
        verdict = "✅ مدیریت‌شده" if mitigation >= 25 else ("⚠️ واکنش ناکافی" if crisis["stage"] == "ended" else "🔄 در جریان")
        lines.append(
            f"• {spec.get('label', crisis['crisis_key'])} "
            f"({ia.SEVERITY_LABELS.get(crisis['severity'], '')}) — {verdict} — {mitigation}٪"
        )
    await query.edit_message_text("\n".join(lines), reply_markup=_kb([_back_row()]), parse_mode="HTML")


# ─────────────────────────────────────────────────────────────────────────────
# روتر
# ─────────────────────────────────────────────────────────────────────────────
async def domestic_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    country = await _require_country(update)
    if not country:
        return
    await query.answer()
    data = query.data

    if not ia.is_enabled():
        await query.edit_message_text(
            _disabled_text(),
            reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به کشور", callback_data="country:back_profile")]]),
            parse_mode="HTML",
        )
        return

    state = ia.get_state(country["id"]) or {}

    if data == "dom:menu":
        await domestic_menu(update, context)
    elif data == "dom:population":
        await _population_page(query, country, state)
    elif data == "dom:tax":
        await _tax_page(query, country, state)
    elif data == "dom:unrest":
        await _unrest_page(query, country, state)
    elif data == "dom:crises":
        await _crises_page(query, country)
    elif data == "dom:actions":
        await _actions_page(query, country)
    elif data == "dom:trend":
        await _trend_page(query, country)
    elif data == "dom:history":
        await _history_page(query, country)
    elif data.startswith("dom:setpolicy:"):
        policy = data.split(":", 2)[2]
        ok, message = ia.set_tax_policy(country["id"], policy, actor_id=query.from_user.id)
        await query.answer(message, show_alert=not ok)
        await _tax_page(query, db.get_country_by_id(country["id"]) or country, ia.get_state(country["id"]) or state)
    elif data.startswith("dom:crisis:"):
        await _crisis_detail(query, country, int(data.split(":")[2]))
    elif data.startswith("dom:act:"):
        _, _, crisis_id, action_key = data.split(":", 3)
        ok, message, _info = ia.respond_to_crisis(int(crisis_id), action_key, actor_id=query.from_user.id)
        await query.answer(message, show_alert=not ok)
        fresh = db.get_country_by_id(country["id"]) or country
        await _crisis_detail(query, fresh, int(crisis_id), notice=message if ok else "")


def get_domestic_handlers():
    return [
        CommandHandler(["domestic", "internal", "siasat_dakheli"], domestic_menu),
        CallbackQueryHandler(domestic_callback_handler, pattern=r"^dom:"),
    ]
