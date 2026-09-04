# -*- coding: utf-8 -*-
"""موتور شورش مسلحانه — مغز یک «بازیکن بات» در برابر دولت بازیکن.

فلسفه:
  شورش یک تایمر نیست؛ یک بازیکن ساختگی است که هر شب تصمیم می‌گیرد، به واکنش
  دولت جواب می‌دهد (شاخص «جسارت») و از نردبان تشدید بالا می‌رود:
      🟡 آشوب شهری → 🟠 جنگ سایه → 🔴 جنگ گسترده → ⚫️ نبرد پایتخت

قواعد ایمنی:
  * همه‌چیز پشت کلید سراسری است (settings: insurgency_enabled) — پیش‌فرض خاموش.
  * همه‌ی اعداد نسبی‌اند (درصدی از آمار خود کشور) تا بین کشورها خودبالانس باشد.
  * همه‌ی اعداد تصادفی با seed بذردار تولید می‌شوند → هر شب قابل بازتولید و داوری.
  * مرگ فرمانده در این نسخه ممنوع است؛ فقط گروگان‌گیری/ناتوان‌سازی موقت.
  * هیچ خبری مستقیماً از این ماژول ارسال نمی‌شود؛ رویدادها برمی‌گردند تا لایه‌ی
    async (main.py) از طریق news_engine منتشرشان کند (با سقف روزانه).

این ماژول فقط منطق است؛ دسترسی داده از طریق database.py انجام می‌شود.
"""

from __future__ import annotations

import datetime
import random

import database as db

# ─────────────────────────────────────────────────────────────────────────────
# کلید و ثابت‌ها — همه‌ی اعداد بالانس اینجا هستند
# ─────────────────────────────────────────────────────────────────────────────
FEATURE_KEY = "insurgency_enabled"      # «۱» = روشن

ERUPTION_CHANCE = 0.60                  # شانس ترکیدن در هر شبِ واجد شرایط
POWER_MIN = 0.18                        # نیروی اولیه: ۱۸٪ تا ۳۰٪ پرسنل فعال دولت
POWER_MAX = 0.30
MIN_FIGHTERS = 40                       # زیر این عدد «گروهک» معنا ندارد

BOLDNESS_START = 55                     # جسارت اولیه (۰..۱۰۰)
BOLDNESS_IDLE = 15.0                    # دولت هیچ کاری نکند
BOLDNESS_WIN = -25.0                    # سرکوب موفق دولت
BOLDNESS_STALEMATE = 5.0                # بن‌بست
BOLDNESS_FINALE_FAIL = -8.0             # شکست تلاش فینال
BOLDNESS_BETRAYAL = 20.0

GROWTH_BASE = 0.05                      # جذب پایه در شب
GROWTH_LOW_APPROVAL = 0.08              # رضایت < ۳۰
GROWTH_FAMINE = 0.06                    # بحران غذا (غلات زیر کف)
GROWTH_WARTIME = 0.04                   # کشور در جنگ خارجی
DESERTION = 0.005                       # فرار شورشی هر شب
SOFT_CAP_RATIO = 0.60                   # بالای این نسبت، رشد اضافی محو می‌شود

GOV_ATTRITION = {1: 0.001, 2: 0.0025, 3: 0.0045, 4: 0.007}   # فرسایش پرسنل دولت

APPROVAL_HIT = (2, 4)                   # افت رضایت هر شب
UNREST_FLOOR = 45.0                     # کف ناآرامی تا پایان شورش (قفل)

PHASE_POWER = {2: 0.35, 3: 0.55, 4: 0.70}   # ورود به فاز با قدرت
PHASE_NIGHT = {2: 3, 3: 6}                  # یا با گذر شب‌ها (فاز ۴ فقط با قدرت)
PHASE_LABELS = {
    1: "🟡 آشوب شهری",
    2: "🟠 جنگ سایه",
    3: "🔴 جنگ گسترده",
    4: "⚫️ نبرد پایتخت",
}
PHASE_DOWN_FROM = 4                     # اگر نسبت بعد از سرکوب زیر این شد...
PHASE_DOWN_RATIO = 0.70                 # ...به فاز ۳ برمی‌گردد

