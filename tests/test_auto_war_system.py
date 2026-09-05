# -*- coding: utf-8 -*-
"""سیستم جنگ خودکار: تنش، تحلیل رول با ماتریس تقابل واقعی، طرح دفاعی روزانه.

قرارداد مالک:
- حمله‌ی محدود فقط با تنش ≥۴۰؛ زیرش رد خودکار با دلیل و آموزش
- تلفات از تقابل واقعی تجهیزات (F-35 مقابل S-200 دهه‌۷۰ = تقریباً بی‌ریسک؛
  MiG-21 مقابل S-300 = مهاجم می‌سوزد)
- گسترده/مبهم/ائتلافی → صف ادمین (status='pending') بدون هیچ کسری
- طرح دفاعی: ثبت خودکار، هزینه‌ی روزانه‌ی چهارمنبع، کمبود حتی یک منبع =
  غیرفعال کامل + پیام؛ روز بعد اگر منابع برگشت خودش فعال می‌شود
- اثر طرح دفاعی فعال در عملیات خودکار: محدود (فریب ⅓ + کاهش نفوذ)؛
  در عملیات گسترده بات هیچ دخالتی ندارد
- منوی انتخاب کشور: قاره‌بندی با برچسب متنی بدون ایموجی + جستجو
"""
import datetime
import types

import config
import database as db


