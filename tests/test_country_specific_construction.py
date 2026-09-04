"""سازه‌سازی کشورمحور: خوراک پالایشگاه غیرنفتی، فهرست واقعی معادن اورانیوم، زنجیره‌ی هسته‌ای.

مبنا: واقعیت. کشورهای بدون میدان نفتی نفت کافی برای خوراک یک‌میلیون‌بشکه‌ای
پالایشگاه ندارند (آلمان ~۶۵۰ هزار بشکه ذخیره)؛ معادن اورانیوم فقط برای ۱۳
کشوری است که واقعاً معدن دارند؛ و هر مجتمع غنی‌سازی باید بتواند یک نیروگاه
را سوخت‌رسانی کند.
"""
import importlib

import pytest

import config


def _fresh(monkeypatch, tmp_path, name="csc.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    import database as db
    importlib.reload(db)
    db.init_db()
    return db


def _country(db, key, player_id, **fields):
    cid = db.create_country(player_id, "کشور آزمون", "🏳️", country_key=key)
    for k, v in fields.items():
        db.update_country_field(cid, k, v)
    return cid


# ───────────── خوراک احداث وابسته به کشور ─────────────

def test_non_oil_refinery_construction_needs_only_250k(monkeypatch, tmp_path):
    """کشور غیرنفتی با ذخیره‌ی ۴۰۰ هزار بشکه باید بتواند پالایشگاه بسازد (۲۵۰k)."""
    db = _fresh(monkeypatch, tmp_path)
    cid = _country(db, "germany", 7001, treasury=30_000_000, oil_reserves=400_000,
                   iron_ore=10_000)
    ok, msg = db.buy_item_transaction(cid, "oil_refinery", 1, 25_000_000, "پالایشگاه")
    assert ok, msg
    c = db.get_country_by_id(cid)
    assert c["oil_reserves"] == 400_000 - 250_000, "باید دقیقاً ۲۵۰ هزار بشکه کسر شود"


def test_oil_country_refinery_still_needs_full_1m(monkeypatch, tmp_path):
    """کشور نفتی همان خوراک کامل یک‌میلیون‌بشکه‌ای را می‌دهد."""
    db = _fresh(monkeypatch, tmp_path)
    cid = _country(db, "iran", 7002, treasury=30_000_000, oil_reserves=600_000,
                   iron_ore=10_000)
    ok, msg = db.buy_item_transaction(cid, "oil_refinery", 1, 25_000_000, "پالایشگاه")
    assert not ok, "با ۶۰۰ هزار بشکه نباید پالایشگاهِ نفتی ساختنی باشد"
    assert "نفت" in msg

    db.update_country_field(cid, "oil_reserves", 1_100_000)
    ok, msg = db.buy_item_transaction(cid, "oil_refinery", 1, 25_000_000, "پالایشگاه")
    assert ok, msg
    assert db.get_country_by_id(cid)["oil_reserves"] == 100_000


def test_other_buildings_keep_catalog_oil_req(monkeypatch, tmp_path):
    """تنها پالایشگاه استثناست؛ بقیه‌ی سازه‌ها خوراک کاتالوگی دارند."""
    assert config.get_construction_oil_req("fossil_plant", "germany") == \
        int(config.ALL_SHOP_ITEMS["fossil_plant"]["oil_req"])
    assert config.get_construction_oil_req("large_factory", "japan") == \
        int(config.ALL_SHOP_ITEMS["large_factory"]["oil_req"])


# ───────────── فهرست واقعی معادن اورانیوم (۱۳ کشور) ─────────────

def test_uranium_mine_allowed_countries_are_the_13_real_miners():
    """فهرست باید دقیقاً ۱۳ کشورِ دارای معدن اورانیوم در واقعیت باشد."""
    expected = {"kazakhstan", "canada", "russia", "australia", "china", "usa",
                "iran", "brazil", "south_africa", "ukraine", "india",
                "uzbekistan", "mongolia"}
    allowed = set(config.ALL_SHOP_ITEMS["uranium_mine"].get("allowed_countries", []))
    assert len(allowed) == 13, f"باید ۱۳ کشور باشد؛ الان {len(allowed)}"
    assert allowed == expected
    assert "jordan" not in allowed, "اردن معدن اورانیوم فعال ندارد"


def test_enrichment_outsupplies_one_reactor():
    """هر مجتمع غنی‌سازی باید بتواند دست‌کم یک نیروگاه هسته‌ای را سوخت‌رسانی کند."""
    out = int(config.ALL_SHOP_ITEMS["enrichment_facility"]["nuclear_fuel_daily_add"])
    need = int(config.get_building_upkeep("nuclear_plant").get("nuclear_fuel", 0))
    assert out >= need, f"غنی‌سازی {out} < مصرف نیروگاه {need} — زنجیره قفل می‌شود"
