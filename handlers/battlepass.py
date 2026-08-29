# -*- coding: utf-8 -*-
"""
ماژول اختصاصی بتل‌پس فصلی و کمپین‌های ماموریت ویژه (Battle Pass System).
سیستم پیشرفت پله‌ای شبیه بازی‌های مطرح (COD/Warzone)، ردیف‌های رایگان و پرمیوم،
چالش‌های هفتگی کسب XP و پاداش‌های کلان ارزی و تسلیحاتی.
"""

import html
import math
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

import database as db
import config
from utils import format_money, format_number, format_oil, get_main_keyboard


_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def _fa(num) -> str:
    return str(num).translate(_FA_DIGITS)


def _fa_toman(num: int) -> str:
    """۳۰۰۰۰۰ → «۳۰۰٬۰۰۰» با ارقام و جداکننده‌ی فارسی."""
    return _fa(f"{int(num or 0):,}".replace(",", "٬"))


def _bp_price():
    """قیمت بتل‌پس با تخفیف جاری فروشگاه ویژه. برمی‌گرداند: (قیمت نهایی, درصد تخفیف)."""
    base = int(getattr(config, "BATTLE_PASS_PRICE_TOMAN", 300_000) or 0)
    try:
        pct = db.get_vip_discount("battle_pass")
    except Exception:
        pct = 0
    if pct <= 0:
        return base, 0
    return int(round(base * (100 - pct) / 100)), int(pct)


def _bp_price_text() -> str:
    """برچسب قیمت بتل‌پس با تخفیف؛ مثلاً «۲۴۰ هزار تومان (۲۰٪-)»."""
    eff, pct = _bp_price()
    txt = f"{_fa_toman(eff)} هزار تومان" if eff >= 1000 else f"{_fa_toman(eff)} تومان"
    if pct > 0:
        txt += f" ({_fa(pct)}٪-)"
    return txt


def _bp_price_note() -> str:
    """خط توضیح تخفیف برای فاکتور بتل‌پس؛ خالی اگر تخفیفی نیست."""
    eff, pct = _bp_price()
    if pct <= 0:
        return ""
    base = int(getattr(config, "BATTLE_PASS_PRICE_TOMAN", 300_000) or 0)
    return f"\n🎉 <b>{_fa(pct)}٪ تخفیف اعمال شد</b> — قیمت قبلی: {_fa_toman(base)} تومان"


def _build_progress_bar(current_xp: int, xp_per_tier: int = 1000, total_blocks: int = 10) -> str:
    """ساخت نوار پیشرفت گرافیکی XP."""
    prog = min(1.0, max(0.0, (current_xp % xp_per_tier) / float(xp_per_tier)))
    filled = int(prog * total_blocks)
    empty = total_blocks - filled
    return "🟩" * filled + "⬜" * empty


def _build_tier_bar(current_tier: int, max_tier: int = 20, total_blocks: int = 10) -> str:
    """ساخت نوار پیشرفت لول بتل‌پس."""
    prog = min(1.0, max(0.0, current_tier / float(max_tier)))
    filled = int(prog * total_blocks)
    empty = total_blocks - filled
    return "🟨" * filled + "⬜" * empty


