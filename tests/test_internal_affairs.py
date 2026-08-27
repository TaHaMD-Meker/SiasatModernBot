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
    """اجرای چند چرخه‌ی روزانه‌ی متوالی با تاریخ‌های متفاوت."""
    base = start or ia._now()
    results = []
    for offset in range(days):
        moment = base + datetime.timedelta(days=offset)
        results.append(ia.run_daily_cycle(db.get_country_by_id(cid), None, now_dt=moment))
    return results


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
    assert database.get_country_by_id(cid)["population"] < pop_before

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
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "treasury", 300_000_000)
    database.update_country_field(cid, "microchips", 5_000)
    database.update_country_field(cid, "tech_level", 2)
    _ok, _m, crisis = ia.create_crisis(cid, "epidemic", admin_id=1)

    ok, reason = ia.check_action("vaccine_program", crisis, database.get_country_by_id(cid))
    assert not ok and "فناوری" in reason
    ok, message, _i = ia.respond_to_crisis(crisis["id"], "vaccine_program", actor_id=1)
    assert not ok

    # کشور با فناوری کافی می‌تواند
    database.update_country_field(cid, "tech_level", 5)
    ok, message, info = ia.respond_to_crisis(crisis["id"], "vaccine_program", actor_id=1)
    assert ok, message
    assert database.get_country_by_id(cid)["microchips"] < 5_000, "واکسن باید میکروچیپ مصرف کند"


def test_vaccine_is_once_per_crisis(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "treasury", 900_000_000)
    database.update_country_field(cid, "microchips", 50_000)
    database.update_country_field(cid, "tech_level", 5)
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
