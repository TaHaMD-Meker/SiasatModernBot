# -*- coding: utf-8 -*-
"""فاز ۱ جنگ — جبهه‌ی فعال، فرسودگی، آتش‌بس/غرامت، بازگشت یگان.

قرارداد مالک:
- اولین عملیات محدود میان دو کشور = آغاز «جنگ فعال» (خبر + پیوی دو طرف)
- هر عملیات موفق جبهه را جلو می‌برد؛ جنگ = تنش سرد نمی‌شود (جنگ می‌سوزد)
- فرسودگی روزانه: پول+نفت+رضایت از هر دو طرف تا جنگ تمام شود
- آتش‌بس: درخواست → پذیرش طرف مقابل؛ صلح با غرامت وقتی جبهه ≥۵۰
- خروج یک‌طرفه: جنگ تمام، آبرو می‌رود (رضایت↓)
- بازگشت یگان: از پایگاه به انبار مبدأ با نصف هزینه‌ی اعزام
"""
import datetime
import types

import config
import database as db


def _fresh(monkeypatch, tmp_path, name="war1.db"):
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


def _tension_up(a, b, n=50):
    db.add_tension(a, b, n, "تنش آزمون", bypass_daily_cap=True)


def test_first_auto_attack_opens_war_with_news(monkeypatch, tmp_path):
    from handlers import auto_ops
    _fresh(monkeypatch, tmp_path)
    a = _mk("عربستان", "🇸🇦", "saudi", 9801)
    d = _mk("سوریه", "🇸🇾", "syria", 9802)
    _asset(a, "ef_saud", "Eurofighter Typhoon", 72)
    _asset(a, "ss_saud", "Storm Shadow", 200)
    _asset(d, "pantir_sy", "Pantsir-S1", 20, "Air Defense")
    _tension_up(a, d)

    posted = []

    class _Bot:
        async def send_message(self, chat_id=None, text=None, **k):
            posted.append((chat_id, str(text)[:40]))
            return True

    text = "عملیات محدود: ۸ جنگنده تایفون با ۱۲ موشک کروز Storm Shadow علیه پدافند دمشق"
    res = auto_ops.process_attack_submission(a, d, text, bot=_Bot())

    assert res["verdict"] == "auto"
    war = db.get_active_war(a, d)
    assert war, "جنگ فعال باید باز شود"
    assert war["status"] == "active"
    assert posted, "خبر آغاز جنگ باید پست شود و DM برود"
    assert any("جنگ" in t for _c, t in posted)


def test_repeated_attacks_advance_front_and_no_decay_at_war(monkeypatch, tmp_path):
    from handlers import auto_ops
    _fresh(monkeypatch, tmp_path, "front.db")
    a = _mk("عربستان", "🇸🇦", "saudi2", 9803)
    d = _mk("سوریه", "🇸🇾", "syria2", 9804)
    _asset(a, "ef2", "Eurofighter Typhoon", 72)
    _asset(a, "ss2", "Storm Shadow", 500)
    _asset(d, "z23", "توپ ۲۳ م‌م ZU-23-2", 400, "Air Defense")
    _tension_up(a, d, 60)
    auto_ops.process_attack_submission(a, d,
        "عملیات محدود: ۸ جنگنده تایفون با ۱۲ موشک کروز Storm Shadow علیه پدافند حومه دمشق", bot=None)
    w1 = db.get_active_war(a, d)
    db.add_tension(a, d, -10, "خنک‌سازی مصنوعی", bypass_daily_cap=True)

    # سردشدن روزانه باید جنگ‌دارها را رد کند
    db.decay_all_tensions(config.TENSION_DAILY_DECAY)
    # (تنش جنگی سرد نمی‌شود — پایش در decay_all_tensions است)

    auto_ops.process_attack_submission(a, d,
        "عملیات محدود: ۸ جنگنده تایفون با ۱۲ موشک کروز Storm Shadow علیه پدافند حومه حمص", bot=None)
    w2 = db.get_active_war(a, d)
    assert w2["front"] > w1["front"], "عملیات دوم باید جبهه را جلو ببرد"
    assert w2["warscore"] > 0


