# -*- coding: utf-8 -*-
"""
ماژول سازمان ملل متحد (United Nations Module)
امکانات ویژه دبیرکل سازمان ملل (انحصاری ادمین اصلی):
صدور قطعنامه‌های شورای امنیت، سیستم رای‌گیری بین‌المللی با حق وتو،
استقرار نیروهای صلح‌بان کلاه‌آبی، تحریم‌های جامع، و صندوق امداد بشردوستانه.
"""

import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

import database as db
import config
import news_engine
from utils import format_money, format_number, format_oil, get_main_keyboard


async def require_un_or_admin(update: Update):
    user_id = update.effective_user.id
    if user_id not in config.ADMIN_IDS:
        if update.message:
            await update.message.reply_text("⛔ این بخش فقط برای دبیرکل سازمان ملل متحد مجاز است.", parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.answer("⛔ عدم دسترسی!", show_alert=True)
        return None, None

    country = db.get_country_by_player(user_id)
    if not country or country.get("country_key") != "un":
        if update.message:
            await update.message.reply_text(
                "🇺🇳 **اتاق مدیریت سازمان ملل متحد**\n\n"
                "جهت استفاده از اختیارات دبیرکل سازمان ملل، ابتدا باید نقش سازمان ملل را از پنل مدیریت (`/admin`) فعال فرمایید.",
                parse_mode="Markdown"
            )
        elif update.callback_query:
            await update.callback_query.answer("ابتدا نقش سازمان ملل را از پنل ادمین فعال کنید.", show_alert=True)
        return None, None

    return user_id, country


# ==================== اتاق دیپلماسی دبیرکل سازمان ملل ====================

async def un_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id, c = await require_un_or_admin(update)
    if not c:
        return

    text = (
        f"🇺🇳 **ستاد دبیرکل سازمان ملل متحد (United Nations Headquarters)**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"🏦 *صندوق امداد سازمان ملل:* **{format_money(c['treasury'])}**\n"
        f"🌾 *ذخیره استراتژیک غلات:* **{format_number(c['grain'])} تن**\n"
        f"👤 *یگان صلح‌بانان کلاه‌آبی:* **{format_number(c['active_personnel'])} نفر**\n\n"
        "جهت اعمال اختیارات دیپلماتیک و صلح بین‌المللی، بخش مورد نظر را انتخاب بفرمایید:"
    )

    keyboard = [
        [InlineKeyboardButton("📜 صدور قطعنامه و رای‌گیری شورای امنیت", callback_data="un:create_res")],
        [InlineKeyboardButton("📋 قطعنامه‌ها و رای‌گیری‌های فعال", callback_data="un:res_list")],
        [InlineKeyboardButton("🕊️ اعزام نیروهای صلح‌بان کلاه‌آبی", callback_data="un:peacekeeper_start")],
        [InlineKeyboardButton("📦 ارسال کمک‌های بشردوستانه سازمان ملل", callback_data="un:relief_start")],
        [InlineKeyboardButton("☢️ آژانس بین‌المللی انرژی اتمی (IAEA)", callback_data="un:iaea:menu")],
        [InlineKeyboardButton("🚫 تحریم‌های هدفمند سازمان ملل", callback_data="un:sanc:list:0")],
        [InlineKeyboardButton("📢 بیانیه رسمی دبیرکل سازمان ملل", callback_data="un:statement_start")],
        [InlineKeyboardButton("🔙 بازگشت به پنل مدیریت", callback_data="admin:menu")],
    ]

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== Callback Handler سازمان ملل ====================

# ==================== 🚫 تحریم‌های هدفمند سازمان ملل ====================

def _sanc_kb_back(cid=None):
    if cid:
        return [[InlineKeyboardButton("🔙 پرونده‌ی کشور", callback_data=f"un:sanc:country:{cid}")],
                [InlineKeyboardButton("🔙 فهرست کشورها", callback_data="un:sanc:list:0")]]
    return [[InlineKeyboardButton("🔙 ستاد سازمان ملل", callback_data="un:menu")]]


def _filter_sanction_countries(countries: list, cont: str | None = None,
                               q: str | None = None) -> list:
    """فیلتر کشورها برای پنل تحریم — بر اساس قاره و/یا جستجوی نام/کلید.
    تابع خالص است تا تست‌پذیر باشد. گروهک‌ها (faction_) زیر خاورمیانه می‌آیند."""
    out = countries
    if cont and cont != "all":
        cont_keys = config.CONTINENTS.get(cont, {}).get("keys", [])
        out = [x for x in out if (x.get("country_key") or "") in cont_keys
               or (cont == "mideast" and (x.get("country_key") or "").startswith("faction_"))]
    if q:
        q = q.lower().strip()
        out = [x for x in out
               if q in (x.get("name") or "").lower()
               or q in (x.get("country_key") or "").lower()]
    return out


async def _sanc_list_page(update, context, page: int, cont: str = "all"):
    user_id, c = await require_un_or_admin(update)
    if not c:
        return
    countries = [x for x in db.get_all_countries() if (x.get("country_key") or "") != "un"]
    countries = _filter_sanction_countries(countries, cont=cont)
    countries.sort(key=lambda x: x.get("name") or "")
    per, per_row = 12, 3
    total_pages = max(1, (len(countries) + per - 1) // per)
    page = max(0, min(page, total_pages - 1))
    chunk = countries[page * per:(page + 1) * per]

    cont_name = "همه‌ی قاره‌ها" if cont == "all" else \
        config.CONTINENTS.get(cont, {}).get("short_name", cont)
    text = ("🚫 **تحریم‌های هدفمند سازمان ملل**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"🌐 فیلتر: **{cont_name}** — {len(countries)} کشور (صفحه {page + 1}/{total_pages})\n\n"
            "هر نوع تحریم **جداگانه** اعمال و لغو می‌شود:\n")
    for key, spec in config.UN_TARGETED_SANCTIONS.items():
        text += f"• {spec['label']}\n"

    rows = [
        [InlineKeyboardButton("📋 تحریم‌های فعال (همه‌ی کشورها)", callback_data="un:sanc:active:0"),
         InlineKeyboardButton("🔎 جستجوی کشور", callback_data="un:sanc:search")],
    ]
    cont_row = []
    for ckey, cspec in config.CONTINENTS.items():
        mark = "●" if ckey == cont else "○"
        cont_row.append(InlineKeyboardButton(
            f"{mark}{cspec.get('emoji', '')}", callback_data=f"un:sanc:list:0:{ckey}"))
    if cont != "all":
        cont_row.append(InlineKeyboardButton("🌐 همه", callback_data="un:sanc:list:0:all"))
    rows.append(cont_row)

    for i in range(0, len(chunk), per_row):
        rows.append([InlineKeyboardButton(
            f"{x.get('flag', '🏳️')} {x.get('name', '')}",
            callback_data=f"un:sanc:country:{x['id']}") for x in chunk[i:i + per_row]])
    if not chunk:
        rows.append([InlineKeyboardButton("— کشوری در این فیلتر نیست —", callback_data="un:noop")])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"un:sanc:list:{page - 1}:{cont}"))
    nav.append(InlineKeyboardButton(f"{page + 1}/{total_pages}", callback_data="un:noop"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"un:sanc:list:{page + 1}:{cont}"))
    rows.append(nav)
    rows.append([InlineKeyboardButton("🔙 ستاد سازمان ملل", callback_data="un:menu")])
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows), parse_mode="Markdown")


