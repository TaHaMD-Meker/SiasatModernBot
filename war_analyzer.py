# -*- coding: utf-8 -*-
"""
ماژول تحلیل هوشمند سناریوی نبرد و شبیه‌ساز جنگ‌ها (AI War & Battle Simulator Engine v4.0)
دارای سیستم شبیه‌سازی چندعاملی و احتمالی (Probabilistic Multi-Factor Battle Engine):
- محاسبه متوازن بر اساس سطح فناوری (Tech Level)، تراکم پدافند هوایی، موازنه قوا و آمادگی رزمی.
- عدم وجود نتیجه ۱۰۰٪ قطعی (تصادفی‌سازی تاکتیکی و احتمال عبور/رهگیری پرتابه‌ها).
- محاسبه خسارات متقابل به مهاجم (افتادن پهپاد/جنگنده بر اثر جنگ الکترونیک و پدافند).
- استخراج هوشمند تسلیحات از متن رول بازیکنان.
- نگارش کارشناسی، رسمی، سنگین و بدون ایموجی‌های اضافی.
"""

import os
import re
import random
import json
import urllib.request
import database as db
import config

NON_CONTIGUOUS_PAIRS = {
    ("iran", "israel"), ("israel", "iran"),
    ("usa", "russia"), ("russia", "usa"),
    ("usa", "iran"), ("iran", "usa"),
    ("usa", "china"), ("china", "usa"),
    ("uk", "iran"), ("iran", "uk"),
    ("france", "iran"), ("iran", "france"),
    ("qatar", "israel"), ("israel", "qatar"),
    ("saudi", "israel"), ("israel", "saudi"),
    ("usa", "israel"), ("israel", "usa"),
}


def convert_farsi_digits(text: str) -> str:
    farsi_digits = '۰۱۲۳۴۵۶۷۸۹'
    eng_digits = '0123456789'
    trans_table = str.maketrans(farsi_digits, eng_digits)
    return text.translate(trans_table)


def detect_operation_type(attacker_key: str, defender_key: str, attacker_role: str, defender_role: str):
    """تشخیص هوشمند نوع عملیات (موشکی/هوایی یا تهاجم زمینی)."""
    if (attacker_key, defender_key) in NON_CONTIGUOUS_PAIRS or (defender_key, attacker_key) in NON_CONTIGUOUS_PAIRS:
        return "air_missile"

    text = (attacker_role + " " + defender_role).lower()
    
    ground_keywords = [
        "پیشروی زمینی", "تانک", "نفربر", "پیاده نظام", "تصرف شهر", "عبور از مرز",
        "مرزی", "محور زمینی", "زرهی", "عملیات زمینی", "ورود به خاک", "تسخیر"
    ]
    air_keywords = [
        "موشک", "شلیک", "پرتاب", "پهپاد", "جنگنده", "پدافند", "سایبری",
        "پایگاه هوایی", "رادار", "سوله", "کروز", "بالستیک"
    ]

    ground_score = sum(1 for kw in ground_keywords if kw in text)
    air_score = sum(1 for kw in air_keywords if kw in text)

    if ground_score > 2 and ground_score >= air_score:
        return "ground_invasion"
    else:
        return "air_missile"


