# -*- coding: utf-8 -*-
"""
گزارش بازیکن: قرارداد نفت بعد از تأیید گیرنده به‌خاطر ظرفیت رد می‌شود،
ولی سهمیه‌ی ترانزیت روزانه او سوخته است (شمارنده موقع پیشنهاد +۱ می‌شود).
قرار: شمارنده فقط با اجرای موفق +۱ شود؛ ظرفیت از همان لحظه‌ی پیشنهاد چک شود.
"""

import pytest
import config
import database as db


def _fresh(monkeypatch, tmp_path, name):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


def _country(cur, cid, pid, name, key):
    cur.execute(
        "INSERT OR REPLACE INTO countries (id, player_id, name, flag, country_key, treasury, oil_reserves) "
        "VALUES (?, ?, ?, '🏳️', ?, 50000000, 1000000)", (cid, pid, name, key))


def _oil_contract(seller, buyer, amount, mode="air"):
    return db.create_trade_contract(
        proposer_id=seller, recipient_id=buyer,
        offered_type="oil", offered_amount=amount,
        requested_type="treasury", requested_amount=1_000_000,
        transport_payer="seller", transport_cost=300_000,
        transport_mode=mode)


# ─────────────────────────── pure ───────────────────────────

def test_shipment_capacity_helper():
    cap, name = db.shipment_capacity("oil", "air")
    assert cap == 35_000
    assert "هوایی" in name
    cap_sea, _ = db.shipment_capacity("oil", "sea")
    assert cap_sea == 2_000_000
    cap_t, _ = db.shipment_capacity("treasury", "air")
    assert cap_t >= 20_000_000  # پول محموله‌ی وزنی معمولی نیست


# ─────────────────────────── behavioral ───────────────────────────

def test_failed_execution_frees_daily_slot(monkeypatch, tmp_path):
    """پیشنهاد سهمیه می‌گیرد (ضداسپم)، ولی شکستِ اجرا — مثل رد و لغو — آزادش می‌کند."""
    _fresh(monkeypatch, tmp_path, "cap_slot.db")
    conn = db.get_connection(); cur = conn.cursor()
    _country(cur, 1, 1001, "فروشنده", "seller"); _country(cur, 2, 1002, "خریدار", "buyer")
    conn.commit(); conn.close()

    cid = _oil_contract(1, 2, 100_000, mode="air")  # فراتر از ظرفیت هوایی نفت
    assert db.get_trade_mode_day_count(1, "air") == 1, "پیشنهاد باید سهمیه بگیرد"

    ok, msg = db.execute_trade_contract_transaction(cid)
    assert not ok and "ظرفیت" in msg
    db.free_trade_slot_for_contract(cid)  # همان کاری که هندلر تأیید انجام می‌دهد
    assert db.get_trade_mode_day_count(1, "air") == 0, "شکست اجرا سهمیه را آزاد کند"

    can, _ = db.check_trade_mode_limit(1, "air")
    assert can, "بعد از شکست اجرا باید بتوان دوباره پیشنهاد داد"


def test_successful_execution_does_not_double_count(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "cap_ok.db")
    conn = db.get_connection(); cur = conn.cursor()
    _country(cur, 1, 1001, "فروشنده", "seller"); _country(cur, 2, 1002, "خریدار", "buyer")
    conn.commit(); conn.close()

    cid = _oil_contract(1, 2, 500, mode="land")
    assert db.get_trade_mode_day_count(1, "land") == 1
    ok, msg = db.execute_trade_contract_transaction(cid)
    assert ok, msg
    assert db.get_trade_mode_day_count(1, "land") == 1, "اجرای موفق نباید دوباره بشمارد"


