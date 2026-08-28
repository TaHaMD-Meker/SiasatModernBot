# -*- coding: utf-8 -*-
"""تست‌های سیستم جمعیت پویا، مالیات، ناآرامی و بحران‌ها."""

import datetime

import config
import database as db
import internal_affairs as ia
from utils import get_main_keyboard


def _fresh_db(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "internal.db"))
    db.init_db()
    ia.set_enabled(True)
    ia.set_random_crises(False)
    return db


def _country(database, player_id=7101, approval=80, key="iran"):
    cid = database.create_country(player_id, "کشور آزمون", "🏳️", country_key=key)
    database.update_country_field(cid, "approval_rating", approval)
    return cid


def _run(cid, days=1, start=None):
    """اجرای چند «روز» کامل: چرخه‌ی روزانه به‌علاوه‌ی چهار نوبت ۶ ساعته‌ی شدت بحران."""
    base = start or ia._now()
    results = []
    for offset in range(days):
        moment = base + datetime.timedelta(days=offset)
        results.append(ia.run_daily_cycle(db.get_country_by_id(cid), None, now_dt=moment))
        _run_slots(cid, moment)
    return results



def _run_slots(cid, moment, count=4):
    """نوبت‌های ۶ ساعته‌ی همان روز تقویمی تهران (گرید پرداخت درآمد).

    نوبت‌هایی که به روز بعد سُر می‌خورند اجرا نمی‌شوند، وگرنه سقف «یک تشدید در روز»
    در آزمون بی‌معنا می‌شود.
    """
    day = moment.astimezone(ia.IRAN_TZ).date()
    events = []
    for index in range(count):
        instant = moment + datetime.timedelta(hours=6 * index)
        if instant.astimezone(ia.IRAN_TZ).date() != day:
            break
        events.extend(ia.run_crisis_slot_cycle(db.get_country_by_id(cid), instant))
    return events


# ─────────────────────────────────────────────────────────────────────────────
# کلید اصلی و idempotency
# ─────────────────────────────────────────────────────────────────────────────

def test_system_is_disabled_by_default(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "off.db"))
    db.init_db()
    assert ia.is_enabled() is False
    assert ia.random_crises_enabled() is False

    cid = _country(db)
    before = db.get_country_by_id(cid)
    assert ia.run_daily_cycle(before) is None
    after = db.get_country_by_id(cid)
    assert after["population"] == before["population"]
    assert after["tax_income"] == before["tax_income"]


def test_daily_cycle_runs_only_once_per_day(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)

    first = ia.run_daily_cycle(database.get_country_by_id(cid))
    assert first is not None
    population_after_first = database.get_country_by_id(cid)["population"]

    for _ in range(5):
        assert ia.run_daily_cycle(database.get_country_by_id(cid)) is None
    assert database.get_country_by_id(cid)["population"] == population_after_first

    logs = ia.get_history(cid, days=10)
    assert len(logs) == 1


# ─────────────────────────────────────────────────────────────────────────────
# جمعیت
# ─────────────────────────────────────────────────────────────────────────────

def test_high_approval_grows_population_low_approval_shrinks_it(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    happy = _country(database, player_id=7201, approval=90, key="c_happy")
    angry = _country(database, player_id=7202, approval=15, key="c_angry")

    happy_before = database.get_country_by_id(happy)["population"]
    angry_before = database.get_country_by_id(angry)["population"]
    _run(happy)
    _run(angry)

    assert database.get_country_by_id(happy)["population"] > happy_before
    assert database.get_country_by_id(angry)["population"] < angry_before


def test_population_change_is_relative_not_flat(monkeypatch, tmp_path):
    """کاهش باید نسبت به اندازه‌ی کشور باشد، نه عدد ثابت برای همه."""
    database = _fresh_db(monkeypatch, tmp_path)
    small = _country(database, player_id=7301, approval=15, key="c_small")
    big = _country(database, player_id=7302, approval=15, key="c_big")
    database.update_country_field(small, "population", 5_000_000)
    database.update_country_field(big, "population", 300_000_000)

    small_result = _run(small)[0]
    big_result = _run(big)[0]

    assert abs(big_result["population_delta"]) > abs(small_result["population_delta"])
    small_pct = abs(small_result["population_delta"]) / 5_000_000
    big_pct = abs(big_result["population_delta"]) / 300_000_000
    assert abs(small_pct - big_pct) < 0.001


def test_population_never_falls_below_floor(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database, approval=0)
    database.update_country_field(cid, "population", ia.POPULATION_FLOOR + 500)

    _run(cid, days=6)
    assert database.get_country_by_id(cid)["population"] >= ia.POPULATION_FLOOR


def test_daily_population_change_is_capped(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database, approval=0)
    before = database.get_country_by_id(cid)["population"]
    result = _run(cid)[0]
    assert abs(result["population_delta"]) <= before * ia.MAX_DAILY_POP_CHANGE_PCT + 1


# ─────────────────────────────────────────────────────────────────────────────
# مالیات
# ─────────────────────────────────────────────────────────────────────────────

def test_heavy_tax_raises_income_but_hurts_approval(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database, approval=80)
    state = ia.get_state(cid)
    country = database.get_country_by_id(cid)

    normal = ia.project_tax_income(country, state, "normal")
    heavy = ia.project_tax_income(country, state, "heavy")
    emergency = ia.project_tax_income(country, state, "emergency")
    low = ia.project_tax_income(country, state, "low")
    assert low < normal < heavy < emergency

    approval_before = country["approval_rating"]
    assert ia.set_tax_policy(cid, "emergency")[0]
    _run(cid)
    assert database.get_country_by_id(cid)["approval_rating"] < approval_before


def test_low_approval_reduces_tax_collection(monkeypatch, tmp_path):
    """قلب سیستم: رضایت پایین‌تر → فرار مالیاتی → وصولی کمتر."""
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database, approval=90)
    state = ia.get_state(cid)
    country = database.get_country_by_id(cid)
    rich_collection = ia.project_tax_income(country, state, "normal")

    database.update_country_field(cid, "approval_rating", 15)
    country = database.get_country_by_id(cid)
    poor_collection = ia.project_tax_income(country, state, "normal")

    assert poor_collection < rich_collection
    assert ia.compliance_for(15) < ia.compliance_for(90)


def test_heavy_tax_on_angry_population_can_backfire(monkeypatch, tmp_path):
    """مالیات سنگین روی کشور ناراضی می‌تواند از مالیات عادیِ کشور راضی کمتر بدهد."""
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database, approval=85)
    state = ia.get_state(cid)
    calm_normal = ia.project_tax_income(database.get_country_by_id(cid), state, "normal")

    database.update_country_field(cid, "approval_rating", 12)
    angry_state = dict(state)
    angry_state["unrest_stage"] = 3
    angry_heavy = ia.project_tax_income(database.get_country_by_id(cid), angry_state, "heavy")

    assert angry_heavy < calm_normal


def test_tax_scales_with_population(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database, approval=80)
    state = ia.get_state(cid)
    country = database.get_country_by_id(cid)
    baseline = ia.project_tax_income(country, state, "normal")

    database.update_country_field(cid, "population", int(country["population"] * 1.5))
    grown = ia.project_tax_income(database.get_country_by_id(cid), state, "normal")
    assert grown > baseline


# ─────────────────────────────────────────────────────────────────────────────
# ناآرامی
# ─────────────────────────────────────────────────────────────────────────────

def test_unrest_escalates_in_stages_not_instantly(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database, approval=5)
    assert ia.set_tax_policy(cid, "emergency")[0]

    stages = [r["unrest_stage"] for r in _run(cid, days=5)]
    assert stages[0] < 4, "ناآرامی نباید در همان روز اول به بحران حکومتی برسد"
    assert stages == sorted(stages), "مراحل ناآرامی باید پلکانی بالا بروند"
    assert max(stages) >= 2


def test_collapse_risk_needs_several_critical_days(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database, approval=0)
    assert ia.set_tax_policy(cid, "emergency")[0]

    results = _run(cid, days=10)
    risky = [index for index, r in enumerate(results) if r["collapse_risk"]]
    if risky:
        assert risky[0] >= ia.COLLAPSE_CRITICAL_DAYS
    # سیستم هرگز خودش کشور را حذف نمی‌کند
    assert database.get_country_by_id(cid) is not None


def test_calm_country_stays_calm(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database, approval=95)
    database.update_country_field(cid, "grain", 500_000)
    results = _run(cid, days=5)
    assert all(r["unrest_stage"] == 0 for r in results)


# ─────────────────────────────────────────────────────────────────────────────
# بحران‌ها
# ─────────────────────────────────────────────────────────────────────────────