async def _sanc_active_page(update, context, page: int, notice: str = ""):
    user_id, c = await require_un_or_admin(update)
    if not c:
        return
    actives = db.get_all_active_targeted_sanctions(limit=300)
    per = 10
    total_pages = max(1, (len(actives) + per - 1) // per)
    page = max(0, min(page, total_pages - 1))
    chunk = actives[page * per:(page + 1) * per]

    text = (f"📋 **تحریم‌های فعال سازمان ملل** ({len(actives)} مورد — صفحه {page + 1}/{total_pages})\n"
            "━━━━━━━━━━━━━━━━━━\n\n")
    rows = []
    if not chunk:
        text += "✅ هیچ تحریم هدفمندی روی هیچ کشوری فعال نیست."
    for s in chunk:
        spec = config.UN_TARGETED_SANCTIONS.get(s["sanction_key"], {})
        label = spec.get("label", s["sanction_key"])
        reason = str(s.get("reason") or "").strip()
        created = str(s.get("created_at") or "")[:16].replace("T", " ")
        text += (f"• {s.get('country_flag', '')} **{s.get('country_name', '')}** — {label}"
                 + (f"\n   ↳ {reason}" if reason else "")
                 + (f" | از {created}" if created else "") + "\n")
        rows.append([
            InlineKeyboardButton(f"⛔ لغو {label} — {s.get('country_name', '')}",
                                 callback_data=f"un:sanc:quicklift:{s['country_id']}:{s['sanction_key']}:{page}"),
            InlineKeyboardButton("📋", callback_data=f"un:sanc:country:{s['country_id']}"),
        ])
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"un:sanc:active:{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"un:sanc:active:{page + 1}"))
    if nav:
        rows.append(nav)
    rows.append([InlineKeyboardButton("🔙 فهرست کشورها", callback_data="un:sanc:list:0:all")])
    rows.append([InlineKeyboardButton("🔙 ستاد سازمان ملل", callback_data="un:menu")])
    if notice:
        text = f"✅ {notice}\n\n" + text
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows), parse_mode="Markdown")


async def _sanc_search_prompt(update, context):
    user_id, c = await require_un_or_admin(update)
    if not c:
        return
    context.user_data["un_sanc_search"] = True
    await update.callback_query.edit_message_text(
        "🔎 **جستجوی کشور برای تحریم**\n\n"
        "نام کشور یا کلید آن را بفرست (مثلاً: `انگلیس` یا `uk`).\n"
        "برای انصراف، دکمه‌ی پایین را بزن.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(
            "❌ انصراف", callback_data="un:sanc:list:0:all")]]),
        parse_mode="Markdown")


async def _sanc_search_handle(update, context, text: str) -> bool:
    """جستجوی متنی کشور در پنل تحریم. خروجی: آیا فلگ سرچ مصرف شد؟"""
    if not context.user_data.get("un_sanc_search"):
        return False
    context.user_data["un_sanc_search"] = None
    user_id = update.effective_user.id
    if user_id not in config.ADMIN_IDS:
        return True
    countries = [x for x in db.get_all_countries() if (x.get("country_key") or "") != "un"]
    hits = _filter_sanction_countries(countries, q=text)[:8]
    if not hits:
        await update.message.reply_text(
            f"❌ کشوری با «{text}» پیدا نشد. دوباره تلاش کن یا از فهرست قاره‌ای استفاده کن.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 فهرست کشورها", callback_data="un:sanc:list:0:all"),
                InlineKeyboardButton("🔎 دوباره", callback_data="un:sanc:search")]]))
        return True
    rows = [[InlineKeyboardButton(f"{x.get('flag', '🏳️')} {x.get('name', '')}",
                                  callback_data=f"un:sanc:country:{x['id']}")]
            for x in hits]
    rows.append([InlineKeyboardButton("🔎 جستجوی دیگر", callback_data="un:sanc:search"),
                 InlineKeyboardButton("🔙 فهرست کشورها", callback_data="un:sanc:list:0:all")])
    await update.message.reply_text(f"🔎 {len(hits)} نتیجه برای «{text}»:",
                                    reply_markup=InlineKeyboardMarkup(rows))
    return True


async def _sanc_country_panel(update, context, cid: int, notice: str = ""):
    user_id, c = await require_un_or_admin(update)
    if not c:
        return
    target = db.get_country_by_id(cid)
    if not target:
        await update.callback_query.edit_message_text(
            "❌ کشور یافت نشد.", reply_markup=InlineKeyboardMarkup(_sanc_kb_back()))
        return

    active = {s["sanction_key"]: s for s in db.get_targeted_sanctions(cid)}
    text = (f"🚫 **تحریم‌های هدفمند — {target.get('flag', '')} {target.get('name', '')}**\n"
            "━━━━━━━━━━━━━━━━━━\n\n")
    if active:
        text += "⛔ **تحریم‌های فعال:**\n"
        for key, row in active.items():
            spec = config.UN_TARGETED_SANCTIONS.get(key, {})
            created = str(row.get("created_at") or "")[:16].replace("T", " ")
            text += f"• {spec.get('label', key)}" + (f" (از {created})" if created else "") + "\n"
            if row.get("reason"):
                text += f"   ↳ دلیل: {row['reason']}\n"
    else:
        text += "✅ هیچ تحریم هدفمندی فعال نیست.\n"
    text += "\nبرای اعمال یا لغو، روی هر نوع بزنید (دونه‌دونه):"

    rows = []
    for key, spec in config.UN_TARGETED_SANCTIONS.items():
        mark = "⛔ لغو" if key in active else "➕ اعمال"
        rows.append([InlineKeyboardButton(
            f"{mark} — {spec['label']}", callback_data=f"un:sanc:ask:{cid}:{key}")])
    rows.append([InlineKeyboardButton("📋 تحریم‌های فعال (همه‌ی کشورها)", callback_data="un:sanc:active:0")])
    rows.append([InlineKeyboardButton("🔙 فهرست کشورها", callback_data="un:sanc:list:0:all")])
    if notice:
        text = f"✅ {notice}\n\n" + text
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows), parse_mode="Markdown")


async def _sanc_confirm(update, context, cid: int, key: str):
    user_id, c = await require_un_or_admin(update)
    if not c:
        return
    target = db.get_country_by_id(cid)
    if not target:
        await update.callback_query.edit_message_text("❌ کشور یافت نشد.", reply_markup=InlineKeyboardMarkup(_sanc_kb_back()))
        return
    spec = config.UN_TARGETED_SANCTIONS.get(key)
    if not spec:
        await update.callback_query.answer("نوع تحریم نامعتبر است.", show_alert=True)
        return
    imposing = not db.has_targeted_sanction(cid, key)
    verb = "اعمال" if imposing else "لغو"
    text = (f"{'🚫' if imposing else '✅'} **تأیید {verb} تحریم**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• کشور: {target.get('flag', '')} {target.get('name', '')}\n"
            f"• نوع: {spec['label']}\n"
            f"• اثر: {spec['desc']}\n\n"
            "مطمئنی؟")
    rows = [
        [InlineKeyboardButton(f"✅ بله، {verb} کن", callback_data=f"un:sanc:do:{cid}:{key}")],
        [InlineKeyboardButton("🔙 پرونده‌ی کشور", callback_data=f"un:sanc:country:{cid}")],
    ]
    await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows), parse_mode="Markdown")


