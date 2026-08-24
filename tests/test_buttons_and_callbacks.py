# -*- coding: utf-8 -*-
"""
تست‌های اعتبارسنجی کیبورد، الگوهای دکمه‌ها و کال‌بک‌ها.
"""

import pytest
import re
from unittest.mock import AsyncMock, MagicMock
from telegram import Update, User, Message, CallbackQuery
from telegram.ext import ContextTypes, Application, MessageHandler, CallbackQueryHandler

import config
import database as db
from utils import get_main_keyboard
from handlers.country import require_country as country_require_country
from handlers.assets import get_assets_handlers
from handlers.bases import get_bases_handlers


def test_main_keyboard_regex_matching():
    """بررسی تطابق تمام دکمه‌های کیبورد پایین با Regexهای ثبت‌شده در main.py."""
    # کلیدهای کیبورد برای کاربر عادی و ادمین
    user_kb = get_main_keyboard(12345)
    admin_kb = get_main_keyboard(config.ADMIN_IDS[0] if config.ADMIN_IDS else 8052987465)

    all_buttons = set()
    for row in user_kb.keyboard:
        for btn in row:
            txt = btn.text if hasattr(btn, "text") else str(btn)
            all_buttons.add(txt)
    for row in admin_kb.keyboard:
        for btn in row:
            txt = btn.text if hasattr(btn, "text") else str(btn)
            all_buttons.add(txt)

    registered_patterns = [
        r"^🌐 وضعیت کشور$",
        r"^📊 رضایت عمومی$",
        r"^🎖️ دارایی‌های نظامی$",
        r"^🏦 خزانه و طلا$",
        r"^🛢️ وضعیت نفت$",
        r"^🪖 وضعیت ارتش$",
        r"^🏪 فروشگاه$",
        r"^(?:⭐️\s*بتل‌پس|⭐️\s*بتل پس|⭐️\s*بتل‌پس فصلی|⭐️\s*Battle Pass|/pass|/bp)$",
        r"^(?:💎\s*خدمات ویژه VIP|👑\s*خدمات VIP|💎\s*اشتراک VIP)$",
        r"^(?:🏛️ دانشکده|📜 راهنما)$",
        r"^👑 پنل مدیریت$",
        r"^(?:🎯 ستاد توسعه و اقدامات راهبردی|🎖️ تحرکات نظامی)$",
        r"^🎯 عملیات$",
        r"^📢 بیانیه و توییت$",
        r"^🤝 دیپلماسی و روابط$",
    ]
    compiled_patterns = [re.compile(p) for p in registered_patterns]

    for btn in all_buttons:
        matched = any(p.match(btn) for p in compiled_patterns)
        assert matched, f"دکمه «{btn}» در هیچ یک از Regexهای پیام‌های اصلی ثبت نشده است!"


@pytest.mark.anyio
async def test_require_country_pending_request():
    """اگر کاربر کشوری نداشته باشد ولی در صف تایید ادمین باشد، پیام دقیق دریافت می‌کند."""
    db.init_db()
    test_uid = 999111222
    db.delete_country_by_player(test_uid)

    # کاربر کشوری ندارد و درخواستی هم ندارد
    mock_update = MagicMock(spec=Update)
    mock_msg = MagicMock(spec=Message)
    mock_msg.reply_text = AsyncMock()
    mock_update.message = mock_msg
    mock_update.callback_query = None
    mock_user = MagicMock(spec=User)
    mock_user.id = test_uid
    mock_update.effective_user = mock_user

    c = await country_require_country(mock_update)
    assert c is None
    assert mock_msg.reply_text.called
    assert "هنوز کشوری در بازی ندارید" in mock_msg.reply_text.call_args[0][0]

    # حالا درخواست ثبت می‌کنیم
    req_id = db.create_pending_country_request(test_uid, "Test", "User", "testuser", "iran")
    assert req_id > 0

    mock_msg.reply_text.reset_mock()
    c2 = await country_require_country(mock_update)
    assert c2 is None
    assert mock_msg.reply_text.called
    assert "در صف بررسی ادمین است" in mock_msg.reply_text.call_args[0][0]

    # پاکسازی
    with db.get_connection() as conn:
        conn.execute("DELETE FROM pending_country_requests WHERE player_id = ?", (test_uid,))
        conn.commit()


def test_guide_navigation_callback_patterns():
    """بررسی اینکه دکمه‌های دانشکده (assets:menu و bases:menu) توسط هندلرها پوشش داده می‌شوند."""
    asset_handlers = get_assets_handlers()
    base_handlers = get_bases_handlers()

    asset_cb_patterns = [h.pattern for h in asset_handlers if isinstance(h, CallbackQueryHandler)]
    base_cb_patterns = [h.pattern for h in base_handlers if isinstance(h, CallbackQueryHandler)]

    assert any(p.search("assets:menu") for p in asset_cb_patterns)
    assert any(p.search("bases:menu") for p in base_cb_patterns)