def parse_weapon_mentions_from_roleplay_text(roleplay_text: str, country_assets: list, country_key: str) -> list:
    """استخراج هوشمند دقیق نام تسلیحات و تعداد شلیک‌شده/استفاده‌شده از متن رول بازیکن."""
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
                "equipment_key": e_key,
                "equipment_name": e_name,
                "amount": e_amt,
                "category": e_cat,
                "price": e_price
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

    parsed_losses = {}

    alias_dict = {
        "hoveyzeh": ["هویزه", "hoveyzeh"],
        "noor": ["نور", "noor"],
        "paveh": ["پاوه", "paveh"],
        "kheybar": ["خیبرشکن", "خیبر شکن", "kheibar", "kheybar"],
        "sejjil": ["سجیل", "sejjil", "sajil"],
        "khorramshahr": ["خرمشهر", "khorramshahr"],
        "fattah": ["فتاح", "fattah"],
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
        "abrams": ["آبرامز", "ابرامز", "abrams"],
        "merkava": ["مرکاوا", "merkava"],
        "leopard": ["لئوپارد", "لیوپارد", "leopard"],
        "t90": ["تی-۹۰", "ت-۹۰", "t-90", "t90"],
    }

    for e_key, item in assets_map.items():
        name = item["equipment_name"].lower()
        key = e_key.lower()

        keywords = set()
        keywords.add(name)
        keywords.add(key)

        clean_name = re.sub(r'^(موشک|کروز|پدافند|ضدکشتی|تپ|راکت|تانک|شناور|ناوچه|پهپاد|سامانه|ناو)\s+', '', name)
        keywords.add(clean_name)
        keywords.add(clean_name.replace('-', ' '))
        keywords.add(clean_name.replace('-', ''))

        for alias_key, aliases in alias_dict.items():
            if alias_key in key or any(alias_key in kw for kw in keywords):
                for a in aliases:
                    keywords.add(a.lower())

        valid_keywords = sorted([kw for kw in keywords if len(kw) >= 2], key=len, reverse=True)

        found_qty = None
        for kw in valid_keywords:
            esc_kw = re.escape(kw)

            p1 = r'(\d+)\s*(?:فروند|عدد|دستگاه|سامانه|آتشبار|واحد|دست)?\s*(?:موشک|پهپاد|جنگنده|کروز|تانک|نفربر)?\s*' + esc_kw
            p2 = esc_kw + r'\s*(?:\([^)]*\))?\s*(?:برد\s*\d+\s*کیلومتر)?\s*(?:با|تعداد|به تعداد)?\s*(\d+)\s*(?:فروند|عدد|دستگاه|واحد)?'
            p3 = esc_kw + r'\s*\(\s*(\d+)\s*\)'
            p4 = r'\(\s*(\d+)\s*' + esc_kw + r'\s*\)'

            m1 = re.search(p1, text_clean, re.IGNORECASE)
            m3 = re.search(p3, text_clean, re.IGNORECASE)
            m4 = re.search(p4, text_clean, re.IGNORECASE)
            m2 = re.search(p2, text_clean, re.IGNORECASE)

            if m1:
                found_qty = int(m1.group(1))
            elif m3:
                found_qty = int(m3.group(1))
            elif m4:
                found_qty = int(m4.group(1))
            elif m2:
                found_qty = int(m2.group(1))

            if found_qty and found_qty > 0 and found_qty < 50000:
                parsed_losses[e_key] = {
                    "equipment_key": e_key,
                    "equipment_name": item["equipment_name"],
                    "amount": found_qty,
                    "category": item["category"],
                    "price": item["price"]
                }
                break

    return list(parsed_losses.values())


