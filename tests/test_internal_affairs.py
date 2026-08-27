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


def test_same_response_cannot_be_used_twice(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    cid = _country(database)
    database.update_country_field(cid, "treasury", 200_000_000)
    _ok, _m, crisis = ia.create_crisis(cid, "flood", admin_id=1)

    assert ia.respond_to_crisis(crisis["id"], "emergency_aid", actor_id=1)[0]
    ok, message, _info = ia.respond_to_crisis(crisis["id"], "emergency_aid", actor_id=1)
    assert not ok
    assert "قبلاً" in message


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
