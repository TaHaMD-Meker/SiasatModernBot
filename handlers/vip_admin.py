# -*- coding: utf-8 -*-
"""پنل ادمین: مدیریت قیمت و تخفیف فروشگاه ویژه (VIP).

ادمین برای هر آیتم فروشگاه ویژه، درصد تخفیف تعیین می‌کند (۱۰٪، ۲۰٪، ...)؛
قیمت تخفیف‌خورده خودکار در همه‌ی منوها، دکمه‌ها و فاکتورهای فروشگاه اعمال
می‌شود — بدون دست‌زدن به قیمت پایه در کد.
"""

from __future__ import annotations

import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import database as db
from handlers.vip import PLANS_METADATA, effective_price, discount_of

PAGE_SIZE = 8
_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa(num) -> str:
    return str(num).translate(_FA_DIGITS)

# کلیدهای قابل مدیریت — بدون نام‌های مستعار تکراری (bronze/silver/... aliases)
MANAGEABLE_KEYS = [
    "vip_bronze", "vip_silver", "vip_gold", "vip_diamond",
    "battle_pass", "militia",
    "survival_small", "survival_medium", "survival_large", "survival_ultra",
    "ticket_drill", "ticket_drill_3", "ticket_statement", "ticket_statement_5",
    "ticket_contract_3d", "ticket_contract_7d",
    "bp_booster_3d", "bp_booster_7d", "bp_booster_30d",
    "golden_stmt_1", "golden_stmt_3", "golden_stmt_10",
    "pin_1", "pin_3",
    "title_7d", "title_30d",
    "frame_7d", "frame_30d",
]

DISCOUNT_CHOICES = (10, 20, 30, 40, 50)


def _kb(rows):
    return InlineKeyboardMarkup(rows)


async def vip_price_menu(query, page: int = 0):
    items = [(key, PLANS_METADATA[key]) for key in MANAGEABLE_KEYS if key in PLANS_METADATA]
    total_pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    chunk = items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    lines = ["🛒 <b>قیمت و تخفیف فروشگاه ویژه</b>", "━━━━━━━━━━━━━━━━━━"]
    lines.append("روی <b>تخفیف</b> بزنید تا درصد انتخاب کنید؛ قیمت تخفیف‌خورده "
                 "خودکار در فروشگاه و فاکتورها اعمال می‌شود.")
    lines.append("")
    for key, plan in chunk:
        pct = discount_of(key)
        base = int(plan.get("price") or 0)
        eff = effective_price(key)
        title = html.escape(plan.get("title") or key)
        if pct > 0:
            lines.append(f"• {title}\n"
                         f"   <s>قیمت پایه:</s> {base:,} تومان → <b>{eff:,} تومان</b> 🔥<b>{_fa(pct)}٪</b>")
        else:
            lines.append(f"• {title}\n   قیمت: {base:,} تومان")

    rows = []
    for key, _plan in chunk:
        pct = discount_of(key)
        btn = f"🏷️ تخفیف ({_fa(pct)}٪)" if pct > 0 else "🏷️ تخفیف"
        rows.append([InlineKeyboardButton(btn, callback_data=f"admin:vip_disc:{key}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"admin:vip_price:{page - 1}"))
    nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"admin:vip_price:{page + 1}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton("🔙 پنل ادمین", callback_data="admin:menu")])

    await query.edit_message_text("\n".join(lines), reply_markup=_kb(rows), parse_mode="HTML")


async def vip_discount_picker(query, plan_key: str):
    plan = PLANS_METADATA.get(plan_key)
    if not plan:
        await query.answer("آیتم یافت نشد.", show_alert=True)
        return
    base = int(plan.get("price") or 0)
    pct = discount_of(plan_key)
    eff = effective_price(plan_key)

    text = (
        f"🏷️ <b>تخفیف: {html.escape(plan.get('title') or plan_key)}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"قیمت پایه: <b>{base:,} تومان</b>\n"
        f"تخفیف فعلی: <b>{_fa(pct)}٪</b> → قیمت نهایی: <b>{eff:,} تومان</b>\n\n"
        "درصد تخفیف را انتخاب کنید:"
    )
    rows = []
    row = []
    for choice in DISCOUNT_CHOICES:
        row.append(InlineKeyboardButton(f"{_fa(choice)}٪", callback_data=f"admin:vip_disc_set:{plan_key}:{choice}"))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("❌ حذف تخفیف", callback_data=f"admin:vip_disc_set:{plan_key}:0")])
    rows.append([InlineKeyboardButton("🔙 قیمت و تخفیف", callback_data="admin:vip_price:0")])
    await query.edit_message_text(text, reply_markup=_kb(rows), parse_mode="HTML")


async def vip_admin_callback(query, context, data: str) -> bool:
    """روت تخفیف فروشگاه ویژه؛ True یعنی هندل شد."""
    if data == "admin:vip_price" or data.startswith("admin:vip_price:"):
        try:
            page = int(data.split(":")[2])
        except (IndexError, ValueError):
            page = 0
        await vip_price_menu(query, page)
        return True

    if data.startswith("admin:vip_disc_set:"):
        _, _, plan_key, pct_raw = data.split(":", 3)
        try:
            pct = int(pct_raw)
        except (TypeError, ValueError):
            pct = 0
        pct = max(0, min(90, pct))
        db.set_vip_discount(plan_key, pct)
        plan = PLANS_METADATA.get(plan_key, {})
        name = plan.get("title") or plan_key
        if pct > 0:
            await query.answer(f"✅ تخفیف {_fa(pct)}٪ روی «{name}» اعمال شد.", show_alert=True)
            db.add_log(f"admin:{query.from_user.id}", "vip_discount", f"{plan_key} {pct}%")
        else:
            await query.answer(f"✅ تخفیف «{name}» حذف شد.", show_alert=True)
            db.add_log(f"admin:{query.from_user.id}", "vip_discount_clear", plan_key)
        await vip_discount_picker(query, plan_key)
        return True

    if data.startswith("admin:vip_disc:"):
        plan_key = data.split(":", 2)[2]
        await vip_discount_picker(query, plan_key)
        return True

    return False
