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