# سرکوب
SUPPRESSION_ASSIGN = {"light": 0.40, "wide": 0.70, "heavy": 0.90}
SUPPRESSION_REQUIRED = 1.6              # نیروی لازم = ۱.۶ برابر شورش
SUPPRESSION_HEAVY_MULT = 1.5            # پیشروی سریع‌تر در حالت سنگین
REBEL_LOSS_WIN = (0.08, 0.15)
REBEL_LOSS_HEAVY = (0.15, 0.25)
GOV_KIA_WIN = (5, 15)
GOV_KIA_STALEMATE = (8, 25)
REBEL_KIA_STALEMATE = (10, 30)
CIVILIAN_WIN = (0, 4)
CIVILIAN_STALEMATE = (0, 6)
CIVILIAN_HEAVY = (4, 28)
HEAVY_APPROVAL_HIT = (8, 12)
HEAVY_UNREST_ADD = 10.0
COST_PER_SOLDIER = {"light": 6, "wide": 9, "heavy": 13}       # دلار
FUEL_PER_SOLDIER = {"light": 0.010, "wide": 0.015, "heavy": 0.030}  # بشکه
MAX_ACTIONS_PER_NIGHT = 2

# مذاکره
NEGOTIATION_TREASURY_PCT = 0.10
NEGOTIATION_MONTHLY_INCOME_PCT = 0.80   # از درآمد مالیاتی ~۳۰ شب
NEGOTIATION_POWER_CUT = (0.20, 0.35)
NEGOTIATION_UNREST_DROP = 8.0
NEGOTIATION_BOLDNESS = -10.0
NEGOTIATION_COOLDOWN_NIGHTS = 3
TRUCE_BETRAY_CHANCE = 0.35
TRUCE_BETRAY_DELAY = (2, 3)
TRUCE_BETRAY_GROWTH = 0.10

# فینال فاز ۴
FINALE_BASE_CHANCE = 0.22
FINALE_BOLDNESS_BONUS = 0.18
HOSTAGE_CHANCE = 0.12                   # فقط فاز ۳ و ۴ — گروگان، نه مرگ
SLOT_BOLDNESS_WIN = 3.0                 # جسارت += حمله‌ی دوره‌ای موفق
GUARD_BOLDNESS_FOIL = -6.0              # جسارت -= حمله‌ی خنثی‌شده

TREASURY_SKIM = (0.005, 0.015)          # خزانه‌داریِ عملیات‌های مهاجم
OIL_SABOTAGE = (0.004, 0.012)           # حمله به مخازن سوخت
GRAIN_RAID = (0.005, 0.015)             # حمله به انبار غلات
BANK_RAID = (0.003, 0.008)              # سرقت از بانک‌ها (سهم خزانه)
CAMP_KIA = (8, 25)                      # حمله به اردوگاه نظامی
FOILED_REBEL_KIA = (2, 8)               # تلفات شورشیان وقتی حمله خنثی می‌شود

# تدابیر امنیتی دولت — «جلوگیری قبل از حمله»
GUARD_SLOTS = 4                         # هر فعال‌سازی: ۴ دوره‌ی ۶ ساعته (یک شبانه‌روز)
GUARD_FOIL_CHANCE = 0.45                # شانس خنثی‌سازی هر حمله
GUARD_COST_PCT = 0.004                  # هزینه: ۰.۴٪ خزانه

# خبر
NEWS_CAP_PER_NIGHT = 2
NEWS_DATE_KEY = "insurgency_news_date"
NEWS_COUNT_KEY = "insurgency_news_count"

MODE_LABELS = {
    "light": "⚔️ سرکوب محدود",
    "wide": "🎯 حمله‌ی گسترده",
    "heavy": "🔥 سرکوب سنگین",
}

# استخر حمله‌های دوره‌ای ۶ ساعته — هم‌ضرب با گرید پرداخت خزانه
# (کلید، کمینه‌فاز، وزن) — اردوگاه از فاز ۳، کارخانه از فاز ۲
SLOT_ATTACK_CHANCE = 0.75               # شانس حمله در هر دوره
SLOT_OPS = (
    ("grain_depot",  1, 3),   # 🌾 انبار غلات → خسارت غلات
    ("fuel_depot",   1, 3),   # ⛽ پمپ بنزین/مخازن سوخت → خسارت نفت
    ("bank_raid",    1, 3),   # 🏦 بانک‌ها → خسارت مالی
    ("factory_raid", 2, 2),   # 🏭 کارخانه/سازه → خاموشی یک واحد
    ("camp_raid",    3, 3),   # 🎖️ اردوگاه نظامی → تلفات نظامی
)
NEWS_SLOT_CAP = 2                       # سقف خبر حمله در هر دوره (کل کانال)

FINALE_OBJECTIVES = ("فتح ساختمان ریاست‌جمهوری", "محاصره‌ی پارلمان",
                     "تصرف صداوسیمای دولتی", "فرار رهبر کشور به خارج")


