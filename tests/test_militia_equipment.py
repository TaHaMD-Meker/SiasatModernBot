"""تست‌های رگرسیون: گروه‌های شبه‌نظامی نباید تجهیزات کشوری بگیرند.

باگ اصلی: `seed_country_assets` و `sync_all_country_assets_to_catalog` برای
کلیدهای `faction_*` به `DEFAULT_COUNTRY_EQUIPMENT` fallback می‌کردند و
«جنگنده پیشرفته نسل ۴.۵»، بمب‌افکن استراتژیک، ناو و... را به گروه‌های
شبه‌نظامی تزریق می‌کردند — کافی بود بازیکن یک بار فروشگاه را باز کند.
"""
import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import database as db  # noqa: E402


@pytest.fixture(autouse=True)
def db_temp(monkeypatch):
    """هر تست روی یک دیتابیس تازه و ایزوله اجرا می‌شود."""
    tmpdir = tempfile.mkdtemp(prefix="militia_test_")
    monkeypatch.setattr(config, "DB_PATH", os.path.join(tmpdir, "test.db"))
    db.init_db()
    return db


STATE_ONLY_KEYS = {i["key"] for i in config.DEFAULT_COUNTRY_EQUIPMENT}


def _make_militia(player_id, faction_key=None, name="گروه تست"):
    conn = db.get_connection()
    cur = conn.cursor()
    cid = _create(cur, player_id, name, faction_key)
    conn.commit()
    conn.close()
    return cid


def _create(cur, player_id, name, faction_key):
    return db._create_custom_militia_with_cur(
        cur, player_id, name, "🏴", "مقر تست", "دکترین تست", faction_key, "tester"
    )


def _asset_keys(country_id):
    return {a["equipment_key"] for a in db.get_country_assets(country_id)}


# ---------- انتخاب کاتالوگ ----------

def test_is_militia_country_key():
    assert db.is_militia_country_key("faction_12345")
    assert db.is_militia_country_key("faction_ansarullah")
    assert not db.is_militia_country_key("iran")
    assert not db.is_militia_country_key("usa")
    assert not db.is_militia_country_key("")
    assert not db.is_militia_country_key(None)


def test_custom_militia_gets_generic_militia_catalog():
    catalog = db.get_equipment_catalog_for("faction_999123")
    assert catalog is config.DEFAULT_MILITIA_EQUIPMENT
    keys = {i["key"] for i in catalog}
    assert keys.isdisjoint(STATE_ONLY_KEYS)


def test_predefined_faction_gets_its_own_catalog():
    catalog = db.get_equipment_catalog_for("faction_ansarullah")
    assert catalog is config.MILITIA_EQUIPMENT_CATALOG["ansarullah"]


def test_normal_country_still_uses_country_catalog():
    assert db.get_equipment_catalog_for("usa") is config.COUNTRY_EQUIPMENT_CATALOG["usa"]
    # کشور ناشناخته همچنان fallback کشوری دارد
    assert db.get_equipment_catalog_for("atlantis") is config.DEFAULT_COUNTRY_EQUIPMENT


# ---------- کاتالوگ پیش‌فرض شبه‌نظامی ----------

def test_default_militia_catalog_has_no_state_grade_hardware():
    """گروه شبه‌نظامی نباید نیروی هوایی یا ناوگان سطحی داشته باشد."""
    banned_words = ("جنگنده", "بمب‌افکن استراتژیک", "ناوشکن", "ناوگروه", "زیردریایی")
    for item in config.DEFAULT_MILITIA_EQUIPMENT:
        assert item["key"].startswith("militia_"), item["key"]
        assert item["key"] not in STATE_ONLY_KEYS, item["key"]
        assert item["category"] != "Air Force", item["name"]
        for word in banned_words:
            assert word not in item["name"], f"{item['name']} شامل «{word}» است"


def test_default_militia_gear_is_affordable_for_a_militia():
    """قیمت اقلام باید در حد بودجه یک گروه شبه‌نظامی باشد، نه یک دولت."""
    for item in config.DEFAULT_MILITIA_EQUIPMENT:
        assert item["price"] <= 1_000_000, f"{item['name']} گران‌تر از توان شبه‌نظامی است"


def test_default_militia_catalog_keys_are_unique():
    keys = [i["key"] for i in config.DEFAULT_MILITIA_EQUIPMENT]
    assert len(keys) == len(set(keys))


