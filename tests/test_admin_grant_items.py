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


class TestCivilZeroAndSetButtons:
    """دکمه‌های 🗑️ صفر کن و ✏️ تعیین عدد دقیق."""

    def _setup(self, tmp_path, monkeypatch, name):
        import importlib, config
        monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
        import database as db
        importlib.reload(db)
        db.init_db()
        return db, db.create_country(777004, "سوئد", "🇸🇪", country_key="sweden")

    def test_zero_button_clears_stock(self, tmp_path, monkeypatch):
        import asyncio
        db, cid = self._setup(tmp_path, monkeypatch, "z1.db")
        import handlers.admin_dossier as ad

        db.add_equipment(cid, "grain_silo", 305)

        class Q:
            async def answer(self, *a, **k):
                pass

            async def edit_message_text(self, *a, **k):
                pass

        ctx = type("C", (), {"user_data": {}})()
        asyncio.run(ad.handle_dossier_callbacks(Q(), ctx, f"admin:c_civ_zero:{cid}:grain_silo"))
        assert db.get_equipment(cid).get("grain_silo", 0) == 0

    def test_set_exact_quantity_up_and_down(self, tmp_path, monkeypatch):
        import asyncio
        db, cid = self._setup(tmp_path, monkeypatch, "z2.db")
        import handlers.admin_dossier as ad

        db.add_equipment(cid, "oil_refinery", 1)

        class Msg:
            async def reply_text(self, *a, **k):
                pass

        upd = type("U", (), {"message": Msg(), "effective_user": type("X", (), {"id": 1})()})()
        ctx = type("C", (), {"user_data": {}})()
        state = {"type": "civ_set_qty", "country_id": cid, "item_key": "oil_refinery"}

        asyncio.run(ad.handle_dossier_inputs(upd, ctx, "civ_set_qty", "۴", state))
        assert db.get_equipment(cid)["oil_refinery"] == 4

        asyncio.run(ad.handle_dossier_inputs(upd, ctx, "civ_set_qty", "1", state))
        assert db.get_equipment(cid)["oil_refinery"] == 1

        # ورودی نامعتبر نباید چیزی را تغییر دهد
        asyncio.run(ad.handle_dossier_inputs(upd, ctx, "civ_set_qty", "سلام", state))
        asyncio.run(ad.handle_dossier_inputs(upd, ctx, "civ_set_qty", "-5", state))
        assert db.get_equipment(cid)["oil_refinery"] == 1


# ==================== بازمحاسبهٔ عواید پس از تغییر ساخت‌وساز ====================

class TestCivEffectsRecalc:
    """باگ: دکمه‌های ± / صفر / تعیین عدد فقط جدول equipment را عوض می‌کردند و
    daily_income و grain_daily دست‌نخورده می‌ماند؛ یعنی ساخت‌وسازی که ادمین
    می‌داد یا می‌گرفت هیچ اثر واقعی روی اقتصاد کشور نداشت."""

    def test_grant_and_remove_silo_updates_income(self, db_temp):
        cid = _new_country(db_temp)
        base = db_temp.get_country_by_id(cid)["daily_income"]
        silo_inc = config.ALL_SHOP_ITEMS["grain_silo"]["income_add"]

        db_temp.add_equipment(cid, "grain_silo", 10)
        db_temp.recalc_country_civ_effects(cid)
        assert db_temp.get_country_by_id(cid)["daily_income"] == base + silo_inc * 10

        # صفر کردن باید درآمد را دقیقاً به پایه برگرداند (نه چسبیدن به مقدار باد‌کرده)
        db_temp.add_equipment(cid, "grain_silo", -10)
        db_temp.recalc_country_civ_effects(cid)
        assert db_temp.get_country_by_id(cid)["daily_income"] == base

    def test_recalc_is_idempotent(self, db_temp):
        """اجرای مکرر نباید عواید را تجمعی بالا ببرد (باگ کلاسیک MAX/جمع)."""
        cid = _new_country(db_temp)
        db_temp.add_equipment(cid, "agro_complex", 2)
        first = db_temp.recalc_country_civ_effects(cid)
        for _ in range(5):
            again = db_temp.recalc_country_civ_effects(cid)
        assert again == first

    def test_agro_complex_updates_grain_daily(self, db_temp):
        cid = _new_country(db_temp)
        base = db_temp.get_country_by_id(cid)["grain_daily"]
        add = config.ALL_SHOP_ITEMS["agro_complex"]["grain_daily_add"]

        db_temp.add_equipment(cid, "agro_complex", 3)
        db_temp.recalc_country_civ_effects(cid)
        assert db_temp.get_country_by_id(cid)["grain_daily"] == base + add * 3

    def test_silo_updates_grain_daily(self, db_temp):
        """سیلو با کاهش ضایعات پس از برداشت، عرضهٔ روزانه را بالا می‌برد
        (جایگزین ذخیرهٔ فوری ۵۰٬۰۰۰ تنی که غله را یک‌باره اسپان می‌کرد)."""
        cid = _new_country(db_temp)
        base = db_temp.get_country_by_id(cid)["grain_daily"]
        add = config.ALL_SHOP_ITEMS["grain_silo"]["grain_daily_add"]

        db_temp.add_equipment(cid, "grain_silo", 5)
        db_temp.recalc_country_civ_effects(cid)
        assert db_temp.get_country_by_id(cid)["grain_daily"] == base + add * 5

    def test_reserves_are_never_touched(self, db_temp):
        """ذخایر انبار دارایی بازیکن‌اند و بازمحاسبه نباید ریست‌شان کند."""
        cid = _new_country(db_temp)
        db_temp.update_country_field(cid, "grain", 123_456)
        db_temp.update_country_field(cid, "oil_reserves", 7_654_321)
        db_temp.add_equipment(cid, "grain_silo", 2)
        db_temp.recalc_country_civ_effects(cid)
        c = db_temp.get_country_by_id(cid)
        assert c["grain"] == 123_456
        assert c["oil_reserves"] == 7_654_321


