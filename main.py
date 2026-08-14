# -*- coding: utf-8 -*-
"""
فایل اصلی اجرای بات «سیاست مدرن».
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
from handlers.start import get_start_handlers
from handlers.country import country_profile, treasury, oil, army, help_command
from handlers.shop import shop, show_category, back_to_shop, confirm_purchase, execute_purchase
from handlers.admin import (
    admin_panel, admin_callback_handler, admin_input_text_handler,
    addmoney, removemoney, listcountries
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def daily_income_job(context: ContextTypes.DEFAULT_TYPE):
    """
    هر کشور رو چک می‌کنه؛ اگه امروز درآمدش رو نگرفته، اضافه می‌کنه.
    مانع گرفتن چندباره درآمد روزانه در یک روز می‌شود.
    """
    today = datetime.date.today().isoformat()
    countries = db.get_all_countries()

    updated_count = 0
    for c in countries:
        if c["last_income_date"] == today:
            continue  # امروز قبلاً گرفته

        db.adjust_treasury(c["id"], c["daily_income"])
        db.adjust_gold(c["id"], c["gold_daily"])
        db.update_country_field(c["id"], "last_income_date", today)
        db.add_transaction(c["id"], "daily_income", "درآمد روزانه", c["daily_income"])
        updated_count += 1

    logger.info(f"درآمد روزانه برای {updated_count} کشور از مجموع {len(countries)} کشور واریز شد.")


def main():
    db.init_db()

    app = Application.builder().token(config.BOT_TOKEN).build()

    # ثبت‌نام و انتخاب کشور با دکمه شیشه‌ای
    for handler in get_start_handlers():
        app.add_handler(handler)

    # دستورات نمایش وضعیت کشور
    app.add_handler(CommandHandler("country", country_profile))
    app.add_handler(CommandHandler("treasury", treasury))
    app.add_handler(CommandHandler("oil", oil))
    app.add_handler(CommandHandler("army", army))
    app.add_handler(CommandHandler("help", help_command))

    # فروشگاه
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(CallbackQueryHandler(show_category, pattern=r"^shopcat:"))
    app.add_handler(CallbackQueryHandler(back_to_shop, pattern=r"^shopback$"))
    app.add_handler(CallbackQueryHandler(confirm_purchase, pattern=r"^buyitem:"))
    app.add_handler(CallbackQueryHandler(execute_purchase, pattern=r"^confirmbuy:"))

    # پنل پیشرفته ادمین
    app.add_handler(CommandHandler(["admin", "panel"], admin_panel))
    app.add_handler(CallbackQueryHandler(admin_callback_handler, pattern=r"^admin:"))

    # دستورات متنی قدیمی ادمین
    app.add_handler(CommandHandler("addmoney", addmoney))
    app.add_handler(CommandHandler("removemoney", removemoney))
    app.add_handler(CommandHandler("listcountries", listcountries))

    # دریافت ورودی‌های متنی (تایپی) برای پنل ادمین
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, admin_input_text_handler))

    # درآمد روزانه: هر روز ساعت 00:05 به وقت سرور اجرا می‌شود
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_daily(daily_income_job, time=datetime.time(hour=0, minute=5))

    logger.info("بات در حال اجراست...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
