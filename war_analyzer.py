# -*- coding: utf-8 -*-
"""
ماژول تحلیل هوشمند سناریوی نبرد و شبیه‌ساز جنگ‌ها (AI War & Battle Simulator Engine v6.0)
پشتیبانی از مشاهده تعاملی جزئیات نبرد با دکمه‌های شیشه‌ای:
- [📋 گاه‌شماری نبرد] [💥 آسیب‌های زیرساختی] [🗺️ وضعیت خطوط مرزی] [📊 فاکتور تلفات]
- اعمال اثر مستقیم استراتژیک بر دیتابیس (پالایشگاه‌ها، نیروگاه‌های برق، رادارها).
- نگارش کاملاً کارشناسی، سنگین، بدون ایموجی‌های اضافی و مرتب.
"""

import os
import re
import random
import json
import urllib.request
import database as db
import config

# نقشه مرز زمینی مشترک — تهاجم زمینی فقط بین همسایه‌های واقعی مجاز است
# (کشورهای جزیره‌ای مانند انگلستان، ژاپن، تایوان، سوئد و کوبا مرز زمینی ندارند)
GROUND_ADJACENCY = {
    "iran": {"iraq", "turkey", "pakistan"},
    "iraq": {"iran", "turkey", "saudi", "kuwait"},
    "saudi": {"iraq", "kuwait", "uae", "qatar", "oman"},
    "qatar": {"saudi"},
    "uae": {"saudi", "oman"},
    "oman": {"saudi", "uae"},
    "kuwait": {"iraq", "saudi"},
    "israel": {"egypt", "hezbollah"},
    "egypt": {"israel"},
    "hezbollah": {"israel"},
    "turkey": {"iran", "iraq"},
    "russia": {"ukraine", "poland", "china", "north_korea"},
    "ukraine": {"russia", "poland"},
    "poland": {"germany", "ukraine", "russia"},
    "germany": {"poland", "france"},
    "france": {"germany", "italy"},
    "italy": {"france"},
    "china": {"russia", "north_korea", "pakistan", "india"},
    "north_korea": {"china", "russia", "south_korea"},
    "south_korea": {"north_korea"},
    "india": {"pakistan", "china"},
    "pakistan": {"iran", "india", "china"},
    "usa": {"canada"},
    "canada": {"usa"},
    "brazil": {"venezuela"},
    "venezuela": {"brazil"},
}

def has_ground_border(a: str, b: str) -> bool:
    return b in GROUND_ADJACENCY.get(a, set())


def convert_farsi_digits(text: str) -> str:
    farsi_digits = '۰۱۲۳۴۵۶۷۸۹'
    eng_digits = '0123456789'
    trans_table = str.maketrans(farsi_digits, eng_digits)
    return text.translate(trans_table)


def detect_operation_type(attacker_key: str, defender_key: str, attacker_role: str, defender_role: str):
    """تشخیص هوشمند نوع عملیات: ترکیبی (زمینی+موشکی)، تهاجم زمینی، یا حمله موشکی/هوایی.

    نسخه ۲: فقط رول مهاجم ملاک است (رول مدافع توصیف دفاع است نه نوع عملیات) و
    تشخیص زمینی نیازمند «نشانگر قوی» است که واقعاً به معنای پیشروی/اشغال باشد؛
    صفت‌های توصیفی مانند «مرزی»، «شهر» یا «شهرک» دیگر حمله را زمینی نمی‌کنند.
    """
    # بدون مرز زمینی مشترک، تهاجم زمینی غیرممکن است
    if not has_ground_border(attacker_key, defender_key):
        return "air_missile"

    text = convert_farsi_digits((attacker_role or "").lower())

    # نشانگرهای قوی: فقط این‌ها یعنی عملیات زمینی واقعی در جریان است
    strong_ground = [
        "پیشروی", "ورود به خاک", "عبور از مرز", "تهاجم زمینی", "حمله زمینی",
        "عملیات زمینی", "نبرد زمینی", "حمله زرهی", "تسخیر", "اشغال", "تصرف",
        "ستون زرهی", "نبرد شهری", "گسترش قلمرو", "عبور زمینی", "پایگاه اشغالی",
        "حمله پیاده", "تهاجم پیاده", "عملیات هوابرد", "پیاده‌سازی نیرو",
    ]
    # نشانگرهای ضعیف: به‌تنهایی زمینی نمی‌کنند (ممکن است هدف حمله هوایی باشند)
    weak_ground = ["تانک", "نفربر", "زرهی", "پیاده‌نظام", "پیاده نظام", "محور"]
    air_keywords = [
        "موشک", "شلیک", "پرتاب", "پهپاد", "جنگنده", "پدافند", "سایبری",
        "پایگاه هوایی", "رادار", "سوله", "کروز", "بالستیک", "هایپرسونیک", "فتاح", "کالیبر", "اسکندر",
        "ضربتی هوایی", "سرکوب پدافند", "حمله هوایی", "ضربه هوایی",
    ]

    has_strong = any(kw in text for kw in strong_ground)
    weak_score = sum(1 for kw in weak_ground if kw in text)
    air_score = sum(1 for kw in air_keywords if kw in text)

    if has_strong:
        return "combined_arms" if air_score >= 2 else "ground_invasion"
    # فقط وقتی هیچ نشانه هوایی نیست و حداقل دو نشانگر ضعیف زمینی وجود دارد
    if weak_score >= 2 and air_score == 0:
        return "ground_invasion"
    return "air_missile"


