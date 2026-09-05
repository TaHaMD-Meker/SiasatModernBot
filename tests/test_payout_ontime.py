# -*- coding: utf-8 -*-
"""گزارش مالک: «پیام واریز درآمدها سر ساعت نمی‌آید.»

سه ریشه‌ی مستقل برای گم‌شدن/دیر رسیدن پیام واریز:

۱) دیرِ ذاتی: تیک بررسی ۹۰۰ ثانیه‌ای است — پیام واریز تا ۱۵ دقیقه بعد از
   مرز نوبت (۰۳/۰۹/۱۵/۲۱ تهران) می‌تواند عقب بیفتد. چک باید ۶۰ ثانیه‌ای
   باشد تا واریز ~سر ساعت برسد.
۲) حذف بی‌صدا: پیام واریز با parse_mode="Markdown" می‌رود؛ اگر هر چیزی در
   متن مارک‌داون را بشکند (کاراکترهای نام کشور/نوشته‌های متغیر)،
   BadRequest می‌خورد و پیام برای همیشه نمی‌رسد — فقط یک logger.warning.
   باید fallback بدون مارک‌داون باشد تا پیام همیشه برسد.
۳) تداخل اجرا: اگر اجرای قبلی job هنوز تمام نشده باشد (سرور کند/شبکه‌ی
   قفل‌شده)، اجرای موازی می‌تواند پرداخت تکراری یا نیمه‌کاره بسازد —
   job باید reentrancy-guard داشته باشد.
"""
import asyncio
import datetime
import inspect
import types

import pytest
from telegram.error import BadRequest

import config
import database as db


def _fresh(monkeypatch, tmp_path, name="ontime.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


# ───────────── ۱) گرید زمان‌بندی: تیک دقیقه‌ای + قفل تک‌نمونه ─────────────

def test_job_polls_every_minute_with_single_instance():
    src = inspect.getsource(__import__("main"))
    line = next(l for l in src.splitlines() if "run_repeating(daily_income_job" in l)
    assert "interval=60" in line, f"تیک واریز باید ۶۰ ثانیه باشد (سر ساعت): {line.strip()}"
    assert 'job_kwargs={"max_instances": 1}' in src, \
        "job باید تک‌نمونه باشد تا اجراهای موازی پرداخت را خراب نکنند"


# ───────────── ۲) پیام واریز باید همیشه برسد — حتی با مارک‌داونِ شکسته ─────────────

def test_payout_dm_falls_back_to_plain_when_markdown_breaks(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "ontime2.db")
    cid = db.create_country(8500, "آلمان*تست[", "🇩🇪", country_key="germany_md")
    db.update_country_field(cid, "daily_income", 2_000_000)
    db.update_country_field(cid, "player_id", 5566)
    last = (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(hours=5)).isoformat()   # نوبتِ بعدی
    db.update_country_field(cid, "last_income_date", last)
    # گارد مصرف روزانه برای امروز ثبت شده → first_of_day قطع می‌شود (مسیر پیام واریز نوبت دوم)
    db.set_setting(f"daily_cycle_date:{cid}",
                   datetime.datetime.now(datetime.timezone.utc).date().isoformat())
    before = db.get_country_by_id(cid)["treasury"]

    sent = []

    class _Bot:
        async def send_message(self, chat_id=None, text=None, reply_markup=None, parse_mode=None, **k):
            if parse_mode:                      # هر ارسال مارک‌داونی می‌شکند
                raise BadRequest("Can't parse entities")
            sent.append((chat_id, str(text)))
            return True

    import main as main_mod
    asyncio.run(main_mod.daily_income_job(types.SimpleNamespace(bot=_Bot()), force=False))

    assert sent, "پیام واریز باید حتی با مارک‌داون شکسته برسد (fallback ساده)"
    assert any("واریز دوره‌ای" in t for _c, t in sent)
    after = db.get_country_by_id(cid)["treasury"]
    assert after > before, "واریز پول هم باید انجام شده باشد"


# ───────────── ۳) اجرای هم‌زمان دو تیک = پرداخت تکراری ممنوع ─────────────

def test_concurrent_ticks_pay_exactly_once(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "ontime3.db")
    cid = db.create_country(8501, "ترکیه", "🇹🇷", country_key="turkey_md")
    db.update_country_field(cid, "daily_income", 4_000_000)
    last = (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(hours=5)).isoformat()
    db.update_country_field(cid, "last_income_date", last)
    before = db.get_country_by_id(cid)["treasury"]

    class _Bot:
        async def send_message(self, *a, **k):
            return True

    import main as main_mod
    ctx = types.SimpleNamespace(bot=_Bot())
    # دو تیک ۱۵ثانیه‌ایِ هم‌پوشان (سرور کند: اجرای قبلی هنوز تمام نشده)
    awaiteds = [main_mod.daily_income_job(ctx, force=False) for _ in range(3)]
    results = asyncio.run(_gather(*awaiteds))

    paid = db.get_country_by_id(cid)["treasury"] - before
    c = db.get_country_by_id(cid)
    expected = (int(4_000_000 / main_mod.INCOME_PARTS)
                + int((c["tax_income"] or 0) / main_mod.INCOME_PARTS)
                - int(db.calculate_country_maintenance_cost(cid)["total_maint"] / main_mod.INCOME_PARTS))
    assert paid == expected, \
        f"سه تیک هم‌پوشان باید دقیقاً یک نوبت پرداخت کند (شد: {paid:,} بجای {expected:,})"


async def _gather(*aws):
    return await asyncio.gather(*aws, return_exceptions=True)
