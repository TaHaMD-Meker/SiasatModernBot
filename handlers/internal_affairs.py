# -*- coding: utf-8 -*-
"""رابط بازیکن برای سیاست داخلی: جمعیت، مالیات، ناآرامی و بحران‌ها."""

from __future__ import annotations

import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import CallbackQueryHandler, CommandHandler, ContextTypes

import database as db
import internal_affairs as ia
from utils import format_money, format_number, format_oil


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
def _menu_keyboard(active_crises: int, doses: int = 0):
    crisis_label = f"🚨 بحران‌های فعال ({active_crises})" if active_crises else "🚨 بحران‌های فعال"
    vaccine_label = f"💉 برنامه واکسن ({format_number(doses)} دُز)" if doses else "💉 برنامه واکسن"
    return _kb([
        [
            InlineKeyboardButton("👥 جمعیت", callback_data="dom:population"),
            InlineKeyboardButton("💰 مالیات", callback_data="dom:tax"),
        ],
        [InlineKeyboardButton("📉 رضایت و ناآرامی", callback_data="dom:unrest")],
        [InlineKeyboardButton(crisis_label, callback_data="dom:crises")],
        [InlineKeyboardButton("🛠️ اقدامات اضطراری", callback_data="dom:actions")],
        [InlineKeyboardButton(vaccine_label, callback_data="dom:vaccine")],
        [InlineKeyboardButton("🛡 آمادگی و پیشگیری", callback_data="dom:readiness")],
        [
            InlineKeyboardButton("📈 روند کشور", callback_data="dom:trend"),
            InlineKeyboardButton("📜 تاریخچه", callback_data="dom:history"),
        ],
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
        markup = _kb([
            [InlineKeyboardButton("📉 رضایت عمومی", callback_data="dom:unrest")],
            [InlineKeyboardButton("🔙 بازگشت به کشور", callback_data="country:back_profile")],
        ])
        if query:
            await query.edit_message_text(_disabled_text(), reply_markup=markup, parse_mode="HTML")
        else:
            await update.message.reply_text(_disabled_text(), reply_markup=markup, parse_mode="HTML")
        return

    state = ia.get_state(country["id"]) or {}
    active = ia.get_active_crises(country["id"])
    text = _menu_text(country, state, active)
    markup = _menu_keyboard(len(active), int(country.get("vaccine_doses") or 0))
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



def _approval_causes(country: dict) -> list[str]:
    """بخش «چرا رضایت این‌طور است» — منطق منتقل‌شده از approval_system.

    این تنها جایی است که این توضیح رندر می‌شود؛ قبلاً یک نسخه‌ی موازی در
    «وضعیت کشور → مشاهده کامل رضایت» بود که با این صفحه واگرا می‌شد.
    """
    import approval_system

    reqs = approval_system.calculate_country_requirements(country)
    lines = ["<b>📋 ارزیابی روزانه منابع حیاتی</b>"]

    elec = int(country.get("electricity") or 0)
    elec_need = int(reqs["elec_need"])
    if elec >= elec_need:
        lines.append(f"✅ برق و انرژی: تأمین کامل ({elec}٪ از {elec_need}٪ موردنیاز)")
    else:
        lines.append(f"❌ برق و انرژی: <b>کسری</b> ({elec}٪ از {elec_need}٪ موردنیاز)")

    oil_res = int(country.get("oil_reserves") or 0)
    oil_prod = int(country.get("oil_production") or 0)
    oil_need = int(reqs["oil_need_daily"])
    if oil_prod >= oil_need:
        lines.append(f"✅ سوخت و نفت: تولید مازاد ({format_oil(oil_prod - oil_need)} در روز)")
    elif oil_res + oil_prod >= oil_need:
        lines.append(f"⚠️ سوخت و نفت: تأمین از ذخایر (کسری تولید {format_oil(oil_need - oil_prod)}/روز)")
    else:
        lines.append(f"❌ سوخت و نفت: <b>کمبود شدید</b> (کسری {format_oil(oil_need - oil_res - oil_prod)})")

    grain = int(country.get("grain") or 0)
    grain_daily = int(country.get("grain_daily") or 0)
    grain_need = int(reqs["grain_need_daily"])
    if grain + grain_daily >= grain_need:
        lines.append(f"✅ غذا و غلات: تأمین کامل (ذخیره {format_number(grain)} تن، نیاز {format_number(grain_need)} تن/روز)")
    else:
        lines.append(f"❌ غذا و غلات: <b>گرسنگی</b> (کسری {format_number(grain_need - grain - grain_daily)} تن)")

    treasury = int(country.get("treasury") or 0)
    if treasury < 0:
        lines.append(f"❌ بدهی خزانه: کسر {int(abs(treasury) / 10_000_000 * 10)}٪ از رضایت ({format_money(treasury)})")

    approval = int(country.get("approval_rating") or 0)
    lines.append("")
    lines.append("<b>👥 جمعیت و مهاجرت</b>")
    if approval >= 40:
        lines.append(f"🟢 پایدار — نرخ مهاجرت ۰٪ (جمعیت {format_number(country.get('population'))} نفر)")
        lines.append("<i>زیر ۴۰٪ رضایت، مهاجرت و کاهش ارتش شروع می‌شود.</i>")
    else:
        rate = 0.005 if approval >= 30 else (0.010 if approval >= 20 else (0.020 if approval >= 10 else 0.035))
        leaving = int(int(country.get("population") or 0) * rate)
        lines.append(f"🔴 <b>هشدار خروج جمعیت</b> — روزانه {rate * 100:g}٪ (حدود {format_number(leaving)} نفر)")
        lines.append("<i>این مستقیماً نیروی انسانی ارتش و پایه‌ی درآمد مالیاتی را کم می‌کند.</i>")
    return lines


def build_approval_view(country: dict, state: dict):
    """تنها صفحه‌ی تفصیلی رضایت عمومی در کل بات.

    حتی وقتی سیستم سیاست داخلی خاموش است هم کار می‌کند — رضایت عمومی متعلق به
    این سیستم نیست و مصرف‌کننده‌های دیگری (کمبود منابع، دیپلماسی، عملیات،
    تحریم) هم دارد.
    """
    approval = int(country.get("approval_rating") or 0)
    filled_a = max(0, min(10, int(round(approval / 10))))
    bar_a = "█" * filled_a + "░" * (10 - filled_a)
    if approval >= 75:
        verdict = "🟢 رضایت عالی — ثبات کامل اجتماعی"
    elif approval >= 50:
        verdict = "🟡 رضایت متوسط — ثبات شکننده"
    elif approval >= 40:
        verdict = "🟠 رضایت پایین — آستانه بحران"
    else:
        verdict = "🔴 رضایت بحرانی — مهاجرت گسترده"

    lines = [
        "📉 <b>رضایت عمومی و ناآرامی</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"{country.get('flag', '🏳️')} <b>{html.escape(country.get('name', 'کشور'))}</b>",
        "",
        f"<code>[{bar_a}]</code> <b>{approval}٪</b>",
        verdict,
    ]

    trend = ia.approval_trend(country["id"])
    if trend is not None:
        lines.append(f"روند آخرین چرخه: <b>{_trend_arrow(trend)} {abs(trend)} واحد</b>")

    lines.append("")
    lines.extend(_approval_causes(country))

    if ia.is_enabled():
        stage = int(state.get("unrest_stage") or 0)
        unrest = float(state.get("unrest") or 0)
        filled_u = max(0, min(10, int(round(unrest / 10))))
        bar_u = "█" * filled_u + "░" * (10 - filled_u)
        lines.extend([
            "",
            "<b>⚖️ ناآرامی داخلی</b>",
            f"<code>[{bar_u}]</code> <b>{int(unrest)}/100</b> — {ia.stage_label(stage)}",
            f"<i>{ia.UNREST_STAGES.get(stage, {}).get('desc', '')}</i>",
            "",
        ])
        for level in range(5):
            lines.append(f"{'◀️' if level == stage else '　'} {ia.UNREST_STAGES[level]['label']}")

        lines.extend([
            "",
            "<b>💰 اثر روی درآمد مالیاتی</b>",
            f"• نرخ تمکین (از رضایت): <b>{int(ia.compliance_for(approval) * 100)}٪</b>",
            f"• ضریب ناآرامی: <b>{int(ia.UNREST_TAX_MULT.get(stage, 1.0) * 100)}٪</b>",
            f"• درآمد مالیاتی فعلی: <b>{format_money(country.get('tax_income'))}</b>",
        ])

        active = ia.get_active_crises(country["id"])
        if active:
            lines.append("")
            lines.append(f"<b>🚨 بحران‌های فعال ({len(active)})</b>")
            for crisis in active[:3]:
                spec = ia.CRISIS_CATALOG.get(crisis["crisis_key"], {})
                lines.append(f"• {spec.get('label', '')} — {_stage_fa(crisis['stage'])}")

        if state.get("collapse_risk"):
            lines.append("\n⚫️ <b>کشور شما چند روز است در بحران حکومتی قرار دارد. کنترل اوضاع فوری است.</b>")

        lines.extend([
            "",
            "<b>🛠 راه‌های بهبود</b>",
            "• کاهش مالیات • واردات غله • تأمین برق و سوخت",
            "• بازسازی زیرساخت • بیانیه رسمی • اقدامات اضطراری",
        ])
        rows = [
            [InlineKeyboardButton("💰 سیاست مالیاتی", callback_data="dom:tax")],
            [InlineKeyboardButton("🛠️ اقدامات اضطراری", callback_data="dom:actions")],
            [InlineKeyboardButton("🏛️ سیاست داخلی", callback_data="dom:menu")],
            [InlineKeyboardButton("🔙 وضعیت کشور", callback_data="country:back_profile")],
        ]
    else:
        lines.extend([
            "",
            "<i>سیستم سیاست داخلی (جمعیت پویا، مالیات و بحران‌ها) هنوز فعال نشده است.</i>",
        ])
        rows = [[InlineKeyboardButton("🔙 وضعیت کشور", callback_data="country:back_profile")]]

    return "\n".join(lines), _kb(rows)


async def _unrest_page(query, country: dict, state: dict):
    text, markup = build_approval_view(country, state)
    await query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")


async def show_approval_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نقطه‌ی ورود مشترک: /approval، دکمه‌ی «📊 رضایت عمومی» و دکمه‌های اینلاین.

    همه به یک صفحه و یک پیاده‌سازی می‌رسند تا دو روایت موازی از یک عدد نداشته باشیم.
    """
    country = await _require_country(update)
    if not country:
        return
    state = (ia.get_state(country["id"]) or {}) if ia.is_enabled() else {}
    text, markup = build_approval_view(country, state)
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(text, reply_markup=markup, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="HTML")


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
    lines = [
        (f"✅ {html.escape(notice)}\n" if notice else "") + f"{spec.get('label', '')} — <b>{ia.SEVERITY_LABELS.get(crisis['severity'], '')}</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"مرحله: <b>{_stage_fa(crisis['stage'])}</b>",
        f"کاهش خسارت فعلی: <b>{int(float(crisis.get('mitigation') or 0) * 100)}٪</b>"
        f" از سقف <b>{int(ia.mitigation_cap(crisis) * 100)}٪</b>",
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

    lines.append("\n<b>🛠 اقدامات در دسترس</b>")
    rows = []
    locked_lines = []
    for action_key in ia.available_actions(crisis):
        action = ia.CRISIS_ACTIONS[action_key]
        costs = ia.action_cost(action_key, country)
        ok, reason = ia.check_action(action_key, crisis, country)

        price_parts = ["رایگان"] if costs["money"] == 0 else [format_money(costs["money"])]
        if costs["money"] == 0:
            price_parts = ["رایگان"]
        for field, amount in (costs["resources"] or {}).items():
            unit = {"grain": "تن غله", "oil_reserves": "بشکه نفت", "microchips": "چیپ"}.get(field, field)
            price_parts.append(f"{format_number(amount)} {unit}")
        for field, amount in (action.get("grants") or {}).items():
            unit = {"grain": "تن غله", "oil_reserves": "بشکه نفت"}.get(field, field)
            price_parts.append(f"➕ {format_number(amount)} {unit}")
        price_text = " + ".join(price_parts)

        effect = f"مهار {int(float(action['mitigation']) * 100)}٪"
        if action.get("approval"):
            effect += f" | رضایت {action['approval']:+d}"
        if action.get("unrest"):
            effect += f" | ناآرامی {int(action['unrest']):+d}"

        if ok:
            lines.append(f"\n{action['label']} — <b>{price_text}</b>\n<i>{action['desc']}</i>\n<code>{effect}</code>")
            rows.append([InlineKeyboardButton(
                f"{action['label']} ({price_text.split(' + ')[0]})",
                callback_data=f"dom:act:{crisis_id}:{action_key}",
            )])
        else:
            locked_lines.append(f"🔒 {action['label']} — <i>{html.escape(reason)}</i>")

    if locked_lines:
        lines.append("\n<b>غیرقابل اجرا</b>")
        lines.extend(locked_lines)

    cap = int(ia.mitigation_cap(crisis) * 100)
    lines.append(
        f"\nℹ️ <i>سقف مهار این بحران {cap}٪ است — هیچ بحرانی کاملاً خنثی نمی‌شود. "
        f"با اقدامات راهبردی مثل واکسن، سقف تا ۹۵٪ بالا می‌رود.</i>"
    )

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


async def _readiness_page(query, country: dict, state: dict):
    """آمادگی کشور در برابر بحران‌هایی که جغرافیایش محتمل می‌کند."""
    labels = {"earthquake": "🌍 زلزله", "flood": "🌊 سیل", "drought": "🏜 خشکسالی",
              "storm": "🌪 طوفان", "wildfire": "🔥 آتش‌سوزی", "epidemic": "🦠 اپیدمی"}
    weights = ia.hazard_weights(country)
    total = sum(weights.values()) or 1.0
    ranked = sorted(weights.items(), key=lambda kv: -kv[1])

    lines = [
        "🛡 <b>آمادگی و پیشگیری</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"{country.get('flag', '🏳️')} <b>{html.escape(country.get('name', 'کشور'))}</b>",
        "",
        "<b>محتمل‌ترین بلایا در کشور شما</b>",
        "<i>بر پایه‌ی موقعیت جغرافیایی و فصل جاری</i>",
        "",
    ]
    for hazard, weight in ranked:
        share = int(weight / total * 100)
        filled = max(0, min(10, round(share / 10)))
        lines.append(f"{labels.get(hazard, hazard)}  <code>{'█' * filled}{'░' * (10 - filled)}</code> {share}٪")

    grain = int(country.get("grain") or 0)
    oil = int(country.get("oil_reserves") or 0)
    doses = int(country.get("vaccine_doses") or 0)
    treasury = int(country.get("treasury") or 0)
    tech = int(country.get("tech_level") or 1)

    lines.extend(["", "<b>وضعیت ذخایر شما</b>"])
    lines.append(f"{'✅' if grain > 50_000 else '⚠️'} غلات: {format_number(grain)} تن — سپر قحطی و خشکسالی")
    lines.append(f"{'✅' if oil > 200_000 else '⚠️'} نفت: {format_number(oil)} بشکه — لازم برای اطفای حریق هوایی")
    lines.append(f"{'✅' if doses >= ia.VACCINE_DOSES_PER_USE else '⚠️'} واکسن: {format_number(doses)} دُز — تنها راه عبور از سقف مهار ۸۰٪")
    lines.append(f"{'✅' if treasury > 50_000_000 else '⚠️'} خزانه: {format_money(treasury)} — بدون پول هیچ اقدامی ممکن نیست")
    lines.append(f"{'✅' if tech >= ia.VACCINE_MIN_TECH_LEVEL else '⚠️'} فناوری: سطح {tech} — سطح {ia.VACCINE_MIN_TECH_LEVEL} برای تولید واکسن")

    top_hazard = ranked[0][0]
    advice = {
        "earthquake": "خزانه و بودجه‌ی بازسازی نگه دارید؛ زلزله هشدار کوتاهی دارد.",
        "flood": "ذخیره‌ی غلات و بودجه‌ی سیل‌بند مهم‌ترین سپر شماست.",
        "drought": "غله ذخیره کنید و اگر فناوری‌تان به ۳ رسید، آب‌شیرین‌کن سقف مهار را به ۹۰٪ می‌برد.",
        "storm": "بنادر و ذخایر سوخت را پیش از فصل طوفان آماده کنید.",
        "wildfire": "بدون ذخیره‌ی نفت، اطفای حریق هوایی ممکن نیست.",
        "epidemic": "از همین حالا واکسن تولید کنید — سه روز طول می‌کشد و در بحران دیر است.",
    }.get(top_hazard, "")
    if advice:
        lines.append(f"\n💡 <b>توصیه:</b> {advice}")

    rows = [
        [InlineKeyboardButton("💉 برنامه واکسن", callback_data="dom:vaccine")],
        _back_row(),
    ]
    await query.edit_message_text("\n".join(lines), reply_markup=_kb(rows), parse_mode="HTML")


async def _vaccine_page(query, country: dict, notice: str = ""):
    doses = int(country.get("vaccine_doses") or 0)
    active = ia.get_active_vaccine_project(country["id"])
    lines = [
        (f"✅ {html.escape(notice)}\n" if notice else "") + "💉 <b>برنامه واکسن</b>",
        "━━━━━━━━━━━━━━━━━━",
        f"📦 دُز آماده در انبار: <b>{format_number(doses)}</b>",
        "",
        "<i>تولید داخلی چند روز طول می‌کشد، اما دُز واکسن در بورس کالا</i>",
        "<i>قابل خرید و فروش است — می‌توانید بخرید یا مازادتان را بفروشید.</i>",
    ]

    rows = []
    if active:
        ready = ia._parse_dt(active["ready_at"])
        remaining = max(0, int((ready - ia._now()).total_seconds() // 3600)) if ready else 0
        lines.extend([
            "",
            "🏭 <b>پروژه در حال تولید</b>",
            f"• مقدار: <b>{format_number(active['doses'])}</b> دُز",
            f"• زمان باقی‌مانده: <b>{remaining} ساعت</b>",
            "<i>تا تحویل این پروژه، پروژه‌ی جدید نمی‌توانید شروع کنید.</i>",
        ])
    else:
        lines.extend(["", "<b>شروع تولید جدید</b>"])
        for batches in (1, 3, 6):
            need = ia.vaccine_requirements(batches)
            ok, reason, _n = ia.can_start_vaccine(country, batches)
            body = (
                f"\n{'✅' if ok else '🔒'} <b>{format_number(need['doses'])} دُز</b> — {need['days']} روز\n"
                f"   {format_money(need['cost'])} | {format_number(need['microchips'])} چیپ | "
                f"{need['medical_isotopes']} کیلو ایزوتوپ"
            )
            if not ok:
                body += f"\n   <i>{html.escape(reason)}</i>"
            lines.append(body)
            if ok:
                rows.append([InlineKeyboardButton(
                    f"🏭 تولید {format_number(need['doses'])} دُز ({need['days']} روز)",
                    callback_data=f"dom:vax_start:{batches}",
                )])

        lines.extend([
            "",
            f"<b>پیش‌نیازها:</b> سطح فناوری {ia.VACCINE_MIN_TECH_LEVEL} + میکروچیپ + ایزوتوپ پزشکی",
            "<i>ایزوتوپ پزشکی از نیروگاه هسته‌ای و چرخه‌ی سوخت به دست می‌آید.</i>",
        ])

    history = [p for p in ia.get_vaccine_history(country["id"], 5) if p["status"] == "delivered"]
    if history:
        lines.append("\n<b>تولیدهای پیشین</b>")
        for project in history:
            lines.append(f"• {format_number(project['doses'])} دُز — {str(project.get('collected_at') or '')[:10]}")

    lines.append(
        f"\n💡 هر بار تزریق سراسری <b>{format_number(ia.VACCINE_DOSES_PER_USE)}</b> دُز مصرف می‌کند "
        f"و سقف مهار بحران را به <b>۹۵٪</b> می‌رساند."
    )
    rows.append(_back_row())
    await query.edit_message_text("\n".join(lines), reply_markup=_kb(rows), parse_mode="HTML")


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

    # رضایت عمومی متعلق به این سیستم نیست؛ صفحه‌اش همیشه باید باز شود.
    if data == "dom:unrest":
        await _unrest_page(query, country, ia.get_state(country["id"]) or {} if ia.is_enabled() else {})
        return

    if not ia.is_enabled():
        await query.edit_message_text(
            _disabled_text(),
            reply_markup=_kb([
                [InlineKeyboardButton("📉 رضایت عمومی", callback_data="dom:unrest")],
                [InlineKeyboardButton("🔙 بازگشت به کشور", callback_data="country:back_profile")],
            ]),
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
    elif data == "dom:readiness":
        await _readiness_page(query, country, state)
    elif data == "dom:vaccine":
        await _vaccine_page(query, country)
    elif data.startswith("dom:vax_start:"):
        batches = int(data.split(":")[2])
        ok, message, _project = ia.start_vaccine_project(country["id"], batches, actor_id=query.from_user.id)
        await query.answer(message, show_alert=True)
        await _vaccine_page(query, db.get_country_by_id(country["id"]) or country, notice=message if ok else "")
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
