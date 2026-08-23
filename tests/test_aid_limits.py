# -*- coding: utf-8 -*-
"""
تست‌های سقف ظرفیت بارگیری و ترابری برای کمک‌های خارجی (Foreign Aid Capacity Limits).
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import database as db  # noqa: E402


def test_foreign_aid_capacity_limits(monkeypatch):
    import tempfile
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr(config, "DB_PATH", os.path.join(tmpdir, "test.db"))

    import importlib
    importlib.reload(db)
    db.init_db()

    cid1 = db.create_country(111, "کشور الف", "🅰️", country_key="usa")
    cid2 = db.create_country(222, "کشور ب", "🅱️", country_key="uk")

    conn = db.get_connection()
    conn.execute("UPDATE countries SET oil_reserves = 10000000, treasury = 50000000 WHERE id = ?", (cid1,))
    conn.commit()
    conn.close()

    # تلاش برای ارسال ۶۰۰ هزار بشکه نفت (سقف ۵۰۰ هزار بشکه است)
    ok, msg = db.execute_foreign_aid_transaction(cid1, cid2, "oil", 600_000)
    assert not ok
    assert "سقف مجاز" in msg

    # ارسال ۵۰۰ هزار بشکه نفت (در محدوده سقف)
    before_oil = db.get_country_by_id(cid2)["oil_reserves"] or 0
    ok, msg = db.execute_foreign_aid_transaction(cid1, cid2, "oil", 500_000)
    assert ok
    assert db.get_country_by_id(cid2)["oil_reserves"] == before_oil + 500_000

    # تلاش برای ارسال ۳۰ میلیون دلار کمک مالی (سقف ۲۰ میلیون دلار است)
    ok_m, msg_m = db.execute_foreign_aid_transaction(cid1, cid2, "treasury", 30_000_000)
    assert not ok_m
    assert "سقف مجاز" in msg_m
