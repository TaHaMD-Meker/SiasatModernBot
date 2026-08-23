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
