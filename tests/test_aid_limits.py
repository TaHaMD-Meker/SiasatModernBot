# -*- coding: utf-8 -*-
"""
تست‌های سقف ظرفیت بارگیری، روش ترابری و هزینه ترانزیت برای کمک‌های خارجی (Foreign Aid Transport).
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import database as db  # noqa: E402


def test_foreign_aid_capacity_and_transport_costs(monkeypatch):
    import tempfile
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr(config, "DB_PATH", os.path.join(tmpdir, "test.db"))

    import importlib
    importlib.reload(db)
    db.init_db()

    cid1 = db.create_country(111, "آمریکا", "🇺🇸", country_key="usa")
    cid2 = db.create_country(222, "بریتانیا", "🇬🇧", country_key="uk")

    conn = db.get_connection()
    conn.execute("UPDATE countries SET oil_reserves = 10000000, treasury = 50000000 WHERE id = ?", (cid1,))
    conn.commit()
    conn.close()

    # ۱. تلاش برای ارسال ۱۳۰ هزار بشکه با ترابری زمینی (سقف زمینی جدید ۱۲۰ هزار است)
    ok_land, msg_land = db.execute_foreign_aid_transaction(cid1, cid2, "oil", 130_000, transport_mode="land")
    assert not ok_land
    assert "مازاد" in msg_land

    # ۲. ارسال ۵۰ هزار بشکه با ترابری زمینی (هزینه ترانزیت زمینی ۱ میلیون دلار از خزانه آمریکا کسر می‌شود)
    usa_treasury_before = db.get_country_by_id(cid1)["treasury"]
    ok_land_ok, _ = db.execute_foreign_aid_transaction(cid1, cid2, "oil", 50_000, transport_mode="land")
    assert ok_land_ok
    assert db.get_country_by_id(cid1)["treasury"] == usa_treasury_before - 1_000_000

    # ۳. تلاش برای ارسال ۲.۵ میلیون بشکه با ترابری دریایی (سقف جدید ۲ میلیون بشکه است)
    ok_sea_exceed, msg_sea_exceed = db.execute_foreign_aid_transaction(cid1, cid2, "oil", 2_500_000, transport_mode="sea")
    assert not ok_sea_exceed
    assert "مازاد" in msg_sea_exceed

    # ۴. ارسال ۱.۵ میلیون بشکه با ترابری دریایی / نفتکش (هزینه ۳۰۰ هزار دلار)
    usa_tr_sea = db.get_country_by_id(cid1)["treasury"]
    ok_sea, _ = db.execute_foreign_aid_transaction(cid1, cid2, "oil", 1_500_000, transport_mode="sea")
    assert ok_sea
    assert db.get_country_by_id(cid1)["treasury"] == usa_tr_sea - 300_000

    # ۵. اگر کشور تحت محاصره دریایی باشد، ترابری دریایی مسدود است
    db.create_naval_blockade(cid1, cid2)
    ok_block, msg_block = db.execute_foreign_aid_transaction(cid1, cid2, "oil", 10_000, transport_mode="sea")
    assert not ok_block
    assert "محاصره" in msg_block
