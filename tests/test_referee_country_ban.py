# -*- coding: utf-8 -*-
"""ممنوعیت گرفتن کشور برای داورهای فعال.

قاعده: داور نباید همزمان بازیکن باشد (بی‌طرفی داوری). هر سه مسیر ورود کشور —
صف، پذیرش پیشنهاد و استرداد کشور قرنطینه‌ای — باید بسته باشد. مالک همیشه آزاد است.
"""

import datetime

import config
import country_queue as cq
import database as db


def _fresh(monkeypatch, tmp_path, name="refban.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


def _country(player_id=0, key="freeland", quarantine=False):
    cid = db.create_country(player_id, "کشور آزاد", "🏳️", country_key=key)
    if player_id:
        db.update_country_field(cid, "player_id", 0)
    if quarantine:
        conn = db.get_connection()
        with conn:
            conn.execute(
                "UPDATE countries SET previous_player_id = ?, quarantine_until = ? WHERE id = ?",
                (player_id, (datetime.datetime.now(datetime.timezone.utc)
                             + datetime.timedelta(days=3)).isoformat(), cid))
    return cid


# ─────────────────────────────────────────────────────────────────────────────
# helper تشخیص محرومیت
# ─────────────────────────────────────────────────────────────────────────────

def test_plain_player_not_restricted(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert db.is_playing_restricted(90_001) is False


def test_active_referee_restricted(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    ok, _msg = db.add_referee(90_002, added_by=1, display_name="داور آزمون")
    assert ok
    assert db.is_playing_restricted(90_002) is True
    assert db.is_referee(90_002) is True


def test_removed_referee_not_restricted(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    db.add_referee(90_003, added_by=1)
    db.remove_referee(90_003, removed_by=1)
    assert db.is_playing_restricted(90_003) is False


def test_owner_never_restricted_even_with_referee_row(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "ADMIN_IDS", [90_004])
    db.add_referee(90_004, added_by=90_004)
    assert db.is_referee(90_004) is True
    assert db.is_playing_restricted(90_004) is False, "مالک هرگز محروم نمی‌شود"


# ─────────────────────────────────────────────────────────────────────────────
# مسیر ۱: صف کشور
# ─────────────────────────────────────────────────────────────────────────────

def test_referee_cannot_join_queue(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    db.add_referee(91_001, added_by=1)
    ok, msg, entry = cq.join_queue(91_001, first_name="داور")
    assert ok is False and entry is None
    assert "داور" in msg


def test_after_removal_referee_can_join(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "refban2.db")
    db.add_referee(91_002, added_by=1)
    db.remove_referee(91_002, removed_by=1)
    ok, _msg, _entry = cq.join_queue(91_002, first_name="داور سابق")
    assert ok is True


# ─────────────────────────────────────────────────────────────────────────────
# مسیر ۲: پذیرش پیشنهاد کشور
# ─────────────────────────────────────────────────────────────────────────────

def test_referee_cannot_accept_offer(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "refban3.db")
    cid = _country(key="offeredland")
    db.add_referee(91_003, added_by=1)
    # پیشنهاد معلق دستی برای داور می‌سازیم (انگار قبل از داوری شده)
    conn = db.get_connection()
    with conn:
        conn.execute(
            "INSERT INTO country_queue (player_id, first_name, preferred_country_key,"
            " status, offered_country_id, offer_expires_at, joined_at)"
            " VALUES (91_003, 'داور', 'offeredland', 'offered', ?, ?, ?)",
            (cid, (datetime.datetime.now(datetime.timezone.utc)
                   + datetime.timedelta(hours=24)).isoformat(),
             datetime.datetime.now(datetime.timezone.utc).isoformat()))
    ok, msg, country = cq.accept_offer(91_003)
    assert ok is False and country is None
    assert "داور" in msg
    assert db.get_country_by_id(cid)["player_id"] == 0, "کشور نباید منتقل شده باشد"


# ─────────────────────────────────────────────────────────────────────────────
# مسیر ۳: استرداد کشور قرنطینه‌ای
# ─────────────────────────────────────────────────────────────────────────────

def test_referee_cannot_reclaim_quarantined_country(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "refban4.db")
    _country(player_id=91_004, key="oldland", quarantine=True)
    db.add_referee(91_004, added_by=1)
    ok, msg, _country_row = cq.reclaim_country(91_004)
    assert ok is False
    assert "قرنطینه" in msg  # بازپس‌گیری برای همه‌ی نقش‌ها منسوخ است
