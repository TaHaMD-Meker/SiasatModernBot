# -*- coding: utf-8 -*-
"""قرارداد مالک: «وقتی واریز فوری درآمد می‌زنم نباید ربطی به بقیه‌ها داشته باشد.»

باگ: دکمه‌ی «⚡ توزیع فوری درآمد روزانه» کل daily_income_job را با force=True
اجرا می‌کرد یعنی:
• درآمد کاملِ روز همه‌ی کشورها یک‌جا واریز می‌شد (تورم خالص)
• برای همه‌ی رهبران پیام «توزیع فوری» می‌رفت
• last_income_date همه صفر می‌شد → گرید ۶ساعته‌ی همه‌ی سرور به ساعت کلیک
  ادمین کشیده می‌شد و نوبت‌های بعدی همه جابه‌جا می‌شد.

قرارداد: واریز فوری فقط کشور خودِ ادمین را پرداخت می‌کند — تمام.
"""
import asyncio
import datetime
import inspect
import types

import config
import database as db


def _fresh(monkeypatch, tmp_path, name="instant.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


class _Bot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id=None, text=None, **k):
        self.sent.append((chat_id, str(text)))
        return True


def _mk(player_id, key, name, daily=4_000_000):
    cid = db.create_country(player_id, name, "🏳️", country_key=key)
    db.update_country_field(cid, "daily_income", daily)
    db.update_country_field(cid, "tax_income", 2_000_000)
    db.update_country_field(cid, "player_id", player_id)
    return cid


def test_instant_payout_touches_only_the_admins_country(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "instant2.db")
    a = _mk(8600, "atland", "آتلانتیس")       # کشور ادمین
    b = _mk(8601, "bloria", "بلوریا")          # شاهد بی‌گناه
    a_before = db.get_country_by_id(a)["treasury"]
    b_before = db.get_country_by_id(b)["treasury"]
    b_last = db.get_country_by_id(b)["last_income_date"]

    import main as main_mod
    bot = _Bot()
    msg = asyncio.run(main_mod.instant_payout_for(a, types.SimpleNamespace(bot=bot)))

    a_after = db.get_country_by_id(a)["treasury"]
    b_after = db.get_country_by_id(b)
    paid = a_after - a_before
    expected = ((4_000_000 + 2_000_000)
                - db.calculate_country_maintenance_cost(a)["total_maint"])
    assert paid == expected, f"کشور ادمین باید درآمد کامل روز را بگیرد (شد: {paid:,})"
    assert (db.get_country_by_id(a)["last_income_date"] or ""), "گرید خودِ ادمین به‌روز شود"
    assert b_after["treasury"] == b_before, "🚨 پولِ کشورهای دیگر دست نخورد"
    assert b_after["last_income_date"] == b_last, "🚨 گرید کشورهای دیگر جابه‌جا نشود"
    assert not any(c == 8601 for c, _t in bot.sent), "🚨 برای بازیکن دیگر پیام نرود"
    assert any(8600 == c for c, _t in bot.sent), "پول‌رسان به خود بازیکن برسد"
    assert msg, "پیام نتیجه برای پنل ادمین برگردد"


def test_instant_payout_does_not_double_burn_daily_cycle(monkeypatch, tmp_path):
    """force نباید مصرف روزانه را دوباره بسوزاند (قرارداد قبلی — همچنان برقرار)."""
    _fresh(monkeypatch, tmp_path, "instant3.db")
    a = _mk(8602, "ctide", "سایدیا")
    db.set_setting(f"daily_cycle_date:{a}",
                   datetime.datetime.now(datetime.timezone.utc).date().isoformat())
    oil_before = db.get_country_by_id(a)["oil_reserves"]
    ledger_before = len(db.get_oil_ledger(a))

    import main as main_mod
    asyncio.run(main_mod.instant_payout_for(a, types.SimpleNamespace(bot=_Bot())))

    assert db.get_country_by_id(a)["oil_reserves"] == oil_before, "مصرف روزانه دوباره نشود"
    assert len(db.get_oil_ledger(a)) == ledger_before, "دفتر نفت ردیف تکراری نمی‌گیرد"


def test_admin_button_is_scoped_to_admin_country_only():
    """دکمه‌ی admin:daily_income دیگر نباید job عمومی را با force بزند."""
    src = inspect.getsource(__import__("handlers.admin", fromlist=["x"]))
    assert "daily_income_job(context, force=True)" not in src, \
        "دکمه نباید همه‌ی کشورها را پرداخت کند"
    assert "instant_payout_for" in src, "دکمه باید واریز فوریِ تک‌کشوری را صدا بزند"
