# -*- coding: utf-8 -*-
"""
تست‌های سیستم خدمات ویژه، اشتراک‌های تومانی و ساخت گروه‌های غیردولتی (VIP & Custom Militia).
"""

import os
import sys
import json
import tempfile
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


def test_custom_militia_creation_for_new_player_without_country(db_temp):
    """تست ثبت درخواست و ساخت خودکار گروه شبه‌نظامی غیردولتی برای بازیکنی که کشور ندارد."""
    player_id = 998877

    # بازیکن هنوز کشوری ندارد
    assert db_temp.get_country_by_player(player_id) is None

    payload = {
        "name": "سازمان نظامی واگنر",
        "flag": "💀",
        "hq": "منطقه دونباس و تدمر",
        "doctrine": "شرکت نظامی خصوصی (PMC)"
    }

    # ثبت درخواست مجوز و فیش واریزی ۵۰ هزار تومانی
    req_id = db_temp.create_payment_request(
        player_id=player_id,
        country_id=None,
        item_type="militia",
        plan_title="🏴‍☠️ مجوز گروه غیردولتی",
        amount_toman=50_000,
        tracking_code="TRX-MILITIA-101",
        custom_payload=json.dumps(payload, ensure_ascii=False)
    )

    p_req = db_temp.get_payment_request_by_id(req_id)
    assert p_req["status"] == "pending"

    # تایید درخواست توسط ادمین
    ok, msg, p = db_temp.approve_payment_request(req_id, admin_id=8052987465)
    assert ok
    assert p["status"] == "approved"

    # بررسی ساخته شدن گروه در دیتابیس با تسلیحات و منابع اولیه
    new_faction = db_temp.get_country_by_player(player_id)
    assert new_faction is not None
    assert new_faction["name"] == "سازمان نظامی واگنر"
    assert new_faction["flag"] == "💀"
    assert new_faction["treasury"] == 25_000_000
    assert new_faction["active_personnel"] == 60_000
    assert new_faction["is_vip"] == 1

    # بررسی وجود تسلیحات نامتقارن گروه
    assets = db_temp.get_country_assets(new_faction["id"])
    assert len(assets) >= 10
    asset_names = [a["equipment_name"] for a in assets]
    assert any("تویوتا" in name for name in asset_names)
    assert any("گراد" in name for name in asset_names)


def test_militia_license_rejection_flow(db_temp):
    player_id = 666

    req_id = db_temp.create_payment_request(
        player_id=player_id,
        country_id=None,
        item_type="militia",
        plan_title="🏴‍☠️ مجوز گروه غیردولتی",
        amount_toman=50_000,
        tracking_code="TRX-FAKE-000"
    )

    ok, msg, p = db_temp.reject_payment_request(req_id, admin_id=8052987465, reason="فیش جعلی")
    assert ok
    assert p["status"] == "rejected"
    assert p["admin_note"] == "فیش جعلی"

    # کشوری برای بازیکن نباید ساخته شده باشد
    assert db_temp.get_country_by_player(player_id) is None
