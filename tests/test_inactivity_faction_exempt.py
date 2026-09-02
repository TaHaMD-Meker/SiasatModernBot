# -*- coding: utf-8 -*-
"""
گروهک‌های استاندارد (۱۰۰هزاری) و شبه‌نظامی‌های سفارشی — همه با کلید faction_* —
مشمول قانون «۲ بیانیه در روز» و سلب مالکیت نیمه‌شب نیستند؛ فقط کشورهای رسمی.
"""

import asyncio
import pytest
import config
import database as db
import main


def _fresh(monkeypatch, tmp_path, name):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()
    monkeypatch.setattr(config, "ADMIN_IDS", [999])


def _mk(cur, cid, pid, name, key):
    cur.execute(
        "INSERT OR REPLACE INTO countries (id, player_id, name, flag, country_key, treasury, created_at) "
        "VALUES (?, ?, ?, '🏳️', ?, 1000000, '2024-01-01T00:00:00+00:00')", (cid, pid, name, key))


class _Bot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text, **kw):
        self.sent.append(chat_id)


def _run_job(monkeypatch, tmp_path, name):
    _fresh(monkeypatch, tmp_path, name)
    conn = db.get_connection(); cur = conn.cursor()
    _mk(cur, 1, 1001, "ایران رسمی", "iran")            # کشور رسمی — بدون بیانیه
    _mk(cur, 2, 1002, "گروهک استاندارد", "faction_hezbollah")   # گروهک ۱۰۰هزاری
    _mk(cur, 3, 1003, "گروهک سفارشی", "faction_custom_x")       # شبه‌نظامی سفارشی
    conn.commit(); conn.close()
    # تا «اولین اجرا» صرفاً تاریخ ذخیره نکند و واقعاً پردازش کند
    db.set_setting("last_inactivity_check_date", "2024-01-01")

    bot = _Bot()
    ctx = type("C", (), {"bot": bot})()
    asyncio.run(main.check_daily_inactivity_job(ctx, force_date="2024-01-02"))
    return bot


def test_factions_exempt_official_revoked(monkeypatch, tmp_path):
    bot = _run_job(monkeypatch, tmp_path, "exemp.db")

    conn = db.get_connection(); cur = conn.cursor()
    rows = {r["id"]: r for r in cur.execute(
        "SELECT id, player_id, quarantined_at FROM countries").fetchall()}
    conn.close()

    # کشور رسمی بدون بیانیه → قرنطینه (player_id صفر و مهر زمانی قرنطینه)
    assert rows[1]["player_id"] == 0 and rows[1]["quarantined_at"], \
        "کشور رسمی بدون بیانیه باید قرنطینه شود"
    # گروهک‌ها باید کاملاً دست‌نخورده بمانند
    assert rows[2]["player_id"] == 1002 and not rows[2]["quarantined_at"], \
        "گروهک استاندارد (۱۰۰هزاری) نباید سلب مالکیت/قرنطینه شود"
    assert rows[3]["player_id"] == 1003 and not rows[3]["quarantined_at"], \
        "گروهک سفارشی نباید سلب مالکیت/قرنطینه شود"


def test_source_guard_job_checks_faction():
    src = open("main.py", encoding="utf-8").read()
    start = src.index("async def check_daily_inactivity_job")
    end = src.index("revoked_count += 1", start)
    window = src[start:end]
    assert "is_militia_country_key" in window, \
        "جاب نیمه‌شب باید گروهک‌های faction_* را از سلب مالکیت معاف کند"


def test_ui_badges_exempt_factions():
    d = open("handlers/admin_dossier.py", encoding="utf-8").read()
    assert 'معاف از بیانیه‌ی روزانه' in d and "is_militia_country_key" in d
    s = open("handlers/statements.py", encoding="utf-8").read()
    assert s.count("گروهک — معاف از سهمیه") == 2, "بیانیه و توییت هر دو باید معافیت را نشان دهند"
    assert "گروهک شبه‌نظامی هستید" in s
