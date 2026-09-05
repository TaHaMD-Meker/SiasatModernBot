# -*- coding: utf-8 -*-
"""⚙️ عملیات‌خودکار جنگ — مغز تحلیل رول‌های حمله و ثبت طرح دفاعی.

مسیر رول حمله: دروازه‌ی تنش → استخراج مهمات از انبار واقعی مهاجم →
شناسایی اهداف → کلاسه‌بندی مقیاس → اجرای خودکار (کسر اتمیک + تلفات
تقابلی + خبر) یا ارجاع به مدیریت (بدون هیچ کسری).

اصل مالک: بات فقط چیزی را اجرا می‌کند که واقعاً فهمیده و واقعاً در
انبار هست؛ ابهام = ارجاع، هرگز حدس و کسر کور.
"""
import json
import re

import config
import database as db
import combat_model as cm
from handlers.losses import match_country_by_name, match_asset_by_name, is_explicit_strategic
from utils import format_money


# ────────────────── منوی قاره‌ای بدون ایموجی + جستجو ──────────────────

def build_plain_continent_selector(prefix: str, extra_rows=None):
    """انتخابگر قاره با برچسب متنی خالص (بدون ایموجی) + دکمه‌ی جستجو.

    extra_rows: ردیف‌های اضافی (مثل دکمه‌ی بازگشت) — tuple داخلیِ
    InlineKeyboardMarkup تغییرناپذیر است؛ باید همین‌جا اضافه شود.
    """
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    buttons = []
    for cont_key, info in config.CONTINENTS.items():
        label = (info.get("short_name") or info.get("name") or cont_key).strip()
        buttons.append([InlineKeyboardButton(label, callback_data=f"{prefix}:cont:{cont_key}")])
    buttons.append([InlineKeyboardButton("جستجوی تایپی کشور", callback_data=f"{prefix}:search")])
    for row in (extra_rows or []):
        buttons.append(list(row))
    text = "قاره‌ی کشور را انتخاب کنید یا از جستجوی تایپی استفاده کنید:"
    return text, InlineKeyboardMarkup(buttons)


# ────────────────── استخراج مهمات از متن رول ──────────────────

_UNIT_WORDS = ("فروند", "واحد", "دسته", "اسکادران", "آتشبار", "دلار", "هزار", "میلیون", "باب", "رایگانه", "ناو", "قبضه")
_NUMBER_RE = re.compile(r"(\d[\d,٬]*)")
_STOP = frozenset({"به", "با", "از", "و", "در", "برای", "علیه", "سمت", "روی", "تا", "که", "هم", "ای", "های", "حمله", "حمله‌ی", "عملیات", "هدف", "اهداف", "زده", "شود", "می", "انجام", "باکثر", "کامل", "کاملترین", "همه‌جانبه", "موج", "شب", "امشب", "فردا"})


_TRANSLIT = {
    "تایفون": "typhoon", "یوروفایتر": "eurofighter", "رافال": "rafale",
    "تورنادو": "tornado", "فانتوم": "phantom", "میراژ": "mirage",
    "میگ": "mig", "سوخو": "su", "هاریه": "harrier", "گرشاپ": "gripen",
    "استورم": "storm", "شادو": "shadow", "اسکالپ": "scalp", "پنجه": "pantsir",
    "پانتسیر": "pantsir", "تاماهاک": "tomahawk", "کالیبر": "kalibr",
    "هایپرسونیک": "hypersonic", "زیرکون": "zircon", "اسکاد": "scud",
    "شهاب": "shahab", "فتاح": "fateh", "شاهد": "shahed", "ابابیل": "ababil",
    "مهاجر": "mohajer", "پاتریوت": "patriot", "بوک": "buk", "پنج-سانت": "pantsir",
}


def _expand_translit(candidate: str) -> str:
    """هم‌سنجی ترانویسی فارسی با نام لاتین انبار («تایفون» ↔ Typhoon)."""
    extra = []
    for fa, en in _TRANSLIT.items():
        if fa in candidate:
            extra.append(en)
    return candidate + (" " + " ".join(extra) if extra else "")


