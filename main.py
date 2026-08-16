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
from handlers.start import get_start_handlers
from handlers.country import country_profile, treasury, oil, army, help_command, approval_command, country_callback_handler
from handlers.diplomacy import diplomacy_menu, diplomacy_callback_handler, diplomacy_text_input_handler
from handlers.operations import operations_menu, operations_callback_handler, operations_text_input_handler
from handlers.statements import statements_menu, statements_callback_handler, statements_text_input_handler
from handlers.research import research_menu, research_callback_handler
from handlers.assets import show_assets_menu, get_assets_handlers
from handlers.shop import (
    shop, show_category, show_military_asset_category, back_to_shop,
    confirm_asset_purchase, execute_asset_purchase,
    confirm_civilian_purchase, execute_civilian_purchase
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


async def daily_income_job(context: ContextTypes.DEFAULT_TYPE, force: bool = False):
    today = datetime.date.today().isoformat()
    countries = db.get_all_countries()

    updated_count = 0
    for c in countries:
        if not force and c["last_income_date"] == today:
            continue

        # 1. Deposit income & gold minus maintenance
        maint_info = db.calculate_country_maintenance_cost(c["id"])
        net_income = c["daily_income"] - maint_info["total_maint"]

        db.adjust_treasury(c["id"], net_income)
        db.adjust_gold(c["id"], c["gold_daily"])

        # 2. Process Approval Rating, Consumption & Emigration
        app_res = approval_system.process_daily_approval_and_emigration(c)

        db.update_country_field(c["id"], "last_income_date", today)
        db.add_transaction(c["id"], "daily_income", "درآمد روزانه و واریز منابع", c["daily_income"])

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

    # دستورات متنی قدیمی ادمین
    app.add_handler(CommandHandler("addmoney", addmoney))
    app.add_handler(CommandHandler("removemoney", removemoney))
    app.add_handler(CommandHandler("listcountries", listcountries))

    # دریافت ورودی‌های متنی و تصویری (تایپی) ادمین، دیپلماسی، رول‌ها و بیانیه‌ها
    async def combined_text_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if context.user_data.get("admin_awaiting_input"):
            await admin_input_text_handler(update, context)
        elif context.user_data.get("diplomacy_input"):
            await diplomacy_text_input_handler(update, context)
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