# ─────────────────────────────────────────────────────────────────────────────
# کلید و وضعیت
# ─────────────────────────────────────────────────────────────────────────────
try:
    from zoneinfo import ZoneInfo as _ZoneInfo
    IRAN_TZ = _ZoneInfo("Asia/Tehran")
except Exception:  # pragma: no cover
    IRAN_TZ = datetime.timezone(datetime.timedelta(hours=3, minutes=30))


def today_tehran() -> str:
    """تاریخ روز به وقت ایران — مبنای کلیدهای «امشب» در پنل و موتور."""
    return datetime.datetime.now(datetime.timezone.utc).astimezone(IRAN_TZ).date().isoformat()


def is_enabled() -> bool:
    return db.get_setting(FEATURE_KEY) == "1"


def set_enabled(on: bool, admin_id: int = 0, role: str = "owner"):
    db.set_setting(FEATURE_KEY, "1" if on else "0")
    try:
        db.log_admin_action(admin_id, role, "insurgency_toggle",
                            target="global", details="on" if on else "off")
    except Exception:
        pass


def get(country_id: int) -> dict | None:
    return db.get_insurgency(country_id)


def power_ratio(ins: dict, country: dict) -> float:
    """نسبت نیروی شورش به پرسنل فعال دولت (۰..)."""
    gov = max(1, int(country.get("active_personnel") or 0))
    return float(ins["fighters"]) / gov


def phase_of(ins: dict) -> int:
    return max(1, min(4, int(ins.get("phase") or 1)))


def status_line(country: dict) -> str:
    """خط وضعیت برای گزارش صبحگاهی و پنل ادمین."""
    ins = get(int(country.get("id") or 0))
    if not ins:
        return ""
    pct = power_ratio(ins, country) * 100
    host = f" | 🎖️ گروگان: {ins['commander_hostage']}" if ins.get("commander_hostage") else ""
    return (f"⚔️ <b>شورش مسلحانه</b> — شب {int(ins['night'])} | فاز: {PHASE_LABELS[phase_of(ins)]} | "
            f"قدرت: {pct:.0f}٪ پرسنل دولت | روحیه: {int(ins['boldness'])}{host}")


# ─────────────────────────────────────────────────────────────────────────────
# ترکیدن
# ─────────────────────────────────────────────────────────────────────────────
def eruption_allowed(country: dict, cycle: dict | None = None) -> bool:
    """گیت‌های ترکیدن خودکار: کلید روشن + بازیکن دارد + collapse_risk."""
    if not is_enabled():
        return False
    if not country.get("player_id"):
        return False
    if get(int(country["id"])):
        return False
    if not ((cycle or {}).get("collapse_risk") or 0):
        return False
    return True


def erupt(country: dict, today_str: str, seed=None, force: bool = False) -> dict | None:
    """ترکیدن شورش. گیت بحرانی (collapse_risk) با لایه‌ی بالاتر (nightly_tick) چک می‌شود؛
    اینجا فقط کلید، تکراری‌نبودن و در حالت غیرفورس شانس ۶۰٪."""
    if not is_enabled() or get(int(country["id"])):
        return None

    rng = random.Random(seed if seed is not None else f"erupt|{country['id']}|{today_str}")
    if not force and rng.random() > ERUPTION_CHANCE:
        return None

    gov = max(1, int(country.get("active_personnel") or 0))
    fighters = max(MIN_FIGHTERS, int(gov * rng.uniform(POWER_MIN, POWER_MAX)))
    ins = db.create_insurgency(int(country["id"]), fighters,
                               seed_base=rng.randrange(10 ** 9),
                               now_str=_now_str())
    return {"ins": ins, "fighters": fighters,
            "gov_personnel": gov, "ratio": fighters / max(1, gov)}


