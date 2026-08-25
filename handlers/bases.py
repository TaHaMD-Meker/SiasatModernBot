# -*- coding: utf-8 -*-
"""
سیستم تحرکات نظامی: مانور + پایگاه‌های پیشروی (Forward Bases).

مانور از منوی عملیات به اینجا منتقل شده است. پایگاه پیشروی با تأیید کشور میزبان
ساخته می‌شود، هزینه ساخت و نگهداری روزانه دارد، تجهیزات در آن مستقر می‌شوند و
قابل ارتقا/انحلال/اخراج است.
"""

import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters

import database as db
import config
from utils import format_money, format_number, get_main_keyboard


def _clean_persian_str(s: str) -> str:
    """استانداردسازی متن فارسی/انگلیسی جهت جستجوی دقیق."""
    if not s:
        return ""
    t = str(s).strip().lower()
    t = t.replace("_", " ")
    trans = {
        "ي": "ی", "ى": "ی", "ك": "ک", "ؤ": "و",
        "إ": "ا", "أ": "ا", "آ": "ا", "ة": "ه",
        "ئ": "ی", "ـ": ""
    }
    for k, v in trans.items():
        t = t.replace(k, v)
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def _md_escape(text):
    return str(text).replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("]", "\\]")


def _kb(rows):
    return InlineKeyboardMarkup(rows)


def _to_int(text):
    raw = str(text).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))
    raw = re.sub(r"[^0-9]", "", raw)
    return int(raw) if raw else None


def _cost_str(cost):
    parts = []
    if cost.get("money"):
        parts.append(f"💵 {format_money(cost['money'])}")
    if cost.get("gold"):
        parts.append(f"🪙 {format_number(cost['gold'])} سکه طلا")
    if cost.get("grain"):
        parts.append(f"🌾 {format_number(cost['grain'])} تن غلات")
    if cost.get("oil"):
        parts.append(f"🛢️ {format_number(cost['oil'])} بشکه نفت")
    return " | ".join(parts)


# ==================== منوی اصلی تحرکات نظامی ====================

async def military_movements_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text(
            "🎯 **ستاد توسعه و اقدامات راهبردی**\n━━━━━━━━━━━━━━━━━━\n\nیک بخش را جهت اقدام انتخاب کنید:",
            reply_markup=_kb([
                [InlineKeyboardButton("🪖 برگزاری مانور نظامی", callback_data="op:military_drill")],
                [InlineKeyboardButton("🕵️‍♂️ سازمان اطلاعات و عملیات سایبری", callback_data="intel:menu")],
                [InlineKeyboardButton("🎖️ کادر فرماندهی و سران نظامی", callback_data="intel:commanders_menu")],
                [InlineKeyboardButton("☢️ برنامه راهبردی هسته‌ای (سوخت و بازدارندگی)", callback_data="nuc:menu")],
                [InlineKeyboardButton("🏗️ ساخت پایگاه پیشروی", callback_data="mv:newbase")],
                [InlineKeyboardButton("📍 پایگاه‌های من", callback_data="mv:mybases")],
                [InlineKeyboardButton("🗺️ پایگاه‌های روی خاک من", callback_data="mv:hostbases")],
                [InlineKeyboardButton("🔙 بستن", callback_data="mv:close")],
            ]),
            parse_mode="Markdown",
        )
        return
    await update.message.reply_text(
        "🎯 **ستاد توسعه و اقدامات راهبردی**\n━━━━━━━━━━━━━━━━━━\n\nیک بخش را جهت اقدام انتخاب کنید:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🪖 برگزاری مانور نظامی", callback_data="op:military_drill")],
            [InlineKeyboardButton("🕵️‍♂️ سازمان اطلاعات و عملیات سایبری", callback_data="intel:menu")],
            [InlineKeyboardButton("🎖️ کادر فرماندهی و سران نظامی", callback_data="intel:commanders_menu")],
            [InlineKeyboardButton("☢️ برنامه راهبردی هسته‌ای (سوخت و بازدارندگی)", callback_data="nuc:menu")],
            [InlineKeyboardButton("🏗️ ساخت پایگاه پیشروی", callback_data="mv:newbase")],
            [InlineKeyboardButton("📍 پایگاه‌های من", callback_data="mv:mybases")],
            [InlineKeyboardButton("🗺️ پایگاه‌های روی خاک من", callback_data="mv:hostbases")],
        ]),
        parse_mode="Markdown",
    )


