# -*- coding: utf-8 -*-
"""
سیستم مدیریت تلفات تجهیزات (Losses Management System) — ماژول مستقل.

فلسفه: بات هیچ تلفاتی را «محاسبه» نمی‌کند؛ نتیجه و مقدار تلفات را مدیریت بازی
تعیین کرده و این سیستم فقط ثبت، اعمال روی موجودی، نمایش تاریخچه/آمار،
جستجو و بازگردانی را انجام می‌دهد. معماری برای افزودن آینده‌ی
«خسارت زیرساخت/اقتصادی/مصرف مهمات» با همین الگو توسعه‌پذیر است.
"""

import math
import re
import json
from collections import OrderedDict
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

import database as db
import config
import news_engine
from utils import format_number

# ---------- زیردسته‌های نمایشی (روی دسته‌های اصلی دیتابیس سوار می‌شوند) ----------
# ترتیب مهم است: اولین تطبیق برنده است. (برچسب، ایموجی، کلیدواژه‌ها، دسته‌ی پایه)
_SUBCAT_RULES = [
    ("رادارها", "📡", ["رادار", "radar"], "Air Defense"),
    ("بمب‌افکن‌ها", "💣", ["بمب‌افکن", "bomber", "b-1", "b-2", "b-52", "tu-95", "tu-160", "tu-22", "h-6"], "Aircraft"),
    ("آواکس و شناسایی", "📡", ["awacs", "آواکس", "هشدار زودهنگام", "erieye", "phalcon", "globaleye", "a-50", "r-99", "e-2", "e-3", "e-7", "شناسایی استراتژیک"], "Aircraft"),
    ("هواپیماهای پشتیبانی", "🛫", ["ترابری", "سوخت‌رسان", "kc-", "c-130", "c-17", "c-390", "a400", "il-76", "an-", "a310", "a330", "mrtt"], "Aircraft"),
    ("بالگردها", "🚁", ["بالگرد", "بالاگرد", "heli", "mi-17", "mi-8", "mi-24", "mi-26", "mi-28", "ka-52", "ka-31", "ah-64", "ah-1", "uh-60", "uh-1", "nh90", "ch-47", "ch-53", "ch-148", "ch-149", "sh-60", "mh-60", "aw101", "aw109", "aw139", "کبرا", "آپاچی", "پوما", "گazel", "gazelle", "سی‌کینگ", "لینکس", "وایکات"], "Aircraft"),
    ("جنگنده‌ها", "✈️", [], "Aircraft"),
    ("پهپادها", "🛩️", [], "UAV"),
    ("تانک‌ها", "🛡️", ["تانک", "t-90", "t-80", "t-72", "t-14", "t-69", "t-62", "t-55", "merkava", "مرکاوا", "آبرامز", "ابرامز", "abrams", "لئوپارد", "لیوپارد", "leopard", "leclerc", "لکلرک", "challenger", "چلنجر", "ztz", "type 90", "k2", "altay", "ارماتا", "armata", "karrar", "کرار"], "Ground Forces"),
    ("خودروهای زرهی", "🚙", ["نفربر", "bmp", "btr", "m113", "namer", "نمر", "eitan", "ایتان", "stryker", "برادلی", "bradley", "mrap", "typhoon", "tigr", "تیگر", "خودروی زرهی", "زرهی", "فنی", "هموند", "humvee", "کوگر", "aryeh", "پل‌گذار", "مهندسی",
     "تویوتا", "تکنیکال", "technical", "پیکاپ", "دوشکا", "لندکروزر", "land cruiser", "خودرو تاکتیکی", "تاکتیکی",
     "sandcat", "tigris", "achzarit", "اچزاریت", "btr", "بی تی آر"], "Ground Forces"),
    ("توپخانه", "🎯", ["توپخانه", "توپ خودکششی", "خمپاره", "howitzer", "هویتزر", "m109", "m777", "2s1", "2s3", "2s19", "2s35", "msta", "paladin", "pzh", "k9", "firtina", "ceasar", "قیسر", "اتمز"], "Artillery"),
    ("راکت‌اندازها", "🚀", ["راکت", "himars", "هیمارس", "گراد", "grad", "smerch", "سمرچ", "tornado", "تورنادو", "uragan", "فجر", "رعد", "mlrs", "پیندا", "arityah", "امرسال", "lars", "astro", "لنچر"], "Artillery"),
    ("ناوهای هواپیمابر", "⚓", ["ناو هواپیمابر", "ناو بالگردبر", "carrier", "کوزنتسف", "ford", "nimitz", "cavour", "elizabeth", "ویکرانت", "آنادول", "dokdo", "wasl"], "Navy"),
    ("زیردریایی‌ها", "🛥️", ["زیردریایی", "submarine", "kilo", "کیلو", "yasen", "borei", "type 212", "type 214", "scorpène", "اسکورپن", "دلفین", "dolphin", "gotland", "باراک", "taigei", "soryu", "ریاچولو", "بلگورود"], "Navy"),
    ("ناوشکن‌ها", "🚢", ["ناوشکن", "destroyer", "ایجیس", "aegis", "arleigh", "burke", "sejong", "ddg", "kongō", "مایت", "055", "type 055"], "Navy"),
    ("ناوچه‌ها", "🚢", ["ناوچه", "کوروت", "frigate", "corvette", "fremm", "برگامینی", "گوییند", "gowind", "میکو", "mecko", "ادمیرال", "gorshkov", "سریگوشچی", "مولگه", "عاصف", "تغرل", "بني ياس", "فلاخن دریایی"], "Navy"),
    ("شناورهای رزمی", "⛵", [], "Navy"),
    ("موشک‌های کروز", "🚀", ["کروز", "cruise", "کالیبر", "kalibr", "تاماهاوک", "tomahawk", "دلیله", "delilah", "popeye", "پوپ", "نو ", "noor ", "قادر", "qader", "kh-55", "kh-101", "jassm", "براهموس", "سومار", "پاوه", "هداف‌گیری", "توفان"], "Missiles"),
    ("موشک‌های ضدکشتی", "🚀", ["ضدکشتی", "antiship", "anti-ship", "هارپون", "harpoon", "اگزوسه", "exocet", "یاخونت", "yakhont", "اونیکس", "onyx", "موسکیت", "sunburn", "sunburn", "c-802", "c-701", "زربه", "سیلیکوورم"], "Missiles"),
    ("موشک‌های هوا‌به‌هوا", "🚀", ["هوا به هوا", "هوابه‌هوا", "هوا به هوای", "aim-9", "aim-120", "r-27", "r-37", "r-60", "r-73", "r-77", "میکا", "mica", "مستر", "meteor", "pl-8", "pl-10", "pl-15", "دلایل"], "Missiles"),
    ("موشک‌های هوا‌به‌زمین", "🚀", ["هوا به زمین", "هوابه‌زمین", "agm-", "بریمستون", "brimstone", "kh-2", "kh-3", "ماسکو", "مسیل"], "Missiles"),
    ("موشک‌های بالستیک پیشرفته", "🚀", ["هایپرسونیک", "hypersonic", "فتاح", "fattah", "اوانگارد", "avangard", "کینژال", "kinzhal", "زرکون", "zircon", "prompt"], "Missiles"),
    ("موشک‌های بالستیک دوربرد", "🚀", ["قاره‌پیمای", "intercontinental", "icbm", "sarmat", "سارمات", "topol", "hwasong", "مینتمان", "peacekeeper"], "Missiles"),
    ("موشک‌های بالستیک میان‌برد", "🚀", ["اسکندر", "iskander", "شهاب", "shahab", "غادر", "ghadr", "عماد", "emad", "سجیل", "sejjil", "خرمشهر", "khorramshahr", "قدر", "بدر", "pukguksong", "kn-", " Musudan"], "Missiles"),
    ("موشک‌های بالستیک کوتاه‌برد", "🚀", [], "Missiles"),
    ("سامانه‌های پدافندی", "🛡️", [], "Air Defense"),
]

_UNIT_BY_CATEGORY = {k: v[1] for k, v in config.ASSET_CATEGORIES.items()}


def _split_emoji(label: str, default_emoji: str = "📦"):
    """جداکردن ایموجی ابتدای یک برچسب از متن آن.

    نام‌های config معمولاً به شکل «🛢️ پالایشگاه نفت» هستند؛ اگر ایموجی
    جداگانه‌ای هم کنارشان بگذاریم، خروجی «🏗️ 🛢️ پالایشگاه نفت» می‌شود.
    خروجی: (متن بدون ایموجی، ایموجی)
    """
    label = (label or "").strip()
    parts = label.split(" ", 1)
    if len(parts) == 2 and parts[0] and not parts[0][0].isalnum():
        return parts[1].strip(), parts[0]
    return label, default_emoji


