# -*- coding: utf-8 -*-
"""تأیید درخواست کشور وقتی کشور به‌صورت «ردیف بی‌صاحب» (player_id=0) وجود دارد.

از زمان حذف صف و آمدن «پاک‌سازی کامل بی‌صاحب‌ها»، کشور آزاد یعنی ردیف با
player_id=0 — نه «بدون ردیف». تأیید ادمین نباید این را «واگذارشده به کاربر
دیگری» بگیرد؛ باید همان ردیف فکتوری را به متقاضی واگذار کند.
(باگ واقعی: «❌ کشور ترکیه قبلاً به کاربر دیگری واگذار شده است.»)
"""
import asyncio
import types

import config
import database as db


def _fresh(monkeypatch, tmp_path, name):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


class _FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id, text, **k):
        self.sent.append((chat_id, text))


class _FakeQuery:
    def __init__(self, data):
        self.from_user = types.SimpleNamespace(id=999001)
        self.data = data
        self.message = types.SimpleNamespace(photo=None)
        self.alerts = []
        self.edits = []

    async def answer(self, text=None, show_alert=False):
        self.alerts.append(text or "")
        if text and len(text) > 200:
            from telegram.error import BadRequest
            raise BadRequest("MESSAGE_TOO_LONG")

    async def edit_message_text(self, *a, **k):
        self.edits.append(k.get("text") or (a[0] if a else ""))


def _run(monkeypatch, data):
    from handlers import admin as admin_mod
    monkeypatch.setattr(admin_mod, "is_admin", lambda uid: True)
    query = _FakeQuery(data)
    context = types.SimpleNamespace(bot=_FakeBot())
    update = types.SimpleNamespace(callback_query=query)
    asyncio.run(admin_mod.admin_callback_handler(update, context))
    return query, context


def test_approve_assigns_existing_ownerless_row(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "ap1.db")
    # ترکیه‌ی فکتوری‌شده بی‌صاحب (مثلاً بعد از «پاک‌سازی کامل»)
    db.create_country(0, "ترکیه", "🇹🇷", country_key="turkey")
    req_id = db.create_pending_country_request(777001, "علی", "ر", "ali", "turkey")

    query, context = _run(monkeypatch, f"admin:approve_country:{req_id}")

    assert not any("قبلاً به کاربر دیگری" in t for t in query.edits), \
        "ردیف بی‌صاحب نباید «واگذارشده به دیگری» تلقی شود"
    c = db.get_country_by_key("turkey")
    assert c is not None and c["player_id"] == 777001, \
        "ردیف بی‌صاحب باید مستقیم به متقاضی واگذار می‌شد"
    assert db.get_pending_country_request(req_id) is None, "درخواست باید تعیین تکلیف شود"
    assert any(cid == 777001 for cid, _ in context.bot.sent), "DM تبریک باید برای برنده برود"


def test_approve_still_rejects_really_owned_country(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "ap2.db")
    db.create_country(555, "ترکیه", "🇹🇷", country_key="turkey")
    req_id = db.create_pending_country_request(777002, "س", "ر", None, "turkey")

    query, context = _run(monkeypatch, f"admin:approve_country:{req_id}")

    assert any("قبلاً به کاربر دیگری" in t for t in query.edits), \
        "کشورِ واقعاً صاحب‌دار باید رد شود"
    assert db.get_country_by_key("turkey")["player_id"] == 555
    assert db.get_pending_country_request(req_id) is None
    assert not any(cid == 777002 for cid, _ in context.bot.sent)


def test_quick_approve_assigns_ownerless_row_too(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "ap3.db")
    db.create_country(0, "ترکیه", "🇹🇷", country_key="turkey")
    req_id = db.create_pending_country_request(777003, "ق", "ر", "q", "turkey")

    query, context = _run(monkeypatch, f"admin:quick_approve:{req_id}")

    assert not any("قبلاً واگذار شده" in t for t in query.alerts)
    assert db.get_country_by_key("turkey")["player_id"] == 777003
    assert db.get_pending_country_request(req_id) is None
