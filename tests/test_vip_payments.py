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


def test_predefined_faction_creation_with_40_assets(db_temp):
    """تست انتخاب گروه آماده واگنر و دریافت کاتالوگ واقعی ۴۰ عددی."""
    player_id = 998877

    payload = {
        "faction_key": "wagner",
        "name": "واگنر",
        "flag": "💀",
        "hq": "منطقه باخموت",
        "doctrine": "شرکت نظامی خصوصی (PMC)"
    }

    req_id = db_temp.create_payment_request(
        player_id=player_id,
        country_id=None,
        item_type="militia",
        plan_title="🏴‍☠️ هدایت واگنر",
        amount_toman=50_000,
        tracking_code="TRX-WAGNER-101",
        custom_payload=json.dumps(payload, ensure_ascii=False)
    )

    ok, msg, p = db_temp.approve_payment_request(req_id, admin_id=8052987465)
    assert ok

    new_faction = db_temp.get_country_by_player(player_id)
    assert new_faction is not None
    assert new_faction["name"] == "واگنر"
    assert new_faction["flag"] == "💀"

    # بررسی دارایی‌های اختصاصی واگنر (+40 قلم)
    assets = db_temp.get_country_assets(new_faction["id"])
    assert len(assets) >= 40
    asset_names = [a["equipment_name"] for a in assets]
    assert any("T-90M" in name for name in asset_names)
    assert any("Lancet" in name for name in asset_names)


def test_custom_militia_admin_renaming_approval(db_temp):
    """تست تغییر نام گروه سفارشی توسط ادمین در لحظه تایید."""
    player_id = 333444

    payload = {
        "name": "گنگ خفن محله",
        "flag": "⚔️",
        "hq": "شمال حلب",
        "doctrine": "جنگ چریکی"
    }

    req_id = db_temp.create_payment_request(
        player_id=player_id,
        country_id=None,
        item_type="militia",
        plan_title="🏴‍☠️ مجوز گروه سفارشی",
        amount_toman=50_000,
        tracking_code="TRX-CUSTOM-101",
        custom_payload=json.dumps(payload, ensure_ascii=False)
    )

    # ادمین اسم را به نام رسمی و شیک تغییر داده و تایید می‌کند
    refined_name = "تیپ ذوالفقار مقاومت"
    ok, msg, p = db_temp.approve_payment_request(req_id, admin_id=8052987465, override_name=refined_name)
    assert ok

    created = db_temp.get_country_by_player(player_id)
    assert created["name"] == "تیپ ذوالفقار مقاومت"
    assert created["flag"] == "⚔️"