def parse_weapon_mentions_from_roleplay_text(roleplay_text: str, country_assets: list, country_key: str) -> list:
    """استخراج هوشمند تسلیحات به‌کاررفته (استفاده‌شده) از متن رول بازیکن.

    نسخه ۲: هر عبارت متن فقط یک‌بار و فقط به یک تجهیز نسبت داده می‌شود تا
    واریانت‌های هم‌نام (مثل M1A1 و M1A2 آبرامز) دوباره‌شماری نشوند.
    خروجی = فهرست تسلیحات درگیر (نه تلفات نهایی).
    """
    if not roleplay_text or len(roleplay_text.strip()) < 5:
        return []

    text_clean = convert_farsi_digits(roleplay_text)
    catalog = config.COUNTRY_EQUIPMENT_CATALOG.get(country_key, [])

    assets_map = {}
    for a in country_assets:
        e_key = a.get("equipment_key") or a.get("key")
        e_name = a.get("equipment_name") or a.get("name")
        e_cat = a.get("category", "Missiles")
        e_amt = a.get("amount", a.get("initial", 100))
        e_price = a.get("buy_price", a.get("price", 1_000_000))
        if e_key:
            assets_map[e_key] = {
                "equipment_key": e_key, "equipment_name": e_name,
                "amount": e_amt, "category": e_cat, "price": e_price
            }

    for cat_item in catalog:
        e_key = cat_item.get("key")
        if e_key and e_key not in assets_map:
            assets_map[e_key] = {
                "equipment_key": e_key,
                "equipment_name": cat_item.get("name", e_key),
                "amount": cat_item.get("initial", 100),
                "category": cat_item.get("category", "Missiles"),
                "price": cat_item.get("price", 1_000_000)
            }

    alias_dict = {
        "hoveyzeh": ["هویزه", "hoveyzeh"],
        "noor": ["نور", "noor"],
        "paveh": ["پاوه", "paveh"],
        "kheybar": ["خیبرشکن", "خیبر شکن", "kheibar", "kheybar"],
        "sejjil": ["سجیل", "sejjil", "sajil"],
        "khorramshahr": ["خرمشهر", "khorramshahr"],
        "fattah": ["فتاح", "fattah"],
        "kalibr": ["کالیبر", "kalibr"],
        "iskander": ["اسکندر", "iskander"],
        "geran": ["جران", "گرن", "geran"],
        "shahed136": ["شاهد ۱۳۶", "شاهد-۱۳۶", "شاهد۱۳۶"],
        "shahed129": ["شاهد ۱۲۹", "شاهد-۱۲۹", "شاهد۱۲۹"],
        "shahed191": ["شاهد ۱۹۱", "شاهد-۱۹۱", "شاهد۱۹۱"],
        "mohajer6": ["مهاجر ۶", "مهاجر-۶", "مهاجر۶"],
        "fateh110": ["فاتح ۱۱۰", "فاتح-۱۱۰"],
        "fateh313": ["فاتح ۳۱۳", "فاتح-۳۱۳"],
        "zolfaghar": ["ذوالفقار"],
        "dezful": ["دزفول", "dezful"],
        "haj_qasem": ["حاج قاسم", "قاسم"],
        "iron_dome": ["گنبد آهنین", "گنبد اهنین", "iron dome"],
        "arrow": ["پیکان", "اروو", "arrow"],
        "david": ["فلاخن داوود", "داوود", "davids sling"],
        "patriot": ["پاتریوت", "patriot"],
        "f35": ["f-35", "f35", "اف-۳۵", "اف ۳۵"],
        "f15": ["f-15", "f15", "اف-۱۵", "اف ۱۵"],
        "f16": ["f-16", "f16", "اف-۱۶", "اف ۱۶"],
        "su35": ["سوخو-۳۵", "سوخو ۳۵", "su-35", "su35"],
        "su34": ["سوخو-۳۴", "سوخو ۳۴", "su-34", "su34"],
        "ka52": ["کا-۵۲", "آلیگاتور", "ka-52", "ka52"],
        "t90": ["t-90", "t90", "تی-۹۰", "تی ۹۰"],
        "t80": ["t-80", "t80", "تی-۸۰", "تی ۸۰"],
        "t72": ["t-72", "t72", "تی-۷۲", "تی ۷۲"],
        "bmp3": ["bmp-3", "bmp3", "بی‌ام‌پی-۳"],
        "abrams": ["آبرامز", "ابرامز", "abrams"],
        "merkava": ["مرکاوا", "merkava"],
        "leopard": ["لئوپارد", "لیوپارد", "leopard"],
        "javelin": ["جاولین", "javelin"],
        "stugna": ["استوگنا", "stugna"],
        "fpv": ["fpv", "اف‌پیوِی", "پهپاد انتحاری"],
    }

    # گزینش حریصانه مبتنی بر موقعیت: هر بازه متن فقط به یک تجهیز نسبت داده می‌شود
    candidates = []  # (start, length, order, e_key, qty)
    for order, (e_key, item) in enumerate(assets_map.items()):
        name = item["equipment_name"].lower()
        key = e_key.lower()

        keywords = set()
        keywords.add(name)
        keywords.add(key)
        # توکن اول کلید (مثل namer از namer_apc) برای تطبیق نام‌های عام در رول
        first_tok = key.split('_')[0]
        if len(first_tok) >= 4:
            keywords.add(first_tok)

        clean_name = re.sub(r'^(موشک|کروز|پدافند|ضدکشتی|تپ|راکت|تانک|شناور|ناوچه|پهپاد|سامانه|ناو)\s+', '', name)
        keywords.add(clean_name)
        keywords.add(clean_name.replace('-', ' '))
        keywords.add(clean_name.replace('-', ''))

        for alias_key, aliases in alias_dict.items():
            if alias_key in key or any(alias_key in kw for kw in keywords):
                for a in aliases:
                    keywords.add(a.lower())

        valid_keywords = sorted([kw for kw in keywords if len(kw) >= 2], key=len, reverse=True)

        for kw in valid_keywords:
            esc_kw = re.escape(kw)
            patterns = [
                # فرمت رول‌نویسی استاندارد: «نام ×عدد» یا «عدد× نام» (با اجازه پسوند مدل تا ۱۸ نویسه)
                esc_kw + r'\s*[\w.\- ]{0,18}?\s*[\u00d7xX\*]\s*(\d+)',
                r'(\d+)\s*[\u00d7xX\*]\s*[\w.\- ]{0,4}?\s*' + esc_kw,
                r'(\d+)\s*(?:فروند|عدد|دستگاه|سامانه|آتشبار|واحد|دست)?\s*(?:موشک|پهپاد|جنگنده|کروز|تانک|نفربر)?\s*' + esc_kw,
                esc_kw + r'\s*(?:\([^)]*\))?\s*(?:برد\s*\d+\s*کیلومتر)?\s*(?:با|تعداد|به تعداد)?\s*(\d+)\s*(?:فروند|عدد|دستگاه|واحد)?',
                esc_kw + r'\s*\(\s*(\d+)\s*\)',
                r'\(\s*(\d+)\s*' + esc_kw + r'\s*\)',
            ]
            for pat in patterns:
                m = re.search(pat, text_clean, re.IGNORECASE)
                if m and m.group(1):
                    qty = int(m.group(1))
                    if 0 < qty < 50000:
                        candidates.append((m.start(), m.end() - m.start(), order, e_key, qty))
                    break

    candidates.sort(key=lambda x: (x[0], -x[1], x[2]))

    claimed_ranges = []
    chosen = {}
    for start, length, order, e_key, qty in candidates:
        end = start + length
        if any(s < end and start < e for s, e in claimed_ranges):
            continue  # این بازه متن قبلاً به تجهیز دیگری اختصاص یافته
        if e_key in chosen:
            continue
        claimed_ranges.append((start, end))
        chosen[e_key] = qty

    return [
        {
            "equipment_key": e_key,
            "equipment_name": assets_map[e_key]["equipment_name"],
            "amount": qty,
            "category": assets_map[e_key]["category"],
            "price": assets_map[e_key]["price"],
        }
        for e_key, qty in chosen.items()
    ]


def calculate_battle_balance(att_assets, def_assets, att_tech=1, def_tech=1, att_app=80, def_app=80, att_readiness=70, def_readiness=70, op_type='air_missile'):
    """محاسبه موازنه توان هجومی، شبکه پدافندی و نرخ‌های احتمالی رهگیری/عبور/خسارت مهاجم."""
    
    att_missiles = sum(a.get("amount", 0) for a in att_assets if a.get("category") == "Missiles")
    att_uavs = sum(a.get("amount", 0) for a in att_assets if a.get("category") == "UAV")
    att_aircraft = sum(a.get("amount", 0) for a in att_assets if a.get("category") == "Aircraft")
    att_ground = sum(a.get("amount", 0) for a in att_assets if a.get("category") == "Ground Forces")

    att_tech_mult = 1.0 + (att_tech - 1) * 0.15
    att_app_mult = 0.85 + (att_app / 100.0) * 0.3
    att_readiness_mult = 0.80 + (att_readiness / 100.0) * 0.30

    if op_type == "air_missile":
        att_strike_power = (att_missiles * 1.5 + att_uavs * 0.8 + att_aircraft * 3.0) * att_tech_mult * att_app_mult * att_readiness_mult
    elif op_type == "ground_invasion":
        att_strike_power = (att_ground * 2.5 + att_aircraft * 1.5 + att_missiles * 1.0) * att_tech_mult * att_app_mult * att_readiness_mult
    else: # combined_arms
        att_strike_power = (att_ground * 2.0 + att_missiles * 1.5 + att_uavs * 1.0 + att_aircraft * 2.5) * att_tech_mult * att_app_mult * att_readiness_mult

    # کانال رهگیری ارزش‌محور: هر ۸ میلیون دلار سامانه پدافندی ~ یک کانال اثربخش
    # (باتری گنبد آهنین/پاتریوت ده‌ها کانال دارد، مپادس ارزان تقریباً هیچ در برابر موشک)
    def_ad_channels = 0.0
    _ad_types = 0
    for d in def_assets:
        if d.get("category") == "Air Defense":
            amt = d.get("amount", 0) or 0
            if amt > 0:
                _ad_types += 1
            price = d.get("buy_price", d.get("price", 0)) or 0
            def_ad_channels += amt * (price / 8_000_000.0)
    def_ad_channels += _ad_types * 2
    def_airdef = def_ad_channels
    def_aircraft = sum(d.get("amount", 0) for d in def_assets if d.get("category") == "Aircraft")
    def_uavs = sum(d.get("amount", 0) for d in def_assets if d.get("category") == "UAV")
    def_ground = sum(d.get("amount", 0) for d in def_assets if d.get("category") == "Ground Forces")

    def_tech_mult = 1.0 + (def_tech - 1) * 0.15
    def_app_mult = 0.85 + (def_app / 100.0) * 0.3
    def_readiness_mult = 0.80 + (def_readiness / 100.0) * 0.30

    if op_type == "air_missile":
        def_shield_power = (def_airdef * 15 + def_aircraft * 0.8) * def_tech_mult * def_app_mult * def_readiness_mult
    elif op_type == "ground_invasion":
        def_shield_power = (def_ground * 2.5 + def_airdef * 1.5) * def_tech_mult * def_app_mult * def_readiness_mult
    else: # combined_arms
        def_shield_power = (def_ground * 2.0 + def_airdef * 3.5 + def_aircraft * 1.5) * def_tech_mult * def_app_mult * def_readiness_mult

    base_ratio = def_shield_power / max(1.0, att_strike_power)
    tactical_variance = random.uniform(-0.10, 0.10)
    
    raw_intercept = 0.42 + (base_ratio - 0.8) * 0.25 + tactical_variance
    intercept_rate = round(max(0.20, min(0.85, raw_intercept)), 2)
    penetration_rate = round(1.0 - intercept_rate, 2)

    raw_att_risk = (def_shield_power / max(100.0, att_strike_power)) * 0.22 + random.uniform(-0.03, 0.03)
    att_risk_rate = round(max(0.04, min(0.50, raw_att_risk)), 2)

    return {
        "att_strike_power": int(att_strike_power),
        "def_shield_power": int(def_shield_power),
        "intercept_rate": intercept_rate,
        "penetration_rate": penetration_rate,
        "att_risk_rate": att_risk_rate,
        "def_airdef_qty": def_airdef,
        "def_tech": def_tech,
        "att_tech": att_tech
    }


