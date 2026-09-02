"""پنل داور — دسترسی محدود و کاملاً جدا از پنل مالک.

داور فقط دو کار می‌تواند بکند:
  ۱) دیدن انبار کشورها (برای ساختن پرامپت داوری)
  ۲) مدیریت جنگ: اعتبارسنجی و ثبت گزارش تلفات

هیچ دسترسی‌ای به ویرایش منابع، حذف کشور، ریست فصل یا پنل مالک ندارد.
"""

import math

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

import database as db
import config
from utils import format_money

PER_PAGE = 6

CONTINENT_BUTTONS = (
    ("🌍 خاورمیانه", "mideast"), ("🇪🇺 اروپا", "europe"), ("🌏 آسیا", "asia"),
    ("🌎 آمریکا", "americas"), ("🌍 آفریقا", "africa"), ("🌐 همه", "all"),
)


def _deny_markup():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بستن", callback_data="ref:close")]])


async def _guard(update_or_query, user_id: int) -> bool:
    """آیا این کاربر داور فعال است؟"""
    return db.is_referee(user_id)


# ==================== منوی اصلی داور ====================

def _main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📦 انبار کشورها", callback_data="ref:inv:0:all")],
        [InlineKeyboardButton("⚔️ مدیریت جنگ", callback_data="ref:war")],
        [InlineKeyboardButton("🏆 امتیاز من", callback_data="ref:me")],
    ])


def _main_text(user_id: int) -> str:
    a = db.get_game_admin(user_id) or {}
    pts = a.get("points", 0) if a else 0
    role = "👑 مالک" if db.is_owner(user_id) else "⚖️ داور"
    return (f"{role} — *پنل داوری*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"🏆 امتیاز شما: *{pts}*\n\n"
            "📦 *انبار کشورها* — برای ساختن پرامپت داوری\n"
            "⚔️ *مدیریت جنگ* — اعتبارسنجی و ثبت گزارش تلفات\n\n"
            "_دسترسی شما فقط به همین دو بخش است._")


async def referee_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not db.is_referee(uid):
        await update.message.reply_text("⛔ شما داور نیستید.")
        return
    await update.message.reply_text(_main_text(uid), reply_markup=_main_keyboard(),
                                    parse_mode="Markdown")


# ==================== انبار کشورها ====================

async def _inventory_list(query, page: int, cont: str):
    countries = db.get_all_countries()
    if cont and cont != "all":
        keys = config.CONTINENTS.get(cont, {}).get("keys", [])
        countries = [c for c in countries if c.get("country_key") in keys]

    total = max(1, math.ceil(len(countries) / PER_PAGE))
    page = max(0, min(page, total - 1))
    rows = []
    for c in countries[page * PER_PAGE:(page + 1) * PER_PAGE]:
        rows.append([InlineKeyboardButton(
            f"{c.get('flag', '🏳️')} {c['name']}",
            callback_data=f"ref:inv_show:{c['id']}")])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"ref:inv:{page - 1}:{cont}"))
    if total > 1:
        nav.append(InlineKeyboardButton(f"{page + 1}/{total}", callback_data="ref:noop"))
    if page < total - 1:
        nav.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"ref:inv:{page + 1}:{cont}"))
    if nav:
        rows.append(nav)

    btns = [InlineKeyboardButton(lbl, callback_data=f"ref:inv:0:{key}")
            for lbl, key in CONTINENT_BUTTONS]
    rows.append(btns[:3])
    rows.append(btns[3:])
    rows.append([InlineKeyboardButton("🔎 جستجوی نام کشور", callback_data="ref:inv_search")])
    rows.append([InlineKeyboardButton("🔙 منوی داوری", callback_data="ref:menu")])

    cont_name = dict((k, l) for l, k in CONTINENT_BUTTONS).get(cont, "همه")
    await query.edit_message_text(
        f"📦 *انبار کشورها* — {cont_name}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"{len(countries)} کشور. روی هرکدام بزنی، انبارش را می‌دهد.",
        reply_markup=InlineKeyboardMarkup(rows), parse_mode="Markdown")


