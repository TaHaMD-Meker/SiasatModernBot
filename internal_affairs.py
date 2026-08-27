# -*- coding: utf-8 -*-
"""موتور جمعیت پویا، مالیات، ناآرامی و بحران‌های «سیاست مدرن».

چرخه‌ی هسته:
    جمعیت تغییر می‌کند → مالیات تغییر می‌کند → رضایت تغییر می‌کند →
    ناآرامی شکل می‌گیرد → بحران ایجاد می‌شود → بازیکن واکنش نشان می‌دهد →
    نتیجه روی جمعیت، خزانه، اقتصاد و تورنومنت اثر می‌گذارد.

اصول طراحی (عمداً محافظه‌کارانه):
* کل سیستم پشت یک کلید اصلی خاموش است و فقط ادمین آن را روشن می‌کند.
* بحران تصادفی کلید جداگانه‌ی خودش را دارد و آن هم پیش‌فرض خاموش است.
* چرخه‌ی روزانه idempotent است: برای هر کشور در هر تاریخ فقط یک‌بار اجرا می‌شود
  (قفل روی UNIQUE(country_id, log_date) و همچنین last_cycle_date).
* هیچ بحرانی بدون مرحله‌ی هشدار اعمال نمی‌شود، مگر بحران داستانی ادمین.
* سیستم هرگز خودش کشوری را حذف یا سلب مالکیت نمی‌کند؛ فقط پرچم «خطر سقوط»
  را بالا می‌برد تا ادمین تصمیم بگیرد.
"""

from __future__ import annotations

import datetime
import json
import logging
import random

import config
import database as db

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# کلیدهای اصلی (پیش‌فرض: خاموش)
# ─────────────────────────────────────────────────────────────────────────────
SETTING_ENABLED = "internal_affairs_enabled"
SETTING_RANDOM_CRISES = "internal_random_crises_enabled"

POPULATION_FLOOR = 100_000
MAX_DAILY_POP_CHANGE_PCT = 0.03      # سقف ±۳٪ تغییر جمعیت در روز
MAX_ACTIVE_CRISES = 2                # هم‌زمان بیش از دو بحران روی یک کشور نه
MAX_SEVERE_CRISES = 1                # و حداکثر یکی از آن‌ها سنگین
CRISIS_SHIELD_DAYS = 2               # مصونیت بعد از پایان بحران سنگین
RANDOM_CRISIS_BASE_CHANCE = 0.06     # شانس پایه‌ی روزانه بحران تصادفی

# ─────────────────────────────────────────────────────────────────────────────
# سیاست‌های مالیاتی
# ─────────────────────────────────────────────────────────────────────────────
TAX_POLICIES = {
    "low": {
        "label": "🕊 مالیات کم",
        "income_mult": 0.65,
        "approval_delta": 2,
        "unrest_delta": -4.0,
        "pop_bonus": 0.0008,
        "desc": "درآمد کمتر، رضایت و رشد جمعیت بیشتر. مناسب دوران آرامش و جذب جمعیت.",
    },
    "normal": {
        "label": "⚖️ مالیات عادی",
        "income_mult": 1.00,
        "approval_delta": 0,
        "unrest_delta": -1.0,
        "pop_bonus": 0.0,
        "desc": "حالت پیش‌فرض کشور. درآمد متعادل و اثر خنثی روی رضایت.",
    },
    "heavy": {
        "label": "💼 مالیات سنگین",
        "income_mult": 1.35,
        "approval_delta": -3,
        "unrest_delta": 5.0,
        "pop_bonus": -0.0005,
        "desc": "درآمد بیشتر، اما افت تدریجی رضایت و افزایش مهاجرت و احتمال اعتصاب.",
    },
    "emergency": {
        "label": "🚨 مالیات اضطراری",
        "income_mult": 1.75,
        "approval_delta": -8,
        "unrest_delta": 12.0,
        "pop_bonus": -0.0012,
        "desc": "درآمد فوری و زیاد. افت شدید رضایت و ناآرامی سریع. فقط برای جنگ یا بحران مالی.",
    },
}
DEFAULT_TAX_POLICY = "normal"

# میزان تمکین مالیاتی بر اساس رضایت عمومی.
# منطق: هرچه رضایت پایین‌تر، فرار مالیاتی و تعطیلی کسب‌وکار بیشتر و وصولی کمتر.
COMPLIANCE_BANDS = (
    (80, 1.05),
    (60, 1.00),
    (40, 0.85),
    (25, 0.65),
    (10, 0.40),
    (0, 0.20),
)

# اثر مرحله‌ی ناآرامی روی وصول مالیات
UNREST_TAX_MULT = {0: 1.00, 1: 0.95, 2: 0.85, 3: 0.65, 4: 0.40}

# نرخ پایه‌ی تغییر روزانه جمعیت بر اساس رضایت عمومی (نسبت به جمعیت فعلی)
POPULATION_BANDS = (
    (80, 0.0035, "رشد زیاد"),
    (60, 0.0018, "رشد طبیعی"),
    (40, 0.0002, "تقریباً ثابت"),
    (25, -0.0035, "مهاجرت و کاهش"),
    (10, -0.0090, "مهاجرت شدید"),
    (0, -0.0180, "بحران جمعیتی"),
)

UNREST_STAGES = {
    0: {"label": "🟢 آرام", "desc": "وضعیت داخلی پایدار است."},
    1: {"label": "🟡 نارضایتی", "desc": "نارضایتی عمومی محسوس است؛ وصول مالیات کمی افت کرده."},
    2: {"label": "🟠 اعتراض عمومی", "desc": "تجمعات اعتراضی در چند شهر؛ افت تولید و مالیات."},
    3: {"label": "🔴 اعتصاب و شورش", "desc": "اعتصاب سراسری و خسارت مستقیم به خزانه و زیرساخت."},
    4: {"label": "⚫️ بحران حکومتی", "desc": "کنترل دولت بر بخش‌هایی از کشور متزلزل است."},
}
UNREST_THRESHOLDS = ((80, 4), (60, 3), (40, 2), (20, 1), (0, 0))
COLLAPSE_CRITICAL_DAYS = 3  # چند روز پیاپی در مرحله ۴ تا پرچم خطر سقوط

SEVERITY_FACTORS = {"light": 0.5, "medium": 1.0, "severe": 1.8}
SEVERITY_LABELS = {"light": "خفیف", "medium": "متوسط", "severe": "شدید"}