def calculate_weapon_breakdown(att_losses, balance):
    """محاسبه تفکیکی شلیک، رهگیری پدافند و عبور موثر برای هر سلاح تهاجمی."""
    breakdown = []
    intercept_rate = balance.get("intercept_rate", 0.5)

    for item in att_losses:
        cat = item.get("category", "")
        # فقط پرتابه‌ها، موشک‌ها و پهپادهای انتحاری (بدون هواپیما، بالگرد و هواپیمای ترابری)
        if cat not in ["Missiles", "UAV"]:
            continue

        total_fired = item["amount"]
        name = item["equipment_name"]
        name_lower = name.lower()

        # استثنا کردن هواپیماها و بالگردهای شناسایی/ترابری که ممکن است در دسته UAV ثبت شده باشند
        if any(ex in name_lower for ex in ["c-130", "c-17", "awacs", "ترابری", "سوخت‌رسان", "بالگرد", "هواپیما"]):
            continue

        if any(k in name_lower for k in ["هایپرسونیک", "فتاح", "خیبرشکن", "fattah"]):
            weapon_intercept = max(0.10, intercept_rate - 0.25)
        elif any(k in name_lower for k in ["کروز", "پاوه", "هویزه", "سومار", "کالیبر"]):
            weapon_intercept = max(0.15, intercept_rate - 0.10)
        elif any(k in name_lower for k in ["پهپاد", "شاهد", "مهاجر", "geran", "uav", "انتحاری"]):
            weapon_intercept = min(0.88, intercept_rate + 0.10)
        else:
            weapon_intercept = intercept_rate

        intercepted = int(total_fired * weapon_intercept)
        penetrated = max(0, total_fired - intercepted)

        breakdown.append({
            "name": name,
            "total_fired": total_fired,
            "intercepted": intercepted,
            "penetrated": penetrated,
            "pen_pct": int((penetrated / max(1, total_fired)) * 100)
        })

    return breakdown


def generate_war_analysis_report(attacker_key: str, defender_key: str, attacker_role: str, defender_role: str = ""):
    """تولید گزارش هوشمند سناریوی نبرد بر اساس رول‌های واقعی دو طرف و موازنه قوا."""
    
    attacker_info = config.COUNTRIES.get(attacker_key, {})
    defender_info = config.COUNTRIES.get(defender_key, {})

    att_flag = attacker_info.get("flag", "")
    att_name = attacker_info.get("name", attacker_key)
    def_flag = defender_info.get("flag", "")
    def_name = defender_info.get("name", defender_key)

    # نسخه ۲: دیگر کشور فیک ساخته نمی‌شود؛ تحلیل کشورهای بدون بازیکن از کاتالوگ انجام
    # می‌شود و اعمال دیتابیسی تلفات فقط برای کشورهای بازیکن‌دار صورت می‌گیرد.
    att_country = db.get_country_by_key(attacker_key)
    def_country = db.get_country_by_key(defender_key)

    def _catalog_assets(key):
        out = []
        for it in config.COUNTRY_EQUIPMENT_CATALOG.get(key, []):
            out.append({
                "equipment_key": it.get("key"),
                "equipment_name": it.get("name"),
                "amount": it.get("initial", 50),
                "category": it.get("category", "Ground Forces"),
                "buy_price": it.get("price", 1_000_000),
            })
        return out

    att_cid = att_country["id"] if att_country else None
    def_cid = def_country["id"] if def_country else None

    if att_cid:
        db.seed_country_assets(att_cid, attacker_key)
        att_assets = db.get_country_assets(att_cid)
    else:
        att_assets = _catalog_assets(attacker_key)

    if def_cid:
        db.seed_country_assets(def_cid, defender_key)
        def_assets = db.get_country_assets(def_cid)
    else:
        def_assets = _catalog_assets(defender_key)

    op_type = detect_operation_type(attacker_key, defender_key, attacker_role, defender_role)

    balance = calculate_battle_balance(
        att_assets, def_assets,
        att_tech=att_country.get("tech_level", 1) if att_country else 1,
        def_tech=def_country.get("tech_level", 1) if def_country else 1,
        att_app=att_country.get("approval_rating", 80) if att_country else 80,
        def_app=def_country.get("approval_rating", 80) if def_country else 80,
        att_readiness=att_country.get("combat_readiness", 70) if att_country else 70,
        def_readiness=def_country.get("combat_readiness", 70) if def_country else 70,
        op_type=op_type
    )

    losses = calculate_simulated_losses(
        att_assets, def_assets, att_country, def_country, op_type,
        attacker_key, defender_key, attacker_role, defender_role, balance
    )

    # تعیین تلفات توسط هوش مصنوعی واقعی (اختیاری) — همیشه درون بازه‌های امن
    try:
        ai_loss = ai_war_losses(
            att_name, def_name, op_type, balance, att_assets, def_assets,
            losses.get("att_fired", []), attacker_role, defender_role, losses
        )
    except Exception:
        ai_loss = None
    if ai_loss:
        losses = apply_ai_loss_guardrails(losses, ai_loss, att_assets, def_assets)

    weapon_breakdown = calculate_weapon_breakdown(losses.get("att_fired") or losses["att_losses"], balance)

    # ۱. کارت خلاصه اصلی گزارش نبرد
    summary_text = build_war_summary_card(
        att_flag, att_name, def_flag, def_name, losses, balance, op_type
    )

    # ۲. متن گاه‌شماری نبرد (Timeline)
    timeline_text = build_war_timeline_text(
        att_flag, att_name, def_flag, def_name, balance, op_type, weapon_breakdown
    )

    # ۳. متن آسیب‌های زیرساختی و اهداف استراتژیک (Targets)
    targets_text = build_war_targets_text(
        att_flag, att_name, def_flag, def_name, balance, op_type
    )

    # ۴. متن تغییرات خطوط مرزی و جغرافیا (Territory)
    territory_text = build_war_territory_text(
        att_flag, att_name, def_flag, def_name, balance, op_type
    )

    # ۵. روایت هوش مصنوعی (اختیاری — در صورت وجود کلید API، جایگزین قالب‌های متنی می‌شود)
    try:
        ai_narr = ai_war_narrative(att_name, def_name, op_type, balance, losses, weapon_breakdown, attacker_role, defender_role)
    except Exception:
        ai_narr = None
    if ai_narr:
        if ai_narr.get("timeline"):
            timeline_text = ai_narr["timeline"]
        if ai_narr.get("targets"):
            targets_text = ai_narr["targets"]
        if ai_narr.get("territory"):
            territory_text = ai_narr["territory"]
        if ai_narr.get("assessment"):
            summary_text += f"\n\n■ *ارزیابی راهبردی کارشناسان:*\n> {str(ai_narr['assessment']).strip()}"

    # ۶. فاکتورهای تلفات
    receipt_att = build_detailed_loss_receipt(attacker_key, losses["att_losses"], losses["att_military_loss"], losses["att_civilian_loss"], "عملیات تهاجمی اخیر", is_attacker=True, op_type=op_type)
    receipt_def = build_detailed_loss_receipt(defender_key, losses["def_losses"], losses["def_military_loss"], losses["def_civilian_loss"], "عملیات دفاعی اخیر", is_attacker=False, op_type=op_type)

    losses_json = json.dumps({
        "att_key": attacker_key,
        "def_key": defender_key,
        "losses": losses,
        "receipt_att": receipt_att,
        "receipt_def": receipt_def,
        "op_type": op_type,
        "targets_text": targets_text
    })

    # ذخیره در دیتابیس جهت فعال‌سازی دکمه‌های شیشه‌ای تعاملی
    war_id = 0
    if att_cid and def_cid:
        war_id = db.save_war_result(
            att_cid, def_cid, op_type,
            summary_text, timeline_text, targets_text, territory_text, losses_json
        )
    else:
        summary_text += "\n\nℹ️ _یکی از طرف‌های نبرد کشور بازیکن‌دار نیست؛ اعمال دیتابیسی تلفات فقط برای کشورهای دارای بازیکن انجام می‌شود._"

    return summary_text, losses, war_id, timeline_text, targets_text, territory_text


_LAST_GOOD_AI_MODEL = None


