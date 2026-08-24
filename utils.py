# -*- coding: utf-8 -*-
"""
توابع کمکی، فرمت‌دهی اعداد و کیبورد اصلی بازی.
"""

try:
    from telegram import ReplyKeyboardMarkup
except ImportError:
    ReplyKeyboardMarkup = None
import config


def format_money(amount: int) -> str:
    """
    1_000_000       -> "1 میلیون دلار"
    20_000_000      -> "20 میلیون دلار"
    1_500_000_000   -> "1.5 میلیارد دلار"
    500              -> "500 دلار"
    """
    if amount is None:
        return "0 دلار"
    try:
        amount = int(amount)
    except (ValueError, TypeError):
        return "0 دلار"

    sign = "-" if amount < 0 else ""
    amount = abs(amount)

    if amount >= 1_000_000_000:
        value = amount / 1_000_000_000
        unit = "میلیارد"
    elif amount >= 1_000_000:
        value = amount / 1_000_000
        unit = "میلیون"
    elif amount >= 1_000:
        value = amount / 1_000
        unit = "هزار"
    else:
        return f"{sign}{amount:,}".replace(",", "٬") + " دلار"

    if value == int(value):
        value_str = str(int(value))
    else:
        value_str = f"{value:.1f}"

    return f"{sign}{value_str} {unit} دلار"


def format_number(amount: int) -> str:
    """برای اعدادی که پول نیستن (مثل جمعیت یا نفر) با جداکننده هزارتایی."""
    if amount is None:
        return "0"
    try:
        amount = int(amount)
    except (ValueError, TypeError):
        return "0"
    return f"{amount:,}".replace(",", "٬")


def format_oil(barrels: int) -> str:
    if barrels is None:
        return "0 بشکه"
    try:
        barrels = int(barrels)
    except (ValueError, TypeError):
        return "0 بشکه"
    if barrels >= 1_000_000:
        value = barrels / 1_000_000
        value_str = str(int(value)) if value == int(value) else f"{value:.1f}"
        return f"{value_str} میلیون بشکه"
    return f"{format_number(barrels)} بشکه"


def get_main_keyboard(user_id: int):
    """ایجاد کیبورد اصلی دکمه‌های پایین صفحه (ReplyKeyboardMarkup)"""
    buttons = [
        ["🌐 وضعیت کشور", "🎯 عملیات"],
        ["🏪 فروشگاه", "📢 بیانیه و توییت"],
        ["🤝 دیپلماسی و روابط", "🎖️ دارایی‌های نظامی"],
        ["🎯 ستاد توسعه و اقدامات راهبردی", "🏛️ دانشکده"],
    ]
    if user_id in config.ADMIN_IDS:
        buttons.append(["⭐️ بتل‌پس فصلی", "💎 خدمات ویژه VIP", "👑 پنل مدیریت"])
    else:
        buttons.append(["⭐️ بتل‌پس فصلی", "💎 خدمات ویژه VIP"])

    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)


def clear_text_input_flags(user_data: dict):
    """پاک‌سازی تمام پرچم‌های ورودی متنی برای جلوگیری از تداخل فیلدها."""
    input_keys = [
        "admin_awaiting_input", "diplomacy_input", "market_sell_draft",
        "un_draft", "roleplay_text_input", "statement_input", "aid_draft",
        "trade_draft", "mil_draft", "role_submit_draft"
    ]
    for key in input_keys:
        if key in user_data:
            del user_data[key]