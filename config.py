# -*- coding: utf-8 -*-
"""
تنظیمات عمومی بازی، لیست ۱۷ کشور، مقادیر اولیه و کاتالوگ جامع دارایی‌های نظامی اختصاصی تمام کشورها (Country Assets Catalog).
دارای فیلد producible (داشتن خط تولید بومی) برای تفکیک سلاح‌های بومی قابل ساخت در فروشگاه از سلاح‌های وارداتی.
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

# ===== لیست کامل کشورهای قابل انتخاب در بازی (۱۷ کشور) =====
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
    "israel":  {"name": "اسرائیل",  "flag": "🇮🇱"},
}

# ===== مقادیر اولیه عمومی کشورها =====
STARTING_VALUES = {
    "population": 20_000_000,
    "treasury": 40_000_000,
    "tax_income": 8_000_000,
    "daily_income": 15_000_000,
    "gold": 300,
    "gold_daily": 40,
    "oil_reserves": 100_000_000,
    "oil_production": 1_500_000,
    "grain": 100,
    "electricity": 130,
    "active_personnel": 200_000,
    "reserve_personnel": 500_000,
}

# ===== مقادیر اختصاصی و بالانس‌شده اقتصادی و انسانی تمام ۱۷ کشور =====
COUNTRY_STARTING_OVERRIDES = {
    "usa": {
        "population": 340_000_000,
        "treasury": 80_000_000,
        "tax_income": 12_000_000,
        "daily_income": 28_000_000,
        "gold": 500,
        "gold_daily": 60,
        "oil_reserves": 250_000_000,
        "oil_production": 5_000_000,
        "grain": 50,
        "electricity": 145,
        "active_personnel": 1_300_000,
        "reserve_personnel": 800_000,
    },
    "china": {
        "population": 1_400_000_000,
        "treasury": 120_000_000,
        "tax_income": 18_000_000,
        "daily_income": 25_000_000,
        "gold": 700,
        "gold_daily": 80,
        "oil_reserves": 250_000_000,
        "oil_production": 4_500_000,
        "grain": 60,
        "electricity": 155,
        "active_personnel": 2_000_000,
        "reserve_personnel": 1_000_000,
    },
    "russia": {
        "population": 144_000_000,
        "treasury": 55_000_000,
        "tax_income": 12_000_000,
        "daily_income": 16_000_000,
        "gold": 400,
        "gold_daily": 60,
        "oil_reserves": 375_000_000,
        "oil_production": 4_000_000,
        "grain": 40,
        "electricity": 145,
        "active_personnel": 1_320_000,
        "reserve_personnel": 2_000_000,
    },
    "iran": {
        "population": 90_000_000,
        "treasury": 45_000_000,
        "tax_income": 7_000_000,
        "daily_income": 14_000_000,
        "gold": 250,
        "gold_daily": 50,
        "oil_reserves": 250_000_000,
        "oil_production": 4_000_000,
        "grain": 35,
        "electricity": 130,
        "active_personnel": 610_000,
        "reserve_personnel": 1_200_000,
    },
    "germany": {
        "population": 84_000_000,
        "treasury": 55_000_000,
        "tax_income": 10_000_000,
        "daily_income": 18_000_000,
        "gold": 350,
        "gold_daily": 50,
        "oil_reserves": 40_000_000,
        "oil_production": 1_000_000,
        "grain": 45,
        "electricity": 155,
        "active_personnel": 185_000,
        "reserve_personnel": 800_000,
    },
    "uk": {
        "population": 69_000_000,
        "treasury": 50_000_000,
        "tax_income": 10_000_000,
        "daily_income": 17_000_000,
        "gold": 350,
        "gold_daily": 50,
        "oil_reserves": 25_000_000,
        "oil_production": 1_000_000,
        "grain": 40,
        "electricity": 150,
        "active_personnel": 185_000,
        "reserve_personnel": 900_000,
    },
    "israel": {
        "population": 10_000_000,
        "treasury": 38_000_000,
        "tax_income": 7_000_000,
        "daily_income": 14_000_000,
        "gold": 200,
        "gold_daily": 40,
        "oil_reserves": 12_000_000,
        "oil_production": 1_000,
        "grain": 100,
        "electricity": 120,
        "active_personnel": 170_000,
        "reserve_personnel": 450_000,
    },
    "france": {
        "population": 68_000_000,
        "treasury": 60_000_000,
        "tax_income": 10_000_000,
        "daily_income": 18_000_000,
        "gold": 350,
        "gold_daily": 50,
        "oil_reserves": 20_000_000,
        "oil_production": 500_000,
        "grain": 45,
        "electricity": 150,
        "active_personnel": 200_000,
        "reserve_personnel": 700_000,
    },
    "japan": {
        "population": 124_000_000,
        "treasury": 70_000_000,
        "tax_income": 12_000_000,
        "daily_income": 20_000_000,
        "gold": 400,
        "gold_daily": 60,
        "oil_reserves": 10_000_000,
        "oil_production": 100_000,
        "grain": 30,
        "electricity": 160,
        "active_personnel": 240_000,
        "reserve_personnel": 600_000,
    },
    "turkey": {
        "population": 85_000_000,
        "treasury": 40_000_000,
        "tax_income": 6_000_000,
        "daily_income": 12_000_000,
        "gold": 300,
        "gold_daily": 40,
        "oil_reserves": 30_000_000,
        "oil_production": 500_000,
        "grain": 40,
        "electricity": 130,
        "active_personnel": 355_000,
        "reserve_personnel": 800_000,
    },
    "saudi": {
        "population": 36_000_000,
        "treasury": 65_000_000,
        "tax_income": 8_000_000,
        "daily_income": 22_000_000,
        "gold": 300,
        "gold_daily": 50,
        "oil_reserves": 260_000_000,
        "oil_production": 10_000_000,
        "grain": 20,
        "electricity": 140,
        "active_personnel": 250_000,
        "reserve_personnel": 300_000,
    },
    "india": {
        "population": 1_420_000_000,
        "treasury": 75_000_000,
        "tax_income": 12_000_000,
        "daily_income": 20_000_000,
        "gold": 500,
        "gold_daily": 60,
        "oil_reserves": 50_000_000,
        "oil_production": 800_000,
        "grain": 55,
        "electricity": 140,
        "active_personnel": 1_450_000,
        "reserve_personnel": 1_150_000,
    },
    "qatar": {
        "population": 3_000_000,
        "treasury": 35_000_000,
        "tax_income": 4_000_000,
        "daily_income": 12_000_000,
        "gold": 200,
        "gold_daily": 30,
        "oil_reserves": 25_000_000,
        "oil_production": 1_500_000,
        "grain": 10,
        "electricity": 120,
        "active_personnel": 20_000,
        "reserve_personnel": 30_000,
    },
    "uae": {
        "population": 10_000_000,
        "treasury": 50_000_000,
        "tax_income": 6_000_000,
        "daily_income": 15_000_000,
        "gold": 250,
        "gold_daily": 40,
        "oil_reserves": 100_000_000,
        "oil_production": 3_200_000,
        "grain": 15,
        "electricity": 135,
        "active_personnel": 65_000,
        "reserve_personnel": 75_000,
    },
    "egypt": {
        "population": 105_000_000,
        "treasury": 30_000_000,
        "tax_income": 5_000_000,
        "daily_income": 10_000_000,
        "gold": 200,
        "gold_daily": 30,
        "oil_reserves": 15_000_000,
        "oil_production": 600_000,
        "grain": 30,
        "electricity": 125,
        "active_personnel": 440_000,
        "reserve_personnel": 480_000,
    },
    "ukraine": {
        "population": 38_000_000,
        "treasury": 25_000_000,
        "tax_income": 4_000_000,
        "daily_income": 8_000_000,
        "gold": 150,
        "gold_daily": 25,
        "oil_reserves": 10_000_000,
        "oil_production": 100_000,
        "grain": 50,
        "electricity": 110,
        "active_personnel": 800_000,
        "reserve_personnel": 900_000,
    },
    "brazil": {
        "population": 215_000_000,
        "treasury": 40_000_000,
        "tax_income": 7_000_000,
        "daily_income": 12_000_000,
        "gold": 250,
        "gold_daily": 35,
        "oil_reserves": 150_000_000,
        "oil_production": 3_000_000,
        "grain": 60,
        "electricity": 140,
        "active_personnel": 360_000,
        "reserve_personnel": 1_300_000,
    }
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

# ===== کاتالوگ دارایی‌های اختصاصی تمام ۱۷ کشور =====
COUNTRY_EQUIPMENT_CATALOG = {
    # ۱. ایران
    "iran": [
        {"key": "shahed136",      "name": "شاهد-۱۳۶",             "category": "UAV",          "price": 100_000,    "initial": 2500, "maint": 500,  "producible": True},
        {"key": "shahed129",      "name": "شاهد-۱۲۹",             "category": "UAV",          "price": 800_000,    "initial": 200,  "maint": 3_000,"producible": True},
        {"key": "mohajer6",       "name": "مهاجر-۶",              "category": "UAV",          "price": 500_000,    "initial": 300,  "maint": 2_000,"producible": True},
        {"key": "karrar_tank",    "name": "تانک کرار",            "category": "Ground Forces","price": 2_500_000,  "initial": 100,  "maint": 6_000,"producible": True},
        {"key": "zulfiqar_tank",  "name": "تانک ذوالفقار",        "category": "Ground Forces","price": 2_000_000,  "initial": 200,  "maint": 5_000,"producible": True},
        {"key": "fateh110",       "name": "فاتح-۱۱۰",             "category": "Missiles",     "price": 1_000_000,  "initial": 500,  "maint": 1_500,"producible": True},
        {"key": "kheybar_shekan", "name": "خیبرشکن",             "category": "Missiles",     "price": 3_000_000,  "initial": 100,  "maint": 5_000,"producible": True},
        {"key": "khorramshahr",   "name": "خرمشهر-۴",             "category": "Missiles",     "price": 5_000_000,  "initial": 100,  "maint": 8_000,"producible": True},
        {"key": "fattah1",        "name": "فتاح-۱ هایپرسونیک",    "category": "Missiles",     "price": 5_000_000,  "initial": 40,   "maint": 8_000,"producible": True},
        {"key": "fattah2",        "name": "فتاح-۲ هایپرسونیک",    "category": "Missiles",     "price": 7_000_000,  "initial": 30,   "maint": 10_000,"producible": True},
        {"key": "soumar_cruise",  "name": "کروز سومار",           "category": "Missiles",     "price": 1_500_000,  "initial": 100,  "maint": 2_500,"producible": True},
        {"key": "paveh_c",        "name": "کروز پاوه",            "category": "Missiles",     "price": 2_000_000,  "initial": 50,   "maint": 3_500,"producible": True},
        {"key": "bavar373",       "name": "پدافند باور-۳۷۳",      "category": "Air Defense",  "price": 10_000_000, "initial": 10,   "maint": 30_000,"producible": True},
        {"key": "khordad_3",      "name": "پدافند سوم خرداد",     "category": "Air Defense",  "price": 5_000_000,  "initial": 20,   "maint": 15_000,"producible": True},
        {"key": "moudge_frigate", "name": "ناوچه کلاس موج",       "category": "Navy",         "price": 15_000_000, "initial": 4,    "maint": 50_000,"producible": True},
        {"key": "fateh_sub",      "name": "زیردریایی فاتح",       "category": "Navy",         "price": 15_000_000, "initial": 2,    "maint": 50_000,"producible": True},
        {"key": "ghadir_sub",     "name": "زیردریایی غدیر",       "category": "Navy",         "price": 3_000_000,  "initial": 20,   "maint": 10_000,"producible": True},
        # وارداتی (غیرقابل ساخت مجدد در فروشگاه)
        {"key": "s300_iran",      "name": "S-300PMU-2 (وارداتی)", "category": "Air Defense",  "price": 12_000_000, "initial": 10,   "maint": 35_000,"producible": False},
        {"key": "su35_iran",      "name": "Su-35 (وارداتی)",      "category": "Aircraft",     "price": 15_000_000, "initial": 24,   "maint": 45_000,"producible": False},
        {"key": "f14_tomcat",     "name": "F-14 Tomcat (قدیمی)",  "category": "Aircraft",     "price": 15_000_000, "initial": 40,   "maint": 40_000,"producible": False},
        {"key": "mig29",          "name": "MiG-29 (وارداتی)",     "category": "Aircraft",     "price": 10_000_000, "initial": 35,   "maint": 30_000,"producible": False},
    ],

    # ۲. آمریکا
    "usa": [
        {"key": "f35a",           "name": "F-35A Lightning II",    "category": "Aircraft",     "price": 15_000_000, "initial": 400,  "maint": 50_000,"producible": True},
        {"key": "f22",            "name": "F-22 Raptor",          "category": "Aircraft",     "price": 25_000_000, "initial": 180,  "maint": 80_000,"producible": True},
        {"key": "f15e",           "name": "F-15E Strike Eagle",   "category": "Aircraft",     "price": 12_000_000, "initial": 220,  "maint": 35_000,"producible": True},
        {"key": "b2",             "name": "B-2 Spirit Bomber",    "category": "Aircraft",     "price": 50_000_000, "initial": 20,   "maint": 150_000,"producible": True},
        {"key": "mq9",            "name": "MQ-9 Reaper UAV",      "category": "UAV",          "price": 3_000_000,  "initial": 300,  "maint": 10_000,"producible": True},
        {"key": "m1a2_abrams",    "name": "M1A2 Abrams Tank",     "category": "Ground Forces","price": 3_000_000,  "initial": 2500, "maint": 8_000,"producible": True},
        {"key": "m2_bradley",     "name": "M2 Bradley IFV",       "category": "Ground Forces","price": 1_200_000,  "initial": 2500, "maint": 3_000,"producible": True},
        {"key": "himars",         "name": "HIMARS Rocket",        "category": "Artillery",    "price": 3_000_000,  "initial": 500,  "maint": 8_000,"producible": True},
        {"key": "ford_class",     "name": "Ford Class Carrier",   "category": "Navy",         "price": 100_000_000,"initial": 3,    "maint": 500_000,"producible": True},
        {"key": "burke_class",    "name": "Arleigh Burke Destroyer","category": "Navy",       "price": 20_000_000, "initial": 70,   "maint": 100_000,"producible": True},
        {"key": "virginia_class", "name": "Virginia Class Sub",   "category": "Navy",         "price": 35_000_000, "initial": 25,   "maint": 150_000,"producible": True},
        {"key": "tomahawk",       "name": "Tomahawk Cruise Missile","category": "Missiles",   "price": 2_000_000,  "initial": 2000, "maint": 2_000,"producible": True},
        {"key": "patriot_pac3",   "name": "Patriot PAC-3",        "category": "Air Defense",  "price": 10_000_000, "initial": 60,   "maint": 30_000,"producible": True},
        {"key": "thaad",          "name": "THAAD Battery",        "category": "Air Defense",  "price": 40_000_000, "initial": 10,   "maint": 100_000,"producible": True},
    ],

    # ۳. روسیه
    "russia": [
        {"key": "su57",           "name": "Su-57 Felon",          "category": "Aircraft",     "price": 20_000_000, "initial": 24,   "maint": 70_000,"producible": True},
        {"key": "su35",           "name": "Su-35S Flanker-E",     "category": "Aircraft",     "price": 12_000_000, "initial": 100,  "maint": 40_000,"producible": True},
        {"key": "tu160",          "name": "Tu-160 Bomber",        "category": "Aircraft",     "price": 40_000_000, "initial": 16,   "maint": 120_000,"producible": True},
        {"key": "ka52_heli",      "name": "Ka-52 Alligator",      "category": "Aircraft",     "price": 6_000_000,  "initial": 150,  "maint": 15_000,"producible": True},
        {"key": "geran2_drone",   "name": "Geran-2 Drone",        "category": "UAV",          "price": 100_000,    "initial": 500,  "maint": 500,  "producible": True},
        {"key": "t90m",           "name": "T-90M Proryv Tank",    "category": "Ground Forces","price": 2_500_000,  "initial": 800,  "maint": 6_000,"producible": True},
        {"key": "bmp3_ifv",       "name": "BMP-3 IFV",            "category": "Ground Forces","price": 1_200_000,  "initial": 2000, "maint": 3_000,"producible": True},
        {"key": "msta_s",          "name": "2S19 Msta-S Howitzer", "category": "Artillery",    "price": 1_800_000,  "initial": 800,  "maint": 4_000,"producible": True},
        {"key": "iskander_system","name": "Iskander-M System",    "category": "Artillery",    "price": 3_000_000,  "initial": 150,  "maint": 8_000,"producible": True},
        {"key": "borei",          "name": "Borei Submarine",      "category": "Navy",         "price": 40_000_000, "initial": 6,    "maint": 200_000,"producible": True},
        {"key": "kalibr",         "name": "Kalibr Cruise Missile","category": "Missiles",     "price": 1_500_000,  "initial": 2000, "maint": 1_500,"producible": True},
        {"key": "kinzhal_hypersonic","name":"Kinzhal Hypersonic", "category": "Missiles",     "price": 5_000_000,  "initial": 100,  "maint": 10_000,"producible": True},
        {"key": "s400",           "name": "S-400 Triumf System",  "category": "Air Defense",  "price": 15_000_000, "initial": 50,   "maint": 40_000,"producible": True},
        {"key": "pantsir",        "name": "Pantsir-S1 System",    "category": "Air Defense",  "price": 5_000_000,  "initial": 100,  "maint": 15_000,"producible": True},
    ],

    # ۴. چین
    "china": [
        {"key": "j20",             "name": "J-20 Stealth Fighter", "category": "Aircraft",     "price": 25_000_000, "initial": 250,  "maint": 70_000,"producible": True},
        {"key": "j16",             "name": "J-16 Multirole",       "category": "Aircraft",     "price": 15_000_000, "initial": 350,  "maint": 40_000,"producible": True},
        {"key": "h6k",             "name": "H-6K Bomber",          "category": "Aircraft",     "price": 30_000_000, "initial": 120,  "maint": 80_000,"producible": True},
        {"key": "gj11",            "name": "GJ-11 Stealth UAV",    "category": "UAV",          "price": 5_000_000,  "initial": 30,   "maint": 12_000,"producible": True},
        {"key": "type_99a",        "name": "Type 99A Tank",        "category": "Ground Forces","price": 3_500_000,  "initial": 1200, "maint": 8_000,"producible": True},
        {"key": "plz_05",          "name": "PLZ-05 Howitzer",      "category": "Artillery",    "price": 1_800_000,  "initial": 400,  "maint": 4_000,"producible": True},
        {"key": "fujian_carrier",  "name": "Fujian Class Carrier", "category": "Navy",         "price": 100_000_000,"initial": 1,    "maint": 500_000,"producible": True},
        {"key": "type_055",        "name": "Type 055 Destroyer",   "category": "Navy",         "price": 30_000_000, "initial": 8,    "maint": 120_000,"producible": True},
        {"key": "df41",            "name": "DF-41 ICBM",           "category": "Missiles",     "price": 20_000_000, "initial": 40,   "maint": 50_000,"producible": True},
        {"key": "df17",            "name": "DF-17 Hypersonic",     "category": "Missiles",     "price": 10_000_000, "initial": 50,   "maint": 20_000,"producible": True},
        {"key": "hq9_hq9b",        "name": "HQ-9B System",         "category": "Air Defense",  "price": 12_000_000, "initial": 40,   "maint": 35_000,"producible": True},
    ],

    # ۵. آلمان
    "germany": [
        {"key": "eurofighter",     "name": "Eurofighter Typhoon",  "category": "Aircraft",     "price": 18_000_000, "initial": 138,  "maint": 50_000,"producible": True},
        {"key": "tiger_heli",     "name": "Eurocopter Tiger",     "category": "Aircraft",     "price": 8_000_000,  "initial": 50,   "maint": 20_000,"producible": True},
        {"key": "leopard_2a7",    "name": "Leopard 2A7 Tank",     "category": "Ground Forces","price": 4_500_000,  "initial": 100,  "maint": 10_000,"producible": True},
        {"key": "puma_ifv",       "name": "Puma IFV",             "category": "Ground Forces","price": 2_000_000,  "initial": 300,  "maint": 5_000,"producible": True},
        {"key": "pzh_2000",       "name": "PzH 2000 Howitzer",    "category": "Artillery",    "price": 2_500_000,  "initial": 100,  "maint": 6_000,"producible": True},
        {"key": "type_212a_sub",  "name": "Type 212A Submarine",  "category": "Navy",         "price": 30_000_000, "initial": 6,    "maint": 120_000,"producible": True},
        {"key": "taurus_kepd",    "name": "Taurus KEPD 350",      "category": "Missiles",     "price": 2_000_000,  "initial": 150,  "maint": 3_000,"producible": True},
        {"key": "iris_t_slm",     "name": "IRIS-T SLM System",    "category": "Air Defense",  "price": 8_000_000,  "initial": 6,    "maint": 25_000,"producible": True},
        # وارداتی
        {"key": "f35a_germany",   "name": "F-35A (وارداتی)",      "category": "Aircraft",     "price": 15_000_000, "initial": 35,   "maint": 50_000,"producible": False},
        {"key": "patriot_germany","name": "Patriot PAC-3 (وارداتی)","category":"Air Defense", "price": 10_000_000, "initial": 12,   "maint": 30_000,"producible": False},
    ],

    # ۶. فرانسه
    "france": [
        {"key": "rafale",         "name": "Dassault Rafale",      "category": "Aircraft",     "price": 18_000_000, "initial": 180,  "maint": 50_000,"producible": True},
        {"key": "leclerc_tank",  "name": "Leclerc Tank",         "category": "Ground Forces","price": 4_000_000,  "initial": 220,  "maint": 9_000,"producible": True},
        {"key": "caesar_art",    "name": "CAESAR Howitzer",      "category": "Artillery",    "price": 2_000_000,  "initial": 80,   "maint": 5_000,"producible": True},
        {"key": "charles_de_gaulle","name":"Charles de Gaulle Carrier","category": "Navy",   "price": 95_000_000, "initial": 1,    "maint": 500_000,"producible": True},
        {"key": "fremm_frigate", "name": "FREMM Frigate",         "category": "Navy",         "price": 25_000_000, "initial": 8,    "maint": 90_000,"producible": True},
        {"key": "scalp_eg",      "name": "SCALP EG Cruise",      "category": "Missiles",     "price": 2_000_000,  "initial": 300,  "maint": 3_000,"producible": True},
        {"key": "samp_t",        "name": "SAMP/T Air Defense",   "category": "Air Defense",  "price": 12_000_000, "initial": 10,   "maint": 35_000,"producible": True},
        # وارداتی
        {"key": "reaper_fr",     "name": "MQ-9 Reaper (وارداتی)","category": "UAV",          "price": 3_000_000,  "initial": 12,   "maint": 10_000,"producible": False},
    ],

    # ۷. انگلیس
    "uk": [
        {"key": "typhoon_uk",      "name": "Eurofighter Typhoon",  "category": "Aircraft",     "price": 18_000_000, "initial": 140,  "maint": 50_000,"producible": True},
        {"key": "challenger2",     "name": "Challenger 2 Tank",    "category": "Ground Forces","price": 3_500_000,  "initial": 220,  "maint": 8_000,"producible": True},
        {"key": "challenger3",     "name": "Challenger 3 Tank",    "category": "Ground Forces","price": 5_000_000,  "initial": 14,   "maint": 12_000,"producible": True},
        {"key": "as90_howitzer",   "name": "AS90 Howitzer",        "category": "Artillery",    "price": 2_000_000,  "initial": 60,   "maint": 5_000,"producible": True},
        {"key": "queen_elizabeth_carrier","name":"Queen Elizabeth Carrier","category":"Navy", "price": 90_000_000, "initial": 2,    "maint": 450_000,"producible": True},
        {"key": "type_45_destroyer","name":"Type 45 Destroyer",    "category": "Navy",         "price": 25_000_000, "initial": 6,    "maint": 100_000,"producible": True},
        {"key": "storm_shadow",    "name": "Storm Shadow Cruise",  "category": "Missiles",     "price": 2_000_000,  "initial": 300,  "maint": 3_000,"producible": True},
        {"key": "sky_sabre",       "name": "Sky Sabre Air Defense","category": "Air Defense",  "price": 8_000_000,  "initial": 12,   "maint": 25_000,"producible": True},
        # وارداتی
        {"key": "f35b_uk",         "name": "F-35B (وارداتی)",      "category": "Aircraft",     "price": 16_000_000, "initial": 70,   "maint": 55_000,"producible": False},
        {"key": "ah64e_uk",        "name": "AH-64E Apache (وارداتی)","category":"Aircraft",    "price": 5_000_000,  "initial": 50,   "maint": 15_000,"producible": False},
    ],

    # ۸. اسرائیل
    "israel": [
        {"key": "merkava_mk4",    "name": "مرکاوا Mk4",           "category": "Ground Forces","price": 3_500_000,  "initial": 700,  "maint": 8_000, "producible": True},
        {"key": "namer_apc",      "name": "نفربر نمر (Namer)",    "category": "Ground Forces","price": 2_000_000,  "initial": 300,  "maint": 4_000, "producible": True},
        {"key": "hermes_450",     "name": "پهپاد هرمس ۴۵۰",       "category": "UAV",          "price": 1_000_000,  "initial": 50,   "maint": 3_000, "producible": True},
        {"key": "iron_dome",      "name": "سامانه گنبد آهنین",    "category": "Air Defense",  "price": 10_000_000, "initial": 15,   "maint": 30_000,"producible": True},
        {"key": "davids_sling",   "name": "سامانه فلاخن داوود",   "category": "Air Defense",  "price": 20_000_000, "initial": 5,    "maint": 50_000,"producible": True},
        {"key": "arrow_3",        "name": "سامانه پیکان ۳ (Arrow)","category":"Air Defense",  "price": 30_000_000, "initial": 6,    "maint": 80_000,"producible": True},
        {"key": "jericho_3",      "name": "موشک بالستیک جریکو ۳", "category": "Missiles",     "price": 15_000_000, "initial": 30,   "maint": 40_000,"producible": True},
        {"key": "spike_missile",  "name": "موشک ضدتانک اسپایک",   "category": "Missiles",     "price": 200_000,    "initial": 1000, "maint": 300,   "producible": True},
        # وارداتی
        {"key": "f35i_adir",      "name": "F-35I Adir (وارداتی)", "category": "Aircraft",     "price": 18_000_000, "initial": 40,   "maint": 60_000,"producible": False},
        {"key": "f15_israel",     "name": "F-15 Eagle (وارداتی)", "category": "Aircraft",     "price": 12_000_000, "initial": 80,   "maint": 35_000,"producible": False},
        {"key": "f16_israel",     "name": "F-16 Falcon (وارداتی)","category": "Aircraft",     "price": 8_000_000,  "initial": 170,  "maint": 20_000,"producible": False},
        {"key": "patriot_israel", "name": "پاتریوت (وارداتی)",    "category": "Air Defense",  "price": 8_000_000,  "initial": 8,    "maint": 20_000,"producible": False},
        {"key": "dolphin_sub",    "name": "زیردریایی دولفین (وارداتی)","category":"Navy",    "price": 40_000_000, "initial": 6,    "maint": 150_000,"producible": False},
    ],

    # ۹. ترکیه
    "turkey": [
        {"key": "tb2_drone",     "name": "پهپاد بایراکتار TB2",  "category": "UAV",          "price": 500_000,    "initial": 200,  "maint": 1_000, "producible": True},
        {"key": "akinci_drone",  "name": "پهپاد آکینجی (Akıncı)","category": "UAV",          "price": 2_000_000,  "initial": 40,   "maint": 5_000, "producible": True},
        {"key": "kizilelma",     "name": "پهپاد استلت قزل‌الما", "category": "UAV",          "price": 4_000_000,  "initial": 10,   "maint": 10_000,"producible": True},
        {"key": "altay_tank",    "name": "تانک آلتای (Altay)",   "category": "Ground Forces","price": 4_000_000,  "initial": 10,   "maint": 9_000, "producible": True},
        {"key": "firtina_art",   "name": "توپخانه فورتونا T-155","category": "Artillery",    "price": 1_800_000,  "initial": 350,  "maint": 4_000, "producible": True},
        {"key": "anadolu_carrier","name":"ناو تهاجمی TCG Anadolu","category":"Navy",         "price": 60_000_000, "initial": 1,    "maint": 300_000,"producible": True},
        {"key": "som_missile",   "name": "موشک کروز SOM",        "category": "Missiles",     "price": 1_200_000,  "initial": 200,  "maint": 2_000, "producible": True},
        {"key": "tayfun_m",      "name": "موشک بالستیک تایفون",  "category": "Missiles",     "price": 3_000_000,  "initial": 50,   "maint": 5_000, "producible": True},
        {"key": "hisar_o",       "name": "پدافند حصار (Hisar-O+)","category":"Air Defense",  "price": 5_000_000,  "initial": 15,   "maint": 12_000,"producible": True},
        # وارداتی
        {"key": "f16_turkey",    "name": "F-16 Block 50+ (وارداتی)","category":"Aircraft",   "price": 8_000_000,  "initial": 240,  "maint": 20_000,"producible": False},
        {"key": "s400_turkey",   "name": "S-400 (وارداتی)",      "category": "Air Defense",  "price": 15_000_000, "initial": 4,    "maint": 40_000,"producible": False},
    ],

    # ۱۰. عربستان
    "saudi": [
        {"key": "al_masmak",      "name": "خودرو زرهی المسمک",     "category": "Ground Forces","price": 400_000,    "initial": 500,  "maint": 1_000, "producible": True},
        {"key": "saudi_drones",   "name": "پهپادهای مونتاژ بومی", "category": "UAV",          "price": 500_000,    "initial": 100,  "maint": 1_200, "producible": True},
        # وارداتی (سهم عمده ارتش)
        {"key": "f15sa",          "name": "F-15SA (وارداتی)",     "category": "Aircraft",     "price": 15_000_000, "initial": 230,  "maint": 40_000,"producible": False},
        {"key": "typhoon_saudi",  "name": "Eurofighter (وارداتی)","category": "Aircraft",     "price": 18_000_000, "initial": 72,   "maint": 50_000,"producible": False},
        {"key": "m1a2s_abrams",   "name": "M1A2S Abrams (وارداتی)","category":"Ground Forces","price": 3_000_000,  "initial": 450,  "maint": 8_000, "producible": False},
        {"key": "patriot_saudi",  "name": "پاتریوت PAC-3 (وارداتی)","category":"Air Defense", "price": 10_000_000, "initial": 24,   "maint": 30_000,"producible": False},
        {"key": "thaad_saudi",    "name": "سامانه ثاد THAAD (وارداتی)","category":"Air Defense","price": 40_000_000,"initial": 4,    "maint": 100_000,"producible": False},
    ],

    # ۱۱. ژاپن
    "japan": [
        {"key": "f2_japan",      "name": "جنگنده Mitsubishi F-2","category": "Aircraft",     "price": 14_000_000, "initial": 90,   "maint": 38_000,"producible": True},
        {"key": "type10_tank",   "name": "تانک تایپ ۱۰",         "category": "Ground Forces","price": 4_500_000,  "initial": 100,  "maint": 10_000,"producible": True},
        {"key": "izumo_carrier", "name": "ناو ایزومو (Izumo)",    "category": "Navy",         "price": 70_000_000, "initial": 2,    "maint": 350_000,"producible": True},
        {"key": "soryu_sub",     "name": "زیردریایی کلاس سوریا", "category": "Navy",         "price": 25_000_000, "initial": 12,   "maint": 100_000,"producible": True},
        {"key": "type12_antiship","name":"موشک ضدکشتی تایپ ۱۲",  "category": "Missiles",     "price": 1_500_000,  "initial": 300,  "maint": 2_500, "producible": True},
        # وارداتی
        {"key": "f35_japan",     "name": "F-35A/B (وارداتی)",    "category": "Aircraft",     "price": 16_000_000, "initial": 40,   "maint": 50_000,"producible": False},
        {"key": "f15j",          "name": "F-15J Eagle (تحت لیسانس)","category":"Aircraft",   "price": 12_000_000, "initial": 200,  "maint": 35_000,"producible": False},
        {"key": "pac3_japan",    "name": "پاتریوت PAC-3 (وارداتی)","category":"Air Defense", "price": 10_000_000, "initial": 24,   "maint": 30_000,"producible": False},
    ],

    # ۱۲. هند
    "india": [
        {"key": "tejas_fighter",  "name": "جنگنده بومی تجاس (Tejas)","category":"Aircraft",  "price": 8_000_000,  "initial": 40,   "maint": 20_000,"producible": True},
        {"key": "arjun_tank",     "name": "تانک بومی آرجون",      "category": "Ground Forces","price": 3_000_000,  "initial": 120,  "maint": 7_000, "producible": True},
        {"key": "ins_vikrant",    "name": "ناو هواپیمابر ویکرانت", "category": "Navy",         "price": 80_000_000, "initial": 1,    "maint": 400_000,"producible": True},
        {"key": "brahmos",        "name": "موشک هایپرسونیک براموس","category": "Missiles",   "price": 2_500_000,  "initial": 500,  "maint": 4_000, "producible": True},
        {"key": "agni_v",         "name": "موشک قاره‌پیمای آگنی ۵","category": "Missiles",    "price": 15_000_000, "initial": 30,   "maint": 35_000,"producible": True},
        {"key": "akash_def",      "name": "پدافند بومی آکاش",     "category": "Air Defense",  "price": 5_000_000,  "initial": 30,   "maint": 15_000,"producible": True},
        # وارداتی
        {"key": "su30mki",        "name": "Su-30MKI (وارداتی)",   "category": "Aircraft",     "price": 14_000_000, "initial": 260,  "maint": 40_000,"producible": False},
        {"key": "rafale_india",   "name": "رافال (وارداتی)",      "category": "Aircraft",     "price": 18_000_000, "initial": 36,   "maint": 50_000,"producible": False},
        {"key": "s400_india",     "name": "S-400 (وارداتی)",      "category": "Air Defense",  "price": 15_000_000, "initial": 3,    "maint": 40_000,"producible": False},
    ],

    # ۱۳. قطر
    "qatar": [
        {"key": "al_zubarah",     "name": "ناوچه گشتی الزباره",   "category": "Navy",         "price": 18_000_000, "initial": 4,    "maint": 60_000,"producible": True},
        # وارداتی
        {"key": "rafale_qatar",   "name": "رافال (وارداتی)",      "category": "Aircraft",     "price": 18_000_000, "initial": 36,   "maint": 50_000,"producible": False},
        {"key": "f15qa",          "name": "F-15QA Ababil (وارداتی)","category":"Aircraft",    "price": 15_000_000, "initial": 36,   "maint": 40_000,"producible": False},
        {"key": "typhoon_qatar",  "name": "یوروفایتر (وارداتی)",  "category": "Aircraft",     "price": 18_000_000, "initial": 24,   "maint": 50_000,"producible": False},
        {"key": "leopard_qatar",  "name": "تانک لئوپارد (وارداتی)","category":"Ground Forces","price": 4_500_000,  "initial": 62,   "maint": 10_000,"producible": False},
        {"key": "patriot_qatar",  "name": "پاتریوت (وارداتی)",    "category": "Air Defense",  "price": 10_000_000, "initial": 4,    "maint": 30_000,"producible": False},
    ],

    # ۱۴. امارات
    "uae": [
        {"key": "nimr_ajban",     "name": "خودرو زرهی بومی نمر",  "category": "Ground Forces","price": 300_000,    "initial": 1000, "maint": 800,   "producible": True},
        {"key": "jobaria_mlrs",   "name": "راکت‌انداز سنگین جوبریا","category": "Artillery",  "price": 5_000_000,  "initial": 6,    "maint": 15_000,"producible": True},
        {"key": "yabhon_uav",      "name": "پهپاد بومی یبحون",     "category": "UAV",          "price": 1_000_000,  "initial": 10,   "maint": 3_000, "producible": True},
        # وارداتی
        {"key": "f16_block60",    "name": "F-16 Block 60 (وارداتی)","category":"Aircraft",    "price": 10_000_000, "initial": 78,   "maint": 25_000,"producible": False},
        {"key": "mirage_2000_9",  "name": "میراژ ۲۰۰ labor (وارداتی)","category":"Aircraft",  "price": 10_000_000, "initial": 55,   "maint": 25_000,"producible": False},
        {"key": "leclerc_uae",    "name": "تانک لوکلرک (وارداتی)","category": "Ground Forces","price": 4_000_000,  "initial": 380,  "maint": 9_000, "producible": False},
        {"key": "thaad_uae",      "name": "سامانه ثاد (وارداتی)", "category": "Air Defense",  "price": 40_000_000, "initial": 2,    "maint": 100_000,"producible": False},
    ],

    # ۱۵. مصر
    "egypt": [
        {"key": "m1a1_egypt",     "name": "تانک M1A1 (مونتاژ بومی)","category":"Ground Forces","price": 2_000_000, "initial": 1100, "maint": 5_000,"producible": True},
        {"key": "sakr_mlrs",      "name": "راکت‌انداز بومی صقر",  "category": "Artillery",    "price": 800_000,    "initial": 200,  "maint": 2_000, "producible": True},
        # وارداتی
        {"key": "rafale_egypt",   "name": "رافال (وارداتی)",      "category": "Aircraft",     "price": 18_000_000, "initial": 24,   "maint": 50_000,"producible": False},
        {"key": "f16_egypt",      "name": "F-16 (وارداتی)",       "category": "Aircraft",     "price": 8_000_000,  "initial": 200,  "maint": 20_000,"producible": False},
        {"key": "mistral_egypt",  "name": "ناو می‌سترال (وارداتی)","category":"Navy",         "price": 50_000_000, "initial": 2,    "maint": 250_000,"producible": False},
    ],

    # ۱۶. اوکراین
    "ukraine": [
        {"key": "neptune_missile","name": "موشک ضدکشتی نپتون",    "category": "Missiles",     "price": 1_000_000,  "initial": 50,   "maint": 2_000, "producible": True},
        {"key": "fpv_kamikaze",   "name": "پهپادهای انتحاری FPV", "category": "UAV",          "price": 50_000,     "initial": 1000, "maint": 100,   "producible": True},
        {"key": "sea_baby_usv",   "name": "شناور بی‌سرنشین سی‌بی‌بی","category":"Navy",       "price": 100_000,    "initial": 100,  "maint": 300,   "producible": True},
        {"key": "btr4_ukraine",   "name": "نفربر بومی BTR-4",     "category": "Ground Forces","price": 800_000,    "initial": 200,  "maint": 2_000, "producible": True},
        # وارداتی / کمکی
        {"key": "su27_ukraine",   "name": "Su-27 (قدیمی)",        "category": "Aircraft",     "price": 8_000_000,  "initial": 30,   "maint": 22_000,"producible": False},
        {"key": "leopard2_ukraine","name":"لئوپارد ۲ (کمکی)",     "category": "Ground Forces","price": 3_000_000,  "initial": 60,   "maint": 7_000, "producible": False},
        {"key": "himars_ukraine", "name": "هیمارس HIMARS (کمکی)","category": "Artillery",    "price": 3_000_000,  "initial": 38,   "maint": 8_000, "producible": False},
        {"key": "patriot_ukraine","name":"پاتریوت PAC-3 (کمکی)",  "category": "Air Defense",  "price": 10_000_000, "initial": 3,    "maint": 30_000,"producible": False},
    ],

    # ۱۷. برزیل
    "brazil": [
        {"key": "super_tucano",   "name": "جنگنده سبک سوپر توکانو","category":"Aircraft",     "price": 2_000_000,  "initial": 60,   "maint": 5_000, "producible": True},
        {"key": "kc390",          "name": "ترابری بومی Embraer C-390","category":"Aircraft", "price": 18_000_000, "initial": 6,    "maint": 35_000,"producible": True},
        {"key": "guarani_apc",    "name": "نفربر زرهی گوارانی",   "category": "Ground Forces","price": 600_000,    "initial": 600,  "maint": 1_500, "producible": True},
        {"key": "astros2_mlrs",   "name": "راکت‌انداز آستروس ۲",  "category": "Artillery",    "price": 2_500_000,  "initial": 60,   "maint": 6_000, "producible": True},
        {"key": "mansup_missile", "name": "موشک ضدکشتی مانسوپ",   "category": "Missiles",     "price": 1_000_000,  "initial": 50,   "maint": 2_000, "producible": True},
        # وارداتی
        {"key": "gripen_e",       "name": "Gripen E (تحت لیسانس)","category": "Aircraft",    "price": 15_000_000, "initial": 15,   "maint": 40_000,"producible": False},
        {"key": "atlantico_carrier","name":"ناو آتلانتیکو (وارداتی)","category":"Navy",       "price": 50_000_000, "initial": 1,    "maint": 250_000,"producible": False},
    ],
}

# کاتالوگ عمومی برای سایر کشورها
DEFAULT_COUNTRY_EQUIPMENT = [
    {"key": "gen_fighter",   "name": "جنگنده پیشرفته نسل ۴.۵", "category": "Aircraft",     "price": 10_000_000, "initial": 150, "maint": 25_000, "producible": True},
    {"key": "gen_bomber",    "name": "بمب‌افکن استراتژیک",     "category": "Aircraft",     "price": 25_000_000, "initial": 20,  "maint": 60_000, "producible": True},
    {"key": "gen_missile",   "name": "موشک کروز استراتژیک",   "category": "Missiles",     "price": 2_000_000,  "initial": 500, "maint": 2_000,  "producible": True},
    {"key": "gen_airdef",    "name": "سامانه پدافند موشکی",  "category": "Air Defense",  "price": 10_000_000, "initial": 20,  "maint": 25_000, "producible": True},
    {"key": "gen_uav",       "name": "پهپاد شناسایی-رزمی",  "category": "UAV",          "price": 1_000_000,  "initial": 200, "maint": 3_000,  "producible": True},
    {"key": "gen_frigate",   "name": "ناو محافظ سنگین",       "category": "Navy",         "price": 20_000_000, "initial": 10,  "maint": 80_000, "producible": True},
    {"key": "gen_tank",      "name": "تانک اصلی میدان نبرد",  "category": "Ground Forces","price": 2_000_000,  "initial": 1000,"maint": 5_000,  "producible": True},
    {"key": "gen_artillery", "name": "توپخانه خودکششی",       "category": "Artillery",    "price": 1_500_000,  "initial": 300, "maint": 4_000,  "producible": True},
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