def test_crisis_starts_with_warning_and_has_no_damage_yet(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    pop_before = database.get_country_by_id(cid)["population"]

    ok, _msg, crisis = ia.create_crisis(cid, "earthquake", severity="medium", admin_id=1)
    assert ok
    assert crisis["stage"] == "warning"
    assert database.get_country_by_id(cid)["population"] == pop_before


def test_crisis_lifecycle_warning_impact_recovery_end(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    ok, _msg, crisis = ia.create_crisis(cid, "earthquake", severity="medium", admin_id=1)
    assert ok
    crisis_id = crisis["id"]
    pop_before = database.get_country_by_id(cid)["population"]

    start = ia._now()
    _run(cid, days=1, start=start)  # هشدار → وقوع
    assert ia.get_crisis(crisis_id)["stage"] == "impact"
    # تلفات از خسارت ثبت‌شده سنجیده می‌شود، نه از جمعیت خالص:
    # با اعداد واقع‌گرایانه‌ی جدید، رشد طبیعی جمعیت از تلفات یک زلزله بیشتر است.
    damage = ia._json_load(ia.get_crisis(crisis_id)["damage_json"], {})
    assert damage.get("population", 0) > 0

    _run(cid, days=1, start=start + datetime.timedelta(days=5))  # وقوع → بازسازی
    assert ia.get_crisis(crisis_id)["stage"] == "recovery"

    _run(cid, days=1, start=start + datetime.timedelta(days=6))  # بازسازی → پایان
    assert ia.get_crisis(crisis_id)["stage"] == "ended"


def test_player_response_reduces_crisis_damage(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    passive = _country(database, player_id=7401, key="c_passive")
    active = _country(database, player_id=7402, key="c_active")
    for cid in (passive, active):
        database.update_country_field(cid, "treasury", 500_000_000)
        database.update_country_field(cid, "population", 50_000_000)

    _ok, _m, crisis_passive = ia.create_crisis(passive, "earthquake", severity="severe", admin_id=1)
    _ok, _m, crisis_active = ia.create_crisis(active, "earthquake", severity="severe", admin_id=1)

    ok, _msg, _info = ia.respond_to_crisis(crisis_active["id"], "emergency_aid", actor_id=7402)
    assert ok
    ok, _msg, _info = ia.respond_to_crisis(crisis_active["id"], "rapid_rebuild", actor_id=7402)
    assert ok

    start = ia._now()
    _run(passive, days=1, start=start)
    _run(active, days=1, start=start)

    damage_passive = ia._json_load(ia.get_crisis(crisis_passive["id"])["damage_json"], {})
    damage_active = ia._json_load(ia.get_crisis(crisis_active["id"])["damage_json"], {})
    assert damage_active["population"] < damage_passive["population"]


def test_same_response_cannot_be_used_twice_in_one_day(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "treasury", 200_000_000)
    _ok, _m, crisis = ia.create_crisis(cid, "flood", admin_id=1)

    assert ia.respond_to_crisis(crisis["id"], "emergency_aid", actor_id=1)[0]
    ok, message, _info = ia.respond_to_crisis(crisis["id"], "emergency_aid", actor_id=1)
    assert not ok
    assert "امروز" in message


def test_response_requires_treasury(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "treasury", 100)
    _ok, _m, crisis = ia.create_crisis(cid, "flood", admin_id=1)

    ok, message, _info = ia.respond_to_crisis(crisis["id"], "rapid_rebuild", actor_id=1)
    assert not ok
    assert "خزانه" in message
    # بیانیه رسمی رایگان است و باید همیشه در دسترس باشد
    assert ia.respond_to_crisis(crisis["id"], "official_address", actor_id=1)[0]


def test_two_severe_crises_cannot_stack(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    assert ia.create_crisis(cid, "earthquake", severity="severe", admin_id=1)[0]
    ok, message, _crisis = ia.create_crisis(cid, "epidemic", severity="severe", admin_id=1)
    assert not ok
    assert "سنگین" in message


def test_active_crisis_limit_is_enforced(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    for key in ("earthquake", "flood"):
        assert ia.create_crisis(cid, key, severity="light", admin_id=1)[0]
    ok, message, _crisis = ia.create_crisis(cid, "storm", severity="light", admin_id=1)
    assert not ok
    assert "سقف" in message


def test_random_crises_stay_off_until_admin_enables_them(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database, approval=10)
    monkeypatch.setattr(ia.random, "random", lambda: 0.0)  # بدترین حالت شانس

    _run(cid, days=5)
    assert [c for c in ia.get_crisis_history(cid) if c["origin"] == "random"] == []


def test_chain_crisis_fires_from_country_behaviour(monkeypatch, tmp_path):
    """قحطی باید از تمام‌شدن غلات ایجاد شود، نه از شانس."""
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database, approval=30)
    database.update_country_field(cid, "grain", 0)

    _run(cid, days=1)
    keys = {c["crisis_key"] for c in ia.get_crisis_history(cid)}
    origins = {c["origin"] for c in ia.get_crisis_history(cid)}
    assert "famine" in keys
    assert origins == {"chain"}


def test_admin_can_force_instant_story_crisis(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    pop_before = database.get_country_by_id(cid)["population"]

    ok, _msg, crisis = ia.create_crisis(
        cid, "earthquake", severity="severe", admin_id=99, skip_warning=True, force=True
    )
    assert ok
    assert crisis["stage"] == "impact"
    assert database.get_country_by_id(cid)["population"] < pop_before


def test_admin_can_end_and_retune_crisis(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    _ok, _m, crisis = ia.create_crisis(cid, "storm", severity="light", admin_id=1)

    assert ia.update_crisis(crisis["id"], severity="severe", duration_days=9, admin_id=1)[0]
    refreshed = ia.get_crisis(crisis["id"])
    assert refreshed["severity"] == "severe"
    assert refreshed["duration_days"] == 9

    assert ia.end_crisis(crisis["id"], admin_id=1)[0]
    assert ia.get_crisis(crisis["id"])["stage"] == "ended"
    assert ia.get_active_crises(cid) == []


# ─────────────────────────────────────────────────────────────────────────────
# اتصال به تورنومنت
# ─────────────────────────────────────────────────────────────────────────────

def test_crisis_occurrence_alone_gives_no_tournament_points(monkeypatch, tmp_path):
    """بدشانسی نباید امتیاز بدهد یا بگیرد؛ فقط واکنش شمرده می‌شود."""
    import tournament_system as tournament

    database = _fresh_db(monkeypatch, tmp_path)
    unlucky = _country(database, player_id=7501, key="c_unlucky")
    calm = _country(database, player_id=7502, key="c_calm")
    for cid in (unlucky, calm):
        database.update_country_field(cid, "treasury", 300_000_000)

    _ok, _m, season = tournament.create_draft(duration_days=7)
    assert tournament.join_tournament(7501, unlucky)[0]
    assert tournament.join_tournament(7502, calm)[0]
    assert tournament.start_season(season["id"])[0]

    ia.create_crisis(unlucky, "earthquake", severity="medium", admin_id=1, skip_warning=True, force=True)

    tournament.refresh_player(season["id"], country_id=unlucky, force=True)
    tournament.refresh_player(season["id"], country_id=calm, force=True)
    unlucky_score = tournament.get_score_details(season["id"], 7501)
    calm_score = tournament.get_score_details(season["id"], 7502)
    assert unlucky_score["objectives_score"] == calm_score["objectives_score"]


def test_good_crisis_management_earns_tournament_points(monkeypatch, tmp_path):
    import tournament_system as tournament

    database = _fresh_db(monkeypatch, tmp_path)
    responder = _country(database, player_id=7601, key="c_responder")
    passive = _country(database, player_id=7602, key="c_passive2")
    for cid in (responder, passive):
        database.update_country_field(cid, "treasury", 500_000_000)

    _ok, _m, season = tournament.create_draft(duration_days=7)
    assert tournament.join_tournament(7601, responder)[0]
    assert tournament.join_tournament(7602, passive)[0]
    assert tournament.start_season(season["id"])[0]

    _ok, _m, crisis_r = ia.create_crisis(responder, "flood", severity="medium", admin_id=1)
    ia.create_crisis(passive, "flood", severity="medium", admin_id=1)
    assert ia.respond_to_crisis(crisis_r["id"], "emergency_aid", actor_id=7601)[0]
    assert ia.respond_to_crisis(crisis_r["id"], "rapid_rebuild", actor_id=7601)[0]

    tournament.refresh_player(season["id"], country_id=responder, force=True)
    tournament.refresh_player(season["id"], country_id=passive, force=True)
    responder_details = tournament.get_score_details(season["id"], 7601)
    passive_details = tournament.get_score_details(season["id"], 7602)
    assert responder_details["objectives_score"] > passive_details["objectives_score"]
    assert responder_details["stability_score"] > passive_details["stability_score"]


def test_security_crackdown_is_penalised_in_stability(monkeypatch, tmp_path):
    import tournament_system as tournament

    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database, player_id=7701, key="c_crackdown")
    database.update_country_field(cid, "treasury", 500_000_000)
    _ok, _m, season = tournament.create_draft(duration_days=7)
    assert tournament.join_tournament(7701, cid)[0]
    assert tournament.start_season(season["id"])[0]

    _ok, _m, crisis = ia.create_crisis(cid, "civil_unrest", severity="medium", admin_id=1)
    approval_before = database.get_country_by_id(cid)["approval_rating"]
    assert ia.respond_to_crisis(crisis["id"], "security_crackdown", actor_id=7701)[0]

    # سرکوب ناآرامی را می‌خواباند اما رضایت را می‌سوزاند
    assert database.get_country_by_id(cid)["approval_rating"] < approval_before
    assert ia.get_state(cid)["unrest"] <= 0


# ─────────────────────────────────────────────────────────────────────────────
# رابط کاربری
# ─────────────────────────────────────────────────────────────────────────────

def test_player_keyboard_has_domestic_button():
    keyboard = get_main_keyboard(7801)
    texts = {button.text for row in keyboard.keyboard for button in row}
    assert "🏛️ سیاست داخلی" in texts


def test_admin_panel_exposes_crisis_management():
    import inspect
    from handlers import admin as admin_handlers

    source = inspect.getsource(admin_handlers.admin_panel)
    assert "admin:dom" in source
    assert "مدیریت بحران و سیاست داخلی" in source


def test_every_crisis_has_actions_and_news():
    for key, spec in ia.CRISIS_CATALOG.items():
        crisis = {"crisis_key": key, "severity": "medium", "stage": "warning", "mitigation": 0}
        actions = ia.available_actions(crisis)
        assert actions, f"بحران {key} هیچ اقدام واکنشی ندارد"
        assert all(action in ia.CRISIS_ACTIONS for action in actions)
        assert spec.get("warning") and spec.get("impact")
        news = ia.build_news({"name": "X", "flag": "🏳️"}, crisis, "warning")
        assert news and news[0] and news[1]


# ─────────────────────────────────────────────────────────────────────────────
# رگرسیون گزارش بازیکن (۲۰۲۶-۰۸-۲۷): «مالیات را بردم روی ۲ میل ولی وضعیت ۱.۴ زده»
# ─────────────────────────────────────────────────────────────────────────────

def test_tax_policy_change_applies_immediately(monkeypatch, tmp_path):
    """درآمد مالیاتی باید همان لحظه عوض شود، نه چرخه‌ی بعد.

    قبلاً صفحه‌ی مالیات پیش‌بینی ۱٫۸۹M را نشان می‌داد ولی «وضعیت کشور» هنوز
    ۱٫۴M بود و بازیکن فکر می‌کرد باگ است.
    """
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database, approval=86)
    database.update_country_field(cid, "population", 59_000_000)
    database.update_country_field(cid, "tax_income", 1_333_000)
    state = ia.get_state(cid)

    expected = ia.project_tax_income(database.get_country_by_id(cid), state, "heavy")
    ok, message = ia.set_tax_policy(cid, "heavy")
    assert ok

    shown_in_country_status = database.get_country_by_id(cid)["tax_income"]
    assert shown_in_country_status == expected
    assert str(f"{expected:,}") in message


def test_policy_is_locked_until_next_cycle(monkeypatch, tmp_path):
    """جلوی «اضطراری بزن، پول بگیر، برگرد به کم» گرفته می‌شود."""
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database, approval=80)

    assert ia.set_tax_policy(cid, "emergency")[0]
    ok, message = ia.set_tax_policy(cid, "low")
    assert not ok
    assert "چرخه" in message

    _run(cid)  # چرخه‌ی روزانه قفل را باز می‌کند و هزینه‌ی رضایت را می‌گیرد
    assert ia.set_tax_policy(cid, "low")[0]


def test_flipping_between_harsh_policies_cannot_dodge_unrest_crisis(monkeypatch, tmp_path):
    """اکسپلویت: جابه‌جایی سنگین↔اضطراری شمارنده را صفر می‌کرد و بحران را دور می‌زد."""
    database = _fresh_db(monkeypatch, tmp_path)
    flipper = _country(database, player_id=7901, approval=70, key="c_flip")
    honest = _country(database, player_id=7902, approval=70, key="c_honest")

    start = ia._now()
    ia.set_tax_policy(honest, "heavy")
    for day in range(8):
        moment = start + datetime.timedelta(days=day)
        ia.set_tax_policy(flipper, "emergency" if day % 2 else "heavy")
        ia.run_daily_cycle(database.get_country_by_id(flipper), None, now_dt=moment)
        ia.run_daily_cycle(database.get_country_by_id(honest), None, now_dt=moment)

    flipper_pressure = ia.get_state(flipper)["pressure_days"]
    assert flipper_pressure >= 7, "روزهای فشار مالیاتی نباید با تعویض سیاست صفر شود"

    flipper_crises = [c for c in ia.get_crisis_history(flipper, 50) if c["crisis_key"] == "civil_unrest"]
    honest_crises = [c for c in ia.get_crisis_history(honest, 50) if c["crisis_key"] == "civil_unrest"]
    assert flipper_crises, "بازیکنی که سیاست را جابه‌جا می‌کند نباید از بحران فرار کند"
    assert len(flipper_crises) >= len(honest_crises) - 1


# ─────────────────────────────────────────────────────────────────────────────
# یکپارچگی نمایش رضایت عمومی: یک صفحه‌ی تفصیلی، چند در ورودی
# ─────────────────────────────────────────────────────────────────────────────

def test_approval_detail_page_is_reachable_even_when_system_is_off(monkeypatch, tmp_path):
    """رضایت عمومی مال سیاست داخلی نیست؛ خاموش‌بودن سیستم نباید قایمش کند."""
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "off_view.db"))
    db.init_db()
    assert ia.is_enabled() is False

    from handlers.internal_affairs import build_approval_view
    cid = _country(db, approval=42)
    text, markup = build_approval_view(db.get_country_by_id(cid), {})

    assert "رضایت عمومی" in text
    assert "42" in text
    assert "برق و انرژی" in text and "غذا و غلات" in text
    assert markup.inline_keyboard


def test_approval_page_merges_causes_and_effects_when_enabled(monkeypatch, tmp_path):
    """صفحه‌ی واحد باید هم «چرا افتاد» و هم «چه شد» را داشته باشد."""
    database = _fresh_db(monkeypatch, tmp_path)
    from handlers.internal_affairs import build_approval_view

    cid = _country(database, approval=30)
    database.update_country_field(cid, "grain", 0)
    _run(cid)

    text, _markup = build_approval_view(database.get_country_by_id(cid), ia.get_state(cid))
    # علت‌ها (از approval_system)
    assert "ارزیابی روزانه منابع حیاتی" in text
    assert "غذا و غلات" in text
    assert "جمعیت و مهاجرت" in text
    # معلول‌ها (از سیستم جدید)
    assert "ناآرامی داخلی" in text
    assert "اثر روی درآمد مالیاتی" in text
    assert "نرخ تمکین" in text


def test_only_one_detailed_approval_renderer_remains(monkeypatch, tmp_path):
    """رگرسیون: صفحه‌ی موازی قدیمی نباید برگردد."""
    import inspect
    from handlers import country as country_handlers

    profile_src = inspect.getsource(country_handlers.country_profile)
    callback_src = inspect.getsource(country_handlers.country_callback_handler)
    command_src = inspect.getsource(country_handlers.approval_command)

    # وضعیت کشور فقط خلاصه‌ی یک‌خطی دارد و به مقصد واحد اشاره می‌کند
    assert "سیاست داخلی" in profile_src
    assert "get_approval_status_message" not in profile_src
    # هر سه در ورودی به همان یک صفحه می‌روند
    assert "get_approval_status_message" not in callback_src
    assert "get_approval_status_message" not in command_src
    assert "show_approval_page" in command_src


def test_country_status_shows_approval_trend(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database, approval=80)
    assert ia.approval_trend(cid) is None  # هنوز داده‌ی کافی نیست

    start = ia._now()
    ia.set_tax_policy(cid, "heavy")
    _run(cid, days=2, start=start)

    trend = ia.approval_trend(cid)
    assert trend is not None
    assert trend < 0, "مالیات سنگین باید روند نزولی رضایت بسازد"


# ─────────────────────────────────────────────────────────────────────────────
# رگرسیون: بحران دستی ادمین در مرحله‌ی هشدار می‌ماند تا چرخه‌ی روزانه
# ─────────────────────────────────────────────────────────────────────────────

def test_admin_created_crisis_applies_nothing_until_impact(monkeypatch, tmp_path):
    """توضیح رفتار گزارش‌شده: ساخت بحران از پنل، فوراً رضایت را کم نمی‌کند."""
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database, approval=86)
    database.update_country_field(cid, "treasury", 50_000_000)

    ok, _msg, crisis = ia.create_crisis(cid, "civil_unrest", severity="medium", admin_id=1)
    assert ok
    assert crisis["stage"] == "warning"
    assert database.get_country_by_id(cid)["approval_rating"] == 86
    assert float(ia.get_state(cid)["unrest"]) == 0