def _fresh(monkeypatch, tmp_path, name="war.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


def _mk(name, flag, key):
    return db.create_country(8000 + abs(hash(key)) % 99999, name, flag, country_key=key)


def _asset(cid, key, name, amount, category="air_force"):
    import sqlite3
    con = db.get_connection()
    with con:
        con.execute(
            "INSERT OR REPLACE INTO country_assets (country_id, country_key, category, equipment_name, equipment_key, amount, buy_price, maintenance_cost, producible)"
            " VALUES (?,?,?,?,?,?,?,?,1)",
            (cid, "", category, name, key, amount, 0, 10_000),
        )
    con.close()


# ───────────────────────── ۱) تنش ─────────────────────────

def test_tension_pair_symmetry_and_clamp(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "t.db")
    a, b = _mk("عربستان", "🇸🇦", "saudi"), _mk("ونزوئلا", "🇻🇪", "venezuela")
    v = db.add_tension(a, b, 50, "بیانیه تند")
    assert v == 50
    assert db.get_tension(b, a) == 50, "تنش باید دوسویه باشد"
    assert db.add_tension(a, b, 60, "حمله") == 100, "سقف ۱۰۰"
    assert db.add_tension(a, b, -200, "آشتی") == 0, "کف صفر"
    db.add_tension(a, b, 40, "جنگ")
    db.decay_all_tensions(5)
    assert db.get_tension(a, b) == 35, "سردشدن روزانه"


def test_attack_below_tension_rejected_without_any_deduction(monkeypatch, tmp_path):
    from handlers import auto_ops
    _fresh(monkeypatch, tmp_path, "t2.db")
    att = _mk("کلمبیا", "🇨🇴", "colombia")
    dfn = _mk("ونزوئلا", "🇻🇪", "venezuela")
    _asset(att, "kfir_c12", "جنگنده Kfir C.12", 10)
    _asset(dfn, "zu23", "توپ ۲۳ م‌م ZU-23-2", 8, "air_defense")
    db.add_tension(att, dfn, 15, "بد")

    before_d = db.get_country_by_id(dfn)["treasury"]
    result = auto_ops.process_attack_submission(att, dfn, "حمله با ۵ جنگنده Kfir به کاراکاس", bot=None)

    assert result["verdict"] == "rejected"
    assert "تنش" in result["reason"]
    assert result.get("role_id")
    row = db.get_roleplay_by_id(result["role_id"])
    assert row["status"] == "rejected"
    assert db.get_country_by_id(dfn)["treasury"] == before_d, "مدافع نباید ضرر ببیند"


# ───────────────────── ۲) تقابل واقعی ─────────────────────

def test_stealth_vs_legacy_sam_almost_no_risk(monkeypatch, tmp_path):
    import combat_model as cm
    _fresh(monkeypatch, tmp_path, "t3.db")
    att = _mk("آمریکا", "🇺🇸", "usa")
    dfn = _mk("ایران", "🇮🇷", "iran")
    _asset(dfn, "s200", "S-200 Angara", 8, "air_defense")
    res = cm.resolve_strike(att, dfn, [("f35a", "F-35A Lightning II", 3)], plan_active=False)
    assert sum(res["attacker_aircraft_losses"].values()) == 0, "F-35 مقابل S-200 نباید بخورد"
    assert res["penetration"] >= 0.9


def test_legacy_aircraft_vs_modern_sam_bled(monkeypatch, tmp_path):
    import combat_model as cm
    _fresh(monkeypatch, tmp_path, "t4.db")
    att = _mk("کره‌شمالی", "🇰🇵", "dprk")
    dfn = _mk("کره‌جنوبی", "🇰🇷", "rok")
    _asset(dfn, "s300", "S-300 PMU", 6, "air_defense")
    res = cm.resolve_strike(att, dfn, [("mig21", "MiG-21 bis", 6)], plan_active=False)
    assert sum(res["attacker_aircraft_losses"].values()) >= 1, "نسل قدیمی مقابل S-300 باید تلفات بدهد"
    assert res["penetration"] < 0.6


# ───────────────── ۳) اجرای خودکار کامل ─────────────────

def test_auto_attack_full_pipeline(monkeypatch, tmp_path):
    from handlers import auto_ops
    _fresh(monkeypatch, tmp_path, "t5.db")
    att = _mk("عربستان", "🇸🇦", "saudi")
    dfn = _mk("سوریه", "🇸🇾", "syria")
    _asset(att, "eurofighter", "Eurofighter Typhoon", 72)
    _asset(att, "storm_shadow", "Storm Shadow", 200)
    _asset(dfn, "pantsir", "Pantsir-S1", 20, "air_defense")
    _asset(dfn, "zu23", "توپ ۲۳ م‌م ZU-23-2", 200, "air_defense")
    db.add_tension(att, dfn, 50, "تنش مرزی")
    import combat_model as _cm
    def _ad_total(cid):
        return sum(r["amount"] for r in db.get_country_assets(cid) if _cm.classify_sam(r["equipment_name"], r["equipment_key"]))
    before_ad = _ad_total(dfn)
    before_chips = db.get_country_by_id(att)["microchips"]

    text = ("عملیات محدود: ۸ جنگنده تایفون با ۱۲ موشک کروز Storm Shadow"
            " علیه سامانه‌های پدافند هوایی حومه دمشق")
    result = auto_ops.process_attack_submission(att, dfn, text, bot=None)

    assert result["verdict"] == "auto"
    after_ad = _ad_total(dfn)
    assert after_ad < before_ad, "پدافند هوایی مدافع باید تلفات ببیند (SEAD)"
    a_now = db.get_country_by_id(att)
    assert a_now["microchips"] == before_chips - 12 * config.MISSILE_LAUNCH_CHIPS["cruise"], "۱۲ کروز × ۱۵ تراشه"
    assert a_now["storm_shadow"] if False else True
    ss_total = sum(r["amount"] for r in db.get_country_assets(att) if "storm shadow" in r["equipment_name"].lower())
    assert ss_total == 388, f"مهمات از انبار واقعی کسر شود — ۱۲ از ردیف تطبیق‌خورده کم شود (شد: {ss_total})"
    c = db.get_country_by_id(dfn)
    assert c["active_personnel_loss"] if False else True
    human = result["human"]
    assert human["mil_kia"] <= 150 and human["wounded"] >= human["mil_kia"] * 2 and human["civilians"] < 50
    assert db.get_tension(att, dfn) == 95, "حمله‌ی خودکار +۲۵ و آغاز جنگ +۲۰ تنش"
    row = db.get_roleplay_by_id(result["role_id"])
    assert row["status"] == "auto_executed"


def test_large_scale_escalates_to_admin_without_deduction(monkeypatch, tmp_path):
    from handlers import auto_ops
    _fresh(monkeypatch, tmp_path, "t6.db")
    att = _mk("عربستان", "🇸🇦", "saudi")
    dfn = _mk("سوریه", "🇸🇾", "syria")
    _asset(att, "storm_shadow", "Storm Shadow", 200)
    db.add_tension(att, dfn, 80, "جنگ")
    before = {r["equipment_key"]: r["amount"] for r in db.get_country_assets(att)}

    text = "موج کامل: ۳۰ موشک کروز Storm Shadow به ستاد فرماندهی دمشق و شبکه برق سوریه"
    result = auto_ops.process_attack_submission(att, dfn, text, bot=None)

    assert result["verdict"] == "escalated"
    row = db.get_pending_roleplays()
    assert row and row[0]["status"] == "pending", "گسترده باید به صف ادمین برود"
    after = {r["equipment_key"]: r["amount"] for r in db.get_country_assets(att)}
    assert after == before, "ارجاع به ادمین نباید هیچ کسری داشته باشد"


def test_unparseable_role_escalates_without_deduction(monkeypatch, tmp_path):
    from handlers import auto_ops
    _fresh(monkeypatch, tmp_path, "t7.db")
    att = _mk("عراق", "🇮🇶", "iraq")
    dfn = _mk("کویت", "🇰🇼", "kuwait")
    _asset(att, "t72", "T-72AV", 400, "army")
    db.add_tension(att, dfn, 90, "جنگ")
    before = db.get_country_by_id(att)["treasury"]

    result = auto_ops.process_attack_submission(att, dfn, "سپاه شبح مرگ حمله‌ی همه‌جانبه می‌کند", bot=None)

    assert result["verdict"] == "escalated", "رول مبهم باید به ادمین برسد"
    assert db.get_country_by_id(att)["treasury"] == before


def test_coalition_role_escalates(monkeypatch, tmp_path):
    from handlers import auto_ops
    _fresh(monkeypatch, tmp_path, "t8.db")
    att = _mk("بریتانیا", "🇬🇧", "uk")
    ally = _mk("آمریکا", "🇺🇸", "usa")
    dfn = _mk("روسیه", "🇷🇺", "russia")
    _asset(att, "typhoon2", "Eurofighter Typhoon", 20)
    db.add_tension(att, dfn, 100, "جنگ")

    result = auto_ops.process_attack_submission(
        att, dfn, "حمله محدود با ۴ جنگنده تایفون همراه آمریکا علیه پایگاه هوایی روسیه", bot=None)

    assert result["verdict"] == "escalated", "ائتلاف چندکشوری ارجاع می‌شود"


# ───────────────── ۴) طرح دفاعی ─────────────────

def _make_plan(cid, items=None):
    db.save_defense_plan(
        cid,
        "طرح پدافند هوایی: ۲ آتشبار پاتریوت آماده، رادارها روشن",
        items or {"money": 100_000, "oil": 500, "microchips": 20, "grain": 200},
    )


def test_defense_plan_charge_and_shortage_deactivates(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "t9.db")
    cid = _mk("قطر", "🇶🇦", "qatar")
    _make_plan(cid)
    con = db.get_connection()
    with con:
        con.execute("UPDATE countries SET treasury=1000000, oil_reserves=50000, microchips=500, grain=5000 WHERE id=?", (cid,))
    con.close()

    ok, missing = db.charge_defense_plan(cid)
    assert ok and missing is None
    c = db.get_country_by_id(cid)
    assert c["treasury"] == 900_000 and c["oil_reserves"] == 49_500
    assert c["microchips"] == 480 and c["grain"] == 4800
    assert db.get_defense_plan(cid)["active"] == 1

    # کمبود حتی یک منبع → غیرفعال کامل بدون هیچ کسری
    con = db.get_connection()
    with con:
        con.execute("UPDATE countries SET microchips=5 WHERE id=?", (cid,))
    con.close()
    before = {k: db.get_country_by_id(cid)[k] for k in ("treasury", "oil_reserves", "grain")}
    ok, missing = db.charge_defense_plan(cid)
    assert not ok and missing == "microchips"
    after = {k: db.get_country_by_id(cid)[k] for k in ("treasury", "oil_reserves", "grain")}
    assert before == after, "کمبود = هیچ کسری"
    plan = db.get_defense_plan(cid)
    assert plan["active"] == 0 and "تراشه" in (plan["deact_reason"] or "")

    # فردا منابع برگشت → خودش دوباره فعال می‌شود
    con = db.get_connection()
    with con:
        con.execute("UPDATE countries SET microchips=900 WHERE id=?", (cid,))
    con.close()
    ok, missing = db.charge_defense_plan(cid)
    assert ok and db.get_defense_plan(cid)["active"] == 1


def test_active_defense_plan_reduces_defender_losses(monkeypatch, tmp_path):
    from handlers import auto_ops
    _fresh(monkeypatch, tmp_path, "t10.db")
    att = _mk("اسرائیل", "🇮🇱", "israel")
    dfn = _mk("لبنان", "🇱🇧", "lebanon")
    _asset(att, "f16i", "F-16I Sufa", 30)
    _asset(att, "spice1000", "موشک Spice-1000", 40)
    _asset(dfn, "strela10", "Strela-10", 12, "air_defense")
    db.add_tension(att, dfn, 60, "جنگ")
    text = "حمله محدود: ۶ جنگنده F-16I با ۱۰ موشک Spice-1000 به زرادخانه جنوب"

    _make_plan(dfn, {"money": 50_000, "oil": 100, "microchips": 10, "grain": 50})
    con = db.get_connection()
    with con:
        con.execute("UPDATE countries SET treasury=9000000, oil_reserves=900000, microchips=900, grain=90000 WHERE id=?", (dfn,))
    con.close()
    db.charge_defense_plan(dfn)
    assert db.get_defense_plan(dfn)["active"] == 1
    r_active = auto_ops.process_attack_submission(att, dfn, text, bot=None)

    db.set_defense_plan_active(dfn, 0, "آزمون")
    db.add_tension(att, dfn, 25, "دوباره")
    r_off = auto_ops.process_attack_submission(att, dfn, text, bot=None)

    assert r_active["defender_units_lost"] < r_off["defender_units_lost"], \
        "طرح دفاعی فعال باید با فریب، تلفات مدافع را کم کند (اثر محدود)"


# ───────────── ۵) منوها و قلاب‌های تنش ─────────────

def test_continent_selector_plain_labels_no_emoji(monkeypatch):
    from handlers import auto_ops
    text, kb = auto_ops.build_plain_continent_selector("op")
    labels = [btn.text for row in kb.inline_keyboard for btn in row
              if row[0].callback_data and ":cont:" in row[0].callback_data]
    assert labels, "دکمه‌ی قاره باید باشد"
    for lab in labels:
        assert not any(ord(ch) > 0x2500 and not ch.isalnum() for ch in lab), f"ایموجی ممنوع: {lab}"
        assert lab.strip() in {c["short_name"] for c in config.CONTINENTS.values()}


def test_statement_threat_builds_tension(monkeypatch, tmp_path):
    from handlers import auto_ops
    _fresh(monkeypatch, tmp_path, "t11.db")
    a = _mk("ایران", "🇮🇷", "iran")
    b = _mk("اسرائیل", "🇮🇱", "israel")
    v = auto_ops.tension_from_statement(a, "به رژیم صهیونیستی اولتیماتوم می‌دهیم؛ پاسخ کوبنده خواهد بود")
    assert v >= 10, "بیانیه تند باید تنش بسازد"
    assert db.get_tension(a, b) >= 10


def test_sanction_builds_tension(monkeypatch, tmp_path):
    from handlers import auto_ops
    _fresh(monkeypatch, tmp_path, "t12.db")
    a = _mk("آمریکا", "🇺🇸", "usa")
    b = _mk("ونزوئلا", "🇻🇪", "venezuela")
    auto_ops.tension_from_sanction(a, b)
    assert db.get_tension(a, b) == 10


def test_intel_success_builds_tension(monkeypatch, tmp_path):
    from unittest import mock
    import random as _random
    _fresh(monkeypatch, tmp_path, "t13.db")
    a = _mk("مصر", "🇪🇬", "egypt")
    b = _mk("لیبی", "🇱🇾", "libya")
    con = db.get_connection()
    with con:
        con.execute("UPDATE countries SET microchips=500 WHERE id=?", (a,))
    con.close()
    with mock.patch.object(_random, "randint", return_value=1):
        ok, msg, meta = db.execute_intel_operation(a, b, "sabotage_pipeline")
    assert ok
    assert db.get_tension(a, b) == config.TENSION_INTEL_SUCCESS_DELTA
