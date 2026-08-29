# -*- coding: utf-8 -*-
"""پنل ادمین: مدیریت قیمت و تخفیف فروشگاه ویژه (VIP).

ادمین برای هر آیتم فروشگاه ویژه، درصد تخفیف تعیین می‌کند (۱۰٪، ۲۰٪، ...)؛
قیمت تخفیف‌خورده خودکار در همه‌ی منوها، دکمه‌ها و فاکتورهای فروشگاه اعمال
می‌شود — بدون دست‌زدن به قیمت پایه در کد.

پنل دسته‌بندی شده است (مثل خود فروشگاه): اشتراک‌ها، بتل پس، ویژه/بقا،
دیده شدن و بلیط، گروهک — تا ادمین بین ۲۸ آیتم سردرگم نشود.
"""

from __future__ import annotations

import html

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

import database as db
from handlers.vip import PLANS_METADATA, effective_price, discount_of

_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa(num) -> str:
    return str(num).translate(_FA_DIGITS)


# دسته‌های پنل تخفیف — همان ساختار منوی خود فروشگاه
VIP_CATEGORIES = (
    ("passes", "👑 اشتراک‌های رهبری", (
        "vip_bronze", "vip_silver", "vip_gold", "vip_diamond",
    )),
    ("battlepass", "⭐️ بتل پس", (
        "battle_pass", "bp_booster_3d", "bp_booster_7d", "bp_booster_30d",
    )),
    ("special", "📦 ویژه (بقا و لجستیک)", (
        "survival_small", "survival_medium", "survival_large", "survival_ultra",
    )),
    ("visibility", "🎨 دیده شدن و بلیط", (
        "golden_stmt_1", "golden_stmt_3", "golden_stmt_10",
        "pin_1", "pin_3",
        "title_7d", "title_30d",
        "frame_7d", "frame_30d",
        "ticket_drill", "ticket_drill_3",
        "ticket_statement", "ticket_statement_5",
        "ticket_contract_3d", "ticket_contract_7d",
    )),
    ("militia", "🏴 گروهک", (
        "militia",
    )),
)

# کلیدهای قابل مدیریت (بدون نام‌های مستعار تکراری bronze/silver/...)
MANAGEABLE_KEYS = [key for _cat, _label, keys in VIP_CATEGORIES for key in keys]

# نقشه‌ی معکوس: آیتم → دسته
_GROUP_OF_KEY = {key: cat for cat, _label, keys in VIP_CATEGORIES for key in keys}

PAGE_SIZE = 8
DISCOUNT_CHOICES = (10, 20, 30, 40, 50)


def _kb(rows):
    return InlineKeyboardMarkup(rows)


def _category_label(cat_key: str) -> str:
    for key, label, _keys in VIP_CATEGORIES:
        if key == cat_key:
            return label
    return cat_key


def _category_items(cat_key: str) -> list[tuple[str, dict]]:
    for key, _label, keys in VIP_CATEGORIES:
        if key == cat_key:
            return [(k, PLANS_METADATA[k]) for k in keys if k in PLANS_METADATA]
    return []


async def vip_price_menu(query, page: int = 0):
    """صفحه‌ی اول: انتخاب دسته — نه ۲۸ آیتم پشت‌سرهم."""
    lines = [
        "🛒 <b>قیمت و تخفیف فروشگاه ویژه</b>",
        "━━━━━━━━━━━━━━━━━━",
        "یک دسته را انتخاب کنید؛ قیمت تخفیف‌خورده خودکار در فروشگاه و فاکتورها اعمال می‌شود.",
        "",
    ]
    rows = []
    for cat_key, label, keys in VIP_CATEGORIES:
        items = [k for k in keys if k in PLANS_METADATA]
        discounted = sum(1 for k in items if discount_of(k) > 0)
        suffix = f" 🔥{_fa(discounted)}" if discounted else ""
        rows.append([InlineKeyboardButton(
            f"{label} ({_fa(len(items))}){suffix}",
            callback_data=f"admin:vip_cat:{cat_key}:0",
        )])
    rows.append([InlineKeyboardButton("🔙 پنل ادمین", callback_data="admin:menu")])
    await query.edit_message_text("\n".join(lines), reply_markup=_kb(rows), parse_mode="HTML")