def ai_war_narrative(att_name, def_name, op_type, balance, losses, weapon_breakdown, attacker_role, defender_role):
    """روایت گزارش نبرد با هوش مصنوعی واقعی (اختیاری).

    نیازمند یکی از کلیدهای OPENAI_API_KEY / AI_API_KEY / OPENROUTER_API_KEY در متغیرهای محیطی.
    اعداد قطعی نبرد همیشه توسط موتور داخلی تولید می‌شوند؛ هوش مصنوعی فقط «روایت» سه بخش
    گاه‌شماری، آسیب زیرساختی و خطوط مرزی را می‌نویسد. در صورت خطا None برمی‌گردد و
    قالب‌های داخلی جایگزین می‌شوند.
    """
    openai_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("AI_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    api_key = openai_key or openrouter_key
    if not api_key:
        return None

    if not openai_key and openrouter_key:
        api_base = "https://openrouter.ai/api/v1"
        model_candidates = [
            os.environ.get("AI_MODEL") or "z-ai/glm-5.2:free",
            "openai/gpt-oss-20b:free",
            "google/gemma-4-31b-it:free",
            "nvidia/nemotron-3-super-120b-a12b:free",
        ]
    else:
        api_base = "https://api.openai.com/v1"
        model_candidates = [os.environ.get("AI_MODEL") or "gpt-4o-mini"]

    op_labels = {
        "combined_arms": "عملیات ترکیبی (زمینی + موشکی/هوایی)",
        "ground_invasion": "تهاجم زمینی",
        "air_missile": "حمله موشکی/پهپادی/هوایی",
    }

    wb_summary = "\n".join(
        f"- {wb['name']}: شلیک {wb['total_fired']}, رهگیری {wb['intercepted']}, عبور {wb['penetrated']}"
        for wb in (weapon_breakdown or [])
    ) or "- (بدون تفکیک)"
    att_fired = ", ".join(f"{x['equipment_name']} ×{x['amount']}" for x in losses.get("att_fired", [])[:14]) or "-"
    def_fired = ", ".join(f"{x['equipment_name']} ×{x['amount']}" for x in losses.get("def_fired", [])[:14]) or "-"

    prompt = f"""شما یک تحلیلگر ارشد نظامی هستید. بر اساس «اعداد قطعی» زیر، گزارش کارشناسی فارسی بنویس.
اعداد را هرگز تغییر نده یا جدید از خودت نساز؛ فقط روایت کن. لحن رسمی، فاخر و بدون ایموجی اضافی.
قواعد الزامی زبان: فقط و فقط فارسی روان و رسمی؛ به کار بردن هر واژه انگلیسی/لاتین ممنوع است و به جای آن معادل فارسی دقیق بنویس.

نبرد: {att_name} علیه {def_name} — نوع: {op_labels.get(op_type, op_type)}
نرخ عبور پرتابه‌ها: {int(balance['penetration_rate']*100)}٪ | نرخ رهگیری پدافند: {int(balance['intercept_rate']*100)}٪
تلفات نظامی مهاجم: {losses['att_military_loss']:,} | مدافع: {losses['def_military_loss']:,} | غیرنظامی مدافع: {losses['def_civilian_loss']:,}
تفکیک شلیک/رهگیری:
{wb_summary}
نیروهای درگیر مهاجم: {att_fired}
نیروهای درگیر مدافع: {def_fired}
خلاصه رول مهاجم (حداکثر ۸۰۰ کلمه):
{(attacker_role or '')[:1500]}
خلاصه رول مدافع:
{(defender_role or '')[:800] or '(مدافع رولی نفرستاده است)'}

تلفات نهایی ثبت‌شده (این اعداد قطعی هستند و باید در روایت منعکس شوند):
- مهاجم: {losses.get('att_military_loss', 0):,} نظامی
- مدافع: {losses.get('def_military_loss', 0):,} نظامی و {losses.get('def_civilian_loss', 0):,} غیرنظامی
- تجهیزات منهدم‌شده مدافع: {", ".join(f"{x['equipment_name']} ({x['amount']} عدد)" for x in losses.get('def_losses', [])[:10]) or '-'}

قواعد نگارش: هر بخش را با عنوان «■ *عنوان:*» شروع کن و جزئیات را با «> » بیاور (مطابق قالب بازی). فقط فارسی روان و رسمی.

فقط و فقط یک JSON معتبر با این ساختار بازگردان (بدون هیچ توضیح اضافی):
{{"timeline": "متن گاه‌شماری نبرد با ساعت‌های فرضی متفاوت (۸ تا ۱۲ سطر)", "targets": "متن آسیب‌های زیرساختی و اهداف استراتژیک متناسب با نرخ عبور (۶ تا ۹ سطر)", "territory": "متن وضعیت خطوط مرزی و عمق پیشروی متناسب با نوع عملیات و نرخ عبور (۴ تا ۶ سطر)", "assessment": "ارزیابی راهبردی کوتاه دو تا سه سطری درباره پیامد این نبرد برای معادلات منطقه‌ای"}}"""

    global _LAST_GOOD_AI_MODEL
    if _LAST_GOOD_AI_MODEL and _LAST_GOOD_AI_MODEL in model_candidates:
        model_candidates = [_LAST_GOOD_AI_MODEL] + [m for m in model_candidates if m != _LAST_GOOD_AI_MODEL]

    for model_name in model_candidates:
        try:
            data = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You are a senior military analyst writing formal Persian battle reports. Always answer with strict JSON only."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
            }
            req = urllib.request.Request(
                api_base + "/chat/completions",
                data=json.dumps(data).encode("utf-8"),
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=20) as response:
                res = json.loads(response.read().decode("utf-8"))
            content = res["choices"][0]["message"]["content"].strip()
            # حذف بلوک کد احتمالی و استخراج مقاوم JSON
            if content.startswith("```"):
                content = content.strip("`").lstrip("json").strip()
            try:
                parsed = json.loads(content)
            except Exception:
                m_json = re.search(r"\{.*\}", content, re.S)
                parsed = json.loads(m_json.group(0)) if m_json else None
            if isinstance(parsed, dict) and parsed.get("timeline"):
                _LAST_GOOD_AI_MODEL = model_name
                return parsed
        except Exception as e:
            print(f"AI war narrative error ({model_name}, trying next): {e}")
            continue
    return None


def apply_ai_loss_guardrails(base: dict, ai: dict, att_assets, def_assets) -> dict:
    """اعمال تلفات پیشنهادی هوش مصنوعی درون بازه‌های امن.

    موتور بازی baseline می‌سازد؛ هوش مصنوعی اعداد را با خواندن رول واقعی دو طرف
    واقعی‌تر تنظیم می‌کند و این تابع خروجی را به بازه‌های منطقی محدود می‌کند تا
    خطای مدل هرگز اقتصاد بازی را نابود نکند.
    """
    def clamp(v, lo, hi):
        try:
            v = int(v)
        except (TypeError, ValueError):
            return lo
        return max(lo, min(hi, v))

    out = dict(base)
    out["att_military_loss"] = clamp(ai.get("att_military_loss", base["att_military_loss"]), 0, base["att_military_loss"] * 3 + 50)
    out["def_military_loss"] = clamp(ai.get("def_military_loss", base["def_military_loss"]), int(base["def_military_loss"] * 0.4), base["def_military_loss"] * 3 + 200)
    out["att_civilian_loss"] = clamp(ai.get("att_civilian_loss", 0), 0, base["att_civilian_loss"] * 3 + 30)
    out["def_civilian_loss"] = clamp(ai.get("def_civilian_loss", 0), 0, base["def_civilian_loss"] * 4 + 60)

    def fix_equipment(ai_list, base_list, assets, is_attacker):
        stock, info = {}, {}
        for a in assets:
            k = a.get("equipment_key") or a.get("key")
            if k:
                stock[k] = a.get("amount", a.get("initial", 0)) or 0
                info[k] = (
                    a.get("equipment_name") or a.get("name") or k,
                    a.get("category", ""),
                    a.get("buy_price", a.get("price", 1_000_000)) or 1_000_000,
                )
        base_map = {x["equipment_key"]: x["amount"] for x in base_list}
        out_list = []
        # مصرف پرتابه‌های مهاجم (موشک/پهپاد) فیزیک عملیات است و دست‌نخورده می‌ماند
        if is_attacker:
            for x in base_list:
                if x.get("category") in ("Missiles", "UAV"):
                    out_list.append(dict(x))
        for it in (ai_list or []):
            k = it.get("key") or it.get("equipment_key")
            try:
                amt = int(it.get("amount", 0))
            except (TypeError, ValueError):
                continue
            if not k or k not in stock or amt <= 0:
                continue
            name, cat, price = info[k]
            if is_attacker and cat in ("Missiles", "UAV"):
                continue
            cap = min(stock[k], max(int(stock[k] * 0.35), base_map.get(k, 0) * 3, 3))
            amt = max(1, min(amt, cap))
            out_list.append({"equipment_key": k, "equipment_name": name, "amount": amt, "category": cat, "price": price})
        if not out_list:
            out_list = [dict(x) for x in base_list]
        return out_list

    out["att_losses"] = fix_equipment(ai.get("att_losses"), base["att_losses"], att_assets, True)
    out["def_losses"] = fix_equipment(ai.get("def_losses"), base["def_losses"], def_assets, False)
    return out


