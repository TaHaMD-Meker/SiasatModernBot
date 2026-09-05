# -*- coding: utf-8 -*-
"""باگ گزارش بازیکن‌ها: «نوبت ۱۵:۰۰ واریز نشده» (بعضی‌ها گرفتند، بعضی‌ها نه).

ریشه: بدنه‌ی حلقه‌ی daily_income_job برای هر کشور حصار try ندارد؛ هر استثنایی
(مثلاً خطای شبکه در send_message یا داده‌ی خراب یک کشور) کل اجرای job را
می‌کشد و پرداخت کشورهای بعدیِ صف برای همیشه در آن نوبت از دست می‌رود — تا
نوبت بعدی ۶ ساعت بعد. فیکس: حصار per-country + جبران خودکار نوبت‌های
از‌دست‌رفته (اگر نوبتِ تعیین‌شده از دست رفته باشد، دفعه‌ی بعد بلافاصله
پرداخت می‌شود — خود _payout_due با مقایسه‌ی slot این را تضمین می‌کند).
"""
import asyncio
import datetime
import types

import config
import database as db


def _fresh(monkeypatch, tmp_path, name="payout.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


class _Bot:
    async def send_message(self, *a, **k):
        return True


def test_slot_advance_pays_missed_slot(monkeypatch, tmp_path):
    """کشوری که نوبتش از دست رفته، در اولین تیک بعدی پرداخت می‌شود."""
    _fresh(monkeypatch, tmp_path)
    cid = db.create_country(8400, "قطر", "🇶🇦", country_key="qatar")
    start_treasury = db.get_country_by_id(cid)["treasury"]

    import main as main_mod

    # آخرین پرداخت: نوبت قبل (۵ ساعت پیش) — یعنی نوبت جاری از دست رفته
    last = (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(hours=5)).isoformat()
    db.update_country_field(cid, "last_income_date", last)
    # گارد چرخه‌ی روزانه هم برای امروز ست شده (روزانه یک‌بار مصرف/چرخه)
    db.set_setting(f"daily_cycle_date:{cid}",
                   datetime.datetime.now(datetime.timezone.utc).date().isoformat())

    ctx = types.SimpleNamespace(bot=_Bot())
    asyncio.run(main_mod.daily_income_job(ctx, force=False))

    after = db.get_country_by_id(cid)
    assert after["treasury"] > start_treasury, \
        "نوبت از‌دست‌رفته باید در اولین تیک پرداخت شود"
    # و last_income_date تازه شده باشد
    assert (after["last_income_date"] or "") != last
