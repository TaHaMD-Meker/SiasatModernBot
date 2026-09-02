# -*- coding: utf-8 -*-
"""
واگذاری دستی کشور با آیدی — مرجع کامل دست ادمین:
قفل پیشنهاد صف (همان «قفل»ی که بازیکن هنگام گرفتن کشور می‌بیند)، قرنطینه و
ردپای مالک قبلی همه باید پاک شوند.
"""

import pytest
import config
import database as db
import country_queue as cq


def _fresh(monkeypatch, tmp_path, name):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()
    monkeypatch.setattr(config, "ADMIN_IDS", [42])


def test_assign_breaks_queue_offer_lock(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "assign.db")
    conn = db.get_connection(); cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO countries (id, player_id, name, flag, country_key, treasury) "
                "VALUES (1, 0, 'آزادشده', '🏳️', 'freed_c', 9000000)")
    cur.execute("INSERT OR REPLACE INTO country_queue (id, player_id, status, offered_country_id, offer_expires_at, joined_at) "
                "VALUES (10, 2002, 'offered', 1, '2026-09-03T12:00:00+00:00', 'x')")
    conn.commit(); conn.close()

    assert db.get_active_offer_for_country(1)["player_id"] == 2002

    ok, msg = db.admin_transfer_country_ownership(1, 7777)
    assert ok, msg

    c = db.get_country_by_id(1)
    assert c["player_id"] == 7777
    assert c["previous_player_id"] is None and c["quarantine_until"] is None
    assert db.get_active_offer_for_country(1) is None, "قفل پیشنهاد باید پاک شده باشد"

    conn = db.get_connection(); cur = conn.cursor()
    q = cur.execute("SELECT status, offered_country_id FROM country_queue WHERE id=10").fetchone()
    conn.close()
    assert q["status"] == "waiting" and q["offered_country_id"] is None, \
        "بازیکنِ قفل‌شده باید بدون پیشنهاد، سر صف منتظر بماند"


def test_assign_rejects_banned_and_double_owner(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "assign2.db")
    db.create_country(3003, "کشور الف", "🏳️", country_key="c_a")
    db.create_country(3004, "کشور ب", "🏳️", country_key="c_b")
    db.ban_player(3005, "تست")

    ok, msg = db.admin_transfer_country_ownership(db.get_country_by_player(3003)["id"], 3005)
    assert not ok, "بازیکن بن‌شده نباید کشور بگیرد"

    cid_a = db.get_country_by_player(3003)["id"]
    ok2, msg2 = db.admin_transfer_country_ownership(cid_a, 3004)
    assert not ok2 and "رهبر کشور" in msg2, "کسانی که کشور دارند نباید دوباره بگیرند"


def test_release_country_offer_helper(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "assign3.db")
    conn = db.get_connection(); cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO countries (id, player_id, name, flag, country_key, treasury) "
                "VALUES (3, 0, 'قفلی', '🔒', 'locked_c', 1)")
    cur.execute("INSERT OR REPLACE INTO country_queue (id, player_id, status, offered_country_id, joined_at) "
                "VALUES (11, 4004, 'offered', 3, 'x')")
    conn.commit(); conn.close()

    assert db.release_country_offer(3) == 1
    assert db.release_country_offer(3) == 0  # دوباره: چیزی برای آزاد کردن نیست
    assert db.get_active_offer_for_country(3) is None


def test_ui_buttons_present():
    src = open("handlers/admin_dossier.py", encoding="utf-8").read()
    assert "🎯 واگذاری به بازیکن با آیدی" in src, "دکمه‌ی مستقیم روی پرونده"
    assert "🔓 آزادسازی قفل پیشنهاد صف" in src
    assert "admin:c_unlock_offer:" in src
    # اندیس پارسر: فرمت سه‌تکه → اندیس ۲ (درس list index out of range)
    idx = src.index('data.startswith("admin:c_unlock_offer:")')
    window = src[idx:idx + 200]
    assert 'data.split(":")[2]' in window
    assert 'data.split(":")[3]' not in window