# ─────────────────────────────────────────────────────────────────────────────
# چرخه‌ی شبانه — مغز بات
# ─────────────────────────────────────────────────────────────────────────────
def nightly_tick(country: dict, today_str: str, cycle: dict | None = None) -> dict:
    """یک شب از زندگی شورش. خروجی: رویدادها + خط گزارش + پرچم سقوط.

    Idempotent است: اگر last_tick_date == today_str باشد کاری نمی‌کند.
    """
    out: dict = {"events": [], "report": "", "collapse": False, "news": False}
    if not is_enabled():
        return out
    cid = int(country.get("id") or 0)
    if not cid:
        return out

    ins = get(cid)
    if not ins:
        # شانس ترکیدن امشب — فقط وقتی چرخه‌ی امروز collapse_risk داده باشد
        if eruption_allowed(country, cycle):
            res = erupt(country, today_str)
            if res:
                out["events"].append({"kind": "eruption", "seed": ins_seed(res["ins"])})
                out["report"] = status_line(country)
                out["news"] = True
        return out

    if (ins.get("last_tick_date") or "") == today_str:
        out["report"] = status_line(country)
        return out

    rng = random.Random(f"{ins['seed_base']}|{ins['night']}|{today_str}")
    phase = phase_of(ins)
    ratio = power_ratio(ins, country)

    # ۱) جذب نیرو و فرار
    growth = GROWTH_BASE
    approval = int(country.get("approval_rating") or 0)
    if approval < 30:
        growth += GROWTH_LOW_APPROVAL
    if _in_famine(country):
        growth += GROWTH_FAMINE
    if _at_war(country):
        growth += GROWTH_WARTIME
    if ratio > SOFT_CAP_RATIO:
        growth *= max(0.2, 1.0 - (ratio - SOFT_CAP_RATIO) * 2.0)
    fighters = ins["fighters"] * (1.0 + growth - DESERTION)

    # ۲) فرسایش پرسنل دولت
    gov_kia_attrition = int(max(1, int(country.get("active_personnel") or 0)) * GOV_ATTRITION[phase] * rng.uniform(0.7, 1.3))

    # ۳) رضایت و ناآرامی
    approval_drop = rng.randint(*APPROVAL_HIT)

    # ۴) جسارت: دولت بی‌کار مانده؟ (آخرین عملیت ثبت‌شده قبل از این شب)
    boldness_delta = BOLDNESS_IDLE if (ins.get("last_action_date") or "") != today_str else 0.0

    # ۵) خیانت به آتش‌بس
    betrayal = False
    if ins.get("truce_betray_night") and ins["night"] >= int(ins["truce_betray_night"]):
        betrayal = True
        fighters *= (1.0 + TRUCE_BETRAY_GROWTH)
        boldness_delta += BOLDNESS_BETRAYAL

    fighters = max(MIN_FIGHTERS * 0.5, int(fighters))
    new_ratio = fighters / max(1, int(country.get("active_personnel") or 1) - gov_kia_attrition or 1)

    # ۶) مغز راهبردی شبانه: ارتقای فاز و فینال نبرد پایتخت
    #    (حمله‌های تاکتیکی اقتصادی به دوره‌های ۶ ساعته منتقل شد → slot_tick)
    new_phase = _escalate_phase(ins, new_ratio)
    ops = []

    if new_phase == 4:
        finale_obj = FINALE_OBJECTIVES[rng.randrange(len(FINALE_OBJECTIVES))]
        p = FINALE_BASE_CHANCE + FINALE_BOLDNESS_BONUS * (max(0.0, min(100.0, ins["boldness"] + boldness_delta)) / 100.0)
        if rng.random() < p:
            out["collapse"] = True
            ops.append({"kind": "finale_win", "objective": finale_obj,
                        "gov_kia": rng.randint(*GOV_KIA_WIN) + rng.randint(10, 30),
                        "civ": rng.randint(10, 40)})
        else:
            boldness_delta += BOLDNESS_FINALE_FAIL
            ops.append({"kind": "finale_fail", "objective": finale_obj,
                        "gov_kia": rng.randint(25, 60), "civ": rng.randint(10, 40)})

    # گروگان‌گیری (فاز ۳ و ۴، بدون مرگ)
    hostage = None
    if new_phase >= 3 and not (ins.get("commander_hostage") or "") and rng.random() < HOSTAGE_CHANCE:
        hostage = db.insurgency_take_hostage(cid)

    # ۷) اعمال افکت‌ها به دیتابیس
    db.insurgency_apply_effects(
        cid,
        fighters_delta=fighters - ins["fighters"],
        boldness_delta=boldness_delta,
        approval_delta=-approval_drop,
        unrest_floor=UNREST_FLOOR,
        personnel_delta=-gov_kia_attrition - sum(op.get("gov_kia", 0) for op in ops),
        treasury_delta=0,
        oil_delta_pct=0, grain_delta_pct=0, chips_delta_pct=0,
        outage_item=None,
        phase=new_phase,
        night=ins["night"] + 1,
        last_tick_date=today_str,
        neg_cooldown=max(0, int(ins.get("neg_cooldown") or 0) - 1),
    )

    ins = get(cid) or ins
    out["events"] = [_event(ins, country, op, betrayal) for op in ops]
    if new_phase > phase:
        out["events"].insert(0, {"kind": "escalation", "phase": new_phase, "seed": ins["seed_base"]})
    if betrayal:
        out["events"].insert(0, {"kind": "betrayal", "seed": ins["seed_base"]})
    if hostage:
        out["events"].append({"kind": "hostage", "title": hostage, "seed": ins["seed_base"]})
    out["report"] = status_line(country)
    big = out["collapse"] or new_phase != phase or betrayal or hostage
    out["news"] = bool(big)
    return out