async def _inventory_show(query, context, country_id: int, user_id: int):
    c = db.get_country_by_id(country_id)
    text = db.export_country_inventory_text(country_id)
    if not c or not text:
        await query.answer("انبار خالی یا کشور یافت نشد.", show_alert=True)
        return

    db.log_admin_action(user_id, db.user_role(user_id), "inventory_export",
                        c.get("country_key", ""), c["name"])

    chunks, cur = [], ""
    for line in text.splitlines(keepends=True):
        if len(cur) + len(line) > 3400:
            chunks.append(cur)
            cur = ""
        cur += line
    if cur:
        chunks.append(cur)

    head = (f"📦 *انبار {c.get('flag', '')} {c['name']}*\n"
            "این متن را در بخش «انبار» پرامپت داوری بچسبان.\n\n")
    await query.edit_message_text(
        head + f"`{chunks[0]}`",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("📦 کشور دیگر", callback_data="ref:inv:0:all")],
            [InlineKeyboardButton("🔙 منوی داوری", callback_data="ref:menu")]]),
        parse_mode="Markdown")
    for extra in chunks[1:]:
        await context.bot.send_message(query.from_user.id, f"`{extra}`", parse_mode="Markdown")


# ==================== مدیریت جنگ ====================

async def _war_menu(query):
    await query.edit_message_text(
        "⚔️ *مدیریت جنگ*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "✅ *اعتبارسنجی گزارش* — قبل از ثبت، گزارش هوش مصنوعی را بررسی کن\n"
        "📊 *وضعیت تنگه‌ها* — ببین کدام مسیر دریایی بسته است\n"
        "⚓ *محاصره‌های فعال* — فهرست محاصره‌های دریایی جاری\n\n"
        "_برای ثبت نهایی گزارش، از همان روال همیشگی ارسال گزارش استفاده کن._",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ اعتبارسنجی گزارش تلفات", callback_data="ref:validate")],
            [InlineKeyboardButton("🌊 وضعیت تنگه‌ها", callback_data="ref:straits")],
            [InlineKeyboardButton("⚓ محاصره‌های فعال", callback_data="ref:blockades")],
            [InlineKeyboardButton("🔙 منوی داوری", callback_data="ref:menu")]]),
        parse_mode="Markdown")


async def _straits_view(query):
    rows = db.list_strait_statuses()
    icons = {"open": "🟢", "blocked": "⛔", "closed": "⛔", "toll": "💰"}
    blocked = [r for r in rows if r["status"] in ("blocked", "closed")]
    lines = ["🌊 *وضعیت تنگه‌ها*", "━━━━━━━━━━━━━━━━━━", ""]
    if blocked:
        lines.append(f"⚠️ {len(blocked)} تنگه بسته است — مسیر دریایی بخشی از کشورها قطع شده.")
        lines.append("")
    for r in rows:
        extra = f" — عوارض {r['toll']:,} $" if r["status"] == "toll" else ""
        lines.append(f"{icons.get(r['status'], '❔')} {r['name'][:34]}")
        lines.append(f"    {r['owner_flag']} {r['owner_name']}{extra}")
    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 مدیریت جنگ", callback_data="ref:war")]]),
        parse_mode="Markdown")


async def _blockades_view(query):
    rows = db.get_all_active_blockades() or []
    lines = ["⚓ *محاصره‌های دریایی فعال*", "━━━━━━━━━━━━━━━━━━", ""]
    if not rows:
        lines.append("_هیچ محاصره‌ی فعالی وجود ندارد._")
    for b in rows:
        bl = db.get_country_by_id(b["blockader_id"])
        tg = db.get_country_by_id(b["target_id"])
        if not bl or not tg:
            continue
        roe = db.get_blockade_roe(b["blockader_id"], b["target_id"])
        roe_lbl = config.NAVAL_ROE.get(roe, {}).get("label", roe)
        lines.append(f"{bl.get('flag', '')} *{bl['name']}* ← {tg.get('flag', '')} *{tg['name']}*")
        lines.append(f"    📜 {roe_lbl}")
    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 مدیریت جنگ", callback_data="ref:war")]]),
        parse_mode="Markdown")


