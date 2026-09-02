# -*- coding: utf-8 -*-
"""موتور شورش مسلحانه — ترکیدن، چرخه‌ی شبانه‌ی بات، سرکوب، مذاکره، فینال و سقوط.

قواعد کلی که این تست‌ها قفل می‌کنند:
* همه‌چیز پشت کلید insurgency_enabled است (پیش‌فرض خاموش).
* ترکیدن خودکار فقط با collapse_risk و برای کشورِ دارای بازیکن.
* همه‌ی اعداد تصادفی بذردارند → قابل بازتولید.
* مرگ فرمانده ممنوع؛ فقط گروگان.
"""

import asyncio
import datetime

import pytest

import config
import database as db
import internal_affairs as ia
import insurgency
import news_engine


def _fresh(monkeypatch, tmp_path, name="ins.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()
    insurgency.set_enabled(True, admin_id=0, role="system")


def _country(player_id=71_001, key="testland", personnel=20_000, treasury=50_000_000,
             oil=1_000_000):
    cid = db.create_country(player_id, "کشور آزمون", "🏳️", country_key=key)
    db.update_country_field(cid, "active_personnel", personnel)
    db.update_country_field(cid, "treasury", treasury)
    db.update_country_field(cid, "oil_reserves", oil)
    ia.get_state(cid)  # اطمینان از ساخت ردیف country_internal
    db.seed_country_commanders(cid, key)
    return cid


def _cid_of(player_id):
    c = db.get_country_by_player(player_id)
    return int(c["id"])


def _tick(cid, date, cycle=None):
    country = db.get_country_by_id(cid)
    return insurgency.nightly_tick(country, date, cycle or {"collapse_risk": 1})


# ─────────────────────────────────────────────────────────────────────────────
# کلید و گیت‌های ترکیدن
# ─────────────────────────────────────────────────────────────────────────────

def test_feature_default_off(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "off.db"))
    db.init_db()
    assert insurgency.is_enabled() is False
    cid = _country()
    out = insurgency.nightly_tick(db.get_country_by_id(cid), "2026-09-01",
                                  {"collapse_risk": 1})
    assert out["events"] == [] and not out["collapse"]
    assert insurgency.get(cid) is None


