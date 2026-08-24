# -*- coding: utf-8 -*-
"""
تست‌های سیستم استراتژیک سنگ آهن و فولاد (Iron & Steel System).
"""

import pytest
import config
import database as db


def setup_module(module):
    db.init_db()


def test_iron_requirement_calculation():
    """تست محاسبه تناژ فولاد مورد نیاز برای ادوات نظامی."""
    # تانک‌ها: ۲۵ تن
    tank_item = {"category": "Ground Forces", "equipment_name": "M1A2 SEPv3 Abrams", "equipment_key": "abrams_m1a2"}
    assert config.get_equipment_iron_req(tank_item) == 25

    # ناوشکن: ۲۰۰ تن
    destroyer_item = {"category": "Navy", "equipment_name": "Arleigh Burke Destroyer", "equipment_key": "burke_destroyer"}
    assert config.get_equipment_iron_req(destroyer_item) == 200

    # ناو هواپیمابر: ۵۰۰ تن
    carrier_item = {"category": "Navy", "equipment_name": "Gerald R. Ford Aircraft Carrier", "equipment_key": "ford_carrier"}
    assert config.get_equipment_iron_req(carrier_item) == 500

    # نفربر: ۱۲ تن
    ifv_item = {"category": "Ground Forces", "equipment_name": "M2A3 Bradley IFV", "equipment_key": "bradley_m2"}
    assert config.get_equipment_iron_req(ifv_item) == 12

    # جنگنده‌ها: ۰ تن فولاد (نیاز به میکروچیپ دارند)
    fighter_item = {"category": "Aircraft", "equipment_name": "F-35A Lightning II", "equipment_key": "f35_usa"}
    assert config.get_equipment_iron_req(fighter_item) == 0


def test_buy_military_asset_with_iron_check():
    """تست خرید تجهیزات با بررسی موجودی و کسر آهن و فولاد."""
    conn = db.get_connection()
    cur = conn.cursor()

    # ایجاد کشور با ۱۰۰ میلیون خزانه و ۵۰ تن آهن و ۵۰ چیپ
    cur.execute("INSERT OR REPLACE INTO countries (id, player_id, name, flag, country_key, treasury, iron_ore, microchips) VALUES (401, 40001, 'آلمان', '🇩🇪', 'germany', 100000000, 50, 50)")

    # افزودن تانک لئوپارد (producible=1)
    cur.execute("""
        INSERT INTO country_assets (country_id, country_key, category, equipment_name, equipment_key, amount, buy_price, maintenance_cost, producible)
        VALUES (401, 'germany', 'Ground Forces', 'Leopard 2A7+ Tank', 'leopard2a7', 10, 8000000, 8000, 1)
        ON CONFLICT(country_id, equipment_key) DO UPDATE SET amount = 10
    """)
    conn.commit()
    conn.close()

    # ۱. تلاش برای خرید ۳ تانک (نیازمند ۷۵ تن آهن، ولی موجودی فقط ۵۰ تن است)
    succ, err_msg, asset_dict = db.buy_country_asset_transaction(401, "leopard2a7", 3)
    assert succ is False
    assert "کسری آهن و فولاد" in err_msg

    # ۲. خرید ۲ تانک (نیازمند ۵۰ تن آهن، موجودی کافی است)
    succ2, msg2, asset_dict2 = db.buy_country_asset_transaction(401, "leopard2a7", 2)
    assert succ2 is True
    assert asset_dict2["amount"] == 12

    # بررسی موجودی نهایی آهن (باید ۰ شده باشد) و خزانه (۱۰۰M - ۱۶M = ۸۴M)
    c = db.get_country_by_id(401)
    assert c["iron_ore"] == 0
    assert c["treasury"] == 84_000_000


def test_iron_market_order_and_exchange():
    """تست عرضه و خرید سنگ آهن در بورس کالا."""
    conn = db.get_connection()
    cur = conn.cursor()

    # استرالیا (فروشنده سنگ آهن) و ژاپن (خریدار)
    cur.execute("INSERT OR REPLACE INTO countries (id, player_id, name, flag, country_key, treasury, iron_ore) VALUES (402, 40002, 'استرالیا', '🇦🇺', 'australia', 50000000, 10000)")
    cur.execute("INSERT OR REPLACE INTO countries (id, player_id, name, flag, country_key, treasury, iron_ore) VALUES (403, 40003, 'ژاپن', '🇯🇵', 'japan', 50000000, 500)")
    conn.commit()
    conn.close()

    # استرالیا ۲,۰۰۰ تن آهن با قیمت ۱,۲۰۰ دلار در بورس عرضه می‌کند
    ok, msg = db.create_market_order(402, "iron_ore", 2000, 1200)
    assert ok is True

    orders = db.get_market_orders("iron_ore")
    assert len(orders) > 0
    ord_item = next(o for o in orders if o["seller_id"] == 402)
    assert ord_item["amount"] == 2000
    assert ord_item["unit_price"] == 1200

    # ژاپن ۱,۰۰۰ تن از این عرضه را از طریق ترابری دریایی می‌خرد
    # هزینه: ۱,۰۰۰ * ۱,۲۰۰ = ۱,۲۰۰,۰۰۰ دلار + ۳۰۰,۰۰۰ ترانزیت دریایی = ۱,۵۰۰,۰۰۰ دلار
    succ, msg, res = db.execute_market_buy_transaction(buyer_id=403, order_id=ord_item["id"], buy_amount=1000, transport_mode="sea")
    assert succ is True

    japan_c = db.get_country_by_id(403)
    aus_c = db.get_country_by_id(402)

    assert japan_c["iron_ore"] == 1500  # 500 + 1000
    assert japan_c["treasury"] == 50_000_000 - 1_500_000
    assert aus_c["treasury"] == 50_000_000 + 1_200_000