async def require_country(update: Update):
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        pending = db.get_pending_request_by_player(user_id)
        if pending:
            p_key = pending.get("country_key", "")
            p_info = config.COUNTRIES.get(p_key, {})
            flag = p_info.get("flag", "🏳️")
            name = p_info.get("name", p_key)
            msg = f"⏳ **درخواست رهبری کشور {flag} {name} در صف بررسی ادمین است.**\n\nپس از تایید ادمین، بتل‌پس فعال می‌شود."
            alert_text = f"درخواست کشور {name} در انتظار تأیید ادمین است!"
        else:
            msg = "❌ شما هنوز کشوری در بازی ثبت نکرده‌اید. برای شروع /start را بزنید."
            alert_text = "هنوز کشوری نساختی! برای شروع /start بزن."

        if update.message:
            await update.message.reply_text(msg, parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.answer(alert_text, show_alert=True)
        return None
    return country


# ==================== داشبورد اصلی بتل‌پس ====================

async def battlepass_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = await require_country(update)
    if not c:
        return

    c_id = c["id"]
    # همگام‌سازی و بررسی خودکار تسک‌ها (مانند آمادگی بالای ۸۵٪، بیانیه‌ها و زیرساخت‌ها)
    db.sync_and_check_all_challenges(c_id)

    bp = db.get_or_create_battle_pass(c_id)
    curr_tier = bp["current_tier"]
    curr_xp = bp["current_xp"]
    is_premium = bp["is_premium"]
    xp_per_tier = getattr(config, "BATTLE_PASS_XP_PER_TIER", 1000)

    claimed_free = set(bp["claimed_free_tiers"])
    claimed_prem = set(bp["claimed_premium_tiers"])

    # محاسبه تعداد جوایز قابل دریافت در حال حاضر
    unclaimed_free_count = len([t for t in range(1, curr_tier + 1) if t not in claimed_free])
    unclaimed_prem_count = len([t for t in range(1, curr_tier + 1) if t not in claimed_prem]) if is_premium else 0
    total_unclaimed = unclaimed_free_count + unclaimed_prem_count

    xp_in_level = curr_xp % xp_per_tier if curr_tier < 20 else xp_per_tier
    xp_bar = _build_progress_bar(curr_xp, xp_per_tier)
    tier_bar = _build_tier_bar(curr_tier, 20)

    season_title = getattr(config, "BATTLE_PASS_SEASON_TITLE", "فصل ۱: طوفان ژئوپلیتیک")

    pass_status = "👑 <b>بتل‌پس پرمیوم فعال (Pass Holder)</b> | +25% بوست XP" if is_premium else "👤 <b>ردیف رایگان (Free Track)</b>"

    tiers_config = getattr(config, "BATTLE_PASS_TIERS", {})
    next_tier_info = tiers_config.get(min(20, curr_tier + (0 if curr_tier == 20 else 1)), {})
    next_free_desc = next_tier_info.get("free", {}).get("desc", "—")
    next_prem_desc = next_tier_info.get("premium", {}).get("desc", "—")

    text = (
        f"⭐️ <b>«بتل‌پس استراتژیک سیاست مدرن»</b>\n"
        f"🏆 <b>{season_title}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🌐 <b>کشور:</b> {c['flag']} <b>{html.escape(c['name'])}</b>\n"
        f"🎖️ <b>وضعیت حساب:</b> {pass_status}\n\n"
        f"⭐️ <b>لول فعلی:</b> <b>Tier {curr_tier} / 20</b>\n"
        f"📊 پیشرفت کلی: {tier_bar} ({curr_tier}/20)\n"
        f"⚡ <b>امتیاز پله:</b> <code>{xp_in_level} / {xp_per_tier} XP</code>\n"
        f"🔋 نوار XP: {xp_bar}\n\n"
        f"🎁 <b>جوایز پله بعدی (Tier {min(20, curr_tier + 1)}):</b>\n"
        f"• 🆓 <b>ردیف رایگان:</b> {next_free_desc}\n"
        f"• 👑 <b>ردیف پرمیوم:</b> {next_prem_desc}\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
    )

    if total_unclaimed > 0:
        text += f"🔔 <b>شما {total_unclaimed} پاداش آماده دریافت دارید!</b> برای واریز به خزانه روی دکمه دریافت کلیک کنید:\n\n"
    else:
        text += "💡 با ثبت بیانیه، رزمایش، تجارت و توسعه کارخانه‌ها XP کسب کنید و لول‌آپ شوید!\n\n"

    keyboard = []

    # دکمه دریافت پاداش
    if total_unclaimed > 0:
        keyboard.append([InlineKeyboardButton(f"🎁 دریافت یکجای پاداش‌ها ({total_unclaimed} مورد)", callback_data="bp:claim_all")])

    keyboard.append([
        InlineKeyboardButton("📜 جدول ۲۰ لول و جوایز", callback_data="bp:view_tiers:1"),
        InlineKeyboardButton("🎯 چالش‌های هفتگی کسب XP", callback_data="bp:challenges"),
    ])

    if not is_premium:
        keyboard.append([InlineKeyboardButton(f"⭐️ خرید بتل‌پس پرمیوم ({_bp_price_text()})", callback_data="bp:buy_pass")])

    keyboard.append([
        InlineKeyboardButton("🔙 بازگشت به فروشگاه ویژه", callback_data="vip:menu"),
        InlineKeyboardButton("🌐 وضعیت کشور", callback_data="country:back_profile")
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text("⭐️ **بتل‌پس استراتژیک فصلی**", reply_markup=get_main_keyboard(update.effective_user.id), parse_mode="HTML")
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")
    elif update.callback_query:
        try:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
        except Exception:
            pass


# ==================== دریافت جوایز پله‌ها ====================

async def battlepass_claim_all(query, context, country_id: int):
    ok, msg, totals = db.claim_all_unlocked_battle_pass_rewards(country_id)
    if not ok:
        await query.answer(msg, show_alert=True)
        return

    await query.answer("🎉 پاداش‌ها با موفقیت دریافت شدند!", show_alert=False)
    keyboard = [
        [InlineKeyboardButton("⭐️ بازگشت به منوی بتل‌پس", callback_data="bp:menu")],
        [InlineKeyboardButton("🏛️ مشاهده وضعیت خزانه و کشور", callback_data="country:back_profile")]
    ]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# ==================== مشاهده جدول ۲۰ لول بتل‌پس ====================

async def battlepass_view_tiers(query, context, country_id: int, page: int = 1):
    bp = db.get_or_create_battle_pass(country_id)
    curr_tier = bp["current_tier"]
    is_premium = bp["is_premium"]
    claimed_free = set(bp["claimed_free_tiers"])
    claimed_prem = set(bp["claimed_premium_tiers"])

    tiers_config = getattr(config, "BATTLE_PASS_TIERS", {})

    per_page = 5
    total_pages = 4
    page = max(1, min(total_pages, page))
    start_tier = (page - 1) * per_page + 1
    end_tier = start_tier + per_page

    lines = [
        f"📜 <b>جدول سطوح و جوایز بتل‌پس (پله {start_tier} تا {end_tier - 1})</b>",
        f"⭐️ لول فعلی شما: <b>Tier {curr_tier} / 20</b> | وضعیت: {'👑 پرمیوم' if is_premium else '👤 رایگان'}",
        "━━━━━━━━━━━━━━━━━━━━━━\n"
    ]

    for t_num in range(start_tier, end_tier):
        t_info = tiers_config.get(t_num, {})
        free_r = t_info.get("free", {})
        prem_r = t_info.get("premium", {})

        is_unlocked = t_num <= curr_tier
        tier_icon = "🟢" if is_unlocked else "🔒"

        free_status = "✅ دریافت شده" if t_num in claimed_free else ("🎁 آماده دریافت" if is_unlocked else "قفل")
        prem_status = "✅ دریافت شده" if t_num in claimed_prem else ("🎁 آماده دریافت" if (is_unlocked and is_premium) else ("🔒 نیاز به پرمیوم" if is_unlocked else "قفل"))

        lines.append(f"{tier_icon} <b>{t_info.get('title', f'پله {t_num}')}</b>")
        lines.append(f"  • 🆓 <b>رایگان:</b> {free_r.get('desc','')} ➔ <i>[{free_status}]</i>")
        lines.append(f"  • 👑 <b>پرمیوم:</b> {prem_r.get('desc','')} ➔ <i>[{prem_status}]</i>")
        lines.append("")

    keyboard = []
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"bp:view_tiers:{page - 1}"))
    nav_row.append(InlineKeyboardButton(f"صفحه {page} از {total_pages}", callback_data="ignore"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"bp:view_tiers:{page + 1}"))
    keyboard.append(nav_row)

    if not is_premium:
        keyboard.append([InlineKeyboardButton(f"⭐️ ارتقا به بتل‌پس پرمیوم ({_bp_price_text()})", callback_data="bp:buy_pass")])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت به بتل‌پس", callback_data="bp:menu")])

    await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# ==================== چالش‌های هفتگی کسب سریع XP ====================

async def battlepass_challenges_menu(query, context, country_id: int):
    # همگام‌سازی و بررسی خودکار تسک‌ها
    db.sync_and_check_all_challenges(country_id)

    bp = db.get_or_create_battle_pass(country_id)
    completed = set(bp.get("completed_challenges", []))
    prog_map = bp.get("challenge_progress", {})

    challenges = getattr(config, "BATTLE_PASS_CHALLENGES", {})

    lines = [
        "🎯 <b>چالش‌های ویژه کسب XP بتل‌پس فصلی</b>",
        "با تکمیل هر چالش، امتیاز XP کلان دریافت کرده و بلافاصله لول‌آپ شوید:",
        "━━━━━━━━━━━━━━━━━━━━━━\n"
    ]

    for c_key, c_info in challenges.items():
        is_done = c_key in completed
        target = c_info.get("target", 1)
        curr_val = min(target, prog_map.get(c_key, 0))

        if is_done:
            icon = "✅"
            bar = "🟩🟩🟩🟩🟩"
            status = "تکمیل شد (+XP دریافت گردید)"
        else:
            icon = "⏳"
            prog_pct = curr_val / float(target)
            bar = _build_progress_bar(int(prog_pct * 1000), 1000, 6)
            # چالش‌های تجمعی (مثل صادرات) اعداد بزرگ دارند و باید خوانا نمایش داده شوند
            unit = c_info.get("unit", "")
            unit_sfx = f" {unit}" if unit else ""
            status = f"{curr_val:,} از {target:,}{unit_sfx}"

        lines.append(f"{icon} <b>{c_info.get('title','')}</b> (+{c_info.get('xp',400)} XP)")
        lines.append(f"  📝 {c_info.get('desc','')}")
        lines.append(f"  📊 وضعیت: {bar} ({status})\n")

    keyboard = [
        [InlineKeyboardButton("⭐️ بازگشت به منوی بتل‌پس", callback_data="bp:menu")],
        [InlineKeyboardButton("🔙 بازگشت به کشور", callback_data="country:back_profile")]
    ]
    await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# ==================== صفحه خرید بتل‌پس پرمیوم (قیمت پویا) ====================

async def battlepass_buy_pass_prompt(query, context, user_id: int):
    card_info = getattr(config, "PAYMENT_CARD_INFO", {
        "card_number": "۵۸۹۲-۱۰۱۴-۶۷۲۲-۷۲۲۵",
        "card_holder": "زینب فیاضی",
        "bank_name": "بانک سپه",
    })

    context.user_data["vip_input"] = {"plan_key": "battle_pass"}

    text = (
        "⭐️ <b>خرید و فعال‌سازی بتل‌پس پرمیوم (Season 1 Pass)</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "👑 <b>مزایا و محتویات ردیف پرمیوم بتل‌پس:</b>\n"
        "• 💰 <b>تا ۷۰ میلیون دلار</b> پاداش نقد خزانه در ۲۰ لول پیشرفت\n"
        "• 🛢️ <b>تا ۲۰ میلیون بشکه نفت خام</b> برای انباشت و تجارت استراتژیک\n"
        "• 🪙 <b>بیش از ۳۰۰ شمش طلا</b> و ۳۰۰ عدد میکروچیپ های‌تک\n"
        "• 🌾 <b>ده‌ها هزار تن غلات</b> و امنیت پایدار غذایی کشور\n"
        "• ⚡ <b>+۲۵٪ بوست دائمی XP</b> برای باز کردن برق‌آسای تمام پله‌ها\n"
        "• 👑 <b>تندیس طلایی و نشان اختصاصی «Warzone Economic Titan»</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💳 <b>اطلاعات پرداخت کارت به کارت:</b>\n"
        f"• <b>شماره کارت:</b> <code>{card_info['card_number']}</code>\n"
        f"• <b>به نام:</b> <b>{card_info['card_holder']}</b>\n"
        f"• <b>بانک:</b> <b>{card_info['bank_name']}</b>\n"
        f"• <b>مبلغ قابل پرداخت:</b> <b>{_fa_toman(_bp_price()[0])} تومان</b>{_bp_price_note()}\n\n"
        "📸 <b>نحوه ثبت:</b> پس از واریز، <b>تصویر فیش واریزی</b> یا <b>کد پیگیری</b> را همینجا در ربات ارسال فرمایید تا بلافاصله بررسی و فعال گردد."
    )

    keyboard = [
        [InlineKeyboardButton("🔙 انصراف و بازگشت", callback_data="bp:menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# ==================== هاندر کلی کال‌بک‌های بتل‌پس ====================

async def battlepass_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    country = db.get_country_by_player(user_id)

    if not country:
        await query.answer("شما هنوز کشوری نساخته‌اید!", show_alert=True)
        return

    country_id = country["id"]

    if data == "bp:menu":
        await battlepass_menu(update, context)

    elif data == "bp:claim_all":
        await battlepass_claim_all(query, context, country_id)

    elif data.startswith("bp:view_tiers:"):
        page = int(data.split(":")[2])
        await battlepass_view_tiers(query, context, country_id, page)

    elif data == "bp:challenges":
        await battlepass_challenges_menu(query, context, country_id)

    elif data == "bp:buy_pass":
        await battlepass_buy_pass_prompt(query, context, user_id)


def get_battlepass_handlers():
    """ثبت دستورات و کال‌بک‌های ماژول بتل‌پس."""
    return [
        CommandHandler(["pass", "battlepass", "bp"], battlepass_menu),
        CallbackQueryHandler(battlepass_callback_handler, pattern=r"^bp:"),
    ]