def extract_munitions(text: str, assets: list):
    """جفت «عدد + نام تجهیز» را با انبار واقعی مهاجم تطبیق می‌دهد.

    خروجی: (committed، unmatched_numbers)
    committed: [(asset_key, equipment_name, qty, kind)]
    kind: aircraft | missile | drone — فقط اقلامِ تطبیق‌خورده با انبار.
    """
    from handlers.losses import to_english_digits
    t = to_english_digits(str(text))
    committed, seen = [], set()
    unmatched = 0
    for m in _NUMBER_RE.finditer(t):
        # عدد داخل نام تجهیز (F-16I، Spice-1000، S-300) تعداد نیست — رد کامل
        before_ch = t[m.start() - 1] if m.start() > 0 else " "
        after_ch = t[m.end()] if m.end() < len(t) else " "
        if (before_ch.isalnum() or before_ch == "-") or (after_ch.isalnum() or after_ch == "-"):
            continue
        qty = int(m.group(1).replace(",", "").replace("٬", ""))
        if qty <= 0 or qty > 10000:
            continue
        window = t[m.end(): m.end() + 60].strip()
        # نام کاندید: تا ۵ واژه بعد از عدد، حذف واژه‌های واحد و ایست
        words = []
        for w in window.split():
            w_clean = w.strip("،؛:!?.«»()[]-—ـ")
            if not w_clean:
                continue
            if w_clean.lower() in _UNIT_WORDS:
                continue
            if w_clean in _STOP and words:
                break
            words.append(w_clean)
            if len(words) >= 5:
                break
        best, best_len = None, 0
        for n in range(len(words), 0, -1):
            cand = _expand_translit(" ".join(words[:n]))
            a = match_asset_by_name(cand, assets)
            if a and len(a.get("equipment_name") or "") > best_len:
                best, best_len = a, len(a.get("equipment_name") or "")
        if not best:
            unmatched += 1
            continue
        key = best["equipment_key"]
        if key in seen:
            row = next(x for x in committed if x[0] == key)
            if qty > row[2]:
                committed[committed.index(row)] = (key, best["equipment_name"], qty, row[3])
            continue
        name_all = f"{best.get('equipment_name','')} {best.get('equipment_key','')}"
        if cm.classify_aircraft(name_all) or any(p in cm._norm(name_all) for p in ("جنگنده", "بمب‌افکن", "fighter", "اف-")):
            kind = "aircraft"
        else:
            kind = "missile" if cm.classify_munition(name_all) in ("cruise", "ballistic", "hypersonic", "supersonic_cruise") else "drone" if cm.classify_munition(name_all) in ("drone", "drone_loitering") else "missile"
        committed.append((key, best["equipment_name"], qty, kind))
    return committed, unmatched


def extract_targets(text: str, defender_id: int) -> dict:
    """اهداف راهبردی و ساختمانیِ ذکرشده در متن رول."""
    from handlers.losses import to_english_digits
    t = to_english_digits(str(text))
    strategic = [p for p in _EXPLICIT_STRATEGIC if p in t]
    buildings = []
    for phrase, key in _BUILDING_PHRASES:
        if phrase in t:
            buildings.append(key)
    return {"strategic": strategic, "buildings": buildings}


_EXPLICIT_STRATEGIC = (
    "شبکه برق", "پست انتقال", "زیرساخت برق", "قطع برق", "برق سراسری", "خاموشی سراسری",
    "ذخایر نفت", "ذخیره نفت", "مخازن نفت", "نفت خام", "پالایشگاه",
    "ذخایر غلات", "ذخیره غلات", "انبار غلات", "ذخایر گندم",
    "شمش طلا", "خزانه طلا", "کلاهک هسته", "کیک زرد", "تسهیحات غنی‌سازی", "غنی‌سازی",
)
_WAR_DECLARATION = ("اعلان جنگ", "حمله‌ی تمام‌عیار", "حمله تمام عیار", "جنگ رسمی", "تهاجم تمام‌عیار")
_BUILDING_PHRASES = (("ستاد فرماندهی", "command_center"), ("باند فرودگاه", "airport"), ("فرودگاه", "airport"), ("زرادخانه", "armory"))


def detect_coalition(text: str, attacker_cid: int) -> list:
    """کشورهای دیگرِ نام‌برده در متن (به‌جز مهاجم و هدف) = ائتلاف."""
    others = []
    for c in db.get_all_countries():
        if c["id"] in (attacker_cid,):
            continue
        name = c.get("name") or ""
        if len(name) >= 3 and name in str(text):
            others.append(c)
    return others


def classify_scale(committed, targets: dict, text: str, coalition: list):
    """خروجی: ('auto', None) یا ('escalate', دلایل)."""
    reasons = []
    combat_munitions = sum(q for (k, n, q, kind) in committed if kind in ("missile", "drone"))
    aircraft = sum(q for (k, n, q, kind) in committed if kind == "aircraft")
    if combat_munitions + aircraft > config.AUTO_OP_MAX_MUNITIONS:
        reasons.append(f"مقیاس گسترده (مهمات {combat_munitions + aircraft} ≥ {config.AUTO_OP_MAX_MUNITIONS})")
    if targets.get("strategic"):
        reasons.append("هدف راهبردی: " + "، ".join(targets["strategic"][:2]))
    if any(w in str(text) for w in _WAR_DECLARATION):
        reasons.append("ادعای اعلان جنگ رسمی")
    if coalition:
        reasons.append("ائتلاف چندکشوری: " + "، ".join(c["name"] for c in coalition[:2]))
    return ("escalate", reasons) if reasons else ("auto", None)


