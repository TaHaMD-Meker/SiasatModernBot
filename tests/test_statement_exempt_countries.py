# -*- coding: utf-8 -*-
"""دو درخواست مالک:
۱) کشورهای خلع‌شده‌ی ساعت ۰۰:۰۰ باید بلافاصله در منوی گرفتن کشور آزاد دیده شوند
   (قبلاً get_taken_and_pending_country_keys همه‌ی ردیف‌ها حتی player_id=0 را
   «گرفته‌شده» می‌شمرد و کشور آزاد برای همیشه 🔒 می‌ماند).
۲) ادمین بتواند فهرستی از کشورهای معاف از قانون بیانیه بسازد — این‌ها با وجود
   نداشتن بیانیه حذف نمی‌شوند.
"""
import asyncio

import pytest

import config
import database as db
import country_queue
import main


def _mk(cur, cid, pid, name, key):
    cur.execute(
        "INSERT OR REPLACE INTO countries (id, player_id, name, flag, country_key, treasury, created_at) "
        "VALUES (?, ?, ?, '🏳️', ?, 1000000, '2024-01-01T00:00:00+00:00')", (cid, pid, name, key))


class _Bot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text, **kw):
        self.sent.append(chat_id)


# ───────────── ۱) باز شدن فوری در منوی گرفتن کشور ─────────────

def test_revoked_country_is_not_taken_anymore(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "taken.db"))
    db.init_db()
    conn = db.get_connection(); cur = conn.cursor()
    _mk(cur, 1, 1001, "ایران", "iran")
    _mk(cur, 2, 1002, "عراق", "iraq")
    conn.commit(); conn.close()

    assert "iran" in db.get_taken_and_pending_country_keys()

    # خلع ساعت ۰۰:۰۰ (قرنطینه حذف شده → آزاد فوری)
    ok, _ = country_queue.quarantine_country(1, reason="inactivity")
    assert ok

    keys = db.get_taken_and_pending_country_keys()
    assert "iran" not in keys, "کشور خلع‌شده باید فوراً در منوی گرفتن کشور آزاد باشد"
    assert "iraq" in keys
    assert "iran" in {c["country_key"] for c in country_queue.get_free_countries()}


def test_pending_request_still_locks_country(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "pend.db"))
    db.init_db()
    conn = db.get_connection(); cur = conn.cursor()
    cur.execute(
        "INSERT INTO pending_country_requests (player_id, first_name, country_key, status) "
        "VALUES (2001, 'تستر', 'france', 'pending')")
    conn.commit(); conn.close()
    assert "france" in db.get_taken_and_pending_country_keys()


# ───────────── ۲) کشورهای معاف از قانون بیانیه (انتخاب ادمین) ─────────────

def _run_sweep(monkeypatch, tmp_path, name):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()
    monkeypatch.setattr(config, "ADMIN_IDS", [999])
    conn = db.get_connection(); cur = conn.cursor()
    _mk(cur, 1, 1001, "ایران", "iran")      # معاف — نباید حذف شود
    _mk(cur, 2, 1002, "عراق", "iraq")       # بدون معافیت و بدون بیانیه → حذف
    conn.commit(); conn.close()
    db.set_setting("last_inactivity_check_date", "2024-01-01")

    bot = _Bot()
    ctx = type("C", (), {"bot": bot})()
    asyncio.run(main.check_daily_inactivity_job(ctx, force_date="2024-01-02"))
    return bot


def test_exempt_country_survives_midnight_sweep(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "ex.db"))
    db.init_db()
    db.set_statement_exempt_countries(["iran"])
    assert db.get_statement_exempt_countries() == ["iran"]
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "ex.db"))

    _run_sweep(monkeypatch, tmp_path, "ex.db")

    conn = db.get_connection(); cur = conn.cursor()
    rows = {r["id"]: r["player_id"] for r in cur.execute(
        "SELECT id, player_id FROM countries").fetchall()}
    conn.close()
    assert rows[1] == 1001, "کشور معاف (ایران) نباید حذف شود"
    assert rows[2] == 0, "کشور بدون معافیت و بدون بیانیه باید حذف شود"


def test_exempt_list_persist_and_clear(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "clr.db"))
    db.init_db()
    db.set_statement_exempt_countries(["iran", "japan", "iran"])
    assert db.get_statement_exempt_countries() == ["iran", "japan"]
    db.set_statement_exempt_countries([])
    assert db.get_statement_exempt_countries() == []


def test_source_guard_sweep_checks_exempt_list():
    src = open("main.py", encoding="utf-8").read()
    start = src.index("async def check_daily_inactivity_job")
    end = src.index("revoked_count += 1", start)
    window = src[start:end]
    assert "get_statement_exempt_countries" in window, \
        "جاب نیمه‌شب باید فهرست معافیت دستی ادمین را اعمال کند"
