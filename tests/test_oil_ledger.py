# -*- coding: utf-8 -*-
"""گزارش پلیر آلمان: «هر شب نفتم یکهو صفر می‌شود — غروب ۱۲ میلیون داشتم.»

شبیه‌سازی لجر با پرتفوی نهنگِ آلمان نشان داد مصرف استاندارد شبانه ~۳-۴ میلیون
است، نه ۱۲. مشکل واقعی: هیچ‌کدام از کسرهای شبانه‌ی نفت **جایی ثبت نمی‌شوند** —
نه پلیر می‌فهمد چه خورد، نه مالک می‌تواند دیاگنوز کند، و وقتی نیاز از موجودی
بیشتر شود موجودی بی‌توضیح صفر می‌شود (MAX(0, …)).

قرارداد: هر کسر/واریز شبانه‌ی نفت باید در «دفتر نفت» آن کشور و آن تاریخ ثبت شود؛
جمع دلتاهای دفتر باید دقیقاً برابر تغییر ذخیره باشد (دفتر دروغ نگوید)؛
و در کسری، عبارت «ذخیره صفر شد چون نیاز بیشتر بود» ثبت شود.
"""
import config
import database as db
import internal_affairs as ia


def _fresh(monkeypatch, tmp_path, name="oilledger.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()
    cid = db.create_country(9300, "آلمان", "🇩🇪", country_key="germany")
    db.update_country_field(cid, "population", 84_000_000)
    db.update_country_field(cid, "oil_reserves", 12_000_000)
    db.update_country_field(cid, "oil_production", 30_000)
    db.update_country_field(cid, "treasury", 500_000_000)
    db.update_country_field(cid, "iron_ore", 50_000_000)
    db.update_country_field(cid, "microchips", 5_000_000)
    db.update_country_field(cid, "grain", 5_000_000)
    db.update_country_field(cid, "nuclear_fuel", 100_000)
    return cid


def _add_building(cid, key, qty):
    conn = db.get_connection()
    with conn:
        conn.execute("INSERT INTO equipment (country_id, item_key, quantity) VALUES (?,?,?)",
                     (cid, key, qty))
    conn.close()


# ───────────── ۱) دفتر ثبت می‌کند و دروغ نمی‌گوید ─────────────

def test_ledger_records_every_nightly_oil_write(monkeypatch, tmp_path):
    cid = _fresh(monkeypatch, tmp_path, "oilledger2.db")
    before = db.get_country_by_id(cid)["oil_reserves"]

    # هر رخدادِ واقعی = نوشته به ذخیره + ردیف دفتر (جفت‌جفت، مثل سیم‌کشی واقعی)
    db.adjust_oil(cid, +30_000); db.record_oil_event(cid, +30_000, "تولید روزانه")
    db.adjust_oil(cid, -2_500_000); db.record_oil_event(cid, -2_500_000, "مصرف جمعیت و صنایع")
    db.adjust_oil(cid, -677_800); db.record_oil_event(cid, -677_800, "نگهداری سازه‌ها")
    db.adjust_oil(cid, -130_865); db.record_oil_event(cid, -130_865, "سوخت نیروهای مسلح")
    after = db.get_country_by_id(cid)["oil_reserves"]

    ledger = db.get_oil_ledger(cid)
    assert len(ledger) == 4, "همه‌ی رخدادهای شب باید در دفتر باشد"
    total = sum(e["delta"] for e in ledger)
    assert total == after - before, "جمع دفتر باید دقیقاً تغییر ذخیره باشد"
    assert any("صنایع" in e["reason"] for e in ledger)


def test_ledger_is_per_day_and_readable_as_report_line(monkeypatch, tmp_path):
    cid = _fresh(monkeypatch, tmp_path, "oilledger3.db")
    db.record_oil_event(cid, -1_000, "آزمون دیروز")
    # تاریخ دیروز را دستی ثبت می‌کنیم
    import datetime
    yest = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()
    db.record_oil_event(cid, -2_000, "آزمون امروز", day=yest)

    today_l = db.get_oil_ledger(cid)
    yest_l = db.get_oil_ledger(cid, day=yest)
    assert [e["delta"] for e in today_l] == [-1_000]
    assert [e["delta"] for e in yest_l] == [-2_000]

    line = db.format_oil_ledger(today_l)
    assert "آزمون دیروز" in line and "-1,000" in line, "گزارش خوانا با اعداد جداشده"


# ───────────── ۲) مسیرهای واقعی شب باید خودشان ثبت کنند ─────────────

def test_resource_consumption_logs_itself(monkeypatch, tmp_path):
    cid = _fresh(monkeypatch, tmp_path, "oilledger4.db")
    _add_building(cid, "fossil_plant", 10)
    before = db.get_country_by_id(cid)["oil_reserves"]

    ia.process_daily_resource_consumption(db.get_country_by_id(cid))

    ledger = db.get_oil_ledger(cid)
    assert any("جمعیت" in e["reason"] for e in ledger), "مصرف جمعیت/صنایع باید ثبت شود"
    total = sum(e["delta"] for e in ledger)
    assert total == db.get_country_by_id(cid)["oil_reserves"] - before


def test_building_upkeep_logs_its_oil(monkeypatch, tmp_path):
    cid = _fresh(monkeypatch, tmp_path, "oilledger5.db")
    _add_building(cid, "fossil_plant", 10)   # ۱۰ × ۲۰هزار = ۲۰۰هزار نفت
    before = db.get_country_by_id(cid)["oil_reserves"]

    res = db.apply_building_upkeep(cid)
    assert res["consumed"].get("oil", 0) == 200_000

    ledger = db.get_oil_ledger(cid)
    assert any("سازه" in e["reason"] and e["delta"] == -200_000 for e in ledger)


def test_military_fuel_logs_itself(monkeypatch, tmp_path):
    """مسیر سوخت نظامی در main باید ثبت کند — تابع کمکی مستقیم آزموده می‌شود."""
    from main import military_fuel_step
    cid = _fresh(monkeypatch, tmp_path, "oilledger6.db")
    for it in config.COUNTRY_EQUIPMENT_CATALOG["germany"]:
        conn = db.get_connection()
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO country_assets (country_id, country_key, category,"
                " equipment_name, equipment_key, amount, buy_price, maintenance_cost, producible)"
                " VALUES (?,?,?,?,?,?,?,?,1)",
                (cid, "germany", it["category"], it["name"], it["key"],
                 it.get("initial", 0), it["price"], it.get("maint", 0)))
        conn.close()
    need = db.calculate_military_fuel_consumption(cid)
    assert need > 0

    c = db.get_country_by_id(cid)
    military_fuel_step(c)   # با نفتِ کافی: فقط کسر + ثبت

    ledger = db.get_oil_ledger(cid)
    assert any("نیروهای مسلح" in e["reason"] and e["delta"] == -need for e in ledger)

    # حالا کشوری با نفت صفر: موجودی که نیست کسر نمی‌شود ولی دلیلش ثبت می‌شود
    db.update_country_field(cid, "oil_reserves", 0)
    c2 = db.get_country_by_id(cid)
    military_fuel_step(c2)
    ledger2 = db.get_oil_ledger(cid)
    assert any("کسر نشد" in e["reason"] for e in ledger2), \
        "وقتی سوخت نیست، باید در دفتر نوشته شود که کسر نشد"


# ───────────── ۳) صفرشدن ناگهانی باید توضیح داشته باشد ─────────────

def test_zeroing_shortage_is_explained_in_ledger(monkeypatch, tmp_path):
    cid = _fresh(monkeypatch, tmp_path, "oilledger7.db")
    db.update_country_field(cid, "oil_reserves", 500_000)   # ذخیره‌ی ناچیز
    _add_building(cid, "fossil_plant", 10)
    ia.process_daily_resource_consumption(db.get_country_by_id(cid))

    assert db.get_country_by_id(cid)["oil_reserves"] >= 0
    ledger = db.get_oil_ledger(cid)
    oil_events = [e for e in ledger if "جمعیت" in e["reason"]]
    assert oil_events and oil_events[0].get("note"), \
        "در کسری باید توضیح «نیاز بیشتر از موجودی بود؛ ذخیره صفر شد» ثبت شود"

    line = db.format_oil_ledger(ledger)
    assert "صفر" in line or "کسری" in line, "گزارش دفتر باید صفرشدن را توضیح دهد"


# ───────────── ۴) نمای پلیر: پنل باید کل بودجه‌ی شب را بگوید ─────────────

def test_approval_panel_oil_line_includes_building_and_military_burn(monkeypatch, tmp_path):
    """پنل فقط «جمعیت+صنعت» را نشان می‌داد در حالی که سازه‌ها و ارتش هم جدا
    می‌سوزند — پلیر مصرف کل را نمی‌دید (همان «یهو صفر شد»)."""
    from handlers import internal_affairs as hia
    cid = _fresh(monkeypatch, tmp_path, "oilledger8.db")
    _add_building(cid, "fossil_plant", 10)
    for it in config.COUNTRY_EQUIPMENT_CATALOG["germany"]:
        conn = db.get_connection()
        with conn:
            conn.execute(
                "INSERT OR REPLACE INTO country_assets (country_id, country_key, category,"
                " equipment_name, equipment_key, amount, buy_price, maintenance_cost, producible)"
                " VALUES (?,?,?,?,?,?,?,?,1)",
                (cid, "germany", it["category"], it["name"], it["key"],
                 it.get("initial", 0), it["price"], it.get("maint", 0)))
        conn.close()

    ia.process_daily_resource_consumption(db.get_country_by_id(cid))
    db.apply_building_upkeep(cid)
    from main import military_fuel_step
    military_fuel_step(db.get_country_by_id(cid))

    country = db.get_country_by_id(cid)
    lines = hia._approval_causes(country)
    oil_block = "\n".join(lines)
    assert "دفتر نفت" in oil_block or "مصرف کل دیشب" in oil_block, \
        "پنل باید مصرف کل شب (همه‌ی مسیرها) را از دفتر نشان دهد"
