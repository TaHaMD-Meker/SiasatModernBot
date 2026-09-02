# -*- coding: utf-8 -*-
"""
قرنطینه‌ی بیانیه‌نیاوردها: مهلت ۲۴ ساعته + پنل مالک برای آزادسازی دستی
(تک‌تک یا همه‌یکجا) — کشورِ آزادشده فوری به استخر واگذاری می‌رود.
"""

import datetime
import pytest
import config
import database as db
import country_queue as cq


def _fresh(monkeypatch, tmp_path, name):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


def _country(cur, cid, pid, name, key):
    cur.execute(
        "INSERT OR REPLACE INTO countries (id, player_id, name, flag, country_key, treasury, created_at) "
        "VALUES (?, ?, ?, '🏳️', ?, 1000000, '2024-01-01T00:00:00+00:00')", (cid, pid, name, key))


def test_quarantine_is_24_hours(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "q24.db")
    conn = db.get_connection(); cur = conn.cursor()
    _country(cur, 1, 1001, "کشور غایب", "absent_c")
    conn.commit(); conn.close()

    ok, msg = cq.quarantine_country(1, reason="inactivity")
    assert ok and "۲۴ ساعت" in msg or "24 ساعت" in msg
    c = db.get_country_by_id(1)
    until = cq._parse(c["quarantine_until"])
    at = cq._parse(c["quarantined_at"])
    delta_h = (until - at).total_seconds() / 3600
    assert delta_h == 24, f"مهلت قرنطینه باید ۲۴ ساعت باشد، بود {delta_h}"


def test_release_one_and_all(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "qrel.db")
    conn = db.get_connection(); cur = conn.cursor()
    _country(cur, 1, 1001, "کشور یک", "qone_c")
    _country(cur, 2, 1002, "کشور دو", "qtwo_c")
    _country(cur, 3, 1003, "کشور سه", "qthree_c")
    conn.commit(); conn.close()
    cq.quarantine_country(1); cq.quarantine_country(2); cq.quarantine_country(3)
    assert len(cq.get_quarantined_countries()) == 3

    # آزادسازی تک
    ok, msg = cq.release_quarantine(2)
    assert ok
    assert db.get_country_by_id(2)["quarantine_until"] is None
    assert db.get_country_by_id(2)["previous_player_id"] is None
    assert len(cq.get_quarantined_countries()) == 2

    # آزادسازی همه
    n, released = cq.release_all_quarantines()
    assert n == 2 and {c["id"] for c in released} == {1, 3}
    assert cq.get_quarantined_countries() == []
    # آزادشده‌ها فوری در استخر واگذاری‌اند
    free = {x["id"] for x in cq.get_free_countries()}
    assert {1, 2, 3} <= free

    # دوباره: چیزی برای آزاد کردن نیست
    assert cq.release_all_quarantines()[0] == 0
    ok2, _ = cq.release_quarantine(1)
    assert not ok2


def test_panel_buttons_and_routes_present():
    src = open("handlers/admin.py", encoding="utf-8").read()
    assert "admin:q_release:" in src, "دکمه‌ی آزادسازی تک‌کشور"
    assert "admin:q_release_all" in src, "دکمه‌ی آزادسازی همه"
    assert "آزادسازی همه‌ی قرنطینه‌ها" in src
    idx = src.index('data.startswith("admin:q_release:")')
    window = src[idx:idx + 200]
    assert 'data.split(":")[2]' in window, "اندیس ۲ (فرمت سه‌تکه)"
    assert "release_quarantine(" in window or "release_quarantine" in src
    assert "def show_queue_panel" in src, "پنل صف/قرنطینه جداشده"
