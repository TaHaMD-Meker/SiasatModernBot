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
    "israel":  {"name": "اسرائیل",  "flag": "🇮🇱"},
}

# ===== مقادیر اولیه عمومی کشورها =====
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

# ===== مقادیر اختصاصی برای کشورهای خاص =====
COUNTRY_STARTING_OVERRIDES = {
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
    "usa": {
        "population": 340_000_000,
        "treasury": 80_000_000,
        "tax_income": 12_000_000,
        "daily_income": 8_000_000,
        "gold": 500,
        "gold_daily": 60,
        "oil_reserves": 250_000_000,
        "oil_production": 5_000_000,
        "grain": 50,
        "electricity": 145,
        "active_personnel": 1_300_000,
        "reserve_personnel": 800_000,
    },
    "israel": {
        "population": 10_000_000,
        "treasury": 18_000_000,
        "tax_income": 7_000_000,
        "daily_income": 4_000_000,
        "gold": 200,
        "gold_daily": 40,
        "oil_reserves": 12_000_000,
        "oil_production": 1_000,
        "grain": 100_000,
        "electricity": 120,
        "active_personnel": 170_000,
        "reserve_personnel": 450_000,
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

# ===== کاتالوگ دارایی‌های اختصاصی کشورها (Country Assets Catalog) =====
COUNTRY_EQUIPMENT_CATALOG = {
    "iran": [
        # نیروی هوایی و بالگردها (Aircraft)
        {"key": "f14_tomcat",     "name": "F-14 Tomcat",          "category": "Aircraft",     "price": 15_000_000, "initial": 40,   "maint": 40_000},
        {"key": "mig29",          "name": "MiG-29",               "category": "Aircraft",     "price": 10_000_000, "initial": 35,   "maint": 30_000},
        {"key": "f4_phantom",     "name": "F-4 Phantom II",       "category": "Aircraft",     "price": 6_000_000,  "initial": 60,   "maint": 20_000},
        {"key": "f5_tiger",       "name": "F-5 Tiger",            "category": "Aircraft",     "price": 4_000_000,  "initial": 60,   "maint": 10_000},
        {"key": "su24",           "name": "Su-24 Fencer",         "category": "Aircraft",     "price": 10_000_000, "initial": 30,   "maint": 30_000},
        {"key": "su35_iran",      "name": "Su-35 Flanker-E",      "category": "Aircraft",     "price": 15_000_000, "initial": 24,   "maint": 45_000},
        {"key": "mirage_f1",      "name": "Mirage F1",            "category": "Aircraft",     "price": 5_000_000,  "initial": 20,   "maint": 15_000},
        {"key": "su22",           "name": "Su-22",                "category": "Aircraft",     "price": 4_000_000,  "initial": 10,   "maint": 10_000},
        {"key": "c130_iran",      "name": "C-130 Hercules",       "category": "Aircraft",     "price": 6_000_000,  "initial": 20,   "maint": 15_000},
        {"key": "il76_iran",      "name": "Il-76 Transporter",    "category": "Aircraft",     "price": 15_000_000, "initial": 10,   "maint": 35_000},
        {"key": "recon_planes",   "name": "Recon & Trainer Aircraft","category": "Aircraft", "price": 2_000_000,  "initial": 30,   "maint": 5_000},
        {"key": "mi8_mi17",       "name": "Mi-8 / Mi-17",         "category": "Aircraft",     "price": 3_000_000,  "initial": 100,  "maint": 8_000},
        {"key": "ah1j_cobra",     "name": "AH-1J Cobra",          "category": "Aircraft",     "price": 4_000_000,  "initial": 30,   "maint": 10_000},
        {"key": "ch47_iran",      "name": "CH-47 Chinook",        "category": "Aircraft",     "price": 6_000_000,  "initial": 20,   "maint": 15_000},
        {"key": "bell_214",       "name": "Bell 214 Helicopter",  "category": "Aircraft",     "price": 2_000_000,  "initial": 30,   "maint": 5_000},
        {"key": "light_helis",    "name": "Light Helicopters",    "category": "Aircraft",     "price": 1_500_000,  "initial": 100,  "maint": 3_000},

        # پهپادها (UAV)
        {"key": "shahed136",      "name": "Shahed-136",           "category": "UAV",          "price": 100_000,    "initial": 2500, "maint": 500},
        {"key": "shahed129",      "name": "Shahed-129",           "category": "UAV",          "price": 800_000,    "initial": 200,  "maint": 3_000},
        {"key": "shahed191",      "name": "Shahed-191",           "category": "UAV",          "price": 1_000_000,  "initial": 100,  "maint": 4_000},
        {"key": "mohajer6",       "name": "Mohajer-6",            "category": "UAV",          "price": 500_000,    "initial": 300,  "maint": 2_000},
        {"key": "ababil_drone",   "name": "Ababil UAV",           "category": "UAV",          "price": 300_000,    "initial": 500,  "maint": 1_000},
        {"key": "kaman22",        "name": "Kaman-22",             "category": "UAV",          "price": 1_500_000,  "initial": 50,   "maint": 5_000},

        # نیروی زمینی (Ground Forces)
        {"key": "t72_tank",       "name": "T-72 Tank",            "category": "Ground Forces","price": 1_500_000,  "initial": 600,  "maint": 4_000},
        {"key": "t62_tank",       "name": "T-62 Tank",            "category": "Ground Forces","price": 800_000,    "initial": 400,  "maint": 2_000},
        {"key": "t55_tank",       "name": "T-55 Tank",            "category": "Ground Forces","price": 500_000,    "initial": 300,  "maint": 1_000},
        {"key": "zulfiqar_tank",  "name": "Zulfiqar Tank",        "category": "Ground Forces","price": 2_000_000,  "initial": 200,  "maint": 5_000},
        {"key": "karrar_tank",    "name": "Karrar Tank",          "category": "Ground Forces","price": 2_500_000,  "initial": 100,  "maint": 6_000},
        {"key": "bmp1_bmp2",      "name": "BMP-1 / BMP-2",        "category": "Ground Forces","price": 600_000,    "initial": 800,  "maint": 1_500},
        {"key": "apc_iran",       "name": "Armored Personnel Carriers","category": "Ground Forces","price": 400_000,"initial": 1500, "maint": 1_000},
        {"key": "tactical_veh",   "name": "Light Tactical Vehicles","category": "Ground Forces","price": 100_000,  "initial": 3000, "maint": 300},

        # توپخانه و راکت‌اندازها (Artillery)
        {"key": "sp_artillery",   "name": "Self-Propelled Artillery","category": "Artillery", "price": 1_000_000,  "initial": 250,  "maint": 3_000},
        {"key": "towed_artillery","name": "Towed Artillery",       "category": "Artillery",    "price": 300_000,    "initial": 1500, "maint": 800},
        {"key": "bm21_grad",      "name": "BM-21 Grad",           "category": "Artillery",    "price": 500_000,    "initial": 300,  "maint": 1_200},
        {"key": "fajr_rocket",    "name": "Fajr Rocket System",   "category": "Artillery",    "price": 800_000,    "initial": 500,  "maint": 2_000},
        {"key": "zelzal_rocket",  "name": "Zelzal Heavy Rocket",  "category": "Artillery",    "price": 1_200_000,  "initial": 200,  "maint": 3_000},

        # توان موشکی (Missiles)
        {"key": "fateh110",       "name": "Fateh-110",            "category": "Missiles",     "price": 1_000_000,  "initial": 500,  "maint": 1_500},
        {"key": "fateh313",       "name": "Fateh-313",            "category": "Missiles",     "price": 1_200_000,  "initial": 300,  "maint": 2_000},
        {"key": "zolfaghar_m",    "name": "Zolfaghar Ballistic",  "category": "Missiles",     "price": 2_000_000,  "initial": 200,  "maint": 3_000},
        {"key": "dezful_m",       "name": "Dezful Ballistic",     "category": "Missiles",     "price": 2_500_000,  "initial": 200,  "maint": 4_000},
        {"key": "qiam_m",         "name": "Qiam Ballistic",       "category": "Missiles",     "price": 2_000_000,  "initial": 200,  "maint": 3_000},
        {"key": "ghadr_m",        "name": "Ghadr-110",            "category": "Missiles",     "price": 3_000_000,  "initial": 150,  "maint": 5_000},
        {"key": "emad_m",         "name": "Emad Ballistic",       "category": "Missiles",     "price": 3_500_000,  "initial": 100,  "maint": 6_000},
        {"key": "haj_qasem",      "name": "Haj Qasem Missile",    "category": "Missiles",     "price": 4_000_000,  "initial": 100,  "maint": 7_000},
        {"key": "kheybar_shekan", "name": "Kheybar Shekan",       "category": "Missiles",     "price": 3_000_000,  "initial": 100,  "maint": 5_000},
        {"key": "khorramshahr",   "name": "Khorramshahr-4",       "category": "Missiles",     "price": 5_000_000,  "initial": 100,  "maint": 8_000},
        {"key": "sejjil",         "name": "Sejjil ICBM",          "category": "Missiles",     "price": 6_000_000,  "initial": 50,   "maint": 10_000},
        {"key": "fattah1",        "name": "Fattah-1 Hypersonic",  "category": "Missiles",     "price": 5_000_000,  "initial": 40,   "maint": 8_000},
        {"key": "fattah2",        "name": "Fattah-2 Hypersonic",  "category": "Missiles",     "price": 7_000_000,  "initial": 30,   "maint": 10_000},
        {"key": "qasem_basir",    "name": "Qasem Basir",          "category": "Missiles",     "price": 4_000_000,  "initial": 30,   "maint": 6_000},
        {"key": "soumar_cruise",  "name": "Soumar Cruise",        "category": "Missiles",     "price": 1_500_000,  "initial": 100,  "maint": 2_500},
        {"key": "hoveyzeh_c",     "name": "Hoveyzeh Cruise",      "category": "Missiles",     "price": 1_800_000,  "initial": 100,  "maint": 3_000},
        {"key": "paveh_c",        "name": "Paveh Cruise",         "category": "Missiles",     "price": 2_000_000,  "initial": 50,   "maint": 3_500},
        {"key": "noor_antiship",  "name": "Noor Anti-Ship",       "category": "Missiles",     "price": 800_000,    "initial": 500,  "maint": 1_200},
        {"key": "qader_antiship", "name": "Qader Anti-Ship",      "category": "Missiles",     "price": 1_200_000,  "initial": 200,  "maint": 2_000},
        {"key": "qadir_antiship", "name": "Qadir Anti-Ship",      "category": "Missiles",     "price": 1_500_000,  "initial": 100,  "maint": 2_500},
        {"key": "khalij_fars",    "name": "Khalij Fars Anti-Ship","category": "Missiles",     "price": 1_500_000,  "initial": 200,  "maint": 2_500},
        {"key": "zolfaghar_nav",  "name": "Naval Zolfaghar",      "category": "Missiles",     "price": 2_000_000,  "initial": 100,  "maint": 3_000},

        # نیروی دریایی (Navy)
        {"key": "moudge_frigate", "name": "Moudge Class Frigate", "category": "Navy",         "price": 15_000_000, "initial": 4,    "maint": 50_000},
        {"key": "alvand_frigate", "name": "Alvand Class Frigate", "category": "Navy",         "price": 10_000_000, "initial": 3,    "maint": 30_000},
        {"key": "fast_attack",    "name": "Fast Attack Missile Boats","category": "Navy",     "price": 200_000,    "initial": 1500, "maint": 500},
        {"key": "missile_corv",   "name": "Missile Vessels",      "category": "Navy",         "price": 1_000_000,  "initial": 200,  "maint": 3_000},
        {"key": "patrol_iran",    "name": "Patrol Boats",         "category": "Navy",         "price": 300_000,    "initial": 300,  "maint": 800},
        {"key": "usv_drones",     "name": "Unmanned Surface Vessels","category": "Navy",      "price": 200_000,    "initial": 150,  "maint": 500},
        {"key": "kilo_sub",       "name": "Kilo Class Submarine", "category": "Navy",         "price": 25_000_000, "initial": 3,    "maint": 90_000},
        {"key": "fateh_sub",      "name": "Fateh Class Submarine","category": "Navy",         "price": 15_000_000, "initial": 2,    "maint": 50_000},
        {"key": "ghadir_sub",     "name": "Ghadir Midget Sub",    "category": "Navy",         "price": 3_000_000,  "initial": 20,   "maint": 10_000},
        {"key": "midget_subs",    "name": "Midget Submarines",    "category": "Navy",         "price": 1_000_000,  "initial": 30,   "maint": 3_000},

        # پدافند هوایی (Air Defense)
        {"key": "s300_iran",      "name": "S-300PMU-2",           "category": "Air Defense",  "price": 12_000_000, "initial": 10,   "maint": 35_000},
        {"key": "bavar373",       "name": "Bavar-373",            "category": "Air Defense",  "price": 10_000_000, "initial": 10,   "maint": 30_000},
        {"key": "khordad_3",      "name": "3rd Khordad",          "category": "Air Defense",  "price": 5_000_000,  "initial": 20,   "maint": 15_000},
        {"key": "khordad_15",     "name": "15th Khordad",         "category": "Air Defense",  "price": 6_000_000,  "initial": 20,   "maint": 18_000},
        {"key": "talash_sys",     "name": "Talash Defense",       "category": "Air Defense",  "price": 5_000_000,  "initial": 20,   "maint": 15_000},
        {"key": "tabas_sys",      "name": "Tabas Defense",        "category": "Air Defense",  "price": 4_000_000,  "initial": 20,   "maint": 12_000},
        {"key": "tor_m1",         "name": "Tor-M1",               "category": "Air Defense",  "price": 6_000_000,  "initial": 30,   "maint": 18_000},
        {"key": "short_range_def","name": "Short Range Air Defense","category": "Air Defense", "price": 1_000_000,  "initial": 300,  "maint": 3_000},
        {"key": "radars_iran",    "name": "Military Radars",      "category": "Air Defense",  "price": 3_000_000,  "initial": 200,  "maint": 10_000},
    ],
    "usa": [
        # نیروی هوایی و پشتیبانی (Aircraft)
        {"key": "f35a",           "name": "F-35A Lightning II",    "category": "Aircraft",     "price": 15_000_000, "initial": 400,  "maint": 50_000},
        {"key": "f35b",           "name": "F-35B Lightning II",    "category": "Aircraft",     "price": 16_000_000, "initial": 100,  "maint": 55_000},
        {"key": "f35c",           "name": "F-35C Lightning II",    "category": "Aircraft",     "price": 17_000_000, "initial": 80,   "maint": 60_000},
        {"key": "f22",            "name": "F-22 Raptor",          "category": "Aircraft",     "price": 25_000_000, "initial": 180,  "maint": 80_000},
        {"key": "f15e",           "name": "F-15E Strike Eagle",   "category": "Aircraft",     "price": 12_000_000, "initial": 220,  "maint": 35_000},
        {"key": "f15ex",          "name": "F-15EX Eagle II",      "category": "Aircraft",     "price": 15_000_000, "initial": 20,   "maint": 40_000},
        {"key": "f16",            "name": "F-16 Fighting Falcon", "category": "Aircraft",     "price": 8_000_000,  "initial": 700,  "maint": 20_000},
        {"key": "fa18ef",         "name": "F/A-18E/F Super Hornet","category": "Aircraft",    "price": 10_000_000, "initial": 550,  "maint": 30_000},
        {"key": "b1b",            "name": "B-1B Lancer",          "category": "Aircraft",     "price": 35_000_000, "initial": 40,   "maint": 110_000},
        {"key": "b2",             "name": "B-2 Spirit",           "category": "Aircraft",     "price": 50_000_000, "initial": 20,   "maint": 150_000},
        {"key": "b52h",           "name": "B-52H Stratofortress", "category": "Aircraft",     "price": 30_000_000, "initial": 70,   "maint": 100_000},
        {"key": "c17",            "name": "C-17 Globemaster III", "category": "Aircraft",     "price": 20_000_000, "initial": 220,  "maint": 45_000},
        {"key": "c130",           "name": "C-130 Hercules",       "category": "Aircraft",     "price": 6_000_000,  "initial": 300,  "maint": 15_000},
        {"key": "c5m",            "name": "C-5M Galaxy",          "category": "Aircraft",     "price": 30_000_000, "initial": 50,   "maint": 80_000},
        {"key": "kc135",          "name": "KC-135 Stratotanker",  "category": "Aircraft",     "price": 8_000_000,  "initial": 380,  "maint": 20_000},
        {"key": "kc46",           "name": "KC-46 Pegasus",        "category": "Aircraft",     "price": 12_000_000, "initial": 100,  "maint": 25_000},
        {"key": "e3_sentry",      "name": "E-3 Sentry AEW",       "category": "Aircraft",     "price": 25_000_000, "initial": 20,   "maint": 50_000},
        {"key": "e7_wedgetail",   "name": "E-7 Wedgetail",        "category": "Aircraft",     "price": 30_000_000, "initial": 10,   "maint": 60_000},
        {"key": "rc135",          "name": "RC-135 Rivet Joint",   "category": "Aircraft",     "price": 20_000_000, "initial": 20,   "maint": 40_000},
        {"key": "u2_dragon",      "name": "U-2 Dragon Lady",      "category": "Aircraft",     "price": 15_000_000, "initial": 20,   "maint": 30_000},
        {"key": "ah64e",          "name": "AH-64E Apache",        "category": "Aircraft",     "price": 5_000_000,  "initial": 800,  "maint": 15_000},
        {"key": "uh60",           "name": "UH-60 Black Hawk",     "category": "Aircraft",     "price": 3_000_000,  "initial": 2000, "maint": 8_000},
        {"key": "ch47",           "name": "CH-47 Chinook",        "category": "Aircraft",     "price": 6_000_000,  "initial": 500,  "maint": 15_000},
        {"key": "ah1z",           "name": "AH-1Z Viper",          "category": "Aircraft",     "price": 4_000_000,  "initial": 100,  "maint": 10_000},
        {"key": "v22",            "name": "V-22 Osprey",          "category": "Aircraft",     "price": 10_000_000, "initial": 400,  "maint": 25_000},
        {"key": "mh60",           "name": "MH-60 Seahawk",        "category": "Aircraft",     "price": 4_000_000,  "initial": 500,  "maint": 10_000},

        # پهپادها (UAV)
        {"key": "mq9",            "name": "MQ-9 Reaper",          "category": "UAV",          "price": 3_000_000,  "initial": 300,  "maint": 10_000},
        {"key": "rq4",            "name": "RQ-4 Global Hawk",     "category": "UAV",          "price": 15_000_000, "initial": 30,   "maint": 30_000},
        {"key": "mq1c",           "name": "MQ-1C Gray Eagle",     "category": "UAV",          "price": 2_000_000,  "initial": 100,  "maint": 5_000},
        {"key": "tactical_drones","name": "Tactical Recon UAVs",  "category": "UAV",          "price": 500_000,    "initial": 300,  "maint": 1_000},

        # نیروی زمینی (Ground Forces)
        {"key": "m1a2_abrams",    "name": "M1A2 Abrams",          "category": "Ground Forces","price": 3_000_000,  "initial": 2500, "maint": 8_000},
        {"key": "m1a1_abrams",    "name": "M1A1 Abrams",          "category": "Ground Forces","price": 2_000_000,  "initial": 1000, "maint": 5_000},
        {"key": "m2_bradley",     "name": "M2 Bradley IFV",       "category": "Ground Forces","price": 1_200_000,  "initial": 2500, "maint": 3_000},
        {"key": "stryker",        "name": "Stryker APC",          "category": "Ground Forces","price": 800_000,    "initial": 5000, "maint": 2_000},
        {"key": "m113_usa",       "name": "M113 APC",             "category": "Ground Forces","price": 300_000,    "initial": 1500, "maint": 800},
        {"key": "jltv",           "name": "JLTV Vehicle",         "category": "Ground Forces","price": 400_000,    "initial": 10000,"maint": 1_000},
        {"key": "light_armored",  "name": "Light Armored Vehicles","category": "Ground Forces","price": 500_000,   "initial": 6000, "maint": 1_200},

        # توپخانه و راکت‌اندازها (Artillery)
        {"key": "m109_paladin",   "name": "M109 Paladin",         "category": "Artillery",    "price": 1_500_000,  "initial": 900,  "maint": 4_000},
        {"key": "m777",           "name": "M777 Howitzer",        "category": "Artillery",    "price": 800_000,    "initial": 800,  "maint": 2_000},
        {"key": "himars",         "name": "HIMARS Rocket",        "category": "Artillery",    "price": 3_000_000,  "initial": 500,  "maint": 8_000},
        {"key": "m270_mlrs",      "name": "M270 MLRS",            "category": "Artillery",    "price": 2_500_000,  "initial": 300,  "maint": 6_000},

        # نیروی دریایی و آبی‌خاکی (Navy)
        {"key": "ford_class",     "name": "Ford Class Carrier",   "category": "Navy",         "price": 100_000_000,"initial": 3,    "maint": 500_000},
        {"key": "nimitz_class",   "name": "Nimitz Class Carrier", "category": "Navy",         "price": 80_000_000, "initial": 10,   "maint": 400_000},
        {"key": "america_class",  "name": "America Class Ship",   "category": "Navy",         "price": 30_000_000, "initial": 2,    "maint": 120_000},
        {"key": "wasp_class",     "name": "Wasp Class Ship",      "category": "Navy",         "price": 25_000_000, "initial": 8,    "maint": 100_000},
        {"key": "san_antonio",    "name": "San Antonio Class",    "category": "Navy",         "price": 15_000_000, "initial": 12,   "maint": 60_000},
        {"key": "harpers_ferry",  "name": "Harpers Ferry Class",  "category": "Navy",         "price": 10_000_000, "initial": 4,    "maint": 40_000},
        {"key": "whidbey_island", "name": "Whidbey Island Class", "category": "Navy",         "price": 10_000_000, "initial": 6,    "maint": 40_000},
        {"key": "burke_class",    "name": "Arleigh Burke Destroyer","category": "Navy",       "price": 20_000_000, "initial": 70,   "maint": 100_000},
        {"key": "zumwalt",        "name": "Zumwalt Destroyer",    "category": "Navy",         "price": 40_000_000, "initial": 3,    "maint": 180_000},
        {"key": "ticonderoga",    "name": "Ticonderoga Cruiser",  "category": "Navy",         "price": 25_000_000, "initial": 10,   "maint": 120_000},
        {"key": "lcs_ship",       "name": "Littoral Combat Ship", "category": "Navy",         "price": 8_000_000,  "initial": 20,   "maint": 30_000},
        {"key": "patrol_coastal", "name": "Patrol / Coastal Ships","category": "Navy",        "price": 1_000_000,  "initial": 70,   "maint": 3_000},
        {"key": "supply_ships",   "name": "Supply Support Ships", "category": "Navy",         "price": 5_000_000,  "initial": 6,    "maint": 20_000},
        {"key": "puller_ships",   "name": "Lewis B. Puller Base", "category": "Navy",         "price": 8_000_000,  "initial": 2,    "maint": 30_000},
        {"key": "logistics_ships","name": "Logistics & Support",  "category": "Navy",         "price": 3_000_000,  "initial": 100,  "maint": 10_000},
        {"key": "virginia_class", "name": "Virginia Class Sub",   "category": "Navy",         "price": 35_000_000, "initial": 25,   "maint": 150_000},
        {"key": "los_angeles_sub","name": "Los Angeles Class Sub","category": "Navy",         "price": 20_000_000, "initial": 20,   "maint": 90_000},
        {"key": "seawolf_sub",    "name": "Seawolf Class Sub",    "category": "Navy",         "price": 45_000_000, "initial": 3,    "maint": 200_000},
        {"key": "ohio_ssbn",      "name": "Ohio Class SSBN Sub",  "category": "Navy",         "price": 50_000_000, "initial": 14,   "maint": 220_000},
        {"key": "ohio_ssgn",      "name": "Ohio Class SSGN Sub",  "category": "Navy",         "price": 40_000_000, "initial": 4,    "maint": 180_000},

        # توان موشکی و مهمات (Missiles)
        {"key": "tomahawk",       "name": "Tomahawk Cruise Missile","category": "Missiles",   "price": 2_000_000,  "initial": 2000, "maint": 2_000},
        {"key": "sm6",            "name": "SM-6 Missile",         "category": "Missiles",     "price": 3_000_000,  "initial": 500,  "maint": 4_000},
        {"key": "sm3",            "name": "SM-3 Anti-Ballistic",  "category": "Missiles",     "price": 10_000_000, "initial": 300,  "maint": 15_000},
        {"key": "aim120",         "name": "AIM-120 AMRAAM",       "category": "Missiles",     "price": 1_000_000,  "initial": 1500, "maint": 1_000},
        {"key": "aim9x",          "name": "AIM-9X Sidewinder",    "category": "Missiles",     "price": 500_000,    "initial": 1000, "maint": 500},
        {"key": "jassm",          "name": "AGM-158 JASSM",        "category": "Missiles",     "price": 1_500_000,  "initial": 500,  "maint": 2_000},
        {"key": "lrasm",          "name": "AGM-158C LRASM",       "category": "Missiles",     "price": 3_000_000,  "initial": 300,  "maint": 4_000},
        {"key": "harm_aargm",     "name": "AGM-88 HARM/AARGM",    "category": "Missiles",     "price": 1_000_000,  "initial": 500,  "maint": 1_200},
        {"key": "hellfire",       "name": "AGM-114 Hellfire",     "category": "Missiles",     "price": 150_000,    "initial": 3000, "maint": 200},

        # پدافند هوایی (Air Defense)
        {"key": "patriot_pac3",   "name": "Patriot PAC-3",        "category": "Air Defense",  "price": 10_000_000, "initial": 60,   "maint": 30_000},
        {"key": "thaad",          "name": "THAAD Battery",        "category": "Air Defense",  "price": 40_000_000, "initial": 10,   "maint": 100_000},
        {"key": "nasams",         "name": "NASAMS System",        "category": "Air Defense",  "price": 8_000_000,  "initial": 15,   "maint": 25_000},
        {"key": "avenger",        "name": "Avenger Air Defense",  "category": "Air Defense",  "price": 2_000_000,  "initial": 100,  "maint": 5_000},
        {"key": "military_radars","name": "Military Radars",      "category": "Air Defense",  "price": 5_000_000,  "initial": 250,  "maint": 15_000},
    ],
    "israel": [
        # نیروی هوایی (Aircraft)
        {"key": "f35i_adir",      "name": "F-35I Adir",           "category": "Aircraft",     "price": 18_000_000, "initial": 40,   "maint": 60_000},
        {"key": "f15_israel",     "name": "F-15 Eagle/Strike",    "category": "Aircraft",     "price": 12_000_000, "initial": 80,   "maint": 35_000},
        {"key": "f16_israel",     "name": "F-16 Fighting Falcon", "category": "Aircraft",     "price": 8_000_000,  "initial": 170,  "maint": 20_000},
        {"key": "c130_hercules",  "name": "C-130 Hercules",       "category": "Aircraft",     "price": 6_000_000,  "initial": 10,   "maint": 15_000},
        {"key": "kc707_reem",     "name": "KC-707 Re'em",         "category": "Aircraft",     "price": 10_000_000, "initial": 5,    "maint": 25_000},
        {"key": "gulfstream_g550","name": "Gulfstream G550",      "category": "Aircraft",     "price": 15_000_000, "initial": 10,   "maint": 30_000},
        {"key": "e2c_hawkeye",    "name": "E-2C Hawkeye",         "category": "Aircraft",     "price": 12_000_000, "initial": 5,    "maint": 25_000},
        {"key": "ah64_apache",    "name": "AH-64 Apache",         "category": "Aircraft",     "price": 5_000_000,  "initial": 50,   "maint": 15_000},
        {"key": "ch53_yasur",     "name": "CH-53 Yasur",          "category": "Aircraft",     "price": 7_000_000,  "initial": 20,   "maint": 18_000},
        {"key": "uh60_blackhawk", "name": "UH-60 Black Hawk",     "category": "Aircraft",     "price": 3_000_000,  "initial": 50,   "maint": 8_000},

        # پهپادها (UAV)
        {"key": "hermes_450",     "name": "Hermes 450",           "category": "UAV",          "price": 1_000_000,  "initial": 50,   "maint": 3_000},
        {"key": "hermes_900",     "name": "Hermes 900",           "category": "UAV",          "price": 2_500_000,  "initial": 30,   "maint": 7_000},
        {"key": "heron_tp",       "name": "Heron TP (Eitan)",     "category": "UAV",          "price": 4_000_000,  "initial": 20,   "maint": 10_000},
        {"key": "harpy_drone",    "name": "Harpy Drone",          "category": "UAV",          "price": 200_000,    "initial": 200,  "maint": 500},

        # نیروی زمینی (Ground Forces)
        {"key": "merkava_mk4",    "name": "Merkava Mk4",          "category": "Ground Forces","price": 3_500_000,  "initial": 700,  "maint": 8_000},
        {"key": "merkava_mk3",    "name": "Merkava Mk3",          "category": "Ground Forces","price": 2_000_000,  "initial": 500,  "maint": 5_000},
        {"key": "merkava_barak",  "name": "Merkava Barak",        "category": "Ground Forces","price": 5_000_000,  "initial": 50,   "maint": 12_000},
        {"key": "namer_apc",      "name": "Namer APC",            "category": "Ground Forces","price": 2_000_000,  "initial": 300,  "maint": 4_000},
        {"key": "achzarit_apc",   "name": "Achzarit APC",         "category": "Ground Forces","price": 1_000_000,  "initial": 200,  "maint": 2_000},
        {"key": "m113_apc",       "name": "M113 APC",             "category": "Ground Forces","price": 300_000,    "initial": 5000, "maint": 800},
        {"key": "eitan_apc",      "name": "Eitan APC",            "category": "Ground Forces","price": 1_500_000,  "initial": 50,   "maint": 3_000},

        # توپخانه (Artillery)
        {"key": "m109_doher",     "name": "M109 Doher",           "category": "Artillery",    "price": 1_200_000,  "initial": 400,  "maint": 3_000},
        {"key": "atmos_2000",     "name": "ATMOS 2000",           "category": "Artillery",    "price": 2_000_000,  "initial": 40,   "maint": 5_000},
        {"key": "m270_mlrs",      "name": "M270 MLRS",            "category": "Artillery",    "price": 2_500_000,  "initial": 50,   "maint": 6_000},

        # نیروی دریایی (Navy)
        {"key": "saar_6",         "name": "Sa'ar 6 Corvette",     "category": "Navy",         "price": 30_000_000, "initial": 4,    "maint": 100_000},
        {"key": "saar_5",         "name": "Sa'ar 5 Corvette",     "category": "Navy",         "price": 18_000_000, "initial": 3,    "maint": 60_000},
        {"key": "dolphin_sub",    "name": "Dolphin Submarine",    "category": "Navy",         "price": 40_000_000, "initial": 6,    "maint": 150_000},
        {"key": "super_dvora",    "name": "Super Dvora",          "category": "Navy",         "price": 800_000,    "initial": 15,   "maint": 2_000},
        {"key": "patrol_vessels", "name": "Patrol Vessels",       "category": "Navy",         "price": 500_000,    "initial": 50,   "maint": 1_000},

        # موشکی (Missiles)
        {"key": "jericho_3",      "name": "Jericho III",          "category": "Missiles",     "price": 15_000_000, "initial": 30,   "maint": 40_000},
        {"key": "jericho_2",      "name": "Jericho II",           "category": "Missiles",     "price": 8_000_000,  "initial": 50,   "maint": 20_000},
        {"key": "popeye_missile", "name": "Popeye Missile",       "category": "Missiles",     "price": 1_500_000,  "initial": 300,  "maint": 2_000},
        {"key": "delilah_missile","name": "Delilah Missile",      "category": "Missiles",     "price": 1_000_000,  "initial": 400,  "maint": 1_500},
        {"key": "spike_missile",  "name": "Spike Anti-Tank",      "category": "Missiles",     "price": 200_000,    "initial": 1000, "maint": 300},

        # پدافند هوایی (Air Defense)
        {"key": "iron_dome",      "name": "Iron Dome",            "category": "Air Defense",  "price": 10_000_000, "initial": 15,   "maint": 30_000},
        {"key": "davids_sling",   "name": "David's Sling",        "category": "Air Defense",  "price": 20_000_000, "initial": 5,    "maint": 50_000},
        {"key": "arrow_3",        "name": "Arrow-2 / Arrow-3",    "category": "Air Defense",  "price": 30_000_000, "initial": 6,    "maint": 80_000},
        {"key": "patriot_israel", "name": "Patriot Battery",      "category": "Air Defense",  "price": 8_000_000,  "initial": 8,    "maint": 20_000},
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
