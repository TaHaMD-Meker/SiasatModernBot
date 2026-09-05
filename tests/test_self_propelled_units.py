# -*- coding: utf-8 -*-
"""واقعیت‌سازی تحرک تجهیزات — قرارداد مالک: «هرکاری که ریلستیک باشه».

- جنگنده/آواکس/پهپاد: پروازی خودگردان (Fly-away) — کراته نمی‌شود؛
  در کمک/تجارت رد می‌شود و به «اعزام یگان» ارجاع داده می‌شود.
- ناو جنگی/زیردریایی/هواپیمابر: دریرو — از تنگه‌ی بسته عبور نمی‌کند.
- بقیه (موشک/تانک/مهمات/...): بار بجا با سیستم فعلی.
- اعزام یگان به پایگاه پیشروی خودت/متحدِ پذیرنده:
  هزینه‌ی نفت+پول، چندساعته (پروازی) یا چندروزه (دریرو)،
  یگان اعزامی از عملیات داخلی مبدأ حذف می‌شود (ضد دوقلو شدن نیرو)،
  ذخیره‌سازی امن ممنوع: میزبان در جنگ باشد یگان در خطر است.
"""
import datetime
import config
import database as db


def _fresh(monkeypatch, tmp_path, name="mob.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


def _mk(name, flag, key, pid):
    return db.create_country(pid, name, flag, country_key=key)


def _asset(cid, key, name, amount, category="Air Force"):
    con = db.get_connection()
    with con:
        con.execute(
            "INSERT OR REPLACE INTO country_assets (country_id,country_key,category,equipment_name,equipment_key,amount,buy_price,maintenance_cost,producible)"
            " VALUES (?,?,?,?,?,?,?,?,1)",
            (cid, "", category, name, key, amount, 0, 10_000),
        )
    con.close()


# ────────── ۱) کلاس‌بندی تحرک ──────────

def test_mobility_classification(monkeypatch):
    from combat_model import classify_mobility
    assert classify_mobility("جنگنده F-16C/D Block 52+", "f16_pakistan") == "flyaway"
    assert classify_mobility("بمب‌افکن استراتژیک", "gen_bomber") == "flyaway"
    assert classify_mobility("پهپاد شناسایی-رزمی", "gen_uav") == "flyaway"
    assert classify_mobility("ناو هواپیمابر", "cvn") == "seagoing"
    assert classify_mobility("زیردریایی کلاس کیلو", "kilo_sub") == "seagoing"
    assert classify_mobility("ناوشکن", "ddg") == "seagoing"
    assert classify_mobility("موشک کروز استراتژیک", "gen_missile") == "cargo"
    assert classify_mobility("تانک اصلی میدان نبرد", "gen_tank") == "cargo"
    assert classify_mobility("توپخانه خودکششی", "gen_artillery") == "cargo"


# ────────── ۲) بند کمک/تجارت ──────────

def test_aid_rejects_self_propelled_equipment(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    a = _mk("آمریکا", "🇺🇸", "usa", 9701)
    b = _mk("عراق", "🇮🇶", "iraq", 9702)
    _asset(a, "f16_usa", "جنگنده F-16", 10)
    _asset(a, "m1a2", "تانک M1A2", 50, "Ground Forces")
    ok, err = db.execute_aid_equipment(a, b, "f16_usa", 2, transport_mode="air")
    assert not ok, "جنگنده با کارگو فرستاده نمی‌شود"
    assert "خودمتحرک" in err or "اعزام یگان" in err
    # تانک بار بجاست — مجاز
    ok2, err2 = db.execute_aid_equipment(a, b, "m1a2", 5, transport_mode="land")
    assert ok2, err2
    row = [r for r in db.get_country_assets(b) if r["equipment_key"] == "m1a2"][0]
    assert row["amount"] == 5


def test_seagoing_rejected_in_aid_even_manually(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    a = _mk("انگلیس", "🇬🇧", "uk", 9703)
    b = _mk("آرژانتین", "🇦🇷", "argentina", 9704)
    _asset(a, "ddg_uk", "ناوشکن Type 45", 4, "Navy")
    ok, err = db.execute_aid_equipment(a, b, "ddg_uk", 1, transport_mode="sea")
    assert not ok and "دریرو" in err, "ناو باید به مسیر اعزام یگان ارجاع شود"


# ────────── ۳) اعزام یگان (Deployment) ──────────

def test_flyaway_deployment_moves_units_to_ally_base(monkeypatch, tmp_path):
    from handlers import bases as bases_mod
    _fresh(monkeypatch, tmp_path)
    a = _mk("عربستان", "🇸🇦", "saudi", 9705)
    b = _mk("امارات", "🇦🇪", "uae", 9706)
    db.set_diplomatic_relation(a, b, "allied", 0)
    # پایگاه پیشروی سعودی در خاک امارات
    base_id = db.create_base_record(owner_id=a, host_id=b, name="Al-Dhafra FOB")
    _asset(a, "typhoon_saud", "Eurofighter Typhoon", 72)
    con = db.get_connection()
    with con:
        con.execute("UPDATE countries SET oil_reserves=900000, treasury=9000000 WHERE id=?", (a,))
    con.close()
    before = 72
    ok, msg, meta = bases_mod.deploy_units(
        a, base_id, [("typhoon_saud", 12)], bot=None)
    assert ok, msg
    now_src = [r for r in db.get_country_assets(a) if r["equipment_key"] == "typhoon_saud"][0]
    assert now_src["amount"] == before - 12, "یگان از مبدأ خارج شود (ضد دوقلویی)"
    base_assets = db.get_base_assets(base_id) if hasattr(db, "get_base_assets") else None
    assert base_assets and any(r["equipment_key"] == "typhoon_saud" and r["amount"] == 12 for r in base_assets), \
        "یگان در پایگاه مقصد ثبت شود"
    c = db.get_country_by_id(a)
    assert c["oil_reserves"] < 900000 and c["treasury"] < 9_000_000, "هزینه‌ی سوخت+لجستیک کسر شود"


def test_deployment_rejects_enemy_destination_and_hostile_transit(monkeypatch, tmp_path):
    from handlers import bases as bases_mod
    _fresh(monkeypatch, tmp_path)
    a = _mk("قطر", "🇶🇦", "qatar", 9707)
    e = _mk("عربستان", "🇸🇦", "saudi2", 9708)
    db.set_diplomatic_relation(a, e, "war", a)
    base_id = db.create_base_record(owner_id=a, host_id=e, name="X")
    _asset(a, "gen_fighter_q", "جنگنده پیشرفته نسل ۴.۵", 20)
    ok, msg, meta = bases_mod.deploy_units(a, base_id, [("gen_fighter_q", 4)], bot=None)
    assert not ok and "جنگ" in msg, "اعزام به خاک دشمن ممنوع"


def test_deployed_units_vulnerable_when_host_at_war(monkeypatch, tmp_path):
    from handlers import bases as bases_mod
    _fresh(monkeypatch, tmp_path)
    a = _mk("ترکیه", "🇹🇷", "turkey", 9709)
    h = _mk("قطر", "🇶🇦", "qatar2", 9710)
    e = _mk("مصر", "🇪🇬", "egypt", 9711)
    base_id = db.create_base_record(owner_id=a, host_id=h, name="Udeid")
    db.set_diplomatic_relation(a, h, "allied", 0)
    _asset(a, "f16_tr", "جنگنده F-16", 30)
    from handlers.auto_ops import process_attack_submission
    ok, msg, meta = bases_mod.deploy_units(a, base_id, [("f16_tr", 10)], bot=None)
    assert ok, msg
    # میزبان (قطر) مورد حمله قرار می‌گیرد → ⅓ یگان اعزامی ترکیه در خطر است
    db.add_tension(e, h, 80, "جنگ")
    res = bases_mod.on_host_under_attack(h, attacker_id=e, bot=None)
    assert res, "هشدار یگان‌های مستقر تولید شود"
    at_risk = [x for x in res if x["owner_id"] == a]
    assert at_risk and at_risk[0]["at_risk_units"] >= 3, "⅓ یگان در معرض خطر + حداقل ۳"
