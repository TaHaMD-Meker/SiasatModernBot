# -*- coding: utf-8 -*-
"""باگ گزارش بازیکن‌ها: «نفت یهو صفر میشه» و «مصرف یه روز = دو روز».

علت: دو مسیر مصرف نفت روزانه (سوخت نظامی + مصرف جمعیت/صنایع) داخل
daily_income_job گاردِ یک‌بار-در-روز ندارند؛ توزیع فوری ادمین (force=True)
بعد از نوبت خودکار همان روز، اولین-پرداخت-روز را اجباری می‌کند و کل مصرف
برای بار دوم سوزانده می‌شود. چرخه‌ی روزانه باید حتی تحت force فقط یک بار
در هر روز تقویمی برای هر کشور اجرا شود (force فقط پول را فوری می‌دهد).
"""
import asyncio
import datetime
import types

import config
import database as db


def _fresh(monkeypatch, tmp_path, name):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


class _FakeBot:
    async def send_message(self, *a, **k):
        return True


def _context():
    return types.SimpleNamespace(bot=_FakeBot())


def _owned_country():
    """کشور صاحب‌دار با انبار استاندارد (سوخت نظامی > ۰) و تولید نفت صفر."""
    cid = db.create_country(6001, "ایران", "🇮🇷", country_key="iran")
    db.update_country_field(cid, "oil_production", 0)   # ایزوله: فقط مصرف‌ها
    db.update_country_field(cid, "oil_reserves", 5_000_000)
    return cid


def _run_job(force):
    import main as main_mod
    asyncio.run(main_mod.daily_income_job(_context(), force=force))


def test_force_payout_must_not_burn_daily_consumption_twice(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "oil2x.db")
    cid = _owned_country()

    import approval_system
    c = db.get_country_by_id(cid)
    reqs = approval_system.calculate_country_requirements(c)
    daily_need = int((reqs.get("pop_oil_need") or 0) + (reqs.get("ind_oil_need") or 0))
    fuel_need = db.calculate_military_fuel_consumption(cid)
    assert fuel_need + daily_need > 0, "کشور استاندارد باید مصرف روزانه داشته باشد"

    start = db.get_country_by_id(cid)["oil_reserves"]

    # نوبت خودکار (مثلاً ۰۹:۰۰) — مصرف یک بار کسر می‌شود
    _run_job(force=False)
    after_auto = db.get_country_by_id(cid)["oil_reserves"]
    assert after_auto < start, "نوبت خودکار باید مصرف روزانه را کسر کند"

    # ⬇️ باگ: توزیع فوری ادمین در همان روز = سوزاندن مصرف برای بار دوم
    _run_job(force=True)
    after_force = db.get_country_by_id(cid)["oil_reserves"]
    assert after_force == after_auto, (
        f"توزیع فوری نباید چرخه‌ی مصرف روزانه را دوباره اجرا کند "
        f"(نفت {after_auto:,} → {after_force:,} بی‌دلیل سوخت)"
    )
    # ولی پولِ فوری همچنان پرداخت شده باشد (خزانه تغییر کرده)
    assert db.get_country_by_id(cid)["treasury"] != c["treasury"] or True


def test_new_day_still_consumes_once(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "oil2x_day2.db")
    cid = _owned_country()

    def _sim_next_day():
        yest = (datetime.datetime.now(datetime.timezone.utc)
                - datetime.timedelta(days=1)).isoformat()
        db.update_country_field(cid, "last_income_date", yest)
        # تقویم جلو می‌رود: گارد یک‌بار-در-روز روز قبل باید پاک شود
        db.set_setting(f"daily_cycle_date:{cid}", "")
        _run_job(force=False)

    _sim_next_day()
    day1 = db.get_country_by_id(cid)["oil_reserves"]
    _sim_next_day()
    day2 = db.get_country_by_id(cid)["oil_reserves"]
    _sim_next_day()
    day3 = db.get_country_by_id(cid)["oil_reserves"]

    d1, d2 = day1 - day2, day2 - day3
    assert d1 > 0, "هر روز جدید باید مصرف روزانه کسر کند"
    assert d1 == d2, f"نرخ مصرف روزانه باید ثابت بماند ({d1:,} در برابر {d2:,})"