def classify_subcat(asset: dict):
    """تشخیص زیردسته نمایشی + ایموجی برای یک دارایی."""
    cat = asset.get("category", "")
    text = f"{asset.get('equipment_name', '')} {asset.get('equipment_key', '')}".lower().replace("\u200c", " ")
    for label, emoji, hints, base in _SUBCAT_RULES:
        if cat != base:
            continue
        if not hints or any(h in text for h in hints):
            return label, emoji
    # هیچ زیردسته‌ای تطبیق نخورد → برچسب دسته‌ی اصلی.
    # برچسب‌های config خودشان ایموجی دارند («🚛 نیروی زمینی»)، پس ایموجی را
    # از خودشان بیرون می‌کشیم تا «📦 🚛 نیروی زمینی» تولید نشود.
    return _split_emoji(config.ASSET_CATEGORIES.get(cat, (cat, "تجهیز"))[0])


def to_english_digits(text: str) -> str:
    return str(text).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789"))




# ---------- پارسر متن گزارش استاندارد (ثبت سریع) ----------
def _clean_str(t):
    t = to_english_digits(str(t)).translate(str.maketrans('يک', 'یک')).lower()
    t = re.sub(r'\([^)]*\)', ' ', t)
    t = re.sub(r'\[[^\]]*\]', ' ', t)
    t = re.sub(r'[-_–—:،,./«»*#]', ' ', t)
    t = t.replace('‌', ' ')
    return re.sub(r'\s+', ' ', t).strip()

_PREFIXES = [
    'سامانه پدافندی', 'سامانه موشکی', 'سامانه پدافند', 'سامانه',
    'موشک بالستیک میان برد', 'موشک بالستیک دوربرد', 'موشک بالستیک کوتاه برد',
    'موشک بالستیک هایپرسونیک', 'موشک بالستیک', 'موشک کروز', 'موشک ضدکشتی', 'موشک ضدزره', 'موشک',
    'جنگنده نسل ۵', 'جنگنده نسل پنجم', 'جنگنده بمب افکن', 'جنگنده برتری هوایی', 'جنگنده چندمنظوره', 'جنگنده',
    'هواپیمای ترابری', 'هواپیمای سوخت رسان', 'هواپیمای شناسایی', 'هواپیمای آواکس', 'هواپیمای',
    'بمب افکن استراتژیک', 'بمب افکن',
    'بالگرد تهاجمی', 'بالگرد ترابری', 'بالگرد',
    'پهپاد انتحاری', 'پهپاد شناسایی', 'پهپاد رزمی', 'پهپاد',
    'تانک اصلی میدان نبرد', 'تانک',
    'خودرو رزمی پیاده نظام', 'خودروی زرهی', 'خودرو رزمی', 'خودرو زرهی', 'نفربر زرهی', 'نفربر',
    'توپ خودکششی', 'توپخانه خودکششی', 'توپخانه', 'توپ',
    'راکت انداز چندگانه', 'راکت انداز',
    'ناو هواپیمابر', 'ناو بالگردبر', 'ناوشکن', 'ناوچه موشک انداز', 'ناوچه', 'زیردریایی', 'شناور تندرو', 'شناور'
]

def _strip_prefix(t):
    for p in sorted(_PREFIXES, key=len, reverse=True):
        p_clean = _clean_str(p)
        if t.startswith(p_clean + ' '):
            return t[len(p_clean):].strip()
    return t

def _norm_name(t):
    return _clean_str(t)


def match_country_by_name(name_part: str):
    """تطبیق نام کشور از متن گزارش با کشورهای واقعی بازی."""
    if not name_part:
        return None
    q = _clean_str(name_part)
    if len(q) < 2:
        return None
    best, best_len = None, 0
    for c in db.get_all_countries():
        n = _clean_str(c.get('name') or '')
        k = _clean_str(c.get('country_key') or '')
        if not n:
            continue
        if q == n or q == k:
            return c
        if (q in n or n in q or (k and (q in k or k in q))) and len(n) > best_len:
            best, best_len = c, len(n)
    return best


# واژه‌های عمومی که به‌تنهایی هیچ تجهیزی را مشخص نمی‌کنند.
# اگر تنها اشتراک دو نام یکی از این‌ها باشد، تطبیق نباید انجام شود
# (وگرنه «جنگنده رافال» به «جنگنده F-16» تطبیق می‌خورد و از انبار اشتباه کسر می‌شود).
_GENERIC_TOKENS = frozenset({
    'های', 'ها', 'ای', 'در', 'به', 'با', 'و', 'از',
    'جنگنده', 'هواپیما', 'هواپیمای', 'بمب', 'افکن', 'بمب‌افکن', 'بالگرد', 'پهپاد',
    'موشک', 'موشکی', 'سامانه', 'پدافند', 'پدافندی', 'تانک', 'خودرو', 'خودروی',
    'زرهی', 'نفربر', 'توپ', 'توپخانه', 'راکت', 'انداز', 'ناو', 'ناوشکن', 'ناوچه',
    'زیردریایی', 'شناور', 'کروز', 'بالستیک', 'ضدکشتی', 'رزمی', 'تهاجمی', 'ترابری',
    'شناسایی', 'استراتژیک', 'سنگین', 'سبک', 'اصلی', 'میدان', 'نبرد', 'نسل',
    'chip', 'fighter', 'jet', 'tank', 'missile', 'radar', 'drone',
})


def _significant_tokens(text: str):
    """توکن‌های معنادار یک نام: عمومی‌ها حذف، بقیه نگه داشته می‌شوند."""
    return {w for w in text.split() if len(w) >= 2 and w not in _GENERIC_TOKENS}


def _has_distinctive_overlap(q_tokens, c_tokens) -> bool:
    """آیا دو نام حداقل یک نشانگر اختصاصی مشترک دارند؟

    نشانگر اختصاصی = توکنی که در فهرست واژه‌های عمومی نیست
    (مثل «رافال»، «f-16»، «تامکت»، «373»).
    """
    return bool(q_tokens & c_tokens)


def match_asset_by_name(name: str, assets: list):
    """تطبیق هوشمند و چندلایه‌ای نام تجهیز با موجودی انبار.

    قانون طلایی: هیچ تطبیقی صرفاً بر پایه‌ی واژه‌های عمومی («جنگنده»، «موشک»، …)
    انجام نمی‌شود؛ باید دست‌کم یک نشانگر اختصاصی مشترک وجود داشته باشد.
    """
    q_raw = _clean_str(name)
    if len(q_raw) < 2:
        return None
    q_stripped = _strip_prefix(q_raw)
    q_tokens = set(q_raw.split()) | set(q_stripped.split())
    q_sig_tokens = _significant_tokens(q_raw) | _significant_tokens(q_stripped)

    best = None
    best_score = 0

    for a in assets:
        candidates = [
            _clean_str(a.get('equipment_name') or ''),
            _clean_str(a.get('equipment_key') or ''),
        ]
        candidates += [_strip_prefix(c) for c in candidates if c]

        for c in candidates:
            if not c:
                continue
            c_sig_tokens = _significant_tokens(c)
            # 1. تطبیق دقیق کل نام
            if q_raw == c or q_stripped == c:
                score = 1000 + len(c)
            # 2. دربرگیری زیررشته — فقط اگر نشانگر اختصاصی مشترک هم داشته باشند
            elif (q_stripped in c or c in q_stripped) and _has_distinctive_overlap(q_sig_tokens, c_sig_tokens):
                score = 500 + len(min(q_stripped, c, key=len))
            elif (q_raw in c or c in q_raw) and _has_distinctive_overlap(q_sig_tokens, c_sig_tokens):
                score = 400 + len(min(q_raw, c, key=len))
            else:
                # 3. تطبیق واژگانی روی نشانگرهای اختصاصی (مثل F-14, 373, 136)
                inter = q_sig_tokens & c_sig_tokens
                if inter:
                    distinctive = sum(20 for t in inter if any(ch.isalnum() for ch in t))
                    score = len(inter) * 50 + distinctive
                else:
                    score = 0

            if score > best_score:
                best = a
                best_score = score

    return best if best_score >= 50 else None


