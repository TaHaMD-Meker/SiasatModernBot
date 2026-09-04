# -*- coding: utf-8 -*-
"""مسدودسازی بازیکن — فقط مالک، محروم از هر مسیر دریافت کشور.

قاعده: کاربر مسدودشده نباید بتواند از /start، صف، پذیرش پیشنهاد یا استرداد
قرنطینه کشوری بگیرد (پادزهر اسپم درخواست کشور). مسدودی/رفع آن باید لاگ شود.
"""

import datetime

import config
import country_queue as cq
import database as db


def _fresh(monkeypatch, tmp_path, name="ban.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


def _country(player_id=0, key="freeland", quarantine_for=None):
    cid = db.create_country(player_id, "کشور آزاد", "🏳️", country_key=key)
    if player_id:
        db.update_country_field(cid, "player_id", 0)
    if quarantine_for:
        conn = db.get_connection()
        with conn:
            conn.execute(
                "UPDATE countries SET previous_player_id = ?, quarantine_until = ? WHERE id = ?",
                (quarantine_for, (datetime.datetime.now(datetime.timezone.utc)
                                  + datetime.timedelta(days=3)).isoformat(), cid))
    return cid


def _logs(action, limit=50):
    return [log for log in db.get_recent_logs(limit=limit) if log["action"] == action]


# ─────────────────────────────────────────────────────────────────────────────
# پایه: ban / unban / is_banned / list
# ─────────────────────────────────────────────────────────────────────────────

def test_ban_and_status(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert db.is_banned(95_001) is False
    ok, _msg = db.ban_player(95_001, reason="اسپم درخواست کشور", banned_by=77)
    assert ok
    assert db.is_banned(95_001) is True
    info = db.get_ban_info(95_001)
    assert info and info["reason"] == "اسپم درخواست کشور"
    assert int(info["banned_by"]) == 77


def test_double_ban_rejected(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert db.ban_player(95_002)[0]
    ok, msg = db.ban_player(95_002)
    assert ok is False and "مسدود" in msg


def test_unban_and_reban(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    db.ban_player(95_003)
    ok, _msg = db.unban_player(95_003, unbanned_by=77)
    assert ok and db.is_banned(95_003) is False
    ok2, _msg2 = db.unban_player(95_003)
    assert ok2 is False, "رفع مسدودی دوباره نباید موفق باشد"
    ok3, _msg3 = db.ban_player(95_003, reason="دوباره اسپم کرد", banned_by=77)
    assert ok3 and db.is_banned(95_003)
    assert db.get_ban_info(95_003)["reason"] == "دوباره اسپم کرد"


def test_banned_list_only_active(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    db.ban_player(95_004)
    db.ban_player(95_005)
    db.unban_player(95_004)
    ids = {b["user_id"] for b in db.get_banned_players()}
    assert 95_005 in ids and 95_004 not in ids


def test_ban_unban_logged(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    db.ban_player(95_006, reason="مولتی", banned_by=77)
    db.unban_player(95_006, unbanned_by=77)
    bans = _logs("player_ban")
    unban = _logs("player_unban")
    assert bans and "95_006".replace("_", "") in bans[0]["details"].replace("_", "")
    assert unban and unban[0]["actor"] == "admin:77"


# ─────────────────────────────────────────────────────────────────────────────
# مسیرهای دریافت کشور همه بسته‌اند (صف حذف شده — فقط درخواست /start)
# ─────────────────────────────────────────────────────────────────────────────

def test_banned_cannot_request_country_in_pick_flow(monkeypatch, tmp_path):
    """بن‌شده در مسیر مستقیم انتخاب کشور (pick_country) رد می‌شود."""
    _fresh(monkeypatch, tmp_path)
    db.ban_player(96_001)
    assert db.is_banned(96_001)
    src = open("handlers/start.py", encoding="utf-8").read()
    pick = src.index("async def pick_country")
    window = src[pick:pick + 6000]
    assert "is_banned" in window, "مسیر گرفتن کشور باید کاربر مسدود را رد کند"


def test_banned_cannot_reclaim_quarantined_country(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "ban2.db")
    _country(quarantine_for=96_002)
    db.ban_player(96_002)
    ok, msg, _row = cq.reclaim_country(96_002)
    assert ok is False and "قرنطینه" in msg  # بازپس‌گیری منسوخ شده
