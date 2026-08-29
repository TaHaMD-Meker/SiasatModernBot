# -*- coding: utf-8 -*-
"""چرخه‌ی ۶ ساعته‌ی شدت بحران و محو شدن بحران خفیف.

خواسته‌ی کارفرما:
۱. تغییر سطح بحران (بالا/پایین) و خبرش با همان نوبت‌های ۶ ساعته‌ی درآمد بیاید،
   نه یک‌بار در شب — و فقط برای بحران‌هایی که **کل سطحشان** عوض شده، نه درصد مهار.
۲. بحرانی که یک شبانه‌روز روی «خفیف» بماند، خودش از بین برود — به‌جز اپیدمی که
   در خفیف محو نمی‌شود، فقط از مهار ۸۰٪ پایین می‌آید و تنها با مهار ۹۰٪
   (که بدون واکسن ممکن نیست) ریشه‌کن می‌شود.
"""

import datetime

import config
import database as db
import internal_affairs as ia


def _fresh(monkeypatch, tmp_path, name="slot.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()
    ia.set_enabled(True)
    ia.set_random_crises(False)


def _new_crisis(cid, key, severity):
    ok, _msg, crisis = ia.create_crisis(cid, key, severity=severity, origin="admin", force=True)
    assert ok
    return crisis


def _country(player_id=61_001, key="slotland"):
    cid = db.create_country(player_id, "کشور آزمون", "🏳️", country_key=key)
    db.update_country_field(cid, "approval_rating", 70)
    return cid


def _set(crisis_id, **fields):
    conn = db.get_connection()
    try:
        with conn:
            for key, value in fields.items():
                conn.execute(f"UPDATE country_crises SET {key} = ? WHERE id = ?", (value, crisis_id))
    finally:
        conn.close()


def _slots(base, count):
    """چند لحظه‌ی متوالی که هر کدام در یک بازه‌ی ۶ ساعته‌ی متفاوت هستند."""
    return [base + datetime.timedelta(hours=6 * i) for i in range(count)]


# ─────────────────────────────────────────────────────────────────────────────
# گرید ۶ ساعته
# ─────────────────────────────────────────────────────────────────────────────

def test_slot_key_matches_the_income_grid():
    base = datetime.datetime(2026, 8, 28, 0, 0, tzinfo=datetime.timezone.utc)
    keys = [ia.slot_key(base + datetime.timedelta(hours=h)) for h in range(0, 24, 6)]
    assert len(set(keys)) == 4, "چهار نوبت در شبانه‌روز باید چهار شناسه‌ی متفاوت بدهد"
    # دو لحظه در یک بازه، یک شناسه
    assert ia.slot_key(base) == ia.slot_key(base + datetime.timedelta(hours=1))


def test_a_crisis_is_touched_once_per_slot(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "slot_once.db")
    cid = _country()
    _new_crisis(cid, "epidemic", "light")
    moment = ia._now()

    first = ia.run_crisis_slot_cycle(db.get_country_by_id(cid), moment)
    again = ia.run_crisis_slot_cycle(db.get_country_by_id(cid), moment + datetime.timedelta(minutes=20))
    assert again == [], "اجرای دوباره در همان بازه نباید چیزی را تکان بدهد"
    assert isinstance(first, list)


# ─────────────────────────────────────────────────────────────────────────────
# تخفیف و تشدید
# ─────────────────────────────────────────────────────────────────────────────

def test_good_mitigation_steps_the_level_down_in_the_next_slot(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "slot_down.db")
    cid = _country()
    crisis = _new_crisis(cid, "flood", "severe")
    _set(crisis["id"], mitigation=ia.DEESCALATION_MITIGATION_THRESHOLD + 0.05, stage="impact")

    events = ia.run_crisis_slot_cycle(db.get_country_by_id(cid), ia._now())
    assert [e["event"] for e in events] == ["deescalated"]
    assert ia.get_crisis(crisis["id"])["severity"] == "medium"


def test_mitigation_alone_makes_no_news(monkeypatch, tmp_path):
    """درصد مهار بالا برود ولی سطح عوض نشود → هیچ خبری ساخته نشود."""
    _fresh(monkeypatch, tmp_path, "slot_quiet.db")
    cid = _country()
    crisis = _new_crisis(cid, "epidemic", "light")
    _set(crisis["id"], mitigation=0.55, stage="impact")  # بالای آستانه‌ی تخفیف، ولی سطح از خفیف پایین‌تر نمی‌رود

    events = ia.run_crisis_slot_cycle(db.get_country_by_id(cid), ia._now())
    assert [e["event"] for e in events if e["event"] in ("escalated", "deescalated")] == []


def test_neglected_crisis_escalates_but_only_once_a_day(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "slot_up.db")
    cid = _country()
    crisis = _new_crisis(cid, "epidemic", "light")
    _set(crisis["id"], mitigation=0.0, stage="impact")

    # ۰۴:۰۰ UTC یعنی ۰۷:۳۰ تهران؛ سه نوبت بعدی در همان روز تهران می‌مانند
    base = ia._now().replace(hour=4, minute=0, second=0, microsecond=0)
    first, second, third = _slots(base, 3)

    e1 = ia.run_crisis_slot_cycle(db.get_country_by_id(cid), first)
    assert [e["event"] for e in e1] == ["escalated"]
    assert ia.get_crisis(crisis["id"])["severity"] == "medium"

    e2 = ia.run_crisis_slot_cycle(db.get_country_by_id(cid), second)
    e3 = ia.run_crisis_slot_cycle(db.get_country_by_id(cid), third)
    assert e2 == [] and e3 == [], "تشدید نباید در همان روز تکرار شود"
    assert ia.get_crisis(crisis["id"])["severity"] == "medium"


def test_escalation_resumes_the_next_day(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "slot_nextday.db")
    cid = _country()
    crisis = _new_crisis(cid, "epidemic", "light")
    _set(crisis["id"], mitigation=0.0, stage="impact")

    base = ia._now().replace(hour=4, minute=0, second=0, microsecond=0)
    ia.run_crisis_slot_cycle(db.get_country_by_id(cid), base)
    tomorrow = base + datetime.timedelta(days=1)
    events = ia.run_crisis_slot_cycle(db.get_country_by_id(cid), tomorrow)
    assert [e["event"] for e in events] == ["escalated"]
    assert ia.get_crisis(crisis["id"])["severity"] == "severe"


def test_only_changed_crises_appear_in_the_batch(monkeypatch, tmp_path):
    """سه بحران، فقط یکی سطحش عوض می‌شود؛ خروجی باید فقط همان یکی باشد."""
    _fresh(monkeypatch, tmp_path, "slot_subset.db")
    cid = _country()
    moving = _new_crisis(cid, "flood", "severe")
    calm_a = _new_crisis(cid, "earthquake", "light")
    calm_b = _new_crisis(cid, "drought", "light")

    _set(moving["id"], mitigation=0.60, stage="impact")
    for other in (calm_a, calm_b):
        _set(other["id"], mitigation=0.30, stage="impact", light_since=ia._iso())

    events = ia.run_crisis_slot_cycle(db.get_country_by_id(cid), ia._now())
    changed = [e for e in events if e["event"] in ("escalated", "deescalated")]
    assert len(changed) == 1
    assert changed[0]["crisis"]["id"] == moving["id"]


# ─────────────────────────────────────────────────────────────────────────────
# محو شدن بحران خفیف
# ─────────────────────────────────────────────────────────────────────────────

def test_a_light_crisis_fades_after_one_day(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "slot_fade.db")
    cid = _country()
    crisis = _new_crisis(cid, "flood", "light")
    # مهار متوسط: نه آن‌قدر که تشدید شود، نه آن‌قدر که مهار کامل حساب شود
    _set(crisis["id"], mitigation=0.30, stage="impact",
         light_since=ia._iso(ia._now() - datetime.timedelta(hours=25)))

    events = ia.run_crisis_slot_cycle(db.get_country_by_id(cid), ia._now())
    assert [e["event"] for e in events] == ["faded"]
    assert ia.get_crisis(crisis["id"])["stage"] == "ended"
    assert ia.get_crisis(crisis["id"])["outcome"] == "faded"


def test_a_light_crisis_survives_the_first_hours(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "slot_nofade.db")
    cid = _country()
    crisis = _new_crisis(cid, "flood", "light")
    _set(crisis["id"], mitigation=0.30, stage="impact")

    base = ia._now()
    ia.run_crisis_slot_cycle(db.get_country_by_id(cid), base)          # ساعت شروع خفیف ثبت می‌شود
    events = ia.run_crisis_slot_cycle(db.get_country_by_id(cid), base + datetime.timedelta(hours=6))
    assert [e["event"] for e in events] == []
    assert ia.get_crisis(crisis["id"])["stage"] != "ended"


def test_stepping_down_to_light_starts_the_fade_clock(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "slot_clock.db")
    cid = _country()
    crisis = _new_crisis(cid, "flood", "medium")
    _set(crisis["id"], mitigation=0.60, stage="impact")

    ia.run_crisis_slot_cycle(db.get_country_by_id(cid), ia._now())
    fresh = ia.get_crisis(crisis["id"])
    assert fresh["severity"] == "light"
    assert fresh["light_since"], "ساعت خفیف‌ماندن ثبت نشد"


def test_escalating_clears_the_fade_clock(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "slot_clear.db")
    cid = _country()
    crisis = _new_crisis(cid, "epidemic", "light")
    _set(crisis["id"], mitigation=0.0, stage="impact", light_since=ia._iso())

    ia.run_crisis_slot_cycle(db.get_country_by_id(cid), ia._now())
    fresh = ia.get_crisis(crisis["id"])
    assert fresh["severity"] == "medium"
    assert not fresh["light_since"], "با تشدید، ساعت خفیف باید پاک شود"


def test_fade_produces_a_news_item(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "slot_fadenews.db")
    cid = _country()
    crisis = _new_crisis(cid, "flood", "light")
    _set(crisis["id"], mitigation=0.30, stage="impact",
         light_since=ia._iso(ia._now() - datetime.timedelta(hours=25)))

    country = db.get_country_by_id(cid)
    events = ia.run_crisis_slot_cycle(country, ia._now())
    news = ia.collect_slot_news(country, events)
    assert news and news[0]["event"] == "faded"
    assert "فروکش" in news[0]["body"] or "پایان" in news[0]["title"]
    assert "faded" in ia.SEVERITY_EVENTS, "در حالت پیش‌فرض کانال هم باید منتشر شود"


# ─────────────────────────────────────────────────────────────────────────────
# چرخه‌ی روزانه دیگر سطح را تکان نمی‌دهد
# ─────────────────────────────────────────────────────────────────────────────

def test_daily_cycle_no_longer_changes_severity(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "slot_daily.db")
    cid = _country()
    crisis = _new_crisis(cid, "epidemic", "light")
    _set(crisis["id"], mitigation=0.0, stage="impact")

    ia.run_daily_cycle(db.get_country_by_id(cid), None)
    assert ia.get_crisis(crisis["id"])["severity"] == "light", "تشدید باید فقط کار چرخه‌ی ۶ ساعته باشد"


def test_containment_still_ends_a_crisis_daily(monkeypatch, tmp_path):
    """مهار کامل دو روزه برای بحران‌های عادی دست‌نخورده باقی مانده است."""
    _fresh(monkeypatch, tmp_path, "slot_contain.db")
    cid = _country()
    crisis = _new_crisis(cid, "flood", "medium")
    _set(crisis["id"], mitigation=ia.CONTAINMENT_THRESHOLD + 0.05, stage="impact")

    base = ia._now()
    for day in range(ia.CONTAINMENT_DAYS_TO_RESOLVE):
        ia.run_daily_cycle(db.get_country_by_id(cid), None, now_dt=base + datetime.timedelta(days=day))
    assert ia.get_crisis(crisis["id"])["stage"] == "ended"


def test_only_one_level_step_per_day_even_across_four_slots(monkeypatch, tmp_path):
    """چهار نوبت در روز یعنی «زودتر دیده می‌شود»، نه «چهار برابر سریع‌تر»."""
    _fresh(monkeypatch, tmp_path, "slot_pace.db")
    cid = _country()
    crisis = _new_crisis(cid, "flood", "severe")
    _set(crisis["id"], mitigation=0.70, stage="impact")

    base = ia._now().replace(hour=4, minute=0, second=0, microsecond=0)  # ۰۷:۳۰ تهران
    changes = []
    for index in range(3):  # ۰۷:۳۰، ۱۳:۳۰ و ۱۹:۳۰ تهران — یک روز تقویمی
        instant = base + datetime.timedelta(hours=6 * index)
        assert ia._iran_date(instant) == ia._iran_date(base)
        changes += ia.run_crisis_slot_cycle(db.get_country_by_id(cid), instant)
    assert len([c for c in changes if c["event"] == "deescalated"]) == 1
    assert ia.get_crisis(crisis["id"])["severity"] == "medium"

    # روز بعد، یک پله‌ی دیگر
    tomorrow = base + datetime.timedelta(days=1)
    again = ia.run_crisis_slot_cycle(db.get_country_by_id(cid), tomorrow)
    assert [e["event"] for e in again] == ["deescalated"]
    assert ia.get_crisis(crisis["id"])["severity"] == "light"


def test_the_step_lands_in_the_slot_right_after_the_player_acts(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "slot_timing.db")
    cid = _country()
    crisis = _new_crisis(cid, "flood", "severe")
    base = datetime.datetime(2026, 8, 28, 4, 0, tzinfo=datetime.timezone.utc)

    quiet = ia.run_crisis_slot_cycle(db.get_country_by_id(cid), base)
    assert [e["event"] for e in quiet if e["event"] == "deescalated"] == []

    _set(crisis["id"], mitigation=0.70)  # بازیکن وسط روز اقدام می‌کند
    later = ia.run_crisis_slot_cycle(db.get_country_by_id(cid), base + datetime.timedelta(hours=6))
    assert [e["event"] for e in later] == ["deescalated"], "نتیجه باید همان نوبت بعدی دیده شود"


# ─────────────────────────────────────────────────────────────────────────────
# قواعد ویژه‌ی اپیدمی
# ─────────────────────────────────────────────────────────────────────────────

def test_an_epidemic_only_steps_down_above_eighty_percent(monkeypatch, tmp_path):
    """اپیدمی مثل بقیه از ۵۰٪ پایین نمی‌آید؛ فقط از مهار ۸۰٪ به پایین می‌رود."""
    _fresh(monkeypatch, tmp_path, "epid_down.db")
    cid = _country()
    crisis = _new_crisis(cid, "epidemic", "severe")
    _set(crisis["id"], mitigation=0.60, stage="impact")  # بالای آستانه‌ی عادی، زیر آستانه‌ی اپیدمی

    moment = ia._now()
    events = ia.run_crisis_slot_cycle(db.get_country_by_id(cid), moment)
    assert [e["event"] for e in events] == [], "۶۰٪ برای اپیدمی کافی نیست"
    assert ia.get_crisis(crisis["id"])["severity"] == "severe"

    _set(crisis["id"], mitigation=ia.EPIDEMIC_DEESCALATION_MITIGATION + 0.02)
    later = ia.run_crisis_slot_cycle(db.get_country_by_id(cid), moment + datetime.timedelta(hours=6))
    assert [e["event"] for e in later] == ["deescalated"]
    assert ia.get_crisis(crisis["id"])["severity"] == "medium"


def test_an_epidemic_never_fades_while_light(monkeypatch, tmp_path):
    """اپیدمی در خفیف محو نمی‌شود؛ یک شبانه‌روز خفیف ماندن پرونده‌اش را نمی‌بندد."""
    _fresh(monkeypatch, tmp_path, "epid_nofade.db")
    cid = _country()
    crisis = _new_crisis(cid, "epidemic", "light")
    _set(crisis["id"], mitigation=0.30, stage="impact",
         light_since=ia._iso(ia._now() - datetime.timedelta(hours=30)))

    events = ia.run_crisis_slot_cycle(db.get_country_by_id(cid), ia._now())
    assert [e["event"] for e in events] == []
    fresh = ia.get_crisis(crisis["id"])
    assert fresh["stage"] != "ended", "اپیدمی نباید خودبه‌خود تمام شود"


def test_an_epidemic_ends_only_above_ninety_percent(monkeypatch, tmp_path):
    """۸۵٪ مهار برای پایان اپیدمی کافی نیست؛ فقط مهار بالای ۹۰٪ (با واکسن) آن را ریشه‌کن می‌کند."""
    _fresh(monkeypatch, tmp_path, "epid_90.db")
    cid = _country()
    crisis = _new_crisis(cid, "epidemic", "medium")
    _set(crisis["id"], mitigation=0.85, stage="impact")

    base = ia._now()
    for day in range(ia.CONTAINMENT_DAYS_TO_RESOLVE):
        ia.run_daily_cycle(db.get_country_by_id(cid), None, now_dt=base + datetime.timedelta(days=day))
    assert ia.get_crisis(crisis["id"])["stage"] != "ended", "۸۵٪ یعنی بدون واکسن؛ نباید تمام شود"

    _set(crisis["id"], mitigation=ia.EPIDEMIC_ERADICATION_THRESHOLD + 0.02)
    start = ia._now() + datetime.timedelta(days=3)
    for day in range(ia.CONTAINMENT_DAYS_TO_RESOLVE):
        ia.run_daily_cycle(db.get_country_by_id(cid), None, now_dt=start + datetime.timedelta(days=day))
    final = ia.get_crisis(crisis["id"])
    assert final["stage"] == "ended"
    assert final["outcome"] == "contained"


def test_epidemic_contained_news_says_eradicated(monkeypatch, tmp_path):
    """خبر پایان اپیدمی از واژه‌ی «ریشه‌کن» استفاده می‌کند تا با بقیه فرق داشته باشد."""
    _fresh(monkeypatch, tmp_path, "epid_news.db")
    cid = _country()
    _ok, _m, crisis = ia.create_crisis(cid, "epidemic", severity="medium", admin_id=1, force=True)
    ia.end_crisis(crisis["id"], outcome="contained")
    title, body = ia.build_news(db.get_country_by_id(cid), ia.get_crisis(crisis["id"]), "contained")
    assert "ریشه‌کن" in title or "ریشه‌کن" in body

    _ok, _m, flood = ia.create_crisis(cid, "flood", severity="medium", admin_id=1, force=True)
    ia.end_crisis(flood["id"], outcome="contained")
    ftitle, fbody = ia.build_news(db.get_country_by_id(cid), ia.get_crisis(flood["id"]), "contained")
    assert "ریشه‌کن" not in ftitle and "ریشه‌کن" not in fbody


# ─────────────────────────────────────────────────────────────────────────────
# گزارش روزنامه‌ای بحران‌ها
# ─────────────────────────────────────────────────────────────────────────────

def test_jalali_date_line_known_values():
    line = ia._jalali_date_line(datetime.datetime(2026, 8, 28, 12, 0, tzinfo=datetime.timezone.utc))
    assert "جمعه" in line and "شهریور" in line and "۱۴۰۵" in line


def _norm(s: str) -> str:
    """نیم‌فاصله را حذف می‌کند تا مقایسه‌ی متون فارسی ساده شود."""
    return s.replace("\u200c", "")


def test_digest_has_newspaper_layout():
    items = [
        {"crisis_id": 1, "country": {"flag": "🇦🇹", "name": "اتریش"},
         "crisis": {"crisis_key": "epidemic", "severity": "severe"},
         "event": "escalated", "flag": "x", "title": "t", "body": "b"},
        {"crisis_id": 2, "country": {"flag": "🇨🇦", "name": "کانادا"},
         "crisis": {"crisis_key": "epidemic", "severity": "medium"},
         "event": "deescalated", "flag": "x", "title": "t", "body": "b"},
        {"crisis_id": 3, "country": {"flag": "🇫🇮", "name": "فنلاند"},
         "crisis": {"crisis_key": "epidemic", "severity": "light"},
         "event": "contained", "flag": "x", "title": "t", "body": "b"},
        {"crisis_id": 4, "country": {"flag": "🇸🇪", "name": "سوئد"},
         "crisis": {"crisis_key": "flood", "severity": "light"},
         "event": "contained", "flag": "x", "title": "t", "body": "b"},
    ]
    title, body = ia.build_news_digest(items)
    assert "روزنامه" in title and "بحران" in title
    assert "🗓" in body and "━━━" in body
    # هر نوع بحران تیتر خودش را دارد و قاطی نشده
    nbody = _norm(body)
    assert "\n🦠 اپیدمی\n" in nbody
    assert "\n🌊 سیل\n" in nbody
    # لید خبر با شمارنده
    assert "تشدید شد" in nbody
    # متن روان، نه جدول
    assert "▫️" not in nbody
    assert "—" not in nbody
    assert "رسید" in nbody
    assert "اتریش" in nbody
    # ریشه‌کنی اپیدمی در برابر پایان سیل
    assert "ریشهکن" in nbody
    assert "پایان یافت" in nbody
    # مقاله‌ی اپیدمی، تشدید و مهار و پایانِ همان نوع را یک‌جا دارد
    epidemic_article = _norm(body.split("\n🦠 اپیدمی\n")[1].split("\n🌊 سیل\n")[0])
    assert "به «شدید» رسید" in epidemic_article
    assert "کاهش یافت" in epidemic_article
    assert "ریشهکنی کامل" in epidemic_article


def test_war_summary_dedupes_crisis_countries():
    """کشوری که تلفات انسانی دارد فقط در «میدان جنگ» بیاید، نه در بخش بحران."""
    items = [
        {"crisis_id": 1, "country": {"name": "یمن"},
         "crisis": {"crisis_key": "epidemic", "severity": "severe"},
         "event": "escalated", "flag": "x", "title": "t", "body": "b"},
        {"crisis_id": 2, "country": {"name": "اتریش"},
         "crisis": {"crisis_key": "epidemic", "severity": "medium"},
         "event": "escalated", "flag": "x", "title": "t", "body": "b"},
    ]
    war = [{"name": "یمن", "flag": "🇾🇪", "mil_kia": 35, "wounded": 120, "civ_kia": 55,
            "ops": ["الله مدینه"], "equip_items": 0}]
    title, body = ia.build_news_digest(items, war)
    assert "⚔️ میدان جنگ" in body
    war_part, crisis_part = body.split("⚔️ میدان جنگ")[1].split("\n🦠 اپیدمی\n", 1)
    assert "یمن" in war_part  # یمن فقط در میدان جنگ
    assert "یمن" not in crisis_part
    assert "اتریش" in crisis_part
    assert "در اتریش به «متوسط» رسید" in crisis_part


def test_war_only_digest():
    """بدون رویداد بحرانی، تلفاتِ جدید همان روز «گزارش میدان جنگ» می‌شود."""
    war = [{"name": "عربستان", "flag": "🇸🇦", "mil_kia": 240, "wounded": 720, "civ_kia": 90,
            "ops": ["وعده صادق"], "equip_items": 10}]
    title, body = ia.build_news_digest([], war)
    assert title == "گزارش میدان جنگ"
    assert "میدان جنگ" in body
    nbody = _norm(body)
    assert "مجموع کشتهشدگان ۳۳۰ نفر و مجروحان ۷۲۰ نفر برآورد شده است" in nbody
    assert "عربستان در عملیات «وعده صادق» هدف درگیری قرار گرفت" in nbody
    assert "۲۴۰ نظامی و ۹۰ غیرنظامی کشته شدند" in nbody
    assert "۷۲۰ نفر مجروح شدند" in nbody


def test_war_section_is_per_country_paragraphs():
    """هر کشور پاراگراف مستقل خودش را دارد — پشت‌سرهم قاطی نمی‌شود."""
    war = [
        {"name": "افغانستان", "flag": "🇦🇫", "mil_kia": 185, "wounded": 520, "civ_kia": 45,
         "ops": ["تحدیدزدایی"], "equip_items": 0},
        {"name": "چین", "flag": "🇨🇳", "mil_kia": 34, "wounded": 115, "civ_kia": 28,
         "ops": ["دیوار تاریکی اژدها"], "equip_items": 0},
        {"name": "انصارالله یمن", "flag": "🇾🇪", "mil_kia": 35, "wounded": 120, "civ_kia": 55,
         "ops": ["آرامکو", "الله مدینه"], "equip_items": 0},
    ]
    title, body = ia.build_news_digest([], war)
    # لید با مجموع تلفات
    nbody = _norm(body)
    assert "درگیریهای امروز در ۳ کشور تلفات انسانی بر جای گذاشت" in nbody
    assert "مجموع کشتهشدگان ۳۸۲ نفر و مجروحان ۷۵۵ نفر برآورد شده است" in nbody
    # هر کشور پاراگراف خودش — افغانستان (سنگین‌ترین) اول
    assert nbody.index("🇦🇫 افغانستان") < nbody.index("🇨🇳 چین")
    assert "🇦🇫 افغانستان در عملیات «تحدیدزدایی» هدف درگیری قرار گرفت" in nbody
    assert "🇨🇳 چین در عملیات «دیوار تاریکی اژدها» هدف درگیری قرار گرفت" in nbody
    assert "🇾🇪 انصارالله یمن در عملیات «آرامکو» و «الله مدینه» هدف درگیری قرار گرفت" in nbody
    # بین پاراگراف‌ها فاصله‌ی واقعی هست
    assert "\n\n" in body


def test_war_paragraph_describes_the_attack():
    """میدان جنگ باید بگوید چه جور حمله‌ای بوده و چه چیزی آسیب دیده."""
    war = [
        {"name": "افغانستان", "flag": "🇦🇫", "mil_kia": 185, "wounded": 520, "civ_kia": 45,
         "ops": ["تحدیدزدایی"], "equip_items": 29,
         "subcats": ["پدافند هوایی", "جنگنده‌ها و هوانوردی", "نیروی زمینی"],
         "strategic": ["شبکه برق", "ذخایر سوخت"], "buildings": 2},
        {"name": "ونزوئلا", "flag": "🇻🇪", "mil_kia": 10, "wounded": 40, "civ_kia": 0,
         "ops": [], "equip_items": 0,
         "subcats": ["نیروی دریایی"], "strategic": [], "buildings": 0},
    ]
    title, body = ia.build_news_digest([], war)
    nbody = _norm(body)
    assert "افغانستان در عملیات «تحدیدزدایی» هدف حملات هوایی و موشکی قرار گرفت" in nbody
    assert "پایگاههای هوایی، شبکه پدافند هوایی، یگانهای زمینی، شبکه برق، ذخایر سوخت و تأسیسات صنعتی آسیب دید" in nbody
    assert "ونزوئلا هدف عملیات دریایی قرار گرفت" in nbody
    assert "نیروی دریایی آسیب دید" in nbody


# ─────────────────────────────────────────────────────────────────────────────
# اتصال روزنامه به گزارش تلفاتِ همان روز
# ─────────────────────────────────────────────────────────────────────────────

def _loss_item(special, qty):
    return {"key": f"__{special}__", "special": special, "qty": qty, "name": special, "unit": "نفر"}


def test_collect_new_war_summary_reads_todays_losses(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "war_sum.db")
    yemen = db.create_country(70_001, "انصارالله یمن", "🇾🇪", country_key="yemen")
    saudi = db.create_country(70_002, "عربستان", "🇸🇦", country_key="saudi")
    ok, rid1, err = db.create_loss_report(
        yemen, [_loss_item("mil_kia", 35), _loss_item("wounded", 120), _loss_item("civ_kia", 55)],
        operation_name="الله مدینه",
    )
    assert ok, err
    ok, rid2, err = db.create_loss_report(
        saudi, [_loss_item("mil_kia", 0), _loss_item("wounded", 0), _loss_item("civ_kia", 0),
                {"key": "f15", "special": None, "qty": 2, "name": "F-15", "unit": "فروند"}],
        operation_name="وعده صادق",
    )
    assert ok, err

    summaries, marker = ia.collect_new_war_summary()
    assert marker >= rid2
    names = {s["name"] for s in summaries}
    assert names == {"انصارالله یمن"}, "کشورِ بدون تلفات انسانی نباید در میدان جنگ بیاید"
    y = [s for s in summaries if s["name"] == "انصارالله یمن"][0]
    assert y["mil_kia"] == 35 and y["wounded"] == 120 and y["civ_kia"] == 55
    assert "الله مدینه" in y["ops"]

    ia.mark_war_summary_published(marker)
    again, marker2 = ia.collect_new_war_summary()
    assert again == [], "بعد از انتشار، نباید دوباره همان گزارش بیاید"


def test_war_summary_only_uses_todays_reports(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "war_old.db")
    cid = db.create_country(70_003, "کشور آزمون", "🏳️", country_key="w1")
    db.create_loss_report(cid, [_loss_item("mil_kia", 5)], operation_name="قدیمی")

    # گزارشِ دیروز را شبیه‌سازی کن
    import datetime as _dt
    conn = db.get_connection()
    with conn:
        yesterday = (_dt.datetime.now(_dt.timezone.utc) - _dt.timedelta(days=1)).isoformat()
        conn.execute("UPDATE loss_reports SET created_at = ? WHERE id = 1", (yesterday,))
    conn.close()

    summaries, marker = ia.collect_new_war_summary()
    assert summaries == [], "گزارش دیروز نباید وارد روزنامه‌ی امروز شود"
    # ولی مارکر جلو می‌رود تا دفعه‌ی بعد دوباره خوانده نشود
    again, marker2 = ia.collect_new_war_summary()
    assert marker == marker2


# ─────────────────────────────────────────────────────────────────────────────
# تلفات بحران‌ها در روزنامه
# ─────────────────────────────────────────────────────────────────────────────

def _crisis_with_impact(cid, crisis_key, severity="severe"):
    ok, _msg, crisis = ia.create_crisis(cid, crisis_key, severity=severity, origin="admin", force=True)
    assert ok
    ia.force_impact(crisis["id"], admin_id=1)
    return crisis


def test_crisis_casualties_summary_aggregates_by_type(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "cas_sum.db")
    c1 = _country(71_001, key="cas_a")
    c2 = _country(71_002, key="cas_b")
    c3 = _country(71_003, key="cas_c")
    db.update_country_field(c1, "population", 50_000_000)
    db.update_country_field(c2, "population", 40_000_000)
    db.update_country_field(c3, "population", 60_000_000)
    _crisis_with_impact(c1, "epidemic", "severe")
    _crisis_with_impact(c2, "epidemic", "severe")
    _crisis_with_impact(c3, "flood", "medium")

    cas = ia.crisis_casualties_summary()
    assert cas["by_type"]["epidemic"]["count"] == 2
    assert cas["by_type"]["epidemic"]["casualties"] > 0
    assert cas["by_type"]["flood"]["count"] == 1
    assert cas["by_type"]["flood"]["casualties"] > 0
    assert cas["total"] > 0
    # مجموع تلفات اپیدمی باید مجموع دو کشور باشد
    epi = cas["by_type"]["epidemic"]["casualties"]
    single_epidemic = None
    for cid in (c1, c2):
        crisis = [c for c in ia.get_active_crises(cid) if c["crisis_key"] == "epidemic"][0]
        dmg = ia._json_load(crisis.get("damage_json") or "{}", {})
        single_epidemic = (single_epidemic or 0) + int(dmg.get("population") or 0)
    assert epi == single_epidemic
    # جزئیات کشوری هم موجود است
    assert len(cas["by_country"]) == 3


def test_digest_includes_casualties_section(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "cas_digest.db")
    c1 = _country(71_011, key="cas_d")
    db.update_country_field(c1, "population", 50_000_000)
    _crisis_with_impact(c1, "epidemic", "severe")
    cas = ia.crisis_casualties_summary()

    title, body = ia.build_news_digest([], [], cas)
    assert title == "گزارش تلفات بحران‌ها"
    assert "مجموع تلفات" in body
    assert "اپیدمی" in body or "سیل" in body


def test_casualties_section_shows_totals_for_multi_country_crises(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "cas_multi.db")
    c1 = _country(71_021, key="cas_e")
    c2 = _country(71_022, key="cas_f")
    db.update_country_field(c1, "population", 50_000_000)
    db.update_country_field(c2, "population", 40_000_000)
    _crisis_with_impact(c1, "epidemic", "severe")
    _crisis_with_impact(c2, "epidemic", "severe")

    cas = ia.crisis_casualties_summary()
    title, body = ia.build_news_digest([], [], cas)
    # وقتی در چند کشور فعال است، مجموع کل و کشورها تحلیل می‌شود
    assert "مجموع تلفات" in body
    assert "بیشترین سهم" in body


def test_warning_stage_crises_have_no_casualties(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "cas_warn.db")
    c1 = _country(71_031, key="cas_g")
    db.update_country_field(c1, "population", 50_000_000)
    _ok, _m, crisis = ia.create_crisis(c1, "epidemic", severity="severe", origin="admin", force=True)
    # در مرحله‌ی هشدار بماند (impact نزنیم)
    cas = ia.crisis_casualties_summary()
    assert cas["total"] == 0 and cas["by_type"] == {}, "بحران هشدار که خسارت نداده نباید تلفات داشته باشد"


def test_casualty_analysis_mentions_worst_country_and_heaviest_crisis(monkeypatch, tmp_path):
    """جمع‌بندی باید بیشترین تلفات را به‌صورت تحلیلی بگوید (کشور + نوع بحران)."""
    _fresh(monkeypatch, tmp_path, "cas_analysis.db")
    c1 = _country(71_041, key="ca1")
    c2 = _country(71_042, key="ca2")
    db.update_country_field(c1, "population", 60_000_000)  # بزرگ‌تر → تلفات بیشتر
    db.update_country_field(c2, "population", 20_000_000)
    _crisis_with_impact(c1, "flood", "severe")
    _crisis_with_impact(c2, "epidemic", "medium")

    cas = ia.crisis_casualties_summary()
    title, body = ia.build_news_digest([], [], cas)
    assert "مجموع تلفات" in body
    assert "بیشترین سهم" in body
    assert "کشورهای آسیب‌دیده به‌ترتیب" in body
    assert "اولین" in body
    # کشوری با جمعیت بیشتر (c1) باید در صدر باشد
    worst = max(cas["by_country"].values(), key=lambda c: c["casualties"])
    assert worst["name"] == "کشور آزمون"


# ─────────────────────────────────────────────────────────────────────────────
# باگ: تلفات نباید کم شود + گزارش نباید هر ۱۵ دقیقه بیاید
# ─────────────────────────────────────────────────────────────────────────────

def test_casualties_never_decrease_after_crisis_ends(monkeypatch, tmp_path):
    """وقتی بحرانی تمام می‌شود، تلفاتش نباید از مجموع کل حذف شود."""
    _fresh(monkeypatch, tmp_path, "cas_no_decrease.db")
    c1 = _country(71_051, key="nd1")
    db.update_country_field(c1, "population", 50_000_000)
    _crisis_with_impact(c1, "epidemic", "severe")

    before = ia.crisis_casualties_summary()
    assert before["total"] > 0

    # بحران را تمام کن
    crisis = ia.get_active_crises(c1)[0]
    ia.end_crisis(crisis["id"], outcome="contained")

    after = ia.crisis_casualties_summary()
    assert after["total"] == before["total"], "تلفات نباید بعد از پایان بحران کم شود"
    # تعداد کشورهای «جاری» کم می‌شود ولی تلفات نمی‌کاهد
    assert after["by_type"]["epidemic"]["count"] == 0
    assert after["by_type"]["epidemic"]["casualties"] == before["by_type"]["epidemic"]["casualties"]


def test_casualties_report_is_throttled_to_six_hours(monkeypatch, tmp_path):
    """گزارش تلفاتِ تنها نباید زودتر از ۶ ساعت دوباره منتشر شود."""
    _fresh(monkeypatch, tmp_path, "cas_throttle.db")
    c1 = _country(71_052, key="th1")
    db.update_country_field(c1, "population", 50_000_000)
    _crisis_with_impact(c1, "epidemic", "severe")

    now = ia._now()
    assert ia.casualties_due(now) is True, "اولین بار باید مجاز باشد"
    ia.mark_casualties_posted(now)

    # ۱ دقیقه بعد → نباید مجاز باشد
    assert ia.casualties_due(now + datetime.timedelta(minutes=1)) is False
    # ۶ ساعت بعد → مجاز
    assert ia.casualties_due(now + datetime.timedelta(hours=6, minutes=1)) is True


def test_publisher_only_posts_casualties_when_due():
    """پابلیشر باید گیت زمانی را برای گزارش تلفاتِ تنها چک کند."""
    import inspect
    import main as main_module
    source = inspect.getsource(main_module._publish_crisis_news)
    assert "casualties_due" in source
    assert "mark_casualties_posted" in source
    assert "not items and not war_summary" in source
