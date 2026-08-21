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
import war_stats as ws

# نقشه مرز زمینی مشترک — تهاجم زمینی فقط بین همسایه‌های واقعی مجاز است
# (کشورهای جزیره‌ای مانند انگلستان، ژاپن، تایوان، سوئد و کوبا مرز زمینی ندارند)
GROUND_ADJACENCY = {
    "iran": {"iraq", "turkey", "pakistan", "azerbaijan", "armenia", "afghanistan"},
    "iraq": {"iran", "turkey", "saudi", "kuwait", "syria", "jordan"},
    "saudi": {"iraq", "kuwait", "uae", "qatar", "oman", "jordan"},
    "qatar": {"saudi"},
    "uae": {"saudi", "oman"},
    "oman": {"saudi", "uae"},
    "kuwait": {"iraq", "saudi"},
    "israel": {"egypt", "hezbollah", "syria", "jordan"},
    "egypt": {"israel", "libya"},
    "hezbollah": {"israel"},
    "turkey": {"iran", "iraq", "syria", "georgia", "armenia", "azerbaijan", "greece"},
    "russia": {"ukraine", "poland", "china", "north_korea", "georgia", "azerbaijan", "kazakhstan", "norway", "finland"},
    "ukraine": {"russia", "poland"},
    "poland": {"germany", "ukraine", "russia"},
    "germany": {"poland", "france", "netherlands"},
    "france": {"germany", "italy", "spain"},
    "italy": {"france"},
    "china": {"russia", "north_korea", "pakistan", "india", "kazakhstan", "afghanistan", "vietnam"},
    "north_korea": {"china", "russia", "south_korea"},
    "south_korea": {"north_korea"},
    "india": {"pakistan", "china"},
    "pakistan": {"iran", "india", "china", "afghanistan"},
    "usa": {"canada", "mexico"},
    "canada": {"usa"},
    "mexico": {"usa"},
    "brazil": {"venezuela"},
    "venezuela": {"brazil"},
    "syria": {"turkey", "iraq", "israel", "jordan"},
    "jordan": {"syria", "israel", "iraq", "saudi"},
    "azerbaijan": {"iran", "russia", "georgia", "armenia", "turkey"},
    "armenia": {"georgia", "azerbaijan", "iran", "turkey"},
    "georgia": {"russia", "azerbaijan", "armenia", "turkey"},
    "greece": {"turkey"},
    "indonesia": {"malaysia"},
    "malaysia": {"indonesia", "singapore"},
    "singapore": {"malaysia"},
    "algeria": {"libya", "morocco"},
    "libya": {"algeria", "egypt"},
    "morocco": {"algeria"},
    "kazakhstan": {"russia", "china"},
    "afghanistan": {"iran", "pakistan", "china"},
    "spain": {"france"},
    "netherlands": {"germany"},
    "norway": {"russia", "sweden", "finland"},
    "sweden": {"norway", "finland"},
    "finland": {"russia", "sweden", "norway"},
    "vietnam": {"china"},
    # کشورهای جزیره‌ای (بحرین، استرالیا، فیلیپین، انگلستان، ژاپن، تایوان، کوبا) مرز زمینی ندارند
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

    # ---------- استخراج مقادیر «عمومی» بدون نام خاص ----------
    # مثال: «شلیک ۲۰۰ موشک بالستیک» یا «۵۰ راکت» یا «۳۰ پهپاد» → توزیع روی
    # تجهیزات هم‌کلاسِ موجود در انبار مهاجم (تا سقف موجودی)
    generic_patterns = [
        (r'(\d+)\s*(?:فروند|عدد)?\s*موشک\s*بالستیک', "ballistic"),
        (r'(\d+)\s*(?:فروند|عدد)?\s*موشک\s*کروز', "cruise"),
        (r'(\d+)\s*(?:فروند|عدد)?\s*(?:موشک|راکت)', "rocket"),
        (r'(\d+)\s*(?:فروند|عدد)?\s*پهپاد', "drone"),
        (r'(\d+)\s*(?:فروند)?\s*جنگنده', "aircraft"),
        (r'(\d+)\s*(?:دستگاه|عدد)?\s*(?:تانک|زرهی)', "armor"),
        (r'(\d+)\s*(?:قبضه|عدد)?\s*(?:توپ|توپخانه)', "artillery"),
    ]
    text_norm = text_clean.lower()
    generic_spans = []
    for pat, wcls in generic_patterns:
        for m in re.finditer(pat, text_norm):
            span = (m.start(), m.end())
            # اگر این بازه متن قبلاً به تطبیق نامی یا عمومی دیگری اختصاص یافته، رد شود
            if any(s < span[1] and span[0] < e for s, e in claimed_ranges + generic_spans):
                continue
            qty = int(m.group(1))
            if qty <= 0 or qty >= 50000:
                continue
            generic_spans.append(span)
            # تجهیزات هم‌کلاس موجود (بیشترین موجودی اول) که قبلاً انتخاب نشده‌اند
            pool = [
                (k, v) for k, v in assets_map.items()
                if k not in chosen and ws.weapon_class(v) == wcls
            ]
            pool.sort(key=lambda kv: -(kv[1].get("amount", 0) or 0))
            remaining = qty
            for k, v in pool:
                if remaining <= 0:
                    break
                stock = v.get("amount", 0) or 0
                if stock <= 0:
                    continue
                take = min(remaining, stock)
                chosen[k] = take
                remaining -= take

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


def ad_channels(def_assets) -> float:
    """ظرفیت درگیری پدافند: هر ۸ میلیون دلار سامانه = یک کانال (+۲ به ازای هر نوع)."""
    channels = 0.0
    types = 0
    for d in def_assets:
        if d.get("category") == "Air Defense":
            amt = d.get("amount", 0) or 0
            price = d.get("buy_price", d.get("price", 0)) or 0
            if amt > 0:
                types += 1
            channels += amt * (price / ws.AD_CHANNEL_VALUE)
    return channels + types * 2


def _weighted_rate(def_assets, wclass: str) -> float:
    """میانگین وزنی نرخ رهگیری مدافع برای یک کلاس پرتابه (وزن = کانال‌های هر سامانه)."""
    num = 0.0
    den = 0.0
    for d in def_assets:
        if d.get("category") != "Air Defense":
            continue
        amt = d.get("amount", 0) or 0
        price = d.get("buy_price", d.get("price", 0)) or 0
        w = amt * (price / ws.AD_CHANNEL_VALUE)
        if w <= 0:
            continue
        key = d.get("equipment_key") or d.get("key") or ""
        name = d.get("equipment_name") or d.get("name") or ""
        rates = ws.ad_rates_for(key, name)
        num += w * rates.get(wclass, rates.get("default", 0.4) if isinstance(rates.get("default"), float) else 0.4)
        den += w
    if den <= 0:
        return 0.0
    # اگر نرخ برای آن کلاس تعریف نشده بود (مثلاً sam در برابر rocket) از میانگین جدول پیش‌فرض
    if num == 0.0:
        return ws.AD_RATES["default"].get(wclass, 0.4)
    return num / den


def layered_defense(att_fired, def_assets):
    """شبیه‌سازی لایه‌ای رهگیری با آمار واقعی.

    هر پرتابه بر اساس کلاسش با نرخ رهگیری موزون مدافع درگیر می‌شود؛
    اگر تعداد پرتابه‌ها از ظرفیت کانال‌های پدافند بیشتر باشد (اشباع آتش)،
    پرتابه‌های اضافی بدون درگیری عبور می‌کنند — دقیقاً مثل دنیای واقعی.
    """
    per_item = []
    cap = int(ad_channels(def_assets))
    remaining = cap
    priority = ["ballistic", "cruise", "aircraft", "drone", "rocket", "other"]
    items = sorted(att_fired, key=lambda it: priority.index(ws.weapon_class(it)) if ws.weapon_class(it) in priority else 5)
    for it in items:
        wclass = ws.weapon_class(it)
        n = it.get("amount", 0) or 0
        key = it.get("equipment_key") or it.get("key")
        name = it.get("equipment_name") or it.get("name") or key
        price = it.get("buy_price", it.get("price", 0)) or 0
        engaged = max(0, min(n, remaining))
        remaining -= engaged
        rate = _weighted_rate(def_assets, wclass) if engaged > 0 else 0.0
        rate = max(0.0, min(0.95, rate + random.uniform(-0.04, 0.04)))
        intercepted = int(round(engaged * rate)) if wclass not in ("armor", "artillery", "naval", "sam") else 0
        penetrated = max(0, n - intercepted)
        per_item.append({
            "key": key, "name": name, "wclass": wclass, "price": price,
            "amount": n, "engaged": engaged, "intercepted": intercepted, "penetrated": penetrated,
        })
    total_fired = sum(p["amount"] for p in per_item)
    total_int = sum(p["intercepted"] for p in per_item)
    intercept_rate = round(total_int / max(1, total_fired), 2) if total_fired else 0.0
    return {
        "per_item": per_item,
        "channels": cap,
        "total_fired": total_fired,
        "total_intercepted": total_int,
        "total_penetrated": total_fired - total_int,
        "intercept_rate": intercept_rate,
        "penetration_rate": round(1.0 - intercept_rate, 2),
    }


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

    losses = calculate_simulated_losses(
        att_assets, def_assets, att_country, def_country, op_type,
        attacker_key, defender_key, attacker_role, defender_role
    )

    sim = losses.pop("sim", {}) or {}
    balance = {
        "intercept_rate": sim.get("intercept_rate", 0.5),
        "penetration_rate": sim.get("penetration_rate", 0.5),
        "att_risk_rate": min(0.5, 0.05 + sim.get("intercept_rate", 0.5) * 0.3),
        "att_strike_power": sim.get("total_fired", 0),
        "def_shield_power": sim.get("channels", 0),
    }
    weapon_breakdown = [
        {
            "name": p["name"], "total_fired": p["amount"],
            "intercepted": p["intercepted"], "penetrated": p["penetrated"],
            "pen_pct": int(round(100 * p["penetrated"] / max(1, p["amount"]))),
        }
        for p in sim.get("per_item", [])
    ]

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

    # ۵. فاکتورهای تلفات
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
    """موتور تحلیل آماری واقعی (نسخه ۹).

    هر پرتابه بر اساس کلاس خود با نرخ رهگیری واقعی سامانه‌های مدافع درگیر می‌شود؛
    اشباع آتش (تعداد پرتابه > ظرفیت کانال‌های پدافند) باعث عبور بی‌درگیری باقی
    پرتابه‌ها می‌شود. تلفات انسانی از جدول «تلفات به‌ازای هر اصابت» استخراج و
    با سقف‌های تضمینی محدود می‌شود.
    """
    def pick_engaged_from_assets(assets_list, op_type):
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
                    "amount": amount, "category": cat, "price": buy_price,
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
                    "amount": fired_qty, "category": cat, "price": it["price"],
                })
        return result

    att_fired = parse_weapon_mentions_from_roleplay_text(attacker_role, att_assets, attacker_key) or pick_engaged_from_assets(att_assets, op_type)
    def_fired = parse_weapon_mentions_from_roleplay_text(defender_role, def_assets, defender_key) or pick_engaged_from_assets(def_assets, op_type)

    # ---------- لایه ۱: عبور از پدافند ----------
    sim = layered_defense(att_fired, def_assets)

    # ---------- لایه ۲: تلفات مدافع از اصابت‌ها ----------
    mil = 0
    civ = 0
    ground_engaged = 0
    for pr in sim["per_item"]:
        wcls = pr["wclass"]
        if pr["penetrated"] <= 0 and wcls not in ("armor", "artillery"):
            continue
        if wcls in ("armor", "artillery"):
            # نبرد تماسی زمینی: تلفات مستقیم از درگیری زرهی/توپخانه
            ground_engaged += pr["amount"]
            continue
        m_per, c_per = ws.CASUALTY_PER_HIT.get(wcls)
        civ_factor = 0.5 if wcls in ("rocket", "drone") else 1.0  # اهداف عمدتاً نظامی‌اند
        mil += int(pr["penetrated"] * m_per * random.uniform(0.6, 1.4))
        civ += int(pr["penetrated"] * c_per * civ_factor * random.uniform(0.3, 1.0))
    if ground_engaged > 0 and op_type in ("ground_invasion", "combined_arms"):
        mil += int(ground_engaged * random.uniform(1.5, 3.0))
    def_military_loss = min(800, mil)
    def_civilian_loss = min(150, civ)

    # ---------- لایه ۳: تجهیزات مدافع منهدم‌شده بر اساس اصابت‌ها ----------
    def_losses = []
    total_hits = sum(pr["penetrated"] for pr in sim["per_item"])
    destroy_budget = int(total_hits * random.uniform(0.08, 0.15))
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
                max_kill = max(1, int(amt * 0.30))
                kill = min(budget, max_kill)
                k = item.get("equipment_key") or item.get("key")
                nm = item.get("equipment_name") or item.get("name") or k
                pr = item.get("buy_price", item.get("price", 1_000_000)) or 1_000_000
                existing = next((x for x in def_losses if x["equipment_key"] == k), None)
                if existing:
                    existing["amount"] = max(existing["amount"], kill)
                else:
                    def_losses.append({"equipment_key": k, "equipment_name": nm, "amount": kill, "category": cat, "price": pr})
                budget -= kill

    # ---------- لایه ۴: تلفات مهاجم ----------
    att_losses = []
    att_mil = 0
    int_rate = sim["intercept_rate"]
    for it in att_fired:
        wclass = ws.weapon_class(it)
        base = {
            "equipment_key": it.get("equipment_key") or it.get("key"),
            "equipment_name": it.get("equipment_name") or it.get("name"),
            "category": it.get("category", ""), "price": it.get("price", 0) or 0,
        }
        if wclass in ("rocket", "ballistic", "cruise", "drone"):
            base["amount"] = it.get("amount", 0)  # مصرف کامل
            att_losses.append(base)
        elif wclass == "aircraft":
            rate = ws.ATTACKER_ATTRITION["aircraft"] + int_rate * 0.08
            k = int(round((it.get("amount", 0) or 0) * rate))
            if (it.get("amount", 0) or 0) >= 5:
                k = max(k, 1)
            if k > 0:
                base["amount"] = k
                att_losses.append(base)
                att_mil += k * 2
        elif wclass in ("armor", "artillery", "naval", "sam"):
            rate = ws.ATTACKER_ATTRITION.get(wclass, 0.04)
            if op_type in ("ground_invasion", "combined_arms") and wclass == "armor":
                rate += int_rate * 0.06
            k = int(round((it.get("amount", 0) or 0) * rate))
            if (it.get("amount", 0) or 0) >= 10:
                k = max(k, 1)
            if k > 0:
                base["amount"] = k
                att_losses.append(base)
                att_mil += k * (4 if wclass == "armor" else 3)
    att_military_loss = min(400, att_mil + random.randint(5, 40))
    att_civilian_loss = 0 if op_type == "air_missile" else random.randint(0, 15)

    # ---------- لایه ۵: پاسخ آتشین مدافع (اگر رول دفاع داشته) ----------
    if def_fired:
        sim_r = layered_defense(def_fired, att_assets)
        hits_r = sim_r["total_penetrated"]
        if hits_r > 0:
            att_military_loss = min(400, att_military_loss + int(hits_r * 1.2 * random.uniform(0.5, 1.2)))
            budget_r = int(hits_r * random.uniform(0.05, 0.10))
            for it in att_fired:
                if budget_r <= 0:
                    break
                wclass = ws.weapon_class(it)
                if wclass in ("rocket", "ballistic", "cruise", "drone"):
                    continue
                existing = next((x for x in att_losses if x["equipment_key"] == (it.get("equipment_key") or it.get("key"))), None)
                if existing:
                    existing["amount"] += min(budget_r, 2)
                    budget_r -= 2

    return {
        "att_losses": att_losses,
        "def_losses": def_losses,
        "att_fired": att_fired,
        "def_fired": def_fired,
        "att_military_loss": att_military_loss,
        "att_civilian_loss": att_civilian_loss,
        "def_military_loss": def_military_loss,
        "def_civilian_loss": def_civilian_loss,
        "sim": sim,
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
