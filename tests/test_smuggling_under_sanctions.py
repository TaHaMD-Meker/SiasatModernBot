# -*- coding: utf-8 -*-
"""
قاچاق زیر تحریم: رسمی بسته می‌ماند، بازار سیاه سلاح سبک باز می‌ماند.
ریسک رهگیری: پایه ۲۵٪ — نقض تحریم تسلیحاتی سازمان ملل ۴۰٪ — تحریم دوجانبه ۳۵٪.
"""

import re
import pytest
import config
import database as db


def _fresh(monkeypatch, tmp_path, name):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()
    monkeypatch.setattr(db, "transfer_weight_enabled", lambda: False)


def _country(cur, cid, pid, name, key):
    cur.execute(
        "INSERT OR REPLACE INTO countries (id, player_id, name, flag, country_key, treasury, approval_rating) "
        "VALUES (?, ?, ?, '🏳️', ?, 100000000, 85)", (cid, pid, name, key))


def _asset(cur, cid, ckey, cat, name, ekey, amt):
    cur.execute("""
        INSERT INTO country_assets (country_id, country_key, category, equipment_name, equipment_key, amount, buy_price, maintenance_cost, producible)
        VALUES (?, ?, ?, ?, ?, ?, 100000, 500, 0)
        ON CONFLICT(country_id, equipment_key) DO UPDATE SET amount = ?
    """, (cid, ckey, cat, name, ekey, amt, amt))


LIGHT = ("Ground Forces", "تیم ضدزره کورنت (Kornet-EM)", "kornet_team")
HEAVY = ("Ground Forces", "تانک M1A2 Abrams", "m1a2_abrams")


def _contract(seller, buyer, smuggled, heavy=False, req=5_000_000):
    cat, name, ekey = HEAVY if heavy else LIGHT
    return db.create_trade_contract(
        proposer_id=seller, recipient_id=buyer,
        offered_type="military_asset", offered_amount=10,
        requested_type="treasury", requested_amount=req,
        transport_payer="seller", transport_cost=300_000,
        offered_key=ekey, transport_mode="land",
        is_smuggled=1 if smuggled else 0,
        origin_country_key="russia",
        license_country_id=None, license_status="approved")


# ─────────────────────────── behavioral ───────────────────────────

def test_formal_transfer_to_arms_embargoed_blocked(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "sanc_f.db")
    conn = db.get_connection(); cur = conn.cursor()
    _country(cur, 1, 1001, "فروشنده", "seller"); _country(cur, 2, 1002, "خریدار", "buyer")
    _asset(cur, 1, "seller", *LIGHT, 10)
    conn.commit(); conn.close()
    ok, _ = db.apply_targeted_sanction(2, "arms_embargo")
    assert ok
    cid = _contract(1, 2, smuggled=False)
    ok, msg = db.execute_trade_contract_transaction(cid)
    assert not ok and "تحریم تسلیحاتی سازمان ملل" in msg


def test_smuggled_light_to_arms_embargoed_succeeds(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "sanc_s.db")
    conn = db.get_connection(); cur = conn.cursor()
    _country(cur, 1, 1001, "فروشنده", "seller"); _country(cur, 2, 1002, "خریدار", "buyer")
    _asset(cur, 1, "seller", *LIGHT, 10)
    conn.commit(); conn.close()
    ok, _ = db.apply_targeted_sanction(2, "arms_embargo")
    assert ok
    monkeypatch.setattr("random.random", lambda: 0.99)  # رد نمی‌شود
    cid = _contract(1, 2, smuggled=True)
    ok, msg = db.execute_trade_contract_transaction(cid)
    assert ok and str(msg).startswith("SMUGGLED_SAFE:")
    conn = db.get_connection(); cur = conn.cursor()
    got = cur.execute("SELECT amount FROM country_assets WHERE country_id=2 AND equipment_key='kornet_team'").fetchone()
    left = cur.execute("SELECT amount FROM country_assets WHERE country_id=1 AND equipment_key='kornet_team'").fetchone()
    conn.close()
    assert got["amount"] == 10 and left["amount"] == 0


def test_risk_escalation_40_percent(monkeypatch, tmp_path):
    """random=0.30 → بدون تحریم امن است (۲۵٪)، با تحریم UN رد می‌شود (۴۰٪) و برچسب نقض می‌خورد."""
    _fresh(monkeypatch, tmp_path, "sanc_r.db")
    conn = db.get_connection(); cur = conn.cursor()
    _country(cur, 1, 1001, "فروشنده", "seller"); _country(cur, 2, 1002, "خریدار", "buyer")
    _asset(cur, 1, "seller", *LIGHT, 10)
    conn.commit(); conn.close()
    monkeypatch.setattr("random.random", lambda: 0.30)

    cid = _contract(1, 2, smuggled=True)
    ok, msg = db.execute_trade_contract_transaction(cid)
    assert ok and str(msg).startswith("SMUGGLED_SAFE"), "بدون تحریم باید با 0.30 رد نشود"

    ok, _ = db.apply_targeted_sanction(2, "arms_embargo")
    assert ok
    _asset_cur = db.get_connection()
    cur2 = _asset_cur.cursor()
    _asset(cur2, 1, "seller", *LIGHT, 10)  # دوباره ذخیره کن
    _asset_cur.commit(); _asset_cur.close()
    cid2 = _contract(1, 2, smuggled=True)
    ok2, msg2 = db.execute_trade_contract_transaction(cid2)
    assert ok2 and "INTERCEPTED:5:5:" in str(msg2) and str(msg2).endswith(":1"), msg2