async def _my_score(query, user_id: int):
    a = db.get_game_admin(user_id)
    acts = db.get_admin_actions(user_id, limit=10)
    lines = ["🏆 *امتیاز و فعالیت شما*", "━━━━━━━━━━━━━━━━━━", ""]
    lines.append(f"🏆 امتیاز کل: *{(a or {}).get('points', 0)}*")
    lines.append(f"📊 اقدام‌های اخیر: {len(acts)}")
    lines.append("")
    labels = {"report_validated": "اعتبارسنجی گزارش", "report_registered": "ثبت گزارش",
              "inventory_export": "خروجی انبار", "war_action": "اقدام جنگی"}
    for act in acts:
        when = (act["created_at"] or "")[:16].replace("T", " ")
        pts = f" (+{act['points']})" if act["points"] else ""
        lines.append(f"• {labels.get(act['action'], act['action'])}{pts} — {when}")
    if not acts:
        lines.append("_هنوز فعالیتی ثبت نشده._")
    await query.edit_message_text(
        "\n".join(lines),
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منوی داوری", callback_data="ref:menu")]]),
        parse_mode="Markdown")


# ==================== مسیریابی ====================

async def referee_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    if not db.is_referee(uid):
        await query.edit_message_text("⛔ دسترسی داوری شما فعال نیست.", reply_markup=_deny_markup())
        return

    if data == "ref:noop":
        return
    if data == "ref:close":
        await query.edit_message_text("بسته شد.")
        return
    if data == "ref:menu":
        await query.edit_message_text(_main_text(uid), reply_markup=_main_keyboard(),
                                      parse_mode="Markdown")
    elif data.startswith("ref:inv:"):
        _, _, page, cont = data.split(":")
        await _inventory_list(query, int(page), cont)
    elif data.startswith("ref:inv_show:"):
        await _inventory_show(query, context, int(data.split(":")[2]), uid)
    elif data == "ref:inv_search":
        context.user_data["ref_awaiting"] = "search_country"
        await query.edit_message_text(
            "🔎 نام کشور را بفرست:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="ref:inv:0:all")]]))
    elif data == "ref:war":
        await _war_menu(query)
    elif data == "ref:straits":
        await _straits_view(query)
    elif data == "ref:blockades":
        await _blockades_view(query)
    elif data == "ref:me":
        await _my_score(query, uid)
    elif data == "ref:validate":
        context.user_data["ref_awaiting"] = "validate_report"
        await query.edit_message_text(
            "✅ *اعتبارسنجی گزارش تلفات*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "متن کامل گزارش را بفرست تا قبل از ثبت بررسی شود.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="ref:war")]]),
            parse_mode="Markdown")


async def referee_text_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    waiting = context.user_data.get("ref_awaiting")
    if not waiting or not db.is_referee(uid):
        return False
    text = (update.message.text or "").strip()
    if not text:
        return False
    context.user_data["ref_awaiting"] = None

    if waiting == "validate_report":
        result = db.validate_loss_report_text(text)
        db.log_admin_action(uid, db.user_role(uid), "report_validated",
                            result.get("country", ""), "ok" if result.get("ok") else "rejected")
        await update.message.reply_text(
            db.format_validation_report(result),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("✅ بررسی گزارش دیگر", callback_data="ref:validate")],
                [InlineKeyboardButton("🔙 منوی داوری", callback_data="ref:menu")]]),
            parse_mode="HTML")
        return True

    if waiting == "search_country":
        q = text.lower().strip()
        hits = [c for c in db.get_all_countries()
                if q in (c["name"] or "").lower() or q in (c.get("country_key") or "").lower()][:8]
        if not hits:
            await update.message.reply_text(
                f"❌ کشوری با «{text}» پیدا نشد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔎 دوباره", callback_data="ref:inv_search")]]))
            return True
        rows = [[InlineKeyboardButton(f"{c.get('flag', '🏳️')} {c['name']}",
                                      callback_data=f"ref:inv_show:{c['id']}")] for c in hits]
        rows.append([InlineKeyboardButton("🔙 منوی داوری", callback_data="ref:menu")])
        await update.message.reply_text(f"🔎 {len(hits)} نتیجه:",
                                        reply_markup=InlineKeyboardMarkup(rows))
        return True
    return False


def register(app):
    app.add_handler(CommandHandler("referee", referee_command))
    app.add_handler(CallbackQueryHandler(referee_callback, pattern=r"^ref:"))
