# -*- coding: utf-8 -*-
"""استخر واگذاری بدون صف: خلع = آزاد فوری؛ صف انتظار کلاً حذف شده است.

مسیر گرفتن کشور فقط: ‎/start ← pick_country ← درخواست معلق ← تایید ادمین.
"""
import pytest

import config
import database as db
import country_queue as cq


def _fresh(monkeypatch, tmp_path, name="cq.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


# ───────────── رفتار هسته‌ای: خلع = آزاد فوری با حفظ دارایی ─────────────

def test_revocation_frees_country_instantly_keeping_assets(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = db.create_country(5001, "ایران", "🇮🇷", country_key="iran")
    conn = db.get_connection()
    with conn:
        conn.execute("UPDATE countries SET treasury = 7_000_000 WHERE id = ?", (cid,))
    conn.close()

    ok, _msg = cq.quarantine_country(cid, reason="inactivity")
    assert ok

    country = db.get_country_by_id(cid)
    assert country["player_id"] == 0 and country["treasury"] == 7_000_000, \
        "خلع باید فوری باشد و دارایی دست‌نخورده بماند"
    assert any(c["id"] == cid for c in cq.get_free_countries())


def test_reclaim_is_retired():
    ok, msg, row = cq.reclaim_country(123)
    assert ok is False and row is None and "قرنطینه" in msg


# ───────────── صف دیگر وجود ندارد ─────────────

def test_queue_system_is_gone():
    src = open("country_queue.py", encoding="utf-8").read()
    for gone in ("join_queue", "process_queue", "accept_offer", "decline_offer",
                 "get_queue_entry", "queue_position", "OFFER_HOURS", "PRIORITY_PAID"):
        assert gone not in src, f"{gone} باید از سیستم حذف شده باشد"
    src = open("main.py", encoding="utf-8").read()
    assert "handlers.queue" not in src and "country_queue_job" not in src, \
        "هندلر و جاب صف باید از main حذف شده باشند"
    assert "/queue" not in src or "صف کشور حذف شد" in src


def test_player_country_request_path_has_guards():
    """مسیر جدید گرفتن کشور باید هم بن‌شده و هم داور را رد کند."""
    src = open("handlers/start.py", encoding="utf-8").read()
    pick = src.index("async def pick_country")
    window = src[pick:pick + 6000]
    assert "is_banned" in window, "مسیر گرفتن کشور باید کاربر مسدود را رد کند"
    assert "is_playing_restricted" in window, "مسیر گرفتن کشور باید داور محروم را رد کند"
    assert "get_taken_and_pending_country_keys" in window, "جلوگیری از درخواست همزمان دو نفر"
