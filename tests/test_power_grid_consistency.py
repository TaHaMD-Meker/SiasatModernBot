# -*- coding: utf-8 -*-
"""باگ گزارش بازیکن‌ها درباره‌ی برق:

۱) «مصرف برق بالا نمی‌رود»: کارخانه/معدن می‌خرند ولی list نیازها ناقص است —
   `calculate_country_requirements` فقط ۶ قلم را می‌شمارد (chip_fab، iron_mine،
   copper_mine، uranium_mine، enrichment_facility جا افتاده‌اند)؛ `power_status`
   و `POWER_CONSUMERS` لیست کامل دارند. یعنی خریدِ Chip Fab هیچ اثری روی
   «نیاز برق» گزارش روزانه ندارد ← «درصدش نمی‌رود بالا».
۲) «توان برق بالا نمی‌رود»: نیاز باید واحدهای «فعال» را بشمارد نه خاموش‌شده‌های
   نگهداری را — واحد خاموش برق نمی‌خواهد.
۳) «تراز انرژی» گمراه‌کننده بود: تولید را به‌عنوان درصد نشان می‌داد. حالا
   تراز واقعی (تولید − نیاز) نمایش داده می‌شود و در نمای آمادگی هم دیده می‌شود.
"""
import config
import database as db
import approval_system
from handlers import internal_affairs as ia_mod
import internal_affairs as ia


def _fresh(monkeypatch, tmp_path, name="pw.db", base_elec=100):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()
    cid = db.create_country(8100, "ایران", "🇮🇷", country_key="iran")
    db.update_country_field(cid, "treasury", 900_000_000)
    db.update_country_field(cid, "oil_reserves", 900_000_000)
    db.update_country_field(cid, "iron_ore", 90_000_000)
    db.update_country_field(cid, "tech_level", 3)  # پیش‌نیاز فب/غنی‌سازی
    return cid


def test_chip_fab_increases_elec_need(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = db.get_country_by_player(8100)["id"]
    before = approval_system.calculate_country_requirements(
        db.get_country_by_id(cid))["elec_need"]
    db.buy_item_transaction(cid, "chip_fab", 2,
                            config.ALL_SHOP_ITEMS["chip_fab"]["price"] * 2, "فب")
    after = approval_system.calculate_country_requirements(
        db.get_country_by_id(cid))["elec_need"]
    assert after - before == 2 * 4, "Chip Fab باید ۴ واحد برق به ازای هر واحد مصرف کند"


def test_iron_and_uranium_mines_and_enrichment_count_too(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "pw2.db")
    cid = db.get_country_by_player(8100)["id"]
    before = approval_system.calculate_country_requirements(
        db.get_country_by_id(cid))["elec_need"]
    for key, qty in (("iron_mine", 1), ("uranium_mine", 1), ("enrichment_facility", 1)):
        price = config.ALL_SHOP_ITEMS[key]["price"] * qty
        ok, msg = db.buy_item_transaction(cid, key, qty, price, key)
        assert ok, msg
    after = approval_system.calculate_country_requirements(
        db.get_country_by_id(cid))["elec_need"]
    assert after - before == 2 + 3 + 5, "معدن‌ها و غنی‌سازی هم مصرف‌کننده‌ی برق‌اند"


def test_offline_units_do_not_consume(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "pw3.db")
    cid = db.get_country_by_player(8100)["id"]
    db.buy_item_transaction(cid, "chip_fab", 1, config.ALL_SHOP_ITEMS["chip_fab"]["price"], "فب")
    # نگهداری را زمستانی کن: همه‌چیز خاموش شود (منابع صفر)
    db.update_country_field(cid, "oil_reserves", 0)
    db.update_country_field(cid, "iron_ore", 0)
    res = db.apply_building_upkeep(cid)
    assert res["shut_down"]

    c = db.get_country_by_id(cid)
    reqs = approval_system.calculate_country_requirements(c)
    assert reqs["elec_need"] == 100, "واحد خاموش نباید در نیاز برق بیاید"

    # power_status هم نباید برای واحد خاموش درآمد از‌دست‌رفته حساب کند
    p = ia.power_status(c)
    assert p["industrial_need"] == 0
    assert not p["offline"]


def test_power_status_sums_complete_consumers(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "pw4.db")
    cid = db.get_country_by_player(8100)["id"]
    for key, elec in ia.POWER_CONSUMERS.items():
        price = config.ALL_SHOP_ITEMS[key]["price"]
        db.buy_item_transaction(cid, key, 1, price, key)
    c = db.get_country_by_id(cid)
    p = ia.power_status(c)
    expected = sum(ia.POWER_CONSUMERS.values())
    assert p["industrial_need"] == expected
    reqs = approval_system.calculate_country_requirements(c)
    assert reqs["elec_need"] == 100 + expected, \
        "دو موتور محاسبه‌ی برق باید هم‌عدد باشند"