def calculate_battle_balance(att_assets, def_assets, att_tech=1, def_tech=1, att_app=80, def_app=80, op_type='air_missile'):
    """محاسبه موازنه توان هجومی، شبکه پدافندی و نرخ‌های احتمالی رهگیری/عبور/خسارت مهاجم."""
    
    # ۱. محاسبه توان هجومی مهاجم
    att_missiles = sum(a.get("amount", 0) for a in att_assets if a.get("category") == "Missiles")
    att_uavs = sum(a.get("amount", 0) for a in att_assets if a.get("category") == "UAV")
    att_aircraft = sum(a.get("amount", 0) for a in att_assets if a.get("category") == "Aircraft")
    att_ground = sum(a.get("amount", 0) for a in att_assets if a.get("category") == "Ground Forces")

    att_tech_mult = 1.0 + (att_tech - 1) * 0.15
    att_app_mult = 0.85 + (att_app / 100.0) * 0.3

    if op_type == "air_missile":
        att_strike_power = (att_missiles * 1.5 + att_uavs * 0.8 + att_aircraft * 3.0) * att_tech_mult * att_app_mult
    else:
        att_strike_power = (att_ground * 2.0 + att_aircraft * 2.5 + att_missiles * 1.0) * att_tech_mult * att_app_mult

    # ۲. محاسبه توان پدافندی و سپری مدافع
    def_airdef = sum(d.get("amount", 0) for d in def_assets if d.get("category") == "Air Defense")
    def_aircraft = sum(d.get("amount", 0) for d in def_assets if d.get("category") == "Aircraft")
    def_uavs = sum(d.get("amount", 0) for d in def_assets if d.get("category") == "UAV")
    def_ground = sum(d.get("amount", 0) for d in def_assets if d.get("category") == "Ground Forces")

    def_tech_mult = 1.0 + (def_tech - 1) * 0.15
    def_app_mult = 0.85 + (def_app / 100.0) * 0.3

    if op_type == "air_missile":
        def_shield_power = (def_airdef * 4.5 + def_aircraft * 1.5) * def_tech_mult * def_app_mult
    else:
        def_shield_power = (def_ground * 2.5 + def_airdef * 2.0 + def_aircraft * 2.0) * def_tech_mult * def_app_mult

    # ۳. محاسبه نرخ احتمالی رهگیری پدافند و عبور پرتابه‌ها
    base_ratio = def_shield_power / max(1.0, att_strike_power)
    
    # فاکتور شانس و متغیرهای غیرقابل پیش‌بینی تاکتیکی (±۱۲٪)
    tactical_variance = random.uniform(-0.12, 0.12)
    
    # نرخ رهگیری بین ۱۵٪ تا ۸۸٪ متغیر است
    raw_intercept = 0.35 + (base_ratio - 0.8) * 0.25 + tactical_variance
    intercept_rate = round(max(0.15, min(0.88, raw_intercept)), 2)
    penetration_rate = round(1.0 - intercept_rate, 2)

    # ۴. محاسبه ریسک و احتمال خسارت متقابل به مهاجم (سقوط پهپاد/جنگنده بر اثر پدافند/جنگ الکترونیک)
    raw_att_risk = (def_shield_power / max(100.0, att_strike_power)) * 0.25 + random.uniform(-0.04, 0.04)
    att_risk_rate = round(max(0.03, min(0.55, raw_att_risk)), 2)

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