def _understand_ratio(text: str, committed, unmatched: int, targets: dict) -> float:
    """نسبت فهم بات از متن — برای تشخیص ابهام."""
    from handlers.losses import to_english_digits
    t = to_english_digits(str(text))
    numbers = len(_NUMBER_RE.findall(t))
    signals = len(committed) + len(targets.get("strategic", [])) + len(targets.get("buildings", []))
    if numbers == 0 and signals > 0:
        return 1.0
    total = numbers + len(_EXPLICIT_STRATEGIC) * 0  # مبنای مقایسه: اعداد متن
    if total == 0:
        return 0.0 if signals == 0 else 1.0
    return max(0.0, min(1.0, (total - unmatched) / total))


# ────────────────── دروازه و پردازش اصلی ──────────────────

_TENSION_GUIDE = (
    "🌡 *تنش را چطور بالا ببرم؟*\n"
    f"• بیانیه تند یا اولتیماتوم ← +{config.TENSION_STATEMENT_DELTA}\n"
    f"• عملیات اطلاعات/سایبری موفق ← +{config.TENSION_INTEL_SUCCESS_DELTA}\n"
    f"• تحریم تجاری ← +{config.TENSION_SANCTION_DELTA}\n"
    f"• حمله‌ی محدود موفق ← +{config.TENSION_AUTO_ATTACK_DELTA}\n"
    f"⚠️ تنش هر روز {config.TENSION_DAILY_DECAY} واحد سرد می‌شود — سریع حرکت کن!"
)


def _as_country(x):
    if isinstance(x, dict):
        return x
    c = db.get_country_by_id(x)
    if not c:
        raise ValueError(f"country {x} not found")
    return c


def process_attack_submission(attacker, target, text: str, bot=None, role_id: int = None) -> dict:
    """مسیر کامل رول حمله — از دروازه تا اجرا/ارجاع/رد. خروجی برای تست و UI."""
    attacker = _as_country(attacker)
    target = _as_country(target)
    att_id, dfn_id = attacker["id"], target["id"]
    if role_id is None:
        role_id = db.create_pending_roleplay(att_id, attacker.get("player_id") or 0, "attack", text)
    tension_now = db.get_tension(att_id, dfn_id)

    # ۰) دروازه‌ی تنش
    if tension_now < config.TENSION_ATTACK_THRESHOLD:
        reason = (
            f"تنش با {target['flag']} {target['name']} فقط {tension_now}/۱۰۰ است — "
            f"حمله نیاز به حداقل {config.TENSION_ATTACK_THRESHOLD} دارد.\n\n{_TENSION_GUIDE}"
        )
        _set_role(role_id, "rejected", reason)
        return {"verdict": "rejected", "reason": reason, "tension": tension_now, "role_id": role_id}

    # ۱) تحلیل متن
    assets = db.get_country_assets(att_id)
    committed, unmatched = extract_munitions(text, assets)
    targets = extract_targets(text, dfn_id)
    coalition = detect_coalition(text, att_id)

    # ۲) ابهام → ارجاع بدون کسر
    if _understand_ratio(text, committed, unmatched, targets) < config.AUTO_OP_MIN_UNDERSTAND_RATIO:
        return _escalate(attacker, target, text, role_id, ["متن رول غیرقابل پردازش خودکار است — اقلام نامفهوم"])

    # ۳) مقیاس → ارجاع بدون کسر
    verdict, reasons = classify_scale(committed, targets, text, coalition)
    if verdict == "escalate":
        return _escalate(attacker, target, text, role_id, reasons)

    # ۴) اجرای خودکار
    return _execute_auto(attacker, target, text, role_id, committed, targets, bot)


def _set_role(role_id, status, note=""):
    if role_id:
        try:
            db.update_roleplay_status(role_id, status)
            db.set_roleplay_status_note(role_id, note or "")
        except Exception:
            pass


def _escalate(attacker, target, text, role_id, reasons):
    _set_role(role_id, "pending")
    return {
        "verdict": "escalated",
        "reasons": reasons,
        "player_msg": (
            f"📤 *طرح عملیاتی شما به ستاد مدیریت ارجاع شد.*\n\n"
            f"علت: {'؛ '.join(reasons)}\n"
            "پس از داوری مدیریت اطلاع‌رسانی می‌شود."
        ),
    }