def test_admin_can_force_impact_of_a_pending_crisis(monkeypatch, tmp_path):
    """ادمین باید بتواند بحرانِ در حالت هشدار را همان لحظه اعمال کند."""
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database, approval=86)
    database.update_country_field(cid, "treasury", 50_000_000)
    _ok, _m, crisis = ia.create_crisis(cid, "civil_unrest", severity="medium", admin_id=1)

    ok, message, applied = ia.force_impact(crisis["id"], admin_id=1)
    assert ok, message
    assert ia.get_crisis(crisis["id"])["stage"] == "impact"
    assert database.get_country_by_id(cid)["approval_rating"] < 86
    assert float(ia.get_state(cid)["unrest"]) > 0
    assert applied["treasury"] > 0

    # دوباره اعمال نشود
    ok2, _msg2, _a = ia.force_impact(crisis["id"], admin_id=1)
    assert not ok2


def test_damage_preview_matches_what_actually_happens(monkeypatch, tmp_path):
    """پیش‌نمایش خسارت در پنل ادمین باید با خسارت واقعی بخواند."""
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database, approval=80)
    database.update_country_field(cid, "treasury", 80_000_000)
    database.update_country_field(cid, "population", 40_000_000)
    _ok, _m, crisis = ia.create_crisis(cid, "earthquake", severity="severe", admin_id=1)

    preview = ia.estimate_damage(ia.get_crisis(crisis["id"]))
    ia.force_impact(crisis["id"], admin_id=1)
    actual = ia._json_load(ia.get_crisis(crisis["id"])["damage_json"], {})

    for key in ("population", "treasury"):
        assert abs(preview[key] - actual[key]) <= max(1, preview[key] * 0.01)


def test_admin_panel_offers_force_impact_only_while_pending():
    import inspect
    from handlers import internal_admin

    source = inspect.getsource(internal_admin._crisis_panel)
    assert "admin:dom_impact" in source
    assert "هنوز هیچ خسارتی اعمال نشده است" in source
    assert "برآورد خسارت در زمان وقوع" in source


# ─────────────────────────────────────────────────────────────────────────────
# اقدامات مهار بحران هر روز دوباره در دسترس می‌شوند
# ─────────────────────────────────────────────────────────────────────────────

def test_crisis_actions_become_available_again_next_day(monkeypatch, tmp_path):
    """بحران چندروزه است؛ بازیکن باید هر روز بتواند دوباره اقدام کند."""
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "treasury", 500_000_000)
    _ok, _m, crisis = ia.create_crisis(cid, "earthquake", severity="severe", admin_id=1)

    assert ia.respond_to_crisis(crisis["id"], "emergency_aid", actor_id=1)[0]
    assert ia.respond_to_crisis(crisis["id"], "emergency_aid", actor_id=1)[0] is False
    assert ia.get_actions_done_today(crisis["id"]) == {"emergency_aid"}

    # فردا
    tomorrow = ia._now() + datetime.timedelta(days=1)
    monkeypatch.setattr(ia, "_today", lambda dt=None: ia._iso(tomorrow)[:10])
    assert ia.get_actions_done_today(crisis["id"]) == set()
    ok, message, _info = ia.respond_to_crisis(crisis["id"], "emergency_aid", actor_id=1)
    assert ok, message


def test_repeated_relief_still_cannot_fully_cancel_a_crisis(monkeypatch, tmp_path):
    """حتی با اقدام هر روزه، سقف مهار ۸۰٪ است — پول نباید بحران را صفر کند."""
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "treasury", 5_000_000_000)
    _ok, _m, crisis = ia.create_crisis(cid, "earthquake", severity="severe", admin_id=1)

    base = ia._now()
    for day in range(6):
        monkeypatch.setattr(ia, "_today", lambda dt=None, d=day: ia._iso(base + datetime.timedelta(days=d))[:10])
        for action in ia.available_actions(ia.get_crisis(crisis["id"])):
            ia.respond_to_crisis(crisis["id"], action, actor_id=1)

    assert float(ia.get_crisis(crisis["id"])["mitigation"]) <= 0.80


# ─────────────────────────────────────────────────────────────────────────────
# وزن مخاطرات جغرافیایی و فصلی
# ─────────────────────────────────────────────────────────────────────────────

