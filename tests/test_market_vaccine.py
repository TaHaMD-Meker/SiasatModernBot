"""بورس دُز واکسن — باگ گزارش‌شده توسط بازیکن: گزینه‌ی واکسن در بورس نبود."""
import importlib
import re
import config


def _fresh(monkeypatch, tmp_path, name="mkt_vax.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    import database as db
    importlib.reload(db)
    db.init_db()
    return db


def _market_src():
    with open("handlers/market.py", encoding="utf-8") as f:
        return f.read()


def test_vaccine_is_a_tradable_commodity_in_config():
    assert "vaccine_doses" in config.COMMODITY_MARKET_BOUNDS


def test_market_menu_has_a_vaccine_button():
    """باگ بازیکن: دکمه‌ی بورس واکسن اصلاً وجود نداشت."""
    assert "market:cat:vaccine_doses" in _market_src()


def test_sell_picker_has_a_vaccine_button():
    assert "market:sell_type:vaccine_doses" in _market_src()


def test_every_resource_column_map_knows_vaccine():
    """res_cols بدون این کلید، موقع فروش واکسن KeyError می‌داد."""
    for block in re.findall(r"res_cols = \{[^}]*\}", _market_src()):
        assert '"vaccine_doses"' in block, f"کلید واکسن ندارد: {block}"


def test_market_stats_reports_vaccine(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path)
    stats = db.get_market_stats()
    assert "vaccine_doses" in stats


def test_player_can_list_vaccine_doses_for_sale(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "mkt_vax2.db")
    cid = db.create_country(7701, "کشور آزمون", "🏳️", country_key="iran")
    db.update_country_field(cid, "vaccine_doses", 200_000)

    ok, msg = db.create_market_order(cid, "vaccine_doses", 150_000, 180)

    assert ok, msg
    assert db.get_country_by_id(cid)["vaccine_doses"] == 50_000
    assert any(o["resource_type"] == "vaccine_doses" for o in db.get_market_orders("vaccine_doses"))


def test_vaccine_order_shows_up_in_market_stats(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "mkt_vax3.db")
    cid = db.create_country(7702, "کشور آزمون", "🏳️", country_key="iran")
    db.update_country_field(cid, "vaccine_doses", 100_000)
    db.create_market_order(cid, "vaccine_doses", 100_000, 250)

    assert db.get_market_stats()["vaccine_doses"]["lowest_active"] == 250


def test_selling_more_doses_than_owned_is_rejected(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "mkt_vax4.db")
    cid = db.create_country(7703, "کشور آزمون", "🏳️", country_key="iran")
    db.update_country_field(cid, "vaccine_doses", 10_000)

    ok, _msg = db.create_market_order(cid, "vaccine_doses", 50_000, 180)

    assert not ok
    assert db.get_country_by_id(cid)["vaccine_doses"] == 10_000
