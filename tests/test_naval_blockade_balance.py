# -*- coding: utf-8 -*-
"""
تست‌های اعتبارسنجی بالانس و موازنه قدرت ژئوپلیتیک در محاصره دریایی و شکستن محاصره.
"""

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import database as db  # noqa: E402


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    test_db_path = os.path.join(tmpdir, "test_naval_balance.db")
    monkeypatch.setattr(config, "DB_PATH", test_db_path)
    import importlib
    importlib.reload(db)
    db.init_db()
    yield test_db_path


def test_naval_power_realism_usa_vs_iran():
    """بررسی واقع‌گرایی قدرت ناوبری دریایی آمریکا و ایران بر اساس تجهیزات کاتالوگ."""
    usa_id = db.create_country(1001, "آمریکا", "🇺🇸", country_key="usa")
    iran_id = db.create_country(1002, "ایران", "🇮🇷", country_key="iran")

    usa_power = db.calculate_naval_power(usa_id)
    iran_power = db.calculate_naval_power(iran_id)

    # آمریکا دارای ۱۱ ناو هواپیمابر و ده‌ها ناوشکن ایجیس و زیردریایی اتمی است
    assert usa_power >= 15000
    # ایران دارای ناوچه‌ها و قایق‌های تندرو و زیردریایی‌های ساحلی است
    assert 500 <= iran_power <= 2000
    # نسبت قدرت ناوبری آمریکا به مراتب بیشتر از ایران است
    assert usa_power > iran_power * 10


def test_antiship_tokens_recognition():
    """شناسایی دقیق انواع موشک‌های ضدکشتی، هایپرسونیک و کروز در انبار کشورها."""
    test_keys = [
        "noor_antiship", "qader_antiship", "khalij_fars", "zircon_hypersonic",
        "brahmos", "exocet_mm40_eg", "harpoon_saudi", "rbs15_fi", "atmaca_antiship",
        "yj18", "nsm_no", "c802_id", "kalibr", "paveh_c"
    ]
    for key in test_keys:
        assert db._is_antiship_key(key), f"Key {key} should be recognized as anti-ship / cruise"


def test_iran_cannot_break_usa_blockade_realism():
    """تست کلیدی: ایران به دلیل برتری مطلق تناژ و پدافند لایه‌ای ایجیس آمریکا نمی‌تواند محاصره کل ناوگان آمریکا را بشکند."""
    usa_id = db.create_country(1001, "آمریکا", "🇺🇸", country_key="usa")
    iran_id = db.create_country(1002, "ایران", "🇮🇷", country_key="iran")

    # اعمال محاصره دریایی توسط آمریکا علیه ایران
    db.create_naval_blockade(usa_id, iran_id)
    assert db.is_country_blockaded(iran_id)

    usa_power = db.calculate_naval_power(usa_id)
    iran_navy, iran_ashm_power, iran_total_power = db.calculate_blockade_break_power(iran_id)

    # توان کل مدافع کمتر از قدرت ناوگان محاصره‌کننده آمریکا است
    assert iran_total_power < usa_power

    # بررسی شکست عملیات شکستن محاصره در موازنه رزمی
    required_power = max(usa_power, 1)
    is_success = (iran_total_power >= required_power)
    assert not is_success

    # در صورت شکست، بخشی از مهمات در آتشباری ساحلی ناموفق مصرف می‌شود ولی محاصره پابرجاست
    initial_stock = db.get_antiship_missile_stock(iran_id)
    spent = db.consume_antiship_missiles(iran_id, max(1, min(initial_stock, max(1, int(initial_stock * 0.15)))))
    assert spent > 0
    assert db.is_country_blockaded(iran_id)


def test_russia_breaks_uk_blockade_with_massive_salvo():
    """کشوری با ناوگان معتبر و ذخایر سنگین هایپرسونیک/کروز (مانند روسیه علیه بریتانیا) توان شکست محاصره را دارد."""
    uk_id = db.create_country(1003, "انگلیس", "🇬🇧", country_key="uk")
    russia_id = db.create_country(1004, "روسیه", "🇷🇺", country_key="russia")

    db.create_naval_blockade(uk_id, russia_id)
    assert db.is_country_blockaded(russia_id)

    uk_power = db.calculate_naval_power(uk_id)
    rus_navy, rus_ashm_power, rus_total_power = db.calculate_blockade_break_power(russia_id)

    # روسیه با بیش از ۴۰۰۰ موشک ضدکشتی/کروز و یگان‌های زیرسطحی توان شکست محاصره ناوگان بریتانیا را دارد
    assert rus_total_power >= uk_power

    # اجرای موفقیت‌آمیز شکستن محاصره
    init_stock = db.get_antiship_missile_stock(russia_id)
    spent = db.consume_antiship_missiles(russia_id, max(1, min(init_stock, max(1, int(init_stock * 0.30)))))
    assert spent > 0
    db.break_naval_blockade(russia_id)

    # محاصره با موفقیت شکسته شده است
    assert not db.is_country_blockaded(russia_id)


def test_landlocked_countries_cannot_be_blockaded():
    """کشورهای محصور در خشکی نمی‌توانند در محاصره دریایی شرکت کنند."""
    assert not db.has_open_sea_access("afghanistan")
    assert not db.has_open_sea_access("armenia")
    assert not db.has_open_sea_access("austria")
    assert not db.has_open_sea_access("bolivia")
    assert db.has_open_sea_access("iran")
    assert db.has_open_sea_access("usa")
