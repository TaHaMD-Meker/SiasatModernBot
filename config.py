# -*- coding: utf-8 -*-
"""
تنظیمات بازی، لیست کشورها، مقادیر اولیه و کاتالوگ تجهیزات اختصاصی هر کشور (Country Assets Catalog).
"""

import os

# ===== توکن بات =====
BOT_TOKEN = os.environ.get("BOT_TOKEN", "TOKEN_ATO_EINJA_BEZAR")

# ===== آیدی عددی ادمین اصلی =====
admin_env = os.environ.get("ADMIN_IDS", "")
if admin_env:
    ADMIN_IDS = [int(x.strip()) for x in admin_env.split(",") if x.strip().isdigit()]
else:
    ADMIN_IDS = [
        8052987465,
    ]

# ===== لیست کشورهای قابل انتخاب در بازی =====
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
    "treasury": 500_000_000,
    "tax_income": 10_000_000,
    "daily_income": 50_000_000,
    "gold": 500,
    "gold_daily": 20,
    "oil_reserves": 200_000_000,
    "oil_production": 2_000_000,
    "grain": 200_000,
    "electricity": 200,
    "active_personnel": 100_000,
    "reserve_personnel": 200_000,
}

# ===== دسته‌بندی‌های دارایی‌های نظامی =====
ASSET_CATEGORIES = {
    "Aircraft":     ("✈️ نیروی هوایی", "فروند"),
    "Missiles":     ("🚀 موشکی", "قبضه"),
    "Air Defense":  ("🛡️ پدافند هوایی", "سامانه"),
    "Navy":         ("🚢 نیروی دریایی", "فروند"),
    "Ground Forces":("🚛 نیروی زمینی", "دستگاه"),
    "UAV":          ("🛩️ پهپادها", "فروند"),
    "Artillery":    ("🎯 توپخانه", "قبضه"),
}