def match_strategic_resource(name: str):
    """تطبیق نام با ذخایر استراتژیک (اورانیوم، سوخت هسته‌ای، کلاهک اتمی، میکروچیپ، طلا)."""
    q = _clean_str(name)
    if not q or len(q) < 2:
        return None

    # کلاهک هسته‌ای / اتمی
    if any(w in q for w in ("کلاهک هسته", "کلاهک اتم", "بمب اتم", "کلاهک بازدارنده", "کلاهک")):
        return {"key": "__warheads__", "name": "کلاهک راهبردی هسته‌ای", "special": "warheads",
                "category": "Strategic", "subcat": "سلاح هسته‌ای", "emoji": "🚀", "unit": "عدد"}

    # کیک زرد / اورانیوم خام
    if any(w in q for w in ("کیک زرد", "سنگ اورانیوم", "اورانیوم خام", "اورانیوم", "ذخایر اورانیوم")):
        return {"key": "__uranium_ore__", "name": "ذخایر اورانیوم (کیک زرد)", "special": "uranium_ore",
                "category": "Strategic", "subcat": "منابع راهبردی", "emoji": "☢️", "unit": "تن"}

    # سوخت هسته‌ای / غنی‌شده ۳.۵٪
    if any(w in q for w in ("سوخت هسته", "میله سوخت", "سوخت ۳", "اورانیوم ۳", "سوخت نیروگاه")):
        return {"key": "__nuclear_fuel__", "name": "سوخت هسته‌ای غنی‌شده (۳.۵٪)", "special": "nuclear_fuel",
                "category": "Strategic", "subcat": "منابع راهبردی", "emoji": "🟢", "unit": "کیلوگرم"}

    # ایزوتوپ‌های پزشکی و سوخت ۲۰٪
    if any(w in q for w in ("ایزوتوپ", "رادیودارو", "سوخت ۲۰", "اورانیوم ۲۰")):
        return {"key": "__medical_isotopes__", "name": "ایزوتوپ پزشکی و سوخت ۲۰٪", "special": "medical_isotopes",
                "category": "Strategic", "subcat": "منابع راهبردی", "emoji": "🟡", "unit": "کیلوگرم"}

    # اورانیوم ۶۰٪
    if any(w in q for w in ("اورانیوم ۶۰", "سوخت ۶۰", "غنای ۶۰")):
        return {"key": "__enriched_60__", "name": "اورانیوم غنی‌شده ۶۰٪", "special": "enriched_60",
                "category": "Strategic", "subcat": "منابع راهبردی", "emoji": "🟠", "unit": "کیلوگرم"}

    # اورانیوم تسلیحاتی ۹۰٪
    if any(w in q for w in ("اورانیوم ۹۰", "سوخت ۹۰", "اورانیوم تسلیحاتی", "غنای ۹۰")):
        return {"key": "__weapons_grade_90__", "name": "اورانیوم تسلیحاتی ۹۰٪", "special": "weapons_grade_90",
                "category": "Strategic", "subcat": "منابع راهبردی", "emoji": "🔴", "unit": "کیلوگرم"}

    # میکروچیپ / تراشه
    if any(w in q for w in ("میکروچیپ", "تراشه", "نیمه هادی", "چیپست", "چیپ")):
        return {"key": "__microchips__", "name": "تراشه و میکروچیپ", "special": "microchips",
                "category": "Strategic", "subcat": "فناوری و قطعات", "emoji": "💻", "unit": "عدد"}

    # عناوین انسانی (فرمانده/سران) هرگز منبع راهبردی نیستند.
    # مثلاً «مدیر سازمان اطلاعات» نباید با «طلا» داخل «اطلاعات» تطبیق بخورد.
    if re.search(r"فرمانده|رئیس|ریاست|مدیر|سرتیپ|سرلشکر|امیر|ژنرال|وزیر|سخنگو|معاون", q):
        return None

    # طلا — با مرز واژه، تا زیررشته‌ی کلماتی مثل «اطلاعات» گرفته نشود
    if re.search(r"(?:^|\s)(?:شمش\s+)?طلا(?:\s|$)", q) or "شمش طلا" in q:
        return {"key": "__gold__", "name": "شمش طلا", "special": "gold",
                "category": "Strategic", "subcat": "ذخایر مالی", "emoji": "🪙", "unit": "شمش"}

    return None


# واژه‌های عمومیِ عناوین فرماندهی که به‌تنهایی هیچ تمایزی ایجاد نمی‌کنند.
# («فرمانده» در لیست کلیدواژه‌ها باعث می‌شد هر عنوانی به اولین فرمانده بچسبد.)
_CMD_STOPWORDS = {
    "فرمانده", "فرماندهی", "رئیس", "ریاست", "مدیر", "مدیریت", "سازمان", "ستاد",
    "کل", "نیروی", "نیروهای", "نیرو", "ارتش", "سپاه", "وزیر", "وزارت", "معاون",
    "امیر", "سرلشکر", "سرتیپ", "ژنرال", "و", "کشور", "ملی", "مسلح", "پاسداران",
}


def _cmd_tokens(text: str):
    """توکن‌های معنادار یک عنوان فرماندهی (بدون واژه‌های عمومی)."""
    return {w for w in _clean_str(text).split() if len(w) >= 3 and w not in _CMD_STOPWORDS}


def match_commander(name: str, commanders: list):
    """بهترین فرماندهٔ فعالِ منطبق با نام را برمی‌گرداند (یا None).

    به‌جای «اولین تطبیق»، امتیازدهی می‌کند تا دو عنوان متفاوت
    (مثلاً «فرمانده کل سپاه» و «فرمانده نیروی هوافضا») یکی نشوند.
    """
    q = _clean_str(name)
    if len(q) < 4:
        return None
    q_tokens = _cmd_tokens(name)
    best, best_score = None, 0
    for cm in commanders or []:
        if cm["status"] != "active":
            continue
        t = _clean_str(cm["title"])
        c_tokens = _cmd_tokens(cm["title"])
        if q == t:
            return cm
        score = 0
        if q in t or t in q:
            score = 100 + len(q)
        else:
            # تطبیق پیشوندی تا «هوافضا» و «هوافضای» یکی حساب شوند
            shared = set()
            for qt in q_tokens:
                for ct in c_tokens:
                    if qt == ct or (len(qt) >= 4 and len(ct) >= 4 and (qt.startswith(ct) or ct.startswith(qt))):
                        shared.add(qt)
                        break
            if shared:
                # نسبت اشتراک به کوچک‌ترین مجموعه، تا عنوان‌های پرکلمه امتیاز الکی نگیرند
                score = int(100 * len(shared) / max(1, min(len(q_tokens), len(c_tokens))))
                if score < 50:
                    score = 0
        if score > best_score:
            best, best_score = cm, score
    return best


def match_building(name: str, country_id: int):
    """تطبیق نام با ساختمان‌های «مالکیت‌دار» کشور از فروشگاه (جدول equipment)."""
    q = _clean_str(name)
    if len(q) < 2:
        return None
    owned = db.get_equipment(country_id) or {}

    # نام‌های مستعار رایج زیرساخت‌ها
    aliases = {
        "enrichment_facility": ("غنی سازی", "سانتریفیوژ", "مجتمع غنی سازی", "فردو", "نطنز", "تاسیسات هسته ای", "تاسیسات غنی سازی"),
        "nuclear_plant": ("نیروگاه اتمی", "نیروگاه هسته ای", "راکتور اتمی", "راکتور هسته ای", "بوشهر", "نیروگاه برق اتمی"),
        "uranium_mine": ("معدن اورانیوم", "استخراج اورانیوم", "معدن ساغند", "معدن گچین"),
        "chip_fab": ("کارخانه فب", "کارخانه تراشه", "کارخانه نیمه هادی", "فب نیمه هادی", "تراشه سازی"),
        "oil_refinery": ("پالایشگاه", "پالایشگاه نفت", "تصفیه خانه نفت"),
    }

    for b_key, b_aliases in aliases.items():
        if (owned.get(b_key, 0) or 0) > 0:
            if any(alias in q for alias in b_aliases):
                item = config.ALL_SHOP_ITEMS.get(b_key, {})
                return {'key': b_key, 'name': item.get('name', b_key)}

    best, best_len = None, 0
    for key, qty in owned.items():
        if (qty or 0) <= 0:
            continue
        item = config.ALL_SHOP_ITEMS.get(key)
        if not item:
            continue
        nm = _clean_str(item.get('name', key))
        if (q in nm or nm in q) and len(nm) > best_len:
            best, best_len = {'key': key, 'name': item.get('name', key)}, len(nm)
    return best