# ─────────────────────────────────────────────────────────────────────────────
# کاتالوگ بحران‌ها
#   pop:   نسبت جمعیت از دست رفته
#   elec:  واحد برق
#   grain / oil: نسبت از ذخیره
#   treasury: نسبت از خزانه
#   income:   نسبت افت درآمد روزانه (موقت، در بازسازی برمی‌گردد)
#   approval / unrest: اثر مستقیم
# ─────────────────────────────────────────────────────────────────────────────
CRISIS_CATALOG = {
    "earthquake": {
        "label": "🌍 زلزله",
        "warning": "منابع محلی از افزایش فعالیت لرزه‌ای در منطقه خبر می‌دهند.",
        "impact": "زلزله‌ای شدید چند منطقه کشور را لرزاند. نیروهای امدادی در آماده‌باش کامل هستند.",
        "duration": 3,
        "effects": {"pop": 0.004, "elec": 25, "treasury": 0.04, "approval": -6, "unrest": 10},
    },
    "flood": {
        "label": "🌊 سیل",
        "warning": "هواشناسی نسبت به بارش‌های سنگین و طغیان رودخانه‌ها هشدار داد.",
        "impact": "سیل گسترده به اراضی کشاورزی و راه‌های ارتباطی خسارت زد.",
        "duration": 3,
        "effects": {"grain": 0.22, "pop": 0.001, "income": 0.10, "approval": -4, "unrest": 7},
    },
    "drought": {
        "label": "🏜 خشکسالی",
        "warning": "کاهش بی‌سابقه‌ی بارش، نگرانی از کم‌آبی و افت محصول را افزایش داده است.",
        "impact": "خشکسالی تولید غلات را به‌شدت کاهش داد و موج مهاجرت روستایی آغاز شد.",
        "duration": 5,
        "effects": {"grain": 0.30, "pop": 0.002, "approval": -5, "unrest": 8},
    },
    "storm": {
        "label": "🌪 طوفان",
        "warning": "سامانه‌ی طوفانی نیرومندی در حال نزدیک‌شدن به سواحل کشور است.",
        "impact": "طوفان به بنادر و تأسیسات ساحلی آسیب زد و صادرات موقتاً متوقف شد.",
        "duration": 2,
        "effects": {"income": 0.15, "elec": 15, "treasury": 0.02, "approval": -3, "unrest": 5},
    },
    "wildfire": {
        "label": "🔥 آتش‌سوزی گسترده",
        "warning": "گرمای بی‌سابقه و خشکی پوشش گیاهی، خطر آتش‌سوزی را بحرانی کرده است.",
        "impact": "آتش‌سوزی گسترده به مناطق صنعتی و مسکونی سرایت کرد.",
        "duration": 2,
        "effects": {"pop": 0.0015, "treasury": 0.05, "income": 0.08, "approval": -4, "unrest": 6},
    },
    "epidemic": {
        "label": "🦠 اپیدمی",
        "warning": "مراکز بهداشتی از افزایش غیرعادی موارد بیماری در چند استان خبر می‌دهند.",
        "impact": "شیوع بیماری، نظام درمانی کشور را زیر فشار برد و فعالیت اقتصادی کاهش یافت.",
        "duration": 5,
        "effects": {"pop": 0.006, "income": 0.12, "approval": -7, "unrest": 9},
    },
    "energy_crisis": {
        "label": "⚡ بحران انرژی",
        "warning": "ذخایر سوخت نیروگاه‌ها رو به اتمام است و شبکه‌ی برق در وضعیت هشدار قرار دارد.",
        "impact": "خاموشی‌های گسترده، تولید کارخانه‌ها را متوقف کرد.",
        "duration": 3,
        "effects": {"elec": 35, "oil": 0.20, "income": 0.18, "approval": -6, "unrest": 11},
    },
    "economic_collapse": {
        "label": "📉 سقوط اقتصادی",
        "warning": "شاخص‌های اقتصادی و خروج سرمایه، نشانه‌های یک بحران مالی جدی را نشان می‌دهند.",
        "impact": "بازارها سقوط کردند، سرمایه از کشور خارج شد و بیکاری جهش کرد.",
        "duration": 4,
        "effects": {"treasury": 0.08, "income": 0.22, "approval": -8, "unrest": 13},
    },
    "famine": {
        "label": "🌾 قحطی",
        "warning": "ذخایر راهبردی غلات به سطح بحرانی رسیده است.",
        "impact": "کمبود شدید مواد غذایی به قحطی و ناآرامی در شهرهای بزرگ انجامید.",
        "duration": 4,
        "effects": {"grain": 0.40, "pop": 0.005, "approval": -10, "unrest": 16},
    },
    "civil_unrest": {
        "label": "✊ ناآرامی مدنی",
        "warning": "فراخوان‌های اعتراضی گسترده‌ای در شبکه‌های اجتماعی منتشر شده است.",
        "impact": "اعتصاب سراسری، تولید و حمل‌ونقل کشور را فلج کرد.",
        "duration": 3,
        "effects": {"treasury": 0.06, "income": 0.20, "approval": -6, "unrest": 14},
    },
}