# ─────────────────────────────────────────────────────────────────────────────
# حمله‌های دوره‌ای ۶ ساعته — هم‌ضرب با گرید پرداخت خزانه
# ─────────────────────────────────────────────────────────────────────────────
def _slot_pool(phase: int) -> list[tuple[str, int]]:
    """اهداف مجاز این فاز با وزن."""
    return [(key, w) for key, min_phase, w in SLOT_OPS if phase >= min_phase]


def _pick_slot_op(rng: random.Random, phase: int) -> str:
    pool = _slot_pool(phase)
    total = sum(w for _, w in pool)
    r = rng.uniform(0, total)
    acc = 0.0
    for key, w in pool:
        acc += w
        if r <= acc:
            return key
    return pool[0][0]


def _run_slot_op(rng: random.Random, op_key: str, country: dict) -> dict:
    """افکت‌های خام یک حمله‌ی دوره‌ای."""
    op: dict = {"kind": op_key}
    treasury = int(country.get("treasury") or 0)
    if op_key == "grain_depot":
        op["grain_pct"] = rng.uniform(*GRAIN_RAID)
    elif op_key == "fuel_depot":
        op["oil_pct"] = rng.uniform(*OIL_SABOTAGE)
        op["gov_kia"] = rng.randint(1, 5)
    elif op_key == "bank_raid":
        op["skim"] = int(max(1, treasury * rng.uniform(*BANK_RAID)))
        op["gov_kia"] = rng.randint(0, 3)
    elif op_key == "factory_raid":
        op["outage_item"] = db.pick_random_structure_item(int(country["id"]))
        op["gov_kia"] = rng.randint(1, 6)
        if not op["outage_item"]:
            op["skim"] = int(max(1, treasury * rng.uniform(*BANK_RAID)))
    elif op_key == "camp_raid":
        op["gov_kia"] = rng.randint(*CAMP_KIA)
        op["skim"] = 0
    op.setdefault("gov_kia", 0)
    op.setdefault("skim", 0)
    return op


def slot_tick(country: dict, slot_key_str: str) -> dict:
    """یک دوره‌ی ۶ ساعته از زندگی شورش — حمله به یک هدف اقتصادی/نظامی رندوم.

    Idempotent با slot_key. اگر «تدابیر امنیتی» فعال باشد، حمله با شانس
    GUARD_FOIL_CHANCE خنثی می‌شود (بدون خسارت، با تلفات کم برای شورشیان).
    خروجی: رویداد برای خبر + خط گزارش.
    """
    out: dict = {"events": [], "report": "", "news": False}
    if not is_enabled():
        return out
    cid = int(country.get("id") or 0)
    if not cid:
        return out
    ins = get(cid)
    if not ins:
        return out
    if (ins.get("slot_key") or "") == slot_key_str:
        return out

    rng = random.Random(f"{ins['seed_base']}|slot|{slot_key_str}|{ins['night']}")
    phase = phase_of(ins)
    guard_left = int(ins.get("guard_slots") or 0)

    event = None
    if rng.random() < SLOT_ATTACK_CHANCE:
        op_key = _pick_slot_op(rng, phase)
        if guard_left > 0 and rng.random() < GUARD_FOIL_CHANCE:
            # خنثی‌سازی — تدابیر امنیتی جواب داده
            rebel_kia = rng.randint(*FOILED_REBEL_KIA)
            event = {"kind": "foiled_raid", "target": op_key, "seed": ins["seed_base"],
                     "country_name": country.get("name"), "country_flag": country.get("flag"),
                     "rebel_kia": rebel_kia, "phase": phase}
            db.insurgency_apply_effects(
                cid, fighters_delta=-rebel_kia, boldness_delta=GUARD_BOLDNESS_FOIL,
                slot_key=slot_key_str, guard_slots=max(0, guard_left - 1))
        else:
            op = _run_slot_op(rng, op_key, country)
            skim = op.pop("skim", 0)
            event = {"kind": op_key, "seed": ins["seed_base"],
                     "country_name": country.get("name"), "country_flag": country.get("flag"),
                     "phase": phase}
            db.insurgency_apply_effects(
                cid,
                boldness_delta=SLOT_BOLDNESS_WIN,
                personnel_delta=-op["gov_kia"],
                treasury_delta=-skim,
                oil_delta_pct=op.get("oil_pct", 0),
                grain_delta_pct=op.get("grain_pct", 0),
                chips_delta_pct=0,
                outage_item=op.get("outage_item"),
                slot_key=slot_key_str,
                guard_slots=max(0, guard_left - 1),
            )
        out["events"].append(event)
        out["news"] = True
    else:
        # امشب حمله نبود؛ فقط اعتبار تدابیر یکی کم می‌شود
        db.insurgency_apply_effects(cid, slot_key=slot_key_str,
                                    guard_slots=max(0, guard_left - 1))

    fresh = db.get_country_by_id(cid) or country
    out["report"] = status_line(fresh)
    return out