def test_hazard_profile_reflects_geography():
    quake_country = {"country_key": "japan"}
    calm_country = {"country_key": "norway"}
    assert ia.hazard_weights(quake_country)["earthquake"] > ia.hazard_weights(calm_country)["earthquake"] * 5

    assert ia.hazard_weights({"country_key": "usa"})["wildfire"] > ia.hazard_weights({"country_key": "bangladesh"})["wildfire"]
    assert ia.hazard_weights({"country_key": "bangladesh"})["flood"] > ia.hazard_weights({"country_key": "saudi"})["flood"]
    assert ia.hazard_weights({"country_key": "saudi"})["drought"] > ia.hazard_weights({"country_key": "norway"})["drought"]
    assert ia.hazard_weights({"country_key": "iran"})["earthquake"] > ia.hazard_weights({"country_key": "egypt"})["earthquake"]
    assert ia.hazard_weights({"country_key": "australia"})["wildfire"] > ia.hazard_weights({"country_key": "finland"})["wildfire"]


def test_hazard_profile_reflects_season():
    summer = datetime.datetime(2026, 7, 15, tzinfo=datetime.timezone.utc)
    winter = datetime.datetime(2026, 1, 15, tzinfo=datetime.timezone.utc)
    country = {"country_key": "spain"}
    assert ia.hazard_weights(country, summer)["wildfire"] > ia.hazard_weights(country, winter)["wildfire"]
    assert ia.hazard_weights(country, winter)["epidemic"] > ia.hazard_weights(country, summer)["epidemic"]


def test_random_crisis_picks_geographically_plausible_hazard(monkeypatch, tmp_path):
    """روی ۳۰۰ نمونه، زلزله در ژاپن باید بسیار بیشتر از هلند باشد."""
    database = _fresh_db(monkeypatch, tmp_path)
    monkeypatch.setattr(ia.random, "random", lambda: 0.0)  # همیشه بحران رخ بدهد

    def sample(country_key):
        counts = {}
        country = {"country_key": country_key, "approval_rating": 80}
        for _ in range(300):
            picked = ia._random_crisis_candidate(country, {})
            counts[picked[0]] = counts.get(picked[0], 0) + 1
        return counts

    japan = sample("japan")
    netherlands = sample("netherlands")
    assert japan.get("earthquake", 0) > netherlands.get("earthquake", 0) * 3
    assert netherlands.get("flood", 0) > japan.get("earthquake", 0) * 0  # سیل هلند وجود دارد
    assert netherlands.get("flood", 0) > 0


def test_every_country_in_the_game_has_a_hazard_profile():
    """اگر کشور جدیدی به بازی اضافه شود، این تست یادآوری می‌کند پروفایلش را بنویسید."""
    missing = [
        key for key in config.COUNTRY_STARTING_OVERRIDES
        if key not in ia.COUNTRY_HAZARD_WEIGHTS
    ]
    assert not missing, f"این کشورها پروفایل مخاطرات ندارند: {missing}"


def test_hazard_profiles_are_well_formed():
    valid = set(ia.BASE_HAZARD_WEIGHTS)
    for country_key, profile in ia.COUNTRY_HAZARD_WEIGHTS.items():
        unknown = set(profile) - valid
        assert not unknown, f"{country_key} بلای ناشناخته دارد: {unknown}"
        for hazard, factor in profile.items():
            assert 0.0 <= factor <= 4.0, f"{country_key}/{hazard} ضریب نامعقول: {factor}"


def test_every_country_can_still_get_some_disaster_except_the_un():
    """هیچ کشوری نباید کاملاً مصون باشد — جز سازمان ملل که سرزمین ندارد."""
    for country_key in config.COUNTRY_STARTING_OVERRIDES:
        weights = ia.hazard_weights({"country_key": country_key})
        total = sum(weights.values())
        if country_key == "un":
            assert total == 0, "سازمان ملل نباید بلای طبیعی بگیرد"
        else:
            assert total > 0, f"{country_key} از همه‌ی بلایا مصون است"


def test_landlocked_and_desert_countries_are_not_storm_magnets():
    for country_key in ("afghanistan", "nepal", "saudi", "iran", "turkmenistan"):
        weights = ia.hazard_weights({"country_key": country_key})
        assert weights["storm"] < weights["drought"] or weights["storm"] < weights["earthquake"], country_key


def test_southern_hemisphere_seasons_are_inverted():
    """مرداد در استرالیا زمستان است، نه اوج فصل آتش‌سوزی."""
    july = datetime.datetime(2026, 7, 15, tzinfo=datetime.timezone.utc)
    january = datetime.datetime(2026, 1, 15, tzinfo=datetime.timezone.utc)

    au_summer = ia.hazard_weights({"country_key": "australia"}, january)["wildfire"]
    au_winter = ia.hazard_weights({"country_key": "australia"}, july)["wildfire"]
    assert au_summer > au_winter * 2

    us_summer = ia.hazard_weights({"country_key": "usa"}, july)["wildfire"]
    us_winter = ia.hazard_weights({"country_key": "usa"}, january)["wildfire"]
    assert us_summer > us_winter * 2

    # و هر کشور نیم‌کره جنوبی واقعاً در مجموعه باشد
    for key in ia.SOUTHERN_HEMISPHERE:
        assert key in config.COUNTRY_STARTING_OVERRIDES, key


def test_wet_tropical_countries_are_not_dominated_by_wildfire():
    for key in ("colombia", "ecuador", "malaysia", "nigeria", "venezuela", "finland", "norway"):
        weights = ia.hazard_weights({"country_key": key})
        dominant = max(weights, key=weights.get)
        assert dominant != "wildfire", f"{key} نباید بلای غالبش آتش‌سوزی باشد"


# ─────────────────────────────────────────────────────────────────────────────
# تشدید شبانه‌ی بحرانِ رسیدگی‌نشده
# ─────────────────────────────────────────────────────────────────────────────

def test_unmanaged_crisis_escalates_one_level_each_night(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "treasury", 200_000_000)
    _ok, _m, crisis = ia.create_crisis(cid, "flood", severity="light", admin_id=1)

    start = ia._now()
    levels = []
    for day in range(4):
        _run(cid, days=1, start=start + datetime.timedelta(days=day))
        levels.append(ia.get_crisis(crisis["id"])["severity"])

    assert levels[0] == "medium", "شب اول باید از خفیف به متوسط برود"
    assert "severe" in levels, "بعد از دو شب باید به شدید برسد"
    assert levels[-1] == "severe", "بالاتر از شدید نمی‌رود"
    assert ia.get_crisis(crisis["id"])["escalations"] >= 2


def test_a_managed_crisis_does_not_escalate(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "treasury", 500_000_000)
    _ok, _m, crisis = ia.create_crisis(cid, "flood", severity="light", admin_id=1)
    assert ia.respond_to_crisis(crisis["id"], "emergency_aid", actor_id=1)[0]

    _run(cid, days=1)
    assert ia.get_crisis(crisis["id"])["severity"] == "light"
    assert ia.get_crisis(crisis["id"])["escalations"] == 0


def test_escalation_only_adds_the_difference_in_damage(monkeypatch, tmp_path):
    """تشدید نباید کشور را دوباره از صفر جریمه کند."""
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "treasury", 400_000_000)
    database.update_country_field(cid, "population", 50_000_000)
    _ok, _m, crisis = ia.create_crisis(cid, "earthquake", severity="light", admin_id=1)
    ia.force_impact(crisis["id"], admin_id=1)

    pop_after_light = database.get_country_by_id(cid)["population"]
    ok, _msg, _c, extra = ia.change_severity(crisis["id"], +1, admin_id=1)
    assert ok
    pop_after_medium = database.get_country_by_id(cid)["population"]

    light_loss = 50_000_000 - pop_after_light
    escalation_loss = pop_after_light - pop_after_medium
    # اختلاف ضریب خفیف→متوسط برابر ضریب خفیف است، پس خسارت افزایشی ≈ همان اندازه
    assert escalation_loss > 0
    assert abs(escalation_loss - light_loss) <= max(2, light_loss * 0.05)
    assert extra["population"] > 0


def test_admin_can_raise_and_lower_severity(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "treasury", 300_000_000)
    _ok, _m, crisis = ia.create_crisis(cid, "storm", severity="medium", admin_id=1)

    ok, message, updated, _x = ia.change_severity(crisis["id"], +1, admin_id=1)
    assert ok and updated["severity"] == "severe" and "تشدید" in message

    ok, _msg, updated, _x = ia.change_severity(crisis["id"], -1, admin_id=1)
    assert ok and updated["severity"] == "medium"

    # سقف و کف
    ia.change_severity(crisis["id"], -1, admin_id=1)
    ok, message, _u, _x = ia.change_severity(crisis["id"], -1, admin_id=1)
    assert not ok and "خفیف" in message
    for _ in range(2):
        ia.change_severity(crisis["id"], +1, admin_id=1)
    ok, message, _u, _x = ia.change_severity(crisis["id"], +1, admin_id=1)
    assert not ok and "شدید" in message


def test_each_severity_level_has_its_own_news():
    country = {"name": "آزمون", "flag": "🏳️"}
    seen = set()
    for severity in ia.SEVERITY_ORDER:
        crisis = {"crisis_key": "flood", "severity": severity, "stage": "impact", "mitigation": 0}
        title, body = ia.build_news(country, crisis, "escalated")
        assert ia.SEVERITY_LABELS[severity] in title
        assert body and body not in seen, "متن هر سطح باید متفاوت باشد"
        seen.add(body)