async def un_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id

    await query.answer()

    # ☢️ مسیر اختصاصی آژانس انرژی اتمی
    if data.startswith("un:iaea:"):
        await iaea_callback_handler(update, context)
        return

    # 🚫 مسیر تحریم‌های هدفمند
    if data.startswith("un:sanc:"):
        parts = data.split(":")
        if parts[2] == "list":
            cont = parts[4] if len(parts) > 4 else "all"
            await _sanc_list_page(update, context, int(parts[3]) if len(parts) > 3 else 0, cont)
        elif parts[2] == "country":
            await _sanc_country_panel(update, context, int(parts[3]))
        elif parts[2] == "ask":
            await _sanc_confirm(update, context, int(parts[3]), parts[4])
        elif parts[2] == "active":
            await _sanc_active_page(update, context, int(parts[3]) if len(parts) > 3 else 0)
        elif parts[2] == "search":
            await _sanc_search_prompt(update, context)
        elif parts[2] == "quicklift":
            cid, key = int(parts[3]), parts[4]
            back_page = int(parts[5]) if len(parts) > 5 else 0
            user_id2, c = await require_un_or_admin(update)
            if not c:
                return
            ok, msg = db.remove_targeted_sanction(cid, key, removed_by=user_id2)
            if not ok:
                await update.callback_query.answer(f"⚠️ {msg}", show_alert=True)
                await _sanc_active_page(update, context, back_page)
                return
            target = db.get_country_by_id(cid)
            if target:
                try:
                    await news_engine.trigger_un_targeted_sanction_news(
                        context.bot, target,
                        config.UN_TARGETED_SANCTIONS.get(key, {}).get("label", key), False)
                except Exception:
                    pass
            await _sanc_active_page(update, context, back_page, notice=msg)
        elif parts[2] == "do":
            cid, key = int(parts[3]), parts[4]
            user_id2, c = await require_un_or_admin(update)
            if not c:
                return
            target = db.get_country_by_id(cid)
            if not target:
                await query.answer("کشور یافت نشد.", show_alert=True)
                return
            imposing = not db.has_targeted_sanction(cid, key)
            if imposing:
                ok, msg = db.apply_targeted_sanction(cid, key,
                                                     reason="تصویب شورای امنیت",
                                                     imposed_by=user_id2)
            else:
                ok, msg = db.remove_targeted_sanction(cid, key, removed_by=user_id2)
            if not ok:
                await query.answer(f"⚠️ {msg}", show_alert=True)
                return
            spec = config.UN_TARGETED_SANCTIONS.get(key, {})
            try:
                await news_engine.trigger_un_targeted_sanction_news(
                    context.bot, target, spec.get("label", key), imposing)
            except Exception:
                pass
            await _sanc_country_panel(update, context, cid, notice=msg)
        return

    if data == "un:menu":
        await un_main_menu(update, context)

    elif data == "un:create_res":
        user_id, c = await require_un_or_admin(update)
        if not c:
            return

        context.user_data["un_draft"] = {"step": "res_title"}
        text = (
            "📜 **صدور قطعنامه جدید شورای امنیت سازمان ملل (UN Resolution)**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً **عنوان و شماره قطعنامه** (مانند: `قطعنامه ۲۲۳۱ — الزام به اعلام آتش‌بس فوری`) را ارسال فرمایید:"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="un:menu")]]), parse_mode="Markdown")

    elif data == "un:res_list":
        resolutions = db.get_un_resolutions("active")

        lines = ["📋 **قطعنامه‌ها و رای‌گیری‌های فعال شورای امنیت سازمان ملل**\n━━━━━━━━━━━━━━━━━━\n"]
        keyboard = []

        if not resolutions:
            lines.append("در حال حاضر هیچ قطعنامه فعالی در شورای امنیت در حال رای‌گیری نیست.")
        else:
            for res in resolutions:
                r_id = res["id"]
                r_title = res["title"]
                r_desc = res["description"]
                votes = db.get_un_resolution_votes(r_id)

                yes_count = len(votes["yes"])
                no_count = len(votes["no"])
                abs_count = len(votes["abstain"])

                lines.append(f"• **قطعنامه #{r_id}: {r_title}**")
                lines.append(f"  _{r_desc}_")
                lines.append(f"  آراء تا کنون: ✅ {yes_count} موافق | ❌ {no_count} مخالف | ⚪ {abs_count} ممتنع\n")

                if user_id in config.ADMIN_IDS:
                    keyboard.append([
                        InlineKeyboardButton(f"✅ تصویب #{r_id}", callback_data=f"un:close_res:{r_id}:passed"),
                        InlineKeyboardButton(f"⛔ وتو/رد #{r_id}", callback_data=f"un:close_res:{r_id}:vetoed")
                    ])

        keyboard.append([InlineKeyboardButton("🔙 بازگشت به ستاد سازمان ملل", callback_data="un:menu")])
        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("un_vote:"):
        # رای‌گیری توسط بازیکنان عادی
        parts = data.split(":")
        res_id = int(parts[1])
        vote_opt = parts[2] # 'yes', 'no', 'abstain'

        voter_c = db.get_country_by_player(user_id)
        if not voter_c:
            await query.answer("شما هنوز کشوری ندارید!", show_alert=True)
            return

        success, msg = db.cast_un_vote(res_id, voter_c["id"], vote_opt)

        if success:
            opt_labels = {"yes": "✅ موافق", "no": "❌ مخالف", "abstain": "⚪ ممتنع"}
            await query.answer(f"رای {opt_labels[vote_opt]} کشور {voter_c['name']} در شورای امنیت ثبت گردید!", show_alert=True)
        else:
            await query.answer(f"❌ {msg}", show_alert=True)

    elif data.startswith("un:close_res:"):
        # این callback فقط باید برای دبیرکل/ادمین صاحب نقش UN قابل اجرا باشد؛
        # دکمه‌های inline ممکن است از یک پیام فورواردشده هم کلیک شوند.
        _, un_country = await require_un_or_admin(update)
        if not un_country:
            return

        parts = data.split(":")
        if len(parts) != 4 or parts[3] not in {"passed", "vetoed"}:
            await query.answer("نتیجه نهایی قطعنامه نامعتبر است.", show_alert=True)
            return
        res_id = int(parts[2])
        final_status = parts[3]

        res = db.get_un_resolution_by_id(res_id)
        if not res:
            await query.answer("قطعنامه یافت نشد.", show_alert=True)
            return

        if not db.close_un_resolution(res_id, final_status):
            await query.answer("این قطعنامه قبلاً تعیین تکلیف شده است.", show_alert=True)
            return
        votes = db.get_un_resolution_votes(res_id)

        yes_str = ", ".join([f"{v['flag']} {v['name']}" for v in votes["yes"]]) or "هیچ"
        no_str = ", ".join([f"{v['flag']} {v['name']}" for v in votes["no"]]) or "هیچ"

        status_text = "✅ **تصویب و لازم‌الاجرا شد**" if final_status == "passed" else "⛔ **وتو / رد شد**"

        broadcast_msg = (
            f"🇺🇳 **نتیجه رسمی رای‌گیری شورای امنیت سازمان ملل**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• **قطعنامه #{res_id}:** {res['title']}\n"
            f"• **وضعیت نهایی:** {status_text}\n\n"
            f"📊 **تفکیک آراء کشورها:**\n"
            f"• **کشورهای موافق ({len(votes['yes'])}):** {yes_str}\n"
            f"• **کشورهای مخالف ({len(votes['no'])}):** {no_str}\n"
            f"• **آراء ممتنع:** {len(votes['abstain'])} کشور\n\n"
            f"📌 _طبق منشور ملل متحد، مفاد قطعنامه‌های تصویب‌شده شورای امنیت برای کلیه دول عضو لازم‌الاجرا می‌باشد._"
        )

        # Broadcast to all players
        all_countries = db.get_all_countries()
        for c_item in all_countries:
            p_id = c_item.get("player_id")
            if p_id:
                try:
                    await context.bot.send_message(chat_id=p_id, text=broadcast_msg, parse_mode="Markdown")
                except Exception:
                    pass

        await query.edit_message_text(
            f"✅ **نتیجه قطعنامه #{res_id} رسماً اعلام و به تمام بازیکنان برودکست گردید.**\n\n{broadcast_msg}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به سازمان ملل", callback_data="un:menu")]]),
            parse_mode="Markdown"
        )

    elif data == "un:peacekeeper_start":
        user_id, c = await require_un_or_admin(update)
        if not c:
            return

        context.user_data["un_draft"] = {"step": "peacekeeper"}
        text = (
            "🕊️ **استقرار نیروهای صلح‌بان کلاه‌آبی سازمان ملل (UN Peacekeepers)**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً **نام کشور یا منطقه حائل هدف** و **جزئیات ماموریت صلح‌بانی** را ارسال فرمایید:"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="un:menu")]]), parse_mode="Markdown")

    elif data == "un:relief_start":
        user_id, c = await require_un_or_admin(update)
        if not c:
            return

        context.user_data["un_draft"] = {"step": "relief"}
        text = (
            "📦 **صندوق امداد و کمک‌های بشردوستانه سازمان ملل (UN Relief Fund)**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً **نام کشور دریافت‌کننده** و **مبلغ یا میزان غلات اهدایی** را ارسال فرمایید:"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="un:menu")]]), parse_mode="Markdown")

    elif data == "un:statement_start":
        user_id, c = await require_un_or_admin(update)
        if not c:
            return

        context.user_data["un_draft"] = {"step": "statement"}
        text = (
            "📢 **بیانیه رسمی دبیرکل سازمان ملل متحد**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً **متن بیانیه رسمی دبیرکل** را ارسال فرمایید (این پیام مستقیماً برای تمامی بازیکنان برودکست خواهد شد):"
        )
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="un:menu")]]), parse_mode="Markdown")


