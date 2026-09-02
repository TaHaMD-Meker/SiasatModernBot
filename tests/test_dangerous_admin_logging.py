# -*- coding: utf-8 -*-
"""لاگ اجباری عملیات خطرناک ادمین.

خواسته‌ی مالک: اعمال تغییر آمار (cstat)، حذف کشور و ریست فصل نباید بی‌ردیف
بمانند — اسنپ‌شات قبل از تخریب + رکورد لاگ بعد از آن، برای داوری و پیشگیری
از سوءاستفاده ادمینی.
"""

import json

import config
import database as db
import insurgency
import handlers.admin as admin


def _fresh(monkeypatch, tmp_path, name="audit.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


def _country(player_id=81_001, key="auditland", **over):
    cid = db.create_country(player_id, "کشور آزمون", "🏳️", country_key=key)
    for field, value in over.items():
        db.update_country_field(cid, field, value)
    return cid


def _logs(action=None, limit=50):
    logs = db.get_recent_logs(limit=limit)
    if action:
        logs = [log for log in logs if log["action"] == action]
    return logs


# ─────────────────────────────────────────────────────────────────────────────
# apply_cstat_delta / apply_cstat_value
# ─────────────────────────────────────────────────────────────────────────────

def test_cstat_delta_logs_with_actor(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country(vaccine_doses=100)
    step = admin.COUNTRY_STAT_FIELDS["vaccine_doses"][2]
    new_val, err = admin.apply_cstat_delta(cid, "vaccine_doses", 10, actor_id=42)
    assert err is None and new_val == 100 + 10 * step
    entries = _logs("admin_cstat_delta")
    assert len(entries) == 1
    assert entries[0]["actor"] == "admin:42"
    assert "vaccine_doses" in entries[0]["details"]
    assert f"→ {100 + 10 * step}" in entries[0]["details"]


def test_cstat_delta_without_actor_is_system(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country()
    admin.apply_cstat_delta(cid, "vaccine_doses", -5)
    entries = _logs("admin_cstat_delta")
    assert entries and entries[0]["actor"] == "system"


def test_cstat_invalid_field_logs_nothing(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country()
    out, err = admin.apply_cstat_delta(cid, "not_a_field", 3, actor_id=42)
    assert out is None and err
    assert not _logs("admin_cstat_delta")
    out, err = admin.apply_cstat_value(cid, "not_a_field", 3, actor_id=42)
    assert out is None and err
    assert not _logs("admin_cstat_set")


def test_cstat_missing_country_logs_nothing(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    out, err = admin.apply_cstat_delta(999_999, "vaccine_doses", 3, actor_id=42)
    assert out is None and err
    assert not _logs("admin_cstat_delta")


def test_cstat_set_logs_old_and_new(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country(vaccine_doses=7)
    value, err = admin.apply_cstat_value(cid, "vaccine_doses", 137_000, actor_id=77)
    assert err is None and value == 137_000
    entries = _logs("admin_cstat_set")
    assert len(entries) == 1
    assert entries[0]["actor"] == "admin:77"
    assert "7" in entries[0]["details"] and "137000" in entries[0]["details"]


# ─────────────────────────────────────────────────────────────────────────────
# delete_country_by_id
# ─────────────────────────────────────────────────────────────────────────────

def test_delete_country_logs_snapshot_and_survives(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country(player_id=82_002, key="doomed",
                   treasury=123_456, active_personnel=9_000)
    ok = db.delete_country_by_id(cid, actor="admin:42")
    assert ok
    assert db.get_country_by_id(cid) is None, "کشور باید حذف شده باشد"
    entries = _logs("country_deleted")
    assert len(entries) == 1
    assert entries[0]["actor"] == "admin:42"
    snap = json.loads(entries[0]["details"])
    assert snap["id"] == cid
    assert snap["country_key"] == "doomed"
    assert snap["player_id"] == 82_002
    assert snap["treasury"] == 123_456
    assert snap["active_personnel"] == 9_000


def test_delete_country_default_actor_is_system(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country()
    assert db.delete_country_by_id(cid)
    assert _logs("country_deleted")[0]["actor"] == "system"


def test_delete_missing_country_logs_nothing(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert db.delete_country_by_id(999_999) is False
    assert not _logs("country_deleted")


def test_insurgency_collapse_delete_is_labeled(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "audins.db")
    insurgency.set_enabled(True, admin_id=0, role="system")
    cid = _country(player_id=82_003, key="fallland")
    insurgency.erupt(db.get_country_by_id(cid), "2026-09-01", force=True)
    insurgency.execute_collapse(db.get_country_by_id(cid), "2026-09-02")
    entries = _logs("country_deleted")
    assert entries and entries[0]["actor"] == "insurgency_collapse"
    # لاگ سقوط هم جداگانه هست
    assert any(a["action"] == "insurgency_collapse" for a in db.get_admin_actions(limit=50))


# ─────────────────────────────────────────────────────────────────────────────
# reset_all_countries_for_new_season
# ─────────────────────────────────────────────────────────────────────────────

def test_season_reset_logs_count_and_country_list(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "audreset.db")
    c1 = _country(player_id=83_001, key="r1")
    c2 = _country(player_id=83_002, key="r2")
    ok, count, msg = db.reset_all_countries_for_new_season(actor="admin:42")
    assert ok and count == 2, "دو کشور دارای بازیکن باید ریست شوند"
    assert db.get_country_by_id(c1) is None
    assert db.get_country_by_id(c2) is None
    entries = _logs("season_reset")
    assert len(entries) == 1
    assert entries[0]["actor"] == "admin:42"
    assert f"count={count}" in entries[0]["details"]
    snap = json.loads(entries[0]["details"].split("countries=", 1)[1])
    keys = {row["country_key"] for row in snap}
    assert {"r1", "r2"} <= keys


def test_season_reset_default_actor_is_system(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "audreset2.db")
    _country()
    ok, count, msg = db.reset_all_countries_for_new_season()
    assert ok
    assert _logs("season_reset")[0]["actor"] == "system"