# تدابیر امنیتی
def guard_preview(country: dict) -> dict:
    cost = max(1, int(int(country.get("treasury") or 0) * GUARD_COST_PCT))
    ins = get(int(country["id"]))
    return {"cost": cost, "active_slots": int(ins.get("guard_slots") or 0) if ins else 0,
            "total_slots": GUARD_SLOTS}


def resolve_guard(country: dict) -> dict:
    """فعال‌سازی تدابیر امنیتی برای GUARD_SLOTS دوره‌ی بعد."""
    res = {"ok": False, "reason": ""}
    if not is_enabled():
        res["reason"] = "disabled"
        return res
    cid = int(country["id"])
    if not get(cid):
        res["reason"] = "no_insurgency"
        return res
    prev = guard_preview(country)
    if prev["active_slots"] >= GUARD_SLOTS:
        res["reason"] = "already_active"
        return res
    if int(country.get("treasury") or 0) < prev["cost"]:
        res["reason"] = "no_money"
        return res
    db.insurgency_apply_effects(cid, treasury_delta=-prev["cost"],
                                guard_slots=GUARD_SLOTS)
    res.update({"ok": True, "cost": prev["cost"], "slots": GUARD_SLOTS})
    return res


# ─────────────────────────────────────────────────────────────────────────────
# اقدامات دولت
# ─────────────────────────────────────────────────────────────────────────────
def suppression_preview(country: dict, mode: str) -> dict:
    """اطلاعات نمایشی قبل از تأیید عملیات."""
    ins = get(int(country["id"]))
    gov = max(1, int(country.get("active_personnel") or 0))
    assigned = int(gov * SUPPRESSION_ASSIGN.get(mode, 0.4))
    cost = assigned * COST_PER_SOLDIER.get(mode, 6)
    fuel = int(assigned * FUEL_PER_SOLDIER.get(mode, 0.01)) + 1
    required = int(SUPPRESSION_REQUIRED * (ins["fighters"] if ins else 0))
    return {"assigned": assigned, "cost": cost, "fuel": fuel, "required": required,
            "enough": assigned >= required and (ins is not None)}


