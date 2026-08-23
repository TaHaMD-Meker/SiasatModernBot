# -*- coding: utf-8 -*-
"""
تست‌های سیستم خدمات ویژه، اشتراک‌های تومانی و تایید پرداخت‌ها (VIP & Toman Payments).
"""

import os
import sys
import tempfile
import datetime
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import database as db  # noqa: E402


@pytest.fixture()
def db_temp(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr(config, "DB_PATH", os.path.join(tmpdir, "test.db"))

    import importlib
    importlib.reload(db)
    db.init_db()
    return db


def test_vip_payment_creation_and_approval(db_temp):
    cid = db_temp.create_country(555, "ایران", "🇮🇷", country_key="iran")
    
    # کشور در ابتدا VIP نیست
    c_before = db_temp.get_country_by_id(cid)
    assert not c_before.get("is_vip")

    # ثبت فیش واریز VIP ۱ ماهه (۷۹ هزار تومان)
    req_id = db_temp.create_payment_request(
        player_id=555,
        country_id=cid,
        item_type="vip_1month",
        plan_title="👑 اشتراک ۱ ماهه VIP",
        amount_toman=79_000,
        receipt_photo_id="photo_file_123",
        tracking_code="TRX-987654"
    )

    pending = db_temp.get_pending_payment_requests()
    assert len(pending) == 1
    assert pending[0]["id"] == req_id
    assert pending[0]["amount_toman"] == 79_000

    # تایید پرداخت توسط ادمین
    ok, msg, p = db_temp.approve_payment_request(req_id, admin_id=8052987465)
    assert ok
    assert p["status"] == "approved"

    # کشور باید اکنون VIP فعال داشته باشد با تاریخ انقضا ۳۰ روزه
    c_after = db_temp.get_country_by_id(cid)
    assert c_after["is_vip"] == 1
    assert c_after["vip_expires_at"] is not None

    # لیست فیش‌های معلق اکنون باید خالی باشد
    assert len(db_temp.get_pending_payment_requests()) == 0


def test_militia_license_rejection_flow(db_temp):
    cid = db_temp.create_country(666, "روسیه", "🇷🇺", country_key="russia")

    # ثبت درخواست مجوز گروه شبه‌نظامی (۵۰ هزار تومان)
    req_id = db_temp.create_payment_request(
        player_id=666,
        country_id=cid,
        item_type="militia",
        plan_title="🏴‍☠️ مجوز گروه غیردولتی",
        amount_toman=50_000,
        tracking_code="TRX-FAKE-000"
    )

    # رد درخواست توسط ادمین
    ok, msg, p = db_temp.reject_payment_request(req_id, admin_id=8052987465, reason="فیش جعلی")
    assert ok
    assert p["status"] == "rejected"
    assert p["admin_note"] == "فیش جعلی"

    p_req = db_temp.get_payment_request_by_id(req_id)
    assert p_req["status"] == "rejected"
