# -*- coding: utf-8 -*-
"""
دستورات ادمین. فقط آیدی‌های داخل config.ADMIN_IDS اجازه استفاده دارن.
"""

from telegram import Update
from telegram.ext import ContextTypes

import database as db
import config
from utils import format_money


def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


async def addmoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کاربرد: /addmoney <player_id> <amount>"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ این دستور فقط برای ادمین‌هاست.")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text("کاربرد درست: /addmoney <player_id> <amount>")
        return

    try:
        player_id, amount = int(args[0]), int(args[1])
    except ValueError:
        await update.message.reply_text("player_id و amount باید عدد باشن.")
        return

    country = db.get_country_by_player(player_id)
    if not country:
        await update.message.reply_text("کشوری با این player_id پیدا نشد.")
        return

    db.adjust_treasury(country["id"], amount)
    db.add_log(actor=str(update.effective_user.id), action="admin_addmoney",
               details=f"player={player_id} amount={amount}")

    await update.message.reply_text(
        f"✅ انجام شد.\n{country['name']}: {format_money(amount)} به خزانه اضافه شد."
    )


async def removemoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """کاربرد: /removemoney <player_id> <amount>"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ این دستور فقط برای ادمین‌هاست.")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text("کاربرد درست: /removemoney <player_id> <amount>")
        return

    try:
        player_id, amount = int(args[0]), int(args[1])
    except ValueError:
        await update.message.reply_text("player_id و amount باید عدد باشن.")
        return

    country = db.get_country_by_player(player_id)
    if not country:
        await update.message.reply_text("کشوری با این player_id پیدا نشد.")
        return

    db.adjust_treasury(country["id"], -amount)
    db.add_log(actor=str(update.effective_user.id), action="admin_removemoney",
               details=f"player={player_id} amount={amount}")

    await update.message.reply_text(
        f"✅ انجام شد.\n{country['name']}: {format_money(amount)} از خزانه کم شد."
    )


async def listcountries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ این دستور فقط برای ادمین‌هاست.")
        return

    countries = db.get_all_countries()
    if not countries:
        await update.message.reply_text("هنوز هیچ کشوری ثبت نشده.")
        return

    lines = ["📋 لیست کشورها:\n"]
    for c in countries:
        lines.append(f"{c['flag']} {c['name']} — player_id: {c['player_id']} — خزانه: {format_money(c['treasury'])}")

    await update.message.reply_text("\n".join(lines))
