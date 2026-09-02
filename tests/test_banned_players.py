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
# مسیرهای دریافت کشور همه بسته‌اند
# ─────────────────────────────────────────────────────────────────────────────

def test_banned_cannot_join_queue(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    db.ban_player(96_001)
    ok, msg, entry = cq.join_queue(96_001, first_name="اسپمر")
    assert ok is False and entry is None
    assert "مسدود" in msg


def test_banned_cannot_reclaim_quarantined_country(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "ban2.db")
    _country(quarantine_for=96_002)
    db.ban_player(96_002)
    ok, msg, _row = cq.reclaim_country(96_002)
    assert ok is False and "قرنطینه" in msg  # بازپس‌گیری منسوخ شده


def test_banned_cannot_accept_offer(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "ban3.db")
    cid = _country(key="offerland")
    db.ban_player(96_003)
    conn = db.get_connection()
    with conn:
        conn.execute(
            "INSERT INTO country_queue (player_id, first_name, preferred_country_key,"
            " status, offered_country_id, offer_expires_at, joined_at)"
            " VALUES (96_003, 'اسپمر', 'offerland', 'offered', ?, ?, ?)",
            (cid, (datetime.datetime.now(datetime.timezone.utc)
                   + datetime.timedelta(hours=24)).isoformat(),
             datetime.datetime.now(datetime.timezone.utc).isoformat()))
    ok, msg, country = cq.accept_offer(96_003)
    assert ok is False and country is None and "مسدود" in msg
    assert db.get_country_by_id(cid)["player_id"] == 0, "کشور نباید منتقل شده باشد"


def test_unbanned_player_can_join_again(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "ban4.db")
    db.ban_player(96_004)
    db.unban_player(96_004)
    ok, _msg, _entry = cq.join_queue(96_004, first_name="بازگشته")
    assert ok is True