# ==================== Text Input Handler سازمان ملل ====================

async def un_text_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # 🔎 جستجوی کشور در پنل تحریم‌های هدفمند
    if context.user_data.get("un_sanc_search"):
        text = (update.message.text or "").strip()
        if text:
            await _sanc_search_handle(update, context, text)
        return
    draft = context.user_data.get("un_draft")
    if not draft:
        return

    text = (update.message.text or update.message.caption or "").strip()
    if not text:
        await update.message.reply_text("لطفاً متن را بفرست.")
        return
    step = draft.get("step")

    if step == "res_title":
        draft["res_title"] = text
        draft["step"] = "res_desc"
        await update.message.reply_text(
            f"✅ **عنوان ثبت شد:** `{text}`\n\nحال لطفاً **متن کامل و مفاد قطعنامه شورای امنیت** را ارسال فرمایید:",
            parse_mode="Markdown"
        )

    elif step == "res_desc":
        res_title = draft.get("res_title", "قطعنامه شورای امنیت")
        res_desc = text
        del context.user_data["un_draft"]

        res_id = db.create_un_resolution(res_title, res_desc, user_id)

        broadcast_msg = (
            f"📜 **قطعنامه جدید شورای امنیت سازمان ملل متحد (قطعنامه #{res_id})**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• **عنوان:** {res_title}\n\n"
            f"📋 **مفاد قطعنامه:**\n"
            f'"{res_desc}"\n\n'
            f"📌 _از کلیه دول عضو دعوت می‌شود رای رسمی خود را در خصوص این قطعنامه ثبت نمایند:_"
        )

        vote_keyboard = [
            [
                InlineKeyboardButton("✅ موافق", callback_data=f"un_vote:{res_id}:yes"),
                InlineKeyboardButton("❌ مخالف", callback_data=f"un_vote:{res_id}:no"),
                InlineKeyboardButton("⚪ ممتنع", callback_data=f"un_vote:{res_id}:abstain"),
            ]
        ]

        # Broadcast resolution to all players
        all_countries = db.get_all_countries()
        sent_count = 0
        for c_item in all_countries:
            p_id = c_item.get("player_id")
            if p_id:
                try:
                    await context.bot.send_message(
                        chat_id=p_id,
                        text=broadcast_msg,
                        reply_markup=InlineKeyboardMarkup(vote_keyboard),
                        parse_mode="Markdown"
                    )
                    sent_count += 1
                except Exception:
                    pass

        await update.message.reply_text(
            f"✅ **قطعنامه #{res_id} با موفقیت صادر و رای‌گیری آنلاین آن برای {sent_count} کشور فعال گردید.**",
            reply_markup=get_main_keyboard(user_id),
            parse_mode="Markdown"
        )

    elif step == "peacekeeper":
        del context.user_data["un_draft"]
        msg = (
            f"🕊️ **دستور دبیرکل سازمان ملل متحد — ماموریت صلح‌بانی**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f'"{text}"\n\n'
            f"📌 _یگان صلح‌بانان کلاه‌آبی سازمان ملل متحد (UN Peacekeepers) به منطقه اعزام شدند._"
        )
        all_countries = db.get_all_countries()
        for c_item in all_countries:
            p_id = c_item.get("player_id")
            if p_id:
                try: await context.bot.send_message(chat_id=p_id, text=msg, parse_mode="Markdown")
                except Exception: pass

        await update.message.reply_text("✅ دستور اعزام صلح‌بانان ابلاغ گردید.", reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")

    elif step == "relief":
        del context.user_data["un_draft"]
        msg = (
            f"📦 **ابلاغیه کمک‌های بشردوستانه سازمان ملل متحد**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f'"{text}"\n\n'
            f"📌 _کمک‌های غذایی و مالی از محل صندوق امداد سازمان ملل تخصیص یافت._"
        )
        all_countries = db.get_all_countries()
        for c_item in all_countries:
            p_id = c_item.get("player_id")
            if p_id:
                try: await context.bot.send_message(chat_id=p_id, text=msg, parse_mode="Markdown")
                except Exception: pass

        await update.message.reply_text("✅ کمک‌های بشردوستانه صادر و ابلاغ گردید.", reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")

    elif step == "iaea_cap":
        t_id = draft.get("target_id")
        clean_val = (
            str(text)
            .translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"))
            .replace("٬", "").replace(",", "").replace("_", "").strip()
        )
        if not re.fullmatch(r"-?\d+", clean_val):
            await update.message.reply_text(
                "⛔ لطفاً فقط یک عدد صحیح ارسال کنید (مثلاً `10` یا `۱۰` یا `-1`).",
                parse_mode="Markdown"
            )
            return
        val = int(clean_val)
        if val < -1 or val > 10000:
            await update.message.reply_text("⛔ بازه مجاز: `-1` تا `10000`.", parse_mode="Markdown")
            return
        target = db.get_country_by_id(t_id)
        if not target:
            del context.user_data["un_draft"]
            await update.message.reply_text("⛔ کشور یافت نشد.")
            return
        del context.user_data["un_draft"]
        db.set_warhead_cap_override(t_id, val)
        if val >= 0:
            db.add_transaction(t_id, "iaea_cap", f"⚖️ آژانس سقف اختصاصی نگهداری کلاهک کشور شما را به {val} عدد تعیین کرد.", 0)
            try:
                if target.get("player_id"):
                    await context.bot.send_message(
                        target["player_id"],
                        f"⚖️ **ابلاغیه آژانس بین‌المللی انرژی اتمی**\n\n سقف مجاز نگهداری کلاهک هسته‌ای برای کشور {target['flag']} *{target['name']}* به تعداد *{val}* تعیین گردید.\n\n_IAEA — وین_",
                        parse_mode="Markdown"
                    )
            except Exception:
                pass
            confirm = (
                f"✅ سقف اختصاصی {target['flag']} *{target['name']}* روی **{val} کلاهک** تنظیم شد "
                "و به کشور ابلاغ گردید."
            )
        else:
            db.add_transaction(t_id, "iaea_cap", "⚖️ سقف اختصاصی کلاهک کشور شما لغو و به قانون پیش‌فرض بازگشت.", 0)
            confirm = (
                f"✅ سقف اختصاصی {target['flag']} *{target['name']}* حذف شد — قانون پیش‌فرض اعمال می‌شود "
                "(P5/خارج از NPT: نامحدود، بقیه: ۵ کلاهک)."
            )
        await update.message.reply_text(
            confirm,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🔍 مشاهده پرونده به‌روزشده", callback_data=f"un:iaea:dossier:{t_id}")]
            ]),
            parse_mode="Markdown"
        )
        return

    elif step == "statement":
        del context.user_data["un_draft"]
        msg = (
            f"📢 **بیانیه رسمی دبیرکل سازمان ملل متحد (UN Secretary-General)**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f'"{text}"\n\n'
            f"📌 _نیویورک — مقر اصلی سازمان ملل متحد_"
        )
        all_countries = db.get_all_countries()
        for c_item in all_countries:
            p_id = c_item.get("player_id")
            if p_id:
                try: await context.bot.send_message(chat_id=p_id, text=msg, parse_mode="Markdown")
                except Exception: pass

        try:
            await news_engine.post_breaking_news(
                context.bot,
                news_title="بیانیه رسمی دبیرکل سازمان ملل متحد",
                news_body=text,
                event_category="سازمان ملل متحد"
            )
        except Exception:
            pass

        await update.message.reply_text("✅ بیانیه رسمی دبیرکل با موفقیت برای تمامی بازیکنان و کانال اصلی برودکست شد.", reply_markup=get_main_keyboard(user_id), parse_mode="Markdown")


# ==================== ☢️ آژانس بین‌المللی انرژی اتمی (IAEA) ====================

IAEA_P5 = ("usa", "russia", "china", "france", "uk", "pakistan", "india", "israel", "north_korea")


