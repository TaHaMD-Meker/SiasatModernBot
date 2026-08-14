# -*- coding: utf-8 -*-
"""
توابع کمکی، مهم‌ترینش فرمت کردن اعداد پول طبق قانون سند:
اعداد باید گرد و خوانا نمایش داده بشن، نه اعداد طولانی.
"""

def format_money(amount: int) -> str:
    """
    1_000_000       -> "1 میلیون دلار"
    20_000_000      -> "20 میلیون دلار"
    1_500_000_000   -> "1.5 میلیارد دلار"
    500              -> "500 دلار"
    """
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
        return f"{sign}{amount} دلار"

    # اگر عدد رنده، بدون اعشار نشون بده
    if value == int(value):
        value_str = str(int(value))
    else:
        value_str = f"{value:.1f}"

    return f"{sign}{value_str} {unit} دلار"


def format_number(amount: int) -> str:
    """برای اعدادی که پول نیستن (مثل جمعیت یا نفر) با جداکننده هزارتایی."""
    return f"{amount:,}".replace(",", "٬")


def format_oil(barrels: int) -> str:
    if barrels >= 1_000_000:
        value = barrels / 1_000_000
        value_str = str(int(value)) if value == int(value) else f"{value:.1f}"
        return f"{value_str} میلیون بشکه"
    return f"{format_number(barrels)} بشکه"
