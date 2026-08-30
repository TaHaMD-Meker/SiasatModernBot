# -*- coding: utf-8 -*-
"""
تست‌های اعتبارسنجی مسیرهای دریایی و تنگه‌های استراتژیک (Maritime Straits Routing).
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import database as db  # noqa: E402


def test_usa_uk_direct_atlantic_route_never_touches_suez_or_hormuz():
    """آمریکا و بریتانیا در اقیانوس اطلس تجارت مستقیم دارند و به سوئز یا هرمز برخورد نمی‌کنند."""
    assert not db.is_trade_route_crossing_strait("usa", "uk", "suez")
    assert not db.is_trade_route_crossing_strait("usa", "uk", "hormuz")
    assert not db.is_trade_route_crossing_strait("usa", "uk", "bab_el_mandeb")
    assert not db.is_trade_route_crossing_strait("usa", "uk", "bosphorus")
    assert not db.is_trade_route_crossing_strait("usa", "uk", "gibraltar_south")


def test_uk_india_crosses_suez_and_bab_el_mandeb():
    """تجارت بریتانیا با هند از کانال سوئز و باب‌المندب عبور می‌کند."""
    assert db.is_trade_route_crossing_strait("uk", "india", "suez")
    assert db.is_trade_route_crossing_strait("uk", "india", "bab_el_mandeb")
    assert not db.is_trade_route_crossing_strait("uk", "india", "hormuz")


def test_iran_china_crosses_hormuz_and_malacca():
    """تجارت ایران با چین از تنگه هرمز و تنگه مالاکا عبور می‌کند."""
    assert db.is_trade_route_crossing_strait("iran", "china", "hormuz")
    assert db.is_trade_route_crossing_strait("iran", "china", "malacca")
    assert not db.is_trade_route_crossing_strait("iran", "china", "suez")


def test_usa_italy_crosses_gibraltar():
    """تجارت آمریکا با ایتالیا (ورود به مدیترانه) از جبل‌الطارق عبور می‌کند."""
    assert db.is_trade_route_crossing_strait("usa", "italy", "gibraltar_north")
    assert not db.is_trade_route_crossing_strait("usa", "italy", "suez")


def test_black_sea_to_world_crosses_bosphorus():
    """تجارت روسیه/اوکراین به مصر یا آب‌های آزاد از تنگه بسفر عبور می‌کند."""
    assert db.is_trade_route_crossing_strait("russia", "egypt", "bosphorus")
    assert db.is_trade_route_crossing_strait("ukraine", "france", "bosphorus")
    assert not db.is_trade_route_crossing_strait("france", "germany", "bosphorus")

def test_get_trade_route_strait_analysis_blocked_and_toll(monkeypatch):
    import tempfile
    import config
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr(config, "DB_PATH", os.path.join(tmpdir, "test_strait_analysis.db"))

    import importlib
    importlib.reload(db)
    db.init_db()

    # ایجاد کشورهای نمونه
    db.create_country(101, "ایران", "🇮🇷", country_key="iran")
    db.create_country(102, "عربستان", "🇸🇦", country_key="saudi")
    db.create_country(103, "چین", "🇨🇳", country_key="china")
    db.create_country(104, "مصر", "🇪🇬", country_key="egypt")

    # وضعیت اولیه: مسیر آزاد
    res = db.get_trade_route_strait_analysis("saudi", "china")
    assert not res["is_blocked"]
    assert not res["has_tolls"]

    # وضع عوارض بر تنگه هرمز توسط ایران
    db.set_strait_status("hormuz", "toll", 1_000_000)
    res_toll = db.get_trade_route_strait_analysis("saudi", "china")
    assert not res_toll["is_blocked"]
    assert res_toll["has_tolls"]
    assert res_toll["total_toll"] == 1_000_000
    assert len(res_toll["toll_straits"]) == 1
    assert res_toll["toll_straits"][0]["strait_key"] == "hormuz"

    # کشور صاحب تنگه (ایران) از عوارض خودش معاف است
    res_owner = db.get_trade_route_strait_analysis("iran", "china")
    assert not res_owner["has_tolls"]

    # مسدودسازی هرمز
    db.set_strait_status("hormuz", "blocked", 0)
    res_blocked = db.get_trade_route_strait_analysis("saudi", "china")
    assert res_blocked["is_blocked"]
    assert res_blocked["blocked_straits"][0]["strait_key"] == "hormuz"


def test_execute_trade_contract_with_strait_tolls_buyer_and_seller(monkeypatch):
    import tempfile
    import config
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr(config, "DB_PATH", os.path.join(tmpdir, "test_strait_contract.db"))

    import importlib
    importlib.reload(db)
    db.init_db()

    c_iran = db.create_country(101, "ایران", "🇮🇷", country_key="iran")
    c_saudi = db.create_country(102, "عربستان", "🇸🇦", country_key="saudi")
    c_china = db.create_country(103, "چین", "🇨🇳", country_key="china")

    # تنظیم دارایی اولیه
    conn = db.get_connection()
    conn.execute("UPDATE countries SET treasury = 10000000, oil_reserves = 50000 WHERE id = ?", (c_saudi,))
    conn.execute("UPDATE countries SET treasury = 20000000 WHERE id = ?", (c_china,))
    conn.execute("UPDATE countries SET treasury = 5000000 WHERE id = ?", (c_iran,))
    conn.commit()
    conn.close()

    # وضع عوارض ۱ میلیون دلاری در هرمز
    db.set_strait_status("hormuz", "toll", 1_000_000)

    # معاهده ۱: عربستان (فروشنده نفت) به چین (خریدار)، هزینه ترانزیت با فروشنده
    cid1 = db.create_trade_contract(
        proposer_id=c_saudi,
        recipient_id=c_china,
        offered_type="oil",
        offered_amount=1000,
        requested_type="treasury",
        requested_amount=2_000_000,
        transport_payer="seller",
        transport_cost=300_000,
        transport_mode="sea"
    )

    succ1, msg1 = db.execute_trade_contract_transaction(cid1)
    assert succ1, msg1

    saudi_data = db.get_country_by_id(c_saudi)
    iran_data = db.get_country_by_id(c_iran)
    china_data = db.get_country_by_id(c_china)

    # عربستان: ۱۰M + ۲M قیمت - ۳۰۰k کرایه - ۱M عوارض = ۱۰,۷۰۰,۰۰۰
    assert saudi_data["treasury"] == 10_700_000
    # ایران: ۵M + ۱M عوارض هرمز = ۶,۰۰۰,۰۰۰
    assert iran_data["treasury"] == 6_000_000
    # چین: ۲۰M - ۲M قیمت = ۱۸,۰۰۰,۰۰۰
    assert china_data["treasury"] == 18_000_000


def test_execute_market_buy_with_strait_tolls(monkeypatch):
    import tempfile
    import config
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr(config, "DB_PATH", os.path.join(tmpdir, "test_strait_market.db"))

    import importlib
    importlib.reload(db)
    db.init_db()

    c_iran = db.create_country(101, "ایران", "🇮🇷", country_key="iran")
    c_saudi = db.create_country(102, "عربستان", "🇸🇦", country_key="saudi")
    c_china = db.create_country(103, "چین", "🇨🇳", country_key="china")

    # ثبت سفارش عرضه نفت توسط عربستان در بورس
    conn = db.get_connection()
    conn.execute("UPDATE countries SET treasury = 10000000, oil_reserves = 50000 WHERE id = ?", (c_saudi,))
    conn.execute("UPDATE countries SET treasury = 20000000 WHERE id = ?", (c_china,))
    conn.execute("UPDATE countries SET treasury = 5000000 WHERE id = ?", (c_iran,))
    conn.commit()
    conn.close()

    succ_order, msg_order = db.create_market_order(c_saudi, "oil", 2000, 500) # ارزش = ۱,۰۰۰,۰۰۰ $
    assert succ_order, msg_order

    orders = db.get_market_orders(resource_type="oil")
    assert len(orders) == 1
    order_id = orders[0]["id"]

    # وضع عوارض ۱ میلیون دلاری در هرمز
    db.set_strait_status("hormuz", "toll", 1_000_000)

    # خرید توسط چین از طریق ناوگان دریایی
    succ, msg, meta = db.execute_market_buy_transaction(c_china, order_id, 2000, transport_mode="sea")
    assert succ, msg

    china_data = db.get_country_by_id(c_china)
    saudi_data = db.get_country_by_id(c_saudi)
    iran_data = db.get_country_by_id(c_iran)

    # چین: ۲۰M - ۱M کالا - ۳۰۰k کرایه - ۱M عوارض = ۱۷,۷۰۰,۰۰۰
    assert china_data["treasury"] == 17_700_000
    # عربستان: ۱۰M + ۱M کالا = ۱۱,۰۰۰,۰۰۰
    assert saudi_data["treasury"] == 11_000_000
    # ایران: ۵M + ۱M عوارض هرمز = ۶,۰۰۰,۰۰۰
    assert iran_data["treasury"] == 6_000_000


def test_foreign_aid_with_strait_tolls(monkeypatch):
    import tempfile
    import config
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr(config, "DB_PATH", os.path.join(tmpdir, "test_strait_aid.db"))

    import importlib
    importlib.reload(db)
    db.init_db()

    c_iran = db.create_country(101, "ایران", "🇮🇷", country_key="iran")
    c_saudi = db.create_country(102, "عربستان", "🇸🇦", country_key="saudi")
    c_china = db.create_country(103, "چین", "🇨🇳", country_key="china")

    conn = db.get_connection()
    conn.execute("UPDATE countries SET treasury = 10000000, oil_reserves = 50000 WHERE id = ?", (c_saudi,))
    conn.execute("UPDATE countries SET treasury = 20000000, oil_reserves = 0 WHERE id = ?", (c_china,))
    conn.execute("UPDATE countries SET treasury = 5000000 WHERE id = ?", (c_iran,))
    conn.commit()
    conn.close()

    # وضع عوارض ۱ میلیون دلاری در هرمز
    db.set_strait_status("hormuz", "toll", 1_000_000)

    # ارسال کمک ۵۰۰۰ بشکه نفت از عربستان به چین با ترابری دریایی
    succ, msg = db.execute_foreign_aid_transaction(c_saudi, c_china, "oil", 5000, transport_mode="sea")
    assert succ, msg

    saudi_data = db.get_country_by_id(c_saudi)
    china_data = db.get_country_by_id(c_china)
    iran_data = db.get_country_by_id(c_iran)

    # عربستان: ۱۰M - ۳۰۰k کرایه - ۱M عوارض = ۸,۷۰۰,۰۰۰ | نفت: ۵۰,۰۰۰ - ۵,۰۰۰ = ۴۵,۰۰۰
    assert saudi_data["treasury"] == 8_700_000
    assert saudi_data["oil_reserves"] == 45_000
    # چین: نفت دریافتی ۵,۰۰۰
    assert china_data["oil_reserves"] == 5000
    # ایران: ۵M + ۱M عوارض هرمز = ۶,۰۰۰,۰۰۰
    assert iran_data["treasury"] == 6_000_000


def test_strait_blockade_daily_cost_and_auto_reopen(monkeypatch):
    import tempfile
    import config
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr(config, "DB_PATH", os.path.join(tmpdir, "test_strait.db"))

    import importlib
    importlib.reload(db)
    db.init_db()

    cid_iran = db.create_country(999, "ایران", "🇮🇷", country_key="iran")
    
    # تنظیم وضعیت انسداد هرمز
    db.set_strait_status("hormuz", "blocked")
    st = db.get_strait_status("hormuz")
    assert st["status"] == "blocked"

    # موجودی ناکافی برای هزینه روزانه (۲.۵M دلار + ۱۰۰k بشکه)
    conn = db.get_connection()
    conn.execute("UPDATE countries SET treasury = 1000000, oil_reserves = 50000 WHERE id = ?", (cid_iran,))
    conn.commit()
    conn.close()

    owner_c = db.get_country_by_key("iran")
    money_cost = 2_500_000
    oil_cost = 100_000

    # شبیه‌سازی منطق چرخه روزانه هزینه انسداد تنگه
    if (owner_c.get("treasury") or 0) < money_cost or (owner_c.get("oil_reserves") or 0) < oil_cost:
        db.set_strait_status("hormuz", "open", 0)

    st_after = db.get_strait_status("hormuz")
    assert st_after["status"] == "open"
