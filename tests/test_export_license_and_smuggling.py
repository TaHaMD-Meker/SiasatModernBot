# -*- coding: utf-8 -*-
"""
تست‌های جامع سیستم مجوز صادرات تسلیحات (End-User Export License) و قاچاق سلاح‌های سبک (Smuggling).
"""

import pytest
import config
import database as db


def setup_module(module):
    db.init_db()


def test_detect_weapon_origin_and_light_classification():
    """تست تشخیص کشور سازنده و دسته‌بندی سلاح‌های سبک و سنگین."""
    # ۱. سلاح‌های بومی و وارداتی
    assert config.detect_weapon_origin("rafale_qatar", "Dassault Rafale EQ", "qatar") == "france"
    assert config.detect_weapon_origin("f16_turkey", "F-16C Block 50+", "turkey") == "usa"
    assert config.detect_weapon_origin("shahed136_drone", "پهپاد انتحاری شاهد-۱۳۶", "iran") == "iran"
    assert config.detect_weapon_origin("pantsir_s1_syria", "سامانه پانتسیر Pantsir-S1", "syria") == "russia"
    assert config.detect_weapon_origin("leclerc_uae", "تانک لوکلرک Leclerc", "uae") == "france"

    # ۲. دسته‌بندی سلاح‌های سبک مجاز به قاچاق در برابر پلتفرم‌های سنگین
    # سنگین (غیرقابل قاچاق)
    assert config.is_light_weapon("Aircraft", "f35_usa", "F-35A Lightning II") is False
    assert config.is_light_weapon("Aircraft", "rafale_france", "Dassault Rafale C") is False
    assert config.is_light_weapon("Ground Forces", "m1a2_abrams", "M1A2 Abrams") is False
    assert config.is_light_weapon("Air Defense", "patriot_pac3", "سامانه پاتریوت PAC-3") is False
    assert config.is_light_weapon("Navy", "burke_destroyer", "ناوشکن ارلی برک") is False
    assert config.is_light_weapon("Missiles", "fateh110", "موشک بالستیک فاتح-۱۱۰") is False

    # سبک (مجاز به قاچاق)
    assert config.is_light_weapon("Ground Forces", "kornet_team", "تیم ضدزره کورنت (Kornet-EM)") is True
    assert config.is_light_weapon("Air Defense", "misagh3_manpads", "دوش‌پرتاب میثاق-۳") is True
    assert config.is_light_weapon("Air Defense", "stinger_manpads", "FIM-92 Stinger MANPADS") is True
    assert config.is_light_weapon("UAV", "shahed136_drone", "پهپاد انتحاری شاهد-۱۳۶") is True
    assert config.is_light_weapon("Ground Forces", "hamza_mrap", "خودرو ضدکمین بومی حمزه Hamza 8x8") is True


def test_export_license_approval_flow():
    """تست چرخه کامل درخواست و صدور مجوز صادرات توسط کشور سازنده فعال."""
    conn = db.get_connection()
    cur = conn.cursor()

    # ۱. ایجاد سه کشور: فرانسه (سازنده)، قطر (فروشنده)، امارات (خریدار)
    cur.execute("INSERT OR REPLACE INTO countries (id, player_id, name, flag, country_key, treasury, approval_rating) VALUES (101, 10001, 'فرانسه', '🇫🇷', 'france', 100000000, 85)")
    cur.execute("INSERT OR REPLACE INTO countries (id, player_id, name, flag, country_key, treasury, approval_rating) VALUES (102, 10002, 'قطر', '🇶🇦', 'qatar', 100000000, 85)")
    cur.execute("INSERT OR REPLACE INTO countries (id, player_id, name, flag, country_key, treasury, approval_rating) VALUES (103, 10003, 'امارات', '🇦🇪', 'uae', 100000000, 85)")

    # افزودن رافال به قطر
    cur.execute("""
        INSERT INTO country_assets (country_id, country_key, category, equipment_name, equipment_key, amount, buy_price, maintenance_cost, producible)
        VALUES (102, 'qatar', 'Aircraft', 'Dassault Rafale EQ', 'rafale_qatar', 5, 50000000, 50000, 0)
        ON CONFLICT(country_id, equipment_key) DO UPDATE SET amount = 5
    """)
    conn.commit()
    conn.close()

    # ۲. قطر پیشنهاد فروش رافال به امارات می‌دهد (نیاز به مجوز فرانسه)
    cid = db.create_trade_contract(
        proposer_id=102,
        recipient_id=103,
        offered_type="military_asset",
        offered_amount=2,
        requested_type="treasury",
        requested_amount=80_000_000,
        transport_payer="seller",
        transport_cost=2_000_000,
        offered_key="rafale_qatar",
        transport_mode="air",
        is_smuggled=0,
        origin_country_key="france",
        license_country_id=101,
        license_status="pending"
    )

    contract = db.get_trade_contract(cid)
    assert contract["status"] == "pending_license"
    assert contract["license_status"] == "pending"

    # خریدار قبل از صدور مجوز نمی‌تواند قبول کند
    succ, err_msg = db.execute_trade_contract_transaction(cid)
    assert succ is False
    assert "انتظار صدور مجوز" in err_msg

    # ۳. فرانسه مجوز صادرات را تأیید می‌کند
    app_ok, app_msg, updated_c = db.approve_export_license(cid, licenser_country_id=101)
    assert app_ok is True
    assert updated_c["status"] == "pending"
    assert updated_c["license_status"] == "approved"

    # ۴. امارات معاهده را امضا و دریافت می‌کند
    succ2, msg2 = db.execute_trade_contract_transaction(cid)
    assert succ2 is True

    # بررسی موجودی رافال در قطر (۳) و امارات (۲)
    q_rafale = db.get_asset_by_key(102, "rafale_qatar")
    u_rafale = db.get_asset_by_key(103, "rafale_qatar")
    assert q_rafale["amount"] == 3
    assert u_rafale["amount"] == 2


