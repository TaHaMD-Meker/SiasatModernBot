# -*- coding: utf-8 -*-
"""
ماژول برنامه راهبردی هسته‌ای، چرخه سوخت و بازدارندگی استراتژیک (Strategic Nuclear Program).
پشتیبانی کامل از ایموجی‌های پرمیوم و متحرک تلگرام (<tg-emoji>)، کادربندی‌های رسمی (<blockquote>) و ارقام فارسی.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database as db
import config
import news_engine
from utils import format_money
from premium_emojis import pe


def _kb(rows):
    return InlineKeyboardMarkup(rows)


def fa_num(val) -> str:
    """تبدیل اعداد به ارقام فارسی با جداکننده ویرگول فارسی."""
    if val is None:
        return "۰"
    try:
        val = int(val)
    except (ValueError, TypeError):
        return "۰"
    s = f"{val:,}".replace(",", "٬")
    tr = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return s.translate(tr)


async def require_country(update: Update):
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        if update.message:
            await update.message.reply_text("هنوز کشوری نساختی! برای شروع /start رو بزن.", parse_mode="HTML")
        elif update.callback_query:
            await update.callback_query.answer("هنوز کشوری نساختی!", show_alert=True)
        return None
    return country


# ==================== منوی اصلی برنامه هسته‌ای ====================

async def nuclear_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    country = await require_country(update)
    if not country:
        return

    c = db.get_country_by_id(country["id"]) or country
    cid = c["id"]

    u_ore = c.get("uranium_ore", 0) or 0
    u_ore_d = c.get("uranium_ore_daily", 0) or 0
    fuel_35 = c.get("nuclear_fuel", 0) or 0
    fuel_d = c.get("nuclear_fuel_daily", 0) or 0
    med_20 = c.get("medical_isotopes", 0) or 0
    med_d = c.get("medical_isotopes_daily", 0) or 0
    enr_60 = c.get("enriched_60", 0) or 0
    w_90 = c.get("weapons_grade_90", 0) or 0
    warheads = c.get("warheads", 0) or 0
    tested = bool(c.get("nuclear_tested", 0))

    equipment = db.get_equipment(cid)
    enr_fac_count = equipment.get("enrichment_facility", 0) or 0
    is_p5 = c.get("country_key") in ("usa", "russia", "china", "france", "uk", "pakistan", "india", "israel", "north_korea")

    tier = c.get("enrichment_tier", 1) or 1
    tier_info = config.ENRICHMENT_TIERS.get(tier, config.ENRICHMENT_TIERS[1])

    npt_status = f"{pe('cross', '❌')} خارج از NPT" if c.get("npt_withdrawn") else f"{pe('dove', '🕊️')} عضو متعهد به NPT"
    iaea_status = f"{pe('alert', '⛔')} تعلیق توسط آژانس" if c.get("enrichment_suspended") else (f"{pe('cross', '🚫')} تحت تحریم جامع" if c.get("un_sanctioned") else f"{pe('verified', '🟢')} عادی و بازرسی‌پذیر")

    eff_cap = db.get_effective_warhead_cap(c)
    cap_str = f"{fa_num(eff_cap)} عدد" if eff_cap is not None else "نامحدود"

    fac_str = f"{fa_num(enr_fac_count)} مجتمع فعال" if enr_fac_count or is_p5 else "فاقد مجتمع غنی‌سازی"
    test_str = f"{pe('verified', '✅')} انجام‌شده (تأیید رسمی)" if tested or is_p5 else f"{pe('cross', '❌')} انجام‌نشده"

    text = (
        f"{pe('nuclear', '☢️')} <b>سند راهبردی چرخه سوخت و بازدارندگی هسته‌ای</b>\n"
        f"<blockquote>"
        f"<b>کشور:</b> {c['flag']} {c['name']}\n"
        f"<b>پیمان عدم اشاعه (NPT):</b> {npt_status}\n"
        f"<b>نظارت بین‌المللی (IAEA):</b> {iaea_status}\n"
        f"</blockquote>\n"
        f"<b>وضعیت زیرساخت و دکترین جاری</b>\n"
        f"<blockquote>"
        f"• مجتمع‌های غنی‌سازی: {fac_str}\n"
        f"• دکترین فعال سانتریفیوژها: {tier_info['short_name']}\n"
        f"• آزمایش انفجار هسته‌ای: {test_str}\n"
        f"</blockquote>\n"
        f"<b>تراز ذخایر و مواد زنجیره هسته‌ای</b>\n"
        f"<blockquote>"
        f"• کیک زرد اورانیوم: <code>{fa_num(u_ore)}</code> تن (+{fa_num(u_ore_d)} تن/روز)\n"
        f"• سوخت نیروگاهی (۳.۵٪): <code>{fa_num(fuel_35)}</code> کیلوگرم (+{fa_num(fuel_d)} ک‌گ/روز)\n"
        f"• ایزوتوپ پزشکی (۲۰٪): <code>{fa_num(med_20)}</code> کیلوگرم (+{fa_num(med_d)} ک‌گ/روز)\n"
        f"• اورانیوم آستانه گریز (۶۰٪): <code>{fa_num(enr_60)}</code> کیلوگرم\n"
        f"• اورانیوم تسلیحاتی (۹۰٪): <code>{fa_num(w_90)}</code> کیلوگرم\n"
        f"• کلاهک‌های بازدارنده: <code>{fa_num(warheads)}</code> عدد (سقف مجاز: {cap_str})\n"
        f"</blockquote>"
    )

    if warheads > 0:
        text += f"\n<blockquote><i>{pe('alert', '⚠️')} هزینه نگهداری روزانه: {format_money(warheads * 5_000_000)} و {fa_num(warheads * 2)} تراشه</i></blockquote>\n"

    buttons = []

    if enr_fac_count < 2 and not is_p5:
        buttons.append([InlineKeyboardButton("🔬 احداث مجتمع غنی‌سازی", callback_data="nuc:build_prompt")])

    buttons.append([
        InlineKeyboardButton("⚙️ تنظیم دکترین سانتریفیوژها", callback_data="nuc:tier_menu"),
    ])

    buttons.append([
        InlineKeyboardButton("🏥 رادیوداروها و سلامت ملی (+۵٪ رضایت)", callback_data="nuc:medical_info"),
    ])

    if not tested and not is_p5:
        buttons.append([InlineKeyboardButton("💥 آزمایش انفجار هسته‌ای (فاز ۴)", callback_data="nuc:test_prompt")])

    buttons.append([
        InlineKeyboardButton("🚀 مونتاژ کلاهک بازدارنده (فاز ۵)", callback_data="nuc:warhead_prompt"),
    ])

    if not is_p5:
        if c.get("npt_withdrawn"):
            buttons.append([InlineKeyboardButton("🕊️ بازگشت به معاهده NPT", callback_data="nuc:do_npt:rejoin")])
        else:
            buttons.append([InlineKeyboardButton("🚪 خروج از معاهده NPT", callback_data="nuc:npt_toggle")])

    buttons.append([InlineKeyboardButton("🔙 بازگشت به ستاد راهبردی", callback_data="mv:menu")])

    if update.message:
        await update.message.reply_text(text, reply_markup=_kb(buttons), parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="HTML")


# ==================== Callback Handler برنامه هسته‌ای ====================

async def nuclear_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    country = db.get_country_by_player(user_id)

    if not country:
        await query.answer("کشور یافت نشد!", show_alert=True)
        return

    await query.answer()
    c = db.get_country_by_id(country["id"]) or country
    cid = c["id"]

    if data in ("nuc:menu", "nuc:back"):
        await nuclear_main_menu(update, context)

    elif data in ("op:movements", "nuc:close", "mv:menu"):
        from handlers.bases import military_movements_menu
        await military_movements_menu(update, context)

    # ---------------- 1. احداث مجتمع غنی‌سازی ----------------
    elif data == "nuc:build_prompt":
        price = config.ENRICHMENT_FACILITY_PRICE
        gold_req = config.ENRICHMENT_FACILITY_GOLD
        chips_req = config.ENRICHMENT_FACILITY_CHIPS
        tech_req = config.ENRICHMENT_FACILITY_TECH_REQ

        text = (
            f"{pe('microscope', '🔬')} <b>احداث مجتمع غنی‌سازی و آبشار سانتریفیوژ</b>\n"
            f"<blockquote>این مجتمع در عمق پناهگاه‌های بتنی زیرزمینی احداث شده تا تبدیل کیک زرد به سوخت راکتور یا اورانیوم غنی‌شده را انجام دهد.</blockquote>\n\n"
            f"<b>مشخصات و الزامات احداث:</b>\n"
            f"• هزینه سرمایه‌گذاری: <b>{format_money(price)}</b>\n"
            f"• پشتوانه طلا: <b>{fa_num(gold_req)} شمش</b>\n"
            f"• تراشه‌های میکروچیپ: <b>{fa_num(chips_req)} عدد</b>\n"
            f"• سطح فناوری مورد نیاز: <b>سطح {fa_num(tech_req)} به بالا</b> (سطح شما: {fa_num(c.get('tech_level', 1))})\n\n"
            f"<blockquote>آیا مایل به صدور دستور احداث مجتمع غنی‌سازی هستید؟</blockquote>"
        )
        buttons = [
            [InlineKeyboardButton("✅ تأیید و آغاز احداث مجتمع", callback_data="nuc:do_build")],
            [InlineKeyboardButton("🔙 انصراف", callback_data="nuc:menu")],
        ]
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="HTML")

    elif data == "nuc:do_build":
        ok, msg = db.build_enrichment_facility_transaction(cid)
        if not ok:
            await query.edit_message_text(
                f"{pe('cross', '❌')} <b>خطا در احداث مجتمع</b>\n\n<blockquote>{msg}</blockquote>",
                reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت", callback_data="nuc:menu")]]),
                parse_mode="HTML"
            )
            return
        await query.edit_message_text(
            f"{pe('verified', '✅')} {msg}\n\n<blockquote>اکنون می‌توانید دکترین سانتریفیوژها را در منوی اصلی تنظیم فرمایید.</blockquote>",
            reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به برنامه هسته‌ای", callback_data="nuc:menu")]]),
            parse_mode="HTML"
        )

    # ---------------- 2. تنظیم دکترین سانتریفیوژها ----------------
    elif data == "nuc:tier_menu":
        curr_tier = c.get("enrichment_tier", 1) or 1
        text = (
            f"{pe('gear', '⚙️')} <b>تنظیم دکترین و اهداف سانتریفیوژها</b>\n"
            f"<blockquote>جهت و هدف غنی‌سازی آبشارها را انتخاب فرمایید:</blockquote>\n\n"
            f"<b>پله ۱: سوخت نیروگاهی (۳.۵٪)</b>\n"
            f"<blockquote>• خروجی: +۲۵ کیلوگرم سوخت در روز (مصرف ۴۰ تن کیک زرد)\n"
            f"• فایده: صفر شدن مصرف نفت شبکه برق و آزادی نفت برای صادرات.</blockquote>\n\n"
            f"<b>پله ۲: ایزوتوپ پزشکی و پیشران (۲۰٪)</b>\n"
            f"<blockquote>• خروجی: +۱۰ کیلوگرم در روز (مصرف ۶۰ تن کیک زرد + ۲ تراشه)\n"
            f"• فایده: +۵٪ رضایت ملی درمان سرطان + ۳۰٪ تخفیف سوخت ناوگان.</blockquote>\n\n"
            f"<b>پله ۳: اورانیوم آستانه گریز (۶۰٪)</b>\n"
            f"<blockquote>• خروجی: +۵ کیلوگرم در روز (مصرف ۸۰ تن کیک زرد + ۴ تراشه)\n"
            f"• پیامد: اهرم چانه‌زنی سنگین در دیپلماسی (هشدار نظارتی آژانس).</blockquote>\n\n"
            f"<b>پله ۴: غنی‌سازی تسلیحاتی (۹۰٪)</b>\n"
            f"<blockquote>• خروجی: +۲.۵ کیلوگرم در روز (مصرف ۱۲۰ تن کیک زرد + ۶ تراشه)\n"
            f"• پیامد: خوراک مستقیم آزمایش انفجار اتمی و ساخت کلاهک.</blockquote>\n\n"
            f"<b>دکترین جاری شما:</b> <code>{config.ENRICHMENT_TIERS.get(curr_tier, {}).get('name')}</code>"
        )
        buttons = [
            [InlineKeyboardButton("پله ۱: سوخت ۳.۵٪ نیروگاهی", callback_data="nuc:set_tier:1")],
            [InlineKeyboardButton("پله ۲: ایزوتوپ پزشکی ۲۰٪", callback_data="nuc:set_tier:2")],
            [InlineKeyboardButton("پله ۳: اورانیوم ۶۰٪ (گریز)", callback_data="nuc:set_tier:3")],
            [InlineKeyboardButton("پله ۴: اورانیوم تسلیحاتی ۹۰٪", callback_data="nuc:set_tier:4")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="nuc:menu")],
        ]
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="HTML")

    elif data.startswith("nuc:set_tier:"):
        tier_target = int(data.split(":")[2])
        ok, msg = db.set_country_enrichment_tier(cid, tier_target)
        if not ok:
            await query.edit_message_text(
                f"{pe('cross', '❌')} <b>خطا در تنظیم دکترین</b>\n\n<blockquote>{msg}</blockquote>",
                reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت", callback_data="nuc:tier_menu")]]),
                parse_mode="HTML"
            )
            return
        await query.edit_message_text(
            f"{pe('verified', '✅')} {msg}\n\n<blockquote>سانتریفیوژها با موفقیت بر روی دکترین جدید کالیبره شدند.</blockquote>",
            reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به برنامه هسته‌ای", callback_data="nuc:menu")]]),
            parse_mode="HTML"
        )

    # ---------------- 3. اطلاعات پزشکی هسته‌ای ----------------
    elif data == "nuc:medical_info":
        med_res = c.get("medical_isotopes", 0) or 0
        text = (
            f"{pe('hospital', '🏥')} <b>پروژه ملی رادیوداروها و پزشکی هسته‌ای</b>\n"
            f"<blockquote>تولید رادیوایزوتوپ‌های درمانی (نظیر ید-۱۳۱ و مولیبدن-۹۹) از طریق غنی‌سازی ۲۰٪ جهت تجهیز مراکز درمان سرطان.</blockquote>\n\n"
            f"<b>دستاوردهای راهبردی سلامت:</b>\n"
            f"• <b>افزایش پایدار رضایت عمومی:</b> <b>+۵٪ رضایت ملی</b> در محاسبات روزانه\n"
            f"• <b>کاهش نرخ بیماری و مرگ‌ومیر جامعه</b>\n"
            f"• <b>فناوری پیشران هسته‌ای:</b> ۳۰٪ صرفه‌جویی در مصرف سوخت ناوگان ارتش\n"
            f"• <b>پرتودهی غلات:</b> افزایش ماندگاری سیلوها و کاهش ضایعات کشاورزی\n\n"
            f"<blockquote><b>ذخیره فعلی ایزوتوپ‌های پزشکی:</b> <code>{fa_num(med_res)}</code> کیلوگرم</blockquote>\n\n"
            f"<i>جهت تولید ایزوتوپ‌ها، دکترین سانتریفیوژها را روی «پله ۲ (۲۰٪)» قرار دهید.</i>"
        )
        buttons = [
            [InlineKeyboardButton("⚙️ تنظیم دکترین سانتریفیوژها", callback_data="nuc:tier_menu")],
            [InlineKeyboardButton("🔙 بازگشت به برنامه هسته‌ای", callback_data="nuc:menu")],
        ]
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="HTML")

    # ---------------- 4. آزمایش انفجار هسته‌ای (فاز ۴) ----------------
    elif data == "nuc:test_prompt":
        w90 = c.get("weapons_grade_90", 0) or 0
        w90_req = config.NUCLEAR_TEST_WEAPONS_GRADE
        price = config.NUCLEAR_TEST_COST_MONEY
        gold_req = config.NUCLEAR_TEST_COST_GOLD
        chips_req = config.NUCLEAR_TEST_COST_CHIPS

        status_w90 = f"{pe('verified', '✅')} موجود" if w90 >= w90_req else f"{pe('cross', '❌')} موجودی: {fa_num(w90)} ک‌گ"

        text = (
            f"{pe('blast', '💥')} <b>فاز ۴: سایت آزمایش انفجار هسته‌ای زیرزمینی</b>\n"
            f"<blockquote>پیش از امکان کوچک‌سازی کلاهک‌های موشکی، عملکرد چاشنی‌های انفجار کروی در یک آزمایش زیرزمینی به اثبات می‌رسد.</blockquote>\n\n"
            f"<b>پیش‌نیازها و مواد لازم:</b>\n"
            f"• اورانیوم تسلیحاتی ۹۰٪: <b>{fa_num(w90_req)} کیلوگرم</b> ({status_w90})\n"
            f"• هزینه اجرای آزمایش: <b>{format_money(price)}</b>\n"
            f"• پشتوانه طلا: <b>{fa_num(gold_req)} شمش</b>\n"
            f"• تراشه‌های میکروچیپ: <b>{fa_num(chips_req)} عدد</b>\n"
            f"• سطح فناوری مورد نیاز: <b>حداقل سطح ۴</b> (سطح شما: {fa_num(c.get('tech_level', 1))})\n\n"
            f"<b>پیامدهای بین‌المللی آزمایش:</b>\n"
            f"<blockquote>"
            f"• ثبت امواج لرزه‌نگاری مصنوعی ۵.۲ ریشتری در رصدهای جهانی\n"
            f"• انتشار بیانیه و خبر رسمی در کانال اخبار\n"
            f"• پیوستن رسمی کشور به باشگاه قدرت‌های دارای توان آزمایش اتمی\n"
            f"</blockquote>"
        )
        buttons = [
            [InlineKeyboardButton("💥 اجرای آزمایش انفجار زیرزمینی", callback_data="nuc:do_test")],
            [InlineKeyboardButton("🔙 انصراف", callback_data="nuc:menu")],
        ]
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="HTML")

    elif data == "nuc:do_test":
        ok, msg = db.conduct_nuclear_test_transaction(cid)
        if not ok:
            await query.edit_message_text(
                f"{pe('cross', '❌')} <b>عدم امکان اجرای آزمایش</b>\n\n<blockquote>{msg}</blockquote>",
                reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت", callback_data="nuc:menu")]]),
                parse_mode="HTML"
            )
            return

        try:
            await news_engine.trigger_general_broadcast(
                context.bot,
                f"🚨 **خبر فوری — آزمایش هسته‌ای موفقیت‌آمیز!**\n\n"
                f"مراکز لرزه‌نگاری بین‌المللی زمین‌لرزه‌ای مصنوعی با قدرت ۵.۲ ریشتر را در عمق کویر کشور {c['flag']} **{c['name']}** ثبت کردند.\n\n"
                f"آژانس بین‌المللی انرژی اتمی (IAEA) وقوع نخستین انفجار اتمی این کشور را تأیید کرد و شورای امنیت سازمان ملل تشکیل جلسه اضطراری داد."
            )
        except Exception:
            pass

        await query.edit_message_text(
            f"{pe('verified', '✅')} {msg}\n\n<blockquote>خبر رسمی این دستاورد در کانال اخبار منتشر گردید. فاز ۵ (کوچک‌سازی و مونتاژ کلاهک) برای کشور شما آزاد شد.</blockquote>",
            reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به برنامه هسته‌ای", callback_data="nuc:menu")]]),
            parse_mode="HTML"
        )

    # ---------------- 5. کوچک‌سازی و ساخت کلاهک (فاز ۵) ----------------
    elif data == "nuc:warhead_prompt":
        w90 = c.get("weapons_grade_90", 0) or 0
        w90_req = config.NUCLEAR_WARHEAD_WEAPONS_GRADE
        price = config.NUCLEAR_WARHEAD_COST_MONEY
        gold_req = config.NUCLEAR_WARHEAD_COST_GOLD
        chips_req = config.NUCLEAR_WARHEAD_COST_CHIPS
        tested = bool(c.get("nuclear_tested", 0))
        is_p5 = c.get("country_key") in ("usa", "russia", "china", "france", "uk", "pakistan", "india", "israel", "north_korea")

        eff_cap = db.get_effective_warhead_cap(c)
        curr_wh = c.get("warheads", 0) or 0

        status_w90 = f"{pe('verified', '✅')} موجود" if w90 >= w90_req else f"{pe('cross', '❌')} موجودی: {fa_num(w90)} ک‌گ"
        status_test = f"{pe('verified', '✅')} انجام‌شده" if tested or is_p5 else f"{pe('cross', '❌')} انجام‌نشده"

        text = (
            f"{pe('rocket', '🚀')} <b>فاز ۵: کوچک‌سازی و مونتاژ کلاهک راهبردی موشکی</b>\n"
            f"<blockquote>ادغام هسته شکافت‌پذیر و چاشنی‌های هدایت الکترونیکی جهت استقرار بر روی موشک‌های بالستیک یا زیردریایی‌های اتمی.</blockquote>\n\n"
            f"<b>پیش‌نیازها و ملزومات ساخت:</b>\n"
            f"• اورانیوم تسلیحاتی ۹۰٪: <b>{fa_num(w90_req)} کیلوگرم</b> ({status_w90})\n"
            f"• آزمایش هسته‌ای (فاز ۴): <b>{status_test}</b>\n"
            f"• هزینه مونتاژ: <b>{format_money(price)}</b>\n"
            f"• پشتوانه طلا: <b>{fa_num(gold_req)} شمش</b>\n"
            f"• تراشه فوق‌پیشرفته: <b>{fa_num(chips_req)} عدد</b>\n"
            f"• سطح فناوری مورد نیاز: <b>سطح ۵ بومی</b> (سطح شما: {fa_num(c.get('tech_level', 1))})\n"
            f"• سقف مجاز نگهداری: <b>{fa_num(curr_wh)} از {fa_num(eff_cap) if eff_cap is not None else 'نامحدود'} عدد</b>\n\n"
            f"<blockquote><i>{pe('alert', '⚠️')} هزینه نگهداری روزانه: ۵ میلیون دلار و ۲ تراشه در روز به ازای هر کلاهک مستقر.</i></blockquote>"
        )
        buttons = [
            [InlineKeyboardButton("🚀 مونتاژ و مسلح‌سازی ۱ کلاهک استراتژیک", callback_data="nuc:do_warhead")],
            [InlineKeyboardButton("🔙 انصراف", callback_data="nuc:menu")],
        ]
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="HTML")

    elif data == "nuc:do_warhead":
        ok, msg = db.assemble_strategic_warhead_transaction(cid)
        if not ok:
            await query.edit_message_text(
                f"{pe('cross', '❌')} <b>عدم امکان مونتاژ کلاهک</b>\n\n<blockquote>{msg}</blockquote>",
                reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت", callback_data="nuc:menu")]]),
                parse_mode="HTML"
            )
            return

        try:
            await news_engine.trigger_general_broadcast(
                context.bot,
                f"🚨 **گزارش محرمانه اطلاعاتی و هشدار آژانس بین‌المللی انرژی اتمی**\n\n"
                f"کشور {c['flag']} **{c['name']}** یک کلاهک راهبردی بازدارنده جدید را با موفقیت مونتاژ و در سیلوهای زیرزمینی خود مستقر کرد."
            )
        except Exception:
            pass

        await query.edit_message_text(
            f"{pe('verified', '✅')} {msg}\n\n<blockquote>کلاهک در زرادخانه بازدارندگی کشور مستقر گردید.</blockquote>",
            reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به برنامه هسته‌ای", callback_data="nuc:menu")]]),
            parse_mode="HTML"
        )

    # ---------------- 6. NPT Toggle ----------------
    elif data == "nuc:npt_toggle":
        is_withdrawn = bool(c.get("npt_withdrawn", 0))
        if not is_withdrawn:
            text = (
                f"{pe('alert', '🚪')} <b>خروج رسمی از پیمان عدم اشاعه سلاح‌های هسته‌ای (NPT)</b>\n"
                f"<blockquote>آیا از خروج رسمی از این معاهده بین‌المللی اطمینان دارید؟</blockquote>\n\n"
                f"<b>پیامدهای تصمیم:</b>\n"
                f"• لغو کامل سقف کلاهک برای کشور شما\n"
                f"• بی‌اثر شدن احکام و تعلیق‌های آژانس بین‌المللی اتمی\n"
                f"• <b>افت {fa_num(config.NPT_WITHDRAWAL_APPROVAL_HIT)}٪ رضایت عمومی</b> به دلیل انزوای دیپلماتیک\n"
                f"• خطر وضع تحریم‌های اقتصادی توسط شورای امنیت سازمان ملل"
            )
            buttons = [
                [InlineKeyboardButton("🚪 تأیید خروج از NPT", callback_data="nuc:do_npt:withdraw")],
                [InlineKeyboardButton("❌ انصراف", callback_data="nuc:menu")],
            ]
        else:
            eff_cap = db.get_effective_warhead_cap(c)
            text = (
                f"{pe('dove', '🕊️')} <b>بازگشت رسمی به پیمان عدم اشاعه (NPT)</b>\n"
                f"<blockquote>با بازگشت به NPT، تعهدات بین‌المللی مجدداً برقرار شده و ریسک تحریم‌های جامع کاهش می‌یابد.</blockquote>\n\n"
                f"<blockquote><i>شرط بازگشت: تعداد کلاهک‌های کشور نباید از سقف مجاز ({fa_num(eff_cap)} عدد) بیشتر باشد.</i></blockquote>"
            )
            buttons = [
                [InlineKeyboardButton("🕊️ بازگشت به پیمان NPT", callback_data="nuc:do_npt:rejoin")],
                [InlineKeyboardButton("❌ انصراف", callback_data="nuc:menu")],
            ]
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="HTML")

    elif data.startswith("nuc:do_npt:"):
        action = data.split(":")[2]
        if action == "withdraw":
            succ, msg = db.set_npt_withdrawn(cid, True)
            if succ:
                new_app = max(0, (c.get("approval_rating") or 80) - config.NPT_WITHDRAWAL_APPROVAL_HIT)
                db.update_country_field(cid, "approval_rating", new_app)
                try:
                    await news_engine.trigger_general_broadcast(
                        context.bot,
                        f"🚨 **خبر فوری — خروج رسمی از NPT!**\n\n"
                        f"دولت {c['flag']} **{c['name']}** رسماً خروج کامل خود از پیمان عدم اشاعه هسته‌ای (NPT) را اعلام کرد و تمامی بازرسان آژانس را اخراج نمود."
                    )
                except Exception:
                    pass
        else:
            succ, msg = db.set_npt_withdrawn(cid, False)
            if succ:
                try:
                    await news_engine.trigger_general_broadcast(
                        context.bot,
                        f"🕊️ **خبر دیپلماتیک — بازگشت به NPT**\n\n"
                        f"کشور {c['flag']} **{c['name']}** پس از تطبیق زرادخانه خود با موازین بین‌المللی، مجدداً به پیمان عدم اشاعه سلاح‌های هسته‌ای پیوست."
                    )
                except Exception:
                    pass

        await query.edit_message_text(
            f"<b>نتیجه عملیات دیپلماتیک</b>\n\n<blockquote>{msg}</blockquote>",
            reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به برنامه هسته‌ای", callback_data="nuc:menu")]]),
            parse_mode="HTML"
        )
