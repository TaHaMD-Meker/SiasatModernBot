"""تست دکمه‌ی اهدای دُز واکسن در پنل ادمین."""
import importlib
import config


def _fresh(monkeypatch, tmp_path, name="admin_vax.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    import database as db
    importlib.reload(db)
    db.init_db()
    return db


def test_vaccine_field_is_registered_in_admin_panel():
    from handlers.admin import COUNTRY_STAT_FIELDS
    assert "vaccine_doses" in COUNTRY_STAT_FIELDS
    label, unit, step, kind = COUNTRY_STAT_FIELDS["vaccine_doses"]
    assert "واکسن" in label
    assert kind == "num"


def test_step_equals_one_national_injection_round():
    """گام دکمه باید یک نوبت تزریق سراسری باشد، نه عددی دلبخواه."""
    import internal_affairs as ia
    from handlers.admin import COUNTRY_STAT_FIELDS
    assert COUNTRY_STAT_FIELDS["vaccine_doses"][2] == ia.VACCINE_DOSES_PER_USE


def test_admin_can_grant_doses_with_the_plus_buttons(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path)
    import handlers.admin as admin
    importlib.reload(admin)
    cid = db.create_country(9001, "کشور آزمون", "🏳️", country_key="iran")
    step = admin.COUNTRY_STAT_FIELDS["vaccine_doses"][2]

    new_val, err = admin.apply_cstat_delta(cid, "vaccine_doses", 10)   # دکمه‌ی ➕ بزرگ

    assert err is None
    assert new_val == step * 10
    assert db.get_country_by_id(cid)["vaccine_doses"] == step * 10


def test_admin_can_set_an_exact_dose_count(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "admin_vax2.db")
    import handlers.admin as admin
    importlib.reload(admin)
    cid = db.create_country(9002, "کشور آزمون", "🏳️", country_key="iran")

    value, err = admin.apply_cstat_value(cid, "vaccine_doses", 137_000)

    assert err is None and value == 137_000
    assert db.get_country_by_id(cid)["vaccine_doses"] == 137_000


def test_doses_can_never_go_negative(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "admin_vax3.db")
    import handlers.admin as admin
    importlib.reload(admin)
    cid = db.create_country(9003, "کشور آزمون", "🏳️", country_key="iran")
    db.update_country_field(cid, "vaccine_doses", 50_000)

    new_val, _err = admin.apply_cstat_delta(cid, "vaccine_doses", -10)

    assert new_val == 0
    assert db.get_country_by_id(cid)["vaccine_doses"] == 0


def test_granted_doses_are_actually_usable_against_an_epidemic(monkeypatch, tmp_path):
    """دُزی که ادمین می‌دهد باید واقعاً اقدام واکسیناسیون را باز کند."""
    db = _fresh(monkeypatch, tmp_path, "admin_vax4.db")
    import handlers.admin as admin
    import internal_affairs as ia
    importlib.reload(admin)
    importlib.reload(ia)
    cid = db.create_country(9004, "کشور آزمون", "🏳️", country_key="iran")
    db.update_country_field(cid, "treasury", 900_000_000)
    _ok, _m, crisis = ia.create_crisis(cid, "epidemic", admin_id=1)

    allowed, reason = ia.check_action("vaccine_program", crisis, db.get_country_by_id(cid))
    assert not allowed and "دُز" in reason

    admin.apply_cstat_delta(cid, "vaccine_doses", 1)   # یک نوبت تزریق

    allowed, reason = ia.check_action("vaccine_program", crisis, db.get_country_by_id(cid))
    assert allowed, reason