def _iaea_nuclear_countries():
    """فهرست کشورهای دارای فعالیت هسته‌ای (مرتب: کلاهک، سپس اورانیوم تسلیحاتی و سوخت)."""
    result = []
    for c in db.get_all_countries():
        if c.get("country_key") == "un":
            continue
        wh = c.get("warheads") or 0
        w90 = c.get("weapons_grade_90") or 0
        e60 = c.get("enriched_60") or 0
        fuel = c.get("nuclear_fuel") or 0
        med = c.get("medical_isotopes") or 0
        u_ore = c.get("uranium_ore") or 0
        f_daily = c.get("nuclear_fuel_daily") or 0
        u_daily = c.get("uranium_ore_daily") or 0
        tested = c.get("nuclear_tested") or 0
        if wh == 0 and w90 == 0 and e60 == 0 and fuel == 0 and med == 0 and u_ore == 0 and f_daily == 0 and u_daily == 0 and tested == 0:
            continue
        result.append(c)
    result.sort(key=lambda c: ((c.get("warheads") or 0) * 1000 + (c.get("weapons_grade_90") or 0) * 10 + (c.get("enriched_60") or 0) * 5 + (c.get("nuclear_fuel") or 0)), reverse=True)
    return result


def _iaea_facilities(country_id):
    """تعداد معدن اورانیوم و مجتمع غنی‌سازیِ مالکیت کشور."""
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute("SELECT item_key, quantity FROM equipment WHERE country_id = ?", (country_id,))
    rows = cur.fetchall()
    conn.close()
    mines = sum((r["quantity"] or 0) for r in rows if r["item_key"] == "uranium_mine")
    enr = sum((r["quantity"] or 0) for r in rows if r["item_key"] == "enrichment_facility")
    return mines, enr


def _iaea_cap_of(c: dict):
    """سقف مؤثر کلاهک کشور (اختصاصی مصوب آژانس > P5 نامحدود > خارج از NPT نامحدود > قانون عام)."""
    return db.get_effective_warhead_cap(c)


def _iaea_monitor_text():
    """🛰️ متن گزارش نظارت جهانی."""
    rows = _iaea_nuclear_countries()
    cap_non_p5 = int(getattr(config, "WARHEAD_MAX_NON_SUPERPOWER", 5))
    lines = [
        "🛰️ **گزارش نظارت جهانی هسته‌ای — IAEA**",
        "━━━━━━━━━━━━━━━━━━", ""
    ]
    if not rows:
        lines.append("در حال حاضر هیچ کشوری دارای برنامه هسته‌ای فعال نیست. ✅")
    violators = []
    suspended_list = []
    npt_out_list = []
    for i, c in enumerate(rows[:25], start=1):
        wh = c.get("warheads") or 0
        p5 = " 🔷P5" if c.get("country_key") in IAEA_P5 else ""
        susp = ""
        if (c.get("enrichment_suspended") or 0):
            susp = " ⛔تعلیق‌شده"
            suspended_list.append(f"{c['flag']} {c['name']}")
        npt_out = " 🚫خارج از NPT" if (c.get("npt_withdrawn") or 0) else ""
        if npt_out:
            npt_out_list.append(f"{c['flag']} {c['name']}")
        threat_tags = []
        if (c.get("weapons_grade_90") or 0) > 0:
            threat_tags.append("🔴 تسلیحاتی ۹۰٪")
        elif (c.get("enriched_60") or 0) > 0:
            threat_tags.append("🟠 آستانه گریز ۶۰٪")
        elif (c.get("medical_isotopes") or 0) > 0:
            threat_tags.append("🟡 پزشکی ۲۰٪")
        threat_str = f" [{' | '.join(threat_tags)}]" if threat_tags else ""

        lines.append(
            f"{i}. {c['flag']} *{c['name']}*{p5}{susp}{npt_out}{threat_str}\n"
            f"   ☢️ کلاهک: *{format_number(wh)}* | 🧪 سوخت: {format_number(c.get('nuclear_fuel') or 0)} ک‌گ | "
            f"⛏️ اورانیوم: {format_number(c.get('uranium_ore') or 0)} تن"
        )
        cap = _iaea_cap_of(c)
        if cap is not None and wh > cap and not (c.get("npt_withdrawn") or 0):
            violators.append(f"{c['flag']} {c['name']} ({format_number(wh)} کلاهک؛ سقف: {cap})")
    if len(rows) > 25:
        lines.append(f"\n… و {len(rows) - 25} کشور دیگر.")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━")
    if violators:
        lines.append("⚠️ *متخلفان از سقف عدم اشاعه:*")
        for v in violators:
            lines.append(f"   • {v}")
    if suspended_list:
        lines.append("⛔ *برنامه‌های غنی‌سازی تعلیق‌شده:*")
        for s in suspended_list:
            lines.append(f"   • {s}")
    if npt_out_list:
        lines.append("🚫 *کشورهای خارج از پیمان عدم اشاعه (NPT):*")
        for n in npt_out_list:
            sanc_mark = ""
            lines.append(f"   • {n}")
    if not violators and not suspended_list and not npt_out_list:
        lines.append("✅ هیچ تخلفی از پیمان عدم اشاعه (NPT) ثبت نشده است.")
    lines.append("\n_ابزار نظارتی آژانس بین‌المللی انرژی اتمی — وین_")
    return "\n".join(lines)


def _iaea_dossier_text(c: dict):
    """🔍 متن پرونده بازرسی فنی یک کشور."""
    mines, enr = _iaea_facilities(c["id"])
    wh = c.get("warheads") or 0
    cap = _iaea_cap_of(c)
    suspended = bool(c.get("enrichment_suspended") or 0)

    npt_out = bool(c.get("npt_withdrawn") or 0)
    sanc = bool(c.get("un_sanctioned") or 0)
    override = c.get("warhead_cap_override")
    has_override = override is not None and override >= 0

    if has_override:
        cap_line = f"{format_number(override)} (مصوب ویژه آژانس ⚖️)"
        status = ("✅ منطبق" if wh <= (cap or 0) else f"⚠️ متخلف ({format_number(wh - (cap or 0))} کلاهک مازاد بر سقف)")
    elif cap is None:
        cap_line = "نامحدود (قدرت هسته‌ای P5) 🔷"
        status = "✅ منطبق"
    elif npt_out:
        cap_line = "نامحدود (خارج از NPT 🚫)"
        status = "🚫 خارج از پیمان — خارج از صلاحدید آژانس"
    else:
        cap_line = format_number(cap)
        status = ("✅ منطبق" if wh <= cap else f"⚠️ متخلف ({format_number(wh - cap)} کلاهک مازاد بر سقف)")

    fac_parts = []
    if mines:
        fac_parts.append(f"⛏️ معدن اورانیوم ×{format_number(mines)}")
    if enr:
        fac_parts.append(f"🔬 مجتمع غنی‌سازی ×{format_number(enr)}")
    facilities = " | ".join(fac_parts) if fac_parts else "ندارد"

    tier = c.get("enrichment_tier", 1) or 1
    tier_name = config.ENRICHMENT_TIERS.get(tier, {}).get("name", "پله ۱")
    tested = bool(c.get("nuclear_tested", 0))

    text = (
        f"🔍 **پرونده بازرسی فنی هسته‌ای آژانس (IAEA) — {c['flag']} {c['name']}**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"☢️ *کلاهک‌های استراتژیک مستقر:* {format_number(wh)}\n"
        f"📋 *سقف مجاز نگهداری:* {cap_line} → *وضعیت:* {status}\n"
        f"💥 *آزمایش انفجار هسته‌ای (فاز ۴):* {'✅ انجام شده' if tested else '❌ انجام نشده'}\n"
        f"⚙️ *دکترین فعال سانتریفیوژها:* {tier_name}\n\n"
        f"🔴 *اورانیوم تسلیحاتی (۹۰٪):* {format_number(c.get('weapons_grade_90') or 0)} کیلوگرم\n"
        f"🟠 *اورانیوم آستانه گریز (۶۰٪):* {format_number(c.get('enriched_60') or 0)} کیلوگرم\n"
        f"🟡 *ایزوتوپ پزشکی و پیشران (۲۰٪):* {format_number(c.get('medical_isotopes') or 0)} کیلوگرم (+{format_number(c.get('medical_isotopes_daily') or 0)}/روز)\n"
        f"🟢 *سوخت راکتور نیروگاهی (۳.۵٪):* {format_number(c.get('nuclear_fuel') or 0)} کیلوگرم (+{format_number(c.get('nuclear_fuel_daily') or 0)}/روز)\n"
        f"⛏️ *کیک زرد اورانیوم خام:* {format_number(c.get('uranium_ore') or 0)} تن (+{format_number(c.get('uranium_ore_daily') or 0)}/روز)\n\n"
        f"🏭 *تأسیسات چرخه سوخت:* {facilities}\n"
        f"🔬 *سطح فناوری:* سطح {format_number(c.get('tech_level') or 1)}\n"
        f"⚖️ *وضعیت غنی‌سازی:* {'⛔ تعلیق‌شده به دستور آژانس' if suspended else '✅ فعال'}\n"
        f"📜 *پیمان عدم اشاعه:* {'🚫 خارج از پیمان NPT' if npt_out else '✅ عضو متعهد NPT'}\n"
        f"🌐 *تحریم جامع سازمان ملل:* {'🚫 تحت تحریم جامع' if sanc else 'ندارد'}\n\n"
        "_بازرسی فنی و ارزیابی ریسک — بازرسان رسمی آژانس، وین_"
    )
    return text