def parse_loss_report_text(text: str):
    """استخراج کشور، پایگاه، عملیات، اقلام تجهیزاتی و تلفات انسانی از متن گزارش استاندارد."""
    t = to_english_digits(str(text))
    lines = [ln.strip() for ln in t.splitlines()]
    result = {"country": None, "base": None, "op": "", "items": [], "human": {"mil": 0, "wounded": 0, "civilians": 0}}

    # استخراج نام پایگاه از هدر یا متن گزارش (مثلاً: پایگاه «Desert Shield» یا پایگاه: Desert Shield)
    base_m = re.search(r"پایگاه(?:\s*هوایی|\s*دریایی|\s*نظامی|\s*پیشروی)?\s*[«'\x22]([^»'\x22]+)[»'\x22]", t)
    if not base_m:
        base_m = re.search(r"(?:پایگاه|مقر|پایگاه هوایی|پایگاه دریایی|پایگاه پیشروی)\s*:\s*([^\n\r]+)", t)
    if base_m:
        result["base"] = base_m.group(1).strip()

    # هدر: 📄 تلفات تجهیزات [پرچم] کشور — عملیات «نام» یا 📄 تلفات پایگاه «...»
    for ln in lines[:6]:
        m = re.search(r"تلفات\s*(?:تجهیزات|پایگاه)?\s*(.*)", ln)
        if not m:
            continue
        rest = m.group(1)
        mo = re.search(r"عملیات\s*[«'\x22]([^»'\x22]+)[»'\x22]", rest)
        if mo:
            result["op"] = mo.group(1).strip()
        country_part = re.split(r"عملیات|—|–|-", rest)[0]
        country_part = re.sub(r"پایگاه(?:\s*هوایی|\s*دریایی|\s*نظامی|\s*پیشروی)?\s*[«'\x22][^»'\x22]+[»'\x22]", " ", country_part)
        country_part = re.sub(r"[^\w\s]", " ", country_part, flags=re.UNICODE)
        country_part = re.sub(r"\s+", " ", country_part).strip()
        result["country"] = country_part or None
        break

    # محل شروع بخش انسانی (اقلام تجهیزاتی قبل از آن می‌مانند)
    human_start = len(lines)
    for idx, ln in enumerate(lines):
        if "تلفات انسانی" in ln:
            human_start = idx
            break

    # اقلام تجهیزاتی: «تلفات: [حدود] N واحد» + نزدیک‌ترین خط قبلی معتبر = نام تجهیز
    qty_pat = re.compile(r"^[*•]?\s*تلفات\s*:?\s*(?:حدود|تقریبا[ً]?|نزدیک|~|≈)?\s*([\d,٬]+(?:\.\d+)?)\s*(.*)$")
    skip_markers = ("جمع تلفات", "وضعیت", "📄", "📌", "━━", "👥")
    for i, ln in enumerate(lines[:human_start]):
        m = qty_pat.match(ln)
        if not m:
            continue
        # عدد اعشاری به بالا گرد می‌شود (نصف یک پالایشگاه یعنی یک واحد آسیب‌دیده)
        qty = int(math.ceil(float(m.group(1).replace(",", "").replace("٬", ""))))
        name = None
        for j in range(i - 1, -1, -1):
            prev = lines[j]
            if not prev or set(prev) <= {"-", "—", "━", " ", "*"}:
                continue
            if qty_pat.match(prev):
                continue
            if any(k in prev for k in skip_markers):
                continue
            cleaned = re.sub(r"^[^\wآ-ی]+", "", prev)
            cleaned = cleaned.replace("*", "").strip()
            if cleaned:
                name = cleaned
                break
        if name:
            result["items"].append((name, qty, (m.group(2) or "").strip()))

    # بخش تلفات انسانی
    if human_start < len(lines):
        # خط‌به‌خط پردازش می‌شود تا هر عدد فقط به دسته‌ی خودش نسبت داده شود
        # و ترتیب «۳۲۰ نفر کشته» هم مثل «کشته: ۳۲۰ نفر» درست خوانده شود.
        def _first_number(s):
            mm = re.search(r"([\d,٬]+(?:\.\d+)?)", s)
            if not mm:
                return None
            return int(math.ceil(float(mm.group(1).replace(",", "").replace("٬", ""))))

        for ln in lines[human_start:]:
            if not ln.strip():
                continue
            num = _first_number(ln)
            if num is None:
                continue
            is_civ = re.search(r"غیر\s?نظامی|غیرنظامی|شهروند|مردم", ln)
            is_wounded = re.search(r"مجروح|زخمی", ln)
            is_mil = re.search(r"نظامی|سرباز|پرسنل|نیرو", ln)
            if is_civ:
                result["human"]["civilians"] = result["human"]["civilians"] or num
            elif is_wounded:
                result["human"]["wounded"] = result["human"]["wounded"] or num
            elif is_mil or re.search(r"کشته|شهید|تلفات جانی", ln):
                result["human"]["mil"] = result["human"]["mil"] or num

    # هزینه آماده‌سازی: فقط از بخش «هزینه آماده‌سازی عملیات» خوانده می‌شود.
    # (قبلاً کل متن جارو می‌شد و هر عدد دلاری — مثلاً «خسارت ۸۰۰ میلیون دلاری به بازار»
    #  در توضیحات — به‌اشتباه از خزانه‌ی کشور کسر می‌شد.)
    # بخش هزینه از ابتدای عنوانش تا شروع بخش بعدی (توضیح/وضعیت/تلفات انسانی/...) محدود می‌شود؛
    # وگرنه اعداد دلاری بخش‌های بعدی هم به‌اشتباه به هزینه‌ی عملیات اضافه می‌شوند.
    cost_start = None
    for idx, ln in enumerate(lines):
        if re.search(r"هزینه\s*(?:آماده[\s‌]*سازی|عملیات)", ln):
            cost_start = idx
            break

    cost_end = len(lines)
    if cost_start is not None:
        _section_break = re.compile(r"📌|👥|📄|توضیح|وضعیت|جمع\s*تلفات|یادداشت|ملاحظات")
        for idx in range(cost_start + 1, len(lines)):
            if _section_break.search(lines[idx]):
                cost_end = idx
                break

    def _amounts_with_unit(scope_text, unit_word):
        total = 0
        for mm in re.finditer(r"([\d,٬]+(?:\.\d+)?)\s*(میلیارد|میلیون|هزار)?\s*" + unit_word, scope_text):
            val = float(mm.group(1).replace(",", "").replace("٬", ""))
            mult = {"میلیارد": 1_000_000_000, "میلیون": 1_000_000, "هزار": 1_000}.get(mm.group(2), 1)
            total += int(val * mult)
        return total

    if cost_start is None:
        result["costs"] = {"money": 0, "oil": 0}
    else:
        cost_text = "\n".join(lines[cost_start:cost_end])
        result["costs"] = {
            "money": _amounts_with_unit(cost_text, "دلار"),
            "oil": _amounts_with_unit(cost_text, "بشکه"),
        }
    return result


# ---------- ساخت گزارش استاندارد ----------
# دسته‌بندی اقلام ویژه برای بخش‌بندی صحیح گزارش رسمی
STRATEGIC_SPECIALS = ("warheads", "uranium_ore", "nuclear_fuel", "microchips", "gold")
HUMAN_SPECIALS = ("mil_kia", "wounded", "civ_kia")
COST_SPECIALS = ("money", "oil")