def resolve_suppression(country: dict, mode: str, today_str: str, seed=None) -> dict:
    """حل یک عملیات سرکوب. خروجی برای نمایش BDA دوطرفه در پنل."""
    res = {"ok": False, "reason": "", "mode": mode}
    if mode not in SUPPRESSION_ASSIGN:
        res["reason"] = "mode_invalid"
        return res
    if not is_enabled():
        res["reason"] = "disabled"
        return res
    cid = int(country["id"])
    ins = get(cid)
    if not ins:
        res["reason"] = "no_insurgency"
        return res
    if (ins.get("last_action_date") or "") == today_str and int(ins.get("actions_today") or 0) >= MAX_ACTIONS_PER_NIGHT:
        res["reason"] = "action_limit"
        return res

    prev = suppression_preview(country, mode)
    if int(country.get("active_personnel") or 0) < prev["assigned"]:
        res["reason"] = "no_personnel"
        return res
    if int(country.get("treasury") or 0) < prev["cost"]:
        res["reason"] = "no_money"
        return res
    if int(country.get("oil_reserves") or 0) < prev["fuel"]:
        res["reason"] = "no_fuel"
        return res

    n_action = int(ins.get("actions_today") or 0)
    if (ins.get("last_action_date") or "") != today_str:
        n_action = 0
    rng = random.Random(seed if seed is not None else f"{ins['seed_base']}|sup|{today_str}|{n_action}")

    assigned = prev["assigned"]
    heavy = mode == "heavy"
    required = prev["required"] / (SUPPRESSION_HEAVY_MULT if heavy else 1.0)
    rebels = ins["fighters"]

    if assigned < required:
        # بن‌بست خونین — صفر پیشروی
        gov_kia = rng.randint(*GOV_KIA_STALEMATE)
        rebel_kia = rng.randint(*REBEL_KIA_STALEMATE)
        civ = rng.randint(*CIVILIAN_STALEMATE)
        rebel_loss = min(rebels - 1, rebel_kia)
        bold_delta = BOLDNESS_STALEMATE
        outcome = "stalemate"
    else:
        gov_kia = rng.randint(*GOV_KIA_WIN)
        civ = rng.randint(*CIVILIAN_HEAVY if heavy else CIVILIAN_WIN)
        lo, hi = REBEL_LOSS_HEAVY if heavy else REBEL_LOSS_WIN
        rebel_loss = int(rebels * rng.uniform(lo, hi))
        bold_delta = BOLDNESS_WIN
        outcome = "win"

    # هزینه‌ها و تلفات
    freed_hostage = None
    if outcome == "win" and (ins.get("commander_hostage") or ""):
        freed_hostage = db.insurgency_free_hostage(cid)

    new_fighters = max(0, rebels - rebel_loss)
    phase = phase_of(ins)
    if phase == PHASE_DOWN_FROM:
        new_ratio = new_fighters / max(1, int(country.get("active_personnel") or 0) - gov_kia or 1)
        if new_ratio < PHASE_DOWN_RATIO:
            phase = 3

    db.insurgency_apply_effects(
        cid,
        fighters_delta=new_fighters - rebels,
        boldness_delta=bold_delta,
        approval_delta=-(rng.randint(*HEAVY_APPROVAL_HIT) if heavy else 0),
        unrest_floor=UNREST_FLOOR,
        unrest_add=HEAVY_UNREST_ADD if heavy else 0,
        personnel_delta=-gov_kia,
        treasury_delta=-prev["cost"],
        oil_delta_units=-prev["fuel"],
        grain_delta_pct=0, chips_delta_pct=0,
        outage_item=None, phase=phase,
        night=ins["night"], action_date=today_str, actions_count=1,
    )

    res.update({
        "ok": True, "outcome": outcome, "assigned": assigned, "gov_kia": gov_kia,
        "rebel_kia": rebel_loss, "civ": civ, "cost": prev["cost"], "fuel": prev["fuel"],
        "fighters_left": new_fighters, "boldness": get(cid)["boldness"] if get(cid) else 0,
        "phase": phase, "freed_hostage": freed_hostage,
        "injured_gov": int(gov_kia * 2.7), "injured_rebel": int(rebel_loss * 2.7),
        "injured_civ": int(civ * 2.7),
    })
    return res


def resolve_negotiation(country: dict, today_str: str, seed=None) -> dict:
    """مذاکره/عفو — هزینه‌دار، با ریسک خیانت."""
    res = {"ok": False, "reason": ""}
    if not is_enabled():
        res["reason"] = "disabled"
        return res
    cid = int(country["id"])
    ins = get(cid)
    if not ins:
        res["reason"] = "no_insurgency"
        return res
    if int(ins.get("neg_cooldown") or 0) > 0:
        res["reason"] = "cooldown"
        return res

    treasury = int(country.get("treasury") or 0)
    monthly_income = int((db.get_internal_state_baseline(cid) or 0) * 30)
    cost = min(int(treasury * NEGOTIATION_TREASURY_PCT),
               int(monthly_income * NEGOTIATION_MONTHLY_INCOME_PCT))
    cost = max(cost, 1)
    if treasury < cost:
        res["reason"] = "no_money"
        return res

    rng = random.Random(seed if seed is not None else f"{ins['seed_base']}|neg|{today_str}")
    cut = rng.uniform(*NEGOTIATION_POWER_CUT)
    betrayal_night = None
    if rng.random() < TRUCE_BETRAY_CHANCE:
        betrayal_night = ins["night"] + rng.randint(*TRUCE_BETRAY_DELAY)

    new_fighters = max(1, int(ins["fighters"] * (1.0 - cut)))
    db.insurgency_apply_effects(
        cid,
        fighters_delta=new_fighters - ins["fighters"],
        boldness_delta=NEGOTIATION_BOLDNESS,
        approval_delta=1,
        unrest_floor=UNREST_FLOOR,
        unrest_add=-NEGOTIATION_UNREST_DROP,
        personnel_delta=0, treasury_delta=-cost,
        oil_delta_units=0, grain_delta_pct=0, chips_delta_pct=0,
        outage_item=None, phase=phase_of(ins), night=ins["night"],
        neg_cooldown=NEGOTIATION_COOLDOWN_NIGHTS,
        truce_betray_night=betrayal_night,
    )
    res.update({"ok": True, "cost": cost, "power_cut_pct": cut * 100,
                "fighters_left": new_fighters, "betrayal_night": betrayal_night})
    return res