# اقدامات اضطراری بازیکن: هزینه نسبت به خزانه، اثر کاهش خسارت و رضایت
CRISIS_ACTIONS = {
    "emergency_aid": {
        "label": "🚑 کمک اضطراری",
        "cost_pct": 0.05, "min_cost": 2_000_000,
        "mitigation": 0.25, "approval": 3, "unrest": -6,
        "desc": "تخصیص بودجه‌ی فوری امداد و اسکان.",
    },
    "medical_mobilization": {
        "label": "🏥 بسیج درمانی",
        "cost_pct": 0.04, "min_cost": 1_500_000,
        "mitigation": 0.20, "approval": 3, "unrest": -4,
        "desc": "بسیج کادر درمان و تجهیزات پزشکی.",
    },
    "food_release": {
        "label": "🌾 توزیع ذخایر غذایی",
        "cost_pct": 0.02, "min_cost": 500_000, "grain_cost": 0.15,
        "mitigation": 0.22, "approval": 4, "unrest": -7,
        "desc": "آزادسازی ذخایر راهبردی غلات بین مردم.",
    },
    "energy_priority": {
        "label": "⚡ اولویت‌بندی انرژی",
        "cost_pct": 0.02, "min_cost": 500_000,
        "mitigation": 0.18, "approval": 1, "unrest": -3,
        "desc": "سهمیه‌بندی برق و اولویت‌دادن به بخش خانگی و درمان.",
    },
    "rapid_rebuild": {
        "label": "🏗️ بازسازی سریع",
        "cost_pct": 0.08, "min_cost": 3_000_000,
        "mitigation": 0.30, "approval": 4, "unrest": -5,
        "desc": "پروژه‌ی فوری بازسازی زیرساخت‌های آسیب‌دیده.",
    },
    "official_address": {
        "label": "📢 بیانیه رسمی",
        "cost_pct": 0.0, "min_cost": 0,
        "mitigation": 0.06, "approval": 2, "unrest": -4,
        "desc": "سخنرانی رسمی و شفاف‌سازی برای افکار عمومی. بدون هزینه.",
    },
    "security_crackdown": {
        "label": "🛡 استفاده از نیروهای امنیتی",
        "cost_pct": 0.03, "min_cost": 1_000_000,
        "mitigation": 0.10, "approval": -6, "unrest": -18,
        "desc": "کنترل قهری ناآرامی. ناآرامی را سریع می‌خواباند اما رضایت عمومی را می‌سوزاند.",
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# کمکی‌ها
# ─────────────────────────────────────────────────────────────────────────────
# ─────────────────────────────────────────────────────────────────────────────
# پروفایل مخاطرات جغرافیایی
#
# بدون این، شانس زلزله در آمریکا با ژاپن یکی بود و شانس خشکسالی در نروژ با
# عربستان. سند طراحی صراحتاً «تصادفی منطقه‌ای بر اساس منطقه‌ی جغرافیایی» خواسته
# بود. عددها ضریب وزن‌اند، نه درصد؛ ۰ یعنی آن بلا در آن کشور رخ نمی‌دهد.
# ─────────────────────────────────────────────────────────────────────────────
BASE_HAZARD_WEIGHTS = {
    "earthquake": 1.0,
    "flood": 1.0,
    "drought": 1.0,
    "storm": 1.0,
    "wildfire": 1.0,
    "epidemic": 0.8,
}

# وزن مخاطرات بر پایه‌ی قاره (config.CONTINENTS)
CONTINENT_HAZARD_WEIGHTS = {
    "mideast": {"earthquake": 1.4, "drought": 2.0, "storm": 0.5, "flood": 0.7, "wildfire": 1.1},
    "asia": {"earthquake": 1.8, "storm": 1.8, "flood": 1.8, "drought": 0.9, "epidemic": 1.1},
    "europe": {"earthquake": 0.6, "flood": 1.3, "wildfire": 1.2, "drought": 0.8, "storm": 0.9},
    "americas": {"storm": 1.7, "wildfire": 1.6, "flood": 1.2, "earthquake": 1.0, "drought": 0.9},
    "africa": {"drought": 2.2, "epidemic": 1.5, "flood": 1.1, "earthquake": 0.5, "wildfire": 0.8},
    "oceania": {"storm": 1.8, "wildfire": 1.8, "drought": 1.3, "earthquake": 1.1, "flood": 0.9},
}

# اصلاح‌کننده‌ی اختصاصی کشور — بر واقعیت جغرافیایی سوار است و بر قاره غالب
COUNTRY_HAZARD_WEIGHTS = {
    # کمربند آتش و گسل‌های بزرگ
    "japan": {"earthquake": 3.5, "storm": 2.0, "wildfire": 0.4},
    "taiwan": {"earthquake": 3.0, "storm": 2.2},
    "indonesia": {"earthquake": 3.0, "flood": 2.0, "storm": 1.4},
    "philippines": {"storm": 3.0, "earthquake": 2.2, "flood": 2.0},
    "iran": {"earthquake": 3.0, "drought": 2.2, "storm": 0.3},
    "turkey": {"earthquake": 3.0, "wildfire": 1.5, "drought": 1.2},
    "chile": {"earthquake": 3.0, "wildfire": 1.5},
    "mexico": {"earthquake": 2.2, "storm": 2.0},
    "nepal": {"earthquake": 2.8, "flood": 1.4, "storm": 0.2},
    "afghanistan": {"earthquake": 2.5, "drought": 2.0, "storm": 0.2},
    "pakistan": {"flood": 2.6, "earthquake": 2.0, "drought": 1.4},
    # سیل‌خیز
    "bangladesh": {"flood": 3.5, "storm": 2.6, "drought": 0.4},
    "india": {"flood": 2.4, "storm": 1.8, "drought": 1.6, "epidemic": 1.3},
    "netherlands": {"flood": 2.2, "earthquake": 0.2, "drought": 0.5},
    "vietnam": {"storm": 2.6, "flood": 2.4},
    # آتش‌سوزی و طوفان
    "usa": {"wildfire": 2.6, "storm": 2.4, "earthquake": 1.2, "drought": 1.2},
    "australia": {"wildfire": 3.2, "drought": 2.2, "storm": 1.6, "earthquake": 0.4},
    "canada": {"wildfire": 2.4, "flood": 1.2, "drought": 0.6, "storm": 0.7},
    "greece": {"wildfire": 2.6, "earthquake": 2.0, "drought": 1.5},
    "spain": {"wildfire": 2.2, "drought": 1.8},
    "portugal": {"wildfire": 2.4, "drought": 1.6},
    # خشکسالی شدید
    "saudi": {"drought": 2.6, "storm": 0.3, "flood": 0.3, "earthquake": 0.3},
    "egypt": {"drought": 2.4, "earthquake": 0.6, "storm": 0.3},
    "yemen": {"drought": 2.4, "flood": 1.2, "epidemic": 1.6},
    "somalia": {"drought": 3.0, "epidemic": 1.8, "flood": 1.2},
    "sudan": {"drought": 2.6, "epidemic": 1.5},
    "iraq": {"drought": 2.4, "storm": 0.3},
    "algeria": {"drought": 2.0, "wildfire": 1.6, "earthquake": 1.4},
    # سرد و کم‌مخاطره
    "russia": {"wildfire": 2.0, "flood": 1.0, "storm": 0.5, "drought": 0.6},
    "norway": {"flood": 1.4, "earthquake": 0.2, "drought": 0.3, "storm": 0.8},
    "sweden": {"wildfire": 1.2, "earthquake": 0.2, "drought": 0.4},
    "finland": {"earthquake": 0.2, "drought": 0.3, "wildfire": 1.1},
    "switzerland": {"flood": 1.3, "earthquake": 0.5, "storm": 0.3},
}

# فصل‌ها روی نیم‌کره شمالی تنظیم شده‌اند (اکثر کشورهای بازی)
SEASONAL_HAZARD_WEIGHTS = {
    12: {"storm": 1.3, "flood": 1.2, "wildfire": 0.5, "epidemic": 1.3},
    1: {"storm": 1.3, "flood": 1.2, "wildfire": 0.4, "epidemic": 1.4},
    2: {"storm": 1.2, "flood": 1.3, "wildfire": 0.4, "epidemic": 1.3},
    3: {"flood": 1.5, "drought": 0.8},
    4: {"flood": 1.5, "drought": 0.9},
    5: {"flood": 1.2, "drought": 1.1},
    6: {"wildfire": 1.6, "drought": 1.5, "flood": 0.7},
    7: {"wildfire": 2.0, "drought": 1.8, "flood": 0.6},
    8: {"wildfire": 2.0, "drought": 1.8, "storm": 1.3},
    9: {"storm": 1.6, "wildfire": 1.3, "flood": 1.1},
    10: {"storm": 1.4, "flood": 1.3},
    11: {"storm": 1.2, "flood": 1.2, "epidemic": 1.2},
}

_CONTINENT_BY_COUNTRY_KEY: dict[str, str] | None = None


def _continent_of(country_key: str) -> str | None:
    """قاره‌ی یک کشور بر پایه‌ی config.CONTINENTS (یک‌بار کش می‌شود)."""
    global _CONTINENT_BY_COUNTRY_KEY
    if _CONTINENT_BY_COUNTRY_KEY is None:
        mapping = {}
        for continent, data in (getattr(config, "CONTINENTS", {}) or {}).items():
            for key in (data.get("keys") or []) if isinstance(data, dict) else []:
                mapping[key] = continent
        _CONTINENT_BY_COUNTRY_KEY = mapping
    return _CONTINENT_BY_COUNTRY_KEY.get(country_key or "")


def hazard_weights(country: dict, now_dt: datetime.datetime | None = None) -> dict:
    """وزن نهایی هر بلای طبیعی برای یک کشور مشخص.

    ترتیب اعمال: پایه × قاره × کشور × فصل.
    """
    now_dt = now_dt or _now()
    country_key = (country or {}).get("country_key") or ""
    weights = dict(BASE_HAZARD_WEIGHTS)

    continent = _continent_of(country_key)
    for hazard, factor in (CONTINENT_HAZARD_WEIGHTS.get(continent) or {}).items():
        if hazard in weights:
            weights[hazard] *= factor

    for hazard, factor in (COUNTRY_HAZARD_WEIGHTS.get(country_key) or {}).items():
        if hazard in weights:
            weights[hazard] *= factor

    for hazard, factor in (SEASONAL_HAZARD_WEIGHTS.get(now_dt.month) or {}).items():
        if hazard in weights:
            weights[hazard] *= factor

    return weights


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _iso(dt: datetime.datetime | None = None) -> str:
    return (dt or _now()).isoformat()


def _today(dt: datetime.datetime | None = None) -> str:
    return (dt or _now()).date().isoformat()


def _parse_dt(raw):
    if not raw:
        return None
    try:
        value = datetime.datetime.fromisoformat(raw)
        return value if value.tzinfo else value.replace(tzinfo=datetime.timezone.utc)
    except (TypeError, ValueError):
        return None


def _json_load(raw, default):
    try:
        value = json.loads(raw or "")
        return value if value is not None else default
    except (TypeError, ValueError):
        return default


def _band(value, bands):
    for threshold, *rest in bands:
        if value >= threshold:
            return rest
    return list(bands[-1][1:])


def is_enabled() -> bool:
    return db.get_setting(SETTING_ENABLED) == "1"


def random_crises_enabled() -> bool:
    return db.get_setting(SETTING_RANDOM_CRISES) == "1"


def set_enabled(value: bool):
    db.set_setting(SETTING_ENABLED, "1" if value else "0")


def set_random_crises(value: bool):
    db.set_setting(SETTING_RANDOM_CRISES, "1" if value else "0")


def tax_policy_label(key: str) -> str:
    return TAX_POLICIES.get(key, TAX_POLICIES[DEFAULT_TAX_POLICY])["label"]


def stage_label(stage: int) -> str:
    return UNREST_STAGES.get(int(stage or 0), UNREST_STAGES[0])["label"]


def compliance_for(approval: float) -> float:
    return _band(approval, COMPLIANCE_BANDS)[0]


def stage_for_unrest(unrest: float) -> int:
    return int(_band(unrest, UNREST_THRESHOLDS)[0])


# ─────────────────────────────────────────────────────────────────────────────
# وضعیت داخلی کشور
# ─────────────────────────────────────────────────────────────────────────────
def _ensure_state_cur(cur, country: dict) -> dict:
    """رکورد وضعیت داخلی را می‌سازد یا برمی‌گرداند (با cursor موجود)."""
    cid = country["id"]
    row = cur.execute("SELECT * FROM country_internal WHERE country_id = ?", (cid,)).fetchone()
    if row:
        return dict(row)
    cur.execute(
        """
        INSERT INTO country_internal
        (country_id, tax_policy, tax_policy_changed_at, baseline_population, baseline_tax_income, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            cid, DEFAULT_TAX_POLICY, _iso(),
            max(1, int(country.get("population") or 0)),
            max(0, int(country.get("tax_income") or 0)),
            _iso(),
        ),
    )
    row = cur.execute("SELECT * FROM country_internal WHERE country_id = ?", (cid,)).fetchone()
    return dict(row)


def get_state(country_id: int) -> dict | None:
    country = db.get_country_by_id(country_id)
    if not country:
        return None
    conn = db.get_connection()
    try:
        with conn:
            state = _ensure_state_cur(conn.cursor(), country)
        return state
    finally:
        conn.close()


def set_tax_policy(country_id: int, policy: str, actor_id: int | None = None):
    """تغییر سیاست مالیاتی کشور.

    درآمد مالیاتی **بلافاصله** بازمحاسبه و اعمال می‌شود (سند: «مالیات اضطراری،
    درآمد فوری»). در عوض تا چرخه‌ی روزانه‌ی بعد قفل می‌شود تا کسی نتواند قبل از
    پرداخت دوره‌ای به اضطراری سوییچ کند، پول را بگیرد و قبل از پرداختِ هزینه‌ی
    رضایت و ناآرامی به سیاست ملایم برگردد.
    """
    if policy not in TAX_POLICIES:
        return False, "سیاست مالیاتی نامعتبر است."
    country = db.get_country_by_id(country_id)
    if not country:
        return False, "کشور یافت نشد."

    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            state = _ensure_state_cur(cur, country)
            previous = state["tax_policy"]
            if previous == policy:
                return False, "همین سیاست مالیاتی هم‌اکنون فعال است."
            if int(state.get("policy_locked") or 0) and is_enabled():
                return False, (
                    "شما امروز یک‌بار سیاست مالیاتی را تغییر داده‌اید. "
                    "تغییر بعدی از چرخه‌ی روزانه‌ی بعد ممکن است."
                )

            state["tax_policy"] = policy
            new_tax = project_tax_income(country, state, policy)
            cur.execute(
                """
                UPDATE country_internal
                SET tax_policy = ?, tax_policy_changed_at = ?, tax_policy_days = 0, policy_locked = 1
                WHERE country_id = ?
                """,
                (policy, _iso(), country_id),
            )
            cur.execute("UPDATE countries SET tax_income = ? WHERE id = ?", (new_tax, country_id))
    finally:
        conn.close()

    db.add_log(
        f"country:{country_id}" if actor_id is None else f"player:{actor_id}",
        "tax_policy_change",
        f"{previous} → {policy} | tax_income={new_tax}",
    )
    return True, (
        f"سیاست مالیاتی به «{TAX_POLICIES[policy]['label']}» تغییر کرد و "
        f"درآمد مالیاتی هم‌اکنون {new_tax:,} دلار در روز است."
    )



def project_tax_income(country: dict, state: dict, policy: str | None = None) -> int:
    """درآمد مالیاتی پیش‌بینی‌شده با یک سیاست مشخص (برای نمایش «اثر تغییر سیاست»)."""
    policy = policy or state.get("tax_policy") or DEFAULT_TAX_POLICY
    spec = TAX_POLICIES.get(policy, TAX_POLICIES[DEFAULT_TAX_POLICY])
    baseline_pop = max(1, int(state.get("baseline_population") or 0) or int(country.get("population") or 1))
    baseline_tax = max(0, int(state.get("baseline_tax_income") or 0))
    pop_ratio = max(0.0, float(country.get("population") or 0) / baseline_pop)
    compliance = compliance_for(float(country.get("approval_rating") or 0))
    unrest_mult = UNREST_TAX_MULT.get(int(state.get("unrest_stage") or 0), 1.0)
    return max(0, int(baseline_tax * pop_ratio * spec["income_mult"] * compliance * unrest_mult))


# ─────────────────────────────────────────────────────────────────────────────
# بحران‌ها
# ─────────────────────────────────────────────────────────────────────────────
def get_active_crises(country_id: int) -> list[dict]:
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM country_crises WHERE country_id = ? AND stage != 'ended' ORDER BY id DESC",
            (country_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_crisis(crisis_id: int) -> dict | None:
    conn = db.get_connection()
    try:
        row = conn.execute("SELECT * FROM country_crises WHERE id = ?", (crisis_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_crisis_history(country_id: int | None = None, limit: int = 15) -> list[dict]:
    conn = db.get_connection()
    try:
        limit = max(1, min(100, int(limit)))
        if country_id is None:
            rows = conn.execute(
                "SELECT c.*, co.name AS country_name, co.flag AS country_flag "
                "FROM country_crises c JOIN countries co ON co.id = c.country_id "
                "ORDER BY c.id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM country_crises WHERE country_id = ? ORDER BY id DESC LIMIT ?",
                (country_id, limit),
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def _can_add_crisis(cur, country_id: int, severity: str, force: bool = False) -> tuple[bool, str]:
    """قوانین ضدبی‌عدالتی: سقف بحران هم‌زمان و مصونیت بعد از بحران سنگین."""
    if force:
        return True, ""
    rows = cur.execute(
        "SELECT severity FROM country_crises WHERE country_id = ? AND stage != 'ended'",
        (country_id,),
    ).fetchall()
    if len(rows) >= MAX_ACTIVE_CRISES:
        return False, "این کشور هم‌اکنون به سقف بحران‌های هم‌زمان رسیده است."
    if severity == "severe" and sum(1 for r in rows if r["severity"] == "severe") >= MAX_SEVERE_CRISES:
        return False, "دو بحران سنگین هم‌زمان روی یک کشور مجاز نیست."
    row = cur.execute("SELECT crisis_shield_until FROM country_internal WHERE country_id = ?", (country_id,)).fetchone()
    shield = _parse_dt(row["crisis_shield_until"]) if row else None
    if shield and _now() < shield:
        return False, "این کشور در دوره‌ی مصونیت پس از بحران قبلی است."
    return True, ""


def create_crisis(
    country_id: int,
    crisis_key: str,
    severity: str = "medium",
    origin: str = "admin",
    duration_days: int | None = None,
    admin_id: int | None = None,
    skip_warning: bool = False,
    force: bool = False,
):
    """ساخت بحران. پیش‌فرض از مرحله‌ی «هشدار» شروع می‌شود.

    skip_warning فقط برای رویداد داستانی صریح ادمین است.
    """
    if crisis_key not in CRISIS_CATALOG:
        return False, "نوع بحران نامعتبر است.", None
    if severity not in SEVERITY_FACTORS:
        return False, "شدت بحران نامعتبر است.", None
    country = db.get_country_by_id(country_id)
    if not country:
        return False, "کشور یافت نشد.", None

    spec = CRISIS_CATALOG[crisis_key]
    try:
        duration = int(duration_days or spec["duration"])
    except (TypeError, ValueError):
        duration = spec["duration"]
    duration = max(1, min(14, duration))

    now_dt = _now()
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            _ensure_state_cur(cur, country)
            ok, message = _can_add_crisis(cur, country_id, severity, force=force)
            if not ok:
                return False, message, None

            stage = "impact" if skip_warning else "warning"
            cur.execute(
                """
                INSERT INTO country_crises
                (country_id, crisis_key, severity, stage, origin, duration_days,
                 warned_at, started_at, ends_at, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    country_id, crisis_key, severity, stage, origin, duration,
                    _iso(now_dt),
                    _iso(now_dt) if skip_warning else None,
                    _iso(now_dt + datetime.timedelta(days=duration)) if skip_warning else None,
                    admin_id, _iso(now_dt),
                ),
            )
            crisis_id = cur.lastrowid
    finally:
        conn.close()

    db.add_log(
        f"admin:{admin_id}" if admin_id else f"system:{origin}",
        "crisis_created",
        f"country={country_id} type={crisis_key} severity={severity} stage={'impact' if skip_warning else 'warning'}",
    )
    crisis = get_crisis(crisis_id)
    if skip_warning:
        _apply_crisis_impact(crisis)
        crisis = get_crisis(crisis_id)
    return True, f"بحران «{spec['label']}» برای کشور ثبت شد.", crisis


def end_crisis(crisis_id: int, admin_id: int | None = None):
    crisis = get_crisis(crisis_id)
    if not crisis:
        return False, "بحران یافت نشد."
    if crisis["stage"] == "ended":
        return False, "این بحران قبلاً پایان یافته است."
    conn = db.get_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE country_crises SET stage = 'ended', ended_at = ? WHERE id = ?",
                (_iso(), crisis_id),
            )
            if crisis["severity"] == "severe":
                conn.execute(
                    "UPDATE country_internal SET crisis_shield_until = ? WHERE country_id = ?",
                    (_iso(_now() + datetime.timedelta(days=CRISIS_SHIELD_DAYS)), crisis["country_id"]),
                )
    finally:
        conn.close()
    db.add_log(f"admin:{admin_id}" if admin_id else "system", "crisis_ended", f"crisis={crisis_id}")
    return True, "بحران پایان یافت."


def update_crisis(crisis_id: int, severity: str | None = None, duration_days: int | None = None, admin_id: int | None = None):
    crisis = get_crisis(crisis_id)
    if not crisis:
        return False, "بحران یافت نشد."
    if crisis["stage"] == "ended":
        return False, "بحران پایان‌یافته قابل ویرایش نیست."
    if severity is not None and severity not in SEVERITY_FACTORS:
        return False, "شدت نامعتبر است."
    new_severity = severity or crisis["severity"]
    new_duration = crisis["duration_days"]
    if duration_days is not None:
        try:
            new_duration = max(1, min(14, int(duration_days)))
        except (TypeError, ValueError):
            return False, "مدت باید عدد صحیح باشد."

    ends_at = crisis["ends_at"]
    started = _parse_dt(crisis["started_at"])
    if started:
        ends_at = _iso(started + datetime.timedelta(days=new_duration))

    conn = db.get_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE country_crises SET severity = ?, duration_days = ?, ends_at = ? WHERE id = ?",
                (new_severity, new_duration, ends_at, crisis_id),
            )
    finally:
        conn.close()
    db.add_log(f"admin:{admin_id}", "crisis_updated", f"crisis={crisis_id} severity={new_severity} duration={new_duration}")
    return True, "بحران به‌روزرسانی شد."