def ai_war_losses(att_name, def_name, op_type, balance, att_assets, def_assets, att_fired, attacker_role, defender_role, base_losses):
    """تعیین تلفات نبرد توسط هوش مصنوعی واقعی (اختیاری — همان زنجیره مدل‌ها).

    موتور بازی baseline تولید می‌کند؛ هوش مصنوعی با خواندن رول‌های واقعی دو طرف،
    اعداد را واقعی‌تر تنظیم می‌کند. خروجی همیشه از apply_ai_loss_guardrails عبور می‌کند.
    در نبود کلید یا خطا None برمی‌گردد و baseline باقی می‌ماند.
    """
    openai_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("AI_API_KEY")
    openrouter_key = os.environ.get("OPENROUTER_API_KEY")
    api_key = openai_key or openrouter_key
    if not api_key:
        return None
    if not openai_key and openrouter_key:
        api_base = "https://openrouter.ai/api/v1"
        model_candidates = [
            os.environ.get("AI_MODEL") or "z-ai/glm-5.2:free",
            "openai/gpt-oss-20b:free",
            "google/gemma-4-31b-it:free",
            "nvidia/nemotron-3-super-120b-a12b:free",
        ]
    else:
        api_base = "https://api.openai.com/v1"
        model_candidates = [os.environ.get("AI_MODEL") or "gpt-4o-mini"]

    def summarize(assets, limit):
        items = sorted(assets, key=lambda a: -(a.get("amount", a.get("initial", 0)) or 0))
        return "\n".join(
            f"{(a.get('equipment_key') or a.get('key'))}: {(a.get('equipment_name') or a.get('name') or '')[:28]} | {a.get('category', '')} | موجودی {max(1, (a.get('amount', a.get('initial', 0)) or 0)):,}"
            for a in items[:limit]
        )

    fired_str = ", ".join(f"{x['equipment_name']}×{x['amount']}" for x in (att_fired or [])[:16]) or "-"

    prompt = f"""شما تحلیلگر ارشد نظامی هستید. بر اساس رول‌های واقعی دو طرف، تلفات نهایی این نبرد را تعیین کن.

نبرد: {att_name} (مهاجم) علیه {def_name} (مدافع) | نرخ عبور پرتابه‌ها: {int(balance['penetration_rate']*100)}٪ | نرخ رهگیری: {int(balance['intercept_rate']*100)}٪

نیروهای درگیر مهاجم (در رول ذکر شده): {fired_str}
موجودی کلیدی مهاجم:
{summarize(att_assets, 14)}
موجودی کلیدی مدافع:
{summarize(def_assets, 22)}

رول مهاجم (خلاصه):
{(attacker_role or '')[:1400]}
رول مدافع (خلاصه):
{(defender_role or '')[:600]}

برآورد اولیه موتور بازی (پایه و میزان):
- تلفات نظامی مهاجم: {base_losses['att_military_loss']:,} | مدافع: {base_losses['def_military_loss']:,}
- غیرنظامی (مدافع): {base_losses['def_civilian_loss']:,}
- تجهیزات مهاجم (کلید: مقدار): {', '.join(f"{x['equipment_key']}:{x['amount']}" for x in base_losses['att_losses'][:14]) or '-'}
- تجهیزات مدافع (کلید: مقدار): {', '.join(f"{x['equipment_key']}:{x['amount']}" for x in base_losses['def_losses'][:18]) or '-'}

قواعد الزامی:
- فقط از کلیدهای تجهیزات داده‌شده استفاده کن و از موجودی بیشتر کسر نکن.
- مصرف موشک/پهپاد مهاجم قبلاً ثابت شده؛ آن را تغییر نده (فقط تلفات تجهیزات دیگر و انسانی).
- تلفات باید با شدت عملیات، نرخ عبور و نسبت قوا سازگار و واقع‌گرایانه باشد.
- همه اعداد صحیح و غیرمنفی.

فقط و فقط JSON معتبر بازگردان:
{{"att_military_loss": 0, "att_civilian_loss": 0, "def_military_loss": 0, "def_civilian_loss": 0,
 "att_losses": [{{"key": "...", "amount": 0}}], "def_losses": [{{"key": "...", "amount": 0}}]}}"""

    global _LAST_GOOD_AI_MODEL
    if _LAST_GOOD_AI_MODEL and _LAST_GOOD_AI_MODEL in model_candidates:
        model_candidates = [_LAST_GOOD_AI_MODEL] + [m for m in model_candidates if m != _LAST_GOOD_AI_MODEL]

    for model_name in model_candidates:
        try:
            data = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": "You are a rigorous military casualty analyst. Always answer with strict JSON only."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.55,
            }
            req = urllib.request.Request(
                api_base + "/chat/completions",
                data=json.dumps(data).encode("utf-8"),
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=25) as response:
                res = json.loads(response.read().decode("utf-8"))
            content = res["choices"][0]["message"]["content"].strip()
            if content.startswith("```"):
                content = content.strip("`").lstrip("json").strip()
            parsed = json.loads(content)
            if isinstance(parsed, dict) and ("def_military_loss" in parsed or "def_losses" in parsed):
                _LAST_GOOD_AI_MODEL = model_name
                return parsed
        except Exception as e:
            print(f"AI war losses error ({model_name}, trying next): {e}")
            continue
    return None


def build_war_summary_card(att_flag, att_name, def_flag, def_name, losses, balance, op_type):
    """کارت خلاصه اصلی سناریوی نبرد."""
    op_labels = {
        "combined_arms": "عملیات ترکیبی (تهاجم زمینی + موشکی/هوایی)",
        "ground_invasion": "تهاجم زمینی و نبرد مرزی",
        "air_missile": "حمله موشکی، پهپادی و هوایی"
    }

    pen_pct = int(balance["penetration_rate"] * 100)
    intercept_pct = int(balance["intercept_rate"] * 100)

    lines = []
    lines.append(f"⚔️ *گزارش ارزیابی نبرد ژئوپلیتیک — {att_flag} {att_name} در برابر {def_flag} {def_name}*")
    lines.append(f"پرونده: {op_labels.get(op_type, op_type)}")
    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *خلاصه نتایج نبرد:*")
    lines.append(f"• **نرخ عبور پرتابه‌ها/اصابت:** {pen_pct}٪")
    lines.append(f"• **نرخ رهگیری پدافند:** {intercept_pct}٪")
    lines.append(f"• **تلفات نیروهای مسلح {att_name}:** {losses['att_military_loss']:,} نفر")
    lines.append(f"• **تلفات نیروهای مسلح {def_name}:** {losses['def_military_loss']:,} نفر")
    lines.append(f"• **تلفات غیرنظامی:** {losses['def_civilian_loss']:,} نفر\n")

    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append("👇 *جهت مشاهده جزئیات کامل، روی دکمه‌های شیشه‌ای زیر کلیک کنید:*")

    return "\n".join(lines)


