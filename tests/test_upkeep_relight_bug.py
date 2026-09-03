"""بازتولید باگ گزارش بازیکن‌ها: «سازه‌ها بعد از تأمین دوباره‌ی نیازها روشن نمی‌شوند».

سه سناریو:
  ۱) e2e با run_daily_cycle واقعی (نه فقط apply_building_upkeep تنها)
  ۲) خاموشی به‌خاطر برق (نیروگاه‌ها خاموش → کلاهک برق سقوط می‌کند) و سپس تأمین
  ۳) خرابکاری (outage +۱) روی کشورِ کم‌بINESS shortage — نباید روشن‌نشدگی بچسبد
"""
import importlib
import datetime

import pytest

import config


def _fresh(monkeypatch, tmp_path, name="relight.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    import database as db
    importlib.reload(db)
    db.init_db()
    import internal_affairs as ia
    importlib.reload(ia)
    return db, ia


def _country(db, **fields):
    cid = db.create_country(6161, "کشور ریلایت", "🏳️", country_key="relight")
    for k, v in fields.items():
        db.update_country_field(cid, k, v)
    return cid


def _give(db, cid, item_key, qty):
    conn = db.get_connection()
    with conn:
        conn.execute(
            "INSERT INTO equipment (country_id, item_key, quantity, inactive_qty) VALUES (?,?,?,0)"
            " ON CONFLICT(country_id, item_key) DO UPDATE SET quantity = ?",
            (cid, item_key, qty, qty))
    conn.close()


def _inactive(db, cid, item_key):
    conn = db.get_connection()
    row = conn.execute("SELECT COALESCE(inactive_qty,0) AS n FROM equipment"
                       " WHERE country_id = ? AND item_key = ?", (cid, item_key)).fetchone()
    conn.close()
    return int(row["n"]) if row else 0


def test_e2e_daily_cycle_relights_after_resupply(monkeypatch, tmp_path):
    """چرخه‌ی روزانه‌ی واقعی: روز ۱ کسری → خاموش؛ تأمین؛ روز ۲ → روشن."""
    db, ia = _fresh(monkeypatch, tmp_path)
    ia.set_enabled(True)
    up = config.get_building_upkeep("small_factory")
    cid = _country(db, treasury=900_000_000, oil_reserves=up["oil"] * 2, iron_ore=500_000)
    _give(db, cid, "small_factory", 6)

    day1 = datetime.datetime(2026, 9, 1, 12, 0, 0)
    out1 = ia.run_daily_cycle(db.get_country_by_id(cid), now_dt=day1)
    assert out1 is not None
    assert _inactive(db, cid, "small_factory") >= 4, "روز ۱ باید با کسری نفت خاموش شود"

    # بازیکن نفت را دوباره تأمین می‌کند (کمک/بازار/درآمد)
    db.update_country_field(cid, "oil_reserves", 50_000_000)

    day2 = datetime.datetime(2026, 9, 2, 12, 0, 0)
    out2 = ia.run_daily_cycle(db.get_country_by_id(cid), now_dt=day2)
    assert out2 is not None
    assert _inactive(db, cid, "small_factory") == 0, (
        "بعد از تأمین نفت، چرخه‌ی روز ۲ باید همه‌ی سازه‌ها را روشن کند")


def test_relight_with_ramp_active(monkeypatch, tmp_path):
    """با رمپ فعال هم بازفعال‌سازی باید کار کند (مصرف مقیاس‌شده است نه خام)."""
    monkeypatch.setattr(config, "UPKEEP_RAMP_START_DATE", "2026-09-01")
    monkeypatch.setattr(config, "UPKEEP_RAMP_DAYS", 7)
    db, ia = _fresh(monkeypatch, tmp_path)
    ia.set_enabled(True)
    up = config.get_building_upkeep("small_factory")
    cid = _country(db, treasury=900_000_000, oil_reserves=up["oil"] * 2, iron_ore=500_000)
    _give(db, cid, "small_factory", 8)

    d1 = datetime.datetime(2026, 9, 4, 9, 0, 0)
    ia.run_daily_cycle(db.get_country_by_id(cid), now_dt=d1)
    off_after_d1 = _inactive(db, cid, "small_factory")
    assert off_after_d1 > 0

    db.update_country_field(cid, "oil_reserves", 90_000_000)
    d2 = datetime.datetime(2026, 9, 5, 9, 0, 0)
    ia.run_daily_cycle(db.get_country_by_id(cid), now_dt=d2)
    assert _inactive(db, cid, "small_factory") == 0


def test_sabotage_outage_does_not_block_relight(monkeypatch, tmp_path):
    """خاموشی خرابکاری (+۱) نباید بعد از تأمین منابع بچسبد؛ چرخه‌ی بعد باید صفرش کند."""
    db, ia = _fresh(monkeypatch, tmp_path)
    ia.set_enabled(True)
    up = config.get_building_upkeep("small_factory")
    cid = _country(db, treasury=900_000_000, oil_reserves=0, iron_ore=500_000)
    _give(db, cid, "small_factory", 5)

    ia.run_daily_cycle(db.get_country_by_id(cid),
                       now_dt=datetime.datetime(2026, 9, 1, 10, 0, 0))
    assert _inactive(db, cid, "small_factory") == 5

    # خرابکاری دشمن یک واحد دیگر هم خاموش می‌کند (در حالی که همه خاموش‌اند)
    conn = db.get_connection()
    with conn:
        conn.execute("UPDATE equipment SET inactive_qty = MIN(quantity, inactive_qty + 1)"
                     " WHERE country_id = ? AND item_key = 'small_factory'", (cid,))
    conn.close()

    db.update_country_field(cid, "oil_reserves", 50_000_000)
    ia.run_daily_cycle(db.get_country_by_id(cid),
                       now_dt=datetime.datetime(2026, 9, 2, 10, 0, 0))
    assert _inactive(db, cid, "small_factory") == 0, (
        "بعد از تأمین منابع هیچ خاموشی چسبیده‌ای نباید بماند")


# ─────────── باگ گزارش بازیکن‌ها: «تأمین شد ولی روشن نشد» ───────────

def test_stale_electricity_column_self_heals_daily(monkeypatch, tmp_path):
    """ستون برقِ کهنه (پایین‌تر از ظرفیت واقعی) باید در چرخه‌ی روزانه‌ی بعدی
    بازسازی شود — حتی وقتی نگهداری هیچ تغییری نداشته. بدون این، کارخانه‌ها با
    منابع کامل و سازه‌ی روشن، تا ابد «بی‌برق» می‌مانند."""
    db, ia = _fresh(monkeypatch, tmp_path)
    ia.set_enabled(True)
    cid = _country(db, treasury=900_000_000, oil_reserves=50_000_000, iron_ore=500_000)
    _give(db, cid, "fossil_plant", 3)
    _give(db, cid, "small_factory", 6)
    # شبیه‌سازی ستون کهنه: مثلاً حذف دستی/قدیمی نیروگاه بدون recalc
    db.update_country_field(cid, "electricity", 5)

    ia.run_daily_cycle(db.get_country_by_id(cid),
                       now_dt=datetime.datetime(2026, 9, 3, 12, 0, 0))

    base = int(config.STARTING_VALUES["electricity"])
    expected = base + 3 * int(config.ALL_SHOP_ITEMS["fossil_plant"]["elec_add"])
    assert db.get_country_by_id(cid)["electricity"] == expected, (
        "چرخه‌ی روزانه باید ستون برقِ کهنه را بازسازی کند")

    p = ia.power_status(db.get_country_by_id(cid))
    assert not p["shortage"], "با منابع کامل و نیروگاه فعال نباید خاموشی برقی بماند"
    assert not p["offline"]


def test_resource_dark_units_do_not_draw_power(monkeypatch, tmp_path):
    """کارخانه‌ای که به‌خاطر کسری نفت خاموش شده نباید هم «بی‌برق» هم حساب شود
    (جریمه‌ی دوگانه) — مصرف برق فقط واحدهای واقعاً روشن است."""
    db, ia = _fresh(monkeypatch, tmp_path)
    ia.set_enabled(True)
    cid = _country(db, treasury=900_000_000, oil_reserves=0, iron_ore=500_000)
    _give(db, cid, "fossil_plant", 1)
    _give(db, cid, "small_factory", 6)

    ia.run_daily_cycle(db.get_country_by_id(cid),
                       now_dt=datetime.datetime(2026, 9, 1, 12, 0, 0))
    assert _inactive(db, cid, "small_factory") == 6  # همه به‌خاطر نفت خاموش

    p = ia.power_status(db.get_country_by_id(cid))
    assert p["industrial_need"] == 0, "واحد خاموش نباید مصرف برق صنعتی داشته باشد"
    assert not p["shortage"] and not p["offline"]
