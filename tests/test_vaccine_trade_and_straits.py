"""تجارت واکسن، مسیر خزر در بورس، و ابزار عیب‌یابی تنگه‌ها."""
import importlib
import itertools
import config


def _fresh(monkeypatch, tmp_path, name="vt.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    import database as db
    importlib.reload(db)
    db.init_db()
    return db


def _c(db, uid, key, name, **f):
    cid = db.create_country(uid, name, "🏳️", country_key=key)
    db.update_country_field(cid, "treasury", 900_000_000)
    db.update_country_field(cid, "oil_reserves", 90_000_000)
    for k, v in f.items():
        db.update_country_field(cid, k, v)
    return cid


# ─────────────── واکسن در همه‌ی مسیرها ───────────────

def test_vaccine_has_a_capacity_in_every_transport_mode():
    for mode, spec in config.TRANSPORT_CAPACITY_LIMITS.items():
        assert spec["limits"].get("vaccine_doses"), f"واکسن در {mode} سقف ندارد"


def test_sea_carries_the_most_vaccine():
    lim = {m: s["limits"]["vaccine_doses"] for m, s in config.TRANSPORT_CAPACITY_LIMITS.items()}
    assert lim["sea"] == max(lim.values())
    assert lim["sea"] > lim["air"] > lim["land"] > lim["caspian"]


def test_vaccine_aid_button_exists():
    """باگ: بک‌اند پشتیبانی می‌کرد ولی دکمه‌ای در منوی کمک خارجی نبود."""
    with open("handlers/diplomacy.py", encoding="utf-8") as f:
        assert "dip:aid_type:vaccine_doses" in f.read()


def test_vaccine_can_actually_be_sent_as_aid_by_sea(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path)
    a = _c(db, 1, "usa", "آمریکا", vaccine_doses=300_000)
    b = _c(db, 2, "uk", "انگلیس", vaccine_doses=0)

    ok, msg = db.execute_foreign_aid_transaction(a, b, "vaccine_doses", 150_000, "sea")

    assert ok, msg
    assert db.get_country_by_id(b)["vaccine_doses"] == 150_000


def test_vaccine_aid_respects_the_transport_cap(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "vt2.db")
    a = _c(db, 1, "usa", "آمریکا", vaccine_doses=900_000)
    b = _c(db, 2, "uk", "انگلیس")
    cap = config.TRANSPORT_CAPACITY_LIMITS["air"]["limits"]["vaccine_doses"]

    assert db.execute_foreign_aid_transaction(a, b, "vaccine_doses", cap, "air")[0] is True
    ok, msg = db.execute_foreign_aid_transaction(a, b, "vaccine_doses", cap + 1, "air")
    assert not ok and "ظرفیت" in msg


# ─────────────── خزر در بورس ───────────────

def test_market_rejects_caspian_for_non_littoral_pair(monkeypatch, tmp_path):
    """باگ: بورس مسیر خزر را اعتبارسنجی نمی‌کرد و آمریکا↔انگلیس را هم قبول می‌کرد."""
    db = _fresh(monkeypatch, tmp_path, "vt3.db")
    a = _c(db, 1, "usa", "آمریکا")
    b = _c(db, 2, "uk", "انگلیس")
    db.create_market_order(a, "oil", 100_000, 6)
    oid = db.get_market_orders("oil")[0]["id"]

    ok, msg, _ = db.execute_market_buy_transaction(b, oid, 1_000, transport_mode="caspian")

    assert not ok and "خزر" in msg


def test_market_allows_caspian_between_littorals(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "vt4.db")
    a = _c(db, 1, "iran", "ایران")
    b = _c(db, 2, "russia", "روسیه")
    db.create_market_order(a, "oil", 100_000, 6)
    oid = db.get_market_orders("oil")[0]["id"]

    ok, msg, meta = db.execute_market_buy_transaction(b, oid, 1_000, transport_mode="caspian")

    assert ok, msg
    assert meta["transport_cost"] >= config.TRANSPORT_CAPACITY_LIMITS["caspian"]["cost"]


# ─────────────── عیب‌یابی تنگه‌ها ───────────────

def test_strait_listing_reports_every_strait(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "vt5.db")
    rows = db.list_strait_statuses()
    assert len(rows) == len(db.STRAITS_MAPPING)
    assert all(r["status"] == "open" for r in rows), "پیش‌فرض باید باز باشد"
    assert all({"strait_key", "name", "owner_name", "status", "toll", "roe"} <= set(r) for r in rows)


def test_one_blocked_strait_silently_kills_many_sea_routes(monkeypatch, tmp_path):
    """ریشه‌ی گزارش بازیکن‌ها: «هرچی روی دریایی می‌زنیم کار نمی‌کنه»."""
    db = _fresh(monkeypatch, tmp_path, "vt6.db")
    keys = list(config.COUNTRY_STARTING_OVERRIDES)[:40]
    pairs = list(itertools.combinations(keys, 2))

    before = sum(db.get_trade_route_strait_analysis(a, b)["is_blocked"] for a, b in pairs)
    db.set_strait_status("hormuz", "blocked")
    after = sum(db.get_trade_route_strait_analysis(a, b)["is_blocked"] for a, b in pairs)

    assert before == 0
    assert after > len(pairs) * 0.10, "یک تنگه‌ی بسته باید مسیرهای زیادی را قطع کند"


def test_reopen_all_straits_unblocks_trade(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "vt7.db")
    db.set_strait_status("hormuz", "blocked")
    db.set_strait_status("suez", "toll", 500_000)

    changed = db.reopen_all_straits()

    assert changed == 2
    assert all(r["status"] == "open" for r in db.list_strait_statuses())
    assert db.reopen_all_straits() == 0, "باید idempotent باشد"


def test_sea_trade_works_again_after_reopening(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "vt8.db")
    # جفت باید از هرمز رد شود ولی مالکش (ایران) نباشد
    saudi = _c(db, 1, "saudi", "عربستان")
    china = _c(db, 2, "china", "چین")
    db.create_market_order(saudi, "oil", 200_000, 6)
    oid = db.get_market_orders("oil")[0]["id"]

    db.set_strait_status("hormuz", "blocked")
    ok_blocked, msg, _ = db.execute_market_buy_transaction(china, oid, 1_000, transport_mode="sea")
    db.reopen_all_straits()
    ok_open, msg2, _ = db.execute_market_buy_transaction(china, oid, 1_000, transport_mode="sea")

    assert not ok_blocked and "مسدود" in msg
    assert ok_open, msg2


def test_admin_panel_exposes_the_strait_screen():
    with open("handlers/admin.py", encoding="utf-8") as f:
        src = f.read()
    assert "admin:straits" in src
    assert "admin:straits_open_all" in src


# ─────────────── صحت مسیریابی تنگه‌ها ───────────────

def _crossed(db, a, b):
    return {s["strait_key"] for s in db.get_trade_route_strait_analysis(a, b)["all_crossed"]}


def test_atlantic_neighbours_cross_nothing(monkeypatch, tmp_path):
    """آمریکا→انگلیس نباید هیچ ربطی به سوئز داشته باشد."""
    db = _fresh(monkeypatch, tmp_path, "rt1.db")
    for a, b in (("usa", "uk"), ("usa", "canada"), ("uk", "france"),
                 ("germany", "usa"), ("brazil", "argentina"), ("usa", "brazil")):
        assert _crossed(db, a, b) == set(), f"{a}→{b} نباید تنگه‌ای داشته باشد"


def test_pacific_pairs_do_not_use_suez_or_malacca(monkeypatch, tmp_path):
    """باگ: آمریکا↔ژاپن از سوئز و باب‌المندب رد می‌شد، روسیه↔چین از بسفر."""
    db = _fresh(monkeypatch, tmp_path, "rt2.db")
    for a, b in (("usa", "japan"), ("usa", "china"), ("russia", "china"),
                 ("russia", "japan"), ("china", "south_korea"), ("australia", "new_zealand")):
        crossed = _crossed(db, a, b)
        assert not crossed & {"suez", "bab_el_mandeb", "bab_el_mandeb_west",
                              "bosphorus", "malacca", "malacca_north"}, f"{a}→{b}: {crossed}"


def test_genuine_long_routes_still_cross_the_right_straits(monkeypatch, tmp_path):
    """اصلاح نباید مسیرهای واقعی را هم خالی کند."""
    db = _fresh(monkeypatch, tmp_path, "rt3.db")
    assert "suez" in _crossed(db, "india", "germany")
    assert "suez" in _crossed(db, "china", "germany")
    assert "suez" in _crossed(db, "australia", "uk")
    assert _crossed(db, "japan", "india") & {"malacca", "malacca_north"}
    assert _crossed(db, "saudi", "china") & {"hormuz", "hormuz_south"}
    assert _crossed(db, "iran", "japan") & {"hormuz", "hormuz_south"}


def test_a_strait_owner_is_never_tolled_on_its_own_route(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "rt4.db")
    db.set_strait_status("hormuz", "blocked")
    assert db.get_trade_route_strait_analysis("iran", "china")["is_blocked"] is False
    assert db.get_trade_route_strait_analysis("saudi", "china")["is_blocked"] is True


def test_route_is_symmetric(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "rt5.db")
    for a, b in (("india", "germany"), ("usa", "japan"), ("saudi", "china"), ("uk", "australia")):
        assert _crossed(db, a, b) == _crossed(db, b, a), f"{a}/{b} نامتقارن است"
