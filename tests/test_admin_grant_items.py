# -*- coding: utf-8 -*-
"""
تست‌های اعطای مستقیم آیتم‌های فروشگاه توسط ادمین از منوی «پرونده مالی و اشتراک VIP».

پوشش:
- تابع مشترک admin_grant_item برای همه دسته‌ها (بقا، بلیط، بتل‌پس، بوستر، دیده شدن)
- ثبت رکورد ردیابی با مبلغ صفر در payment_requests
- یکسان بودن نتیجه اعطای ادمین با مسیر تایید فیش پرداخت
- سلامت کاتالوگ دکمه‌ها در handlers/admin_dossier.py
"""

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import database as db  # noqa: E402

ADMIN_ID = 8052987465


@pytest.fixture()
def db_temp(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr(config, "DB_PATH", os.path.join(tmpdir, "test.db"))
    db.init_db()
    return db


def _new_country(db_temp, player_id=901, name="ایران", key="iran"):
    return db_temp.create_country(player_id, name, "🇮🇷", country_key=key)


# ==================== بسته‌های بقا ====================

def test_grant_survival_pack_adds_resources(db_temp):
    cid = _new_country(db_temp)
    before = db_temp.get_country_by_id(cid)

    ok, msg = db_temp.admin_grant_item(cid, "survival_medium", ADMIN_ID)
    assert ok, msg

    after = db_temp.get_country_by_id(cid)
    assert after["treasury"] - before["treasury"] == 6_000_000
    assert after["oil_reserves"] - before["oil_reserves"] == 900_000
    assert after["grain"] - before["grain"] == 30_000
    assert after["iron_ore"] - before["iron_ore"] == 8_000
    assert after["microchips"] - before["microchips"] == 300


def test_admin_grant_bypasses_survival_daily_cap(db_temp):
    """ادمین باید بتواند فراتر از سقف ۳ بستهٔ روزانه جبران کند."""
    cid = _new_country(db_temp)
    for i in range(5):
        ok, msg = db_temp.admin_grant_item(cid, "survival_small", ADMIN_ID)
        assert ok, f"اعطای {i + 1}ام شکست خورد: {msg}"

    c = db_temp.get_country_by_id(cid)
    assert c["oil_reserves"] >= 400_000 * 5


def test_player_purchase_still_respects_daily_cap(db_temp):
    """سقف روزانه برای خرید عادی بازیکن باید همچنان اعمال شود."""
    cid = _new_country(db_temp, player_id=777)
    for _ in range(3):
        req = db_temp.create_payment_request(777, cid, "survival_small", "بسته بقا کوچک", 149_000)
        ok, _, _ = db_temp.approve_payment_request(req, admin_id=ADMIN_ID)
        assert ok

    req = db_temp.create_payment_request(777, cid, "survival_small", "بسته بقا کوچک", 149_000)
    ok, msg, _ = db_temp.approve_payment_request(req, admin_id=ADMIN_ID)
    assert not ok
    assert "سقف روزانه" in msg


def test_grant_can_opt_into_limits(db_temp):
    """اگر ادمین صریحاً bypass را خاموش کند، سقف روزانه اعمال می‌شود."""
    cid = _new_country(db_temp)
    for _ in range(3):
        assert db_temp.admin_grant_item(cid, "survival_small", ADMIN_ID, bypass_limits=False)[0]

    ok, msg = db_temp.admin_grant_item(cid, "survival_small", ADMIN_ID, bypass_limits=False)
    assert not ok
    assert "سقف روزانه" in msg


# ==================== بلیط‌ها ====================

def test_grant_drill_and_statement_tickets(db_temp):
    cid = _new_country(db_temp)

    assert db_temp.admin_grant_item(cid, "ticket_drill_3", ADMIN_ID)[0]
    assert db_temp.admin_grant_item(cid, "ticket_statement_5", ADMIN_ID)[0]

    c = db_temp.get_country_by_id(cid)
    assert (c["drill_tickets"] or 0) == 3
    assert (c["statement_tickets"] or 0) == 5


def test_grant_tickets_are_cumulative(db_temp):
    cid = _new_country(db_temp)
    db_temp.admin_grant_item(cid, "ticket_drill", ADMIN_ID)
    db_temp.admin_grant_item(cid, "ticket_drill", ADMIN_ID)
    db_temp.admin_grant_item(cid, "ticket_drill_3", ADMIN_ID)

    c = db_temp.get_country_by_id(cid)
    assert (c["drill_tickets"] or 0) == 5


def test_grant_contract_boost_sets_expiry(db_temp):
    cid = _new_country(db_temp)
    ok, _ = db_temp.admin_grant_item(cid, "ticket_contract_7d", ADMIN_ID)
    assert ok

    c = db_temp.get_country_by_id(cid)
    assert c["contract_boost_until"]


# ==================== بتل‌پس و بوسترها ====================

def test_grant_battle_pass_premium(db_temp):
    cid = _new_country(db_temp)
    ok, _ = db_temp.admin_grant_item(cid, "battle_pass", ADMIN_ID)
    assert ok

    bp = db_temp.get_or_create_battle_pass(cid)
    assert bp["is_premium"] == 1


def test_grant_bp_booster_sets_multiplier(db_temp):
    cid = _new_country(db_temp)
    ok, _ = db_temp.admin_grant_item(cid, "bp_booster_7d", ADMIN_ID)
    assert ok

    c = db_temp.get_country_by_id(cid)
    assert c["bp_booster_until"]
    assert float(c["bp_booster_mult"]) == 2.0


# ==================== خدمات دیده شدن ====================

def test_grant_golden_statement_and_pin_credits(db_temp):
    cid = _new_country(db_temp)
    db_temp.admin_grant_item(cid, "golden_stmt_10", ADMIN_ID)
    db_temp.admin_grant_item(cid, "pin_3", ADMIN_ID)

    c = db_temp.get_country_by_id(cid)
    assert (c["golden_stmt_credits"] or 0) == 10
    assert (c["pin_credits"] or 0) == 3


def test_grant_golden_frame(db_temp):
    cid = _new_country(db_temp)
    ok, _ = db_temp.admin_grant_item(cid, "frame_30d", ADMIN_ID)
    assert ok
    assert db_temp.get_country_by_id(cid)["golden_frame_until"]


def test_grant_custom_title_uses_payload(db_temp):
    cid = _new_country(db_temp)
    ok, _ = db_temp.admin_grant_item(
        cid, "title_7d", ADMIN_ID, custom_payload={"custom_title": "سلطان نفت"}
    )
    assert ok

    c = db_temp.get_country_by_id(cid)
    assert c["custom_title"] == "سلطان نفت"
    assert c["title_expires_at"]


# ==================== VIP از مسیر اعطای ادمین ====================

def test_grant_vip_tier(db_temp):
    cid = _new_country(db_temp)
    ok, _ = db_temp.admin_grant_item(cid, "vip_diamond", ADMIN_ID)
    assert ok

    c = db_temp.get_country_by_id(cid)
    assert c["is_vip"] == 1
    assert c["vip_tier"] == "diamond"
    assert c["vip_expires_at"]


# ==================== ردیابی و سازگاری دو مسیر ====================

def test_grant_is_recorded_in_payment_history(db_temp):
    cid = _new_country(db_temp)
    db_temp.admin_grant_item(cid, "ticket_drill", ADMIN_ID)

    history = db_temp.get_country_payment_history(cid, 10)
    assert len(history) == 1
    rec = history[0]
    assert rec["amount_toman"] == 0
    assert rec["status"] == "approved"
    assert rec["tracking_code"] == "ADMIN_GRANT"
    assert rec["item_type"] == "ticket_drill"


def test_admin_grant_matches_payment_approval(db_temp):
    """اعطای ادمین باید دقیقاً همان اثری را بگذارد که تایید فیش پرداخت می‌گذارد."""
    cid_grant = _new_country(db_temp, player_id=111, name="کشور الف", key="alpha")
    cid_pay = _new_country(db_temp, player_id=222, name="کشور ب", key="beta")

    db_temp.admin_grant_item(cid_grant, "survival_large", ADMIN_ID)

    req = db_temp.create_payment_request(222, cid_pay, "survival_large", "بسته بقا بزرگ", 389_000)
    ok, _, _ = db_temp.approve_payment_request(req, admin_id=ADMIN_ID)
    assert ok

    a = db_temp.get_country_by_id(cid_grant)
    b = db_temp.get_country_by_id(cid_pay)
    for field in ("treasury", "oil_reserves", "grain", "iron_ore", "microchips"):
        assert a[field] == b[field], f"عدم تطابق در {field}"


def test_grant_invalid_item_fails_gracefully(db_temp):
    cid = _new_country(db_temp)
    ok, msg = db_temp.admin_grant_item(cid, "survival_nonexistent", ADMIN_ID)
    assert not ok
    assert msg


def test_grant_to_missing_country_fails(db_temp):
    ok, msg = db_temp.admin_grant_item(999_999, "ticket_drill", ADMIN_ID)
    assert not ok
    assert "کشور یافت نشد" in msg


# ==================== سلامت کاتالوگ منوی ادمین ====================

def test_grant_catalog_keys_are_all_supported():
    """هر کلیدی که در منوی ادمین دکمه دارد باید در PLANS_METADATA تعریف شده باشد."""
    from handlers.admin_dossier import GRANT_CATEGORIES
    from handlers.vip import PLANS_METADATA

    for cat_key, (title, items) in GRANT_CATEGORIES.items():
        assert title and items, f"دسته {cat_key} خالی است"
        for item_key, label in items:
            assert item_key in PLANS_METADATA, f"{item_key} در PLANS_METADATA نیست"
            assert label.strip(), f"برچسب خالی برای {item_key}"


def test_grant_catalog_has_no_duplicate_keys():
    from handlers.admin_dossier import GRANT_CATEGORIES

    seen = []
    for _title, items in GRANT_CATEGORIES.values():
        seen.extend(k for k, _ in items)
    assert len(seen) == len(set(seen)), "کلید تکراری در کاتالوگ اعطا"


def test_every_catalog_item_actually_grants(db_temp):
    """هر آیتم کاتالوگ باید بدون خطا اعطا شود (به‌جز محدودیت سقف روزانه بقا)."""
    from handlers.admin_dossier import GRANT_CATEGORIES, GRANT_NEEDS_TEXT

    failures = []
    for _title, items in GRANT_CATEGORIES.values():
        for item_key, label in items:
            cid = _new_country(db_temp, player_id=abs(hash(item_key)) % 10**6,
                               name=f"کشور {item_key}", key=f"k_{item_key}")
            payload = {"custom_title": "لقب آزمایشی"} if item_key in GRANT_NEEDS_TEXT else None
            ok, msg = db_temp.admin_grant_item(cid, item_key, ADMIN_ID, custom_payload=payload)
            if not ok:
                failures.append(f"{item_key}: {msg}")

    assert not failures, "آیتم‌های ناموفق: " + " | ".join(failures)


class TestCivilConstructionAdjust:
    """رگرسیون: دکمه‌های ➕/➖ منوی ساخت‌وسازهای غیرنظامی."""

    def test_add_equipment_takes_delta_not_absolute(self, tmp_path, monkeypatch):
        """add_equipment دلتا می‌گیرد؛ پاس‌دادن مقدار نهایی تعداد را دوبرابر می‌کرد."""
        import importlib, config
        monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "civ.db"))
        import database as db
        importlib.reload(db)
        db.init_db()
        cid = db.create_country(777002, "سوئد", "🇸🇪", country_key="sweden")

        db.add_equipment(cid, "grain_silo", 305)
        assert db.get_equipment(cid)["grain_silo"] == 305

        # ➖۱ باید ۳۰۴ بدهد، نه ۶۰۹
        db.add_equipment(cid, "grain_silo", -1)
        assert db.get_equipment(cid)["grain_silo"] == 304

        db.add_equipment(cid, "grain_silo", 5)
        assert db.get_equipment(cid)["grain_silo"] == 309

    def test_equipment_never_negative(self, tmp_path, monkeypatch):
        import importlib, config
        monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "civ2.db"))
        import database as db
        importlib.reload(db)
        db.init_db()
        cid = db.create_country(777003, "سوئد", "🇸🇪", country_key="sweden")
        db.add_equipment(cid, "oil_refinery", 1)
        db.add_equipment(cid, "oil_refinery", -5)
        assert db.get_equipment(cid).get("oil_refinery", 0) == 0
