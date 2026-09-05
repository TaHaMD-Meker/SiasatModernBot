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


def test_second_slot_sends_payout_dm_and_counts(monkeypatch, tmp_path):
    """نوبت‌های ۲-۴ روز (first_of_day=False) باید DM واریز بفرستند و شمارنده بزنند.

    باگ واقعی ساعت ۰۹:۵۲: پول واریز می‌شد ولی چون «cycle» فقط در شاخه‌ی
    اولین-پرداخت-روز تعریف می‌شد، ساخت پیام واریز می‌ترکید و هیچ DM
    به بازیکن نمی‌رفت + شمارنده‌ی job هم UnboundLocalError می‌داد.
    """
    import types
    import main as main_mod
    _fresh(monkeypatch, tmp_path, "slot2.db")
    cid = db.create_country(8401, "بحرین", "🇧🇭", country_key="bahrain")
    db.update_country_field(cid, "daily_income", 2_000_000)
    # آخرین پرداخت ۵ ساعت پیش = همان روز ایران → نوبت دوم (first_of_day=False)
    last = (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(hours=5)).isoformat()
    db.update_country_field(cid, "last_income_date", last)

    sent = []

    class _Bot:
        async def send_message(self, chat_id=None, text=None, **k):
            sent.append((chat_id, text))
            return True

    ctx = types.SimpleNamespace(bot=_Bot())
    n = asyncio.run(main_mod.daily_income_job(ctx, force=False))

    assert n >= 1, "شمارنده باید کشورِ پرداخت‌شده را بشمارد"
    assert sent, "پیام واریز نوبت دوم باید به بازیکن برود"
    assert any("واریز" in (t or "") for _c, t in sent), "متن پیام باید واریز دوره‌ای باشد"