def _crisis_damage(crisis: dict) -> dict:
    """خسارت خام بحران با اعمال شدت و کاهش ناشی از واکنش بازیکن."""
    spec = CRISIS_CATALOG.get(crisis["crisis_key"], {})
    factor = SEVERITY_FACTORS.get(crisis["severity"], 1.0)
    mitigation = max(0.0, min(0.80, float(crisis.get("mitigation") or 0)))
    scale = factor * (1.0 - mitigation)
    return {key: value * scale for key, value in (spec.get("effects") or {}).items()}


def _apply_crisis_impact(crisis: dict) -> dict:
    """اعمال اثر اصلی بحران روی کشور. فقط یک‌بار و در مرحله‌ی impact."""
    country = db.get_country_by_id(crisis["country_id"])
    if not country:
        return {}
    damage = _crisis_damage(crisis)
    applied = {}
    cid = country["id"]

    pop = int(country.get("population") or 0)
    if damage.get("pop") and pop > 0:
        lost = int(pop * damage["pop"])
        new_pop = max(POPULATION_FLOOR, pop - lost)
        applied["population"] = pop - new_pop
        db.update_country_field(cid, "population", new_pop)

    if damage.get("elec"):
        elec = int(country.get("electricity") or 0)
        loss = int(damage["elec"])
        db.update_country_field(cid, "electricity", max(0, elec - loss))
        applied["electricity"] = min(elec, loss)

    if damage.get("grain"):
        grain = int(country.get("grain") or 0)
        loss = int(grain * damage["grain"])
        db.update_country_field(cid, "grain", max(0, grain - loss))
        applied["grain"] = loss

    if damage.get("oil"):
        oil = int(country.get("oil_reserves") or 0)
        loss = int(oil * damage["oil"])
        db.update_country_field(cid, "oil_reserves", max(0, oil - loss))
        applied["oil_reserves"] = loss

    if damage.get("treasury"):
        treasury = int(country.get("treasury") or 0)
        loss = int(max(0, treasury) * damage["treasury"])
        if loss > 0:
            db.adjust_treasury(cid, -loss)
            db.add_transaction(cid, "crisis_damage", f"خسارت بحران: {CRISIS_CATALOG[crisis['crisis_key']]['label']}", -loss)
        applied["treasury"] = loss

    if damage.get("income"):
        income = int(country.get("daily_income") or 0)
        loss = int(income * damage["income"])
        if loss > 0:
            db.update_country_field(cid, "daily_income", max(0, income - loss))
        applied["daily_income"] = loss

    if damage.get("approval"):
        approval = int(country.get("approval_rating") or 0)
        db.update_country_field(cid, "approval_rating", max(0, min(100, approval + int(damage["approval"]))))
        applied["approval"] = int(damage["approval"])

    now_dt = _now()
    conn = db.get_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE country_crises SET stage = 'impact', started_at = COALESCE(started_at, ?), ends_at = ?, damage_json = ? WHERE id = ?",
                (
                    _iso(now_dt),
                    _iso(now_dt + datetime.timedelta(days=int(crisis["duration_days"] or 2))),
                    json.dumps(applied, ensure_ascii=False),
                    crisis["id"],
                ),
            )
            if damage.get("unrest"):
                conn.execute(
                    "UPDATE country_internal SET unrest = MIN(100, unrest + ?) WHERE country_id = ?",
                    (float(damage["unrest"]), cid),
                )
    finally:
        conn.close()
    return applied


