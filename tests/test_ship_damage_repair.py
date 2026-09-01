"""آسیب و تعمیر شناور — ناوهای بزرگ در حادثه غرق نمی‌شوند."""
import datetime
import importlib
import config


def _fresh(monkeypatch, tmp_path, name="ships.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    import database as db
    importlib.reload(db)
    db.init_db()
    return db


def _navy(db, cid, key, name, qty, price=20_000_000):
    conn = db.get_connection()
    with conn:
        conn.execute(
            "INSERT INTO country_assets (country_id, country_key, category, equipment_name,"
            " equipment_key, amount, buy_price, under_repair_qty) VALUES (?,?,?,?,?,?,?,0)",
            (cid, "iran", "Navy", name, key, qty, price))
    conn.close()


def _country(db, **f):
    cid = db.create_country(4401, "کشور آزمون", "🏳️", country_key="iran")
    for k, v in f.items():
        db.update_country_field(cid, k, v)
    return cid


# ───────────────────── رده‌بندی ─────────────────────

def test_capital_ships_are_recognised():
    for n in ("Nimitz Class Carrier", "Ford Class Carrier", "Ohio Class SSBN Sub",
              "Ticonderoga Cruiser", "Wasp Class Ship", "ناو هواپیمابر سنگین بومی Admiral Kuznetsov"):
        assert config.ship_tier(n) == "capital", n


def test_heavy_medium_light_tiers():
    assert config.ship_tier("Arleigh Burke Destroyer") == "heavy"
    assert config.ship_tier("زیردریایی کلاس کیلو") == "heavy"
    assert config.ship_tier("ناوچه کلاس موج") == "medium"
    assert config.ship_tier("کوروت بومی کلاس Al Jubail") == "medium"
    assert config.ship_tier("قایق تندرو رزمی") == "light"
    assert config.ship_tier("شناور بی‌سرنشین دریایی") == "light"


def test_asw_frigate_is_not_mistaken_for_a_submarine():
    """«ضدزیردریایی» شامل «زیردریایی» است — این تله باید بسته باشد."""
    assert config.ship_tier("ناوچه موشک‌انداز نسل جدید ضدزیردریایی ASW") == "medium"


def test_unknown_ship_falls_back_to_medium():
    assert config.ship_tier("یک چیز عجیب") == config.SHIP_TIER_DEFAULT
    assert config.ship_tier("") == config.SHIP_TIER_DEFAULT
    assert config.ship_tier(None) == config.SHIP_TIER_DEFAULT


def test_capital_ships_can_never_sink_in_an_incident():
    """قلب درخواست بازیکن: ناو بزرگ در حادثه غرق نمی‌شود."""
    assert config.SHIP_SINK_CHANCE["capital"] == 0
    assert config.ship_repair_spec("Nimitz Class Carrier", 46_000_000)["can_sink"] is False
    assert config.ship_repair_spec("قایق تندرو رزمی", 500_000)["can_sink"] is True


def test_bigger_ships_take_longer_to_repair():
    hours = {t: config.SHIP_REPAIR_HOURS[t][1] for t in ("capital", "heavy", "medium", "light")}
    assert hours["capital"] > hours["heavy"] > hours["medium"] >= hours["light"]
    assert hours["capital"] == 240


def test_heavy_damage_costs_more_than_light():
    light = config.ship_repair_spec("Nimitz Class Carrier", 46_000_000, "light")
    heavy = config.ship_repair_spec("Nimitz Class Carrier", 46_000_000, "heavy")
    assert heavy["hours"] > light["hours"]
    assert heavy["money"] > light["money"]
    assert heavy["iron_ore"] > light["iron_ore"]


# ───────────────────── آسیب ─────────────────────

def test_damaged_ship_stays_in_inventory_but_goes_offline(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path)
    cid = _country(db)
    _navy(db, cid, "nimitz", "Nimitz Class Carrier", 10, 46_000_000)

    res = db.damage_ships(cid, "nimitz", 3)

    assert res["damaged"] == 3
    assert res["tier"] == "capital"
    rows = db.get_country_assets(cid, category="Navy")
    row = next(r for r in rows if r["equipment_key"] == "nimitz")
    assert row["amount"] == 10, "شناور نباید از انبار حذف شود"
    assert db.available_ship_count(row) == 7


def test_damaged_ships_do_not_count_toward_naval_power(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ships_pow.db")
    cid = _country(db)
    _navy(db, cid, "burke", "Arleigh Burke Destroyer", 10, 30_000_000)

    full = db.calculate_naval_power(cid)
    db.damage_ships(cid, "burke", 5)
    hurt = db.calculate_naval_power(cid)

    assert 0 < hurt < full


def test_cannot_damage_more_than_are_operational(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ships_cap.db")
    cid = _country(db)
    _navy(db, cid, "boat", "قایق تندرو رزمی", 4, 500_000)

    assert db.damage_ships(cid, "boat", 10)["damaged"] == 4
    assert db.damage_ships(cid, "boat", 5)["damaged"] == 0, "همه قبلاً در تعمیرند"


def test_damaging_an_unknown_ship_is_safe(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ships_nf.db")
    cid = _country(db)
    assert db.damage_ships(cid, "ghost_ship", 3)["damaged"] == 0
    assert db.damage_ships(cid, "ghost_ship", 0)["damaged"] == 0


def test_new_damage_never_shortens_an_existing_repair(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ships_ext.db")
    cid = _country(db)
    _navy(db, cid, "nimitz", "Nimitz Class Carrier", 5, 46_000_000)
    now = datetime.datetime(2026, 9, 1, 8, 0, 0)

    heavy = db.damage_ships(cid, "nimitz", 1, "heavy", now)      # ۲۴۰ ساعت
    light = db.damage_ships(cid, "nimitz", 1, "light", now)      # ۹۶ ساعت

    assert light["ready_at"] == heavy["ready_at"], "آسیب سبک نباید موعد سنگین را جلو بیندازد"


# ───────────────────── غرق ─────────────────────

def test_sinking_removes_from_inventory(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ships_sink.db")
    cid = _country(db)
    _navy(db, cid, "boat", "قایق تندرو رزمی", 20, 500_000)

    assert db.sink_ships(cid, "boat", 6) == 6
    row = next(r for r in db.get_country_assets(cid, category="Navy") if r["equipment_key"] == "boat")
    assert row["amount"] == 14


def test_sinking_keeps_repair_counter_consistent(monkeypatch, tmp_path):
    """اگر بیشتر از فروندهای سالم غرق شود، شمارنده‌ی تعمیر نباید از موجودی بگذرد."""
    db = _fresh(monkeypatch, tmp_path, "ships_sink2.db")
    cid = _country(db)
    _navy(db, cid, "boat", "قایق تندرو رزمی", 10, 500_000)
    db.damage_ships(cid, "boat", 8)

    db.sink_ships(cid, "boat", 9)

    row = next(r for r in db.get_country_assets(cid, category="Navy") if r["equipment_key"] == "boat")
    assert row["amount"] == 1
    assert row["under_repair_qty"] <= row["amount"], "شمارنده‌ی تعمیر از موجودی بیشتر شد"
    assert db.available_ship_count(row) >= 0


# ───────────────────── تعمیر ─────────────────────

def test_repair_completes_after_the_timer_and_costs_money_and_iron(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ships_rep.db")
    cid = _country(db, treasury=500_000_000, iron_ore=200_000)
    _navy(db, cid, "burke", "Arleigh Burke Destroyer", 6, 30_000_000)
    now = datetime.datetime(2026, 9, 1, 8, 0, 0)
    db.damage_ships(cid, "burke", 2, "heavy", now)

    before = db.get_country_by_id(cid)
    assert db.process_ship_repairs(cid, now + datetime.timedelta(hours=1)) == [], "زود است"

    done = db.process_ship_repairs(cid, now + datetime.timedelta(hours=200))
    after = db.get_country_by_id(cid)

    assert done and done[0]["qty"] == 2
    assert before["treasury"] - after["treasury"] == done[0]["money"] > 0
    assert before["iron_ore"] - after["iron_ore"] == done[0]["iron_ore"] > 0
    row = next(r for r in db.get_country_assets(cid, category="Navy") if r["equipment_key"] == "burke")
    assert db.available_ship_count(row) == 6


def test_repair_without_iron_leaves_the_ship_in_dock(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ships_noiron.db")
    cid = _country(db, treasury=500_000_000, iron_ore=0)
    _navy(db, cid, "nimitz", "Nimitz Class Carrier", 3, 46_000_000)
    now = datetime.datetime(2026, 9, 1, 8, 0, 0)
    db.damage_ships(cid, "nimitz", 1, "heavy", now)

    done = db.process_ship_repairs(cid, now + datetime.timedelta(hours=300))

    assert done == [], "بدون فولاد نباید تعمیر شود"
    row = next(r for r in db.get_country_assets(cid, category="Navy") if r["equipment_key"] == "nimitz")
    assert row["under_repair_qty"] == 1


def test_partial_repair_when_resources_only_cover_some(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ships_part.db")
    spec = config.ship_repair_spec("Arleigh Burke Destroyer", 30_000_000, "heavy")
    cid = _country(db, treasury=spec["money"] * 2, iron_ore=spec["iron_ore"] * 2)
    _navy(db, cid, "burke", "Arleigh Burke Destroyer", 8, 30_000_000)
    now = datetime.datetime(2026, 9, 1, 8, 0, 0)
    db.damage_ships(cid, "burke", 5, "heavy", now)

    done = db.process_ship_repairs(cid, now + datetime.timedelta(hours=200))

    assert done[0]["qty"] == 2
    assert done[0]["still_waiting"] == 3
    c = db.get_country_by_id(cid)
    assert c["treasury"] >= 0 and c["iron_ore"] >= 0


def test_repair_listing_reports_hours_left(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ships_list.db")
    cid = _country(db)
    _navy(db, cid, "nimitz", "Nimitz Class Carrier", 4, 46_000_000)
    db.damage_ships(cid, "nimitz", 2, "heavy")

    lst = db.get_ships_under_repair(cid)

    assert len(lst) == 1
    e = lst[0]
    assert e["qty"] == 2 and e["operational"] == 2
    assert e["tier"] == "capital"
    assert 200 < e["hours_left"] <= 240


def test_no_repairs_no_charges(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ships_none.db")
    cid = _country(db, treasury=1_000_000, iron_ore=5_000)
    _navy(db, cid, "burke", "Arleigh Burke Destroyer", 3, 30_000_000)
    before = db.get_country_by_id(cid)

    assert db.process_ship_repairs(cid) == []

    after = db.get_country_by_id(cid)
    assert before["treasury"] == after["treasury"]
    assert before["iron_ore"] == after["iron_ore"]
    assert db.get_ships_under_repair(cid) == []
