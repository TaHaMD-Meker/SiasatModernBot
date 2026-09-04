"""تست‌های نگهداری روزانه‌ی سازه‌ها: مصرف منابع، خاموشی جزئی، بازفعال‌سازی."""
import importlib
import pytest

import config


def _fresh(monkeypatch, tmp_path, name="upkeep.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    import database as db
    importlib.reload(db)
    db.init_db()
    return db


def _country(db, key="iran", **fields):
    cid = db.create_country(5551, "کشور آزمون", "🏳️", country_key=key)
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


# ─────────────────────────── کانفیگ ───────────────────────────

def test_every_shop_item_has_an_upkeep_entry():
    """هیچ سازه‌ای نباید از قلم بیفتد، وگرنه فاوست رایگان باقی می‌ماند."""
    missing = [k for k in config.ALL_SHOP_ITEMS if k not in config.BUILDING_UPKEEP]
    assert not missing, f"سازه‌های بدون نگهداری: {missing}"


def test_money_upkeep_follows_the_configured_ratio():
    """با نسبت صفر هیچ سازه‌ای نباید هزینه‌ی نقدی داشته باشد."""
    for key, item in config.ALL_SHOP_ITEMS.items():
        income = int(item.get("income_add", 0) or 0)
        expected = int(income * config.UPKEEP_INCOME_RATIO)
        got = config.get_building_upkeep(key).get("money", 0)
        assert got == expected


def test_no_cash_cost_while_ratio_is_zero():
    """طراحی فعلی: فشار روی منابع است نه خزانه."""
    if config.UPKEEP_INCOME_RATIO != 0:
        pytest.skip("نسبت نقدی صفر نیست")
    for key in config.ALL_SHOP_ITEMS:
        assert "money" not in config.get_building_upkeep(key)


def test_every_building_consumes_at_least_one_resource():
    """هیچ سازه‌ای نباید کاملاً مجانی بماند."""
    free = [k for k in config.ALL_SHOP_ITEMS if not config.get_building_upkeep(k)]
    assert not free, f"سازه‌های کاملاً مجانی: {free}"


def test_electricity_demand_stays_within_world_capacity():
    """اگر مصرف برق از سقف تولید بگذرد، بازی قفل می‌شود."""
    cap = sum(v.get("elec_add", 0) * v.get("max_limit", 1) for v in config.ALL_SHOP_ITEMS.values())
    need = sum(config.get_building_upkeep(k).get("elec", 0) * v.get("max_limit", 1)
               for k, v in config.ALL_SHOP_ITEMS.items())
    assert need < cap, f"مصرف برق {need} از ظرفیت {cap} بیشتر است"


def test_clean_power_plants_burn_no_oil_but_fossil_does():
    for clean in ("solar_plant", "wind_plant", "hydro_plant", "nuclear_plant"):
        assert config.get_building_upkeep(clean).get("oil", 0) == 0
    assert config.get_building_upkeep("fossil_plant")["oil"] > 0


def test_ramp_factor_ramps_then_saturates(monkeypatch):
    monkeypatch.setattr(config, "UPKEEP_RAMP_START_DATE", "2026-09-01")
    monkeypatch.setattr(config, "UPKEEP_RAMP_DAYS", 7)
    assert config.upkeep_ramp_factor("2026-08-31") == 0.0
    assert config.upkeep_ramp_factor("2026-09-01") == pytest.approx(1 / 8, abs=1e-3)
    assert config.upkeep_ramp_factor("2026-09-04") == pytest.approx(4 / 8, abs=1e-3)
    assert config.upkeep_ramp_factor("2026-09-30") == 1.0
    monkeypatch.setattr(config, "UPKEEP_RAMP_START_DATE", None)
    assert config.upkeep_ramp_factor("2026-09-01") == 1.0


# ─────────────────────────── مصرف ───────────────────────────

def test_upkeep_deducts_resources_when_country_is_rich(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path)
    cid = _country(db, treasury=900_000_000, oil_reserves=50_000_000, iron_ore=500_000)
    _give(db, cid, "large_factory", 3)

    before = db.get_country_by_id(cid)
    res = db.apply_building_upkeep(cid)

    assert res["ok"] is True
    assert res["shut_down"] == []
    after = db.get_country_by_id(cid)
    up = config.get_building_upkeep("large_factory")
    assert before["oil_reserves"] - after["oil_reserves"] == up["oil"] * 3
    assert before["iron_ore"] - after["iron_ore"] == up["iron_ore"] * 3
    assert before["treasury"] - after["treasury"] == up.get("money", 0) * 3


def test_upkeep_is_idempotent_shape(monkeypatch, tmp_path):
    """اجرای دوباره نباید سازه‌ی سالم را خاموش کند."""
    db = _fresh(monkeypatch, tmp_path)
    cid = _country(db, treasury=900_000_000, oil_reserves=50_000_000, iron_ore=500_000)
    _give(db, cid, "small_factory", 5)
    for _ in range(3):
        res = db.apply_building_upkeep(cid)
        assert res["shut_down"] == []
    assert _inactive(db, cid, "small_factory") == 0


# ─────────────────────── خاموشی جزئی ───────────────────────

def test_partial_shutdown_only_kills_what_it_must(monkeypatch, tmp_path):
    """۱۰ کارخانه با سوخت ۷ تا → دقیقاً همه خاموش نشوند."""
    db = _fresh(monkeypatch, tmp_path)
    up = config.get_building_upkeep("small_factory")
    cid = _country(db, treasury=900_000_000, oil_reserves=up["oil"] * 7, iron_ore=500_000)
    _give(db, cid, "small_factory", 10)

    res = db.apply_building_upkeep(cid)

    off = _inactive(db, cid, "small_factory")
    assert 0 < off < 10, "خاموشی باید جزئی باشد نه همه‌یا‌هیچ"
    assert 10 - off <= 7
    assert res["ok"] is False
    assert "oil" in res["shortages"]
    assert res["income_lost"] > 0
    assert db.get_country_by_id(cid)["oil_reserves"] >= 0


def test_shutdown_reports_names_and_lost_income(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path)
    cid = _country(db, treasury=900_000_000, oil_reserves=0, iron_ore=0)
    _give(db, cid, "medium_factory", 4)

    res = db.apply_building_upkeep(cid)

    assert res["shut_down"], "باید خاموشی گزارش شود"
    entry = res["shut_down"][0]
    assert entry["key"] == "medium_factory"
    assert entry["qty"] == 4
    text = db.format_upkeep_report(res)
    assert "کمبود منابع" in text and "خاموش" in text
    assert "درآمد از‌دست‌رفته" in text


def test_clean_plant_survives_a_total_oil_blackout(monkeypatch, tmp_path):
    """نیروگاه خورشیدی نفت نمی‌خورد، پس با نفت صفر هم باید روشن بماند."""
    db = _fresh(monkeypatch, tmp_path)
    cid = _country(db, treasury=900_000_000, oil_reserves=0)
    _give(db, cid, "solar_plant", 5)
    _give(db, cid, "fossil_plant", 5)

    db.apply_building_upkeep(cid)

    assert _inactive(db, cid, "solar_plant") == 0
    assert _inactive(db, cid, "fossil_plant") == 5


# ─────────────────── بازفعال‌سازی خودکار ───────────────────

def test_buildings_come_back_on_when_resources_return(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path)
    cid = _country(db, treasury=900_000_000, oil_reserves=0, iron_ore=0)
    _give(db, cid, "large_factory", 3)

    db.apply_building_upkeep(cid)
    assert _inactive(db, cid, "large_factory") == 3

    db.update_country_field(cid, "oil_reserves", 50_000_000)
    db.update_country_field(cid, "iron_ore", 500_000)
    res = db.apply_building_upkeep(cid)

    assert _inactive(db, cid, "large_factory") == 0
    assert res["reactivated"], "بازفعال‌سازی باید گزارش شود"
    assert res["reactivated"][0]["qty"] == 3
    text = db.format_upkeep_report(res)
    assert "دوباره وارد مدار شدند" in text


# ─────────────── سازه‌ی خاموش بونوس نمی‌دهد ───────────────

def test_inactive_buildings_stop_paying_income(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path)
    cid = _country(db, treasury=900_000_000, oil_reserves=50_000_000, iron_ore=500_000)
    _give(db, cid, "large_factory", 4)

    db.apply_building_upkeep(cid)
    rich = db.recalc_country_civ_effects(cid)["daily_income"]

    db.update_country_field(cid, "oil_reserves", 0)
    db.update_country_field(cid, "iron_ore", 0)
    db.apply_building_upkeep(cid)
    poor = db.recalc_country_civ_effects(cid)["daily_income"]

    assert poor < rich, "درآمد سازه‌ی خاموش نباید حساب شود"
    inc = config.ALL_SHOP_ITEMS["large_factory"]["income_add"]
    assert rich - poor == inc * 4


def test_inactive_power_plant_stops_adding_electricity(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path)
    cid = _country(db, treasury=900_000_000, oil_reserves=50_000_000)
    _give(db, cid, "fossil_plant", 3)

    db.apply_building_upkeep(cid)
    with_power = db.recalc_country_civ_effects(cid)["electricity"]

    db.update_country_field(cid, "oil_reserves", 0)
    db.apply_building_upkeep(cid)
    without = db.recalc_country_civ_effects(cid)["electricity"]

    assert with_power - without == config.ALL_SHOP_ITEMS["fossil_plant"]["elec_add"] * 3


# ─────────────────────── حالات مرزی ───────────────────────

def test_country_with_no_buildings_is_untouched(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path)
    cid = _country(db, treasury=10_000_000, oil_reserves=1_000_000)
    before = db.get_country_by_id(cid)
    res = db.apply_building_upkeep(cid)
    after = db.get_country_by_id(cid)
    assert res["ok"] is True and res["shut_down"] == []
    assert before["treasury"] == after["treasury"]
    assert before["oil_reserves"] == after["oil_reserves"]


def test_ramp_zero_disables_upkeep_entirely(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "UPKEEP_RAMP_START_DATE", "2026-12-01")
    cid = _country(db, treasury=900_000_000, oil_reserves=0)
    _give(db, cid, "large_factory", 3)

    res = db.apply_building_upkeep(cid, today_str="2026-09-01")

    assert res["ramp"] == 0.0
    assert _inactive(db, cid, "large_factory") == 0
    assert db.get_country_by_id(cid)["treasury"] == 900_000_000


def test_upkeep_never_pushes_stock_below_zero(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path)
    cid = _country(db, treasury=1_000, oil_reserves=10, grain=5, iron_ore=1)
    _give(db, cid, "industrial_complex", 3)
    _give(db, cid, "house", 20)

    db.apply_building_upkeep(cid)

    c = db.get_country_by_id(cid)
    for field in ("oil_reserves", "grain", "iron_ore"):
        assert c[field] >= 0, f"{field} منفی شد"


def test_format_report_is_silent_when_nothing_happened():
    assert db_format_silent() == ""


def db_format_silent():
    import database as db
    return db.format_upkeep_report({"ok": True, "shortages": {}, "shut_down": [],
                                    "reactivated": [], "consumed": {}, "income_lost": 0, "ramp": 1.0})


# ─────────────── آهن به‌عنوان مصالح ساخت ───────────────

def test_every_building_needs_iron_to_build():
    """ساخت هر سازه باید آهن و فولاد لازم داشته باشد."""
    free = [k for k, v in config.ALL_SHOP_ITEMS.items() if not int(v.get("iron_req", 0) or 0)]
    assert not free, f"سازه‌های بدون نیاز به آهن: {free}"


def test_iron_build_cost_scales_with_project_size():
    """پروژه‌ی گران‌تر باید آهن بیشتری بخواهد."""
    small = config.ALL_SHOP_ITEMS["small_factory"]
    large = config.ALL_SHOP_ITEMS["large_factory"]
    huge = config.ALL_SHOP_ITEMS["industrial_complex"]
    assert small["iron_req"] < large["iron_req"] < huge["iron_req"]
    assert config.ALL_SHOP_ITEMS["house"]["iron_req"] < config.ALL_SHOP_ITEMS["skyscraper"]["iron_req"]


def test_bootstrap_is_possible_from_default_iron_stock():
    """با موجودی پیش‌فرض باید بشود معدن آهن ساخت، وگرنه بازیکن قفل می‌شود."""
    default_iron = config.STARTING_VALUES.get("iron_ore", 0)
    assert config.ALL_SHOP_ITEMS["iron_mine"]["iron_req"] <= default_iron


def test_building_purchase_is_blocked_without_iron(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "iron_gate.db")
    cid = _country(db, treasury=900_000_000, oil_reserves=90_000_000,
                   gold=5_000, microchips=50_000, iron_ore=0)
    price = config.ALL_SHOP_ITEMS["large_factory"]["price"]
    ok, msg = db.buy_item_transaction(cid, "large_factory", 1, price, "کارخانه بزرگ")
    assert not ok
    assert "آهن" in msg


def test_building_purchase_consumes_iron(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "iron_pay.db")
    need = config.ALL_SHOP_ITEMS["large_factory"]["iron_req"]
    cid = _country(db, treasury=900_000_000, oil_reserves=90_000_000,
                   gold=5_000, microchips=50_000, iron_ore=need + 500)
    price = config.ALL_SHOP_ITEMS["large_factory"]["price"]
    ok, msg = db.buy_item_transaction(cid, "large_factory", 1, price, "کارخانه بزرگ")
    assert ok, msg
    assert db.get_country_by_id(cid)["iron_ore"] == 500


# ─────────────── واقع‌گرایی مصرف (بالانس نفت) ───────────────

def test_upkeep_oil_is_realistic_not_income_linked():
    """هیچ سازه‌ای نباید معادل یک نفتکش در روز بسوزاند؛ سقف واقعی = نیروگاه فسیلی."""
    for key in config.ALL_SHOP_ITEMS:
        oil = config.get_building_upkeep(key).get("oil", 0)
        assert oil <= 20_000, f"{key}: {oil:,} بشکه/روز غیرواقعی است (سقف ۲۰هزار = نیروگاه فسیلی)"


def test_refinery_is_net_positive_even_for_non_oil_countries():
    """پالایشگاه نباید خودش نفت‌خور کشور باشد؛ حتی کشور غیرنفتی (تولید ۲۵k) خالص‌مثبت بماند."""
    use = config.get_building_upkeep("oil_refinery").get("oil", 0)
    assert use < 25_000, "پالایشگاه در کشور غیرنفتی نباید بیشتر از تولیدش مصرف کند"


def test_full_buildout_oil_demand_stays_within_a_major_producer():
    """جمع مصرف نفت همه‌ی سازه‌ها در سقف مجاز باید کمتر از تولید یک تولیدکننده‌ی
    بزرگ (عربستان، ۱۰ میلیون بشکه/روز) باشد وگرنه اقتصاد سازه قفل می‌شود."""
    total = sum(config.get_building_upkeep(k).get("oil", 0) * int(v.get("max_limit", 1))
                for k, v in config.ALL_SHOP_ITEMS.items())
    assert total < 10_000_000, f"مصرف سقف {total:,} بشکه/روز از تولید عربستان می‌گذرد"