def force_impact(crisis_id: int, admin_id: int | None = None):
    """اعمال فوری خسارتِ بحرانی که در مرحله‌ی هشدار مانده است.

    برای رویدادهای زنده‌ی ادمین. در حالت عادی بحران در اولین چرخه‌ی روزانه‌ی
    بعدی (بعد از ۰۰:۰۰ به وقت تهران) خودش وارد مرحله‌ی وقوع می‌شود.
    """
    crisis = get_crisis(crisis_id)
    if not crisis:
        return False, "بحران یافت نشد.", None
    if crisis["stage"] != "warning":
        return False, "این بحران از مرحله‌ی هشدار عبور کرده است.", crisis
    applied = _apply_crisis_impact(crisis)
    db.add_log(f"admin:{admin_id}" if admin_id else "system", "crisis_forced_impact", f"crisis={crisis_id}")
    return True, "خسارت بحران هم‌اکنون اعمال شد.", applied


def estimate_damage(crisis: dict) -> dict:
    """برآورد خسارتی که این بحران در مرحله‌ی وقوع وارد می‌کند (برای پیش‌نمایش ادمین)."""
    country = db.get_country_by_id(crisis["country_id"])
    if not country:
        return {}
    damage = _crisis_damage(crisis)
    preview = {}
    if damage.get("pop"):
        preview["population"] = int(int(country.get("population") or 0) * damage["pop"])
    if damage.get("elec"):
        preview["electricity"] = int(damage["elec"])
    if damage.get("grain"):
        preview["grain"] = int(int(country.get("grain") or 0) * damage["grain"])
    if damage.get("oil"):
        preview["oil_reserves"] = int(int(country.get("oil_reserves") or 0) * damage["oil"])
    if damage.get("treasury"):
        preview["treasury"] = int(max(0, int(country.get("treasury") or 0)) * damage["treasury"])
    if damage.get("income"):
        preview["daily_income"] = int(int(country.get("daily_income") or 0) * damage["income"])
    if damage.get("approval"):
        preview["approval"] = int(damage["approval"])
    if damage.get("unrest"):
        preview["unrest"] = round(float(damage["unrest"]), 1)
    return preview


