"""نرمال‌سازی قیمت شناورها. پیش‌فرض dry-run؛ با --apply روی config.py اعمال می‌شود."""
import sys, re, json, argparse
sys.path.insert(0, "/home/user/project")
import config

# کلیدواژه‌های منفی: اگر در نام باشند، آن رده رد می‌شود
NEGATIVE_KEYWORDS = {
    "submarine": ("ضدزیردریایی", "ضد زیردریایی", "anti-submarine", "asw", "اسکوتر",
                  "dpv", "غواص", "تنفسی", "زیرسطحی"),
    "carrier":   ("ضدهوایی",),
}

SHIP_CLASS_RULES = [
    ("small_craft",  ("اسکوتر", "dpv", "غواص", "تنفسی", "زیرسطحی تکاور", "قورباغه")),
    ("light_carrier",("هواپیمابر سبک", "بالگردبر", "helicopter carrier", "بالگرد بر",
                      "izumo", "hyūga", "hyuga", "anadolu", "cavour", "chakri", "garibaldi",
                      "juan carlos", "dokdo", "کاوور")),
    ("carrier",      ("هواپیمابر", "carrier")),
    ("ssbn",         ("ssbn", "بالستیک اتمی", "vanguard", "borei", "ohio class ssbn", "triomphant")),
    ("cruiser",      ("رزم‌ناو", "cruiser", "ticonderoga", "kirov", "slava")),
    ("amphib",       ("آبی‌خاکی", "lhd", "lha", "lpd", "landing", "wasp class", "america class",
                      "mistral", "type 075", "دریابرد", "تانک‌بر", "ابرمر", "harpers ferry",
                      "whidbey", "san antonio", "type 071")),
    ("destroyer",    ("ناوشکن", "destroyer", "zumwalt", "arleigh", "type 055", "type 052")),
    ("midget_sub",   ("میدجت", "midget")),
    ("submarine",    ("زیردریایی", "submarine", "اسکورپن", "scorp", "کلاس کیلو")),
    ("frigate",      ("ناوچه", "frigate", "فریگیت")),
    ("corvette",     ("کوروت", "corvette", "corv")),
    ("missile_boat", ("موشک‌انداز", "missile boat", "fast attack", "fac ")),
    ("mine",         ("مین‌روب", "minehunter", "mine warfare", "مین‌گذار", "مین‌یاب")),
    ("support",      ("پشتیبانی", "سوخت‌رسان", "logistics", "supply", "tender", "تدارکات",
                      "ترابری", "تحقیقاتی", "هیدروگرافی", "تجسس", "نجات", "بیمارستان",
                      "آموزشی", "فرماندهی", "base")),
    ("patrol",       ("گشتی", "patrol", "قایق", "rib", "تندرو", "interceptor", "گشت",
                      "بی‌سرنشین", "usv", "هاورکرافت", "رودخانه", "gunboat", "strike boat")),
]

# باندهای هدف بر پایه‌ی قیمت‌گذاری کشورهای اصلی که بازی حولش بالانس شده
BANDS = {
    "carrier":      (40_000_000, 48_000_000),
    "light_carrier":(24_000_000, 34_000_000),
    "ssbn":         (38_000_000, 42_000_000),
    "cruiser":      (28_000_000, 45_000_000),
    "amphib":       (15_000_000, 36_000_000),
    "destroyer":    (15_000_000, 34_000_000),
    "submarine":    ( 3_000_000, 30_000_000),
    "frigate":      ( 8_000_000, 22_000_000),
    "corvette":     ( 6_000_000, 14_000_000),
    "missile_boat": ( 1_000_000, 12_000_000),
    "mine":         ( 3_000_000,  8_000_000),
    "support":      ( 3_000_000, 16_000_000),
    "patrol":       (    50_000,  5_000_000),
    "midget_sub":   (   800_000,  4_000_000),
    "small_craft":  (    10_000,    500_000),
}


def ship_class(name: str) -> str | None:
    low = (name or "").lower()
    for tag, words in SHIP_CLASS_RULES:
        if not any(w in low or w in name for w in words):
            continue
        neg = NEGATIVE_KEYWORDS.get(tag, ())
        if any(w in low or w in name for w in neg):
            continue          # مثلا «ناوچه ضدزیردریایی» زیردریایی نیست
        return tag
    return None


def normalized_price(price: int, klass: str) -> int:
    """قیمت داخل باند دست نمی‌خورد؛ فقط پرت‌ها فشرده می‌شوند."""
    lo, hi = BANDS[klass]
    if lo <= price <= hi:
        return price
    if price > hi:
        # فشرده‌سازی لگاریتمی تا ترتیب نسبی حفظ شود ولی از سقف رد نشود
        # فشرده‌سازی لگاریتمی داخل ۱۵٪ بالایی باند تا ترتیب نسبی حفظ شود
        import math
        span = hi - lo
        over = min(1.0, math.log10(price / hi) / 1.5)
        return int(hi - span * 0.15 * (1 - over))
    return lo


def collect():
    out = []
    for ck, items in config.COUNTRY_EQUIPMENT_CATALOG.items():
        for it in items:
            if it.get("category") != "Navy":
                continue
            k = ship_class(it["name"])
            if not k:
                continue
            new = normalized_price(int(it["price"]), k)
            if new != int(it["price"]):
                out.append({"country": ck, "key": it["key"], "name": it["name"],
                            "klass": k, "old": int(it["price"]), "new": new})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    ch = collect()
    up = [c for c in ch if c["new"] > c["old"]]
    dn = [c for c in ch if c["new"] < c["old"]]
    print(f"تغییرات: {len(ch)} قلم  (⬆️ {len(up)} گران‌تر | ⬇️ {len(dn)} ارزان‌تر)\n")
    print("۱۵ کاهش بزرگ:")
    for c in sorted(dn, key=lambda x: x["old"] - x["new"], reverse=True)[:15]:
        print(f"  {c['klass']:<12}{c['country']:<12}{c['old']:>13,} → {c['new']:>12,}  {c['name'][:40]}")
    print("\n۱۰ افزایش:")
    for c in sorted(up, key=lambda x: x["new"] - x["old"], reverse=True)[:10]:
        print(f"  {c['klass']:<12}{c['country']:<12}{c['old']:>13,} → {c['new']:>12,}  {c['name'][:40]}")

    if not a.apply:
        print("\n(اجرای آزمایشی — چیزی نوشته نشد. برای اعمال: --apply)")
        return

    src = open("/home/user/project/config.py", encoding="utf-8").read()
    done = 0
    for c in ch:
        pat = re.compile(r"(['\"]key['\"]:\s*['\"]%s['\"][^}]*?['\"]price['\"]:\s*)%d\b" % (re.escape(c["key"]), c["old"]))
        src, n = pat.subn(lambda m: m.group(1) + str(c["new"]), src, count=1)
        if n == 0:
            pat2 = re.compile(r"(['\"]price['\"]:\s*)%d(\s*,[^}]*?['\"]key['\"]:\s*['\"]%s['\"])" % (c["old"], re.escape(c["key"])))
            src, n = pat2.subn(lambda m: m.group(1) + str(c["new"]) + m.group(2), src, count=1)
        done += n
    open("/home/user/project/config.py", "w", encoding="utf-8").write(src)
    print(f"\n✅ اعمال شد: {done} از {len(ch)}")
    if done != len(ch):
        print(f"⚠️ {len(ch)-done} قلم پیدا نشد — باید دستی بررسی شود")


if __name__ == "__main__":
    main()