async def vip_category_menu(query, cat_key: str, page: int = 0):
    """آیتم‌های یک دسته، با صفحه‌بندی، دکمه‌ی تخفیف برای هر آیتم و
    دکمه‌های سراسری «تخفیف همه» / «حذف تخفیف همه» برای کل دسته."""
    items = _category_items(cat_key)
    if not items:
        await query.answer("دسته‌ی خالی است.", show_alert=True)
        await vip_price_menu(query, 0)
        return
    total_pages = max(1, (len(items) + PAGE_SIZE - 1) // PAGE_SIZE)
    page = max(0, min(page, total_pages - 1))
    chunk = items[page * PAGE_SIZE:(page + 1) * PAGE_SIZE]

    lines = [f"{_category_label(cat_key)}", "━━━━━━━━━━━━━━━━━━"]
    for key, plan in chunk:
        pct = discount_of(key)
        base = int(plan.get("price") or 0)
        eff = effective_price(key)
        title = html.escape(plan.get("title") or key)
        if pct > 0:
            lines.append(f"• {title}\n"
                         f"   <s>{base:,}</s> → <b>{eff:,} ت</b> 🔥<b>{_fa(pct)}٪</b>")
        else:
            lines.append(f"• {title}\n   {base:,} تومان")

    rows = []
    for key, _plan in chunk:
        pct = discount_of(key)
        btn = f"🏷️ تخفیف ({_fa(pct)}٪)" if pct > 0 else "🏷️ تخفیف"
        rows.append([InlineKeyboardButton(btn, callback_data=f"admin:vip_disc:{key}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️", callback_data=f"admin:vip_cat:{cat_key}:{page - 1}"))
    nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("▶️", callback_data=f"admin:vip_cat:{cat_key}:{page + 1}"))
    if total_pages > 1:
        rows.append(nav)

    # دکمه‌های سراسری دسته
    rows.append([
        InlineKeyboardButton("🎯 تخفیف همه‌ی دسته", callback_data=f"admin:vip_cat_all:{cat_key}"),
    ])
    rows.append([
        InlineKeyboardButton("❌ حذف تخفیف همه‌ی دسته", callback_data=f"admin:vip_cat_clear:{cat_key}"),
    ])

    rows.append([InlineKeyboardButton("🔙 دسته‌ها", callback_data="admin:vip_price")])
    rows.append([InlineKeyboardButton("🔙 پنل ادمین", callback_data="admin:menu")])

    await query.edit_message_text("\n".join(lines), reply_markup=_kb(rows), parse_mode="HTML")


async def vip_category_discount_picker(query, cat_key: str):
    """انتخاب درصد برای کل دسته — روی همه‌ی آیتم‌های دسته اعمال می‌شود."""
    items = _category_items(cat_key)
    label = _category_label(cat_key)
    discounted = sum(1 for k, _p in items if discount_of(k) > 0)

    text = (
        f"🎯 <b>تخفیف همه‌ی دسته: {label}</b>\n"
        "━━━━━━━━━━━━━━━━━━\n"
        f"{_fa(len(items))} آیتم در این دسته است؛ "
        f"{_fa(discounted)} مورد تخفیف دارند.\n\n"
        "درصدی که انتخاب کنی روی <b>همه‌ی آیتم‌های این دسته</b> اعمال می‌شود:"
    )
    rows = []
    row = []
    for choice in DISCOUNT_CHOICES:
        row.append(InlineKeyboardButton(
            f"{_fa(choice)}٪", callback_data=f"admin:vip_cat_set:{cat_key}:{choice}",
        ))
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("❌ حذف تخفیف همه‌ی دسته", callback_data=f"admin:vip_cat_clear:{cat_key}")])
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:vip_cat:{cat_key}:0")])
    await query.edit_message_text(text, reply_markup=_kb(rows), parse_mode="HTML")


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
    # برگشت به دسته‌ی همان آیتم
    cat_key = _GROUP_OF_KEY.get(plan_key, "passes")
    rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:vip_cat:{cat_key}:0")])
    await query.edit_message_text(text, reply_markup=_kb(rows), parse_mode="HTML")


async def vip_admin_callback(query, context, data: str) -> bool:
    """روت تخفیف فروشگاه ویژه؛ True یعنی هندل شد."""
    if data == "admin:vip_price":
        await vip_price_menu(query, 0)
        return True

    if data.startswith("admin:vip_cat:"):
        parts = data.split(":")
        cat_key = parts[2]
        page = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
        await vip_category_menu(query, cat_key, page)
        return True

    # تخفیف سراسری یک دسته
    if data.startswith("admin:vip_cat_all:"):
        cat_key = data.split(":", 2)[2]
        await vip_category_discount_picker(query, cat_key)
        return True

    if data.startswith("admin:vip_cat_set:"):
        _, _, cat_key, pct_raw = data.split(":", 3)
        try:
            pct = int(pct_raw)
        except (TypeError, ValueError):
            pct = 0
        pct = max(0, min(90, pct))
        keys = [k for k, _p in _category_items(cat_key)]
        for key in keys:
            db.set_vip_discount(key, pct)
        label = _category_label(cat_key)
        if pct > 0:
            await query.answer(
                f"✅ تخفیف {_fa(pct)}٪ روی {_fa(len(keys))} آیتم «{label}» اعمال شد.",
                show_alert=True,
            )
            db.add_log(f"admin:{query.from_user.id}", "vip_discount_category",
                       f"{cat_key} {pct}% x{len(keys)}")
        else:
            await query.answer(f"✅ تخفیف «{label}» حذف شد.", show_alert=True)
            db.add_log(f"admin:{query.from_user.id}", "vip_discount_category_clear", cat_key)
        await vip_category_menu(query, cat_key, 0)
        return True

    if data.startswith("admin:vip_cat_clear:"):
        cat_key = data.split(":", 2)[2]
        keys = [k for k, _p in _category_items(cat_key)]
        for key in keys:
            db.set_vip_discount(key, 0)
        label = _category_label(cat_key)
        await query.answer(f"✅ تخفیف همه‌ی آیتم‌های «{label}» حذف شد.", show_alert=True)
        db.add_log(f"admin:{query.from_user.id}", "vip_discount_category_clear", cat_key)
        await vip_category_menu(query, cat_key, 0)
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
