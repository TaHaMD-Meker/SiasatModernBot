# -*- coding: utf-8 -*-
"""
تست‌های اعتبارسنجی ۵ کشور جدید قاره اروپا:
ایرلند (ireland)، لیتوانی (lithuania)، اسلوونی (slovenia)، آلبانی (albania)، بوسنی و هرزگوین (bosnia)
"""

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import database as db  # noqa: E402

EUROPE_5_KEYS = ["ireland", "lithuania", "slovenia", "albania", "bosnia"]


def test_europe_5_countries_presence_in_config():
    """بررسی ثبت نام، پرچم و حضور ۵ کشور در قاره اروپا."""
    for key in EUROPE_5_KEYS:
        assert key in config.COUNTRIES, f"Country {key} missing from COUNTRIES"
        c_info = config.COUNTRIES[key]
        assert "name" in c_info and len(c_info["name"]) > 0
        assert "flag" in c_info and len(c_info["flag"]) > 0

    assert "europe" in config.CONTINENTS
    for key in EUROPE_5_KEYS:
        assert key in config.CONTINENTS["europe"]["keys"], f"{key} missing from CONTINENTS['europe']['keys']"


def test_europe_5_overrides_and_stats():
    """بررسی معتبر بودن متغیرها و آمار اولیه اقتصادی/نظامی."""
    for key in EUROPE_5_KEYS:
        assert key in config.COUNTRY_STARTING_OVERRIDES, f"{key} missing from COUNTRY_STARTING_OVERRIDES"
        stats = config.COUNTRY_STARTING_OVERRIDES[key]
        assert stats["population"] > 0
        assert stats["treasury"] > 0
        assert stats["daily_income"] > 0
        assert stats["tax_income"] > 0
        assert stats["active_personnel"] > 0


def test_europe_5_equipment_catalogs_count_and_categories():
    """بررسی اینکه هر یک از ۵ کشور حداقل ۴۰ قلم تجهیزات کامل دارند."""
    required_cats = {"Aircraft", "UAV", "Ground Forces", "Artillery", "Navy", "Missiles", "Air Defense"}
    for key in EUROPE_5_KEYS:
        assert key in config.COUNTRY_EQUIPMENT_CATALOG, f"{key} missing from COUNTRY_EQUIPMENT_CATALOG"
        items = config.COUNTRY_EQUIPMENT_CATALOG[key]
        assert len(items) >= 40, f"{key} has only {len(items)} items (must be >= 40)"

        cats_present = {item["category"] for item in items}
        for req_cat in required_cats:
            assert req_cat in cats_present, f"Category {req_cat} missing in {key} catalog"

        # بررسی ساختار هر تجهیز
        for item in items:
            assert "key" in item and len(item["key"]) > 0
            assert "name" in item and len(item["name"]) > 0
            assert "category" in item and item["category"] in config.ASSET_CATEGORIES
            assert "price" in item and item["price"] > 0
            assert "maint" in item and item["maint"] >= 0
            assert "initial" in item and item["initial"] > 0
            assert "producible" in item and isinstance(item["producible"], bool)


def test_europe_5_database_creation_and_seeding(monkeypatch):
    """بررسی ایجاد موفق کشور در پایگاه داده و درج کامل بیش از ۴۰ قلم تجهیزات."""
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr(config, "DB_PATH", os.path.join(tmpdir, "test_europe_5.db"))

    import importlib
    importlib.reload(db)
    db.init_db()

    for idx, key in enumerate(EUROPE_5_KEYS, start=1001):
        c_info = config.COUNTRIES[key]
        cid = db.create_country(idx, c_info["name"], c_info["flag"], country_key=key)
        assert cid is not None

        c_data = db.get_country_by_id(cid)
        assert c_data["country_key"] == key
        assert c_data["name"] == c_info["name"]

        # بررسی تعداد تجهیزات ثبت شده در دیتابیس
        assets = db.get_country_assets(cid)
        catalog_len = len(config.COUNTRY_EQUIPMENT_CATALOG[key])
        assert len(assets) == catalog_len
        assert len(assets) >= 40


def test_europe_5_maritime_routing():
    """بررسی مسیریابی دریایی ۵ کشور جدید اروپا."""
    # ایرلند و لیتوانی از اقیانوس اطلس وارد سوئز می‌شوند
    assert db.is_trade_route_crossing_strait("ireland", "india", "suez")
    assert db.is_trade_route_crossing_strait("lithuania", "china", "suez")
    assert db.is_trade_route_crossing_strait("lithuania", "usa", "danish_straits")

    # اسلوونی، آلبانی و بوسنی در مدیترانه هستند و برای خروج به اطلس از جبل‌الطارق عبور می‌کنند
    assert db.is_trade_route_crossing_strait("slovenia", "usa", "gibraltar_north")
    assert db.is_trade_route_crossing_strait("albania", "brazil", "gibraltar_south")
    assert db.is_trade_route_crossing_strait("bosnia", "canada", "gibraltar_north")
