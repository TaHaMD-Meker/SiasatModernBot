# -*- coding: utf-8 -*-
"""
تست‌های سیستم خدمات ویژه، اشتراک‌های تومانی، گروه‌های غیردولتی و تایید ادمین با تغییر نام.
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


def test_real_militia_faction_approval(db_temp):
    """تست انتخاب یک گروه واقعی (مثل سپاه قدس یا واگنر) و تایید آن."""
    player_id = 998877

    payload = {
        "name": "شرکت نظامی خصوصی واگنر (Wagner PMC)",
        "flag": "💀",
        "hq": "آفریقا و حوزه ساحل",
        "doctrine": "عملیات ویژه و زرهی سنگین"
    }

    req_id = db_temp.create_payment_request(
        player_id=player_id,
        country_id=None,
        item_type="militia",
        plan_title="🏴‍☠️ مجوز گروه غیردولتی",
        amount_toman=50_000,
        tracking_code="TRX-MILITIA-101",
        custom_payload=json.dumps(payload, ensure_ascii=False)
    )

    ok, msg, p = db_temp.approve_payment_request(req_id, admin_id=8052987465)
    assert ok
    assert p["status"] == "approved"

    faction = db_temp.get_country_by_player(player_id)
    assert faction is not None
    assert "واگنر" in faction["name"]
    assert faction["flag"] == "💀"
    assert faction["treasury"] == 25_000_000
    assert faction["active_personnel"] == 60_000


def test_custom_militia_with_admin_rename(db_temp):
    """تست ثبت گروه سفارشی با نام خام و اصلاح/بازنویسی نام توسط ادمین موقع تایید."""
    player_id = 887766

    payload = {
        "name": "گروه خفن بچه های شرق",  # نام غیررسمی ارسال‌شده توسط کاربر
        "flag": "⚔️",
        "hq": "شمال حلب",
        "doctrine": "جنگ چریکی"
    }

    req_id = db_temp.create_payment_request(
        player_id=player_id,
        country_id=None,
        item_type="militia",
        plan_title="🏴‍☠️ مجوز گروه غیردولتی",
        amount_toman=50_000,
        tracking_code="TRX-CUSTOM-99",
        custom_payload=json.dumps(payload, ensure_ascii=False)
    )

    # ادمین نام را به عنوان رسمی اصلاح و تایید می‌کند
    official_name = "تیپ واکنش سریع مدافعان شمال"
    ok, msg, p = db_temp.approve_payment_request(req_id, admin_id=8052987465, override_name=official_name)
    assert ok

    faction = db_temp.get_country_by_player(player_id)
    assert faction["name"] == official_name
    assert faction["flag"] == "⚔️"


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
    assert db_temp.get_country_by_player(player_id) is None
