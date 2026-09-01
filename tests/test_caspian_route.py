"""دریای خزر — مسیر بسته و مصون از محاصره و تنگه."""
import importlib
import config


def _fresh(monkeypatch, tmp_path, name="caspian.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    import database as db
    importlib.reload(db)
    db.init_db()
    return db


def test_all_five_littoral_states_are_listed():
    for k in ("iran", "russia", "kazakhstan", "turkmenistan", "azerbaijan"):
        assert k in config.CASPIAN_COUNTRIES
    assert len(config.CASPIAN_COUNTRIES) == 5


def test_pairs_inside_the_caspian_work():
    assert config.is_caspian_pair("iran", "russia")
    assert config.is_caspian_pair("kazakhstan", "azerbaijan")
    assert config.is_caspian_pair("turkmenistan", "iran")


def test_outsiders_and_self_pairs_are_rejected():
    assert not config.is_caspian_pair("iran", "china")
    assert not config.is_caspian_pair("usa", "russia")
    assert not config.is_caspian_pair("iran", "iran")
    assert not config.is_caspian_pair("", "russia")
    assert not config.is_caspian_pair(None, "russia")


def test_landlocked_littorals_keep_their_no_sea_access_status():
    """خزر «مسیر جدا» است، نه دسترسی به آب آزاد."""
    for k in ("azerbaijan", "kazakhstan", "turkmenistan"):
        assert k in config.NO_SEA_ACCESS_COUNTRIES


def test_caspian_route_is_immune_to_blockade_and_straits(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path)
    info = db.caspian_route_info("iran", "russia")
    assert info is not None
    assert info["immune_to_blockade"] is True
    assert info["immune_to_straits"] is True
    assert info["max_amount"] > 0


def test_no_caspian_route_for_outsiders(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "caspian2.db")
    assert db.caspian_route_info("iran", "china") is None
    assert db.caspian_route_available("usa", "russia") is False


def test_caspian_capacity_is_smaller_than_open_sea():
    sea = getattr(config, "TRANSPORT_CAPACITY_LIMITS", {}).get("sea", {}).get("oil", 200_000)
    assert config.CASPIAN_TRANSPORT["max_amount"] < sea