# ==================== سیلوی غلات: تولید روزانه به‌جای ذخیرهٔ فوری ====================

class TestSiloDailyGrain:
    """سیلو انبار است، نه مزرعه: نباید هنگام ساخت غله «اسپان» کند.
    به‌جای grain_bonus یک‌باره، حالا grain_daily_add دارد."""

    def test_silo_has_no_instant_bonus(self):
        item = config.ALL_SHOP_ITEMS["grain_silo"]
        assert not item.get("grain_bonus"), "سیلو نباید ذخیرهٔ فوری بدهد"
        assert item.get("grain_daily_add", 0) > 0

    def test_no_item_grants_instant_grain(self):
        offenders = [k for k, v in config.ALL_SHOP_ITEMS.items() if v.get("grain_bonus")]
        assert offenders == [], f"آیتم‌های دارای ذخیرهٔ فوری: {offenders}"

    def test_buying_silo_does_not_spawn_grain(self, db_temp):
        cid = _new_country(db_temp)
        db_temp.update_country_field(cid, "treasury", 300_000_000)
        db_temp.update_country_field(cid, "oil_reserves", 80_000_000)
        before = db_temp.get_country_by_id(cid)
        db_temp.buy_item_transaction(cid, "grain_silo", 1, 15_000_000, "سیلو")
        after = db_temp.get_country_by_id(cid)

        rate = config.ALL_SHOP_ITEMS["grain_silo"]["grain_daily_add"]
        assert after["grain"] == before["grain"], "ذخیرهٔ انبار نباید یک‌باره بپرد"
        assert after["grain_daily"] == before["grain_daily"] + rate

    def test_admin_grant_gives_daily_grain(self, db_temp):
        cid = _new_country(db_temp)
        before = db_temp.get_country_by_id(cid)
        rate = config.ALL_SHOP_ITEMS["grain_silo"]["grain_daily_add"]

        db_temp.add_equipment(cid, "grain_silo", 2)
        db_temp.recalc_country_civ_effects(cid)
        after = db_temp.get_country_by_id(cid)

        assert after["grain"] == before["grain"]
        assert after["grain_daily"] == before["grain_daily"] + rate * 2

    def test_removing_silo_removes_daily_grain(self, db_temp):
        cid = _new_country(db_temp)
        base = db_temp.get_country_by_id(cid)["grain_daily"]
        db_temp.add_equipment(cid, "grain_silo", 3)
        db_temp.recalc_country_civ_effects(cid)
        db_temp.add_equipment(cid, "grain_silo", -3)
        db_temp.recalc_country_civ_effects(cid)
        assert db_temp.get_country_by_id(cid)["grain_daily"] == base

    def test_migration_cap_unaffected_by_silos(self, db_temp):
        """چون دیگر غله‌ای یک‌باره اضافه نمی‌شود، مایگریشن سقف چیزی را پاک نمی‌کند."""
        cid = _new_country(db_temp)
        db_temp.update_country_field(cid, "treasury", 300_000_000)
        db_temp.update_country_field(cid, "oil_reserves", 80_000_000)
        db_temp.buy_item_transaction(cid, "grain_silo", 1, 15_000_000, "سیلو")
        before = db_temp.get_country_by_id(cid)["grain"]
        db_temp.set_setting("grain_scale_fixed_v2", "")
        db_temp.fix_grain_scale_v2()
        assert db_temp.get_country_by_id(cid)["grain"] == before
