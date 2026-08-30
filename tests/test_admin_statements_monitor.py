# -*- coding: utf-8 -*-
"""
تست سیستم رصد بیانیه‌ها و توییت‌های ۲۴ ساعت اخیر در پنل مدیریت ادمین.
"""

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import database as db  # noqa: E402


def test_statement_recording_and_retrieval(monkeypatch):
    """بررسی ثبت و دریافت بیانیه‌ها در ۲۴ ساعت اخیر."""
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr(config, "DB_PATH", os.path.join(tmpdir, "test_statements.db"))

    import importlib
    importlib.reload(db)
    db.init_db()

    # ساخت یک کشور نمونه
    cid = db.create_country(111222, "کشور تست", "🏳️", country_key="test_land")
    assert cid is not None

    # ثبت دو بیانیه و یک توییت
    s1 = db.record_country_statement(cid, 111222, "statement", "بیانیه آزمایشی اول دولت")
    s2 = db.record_country_statement(cid, 111222, "tweet", "توییت آزمایشی وزیر امور خارجه")
    assert s1 > 0
    assert s2 > 0

    # تست get_recent_statements
    recent_24h = db.get_recent_statements(limit=10, hours=24)
    assert len(recent_24h) == 2
    assert recent_24h[0]["statement_type"] in ["statement", "tweet"]
    assert recent_24h[0]["country_name"] == "کشور تست"
    assert recent_24h[0]["player_id"] == 111222

    # تست get_statement_by_id
    detail = db.get_statement_by_id(s1)
    assert detail is not None
    assert detail["content"] == "بیانیه آزمایشی اول دولت"
    assert detail["country_name"] == "کشور تست"

    # تست delete_statement_by_id
    deleted = db.delete_statement_by_id(s1)
    assert deleted is True
    assert db.get_statement_by_id(s1) is None
    assert len(db.get_recent_statements(limit=10, hours=24)) == 1

import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import Update, CallbackQuery, User, Message
from handlers import admin


@pytest.mark.anyio
async def test_admin_statements_monitor_ui(monkeypatch):
    """تست پاسخ‌دهی هندلر پنل ادمین برای رصد بیانیه‌های ۲۴ ساعت اخیر."""
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr(config, "DB_PATH", os.path.join(tmpdir, "test_ui_stmts.db"))
    import importlib
    importlib.reload(db)
    db.init_db()

    cid = db.create_country(999888, "امپراتوری تست", "👑", country_key="test_empire")
    s_id = db.record_country_statement(cid, 999888, "statement", "متن بیانیه مهم کشوری")

    # Mock admin query
    monkeypatch.setattr(config, "ADMIN_IDS", [12345])
    user = User(id=12345, is_bot=False, first_name="Admin")
    query = MagicMock(spec=CallbackQuery)
    query.from_user = user
    query.data = "admin:recent_stmts:0:24h"
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()

    update = MagicMock(spec=Update)
    update.callback_query = query
    context = MagicMock()

    await admin.admin_callback_handler(update, context)

    # Verify query.edit_message_text was called with statements info
    query.edit_message_text.assert_called_once()
    args, kwargs = query.edit_message_text.call_args
    assert "رصد بیانیه‌ها و توییت‌های ارسالی" in args[0]
    assert "امپراتوری تست" in args[0]
    assert "999888" in args[0]
