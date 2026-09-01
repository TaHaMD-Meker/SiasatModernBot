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
    sea = config.TRANSPORT_CAPACITY_LIMITS["sea"]["limits"]["oil"]
    caspian = config.TRANSPORT_CAPACITY_LIMITS["caspian"]["limits"]["oil"]
    assert caspian < sea
    for res, sea_cap in config.TRANSPORT_CAPACITY_LIMITS["sea"]["limits"].items():
        assert config.TRANSPORT_CAPACITY_LIMITS["caspian"]["limits"][res] < sea_cap, res


# ─────────── اتصال واقعی به ترابری ───────────

def _pair(db):
    iran = db.create_country(9101, "ایران", "🇮🇷", country_key="iran")
    rus = db.create_country(9102, "روسیه", "🇷🇺", country_key="russia")
    for c in (iran, rus):
        db.update_country_field(c, "treasury", 900_000_000)
        db.update_country_field(c, "oil_reserves", 90_000_000)
    return iran, rus


def test_caspian_is_a_real_transport_mode():
    assert "caspian" in config.TRANSPORT_CAPACITY_LIMITS
    assert config.TRANSPORT_CAPACITY_LIMITS["caspian"]["cost"] > 0


def test_caspian_transfer_actually_delivers(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "casp_run.db")
    iran, rus = _pair(db)
    before = db.get_country_by_id(rus)["oil_reserves"]

    ok, msg = db.execute_foreign_aid_transaction(iran, rus, "oil", 300_000, "caspian")

    assert ok, msg
    assert db.get_country_by_id(rus)["oil_reserves"] - before == 300_000


def test_caspian_ignores_blockade_and_closed_straits(monkeypatch, tmp_path):
    """قلب فایده‌ی خزر: راه فرار ایرانِ محاصره‌شده."""
    db = _fresh(monkeypatch, tmp_path, "casp_immune.db")
    iran, rus = _pair(db)
    usa = db.create_country(9103, "آمریکا", "🇺🇸", country_key="usa")
    db.set_strait_status("hormuz", "blocked")
    db.create_naval_blockade(usa, iran, {})

    ok_c, _ = db.execute_foreign_aid_transaction(iran, rus, "oil", 100_000, "caspian")
    ok_s, _ = db.execute_foreign_aid_transaction(iran, rus, "oil", 100_000, "sea")

    assert ok_c is True, "خزر باید مصون باشد"
    assert ok_s is False, "دریای آزاد باید مسدود بماند"


def test_caspian_rejects_non_littoral_pairs(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "casp_rej.db")
    saudi = db.create_country(9104, "عربستان", "🇸🇦", country_key="saudi")
    usa = db.create_country(9105, "آمریکا", "🇺🇸", country_key="usa")
    for c in (saudi, usa):
        db.update_country_field(c, "treasury", 900_000_000)
        db.update_country_field(c, "oil_reserves", 90_000_000)

    ok, msg = db.execute_foreign_aid_transaction(saudi, usa, "oil", 1_000, "caspian")

    assert not ok and "خزر" in msg


def test_caspian_capacity_cap_is_enforced(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "casp_cap.db")
    iran, rus = _pair(db)
    cap = config.TRANSPORT_CAPACITY_LIMITS["caspian"]["limits"]["oil"]

    assert db.execute_foreign_aid_transaction(iran, rus, "oil", cap, "caspian")[0] is True
    ok, msg = db.execute_foreign_aid_transaction(iran, rus, "oil", cap + 1, "caspian")
    assert not ok and "ظرفیت" in msg


def test_passage_won_bypasses_the_block(monkeypatch, tmp_path):
    """باگی که تست دود گرفت: بعد از برد قرعه، محموله دوباره رد می‌شد."""
    db = _fresh(monkeypatch, tmp_path, "casp_won.db")
    saudi = db.create_country(9106, "عربستان", "🇸🇦", country_key="saudi")
    usa = db.create_country(9107, "آمریکا", "🇺🇸", country_key="usa")
    for c in (saudi, usa):
        db.update_country_field(c, "treasury", 900_000_000)
        db.update_country_field(c, "oil_reserves", 90_000_000)
    db.set_strait_status("hormuz", "blocked")

    assert db.execute_foreign_aid_transaction(saudi, usa, "oil", 5_000, "sea")[0] is False
    ok, msg = db.execute_foreign_aid_transaction(saudi, usa, "oil", 5_000, "sea", passage_won=True)
    assert ok, msg