def available_actions(crisis: dict) -> list[str]:
    """اقدامات متناسب با نوع بحران."""
    key = crisis["crisis_key"]
    base = ["official_address", "emergency_aid"]
    mapping = {
        "earthquake": ["medical_mobilization", "rapid_rebuild"],
        "flood": ["food_release", "rapid_rebuild"],
        "drought": ["food_release", "energy_priority"],
        "storm": ["rapid_rebuild", "energy_priority"],
        "wildfire": ["medical_mobilization", "rapid_rebuild"],
        "epidemic": ["medical_mobilization", "food_release"],
        "energy_crisis": ["energy_priority", "rapid_rebuild"],
        "economic_collapse": ["food_release", "energy_priority"],
        "famine": ["food_release", "medical_mobilization"],
        "civil_unrest": ["security_crackdown", "food_release"],
    }
    actions = base + mapping.get(key, [])
    if key != "civil_unrest":
        actions.append("security_crackdown")
    seen, ordered = set(), []
    for action in actions:
        if action not in seen:
            seen.add(action)
            ordered.append(action)
    return ordered


def respond_to_crisis(crisis_id: int, action_key: str, actor_id: int | None = None):
    """اجرای یک اقدام اضطراری توسط بازیکن."""
    if action_key not in CRISIS_ACTIONS:
        return False, "اقدام نامعتبر است.", None
    crisis = get_crisis(crisis_id)
    if not crisis:
        return False, "بحران یافت نشد.", None
    if crisis["stage"] not in ("warning", "impact", "recovery"):
        return False, "این بحران دیگر فعال نیست.", None
    if action_key not in available_actions(crisis):
        return False, "این اقدام برای این نوع بحران در دسترس نیست.", None

    country = db.get_country_by_id(crisis["country_id"])
    if not country:
        return False, "کشور یافت نشد.", None

    spec = CRISIS_ACTIONS[action_key]
    treasury = int(country.get("treasury") or 0)
    cost = max(int(spec.get("min_cost", 0)), int(max(0, treasury) * float(spec.get("cost_pct", 0))))
    if cost > 0 and treasury < cost:
        return False, f"خزانه کافی نیست. هزینه‌ی این اقدام {cost:,} دلار است.", None

    grain_cost = 0
    if spec.get("grain_cost"):
        grain_cost = int(int(country.get("grain") or 0) * float(spec["grain_cost"]))

    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            today = _today()
            duplicate = cur.execute(
                "SELECT id FROM crisis_actions WHERE crisis_id = ? AND action_key = ? AND action_date = ?",
                (crisis_id, action_key, today),
            ).fetchone()
            if duplicate:
                return False, "این اقدام را امروز انجام داده‌اید. فردا دوباره در دسترس است.", None

            if cost > 0:
                cur.execute("UPDATE countries SET treasury = treasury - ? WHERE id = ?", (cost, crisis["country_id"]))
                cur.execute(
                    "INSERT INTO transactions (country_id, type, description, amount, created_at) VALUES (?, 'crisis_response', ?, ?, ?)",
                    (crisis["country_id"], f"اقدام اضطراری: {spec['label']}", -cost, _iso()),
                )
            if grain_cost > 0:
                cur.execute("UPDATE countries SET grain = MAX(0, grain - ?) WHERE id = ?", (grain_cost, crisis["country_id"]))

            new_mitigation = min(0.80, float(crisis.get("mitigation") or 0) + float(spec["mitigation"]))
            cur.execute("UPDATE country_crises SET mitigation = ? WHERE id = ?", (new_mitigation, crisis_id))
            cur.execute(
                """
                INSERT INTO crisis_actions
                (crisis_id, country_id, action_key, actor_id, cost, mitigation, action_date, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (crisis_id, crisis["country_id"], action_key, actor_id, cost,
                 float(spec["mitigation"]), today, _iso()),
            )

            approval = int(country.get("approval_rating") or 0)
            cur.execute(
                "UPDATE countries SET approval_rating = ? WHERE id = ?",
                (max(0, min(100, approval + int(spec.get("approval", 0)))), crisis["country_id"]),
            )
            cur.execute(
                "UPDATE country_internal SET unrest = MAX(0, MIN(100, unrest + ?)) WHERE country_id = ?",
                (float(spec.get("unrest", 0)), crisis["country_id"]),
            )
    finally:
        conn.close()

    db.add_log(f"player:{actor_id}", "crisis_response", f"crisis={crisis_id} action={action_key} cost={cost}")
    return True, f"{spec['label']} اجرا شد.", {"cost": cost, "grain_cost": grain_cost}


def get_actions_done_today(crisis_id: int) -> set:
    """اقداماتی که امروز برای این بحران انجام شده‌اند (بقیه دوباره در دسترس‌اند)."""
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT action_key FROM crisis_actions WHERE crisis_id = ? AND action_date = ?",
            (crisis_id, _today()),
        ).fetchall()
        return {row["action_key"] for row in rows}
    except Exception:
        return set()
    finally:
        conn.close()


def get_crisis_actions(crisis_id: int) -> list[dict]:
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM crisis_actions WHERE crisis_id = ? ORDER BY id ASC", (crisis_id,)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# چرخه‌ی روزانه
# ─────────────────────────────────────────────────────────────────────────────
def _chain_crisis_candidates(country: dict, state: dict, reqs: dict) -> list[tuple[str, str]]:
    """بحران‌های زنجیره‌ای که از رفتار خود کشور ایجاد می‌شوند."""
    candidates = []
    grain = int(country.get("grain") or 0)
    treasury = int(country.get("treasury") or 0)
    unrest = float(state.get("unrest") or 0)
    policy = state.get("tax_policy") or DEFAULT_TAX_POLICY
    # عمداً pressure_days و نه tax_policy_days: جابه‌جایی بین «سنگین» و «اضطراری»
    # نباید شمارنده را صفر کند، وگرنه با فلیپ‌فلاپ می‌شد بحران را برای همیشه دور زد.
    policy_days = int(state.get("pressure_days") or 0)

    if grain <= 0:
        candidates.append(("famine", "severe" if unrest >= 50 else "medium"))
    if treasury < -20_000_000:
        candidates.append(("economic_collapse", "severe" if treasury < -80_000_000 else "medium"))
    if int(country.get("oil_reserves") or 0) <= 0 and int(country.get("oil_production") or 0) < reqs.get("oil_need_daily", 0):
        candidates.append(("energy_crisis", "medium"))
    if policy in ("heavy", "emergency") and policy_days >= (2 if policy == "emergency" else 4):
        candidates.append(("civil_unrest", "severe" if policy == "emergency" else "medium"))
    if unrest >= 65:
        candidates.append(("civil_unrest", "severe"))
    return candidates


def _random_crisis_candidate(country: dict, state: dict) -> tuple[str, str] | None:
    """بحران تصادفی با احتمال وابسته به جغرافیا، فصل و وضعیت کشور."""
    approval = float(country.get("approval_rating") or 0)
    unrest = float(state.get("unrest") or 0)
    chance = RANDOM_CRISIS_BASE_CHANCE
    if approval < 40:
        chance += 0.04
    if unrest >= 40:
        chance += 0.04
    if random.random() > chance:
        return None

    weights = hazard_weights(country)
    natural = [key for key, weight in weights.items() if weight > 0]
    if not natural:
        return None
    key = random.choices(natural, weights=[weights[k] for k in natural], k=1)[0]
    severity = random.choices(["light", "medium", "severe"], weights=[0.5, 0.38, 0.12], k=1)[0]
    return key, severity


def _advance_crises(country_id: int, now_dt: datetime.datetime) -> list[dict]:
    """جابه‌جایی مرحله‌ی بحران‌ها: هشدار → وقوع → بازسازی → پایان."""
    events = []
    for crisis in get_active_crises(country_id):
        stage = crisis["stage"]
        if stage == "warning":
            warned = _parse_dt(crisis["warned_at"])
            if warned and (now_dt - warned).total_seconds() >= 0:
                applied = _apply_crisis_impact(crisis)
                events.append({"crisis": get_crisis(crisis["id"]), "event": "impact", "damage": applied})
        elif stage == "impact":
            ends = _parse_dt(crisis["ends_at"])
            if ends and now_dt >= ends:
                conn = db.get_connection()
                try:
                    with conn:
                        conn.execute("UPDATE country_crises SET stage = 'recovery' WHERE id = ?", (crisis["id"],))
                finally:
                    conn.close()
                events.append({"crisis": get_crisis(crisis["id"]), "event": "recovery"})
        elif stage == "recovery":
            end_crisis(crisis["id"])
            events.append({"crisis": get_crisis(crisis["id"]), "event": "ended"})
    return events


def run_daily_cycle(country: dict, approval_result: dict | None = None, now_dt: datetime.datetime | None = None) -> dict | None:
    """چرخه‌ی روزانه‌ی یک کشور. برای هر تاریخ فقط یک‌بار اجرا می‌شود.

    خروجی None یعنی سیستم خاموش است یا امروز قبلاً اجرا شده.
    """
    if not is_enabled():
        return None
    now_dt = now_dt or _now()
    today = _today(now_dt)
    cid = country["id"]

    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            state = _ensure_state_cur(cur, country)
            if state.get("last_cycle_date") == today:
                return None
            # قفل idempotency: اگر ردیف امروز موجود باشد، خطای UNIQUE می‌گیریم و رد می‌شویم
            cur.execute(
                "INSERT OR IGNORE INTO internal_daily_log (country_id, log_date, created_at) VALUES (?, ?, ?)",
                (cid, today, _iso(now_dt)),
            )
            if cur.rowcount != 1:
                cur.execute("UPDATE country_internal SET last_cycle_date = ? WHERE country_id = ?", (today, cid))
                return None
            cur.execute("UPDATE country_internal SET last_cycle_date = ? WHERE country_id = ?", (today, cid))
    finally:
        conn.close()

    # ── وضعیت تازه بعد از اجرای approval_system
    country = db.get_country_by_id(cid) or country
    state = get_state(cid) or {}
    policy = state.get("tax_policy") or DEFAULT_TAX_POLICY
    policy_spec = TAX_POLICIES.get(policy, TAX_POLICIES[DEFAULT_TAX_POLICY])

    import approval_system  # وارد کردن تنبل برای پرهیز از وابستگی حلقوی
    reqs = approval_system.calculate_country_requirements(country)

    approval_result = approval_result or {}
    grain_ok = approval_result.get("grain_ok", int(country.get("grain") or 0) > 0)
    elec_ok = approval_result.get("elec_ok", int(country.get("electricity") or 0) >= reqs["elec_need"])
    oil_ok = approval_result.get("oil_ok", True)

    # ── ۰. پیشروی بحران‌های موجود (هشدار → وقوع → بازسازی → پایان)
    # عمداً قبل از محاسبه‌ی جمعیت و مالیات انجام می‌شود تا خسارت بحران در همان
    # چرخه روی رشد جمعیت، ناآرامی و وصول مالیات اثر بگذارد.
    crisis_events = _advance_crises(cid, now_dt)
    country = db.get_country_by_id(cid) or country
    state = get_state(cid) or state

    pop_before = int(country.get("population") or 0)
    tax_before = int(country.get("tax_income") or 0)
    approval = int(country.get("approval_rating") or 0)

    # ── ۱. ناآرامی
    unrest = float(state.get("unrest") or 0) * 0.85  # فروکش طبیعی روزانه
    unrest += max(0.0, (50 - approval)) * 0.22
    unrest += policy_spec["unrest_delta"]
    if not grain_ok:
        unrest += 12
    if not elec_ok:
        unrest += 8
    if not oil_ok:
        unrest += 6
    if int(country.get("treasury") or 0) < 0:
        unrest += 10
    active_crises = [c for c in get_active_crises(cid) if c["stage"] in ("impact", "recovery")]
    unrest += 6 * len(active_crises)
    if approval >= 70:
        unrest -= 8
    unrest = max(0.0, min(100.0, unrest))
    stage = stage_for_unrest(unrest)

    critical_days = int(state.get("critical_days") or 0)
    critical_days = critical_days + 1 if stage >= 4 else 0
    collapse_risk = 1 if critical_days >= COLLAPSE_CRITICAL_DAYS else 0

    # ── ۲. جمعیت
    rate, band_label = _band(approval, POPULATION_BANDS)
    rate += policy_spec["pop_bonus"]
    if not grain_ok:
        rate -= 0.0030
    if not elec_ok:
        rate -= 0.0010
    rate -= 0.0012 * stage
    if approval >= 60 and grain_ok and elec_ok and stage == 0:
        rate += 0.0006  # زیرساخت و خدمات پایدار
    rate = max(-MAX_DAILY_POP_CHANGE_PCT, min(MAX_DAILY_POP_CHANGE_PCT, rate))

    pop_after = max(POPULATION_FLOOR, int(pop_before + pop_before * rate))
    pop_delta = pop_after - pop_before
    if pop_delta:
        db.update_country_field(cid, "population", pop_after)

    # ── ۳. مالیات پویا
    country["population"] = pop_after
    state["unrest_stage"] = stage
    tax_after = project_tax_income(country, state, policy)
    if tax_after != tax_before:
        db.update_country_field(cid, "tax_income", tax_after)

    # ── ۴. خسارت مستقیم ناآرامی شدید
    unrest_damage = 0
    if stage >= 3:
        treasury = max(0, int(country.get("treasury") or 0))
        unrest_damage = int(treasury * (0.03 if stage == 3 else 0.05))
        if unrest_damage > 0:
            db.adjust_treasury(cid, -unrest_damage)
            db.add_transaction(cid, "unrest_damage", f"خسارت {stage_label(stage)} به اقتصاد کشور", -unrest_damage)

    # ── ۵. اثر سیاست مالیاتی روی رضایت
    approval_after = max(0, min(100, approval + policy_spec["approval_delta"]))
    if approval_after != approval:
        db.update_country_field(cid, "approval_rating", approval_after)

    # ── ۶. بحران‌های جدید (زنجیره‌ای از رفتار امروز کشور، یا تصادفی)
    new_crises = []
    for key, severity in _chain_crisis_candidates(country, state, reqs):
        ok, _msg, crisis = create_crisis(cid, key, severity=severity, origin="chain")
        if ok:
            new_crises.append(crisis)
            break  # حداکثر یک بحران زنجیره‌ای جدید در روز
    if not new_crises and random_crises_enabled():
        candidate = _random_crisis_candidate(country, state)
        if candidate:
            ok, _msg, crisis = create_crisis(cid, candidate[0], severity=candidate[1], origin="random")
            if ok:
                new_crises.append(crisis)

    # ── ۷. ذخیره وضعیت و لاگ
    pressure_days = int(state.get("pressure_days") or 0)
    pressure_days = pressure_days + 1 if policy in ("heavy", "emergency") else 0
    details = {
        "band": band_label,
        "rate": round(rate, 6),
        "policy": policy,
        "pressure_days": pressure_days,
        "compliance": compliance_for(approval),
        "grain_ok": bool(grain_ok),
        "elec_ok": bool(elec_ok),
        "oil_ok": bool(oil_ok),
        "unrest_damage": unrest_damage,
        "active_crises": [c["crisis_key"] for c in active_crises],
        "new_crises": [c["crisis_key"] for c in new_crises if c],
    }
    conn = db.get_connection()
    try:
        with conn:
            conn.execute(
                """
                UPDATE country_internal SET unrest = ?, unrest_stage = ?, critical_days = ?,
                    collapse_risk = ?, tax_policy_days = tax_policy_days + 1,
                    pressure_days = ?, policy_locked = 0
                WHERE country_id = ?
                """,
                (unrest, stage, critical_days, collapse_risk, pressure_days, cid),
            )
            conn.execute(
                """
                UPDATE internal_daily_log SET
                    population_before = ?, population_after = ?, population_delta = ?,
                    tax_before = ?, tax_after = ?, approval = ?, unrest = ?, unrest_stage = ?,
                    tax_policy = ?, notes = ?, details_json = ?
                WHERE country_id = ? AND log_date = ?
                """,
                (
                    pop_before, pop_after, pop_delta, tax_before, tax_after,
                    approval_after, unrest, stage, policy, band_label,
                    json.dumps(details, ensure_ascii=False), cid, today,
                ),
            )
    finally:
        conn.close()

    return {
        "country_id": cid,
        "date": today,
        "population_before": pop_before,
        "population_after": pop_after,
        "population_delta": pop_delta,
        "tax_before": tax_before,
        "tax_after": tax_after,
        "approval": approval_after,
        "unrest": unrest,
        "unrest_stage": stage,
        "collapse_risk": collapse_risk,
        "unrest_damage": unrest_damage,
        "crisis_events": crisis_events,
        "new_crises": [c for c in new_crises if c],
        "band": band_label,
    }


# ─────────────────────────────────────────────────────────────────────────────
# گزارش‌ها
# ─────────────────────────────────────────────────────────────────────────────
def get_history(country_id: int, days: int = 7) -> list[dict]:
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM internal_daily_log WHERE country_id = ? ORDER BY log_date DESC LIMIT ?",
            (country_id, max(1, min(60, int(days)))),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def approval_trend(country_id: int) -> int | None:
    """تغییر رضایت عمومی نسبت به چرخه‌ی روزانه‌ی قبل. None یعنی داده‌ی کافی نیست."""
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT approval FROM internal_daily_log WHERE country_id = ? ORDER BY log_date DESC LIMIT 2",
            (country_id,),
        ).fetchall()
        if len(rows) < 2:
            return None
        return int(rows[0]["approval"] or 0) - int(rows[1]["approval"] or 0)
    except Exception:
        return None
    finally:
        conn.close()


def countries_at_risk(limit: int = 20) -> list[dict]:
    conn = db.get_connection()
    try:
        rows = conn.execute(
            """
            SELECT ci.*, c.name AS country_name, c.flag AS country_flag,
                   c.approval_rating, c.population, c.treasury
            FROM country_internal ci JOIN countries c ON c.id = ci.country_id
            WHERE ci.collapse_risk = 1 OR ci.unrest_stage >= 3 OR c.approval_rating < 20
            ORDER BY ci.collapse_risk DESC, ci.unrest DESC LIMIT ?
            """,
            (max(1, min(100, int(limit))),),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def overview(limit: int = 30) -> list[dict]:
    conn = db.get_connection()
    try:
        rows = conn.execute(
            """
            SELECT c.id AS country_id, c.name AS country_name, c.flag AS country_flag,
                   c.population, c.approval_rating, c.tax_income,
                   COALESCE(ci.tax_policy, 'normal') AS tax_policy,
                   COALESCE(ci.unrest, 0) AS unrest,
                   COALESCE(ci.unrest_stage, 0) AS unrest_stage,
                   COALESCE(ci.collapse_risk, 0) AS collapse_risk,
                   (SELECT COUNT(*) FROM country_crises cc WHERE cc.country_id = c.id AND cc.stage != 'ended') AS active_crises
            FROM countries c LEFT JOIN country_internal ci ON ci.country_id = c.id
            WHERE c.player_id > 0
            ORDER BY ci.unrest DESC, c.approval_rating ASC LIMIT ?
            """,
            (max(1, min(200, int(limit))),),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def crisis_management_stats(country_id: int, since: str | None = None) -> dict:
    """آمار مدیریت بحران برای امتیازدهی تورنومنت.

    عمداً «وقوع بحران» امتیاز منفی یا مثبت نمی‌دهد؛ فقط کیفیت واکنش شمرده می‌شود.
    """
    conn = db.get_connection()
    try:
        params = [country_id]
        clause = ""
        if since:
            clause = " AND created_at >= ?"
            params.append(since)
        total = conn.execute(
            f"SELECT COUNT(*) AS n FROM country_crises WHERE country_id = ?{clause}", params
        ).fetchone()["n"]
        managed = conn.execute(
            f"SELECT COUNT(*) AS n FROM country_crises WHERE country_id = ? AND mitigation >= 0.25{clause}", params
        ).fetchone()["n"]
        responses = conn.execute(
            f"SELECT COUNT(*) AS n FROM crisis_actions WHERE country_id = ?{clause}", params
        ).fetchone()["n"]
        crackdowns = conn.execute(
            f"SELECT COUNT(*) AS n FROM crisis_actions WHERE country_id = ? AND action_key = 'security_crackdown'{clause}",
            params,
        ).fetchone()["n"]
        return {
            "total_crises": int(total or 0),
            "managed_crises": int(managed or 0),
            "responses": int(responses or 0),
            "crackdowns": int(crackdowns or 0),
        }
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# اخبار
# ─────────────────────────────────────────────────────────────────────────────
def build_news(country: dict, crisis: dict, event: str, damage: dict | None = None) -> tuple[str, str] | None:
    """(عنوان، متن) خبر کوتاه برای مرحله‌ی مشخصی از بحران."""
    spec = CRISIS_CATALOG.get(crisis["crisis_key"])
    if not spec:
        return None
    flag = country.get("flag") or "🏳️"
    name = country.get("name") or "کشور"
    severity = SEVERITY_LABELS.get(crisis["severity"], "")

    if event == "warning":
        return f"هشدار {spec['label']} — {flag} {name}", spec["warning"]
    if event == "impact":
        return f"{spec['label']} ({severity}) — {flag} {name}", spec["impact"]
    if event == "damage" and damage:
        parts = []
        if damage.get("population"):
            parts.append(f"تلفات و آوارگی: {damage['population']:,} نفر")
        if damage.get("treasury"):
            parts.append(f"خسارت مالی اولیه: {damage['treasury']:,} دلار")
        if damage.get("grain"):
            parts.append(f"از دست رفتن {damage['grain']:,} تن ذخایر غذایی")
        if not parts:
            return None
        return f"گزارش اولیه خسارت — {flag} {name}", "\n".join(f"• {p}" for p in parts)
    if event == "recovery":
        return f"آغاز بازسازی — {flag} {name}", f"مرحله‌ی حاد {spec['label']} پایان یافت و عملیات بازسازی آغاز شد."
    if event == "ended":
        mitigation = float(crisis.get("mitigation") or 0)
        if mitigation >= 0.4:
            body = "دولت با مدیریت به‌موقع، بحران را مهار کرد و وضعیت به حالت عادی بازگشت."
        elif mitigation > 0:
            body = "بحران پایان یافت، اما آثار آن تا مدتی بر اقتصاد کشور باقی خواهد ماند."
        else:
            body = "بحران بدون واکنش مؤثر دولت پایان یافت و خسارت‌ها سنگین برآورد می‌شود."
        return f"پایان {spec['label']} — {flag} {name}", body
    return None


def mark_news_sent(crisis_id: int, flag: str):
    conn = db.get_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE country_crises SET news_flags = news_flags || ? WHERE id = ? AND news_flags NOT LIKE ?",
                (f"{flag};", crisis_id, f"%{flag};%"),
            )
    finally:
        conn.close()


def news_already_sent(crisis: dict, flag: str) -> bool:
    return f"{flag};" in (crisis.get("news_flags") or "")