# ─────────────────────────────────────────────────────────────────────────────
# سقوط دولت
# ─────────────────────────────────────────────────────────────────────────────
def collapse_snapshot(country: dict, ins: dict) -> str:
    """اسنپ‌شات برای بایگانی داوری — قبل از حذف."""
    import json
    snap = {
        "country": {"id": country.get("id"), "name": country.get("name"),
                    "flag": country.get("flag"), "player_id": country.get("player_id"),
                    "treasury": country.get("treasury"),
                    "active_personnel": country.get("active_personnel"),
                    "population": country.get("population")},
        "insurgency": {"fighters": ins.get("fighters"), "phase": ins.get("phase"),
                       "night": ins.get("night"), "boldness": ins.get("boldness"),
                       "hostage": ins.get("commander_hostage")},
        "at": _now_str(),
    }
    return json.dumps(snap, ensure_ascii=False)


def execute_collapse(country: dict, today_str: str) -> dict:
    """سقوط کامل: لاگ + حذف کشور + بازگشت بازیکن به صف. خبر و DM با لایه‌ی async."""
    cid = int(country["id"])
    ins = get(cid) or {}
    snap = collapse_snapshot(country, ins)
    try:
        db.log_admin_action(0, "system", "insurgency_collapse",
                            target=f"country:{cid}", details=snap)
    except Exception:
        pass
    db.delete_insurgency(cid)
    db.delete_country_by_id(cid, actor="insurgency_collapse")
    pid = country.get("player_id")
    requeued = False
    if pid:
        try:
            remaining = db.get_player_all_entities(int(pid))
            if remaining:
                # بازیکن هنوز نهاد دارد (مثلاً بازوی نیابتی) — سوییچ به اولین نهاد
                db.set_setting(f"active_entity_{int(pid)}", str(remaining[0]["id"]))
            else:
                # صف کشور حذف شده — بازیکن مستقیم از /start کشور بعدی را درخواست می‌کند
                requeued = False
        except Exception:
            pass
    return {"snapshot": snap, "player_id": pid, "requeued": requeued, "date": today_str}


# ─────────────────────────────────────────────────────────────────────────────
# سقف خبر
# ─────────────────────────────────────────────────────────────────────────────
def news_budget_take(today_str: str, force: bool = False) -> bool:
    """سهم خبر از سقف روزانه را رزرو می‌کند. سقوط (force=True) همیشه مجاز است."""
    if db.get_setting(NEWS_DATE_KEY) != today_str:
        db.set_setting(NEWS_DATE_KEY, today_str)
        db.set_setting(NEWS_COUNT_KEY, "0")
    count = int(db.get_setting(NEWS_COUNT_KEY) or 0)
    if not force and count >= NEWS_CAP_PER_NIGHT:
        return False
    db.set_setting(NEWS_COUNT_KEY, str(count + 1))
    return True


def news_budget_take_slot(slot_key_str: str) -> bool:
    """سهم خبر حمله‌ی دوره‌ای — مستقل از سقف شبانه، سقف خودش در هر دوره."""
    key = f"insurgency_news_slot:{slot_key_str}"
    if db.get_setting(key) is None:
        db.set_setting(key, "0")
    count = int(db.get_setting(key) or 0)
    if count >= NEWS_SLOT_CAP:
        return False
    db.set_setting(key, str(count + 1))
    return True


# ─────────────────────────────────────────────────────────────────────────────
# داخلی‌ها
# ─────────────────────────────────────────────────────────────────────────────
def ins_seed(ins: dict) -> int:
    return int(ins.get("seed_base") or 0)


def _now_str() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def _in_famine(country: dict) -> bool:
    grain = country.get("grain")
    floor = getattr(country, "grain_floor", None)
    try:
        return grain is not None and float(grain) < float(floor or 0)
    except Exception:
        return False


def _at_war(country: dict) -> bool:
    try:
        return bool(db.country_has_active_war(int(country["id"])))
    except Exception:
        return False


def _escalate_phase(ins: dict, ratio: float) -> int:
    phase = phase_of(ins)
    night = int(ins["night"]) + 1
    for p in (4, 3, 2):
        if ratio >= PHASE_POWER[p]:
            return max(phase, p)
    for p in (3, 2):
        if phase < p and night >= PHASE_NIGHT.get(p, 10 ** 9):
            return p
    return phase


def _event(ins: dict, country: dict, op: dict, betrayal: bool) -> dict:
    """رویداد استاندارد برای لایه‌ی خبر."""
    ev = {"kind": op.get("kind", "op"), "seed": ins["seed_base"],
          "country_name": country.get("name"), "country_flag": country.get("flag"),
          "phase": ins.get("phase"), "objective": op.get("objective"),
          "repelled": bool(op.get("repelled"))}
    return ev
