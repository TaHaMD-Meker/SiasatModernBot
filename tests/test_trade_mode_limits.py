# -*- coding: utf-8 -*-
"""تست‌های سیستم سقف روزانه تجارت به تفکیک روش‌های ترابری (دریایی/هوایی/زمینی) و زیرساخت‌ها."""

import config
import database as db


def _fresh(monkeypatch, tmp_path, name="trade_limits.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


def _country(pid, key="usa", treasury=100_000_000):
    cid = db.create_country(pid, f"کشور {key}", "🏳️", country_key=key)
    db.update_country_field(cid, "treasury", treasury)
    db.update_country_field(cid, "gold", 1000)
    return cid


def test_fabric_country_base_trade_limits(monkeypatch, tmp_path):
    """کشور فابریک و بدون زیرساخت در روز ۲ تجارت دریایی، ۲ هوایی و ۲ زمینی دارد."""
    _fresh(monkeypatch, tmp_path)
    c1 = _country(8001, "c1")
    assert db.get_trade_mode_daily_limit(c1, "sea") == 2
    assert db.get_trade_mode_daily_limit(c1, "air") == 2
    assert db.get_trade_mode_daily_limit(c1, "land") == 2


def test_trade_mode_limit_blocks_3rd_trade_for_fabric_country(monkeypatch, tmp_path):
    """ثبت ۲ تجارت دریایی مجاز است و در تلاش سوم پیام لیمیت و راهنما برگردانده می‌شود."""
    _fresh(monkeypatch, tmp_path)
    a = _country(8002, "a")
    b = _country(8003, "b")

    # تجارت اول دریایی
    ok1, _ = db.check_trade_mode_limit(a, "sea")
    assert ok1
    c1 = db.create_trade_contract(a, b, "gold", 1, "treasury", 1000, transport_mode="sea")
    assert c1 > 0
    assert db.get_trade_mode_day_count(a, "sea") == 1

    # تجارت دوم دریایی
    ok2, _ = db.check_trade_mode_limit(a, "sea")
    assert ok2
    c2 = db.create_trade_contract(a, b, "gold", 1, "treasury", 1000, transport_mode="sea")
    assert c2 > 0
    assert db.get_trade_mode_day_count(a, "sea") == 2

    # تلاش سوم دریایی -> لیمیت
    ok3, msg3 = db.check_trade_mode_limit(a, "sea")
    assert not ok3
    assert "سقف مجاز تجارت دریایی امروز پر شده است" in msg3
    assert "بندر" in msg3
    assert "2 از 2" in msg3 or "۲ از ۲" in msg3 or "`2` از `2`" in msg3

    # روش‌های هوایی و زمینی همچنان ظرفیت دارند
    ok_air, _ = db.check_trade_mode_limit(a, "air")
    assert ok_air
    ok_land, _ = db.check_trade_mode_limit(a, "land")
    assert ok_land


def test_ports_increase_sea_trade_limit(monkeypatch, tmp_path):
    """هر بندر تجاری +۱ به سقف روزانه تجارت دریایی اضافه می‌کند (۲ بندر = سقف ۴)."""
    _fresh(monkeypatch, tmp_path)
    c = _country(8004, "port_master")
    # پایه ۲
    assert db.get_trade_mode_daily_limit(c, "sea") == 2

    # احداث ۲ بندر تجاری
    db.add_equipment(c, "port", 2)
    assert db.get_trade_mode_daily_limit(c, "sea") == 4

    # احداث ۱ بندر بزرگ استراتژیک -> سقف ۵
    db.add_equipment(c, "mega_port", 1)
    assert db.get_trade_mode_daily_limit(c, "sea") == 5


def test_airports_increase_air_trade_limit(monkeypatch, tmp_path):
    """هر فرودگاه بین‌المللی +۱ به سقف روزانه تجارت هوایی اضافه می‌کند."""
    _fresh(monkeypatch, tmp_path)
    c = _country(8005, "air_master")
    assert db.get_trade_mode_daily_limit(c, "air") == 2

    db.add_equipment(c, "airport", 1)
    assert db.get_trade_mode_daily_limit(c, "air") == 3

    db.add_equipment(c, "airport", 2)
    assert db.get_trade_mode_daily_limit(c, "air") == 5


def test_highways_increase_land_trade_limit(monkeypatch, tmp_path):
    """هر بزرگراه سراسری (جاده) +۱ به سقف روزانه تجارت زمینی اضافه می‌کند."""
    _fresh(monkeypatch, tmp_path)
    c = _country(8006, "road_master")
    assert db.get_trade_mode_daily_limit(c, "land") == 2

    db.add_equipment(c, "highway", 3)
    assert db.get_trade_mode_daily_limit(c, "land") == 5


def test_rejecting_or_canceling_contract_frees_daily_slot(monkeypatch, tmp_path):
    """لغو یا رد قرارداد سهمیه روزانه مصرف‌شده را آزاد می‌کند."""
    _fresh(monkeypatch, tmp_path)
    a = _country(8007, "a_c")
    b = _country(8008, "b_c")

    cid = db.create_trade_contract(a, b, "gold", 1, "treasury", 1000, transport_mode="land")
    assert db.get_trade_mode_day_count(a, "land") == 1

    # لغو قرارداد توسط پیشنهاددهنده
    ok_cancel, _ = db.cancel_pending_contract_by_proposer(a, cid)
    assert ok_cancel
    assert db.get_trade_mode_day_count(a, "land") == 0

    # قرارداد دوم و رد توسط دریافت‌کننده
    cid2 = db.create_trade_contract(a, b, "gold", 1, "treasury", 1000, transport_mode="air")
    assert db.get_trade_mode_day_count(a, "air") == 1
    ok_reject, _ = db.reject_trade_contract(cid2, b)
    assert ok_reject
    assert db.get_trade_mode_day_count(a, "air") == 0
