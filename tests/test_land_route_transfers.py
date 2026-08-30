# -*- coding: utf-8 -*-
"""تست‌های محدودیت «مسیر زمینی» برای ترابری زمینی (قرارداد تجاری، کمک خارجی، بازار).

قانون: حمل زمینی فقط وقتی مجاز است که زنجیره‌ای پیوسته از خشکی (مرز مستقیم یا
ترانزیت خاکی از کشورهای میانی) بین دو کشور وجود داشته باشد. پیوندهای دریایی-
نزدیک مثل آمریکا↔کوبا گذرگاه زمینی محسوب نمی‌شوند، اما گذرگاه‌های مصنوعی واقعی
(تونل مانش، پل اورسوند، گذرگاه ملک فهد، گذرگاه جوهر) زمینی باقی می‌مانند.
"""

import borders
import config
import database as db


VALID_KEYS = sorted((getattr(config, "COUNTRY_STARTING_OVERRIDES", {}) or {}).keys())


def _fresh(monkeypatch, tmp_path, name="land_route.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


def _country(pid, key, treasury=500_000_000):
    cid = db.create_country(pid, f"کشور {key}", "🏳️", country_key=key)
    db.update_country_field(cid, "treasury", treasury)
    db.update_country_field(cid, "grain", 10_000)
    db.update_country_field(cid, "gold", 10_000)
    return cid


# ════════════════ واحد: نقشه‌ی خالص زمینی ════════════════

def test_pure_land_map_drops_near_sea_links_but_keeps_artificial_links():
    m = borders.build_land_route_map(VALID_KEYS)
    # پیوندهای واقعی زمینی حفظ می‌شوند
    assert "canada" in m["usa"]
    assert "mexico" in m["usa"]
    assert "turkey" in m["iran"]
    # خلیج مکزیک — آمریکا↔کوبا و مکزیک↔کوبا گذرگاه زمینی ندارند
    assert "cuba" not in m["usa"]
    assert "cuba" not in m["mexico"]
    # کشورهای جزیره‌ای کاملاً جدا می‌مانند
    assert m.get("japan") == []
    assert m.get("cuba") == []
    assert m.get("australia") == []
    assert m.get("taiwan") == []
    # گذرگاه‌های مصنوعی واقعی زمینی می‌مانند
    assert "france" in m["uk"]          # تونل مانش
    assert "sweden" in m["denmark"]     # پل اورسوند
    assert "bahrain" in m["saudi"]      # گذرگاه ملک فهد
    assert "singapore" in m["malaysia"] # گذرگاه جوهر


def test_has_land_route_direct_transit_and_isolation():
    # مرز مستقیم
    assert borders.has_land_route("iran", "turkey", VALID_KEYS)
    assert borders.has_land_route("usa", "canada", VALID_KEYS)
    # ترانزیت خاکی چندکشوره (ایران→ترکیه→…→آلمان)
    assert borders.has_land_route("iran", "germany", VALID_KEYS)
    # متقارن است
    assert borders.has_land_route("germany", "iran", VALID_KEYS)
    # اقیانوس بین‌شان — مثال خود کاربر: آمریکا و بریتانیا
    assert not borders.has_land_route("usa", "uk", VALID_KEYS)
    # پیوند دریایی-نزدیک در نقشه‌ی قدیمی — نباید مسیر زمینی حساب شود
    assert not borders.has_land_route("usa", "cuba", VALID_KEYS)
    # ژاپن جزیره است و به هیچ‌کجا مسیر زمینی ندارد
    assert not borders.has_land_route("japan", "china", VALID_KEYS)
    # مبدأ = مقصد / کلید نامعتبر
    assert not borders.has_land_route("iran", "iran", VALID_KEYS)
    assert not borders.has_land_route("atlantis", "iran", VALID_KEYS)


def test_db_helper_fail_open_for_unknown_keys_but_strict_for_known():
    """هم‌راستا با سیاست has_open_sea_access: کلید خارج از کاتالوگ محدود نمی‌شود."""
    assert db.has_land_trade_route("made_up_key", "other_fake")
    # اما دو کشور واقعیِ بدون مسیر خشکی قاطعانه مسدود می‌شوند
    assert not db.has_land_trade_route("usa", "uk")
    assert db.has_land_trade_route("usa", "canada")
    assert db.has_land_trade_route("iran", "germany")


# ════════════════ یکپارچگی: کمک خارجی ════════════════

def test_land_aid_blocked_without_land_route(monkeypatch, tmp_path):
    """کمک زمینی آمریکا→بریتانیا باید رد شود و هیچ موجودی تغییر نکند."""
    _fresh(monkeypatch, tmp_path)
    usa = _country(9101, "usa")
    uk = _country(9102, "uk")

    ok, msg = db.execute_foreign_aid_transaction(usa, uk, "grain", 100, transport_mode="land")
    assert not ok
    assert "زمینی" in msg and "مسیر" in msg

    usa_row = db.get_country_by_id(usa)
    uk_row = db.get_country_by_id(uk)
    assert usa_row["grain"] == 10_000          # کالا کسر نشده
    assert usa_row["treasury"] == 500_000_000  # هزینه ترانزیت هم کسر نشده
    assert uk_row["grain"] == 10_000           # به مقصد نرسیده


def test_air_aid_still_allowed_without_land_route(monkeypatch, tmp_path):
    """همان مسیر آمریکا↔بریتانیا با ترابری هوایی آزاد است (قانون فقط برای زمینی است)."""
    _fresh(monkeypatch, tmp_path)
    usa = _country(9111, "usa")
    uk = _country(9112, "uk")

    ok, msg = db.execute_foreign_aid_transaction(usa, uk, "grain", 100, transport_mode="air")
    assert ok, msg
    assert db.get_country_by_id(uk)["grain"] == 10_100
    assert db.get_country_by_id(usa)["treasury"] == 500_000_000 - 2_000_000  # کرایه هوایی


def test_land_aid_allowed_with_transit_land_route(monkeypatch, tmp_path):
    """ایران↔آلمان مرز مستقیم ندارد اما ترانزیت خاکی دارد — کمک زمینی مجاز است."""
    _fresh(monkeypatch, tmp_path)
    iran = _country(9121, "iran")
    germany = _country(9122, "germany")

    ok, msg = db.execute_foreign_aid_transaction(iran, germany, "grain", 100, transport_mode="land")
    assert ok, msg
    assert db.get_country_by_id(germany)["grain"] == 10_100
    assert db.get_country_by_id(iran)["treasury"] == 500_000_000 - 1_000_000  # کرایه زمینی


# ════════════════ یکپارچگی: قرارداد تجاری ════════════════

def test_land_trade_contract_rejected_on_accept_without_route(monkeypatch, tmp_path):
    """قرارداد زمینی آمریکا→بریتانیا هنگام پذیرش رد می‌شود و با کسر همراه نمی‌شود."""
    _fresh(monkeypatch, tmp_path)
    usa = _country(9201, "usa")
    uk = _country(9202, "uk")

    contract_id = db.create_trade_contract(usa, uk, "gold", 10, "treasury", 50_000, transport_mode="land")
    assert contract_id > 0

    ok, msg = db.execute_trade_contract_transaction(contract_id, actor_country_id=uk)
    assert not ok
    assert "زمینی" in msg

    # قرارداد همچنان باز است و هیچ کالا/پولی جابه‌جا نشده
    assert db.get_trade_contract(contract_id)["status"] == "pending"
    assert db.get_country_by_id(usa)["gold"] == 10_000
    assert db.get_country_by_id(uk)["treasury"] == 500_000_000


def test_land_trade_contract_accepted_with_land_route(monkeypatch, tmp_path):
    """قرارداد زمینی ایران→ترکیه (مرز مستقیم) موفق انجام می‌شود."""
    _fresh(monkeypatch, tmp_path)
    iran = _country(9211, "iran")
    turkey = _country(9212, "turkey")

    contract_id = db.create_trade_contract(iran, turkey, "gold", 10, "treasury", 50_000, transport_mode="land")
    assert contract_id > 0

    ok, msg = db.execute_trade_contract_transaction(contract_id, actor_country_id=turkey)
    assert ok, msg
    assert db.get_trade_contract(contract_id)["status"] == "accepted"
    assert db.get_country_by_id(iran)["gold"] == 10_000 - 10
    assert db.get_country_by_id(turkey)["gold"] == 10_000 + 10


def test_sea_and_air_contracts_unaffected_by_land_rule(monkeypatch, tmp_path):
    """برای اطمینان از عدم رگرسیون: قرارداد هوایی آمریکا→بریتانیا همچنان موفق است."""
    _fresh(monkeypatch, tmp_path)
    usa = _country(9221, "usa")
    uk = _country(9222, "uk")

    contract_id = db.create_trade_contract(usa, uk, "gold", 10, "treasury", 50_000, transport_mode="air")
    ok, msg = db.execute_trade_contract_transaction(contract_id, actor_country_id=uk)
    assert ok, msg