def test_escalation_news_is_published_once_per_level(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    _ok, _m, crisis = ia.create_crisis(cid, "drought", severity="light", admin_id=1)

    ia.mark_news_sent(crisis["id"], "escalated_medium")
    refreshed = ia.get_crisis(crisis["id"])
    assert ia.news_already_sent(refreshed, "escalated_medium")
    assert not ia.news_already_sent(refreshed, "escalated_severe")


def test_admin_panel_exposes_severity_controls():
    import inspect
    from handlers import internal_admin

    source = inspect.getsource(internal_admin)
    assert "admin:dom_up" in source and "admin:dom_down" in source
    assert "تشدید یک سطح" in source and "تخفیف یک سطح" in source
    assert "_post_severity_news" in source
    panel = inspect.getsource(internal_admin._crisis_panel)
    assert "امشب یک سطح تشدید می‌شود" in panel


# ─────────────────────────────────────────────────────────────────────────────
# صفحه‌بندی فهرست بحران‌های فعال
# ─────────────────────────────────────────────────────────────────────────────

def test_active_crisis_list_is_paginated_and_loses_nothing(monkeypatch, tmp_path):
    """با ۲۵ بحران، فهرست تک‌صفحه‌ای چندتا را جا می‌انداخت."""
    import asyncio
    from handlers import internal_admin as adm

    database = _fresh_db(monkeypatch, tmp_path)
    keys = list(ia.CRISIS_CATALOG)
    for index in range(25):
        cid = database.create_country(7700 + index, f"کشور{index}", "🏳️", country_key=f"pg{index}")
        ia.create_crisis(cid, keys[index % len(keys)],
                         severity=("light", "medium", "severe")[index % 3], admin_id=1, force=True)

    class FakeQuery:
        def __init__(self):
            self.text = None
            self.markup = None

        async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
            self.text, self.markup = text, reply_markup

        async def answer(self, *a, **k):
            pass

    reachable = set()
    for page in range(6):
        query = FakeQuery()
        asyncio.run(adm._active_crises(query, page))
        buttons = [
            b.callback_data
            for row in query.markup.inline_keyboard
            for b in row
            if b.callback_data.startswith("admin:dom_crisis:")
        ]
        reachable.update(buttons)
        assert len(buttons) <= adm.PAGE_SIZE
        assert len(query.text) < 3500, "پیام نباید به سقف طول تلگرام نزدیک شود"

    assert len(reachable) == 25, "همه‌ی بحران‌ها باید از طریق صفحه‌بندی در دسترس باشند"

    first = FakeQuery()
    asyncio.run(adm._active_crises(first, 0))
    assert "مجموع: <b>25</b>" in first.text
    header_end = first.text.index("#")
    assert "شدید" in first.text[header_end:header_end + 200], "شدیدترها باید اول فهرست بیایند"


# ─────────────────────────────────────────────────────────────────────────────
# اقدامات اختصاصی هر بحران و پیش‌نیازها
# ─────────────────────────────────────────────────────────────────────────────

def test_each_crisis_has_its_own_distinct_action_set():
    seen_signatures = {}
    for crisis_key in ia.CRISIS_CATALOG:
        crisis = {"crisis_key": crisis_key, "severity": "medium", "stage": "impact", "mitigation": 0, "id": 1}
        actions = ia.available_actions(crisis)
        assert len(actions) >= 4, f"{crisis_key} گزینه‌ی کافی ندارد"
        assert all(a in ia.CRISIS_ACTIONS for a in actions)
        specific = tuple(sorted(set(actions) - set(ia._COMMON_ACTIONS)))
        assert specific, f"{crisis_key} هیچ اقدام اختصاصی ندارد"
        seen_signatures[crisis_key] = specific
    # حداقل نیمی از بحران‌ها ترکیب اقدامات یکتا داشته باشند
    assert len(set(seen_signatures.values())) >= len(seen_signatures) - 1


def test_vaccine_requires_high_tech_level(monkeypatch, tmp_path):
    """فناوری حالا پروژه‌ی تولید را قفل می‌کند، نه خودِ تزریق."""
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "treasury", 400_000_000)
    database.update_country_field(cid, "microchips", 9_000)
    database.update_country_field(cid, "medical_isotopes", 200)
    database.update_country_field(cid, "tech_level", 2)

    ok, reason, _n = ia.can_start_vaccine(database.get_country_by_id(cid), 1)
    assert not ok and "فناوری" in reason

    database.update_country_field(cid, "tech_level", ia.VACCINE_MIN_TECH_LEVEL)
    ok, message, project = ia.start_vaccine_project(cid, 1, actor_id=1)
    assert ok, message
    assert project["doses"] == ia.VACCINE_BATCH_DOSES
    assert database.get_country_by_id(cid)["microchips"] < 9_000


def test_vaccine_is_once_per_crisis(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "treasury", 900_000_000)
    database.update_country_field(cid, "tech_level", 5)
    database.update_country_field(cid, "vaccine_doses", ia.VACCINE_DOSES_PER_USE * 4)
    _ok, _m, crisis = ia.create_crisis(cid, "epidemic", admin_id=1)
    assert ia.respond_to_crisis(crisis["id"], "vaccine_program", actor_id=1)[0]

    tomorrow = ia._now() + datetime.timedelta(days=1)
    monkeypatch.setattr(ia, "_today", lambda dt=None: ia._iso(tomorrow)[:10])
    ok, reason, _i = ia.respond_to_crisis(crisis["id"], "vaccine_program", actor_id=1)
    assert not ok and "یک‌بار" in reason
    # ولی قرنطینه فردا باز است
    assert ia.respond_to_crisis(crisis["id"], "quarantine", actor_id=1)[0]


def test_aerial_firefighting_needs_fuel(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "treasury", 300_000_000)
    database.update_country_field(cid, "oil_reserves", 1_000)
    _ok, _m, crisis = ia.create_crisis(cid, "wildfire", admin_id=1)

    ok, reason = ia.check_action("aerial_firefight", crisis, database.get_country_by_id(cid))
    assert not ok and "نفت" in reason
    # با سوخت کافی ممکن می‌شود و سوخت مصرف می‌کند
    database.update_country_field(cid, "oil_reserves", 2_000_000)
    ok, _msg, _i = ia.respond_to_crisis(crisis["id"], "aerial_firefight", actor_id=1)
    assert ok
    assert database.get_country_by_id(cid)["oil_reserves"] < 2_000_000


def test_import_actions_actually_deliver_resources(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "treasury", 300_000_000)
    database.update_country_field(cid, "grain", 1_000)
    _ok, _m, crisis = ia.create_crisis(cid, "famine", admin_id=1)

    before = database.get_country_by_id(cid)["grain"]
    ok, _msg, info = ia.respond_to_crisis(crisis["id"], "import_grain", actor_id=1)
    assert ok
    assert database.get_country_by_id(cid)["grain"] > before
    assert info["grants"]["grain"] > 0


def test_unrest_options_trade_approval_against_order(monkeypatch, tmp_path):
    """سرکوب ناآرامی را بیشتر می‌خواباند ولی رضایت را می‌سوزاند؛ باج برعکس."""
    crackdown = ia.CRISIS_ACTIONS["security_crackdown"]
    concessions = ia.CRISIS_ACTIONS["concessions"]
    assert crackdown["unrest"] < concessions["unrest"]
    assert crackdown["approval"] < 0 < concessions["approval"]

    database = _fresh_db(monkeypatch, tmp_path)
    hard = _country(database, player_id=8201, approval=60, key="c_hard")
    soft = _country(database, player_id=8202, approval=60, key="c_soft")
    for cid in (hard, soft):
        database.update_country_field(cid, "treasury", 400_000_000)
    _ok, _m, c_hard = ia.create_crisis(hard, "civil_unrest", admin_id=1)
    _ok, _m, c_soft = ia.create_crisis(soft, "civil_unrest", admin_id=1)

    assert ia.respond_to_crisis(c_hard["id"], "security_crackdown", actor_id=1)[0]
    assert ia.respond_to_crisis(c_soft["id"], "concessions", actor_id=1)[0]

    assert database.get_country_by_id(hard)["approval_rating"] < database.get_country_by_id(soft)["approval_rating"]
    assert ia.get_state(hard)["unrest"] <= ia.get_state(soft)["unrest"]


def test_free_actions_are_always_reachable_when_broke(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "treasury", 0)
    _ok, _m, crisis = ia.create_crisis(cid, "civil_unrest", admin_id=1)

    country = database.get_country_by_id(cid)
    assert ia.check_action("official_address", crisis, country)[0]
    assert ia.check_action("dialogue", crisis, country)[0]
    assert not ia.check_action("concessions", crisis, country)[0]


# ─────────────────────────────────────────────────────────────────────────────
# سرایت بحران واگیردار به کشورهای هم‌مرز
# ─────────────────────────────────────────────────────────────────────────────

def _border_world(database, keys, treasury=300_000_000):
    ids = {}
    for index, key in enumerate(keys):
        cid = database.create_country(9800 + index, key, "🏳️", country_key=key)
        database.update_country_field(cid, "approval_rating", 80)
        database.update_country_field(cid, "treasury", treasury)
        ids[key] = cid
    return ids


def test_border_map_is_symmetric_and_covers_the_game():
    import borders
    mapping = borders.build_border_map(config.COUNTRY_STARTING_OVERRIDES.keys())
    for country, neighbours in mapping.items():
        for neighbour in neighbours:
            assert country in mapping[neighbour], f"{country}/{neighbour} یک‌طرفه است"
            assert neighbour != country
        # همسایه‌ای که در بازی نیست نباید بماند
        assert all(n in config.COUNTRY_STARTING_OVERRIDES for n in neighbours)
    assert mapping["iran"] and "iraq" in mapping["iran"]
    assert "canada" in mapping["usa"] and "mexico" in mapping["usa"]
    assert mapping["new_zealand"] == ["australia"]


