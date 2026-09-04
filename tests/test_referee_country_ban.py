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
# صف کشور حذف شده — داور فقط در مسیر درخواست /start کنترل می‌شود
# ─────────────────────────────────────────────────────────────────────────────

def test_referee_cannot_request_country_in_pick_flow():
    """مسیر pick_country باید داور محروم (is_playing_restricted) را رد کند."""
    src = open("handlers/start.py", encoding="utf-8").read()
    pick = src.index("async def pick_country")
    window = src[pick:pick + 6000]
    assert "is_playing_restricted" in window
    assert "PLAY_RESTRICTED_MESSAGE" in window


def test_after_removal_referee_restriction_lifts(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "refban2.db")
    db.add_referee(91_002, added_by=1)
    db.remove_referee(91_002, removed_by=1)
    assert db.is_playing_restricted(91_002) is False
