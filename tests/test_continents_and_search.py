# -*- coding: utf-8 -*-
"""
تست‌های سیستم دسته‌بندی قاره‌ای و جستجوی سریع کشورها (Continents & Search).
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
from handlers.start import _clean_persian_str, build_continent_keyboard, build_continent_countries_keyboard  # noqa: E402


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


def test_continent_keyboards_structure():
    """بررسی ساختار دکمه‌های شیشه‌ای انتخاب قاره و کشورها."""
    kb_cont = build_continent_keyboard()
    assert len(kb_cont) >= 4  # ردیف‌های قاره‌ها + جستجو + گروه غیردولتی

    kb_mideast = build_continent_countries_keyboard("mideast")
    assert len(kb_mideast) >= 5
    
    # وجود دکمه جستجو و بازگشت
    last_row = kb_mideast[-1]
    assert any("جستجو" in btn.text for btn in last_row)
    assert any("قاره‌ها" in btn.text for btn in last_row)
