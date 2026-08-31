# -*- coding: utf-8 -*-
"""تست‌های مکانیک مصرف روزانهٔ منابع (گندم/نفت) بر اساس جمعیت و صنایع.

این تست‌ها سه قانون کلیدی پیشنهاد بازیکن را قفل می‌کنند:
۱) تولید روزانه به ذخیره واریز می‌شود (تا قبل از این سقف اعتبار نداشت).
۲) مصرف جمعیت و صنایع از ذخیره کسر می‌شود (بدون منفی‌شدن موجودی).
۳) کمبود گندم = قحطی (افت رضایت + ریزش جمعیت)؛ کمبود نفت = افت رضایت.
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402


@pytest.fixture()
def db(monkeypatch):
    """یک دیتابیس موقت و ایزوله برای هر تست."""
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr(config, "DB_PATH", os.path.join(tmpdir, "test.db"))

    import importlib
    import database
    importlib.reload(database)

    database.init_db()
    database.create_country(111111, "ایران", "🇮🇷", country_key="iran")
    return database


def _set(db, cid, **cols):
    for k, v in cols.items():
        db.update_country_field(cid, k, v)


def test_production_credited_before_consumption(db):
    """تولید روزانه اول به ذخیره واریز، سپس مصرف از آن برداشت می‌شود."""
    import internal_affairs

    c = db.get_all_countries()[0]
    _set(db, c["id"], population=1_000_000,
         grain=500, grain_daily=3_000,
         oil_reserves=100_000, oil_production=500)
    res = internal_affairs.process_daily_resource_consumption(db.get_country_by_id(c["id"]))
    f = db.get_country_by_id(c["id"])
    # گندم: ۵۰۰ + ۳۰۰۰ − نیاز جمعیت (pop=1M ⇒ ۱٬۰۱۵ تن) ⇒ ۲٬۴۸۵ به‌جا می‌ماند
    assert res["grain_need"] > 100
    assert f["grain"] == 500 + 3_000 - res["grain_need"]
    # نیاز نفت به جمعیت ۱ میلیون (۱۰٬۰۰۰ بشکه) از ۱۰۰٬۵۰۰ بشکه کسر می‌شود
    assert f["oil_reserves"] == 100_000 + 500 - res["oil_need"]


def test_no_negative_stock_under_shortage(db):
    """کمبود سنگین: ذخیره به صفر کلمپ و هرگز منفی نمی‌شود."""
    import internal_affairs

    c = db.get_all_countries()[0]
    _set(db, c["id"], population=1_000_000,
         grain=50, grain_daily=0,
         oil_reserves=100, oil_production=0)
    res = internal_affairs.process_daily_resource_consumption(db.get_country_by_id(c["id"]))
    f = db.get_country_by_id(c["id"])
    assert f["grain"] == 0
    assert f["oil_reserves"] == 0
    assert res["grain_shortage"] > 0
    assert res["oil_shortage"] > 0


def test_grain_shortage_is_famine(db):
    """قحطی: کمبود غلات علاوه بر رضایت، جمعیت را هم می‌کاهد."""
    import internal_affairs

    c = db.get_all_countries()[0]
    _set(db, c["id"], population=1_000_000, approval_rating=90,
         grain=0, grain_daily=0,
         # نفت فراوان تا مسیر کمبود گندم جدا تست شود
         oil_reserves=5_000_000, oil_production=0)
    internal_affairs.process_daily_resource_consumption(db.get_country_by_id(c["id"]))
    f = db.get_country_by_id(c["id"])
    assert f["approval_rating"] == 87  # -3
    assert f["population"] == 999_000  # ۰/۱٪ = ۱٬۰۰۰ نفر ریزش


def test_oil_shortage_drops_approval_without_famine(db):
    """بحران انرژی: کمبود نفت رضایت را می‌کاهد ولی جمعیت دست می‌ماند."""
    import internal_affairs

    c = db.get_all_countries()[0]
    _set(db, c["id"], population=1_000_000, approval_rating=90,
         grain=500_000, grain_daily=0,
         oil_reserves=0, oil_production=0)
    internal_affairs.process_daily_resource_consumption(db.get_country_by_id(c["id"]))
    f = db.get_country_by_id(c["id"])
    assert f["approval_rating"] == 87
    assert f["population"] == 1_000_000


def test_selfsufficient_country_has_no_penalty(db):
    """کشور با تولید کافی متوازن می‌ماند: بدون جریمه، بدون کمبود."""
    import internal_affairs

    c = db.get_all_countries()[0]
    _set(db, c["id"], population=1_000_000, approval_rating=75,
         grain=10_000, grain_daily=5_000,
         oil_reserves=10_000, oil_production=50_000)
    res = internal_affairs.process_daily_resource_consumption(db.get_country_by_id(c["id"]))
    f = db.get_country_by_id(c["id"])
    assert res["grain_shortage"] == 0 and res["oil_shortage"] == 0
    assert f["approval_rating"] == 75
    assert f["population"] == 1_000_000


def test_disabled_flag_makes_noop(db, monkeypatch):
    """کلید کانفیگ کامل خاموش: نه واریز تولید، نه مصرف، نه جریمه."""
    monkeypatch.setattr(config, "RESOURCE_CONSUMPTION_ENABLED", False)
    import internal_affairs

    c = db.get_all_countries()[0]
    _set(db, c["id"], grain=100, grain_daily=3_000, oil_reserves=100, oil_production=5_000)
    res = internal_affairs.process_daily_resource_consumption(db.get_country_by_id(c["id"]))
    f = db.get_country_by_id(c["id"])
    assert f["grain"] == 100 and f["oil_reserves"] == 100
    assert all(v == 0 for k, v in res.items())
