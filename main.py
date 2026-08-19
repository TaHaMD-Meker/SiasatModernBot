# -*- coding: utf-8 -*-
"""
فایل اصلی اجرای بات «سیاست مدرن».
پشتیبانی از دکمه‌های ثابت پایین صفحه، سیستم دارایی‌های اختصاصی نظامی (Country Assets) و پنل ادمین.
اجرا: python main.py
"""

import datetime
import logging

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
)

import config
import database as db
import approval_system
import news_engine
from utils import format_money, format_number, format_oil
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
    confirm_civilian_purchase, execute_civilian_purchase
)
from handlers.admin import (
    admin_panel, admin_callback_handler, admin_input_text_handler, war_view_callback_handler,
    addmoney, removemoney, listcountries
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def daily_income_job(context: ContextTypes.DEFAULT_TYPE, force: bool = False):
    today = datetime.date.today().isoformat()
    countries = db.get_all_countries()

    updated_count = 0
    for c in countries:
        if not force and c["last_income_date"] == today:
            continue

        # 1. Deposit income & gold minus maintenance
        maint_info = db.calculate_country_maintenance_cost(c["id"])
        tax_income = c.get("tax_income", 0) or 0
        net_income = c["daily_income"] + tax_income - maint_info["total_maint"]

        db.adjust_treasury(c["id"], net_income)
        db.adjust_gold(c["id"], c["gold_daily"])

        # 2. Process Approval Rating, Consumption & Emigration
        app_res = approval_system.process_daily_approval_and_emigration(c)

        db.update_country_field(c["id"], "last_income_date", today)
        db.add_transaction(c["id"], "daily_income", "درآمد روزانه + مالیات (منهای نگهداری)", net_income)

        # 3. Send Daily Country Report Message to player
        updated_c = db.get_country_by_id(c["id"])
        report_msg = approval_system.build_daily_country_report_message(updated_c, app_res, today)

        p_id = c.get("player_id")
        if p_id:
            try:
                await context.bot.send_message(chat_id=p_id, text=report_msg, parse_mode="Markdown")
            except Exception as e:
                logger.warning(f"Could not send daily report to player {p_id}: {e}")

        updated_count += 1

    # 4. Process Daily Naval Blockade Costs & Auto-Lifting
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
        avail_oil = b_c.get("oil_reserves", 0) + b_c.get("oil_production", 0)

        if b_c["treasury"] < money_cost or avail_oil < oil_cost:
            db.lift_naval_blockade(b_id, t_id)
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
            deficit_oil = max(0, oil_cost - b_c.get("oil_production", 0))
            if deficit_oil > 0:
                db.adjust_oil(b_id, -deficit_oil)
            db.add_transaction(b_id, "blockade_cost", f"هزینه روزانه محاصره بنادر {t_c['name']}", -money_cost)

    logger.info(f"درآمد روزانه، محاسبه رضایت عمومی و ارسال گزارش برای {updated_count} کشور انجام شد.")
    return updated_count


def main():
    db.init_db()

    app = Application.builder().token(config.BOT_TOKEN).build()

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
    app.add_handler(CallbackQueryHandler(war_view_callback_handler, pattern=r"^war_view:"))

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

    # دستورات متنی قدیمی ادمین
    app.add_handler(CommandHandler("addmoney", addmoney))
    app.add_handler(CommandHandler("removemoney", removemoney))
    app.add_handler(CommandHandler("listcountries", listcountries))

    # دریافت ورودی‌های متنی و تصویری (تایپی) ادمین، دیپلماسی، بورس، سازمان ملل، رول‌ها و بیانیه‌ها
    async def combined_text_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        job_queue.run_daily(daily_income_job, time=datetime.time(hour=0, minute=5))

    logger.info("بات در حال اجراست...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()