def _execute_auto(attacker, target, text, role_id, committed, targets, bot=None):
    import combat_model
    att_id, dfn_id = attacker["id"], target["id"]
    op_name = "عملیات محدود"

    # ── مصرف مهاجم: مهمات + هزینه‌ی عملیاتی (اتمیک) ──
    n_items = sum(q for (k, n, q, kind) in committed)
    attacker_items = []
    for (key, name, qty, kind) in committed:
        attacker_items.append({"key": key, "name": name, "qty": qty, "special": None})
    attacker_items.append({"special": "money", "qty": int(config.AUTO_OP_MONEY_PER_ITEM * n_items)})
    attacker_items.append({"special": "oil", "qty": int(config.AUTO_OP_OIL_PER_ITEM * n_items)})
    ok, rid, err = db.create_loss_report(att_id, attacker_items, op_name, "اجرای خودکار")
    if not ok:
        return _escalate(attacker, target, text, role_id, [f"خطا در کسر انبار: {err}"])

    # جنگنده‌های ازدست‌رفته + تلفات مدافع از موتور تقابل
    resolution = combat_model.resolve_strike(
        att_id, dfn_id,
        [(k, n, q, kind) for (k, n, q, kind) in committed],
        plan_active=bool((db.get_defense_plan(dfn_id) or {}).get("active")),
    )

    defender_items = []
    for (key, qty) in resolution["defender_asset_losses"]:
        a = next((x for x in db.get_country_assets(dfn_id) if x["equipment_key"] == key), None)
        if a:
            defender_items.append({"key": key, "name": a["equipment_name"], "qty": qty, "special": None})
    human = resolution["human"]
    if human["mil_kia"]:
        defender_items.append({"special": "mil_kia", "qty": human["mil_kia"]})
    if human["wounded"]:
        defender_items.append({"special": "wounded", "qty": human["wounded"]})
    if human["civilians"]:
        defender_items.append({"special": "civ_kia", "qty": human["civilians"]})
    d_ok, d_rid, d_err = (True, None, None)
    if defender_items:
        d_ok, d_rid, d_err = db.create_loss_report(dfn_id, defender_items, op_name, f"دفاع در برابر {attacker['name']}")

    db.add_tension(att_id, dfn_id, config.TENSION_AUTO_ATTACK_DELTA, f"حمله‌ی محدود {attacker['name']}")

    # ⚔️ جبهه‌ی جنگ فعال: آغاز یا پیشروی
    war_opened = False
    try:
        war, war_opened = db.get_or_create_war(att_id, dfn_id)
        if war_opened:
            db.add_tension(att_id, dfn_id, 20, "آغاز جنگ فعال")
        # دلتای جبهه: نفوذ مؤثر + نسبت تلفات (پیشروی برنده، توقف در setbacks)
        d_loses = sum(q for (_k, q) in resolution["defender_asset_losses"])
        a_air = sum(resolution["attacker_aircraft_losses"].values())
        delta = 3 + int(round(6 * resolution["penetration"]))
        if a_air > 0 and d_loses == 0:
            delta = -4  # موج شکست‌خورده — جبهه عقب می‌نشیند
        db.advance_war_front(war["id"], delta)
    except Exception:
        pass

    _set_role(role_id, "auto_executed")

    units_lost = sum(q for (_, q) in resolution["defender_asset_losses"])
    _notify_players(attacker, target, resolution, units_lost, bot)
    _post_news(attacker, target, resolution, bot)
    if war_opened:
        _announce_war(attacker, target, bot)

    return {
        "verdict": "auto",
        "role_id": role_id,
        "resolution": resolution,
        "human": human,
        "defender_units_lost": units_lost,
        "loss_report_id": rid,
        "defender_report_id": d_rid,
    }


async def _announce_war_async(bot, attacker, target):
    from news_engine import post_breaking_news
    await post_breaking_news(
        bot,
        f"جنگ فعال میان {attacker['name']} و {target['name']} آغاز شد",
        f"با اجرای عملیات محدود {attacker['flag']}، جبهه‌ی جنگ میان دو کشور رسماً گشوده شد. "
        "ناظران نظامی از ادامه‌ی درگیری‌ها در ساعات آینده سخن می‌گویند.")
    for c in (attacker, target):
        if c.get("player_id"):
            try:
                await bot.send_message(
                    chat_id=c["player_id"],
                    text=(f"⚔️ *جنگ فعال با {target['flag']} {target['name']} آغاز شد.*\n"
                          "از این‌به‌بعد: تنش سرد نمی‌شود، فرسودگی روزانه دارید، و با جبهه‌ی ≥۵۰ "
                          "می‌توانید غرامت مطالبه کنید. از بخش «⚔️ جنگ‌های من» مدیریت کنید."),
                    parse_mode="Markdown")
            except Exception:
                pass


