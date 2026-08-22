# -*- coding: utf-8 -*-
"""
ماژول برنامه راهبردی هسته‌ای، چرخه سوخت و بازدارندگی استراتژیک (Strategic Nuclear Program).
شامل ۵ فاز واقعی:
  ۱. تأمین کیک زرد (معدن / واردات)
  ۲. احداث مجتمع غنی‌سازی و سانتریفیوژهای زیرزمینی
  ۳. دکترین غنی‌سازی پله‌پله (۳.۵٪ ⬅️ ۲۰٪ پزشکی ⬅️ ۶۰٪ آستانه گریز ⬅️ ۹۰٪ تسلیحاتی)
  ۴. سایت آزمایش انفجار هسته‌ای زیرزمینی
  ۵. کوچک‌سازی و مونتاژ کلاهک بازدارنده موشکی
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database as db
import config
import news_engine
from utils import format_money, format_number, format_oil


def _kb(rows):
    return InlineKeyboardMarkup(rows)


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

    tech_lvl = c.get("tech_level", 1) or 1
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

    # وضعیت آژانس و NPT
    npt_status = "🚪 خارج‌شده از پیمان NPT" if c.get("npt_withdrawn") else "🕊️ متعهد به NPT"
    iaea_status = "⛔ برنامه تعلیق‌شده توسط آژانس" if c.get("enrichment_suspended") else ("🚫 تحت تحریم جامع سازمان ملل" if c.get("un_sanctioned") else "🟢 وضعیت بازرسی آژانس عادی")

    eff_cap = db.get_effective_warhead_cap(c)
    cap_str = f"{eff_cap} عدد" if eff_cap is not None else "نامحدود (P5 / خارج از NPT)"

    lines = [
        f"☢️ **برنامه راهبردی هسته‌ای و چرخه سوخت — {c['flag']} {c['name']}**\n",
        "━━━━━━━━━━━━━━━━━━\n",
        f"• **وضعیت دیپلماتیک:** {npt_status}\n",
        f"• **وضعیت آژانس اتمی (IAEA):** {iaea_status}\n",
        f"• **سایت غنی‌سازی سانتریفیوژ:** {'✅ ' + str(enr_fac_count) + ' واحد فعال' if enr_fac_count or is_p5 else '❌ فاقد مجتمع غنی‌سازی'}\n",
        f"• **دکترین فعال سانتریفیوژها:** {tier_info['name']}\n",
        f"• **آزمایش انفجار هسته‌ای (فاز ۴):** {'✅ انجام شده' if tested or is_p5 else '❌ انجام نشده'}\n\n",
        "📊 **ذخایر و موجودی زنجیره استراتژیک هسته‌ای:**\n",
        f"• ☢️ **کیک زرد خام (اورانیوم):** `{format_number(u_ore)} تن` (تولید: `+{format_number(u_ore_d)} تن/روز`)\n",
        f"• 🟢 **سوخت راکتور (۳.۵٪):** `{format_number(fuel_35)} کیلوگرم` (تولید: `+{format_number(fuel_d)} ک‌گ/روز`)\n",
        f"• 🟡 **ایزوتوپ پزشکی و پیشران (۲۰٪):** `{format_number(med_20)} کیلوگرم` (تولید: `+{format_number(med_d)} ک‌گ/روز`)\n",
        f"• 🟠 **اورانیوم در آستانه گریز (۶۰٪):** `{format_number(enr_60)} کیلوگرم`\n",
        f"• 🔴 **اورانیوم تسلیحاتی (۹۰٪):** `{format_number(w_90)} کیلوگرم`\n",
        f"• 🚀 **کلاهک‌های راهبردی مستقر:** `☢️ {format_number(warheads)} عدد` (سقف مجاز: `{cap_str}`)\n",
    ]

    if warheads > 0:
        lines.append(f"\n⚠️ *هزینه نگهداری زرادخانه:* {format_money(warheads * 5_000_000)}/روز و {warheads * 2} میکروچیپ/روز\n")

    buttons = []

    # دکمه ساخت مجتمع غنی‌سازی اگر ندارد یا می‌خواهد اضافه کند
    if enr_fac_count < 2 and not is_p5:
        buttons.append([InlineKeyboardButton("🔬 احداث مجتمع غنی‌سازی و سانتریفیوژ", callback_data="nuc:build_prompt")])

    buttons.append([
        InlineKeyboardButton("⚙️ تنظیم دکترین سانتریفیوژها و غنا", callback_data="nuc:tier_menu"),
    ])

    buttons.append([
        InlineKeyboardButton("🏥 پزشکی هسته‌ای و سلامت ملی (+۵٪ رضایت)", callback_data="nuc:medical_info"),
    ])

    if not tested and not is_p5:
        buttons.append([InlineKeyboardButton("💥 سایت آزمایش انفجار هسته‌ای (فاز ۴)", callback_data="nuc:test_prompt")])

    buttons.append([
        InlineKeyboardButton("🚀 کوچک‌سازی و مونتاژ کلاهک موشکی (فاز ۵)", callback_data="nuc:warhead_prompt"),
    ])

    if not is_p5:
        if c.get("npt_withdrawn"):
            buttons.append([InlineKeyboardButton("🕊️ بازگشت به پیمان عدم اشاعه (NPT)", callback_data="nuc:npt_toggle")])
        else:
            buttons.append([InlineKeyboardButton("🚪 خروج رسمی از پیمان عدم اشاعه (NPT)", callback_data="nuc:npt_toggle")])

    buttons.append([InlineKeyboardButton("🔙 بازگشت به تحرکات نظامی", callback_data="op:movements")])

    text = "".join(lines)
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

    if data == "nuc:menu":
        await nuclear_main_menu(update, context)

    # ---------------- 1. احداث مجتمع غنی‌سازی ----------------
    elif data == "nuc:build_prompt":
        price = config.ENRICHMENT_FACILITY_PRICE
        gold_req = config.ENRICHMENT_FACILITY_GOLD
        chips_req = config.ENRICHMENT_FACILITY_CHIPS
        tech_req = config.ENRICHMENT_FACILITY_TECH_REQ

        text = (
            "🔬 **احداث مجتمع غنی‌سازی و سانتریفیوژهای زیرزمینی**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "این مجتمع در عمق زمین و زیر پناهگاه‌های بتنی احداث می‌شود تا فرآیند تبدیل کیک زرد به سوخت راکتور یا اورانیوم غنی‌شده را انجام دهد.\n\n"
            "📋 **الزامات و هزینه‌های احداث:**\n"
            f"• 💰 **هزینه مالی:** {format_money(price)}\n"
            f"• 🪙 **طلا مورد نیاز:** {gold_req} شمش طلا\n"
            f"• 💻 **میکروچیپ مورد نیاز:** {chips_req} عدد تراشه\n"
            f"• 🔬 **پیش‌نیاز فناوری:** سطح {tech_req} به بالا (سطح شما: {c.get('tech_level', 1)})\n"
            "• ⚡ **مصرف برق:** نیازمند برق پایدار شبکه\n\n"
            "آیا مایل به احداث و راه‌اندازی این مجتمع هستید؟"
        )
        buttons = [
            [InlineKeyboardButton("✅ تأیید و احداث مجتمع غنی‌سازی", callback_data="nuc:do_build")],
            [InlineKeyboardButton("🔙 انصراف", callback_data="nuc:menu")],
        ]
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="Markdown")

    elif data == "nuc:do_build":
        ok, msg = db.build_enrichment_facility_transaction(cid)
        if not ok:
            await query.edit_message_text(
                f"❌ **عدم امکان احداث مجتمع غنی‌سازی:**\n\n{msg}",
                reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت", callback_data="nuc:menu")]]),
                parse_mode="Markdown"
            )
            return
        await query.edit_message_text(
            f"{msg}\n\n💡 اکنون می‌توانید دکترین سانتریفیوژها را در منوی اصلی تنظیم فرمایید.",
            reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به برنامه هسته‌ای", callback_data="nuc:menu")]]),
            parse_mode="Markdown"
        )

    # ---------------- 2. تنظیم دکترین سانتریفیوژها ----------------
    elif data == "nuc:tier_menu":
        curr_tier = c.get("enrichment_tier", 1) or 1
        text = (
            "⚙️ **تنظیم دکترین و پله‌های غنی‌سازی سانتریفیوژها**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً سطح و هدف غنی‌سازی را انتخاب فرمایید:\n\n"
            "🟢 **۱. سوخت صلح‌آمیز نیروگاهی (۳.۵٪ تا ۵٪):**\n"
            "• خروجی: `+۲۵ ک‌گ سوخت/روز` (مصرف ۴۰ تن کیک زرد)\n"
            "• فایده: صفر شدن مصرف نفت شبکه برق و آزادی نفت برای صادرات.\n\n"
            "🟡 **۲. ایزوتوپ‌های پزشکی و پیشران (۲۰٪):**\n"
            "• خروجی: `+۱۰ ک‌گ ایزوتوپ/روز` (مصرف ۶۰ تن کیک زرد + ۲ چیپ)\n"
            "• فایده: +۵٪ رضایت ملی پایدار درمان سرطان + ۳۰٪ کاهش سوخت ناوگان.\n\n"
            "🟠 **۳. آستانه گریز هسته‌ای (۶۰٪):**\n"
            "• خروجی: `+۵ ک‌گ اورانیوم ۶۰٪/روز` (مصرف ۸۰ تن کیک زرد + ۴ چیپ)\n"
            "• پیامد: اهرم چانه‌زنی دیپلماتیک (هشدار زرد آژانس IAEA).\n\n"
            "🔴 **۴. غنی‌سازی تسلیحاتی (۹۰٪):**\n"
            "• خروجی: `+۲.۵ ک‌گ اورانیوم ۹۰٪/روز` (مصرف ۱۲۰ تن کیک زرد + ۶ چیپ)\n"
            "• پیامد: تولید مواد انفجاری آزمایش اتمی و کلاهک (آلارم قرمز IAEA).\n\n"
            f"🎯 **دکترین فعلی شما:** `{config.ENRICHMENT_TIERS.get(curr_tier, {}).get('name')}`"
        )
        buttons = [
            [InlineKeyboardButton("🟢 پله ۱: سوخت ۳.۵٪ نیروگاهی", callback_data="nuc:set_tier:1")],
            [InlineKeyboardButton("🟡 پله ۲: ایزوتوپ پزشکی و پیشران ۲۰٪", callback_data="nuc:set_tier:2")],
            [InlineKeyboardButton("🟠 پله ۳: اورانیوم ۶۰٪ (آستانه گریز)", callback_data="nuc:set_tier:3")],
            [InlineKeyboardButton("🔴 پله ۴: اورانیوم تسلیحاتی ۹۰٪", callback_data="nuc:set_tier:4")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="nuc:menu")],
        ]
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="Markdown")

    elif data.startswith("nuc:set_tier:"):
        tier_target = int(data.split(":")[2])
        ok, msg = db.set_country_enrichment_tier(cid, tier_target)
        if not ok:
            await query.edit_message_text(
                f"❌ **تغییر دکترین انجام نشد:**\n\n{msg}",
                reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت", callback_data="nuc:tier_menu")]]),
                parse_mode="Markdown"
            )
            return
        await query.edit_message_text(
            f"{msg}\n\n📊 سانتریفیوژها با موفقیت بر روی هدف جدید کالیبره شدند.",
            reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به برنامه هسته‌ای", callback_data="nuc:menu")]]),
            parse_mode="Markdown"
        )

    # ---------------- 3. اطلاعات پزشکی هسته‌ای ----------------
    elif data == "nuc:medical_info":
        med_res = c.get("medical_isotopes", 0) or 0
        text = (
            "🏥 **پروژه پزشکی هسته‌ای، رادیوداروها و سلامت ملی**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "با تولید سوخت غنی‌شده ۲۰٪، ایزوتوپ‌های درمانی (نظیر ید-۱۳۱ و مولیبدن-۹۹) تولید شده و در مراکز درمان سرطان کشور به کار گرفته می‌شوند.\n\n"
            "💎 **فواید و دستاوردهای فعال بودن این بخش:**\n"
            "• 😀 **افزایش پایدار رضایت عمومی:** **+۵٪ رضایت ملی** در ارزیابی‌های روزانه\n"
            "• 📉 **کاهش چشمگیر نرخ مرگ‌ومیر و بیماری‌ها**\n"
            "• ⚓ **فناوری پیشران اتمی:** ۳۰٪ صرفه‌جویی در مصرف سوخت ناوگان ارتش\n"
            "• 🌾 **پرتودهی غلات:** کاهش ضایعات کشاورزی و پایداری سیلوها\n\n"
            f"📦 **ذخایر فعلی ایزوتوپ‌های پزشکی شما:** `{format_number(med_res)} کیلوگرم`\n\n"
            "💡 _جهت تولید ایزوتوپ‌های پزشکی، دکترین سانتریفیوژها را روی «پله ۲ (۲۰٪)» قرار دهید._"
        )
        buttons = [
            [InlineKeyboardButton("⚙️ رفتن به تنظیم دکترین سانتریفیوژها", callback_data="nuc:tier_menu")],
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

        text = (
            "💥 **فاز ۴: سایت آزمایش انفجار هسته‌ای زیرزمینی (Nuclear Test)**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "قبل از امکان کوچک‌سازی و ساخت کلاهک‌های موشکی، کشور شما باید یک انفجار آزمایشی زیرزمینی در کویر ثبت کند تا کارایی چاشنی‌های انفجاری اثبات شود.\n\n"
            "📋 **پیش‌نیازها و مواد لازم:**\n"
            f"• 🔴 **اورانیوم تسلیحاتی ۹۰٪:** {w90_req} کیلوگرم ({'✅' if w90 >= w90_req else '❌ موجودی: ' + str(w90) + ' ک‌گ'})\n"
            f"• 💰 **هزینه اجرای تست:** {format_money(price)}\n"
            f"• 🪙 **شمش طلا:** {gold_req} شمش\n"
            f"• 💻 **تراشه پیشرفته:** {chips_req} عدد\n"
            f"• 🔬 **سطح فناوری:** حداقل سطح ۴ (سطح شما: {c.get('tech_level', 1)})\n\n"
            "⚠️ **پیامدهای بین‌المللی آزمایش:**\n"
            "• امواج لرزه‌نگاری مصنوعی در سراسر جهان ثبت خواهد شد.\n"
            "• خبر فوری و هشدار شورای امنیت در کانال اخبار منتشر می‌گردد.\n"
            "• کشور شما رسماً به جمع قدرت‌های دارای توان آزمایش اتمی می‌پیوندد."
        )
        buttons = [
            [InlineKeyboardButton("💥 اجرای آزمایش انفجار هسته‌ای زیرزمینی", callback_data="nuc:do_test")],
            [InlineKeyboardButton("🔙 انصراف", callback_data="nuc:menu")],
        ]
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="Markdown")

    elif data == "nuc:do_test":
        ok, msg = db.conduct_nuclear_test_transaction(cid)
        if not ok:
            await query.edit_message_text(
                f"❌ **آزمایش هسته‌ای انجام نشد:**\n\n{msg}",
                reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت", callback_data="nuc:menu")]]),
                parse_mode="Markdown"
            )
            return

        # Broadcast breaking news
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
            f"{msg}\n\n📢 خبر رسمی این دستاورد در کانال اخبار منتشر گردید. اکنون فاز ۵ (کوچک‌سازی و ساخت کلاهک) برای کشور شما آزاد شد!",
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

        text = (
            "🚀 **فاز ۵: کوچک‌سازی و مونتاژ کلاهک راهبردی بازدارنده**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "در این مرحله، هسته شکافت‌پذیر با چاشنی‌های انفجاری کروی ادغام و کوچک‌سازی شده تا بر روی موشک‌های بالستیک قاره‌پیما یا زیردریایی‌های اتمی سوار شود.\n\n"
            "📋 **پیش‌نیازها و مواد لازم:**\n"
            f"• 🔴 **اورانیوم تسلیحاتی ۹۰٪:** {w90_req} کیلوگرم ({'✅' if w90 >= w90_req else '❌ موجودی: ' + str(w90) + ' ک‌گ'})\n"
            f"• 💥 **آزمایش هسته‌ای فاز ۴:** {'✅ انجام شده' if tested or is_p5 else '❌ انجام نشده'}\n"
            f"• 💰 **هزینه مونتاژ:** {format_money(price)}\n"
            f"• 🪙 **شمش طلا:** {gold_req} شمش\n"
            f"• 💻 **میکروچیپ فوق‌پیشرفته:** {chips_req} عدد\n"
            f"• 🔬 **سطح فناوری:** بالاترین سطح (سطح ۵) (سطح شما: {c.get('tech_level', 1)})\n"
            f"• 📊 **سقف مجاز نگهداری کلاهک:** `{curr_wh}/{eff_cap if eff_cap is not None else 'نامحدود'}`\n\n"
            "⚠️ **هزینه نگهداری روزانه:** ۵,۰۰۰,۰۰۰ دلار و ۲ عدد میکروچیپ در روز به ازای هر کلاهک."
        )
        buttons = [
            [InlineKeyboardButton("☢️ مونتاژ و مسلح‌سازی ۱ کلاهک استراتژیک", callback_data="nuc:do_warhead")],
            [InlineKeyboardButton("🔙 انصراف", callback_data="nuc:menu")],
        ]
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="Markdown")

    elif data == "nuc:do_warhead":
        ok, msg = db.assemble_strategic_warhead_transaction(cid)
        if not ok:
            await query.edit_message_text(
                f"❌ **مونتاژ کلاهک انجام نشد:**\n\n{msg}",
                reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت", callback_data="nuc:menu")]]),
                parse_mode="Markdown"
            )
            return

        # Broadcast intel alert
        try:
            await news_engine.trigger_general_broadcast(
                context.bot,
                f"🚨 **گزارش محرمانه اطلاعاتی و هشدار آژانس بین‌المللی انرژی اتمی**\n\n"
                f"کشور {c['flag']} **{c['name']}** یک کلاهک راهبردی بازدارنده جدید را با موفقیت مونتاژ و در سیلوهای زیرزمینی خود مستقر کرد."
            )
        except Exception:
            pass

        await query.edit_message_text(
            f"{msg}\n\n🌐 کلاهک در زرادخانه بازدارندگی کشور مستقر گردید.",
            reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به برنامه هسته‌ای", callback_data="nuc:menu")]]),
            parse_mode="Markdown"
        )

    # ---------------- 6. NPT Toggle ----------------
    elif data == "nuc:npt_toggle":
        is_withdrawn = bool(c.get("npt_withdrawn", 0))
        if not is_withdrawn:
            text = (
                "🚪 **خروج رسمی از معاهده عدم اشاعه سلاح‌های هسته‌ای (NPT)**\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "آیا از خروج رسمی از NPT اطمینان دارید؟\n\n"
                "⚠️ **پیامدهای خروج از NPT:**\n"
                "• سقف ۵ کلاهک برای کشور شما به طور کامل لغو می‌شود.\n"
                "• تمامی تعلیق‌ها و محدودیت‌های آژانس بی‌اثر می‌گردد.\n"
                f"• **افت {config.NPT_WITHDRAWAL_APPROVAL_HIT}٪ رضایت عمومی** به دلیل فشارهای دیپلماتیک و انزوای بین‌المللی.\n"
                "• خطر وضع تحریم‌های جامع اقتصادی توسط سازمان ملل متحد."
            )
            buttons = [
                [InlineKeyboardButton("🚪 تأیید خروج از NPT", callback_data="nuc:do_npt:withdraw")],
                [InlineKeyboardButton("❌ انصراف", callback_data="nuc:menu")],
            ]
        else:
            eff_cap = db.get_effective_warhead_cap(c)
            text = (
                "🕊️ **بازگشت رسمی به پیمان عدم اشاعه (NPT)**\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "با بازگشت به NPT، تعهدات بین‌المللی مجدداً برقرار شده و خطر تحریم‌های سازمان ملل کاهش می‌یابد.\n\n"
                f"📌 شرط بازگشت: تعداد کلاهک‌های کشور نباید از سقف مجاز ({eff_cap} عدد) بیشتر باشد."
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
            f"✅ {msg}",
            reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به برنامه هسته‌ای", callback_data="nuc:menu")]]),
            parse_mode="Markdown"
        )
