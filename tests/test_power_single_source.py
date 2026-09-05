# -*- coding: utf-8 -*-
"""باگ گزارش‌شده‌ی مالک: تناقض دو پنل درباره‌ی برق.

پنل رضایت: «✅ برق و انرژی: تأمین کامل (165٪ از 132٪ موردنیاز)»
همان لحظه پنل سازه‌ها: «🔴 ۲ واحد ساختمان اداری خاموش — انبار ⚡ برق کفاف
مصرف نمی‌داد؛ کسری ۷.۶ واحد.»

ریشه: دو موتور برقِ موازی با دو مدل مصرف متفاوت —
• موتور واقعی (database.apply_building_upkeep): مصرف برق هر سازه را از
  config.BUILDING_UPKEEP["elec"] می‌گیرد (خانه ۰.۷ … مجتمع صنعتی ۲۰.۲) و
  واقعاً واحدها را خاموش می‌کند.
• پنل رضایت و power_status: دیکشنری دستی POWER_CONSUMERS با اعداد کلفتی
  ۱ تا ۵ و کلیدهای کمتر — دو عدد متفاوت به بازیکن نمایش داده می‌شد.

قرارداد (تک‌منبع حقیقت): اعداد برق همه‌ی پنل‌ها باید از BUILDING_UPKEEP
بیاید؛ power_status دیگر موتور موازی نیست و خاموشی/درآمد ازدست‌رفته را از
گزارش واقعی چرخه‌ی نگهداری می‌خواند؛ نیاز برق = «مصرف سازه‌ها» در برابر
«ظرفیت شبکه» (پایه‌ی ۱۰۰٪ خانگی داخل ظرفیت پایه است، نه یک نیاز جدا).
"""
import json

import config
import database as db
import approval_system
import internal_affairs as ia


def _fresh(monkeypatch, tmp_path, name="power1.db", key="testland"):
    """کشور بی‌اورراید → پایه‌ی شبکه دقیقاً ۱۰۰ (STARTING_VALUES)."""
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()
    cid = db.create_country(8200, "آزمونستان", "🏳️", country_key=key)
    db.update_country_field(cid, "treasury", 900_000_000)
    db.update_country_field(cid, "oil_reserves", 900_000_000)
    db.update_country_field(cid, "iron_ore", 90_000_000)
    db.update_country_field(cid, "microchips", 900_000)
    db.update_country_field(cid, "nuclear_fuel", 90_000)
    db.update_country_field(cid, "grain", 900_000)
    return cid


def _add(cid, key, qty):
    conn = db.get_connection()
    with conn:
        conn.execute("INSERT INTO equipment (country_id, item_key, quantity) VALUES (?,?,?)",
                     (cid, key, qty))
    conn.close()


# ───────────── ۱) تک‌منبع حقیقت ─────────────

def test_power_consumers_is_building_upkeep_elec():
    expected = {k: float(v["elec"]) for k, v in config.BUILDING_UPKEEP.items() if v.get("elec")}
    assert ia.POWER_CONSUMERS == expected, \
        "POWER_CONSUMERS باید همان مصرف واقعی BUILDING_UPKEEP باشد — نه اعداد دستی"


# ───────────── ۲) پنل رضایت = اعداد موتور واقعی ─────────────

def test_approval_need_uses_real_engine_numbers(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "pw_a.db")
    cid = db.get_country_by_player(8200)["id"]
    # ظرفیت 160 (پایه ۱۰۰ + fossil 30 + wind 30)، مصرف سازه‌ها 166.6 → کسری 6.6
    _add(cid, "fossil_plant", 1)
    _add(cid, "wind_plant", 1)
    db.update_country_field(cid, "electricity", 160)

    need = round(20 * config.BUILDING_UPKEEP["small_factory"]["elec"]      # 54
                 + 30 * config.BUILDING_UPKEEP["hotel"]["elec"]            # 93
                 + 5 * config.BUILDING_UPKEEP["office"]["elec"]            # 4.5
                 + 10 * config.BUILDING_UPKEEP["house"]["elec"]            # 7
                 + 1 * config.BUILDING_UPKEEP["iron_mine"]["elec"], 2)     # 8.1
    _add(cid, "small_factory", 20)
    _add(cid, "hotel", 30)
    _add(cid, "office", 5)
    _add(cid, "house", 10)
    _add(cid, "iron_mine", 1)

    reqs = approval_system.calculate_country_requirements(db.get_country_by_id(cid))
    assert reqs["elec_need"] == need, "نیاز برق پنل باید همان مصرف واقعی سازه‌ها باشد"
    assert reqs["elec_need"] > 160, "این کشور باید کسری ببیند — نه «تأمین کامل»"

    # خود موتور واقعی هم همین کسری را می‌بیند (هم‌عدد بودن دو پنل)
    res = db.apply_building_upkeep(cid)
    assert round(res["shortages"].get("elec", 0), 2) == round(need - 160, 2), \
        "کسریِ پنل رضایت و کسریِ موتور خاموشی باید یک عدد باشند"