def generate_war_analysis_report(attacker_key: str, defender_key: str, attacker_role: str, defender_role: str = ""):
    """تولید گزارش هوشمند سناریوی نبرد بر اساس رول‌های واقعی دو طرف و موازنه قوا."""
    
    attacker_info = config.COUNTRIES.get(attacker_key, {})
    defender_info = config.COUNTRIES.get(defender_key, {})

    att_flag = attacker_info.get("flag", "")
    att_name = attacker_info.get("name", attacker_key)
    def_flag = defender_info.get("flag", "")
    def_name = defender_info.get("name", defender_key)

    att_country = db.get_country_by_key(attacker_key)
    def_country = db.get_country_by_key(defender_key)

    att_cid = att_country["id"] if att_country else None
    def_cid = def_country["id"] if def_country else None

    if att_cid:
        db.seed_country_assets(att_cid, attacker_key)
        att_assets = db.get_country_assets(att_cid)
    if def_cid:
        db.seed_country_assets(def_cid, defender_key)
        def_assets = db.get_country_assets(def_cid)

    if not att_assets:
        att_assets = config.COUNTRY_EQUIPMENT_CATALOG.get(attacker_key, [])
        for a in att_assets:
            if "equipment_key" not in a: a["equipment_key"] = a.get("key", "")
            if "equipment_name" not in a: a["equipment_name"] = a.get("name", "")
            if "amount" not in a: a["amount"] = a.get("initial", 100)

    if not def_assets:
        def_assets = config.COUNTRY_EQUIPMENT_CATALOG.get(defender_key, [])
        for d in def_assets:
            if "equipment_key" not in d: d["equipment_key"] = d.get("key", "")
            if "equipment_name" not in d: d["equipment_name"] = d.get("name", "")
            if "amount" not in d: d["amount"] = d.get("initial", 100)

    op_type = detect_operation_type(attacker_key, defender_key, attacker_role, defender_role)

    # محاسبه موازنه قوا و ضریب احتمالی شبیه‌سازی
    balance = calculate_battle_balance(
        att_assets, def_assets,
        att_tech=att_country.get("tech_level", 1) if att_country else 1,
        def_tech=def_country.get("tech_level", 1) if def_country else 1,
        att_app=att_country.get("approval_rating", 80) if att_country else 80,
        def_app=def_country.get("approval_rating", 80) if def_country else 80,
        op_type=op_type
    )

    # محاسبه تلفات بر اساس استخراج از متن رول یا موازنه قوا
    losses = calculate_simulated_losses(
        att_assets, def_assets, att_country, def_country, op_type,
        attacker_key, defender_key, attacker_role, defender_role, balance
    )

    # فراخوانی هوش مصنوعی در صورت وجود API Key
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("AI_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if api_key:
        try:
            att_tech = att_country.get("tech_level", 1) if att_country else 1
            def_tech = def_country.get("tech_level", 1) if def_country else 1
            intercept_pct = int(balance["intercept_rate"] * 100)
            pen_pct = int(balance["penetration_rate"] * 100)

            prompt = f"""شما یک تحلیل‌گر عالی ارشد ژئوپلیتیک و ارزیاب نبرد هوشمند در بازی «سیاست مدرن» هستید.
کشور مهاجم: {att_flag} {att_name} (سطح فناوری: {att_tech})
کشور مدافع: {def_flag} {def_name} (سطح فناوری: {def_tech})

رول و طرح عملیاتی مهاجم ({att_name}):
"{attacker_role}"

رول و طرح پدافندی مدافع ({def_name}):
"{defender_role if defender_role else 'دفاع موشکی، هوایی و زمینی طبق دستورالعمل استاندارد'}"

نوع عملیات تشخیص داده شده: {"حمله موشکی، پهپادی و هوایی" if op_type == "air_missile" else "عملیات زمینی و تهاجم مرزی"}

موازنه پدافندی شبیه‌سازی‌شده:
• درصد رهگیری پدافند مدافع: {intercept_pct}٪
• درصد عبور پرتابه‌ها و اصابت: {pen_pct}٪

تلفات انسانی محاسبه‌شده توسط موتور شبیه‌ساز:
مهاجم: {losses['att_military_loss']} نفر نظامی، {losses['att_civilian_loss']} نفر غیرنظامی
مدافع: {losses['def_military_loss']} نفر نظامی، {losses['def_civilian_loss']} نفر غیرنظامی

دستورالعمل نگارش بسیار حیاتی:
۱. از به‌کار بردن هرگونه ایموجی‌های اضافی، تزئینی و کارتونی در متن گزارش خودداری کن. متن باید بسیار رسمی، کارشناسی، سنگین و خوانا باشد.
۲. در صورت موشکی/هوایی بودن عملیات یا عدم وجود مرز زمینی، به هیچ عنوان واژه‌های «پیشروی مرزی» یا «تصرف زمینی» به کار نبر.
۳. نتیجه نبرد نباید ۱۰۰٪ موفق یا ۱۰۰٪ ناموفق باشد؛ همواره موازنه رهگیری پدافند و عبور بخشی از پرتابه‌ها را توضیح بده.
۴. گزارش را در ۶ بخش واضح با خطوط جداکننده ━━━━━━━━━━━━━━━━━━ تدوین کن.

فرمت دقیق نگارش:
*نتیجه سناریوی جنگی — ارزیابی عملیات {att_name} در برابر دفاع {def_name}*
پرونده: عملیات {att_name} / طرح دفاعی {def_name}
━━━━━━━━━━━━━━━━━━

■ *ارزیابی موازنه قوا و سطح فناوری (Tech Level)*
• کشور مهاجم ({att_name}): سطح فناوری {att_tech}
• کشور مدافع ({def_name}): سطح فناوری {def_tech} | پوشش پدافندی {balance['def_airdef_qty']} سامانه

━━━━━━━━━━━━━━━━━━

■ *تحلیل تاکتیکی و موازنه درگیری*
• **درصد رهگیری پدافند مدافع:** {intercept_pct}٪
• **درصد عبور موفق پرتابه‌ها:** {pen_pct}٪
• **مرحله نخست — آماده‌سازی و شلیک اولیه:**
...
• **مرحله دوم — درگیری یگان‌ها و پدافند:**
...
• **مرحله سوم — اصابت‌ها و برآورد آسیب‌های زیرساختی:**
...

━━━━━━━━━━━━━━━━━━

■ *برآورد تلفات انسانی اولیه*
• تلفات نیروهای مسلح {att_name}: {losses['att_military_loss']:,} نفر
• تلفات نیروهای مسلح {def_name}: {losses['def_military_loss']:,} نفر
• تلفات غیرنظامی و خسارات جانبی: {losses['def_civilian_loss']:,} نفر

━━━━━━━━━━━━━━━━━━

■ *جمع‌بندی و ارزیابی استراتژیک*
...
"""
            url = "https://api.openai.com/v1/chat/completions"
            data = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a professional military scenario analyzer. No excess emojis. Professional Persian typography. Realistic probabilistic outcomes."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.6
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                res = json.loads(response.read().decode("utf-8"))
                report_text = res["choices"][0]["message"]["content"]
                if report_text:
                    return report_text, losses
        except Exception as e:
            print(f"AI API call failed, falling back to built-in simulation engine: {e}")

    # موتور داخلی شبیه‌ساز نبرد (Built-in Simulation Engine)
    if op_type == "air_missile":
        report_text = build_air_missile_report_text(
            att_flag, att_name, def_flag, def_name, attacker_role, defender_role, losses, att_assets, def_assets, att_country, def_country, balance
        )
    else:
        report_text = build_ground_invasion_report_text(
            att_flag, att_name, def_flag, def_name, attacker_role, defender_role, losses, att_assets, def_assets, att_country, def_country, balance
        )

    return report_text, losses


def calculate_simulated_losses(att_assets, def_assets, att_country, def_country, op_type, attacker_key, defender_key, attacker_role="", defender_role="", balance=None):
    """محاسبه هوشمند و واقعی تلفات انسانی و تجهیزاتی با احتساب موازنه قوا و استخراج رول."""
    
    att_tech = att_country.get("tech_level", 1) if att_country else 1
    def_tech = def_country.get("tech_level", 1) if def_country else 1

    if not balance:
        balance = calculate_battle_balance(att_assets, def_assets, att_tech, def_tech, op_type=op_type)

    def pick_losses_from_assets(assets_list, is_attacker, op_type, balance):
        result_losses = []
        by_cat = {}
        for item in assets_list:
            eq_key = item.get("equipment_key") or item.get("key")
            eq_name = item.get("equipment_name") or item.get("name")
            cat = item.get("category", "Ground Forces")
            amount = item.get("amount", item.get("initial", 50))
            buy_price = item.get("buy_price", item.get("price", 1_000_000))
            if eq_key and amount > 0:
                by_cat.setdefault(cat, []).append({
                    "key": eq_key, "name": eq_name, "amount": amount, "category": cat, "price": buy_price
                })

        intercept_rate = balance.get("intercept_rate", 0.5)
        pen_rate = balance.get("penetration_rate", 0.5)
        att_risk = balance.get("att_risk_rate", 0.1)

        for cat, items in by_cat.items():
            if is_attacker:
                if op_type == "air_missile":
                    if cat in ["Missiles", "UAV"]:
                        selected = random.sample(items, min(len(items), random.randint(1, 4)))
                        for it in selected:
                            curr_amt = it["amount"]
                            loss_qty = max(1, min(curr_amt, random.randint(2, 12)))
                            result_losses.append({
                                "equipment_key": it["key"], "equipment_name": it["name"],
                                "amount": loss_qty, "category": cat, "price": it["price"]
                            })
                    elif cat in ["Aircraft", "Navy"]:
                        # Attacker has risk of losing jets/drones to defender air defense
                        if random.random() < att_risk:
                            selected = random.sample(items, 1)
                            for it in selected:
                                result_losses.append({
                                    "equipment_key": it["key"], "equipment_name": it["name"],
                                    "amount": 1, "category": cat, "price": it["price"]
                                })
            else:
                # Defender losses scale with attacker penetration rate
                selected = random.sample(items, min(len(items), random.randint(1, 4)))
                for it in selected:
                    curr_amt = it["amount"]
                    if cat in ["Air Defense", "Missiles", "UAV"]:
                        # Defender consumes air defense missiles / SAMs
                        loss_qty = max(1, min(curr_amt, int(random.randint(2, 8) * (1.0 + intercept_rate))))
                    elif cat == "Aircraft":
                        loss_qty = max(1, min(curr_amt, int(random.randint(1, 3) * pen_rate) or 1))
                    else:
                        loss_qty = max(1, min(curr_amt, int(random.randint(2, 8) * pen_rate) or 1))

                    result_losses.append({
                        "equipment_key": it["key"], "equipment_name": it["name"],
                        "amount": loss_qty, "category": cat, "price": it["price"]
                    })

        return result_losses

    # ۱. ابتدا تلاش برای استخراج دقیق تسلیحات و اعداد از متن رول مهاجم
    att_parsed = parse_weapon_mentions_from_roleplay_text(attacker_role, att_assets, attacker_key)
    if att_parsed:
        att_losses = att_parsed
    else:
        att_losses = pick_losses_from_assets(att_assets, True, op_type, balance)

    # ۲. تلاش برای استخراج دقیق تسلیحات از متن رول مدافع
    def_parsed = parse_weapon_mentions_from_roleplay_text(defender_role, def_assets, defender_key)
    if def_parsed:
        def_losses = def_parsed
    else:
        def_losses = pick_losses_from_assets(def_assets, False, op_type, balance)

    tech_diff = att_tech - def_tech
    pen_rate = balance.get("penetration_rate", 0.5)

    if op_type == "air_missile":
        att_military_loss = max(0, int(random.randint(0, 15) * balance.get("att_risk_rate", 0.1)))
        att_civilian_loss = 0
        def_military_loss = max(5, int(random.randint(20, 80) * pen_rate + tech_diff * 4))
        def_civilian_loss = max(0, int(random.randint(2, 25) * pen_rate))
    else:
        att_military_loss = max(20, int(random.randint(120, 350) - tech_diff * 15))
        att_civilian_loss = max(0, random.randint(5, 25))
        def_military_loss = max(30, int(random.randint(160, 480) * pen_rate + tech_diff * 20))
        def_civilian_loss = max(5, int(random.randint(15, 60) * pen_rate))

    return {
        "att_losses": att_losses,
        "def_losses": def_losses,
        "att_military_loss": att_military_loss,
        "att_civilian_loss": att_civilian_loss,
        "def_military_loss": def_military_loss,
        "def_civilian_loss": def_civilian_loss,
    }


def build_air_missile_report_text(att_flag, att_name, def_flag, def_name, attacker_role, defender_role, losses, att_assets, def_assets, att_country, def_country, balance):
    """گزارش رسمی و تحلیل کارشناسی نبرد موشکی و هوایی."""

    att_tech = att_country.get("tech_level", 1) if att_country else 1
    def_tech = def_country.get("tech_level", 1) if def_country else 1

    intercept_pct = int(balance["intercept_rate"] * 100)
    pen_pct = int(balance["penetration_rate"] * 100)

    lines = []
    lines.append(f"*نتیجه سناریوی جنگی — ارزیابی عملیات موشکی/هوایی {att_name} در برابر دفاع {def_name}*")
    lines.append(f"پرونده: عملیات {att_flag} {att_name} / شبکه پدافند هوایی {def_flag} {def_name}")
    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *ارزیابی موازنه قوا و سطح فناوری (Tech Level)*")
    lines.append(f"• **کشور مهاجم ({att_name}):** سطح فناوری {att_tech} | شاخص توان هجومی: {balance['att_strike_power']:,}")
    lines.append(f"• **کشور مدافع ({def_name}):** سطح فناوری {def_tech} | پوشش پدافندی: {balance['def_airdef_qty']} سامانه | شاخص سپری: {balance['def_shield_power']:,}\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *تحلیل تاکتیکی و موازنه پدافندی درگیری*")
    lines.append(f"• **نرخ رهگیری پدافند هوایی {def_name}:** **{intercept_pct}٪** پرتابه‌ها توسط شبکه پدافند چندلایه رهگیری شدند.")
    lines.append(f"• **نرخ عبور موفق پرتابه‌ها:** **{pen_pct}٪** موشک‌ها/پهپادها از لایه‌های پدافندی عبور کردند.")
    lines.append(f"• **میزان ریسک و خسارات متقابل مهاجم:** حدود {int(balance['att_risk_rate']*100)}٪ احتمال اختلال/سقوط پرتابه‌ها در درگیری پدافندی.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *شرح مراحل درگیری*")
    lines.append(f"• **مرحله ۱ — آماده‌سازی و شلیک:** یگان‌های موشکی و پهپادی {att_name} پرتابه‌های خود را به سمت اهداف زیرساختی و پایگاه‌ها شلیک نمودند.")
    lines.append(f"• **مرحله ۲ — واکنش پدافندی:** رادارهای هشدار زودهنگام {def_name} اهداف را ردیابی کرده و سامانه‌های پدافند موشکی {intercept_pct}٪ پرتابه‌ها را در آسمان منهدم کردند.")
    lines.append(f"• **مرحله ۳ — اصابت‌ها:** {pen_pct}٪ پرتابه‌های عبوری به مواضع، سوله‌های نگهداری و مراکز پشتیبانی اصابت کردند.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *برآورد تلفات انسانی اولیه*\n")

    lines.append(f"تلفات کشور مهاجم ({att_flag} {att_name}):")
    lines.append(f"• پرسنل نظامی: {losses['att_military_loss']:,} نفر (عملیات از راه دور)")
    lines.append(f"• تلفات غیرنظامی: {losses['att_civilian_loss']:,} نفر")

    lines.append(f"\nتلفات کشور مدافع ({def_flag} {def_name}):")
    lines.append(f"• پرسنل نظامی: {losses['def_military_loss']:,} نفر")
    lines.append(f"• تلفات غیرنظامی: {losses['def_civilian_loss']:,} نفر\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *جمع‌بندی و ارزیابی نهایی ژئوپلیتیک:*")
    lines.append(f"عملیات تهاجمی {att_name} منجر به اصابت {pen_pct}٪ پرتابه‌ها و بروز خسارت گردید، در حالی که شبکه پدافندی {def_name} با رهگیری {intercept_pct}٪ اهداف، از انهدام کامل زیرساخت‌ها جلوگیری نمود.")

    return "\n".join(lines)


def build_ground_invasion_report_text(att_flag, att_name, def_flag, def_name, attacker_role, defender_role, losses, att_assets, def_assets, att_country, def_country, balance):
    """گزارش نبردهای دارای تهاجم زمینی و مرزی."""

    att_tech = att_country.get("tech_level", 1) if att_country else 1
    def_tech = def_country.get("tech_level", 1) if def_country else 1

    lines = []
    lines.append(f"*نتیجه سناریوی جنگی — ارزیابی عملیات زمینی {att_name} در برابر دفاع {def_name}*")
    lines.append(f"پرونده: تهاجم زمینی {att_flag} {att_name} / دفاع مرزی {def_flag} {def_name}")
    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *ارزیابی موازنه قوا و سطح فناوری (Tech Level)*")
    lines.append(f"• **کشور مهاجم ({att_name}):** سطح فناوری {att_tech} | ستون‌های زرهی و پشتیبانی هوایی")
    lines.append(f"• **کشور مدافع ({def_name}):** سطح فناوری {def_tech} | خطوط پدافند مرزی و یگان‌های ضدزره\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *مرحله ۱ — آتش‌پایه‌های توپخانه (ساعت ۰۳:۰۰)*")
    lines.append(f"آتش سنگین توپخانه و حملات راکتی اولیه {att_name} علیه پاسگاه‌ها و مواضع پیشین {def_name} آغاز شد.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *مرحله ۲ — ورود ستون‌های زرهی (ساعت ۰۶:۰۰)*")
    lines.append(f"پیشروی تانک‌ها و نفربرهای زرهی {att_name} در محورهای مرزی.")
    lines.append(f"شکل‌گیری نبرد شدید زرهی با نیروهای مدافع {def_name}.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *مرحله ۳ — ورود نیروهای پشتیبانی و ضدزره (ساعت ۱۲:۰۰)*")
    lines.append(f"ورود یگان‌های ضدزره و پشتیبانی {def_name} موجب تثبیت نسبی خطوط دفاعی گردید.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *برآورد تلفات انسانی اولیه*\n")

    lines.append(f"تلفات کشور مهاجم ({att_flag} {att_name}):")
    lines.append(f"• پرسنل نظامی: {losses['att_military_loss']:,} نفر")
    lines.append(f"• تلفات غیرنظامی: {losses['att_civilian_loss']:,} نفر")

    lines.append(f"\nتلفات کشور مدافع ({def_flag} {def_name}):")
    lines.append(f"• پرسنل نظامی: {losses['def_military_loss']:,} نفر")
    lines.append(f"• تلفات غیرنظامی: {losses['def_civilian_loss']:,} نفر\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *جمع‌بندی و ارزیابی استراتژیک:*")
    lines.append(f"درگیری زمینی منجر به خسارات متقابل سنگین زرهی و پرسنلی برای هر دو طرف گردید.")

    return "\n".join(lines)


def build_detailed_loss_receipt(country_key: str, item_losses: list, military_loss: int, civilian_loss: int, operation_name: str = "عملیات اخیر", is_attacker: bool = False, op_type: str = "air_missile"):
    """تولید فاکتور دقیق تلفات و کاهش تجهیزات با لحن رسمی و بدون ایموجی اضافی."""
    
    c_info = config.COUNTRIES.get(country_key, {})
    c_flag = c_info.get("flag", "")
    c_name = c_info.get("name", country_key)

    country = db.get_country_by_key(country_key)
    cid = country["id"] if country else None
    db_assets = {a["equipment_key"]: a for a in db.get_country_assets(cid)} if cid else {}

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
        lines.append("> _عملیات شلیک با موفقیت کامل بدون تلفات انسانی نیروهای خودی اجرا گردید و پرتابه‌های شلیک‌شده از دیتابیس کسر شدند._")
    else:
        lines.append("> _خسارات واردشده نیازمند جایگزینی تجهیزات و بازسازی پایگاه‌ها از طریق ساخت‌وسازهای غیرنظامی و خطوط تولید بومی می‌باشد._")

    return "\n".join(lines)


def apply_war_losses_to_db(attacker_key: str, defender_key: str, losses: dict):
    """اعمال کسر تلفات و خسارات از دیتابیس هر دو کشور."""
    conn = db.get_connection()
    cur = conn.cursor()

    att_country = db.get_country_by_key(attacker_key)
    def_country = db.get_country_by_key(defender_key)

    if att_country:
        att_cid = att_country["id"]
        db.seed_country_assets(att_cid, attacker_key)
        new_att_p = max(0, att_country["active_personnel"] - losses.get("att_military_loss", 0))
        cur.execute("UPDATE countries SET active_personnel = ? WHERE id = ?", (new_att_p, att_cid))

        for item in losses.get("att_losses", []):
            cur.execute("""
                UPDATE country_assets SET amount = MAX(0, amount - ?)
                WHERE country_id = ? AND equipment_key = ?
            """, (item["amount"], att_cid, item["equipment_key"]))

    if def_country:
        def_cid = def_country["id"]
        db.seed_country_assets(def_cid, defender_key)
        new_def_p = max(0, def_country["active_personnel"] - losses.get("def_military_loss", 0))
        cur.execute("UPDATE countries SET active_personnel = ? WHERE id = ?", (new_def_p, def_cid))

        for item in losses.get("def_losses", []):
            cur.execute("""
                UPDATE country_assets SET amount = MAX(0, amount - ?)
                WHERE country_id = ? AND equipment_key = ?
            """, (item["amount"], def_cid, item["equipment_key"]))

    conn.commit()
    conn.close()
    return True
