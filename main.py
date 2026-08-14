# -*- coding: utf-8 -*-
"""
فایل اصلی اجرای بات.
اجرا: python main.py
"""

import datetime
import logging

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes
)

import config
import database as db
from handlers.start import get_start_handler
from handlers.country import country_profile, treasury, oil, army, help_command
from handlers.shop import shop, show_category, back_to_shop, confirm_purchase, execute_purchase
from handlers.admin import addmoney, removemoney, listcountries

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def daily_income_job(context: ContextTypes.DEFAULT_TYPE):
    """
    هر کشور رو چک می‌کنه؛ اگه امروز درآمدش رو نگرفته، اضافه می‌کنه.
    این کار جلوی گرفتن دوباره درآمد روزانه رو می‌گیره (طبق بند ۳۰ سند).
    """
    today = datetime.date.today().isoformat()
    countries = db.get_all_countries()

    for c in countries:
        if c["last_income_date"] == today:
            continue  # امروز قبلاً گرفته

        db.adjust_treasury(c["id"], c["daily_income"])
        db.update_country_field(c["id"], "gold", c["gold"] + c["gold_daily"])
        db.update_country_field(c["id"], "last_income_date", today)
        db.add_transaction(c["id"], "daily_income", "درآمد روزانه", c["daily_income"])

    logger.info(f"درآمد روزانه برای {len(countries)} کشور بررسی شد.")


def main():
    db.init_db()

    app = Application.builder().token(config.BOT_TOKEN).build()

    # ثبت‌نام کشور (مکالمه‌ای)
    app.add_handler(get_start_handler())

    # دستورات نمایش وضعیت
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

    # ادمین
    app.add_handler(CommandHandler("addmoney", addmoney))
    app.add_handler(CommandHandler("removemoney", removemoney))
    app.add_handler(CommandHandler("listcountries", listcountries))

    # درآمد روزانه: هر روز ساعت 00:05 به وقت سرور اجرا میشه
    job_queue = app.job_queue
    job_queue.run_daily(daily_income_job, time=datetime.time(hour=0, minute=5))

    logger.info("بات در حال اجراست...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
