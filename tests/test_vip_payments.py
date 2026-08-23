# -*- coding: utf-8 -*-
"""
تست‌های سیستم خدمات ویژه ۴ سطحی، اشتراک‌های تومانی و تخفیف نگهداری ارتش (VIP 4-Tier System).
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


def test_4tier_vip_approval_and_maintenance_discounts(db_temp):
    cid = db_temp.create_country(555, "ایران", "🇮🇷", country_key="iran")
    
    # اضافه کردن تسلیحات نمونه جهت محاسبه هزینه نگهداری
    conn = db_temp.get_connection()
    conn.execute("INSERT INTO country_assets (country_id, country_key, category, equipment_name, equipment_key, amount, maintenance_cost) VALUES (?, 'iran', 'Aircraft', 'F-14', 'f14', 100, 10000)", (cid,))
    conn.commit()
    conn.close()

    # هزینه نگهداری در حالت عادی (بدون VIP)
    maint_normal = db_temp.calculate_country_maintenance_cost(cid)
    assert maint_normal["vip_discount_pct"] == 0

    # ۱. خرید و تایید پلن برنز (۷۹ تومن -> ۵٪ تخفیف)
    req_b = db_temp.create_payment_request(555, cid, "vip_bronze", "🥉 اشتراک برنز", 79_000, tracking_code="TRX-B")
    ok, _, _ = db_temp.approve_payment_request(req_b, admin_id=8052987465)
    assert ok
    maint_bronze = db_temp.calculate_country_maintenance_cost(cid)
    assert maint_bronze["vip_discount_pct"] == 5
    assert maint_bronze["total_maint"] < maint_normal["total_maint"]

    # ۲. خرید و تایید پلن نقره (۱۷۹ تومن -> ۱۰٪ تخفیف)
    req_s = db_temp.create_payment_request(555, cid, "vip_silver", "🥈 اشتراک نقره", 179_000, tracking_code="TRX-S")
    db_temp.approve_payment_request(req_s, admin_id=8052987465)
    maint_silver = db_temp.calculate_country_maintenance_cost(cid)
    assert maint_silver["vip_discount_pct"] == 10

    # ۳. خرید و تایید پلن طلا (۳۴۹ تومن -> ۱۵٪ تخفیف)
    req_g = db_temp.create_payment_request(555, cid, "vip_gold", "🥇 اشتراک طلا", 349_000, tracking_code="TRX-G")
    db_temp.approve_payment_request(req_g, admin_id=8052987465)
    maint_gold = db_temp.calculate_country_maintenance_cost(cid)
    assert maint_gold["vip_discount_pct"] == 15

    # ۴. خرید و تایید پلن الماس (۶۵۰ تومن -> ۲۵٪ تخفیف)
    req_d = db_temp.create_payment_request(555, cid, "vip_diamond", "💎 اشتراک الماس", 650_000, tracking_code="TRX-D")
    db_temp.approve_payment_request(req_d, admin_id=8052987465)
    maint_diamond = db_temp.calculate_country_maintenance_cost(cid)
    assert maint_diamond["vip_discount_pct"] == 25
    assert maint_diamond["total_maint"] < maint_gold["total_maint"]


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