# ==================== ساخت پایگاه ====================

def _player_country(user_id):
    return db.get_country_by_player(user_id)


async def _send(bot, chat_id, text, kb=None):
    try:
        await bot.send_message(chat_id=chat_id, text=text, reply_markup=kb, parse_mode="Markdown")
    except Exception:
        pass


async def mv_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    country = _player_country(user_id)
    if not country:
        await query.answer("اول کشورت رو بساز!", show_alert=True)
        return

    # ---------- منو ----------
    if data in ("mv:menu", "bases:menu"):
        await military_movements_menu(update, context)
        return

    if data == "mv:close":
        await query.message.delete()
        return

    # ---------- ساخت پایگاه: انتخاب کشور میزبان ----------
    if data == "mv:newbase":
        continents = getattr(config, "CONTINENTS", {})
        rows = []
        row = []
        for c_key, c_info in continents.items():
            row.append(InlineKeyboardButton(c_info["name"], callback_data=f"mv:pickcont:{c_key}"))
            if len(row) == 2:
                rows.append(row)
                row = []
        if row:
            rows.append(row)
        rows.append([InlineKeyboardButton("🔎 جستجوی کشور میزبان (تایپی)", callback_data="mv:search_host")])
        rows.append([InlineKeyboardButton("🔙 بازگشت به ستاد راهبردی", callback_data="mv:menu")])
        await query.edit_message_text(
            "🏗️ *ساخت پایگاه پیشروی خارجی*\n━━━━━━━━━━━━━━━━━━\n\n"
            "جهت انتخاب کشور میزبان، **قاره مورد نظر را انتخاب فرمایید** یا از **جستجوی متنی** استفاده کنید:\n"
            "_(درخواست ساخت پایگاه باید توسط رهبر کشور میزبان تأیید شود)_",
            reply_markup=_kb(rows),
            parse_mode="Markdown",
        )
        return

    elif data.startswith("mv:pickcont:"):
        cont_key = data.split(":")[2]
        continents = getattr(config, "CONTINENTS", {})
        cont_info = continents.get(cont_key, {})
        keys = cont_info.get("keys", [])

        all_countries = db.get_all_countries()
        c_map = {c["country_key"]: c for c in all_countries if c.get("country_key")}

        rows = []
        row = []
        for k in keys:
            if k in c_map:
                c = c_map[k]
                if c["id"] == country["id"] or not c.get("player_id"):
                    continue
                row.append(InlineKeyboardButton(f"{c['flag']} {c['name']}", callback_data=f"mv:nb:{c['id']}"))
                if len(row) == 2:
                    rows.append(row)
                    row = []
        if row:
            rows.append(row)

        rows.append([
            InlineKeyboardButton("🔎 جستجو", callback_data="mv:search_host"),
            InlineKeyboardButton("🔙 لیست قاره‌ها", callback_data="mv:newbase")
        ])
        await query.edit_message_text(
            f"🏗️ *کشورهای میزبان در {cont_info.get('name', 'قاره')}*\n\nکشور مورد نظر را انتخاب فرمایید:\n_(فقط کشورهای دارای بازیکن فعال نمایش داده می‌شوند)_",
            reply_markup=_kb(rows),
            parse_mode="Markdown"
        )
        return

    elif data == "mv:search_host":
        context.user_data["mv_search_host"] = True
        await query.edit_message_text(
            "🔎 **جستجوی کشور میزبان پایگاه**\n━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً **نام کشور مورد نظر** را تایپ و ارسال فرمایید:\n"
            "*(مثال: سوریه، عراق، عمان، بلاروس، کوبا)*",
            reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به لیست قاره‌ها", callback_data="mv:newbase")]]),
            parse_mode="Markdown"
        )
        return

    if data.startswith("mv:nb:"):
        host_id = int(data.split(":")[2])
        host = db.get_country_by_id(host_id)
        if not host or not host.get("player_id"):
            await query.edit_message_text("❌ این کشور بازیکن ندارد؛ پایگاه فقط در کشورهای بازیکن‌دار امکان‌پذیر است.")
            return
        context.user_data["mv_input"] = {"state": "mv_name", "host_id": host_id, "owner_id": country["id"]}
        await query.edit_message_text(
            f"🏗️ پایگاه در {host['flag']} {host['name']}\n\n۱️⃣ *نام پایگاه* را ارسال کنید:\n_(مثلاً: پایگاه شهید کرمانی)_",
            parse_mode="Markdown",
        )
        return

    if data == "mv:nbconfirm":
        d = context.user_data.get("mv_input") or {}
        if d.get("state") != "mv_preview":
            return
        host = db.get_country_by_id(d["host_id"])
        req_id = db.create_base_request("create", country["id"], d["host_id"], d["name"], None, d["msg"], d["rent"])
        ok, msg, base_id = db.approve_base_create(req_id, auto=False)
        if not ok:
            await query.edit_message_text(f"⛔ {msg}", reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت", callback_data="mv:newbase")]]), parse_mode="Markdown")
            return
        # ساخت با تأیید میزبان: درخواست برای میزبان ارسال می‌شود
        db.set_base_request_status(req_id, "pending")
        # منابع را رزرو نمی‌کنیم؛ هنگام پذیرش میزبان دوباره بررسی می‌شود
        await query.edit_message_text(
            f"📨 *درخواست ساخت پایگاه «{d['name']}» برای {host['flag']} {host['name']} ارسال شد.*\n\nپس از تأیید میزبان، هزینه‌ها کسر و پایگاه ساخته می‌شود.",
            parse_mode="Markdown",
        )
        await _send(
            context.bot, host["player_id"],
            f"🏗️ *درخواست ساخت پایگاه پیشروی*\n━━━━━━━━━━━━━━━━━━\n\n"
            f"{country['flag']} {country['name']} درخواست ساخت پایگاه به نام:\n\n"
            f"🏠 *«{d['name']}»*\n\n"
            f"💰 اجاره پیشنهادی روزانه: *{format_money(d['rent'])}*\n\n"
            f"💬 پیام:\n_{d['msg']}_",
            _kb([
                [InlineKeyboardButton("✅ پذیرش پایگاه", callback_data=f"mv:nbacc:{req_id}")],
                [InlineKeyboardButton("❌ رد درخواست", callback_data=f"mv:nbrej:{req_id}")],
            ]),
        )
        context.user_data["mv_input"] = None
        return

    if data.startswith("mv:nbacc:") or data.startswith("mv:nbrej:"):
        req_id = int(data.split(":")[2])
        req = db.get_base_request(req_id)
        if not req or req["status"] != "pending":
            await query.answer("این درخواست قبلاً تعیین تکلیف شده است.", show_alert=True)
            return
        if req["host_id"] != country["id"]:
            await query.answer("فقط کشور میزبان می‌تواند پاسخ دهد!", show_alert=True)
            return
        owner = db.get_country_by_id(req["owner_id"])
        if data.startswith("mv:nbrej:"):
            db.set_base_request_status(req_id, "rejected")
            await query.edit_message_text("❌ درخواست پایگاه رد شد.")
            if owner and owner.get("player_id"):
                await _send(context.bot, owner["player_id"], f"⛔ درخواست ساخت پایگاه «{req['base_name']}» توسط {country['flag']} {country['name']} رد شد.")
            return
        ok, msg, base_id = db.approve_base_create(req_id, auto=True)
        if not ok:
            await query.edit_message_text(f"⛔ {msg}\n\nصاحب پایگاه منابع کافی ندارد.")
            return
        await query.edit_message_text(
            f"✅ پایگاه «{req['base_name']}» ساخته شد و در خاک شما مستقر گردید.\n💰 اجاره روزانه: {format_money(req['daily_rent'])}",
            parse_mode="Markdown",
        )
        if owner and owner.get("player_id"):
            await _send(context.bot, owner["player_id"], f"✅ پایگاه «{req['base_name']}» در {country['flag']} {country['name']} ساخته شد!\n📦 ظرفیت: {config.BASE_DEFAULT_CAPACITY} قلم تجهیزات")
        return

    # ---------- پایگاه‌های من ----------
    if data == "mv:mybases":
        bases = db.get_bases(owner_id=country["id"])
        if not bases:
            await query.edit_message_text("📭 شما هنوز پایگاهی نساخته‌اید.", reply_markup=_kb([[InlineKeyboardButton("🏗️ ساخت پایگاه", callback_data="mv:newbase")], [InlineKeyboardButton("🔙", callback_data="mv:menu")]]))
            return
        rows = [[InlineKeyboardButton(f"🏠 {b['name']} — {b['hflag']} {b['hname']}", callback_data=f"mv:base:{b['id']}")] for b in bases]
        rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="mv:menu")])
        await query.edit_message_text("📍 *پایگاه‌های من:*", reply_markup=_kb(rows), parse_mode="Markdown")
        return

    if data == "mv:hostbases":
        bases = db.get_bases(host_id=country["id"])
        if not bases:
            await query.edit_message_text("📭 هیچ پایگاه خارجی روی خاک شما نیست.", reply_markup=_kb([[InlineKeyboardButton("🔙", callback_data="mv:menu")]]))
            return
        rows = [[InlineKeyboardButton(f"🗺️ {b['name']} — {b['oflag']} {b['oname']}", callback_data=f"mv:hview:{b['id']}")] for b in bases]
        rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="mv:menu")])
        await query.edit_message_text("🗺️ *پایگاه‌های روی خاک من:*", reply_markup=_kb(rows), parse_mode="Markdown")
        return

    if data.startswith("mv:hview:"):
        bid = int(data.split(":")[2])
        b = db.get_base(bid)
        if not b or b["host_id"] != country["id"]:
            await query.answer("پایگاه یافت نشد.", show_alert=True)
            return
        await query.edit_message_text(_base_info_text(b), reply_markup=_kb([
            [InlineKeyboardButton("⛔ لغو میزبانی (۲۵٪ تلف تجهیزات)", callback_data=f"mv:evict:{bid}")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="mv:hostbases")],
        ]), parse_mode="Markdown")
        return

    if data.startswith("mv:evict:"):
        bid = int(data.split(":")[2])
        await query.edit_message_text(
            "⚠️ با لغو میزبانی، ۲۵٪ تجهیزات پایگاه حین خروج تلف می‌شود و بقیه به صاحبش برمی‌گردد.\nمطمئنی؟",
            reply_markup=_kb([
                [InlineKeyboardButton("⛔ بله، اخراج کن", callback_data=f"mv:evictok:{bid}")],
                [InlineKeyboardButton("❌ انصراف", callback_data=f"mv:hview:{bid}")],
            ]),
        )
        return

    if data.startswith("mv:evictok:"):
        bid = int(data.split(":")[2])
        b = db.get_base(bid)
        if not b or b["host_id"] != country["id"]:
            await query.answer("پایگاه یافت نشد.", show_alert=True)
            return
        owner = db.get_country_by_id(b["owner_id"])
        db.evict_base(bid)
        await query.edit_message_text(f"⛔ پایگاه «{b['name']}» اخراج شد. تجهیزات باقی‌مانده به صاحب آن برگشت.")
        if owner and owner.get("player_id"):
            await _send(context.bot, owner["player_id"], f"⛔ پایگاه «{b['name']}» توسط میزبان {country['flag']} {country['name']} اخراج شد. ۲۵٪ تجهیزات حین خروج تلف شد.")
        return

    # ---------- نمای پایگاه (صاحب) ----------
    if data.startswith("mv:base:"):
        bid = int(data.split(":")[2])
        b = db.get_base(bid)
        if not b or b["owner_id"] != country["id"]:
            await query.answer("پایگاه یافت نشد.", show_alert=True)
            return
        await query.edit_message_text(_base_info_text(b), reply_markup=_kb([
            [InlineKeyboardButton("📦 انتقال تجهیزات به پایگاه", callback_data=f"mv:deploy:{bid}")],
            [InlineKeyboardButton("↩️ بازگردانی تجهیزات", callback_data=f"mv:recall:{bid}")],
            [InlineKeyboardButton("⬆️ ارتقای ظرفیت (+۵)", callback_data=f"mv:upg:{bid}")],
            [InlineKeyboardButton("🗑️ انحلال پایگاه", callback_data=f"mv:diss:{bid}")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="mv:mybases")],
        ]), parse_mode="Markdown")
        return

    # ---------- انتقال تجهیزات ----------
    if data.startswith("mv:deploy:"):
        bid = int(data.split(":")[2])
        assets = db.get_country_assets(country["id"])
        cats = {}
        for a in assets:
            if (a.get("amount", 0) or 0) > 0:
                cats[a["category"]] = cats.get(a["category"], 0) + 1
        rows = []
        row = []
        for cat, (label, unit) in config.ASSET_CATEGORIES.items():
            if cat in cats:
                row.append(InlineKeyboardButton(f"{label} ({cats[cat]})", callback_data=f"mv:dcat:{bid}:{cat}"))
                if len(row) == 2:
                    rows.append(row)
                    row = []
        if row:
            rows.append(row)
        rows.append([InlineKeyboardButton("🔙 بازگشت به پایگاه", callback_data=f"mv:base:{bid}")])
        await query.edit_message_text("📦 دسته تجهیز را برای انتقال به پایگاه انتخاب کنید:", reply_markup=_kb(rows))
        return

    if data.startswith("mv:dcat:"):
        parts = data.split(":", 3)
        bid, cat = int(parts[2]), parts[3]
        assets = [a for a in db.get_country_assets(country["id"]) if a["category"] == cat and (a.get("amount", 0) or 0) > 0]
        rows = [[InlineKeyboardButton(f"{a['equipment_name']} ({format_number(a['amount'])})", callback_data=f"mv:ditem:{bid}:{a['equipment_key']}")] for a in assets]
        rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"mv:deploy:{bid}")])
        await query.edit_message_text("تجهیز را انتخاب کنید:", reply_markup=_kb(rows))
        return

    if data.startswith("mv:ditem:"):
        parts = data.split(":")
        bid, key = int(parts[2]), parts[3]
        a = db.get_asset_by_key(country["id"], key)
        if not a:
            await query.answer("تجهیز یافت نشد.", show_alert=True)
            return
        context.user_data["mv_input"] = {"state": "mv_qty", "base_id": bid, "key": key}
        await query.edit_message_text(
            f"📦 *{a['equipment_name']}*\nموجودی انبار شما: {format_number(a['amount'])}\n\nتعداد موردنظر برای انتقال را بفرست:",
            parse_mode="Markdown",
        )
        return

    # ---------- بازگردانی ----------
    if data.startswith("mv:recall:"):
        bid = int(data.split(":")[2])
        items = db.get_base_assets(bid)
        if not items:
            await query.edit_message_text("📭 این پایگاه خالی است.", reply_markup=_kb([[InlineKeyboardButton("🔙", callback_data=f"mv:base:{bid}")]]))
            return
        rows = [[InlineKeyboardButton(f"{i['equipment_name']} ({format_number(i['amount'])}) — همه", callback_data=f"mv:ritemall:{bid}:{i['equipment_key']}")] for i in items]
        rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"mv:base:{bid}")])
        await query.edit_message_text("کدام تجهیز به انبار برگردد؟", reply_markup=_kb(rows))
        return

    if data.startswith("mv:ritemall:"):
        parts = data.split(":")
        bid, key = int(parts[2]), parts[3]
        ok, msg = db.recall_from_base(bid, key, None)
        await query.answer("✅ بازگشت" if ok else f"❌ {msg}", show_alert=not ok)
        b = db.get_base(bid)
        if b:
            await query.edit_message_text(_base_info_text(b), reply_markup=_kb([
                [InlineKeyboardButton("📦 انتقال تجهیزات", callback_data=f"mv:deploy:{bid}")],
                [InlineKeyboardButton("↩️ بازگردانی تجهیزات", callback_data=f"mv:recall:{bid}")],
                [InlineKeyboardButton("⬆️ ارتقای ظرفیت", callback_data=f"mv:upg:{bid}")],
                [InlineKeyboardButton("🗑️ انحلال", callback_data=f"mv:diss:{bid}")],
                [InlineKeyboardButton("🔙", callback_data="mv:mybases")],
            ]), parse_mode="Markdown")
        return

    # ---------- ارتقا ----------
    if data.startswith("mv:upg:"):
        bid = int(data.split(":")[2])
        b = db.get_base(bid)
        if not b or b["owner_id"] != country["id"]:
            await query.answer("پایگاه یافت نشد.", show_alert=True)
            return
        await query.edit_message_text(
            f"⬆️ *ارتقای پایگاه «{b['name']}»*\n\nظرفیت: {b['capacity']} ← *{b['capacity'] + config.BASE_UPGRADE_STEP}*\nهزینه: {_cost_str(config.BASE_UPGRADE_COST)}\n\n⚠️ نیازمند تأیید کشور میزبان است.",
            reply_markup=_kb([
                [InlineKeyboardButton("📨 ارسال درخواست ارتقا به میزبان", callback_data=f"mv:upgsend:{bid}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data=f"mv:base:{bid}")],
            ]),
            parse_mode="Markdown",
        )
        return

    if data.startswith("mv:upgsend:"):
        bid = int(data.split(":")[2])
        b = db.get_base(bid)
        host = db.get_country_by_id(b["host_id"])
        req_id = db.create_base_request("upgrade", country["id"], b["host_id"], b["name"], bid, "ارتقای ظرفیت پایگاه", 0)
        await query.edit_message_text("📨 درخواست ارتقا برای میزبان ارسال شد.")
        if host and host.get("player_id"):
            await _send(context.bot, host["player_id"],
                f"⬆️ *درخواست ارتقای پایگاه «{b['name']}»* توسط {country['flag']} {country['name']}\nظرفیت: {b['capacity']} ← {b['capacity'] + config.BASE_UPGRADE_STEP}",
                _kb([
                    [InlineKeyboardButton("✅ پذیرش ارتقا", callback_data=f"mv:upacc:{req_id}")],
                    [InlineKeyboardButton("❌ رد", callback_data=f"mv:uprej:{req_id}")],
                ]))
        return

    if data.startswith("mv:upacc:") or data.startswith("mv:uprej:"):
        req_id = int(data.split(":")[2])
        req = db.get_base_request(req_id)
        if not req or req["status"] != "pending":
            await query.answer("تعیین تکلیف شده.", show_alert=True)
            return
        if req["host_id"] != country["id"]:
            await query.answer("فقط میزبان!", show_alert=True)
            return
        owner = db.get_country_by_id(req["owner_id"])
        if data.startswith("mv:uprej:"):
            db.set_base_request_status(req_id, "rejected")
            await query.edit_message_text("❌ ارتقا رد شد.")
            if owner and owner.get("player_id"):
                await _send(context.bot, owner["player_id"], f"⛔ درخواست ارتقای پایگاه «{req['base_name']}» رد شد.")
            return
        ok, msg = db.approve_base_upgrade(req_id)
        if not ok:
            await query.edit_message_text(f"⛔ {msg}")
            return
        await query.edit_message_text("✅ ارتقا انجام شد.")
        if owner and owner.get("player_id"):
            await _send(context.bot, owner["player_id"], f"✅ پایگاه «{req['base_name']}» ارتقا یافت! ظرفیت جدید: {db.get_base(req['base_id'])['capacity']} قلم")
        return

    # ---------- انحلال ----------
    if data.startswith("mv:diss:"):
        bid = int(data.split(":")[2])
        await query.edit_message_text(
            "🗑️ با انحلال، همه تجهیزات به انبار شما برمی‌گردد و پایگاه حذف می‌شود. ادامه؟",
            reply_markup=_kb([
                [InlineKeyboardButton("🗑️ بله، منحل کن", callback_data=f"mv:dissok:{bid}")],
                [InlineKeyboardButton("❌ انصراف", callback_data=f"mv:base:{bid}")],
            ]),
        )
        return

    if data.startswith("mv:dissok:"):
        bid = int(data.split(":")[2])
        b = db.get_base(bid)
        if not b or b["owner_id"] != country["id"]:
            await query.answer("پایگاه یافت نشد.", show_alert=True)
            return
        db.dissolve_base(bid, loss_pct=0)
        await query.edit_message_text(f"🗑️ پایگاه «{b['name']}» منحل شد. تجهیزات به انبار شما برگشت.")
        return


def _base_info_text(b):
    items = db.get_base_assets(b["id"])
    used = len(items)
    lines = [
        f"🏠 *پایگاه «{_md_escape(b['name'])}»*",
        f"━━━━━━━━━━━━━━━━━━",
        f"🗺️ میزبان: {b['hflag']} {b['hname']}",
        f"🏗️ صاحب: {b['oflag']} {b['oname']}",
        f"⬆️ سطح: {b['level']} | 📦 ظرفیت: {used}/{b['capacity']} قلم",
        f"💰 اجاره روزانه: {format_money(b['daily_rent'] or 0)}",
        f"📉 هزینه روزانه: {_cost_str(config.BASE_DAILY_FLAT)}",
    ]
    if items:
        lines.append("\n*تجهیزات مستقر:*")
        for i in items:
            lines.append(f"  • {i['equipment_name']}: {format_number(i['amount'])}")
    else:
        lines.append("\n_(خالی)_")
    return "\n".join(lines)


# ==================== ورودی‌های متنی ====================

async def mv_text_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # پردازش جستجوی کشور میزبان
    if context.user_data.get("mv_search_host"):
        del context.user_data["mv_search_host"]
        user_query = (update.message.text or "").strip()
        clean_q = _clean_persian_str(user_query)

        user_id = update.effective_user.id
        country = _player_country(user_id)
        cid = country["id"] if country else None

        all_countries = db.get_all_countries()
        matches = [c for c in all_countries if c["id"] != cid and c.get("player_id") and (clean_q in _clean_persian_str(c.get("name", "")) or clean_q in _clean_persian_str(c.get("country_key", "")))]

        if not matches:
            await update.message.reply_text(
                f"❌ کشوری دارای بازیکن فعال با عنوان «{user_query}» یافت نشد.",
                reply_markup=_kb([
                    [InlineKeyboardButton("🔁 جستجوی مجدد", callback_data="mv:search_host")],
                    [InlineKeyboardButton("🔙 لیست قاره‌ها", callback_data="mv:newbase")]
                ]),
                parse_mode="Markdown"
            )
            return True

        rows = []
        row = []
        for c in matches:
            row.append(InlineKeyboardButton(f"{c['flag']} {c['name']}", callback_data=f"mv:nb:{c['id']}"))
            if len(row) == 2:
                rows.append(row)
                row = []
        if row:
            rows.append(row)

        rows.append([
            InlineKeyboardButton("🔁 جستجوی مجدد", callback_data="mv:search_host"),
            InlineKeyboardButton("🔙 لیست قاره‌ها", callback_data="mv:newbase")
        ])
        await update.message.reply_text(
            f"🔎 **نتایج جستجو برای «{user_query}»:**\n━━━━━━━━━━━━━━━━━━\nکشور میزبان را انتخاب فرمایید:",
            reply_markup=_kb(rows),
            parse_mode="Markdown"
        )
        return True

    d = context.user_data.get("mv_input")
    if not d:
        return False  # مربوط به ما نبود
    text = (update.message.text or "").strip()
    state = d.get("state")

    if state == "mv_name":
        if len(text) < 2 or len(text) > 40:
            await update.message.reply_text("❌ نام پایگاه باید ۲ تا ۴۰ نویسه باشد. دوباره بفرست:")
            return True
        d["name"] = text
        d["state"] = "mv_rent"
        await update.message.reply_text("۲️⃣ *اجاره روزانه* به میزبان چند دلار باشد؟ (عدد بفرست؛ ۰ مجاز است)", parse_mode="Markdown")
        return True

    if state == "mv_rent":
        val = _to_int(text)
        if val is None or val < 0 or val > 100_000_000:
            await update.message.reply_text("❌ لطفاً یک عدد معتبر (۰ تا ۱۰۰ میلیون) بفرست:")
            return True
        d["rent"] = val
        d["state"] = "mv_msg"
        await update.message.reply_text("۳️⃣ *پیام درخواست* را بنویس — به میزبان بگو در ازای این پایگاه چه می‌دهی:", parse_mode="Markdown")
        return True

    if state == "mv_msg":
        if len(text) < 5:
            await update.message.reply_text("❌ پیام خیلی کوتاه است؛ کمی توضیح بده:")
            return True
        d["msg"] = text[:600]
        d["state"] = "mv_preview"
        host = db.get_country_by_id(d["host_id"])
        esc_name = _md_escape(d["name"])
        esc_msg = _md_escape(d["msg"])
        preview_text = (
            f"📋 *پیش‌نمایش درخواست پایگاه*\n━━━━━━━━━━━━━━━━━━\n"
            f"🏠 نام: «{esc_name}»\n🗺 میزبان: {host['flag']} {host['name']}\n"
            f"💰 اجاره روزانه: {format_money(d['rent'])}\n\n"
            f"💳 هزینه ساخت:\n{_cost_str(config.BASE_BUILD_COST)}\n"
            f"📉 هزینه روزانه (خالی): {_cost_str(config.BASE_DAILY_FLAT)}\n"
            f"📈 + هر قلم: {_cost_str(config.BASE_DAILY_PER_ITEM)}\n\n"
            f"💬 پیام:\n{esc_msg}"
        )
        kb = _kb([
            [InlineKeyboardButton("📨 ارسال درخواست", callback_data="mv:nbconfirm")],
            [InlineKeyboardButton("❌ انصراف", callback_data="mv:newbase")],
        ])
        try:
            await update.message.reply_text(preview_text, reply_markup=kb, parse_mode="Markdown")
        except Exception:
            try:
                await update.message.reply_text(preview_text.replace("*", ""), reply_markup=kb)
            except Exception as e2:
                print(f"Base preview send error: {e2}")
        return True

    if state == "mv_qty":
        val = _to_int(text)
        if not val or val <= 0:
            await update.message.reply_text("❌ عدد نامعتبر؛ تعداد را دوباره بفرست:")
            return True
        ok, msg = db.deploy_to_base(d["base_id"], d["key"], val)
        context.user_data["mv_input"] = None
        if not ok:
            await update.message.reply_text(f"⛔ {msg}", reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به پایگاه", callback_data=f"mv:base:{d['base_id']}")]]))
            return True
        b = db.get_base(d["base_id"])
        await update.message.reply_text(
            f"✅ تجهیزات به پایگاه «{b['name']}» منتقل شد.\n\n" + _base_info_text(b),
            reply_markup=_kb([
                [InlineKeyboardButton("📍 پایگاه‌های من", callback_data="mv:mybases")],
                [InlineKeyboardButton("🎯 بازگشت به ستاد توسعه", callback_data="mv:menu")],
            ]),
            parse_mode="Markdown"
        )
        return True

    return False


def get_bases_handlers():
    return [
        CallbackQueryHandler(mv_callback_handler, pattern=r"^(?:mv:|bases:menu$)"),
        MessageHandler(filters.Regex(r"^(?:🎯 ستاد توسعه و اقدامات راهبردی|🎖️ تحرکات نظامی)$"), military_movements_menu),
    ]