# ===== کاتالوگ دارایی‌های اختصاصی کشورها (Country Assets Catalog) =====
COUNTRY_EQUIPMENT_CATALOG = {
    "usa": [
        {"key": "f35",            "name": "F-35 Lightning II",    "category": "Aircraft",     "price": 15_000_000, "initial": 591,  "maint": 50_000},
        {"key": "f22",            "name": "F-22 Raptor",          "category": "Aircraft",     "price": 25_000_000, "initial": 180,  "maint": 80_000},
        {"key": "f15",            "name": "F-15 Eagle",           "category": "Aircraft",     "price": 10_000_000, "initial": 245,  "maint": 30_000},
        {"key": "f16",            "name": "F-16 Fighting Falcon", "category": "Aircraft",     "price": 8_000_000,  "initial": 782,  "maint": 20_000},
        {"key": "b2",             "name": "B-2 Spirit",           "category": "Aircraft",     "price": 50_000_000, "initial": 20,   "maint": 150_000},
        {"key": "b52",            "name": "B-52 Stratofortress",  "category": "Aircraft",     "price": 30_000_000, "initial": 69,   "maint": 100_000},
        {"key": "mq9",            "name": "MQ-9 Reaper",          "category": "UAV",          "price": 3_000_000,  "initial": 290,  "maint": 10_000},
        {"key": "ah64",           "name": "AH-64 Apache",         "category": "Aircraft",     "price": 5_000_000,  "initial": 794,  "maint": 15_000},
        {"key": "m1_abrams",      "name": "M1 Abrams",            "category": "Ground Forces","price": 2_000_000,  "initial": 5000, "maint": 5_000},
        {"key": "bradley",        "name": "Bradley IFV",          "category": "Ground Forces","price": 1_000_000,  "initial": 4000, "maint": 2_500},
        {"key": "himars",         "name": "HIMARS",               "category": "Artillery",    "price": 3_000_000,  "initial": 400,  "maint": 8_000},
        {"key": "ford_class",     "name": "Gerald R. Ford Class", "category": "Navy",         "price": 100_000_000,"initial": 2,    "maint": 500_000},
        {"key": "burke_class",    "name": "Arleigh Burke Class",  "category": "Navy",         "price": 20_000_000, "initial": 70,   "maint": 100_000},
        {"key": "virginia_class", "name": "Virginia Class",       "category": "Navy",         "price": 35_000_000, "initial": 25,   "maint": 150_000},
        {"key": "patriot_pac3",   "name": "Patriot PAC-3",        "category": "Air Defense",  "price": 10_000_000, "initial": 53,   "maint": 30_000},
        {"key": "thaad",          "name": "THAAD",                "category": "Air Defense",  "price": 40_000_000, "initial": 3,    "maint": 100_000},
        {"key": "nasams",         "name": "NASAMS",               "category": "Air Defense",  "price": 8_000_000,  "initial": 12,   "maint": 25_000},
        {"key": "tomahawk",       "name": "Tomahawk",             "category": "Missiles",     "price": 2_000_000,  "initial": 3240, "maint": 2_000},
        {"key": "trident2",       "name": "Trident II D5",        "category": "Missiles",     "price": 15_000_000, "initial": 280,  "maint": 40_000},
    ],
    "russia": [
        {"key": "su57",           "name": "Su-57 Felon",          "category": "Aircraft",     "price": 20_000_000, "initial": 22,   "maint": 70_000},
        {"key": "su35",           "name": "Su-35S Flanker-E",     "category": "Aircraft",     "price": 12_000_000, "initial": 110,  "maint": 40_000},
        {"key": "kalibr",         "name": "Kalibr Cruise Missile","category": "Missiles",     "price": 1_500_000,  "initial": 2000, "maint": 1_500},
        {"key": "iskander",       "name": "Iskander-M",           "category": "Missiles",     "price": 3_000_000,  "initial": 500,  "maint": 5_000},
        {"key": "s400",           "name": "S-400 Triumf",         "category": "Air Defense",  "price": 15_000_000, "initial": 56,   "maint": 40_000},
        {"key": "pantsir",        "name": "Pantsir-S1",           "category": "Air Defense",  "price": 5_000_000,  "initial": 110,  "maint": 15_000},
        {"key": "borei",          "name": "Borei Class Submarine","category": "Navy",         "price": 40_000_000, "initial": 7,    "maint": 200_000},
        {"key": "t90m",           "name": "T-90M Proryv",         "category": "Ground Forces","price": 2_500_000,  "initial": 1200, "maint": 6_000},
    ],
    "iran": [
        {"key": "fattah",         "name": "Fattah Hypersonic",    "category": "Missiles",     "price": 2_500_000,  "initial": 100,  "maint": 3_000},
        {"key": "kheybar_shekan", "name": "Kheybar Shekan",       "category": "Missiles",     "price": 2_000_000,  "initial": 350,  "maint": 2_000},
        {"key": "sejjil",         "name": "Sejjil Ballistic",     "category": "Missiles",     "price": 4_000_000,  "initial": 150,  "maint": 5_000},
        {"key": "khorramshahr",   "name": "Khorramshahr-4",       "category": "Missiles",     "price": 5_000_000,  "initial": 80,   "maint": 6_000},
        {"key": "s300",           "name": "S-300PMU2",            "category": "Air Defense",  "price": 12_000_000, "initial": 32,   "maint": 35_000},
        {"key": "bavar373",       "name": "Bavar-373",            "category": "Air Defense",  "price": 10_000_000, "initial": 20,   "maint": 30_000},
        {"key": "shahed136",      "name": "Shahed 136",           "category": "UAV",          "price": 100_000,    "initial": 2500, "maint": 500},
        {"key": "mohajer6",       "name": "Mohajer-6",            "category": "UAV",          "price": 500_000,    "initial": 300,  "maint": 2_000},
        {"key": "jamaran",        "name": "Jamaran Class Frigate","category": "Navy",         "price": 15_000_000, "initial": 5,    "maint": 50_000},
        {"key": "karrar_tank",    "name": "Karrar Tank",          "category": "Ground Forces","price": 1_500_000,  "initial": 800,  "maint": 4_000},
    ],
}

# کاتالوگ عمومی برای سایر کشورها
DEFAULT_COUNTRY_EQUIPMENT = [
    {"key": "gen_fighter",   "name": "جنگنده نسل ۴",         "category": "Aircraft",     "price": 10_000_000, "initial": 150, "maint": 25_000},
    {"key": "gen_bomber",    "name": "بمب‌افکن استراتژیک",     "category": "Aircraft",     "price": 25_000_000, "initial": 20,  "maint": 60_000},
    {"key": "gen_missile",   "name": "موشک کروز استراتژیک",   "category": "Missiles",     "price": 2_000_000,  "initial": 500, "maint": 2_000},
    {"key": "gen_airdef",    "name": "سامانه پدافند موشکی",  "category": "Air Defense",  "price": 10_000_000, "initial": 20,  "maint": 25_000},
    {"key": "gen_uav",       "name": "پهپاد شناسایی-رزمی",  "category": "UAV",          "price": 1_000_000,  "initial": 200, "maint": 3_000},
    {"key": "gen_frigate",   "name": "ناو محافظ",             "category": "Navy",         "price": 20_000_000, "initial": 10,  "maint": 80_000},
    {"key": "gen_tank",      "name": "تانک اصلی میدان نبرد",  "category": "Ground Forces","price": 2_000_000,  "initial": 1000,"maint": 5_000},
    {"key": "gen_artillery", "name": "توپخانه خودکششی",       "category": "Artillery",    "price": 1_500_000,  "initial": 300, "maint": 4_000},
]

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

ALL_SHOP_ITEMS = {}
for group in (BUILDINGS, FACTORIES, POWER_PLANTS):
    ALL_SHOP_ITEMS.update(group)

# ===== مسیر فایل دیتابیس =====
DB_PATH = os.environ.get("DB_PATH", "game.db")