def test_export_license_veto_flow():
    """تست وتو کردن معاهده تسلیحاتی توسط کشور سازنده."""
    conn = db.get_connection()
    cur = conn.cursor()

    cur.execute("INSERT OR REPLACE INTO countries (id, player_id, name, flag, country_key, treasury) VALUES (201, 20001, 'آمریکا', '🇺🇸', 'usa', 100000000)")
    cur.execute("INSERT OR REPLACE INTO countries (id, player_id, name, flag, country_key, treasury) VALUES (202, 20002, 'ترکیه', '🇹🇷', 'turkey', 100000000)")
    cur.execute("INSERT OR REPLACE INTO countries (id, player_id, name, flag, country_key, treasury) VALUES (203, 20003, 'سوریه', '🇸🇾', 'syria', 100000000)")

    cur.execute("""
        INSERT INTO country_assets (country_id, country_key, category, equipment_name, equipment_key, amount, buy_price, maintenance_cost, producible)
        VALUES (202, 'turkey', 'Aircraft', 'F-16C Fighting Falcon', 'f16_turkey', 10, 30000000, 30000, 0)
        ON CONFLICT(country_id, equipment_key) DO UPDATE SET amount = 10
    """)
    conn.commit()
    conn.close()

    # ترکیه می‌خواهد F-16 آمریکایی را به سوریه واگذار کند
    cid = db.create_trade_contract(
        proposer_id=202,
        recipient_id=203,
        offered_type="military_asset",
        offered_amount=2,
        requested_type="treasury",
        requested_amount=40_000_000,
        transport_payer="seller",
        transport_cost=2_000_000,
        offered_key="f16_turkey",
        transport_mode="air",
        is_smuggled=0,
        origin_country_key="usa",
        license_country_id=201,
        license_status="pending"
    )

    # آمریکا وتو می‌کند
    veto_ok, veto_msg, updated_c = db.veto_export_license(cid, licenser_country_id=201)
    assert veto_ok is True
    assert updated_c["status"] == "vetoed"
    assert updated_c["license_status"] == "vetoed"

    # تلاش برای اجرا شکست می‌خورد
    succ, err_msg = db.execute_trade_contract_transaction(cid)
    assert succ is False
    assert "وتو شده" in err_msg


def test_smuggling_light_weapon_and_interception_mechanics():
    """تست قاچاق موفق و مکانیزم ردگیری سلاح‌های سبک در بازار سیاه."""
    conn = db.get_connection()
    cur = conn.cursor()

    cur.execute("INSERT OR REPLACE INTO countries (id, player_id, name, flag, country_key, treasury, approval_rating) VALUES (301, 30001, 'یمن', '🇾🇪', 'yemen', 50000000, 85)")
    cur.execute("INSERT OR REPLACE INTO countries (id, player_id, name, flag, country_key, treasury, approval_rating) VALUES (302, 30002, 'حزب‌الله', '🇱🇧', 'hezbollah', 50000000, 85)")

    cur.execute("""
        INSERT INTO country_assets (country_id, country_key, category, equipment_name, equipment_key, amount, buy_price, maintenance_cost, producible)
        VALUES (301, 'yemen', 'Ground Forces', 'تیم ضدزره کورنت (Kornet-EM)', 'kornet_team', 20, 500000, 500, 0)
        ON CONFLICT(country_id, equipment_key) DO UPDATE SET amount = 20
    """)
    conn.commit()
    conn.close()

    # ارسال ۱۰ تیم کورنت به صورت قاچاق
    cid = db.create_trade_contract(
        proposer_id=301,
        recipient_id=302,
        offered_type="military_asset",
        offered_amount=10,
        requested_type="treasury",
        requested_amount=2_000_000,
        transport_payer="seller",
        transport_cost=1_500_000,
        offered_key="kornet_team",
        transport_mode="land",
        is_smuggled=1,
        origin_country_key="russia",
        license_status="approved"
    )

    succ, msg = db.execute_trade_contract_transaction(cid)
    assert succ is True
    # پاسخ یا SMUGGLED_SAFE است یا INTERCEPTED
    assert msg.startswith("SMUGGLED_SAFE") or msg.startswith("INTERCEPTED")

    # موجودی سلاح در انبار یمن کاهش یافته است
    y_kornet = db.get_asset_by_key(301, "kornet_team")
    assert y_kornet["amount"] == 10
