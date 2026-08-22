# -*- coding: utf-8 -*-
"""
فایل اصلی اجرای بات «سیاست مدرن».
پشتیبانی از دکمه‌های ثابت پایین صفحه، سیستم دارایی‌های اختصاصی نظامی (Country Assets) و پنل ادمین.
اجرا: python main.py
"""

import datetime
import logging
from zoneinfo import ZoneInfo

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
)

import config
import database as db
import approval_system
import news_engine
from utils import format_money, format_number, format_oil
from handlers.nuclear import nuclear_main_menu, nuclear_callback_handler
from handlers.start import get_start_handlers
from handlers.country import country_profile, treasury, oil, army, help_command, approval_command, country_callback_handler
from handlers.diplomacy import diplomacy_menu, diplomacy_callback_handler, diplomacy_text_input_handler
from handlers.operations import operations_menu, operations_callback_handler, operations_text_input_handler
from handlers.statements import statements_menu, statements_callback_handler, statements_text_input_handler
from handlers.research import research_menu, research_callback_handler
from handlers.assets import show_assets_menu, get_assets_handlers
from handlers.market import market_main_menu, market_text_input_handler, get_market_handlers
from handlers.un import un_main_menu, un_text_input_handler, get_un_handlers
from handlers.shop import (
    shop, show_category, show_military_asset_category, back_to_shop,
    confirm_asset_purchase, execute_asset_purchase,
    confirm_civilian_purchase, execute_civilian_purchase,
    execute_warhead_assembly, npt_actions_handler
)
from handlers.admin import (
    admin_panel, admin_callback_handler, admin_input_text_handler,
    addmoney, removemoney, listcountries
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


INCOME_INTERVAL_HOURS = 6
INCOME_PARTS = 4
# گرید پرداخت به وقت ایران: بازه‌های ۰۳:۰۰، ۰۹:۰۰، ۱۵:۰۰، ۲۱:۰۰ تهران
IRAN_TZ = ZoneInfo("Asia/Tehran")
SLOT_OFFSET_HOURS = 3


def _iran_slot_key(dt_utc):
    """شناسه‌ی بازه‌ی ۶ ساعته به وقت ایران."""
    local = dt_utc.astimezone(IRAN_TZ)
    shifted = (local.hour - SLOT_OFFSET_HOURS) % 24
    return f"{local.date().isoformat()}_{shifted // 6}"


def _payout_due(last_raw, now_utc):
    """آیا پرداخت جدید لازم است؟ خروجی: (eligible, first_of_day)."""
    last_dt = None
    try:
        if len(last_raw) >= 19:
            last_dt = datetime.datetime.fromisoformat(last_raw)
        elif len(last_raw) == 10:
            last_dt = datetime.datetime.fromisoformat(last_raw + "T00:00:00+00:00")
    except Exception:
        last_dt = None
    if last_dt is None:
        return True, True
    local_now = now_utc.astimezone(IRAN_TZ)
    local_last = last_dt.astimezone(IRAN_TZ)
    first_of_day = local_last.date() != local_now.date()
    eligible = _iran_slot_key(last_dt) != _iran_slot_key(now_utc)
    return eligible, first_of_day


async def daily_income_job(context: ContextTypes.DEFAULT_TYPE, force: bool = False):
    """پرداخت درآمد به‌صورت تقسیط‌شده: هر ۶ ساعت یک‌چهارم درآمد.

    چرخه‌ی مصرف/رضایت/مهاجرت و هزینه‌ی محاصره‌های دریایی فقط در اولین پرداختِ
    هر روز تقویمی اجرا می‌شود تا نرخ مصرف روزانه تغییر نکند.
    force=True (توزیع فوری ادمین): پرداخت کامل + اجرای چرخه روزانه.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.date().isoformat()
    countries = db.get_all_countries()

    updated_count = 0
    for c in countries:
        last_raw = c.get("last_income_date") or ""
        eligible, first_of_day = _payout_due(last_raw, now)
        if force:
            eligible = True
            first_of_day = True
        if not eligible:
            continue

        maint_info = db.calculate_country_maintenance_cost(c["id"])
        tax_income = c.get("tax_income", 0) or 0
        gross_income = c["daily_income"] + tax_income
        sanction_note = ""
        # 🚫 تحریم جامع سازمان ملل: درآمد روزانه کشور تحریمی کاهش می‌یابد
        if c.get("un_sanctioned") or 0:
            factor = getattr(config, "UN_SANCTION_INCOME_FACTOR", 0.5)
            gross_income = int(gross_income * factor)
            sanction_note = f" — 🚫 درآمد تحت تحریم جامع سازمان ملل ({int(factor * 100)}٪)"
        net_full = gross_income - maint_info["total_maint"]
        net_payment = net_full if force else int(net_full / INCOME_PARTS)
        gold_daily = c.get("gold_daily", 0) or 0
        gold_payment = gold_daily if force else int(gold_daily / INCOME_PARTS)
        chips_daily = c.get("microchips_daily", 0) or 0
        chips_payment = chips_daily if force else int(chips_daily / INCOME_PARTS)
        u_daily = c.get("uranium_ore_daily", 0) or 0
        u_payment = u_daily if force else int(u_daily / INCOME_PARTS)
        fuel_daily = c.get("nuclear_fuel_daily", 0) or 0
        fuel_payment = fuel_daily if force else int(fuel_daily / INCOME_PARTS)
        med_daily = c.get("medical_isotopes_daily", 0) or 0
        med_payment = med_daily if force else int(med_daily / INCOME_PARTS)

        # 🛡 محافظ خزانه: هزینه نگهداری هرگز خزانه را منفی نمی‌کند.
        # (باقی‌مانده هزینه وقتی خزانه پر شود کسر نمی‌شود — ساده و غیرقابل سوءاستفاده)
        treasury_now = c.get("treasury", 0) or 0
        if net_payment < 0 and treasury_now + net_payment < 0:
            net_payment = -max(treasury_now, 0)

        db.adjust_treasury(c["id"], net_payment)
        db.adjust_gold(c["id"], gold_payment)
        if chips_payment > 0:
            db.adjust_microchips(c["id"], chips_payment)
        if u_payment > 0:
            db.adjust_uranium_ore(c["id"], u_payment)
        if fuel_payment > 0:
            db.adjust_nuclear_fuel(c["id"], fuel_payment)
        if med_payment > 0:
            db.adjust_medical_isotopes(c["id"], med_payment)

        app_res = None
        if first_of_day:
            app_res = approval_system.process_daily_approval_and_emigration(c)
            try:
                db.process_base_daily_costs()
            except Exception:
                pass
            # مصرف سوخت روزانه نیروهای مسلح (واقع‌گرایی اقتصادی)
            try:
                fuel_need = db.calculate_military_fuel_consumption(c["id"])
                if fuel_need > 0:
                    oil_now = c.get("oil_reserves") or 0
                    if oil_now >= fuel_need:
                        db.adjust_oil(c["id"], -fuel_need)
                    else:
                        # کسری سوخت → تنزل رضایت عمومی
                        db.adjust_oil(c["id"], -oil_now)
                        new_app = max(0, (c.get("approval_rating") or 80) - 3)
                        db.update_country_field(c["id"], "approval_rating", new_app)
            except Exception:
                pass

        db.update_country_field(c["id"], "last_income_date", now.isoformat())
        if force:
            db.add_transaction(c["id"], "daily_income", "توزیع فوری درآمد روزانه (ادمین)", net_full)
        else:
            db.add_transaction(c["id"], "daily_income", f"واریز دوره‌ای درآمد (هر {INCOME_INTERVAL_HOURS} ساعت){sanction_note}", net_payment)

        p_id = c.get("player_id")
        if p_id:
            try:
                if first_of_day and app_res is not None:
                    report_msg = approval_system.build_daily_country_report_message(db.get_country_by_id(c["id"]), app_res, today)
                else:
                    c2 = db.get_country_by_id(c["id"])
                    chips_line = f"\n• 💻 میکروچیپ: +{chips_payment:,} عدد" if chips_payment > 0 else ""
                    u_line = f"\n• ☢️ کیک زرد: +{u_payment:,} تن" if u_payment > 0 else ""
                    fuel_line = f"\n• 🧪 سوخت غنی‌شده: +{fuel_payment:,} ک‌گ" if fuel_payment > 0 else ""
                    report_msg = (
                        f"💵 *واریز دوره‌ای درآمد — {c2['flag']} {c2['name']}*\n\n"
                        f"• مبلغ واریزی: *{format_money(net_payment)}*\n"
                        f"• طلا: +{gold_payment}{chips_line}{u_line}{fuel_line}\n"
                        f"• خزانه جدید: {format_money(c2['treasury'])}\n\n"
                        f"_درآمد روزانه در {INCOME_PARTS} پرداختِ روزانه (۰۹:۰۰، ۱۵:۰۰، ۲۱:۰۰، ۰۳:۰۰ به وقت ایران) واریز می‌شود._"
                    )
                await context.bot.send_message(chat_id=p_id, text=report_msg, parse_mode="Markdown")
            except Exception as e:
                logger.warning(f"Could not send daily report to player {p_id}: {e}")

        updated_count += 1

    # 4. هزینه روزانه محاصره‌های دریایی — فقط یک بار در هر روز تقویمی
    if db.get_setting("blockade_cycle_date") == today:
        active_blockades = []
    else:
        db.set_setting("blockade_cycle_date", today)
        active_blockades = db.get_all_active_blockades()
    for blk in active_blockades:
        b_id = blk["blockader_id"]
        t_id = blk["target_id"]
        b_c = db.get_country_by_id(b_id)
        t_c = db.get_country_by_id(t_id)

        if not b_c or not t_c:
            continue

        oil_cost = 100_000
        money_cost = 2_000_000

        # واقع‌گرایی: سوخت روزانه ناوگان محاصره‌گر از ذخایر نفت تأمین می‌شود (تولید روزانه مجانی نیست)
        if b_c["treasury"] < money_cost or (b_c.get("oil_reserves", 0) or 0) < oil_cost:
            db.lift_naval_blockade(b_id, t_id)
            # بازیابی رضایت عمومی هدف پس از پایان کامل محاصره
            if not db.is_country_blockaded(t_id):
                new_app = min(100, (t_c.get("approval_rating") or 80) + 15)
                db.update_country_field(t_id, "approval_rating", new_app)
            lift_msg = (
                f"⚓ **لغو خودکار محاصره دریایی!**\n\n"
                f"کشور {b_c['flag']} {b_c['name']} به دلیل عدم تامین سوخت روزانه (۱۰۰,۰۰۰ بشکه) و هزینه‌های نگهداری ناوگان ({format_money(money_cost)})، "
                f"مجبور به لغو محاصره دریایی کشور {t_c['flag']} {t_c['name']} گردید."
            )
            if b_c.get("player_id"):
                try: await context.bot.send_message(chat_id=b_c["player_id"], text=lift_msg, parse_mode="Markdown")
                except Exception: pass
            if t_c.get("player_id"):
                try: await context.bot.send_message(chat_id=t_c["player_id"], text=lift_msg, parse_mode="Markdown")
                except Exception: pass
            await news_engine.trigger_unblockade_news(context.bot, b_c, t_c, is_broken=False)
        else:
            db.adjust_treasury(b_id, -money_cost)
            db.adjust_oil(b_id, -oil_cost)
            db.add_transaction(b_id, "blockade_cost", f"هزینه روزانه محاصره بنادر {t_c['name']}", -money_cost)

    # 5. بررسی و بازگشایی خودکار تنگه‌ها در صورت انهدام ناوگان کشور کنترل‌کننده
    try:
        reopened = db.auto_check_and_reopen_straits_if_navy_destroyed()
        for r in reopened:
            owner = r["owner"]
            s_info = r["strait_info"]
            s_msg = (
                f"🌊 **لغو خودکار کنترل بر تنگه استراتژیک!**\n\n"
                f"کشور {owner['flag']} {owner['name']} به دلیل انهدام یا تضعیف ناوگان دریایی "
                f"(کمتر از ۵ شناور فعال یا ۱۰ میلیون دلار ارزش)، کنترل نظامی خود بر **{s_info['name']}** را از دست داد و این آبراه فوراً بازگشایی شد."
            )
            if owner.get("player_id"):
                try: await context.bot.send_message(chat_id=owner["player_id"], text=s_msg, parse_mode="Markdown")
                except Exception: pass
            await news_engine.trigger_strait_news(context.bot, owner, s_info["name"], "open")
    except Exception as e:
        logger.warning(f"Error checking strait reopening: {e}")

    logger.info(f"درآمد روزانه، محاسبه رضایت عمومی و ارسال گزارش برای {updated_count} کشور انجام شد.")
    return updated_count


def main():
    db.init_db()

    # concurrent_updates: پردازش موازی پیام‌ها — یک درخواست کند (مثل تحلیل AI)
    # نباید بقیه‌ی بازیکن‌ها را در صف قفل کند
    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .concurrent_updates(True)
        .build()
    )

    # هاندرهای ثبت‌نام و انتخاب کشور
    for handler in get_start_handlers():
        app.add_handler(handler)

    # سیستم دارایی‌های اختصاصی کشورها (/assets)
    for handler in get_assets_handlers():
        app.add_handler(handler)

    # دستورات متنی نمایش وضعیت کشور
    app.add_handler(CommandHandler("country", country_profile))
    app.add_handler(CommandHandler("approval", approval_command))
    app.add_handler(CommandHandler("treasury", treasury))
    app.add_handler(CommandHandler("oil", oil))
    app.add_handler(CommandHandler("army", army))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(country_callback_handler, pattern=r"^country:"))

    # دکمه‌های ثابت پایین صفحه (Reply Keyboard Text Handlers)
    app.add_handler(MessageHandler(filters.Regex("^🌐 وضعیت کشور$"), country_profile))
    app.add_handler(MessageHandler(filters.Regex("^📊 رضایت عمومی$"), approval_command))
    app.add_handler(MessageHandler(filters.Regex("^🎖️ دارایی‌های نظامی$"), show_assets_menu))
    app.add_handler(MessageHandler(filters.Regex("^🏦 خزانه و طلا$"), treasury))
    app.add_handler(MessageHandler(filters.Regex("^🛢️ وضعیت نفت$"), oil))
    app.add_handler(MessageHandler(filters.Regex("^🪖 وضعیت ارتش$"), army))
    app.add_handler(MessageHandler(filters.Regex("^🏪 فروشگاه$"), shop))
    app.add_handler(MessageHandler(filters.Regex("^📜 راهنما$"), help_command))
    app.add_handler(MessageHandler(filters.Regex("^👑 پنل مدیریت$"), admin_panel))

    # فروشگاه (دکمه‌های شیشه‌ای)
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(CallbackQueryHandler(show_category, pattern=r"^shopcat:"))
    app.add_handler(CallbackQueryHandler(show_military_asset_category, pattern=r"^shop_asset_cat:"))
    app.add_handler(CallbackQueryHandler(back_to_shop, pattern=r"^shopback$"))
    app.add_handler(CallbackQueryHandler(confirm_asset_purchase, pattern=r"^confirm_asset_buy:"))
    app.add_handler(CallbackQueryHandler(execute_asset_purchase, pattern=r"^do_asset_buy:"))
    app.add_handler(CallbackQueryHandler(confirm_civilian_purchase, pattern=r"^buyciv:"))
    app.add_handler(CallbackQueryHandler(execute_civilian_purchase, pattern=r"^docivbuy:"))
    app.add_handler(CallbackQueryHandler(execute_warhead_assembly, pattern=r"^shop:do_assemble_warhead$"))
    app.add_handler(CallbackQueryHandler(npt_actions_handler, pattern=r"^shop:npt_"))

    # سیستم ابلاغ عملیات و رول‌های نظامی
    app.add_handler(CommandHandler("role", operations_menu))
    app.add_handler(CommandHandler("operation", operations_menu))
    app.add_handler(CommandHandler("ops", operations_menu))
    app.add_handler(CallbackQueryHandler(operations_callback_handler, pattern=r"^op:"))
    app.add_handler(MessageHandler(filters.Regex("^🎯 عملیات$"), operations_menu))

    # سیستم بیانیه‌ها، رسمی‌سازی متن و توییت‌ها
    app.add_handler(CommandHandler("statement", statements_menu))
    app.add_handler(CommandHandler("tweet", statements_menu))
    app.add_handler(CommandHandler("rewrite", statements_menu))
    app.add_handler(CallbackQueryHandler(statements_callback_handler, pattern=r"^stmt:"))
    app.add_handler(MessageHandler(filters.Regex("^📢 بیانیه و توییت$"), statements_menu))

    # سیستم تحقیق و توسعه و لول فناوری بومی
    app.add_handler(CommandHandler("research", research_menu))
    app.add_handler(CommandHandler("tech", research_menu))
    app.add_handler(CallbackQueryHandler(research_callback_handler, pattern=r"^research:"))

    # برنامه راهبردی هسته‌ای (/nuclear)
    app.add_handler(CommandHandler(["nuclear", "nuke"], nuclear_main_menu))
    app.add_handler(CallbackQueryHandler(nuclear_callback_handler, pattern=r"^nuc:"))

    # سیستم دیپلماسی و معاهدات بین‌المللی
    app.add_handler(CommandHandler("diplomacy", diplomacy_menu))
    app.add_handler(CommandHandler("message", diplomacy_menu))
    app.add_handler(CommandHandler("trade", diplomacy_menu))
    app.add_handler(CommandHandler("aid", diplomacy_menu))
    app.add_handler(CommandHandler("relations", diplomacy_menu))
    app.add_handler(CallbackQueryHandler(diplomacy_callback_handler, pattern=r"^dip:"))
    app.add_handler(MessageHandler(filters.Regex("^🤝 دیپلماسی و روابط$"), diplomacy_menu))

    # پنل پیشرفته ادمین (مخصوص آیدی 8052987465)
    app.add_handler(CommandHandler(["admin", "panel"], admin_panel))
    app.add_handler(CallbackQueryHandler(admin_callback_handler, pattern=r"^admin:"))

    async def ignore_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.callback_query:
            try:
                await update.callback_query.answer()
            except Exception:
                pass

    app.add_handler(CallbackQueryHandler(ignore_callback, pattern=r"^ignore$"))

    # سیستم بازار بورس بین‌المللی کالاها (/market)
    for handler in get_market_handlers():
        app.add_handler(handler)

    # سیستم سازمان ملل متحد (/un)
    for handler in get_un_handlers():
        app.add_handler(handler)

    # سیستم مدیریت تلفات تجهیزات (ماژول مستقل)
    from handlers.losses import get_losses_handlers
    for handler in get_losses_handlers():
        app.add_handler(handler)

    # سیستم تحرکات نظامی (مانور + پایگاه‌های پیشروی)
    from handlers.bases import get_bases_handlers
    for handler in get_bases_handlers():
        app.add_handler(handler)

    # دستورات متنی قدیمی ادمین
    app.add_handler(CommandHandler("addmoney", addmoney))
    app.add_handler(CommandHandler("removemoney", removemoney))
    app.add_handler(CommandHandler("listcountries", listcountries))

    # دریافت ورودی‌های متنی و تصویری (تایپی) ادمین، دیپلماسی، بورس، سازمان ملل، رول‌ها و بیانیه‌ها
    async def combined_text_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        from handlers.bases import mv_text_input_handler
        if context.user_data.get("mv_input"):
            handled = await mv_text_input_handler(update, context)
            if handled:
                return
        if context.user_data.get("admin_awaiting_input"):
            await admin_input_text_handler(update, context)
        elif context.user_data.get("diplomacy_input"):
            await diplomacy_text_input_handler(update, context)
        elif context.user_data.get("market_sell_draft"):
            await market_text_input_handler(update, context)
        elif context.user_data.get("un_draft"):
            await un_text_input_handler(update, context)
        elif context.user_data.get("roleplay_text_input"):
            await operations_text_input_handler(update, context)
        elif context.user_data.get("statement_input"):
            await statements_text_input_handler(update, context)

    app.add_handler(MessageHandler(filters.TEXT | filters.PHOTO & ~filters.COMMAND, combined_text_input_handler))

    # درآمد روزانه: هر روز ساعت 00:05 به وقت سرور
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(daily_income_job, interval=900, first=10)  # چک هر ۱۵ دقیقه؛ پرداخت هر ۶ ساعت

    logger.info("بات در حال اجراست...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()