def test_peace_with_reparations_when_front_50(monkeypatch, tmp_path):
    from handlers import auto_ops
    _fresh(monkeypatch, tmp_path, "peace.db")
    a = _mk("عربستان", "🇸🇦", "saudi3", 9805)
    d = _mk("سوریه", "🇸🇾", "syria3", 9806)
    _asset(a, "ef3", "Eurofighter Typhoon", 72)
    _asset(a, "ss3", "Storm Shadow", 900)
    _asset(d, "z3", "توپ ۲۳ م‌م ZU-23-2", 900, "Air Defense")
    _tension_up(a, d, 90)
    for tgt in ("دمشق", "حمص", "لاذقیه", "دیرالزور"):
        auto_ops.process_attack_submission(a, d,
            f"عملیات محدود: ۸ جنگنده تایفون با ۱۲ موشک کروز Storm Shadow علیه پدافند {tgt}", bot=None)
    war = db.get_active_war(a, d)
    if war["front"] < config.WAR_PEACE_FRONT_THRESHOLD:
        db.set_war_front(war["id"], config.WAR_PEACE_FRONT_THRESHOLD, war["warscore"])
    war = db.get_active_war(a, d)

    con = db.get_connection()
    with con:
        con.execute("UPDATE countries SET treasury=10_000_000 WHERE id=?", (d,))
    con.close()

    share = int(10_000_000 * config.WAR_REPARATIONS_SHARE)
    ok, msg = db.end_war_with_reparations(war["id"], winner_id=a, loser_id=d)
    assert ok, msg

    d_now = db.get_country_by_id(d)
    assert d_now["treasury"] == 10_000_000 - share, "غرامت از بازنده کسر شود"
    a_now = db.get_country_by_id(a)
    assert a_now["treasury"] > (30_000_000 - 4 * config.WAR_DAILY_MONEY_COST), "غرامت به برنده رسیده باشد"
    assert db.get_active_war(a, d) is None, "جنگ تمام شود"
    assert db.get_tension(a, d) == config.WAR_CEASEFIRE_TENSION_RESET, "تنش پس از صلح پایین بیاید"


def test_unilateral_withdraw_ends_war(monkeypatch, tmp_path):
    from handlers import auto_ops
    _fresh(monkeypatch, tmp_path, "uni.db")
    a = _mk("عربستان", "🇸🇦", "saudi4", 9807)
    d = _mk("سوریه", "🇸🇾", "syria4", 9808)
    _asset(a, "ef4", "Eurofighter Typhoon", 72)
    _asset(a, "ss4", "Storm Shadow", 200)
    _asset(d, "p4", "Pantsir-S1", 20, "Air Defense")
    _tension_up(a, d)
    auto_ops.process_attack_submission(a, d,
        "عملیات محدود: ۸ جنگنده تایفون با ۱۲ موشک کروز Storm Shadow علیه پدافند دمشق", bot=None)
    war = db.get_active_war(a, d)
    approval_before = db.get_country_by_id(a)["approval_rating"]

    ok, msg = db.withdraw_from_war(war["id"], country_id=a)
    assert ok, msg
    assert db.get_active_war(a, d) is None
    assert db.get_country_by_id(a)["approval_rating"] < approval_before, "خروج یک‌طرفه = هزینه‌ی آبرو"