def test_military_success_keeps_single_count(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "cap_mil.db")
    conn = db.get_connection(); cur = conn.cursor()
    _country(cur, 1, 1001, "فروشنده", "seller"); _country(cur, 2, 1002, "خریدار", "buyer")
    cur.execute("""
        INSERT INTO country_assets (country_id, country_key, category, equipment_name, equipment_key, amount, buy_price, maintenance_cost, producible)
        VALUES (1, 'seller', 'Ground Forces', 'تیم ضدزره کورنت', 'kornet_team', 10, 100000, 500, 0)
    """)
    conn.commit(); conn.close()

    cid = db.create_trade_contract(
        proposer_id=1, recipient_id=2,
        offered_type="military_asset", offered_amount=2,
        requested_type="treasury", requested_amount=100_000,
        transport_payer="seller", transport_cost=300_000,
        offered_key="kornet_team", transport_mode="land",
        origin_country_key="seller", license_country_id=None, license_status="approved")
    assert db.get_trade_mode_day_count(1, "land") == 1
    ok, msg = db.execute_trade_contract_transaction(cid)
    assert ok, msg
    assert db.get_trade_mode_day_count(1, "land") == 1


def test_capacity_fail_is_zero_side_effect(monkeypatch, tmp_path):
    """رد ظرفیت در اجرا: نه پول، نه نفت، نه سهمیه — هیچ‌چیز نباید تغییر کند."""
    _fresh(monkeypatch, tmp_path, "cap_fail.db")
    conn = db.get_connection(); cur = conn.cursor()
    _country(cur, 1, 1001, "فروشنده", "seller"); _country(cur, 2, 1002, "خریدار", "buyer")
    conn.commit(); conn.close()

    cid = _oil_contract(1, 2, 100_000, mode="air")  # ظرفیت هوایی نفت ۳۵هزار
    ok, msg = db.execute_trade_contract_transaction(cid)
    assert not ok and "ظرفیت" in msg
    db.free_trade_slot_for_contract(cid)  # کاری که هندلر تأیید در شکست انجام می‌دهد

    conn = db.get_connection(); cur = conn.cursor()
    s = cur.execute("SELECT treasury, oil_reserves FROM countries WHERE id=1").fetchone()
    r = cur.execute("SELECT treasury, oil_reserves FROM countries WHERE id=2").fetchone()
    conn.close()
    assert s["treasury"] == 50_000_000 and s["oil_reserves"] == 1_000_000
    assert r["treasury"] == 50_000_000 and r["oil_reserves"] == 1_000_000
    assert db.get_trade_mode_day_count(1, "air") == 0, "محموله‌ی ردشده سهمیه نسوزاند"


def test_military_success_also_bumps_counter(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "cap_mil.db")
    conn = db.get_connection(); cur = conn.cursor()
    _country(cur, 1, 1001, "فروشنده", "seller"); _country(cur, 2, 1002, "خریدار", "buyer")
    cur.execute("""
        INSERT INTO country_assets (country_id, country_key, category, equipment_name, equipment_key, amount, buy_price, maintenance_cost, producible)
        VALUES (1, 'seller', 'Ground Forces', 'تیم ضدزره کورنت', 'kornet_team', 10, 100000, 500, 0)
    """)
    conn.commit(); conn.close()

    cid = db.create_trade_contract(
        proposer_id=1, recipient_id=2,
        offered_type="military_asset", offered_amount=2,
        requested_type="treasury", requested_amount=100_000,
        transport_payer="seller", transport_cost=300_000,
        offered_key="kornet_team", transport_mode="land",
        origin_country_key="seller", license_country_id=None, license_status="approved")
    ok, msg = db.execute_trade_contract_transaction(cid)
    assert ok, msg
    assert db.get_trade_mode_day_count(1, "land") == 1


# ─────────────────────────── source guard ───────────────────────────

def test_offer_ui_validates_capacity_before_send():
    src = open("handlers/diplomacy.py", encoding="utf-8").read()
    idx_finish = src.index('data.startswith("dip:trade_finish:")')
    idx_create = src.index("db.create_trade_contract(", idx_finish)
    window = src[idx_finish:idx_create]
    assert "shipment_capacity" in window, \
        "هندلر پیشنهاد باید قبل از ساخت قرارداد ظرفیت محموله را چک کند"