def _iaea_report_body():
    """متن گزارش عمومی آژانس برای برودکست."""
    rows = _iaea_nuclear_countries()
    total_wh = sum((c.get("warheads") or 0) for c in rows)
    violators = []
    suspended = []
    npt_outside = []
    sanctioned = []
    for c in rows:
        cap = _iaea_cap_of(c)
        if cap is not None and (c.get("warheads") or 0) > cap and not (c.get("npt_withdrawn") or 0):
            violators.append(f"{c['flag']} {c['name']}")
        if c.get("enrichment_suspended") or 0:
            suspended.append(f"{c['flag']} {c['name']}")
        if c.get("npt_withdrawn") or 0:
            npt_outside.append(f"{c['flag']} {c['name']}")
        if c.get("un_sanctioned") or 0:
            sanctioned.append(f"{c['flag']} {c['name']}")
    top = rows[:3]
    top_str = " | ".join(f"{c['flag']} {c['name']} ({format_number(c.get('warheads') or 0)})" for c in top) if top else "—"

    body = (
        f"• کشورهای دارای برنامه هسته‌ای فعال: {format_number(len(rows))}\n"
        f"• مجموع کلاهک‌های استراتژیک جهان: {format_number(total_wh)}\n"
        f"• بزرگ‌ترین زرادخانه‌ها: {top_str}\n"
        f"• متخلفان از سقف عدم اشاعه: {'، '.join(violators) if violators else 'موردی ثبت نشد ✅'}\n"
        f"• برنامه‌های غنی‌سازی تعلیق‌شده: {'، '.join(suspended) if suspended else 'موردی نیست ✅'}\n"
        f"• کشورهای خارج از NPT: {'، '.join(npt_outside) if npt_outside else 'موردی نیست ✅'}\n"
        f"• تحت تحریم جامع سازمان ملل: {'، '.join(sanctioned) if sanctioned else 'موردی نیست ✅'}"
    )
    return body


