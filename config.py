# -*- coding: utf-8 -*-
"""
تمام تنظیمات قابل تغییر بازی اینجاست.
برای تغییر قیمت‌ها یا مقادیر اولیه، فقط همین فایل رو ویرایش کن،
نیازی به تغییر بقیه کدها نیست.
"""

import os

# ===== توکن بات =====
# توکن رو از @BotFather می‌گیری و اینجا می‌ذاری
# بهتره به‌جای نوشتن مستقیم توکن، اون رو در Environment Variable هاست بذاری
BOT_TOKEN = os.environ.get("BOT_TOKEN", "TOKEN_ATO_EINJA_BEZAR")

# ===== آیدی عددی ادمین‌ها (آیدی تلگرام خودت) =====
# آیدی عددی خودت رو می‌تونی از بات @userinfobot بگیری
ADMIN_IDS = [
    8052987465,
]

# ===== لیست کشورهای قابل انتخاب در بازی =====
# برای اضافه/کم کردن کشور از لیست بازی، فقط همینجا رو ویرایش کن.
COUNTRIES = {
    "iran":    {"name": "ایران",    "flag": "🇮🇷"},
    "germany": {"name": "آلمان",    "flag": "🇩🇪"},
    "qatar":   {"name": "قطر",      "flag": "🇶🇦"},
    "usa":     {"name": "آمریکا",   "flag": "🇺🇸"},
    "russia":  {"name": "روسیه",    "flag": "🇷🇺"},
    "china":   {"name": "چین",      "flag": "🇨🇳"},
    "france":  {"name": "فرانسه",   "flag": "🇫🇷"},
    "uk":      {"name": "انگلیس",   "flag": "🇬🇧"},
    "japan":   {"name": "ژاپن",     "flag": "🇯🇵"},
    "turkey":  {"name": "ترکیه",    "flag": "🇹🇷"},
    "saudi":   {"name": "عربستان",  "flag": "🇸🇦"},
    "ukraine": {"name": "اوکراین",  "flag": "🇺🇦"},
    "india":   {"name": "هند",      "flag": "🇮🇳"},
    "brazil":  {"name": "برزیل",    "flag": "🇧🇷"},
    "egypt":   {"name": "مصر",      "flag": "🇪🇬"},
    "uae":     {"name": "امارات",   "flag": "🇦🇪"},
}

# ===== مقادیر اولیه هر کشور تازه‌ساز =====
STARTING_VALUES = {
    "population": 10_000_000,
    "treasury": 50_000_000,
    "tax_income": 1_000_000,
    "daily_income": 5_000_000,
    "gold": 200,
    "gold_daily": 10,
    "oil_reserves": 100_000_000,
    "oil_production": 1_000_000,
    "grain": 100_000,
    "electricity": 100,
    "active_personnel": 50_000,
    "reserve_personnel": 100_000,
}

# ===== قیمت هر بشکه نفت (برای فروش پیش‌فرض) =====
OIL_PRICE_PER_BARREL = 1

# ===== فروشگاه: ساختمان‌ها =====
BUILDINGS = {
    "house":      {"name": "🏠 ساختمان مسکونی", "price": 1_000_000},
    "office":     {"name": "🏢 ساختمان اداری",   "price": 2_000_000},
    "commercial": {"name": "🏬 ساختمان تجاری",   "price": 3_000_000},
    "hotel":      {"name": "🏨 هتل",             "price": 7_000_000},
    "tower":      {"name": "🏙️ برج تجاری",       "price": 10_000_000},
    "skyscraper": {"name": "🏙️ آسمان‌خراش",      "price": 20_000_000},
}

# ===== فروشگاه: صنعت =====
FACTORIES = {
    "small_factory":    {"name": "🏭 کارخانه کوچک",   "price": 3_000_000},
    "medium_factory":   {"name": "🏭 کارخانه متوسط",  "price": 7_000_000},
    "large_factory":    {"name": "🏭 کارخانه بزرگ",   "price": 15_000_000},
    "industrial_complex": {"name": "🏭 مجتمع صنعتی", "price": 25_000_000},
}

# ===== فروشگاه: انرژی =====
POWER_PLANTS = {
    "fossil_plant":  {"name": "⚡ نیروگاه فسیلی",   "price": 10_000_000},
    "solar_plant":   {"name": "☀️ نیروگاه خورشیدی", "price": 8_000_000},
    "wind_plant":    {"name": "🌬️ نیروگاه بادی",    "price": 10_000_000},
    "hydro_plant":   {"name": "💧 نیروگاه آبی",     "price": 15_000_000},
    "nuclear_plant": {"name": "☢️ نیروگاه هسته‌ای", "price": 50_000_000},
}

# ===== فروشگاه: تجهیزات نظامی =====
MILITARY_EQUIPMENT = {
    "fighter_jet":    {"name": "✈️ جنگنده",        "price": 2_000_000, "category": "air"},
    "helicopter":     {"name": "🚁 بالگرد",         "price": 1_000_000, "category": "air"},
    "drone":          {"name": "🛩️ پهپاد",          "price": 500_000,   "category": "air"},
    "tank":           {"name": "🛡️ تانک",           "price": 1_500_000, "category": "ground"},
    "armored_vehicle":{"name": "🚙 خودرو زرهی",     "price": 700_000,   "category": "ground"},
    "artillery":      {"name": "🎯 توپخانه",         "price": 900_000,   "category": "ground"},
    "missile_system": {"name": "🚀 سامانه موشکی",   "price": 3_000_000, "category": "missile"},
    "air_defense":    {"name": "🛡️ پدافند",         "price": 2_500_000, "category": "defense"},
    "radar":          {"name": "📡 رادار",           "price": 1_200_000, "category": "defense"},
    "warship":        {"name": "🚢 کشتی",           "price": 5_000_000, "category": "navy"},
    "boat":           {"name": "🛥️ قایق",           "price": 400_000,   "category": "navy"},
}

# ===== ادغام همه‌ی اقلام فروشگاه در یک دیکشنری برای دسترسی راحت =====
ALL_SHOP_ITEMS = {}
for group in (BUILDINGS, FACTORIES, POWER_PLANTS, MILITARY_EQUIPMENT):
    ALL_SHOP_ITEMS.update(group)

# ===== مسیر فایل دیتابیس =====
DB_PATH = os.environ.get("DB_PATH", "game.db")