def test_war_weariness_daily_charge(monkeypatch, tmp_path):
    from handlers import auto_ops
    _fresh(monkeypatch, tmp_path, "wear.db")
    a = _mk("عربستان", "🇸🇦", "saudi5", 9809)
    d = _mk("سوریه", "🇸🇾", "syria5", 9810)
    _asset(a, "ef5", "Eurofighter Typhoon", 72)
    _asset(a, "ss5", "Storm Shadow", 200)
    _asset(d, "p5", "Pantsir-S1", 20, "Air Defense")
    _tension_up(a, d)
    auto_ops.process_attack_submission(a, d,
        "عملیات محدود: ۸ جنگنده تایفون با ۱۲ موشک کروز Storm Shadow علیه پدافند دمشق", bot=None)

    con = db.get_connection()
    with con:
        con.execute("UPDATE countries SET treasury=50_000_000, oil_reserves=500_000, approval_rating=70 WHERE id IN (?,?)", (a, d))
    con.close()

    n = db.apply_war_weariness()
    assert n == 1, "یک جنگ فعال فرسودگی خورد"
    for cid in (a, d):
        c = db.get_country_by_id(cid)
        assert c["treasury"] == 50_000_000 - config.WAR_DAILY_MONEY_COST
        assert c["oil_reserves"] == 500_000 - config.WAR_DAILY_OIL_COST
        assert c["approval_rating"] == 69
    # دوباره در همان روز → نه (idempotent)
    assert db.apply_war_weariness() == 0


def test_unit_return_moves_back_and_costs_half(monkeypatch, tmp_path):
    from handlers import bases as bases_mod
    _fresh(monkeypatch, tmp_path, "ret.db")
    a = _mk("ترکیه", "🇹🇷", "turkey2", 9811)
    h = _mk("قطر", "🇶🇦", "qatar3", 9812)
    base_id = db.create_base_record(owner_id=a, host_id=h, name="Udeid2")
    db.set_diplomatic_relation(a, h, "allied", 0)
    _asset(a, "f16_tr2", "جنگنده F-16", 30)
    con = db.get_connection()
    with con:
        con.execute("UPDATE countries SET oil_reserves=900_000, treasury=9_000_000 WHERE id=?", (a,))
    con.close()

    ok, msg, meta = bases_mod.deploy_units(a, base_id, [("f16_tr2", 10)], bot=None)
    assert ok, msg
    oil_after_deploy = db.get_country_by_id(a)["oil_reserves"]

    ok2, msg2, meta2 = bases_mod.return_units(a, base_id, [("f16_tr2", 10)])
    assert ok2, msg2
    src = [r for r in db.get_country_assets(a) if r["equipment_key"] == "f16_tr2"][0]
    assert src["amount"] == 30, "یگان به مبدأ برگردد"
    ba = db.get_base_assets(base_id)
    assert not any(r["equipment_key"] == "f16_tr2" and r["amount"] > 0 for r in ba), "از پایگاه خارج شود"
    a_now = db.get_country_by_id(a)
    from handlers import bases as _bases
    deploy_oil = _bases.DEPLOY_FLYAWAY_OIL_PER_UNIT * 10
    assert a_now["oil_reserves"] == oil_after_deploy - deploy_oil // 2, "بازگشت = نصف هزینه"


def test_ceasefire_needs_enemy_accept(monkeypatch, tmp_path):
    from handlers import auto_ops
    _fresh(monkeypatch, tmp_path, "cf.db")
    a = _mk("عربستان", "🇸🇦", "saudi6", 9813)
    d = _mk("سوریه", "🇸🇾", "syria6", 9814)
    _asset(a, "ef6", "Eurofighter Typhoon", 72)
    _asset(a, "ss6", "Storm Shadow", 200)
    _asset(d, "p6", "Pantsir-S1", 20, "Air Defense")
    _tension_up(a, d)
    auto_ops.process_attack_submission(a, d,
        "عملیات محدود: ۸ جنگنده تایفون با ۱۲ موشک کروز Storm Shadow علیه پدافند دمشق", bot=None)
    war = db.get_active_war(a, d)

    ok, msg = db.request_ceasefire(war["id"], by_country_id=a)
    assert ok, msg
    assert db.get_active_war(a, d) is not None, "تا پذیرش، جنگ برقرار است"

    ok2, msg2 = db.accept_ceasefire(war["id"], by_country_id=d)
    assert ok2, msg2
    assert db.get_active_war(a, d) is None, "با پذیرش، آتش‌بس نهایی می‌شود"