def build_war_timeline_text(att_flag, att_name, def_flag, def_name, balance, op_type, weapon_breakdown):
    """متن گاه‌شماری نبرد (Timeline) — نسخه ۲: ساعت‌ها و توصیف‌ها بر اساس داده نبرد متغیرند."""
    intercept_pct = int(balance["intercept_rate"] * 100)
    pen_pct = int(balance["penetration_rate"] * 100)

    systems = len(weapon_breakdown) if weapon_breakdown else 0
    total_fired = sum(wb.get("total_fired", 0) for wb in weapon_breakdown) if weapon_breakdown else 0

    h0 = random.choice([22, 23, 0, 1, 2, 3])
    def hh(h):
        return f"{(h % 24):02d}:{random.choice(['05', '12', '20', '31', '40', '47', '55'])}"

    lines = []
    lines.append(f"📋 *گاه‌شماری و شرح مراحل درگیری — {att_flag} {att_name} و {def_flag} {def_name}*")
    lines.append("━━━━━━━━━━━━━━━━━━\n")

    openers = [
        f"⏱️ **ساعت {hh(h0)} — آغاز عملیات و جنگ الکترونیک:**",
        f"⏱️ **ساعت {hh(h0)} — فعال‌سازی میدان مین دیجیتال و اخلال ارتباطی:**",
        f"⏱️ **ساعت {hh(h0)} — موج اول جنگ الکترونیک و سایبری:**",
    ]
    lines.append(random.choice(openers))
    lines.append(f"> اختلال در رادارها و شبکه مخابراتی {def_name} در ساعات نخست به ثبت رسید.\n")

    if op_type in ["combined_arms", "air_missile"]:
        lines.append(f"⏱️ **ساعت {hh(h0 + random.randint(1, 2))} — موج اول ضربات موشکی و هوایی:**")
        if systems:
            lines.append(f"> درگیری {systems} نوع سامانه تهاجمی {att_name}" + (f" با مجموع {total_fired:,} پرتابه" if total_fired else "") + ".")
        else:
            lines.append(f"> شلیک موج اول پرتابه‌ها به سمت پایگاه‌ها و رادارهای {def_name}.")
        lines.append(f"> _پاسخ پدافندی:_ شبکه پدافند چندلایه {def_name} موفق به انهدام {intercept_pct}٪ پرتابه‌ها شد و {pen_pct}٪ عبور کردند.\n")

    if op_type in ["combined_arms", "ground_invasion"]:
        lines.append(f"⏱️ **ساعت {hh(h0 + random.randint(3, 5))} — عبور ستون‌های زرهی از خط آبی:**")
        lines.append(f"> حرکت تانک‌ها و نفربرهای {att_name} در محورهای موازی با پشتیبانی آتش مستقیم.")
        lines.append(f"> مواجهه با کمین‌های ضدزره و پهپادهای انتحاری FPV مدافع در عمق {random.randint(2, 9)} کیلومتری مرز.\n")
        lines.append(f"⏱️ **ساعت {hh(h0 + random.randint(7, 12))} — سازماندهی مجدد خطوط:**")
        lines.append(f"> ورود یگان‌های ذخیره، پاکسازی تونل‌ها و تثبیت نسبی خطوط تماس جدید.\n")

    lines.append(f"⏱️ **ساعت {hh(h0 + random.randint(13, 18))} — کاهش شدت درگیری و ارزیابی اولیه:**")
    lines.append(f"> هر دو طرف به مواضع فعلی عقب‌نشینی تاکتیکی کردند و آتش‌بس‌های موضعی برقرار شد.")

    lines.append("━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


def build_war_targets_text(att_flag, att_name, def_flag, def_name, balance, op_type):
    """متن آسیب‌های زیرساختی و اهداف استراتژیک (Strategic Targets)."""
    pen_pct = int(balance["penetration_rate"] * 100)

    lines = []
    lines.append(f"💥 *ارزیابی آسیب‌های زیرساختی و اهداف استراتژیک {def_flag} {def_name}*")
    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *اهداف اصابت‌شده و برآورد آسیب‌ها:*\n")

    if pen_pct > 50:
        lines.append(f"• **پایگاه‌های هوایی و باندهای پرواز:** خسارت سنگین به سوله‌های نگهداری جنگنده‌ها و خزانه‌های سوخت {def_name}.")
        lines.append(f"• **پالایشگاه‌ها و تاسیسات نفتی:** ایجاد آتش‌سوزی در بخش فرآوری و کاهش موقت نرخ تولید نفت.")
        lines.append(f"• **شبکه برق و نیروگاه‌ها:** اخلال در پست‌های انتقال برق و قطعی موقت در منطقه درگیری.")
        lines.append(f"• **سامانه‌های راداری و C4I:** تخریب رادارهای هشدار زودهنگام و اخلال در شبکه ارتباطی.")
    elif pen_pct > 25:
        lines.append(f"• **پایگاه‌های هوایی:** خسارت متوسط به سوله‌های پشتیبانی {def_name}.")
        lines.append(f"• **سامانه‌های پدافند هوایی:** مصرف بخش قابل‌توجهی از موشک‌های ذخیره رهگیر.")
        lines.append(f"• **مراکز ارتباطی:** اختلال کوتاه‌مدت در شبکه اطلاعاتی.")
    else:
        lines.append(f"• **خسارات محدود زیرساختی:** اکثر پرتابه‌ها توسط پدافند هوایی {def_name} در آسمان منهدم شدند.")
        lines.append(f"• **مصرف ذخایر پدافند:** فشار سنگین بر ذخایر موشک‌های رهگیر مدافع.")

    lines.append("\n━━━━━━━━━━━━━━━━━━")

    return "\n".join(lines)


def build_war_territory_text(att_flag, att_name, def_flag, def_name, balance, op_type):
    """متن تغییرات خطوط مرزی (Territory) — نسخه ۲: عمق پیشروی از موازنه واقعی نبرد محاسبه می‌شود."""
    pen = balance.get("penetration_rate", 0.5)
    pen_pct = int(pen * 100)

    lines = []
    lines.append(f"🗺️ *وضعیت خطوط تماس مرزی و جغرافیا — نبرد {att_name} و {def_name}*")
    lines.append("━━━━━━━━━━━━━━━━━━\n")

    if op_type in ["combined_arms", "ground_invasion"]:
        depth = int(3 + pen * 27)
        depth_max = int(depth * random.uniform(1.5, 2.1))
        lines.append("■ *تغییرات مواضع و عمق پیشروی:*\n")
        lines.append(f"• **عمق نفوذ ثبت‌شده:** خط تماس جدید در بستر {depth} الی {depth_max} کیلومتری خاک {def_name} ترسیم شد (نرخ عبور مؤثر: {pen_pct}٪).")
        if pen >= 0.6:
            lines.append(f"• **وضعیت محورها:** {att_name} تقاطع‌ها و ارتفاعات کلیدی را در اختیار دارد؛ مقاومت سازمان‌یافته {def_name} محدود به کانون‌های مقاومت پراکنده است.")
            lines.append("• **پایداری خط مقدم:** تثبیت تدارکاتی در جریان است و مسیرهای لجستیک عمقی در حال گشایش‌اند.")
        elif pen >= 0.35:
            lines.append(f"• **وضعیت محورها:** پیشروی {att_name} در ۲ محور اصلی متوقف و به جنگ فرسایشی خط تماس تبدیل شده است.")
            lines.append("• **پایداری خط مقدم:** ناپایدار؛ هر دو طرف تحملات سنگین در تبادل آتش ثبت می‌کنند.")
        else:
            lines.append(f"• **وضعیت محورها:** پیشروی {att_name} با آتش متمرکز پدافندی {def_name} شکست خورد و ستون‌های زرهی به خط آبی عقب رانده شدند.")
            lines.append("• **پایداری خط مقدم:** خطوط مرزی عملاً به وضعیت پیش از جنگ بازگشته است.")
    else:
        lines.append("■ *وضعیت خطوط مرزی:*\n")
        variants = [
            "• **تغییرات مرزی:** به دلیل اجرای کامل عملیات در قالب حملات موشکی، پهپادی و هوایی دوربرد، هیچ تغییر ارضی به ثبت نرسید.",
            f"• **حریم هوایی:** آسمان منطقه محل درگیری شدید؛ {def_name} پوشش راداری را به حالت پراکنده درآورده است.",
            "• **خطوط زمینی:** بدون تماس مستقیم نیروهای زمینی؛ محدود به تبادل آتش دوربرد و عملیات ویژه محدود.",
        ]
        lines.extend(random.sample(variants, k=min(2, len(variants))))

    lines.append("\n━━━━━━━━━━━━━━━━━━")
    return "\n".join(lines)


def calculate_simulated_losses(att_assets, def_assets, att_country, def_country, op_type, attacker_key, defender_key, attacker_role="", defender_role="", balance=None):
    """محاسبه هوشمند و واقعی تلفات انسانی و تجهیزاتی با احتساب موازنه قوا و استخراج رول."""
    
    att_tech = att_country.get("tech_level", 1) if att_country else 1
    def_tech = def_country.get("tech_level", 1) if def_country else 1

    if not balance:
        balance = calculate_battle_balance(att_assets, def_assets, att_tech, def_tech, op_type=op_type)

    # ---------- موتور تبدیل «تسلیحات درگیر» به «تلفات واقعی» (نسخه ۲) ----------
    # موشک و پهپادِ شلیک‌شده کامل مصرف می‌شوند؛ اما تانک/جنگنده/پدافند فقط درصدی تلفات می‌دهند
    def compute_actual_losses(engaged_list, is_attacker, balance):
        att_risk = balance.get("att_risk_rate", 0.1)
        pen_rate = balance.get("penetration_rate", 0.5)
        if is_attacker:
            air_rate = max(0.02, min(0.12, att_risk * 0.25))
            other_rate = max(0.03, min(0.15, att_risk * 0.35))
        else:
            air_rate = max(0.02, min(0.10, pen_rate * 0.12))
            other_rate = max(0.02, min(0.12, pen_rate * 0.15))
        result = []
        for it in engaged_list:
            cat = it.get("category", "Ground Forces")
            used = it.get("amount", 0)
            if cat in ("Missiles", "UAV"):
                loss_qty = used
            elif cat == "Aircraft":
                loss_qty = int(round(used * air_rate))
                if used >= 5:
                    loss_qty = max(loss_qty, 1)
            else:
                rate = other_rate
                # نبرد زمینی سنگین: ستون‌های زرهی و توپخانه همیشه تلفات محسوسی می‌دهند
                if op_type in ("ground_invasion", "combined_arms") and cat in ("Ground Forces", "Artillery"):
                    rate = max(rate, 0.06)
                loss_qty = int(round(used * rate))
                if used >= 10:
                    loss_qty = max(loss_qty, 1)
            if loss_qty > 0:
                result.append({
                    "equipment_key": it["equipment_key"], "equipment_name": it["equipment_name"],
                    "amount": loss_qty, "category": cat, "price": it.get("price", 0)
                })
        return result

    def pick_engaged_from_assets(assets_list, op_type):
        """انتخاب تصادفی تسلیحات درگیر وقتی رول بازیکن مقدار دقیق نداده است."""
        by_cat = {}
        for item in assets_list:
            eq_key = item.get("equipment_key") or item.get("key")
            eq_name = item.get("equipment_name") or item.get("name")
            cat = item.get("category", "Ground Forces")
            amount = item.get("amount", item.get("initial", 50))
            buy_price = item.get("buy_price", item.get("price", 1_000_000))
            if eq_key and amount > 0:
                by_cat.setdefault(cat, []).append({
                    "equipment_key": eq_key, "equipment_name": eq_name,
                    "amount": amount, "category": cat, "price": buy_price
                })
        result = []
        strike_cats = ["Missiles", "UAV"] if op_type == "air_missile" else ["Missiles", "UAV", "Aircraft", "Ground Forces", "Artillery"]
        for cat in strike_cats:
            items = by_cat.get(cat)
            if not items:
                continue
            for it in random.sample(items, min(len(items), random.randint(1, 3))):
                fired_qty = max(1, min(it["amount"], random.randint(2, 12)))
                result.append({
                    "equipment_key": it["equipment_key"], "equipment_name": it["equipment_name"],
                    "amount": fired_qty, "category": cat, "price": it["price"]
                })
        return result

    att_fired = parse_weapon_mentions_from_roleplay_text(attacker_role, att_assets, attacker_key) or pick_engaged_from_assets(att_assets, op_type)
    att_losses = compute_actual_losses(att_fired, True, balance)

    def_fired = parse_weapon_mentions_from_roleplay_text(defender_role, def_assets, defender_key) or pick_engaged_from_assets(def_assets, op_type)
    def_losses = compute_actual_losses(def_fired, False, balance)

    tech_diff = att_tech - def_tech
    pen_rate = balance.get("penetration_rate", 0.5)

    # تلفات انسانی متناسب با اندازه ارتش (کشورهای پرنفراتر تلفات بیشتری می‌دهند)
    att_army = (att_country or {}).get("active_personnel", 200_000)
    def_army = (def_country or {}).get("active_personnel", 200_000)
    att_scale = max(0.5, min(4.0, att_army / 200_000))
    def_scale = max(0.5, min(4.0, def_army / 200_000))

    if op_type == "air_missile":
        att_military_loss = max(0, int(random.randint(0, 15) * balance.get("att_risk_rate", 0.1) * att_scale))
        att_civilian_loss = 0
        def_military_loss = max(5, int((random.randint(20, 80) * pen_rate + tech_diff * 4) * def_scale))
        def_civilian_loss = max(0, int(random.randint(2, 25) * pen_rate))
    elif op_type == "combined_arms":
        att_military_loss = max(120, int((random.randint(250, 680) - tech_diff * 20) * att_scale))
        att_civilian_loss = max(0, random.randint(5, 30))
        def_military_loss = max(180, int((random.randint(380, 950) * pen_rate + tech_diff * 30) * def_scale))
        def_civilian_loss = max(10, int(random.randint(25, 90) * pen_rate))
    else: # ground_invasion
        att_military_loss = max(100, int((random.randint(200, 550) - tech_diff * 15) * att_scale))
        att_civilian_loss = max(0, random.randint(5, 25))
        def_military_loss = max(150, int((random.randint(300, 800) * pen_rate + tech_diff * 25) * def_scale))
        def_civilian_loss = max(10, int(random.randint(20, 80) * pen_rate))

    # ---------- نسخه ۷.۲: خسارت مدافع متناسب با قدرت ضربتی نفوذکرده‌ی مهاجم ----------
    try:
        ratio = balance.get("att_strike_power", 1) / max(1.0, balance.get("def_shield_power", 1))
        power_mult = 1.0 + min(4.0, ratio / 2.0)

        pen_units = 0
        for _it in att_fired:
            pen_units += (_it.get("amount", 0) or 0) * pen_rate

        # ۱) تلفات انسانی اضافه‌ی مدافع از آتش نفوذکرده
        if op_type in ("ground_invasion", "combined_arms"):
            extra_personnel = int(pen_units * random.uniform(1.2, 2.4) * power_mult)
        else:
            extra_personnel = int(pen_units * random.uniform(0.8, 1.6) * power_mult)
        def_military_loss += min(35_000, extra_personnel)

        # ۲) بودجه انهدام تجهیزات مدافع بر اساس شدت ضربه
        destroy_budget = int(pen_units * random.uniform(0.08, 0.16) * power_mult)
        if destroy_budget > 0 and def_assets:
            priority = {"Air Defense": 0.40, "Ground Forces": 0.25, "Artillery": 0.20, "UAV": 0.10, "Missiles": 0.05}
            pools = {}
            for item in def_assets:
                cat = item.get("category")
                amt = item.get("amount", item.get("initial", 0)) or 0
                if cat in priority and amt > 0:
                    pools.setdefault(cat, []).append((item, amt))
            for cat, share in priority.items():
                budget = int(destroy_budget * share)
                if budget <= 0 or cat not in pools:
                    continue
                cat_pool = pools[cat][:]
                random.shuffle(cat_pool)
                for item, amt in cat_pool:
                    if budget <= 0:
                        break
                    max_kill = max(1, int(amt * 0.30))  # هر آیتم حداکثر ۳۰٪ موجودی‌اش آسیب می‌بیند
                    kill = min(budget, max_kill)
                    k = item.get("equipment_key") or item.get("key")
                    nm = item.get("equipment_name") or item.get("name") or k
                    pr = item.get("buy_price", item.get("price", 1_000_000)) or 1_000_000
                    existing = next((x for x in def_losses if x["equipment_key"] == k), None)
                    if existing:
                        existing["amount"] = max(existing["amount"], kill)
                    else:
                        def_losses.append({
                            "equipment_key": k, "equipment_name": nm,
                            "amount": kill, "category": cat, "price": pr,
                        })
                    budget -= kill
    except Exception as _e:
        print(f"defender damage scaling error: {_e}")

    return {
        "att_losses": att_losses,
        "def_losses": def_losses,
        "att_fired": att_fired,
        "def_fired": def_fired,
        "att_military_loss": att_military_loss,
        "att_civilian_loss": att_civilian_loss,
        "def_military_loss": def_military_loss,
        "def_civilian_loss": def_civilian_loss,
    }


def build_detailed_loss_receipt(country_key: str, item_losses: list, military_loss: int, civilian_loss: int, operation_name: str = "عملیات اخیر", is_attacker: bool = False, op_type: str = "air_missile"):
    """تولید فاکتور دقیق تلفات و کاهش تجهیزات با لحن رسمی و بدون ایموجی اضافی."""
    
    c_info = config.COUNTRIES.get(country_key, {})
    c_flag = c_info.get("flag", "")
    c_name = c_info.get("name", country_key)

    country = db.get_country_by_key(country_key)
    # نسخه ۲: ساخت کشور فیک ممنوع؛ برای کشورهای بدون بازیکن از کاتالوگ استفاده می‌شود

    cid = country["id"] if country else None
    if cid:
        db.seed_country_assets(cid, country_key)
        db_assets = {a["equipment_key"]: a for a in db.get_country_assets(cid)}
    else:
        db_assets = {}

    catalog = config.COUNTRY_EQUIPMENT_CATALOG.get(country_key, [])
    catalog_map = {item["key"]: item for item in catalog}

    def get_subcat_info(eq_name, category):
        eq_lower = eq_name.lower()
        if category == "Aircraft":
            if any(k in eq_lower for k in ["c-130", "c-17", "c-390", "a400m", "e-2", "e-3", "e-7", "awacs", "ترابری", "سوخت‌رسان", "p-8", "p-3"]):
                return ("Aircraft_Support", "هواپیماهای پشتیبانی و ترابری", "فروند")
            elif any(k in eq_lower for k in ["heli", "apache", "blackhawk", "black hawk", "chinook", "cougar", "tiger", "nh90", "شینوک", "طوفان", "بالگرد", "ka-52", "mi-28", "mi-35"]):
                return ("Helicopter", "هوانیروز و بالگردها", "فروند")
            else:
                return ("Aircraft_Fighter", "نیروی هوایی و جنگنده‌ها", "فروند")
        elif category == "UAV":
            return ("UAV", "پهپادها", "فروند")
        elif category == "Ground Forces":
            return ("Ground Forces", "نیروی زمینی و زرهی", "دستگاه")
        elif category == "Artillery":
            return ("Artillery", "توپخانه و راکت‌انداز", "سامانه")
        elif category == "Navy":
            return ("Navy", "نیروی دریایی و شناورها", "فروند")
        elif category == "Missiles":
            return ("Missiles", "توان موشکی و بالستیک", "فروند")
        elif category == "Air Defense":
            return ("Air Defense", "سامانه‌های پدافند هوایی", "سامانه/آتشبار")
        else:
            return (category, category, "واحد")

    title_label = "مصرف‌شده/شلیک‌شده" if (is_attacker and op_type == "air_missile") else "تلفات و کاهش تجهیزات"
    lines = []
    lines.append(f"*{title_label} {c_flag} {c_name} — «{operation_name}»*")
    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *تلفات انسانی:*")
    lines.append(f"> • پرسنل نظامی: {military_loss:,} نفر")
    lines.append(f"> • تلفات غیرنظامی: {civilian_loss:,} نفر\n")
    lines.append("━━━━━━━━━━━━━━━━━━\n")

    grouped = {}
    total_usd_damage = 0

    for loss in item_losses:
        eq_key = loss["equipment_key"]
        cat_key = loss.get("category", "Ground Forces")
        loss_amt = loss["amount"]

        asset_info = db_assets.get(eq_key, {})
        cat_item = catalog_map.get(eq_key, {})

        eq_name = loss.get("equipment_name") or asset_info.get("equipment_name") or cat_item.get("name") or eq_key
        unit_price = loss.get("price") or asset_info.get("buy_price") or cat_item.get("price", 1_000_000)

        total_usd_damage += (unit_price * loss_amt)

        current_qty = asset_info.get("amount", cat_item.get("initial", loss_amt))
        after_qty = max(0, current_qty - loss_amt)
        before_qty = current_qty

        subcat_id, subcat_label, unit = get_subcat_info(eq_name, cat_key)

        grouped.setdefault(subcat_id, {"label": subcat_label, "items": []})["items"].append({
            "name": eq_name,
            "before": before_qty,
            "loss": loss_amt,
            "after": after_qty,
            "unit": unit
        })

    subcat_order = ["Aircraft_Fighter", "Aircraft_Support", "UAV", "Helicopter", "Ground Forces", "Artillery", "Missiles", "Air Defense", "Navy"]

    summary_rows = []

    for sub_id in subcat_order:
        if sub_id not in grouped:
            continue

        g_data = grouped[sub_id]
        label = g_data["label"]
        items = g_data["items"]

        lines.append(f"■ *{label}*\n")

        sub_sum = 0
        sub_unit = "واحد"
        loss_word = "مصرف/شلیک:" if (is_attacker and op_type == "air_missile") else "تلفات:"

        for item in items:
            sub_sum += item["loss"]
            sub_unit = item["unit"]
            lines.append(f"> **{item['name']}**")
            lines.append(f"> • قبل از نبرد: {item['before']:,} {item['unit']}")
            lines.append(f"> • {loss_word} {item['loss']:,} {item['unit']}")
            lines.append(f"> • موجودی جدید: {item['after']:,} {item['unit']}\n")

        lines.append("━━━━━━━━━━━━━━━━━━\n")

        short_lbl = label.replace("نیروی هوایی و جنگنده‌ها", "جنگنده").replace("نیروی زمینی و زرهی", "زرهی")
        summary_rows.append(f"{short_lbl}: {sub_sum:,} {sub_unit}")

    if summary_rows:
        sum_title = "جمع تسلیحات مصرف‌شده:" if (is_attacker and op_type == "air_missile") else "جمع کاهش تجهیزات ثبت‌شده:"
        lines.append(f"■ *{sum_title}*\n")
        for s_row in summary_rows:
            lines.append(f"> • {s_row}")
        lines.append("\n━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *ارزیابی مالی و استراتژیک:*\n")
    
    if total_usd_damage >= 1_000_000_000:
        damage_str = f"{total_usd_damage / 1_000_000_000:.2f} میلیارد دلار"
    elif total_usd_damage >= 1_000_000:
        damage_str = f"{total_usd_damage / 1_000_000:.1f} میلیون دلار"
    else:
        damage_str = f"{total_usd_damage:,} دلار"

    lines.append(f"> • **ارزش کل تجهیزات و خسارات:** {damage_str}")
    if is_attacker:
        lines.append("> • **تغییر روحیه ملی:** +۱۰٪ (اقتدار ملی)")
        lines.append("> • **زمان آمادگی موج بعدی:** ۱۲ ساعت")
    else:
        lines.append("> • **تغییر روحیه ملی:** -۵٪ (اضطراب عمومی)")
        lines.append("> • **زمان بازسازی زیرساخت‌ها:** ۳ تا ۵ روز")

    lines.append("\n━━━━━━━━━━━━━━━━━━\n")
    lines.append("■ *ارزیابی نهایی کارشناسان نظامی:*\n")
    if is_attacker and op_type == "air_missile":
        if military_loss > 0:
            lines.append(f"> _عملیات شلیک با موفقیت نسبی اجرا گردید؛ تحمل {military_loss:,} نفر تلفات نیروهای خودی و کسر پرتابه‌های مصرف‌شده از دیتابیس به ثبت رسید._")
        else:
            lines.append("> _عملیات شلیک بدون تلفات انسانی نیروهای خودی اجرا گردید و پرتابه‌های شلیک‌شده از دیتابیس کسر شدند._")
    else:
        lines.append("> _خسارات واردشده نیازمند جایگزینی تجهیزات و بازسازی پایگاه‌ها از طریق ساخت‌وسازهای غیرنظامی و خطوط تولید بومی می‌باشد._")

    return "\n".join(lines)


def apply_war_losses_to_db(attacker_key: str, defender_key: str, losses: dict, targets_text: str = ""):
    """اعمال کسر تلفات و خسارات از دیتابیس هر دو کشور و اعمال آسیب به پالایشگاه‌ها و نیروگاه‌ها."""
    att_country = db.get_country_by_key(attacker_key)
    def_country = db.get_country_by_key(defender_key)

    if att_country:
        db.seed_country_assets(att_country["id"], attacker_key)
    if def_country:
        db.seed_country_assets(def_country["id"], defender_key)

    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()

            if att_country:
                att_cid = att_country["id"]
                new_att_p = max(0, att_country["active_personnel"] - losses.get("att_military_loss", 0))
                cur.execute("UPDATE countries SET active_personnel = ? WHERE id = ?", (new_att_p, att_cid))

                for item in losses.get("att_losses", []):
                    cur.execute("""
                        UPDATE country_assets SET amount = MAX(0, amount - ?)
                        WHERE country_id = ? AND equipment_key = ?
                    """, (item["amount"], att_cid, item["equipment_key"]))

            if def_country:
                def_cid = def_country["id"]
                new_def_p = max(0, def_country["active_personnel"] - losses.get("def_military_loss", 0))
                cur.execute("UPDATE countries SET active_personnel = ? WHERE id = ?", (new_def_p, def_cid))

                for item in losses.get("def_losses", []):
                    cur.execute("""
                        UPDATE country_assets SET amount = MAX(0, amount - ?)
                        WHERE country_id = ? AND equipment_key = ?
                    """, (item["amount"], def_cid, item["equipment_key"]))

                # اثر استراتژیک آسیب به پالایشگاه و نیروگاه برق مدافع در صورت لزوم
                # آسیب استراتژیک نسبی (۸٪ ظرفیت با کف مشخص) — منصفانه برای همه اندازه‌های کشور
                if "پالایشگاه" in targets_text or "نفتی" in targets_text:
                    cur.execute("""UPDATE countries SET oil_production =
                        MAX(0, oil_production - MAX(5000, CAST(oil_production * 0.08 AS INTEGER)))
                        WHERE id = ?""", (def_cid,))
                if "نیروگاه" in targets_text or "برق" in targets_text:
                    cur.execute("""UPDATE countries SET electricity =
                        MAX(5, electricity - MAX(2, CAST(electricity * 0.08 AS INTEGER)))
                        WHERE id = ?""", (def_cid,))

        return True
    except Exception as e:
        print(f"Error applying war losses: {e}")
        return False