def test_forged_heavy_smuggle_rejected(monkeypatch, tmp_path):
    """callback جعلی: قرارداد قاچاقی با سلاح سنگین باید در اجرا رد شود."""
    _fresh(monkeypatch, tmp_path, "sanc_h.db")
    conn = db.get_connection(); cur = conn.cursor()
    _country(cur, 1, 1001, "فروشنده", "seller"); _country(cur, 2, 1002, "خریدار", "buyer")
    _asset(cur, 1, "seller", *HEAVY, 10)
    conn.commit(); conn.close()
    cid = _contract(1, 2, smuggled=True, heavy=True)
    ok, msg = db.execute_trade_contract_transaction(cid)
    assert not ok and "قاچاق فقط برای سلاح‌های سبک" in msg


def test_bilateral_sanctioned_smuggle_allowed_formal_blocked(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "sanc_b.db")
    conn = db.get_connection(); cur = conn.cursor()
    _country(cur, 1, 1001, "فروشنده", "seller"); _country(cur, 2, 1002, "خریدار", "buyer")
    _asset(cur, 1, "seller", *LIGHT, 10)
    cur.execute("INSERT INTO diplomatic_relations (country1_id, country2_id, status, created_at) VALUES (1, 2, 'sanctioned', 'x')")
    conn.commit(); conn.close()
    monkeypatch.setattr("random.random", lambda: 0.99)

    cid = _contract(1, 2, smuggled=False)
    ok, msg = db.execute_trade_contract_transaction(cid)
    assert not ok and "تحریم‌شده" in msg

    cid2 = _contract(1, 2, smuggled=True)
    ok2, msg2 = db.execute_trade_contract_transaction(cid2)
    assert ok2 and str(msg2).startswith("SMUGGLED_SAFE:")


def test_trade_embargo_blocks_even_smuggle(monkeypatch, tmp_path):
    """تحریم تجاری UN مطلق است — قاچاق کالا/قرارداد را باز نمی‌کند (فاز ۲)."""
    _fresh(monkeypatch, tmp_path, "sanc_t.db")
    conn = db.get_connection(); cur = conn.cursor()
    _country(cur, 1, 1001, "فروشنده", "seller"); _country(cur, 2, 1002, "خریدار", "buyer")
    _asset(cur, 1, "seller", *LIGHT, 10)
    conn.commit(); conn.close()
    ok, _ = db.apply_targeted_sanction(2, "trade_embargo")
    assert ok
    cid = _contract(1, 2, smuggled=True)
    ok, msg = db.execute_trade_contract_transaction(cid)
    assert not ok and "تحریم تجاری سازمان ملل" in msg


def test_faction_recipient_smuggle_works(monkeypatch, tmp_path):
    """گروهک سفارشی زیر تحریم تسلیحاتی — فقط از مسیر قاچاق سلاح می‌گیرد."""
    _fresh(monkeypatch, tmp_path, "sanc_faction.db")
    conn = db.get_connection(); cur = conn.cursor()
    _country(cur, 1, 1001, "فروشنده", "seller")
    _country(cur, 2, 1003, "گروهک تست", "faction_test")
    _asset(cur, 1, "seller", *LIGHT, 10)
    conn.commit(); conn.close()
    ok, _ = db.apply_targeted_sanction(2, "arms_embargo")
    assert ok
    monkeypatch.setattr("random.random", lambda: 0.99)
    cid = _contract(1, 2, smuggled=True)
    ok, msg = db.execute_trade_contract_transaction(cid)
    assert ok and str(msg).startswith("SMUGGLED_SAFE:")


# ─────────────────────────── source guards ───────────────────────────

def test_un_violation_news_templates_zero_digits():
    import news_engine
    for headline, body in news_engine._UN_VIOLATION_TEMPLATES:
        assert not re.search(r"\d", headline + body), "خبر نقض تحریم نباید رقم داشته باشد"


def test_diplomacy_self_produced_smuggle_button_and_gate():
    src = open("handlers/diplomacy.py", encoding="utf-8").read()
    assert "if is_light:" in src, "سلاح سبک تولید خودی هم باید دکمه‌ی قاچاق داشته باشد"
    assert "not is_self_produced and is_light" not in src
    assert 'mode_type == "smuggle" and not draft.get("is_light")' in src, \
        "دکمه‌ی قاچاق باید سمت UI هم گیت سبک داشته باشد"


def test_intercept_message_carries_un_violation_flag():
    src = open("database.py", encoding="utf-8").read()
    assert '{1 if _un_violation else 0}' in src
    d = open("handlers/diplomacy.py", encoding="utf-8").read()
    assert "_un_viol" in d and "trigger_un_sanction_violation_news" in d