def test_after_upkeep_panels_agree_on_supplied(monkeypatch, tmp_path):
    """بعد از خاموشی خودکار، پنل رضایت هم باید «تأمین کامل» بگوید — نه کسری قدیمی."""
    _fresh(monkeypatch, tmp_path, "pw_b.db", key="testland2")
    cid = db.get_country_by_player(8200)["id"]
    _add(cid, "fossil_plant", 1)
    db.update_country_field(cid, "electricity", 130)   # 100 + 30
    _add(cid, "small_factory", 50)                      # 50 × 2.7 = 135 > 130
    db.apply_building_upkeep(cid)                       # ۲ کارخانه خاموش می‌شود

    c = db.get_country_by_id(cid)
    reqs = approval_system.calculate_country_requirements(c)
    assert reqs["elec_need"] <= c["electricity"] + 0.01, \
        "بعد از خاموشیِ خودکار، مصرف فعال باید داخل ظرفیت باشد"
    p = ia.power_status(c)
    assert not p["shortage"], "پنل شبکه هم باید تأمین را ببیند"


def test_no_buildings_means_no_building_demand(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "pw_c.db")
    cid = db.get_country_by_player(8200)["id"]
    reqs = approval_system.calculate_country_requirements(db.get_country_by_id(cid))
    assert reqs["elec_need"] == 0, "کشور بی‌سازه مصرف سازه‌ای ندارد"


# ───────────── ۳) صفحه‌ی «چرا خاموشی» — عدد درست به ازای هر واحد ─────────────

def test_why_page_per_unit_consumption_and_full_lost_income():
    entry = {"key": "office", "name": "🏢 ساختمان اداری", "qty": 2, "total_off": 2,
             "income": 130_000, "scarce": ["elec"], "consumption": {"oil": 1_600},
             "least_eff": False}
    text = "\n".join(__import__("handlers.internal_affairs", fromlist=["x"]).building_why_lines(
        entry, "🏢 ساختمان اداری"))
    assert "800 بشکه" in text, "«هر واحد» باید ۸۰۰ بشکه باشد نه مجموع ۲ واحد (۱٬۶۰۰)"
    assert "1,600" not in text
    assert "260,000" in text, "درآمد ازدست‌رفته‌ی ۲ واحد خاموش = ۲×۱۳۰هزار"
    assert "⚡ برق" in text, "دلیل خاموشی باید برق باشد"


# ───────────── ۴) power_status گزارش واقعی می‌دهد، موتور دوم نیست ─────────────

def test_power_status_reads_real_shutdown_report(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "pw_d.db", key="testland3")
    cid = db.get_country_by_player(8200)["id"]
    _add(cid, "fossil_plant", 1)
    db.update_country_field(cid, "electricity", 130)
    _add(cid, "small_factory", 50)                      # 135 > 130 → خاموشی برقی
    report = db.apply_building_upkeep(cid)
    assert report["shut_down"]

    # خاموشی واقعیِ برقی از گزارش می‌آید — بدون شبیه‌سازی دوم
    p = ia.power_status(db.get_country_by_id(cid))
    assert p["offline"].get("small_factory") == sum(
        s["total_off"] for s in report["shut_down"] if s["key"] == "small_factory")
    expected_lost = sum(s["income"] * s["total_off"] for s in report["shut_down"]
                        if "elec" in (s.get("scarce") or []))
    assert p["income_lost"] == expected_lost, \
        "درآمد ازدست‌رفته = مجموع درآمد واحدهای واقعاً خاموش"
    # و بعد از خاموشی خودکار، شبکه متعادل گزارش می‌شود (دیگر «کمبود» نیست)
    assert p["industrial_need"] <= p["available"]
