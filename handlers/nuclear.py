# -*- coding: utf-8 -*-
"""
ماژول برنامه راهبردی هسته‌ای، چرخه سوخت و بازدارندگی استراتژیک (Strategic Nuclear Program).
طراحی رسمی و کتابی، بدون شلوغی ایموجی، با نقل‌قول‌های تمیز تلگرام (Blockquotes) و ارقام فارسی.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database as db
import config
import news_engine
from utils import format_money


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
            await update.message.reply_text("هنوز کشوری نساختی! برای شروع /start رو بزن.", parse_mode="Markdown")
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

    npt_status = "خارج از معاهده NPT" if c.get("npt_withdrawn") else "عضو متعهد به NPT"
    iaea_status = "تعلیق توسط آژانس" if c.get("enrichment_suspended") else ("تحت تحریم جامع" if c.get("un_sanctioned") else "عادی و بازرسی‌پذیر")

    eff_cap = db.get_effective_warhead_cap(c)
    cap_str = f"{fa_num(eff_cap)} عدد" if eff_cap is not None else "نامحدود"

    fac_str = f"{fa_num(enr_fac_count)} مجتمع فعال" if enr_fac_count or is_p5 else "فاقد مجتمع غنی‌سازی"
    test_str = "انجام‌شده (تأیید رسمی)" if tested or is_p5 else "انجام‌نشده"

    text = (
        f"**سند راهبردی چرخه سوخت و بازدارندگی هسته‌ای**\n"
        f"> **کشور:** {c['flag']} {c['name']}\n"
        f"> **پیمان عدم اشاعه (NPT):** {npt_status}\n"
        f"> **نظارت بین‌المللی (IAEA):** {iaea_status}\n\n"
        f"**زیرساخت و دکترین جاری**\n"
        f"> • مجتمع‌های غنی‌سازی: {fac_str}\n"
        f"> • دکترین فعال سانتریفیوژها: {tier_info['short_name']}\n"
        f"> • آزمایش انفجار هسته‌ای: {test_str}\n\n"
        f"**تراز ذخایر و مواد زنجیره هسته‌ای**\n"
        f"> • کیک زرد اورانیوم: {fa_num(u_ore)} تن (+{fa_num(u_ore_d)} تن/روز)\n"
        f"> • سوخت نیروگاهی (۳.۵٪): {fa_num(fuel_35)} کیلوگرم (+{fa_num(fuel_d)} ک‌گ/روز)\n"
        f"> • ایزوتوپ پزشکی (۲۰٪): {fa_num(med_20)} کیلوگرم (+{fa_num(med_d)} ک‌گ/روز)\n"
        f"> • اورانیوم آستانه گریز (۶۰٪): {fa_num(enr_60)} کیلوگرم\n"
        f"> • اورانیوم تسلیحاتی (۹۰٪): {fa_num(w_90)} کیلوگرم\n"
        f"> • کلاهک‌های بازدارنده: {fa_num(warheads)} عدد (سقف مجاز: {cap_str})\n"
    )

    if warheads > 0:
        text += f"\n> _هزینه نگهداری روزانه: {format_money(warheads * 5_000_000)} و {fa_num(warheads * 2)} تراشه_\n"

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
            buttons.append([InlineKeyboardButton("🕊️ بازگشت به معاهده NPT", callback_data="nuc:npt_toggle")])
        else:
            buttons.append([InlineKeyboardButton("🚪 خروج از معاهده NPT", callback_data="nuc:npt_toggle")])

    buttons.append([InlineKeyboardButton("🔙 بازگشت به ستاد راهبردی", callback_data="mv:menu")])

    if update.message:
        await update.message.reply_text(text, reply_markup=_kb(buttons), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="Markdown")


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
            "**احداث مجتمع غنی‌سازی و آبشار سانتریفیوژ**\n"
            "> این مجتمع در عمق پناهگاه‌های بتنی زیرزمینی احداث شده تا تبدیل کیک زرد به سوخت راکتور یا اورانیوم غنی‌شده را انجام دهد.\n\n"
            "**مشخصات و الزامات احداث:**\n"
            f"• هزینه سرمایه‌گذاری: {format_money(price)}\n"
            f"• پشتوانه طلا: {fa_num(gold_req)} شمش\n"
            f"• تراشه‌های میکروچیپ: {fa_num(chips_req)} عدد\n"
            f"• سطح فناوری مورد نیاز: سطح {fa_num(tech_req)} به بالا (سطح شما: {fa_num(c.get('tech_level', 1))})\n\n"
            "> آیا مایل به صدور دستور احداث مجتمع غنی‌سازی هستید؟"
        )
        buttons = [
            [InlineKeyboardButton("✅ تأیید و آغاز احداث مجتمع", callback_data="nuc:do_build")],
            [InlineKeyboardButton("🔙 انصراف", callback_data="nuc:menu")],
        ]
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="Markdown")

    elif data == "nuc:do_build":
        ok, msg = db.build_enrichment_facility_transaction(cid)
        if not ok:
            await query.edit_message_text(
                f"**خطا در احداث مجتمع**\n\n> {msg}",
                reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت", callback_data="nuc:menu")]]),
                parse_mode="Markdown"
            )
            return
        await query.edit_message_text(
            f"{msg}\n\n> _اکنون می‌توانید دکترین سانتریفیوژها را در منوی اصلی تنظیم فرمایید._",
            reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به برنامه هسته‌ای", callback_data="nuc:menu")]]),
            parse_mode="Markdown"
        )

    # ---------------- 2. تنظیم دکترین سانتریفیوژها ----------------
    elif data == "nuc:tier_menu":
        curr_tier = c.get("enrichment_tier", 1) or 1
        text = (
            "**تنظیم دکترین و اهداف سانتریفیوژها**\n"
            "> جهت و هدف غنی‌سازی آبشارها را انتخاب فرمایید:\n\n"
            "**پله ۱: سوخت نیروگاهی (۳.۵٪)**\n"
            "> • خروجی: +۲۵ کیلوگرم سوخت در روز (مصرف ۴۰ تن کیک زرد)\n"
            "> • فایده: صفر شدن مصرف نفت شبکه برق و آزادی نفت برای صادرات.\n\n"
            "**پله ۲: ایزوتوپ پزشکی و پیشران (۲۰٪)**\n"
            "> • خروجی: +۱۰ کیلوگرم در روز (مصرف ۶۰ تن کیک زرد + ۲ تراشه)\n"
            "> • فایده: +۵٪ رضایت ملی درمان سرطان + ۳۰٪ تخفیف سوخت ناوگان.\n\n"
            "**پله ۳: اورانیوم آستانه گریز (۶۰٪)**\n"
            "> • خروجی: +۵ کیلوگرم در روز (مصرف ۸۰ تن کیک زرد + ۴ تراشه)\n"
            "> • پیامد: اهرم چانه‌زنی سنگین در دیپلماسی (هشدار نظارتی آژانس).\n\n"
            "**پله ۴: غنی‌سازی تسلیحاتی (۹۰٪)**\n"
            "> • خروجی: +۲.۵ کیلوگرم در روز (مصرف ۱۲۰ تن کیک زرد + ۶ تراشه)\n"
            "> • پیامد: خوراک مستقیم آزمایش انفجار اتمی و ساخت کلاهک.\n\n"
            f"**دکترین جاری شما:** `{config.ENRICHMENT_TIERS.get(curr_tier, {}).get('name')}`"
        )
        buttons = [
            [InlineKeyboardButton("پله ۱: سوخت ۳.۵٪ نیروگاهی", callback_data="nuc:set_tier:1")],
            [InlineKeyboardButton("پله ۲: ایزوتوپ پزشکی ۲۰٪", callback_data="nuc:set_tier:2")],
            [InlineKeyboardButton("پله ۳: اورانیوم ۶۰٪ (گریز)", callback_data="nuc:set_tier:3")],
            [InlineKeyboardButton("پله ۴: اورانیوم تسلیحاتی ۹۰٪", callback_data="nuc:set_tier:4")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="nuc:menu")],
        ]
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="Markdown")

    elif data.startswith("nuc:set_tier:"):
        tier_target = int(data.split(":")[2])
        ok, msg = db.set_country_enrichment_tier(cid, tier_target)
        if not ok:
            await query.edit_message_text(
                f"**خطا در تنظیم دکترین**\n\n> {msg}",
                reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت", callback_data="nuc:tier_menu")]]),
                parse_mode="Markdown"
            )
            return
        await query.edit_message_text(
            f"{msg}\n\n> _سانتریفیوژها با موفقیت بر روی دکترین جدید تنظیم شدند._",
            reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به برنامه هسته‌ای", callback_data="nuc:menu")]]),
            parse_mode="Markdown"
        )

    # ---------------- 3. اطلاعات پزشکی هسته‌ای ----------------
    elif data == "nuc:medical_info":
        med_res = c.get("medical_isotopes", 0) or 0
        text = (
            "**پروژه ملی رادیوداروها و پزشکی هسته‌ای**\n"
            "> تولید رادیوایزوتوپ‌های درمانی (نظیر ید-۱۳۱ و مولیبدن-۹۹) از طریق غنی‌سازی ۲۰٪ جهت تجهیز مراکز درمان سرطان.\n\n"
            "**دستاوردهای راهبردی سلامت:**\n"
            "• **افزایش پایدار رضایت عمومی:** **+۵٪ رضایت ملی** در محاسبات روزانه\n"
            "• **کاهش نرخ بیماری و مرگ‌ومیر جامعه**\n"
            "• **فناوری پیشران هسته‌ای:** ۳۰٪ صرفه‌جویی در مصرف سوخت ناوگان ارتش\n"
            "• **پرتودهی غلات:** افزایش ماندگاری سیلوها و کاهش ضایعات کشاورزی\n\n"
            f"> **ذخیره فعلی ایزوتوپ‌های پزشکی:** `{fa_num(med_res)}` کیلوگرم\n\n"
            "_جهت تولید ایزوتوپ‌ها، دکترین سانتریفیوژها را روی «پله ۲ (۲۰٪)» قرار دهید._"
        )
        buttons = [
            [InlineKeyboardButton("⚙️ تنظیم دکترین سانتریفیوژها", callback_data="nuc:tier_menu")],
            [InlineKeyboardButton("🔙 بازگشت به برنامه هسته‌ای", callback_data="nuc:menu")],
        ]
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="Markdown")

    # ---------------- 4. آزمایش انفجار هسته‌ای (فاز ۴) ----------------
    elif data == "nuc:test_prompt":
        w90 = c.get("weapons_grade_90", 0) or 0
        w90_req = config.NUCLEAR_TEST_WEAPONS_GRADE
        price = config.NUCLEAR_TEST_COST_MONEY
        gold_req = config.NUCLEAR_TEST_COST_GOLD
        chips_req = config.NUCLEAR_TEST_COST_CHIPS

        status_w90 = "موجود" if w90 >= w90_req else f"موجودی: {fa_num(w90)} ک‌گ"

        text = (
            "**فاز ۴: سایت آزمایش انفجار هسته‌ای زیرزمینی**\n"
            "> پیش از امکان کوچک‌سازی کلاهک‌های موشکی، عملکرد چاشنی‌های انفجار کروی در یک آزمایش زیرزمینی به اثبات می‌رسد.\n\n"
            "**پیش‌نیازها و مواد لازم:**\n"
            f"• اورانیوم تسلیحاتی ۹۰٪: {fa_num(w90_req)} کیلوگرم ({status_w90})\n"
            f"• هزینه اجرای آزمایش: {format_money(price)}\n"
            f"• پشتوانه طلا: {fa_num(gold_req)} شمش\n"
            f"• تراشه‌های میکروچیپ: {fa_num(chips_req)} عدد\n"
            f"• سطح فناوری مورد نیاز: حداقل سطح ۴ (سطح شما: {fa_num(c.get('tech_level', 1))})\n\n"
            "**پیامدهای بین‌المللی آزمایش:**\n"
            "> • ثبت امواج لرزه‌نگاری مصنوعی در رصدهای جهانی\n"
            "> • انتشار بیانیه و خبر رسمی در کانال اخبار\n"
            "> • پیوستن رسمی کشور به باشگاه قدرت‌های دارای توان آزمایش اتمی"
        )
        buttons = [
            [InlineKeyboardButton("💥 اجرای آزمایش انفجار زیرزمینی", callback_data="nuc:do_test")],
            [InlineKeyboardButton("🔙 انصراف", callback_data="nuc:menu")],
        ]
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="Markdown")

    elif data == "nuc:do_test":
        ok, msg = db.conduct_nuclear_test_transaction(cid)
        if not ok:
            await query.edit_message_text(
                f"**عدم امکان اجرای آزمایش**\n\n> {msg}",
                reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت", callback_data="nuc:menu")]]),
                parse_mode="Markdown"
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
            f"{msg}\n\n> _خبر رسمی این دستاورد در کانال اخبار منتشر گردید. فاز ۵ (کوچک‌سازی و مونتاژ کلاهک) برای کشور شما آزاد شد._",
            reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به برنامه هسته‌ای", callback_data="nuc:menu")]]),
            parse_mode="Markdown"
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

        status_w90 = "موجود" if w90 >= w90_req else f"موجودی: {fa_num(w90)} ک‌گ"
        status_test = "انجام‌شده" if tested or is_p5 else "انجام‌نشده"

        text = (
            "**فاز ۵: کوچک‌سازی و مونتاژ کلاهک راهبردی موشکی**\n"
            "> ادغام هسته شکافت‌پذیر و چاشنی‌های هدایت الکترونیکی جهت استقرار بر روی موشک‌های بالستیک یا زیردریایی‌های اتمی.\n\n"
            "**پیش‌نیازها و ملزومات ساخت:**\n"
            f"• اورانیوم تسلیحاتی ۹۰٪: {fa_num(w90_req)} کیلوگرم ({status_w90})\n"
            f"• آزمایش هسته‌ای (فاز ۴): {status_test}\n"
            f"• هزینه مونتاژ: {format_money(price)}\n"
            f"• پشتوانه طلا: {fa_num(gold_req)} شمش\n"
            f"• تراشه فوق‌پیشرفته: {fa_num(chips_req)} عدد\n"
            f"• سطح فناوری مورد نیاز: سطح ۵ بومی (سطح شما: {fa_num(c.get('tech_level', 1))})\n"
            f"• سقف مجاز نگهداری: {fa_num(curr_wh)} از {fa_num(eff_cap) if eff_cap is not None else 'نامحدود'} عدد\n\n"
            "> _هزینه نگهداری روزانه: ۵ میلیون دلار و ۲ تراشه در روز به ازای هر کلاهک مستقر._"
        )
        buttons = [
            [InlineKeyboardButton("🚀 مونتاژ و مسلح‌سازی ۱ کلاهک استراتژیک", callback_data="nuc:do_warhead")],
            [InlineKeyboardButton("🔙 انصراف", callback_data="nuc:menu")],
        ]
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="Markdown")

    elif data == "nuc:do_warhead":
        ok, msg = db.assemble_strategic_warhead_transaction(cid)
        if not ok:
            await query.edit_message_text(
                f"**عدم امکان مونتاژ کلاهک**\n\n> {msg}",
                reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت", callback_data="nuc:menu")]]),
                parse_mode="Markdown"
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
            f"{msg}\n\n> _کلاهک در زرادخانه بازدارندگی کشور مستقر گردید._",
            reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به برنامه هسته‌ای", callback_data="nuc:menu")]]),
            parse_mode="Markdown"
        )

    # ---------------- 6. NPT Toggle ----------------
    elif data == "nuc:npt_toggle":
        is_withdrawn = bool(c.get("npt_withdrawn", 0))
        if not is_withdrawn:
            text = (
                "**خروج رسمی از پیمان عدم اشاعه سلاح‌های هسته‌ای (NPT)**\n"
                "> آیا از خروج رسمی از این معاهده بین‌المللی اطمینان دارید؟\n\n"
                "**پیامدهای تصمیم:**\n"
                "• لغو کامل سقف کلاهک برای کشور شما\n"
                "• بی‌اثر شدن احکام و تعلیق‌های آژانس بین‌المللی اتمی\n"
                f"• **افت {fa_num(config.NPT_WITHDRAWAL_APPROVAL_HIT)}٪ رضایت عمومی** به دلیل انزوای دیپلماتیک\n"
                "• خطر وضع تحریم‌های اقتصادی توسط شورای امنیت سازمان ملل"
            )
            buttons = [
                [InlineKeyboardButton("🚪 تأیید خروج از NPT", callback_data="nuc:do_npt:withdraw")],
                [InlineKeyboardButton("❌ انصراف", callback_data="nuc:menu")],
            ]
        else:
            eff_cap = db.get_effective_warhead_cap(c)
            text = (
                "**بازگشت رسمی به پیمان عدم اشاعه (NPT)**\n"
                "> با بازگشت به NPT، تعهدات بین‌المللی مجدداً برقرار شده و ریسک تحریم‌های جامع کاهش می‌یابد.\n\n"
                f"> _شرط بازگشت: تعداد کلاهک‌های کشور نباید از سقف مجاز ({fa_num(eff_cap)} عدد) بیشتر باشد._"
            )
            buttons = [
                [InlineKeyboardButton("🕊️ بازگشت به پیمان NPT", callback_data="nuc:do_npt:rejoin")],
                [InlineKeyboardButton("❌ انصراف", callback_data="nuc:menu")],
            ]
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="Markdown")

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
            f"**نتیجه عملیات دیپلماتیک**\n\n> {msg}",
            reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به برنامه هسته‌ای", callback_data="nuc:menu")]]),
            parse_mode="Markdown"
        )