def build_loss_report_text(c_flag, c_name, op_name, items, status_line="🟠 وضعیت: تلفات ثبت شد.", note=None):
    special_items = [it for it in items if it.get("special")]
    items = [it for it in items if not it.get("special")]
    strategic_items = [it for it in special_items if it.get("special") in STRATEGIC_SPECIALS]
    building_items = [it for it in special_items if it.get("special") == "building"]
    human_items = [it for it in special_items if it.get("special") in HUMAN_SPECIALS]
    cost_items = [it for it in special_items if it.get("special") in COST_SPECIALS]
    groups = OrderedDict()
    for it in items:
        groups.setdefault((it.get("subcat", "تجهیزات"), it.get("emoji", "📦")), []).append(it)

    lines = [
        f"📄 تلفات تجهیزات {c_flag} {c_name} — عملیات «{op_name or 'بدون نام'}»",
        "━━━━━━━━━━━━━━━━━━",
    ]
    for (sub, emo), its in groups.items():
        lines.append(f"\n{emo} {sub}\n")
        for it in its:
            lines.append(f"{emo} {it.get('name', it.get('key'))}")
            lines.append(f"تلفات: {format_number(int(it.get('qty', 0) or 0))} {it.get('unit', '')}")
        lines.append("---")

    if groups:
        lines.append("\n📌 جمع تلفات ثبت‌شده:\n")
        totals = OrderedDict()
        units = {}
        for (sub, emo), its in groups.items():
            t = sum(int(x.get("qty", 0) or 0) for x in its)
            totals[(sub, emo)] = t
            units[sub] = its[0].get("unit", "")
        for (sub, emo), t in totals.items():
            lines.append(f"{emo} {sub}: {format_number(t)} {units[sub]}")

    lines.append("\n━━━━━━━━━━━━━━━━━━")
    if strategic_items:
        lines.append("\n☢️ ذخایر و منابع راهبردی\n")
        for it in strategic_items:
            lines.append(
                f"{it.get('emoji', '📦')} {it.get('name')}: "
                f"{format_number(int(it.get('qty', 0) or 0))} {it.get('unit', '')}".rstrip()
            )
    if building_items:
        lines.append("\n🏗️ خسارت ساخت‌سازی\n")
        for it in building_items:
            lines.append(f"{it.get('emoji', '🏗️')} {it.get('name', it.get('key'))}: {format_number(int(it.get('qty', 0) or 0))} واحد")
    if human_items:
        lines.append("\n👥 تلفات انسانی\n")
        for it in human_items:
            lines.append(f"{it.get('emoji', '👤')} {it.get('name')}: {format_number(int(it.get('qty', 0) or 0))} {it.get('unit', 'نفر')}")
    if cost_items:
        lines.append("\n💸 هزینه آماده‌سازی عملیات\n")
        for it in cost_items:
            if it.get("special") == "money":
                lines.append(f"💵 هزینه مالی: {format_number(int(it.get('qty', 0) or 0))} دلار")
            else:
                lines.append(f"🛢️ سوخت مصرفی: {format_number(int(it.get('qty', 0) or 0))} بشکه")
    if note:
        lines.append(f"\n📝 {note}")
    lines.append(status_line)
    return "\n".join(lines)


# ---------- کیبوردهای کمکی ----------
def _kb(rows):
    return InlineKeyboardMarkup(rows)