def test_eruption_requires_collapse_risk(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country()
    out = insurgency.nightly_tick(db.get_country_by_id(cid), "2026-09-01",
                                  {"collapse_risk": 0})
    assert out["events"] == []
    assert insurgency.get(cid) is None


def test_eruption_requires_player(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country()
    db.update_country_field(cid, "player_id", 0)
    out = insurgency.nightly_tick(db.get_country_by_id(cid), "2026-09-01",
                                  {"collapse_risk": 1})
    assert insurgency.get(cid) is None


def test_eruption_deterministic_seed(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country()
    country = db.get_country_by_id(cid)
    r1 = insurgency.erupt(country, "2026-09-01", seed="fixed-seed", force=True)
    db.delete_insurgency(cid)
    r2 = insurgency.erupt(country, "2026-09-01", seed="fixed-seed", force=True)
    assert r1["fighters"] == r2["fighters"]
    gov = int(country["active_personnel"])
    assert gov * insurgency.POWER_MIN <= r1["fighters"] <= gov * insurgency.POWER_MAX


def test_eruption_chance_over_many_countries(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "chance.db")
    erupted = 0
    n = 40
    for i in range(n):
        cid = _country(player_id=72_000 + i, key=f"chance{i}")
        _tick(cid, "2026-09-01")
        if insurgency.get(cid):
            erupted += 1
    assert erupted >= 15, f"با شانس ۶۰٪ از {n} کشور، فقط {erupted} شورش بست"


def test_forced_eruption_bypasses_chance(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country()
    res = insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    assert res and insurgency.get(cid) is not None


def test_eruption_only_one_per_country(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country()
    assert insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    assert insurgency.erupt(db.get_country_by_id(cid), "2026-09-02", force=True) is None


# ─────────────────────────────────────────────────────────────────────────────
# چرخه‌ی شبانه
# ─────────────────────────────────────────────────────────────────────────────

def test_tick_idempotent_same_day(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country()
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    out1 = _tick(cid, "2026-09-02")
    night_after_first = insurgency.get(cid)["night"]
    _tick(cid, "2026-09-02")
    assert insurgency.get(cid)["night"] == night_after_first
    assert out1["report"], "خط وضعیت برای گزارش صبح باید تولید شود"


def test_idle_tick_grows_and_boldens(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country()
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    before = insurgency.get(cid)
    _tick(cid, "2026-09-02")
    after = insurgency.get(cid)
    assert after["fighters"] > before["fighters"]
    assert after["boldness"] == pytest.approx(before["boldness"] + insurgency.BOLDNESS_IDLE)
    assert after["night"] == before["night"] + 1
    state = ia.get_state(cid)
    assert float(state["unrest"]) >= insurgency.UNREST_FLOOR - 1e-6


def test_low_approval_fasters_rebel_growth(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid_a = _country(player_id=73_001, key="poor-a")
    cid_b = _country(player_id=73_002, key="rich-b")
    db.update_country_field(cid_a, "approval_rating", 10)
    db.update_country_field(cid_b, "approval_rating", 90)
    for cid in (cid_a, cid_b):
        insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", seed="same", force=True)
    a0 = insurgency.get(cid_a)["fighters"]
    b0 = insurgency.get(cid_b)["fighters"]
    _tick(cid_a, "2026-09-02")
    _tick(cid_b, "2026-09-02")
    ga = insurgency.get(cid_a)["fighters"] / a0
    gb = insurgency.get(cid_b)["fighters"] / b0
    assert ga > gb


def test_phase_escalation_by_power(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country(personnel=20_000)
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    conn = db.get_connection()
    with conn:
        conn.execute("UPDATE insurgencies SET fighters = ? WHERE country_id = ?",
                     (int(20_000 * 0.60), cid))
    _tick(cid, "2026-09-02")
    assert insurgency.phase_of(insurgency.get(cid)) == 3


def test_phase_escalation_by_night(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country()
    insurgency.erupt(db.get_country_by_id(cid), "2026-08-30", force=True)
    for i, day in enumerate(("2026-08-31", "2026-09-01", "2026-09-02")):
        _tick(cid, day)
    assert insurgency.phase_of(insurgency.get(cid)) >= 2


def test_escalation_event_emitted(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country(personnel=20_000)
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    conn = db.get_connection()
    with conn:
        conn.execute("UPDATE insurgencies SET fighters = ? WHERE country_id = ?",
                     (int(20_000 * 0.60), cid))
    out = _tick(cid, "2026-09-02")
    kinds = [e["kind"] for e in out["events"]]
    assert "escalation" in kinds


# ─────────────────────────────────────────────────────────────────────────────
# سرکوب
# ─────────────────────────────────────────────────────────────────────────────

def test_suppression_stalemate_when_outnumbered(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country(personnel=5_000)
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    conn = db.get_connection()
    with conn:
        conn.execute("UPDATE insurgencies SET fighters = 4_000 WHERE country_id = ?", (cid,))
    country = db.get_country_by_id(cid)
    res = insurgency.resolve_suppression(country, "light", "2026-09-02", seed="s1")
    assert res["ok"] and res["outcome"] == "stalemate"
    assert res["assigned"] < insurgency.SUPPRESSION_REQUIRED * 4_000
    after = insurgency.get(cid)
    assert after["boldness"] >= insurgency.BOLDNESS_START  # بن‌بست جسارت می‌دهد
    assert after["fighters"] < 4_000  # تلفات شورشی


def test_suppression_win_deducts_costs_and_personnel(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country(personnel=20_000)
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    conn = db.get_connection()
    with conn:
        conn.execute("UPDATE insurgencies SET fighters = 1_000 WHERE country_id = ?", (cid,))
    country = db.get_country_by_id(cid)
    treasury0 = int(country["treasury"])
    oil0 = int(country["oil_reserves"])
    personnel0 = int(country["active_personnel"])
    res = insurgency.resolve_suppression(country, "light", "2026-09-02", seed="win")
    assert res["ok"] and res["outcome"] == "win"
    after = db.get_country_by_id(cid)
    assert int(after["treasury"]) == treasury0 - res["cost"]
    assert int(after["oil_reserves"]) == oil0 - res["fuel"]
    assert int(after["active_personnel"]) == personnel0 - res["gov_kia"]
    ins = insurgency.get(cid)
    assert ins["fighters"] == res["fighters_left"] < 1_000
    assert ins["boldness"] == pytest.approx(insurgency.BOLDNESS_START + insurgency.BOLDNESS_WIN)
    assert res["injured_gov"] == int(res["gov_kia"] * 2.7)


def test_suppression_heavy_burns_approval_and_civilians(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country(personnel=20_000)
    db.update_country_field(cid, "approval_rating", 60)
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    conn = db.get_connection()
    with conn:
        conn.execute("UPDATE insurgencies SET fighters = 1_000 WHERE country_id = ?", (cid,))
    country = db.get_country_by_id(cid)
    res = insurgency.resolve_suppression(country, "heavy", "2026-09-02", seed="heavy1")
    assert res["ok"]
    assert res["civ"] >= insurgency.CIVILIAN_HEAVY[0]
    assert int(db.get_country_by_id(cid)["approval_rating"]) <= 60 - insurgency.HEAVY_APPROVAL_HIT[0]


def test_suppression_action_limit_per_night(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country(personnel=20_000)
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    conn = db.get_connection()
    with conn:
        conn.execute("UPDATE insurgencies SET fighters = 500 WHERE country_id = ?", (cid,))
    country = db.get_country_by_id(cid)
    r1 = insurgency.resolve_suppression(country, "light", "2026-09-02", seed="a")
    assert r1["ok"]
    r2 = insurgency.resolve_suppression(db.get_country_by_id(cid), "light", "2026-09-02", seed="b")
    assert r2["ok"]
    r3 = insurgency.resolve_suppression(db.get_country_by_id(cid), "light", "2026-09-02", seed="c")
    assert not r3["ok"] and r3["reason"] == "action_limit"


def test_suppression_refused_without_money(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country(personnel=20_000, treasury=0)
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    res = insurgency.resolve_suppression(db.get_country_by_id(cid), "light", "2026-09-02")
    assert not res["ok"] and res["reason"] == "no_money"


def test_phase_downgrade_after_suppression(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country(personnel=20_000)
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    conn = db.get_connection()
    with conn:
        conn.execute("UPDATE insurgencies SET fighters = 8_000, phase = 4 WHERE country_id = ?", (cid,))
    res = insurgency.resolve_suppression(db.get_country_by_id(cid), "wide", "2026-09-02", seed="down")
    assert res["ok"] and res["outcome"] == "win"
    assert res["fighters_left"] < insurgency.PHASE_DOWN_RATIO * 20_000
    assert insurgency.phase_of(insurgency.get(cid)) == 3


# ─────────────────────────────────────────────────────────────────────────────
# مذاکره و خیانت
# ─────────────────────────────────────────────────────────────────────────────

def test_negotiation_cuts_power_and_sets_cooldown(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country()
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    before = insurgency.get(cid)
    res = insurgency.resolve_negotiation(db.get_country_by_id(cid), "2026-09-02", seed="neg1")
    assert res["ok"]
    after = insurgency.get(cid)
    cut = 1 - after["fighters"] / before["fighters"]
    assert insurgency.NEGOTIATION_POWER_CUT[0] - 0.01 <= cut <= insurgency.NEGOTIATION_POWER_CUT[1] + 0.01
    assert after["neg_cooldown"] == insurgency.NEGOTIATION_COOLDOWN_NIGHTS
    assert int(db.get_country_by_id(cid)["treasury"]) == int(50_000_000 - res["cost"])


def test_negotiation_cooldown_blocks(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country()
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    assert insurgency.resolve_negotiation(db.get_country_by_id(cid), "2026-09-02", seed="n")["ok"]
    res = insurgency.resolve_negotiation(db.get_country_by_id(cid), "2026-09-03", seed="n")
    assert not res["ok"] and res["reason"] == "cooldown"


def test_negotiation_no_money(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country(treasury=0)
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    res = insurgency.resolve_negotiation(db.get_country_by_id(cid), "2026-09-02")
    assert not res["ok"] and res["reason"] == "no_money"


def test_truce_betrayal_happens_on_schedule(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country()
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    betrayal_night = None
    for s in range(60):
        res = insurgency.resolve_negotiation(db.get_country_by_id(cid), f"2026-09-0{2 + s % 7}", seed=f"b{s}")
        if res.get("ok") and res.get("betrayal_night"):
            betrayal_night = res["betrayal_night"]
            break
        if res.get("ok"):
            # کول‌داون را دستی صفر کن و دوباره امتحان کن
            conn = db.get_connection()
            with conn:
                conn.execute("UPDATE insurgencies SET neg_cooldown = 0 WHERE country_id = ?", (cid,))
    assert betrayal_night, "در ۶۰ امتحان باید حداقل یک خیانت زمان‌بندی می‌شد (۳۵٪)"
    # شب‌ها را جلو ببر تا به شب خیانت برسیم
    d = datetime.date(2026, 9, 10)
    while insurgency.get(cid)["night"] < betrayal_night:
        d += datetime.timedelta(days=1)
        _tick(cid, d.isoformat())
    before = insurgency.get(cid)["fighters"]
    d += datetime.timedelta(days=1)
    out = _tick(cid, d.isoformat())
    after = insurgency.get(cid)
    kinds = [e["kind"] for e in out["events"]]
    assert "betrayal" in kinds
    assert after["fighters"] > before
    assert after["boldness"] >= insurgency.BOLDNESS_BETRAYAL


# ─────────────────────────────────────────────────────────────────────────────
# فینال و سقوط
# ─────────────────────────────────────────────────────────────────────────────

def test_finale_win_leads_to_collapse(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country()
    pid = int(db.get_country_by_id(cid)["player_id"])
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    conn = db.get_connection()
    with conn:
        conn.execute("UPDATE insurgencies SET fighters = ?, phase = 4, boldness = 100"
                     " WHERE country_id = ?", (int(20_000 * 0.8), cid))
    out = None
    d = datetime.date(2026, 9, 2)
    for _ in range(120):
        out = _tick(cid, d.isoformat())
        if out.get("collapse"):
            break
        d += datetime.timedelta(days=1)
    assert out and out["collapse"], "با جسارت ۱۰۰ (شانس ۴۰٪) در ۱۲۰ شب باید فینال برد"
    collapsed = insurgency.execute_collapse(db.get_country_by_id(cid), d.isoformat())
    assert db.get_country_by_id(cid) is None
    assert insurgency.get(cid) is None
    assert collapsed["requeued"]
    import country_queue
    entry = country_queue.get_queue_entry(pid)
    assert entry and entry["status"] == "waiting"
    # لاگ سقوط برای داوری
    logs = db.get_admin_actions(limit=50)
    assert any(a["action"] == "insurgency_collapse" for a in logs)


def test_collapse_with_remaining_entity_switches_not_queues(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "ent.db")
    pid = 74_001
    cid = _country(player_id=pid, key="entland")
    db.create_custom_militia_faction(pid, "گروهک آزمون")
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    res = insurgency.execute_collapse(db.get_country_by_id(cid), "2026-09-02")
    assert not res["requeued"]
    assert db.get_setting(f"active_entity_{pid}") is not None
    assert db.get_country_by_id(cid) is None


def test_tick_after_country_deleted_is_safe(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country()
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    db.delete_insurgency(cid)
    db.delete_country_by_id(cid)
    out = insurgency.nightly_tick({"id": cid}, "2026-09-02", {"collapse_risk": 1})
    assert isinstance(out, dict)


# ─────────────────────────────────────────────────────────────────────────────
# گروگان (بدون مرگ)
# ─────────────────────────────────────────────────────────────────────────────

def test_hostage_taken_and_freed(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country(personnel=20_000)
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    title = db.insurgency_take_hostage(cid)
    assert title, "کشور آزمون باید فرمانده فعال داشته باشد"
    assert insurgency.get(cid)["commander_hostage"] == title
    conn = db.get_connection()
    with conn:
        conn.execute("UPDATE insurgencies SET fighters = 500 WHERE country_id = ?", (cid,))
    res = insurgency.resolve_suppression(db.get_country_by_id(cid), "light", "2026-09-02", seed="free")
    assert res["ok"] and res["outcome"] == "win"
    assert res["freed_hostage"] == title
    assert insurgency.get(cid)["commander_hostage"] == ""


# ─────────────────────────────────────────────────────────────────────────────
# خرابکاری، سقف خبر، خط وضعیت
# ─────────────────────────────────────────────────────────────────────────────

def test_sabotage_outage_disables_one_unit(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country()
    item_key = next(iter(config.ALL_SHOP_ITEMS))
    conn = db.get_connection()
    with conn:
        conn.execute("INSERT OR REPLACE INTO equipment (country_id, item_key, quantity)"
                     " VALUES (?, ?, 5)", (cid, item_key))
    db.insurgency_apply_effects(cid, outage_item=item_key)
    row = conn.execute("SELECT inactive_qty FROM equipment WHERE country_id = ? AND item_key = ?",
                       (cid, item_key)).fetchone()
    conn.close()
    assert int(row["inactive_qty"]) == 1


def test_news_budget_cap_and_reset(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert insurgency.news_budget_take("2026-09-01")
    assert insurgency.news_budget_take("2026-09-01")
    assert not insurgency.news_budget_take("2026-09-01")
    assert insurgency.news_budget_take("2026-09-01", force=True)  # سقوط معاف است
    assert insurgency.news_budget_take("2026-09-02")  # روز جدید = سقف نو


def test_news_budget_shared_between_countries(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "budget.db")
    insurgency.news_budget_take("2026-09-01")
    insurgency.news_budget_take("2026-09-01")
    assert not insurgency.news_budget_take("2026-09-01")


def test_status_line_contains_phase(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country()
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    line = insurgency.status_line(db.get_country_by_id(cid))
    assert "شورش" in line and "شب" in line


def test_insurgency_news_template_has_no_digits(monkeypatch, tmp_path):
    ev = {"kind": "street_blockade", "seed": 42, "country_name": "زیستان",
          "country_flag": "🏳️", "phase": 1}
    sent = []

    class FakeBot:
        async def send_message(self, chat_id, text, parse_mode=None):
            sent.append(text)

    monkeypatch.setattr(config, "get_channel_id", lambda: -100123)
    asyncio.run(news_engine.trigger_insurgency_news(FakeBot(), ev))
    assert sent and "زیستان" in sent[0]
    import re as _re
    assert not _re.search(r"\d", sent[0]), "خبر شورش نباید عدد دقیق داشته باشد"


def test_suppression_preview_matches_assign_table(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country(personnel=10_000)
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    prev = insurgency.suppression_preview(db.get_country_by_id(cid), "wide")
    assert prev["assigned"] == 7_000
    assert prev["required"] == int(insurgency.SUPPRESSION_REQUIRED * insurgency.get(cid)["fighters"])


# ─────────────────────────────────────────────────────────────────────────────
# حمله‌های دوره‌ای ۶ ساعته (گرید پرداخت خزانه) + تدابیر امنیتی
# ─────────────────────────────────────────────────────────────────────────────

def _slot_setup(monkeypatch, tmp_path, name="slotrun.db", phase_fighters=None):
    _fresh(monkeypatch, tmp_path, name)
    cid = _country(personnel=20_000)
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    if phase_fighters:
        conn = db.get_connection()
        with conn:
            conn.execute("UPDATE insurgencies SET fighters = ? WHERE country_id = ?",
                         (phase_fighters, cid))
    return cid


def test_slot_pool_phase_gating():
    pool1 = [k for k, _ in insurgency._slot_pool(1)]
    pool3 = [k for k, _ in insurgency._slot_pool(3)]
    assert "camp_raid" not in pool1, "اردوگاه فقط از فاز ۳"
    assert "grain_depot" in pool1 and "bank_raid" in pool1
    assert "camp_raid" in pool3 and "factory_raid" in pool3


def test_slot_tick_idempotent(monkeypatch, tmp_path):
    cid = _slot_setup(monkeypatch, tmp_path)
    grain0 = int(db.get_country_by_id(cid)["grain"])
    monkeypatch.setattr(insurgency, "SLOT_ATTACK_CHANCE", 1.0)
    monkeypatch.setattr(insurgency, "_pick_slot_op", lambda rng, phase: "grain_depot")
    insurgency.slot_tick(db.get_country_by_id(cid), "2026-09-02_1")
    mid = int(db.get_country_by_id(cid)["grain"])
    insurgency.slot_tick(db.get_country_by_id(cid), "2026-09-02_1")
    assert int(db.get_country_by_id(cid)["grain"]) == mid != grain0


def test_slot_attacks_happen_most_slots(monkeypatch, tmp_path):
    cid = _slot_setup(monkeypatch, tmp_path)
    attacks = 0
    for i in range(8):
        out = insurgency.slot_tick(db.get_country_by_id(cid), f"2026-09-1{i % 10}_{i % 4}")
        attacks += 1 if out["events"] else 0
    assert attacks >= 5, f"با شانس ۷۵٪ از ۸ دوره، فقط {attacks} حمله"


def test_grain_attack_reduces_grain(monkeypatch, tmp_path):
    cid = _slot_setup(monkeypatch, tmp_path)
    grain0 = int(db.get_country_by_id(cid)["grain"])
    monkeypatch.setattr(insurgency, "SLOT_ATTACK_CHANCE", 1.0)
    monkeypatch.setattr(insurgency, "_pick_slot_op", lambda rng, phase: "grain_depot")
    out = insurgency.slot_tick(db.get_country_by_id(cid), "2026-09-02_1")
    assert out["events"][0]["kind"] == "grain_depot"
    grain1 = int(db.get_country_by_id(cid)["grain"])
    assert grain0 * (1 - insurgency.GRAIN_RAID[1] - 0.001) <= grain1 < grain0


def test_fuel_attack_reduces_oil_and_hurts_guards(monkeypatch, tmp_path):
    cid = _slot_setup(monkeypatch, tmp_path)
    oil0 = int(db.get_country_by_id(cid)["oil_reserves"])
    p0 = int(db.get_country_by_id(cid)["active_personnel"])
    monkeypatch.setattr(insurgency, "SLOT_ATTACK_CHANCE", 1.0)
    monkeypatch.setattr(insurgency, "_pick_slot_op", lambda rng, phase: "fuel_depot")
    out = insurgency.slot_tick(db.get_country_by_id(cid), "2026-09-02_1")
    c = db.get_country_by_id(cid)
    assert out["events"][0]["kind"] == "fuel_depot"
    assert int(c["oil_reserves"]) < oil0
    assert int(c["active_personnel"]) < p0


def test_bank_raid_reduces_treasury(monkeypatch, tmp_path):
    cid = _slot_setup(monkeypatch, tmp_path)
    t0 = int(db.get_country_by_id(cid)["treasury"])
    monkeypatch.setattr(insurgency, "SLOT_ATTACK_CHANCE", 1.0)
    monkeypatch.setattr(insurgency, "_pick_slot_op", lambda rng, phase: "bank_raid")
    insurgency.slot_tick(db.get_country_by_id(cid), "2026-09-02_1")
    assert int(db.get_country_by_id(cid)["treasury"]) < t0


def test_factory_raid_disables_structure_unit(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "fac.db")
    cid = _country(personnel=20_000)
    item_key = next(iter(config.ALL_SHOP_ITEMS))
    conn = db.get_connection()
    with conn:
        conn.execute("INSERT OR REPLACE INTO equipment (country_id, item_key, quantity)"
                     " VALUES (?, ?, 3)", (cid, item_key))
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    monkeypatch.setattr(insurgency, "SLOT_ATTACK_CHANCE", 1.0)
    monkeypatch.setattr(insurgency, "_pick_slot_op", lambda rng, phase: "factory_raid")
    insurgency.slot_tick(db.get_country_by_id(cid), "2026-09-02_1")
    row = conn.execute("SELECT inactive_qty FROM equipment WHERE country_id = ? AND item_key = ?",
                       (cid, item_key)).fetchone()
    conn.close()
    assert int(row["inactive_qty"]) == 1


def test_guard_foils_attack_without_damage(monkeypatch, tmp_path):
    cid = _slot_setup(monkeypatch, tmp_path)
    db.insurgency_apply_effects(cid, guard_slots=4)
    grain0 = int(db.get_country_by_id(cid)["grain"])
    p0 = int(db.get_country_by_id(cid)["active_personnel"])
    monkeypatch.setattr(insurgency, "SLOT_ATTACK_CHANCE", 1.0)
    monkeypatch.setattr(insurgency, "GUARD_FOIL_CHANCE", 1.0)
    monkeypatch.setattr(insurgency, "_pick_slot_op", lambda rng, phase: "grain_depot")
    out = insurgency.slot_tick(db.get_country_by_id(cid), "2026-09-02_1")
    ev = out["events"][0]
    assert ev["kind"] == "foiled_raid" and ev["rebel_kia"] > 0
    assert int(db.get_country_by_id(cid)["grain"]) == grain0
    assert int(db.get_country_by_id(cid)["active_personnel"]) == p0
    ins = insurgency.get(cid)
    assert int(ins["guard_slots"]) == 3, "اعتبار تدابیر با هر دوره کم می‌شود"
    assert int(ins["fighters"]) < insurgency.get(cid)["fighters"] + ev["rebel_kia"]


def test_guard_costs_money_and_expires(monkeypatch, tmp_path):
    cid = _slot_setup(monkeypatch, tmp_path)
    t0 = int(db.get_country_by_id(cid)["treasury"])
    res = insurgency.resolve_guard(db.get_country_by_id(cid))
    assert res["ok"]
    assert int(db.get_country_by_id(cid)["treasury"]) == t0 - res["cost"]
    assert int(insurgency.get(cid)["guard_slots"]) == insurgency.GUARD_SLOTS
    # منقضی شدن بعد از ۴ دوره (بدون حمله)
    monkeypatch.setattr(insurgency, "SLOT_ATTACK_CHANCE", 0.0)
    for i in range(insurgency.GUARD_SLOTS):
        insurgency.slot_tick(db.get_country_by_id(cid), f"2026-09-1{i}_{i}")
    assert int(insurgency.get(cid)["guard_slots"]) == 0
    res2 = insurgency.resolve_guard(db.get_country_by_id(cid))
    assert res2["ok"]


def test_guard_refused_without_money(monkeypatch, tmp_path):
    cid = _slot_setup(monkeypatch, tmp_path)
    db.update_country_field(cid, "treasury", 0)
    res = insurgency.resolve_guard(db.get_country_by_id(cid))
    assert not res["ok"] and res["reason"] == "no_money"


def test_slot_news_budget_independent(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "slotnews.db")
    # سقف شبانه را پر کن — نباید روی دوره‌ای اثر بگذارد
    assert insurgency.news_budget_take("2026-09-02")
    assert insurgency.news_budget_take("2026-09-02")
    assert not insurgency.news_budget_take("2026-09-02")
    assert insurgency.news_budget_take_slot("2026-09-02_1")
    assert insurgency.news_budget_take_slot("2026-09-02_1")
    assert not insurgency.news_budget_take_slot("2026-09-02_1")
    assert insurgency.news_budget_take_slot("2026-09-02_2")  # دوره‌ی بعد = سقف نو


def test_slot_raid_news_has_no_digits():
    import re as _re
    for kind in ("grain_depot", "fuel_depot", "bank_raid", "factory_raid",
                 "camp_raid", "foiled_raid"):
        assert kind in news_engine._INS_TEMPLATES, f"قالب خبر {kind} نیست"
        for headline, body in news_engine._INS_TEMPLATES[kind]:
            assert not _re.search(r"\d", headline.format(name="زیستان")), kind
            assert not _re.search(r"\d", body.format(name="زیستان", flag="🏳️")), kind
