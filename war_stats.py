# -*- coding: utf-8 -*-
"""
آمار واقع‌بینانه عملکرد سامانه‌ها برای موتور تحلیل نبرد.
منابع الهام: IISS Military Balance، نرخ‌های عملیاتی عمومی منتشرشده (گنبد آهنین در برابر راکت ~۸۵-۹۰٪،
پاتریوت در برابر تاکتیکال بالستیک ~۷۰٪، پدافند در برابر اشباع آتش به‌شدت افت می‌کند).
این جدول‌ها «حقیقت بازی» هستند؛ موتور فقط از آن‌ها محاسبه می‌کند.
"""

# ظرفیت درگیری: هر ۸ میلیون دلار سامانه پدافندی = یک کانال درگیری در هر موج
AD_CHANNEL_VALUE = 8_000_000

# نرخ رهگیری هر خانواده سامانه پدافندی بر اساس کلاس پرتابه (زیررشته در نام/کلید سامانه)
AD_RATES = {
    "iron_dome|گنبد آهنین":  {"rocket": 0.88, "drone": 0.70, "cruise": 0.30, "ballistic": 0.05, "aircraft": 0.05},
    "david|فلاخن|داوود":      {"rocket": 0.80, "drone": 0.75, "cruise": 0.75, "ballistic": 0.70, "aircraft": 0.55},
    "arrow|پیکان":            {"rocket": 0.30, "drone": 0.20, "cruise": 0.60, "ballistic": 0.80, "aircraft": 0.10},
    "thaad|ثاد":              {"rocket": 0.15, "drone": 0.20, "cruise": 0.55, "ballistic": 0.80, "aircraft": 0.20},
    "patriot|پاتریوت":        {"rocket": 0.50, "drone": 0.65, "cruise": 0.75, "ballistic": 0.70, "aircraft": 0.85},
    "s-400|s400|اس-400":      {"rocket": 0.45, "drone": 0.70, "cruise": 0.70, "ballistic": 0.65, "aircraft": 0.88},
    "s-300|s300|اس-300":      {"rocket": 0.40, "drone": 0.65, "cruise": 0.65, "ballistic": 0.55, "aircraft": 0.82},
    "bavar|باور":             {"rocket": 0.40, "drone": 0.65, "cruise": 0.65, "ballistic": 0.60, "aircraft": 0.80},
    "khordad|خرداد":          {"rocket": 0.35, "drone": 0.60, "cruise": 0.60, "ballistic": 0.45, "aircraft": 0.75},
    "hq-9|hq9":               {"rocket": 0.40, "drone": 0.65, "cruise": 0.65, "ballistic": 0.55, "aircraft": 0.80},
    "nasams|ناسامز":          {"rocket": 0.45, "drone": 0.70, "cruise": 0.60, "ballistic": 0.25, "aircraft": 0.75},
    "aster|sea viper":        {"rocket": 0.45, "drone": 0.70, "cruise": 0.70, "ballistic": 0.55, "aircraft": 0.80},
    "sm-6|sm-3|sm-2|aegis|ایجیس": {"rocket": 0.40, "drone": 0.70, "cruise": 0.75, "ballistic": 0.65, "aircraft": 0.80},
    "barak|باراک":            {"rocket": 0.40, "drone": 0.65, "cruise": 0.65, "ballistic": 0.50, "aircraft": 0.75},
    "buk|بوک":                {"rocket": 0.30, "drone": 0.55, "cruise": 0.50, "ballistic": 0.15, "aircraft": 0.70},
    "tor|تور-م|تورم":         {"rocket": 0.40, "drone": 0.60, "cruise": 0.50, "ballistic": 0.10, "aircraft": 0.65},
    "pantsir|پانتسیر":        {"rocket": 0.45, "drone": 0.65, "cruise": 0.55, "ballistic": 0.10, "aircraft": 0.60},
    "manpads|sa-7|sa-14|sa-18|sa-24|igla|strela|verba|مپادس": {"rocket": 0.02, "drone": 0.30, "cruise": 0.10, "ballistic": 0.0, "aircraft": 0.30},
    "default":                {"rocket": 0.45, "drone": 0.45, "cruise": 0.40, "ballistic": 0.25, "aircraft": 0.55},
}

# تلفات به‌ازای هر اصابت موفق (نظامی مدافع، غیرنظامی) — مقیاس بازی، متأثر از پخش نیروها
CASUALTY_PER_HIT = {
    "rocket": (2, 1), "artillery": (3, 1), "drone": (2, 1),
    "cruise": (6, 2), "ballistic": (12, 3), "aircraft": (8, 2), "naval": (10, 2),
}

# نرخ تلفه شدن عامل مهاجم (بدون احتساب مصرفی‌ها که کامل مصرف می‌شوند)
ATTACKER_ATTRITION = {"aircraft": 0.04, "armor": 0.05, "artillery": 0.04, "naval": 0.03, "sam": 0.02}

_BALLISTIC_HINTS = ["بالستیک", "ballistic", "fattah", "فتاح", "kheibar", "خیبر", "sejjil", "سجیل",
                    "emad", "عماد", "zolfaghar", "ذوالفقار", "hwasong", "iskander", "اسکندر",
                    "shahab", "شهاب", "ghadr", "قدر-", "khorramshahr", "خرمشهر", "dezful", "دزفول",
                    "qiam", "قیام", "haj_qasem", "حاج قاسم", "burkan", "برکان", "fajr", "فجر"]
_CRUISE_HINTS = ["کروز", "cruise", "delilah", "دلیله", "tomahawk", "kalibr", "کالیبر", "popeye",
                 "noor", "نور", "qader", "قادر", "p-800", "yakhont", "ascm", "ضدکشتی"]


def _norm(text: str) -> str:
    return str(text).lower().replace("\u200c", " ").replace("_", " ")


def weapon_class(item: dict) -> str:
    """کلاس‌بندی یک تجهیز درگیر: rocket/ballistic/cruise/drone/aircraft/artillery/armor/naval/sam/other"""
    cat = item.get("category", "")
    t = _norm(f"{item.get('name', '')} {item.get('equipment_key') or item.get('key', '')}")
    if cat == "UAV":
        return "drone"
    if cat == "Aircraft":
        return "aircraft"
    if cat == "Navy":
        return "naval"
    if cat == "Artillery":
        return "artillery"
    if cat == "Ground Forces":
        return "armor"
    if cat == "Air Defense":
        return "sam"
    if cat == "Missiles":
        if any(h in t for h in _BALLISTIC_HINTS):
            return "ballistic"
        if any(h in t for h in _CRUISE_HINTS):
            return "cruise"
        return "rocket"
    return "other"


def ad_rates_for(eq_key: str, eq_name: str) -> dict:
    """نرخ‌های رهگیری سامانه بر اساس تطبیق نام/کلید با جدول."""
    t = _norm(f"{eq_name} {eq_key}")
    for pattern, rates in AD_RATES.items():
        if pattern == "default":
            continue
        if any(part in t for part in pattern.split("|")):
            return rates
    return AD_RATES["default"]