def _country_picker(title, cb_prefix):
    rows = []
    row = []
    for c in db.get_all_countries():
        row.append(InlineKeyboardButton(f"{c['flag']} {c['name']}", callback_data=f"{cb_prefix}:{c['id']}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("🔙 بازگشت به مدیریت تلفات", callback_data="ls:menu")])
    return title, _kb(rows)


def _cat_picker(cid):
    assets = db.get_country_assets(cid)
    by_cat = {}
    for a in assets:
        by_cat.setdefault(a["category"], []).append(a)
    rows = []
    row = []
    for cat, (label, unit) in config.ASSET_CATEGORIES.items():
        if cat not in by_cat:
            continue
        row.append(InlineKeyboardButton(f"{label} ({len(by_cat[cat])})", callback_data=f"ls:cat:{cid}:{cat}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("🔙 بازگشت به مدیریت تلفات", callback_data="ls:menu")])
    return "🗂 لطفاً دسته تجهیزات را انتخاب کنید:", _kb(rows)


# ---------- منوی اصلی ----------
def is_admin(user_id: int) -> bool:
    """فقط ادمین‌های تعریف‌شده در config حق ثبت/بازگردانی تلفات دارند."""
    return user_id in config.ADMIN_IDS


async def losses_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.answer("⛔ این بخش فقط برای مدیریت بازی است.", show_alert=True)
        return
    await query.answer()
    data = query.data

    if data == "ls:menu":
        text = (
            "💥 *مدیریت تلفات تجهیزات*\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "ثبت، تاریخچه، آمار و بازگردانی تلفات — تعیین نتیجه با مدیریت است، بات فقط ثبت می‌کند.\n\n"
            "یک گزینه را انتخاب کنید:"
        )
        await query.edit_message_text(text, reply_markup=_kb([
            [InlineKeyboardButton("📄 ثبت تلفات (پیست گزارش آماده) — روش اصلی", callback_data="ls:fast")],
            [InlineKeyboardButton("🛠 ثبت دستی تک‌تک تجهیزات (اضطراری)", callback_data="ls:new")],
            [InlineKeyboardButton("📋 تاریخچه تلفات", callback_data="ls:histpick")],
            [InlineKeyboardButton("🔎 جستجوی تلفات", callback_data="ls:search")],
            [InlineKeyboardButton("📊 آمار تلفات کشور", callback_data="ls:statpick")],
            [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")],
        ]), parse_mode="Markdown")
        return

    # ---------- ثبت تلفات ----------
    if data == "ls:new":
        t, kb = _country_picker("1️⃣ کشور متحمل‌شده تلفات را انتخاب کنید:", "ls:country")
        await query.edit_message_text(t, reply_markup=kb)
        return

    if data == "ls:fast":
        context.user_data["admin_awaiting_input"] = {"type": "ls_report_text"}
        await query.edit_message_text(
            "📄 *ثبت سریع تلفات با متن گزارش*\n\n"
            "کل متن گزارش استاندارد را ارسال یا فوروارد کنید.\n"
            "بات به‌صورت خودکار کشور، عملیات، تجهیزات و تعدادها را تشخیص می‌دهد،"
            " با انبار واقعی تطبیق می‌دهد و پیش‌نمایش می‌آورد.\n\n"
            "_خط اول باید شامل نام کشور باشد، مثلاً:_\n"
            "`📄 تلفات تجهیزات 🇦🇪 امارات — عملیات «سایه‌های خاکستری»`",
            reply_markup=_kb([[InlineKeyboardButton("❌ انصراف", callback_data="ls:menu")]]),
            parse_mode="Markdown",
        )
        return

    if data.startswith("ls:country:"):
        cid = int(data.split(":")[2])
        c = db.get_country_by_id(cid)
        if not c:
            await query.edit_message_text("❌ کشور یافت نشد.")
            return
        context.user_data["ls_draft"] = {"cid": cid, "cname": c["name"], "cflag": c["flag"], "op": "", "note": "", "items": []}
        t, kb = _cat_picker(cid)
        await query.edit_message_text(f"1️⃣ کشور: {c['flag']} {c['name']}\n\n2️⃣ {t}", reply_markup=kb)
        return

    if data.startswith("ls:catmenu:"):
        cid = int(data.split(":")[2])
        t, kb = _cat_picker(cid)
        await query.edit_message_text(t, reply_markup=kb)
        return

    if data.startswith("ls:cat:"):
        parts = data.split(":", 3)
        cid, cat = int(parts[2]), parts[3]
        items = [a for a in db.get_country_assets(cid) if a["category"] == cat]
        draft = context.user_data.get("ls_draft", {})
        in_cart = {it["key"]: it["qty"] for it in draft.get("items", [])}
        cat_label, unit = config.ASSET_CATEGORIES.get(cat, (cat, "عدد"))
        rows = []
        for a in items:
            mark = f" [سبد: {format_number(in_cart[a['equipment_key']])}]" if a["equipment_key"] in in_cart else ""
            rows.append([InlineKeyboardButton(
                f"{a['equipment_name']} ({format_number(a['amount'])}){mark}",
                callback_data=f"ls:item:{cid}:{a['equipment_key']}",
            )])
        rows.append([InlineKeyboardButton("🔙 بازگشت به دسته‌ها", callback_data=f"ls:catmenu:{cid}")])
        await query.edit_message_text(
            f"3️⃣ {cat_label} — تجهیز مورد نظر را انتخاب کنید:",
            reply_markup=_kb(rows),
        )
        return

    if data.startswith("ls:item:"):
        parts = data.split(":")
        cid, key = int(parts[2]), parts[3]
        a = db.get_asset_by_key(cid, key)
        if not a:
            await query.edit_message_text("❌ تجهیز یافت نشد.")
            return
        sub, emo = classify_subcat(a)
        context.user_data["admin_awaiting_input"] = {"type": "ls_qty", "cid": cid, "key": key}
        await query.edit_message_text(
            f"4️⃣ مقدار تلفات را به‌صورت عدد ارسال کنید:\n\n"
            f"{emo} *{a['equipment_name']}*\n"
            f"موجودی فعلی: {format_number(a['amount'])}\n"
            f"(۰ = فقط در گزارش ثبت می‌شود بدون کسر موجودی)",
            reply_markup=_kb([[InlineKeyboardButton("❌ انصراف", callback_data=f"ls:catmenu:{cid}")]]),
            parse_mode="Markdown",
        )
        return

    if data == "ls:pop":
        draft = context.user_data.get("ls_draft") or {}
        if draft.get("items"):
            removed = draft["items"].pop()
            await query.edit_message_text(f"➖ «{removed['name']}» از سبد حذف شد.", reply_markup=_cart_kb(draft))
        return

    if data == "ls:to_op":
        draft = context.user_data.get("ls_draft") or {}
        if not draft.get("items"):
            await query.edit_message_text("❌ سبد خالی است؛ اول تجهیز اضافه کنید.")
            return
        context.user_data["admin_awaiting_input"] = {"type": "ls_op"}
        await query.edit_message_text(
            "5️⃣ نام عملیات را ارسال کنید (مثلاً: سایه‌های خاکستری):",
            reply_markup=_kb([[InlineKeyboardButton("❌ انصراف", callback_data="ls:menu")]]),
        )
        return

    if data == "ls:to_note":
        context.user_data["admin_awaiting_input"] = {"type": "ls_note"}
        await query.edit_message_text(
            "6️⃣ توضیح اختیاری را ارسال کنید، یا رد شوید:",
            reply_markup=_kb([[InlineKeyboardButton("⏭️ بدون توضیح", callback_data="ls:skipnote")]]),
        )
        return

    if data == "ls:skipnote":
        context.user_data["admin_awaiting_input"] = None
        draft = context.user_data.get("ls_draft") or {}
        await query.edit_message_text(_preview_text(draft), reply_markup=_kb([
            [InlineKeyboardButton("✅ تأیید نهایی و اعمال تلفات", callback_data="ls:confirm")],
            [InlineKeyboardButton("❌ انصراف", callback_data="ls:menu")],
        ]), parse_mode="Markdown")
        return

    if data == "ls:confirm":
        draft = context.user_data.get("ls_draft") or {}
        if not draft.get("items"):
            await query.edit_message_text("❌ سبد خالی است.")
            return
        ok, rid, err = db.create_loss_report(
            draft["cid"], draft["items"], draft.get("op", ""), draft.get("note", ""), admin_id=user_id
        )
        if not ok:
            await query.edit_message_text(
                f"⛔ *ثبت انجام نشد — هیچ تغییری در موجودی ایجاد نشده است.*\n\n❌ {err}",
                reply_markup=_kb([
                    [InlineKeyboardButton("🔁 اصلاح سبد", callback_data=f"ls:catmenu:{draft['cid']}")],
                    [InlineKeyboardButton("🔙 منوی تلفات", callback_data="ls:menu")],
                ]),
                parse_mode="Markdown",
            )
            return
        report = build_loss_report_text(draft["cflag"], draft["cname"], draft.get("op", ""), draft["items"])

        # بررسی و بازگشایی خودکار تنگه‌ها در صورت انهدام ناوگان کنترل‌کننده
        try:
            reopened = db.auto_check_and_reopen_straits_if_navy_destroyed()
            for r in reopened:
                owner = r["owner"]
                s_info = r["strait_info"]
                s_msg = (
                    f"🌊 **لغو خودکار کنترل بر تنگه استراتژیک!**\n\n"
                    f"کشور {owner['flag']} {owner['name']} به دلیل انهدام یا تضعیف ناوگان دریایی در نبرد "
                    f"(کمتر از ۵ شناور فعال یا ۱۰ میلیون دلار ارزش)، کنترل نظامی خود بر **{s_info['name']}** را از دست داد و این آبراه فوراً بازگشایی شد."
                )
                if owner.get("player_id"):
                    await context.bot.send_message(chat_id=owner["player_id"], text=s_msg, parse_mode="Markdown")
                await news_engine.trigger_strait_news(context.bot, owner, s_info["name"], "open")
        except Exception:
            pass

        # ارسال خودکار فاکتور رسمی تلفات به بازیکن صاحب کشور
        target_country = db.get_country_by_id(draft["cid"])
        player_notified = False
        if target_country and target_country.get("player_id"):
            try:
                player_msg = (
                    f"🚨 **گزارش رسمی ستاد کل — ثبت تلفات و خسارات نبرد**\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"
                    f"{report}\n\n"
                    "⚠️ *اقلام فوق از موجودی انبار، تسلیحات و منابع کشور شما کسر گردید.*"
                )
                await context.bot.send_message(
                    chat_id=target_country["player_id"],
                    text=player_msg,
                    parse_mode="Markdown"
                )
                player_notified = True
            except Exception:
                try:
                    await context.bot.send_message(
                        chat_id=target_country["player_id"],
                        text=player_msg
                    )
                    player_notified = True
                except Exception:
                    pass

        notify_status = "📩 *فاکتور رسمی تلفات برای بازیکن ارسال شد.*" if player_notified else "⚠️ *بازیکن یافت نشد یا ارسال پیام به بازیکن ناموفق بود.*"

        await query.edit_message_text(
            f"✅ *تلفات ثبت شد (گزارش #{rid})*\n{notify_status}\n\n{report}",
            reply_markup=_kb([
                [InlineKeyboardButton("📋 تاریخچه این کشور", callback_data=f"ls:history:{draft['cid']}")],
                [InlineKeyboardButton("📄 ثبت تلفات (پیست گزارش آماده) — روش اصلی", callback_data="ls:fast")],
                [InlineKeyboardButton("🛠 ثبت دستی تک‌تک تجهیزات (اضطراری)", callback_data="ls:new")],
                [InlineKeyboardButton("🔙 منوی تلفات", callback_data="ls:menu")],
            ]),
            parse_mode="Markdown",
        )
        context.user_data["ls_draft"] = None
        context.user_data["admin_awaiting_input"] = None
        return

    # ---------- تاریخچه ----------
    if data == "ls:histpick":
        t, kb = _country_picker("کشور مورد نظر برای مشاهده تاریخچه تلفات:", "ls:history")
        await query.edit_message_text(t, reply_markup=kb)
        return

    if data.startswith("ls:history:"):
        cid = int(data.split(":")[2])
        reports = db.get_loss_reports(cid, limit=15)
        if not reports:
            await query.edit_message_text("📭 هیچ گزارش تلفاتی برای این کشور ثبت نشده است.", reply_markup=_kb([[InlineKeyboardButton("🔙", callback_data="ls:menu")]]))
            return
        rows = []
        for r in reports:
            icon = {"applied": "🟠", "reverted": "↩️"}.get(r["status"], "•")
            dt = (r.get("created_at") or "")[:10]
            rows.append([InlineKeyboardButton(f"{icon} #{r['id']} | {r['operation_name'] or 'بدون نام'} | {dt}", callback_data=f"ls:view:{r['id']}")])
        rows.append([InlineKeyboardButton("🔙 بازگشت", callback_data="ls:menu")])
        await query.edit_message_text("📋 آخرین گزارش‌های تلفات:", reply_markup=_kb(rows))
        return

    if data.startswith("ls:view:"):
        rid = int(data.split(":")[2])
        r = db.get_loss_report_by_id(rid)
        if not r or r["status"] == "deleted":
            await query.edit_message_text("❌ گزارش یافت نشد.", reply_markup=_kb([[InlineKeyboardButton("🔙", callback_data="ls:menu")]]))
            return
        its = json.loads(r["items_json"])
        status_line = {"applied": "🟠 وضعیت: اعمال‌شده", "reverted": "↩️ وضعیت: بازگردانی‌شده"}.get(r["status"], r["status"])
        body = build_loss_report_text(r.get("country_flag", ""), r.get("country_name", ""), r.get("operation_name", ""), its, status_line=status_line)
        meta = f"\n\n👤 ادمین ثبت: `{r.get('admin_id')}` | 🕐 {(r.get('created_at') or '')[:16].replace('T', ' ')}"
        if r.get("note"):
            meta += f"\n📝 {r['note']}"
        rows = []
        if r["status"] == "applied":
            rows.append([
                InlineKeyboardButton("↩️ بازگردانی به موجودی", callback_data=f"ls:revert:{rid}"),
                InlineKeyboardButton("📩 ارسال فاکتور به بازیکن", callback_data=f"ls:resend:{rid}")
            ])
        rows.append([InlineKeyboardButton("🗑️ حذف گزارش", callback_data=f"ls:del:{rid}")])
        rows.append([InlineKeyboardButton("🔙 بازگشت به تاریخچه", callback_data=f"ls:history:{r['country_id']}")])
        await query.edit_message_text(body + meta, reply_markup=_kb(rows), parse_mode="Markdown")
        return

    if data.startswith("ls:resend:"):
        rid = int(data.split(":")[2])
        r = db.get_loss_report_by_id(rid)
        if not r or r["status"] == "deleted":
            await query.answer("❌ گزارش یافت نشد.", show_alert=True)
            return

        c = db.get_country_by_id(r["country_id"])
        if not c or not c.get("player_id"):
            await query.answer("❌ شناسه عددی بازیکن یافت نشد.", show_alert=True)
            return

        its = json.loads(r["items_json"])
        status_line = {"applied": "🟠 وضعیت: اعمال‌شده", "reverted": "↩️ وضعیت: بازگردانی‌شده"}.get(r["status"], r["status"])
        body = build_loss_report_text(r.get("country_flag", ""), r.get("country_name", ""), r.get("operation_name", ""), its, status_line=status_line)
        
        player_msg = (
            f"🚨 **گزارش رسمی ستاد کل — ثبت تلفات و خسارات نبرد**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"{body}\n\n"
            "⚠️ *اقلام فوق از موجودی انبار، تسلیحات و منابع کشور شما کسر گردید.*"
        )
        try:
            await context.bot.send_message(chat_id=c["player_id"], text=player_msg, parse_mode="Markdown")
            await query.answer(f"✅ فاکتور با موفقیت به رهبر کشور {c['name']} ارسال شد!", show_alert=True)
        except Exception as ex:
            try:
                await context.bot.send_message(chat_id=c["player_id"], text=player_msg)
                await query.answer(f"✅ فاکتور به رهبر کشور {c['name']} ارسال شد!", show_alert=True)
            except Exception as ex2:
                await query.answer(f"❌ خطا در ارسال پیام به بازیکن: {ex2}", show_alert=True)
        return

    if data.startswith("ls:revert:"):
        rid = int(data.split(":")[2])
        ok, err = db.revert_loss_report(rid)
        msg = "↩️ گزارش بازگردانی شد؛ تجهیزات به موجودی کشور برگشت." if ok else f"❌ {err}"
        await query.edit_message_text(msg, reply_markup=_kb([[InlineKeyboardButton("📋 تاریخچه", callback_data="ls:histpick")], [InlineKeyboardButton("🔙", callback_data="ls:menu")]]))
        return

    if data.startswith("ls:del:"):
        rid = int(data.split(":")[2])
        await query.edit_message_text(
            "⚠️ حذف گزارش، موجودی را نیز بازگردانی می‌کند و از تاریخچه پاک می‌شود.\nمطمئنی؟",
            reply_markup=_kb([
                [InlineKeyboardButton("🗑️ بله، حذف کن", callback_data=f"ls:delok:{rid}")],
                [InlineKeyboardButton("❌ انصراف", callback_data=f"ls:view:{rid}")],
            ]),
        )
        return

    if data.startswith("ls:delok:"):
        rid = int(data.split(":")[2])
        ok, err = db.delete_loss_report(rid)
        msg = "🗑️ گزارش حذف و موجودی بازگردانی شد." if ok else f"❌ {err}"
        await query.edit_message_text(msg, reply_markup=_kb([[InlineKeyboardButton("🔙", callback_data="ls:menu")]]))
        return

    # ---------- آمار ----------
    if data == "ls:statpick":
        t, kb = _country_picker("کشور مورد نظر برای مشاهده آمار تلفات:", "ls:statsc")
        await query.edit_message_text(t, reply_markup=kb)
        return

    if data.startswith("ls:statsc:"):
        cid = int(data.split(":")[2])
        c = db.get_country_by_id(cid)
        s = db.get_loss_stats(cid)
        lines = [f"📊 *آمار تلفات {c['flag']} {c['name']}*", "━━━━━━━━━━━━━━━━━━"]
        lines.append(f"• گزارش‌های فعال (اعمال‌شده): {s['reports']}")
        lines.append(f"• بازگردانی‌شده: {s['reverted']}  |  مجموع ثبت‌ها: {s.get('total', s['reports'] + s['reverted'])}")
        if s["by_subcat"]:
            lines.append("\n📌 مجموع به تفکیک دسته:")
            for sub, total in s["by_subcat"].most_common():
                lines.append(f"  • {sub}: {format_number(total)}")
        if s["by_equip"]:
            lines.append("\n🏆 بیشترین تلفات:")
            for name, total in s["by_equip"].most_common(10):
                lines.append(f"  • {name}: {format_number(total)}")
        if not s["by_subcat"]:
            lines.append("\n📭 تلفات فعالی ثبت نشده است.")
        await query.edit_message_text("\n".join(lines), reply_markup=_kb([[InlineKeyboardButton("🔙", callback_data="ls:menu")]]), parse_mode="Markdown")
        return

    # ---------- جستجو ----------
    if data == "ls:search":
        context.user_data["admin_awaiting_input"] = {"type": "ls_search"}
        await query.edit_message_text(
            "🔎 عبارت جستجو را ارسال کنید (نام عملیات، تجهیز یا توضیح):",
            reply_markup=_kb([[InlineKeyboardButton("❌ انصراف", callback_data="ls:menu")]]),
        )
        return


def _cart_kb(draft):
    rows = [
        [InlineKeyboardButton("➕ افزودن تجهیز دیگر", callback_data=f"ls:catmenu:{draft['cid']}")],
        [InlineKeyboardButton("➖ حذف آخرین قلم", callback_data="ls:pop")],
        [InlineKeyboardButton("➡️ ادامه (نام عملیات)", callback_data="ls:to_op")],
        [InlineKeyboardButton("🗑️ خالی‌کردن سبد و شروع مجدد", callback_data=f"ls:country:{draft['cid']}")],
    ]
    return _kb(rows)


def _preview_text(draft):
    items = draft.get("items", [])
    if not items:
        return "سبد خالی است."
    base_line = f"\n📍 پایگاه هدف: *{draft['base_name']}*" if draft.get("base_name") else ""
    lines = [f"7️⃣ *پیش‌نمایش گزارش تلفات*", "━━━━━━━━━━━━━━━━━━",
             f"کشور: {draft['cflag']} {draft['cname']}{base_line}",
             f"عملیات: «{draft.get('op') or 'بدون نام'}»", ""]
    for it in items:
        lines.append(f"• {it['emoji']} {it['name']} — تلفات: {format_number(it['qty'])} {it['unit']}")
    if draft.get("note"):
        lines.append(f"\n📝 {draft['note']}")
    lines.append("\n8️⃣ در صورت تأیید، همه‌ی اقلام به‌صورت اتمی اعمال می‌شوند.")
    return "\n".join(lines)


# ---------- ورودی‌های متنی (تعداد، نام عملیات، توضیح، جستجو) ----------
async def handle_losses_input(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int, input_state: dict):
    if not is_admin(user_id):
        return
    text = (update.message.text or "").strip()
    t = input_state.get("type")

    if t == "ls_qty":
        raw = to_english_digits(text).replace(",", "").replace("٬", "")
        if not re.fullmatch(r"\d+", raw):
            await update.message.reply_text("❌ لطفاً فقط یک عدد صحیح غیرمنفی بفرست (مثلاً 3 یا ۰).")
            return
        qty = int(raw)
        cid, key = input_state["cid"], input_state["key"]
        a = db.get_asset_by_key(cid, key)
        if not a:
            await update.message.reply_text("❌ تجهیز یافت نشد؛ از منو دوباره انتخاب کن.")
            return
        draft = context.user_data.get("ls_draft")
        if not draft or draft.get("cid") != cid:
            c = db.get_country_by_id(cid)
            draft = {"cid": cid, "cname": c["name"], "cflag": c["flag"], "op": "", "note": "", "items": []}
            context.user_data["ls_draft"] = draft
        sub, emo = classify_subcat(a)
        existing = next((x for x in draft["items"] if x["key"] == key), None)
        if existing:
            existing["qty"] += qty
            name_line = existing
        else:
            item = {"key": key, "name": a["equipment_name"], "category": a["category"],
                    "subcat": sub, "emoji": emo, "unit": _UNIT_BY_CATEGORY.get(a["category"], "عدد"), "qty": qty}
            draft["items"].append(item)
            name_line = item
        context.user_data["admin_awaiting_input"] = None
        await update.message.reply_text(
            f"🧺 سبد تلفات ({draft['cflag']} {draft['cname']}):\n\n" + "\n".join(
                f"• {x['emoji']} {x['name']} — {format_number(x['qty'])} {x['unit']}" for x in draft["items"]
            ),
            reply_markup=_cart_kb(draft),
        )
        return

    if t == "ls_op":
        draft = context.user_data.get("ls_draft") or {}
        draft["op"] = text[:80]
        context.user_data["admin_awaiting_input"] = {"type": "ls_note"}
        await update.message.reply_text(
            f"✅ عملیات: «{draft['op']}»\n\n6️⃣ توضیح اختیاری را بفرست یا رد شو:",
            reply_markup=_kb([[InlineKeyboardButton("⏭️ بدون توضیح", callback_data="ls:skipnote")]]),
        )
        return

    if t == "ls_note":
        draft = context.user_data.get("ls_draft") or {}
        draft["note"] = text[:300]
        context.user_data["admin_awaiting_input"] = None
        await update.message.reply_text(_preview_text(draft), reply_markup=_kb([
            [InlineKeyboardButton("✅ تأیید نهایی و اعمال تلفات", callback_data="ls:confirm")],
            [InlineKeyboardButton("❌ انصراف", callback_data="ls:menu")],
        ]), parse_mode="Markdown")
        return

    if t == "ls_report_text":
        context.user_data["admin_awaiting_input"] = None
        parsed = parse_loss_report_text(text)
        if not parsed["items"]:
            await update.message.reply_text(
                "❌ هیچ قلم تلفاتی در متن پیدا نشد. هر قلم باید به شکل زیر باشد:\n"
                "«نام تجهیز» در یک خط و «تلفات: عدد واحد» در خط بعدی.",
                reply_markup=_kb([[InlineKeyboardButton("🔙", callback_data="ls:menu")]]),
            )
            return
        country = match_country_by_name(parsed["country"])
        if not country:
            await update.message.reply_text(
                f"❌ کشور «{parsed['country'] or '?'}» در بازی شناسایی نشد.\n"
                "مطمئن شو نام کشور در خط اول گزارش آمده است.",
                reply_markup=_kb([[InlineKeyboardButton("🔁 دوباره متن بفرست", callback_data="ls:fast")]]),
            )
            return

        # بررسی تطبیق پایگاه نظامی اختصاصی در صورت ذکر نام پایگاه در گزارش
        base_match = None
        if parsed.get("base"):
            country_bases = db.get_bases(owner_id=country["id"])
            clean_bquery = _clean_str(parsed["base"])
            for b in country_bases:
                b_clean = _clean_str(b["name"])
                if b_clean in clean_bquery or clean_bquery in b_clean:
                    base_match = b
                    break

        if base_match:
            assets = db.get_base_assets(base_match["id"])
            base_id = base_match["id"]
            base_name = base_match["name"]
        else:
            assets = db.get_country_assets(country["id"])
            base_id = None
            base_name = None

        matched, unmatched = [], []
        for name, qty, unit in parsed["items"]:
            a = match_asset_by_name(name, assets)
            if a:
                existing = next((x for x in matched if x["key"] == a["equipment_key"]), None)
                if existing:
                    existing["qty"] += qty
                    continue
                sub, emo = classify_subcat(a)
                item_dict = {
                    "key": a["equipment_key"], "name": a["equipment_name"], "category": a.get("category", ""),
                    "subcat": sub, "emoji": emo,
                    "unit": _UNIT_BY_CATEGORY.get(a.get("category", ""), "عدد"), "qty": qty,
                }
                if base_id:
                    item_dict["base_id"] = base_id
                    item_dict["base_name"] = base_name
                matched.append(item_dict)
                continue

            # تطبیق با ذخایر استراتژیک (اورانیوم، سوخت، کلاهک، میکروچیپ، طلا)
            res_match = match_strategic_resource(name)
            if res_match:
                res_match["qty"] = qty
                matched.append(res_match)
                continue

            # تطبیق با سران و فرماندهان نظامی کشور
            cmd_list = db.get_country_commanders(country["id"])
            # فرماندهانی که در همین گزارش قبلاً ترور شده‌اند دوباره انتخاب نشوند
            _taken = {m.get("cmd_key") for m in matched if m.get("special") == "commander"}
            cmd_match = match_commander(name, [c for c in cmd_list if c["key"] not in _taken])
            if cmd_match:
                matched.append({
                    "key": f"__cmd_{cmd_match['key']}__",
                    "name": f"{cmd_match['title']} (ترور / شهید)",
                    "special": "commander",
                    "cmd_key": cmd_match["key"],
                    "category": "Command",
                    "subcat": "سران نظامی",
                    "emoji": "🎖️",
                    "unit": "نفر",
                    "qty": qty
                })
                continue

            # تطبیق با ساختمان‌ها و صنایع
            b = match_building(name, country["id"])
            if b:
                b_name, b_emoji = _split_emoji(b["name"], "🏗️")
                matched.append({"key": b["key"], "name": b_name, "special": "building",
                                "category": "Infrastructure", "subcat": "ساخت‌سازی", "emoji": b_emoji,
                                "unit": "واحد", "qty": qty})
                continue

            unmatched.append(name)
        if not matched:
            await update.message.reply_text(
                "❌ هیچ‌کدام از تجهیزات متن، در انبار این کشور پیدا نشد:\n" + "\n".join(f"• {n}" for n in unmatched),
                reply_markup=_kb([[InlineKeyboardButton("🔁 دوباره", callback_data="ls:fast")]]),
            )
            return
        costs = parsed.get("costs") or {}
        if costs.get("money", 0) and costs["money"] > 0:
            matched.append({"key": "__cost_money__", "name": "هزینه آماده‌سازی (خزانه)", "special": "money",
                            "category": "Cost", "subcat": "هزینه عملیات", "emoji": "💵", "unit": "دلار", "qty": int(costs["money"])})
        if costs.get("oil", 0) and costs["oil"] > 0:
            matched.append({"key": "__cost_oil__", "name": "سوخت و لجستیک (نفت)", "special": "oil",
                            "category": "Cost", "subcat": "هزینه عملیات", "emoji": "🛢️", "unit": "بشکه", "qty": int(costs["oil"])})
        h = parsed.get("human") or {}
        if h.get("mil", 0) and h["mil"] > 0:
            matched.append({"key": "__personnel_mil__", "name": "نیروهای نظامی (کشته)", "special": "mil_kia",
                            "category": "Personnel", "subcat": "تلفات انسانی", "emoji": "🪖", "unit": "نفر", "qty": int(h["mil"])})
        if h.get("wounded", 0) and h["wounded"] > 0:
            matched.append({"key": "__personnel_wounded__", "name": "مجروحان", "special": "wounded",
                            "category": "Personnel", "subcat": "تلفات انسانی", "emoji": "🏥", "unit": "نفر", "qty": int(h["wounded"])})
        if h.get("civilians", 0) and h["civilians"] > 0:
            matched.append({"key": "__personnel_civ__", "name": "غیرنظامیان (کشته)", "special": "civ_kia",
                            "category": "Personnel", "subcat": "تلفات انسانی", "emoji": "👤", "unit": "نفر", "qty": int(h["civilians"])})
        draft = {
            "cid": country["id"], "cname": country["name"], "cflag": country["flag"],
            "op": parsed["op"], "note": "", "base_name": base_name, "items": matched,
        }
        if unmatched:
            draft["note"] = "اقلام شناخته‌نشده (ثبت نشد): " + "، ".join(unmatched)
        context.user_data["ls_draft"] = draft
        preview = _preview_text(draft)
        if unmatched:
            preview += "\n\nℹ️ _اقلام زیر برای این کشور یافت نشد و نادیده گرفته شدند:_\n" + "\n".join(f"• {n}" for n in unmatched)
        await update.message.reply_text(preview, reply_markup=_kb([
            [InlineKeyboardButton("✅ تأیید و اعمال تلفات", callback_data="ls:confirm")],
            [InlineKeyboardButton("🔁 متن جدید", callback_data="ls:fast")],
            [InlineKeyboardButton("❌ انصراف", callback_data="ls:menu")],
        ]), parse_mode="Markdown")
        return

    if t == "ls_search":
        context.user_data["admin_awaiting_input"] = None
        results = db.get_loss_reports(query=text, limit=12)
        if not results:
            await update.message.reply_text(f"🔎 نتیجه‌ای برای «{text}» یافت نشد.", reply_markup=_kb([[InlineKeyboardButton("🔙", callback_data="ls:menu")]]))
            return
        rows = []
        for r in results:
            icon = {"applied": "🟠", "reverted": "↩️"}.get(r["status"], "•")
            rows.append([InlineKeyboardButton(
                f"{icon} #{r['id']} | {r.get('country_flag','')} {r.get('country_name','')} | {r['operation_name'] or 'بدون نام'}",
                callback_data=f"ls:view:{r['id']}",
            )])
        rows.append([InlineKeyboardButton("🔙", callback_data="ls:menu")])
        await update.message.reply_text(f"🔎 نتایج جستجوی «{text}»:", reply_markup=_kb(rows))
        return


def get_losses_handlers():
    return [CallbackQueryHandler(losses_callback_handler, pattern=r"^ls:")]
