# -*- coding: utf-8 -*-
"""
تست‌های سیستم پایش بیانیه‌ها و سلب مالکیت در صورت عدم فعالیت (Statements & Inactivity System).
"""

import os
import sys
import tempfile
import datetime
try:
    from zoneinfo import ZoneInfo
    IRAN_TZ = ZoneInfo("Asia/Tehran")
except Exception:
    IRAN_TZ = datetime.timezone(datetime.timedelta(hours=3, minutes=30))

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402


@pytest.fixture()
def db(monkeypatch):
    """دیتابیس موقت برای تست."""
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr(config, "DB_PATH", os.path.join(tmpdir, "test.db"))

    import importlib
    import database
    importlib.reload(database)

    database.init_db()
    return database


def test_statement_recording_and_counting(db):
    cid = db.create_country(1001, "ایران", "🇮🇷", country_key="iran")

    # در ابتدا تعداد صفر است
    assert db.get_country_statement_count_today(cid) == 0

    # ثبت ۱ بیانیه
    db.record_country_statement(cid, 1001, "statement", "بیانیه مهم صلح")
    assert db.get_country_statement_count_today(cid) == 1

    # ثبت ۱ توییت
    db.record_country_statement(cid, 1001, "tweet", "توییت واکنش سریع")
    assert db.get_country_statement_count_today(cid) == 2

    today_str = datetime.datetime.now(datetime.timezone.utc).astimezone(IRAN_TZ).date().isoformat()
    counts = db.get_all_country_statement_counts_for_date(today_str)
    assert counts.get(cid) == 2


def test_inactivity_revocation_logic(db):
    """تست سلب مالکیت کشوری که در روز گذشته ۲ بیانیه نداده است."""
    cid1 = db.create_country(2001, "آلمان", "🇩🇪", country_key="germany")
    cid2 = db.create_country(2002, "فرانسه", "🇫🇷", country_key="france")

    c1 = db.get_country_by_id(cid1)
    c2 = db.get_country_by_id(cid2)

    yesterday_str = "2026-08-22"

    # آلمان فقط ۱ بیانیه در دیروز ثبت کرده
    conn = db.get_connection()
    conn.execute(
        "INSERT INTO daily_statements (country_id, player_id, statement_type, created_at, statement_date) VALUES (?, ?, ?, ?, ?)",
        (cid1, 2001, "statement", "2026-08-22T10:00:00+00:00", yesterday_str)
    )
    # فرانسه ۲ بیانیه در دیروز ثبت کرده
    conn.execute(
        "INSERT INTO daily_statements (country_id, player_id, statement_type, created_at, statement_date) VALUES (?, ?, ?, ?, ?)",
        (cid2, 2002, "statement", "2026-08-22T11:00:00+00:00", yesterday_str)
    )
    conn.execute(
        "INSERT INTO daily_statements (country_id, player_id, statement_type, created_at, statement_date) VALUES (?, ?, ?, ?, ?)",
        (cid2, 2002, "tweet", "2026-08-22T15:00:00+00:00", yesterday_str)
    )
    conn.commit()
    conn.close()

    counts = db.get_all_country_statement_counts_for_date(yesterday_str)
    assert counts.get(cid1) == 1
    assert counts.get(cid2) == 2

    # شبیه‌سازی سلب مالکیت برای کشوری که < 2 دارد
    for c in [c1, c2]:
        user_stmts = counts.get(c["id"], 0)
        if user_stmts < 2:
            db.delete_country_by_id(c["id"])

    # آلمان باید حذف شده باشد و فرانسه باید باقی مانده باشد
    assert db.get_country_by_id(cid1) is None
    assert db.get_country_by_id(cid2) is not None
