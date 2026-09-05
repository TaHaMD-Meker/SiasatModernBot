# -*- coding: utf-8 -*-
"""🛠 موتور تقابل واقعی تجهیزات — «تحلیلگر جنگ» عملیات‌های خودکار.

اصل قرارداد مالک: تلفات از تقابل واقعی درمی‌آید نه ریاضی کور —
F-35 مقابل S-200 دهه‌۷۰ تقریباً بی‌ریسک و پرنفوذ است؛ MiG-21 مقابل
S-300 می‌سوزد. مهمات دقیق مؤثر، مهمات کور پرت‌پزا. سقف‌های داکتورین
(کشته ≤۱۵۰، غیرنظامی <۵۰، مجروح ≈۲.۷×) همیشه برقرار می‌ماند.

این ماژول فقط برای مسیر «خودکار» است؛ در عملیات گسترده بات دخالت
نمی‌کند (داوری دستی مدیریت).
"""
import math
import random
import re

import config


def _norm(t) -> str:
    t = str(t or "").lower()
    t = t.replace("ی", "ی").replace("ک", "ک")
    t = re.sub(r"[\u200c\u064b-\u0652]", "", t)
    return t


def _match_class(policies: dict, *names) -> str | None:
    blob = " || ".join(_norm(n) for n in names if n)
    for cls, patterns in policies.items():
        for p in patterns:
            if _norm(p) in blob:
                return cls
    return None


def classify_aircraft(*names) -> str | None:
    return _match_class(config.AIRCRAFT_CLASS_PATTERNS, *names)


def classify_sam(*names) -> str | None:
    return _match_class(config.SAM_CLASS_PATTERNS, *names)


def classify_munition(*names) -> str | None:
    """کلاس مهمات — پهپاد مقدم بر موشک؛ هایپرسونیک مقدم بر کروز (قانون efd1dd2)."""
    blob = _norm(" ".join(str(n or "") for n in names))
    if any(p in blob for p in ("هایپرسونیک", "hypersonic", "زیرکون", "zircon", "avangard")):
        return "hypersonic"
    if any(p in blob for p in ("شاهد", "shahed", "شهید", "ابابیل", "ababil", "loitering", "انتحاری", "kamikaze", "هاروپ", "harop", "harpy")):
        return "drone_loitering"
    if any(p in blob for p in ("پهپاد", "drone", "uav", "مهاجر", "م هاجر", "hermes", "هرمس")):
        return "drone"
    if any(p in blob for p in ("بالستیک", "ballistic", "scud", "اسکاد", "شهاب", "فتاح", "fateh", "خانبر", "نودونگ", "isander", "اسکندر", "tochka", "توچکا")):
        return "ballistic"
    if any(p in blob for p in ("supersonic", "ابرصوت", "خ-۳۱", "kh-31", "براموس", "brahmos", "ونگو", "oniks")):
        return "supersonic_cruise"
    if any(p in blob for p in ("کروز", "cruise", "tomahawk", "تاماهاک", "کالیبر", "kalibr", "storm shadow", "استورم", "اسکالپ", "scalp", "خ-۵۵", "خ-۱۰۱", "kh-55", "kh-101", "جاسوم", "spice", "جدم", "jdam", "سایرآپ", "سوزوکی")):
        return "cruise"
    return None


PRECISION_HINTS = ("هدایت", "precision", "spice", "jdam", "storm", "استورم", "لایتینگ", "hellfire", "هل‌فایر", "هلفایر", "spike", "جدم", "کروز", "cruise", "هایپرسونیک", "hypersonic")


def is_precision(names) -> bool:
    blob = _norm(" ".join(str(n or "") for n in names))
    return any(_norm(p) in blob for p in PRECISION_HINTS)


