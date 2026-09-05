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
    # لحظه‌ی قطعی وسط بازه (۱۰:۰۰ تهران) — لحظه‌ی واقعی نزدیک مرز ۶ساعته flaky است
    moment = datetime.datetime(2026, 9, 5, 6, 30, tzinfo=datetime.timezone.utc)

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


def test_digest_only_includes_domestic_crises():
    """روزنامه فقط رویدادهای تشدید بحران‌های داخلی را پوشش می‌دهد."""
    items = [
        {"crisis_id": 1, "country": {"name": "یمن"},
         "crisis": {"crisis_key": "epidemic", "severity": "severe"},
         "event": "escalated", "flag": "x", "title": "t", "body": "b"},
        {"crisis_id": 2, "country": {"name": "اتریش"},
         "crisis": {"crisis_key": "epidemic", "severity": "medium"},
         "event": "escalated", "flag": "x", "title": "t", "body": "b"},
    ]
    title, body = ia.build_news_digest(items)
    assert title == "روزنامه بحران‌های جهان"
    assert "⚔️ میدان جنگ" not in body
    assert "یمن" in body
    assert "اتریش" in body


def test_empty_items_returns_none_digest():
    """بدون رویدادهای بحرانی داخلی، روزنامه‌ای تولید نمی‌شود."""
    res = ia.build_news_digest([])
    assert res is None


def test_publisher_only_posts_crisis_items():
    """پابلیشر فقط وقتی اخبار بحران وجود دارد اقدام به انتشار می‌کند."""
    import inspect
    import main as main_module
    source = inspect.getsource(main_module._publish_crisis_news)
    assert "collect_new_war_summary" not in source
    assert "crisis_casualties_summary" not in source