# ---------- رفتار انتها به انتها ----------

def test_creation_does_not_grant_state_equipment():
    cid = _make_militia(9911001)
    keys = _asset_keys(cid)
    assert keys.isdisjoint(STATE_ONLY_KEYS)
    assert "gen_fighter" not in keys


def test_seed_country_assets_does_not_inject_fighters():
    """رگرسیون اصلی: باز کردن فروشگاه/دارایی‌ها گروه را آلوده نکند."""
    cid = _make_militia(9911002)
    country = db.get_country_by_id(cid)
    before = _asset_keys(cid)

    # این همان کاری است که handlers/shop.py و handlers/assets.py می‌کنند
    db.seed_country_assets(cid, country["country_key"])

    after = _asset_keys(cid)
    assert after == before, f"تجهیزات جدید تزریق شد: {after - before}"
    assert "gen_fighter" not in after


def test_sync_all_does_not_inject_fighters():
    """رگرسیون: ری‌استارت ربات (init_db → sync) گروه را آلوده نکند."""
    cid = _make_militia(9911003, faction_key="ansarullah")
    before = _asset_keys(cid)

    db.sync_all_country_assets_to_catalog()

    after = _asset_keys(cid)
    assert after == before, f"تجهیزات جدید تزریق شد: {after - before}"
    assert after.isdisjoint(STATE_ONLY_KEYS)


def test_sync_still_updates_normal_countries():
    """فیکس نباید همگام‌سازی کشورهای عادی را بشکند."""
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO countries (player_id, name, flag, country_key) VALUES (?,?,?,?)",
        (9911004, "آمریکا تست", "🇺🇸", "usa"),
    )
    cid = cur.lastrowid
    conn.commit()
    conn.close()

    db.sync_all_country_assets_to_catalog()

    keys = _asset_keys(cid)
    expected = {i["key"] for i in config.COUNTRY_EQUIPMENT_CATALOG["usa"]}
    assert expected.issubset(keys)


# ---------- مایگریشن پاکسازی ----------

def test_purge_removes_injected_state_equipment():
    cid = _make_militia(9911005)
    clean = _asset_keys(cid)

    # شبیه‌سازی دیتابیس آلوده (رفتار قدیمی و باگ‌دار)
    conn = db.get_connection()
    cur = conn.cursor()
    for item in config.DEFAULT_COUNTRY_EQUIPMENT:
        cur.execute(
            """INSERT INTO country_assets
               (country_id, country_key, category, equipment_name, equipment_key,
                amount, buy_price, maintenance_cost, producible)
               VALUES (?,?,?,?,?,?,?,?,1)
               ON CONFLICT(country_id, equipment_key) DO NOTHING""",
            (cid, f"faction_9911005", item["category"], item["name"], item["key"],
             item["initial"], item["price"], item.get("maint", 0)),
        )
    conn.commit()
    conn.close()

    assert "gen_fighter" in _asset_keys(cid)

    db.set_setting("militia_state_equipment_purged_v1", "")
    db.purge_state_equipment_from_militias()

    assert _asset_keys(cid) == clean


def test_purge_is_idempotent_and_spares_normal_countries():
    cid = _make_militia(9911006)
    before = _asset_keys(cid)

    db.set_setting("militia_state_equipment_purged_v1", "")
    db.purge_state_equipment_from_militias()
    db.purge_state_equipment_from_militias()

    assert _asset_keys(cid) == before


def test_purge_keeps_purchased_catalog_items():
    """اقلامی که داخل کاتالوگ خودِ گروه هستند نباید حذف شوند."""
    cid = _make_militia(9911007)

    # گروه یک قلم از کاتالوگ خودش را می‌خرد (تعداد بالاتر از initial)
    conn = db.get_connection()
    cur = conn.cursor()
    cur.execute(
        "UPDATE country_assets SET amount = 9999 WHERE country_id = ? AND equipment_key = ?",
        (cid, "militia_technical"),
    )
    conn.commit()
    conn.close()

    db.set_setting("militia_state_equipment_purged_v1", "")
    db.purge_state_equipment_from_militias()

    assets = {a["equipment_key"]: a["amount"] for a in db.get_country_assets(cid)}
    assert assets.get("militia_technical") == 9999
