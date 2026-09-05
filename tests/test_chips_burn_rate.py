# -*- coding: utf-8 -*-
"""اقتصاد جدید تراشه — «تراشه = نرخ آتش جنگ مدرن» (تایید مالک، بدون شکستن بالانس).

اصول بالانس (تعهد مالک: «گند نزنی»):
• سینک فقط «رویدادمحور» است — هیچ مالیات روزانه‌ی جدیدی به کشورهای غیرجنگی نمی‌خورد.
• کسری تراشه هرگز عملیات را رد نمی‌کند و منفی نمی‌شود: MAX(0, ...) — فقط سقف
  تعداد موشک/پهپادِ قابل‌فiring تا سقف تراشه موجود است.
• نرخ‌ها: کروز/بالستیک/ضدکشتی=15، هایپرسونیک=30، پهپاد انتحاری/کروز=3،
  شناسایی=1؛ نسل۵ و بمب‌افکن پنهان‌کار از قبل 8 داشتند (بدون تغییر).
"""
import config
import database as db


def test_launch_costs_exist_and_are_reasonable():
    assert config.MISSILE_LAUNCH_CHIPS["cruise"] == 15
    assert config.MISSILE_LAUNCH_CHIPS["ballistic"] == 15
    assert config.MISSILE_LAUNCH_CHIPS["anti_ship"] == 15
    assert config.MISSILE_LAUNCH_CHIPS["hypersonic"] == 30
    assert config.DRONE_LAUNCH_CHIPS["drone_combat"] == 3
    assert config.DRONE_LAUNCH_CHIPS["drone_recon"] == 1


def test_max_launchable_caps_by_chips():
    # 500 تراشه → حداکثر 33 موشک کروز (نه صفر، نه منفی)
    assert db.max_launchable("cruise", 500) == 33
    assert db.max_launchable("cruise", 0) == 0
    # هایپرسونیک: 100 تراشه → 3 فروند
    assert db.max_launchable("hypersonic", 100) == 3
    # پهپاد: 61 تراشه → 20 انتحاری
    assert db.max_launchable("drone_combat", 61) == 20
    # نوع ناشناخته → بی‌نهایت (چیزی سد نمی‌شود)
    assert db.max_launchable("unknown_type", 0) is None


def test_consume_launch_chips_atomic_and_floor_zero(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "chips.db"))
    db.init_db()
    cid = db.create_country(8200, "ایران", "🇮🇷", country_key="iran")
    db.update_country_field(cid, "microchips", 100)

    ok, msg = db.consume_launch_chips(cid, "cruise", 5)  # 5×15=75
    assert ok
    assert db.get_country_by_id(cid)["microchips"] == 25

    # درخواست بیش از موجودی → رد، بدون منفی شدن
    ok2, msg2 = db.consume_launch_chips(cid, "cruise", 5)  # 75 > 25
    assert not ok2 and "تراشه" in msg2
    assert db.get_country_by_id(cid)["microchips"] == 25, "کسر ناکام نباید اجرا شود"

    # کسر با سقف ایمن: هرچه هست (25) برای 1 فروند کافی است
    ok3, _ = db.consume_launch_chips(cid, "cruise", 1)
    assert ok3 and db.get_country_by_id(cid)["microchips"] == 10


def test_classify_missile_name_for_launch_chips():
    assert db.classify_launch_type("موشک کروز استراتژیک بومی 3M-54 Kalibr") == "cruise"
    assert db.classify_launch_type("موشک بالستیک نقطه‌زن اسکندر-M") == "ballistic"
    assert db.classify_launch_type("موشک کروز هایپرسونیک ضدکشتی بومی 3M22 Zircon") == "hypersonic"
    assert db.classify_launch_type("موشک هواپایه هایپرسونیک بومی Kh-47M2 Kinzhal") == "hypersonic"
    assert db.classify_launch_type("موشک سنگین مافوق‌صوت ضدکشتی بومی Kh-32") == "anti_ship"
    assert db.classify_launch_type("سامانه موشکی تاکتیکی بومی 9K720 Iskander-M") == "ballistic"
    assert db.classify_launch_type("موشک ضدتانک هدایت سیمی") is None  # تاکتیکی سبک نه
    assert db.classify_launch_type("پهپاد انتحاری دوربرد بومی گران-۲") == "drone_combat"
    assert db.classify_launch_type("پهپادهای شناسایی و هدایت لیزری بومی Orlan-10") == "drone_recon"


def test_hypersonic_scan_priority():
    # «کروز هایپرسونیک» باید هایپرسونیک شود نه کروز (اولویت اسکن)
    assert db.classify_launch_type("موشک کروز هایپرسونیک ضدکشتی بومی 3M22 Zircon") == "hypersonic"


def test_unknown_missile_falls_back_to_cruise():
    assert db.classify_launch_type("موشک بی‌نام و نشون") == "cruise"
    assert db.classify_launch_type("Tactical Noname Missile") == "cruise"


def test_light_tactical_weapons_burn_nothing():
    assert db.classify_launch_type("موشک ضدتانک هدایت سیمی حمله از بالا RBS-56B BILL 2") is None
    assert db.classify_launch_type("سامانه موشک ضدتانک سنگین PAL 2000 (TOW-2)") is None
    assert db.classify_launch_type("راکت‌انداز چندمنظوره Carl Gustaf M4") is None


def test_report_burns_chips_for_missiles_and_drones(monkeypatch, tmp_path):
    import os
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "burn.db"))
    db.init_db()
    cid = db.create_country(8300, "روسیه", "🇷🇺", country_key="russia")
    db.update_country_field(cid, "microchips", 5_000)
    items = [
        {"key": "kalibr", "name": "موشک کروز استراتژیک بومی 3M-54 Kalibr", "qty": 90, "category": "Missiles"},
        {"key": "kh101_cruise", "name": "موشک کروز پنهان‌کار هواپایه بومی Kh-101 / Kh-102", "qty": 55, "category": "Missiles"},
        {"key": "zircon_hypersonic", "name": "موشک کروز هایپرسونیک ضدکشتی بومی 3M22 Zircon", "qty": 5, "category": "Missiles"},
        {"key": "geran2_drone", "name": "پهپاد انتحاری دوربرد بومی گران-۲ (Geran-2)", "qty": 120, "category": "Drones"},
    ]
    ok, _rid, err = db.create_loss_report(cid, items, operation_name="عملیات آزمایشی")
    assert ok, err
    # (90+55)×15 + 5×30 + 120×3 = 2,685
    assert db.get_country_by_id(cid)["microchips"] == 5_000 - 2_685


def test_burn_never_goes_negative(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "burn2.db"))
    db.init_db()
    cid = db.create_country(8301, "روسیه", "🇷🇺", country_key="russia")
    db.update_country_field(cid, "microchips", 50)  # خیلی کمتر از نیاز 145 موشک
    items = [
        {"key": "kalibr", "name": "موشک کروز استراتژیک بومی 3M-54 Kalibr", "qty": 90, "category": "Missiles"},
    ]
    ok, _rid, err = db.create_loss_report(cid, items, operation_name="عملیات کم‌تراشه")
    assert ok, err  # گزارش پذیرفته می‌شود (کسر تراشه هرگز گزارش را رد نمی‌کند)
    assert db.get_country_by_id(cid)["microchips"] == 0  # کف صفر — بدون منفی