def _defender_sam_profile(defender_id: int, defense_plan=None) -> dict:
    """کلاس→تعداد سامانه‌های پدافندی فعال مدافع از انبار واقعی.

    طرح دفاعی غیرفعال یعنی آماده‌باش/رادار کامل نیست؛ فقط سامانه‌های
    همیشه-روشن به‌صورت نصف‌ظرفیت حساب می‌شوند.
    """
    from database import get_country_assets
    profile = {}
    for a in get_country_assets(defender_id):
        cls = classify_sam(a.get("equipment_name"), a.get("equipment_key"))
        if cls:
            profile[cls] = profile.get(cls, 0) + int(a.get("amount") or 0)
    plan_active = bool(defense_plan and defense_plan.get("active"))
    if not plan_active:
        # بدون طرح فعال: فقط نیمی از ظرفیت آماده‌باش (سامانه‌های روشن پایه)
        profile = {k: v // 2 for k, v in profile.items()}
    return profile


def _best_interceptor(profile: dict) -> str:
    for cls in ("modern_long", "legacy_long", "mid", "aaa"):
        if profile.get(cls, 0) > 0:
            return cls
    return "none"


def _defender_batteries(profile: dict) -> int:
    return sum(profile.values())


def resolve_strike(attacker_id: int, defender_id: int, committed: list, plan_active: bool = False) -> dict:
    """تحلیل یک موج محدود.

    committed: [(asset_key, name, qty, kind)] که kind ∈ {aircraft, missile, drone}
    (فرم ۳تایی هم پذیرفته می‌شود؛ kind از نام استخراج می‌شود.)
    خروجی شامل نفوذ، تلفات پلتفرم مهاجم، تلفات تجهیزات مدافع و تلفات انسانی.
    """
    norm = []
    for item in committed:
        if len(item) == 3:
            k, n, q = item
            kind = "aircraft" if classify_aircraft(n) else "missile"
            norm.append((k, n, q, kind))
        else:
            norm.append(tuple(item))
    committed = norm
    profile = _defender_sam_profile(defender_id)
    interceptor = _best_interceptor(profile)
    batteries = _defender_batteries(profile)

    # ── ۱. نفوذ مهمات و پلتفرم‌ها ──
    total_munitions = sum(q for (k, n, q, kind) in committed if kind in ("missile", "drone"))
    total_aircraft = sum(q for (k, n, q, kind) in committed if kind == "aircraft")
    intercept = config.INTERCEPT_RATES.get(interceptor, config.INTERCEPT_RATES["none"])
    # تراکم پدافند: هر آتشبار فقط تا سهمی را پوشش می‌دهد (اشباع)
    defense_saturation = min(1.0, batteries / max(1.0, total_munitions * 1.5)) if total_munitions else 0.0

    penetrated_units = 0.0
    effective_shots = 0.0
    for (key, name, qty, kind) in committed:
        if kind == "aircraft":
            continue
        mcls = classify_munition(name) or "cruise"
        base = intercept.get(mcls, 0.15)
        intercepted = qty * base * (0.6 + 0.4 * defense_saturation)
        survived = max(0.0, qty - intercepted)
        if plan_active:
            # اثر «محدود» طرح دفاعی فعال: یک‌سومِ دوز فریب داکتورین + کاهش نفوذ ثابت
            survived *= (1 - config.DEFENSE_PLAN_PENETRATION_PENALTY - config.DECOY_ABSORB_SHARE / 3)
        prec = config.MUNITION_PRECISION.get(mcls, 0.6)
        penetrated_units += survived * prec
        effective_shots += survived

    aircraft_committed_proxy = [(k, n, q) for (k, n, q, kind) in committed if kind == "aircraft"]
    # جنگنده‌ها با «شلیک از فراتر» کار می‌کنند؛ فقط سهمی در حریم پدافند قرار می‌گیرند
    exposure_share = min(1.0, 0.35 + 0.15 * min(batteries, 8) / 8) if batteries else 0.15

    # سهم تحویل جنگنده‌ها — کیفیت نسل: استلت دقت بالا، نسل قدیمی پرت‌پزا
    _DELIVERY_QUALITY = {"stealth5": 0.95, "gen45": 0.8, "gen4": 0.65, "legacy": 0.45}
    delivered_air = 0.0
    for (key, name, qty) in aircraft_committed_proxy:
        acls = classify_aircraft(name) or "gen4"
        loss_rate = config.EXPOSURE_LOSS_RATES.get(interceptor, {}).get(acls, 0.02)
        survived_air = qty * (1 - loss_rate * exposure_share)
        delivered_air += survived_air * _DELIVERY_QUALITY.get(acls, 0.65)

    # ── ۲. تلفات پلتفرم‌های مهاجم (فقط جنگنده‌ها در معرض دید) ──
    attacker_losses = {}
    for (key, name, qty) in aircraft_committed_proxy:
        acls = classify_aircraft(name) or "gen4"
        loss_rate = config.EXPOSURE_LOSS_RATES.get(interceptor, {}).get(acls, 0.02)
        expected = qty * loss_rate * exposure_share
        # قطعی: تهدید معنادار (≥۰٫۳) = حداقل یک ازدست‌رفته؛ تهدید ناچیز = صفر
        lost = int(math.ceil(expected)) if expected >= 0.3 else 0
        if lost > 0:
            attacker_losses[key] = min(lost, qty)

    # ── ۳. تلفات تجهیزات مدافع (هدف‌محور: پدافند اول، بعد بقیه) ──
    defender_losses = _pick_defender_casualties(
        defender_id, profile, penetrated_units, is_precision_all=any(
            is_precision((n,)) for (k, n, q, kind) in committed if kind in ("missile", "drone")
        ),
    )

    # ── ۴. تلفات انسانی با سقف‌های داکتورین ──
    detonations = effective_shots
    kia = int(min(config.AUTO_ATTACK_MAX_KIA, round(6 + 2.2 * min(detonations, 45) + 1.5 * sum(q for (_k, q) in defender_losses))))
    wounded = int(round(kia * 2.7))
    civilians = int(min(config.AUTO_ATTACK_CIV_CAP - 1, round(kia * 0.18)))
    if civilians < 0:
        civilians = 0

    total_all = total_munitions + total_aircraft
    return {
        "penetration": round((penetrated_units + delivered_air) / max(1.0, total_all), 2) if total_all else 0.0,
        "effective_shots": round(effective_shots, 1),
        "interceptor_class": interceptor,
        "attacker_aircraft_losses": attacker_losses,
        "defender_asset_losses": defender_losses,
        "human": {"mil_kia": kia, "wounded": wounded, "civilians": civilians},
        "committed": committed,
    }


def _pick_defender_casualties(defender_id: int, sam_profile: dict, penetrated_units: float, is_precision_all: bool) -> list:
    """توزیع تلفات تجهیزاتی مدافع — اول پدافند (موج فحص/سپرسشن)، بعد اهداف مجاور.

    سقف: هر عملیات حداکثر ⅓ آتشبارهای پدافندی + تعداد محدودی تجهیز دیگر
    تا عملیات «محدود» واقعاً محدود بماند.
    """
    from database import get_country_assets
    assets = [a for a in get_country_assets(defender_id) if int(a.get("amount") or 0) > 0]
    if not assets or penetrated_units < 0.5:
        return []

    sam_units = [(a, classify_sam(a["equipment_name"], a["equipment_key"])) for a in assets]
    sam_units = [(a, cls) for (a, cls) in sam_units if cls]
    other_units = [a for a in assets if not classify_sam(a["equipment_name"], a["equipment_key"])]

    losses = []
    budget = penetrated_units
    # اولویت ۱: جنگ ضدپدافند (SEAD) — خونسردانه و ارزش‌محور:
    # اول سامانه‌های توانمندتر (مدرن → دوربرد قدیمی → میانی → توپ ضدهوایی)
    _CLS_ORDER = ("modern_long", "legacy_long", "mid", "aaa")
    if sam_units:
        total_sam = sum(int(a["amount"]) for a, _ in sam_units)
        cap = max(1, int(math.ceil(total_sam / 3)))
        hit = min(cap, int(math.floor(budget * 0.6)))
        if hit > 0:
            remaining_hit = hit
            for cls in _CLS_ORDER:
                if remaining_hit <= 0:
                    break
                group = [(a, c) for (a, c) in sam_units if c == cls and int(a["amount"]) > 0]
                if not group:
                    continue
                group_total = sum(int(a["amount"]) for a, _ in group)
                take = min(remaining_hit, group_total)
                # پخش متناسب درون کلاس با روش بزرگ‌ترین باقیمانده
                alloc, fracs = [], []
                used = 0
                for a, _c in group:
                    exact = take * int(a["amount"]) / group_total
                    w = int(math.floor(exact))
                    alloc.append([a, w])
                    fracs.append(exact - w)
                    used += w
                rem = take - used
                for i in sorted(range(len(alloc)), key=lambda i: -fracs[i]):
                    if rem <= 0:
                        break
                    if alloc[i][1] < int(alloc[i][0]["amount"]):
                        alloc[i][1] += 1
                        rem -= 1
                losses.extend((a["equipment_key"], w) for a, w in alloc if w > 0)
                remaining_hit -= take
            budget -= hit
    # اولویت ۲: باقیمانده بودجه روی تجهیزات رزمی دیگر — قطعی، حداکثر چند قلم
    if budget >= 1 and other_units:
        take_cap = min(int(math.floor(budget)), 3 if is_precision_all else 2)
        for a in other_units[:4]:
            if take_cap <= 0:
                break
            take = min(take_cap, int(a["amount"]))
            if take > 0:
                losses.append((a["equipment_key"], take))
                take_cap -= take

    return [(k, q) for (k, q) in losses if q > 0]
