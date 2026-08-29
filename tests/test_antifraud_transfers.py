# -*- coding: utf-8 -*-
"""ضدتقلب: دفترچه‌ی انتقالات، برگشت هنگام حذف کشور، و سقف وزن/ارسال روزانه.

تصمیمات کارفرما:
* کمک خارجی رایگان → برگشت کامل از مقصد.
* معامله‌ی تجاری → جنس برمی‌گردد + ۵۰٪ پول پرداختی خریدار بازپرداخت می‌شود.
* مدل وزن: سبک (سقف وزن هر محموله + سقف ارسال روزانه).
"""

import datetime

import config
import database as db


def _fresh(monkeypatch, tmp_path, name="antifraud.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


def _country(pid, key, treasury=100_000_000):
    cid = db.create_country(pid, f"کشور {key}", "🏳️", country_key=key)
    db.update_country_field(cid, "treasury", treasury)
    return cid


# ─────────────────────────────────────────────────────────────────────────────
# دفترچه‌ی انتقالات
# ─────────────────────────────────────────────────────────────────────────────

def test_aid_and_trade_are_logged(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    a = _country(1001, "alpha")
    b = _country(1002, "beta")
    db.update_country_field(a, "oil_reserves", 500_000)
    db.update_country_field(b, "treasury", 50_000_000)

    ok, msg = db.execute_foreign_aid_transaction(a, b, "oil", 100_000, "sea")
    assert ok, msg
    logs = db.get_active_transfers_from(a, 72)
    assert len(logs) == 1
    assert logs[0]["kind"] == "aid" and logs[0]["resource_type"] == "oil"
    assert logs[0]["amount"] == 100_000


def test_transfer_log_not_written_when_transfer_fails(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    a = _country(1003, "alpha2")
    b = _country(1004, "beta2")
    db.update_country_field(a, "oil_reserves", 100)  # موجودی ناچیز
    # موجودی ناکافی → شکست
    ok, _msg = db.execute_foreign_aid_transaction(a, b, "oil", 999_999, "sea")
    assert not ok
    assert db.get_active_transfers_from(a, 72) == []


# ─────────────────────────────────────────────────────────────────────────────
# برگشت هنگام حذف
# ─────────────────────────────────────────────────────────────────────────────

def test_rollback_removes_free_aid_from_recipient(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    a = _country(2001, "alpha")
    b = _country(2002, "beta")
    db.update_country_field(b, "oil_reserves", 0)
    db.update_country_field(a, "oil_reserves", 500_000)
    ok, _ = db.execute_foreign_aid_transaction(a, b, "oil", 100_000, "sea")
    assert ok
    assert db.get_country_by_id(b)["oil_reserves"] == 100_000

    result = db.rollback_transfers_from(a, 72)
    assert result["total"] == 1
    assert db.get_country_by_id(b)["oil_reserves"] == 0, "کمک رایگان باید کامل برگردد"
    assert db.get_active_transfers_from(a, 72) == [], "لاگ باید بسته شود"


def test_rollback_refunds_half_the_trade_money(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    a = _country(2003, "alpha")
    b = _country(2004, "beta", treasury=50_000_000)
    # یک دارایی به a بدهیم و با معاهده بفروشد
    conn = db.get_connection()
    with conn:
        conn.execute(
            "INSERT INTO country_assets (country_id, country_key, category, equipment_name, equipment_key, "
            "amount, buy_price, maintenance_cost, producible) VALUES (?, 'alpha', 'Air Defense', 'پدافند آزمون', 'test_ad', 10, 5_000_000, 1000, 0)",
            (a,),
        )
    conn.close()

    contract = db.create_trade_contract(a, b, "military_asset", 4, "treasury", 2_000_000,
                                        transport_payer="buyer", transport_cost=0,
                                        offered_key="test_ad", transport_mode="sea")
    ok, msg = db.execute_trade_contract_transaction(contract, b)
    assert ok, msg
    # b صاحب ۴ پدافند شده و ۲ میلیون داده
    asset_row = db.get_connection().execute(
        "SELECT amount FROM country_assets WHERE country_id = ? AND equipment_key = 'test_ad'",
        (b,),
    ).fetchone()
    assert asset_row["amount"] == 4
    assert db.get_country_by_id(b)["treasury"] == 48_000_000

    result = db.rollback_transfers_from(a, 72)
    assert result["total"] == 1
    # جنس برمی‌گردد (کسر از b)
    asset_row = db.get_connection().execute(
        "SELECT amount FROM country_assets WHERE country_id = ? AND equipment_key = 'test_ad'",
        (b,),
    ).fetchone()
    assert asset_row["amount"] == 0
    # ۵۰٪ پول (۱ میلیون) از خزانه‌ی a به b برمی‌گردد
    assert db.get_country_by_id(b)["treasury"] == 49_000_000
    assert result["refunded_total"] == 1_000_000


def test_rollback_skips_missing_recipient(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    a = _country(2005, "alpha")
    b = _country(2006, "beta")
    db.update_country_field(a, "grain", 50_000)
    ok, _ = db.execute_foreign_aid_transaction(a, b, "grain", 10_000, "sea")
    assert ok
    db.delete_country_by_id(b)  # مقصد حذف شده
    result = db.rollback_transfers_from(a, 72)
    assert result["total"] == 0, "مقصدِ حذف‌شده نباید خطا بدهد"


# ─────────────────────────────────────────────────────────────────────────────
# سقف وزن و ارسال روزانه
# ─────────────────────────────────────────────────────────────────────────────

def test_equipment_weight_points_by_category():
    assert db.equipment_weight_points("Air Defense", 1) == 1.0
    assert db.equipment_weight_points("Air Defense", 200) == 200.0
    assert db.equipment_weight_points("UAV", 5) == 1.0
    assert db.equipment_weight_points("Missiles", 2) == 1.0
    assert db.equipment_weight_points("", 3) == 3.0  # ناشناس → ۱ به ازای هر قلم


def test_daily_shipment_cap_blocks_extra_transfers(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    a = _country(3001, "alpha")
    b = _country(3002, "beta")
    db.update_country_field(a, "oil_reserves", 1_000_000)
    db.update_country_field(a, "grain", 1_000_000)
    db.update_country_field(a, "treasury", 100_000_000)
    cap = int(getattr(config, "TRANSFER_DAILY_SHIPMENTS", 3))

    for _ in range(cap):
        ok, msg = db.execute_foreign_aid_transaction(a, b, "oil", 10_000, "sea")
        assert ok, msg
    ok, msg = db.execute_foreign_aid_transaction(a, b, "grain", 5_000, "sea")
    assert not ok, "محموله‌ی چهارم باید رد شود"
    assert "سقف ارسال روزانه" in msg
    assert db.get_transfer_day_count(a) == cap


def test_heavy_equipment_shipment_is_rejected(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    a = _country(3003, "alpha")
    b = _country(3004, "beta", treasury=200_000_000)
    conn = db.get_connection()
    with conn:
        conn.execute(
            "INSERT INTO country_assets (country_id, country_key, category, equipment_name, equipment_key, "
            "amount, buy_price, maintenance_cost, producible) VALUES (?, 'alpha', 'Air Defense', 'پدافند آزمون', 'test_ad', 500, 5_000_000, 1000, 0)",
            (a,),
        )
    conn.close()

    max_w = int(getattr(config, "TRANSFER_MAX_WEIGHT_POINTS", 150))
    # ۲۰۰ پدافند = ۲۰۰ نقطه > سقف
    contract = db.create_trade_contract(a, b, "military_asset", 200, "treasury", 10_000_000,
                                        transport_payer="buyer", transport_cost=0,
                                        offered_key="test_ad", transport_mode="sea")
    ok, msg = db.execute_trade_contract_transaction(contract, b)
    assert not ok
    assert "مازاد بر ظرفیت حمل" in msg
    # محموله‌ی کوچک (۱۰۰ پدافند = ۱۰۰ نقطه) قبول
    contract2 = db.create_trade_contract(a, b, "military_asset", 100, "treasury", 5_000_000,
                                         transport_payer="buyer", transport_cost=0,
                                         offered_key="test_ad", transport_mode="sea")
    ok2, msg2 = db.execute_trade_contract_transaction(contract2, b)
    assert ok2, msg2


def test_weight_system_can_be_toggled(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert db.transfer_weight_enabled() is True  # پیش‌فرض روشن
    db.set_transfer_weight_enabled(False)
    assert db.transfer_weight_enabled() is False
    db.set_transfer_weight_enabled(True)
    assert db.transfer_weight_enabled() is True


# ─────────────────────────────────────────────────────────────────────────────
# پنل ادمین
# ─────────────────────────────────────────────────────────────────────────────

def test_admin_delete_shows_rollback_preview():
    import inspect
    from handlers import admin as admin_handlers
    source = inspect.getsource(admin_handlers)
    assert "rollback_transfers_from" in source
    assert "format_transfer_rollback_summary" in source
    assert "admin:transfer_weight_toggle" in source
    assert "⚖️ سقف وزن و ارسال روزانه انتقال" in source