def test_epidemic_spreads_to_neighbours_once_past_light(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    ia.random.seed(7)
    ids = _border_world(database, ["iran", "iraq", "turkey", "afghanistan", "pakistan", "usa"])
    ia.create_crisis(ids["iran"], "epidemic", severity="light", admin_id=1, force=True)

    start = ia._now()
    for day in range(5):
        moment = start + datetime.timedelta(days=day)
        for cid in ids.values():
            ia.run_daily_cycle(database.get_country_by_id(cid), None, now_dt=moment)
            _run_slots(cid, moment)

    infected = [
        key for key, cid in ids.items()
        if [c for c in ia.get_active_crises(cid) if c["crisis_key"] == "epidemic"]
    ]
    assert len(infected) > 1, "اپیدمی باید به همسایه‌ها سرایت کند"
    assert "usa" not in infected, "آمریکا با ایران هم‌مرز نیست"
    spread = [
        c for cid in ids.values() for c in ia.get_crisis_history(cid, 20)
        if c["origin"] == "spread"
    ]
    assert spread, "بحران‌های سرایتی باید origin=spread داشته باشند"


def test_a_light_epidemic_does_not_spread(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    ids = _border_world(database, ["iran", "iraq", "turkey"])
    _ok, _m, crisis = ia.create_crisis(ids["iran"], "epidemic", severity="light", admin_id=1, force=True)

    # بدون گذشت شب، هنوز خفیف است
    assert ia._spread_to_neighbours(ia.get_crisis(crisis["id"]), ia._now()) == []


def test_containing_an_epidemic_stops_the_spread(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    ia.random.seed(7)
    ids = _border_world(database, ["iran", "iraq", "turkey", "afghanistan", "pakistan"], treasury=500_000_000)
    for cid in ids.values():
        database.update_country_field(cid, "tech_level", 5)
        database.update_country_field(cid, "microchips", 9_000)
    ia.create_crisis(ids["iran"], "epidemic", severity="light", admin_id=1, force=True)

    start = ia._now()
    for day in range(5):
        moment = start + datetime.timedelta(days=day)
        for crisis in ia.get_active_crises(ids["iran"]):
            if crisis["crisis_key"] == "epidemic":
                for action in ("quarantine", "vaccine_program", "field_hospital"):
                    ia.respond_to_crisis(crisis["id"], action, actor_id=1)
        for cid in ids.values():
            ia.run_daily_cycle(database.get_country_by_id(cid), None, now_dt=moment)

    infected = [
        key for key, cid in ids.items()
        if [c for c in ia.get_active_crises(cid) if c["crisis_key"] == "epidemic"]
    ]
    assert infected == ["iran"], f"قرنطینه باید جلوی سرایت را بگیرد، ولی درگیر شدند: {infected}"


def test_spread_is_capped_per_night(monkeypatch, tmp_path):
    """کشوری با ۸ همسایه نباید در یک شب همه را آلوده کند."""
    database = _fresh_db(monkeypatch, tmp_path)
    ia.random.seed(1)
    neighbours = ia.neighbours_of("iran")
    ids = _border_world(database, ["iran"] + neighbours)
    _ok, _m, crisis = ia.create_crisis(ids["iran"], "epidemic", severity="severe", admin_id=1, force=True)

    spawned = ia._spread_to_neighbours(ia.get_crisis(crisis["id"]), ia._now())
    assert len(spawned) <= ia.MAX_SPREAD_PER_NIGHT


def test_only_contagious_crises_spread(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    ids = _border_world(database, ["iran", "iraq", "turkey"])
    _ok, _m, quake = ia.create_crisis(ids["iran"], "earthquake", severity="severe", admin_id=1, force=True)
    assert ia._spread_to_neighbours(ia.get_crisis(quake["id"]), ia._now()) == []
    assert "earthquake" not in ia.CONTAGIOUS_CRISES
    assert "epidemic" in ia.CONTAGIOUS_CRISES


def test_spread_news_names_the_source_country():
    crisis = {"crisis_key": "epidemic", "severity": "light", "stage": "warning",
              "mitigation": 0, "_from_name": "🇮🇷 ایران"}
    title, body = ia.build_news({"name": "عراق", "flag": "🇮🇶"}, crisis, "spread")
    assert "سرایت" in title and "عراق" in title
    assert "ایران" in body


# ─────────────────────────────────────────────────────────────────────────────
# واکسن به‌عنوان آیتم تولیدی، زمان‌بر و غیرقابل فروش
# ─────────────────────────────────────────────────────────────────────────────

def _vaccine_ready_country(database, doses=0, tech=3, treasury=400_000_000):
    cid = _country(database, approval=80)
    database.update_country_field(cid, "tech_level", tech)
    database.update_country_field(cid, "treasury", treasury)
    database.update_country_field(cid, "microchips", 9_000)
    database.update_country_field(cid, "medical_isotopes", 200)
    if doses:
        database.update_country_field(cid, "vaccine_doses", doses)
    return cid


def test_vaccine_needs_tech_three_plus_chips(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _vaccine_ready_country(database, tech=2)

    ok, reason, _n = ia.can_start_vaccine(database.get_country_by_id(cid), 1)
    assert not ok and "فناوری" in reason
    assert ia.VACCINE_MIN_TECH_LEVEL == 3

    database.update_country_field(cid, "tech_level", 3)
    database.update_country_field(cid, "microchips", 0)
    ok, reason, _n = ia.can_start_vaccine(database.get_country_by_id(cid), 1)
    assert not ok and "میکروچیپ" in reason

    database.update_country_field(cid, "microchips", 9_000)
    ok, reason, _n = ia.can_start_vaccine(database.get_country_by_id(cid), 1)
    assert ok, f"با فناوری و چیپ کافی باید ممکن باشد: {reason}"


def test_vaccine_production_takes_at_least_three_days(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _vaccine_ready_country(database)

    assert ia.vaccine_requirements(1)["days"] >= 3
    assert ia.vaccine_requirements(6)["days"] > ia.vaccine_requirements(1)["days"]

    ok, message, _p = ia.start_vaccine_project(cid, 1, actor_id=1)
    assert ok, message
    start = ia._now()

    for day in (1, 2):
        assert ia.collect_ready_vaccines(cid, start + datetime.timedelta(days=day)) == 0
        assert database.get_country_by_id(cid)["vaccine_doses"] == 0

    delivered = ia.collect_ready_vaccines(cid, start + datetime.timedelta(days=3, hours=1))
    assert delivered == ia.VACCINE_BATCH_DOSES
    assert database.get_country_by_id(cid)["vaccine_doses"] == ia.VACCINE_BATCH_DOSES


def test_starting_a_project_consumes_resources_immediately(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _vaccine_ready_country(database)
    before = database.get_country_by_id(cid)

    ok, _msg, _p = ia.start_vaccine_project(cid, 3, actor_id=1)
    assert ok
    after = database.get_country_by_id(cid)
    assert after["treasury"] < before["treasury"]
    assert after["microchips"] < before["microchips"]
    assert after["vaccine_doses"] == 0, "دُز فقط بعد از اتمام زمان تحویل می‌شود"


def test_only_one_vaccine_project_at_a_time(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _vaccine_ready_country(database)
    assert ia.start_vaccine_project(cid, 1, actor_id=1)[0]
    ok, message, _p = ia.start_vaccine_project(cid, 1, actor_id=1)
    assert not ok and "در حال تولید" in message


def test_vaccine_action_requires_stock_and_consumes_it(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _vaccine_ready_country(database, doses=0)
    _ok, _m, crisis = ia.create_crisis(cid, "epidemic", admin_id=1)

    ok, reason = ia.check_action("vaccine_program", crisis, database.get_country_by_id(cid))
    assert not ok and "واکسن" in reason

    database.update_country_field(cid, "vaccine_doses", ia.VACCINE_DOSES_PER_USE)
    ok, _msg, _i = ia.respond_to_crisis(crisis["id"], "vaccine_program", actor_id=1)
    assert ok
    assert database.get_country_by_id(cid)["vaccine_doses"] == 0


def test_vaccine_doses_are_tradeable_on_the_commodity_market():
    """واکسن باید در بورس کالا قابل خرید و فروش باشد."""
    assert "vaccine_doses" in config.COMMODITY_MARKET_BOUNDS
    bounds = config.COMMODITY_MARKET_BOUNDS["vaccine_doses"]
    assert bounds["min_price"] > 0 and bounds["max_price"] > bounds["min_price"]
    for mode in ("sea", "land", "air"):
        assert config.TRANSPORT_CAPACITY_LIMITS[mode]["limits"].get("vaccine_doses", 0) > 0


def test_market_and_aid_know_the_vaccine_column():
    import inspect
    from handlers import market

    source = inspect.getsource(database_module())
    assert source.count('"vaccine_doses": "vaccine_doses"') >= 3, (
        "بازار، کمک خارجی و معاوضه هر سه باید ستون واکسن را بشناسند"
    )
    assert "vaccine_doses" in inspect.getsource(market)


def database_module():
    import database
    return database


# ─────────────────────────────────────────────────────────────────────────────
# سقف مهار
# ─────────────────────────────────────────────────────────────────────────────

def test_mitigation_cap_is_eighty_until_a_strategic_action(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _vaccine_ready_country(database, doses=ia.VACCINE_DOSES_PER_USE, treasury=900_000_000)
    _ok, _m, crisis = ia.create_crisis(cid, "epidemic", severity="severe", admin_id=1)

    assert ia.mitigation_cap(ia.get_crisis(crisis["id"])) == ia.BASE_MITIGATION_CAP

    base = ia._now()
    for day in range(4):
        monkeypatch.setattr(ia, "_today", lambda dt=None, d=day: ia._iso(base + datetime.timedelta(days=d))[:10])
        for action in ia.available_actions(ia.get_crisis(crisis["id"])):
            if action != "vaccine_program":
                ia.respond_to_crisis(crisis["id"], action, actor_id=1)
    assert float(ia.get_crisis(crisis["id"])["mitigation"]) <= ia.BASE_MITIGATION_CAP + 1e-9

    monkeypatch.setattr(ia, "_today", lambda dt=None: ia._iso(base + datetime.timedelta(days=9))[:10])
    ok, message, _i = ia.respond_to_crisis(crisis["id"], "vaccine_program", actor_id=1)
    assert ok, message
    refreshed = ia.get_crisis(crisis["id"])
    assert ia.mitigation_cap(refreshed) == 0.95
    assert float(refreshed["mitigation"]) > ia.BASE_MITIGATION_CAP


def test_mitigation_never_reaches_one_hundred_percent():
    assert ia.MAX_MITIGATION_CAP < 1.0
    for action in ia.CRISIS_ACTIONS.values():
        assert float(action.get("raises_cap", 0) or 0) <= ia.MAX_MITIGATION_CAP


# ─────────────────────────────────────────────────────────────────────────────
# جای‌گذاری منوها: واکسن در مرکز تحقیقات، بحران‌ها در سیاست داخلی
# ─────────────────────────────────────────────────────────────────────────────

def test_research_centre_hosts_the_vaccine_programme():
    import inspect
    from handlers import research

    source = inspect.getsource(research.research_menu)
    assert "برنامه واکسن" in source
    assert "dom:vaccine" in source, "دکمه باید به همان صفحه‌ی واحد واکسن برود"
    assert "VACCINE_MIN_TECH_LEVEL" in source, "سطح فناوری لازم باید نمایش داده شود"
    assert "dom:menu" in source, "میان‌بر سیاست داخلی هم باید باشد"


def test_country_profile_links_to_domestic_politics():
    import inspect
    from handlers import country as country_handlers

    source = inspect.getsource(country_handlers.country_profile)
    assert "dom:menu" in source
    assert "سیاست داخلی" in source


def test_domestic_menu_is_the_single_crisis_hub():
    import inspect
    from handlers import internal_affairs as domestic

    source = inspect.getsource(domestic._menu_keyboard)
    for target in ("dom:population", "dom:tax", "dom:unrest", "dom:crises",
                   "dom:actions", "dom:vaccine", "dom:readiness", "dom:trend", "dom:history"):
        assert target in source, f"{target} باید در منوی سیاست داخلی باشد"


def test_readiness_page_reflects_country_geography(monkeypatch, tmp_path):
    import asyncio
    from handlers.internal_affairs import _readiness_page

    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database, key="iran")
    database.update_country_field(cid, "grain", 10)
    database.update_country_field(cid, "tech_level", 2)

    class FakeQuery:
        async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
            self.text = text

        async def answer(self, *a, **k):
            pass

    query = FakeQuery()
    asyncio.run(_readiness_page(query, database.get_country_by_id(cid), ia.get_state(cid)))
    assert "خشکسالی" in query.text and "زلزله" in query.text
    assert "⚠️" in query.text, "کمبود ذخایر باید هشدار بگیرد"
    assert str(ia.VACCINE_MIN_TECH_LEVEL) in query.text


def test_academy_documents_the_crisis_and_vaccine_systems():
    """دانشکده باید سیستم جدید را آموزش بدهد، وگرنه بازیکن‌ها نمی‌فهمندش."""
    import inspect
    from handlers import guide

    keyboard_source = inspect.getsource(guide.get_guide_main_keyboard)
    assert "help:cat:domestic" in keyboard_source
    assert "help:cat:vaccine" in keyboard_source

    handler_source = inspect.getsource(guide.guide_callback_handler)
    assert 'cat == "domestic"' in handler_source
    assert 'cat == "vaccine"' in handler_source
    # میان‌بر به خود سیستم، نه فقط متن
    assert "dom:menu" in handler_source
    assert "dom:vaccine" in handler_source
    assert "dom:readiness" in handler_source


def test_academy_numbers_come_from_the_engine_not_hardcoded():
    """اگر ضریبی عوض شود، متن دانشکده هم باید خودکار عوض شود."""
    import inspect
    from handlers import guide

    source = inspect.getsource(guide.guide_callback_handler)
    assert "ia.BASE_MITIGATION_CAP" in source
    assert "ia.MAX_MITIGATION_CAP" in source
    assert "ia.VACCINE_MIN_TECH_LEVEL" in source
    assert "ia.vaccine_requirements" in source


# ─────────────────────────────────────────────────────────────────────────────
# مهار: بحران پایین می‌آید و در نهایت حذف می‌شود
# ─────────────────────────────────────────────────────────────────────────────

def test_two_nights_above_eighty_percent_resolves_the_crisis(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "treasury", 900_000_000)
    database.update_country_field(cid, "tech_level", 5)
    database.update_country_field(cid, "vaccine_doses", 200_000)
    _ok, _m, crisis = ia.create_crisis(cid, "epidemic", severity="severe", admin_id=1, force=True)
    ia.force_impact(crisis["id"], admin_id=1)

    start = ia._now()
    for day in range(2):
        for action in ("vaccine_program", "quarantine", "field_hospital", "emergency_aid"):
            ia.respond_to_crisis(crisis["id"], action, actor_id=1)
        ia.run_daily_cycle(database.get_country_by_id(cid), None, now_dt=start + datetime.timedelta(days=day))

    final = ia.get_crisis(crisis["id"])
    assert final["stage"] == "ended"
    assert final["outcome"] == "contained"
    assert final["contained_days"] >= ia.CONTAINMENT_DAYS_TO_RESOLVE


def test_one_night_of_containment_is_not_enough(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "treasury", 900_000_000)
    database.update_country_field(cid, "tech_level", 5)
    database.update_country_field(cid, "vaccine_doses", 200_000)
    _ok, _m, crisis = ia.create_crisis(cid, "epidemic", severity="severe", admin_id=1, force=True)
    ia.force_impact(crisis["id"], admin_id=1)

    for action in ("vaccine_program", "quarantine", "field_hospital", "emergency_aid"):
        ia.respond_to_crisis(crisis["id"], action, actor_id=1)
    _run(cid, days=1)

    assert ia.get_crisis(crisis["id"])["stage"] != "ended"
    assert ia.get_crisis(crisis["id"])["contained_days"] == 1


def test_moderate_containment_steps_the_crisis_down(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "treasury", 900_000_000)
    _ok, _m, crisis = ia.create_crisis(cid, "earthquake", severity="severe", admin_id=1, force=True)
    ia.force_impact(crisis["id"], admin_id=1)

    start = ia._now()
    levels = []
    for day in range(3):
        current = ia.get_crisis(crisis["id"])
        if current["stage"] != "ended" and float(current["mitigation"]) < 0.55:
            ia.respond_to_crisis(crisis["id"], "search_rescue", actor_id=1)
            ia.respond_to_crisis(crisis["id"], "emergency_aid", actor_id=1)
        moment = start + datetime.timedelta(days=day)
        ia.run_daily_cycle(database.get_country_by_id(cid), None, now_dt=moment)
        _run_slots(cid, moment)
        levels.append(ia.get_crisis(crisis["id"])["severity"])

    assert levels[0] == "medium", "مهار متوسط باید شدت را یک پله پایین بیاورد"
    assert levels[-1] == "light"


def test_containment_counter_resets_if_the_country_stops(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "treasury", 900_000_000)
    database.update_country_field(cid, "tech_level", 5)
    database.update_country_field(cid, "vaccine_doses", 200_000)
    _ok, _m, crisis = ia.create_crisis(cid, "epidemic", severity="severe", admin_id=1, force=True)
    ia.force_impact(crisis["id"], admin_id=1)

    for action in ("vaccine_program", "quarantine", "field_hospital", "emergency_aid"):
        ia.respond_to_crisis(crisis["id"], action, actor_id=1)
    _run(cid, days=1)
    assert ia.get_crisis(crisis["id"])["contained_days"] == 1

    # مهار را دستی پایین می‌آوریم (انگار اثر اقدامات تمام شده)
    conn = database.get_connection()
    with conn:
        conn.execute("UPDATE country_crises SET mitigation = 0.1 WHERE id = ?", (crisis["id"],))
    conn.close()

    _run(cid, days=1, start=ia._now() + datetime.timedelta(days=1))
    assert ia.get_crisis(crisis["id"])["contained_days"] == 0


# ─────────────────────────────────────────────────────────────────────────────
# بالانس خسارت
# ─────────────────────────────────────────────────────────────────────────────

def test_single_day_casualties_stay_plausible():
    """یک ضربه نباید صدها هزار نفر بکشد."""
    population = 50_000_000
    worst = ia.SEVERITY_FACTORS["severe"]
    for key, spec in ia.CRISIS_CATALOG.items():
        deaths = population * float(spec["effects"].get("pop", 0)) * worst
        assert deaths <= population * 0.0015, f"{key} تلفات غیرمنطقی: {int(deaths):,}"


def test_crisis_never_wipes_out_a_treasury_or_income_in_one_hit():
    for key, spec in ia.CRISIS_CATALOG.items():
        effects = spec["effects"]
        assert float(effects.get("treasury", 0)) * 1.8 <= 0.10, f"{key} خزانه را زیادی می‌زند"
        assert float(effects.get("income", 0)) * 1.8 <= 0.20, f"{key} درآمد را زیادی می‌زند"


def test_income_loss_is_temporary_and_returns_when_the_crisis_ends(monkeypatch, tmp_path):
    """رگرسیون: افت درآمد روزانه دائمی بود و هرگز برنمی‌گشت."""
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "daily_income", 5_000_000)
    database.update_country_field(cid, "treasury", 200_000_000)
    _ok, _m, crisis = ia.create_crisis(cid, "economic_collapse", severity="severe", admin_id=1, force=True)
    ia.force_impact(crisis["id"], admin_id=1)

    during = database.get_country_by_id(cid)["daily_income"]
    assert during < 5_000_000, "بحران باید درآمد را موقتاً کم کند"

    assert ia.end_crisis(crisis["id"], admin_id=1)[0]
    assert database.get_country_by_id(cid)["daily_income"] == 5_000_000


# ─────────────────────────────────────────────────────────────────────────────
# بالانس نهایی: هزینه واکسن و نرخ مرگ‌ومیر واقعی
# ─────────────────────────────────────────────────────────────────────────────

def test_vaccine_no_longer_needs_enriched_isotopes(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "tech_level", 3)
    database.update_country_field(cid, "treasury", 200_000_000)
    database.update_country_field(cid, "microchips", 5_000)
    database.update_country_field(cid, "medical_isotopes", 0)

    assert ia.VACCINE_ISOTOPES_PER_BATCH == 0
    ok, reason, _n = ia.can_start_vaccine(database.get_country_by_id(cid), 1)
    assert ok, f"ایزوتوپ نباید دیگر لازم باشد: {reason}"


def test_vaccine_total_cost_is_about_eighty_five_million():
    need = ia.vaccine_requirements(1)
    chip_value = need["microchips"] * 15_000
    total = need["cost"] + chip_value
    assert 80_000_000 <= total <= 90_000_000, f"جمع کل باید حدود ۸۵ میلیون باشد، شد {total:,}"
    assert sum(ia.VACCINE_COST_BREAKDOWN.values()) == ia.VACCINE_COST_PER_BATCH
    assert len(ia.VACCINE_COST_BREAKDOWN) >= 3, "هزینه باید تفکیک‌شده باشد"


def test_daily_deaths_match_real_pandemic_scale():
    """اوج کرونا بین ۰.۰۰۰۸٪ و ۰.۰۰۲٪ جمعیت در روز بود."""
    population = 50_000_000
    epidemic = ia.CRISIS_CATALOG["epidemic"]["effects"]["pop"]
    deaths_medium = population * epidemic
    deaths_severe = deaths_medium * ia.SEVERITY_FACTORS["severe"]

    assert 300 <= deaths_medium <= 1_500, f"اپیدمی متوسط: {int(deaths_medium):,}"
    assert deaths_severe <= 2_500, f"اپیدمی شدید: {int(deaths_severe):,}"
    # نسبت جمعیتی در بازه‌ی واقعی
    assert 0.0000060 <= epidemic <= 0.0000250


def test_slow_disasters_kill_less_per_day_than_a_sudden_one():
    """قحطی و خشکسالی تدریجی‌اند؛ زلزله یک رویداد آنی و مرگبار است."""
    effects = {key: spec["effects"].get("pop", 0) for key, spec in ia.CRISIS_CATALOG.items()}
    assert effects["earthquake"] > effects["epidemic"]
    assert effects["earthquake"] > effects["famine"]
    assert effects["drought"] < effects["famine"]
    assert effects["wildfire"] < effects["flood"]


# ─────────────────────────────────────────────────────────────────────────────
# اسپم اخبار کانال
# ─────────────────────────────────────────────────────────────────────────────

def _many_crises_world(database, count=15):
    keys = list(ia.CRISIS_CATALOG)
    ids = []
    for index in range(count):
        cid = database.create_country(8600 + index, f"کشور{index}", "🏳️", country_key=f"nw{index}")
        database.update_country_field(cid, "approval_rating", 70)
        database.update_country_field(cid, "treasury", 50_000_000)
        ia.create_crisis(cid, keys[index % len(keys)], severity="light", admin_id=1, force=True)
        ids.append(cid)
    return ids


def _one_cycle_news(database, ids):
    now = ia._now()
    batch = []
    for cid in ids:
        cycle = ia.run_daily_cycle(database.get_country_by_id(cid), None, now_dt=now)
        if cycle:
            batch.extend(ia.collect_news(database.get_country_by_id(cid), cycle))
        slot_events = ia.run_crisis_slot_cycle(database.get_country_by_id(cid), now)
        if slot_events:
            batch.extend(ia.collect_slot_news(database.get_country_by_id(cid), slot_events))
    return batch


def test_default_news_mode_only_reports_severity_changes(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    ids = _many_crises_world(database)
    batch = _one_cycle_news(database, ids)

    assert ia.news_mode() == "severity"
    assert len(batch) > 20, "چرخه واقعاً ده‌ها رویداد تولید می‌کند"

    published = [i for i in batch if i["event"] in ia.SEVERITY_EVENTS]
    assert published, "تغییر سطح باید منتشر شود"
    assert all(i["event"] in ia.SEVERITY_EVENTS for i in published)
    # رویدادهای پرحجم مثل impact و damage به کانال نمی‌روند
    assert any(i["event"] == "impact" for i in batch)
    assert not any(i["event"] == "impact" for i in published)


def test_a_busy_cycle_collapses_into_one_digest(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    ids = _many_crises_world(database)
    batch = [i for i in _one_cycle_news(database, ids) if i["event"] in ia.SEVERITY_EVENTS]

    assert len(batch) > ia.NEWS_DIGEST_THRESHOLD
    digest = ia.build_news_digest(batch)
    assert digest is not None
    title, body = digest
    assert "بحران" in title and "روزنامه" in title
    assert "🗓" in body
    for item in batch[:3]:
        assert (item["country"].get("name") or "") in body


def test_news_mode_can_be_switched_and_off_publishes_nothing(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    assert ia.set_news_mode("all") and ia.news_mode() == "all"
    assert ia.set_news_mode("off") and ia.news_mode() == "off"
    assert not ia.set_news_mode("nonsense")
    assert ia.news_mode() == "off"
    ia.set_news_mode("severity")


def test_collect_news_does_not_mark_anything_as_sent(monkeypatch, tmp_path):
    """ساخت خبر نباید آن را «ارسال‌شده» علامت بزند، وگرنه فیلترشده‌ها گم می‌شوند."""
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    _ok, _m, crisis = ia.create_crisis(cid, "flood", severity="light", admin_id=1, force=True)
    cycle = ia.run_daily_cycle(database.get_country_by_id(cid), None)

    first = ia.collect_news(database.get_country_by_id(cid), cycle)
    second = ia.collect_news(database.get_country_by_id(cid), cycle)
    assert first and len(first) == len(second), "تا ارسال نشده، باید دوباره ساخته شود"

    ia.mark_news_sent(first[0]["crisis_id"], first[0]["flag"])
    third = ia.collect_news(database.get_country_by_id(cid), cycle)
    assert len(third) == len(first) - 1


def test_player_is_notified_privately_even_when_channel_is_quiet():
    import inspect
    import main as main_module

    source = inspect.getsource(main_module._notify_crisis_owner)
    assert "player_id" in source and "send_message" in source
    job = inspect.getsource(main_module.daily_income_job)
    assert "_notify_crisis_owner" in job
    assert "crisis_news_batch" in job, "اخبار باید تجمیع شوند نه کشور به کشور ارسال"

    publisher = inspect.getsource(main_module._publish_crisis_news)
    assert "news_mode" in publisher and "build_news_digest" in publisher


# ─────────────────────────────────────────────────────────────────────────────
# کمبود برق، تولید صنعتی را می‌خواباند
# ─────────────────────────────────────────────────────────────────────────────

def _industrial_country(database):
    cid = _country(database)
    for key, count in (("small_factory", 10), ("large_factory", 6),
                       ("industrial_complex", 4), ("oil_refinery", 3), ("gold_mine", 2)):
        database.add_equipment(cid, key, count)
    return cid


def test_enough_power_means_no_shutdown(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _industrial_country(database)
    database.update_country_field(cid, "electricity", 250)

    power = ia.power_status(database.get_country_by_id(cid))
    assert not power["shortage"]
    assert power["offline"] == {}
    assert power["income_lost"] == 0


def test_power_shortage_shuts_units_down_and_costs_income(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _industrial_country(database)
    database.update_country_field(cid, "electricity", 132)

    power = ia.power_status(database.get_country_by_id(cid))
    assert power["shortage"]
    assert sum(power["offline"].values()) > 0
    assert power["income_lost"] > 0
    # مصرف واحدهای روشن نباید از بودجه‌ی برق بیشتر باشد
    used = sum(ia.POWER_CONSUMERS[k] * v for k, v in power["online"].items())
    assert used <= power["industrial_budget"]


def test_the_grid_keeps_the_most_efficient_units_running(monkeypatch, tmp_path):
    """اپراتور عاقل بیشترین درآمد را از برق محدود بیرون می‌کشد."""
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _industrial_country(database)
    database.update_country_field(cid, "electricity", 120)

    power = ia.power_status(database.get_country_by_id(cid))
    shop = config.ALL_SHOP_ITEMS

    # پربازده‌ترین نوع باید کامل روشن بماند
    best = max(ia.POWER_CONSUMERS, key=lambda k: shop.get(k, {}).get("income_add", 0) / ia.POWER_CONSUMERS[k]
               if k in shop else 0)
    assert power["online"].get("gold_mine") == 2, "معدن طلا پربازده‌ترین است و باید کامل روشن بماند"

    # تخصیص باید بهتر از «خاموش‌کردن کورکورانه‌ی پرمصرف‌ها» باشد
    budget = power["industrial_budget"]
    naive_income, remaining = 0, budget
    for key in sorted(ia.POWER_CONSUMERS, key=lambda k: ia.POWER_CONSUMERS[k]):
        count = int((database.get_equipment(cid) or {}).get(key) or 0)
        if not count:
            continue
        fit = min(count, remaining // ia.POWER_CONSUMERS[key])
        remaining -= fit * ia.POWER_CONSUMERS[key]
        naive_income += fit * shop[key]["income_add"]

    smart_income = sum(shop[k]["income_add"] * v for k, v in power["online"].items())
    assert smart_income >= naive_income, "تخصیص باید حداقل به‌اندازه‌ی حالت ساده بازده داشته باشد"

    # و برق مصرف‌شده هرگز از بودجه بیشتر نشود
    assert sum(ia.POWER_CONSUMERS[k] * v for k, v in power["online"].items()) <= budget


def test_deeper_shortage_shuts_down_more(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _industrial_country(database)

    losses = []
    for electricity in (166, 140, 120, 100):
        database.update_country_field(cid, "electricity", electricity)
        losses.append(ia.power_status(database.get_country_by_id(cid))["income_lost"])
    assert losses == sorted(losses), "هرچه برق کمتر، افت درآمد بیشتر"
    assert losses[0] == 0 and losses[-1] > 0


def test_power_penalty_is_off_until_an_admin_enables_it(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "power_off.db"))
    db.init_db()
    assert ia.power_penalty_enabled() is False
    ia.set_power_penalty(True)
    assert ia.power_penalty_enabled() is True


def test_payout_uses_the_power_penalty_without_touching_stored_income():
    """درآمد ذخیره‌شده نباید دست بخورد — فقط پرداختِ همان دوره کم می‌شود."""
    import inspect
    import main as main_module

    source = inspect.getsource(main_module.daily_income_job)
    assert "power_penalty_enabled" in source
    assert "power_status" in source
    assert "daily_income = max(0, daily_income - power[\"income_lost\"])" in source
    # هیچ نوشتنی روی ستون daily_income در این مسیر نباشد
    segment = source[source.index("power_note = \"\""):source.index("gross_income = daily_income")]
    assert "update_country_field" not in segment


def test_one_batch_covers_at_least_four_vaccination_campaigns():
    """نسبت به هزینه‌ی ۸۵ میلیونی، یک واحد باید چند بار به کار بیاید."""
    need = ia.vaccine_requirements(1)
    uses = need["doses"] // ia.VACCINE_DOSES_PER_USE
    assert uses >= 4, f"کوچک‌ترین پروژه فقط {uses} بار تزریق می‌دهد"
    assert uses == ia.VACCINE_USES_PER_BATCH
    assert ia.VACCINE_BATCH_DOSES == ia.VACCINE_USES_PER_BATCH * ia.VACCINE_DOSES_PER_USE

    chip_value = need["microchips"] * 15_000
    per_use = (need["cost"] + chip_value) / uses
    assert per_use <= 25_000_000, f"هزینه‌ی هر تزریق هنوز زیاد است: {int(per_use):,}"


def test_bigger_projects_scale_uses_linearly():
    small = ia.vaccine_requirements(1)
    big = ia.vaccine_requirements(ia.VACCINE_MAX_BATCHES)
    assert big["doses"] == small["doses"] * ia.VACCINE_MAX_BATCHES
    per_use_small = (small["cost"] + small["microchips"] * 15_000) / (small["doses"] // ia.VACCINE_DOSES_PER_USE)
    per_use_big = (big["cost"] + big["microchips"] * 15_000) / (big["doses"] // ia.VACCINE_DOSES_PER_USE)
    assert abs(per_use_small - per_use_big) < 1, "هزینه‌ی هر تزریق باید مستقل از اندازه‌ی پروژه باشد"


def test_ui_never_hardcodes_the_batch_size():
    """رگرسیون: عنوان «۵۰ هزار دُز» بعد از تغییر اندازه‌ی واحد، غلط مانده بود."""
    import inspect
    from handlers import internal_affairs as domestic, guide

    for module in (domestic, guide):
        source = inspect.getsource(module)
        assert "۵۰ هزار دُز" not in source, f"{module.__name__} اندازه‌ی واحد را دستی نوشته"
