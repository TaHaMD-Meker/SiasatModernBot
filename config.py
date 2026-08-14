# -*- coding: utf-8 -*-
"""
تنظیمات عمومی بازی، لیست ۱۷ کشور، مقادیر اولیه و کاتالوگ جامع دارایی‌های نظامی اختصاصی تمام کشورها (Country Assets Catalog).
تضمین بالانس بازی (Game Balance) برای تمام قدرت‌ها.
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
    # ۱. فرانسه
    "france": [
        {"key": "rafale",         "name": "Dassault Rafale",      "category": "Aircraft",     "price": 18_000_000, "initial": 180,  "maint": 50_000},
        {"key": "mirage_2000",   "name": "Mirage 2000",          "category": "Aircraft",     "price": 10_000_000, "initial": 90,   "maint": 30_000},
        {"key": "a400m_fr",      "name": "A400M Atlas",          "category": "Aircraft",     "price": 20_000_000, "initial": 20,   "maint": 40_000},
        {"key": "a330_mrtt_fr",  "name": "A330 MRTT Tanker",     "category": "Aircraft",     "price": 25_000_000, "initial": 12,   "maint": 50_000},
        {"key": "tiger_heli_fr", "name": "Eurocopter Tiger",     "category": "Aircraft",     "price": 8_000_000,  "initial": 70,   "maint": 20_000},
        {"key": "nh90_fr",       "name": "NH90 Caiman",          "category": "Aircraft",     "price": 6_000_000,  "initial": 70,   "maint": 15_000},
        {"key": "reaper_fr",     "name": "MQ-9 Reaper",          "category": "UAV",          "price": 3_000_000,  "initial": 12,   "maint": 10_000},
        {"key": "leclerc_tank",  "name": "Leclerc Tank",         "category": "Ground Forces","price": 4_000_000,  "initial": 220,  "maint": 9_000},
        {"key": "vbci_ifv",      "name": "VBCI Armored Vehicle", "category": "Ground Forces","price": 1_500_000,  "initial": 600,  "maint": 3_500},
        {"key": "griffon_apc",   "name": "Griffon VBMR",         "category": "Ground Forces","price": 1_000_000,  "initial": 500,  "maint": 2_500},
        {"key": "caesar_art",    "name": "CAESAR Howitzer",      "category": "Artillery",    "price": 2_000_000,  "initial": 80,   "maint": 5_000},
        {"key": "charles_de_gaulle","name":"Charles de Gaulle Carrier","category": "Navy",   "price": 95_000_000, "initial": 1,    "maint": 500_000},
        {"key": "fremm_frigate", "name": "FREMM Frigate",         "category": "Navy",         "price": 25_000_000, "initial": 8,    "maint": 90_000},
        {"key": "suffren_sub",   "name": "Suffren SSN Submarine", "category": "Navy",         "price": 35_000_000, "initial": 2,    "maint": 150_000},
        {"key": "triomphant_sub","name": "Triomphant SSBN Sub",  "category": "Navy",         "price": 50_000_000, "initial": 4,    "maint": 220_000},
        {"key": "scalp_eg",      "name": "SCALP EG Cruise",      "category": "Missiles",     "price": 2_000_000,  "initial": 300,  "maint": 3_000},
        {"key": "exocet",        "name": "Exocet Anti-Ship",     "category": "Missiles",     "price": 1_200_000,  "initial": 300,  "maint": 2_000},
        {"key": "samp_t",        "name": "SAMP/T Air Defense",   "category": "Air Defense",  "price": 12_000_000, "initial": 10,   "maint": 35_000},
    ],

    # ۲. ژاپن
    "japan": [
        {"key": "f35_japan",     "name": "F-35A/B Lightning II", "category": "Aircraft",     "price": 16_000_000, "initial": 40,   "maint": 50_000},
        {"key": "f15j",          "name": "F-15J Eagle",          "category": "Aircraft",     "price": 12_000_000, "initial": 200,  "maint": 35_000},
        {"key": "f2_japan",      "name": "Mitsubishi F-2",       "category": "Aircraft",     "price": 14_000_000, "initial": 90,   "maint": 38_000},
        {"key": "e2d_hawkeye",   "name": "E-2D Advanced Hawkeye","category": "Aircraft",     "price": 15_000_000, "initial": 15,   "maint": 35_000},
        {"key": "type10_tank",   "name": "Type 10 Main Battle Tank","category":"Ground Forces","price":4_500_000, "initial": 100,  "maint": 10_000},
        {"key": "type90_tank",   "name": "Type 90 Tank",         "category": "Ground Forces","price": 3_000_000,  "initial": 300,  "maint": 7_000},
        {"key": "izumo_carrier", "name": "Izumo Helicopter Carrier","category": "Navy",      "price": 70_000_000, "initial": 2,    "maint": 350_000},
        {"key": "maya_destroyer","name": "Maya Class Aegis Destroyer","category":"Navy",     "price": 30_000_000, "initial": 2,    "maint": 120_000},
        {"key": "soryu_sub",     "name": "Soryu Class Submarine","category": "Navy",         "price": 25_000_000, "initial": 12,   "maint": 100_000},
        {"key": "type12_antiship","name":"Type 12 Anti-Ship",    "category": "Missiles",     "price": 1_500_000,  "initial": 300,  "maint": 2_500},
        {"key": "pac3_japan",    "name": "Patriot PAC-3 Battery","category": "Air Defense",  "price": 10_000_000, "initial": 24,   "maint": 30_000},
    ],

    # ۳. ترکیه
    "turkey": [
        {"key": "f16_turkey",    "name": "F-16C/D Block 50+",    "category": "Aircraft",     "price": 8_000_000,  "initial": 240,  "maint": 20_000},
        {"key": "t129_atak",     "name": "T129 ATAK Helicopter", "category": "Aircraft",     "price": 5_000_000,  "initial": 60,   "maint": 12_000},
        {"key": "tb2_drone",     "name": "Bayraktar TB2",        "category": "UAV",          "price": 500_000,    "initial": 200,  "maint": 1_000},
        {"key": "akinci_drone",  "name": "Bayraktar Akıncı",     "category": "UAV",          "price": 2_000_000,  "initial": 40,   "maint": 5_000},
        {"key": "kizilelma",     "name": "Kızılelma Stealth UAV","category": "UAV",          "price": 4_000_000,  "initial": 10,   "maint": 10_000},
        {"key": "altay_tank",    "name": "Altay Main Battle Tank","category":"Ground Forces","price": 4_000_000,  "initial": 10,   "maint": 9_000},
        {"key": "leopard2_turk", "name": "Leopard 2A4 Tank",     "category": "Ground Forces","price": 2_500_000,  "initial": 300,  "maint": 6_000},
        {"key": "firtina_art",   "name": "Fırtına T-155 Howitzer","category": "Artillery",   "price": 1_800_000,  "initial": 350,  "maint": 4_000},
        {"key": "anadolu_carrier","name":"TCG Anadolu Assault Carrier","category":"Navy",    "price": 60_000_000, "initial": 1,    "maint": 300_000},
        {"key": "reis_sub",      "name": "Type 214 Reis Submarine","category": "Navy",        "price": 25_000_000, "initial": 2,    "maint": 90_000},
        {"key": "som_missile",   "name": "SOM Cruise Missile",   "category": "Missiles",     "price": 1_200_000,  "initial": 200,  "maint": 2_000},
        {"key": "s400_turkey",   "name": "S-400 Triumf Battery", "category": "Air Defense",  "price": 15_000_000, "initial": 4,    "maint": 40_000},
        {"key": "hisar_o",       "name": "Hisar-O+ Defense",     "category": "Air Defense",  "price": 5_000_000,  "initial": 15,   "maint": 12_000},
    ],

    # ۴. عربستان سعودی
    "saudi": [
        {"key": "f15sa",          "name": "F-15SA Strike Eagle",  "category": "Aircraft",     "price": 15_000_000, "initial": 230,  "maint": 40_000},
        {"key": "typhoon_saudi",  "name": "Eurofighter Typhoon",  "category": "Aircraft",     "price": 18_000_000, "initial": 72,   "maint": 50_000},
        {"key": "tornado_saudi",  "name": "Tornado IDS",          "category": "Aircraft",     "price": 10_000_000, "initial": 80,   "maint": 30_000},
        {"key": "ah64_saudi",     "name": "AH-64E Apache",        "category": "Aircraft",     "price": 5_000_000,  "initial": 48,   "maint": 15_000},
        {"key": "m1a2s_abrams",   "name": "M1A2S Abrams Tank",    "category": "Ground Forces","price": 3_000_000,  "initial": 450,  "maint": 8_000},
        {"key": "lav_25_saudi",   "name": "LAV-25 Armored Vehicle","category":"Ground Forces","price": 800_000,   "initial": 1000, "maint": 2_000},
        {"key": "plz45_art",      "name": "PLZ-45 Howitzer",      "category": "Artillery",    "price": 1_500_000,  "initial": 50,   "maint": 3_500},
        {"key": "al_riyadh",      "name": "Al Riyadh Frigate",    "category": "Navy",         "price": 20_000_000, "initial": 3,    "maint": 70_000},
        {"key": "patriot_saudi",  "name": "Patriot PAC-3 Battery","category": "Air Defense",  "price": 10_000_000, "initial": 24,   "maint": 30_000},
        {"key": "thaad_saudi",    "name": "THAAD Battery",        "category": "Air Defense",  "price": 40_000_000, "initial": 4,    "maint": 100_000},
    ],

    # ۵. هند
    "india": [
        {"key": "su30mki",        "name": "Su-30MKI Flanker",     "category": "Aircraft",     "price": 14_000_000, "initial": 260,  "maint": 40_000},
        {"key": "rafale_india",   "name": "Dassault Rafale",      "category": "Aircraft",     "price": 18_000_000, "initial": 36,   "maint": 50_000},
        {"key": "mig29upg",       "name": "MiG-29UPG",            "category": "Aircraft",     "price": 9_000_000,  "initial": 60,   "maint": 25_000},
        {"key": "tejas_fighter",  "name": "LCA Tejas",            "category": "Aircraft",     "price": 8_000_000,  "initial": 40,   "maint": 20_000},
        {"key": "heron_india",    "name": "Heron TP UAV",         "category": "UAV",          "price": 3_000_000,  "initial": 50,   "maint": 8_000},
        {"key": "t90_bhishma",    "name": "T-90S Bhishma Tank",   "category": "Ground Forces","price": 2_500_000,  "initial": 1300, "maint": 6_000},
        {"key": "arjun_tank",     "name": "Arjun Mk1 Tank",       "category": "Ground Forces","price": 3_000_000,  "initial": 120,  "maint": 7_000},
        {"key": "k9_vajra",       "name": "K9 Vajra Howitzer",    "category": "Artillery",    "price": 2_000_000,  "initial": 100,  "maint": 5_000},
        {"key": "pinaka_mlrs",    "name": "Pinaka MLRS",          "category": "Artillery",    "price": 1_500_000,  "initial": 80,   "maint": 3_500},
        {"key": "ins_vikrant",    "name": "INS Vikrant Carrier",  "category": "Navy",         "price": 80_000_000, "initial": 1,    "maint": 400_000},
        {"key": "kolkata_dest",   "name": "Kolkata Class Destroyer","category":"Navy",        "price": 25_000_000, "initial": 3,    "maint": 90_000},
        {"key": "arihant_sub",    "name": "Arihant Nuclear SSBN", "category": "Navy",         "price": 45_000_000, "initial": 2,    "maint": 200_000},
        {"key": "brahmos",        "name": "BrahMos Supersonic",   "category": "Missiles",     "price": 2_500_000,  "initial": 500,  "maint": 4_000},
        {"key": "agni_v",         "name": "Agni-V ICBM",          "category": "Missiles",     "price": 15_000_000, "initial": 30,   "maint": 35_000},
        {"key": "s400_india",     "name": "S-400 Triumf Battery", "category": "Air Defense",  "price": 15_000_000, "initial": 3,    "maint": 40_000},
    ],

    # ۶. قطر
    "qatar": [
        {"key": "rafale_qatar",   "name": "Dassault Rafale",      "category": "Aircraft",     "price": 18_000_000, "initial": 36,   "maint": 50_000},
        {"key": "f15qa",          "name": "F-15QA Ababil",        "category": "Aircraft",     "price": 15_000_000, "initial": 36,   "maint": 40_000},
        {"key": "typhoon_qatar",  "name": "Eurofighter Typhoon",  "category": "Aircraft",     "price": 18_000_000, "initial": 24,   "maint": 50_000},
        {"key": "ah64_qatar",     "name": "AH-64E Apache",        "category": "Aircraft",     "price": 5_000_000,  "initial": 24,   "maint": 15_000},
        {"key": "leopard_qatar",  "name": "Leopard 2A7+ Tank",    "category": "Ground Forces","price": 4_500_000,  "initial": 62,   "maint": 10_000},
        {"key": "pzh2000_qatar",  "name": "PzH 2000 Howitzer",    "category": "Artillery",    "price": 2_500_000,  "initial": 24,   "maint": 6_000},
        {"key": "al_zubarah",     "name": "Al Zubarah Corvette",  "category": "Navy",         "price": 18_000_000, "initial": 4,    "maint": 60_000},
        {"key": "patriot_qatar",  "name": "Patriot PAC-3 Battery","category": "Air Defense",  "price": 10_000_000, "initial": 4,    "maint": 30_000},
    ],

    # ۷. امارات
    "uae": [
        {"key": "f16_block60",    "name": "F-16E/F Block 60",     "category": "Aircraft",     "price": 10_000_000, "initial": 78,   "maint": 25_000},
        {"key": "mirage_2000_9",  "name": "Mirage 2000-9",        "category": "Aircraft",     "price": 10_000_000, "initial": 55,   "maint": 25_000},
        {"key": "ah64_uae",       "name": "AH-64E Apache",        "category": "Aircraft",     "price": 5_000_000,  "initial": 28,   "maint": 15_000},
        {"key": "wing_loong_uae", "name": "Wing Loong II UAV",    "category": "UAV",          "price": 2_000_000,  "initial": 20,   "maint": 5_000},
        {"key": "leclerc_uae",    "name": "Leclerc Tank",         "category": "Ground Forces","price": 4_000_000,  "initial": 380,  "maint": 9_000},
        {"key": "bmp3_uae",       "name": "BMP-3 IFV",            "category": "Ground Forces","price": 1_200_000,  "initial": 590,  "maint": 3_000},
        {"key": "nimr_ajban",     "name": "Nimr Ajban APC",       "category": "Ground Forces","price": 300_000,    "initial": 1000, "maint": 800},
        {"key": "jobaria_mlrs",   "name": "Jobaria Heavy MLRS",   "category": "Artillery",    "price": 5_000_000,  "initial": 6,    "maint": 15_000},
        {"key": "baynunah_corv",  "name": "Baynunah Class Corvette","category":"Navy",        "price": 15_000_000, "initial": 6,    "maint": 50_000},
        {"key": "thaad_uae",      "name": "THAAD Battery",        "category": "Air Defense",  "price": 40_000_000, "initial": 2,    "maint": 100_000},
        {"key": "patriot_uae",    "name": "Patriot PAC-3 Battery","category": "Air Defense",  "price": 10_000_000, "initial": 9,    "maint": 30_000},
        {"key": "pantsir_uae",    "name": "Pantsir-S1 System",    "category": "Air Defense",  "price": 5_000_000,  "initial": 50,   "maint": 15_000},
    ],

    # ۸. مصر
    "egypt": [
        {"key": "rafale_egypt",   "name": "Dassault Rafale",      "category": "Aircraft",     "price": 18_000_000, "initial": 24,   "maint": 50_000},
        {"key": "f16_egypt",      "name": "F-16C/D Falcon",       "category": "Aircraft",     "price": 8_000_000,  "initial": 200,  "maint": 20_000},
        {"key": "mig29m_egypt",   "name": "MiG-29M/M2",           "category": "Aircraft",     "price": 10_000_000, "initial": 45,   "maint": 25_000},
        {"key": "ka52_egypt",     "name": "Ka-52 Alligator",      "category": "Aircraft",     "price": 6_000_000,  "initial": 46,   "maint": 15_000},
        {"key": "m1a1_egypt",     "name": "M1A1 Abrams Tank",     "category": "Ground Forces","price": 2_000_000,  "initial": 1100, "maint": 5_000},
        {"key": "m60a3_egypt",    "name": "M60A3 Tank",           "category": "Ground Forces","price": 800_000,    "initial": 850,  "maint": 2_000},
        {"key": "mistral_egypt",  "name": "Mistral LHD Carrier",  "category": "Navy",         "price": 50_000_000, "initial": 2,    "maint": 250_000},
        {"key": "gowind_corv",    "name": "Gowind 2500 Corvette", "category": "Navy",         "price": 12_000_000, "initial": 4,    "maint": 40_000},
        {"key": "s300vm_egypt",   "name": "Antey-2500 (S-300VM)", "category": "Air Defense",  "price": 12_000_000, "initial": 4,    "maint": 35_000},
    ],

    # ۹. اوکراین
    "ukraine": [
        {"key": "su27_ukraine",   "name": "Su-27 Flanker",        "category": "Aircraft",     "price": 8_000_000,  "initial": 30,   "maint": 22_000},
        {"key": "mig29_ukraine",  "name": "MiG-29",               "category": "Aircraft",     "price": 7_000_000,  "initial": 40,   "maint": 20_000},
        {"key": "f16_ukraine",    "name": "F-16 Fighting Falcon", "category": "Aircraft",     "price": 8_000_000,  "initial": 12,   "maint": 20_000},
        {"key": "tb2_ukraine",    "name": "Bayraktar TB2",        "category": "UAV",          "price": 500_000,    "initial": 30,   "maint": 1_000},
        {"key": "fpv_kamikaze",   "name": "FPV Kamikaze Drones",  "category": "UAV",          "price": 50_000,     "initial": 1000, "maint": 100},
        {"key": "t64bv_tank",     "name": "T-64BV Tank",          "category": "Ground Forces","price": 1_000_000,  "initial": 600,  "maint": 3_000},
        {"key": "leopard2_ukraine","name":"Leopard 2 Tank",       "category": "Ground Forces","price": 3_000_000,  "initial": 60,   "maint": 7_000},
        {"key": "bradley_ukraine","name":"M2 Bradley IFV",        "category": "Ground Forces","price": 1_200_000,  "initial": 150,  "maint": 3_000},
        {"key": "m777_ukraine",   "name": "M777 Howitzer",        "category": "Artillery",    "price": 800_000,    "initial": 150,  "maint": 2_000},
        {"key": "himars_ukraine", "name": "HIMARS Rocket System", "category": "Artillery",    "price": 3_000_000,  "initial": 38,   "maint": 8_000},
        {"key": "sea_baby_usv",   "name": "Sea Baby USV Drones",  "category": "Navy",         "price": 100_000,    "initial": 100,  "maint": 300},
        {"key": "neptune_missile","name": "Neptune Anti-Ship",    "category": "Missiles",     "price": 1_000_000,  "initial": 50,   "maint": 2_000},
        {"key": "patriot_ukraine","name":"Patriot PAC-3 Battery", "category": "Air Defense",  "price": 10_000_000, "initial": 3,    "maint": 30_000},
        {"key": "nasams_ukraine", "name": "NASAMS System",        "category": "Air Defense",  "price": 8_000_000,  "initial": 5,    "maint": 25_000},
        {"key": "gepard_spaag",   "name": "Gepard SPAAG",         "category": "Air Defense",  "price": 1_500_000,  "initial": 40,   "maint": 4_000},
    ],

    # ۱۰. برزیل
    "brazil": [
        {"key": "gripen_e",       "name": "JAS 39 Gripen E",      "category": "Aircraft",     "price": 15_000_000, "initial": 15,   "maint": 40_000},
        {"key": "amx_a1",         "name": "AMX A-1 Attack",       "category": "Aircraft",     "price": 5_000_000,  "initial": 30,   "maint": 15_000},
        {"key": "f5em_brazil",    "name": "F-5EM Tiger II",       "category": "Aircraft",     "price": 4_000_000,  "initial": 40,   "maint": 10_000},
        {"key": "kc390",          "name": "Embraer KC-390",       "category": "Aircraft",     "price": 18_000_000, "initial": 6,    "maint": 35_000},
        {"key": "super_tucano",   "name": "EMB 314 Super Tucano", "category": "Aircraft",     "price": 2_000_000,  "initial": 60,   "maint": 5_000},
        {"key": "leopard1a5",     "name": "Leopard 1A5 Tank",     "category": "Ground Forces","price": 1_000_000,  "initial": 220,  "maint": 3_000},
        {"key": "guarani_apc",    "name": "VBTP-MR Guarani",      "category": "Ground Forces","price": 600_000,    "initial": 600,  "maint": 1_500},
        {"key": "astros2_mlrs",   "name": "ASTROS II MLRS",       "category": "Artillery",    "price": 2_500_000,  "initial": 60,   "maint": 6_000},
        {"key": "atlantico_carrier","name":"NAM Atlântico Carrier","category": "Navy",        "price": 50_000_000, "initial": 1,    "maint": 250_000},
        {"key": "riachuelo_sub",  "name": "Riachuelo Submarine",  "category": "Navy",         "price": 20_000_000, "initial": 2,    "maint": 70_000},
        {"key": "mansup_missile", "name": "MANSUP Anti-Ship",     "category": "Missiles",     "price": 1_000_000,  "initial": 50,   "maint": 2_000},
        {"key": "rbs70_airdef",   "name": "RBS 70 System",        "category": "Air Defense",  "price": 1_000_000,  "initial": 40,   "maint": 2_500},
    ],

    # ۱۱. آلمان (قبلاً ثبت شده)
    # ۱۲. ایران (قبلاً ثبت شده)
    # ۱۳. آمریکا (قبلاً ثبت شده)
    # ۱۴. اسرائیل (قبلاً ثبت شده)
}

# کاتالوگ عمومی برای سایر کشورها (قطر، امارات، مصر، اوکراین و برزیل در صورت عدم ثبت اختصاصی)
DEFAULT_COUNTRY_EQUIPMENT = [
    {"key": "gen_fighter",   "name": "جنگنده پیشرفته نسل ۴.۵", "category": "Aircraft",     "price": 10_000_000, "initial": 150, "maint": 25_000},
    {"key": "gen_bomber",    "name": "بمب‌افکن استراتژیک",     "category": "Aircraft",     "price": 25_000_000, "initial": 20,  "maint": 60_000},
    {"key": "gen_missile",   "name": "موشک کروز استراتژیک",   "category": "Missiles",     "price": 2_000_000,  "initial": 500, "maint": 2_000},
    {"key": "gen_airdef",    "name": "سامانه پدافند موشکی",  "category": "Air Defense",  "price": 10_000_000, "initial": 20,  "maint": 25_000},
    {"key": "gen_uav",       "name": "پهپاد شناسایی-رزمی",  "category": "UAV",          "price": 1_000_000,  "initial": 200, "maint": 3_000},
    {"key": "gen_frigate",   "name": "ناو محافظ سنگین",       "category": "Navy",         "price": 20_000_000, "initial": 10,  "maint": 80_000},
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
