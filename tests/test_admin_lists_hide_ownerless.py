# -*- coding: utf-8 -*-
"""کشورهای بی‌صاحب (player_id=0) نباید در «مدیریت کشورها» دیده شوند.

باگ واقعی: بعد از «پاک‌سازی کامل بی‌صاحب‌ها» ردیف‌های فکتوری (ID: —) در
لیست/جستجوی مدیریت کشورها مثل کشورِ عادی نمایش داده می‌شدند و انگار ربات
آن‌ها را دارای بازیکن می‌داند. این کشورها باید فقط در پنل اختصاصی
«🌍 کشورهای بی‌صاحب» فهرست شوند؛ سازمان ملل مستثناست.
"""
import asyncio
import types

import config
import database as db


def _fresh(monkeypatch, tmp_path, name):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()
    monkeypatch.setattr(config, "ADMIN_IDS", [42])


class _FakeQuery:
    def __init__(self):
        self.from_user = types.SimpleNamespace(id=42)
        self.message = types.SimpleNamespace(photo=None)
        self.edits = []

    async def answer(self, text=None, show_alert=False):
        return True

    async def edit_message_text(self, *a, **k):
        self.edits.append({"text": k.get("text") or (a[0] if a else ""),
                           "markup": k.get("reply_markup")})


class _FakeMessage:
    def __init__(self, text):
        self.text = text
        self.replies = []

    async def reply_text(self, *a, **k):
        self.replies.append({"text": a[0] if a else k.get("text", ""),
                             "markup": k.get("reply_markup")})


def _button_texts(markup):
    out = []
    if markup is None:
        return out
    for row in getattr(markup, "inline_keyboard", []):
        for btn in row:
            out.append(btn.text)
    return out


def _seed():
    # صاحب‌دار: بحرین برای بازیکن ۵۰۰ — بی‌صاحب: ترکیه فکتوری — سازمان ملل: مستثنا
    db.create_country(500, "بحرین", "🇧🇭", country_key="bahrain")
    db.create_country(0, "ترکیه", "🇹🇷", country_key="turkey")
    db.create_country(0, "سازمان ملل", "🇺🇳", country_key="un")


def test_countries_list_hides_ownerless(monkeypatch, tmp_path):
    from handlers import admin as admin_mod

    _fresh(monkeypatch, tmp_path, "lst.db")
    _seed()
    query = _FakeQuery()
    context = types.SimpleNamespace()

    asyncio.run(admin_mod.show_countries_list(query, context, 0, None))

    texts = "\n".join("\n".join(_button_texts(e["markup"])) for e in query.edits)
    body = "\n".join(e["text"] for e in query.edits)
    assert "بحرین" in texts, "کشور صاحب‌دار باید دیده شود"
    assert "ترکیه" not in texts, "کشور بی‌صاحب نباید در لیست مدیریت باشد"
    assert "سازمان ملل" in texts, "سازمان ملل باید مستثنا بماند"
    assert "بی‌صاحب" in body, "باید راهنمای پنل اختصاصی بی‌صاحب‌ها باشد"


def test_country_search_hides_ownerless(monkeypatch, tmp_path):
    from handlers import admin as admin_mod

    _fresh(monkeypatch, tmp_path, "srch.db")
    _seed()
    monkeypatch.setattr(config, "ADMIN_IDS", [42])

    update = types.SimpleNamespace(
        effective_user=types.SimpleNamespace(id=42),
        message=_FakeMessage("ترکیه"),
    )
    context = types.SimpleNamespace(
        user_data={"admin_awaiting_input": {"type": "admin_search_country"}},
        bot=None,
    )

    asyncio.run(admin_mod.admin_input_text_handler(update, context))

    assert update.message.replies, "باید پاسخی برسد"
    rep = update.message.replies[0]
    texts = "\n".join(_button_texts(rep["markup"]))
    assert "ترکیه" not in texts, "کشور بی‌صاحب نباید در نتایج جستجو باشد"
    assert "بی‌صاحب" in rep["text"], "باید راهنمای پنل اختصاصی بی‌صاحب‌ها باشد"

    # جستجوی کشورِ صاحب‌دار همچنان عادی کار می‌کند
    update2 = types.SimpleNamespace(
        effective_user=types.SimpleNamespace(id=42),
        message=_FakeMessage("بحرین"),
    )
    context2 = types.SimpleNamespace(
        user_data={"admin_awaiting_input": {"type": "admin_search_country"}},
        bot=None,
    )
    asyncio.run(admin_mod.admin_input_text_handler(update2, context2))
    texts2 = "\n".join(_button_texts(update2.message.replies[0]["markup"]))
    assert "بحرین" in texts2