def _announce_war(attacker, target, bot):
    """خبر + DM آغاز جنگ فعال — هم داخل loop کار می‌کند هم بیرون آن (تست)."""
    if not bot:
        return
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(_announce_war_async(bot, attacker, target))
    except RuntimeError:
        asyncio.run(_announce_war_async(bot, attacker, target))


def _notify_players(attacker, target, resolution, units_lost, bot):
    if not bot:
        return
    import asyncio
    human = resolution["human"]
    att_msg = (
        f"⚙️ *رول شما وارد چرخه‌ی اجرای خودکار شد.*\n\n"
        f"🎯 هدف: {target['flag']} {target['name']}\n"
        f"🎖 تلفات اعمال‌شده به مدافع: {units_lost} تجهیز، {human['mil_kia']} کشته نظامی\n"
        f"🛬 تلفات هوایی شما: {sum(resolution['attacker_aircraft_losses'].values())} جنگنده\n"
        "📰 خبر فوری منتشر شد و گزارش رسمی به دو طرف ارسال گردید."
    )
    dfn_msg = (
        f"🚨 *{attacker['flag']} {attacker['name']} عملیات محدودی علیه شما اجرا کرد!*\n\n"
        f"🎖 تلفات: {units_lost} تجهیز، {human['mil_kia']} کشته، {human['wounded']} مجروح\n"
        f"🌡 تنش دوطرفه +{config.TENSION_AUTO_ATTACK_DELTA} شد."
    )
    for player_id, msg in ((attacker.get("player_id"), att_msg), (target.get("player_id"), dfn_msg)):
        if not player_id:
            continue
        try:
            asyncio.get_event_loop().create_task(bot.send_message(chat_id=player_id, text=msg, parse_mode="Markdown"))
        except Exception:
            pass


def _post_news(attacker, target, resolution, bot):
    if not bot:
        return
    import asyncio
    from news_engine import post_breaking_news
    title = f"درگیری نظامی محدود میان {attacker['name']} و {target['name']}"
    body = (
        f"منابع نظامی از اجرای یک عملیات محدود {attacker['flag']} علیه اهداف نظامی "
        f"{target['name']} خبر می‌دهند. پدافند {target['name']} واکنش نشان داده؛ "
        "جزئیات و ارقام رسمی منتشر نشده است."
    )
    try:
        asyncio.get_event_loop().create_task(post_breaking_news(bot, title, body))
    except Exception:
        pass


# ────────────────── قلاب‌های تنش ──────────────────

_THREAT_WORDS = ("اولتیماتوم", "تهدید", "پاسخ کوبنده", "انتقام", "خون", "حمله نظامی", "ضربت", "کوبنده", "نابودی", "شکست بی‌قید")


_COUNTRY_ALIASES = {
    "israel": ("صهیونیستی", "صهیونیست", "رژیم اشغالگر", "اسرائیل"),
    "uk": ("بریتانیا", "انگلیس", "لندن"),
    "usa": ("واشنگتن", "آمریکا"),
    "uae": ("امارات", "ابوظبی"),
}


def _find_named_country(text: str, exclude_id: int):
    t = str(text or "")
    for c in db.get_all_countries():
        if c["id"] == exclude_id:
            continue
        name = c.get("name") or ""
        if len(name) >= 3 and name in t:
            return c
        key = (c.get("country_key") or "").lower()
        for frag, aliases in _COUNTRY_ALIASES.items():
            if frag in key and any(al in t for al in aliases):
                return c
    return None


def tension_from_statement(country_id: int, text: str) -> int:
    """بیانیه‌ی تند با نام (یا نام‌ریز) کشور دیگر در متن → +۱۰ تنش دوسویه."""
    t = str(text or "")
    hits = [w for w in _THREAT_WORDS if w in t]
    if not hits:
        return db.get_tension(country_id, country_id)  # بدون تغییر
    target = _find_named_country(t, country_id)
    if not target:
        return 0
    return db.add_tension(country_id, target["id"], config.TENSION_STATEMENT_DELTA, "بیانیه‌ی تند/اولتیماتوم")


def tension_from_sanction(a_id: int, b_id: int) -> int:
    return db.add_tension(a_id, b_id, config.TENSION_SANCTION_DELTA, "تحریم یک‌طرفه")
