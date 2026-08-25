# -*- coding: utf-8 -*-
"""
تست‌های سیستم دسته‌بندی قاره‌ای و جستجوی سریع کشورها (Continents & Search).
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from handlers.start import _clean_persian_str, build_continent_keyboard, build_continent_countries_keyboard  # noqa: E402


@pytest.fixture()
def seeded_db(monkeypatch):
    """دیتابیس موقت و ایزوله که چند کشور واقعی از قاره‌های مختلف در آن ثبت شده است.

    سازنده‌های کیبورد قاره‌ای، کشورها را از دیتابیس می‌خوانند؛ بنابراین بدون
    ثبت کشور، هیچ دکمه‌ای تولید نمی‌شود و تست‌ها بی‌دلیل شکست می‌خورند.
    """
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr(config, "DB_PATH", os.path.join(tmpdir, "test.db"))

    import database

    database.init_db()

    # دو کشور اروپایی و دو کشور خاورمیانه‌ای تا هر دو تست حداقل یک ردیف دکمه بگیرند
    database.create_country(100001, "آلمان", "🇩🇪", country_key="germany")
    database.create_country(100002, "فرانسه", "🇫🇷", country_key="france")
    database.create_country(100003, "ایران", "🇮🇷", country_key="iran")
    database.create_country(100004, "ترکیه", "🇹🇷", country_key="turkey")

    return database


def test_all_playable_countries_have_valid_continent():
    """تضمین اینکه تمام کشورهای بازی در یکی از قاره‌های تعریف‌شده قرار دارند."""
    continents = config.CONTINENTS
    assert len(continents) == 6

    all_keys = set()
    for c_info in continents.values():
        all_keys.update(c_info["keys"])

    for key in config.COUNTRIES.keys():
        if key in ("un", "kurdistan"):
            continue
        assert key in all_keys, f"کشور {key} در هیچ قاره‌ای قرار نگرفته است!"


def test_clean_persian_str_normalization():
    """تست پاک‌سازی و نرمال‌سازی کلمات جستجو."""
    assert _clean_persian_str("آلمان") == "المان"
    assert _clean_persian_str("  ایران  ") == "ایران"
    assert _clean_persian_str("Germany!") == "germany"
    assert _clean_persian_str("امارات_متحده") == "امارات متحده"


def test_continent_keyboards_structure(seeded_db):
    """بررسی ساختار دکمه‌های شیشه‌ای انتخاب قاره و کشورها."""
    kb_cont = build_continent_keyboard()
    assert len(kb_cont) >= 4  # ردیف‌های قاره‌ها + جستجو + گروه غیردولتی

    kb_mideast = build_continent_countries_keyboard("mideast")
    assert len(kb_mideast) >= 5
    
    # وجود دکمه جستجو و بازگشت
    last_row = kb_mideast[-1]
    assert any("جستجو" in btn.text for btn in last_row)
    assert any("قاره‌ها" in btn.text for btn in last_row)

def test_diplomacy_continent_helpers(seeded_db):
    from handlers.diplomacy import build_dip_continent_selector, build_dip_continent_countries_keyboard
    t, kb = build_dip_continent_selector("trade", "تجارت")
    assert len(kb.inline_keyboard) >= 4

    t2, kb2 = build_dip_continent_countries_keyboard("europe", "trade", 999)
    # حداقل یک ردیف کشور (آلمان/فرانسه) + ردیف جستجو و بازگشت
    assert len(kb2.inline_keyboard) >= 2
    assert any(
        "آلمان" in btn.text or "فرانسه" in btn.text
        for row in kb2.inline_keyboard
        for btn in row
    )


def test_intel_target_continent_helpers(seeded_db):
    from handlers.intel import build_intel_continent_countries_keyboard
    t, kb = build_intel_continent_countries_keyboard("mideast", "cyber_blackout", 123)
    # حداقل یک ردیف کشور (ایران/ترکیه) + ردیف جستجو و بازگشت
    assert len(kb.inline_keyboard) >= 2
    assert any(
        "ایران" in btn.text or "ترکیه" in btn.text
        for row in kb.inline_keyboard
        for btn in row
    )