async def iaea_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    parts = data.split(":")  # un:iaea:action[:arg]

    user_id, c = await require_un_or_admin(update)
    if not c:
        return

    action = parts[2] if len(parts) > 2 else "menu"

    # ---------- منوی اصلی آژانس ----------
    if action == "menu":
        text = (
            "☢️ **آژانس بین‌المللی انرژی اتمی (IAEA)**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "آژانس، نهاد نظارتی سازمان ملل در حوزه چرخه سوخت هسته‌ای، غنی‌سازی اورانیوم و پیمان عدم اشاعه (NPT) است.\n\n"
            "**اختیارات در دسترس دبیرکل:**\n"
            "• 🛰️ رصد و نظارت جهانی برنامه‌های هسته‌ای\n"
            "• 🔍 بازرسی فنی و تشکیل پرونده کشورها\n"
            "• ⛔ تعلیق برنامه غنی‌سازی کشور متخلف\n"
            "• 🧹 خلع سلاح هسته‌ای اجباری\n"
            "• 📢 انتشار گزارش عمومی آژانس\n\n"
            "_مقر رسمی آژانس — وین، اتریش_"
        )
        keyboard = [
            [InlineKeyboardButton("🛰️ رصد و نظارت جهانی", callback_data="un:iaea:monitor")],
            [InlineKeyboardButton("🔍 بازرسی فنی کشور", callback_data="un:iaea:inspect")],
            [InlineKeyboardButton("🚫 تحریم‌های جامع سازمان ملل", callback_data="un:iaea:sanctions")],
            [InlineKeyboardButton("📢 انتشار گزارش عمومی آژانس", callback_data="un:iaea:report")],
            [InlineKeyboardButton("🔙 بازگشت به ستاد سازمان ملل", callback_data="un:menu")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # ---------- 🛰️ رصد جهانی ----------
    elif action == "monitor":
        keyboard = [
            [InlineKeyboardButton("🔄 به‌روزرسانی", callback_data="un:iaea:monitor")],
            [InlineKeyboardButton("🔙 بازگشت به آژانس", callback_data="un:iaea:menu")],
        ]
        await query.edit_message_text(_iaea_monitor_text(), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # ---------- 🔍 انتخاب کشور برای بازرسی ----------
    elif action == "inspect":
        all_c = [x for x in db.get_all_countries() if x.get("country_key") != "un"]
        if not all_c:
            await query.edit_message_text("هیچ کشوری برای بازرسی وجود ندارد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="un:iaea:menu")]]))
            return
        keyboard = []
        row = []
        for x in all_c:
            mark = "☢️" if ((x.get("warheads") or 0) > 0 or (x.get("nuclear_fuel") or 0) > 0) else "🕊️"
            row.append(InlineKeyboardButton(f"{mark} {x['name']}", callback_data=f"un:iaea:dossier:{x['id']}"))
            if len(row) == 2:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton("🔙 بازگشت به آژانس", callback_data="un:iaea:menu")])
        await query.edit_message_text(
            "🔍 **بازرسی فنی آژانس — انتخاب کشور**\n\nکشور موردنظر را برای تشکیل پرونده هسته‌ای انتخاب فرمایید:\n_(☢️ دارای فعالیت هسته‌ای | 🕊️ فاقد برنامه)_",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )

    # ---------- 🔍 پرونده کشور ----------
    elif action == "dossier":
        t_id = int(parts[3])
        target = db.get_country_by_id(t_id)
        if not target:
            await query.answer("کشور یافت نشد!", show_alert=True)
            return
        keyboard = []
        if not (target.get("npt_withdrawn") or 0):
            # آژانس فقط بر اعضای NPT اختیار تعلیق دارد
            if (target.get("enrichment_suspended") or 0):
                keyboard.append([InlineKeyboardButton("✅ رفع تعلیق غنی‌سازی", callback_data=f"un:iaea:unsuspend:{t_id}")])
            else:
                keyboard.append([InlineKeyboardButton("⛔ تعلیق برنامه غنی‌سازی", callback_data=f"un:iaea:suspend:{t_id}")])
        if (target.get("un_sanctioned") or 0):
            keyboard.append([InlineKeyboardButton("🔓 لغو تحریم جامع سازمان ملل", callback_data=f"un:iaea:unsanction:{t_id}")])
        else:
            keyboard.append([InlineKeyboardButton("🚫 تحریم جامع سازمان ملل", callback_data=f"un:iaea:sanction:{t_id}")])
        if (target.get("warheads") or 0) > 0:
            keyboard.append([InlineKeyboardButton("🧹 خلع سلاح هسته‌ای اجباری", callback_data=f"un:iaea:disarm:{t_id}")])
        keyboard.append([InlineKeyboardButton("⚖️ تنظیم سقف اختصاصی کلاهک", callback_data=f"un:iaea:setcap:{t_id}")])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت به فهرست بازرسی", callback_data="un:iaea:inspect")])
        await query.edit_message_text(_iaea_dossier_text(target), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # ---------- ⛔ تعلیق غنی‌سازی ----------
    elif action == "suspend":
        t_id = int(parts[3])
        target = db.get_country_by_id(t_id)
        if not target:
            await query.answer("کشور یافت نشد!", show_alert=True)
            return
        if target.get("npt_withdrawn") or 0:
            await query.answer("⛔ این کشور خارج از پیمان عدم اشاعه است — آژانس اختیاری ندارد!", show_alert=True)
            return
        db.set_enrichment_suspended(t_id, True)
        db.add_transaction(t_id, "iaea_suspend", "⛔ تعلیق برنامه غنی‌سازی به دستور آژانس بین‌المللی انرژی اتمی — تولید سوخت غنی‌شده روزانه متوقف شد.", 0)
        try:
            if target.get("player_id"):
                await context.bot.send_message(
                    target["player_id"],
                    f"⛔ **اخطاریه آژانس بین‌المللی انرژی اتمی**\n\n برنامه غنی‌سازی کشور {target['flag']} *{target['name']}* به دستور آژانس تعلیق گردید. تولید سوخت غنی‌شدهٔ روزانه شما تا اطلاع بعدی متوقف است.\n\n_IAEA — وین_",
                    parse_mode="Markdown"
                )
        except Exception:
            pass
        await query.answer("⛔ برنامه غنی‌سازی تعلیق شد", show_alert=True)
        target = db.get_country_by_id(t_id)
        keyboard = [
            [InlineKeyboardButton("✅ رفع تعلیق غنی‌سازی", callback_data=f"un:iaea:unsuspend:{t_id}")],
            [InlineKeyboardButton("🔙 بازگشت به پرونده", callback_data=f"un:iaea:dossier:{t_id}")],
        ]
        await query.edit_message_text(_iaea_dossier_text(target), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # ---------- ✅ رفع تعلیق ----------
    elif action == "unsuspend":
        t_id = int(parts[3])
        target = db.get_country_by_id(t_id)
        if not target:
            await query.answer("کشور یافت نشد!", show_alert=True)
            return
        db.set_enrichment_suspended(t_id, False)
        db.add_transaction(t_id, "iaea_unsuspend", "✅ رفع تعلیق برنامه غنی‌سازی به دستور آژانس بین‌المللی انرژی اتمی — تولید سوخت از سر گرفته شد.", 0)
        try:
            if target.get("player_id"):
                await context.bot.send_message(
                    target["player_id"],
                    f"✅ **ابلاغیه آژانس بین‌المللی انرژی اتمی**\n\n تعلیق برنامه غنی‌سازی کشور {target['flag']} *{target['name']}* لغو گردید و تولید سوخت غنی‌شده از سر گرفته شد.\n\n_IAEA — وین_",
                    parse_mode="Markdown"
                )
        except Exception:
            pass
        await query.answer("✅ تعلیق برداشته شد", show_alert=True)
        target = db.get_country_by_id(t_id)
        keyboard = [
            [InlineKeyboardButton("⛔ تعلیق برنامه غنی‌سازی", callback_data=f"un:iaea:suspend:{t_id}")],
            [InlineKeyboardButton("🔙 بازگشت به فهرست بازرسی", callback_data="un:iaea:inspect")],
        ]
        await query.edit_message_text(_iaea_dossier_text(target), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # ---------- 🧹 خلع سلاح (تأیید دو مرحله‌ای) ----------
    elif action == "disarm":
        t_id = int(parts[3])
        target = db.get_country_by_id(t_id)
        if not target or (target.get("warheads") or 0) <= 0:
            await query.answer("این کشور کلاهکی ندارد!", show_alert=True)
            return
        text = (
            f"🧹 **خلع سلاح هسته‌ای اجباری — تأیید نهایی**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"کشور: {target['flag']} *{target['name']}*\n"
            f"کلاهک‌های ضبط‌شدنی: *{format_number(target.get('warheads') or 0)}*\n\n"
            "⚠️ تمام کلاهک‌های استراتژیک این کشور توسط بازرسان آژانس ضبط و از بین خواهد رفت. این اقدام با رسید رسمی به کشور ابلاغ می‌شود.\n\nآیا مطمئن هستید؟"
        )
        keyboard = [
            [InlineKeyboardButton("✅ تأیید خلع سلاح", callback_data=f"un:iaea:disarmok:{t_id}")],
            [InlineKeyboardButton("❌ انصراف", callback_data=f"un:iaea:dossier:{t_id}")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif action == "disarmok":
        t_id = int(parts[3])
        target = db.get_country_by_id(t_id)
        if not target:
            await query.answer("کشور یافت نشد!", show_alert=True)
            return
        count = db.confiscate_warheads(t_id, f"خلع سلاح اجباری آژانس — {format_number(0 if not target else target.get('warheads') or 0)} کلاهک ضبط شد.")
        if count <= 0:
            await query.answer("کلاهکی برای ضبط وجود نداشت!", show_alert=True)
            return
        try:
            if target.get("player_id"):
                await context.bot.send_message(
                    target["player_id"],
                    f"🧹 **ابلاغیه خلع سلاح — آژانس بین‌المللی انرژی اتمی**\n\n به استحضار می‌رساند {format_number(count)} فقره کلاهک استراتژیک کشور {target['flag']} *{target['name']}* توسط بازرسان آژانس ضبط و нейترالیزه گردید.\n\n_IAEA — وین_",
                    parse_mode="Markdown"
                )
        except Exception:
            pass
        await query.answer(f"🧹 {count} کلاهک ضبط شد", show_alert=True)
        target = db.get_country_by_id(t_id)
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به فهرست بازرسی", callback_data="un:iaea:inspect")]]
        await query.edit_message_text(_iaea_dossier_text(target), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # ---------- ⚖️ تنظیم سقف اختصاصی کلاهک ----------
    elif action == "setcap":
        t_id = int(parts[3])
        target = db.get_country_by_id(t_id)
        if not target:
            await query.answer("کشور یافت نشد!", show_alert=True)
            return
        eff = db.get_effective_warhead_cap(target)
        override = target.get("warhead_cap_override")
        cur_line = (
            f"اختصاصی مصوب: {format_number(override)} ⚖️" if (override is not None and override >= 0)
            else ("قانون پیش‌فرض: نامحدود" if eff is None else f"قانون پیش‌فرض: {format_number(eff)}")
        )
        context.user_data["un_draft"] = {"step": "iaea_cap", "target_id": t_id}
        text = (
            f"⚖️ **تنظیم سقف اختصاصی کلاهک — {target['flag']} {target['name']}**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• کلاهک فعلی: {format_number(target.get('warheads') or 0)}\n"
            f"• سقف فعلی: {cur_line}\n\n"
            "لطفاً **سقف جدید** را به‌صورت عدد ارسال فرمایید:\n"
            "• عدد `0` تا هر مقدار → سقف اختصاصی (بر همه قوانین مقدم است)\n"
            "• `-1` → حذف سقف اختصاصی و بازگشت به قانون پیش‌فرض (P5/خارج از NPT: نامحدود، بقیه: ۵)"
        )
        keyboard = [[InlineKeyboardButton("❌ انصراف", callback_data=f"un:iaea:dossier:{t_id}")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # ---------- 🚫 منوی تحریم‌های جامع سازمان ملل ----------
    elif action == "sanctions":
        all_c = [x for x in db.get_all_countries() if x.get("country_key") != "un"]
        sanctioned = [x for x in all_c if x.get("un_sanctioned") or 0]
        outside = [x for x in all_c if (x.get("npt_withdrawn") or 0) and not (x.get("un_sanctioned") or 0)]

        lines = [
            "🚫 **تحریم‌های جامع سازمان ملل (Comprehensive Sanctions)**",
            "━━━━━━━━━━━━━━━━━━", ""
        ]
        if sanctioned:
            lines.append("⛔ *کشورهای تحت تحریم:*")
            for x in sanctioned:
                lines.append(f"   • {x['flag']} {x['name']}")
        else:
            lines.append("✅ در حال حاضر کشوری تحت تحریم جامع نیست.")
        lines.append("")
        if outside:
            lines.append("⚠️ *کشورهای خارج از NPT که هنوز تحریم نشده‌اند:*")
            for x in outside:
                lines.append(f"   • {x['flag']} {x['name']}")
        elif sanctioned:
            lines.append("ℹ️ همه کشورهای خارج از NPT تحت تحریم‌اند.")
        else:
            lines.append("ℹ️ هیچ کشوری از پیمان عدم اشاعه خارج نشده است.")
        lines.append("")
        lines.append(
            "*آثار تحریم جامع:*\n"
            "• 📉 نصف شدن درآمد روزانه کشور\n"
            "• 🏪 بسته شدن بورس جهانی (خرید و فروش)\n"
            "• 🌐 انزوای بین‌المللی و انعکاس خبری"
        )

        keyboard = []
        for x in sanctioned:
            keyboard.append([InlineKeyboardButton(f"🔓 لغو تحریم {x['flag']} {x['name']}", callback_data=f"un:iaea:unsanction:{x['id']}")])
        for x in outside:
            keyboard.append([InlineKeyboardButton(f"🚫 تحریم {x['flag']} {x['name']}", callback_data=f"un:iaea:sanction:{x['id']}")])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت به آژانس", callback_data="un:iaea:menu")])
        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # ---------- 🚫 تأیید تحریم جامع ----------
    elif action == "sanction":
        t_id = int(parts[3])
        target = db.get_country_by_id(t_id)
        if not target:
            await query.answer("کشور یافت نشد!", show_alert=True)
            return
        if target.get("un_sanctioned") or 0:
            await query.answer("این کشور از قبل تحت تحریم است!", show_alert=True)
            return
        npt_mark = "خارج از پیمان عدم اشاعه 🚫" if (target.get("npt_withdrawn") or 0) else "عضو NPT"
        text = (
            f"🚫 **اعمال تحریم جامع سازمان ملل — تأیید نهایی**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"کشور: {target['flag']} *{target['name']}* ({npt_mark})\n\n"
            "**آثار تحریم:**\n"
            "• 📉 درآمد روزانه کشور نصف می‌شود\n"
            "• 🏪 بورس جهانی برای آن بسته می‌شود\n"
            "• 🌐 ابلاغ رسمی به کشور و انعکاس خبری جهانی\n\n"
            "آیا مطمئن هستید؟"
        )
        keyboard = [
            [InlineKeyboardButton("✅ تأیید تحریم جامع", callback_data=f"un:iaea:sanction_ok:{t_id}")],
            [InlineKeyboardButton("❌ انصراف", callback_data=f"un:iaea:dossier:{t_id}")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif action == "sanction_ok":
        t_id = int(parts[3])
        target = db.get_country_by_id(t_id)
        if not target:
            await query.answer("کشور یافت نشد!", show_alert=True)
            return
        reason = "نقض پیمان عدم اشاعه و تهدید صلح جهانی" if (target.get("npt_withdrawn") or 0) else "مصوبه شورای امنیت سازمان ملل"
        db.set_un_sanctioned(t_id, True, reason)
        try:
            if target.get("player_id"):
                await context.bot.send_message(
                    target["player_id"],
                    f"🚫 **ابلاغیه رسمی سازمان ملل متحد**\n\n کشور شما {target['flag']} *{target['name']}* به دلیل *{reason}* مشمول تحریم جامع گردید:\n\n📉 درآمد روزانه کشور نصف شد\n🏪 دسترسی به بورس جهانی قطع شد\n\n_شورای امنیت سازمان ملل متحد — نیویورک_",
                    parse_mode="Markdown"
                )
        except Exception:
            pass
        try:
            await news_engine.post_breaking_news(
                context.bot,
                news_title="تحریم جامع سازمان ملل علیه یک کشور",
                news_body=f"شورای امنیت سازمان ملل متحد تحریم‌های جامع را علیه کشور {target['flag']} {target['name']} به دلیل {reason} تصویب کرد. درآمد روزانه این کشور نصف و دسترسی آن به بازارهای جهانی قطع شد.",
                event_category="تحریم بین‌المللی"
            )
        except Exception:
            pass
        await query.answer("🚫 تحریم جامع اعمال شد", show_alert=True)
        target = db.get_country_by_id(t_id)
        keyboard = [
            [InlineKeyboardButton("🔓 لغو تحریم", callback_data=f"un:iaea:unsanction:{t_id}")],
            [InlineKeyboardButton("🔙 بازگشت به پرونده", callback_data=f"un:iaea:dossier:{t_id}")],
        ]
        await query.edit_message_text(_iaea_dossier_text(target), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # ---------- 🔓 لغو تحریم ----------
    elif action == "unsanction":
        t_id = int(parts[3])
        target = db.get_country_by_id(t_id)
        if not target:
            await query.answer("کشور یافت نشد!", show_alert=True)
            return
        if not (target.get("un_sanctioned") or 0):
            await query.answer("این کشور تحت تحریم نیست!", show_alert=True)
            return
        db.set_un_sanctioned(t_id, False)
        try:
            if target.get("player_id"):
                await context.bot.send_message(
                    target["player_id"],
                    f"✅ **ابلاغیه رسمی سازمان ملل متحد**\n\n تحریم‌های جامع علیه کشور {target['flag']} *{target['name']}* لغو گردید. درآمد روزانه و دسترسی به بورس جهانی به حالت عادی بازگشت.\n\n_شورای امنیت سازمان ملل متحد — نیویورک_",
                    parse_mode="Markdown"
                )
        except Exception:
            pass
        try:
            await news_engine.post_breaking_news(
                context.bot,
                news_title="لغو تحریم جامع",
                news_body=f"سازمان ملل متحد تحریم‌های جامع علیه کشور {target['flag']} {target['name']} را لغو کرد. روابط اقتصادی این کشور با جهان از سر گرفته شد.",
                event_category="دیپلماسی"
            )
        except Exception:
            pass
        await query.answer("✅ تحریم لغو شد", show_alert=True)
        target = db.get_country_by_id(t_id)
        keyboard = [
            [InlineKeyboardButton("🚫 تحریم جامع سازمان ملل", callback_data=f"un:iaea:sanction:{t_id}")],
            [InlineKeyboardButton("🔙 بازگشت به پرونده", callback_data=f"un:iaea:dossier:{t_id}")],
        ]
        await query.edit_message_text(_iaea_dossier_text(target), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    # ---------- 📢 گزارش عمومی ----------
    elif action == "report":
        body = _iaea_report_body()
        msg = (
            "☢️ **گزارش عمومی آژانس بین‌المللی انرژی اتمی (IAEA)**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"{body}\n\n"
            "_مصوب شورای حکام آژانس — وین، اتریش_"
        )
        sent = 0
        for c_item in db.get_all_countries():
            p_id = c_item.get("player_id")
            if p_id:
                try:
                    await context.bot.send_message(p_id, msg, parse_mode="Markdown")
                    sent += 1
                except Exception:
                    pass
        try:
            await news_engine.post_breaking_news(
                context.bot,
                news_title="گزارش رسمی آژانس بین‌المللی انرژی اتمی",
                news_body=body,
                event_category="آژانس انرژی اتمی"
            )
        except Exception:
            pass
        await query.answer(f"📢 گزارش برای {sent} بازیکن ارسال شد", show_alert=True)
        keyboard = [
            [InlineKeyboardButton("📢 ارسال مجدد", callback_data="un:iaea:report")],
            [InlineKeyboardButton("🔙 بازگشت به آژانس", callback_data="un:iaea:menu")],
        ]
        await query.edit_message_text(
            f"☢️ **گزارش عمومی آژانس**\n\n✅ برای *{format_number(sent)}* بازیکن ارسال شد و خبر فوری آن منتشر گردید.",
            reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
        )


def get_un_handlers():
    return [
        CommandHandler("un", un_main_menu),
        CallbackQueryHandler(un_callback_handler, pattern=r"^(un:|un_vote:)"),
    ]
