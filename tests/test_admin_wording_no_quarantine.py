# -*- coding: utf-8 -*-
"""واژه‌ی منسوخ «قرنطینه» باید از تمام UI ادمین حذف شده باشد (دستور مالک).

سیستم قرنطینه/صف کلاً برداشته شده؛ هیچ متن قابل‌مشاهده‌ای نباید از آن اسم
ببرد. پنل کشورهای بی‌صاحب هم باید شبیه «قفسه‌ی کشورهای باز برای گرفتن» باشد —
نه صف گیرکرده — و ردیف‌ها نباید «(ID: 0)» گیج‌کننده داشته باشند.
"""
import asyncio
import types

import config
import database as db
from handlers import admin as admin_mod


def _fresh(monkeypatch, tmp_path, name):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


class _FakeQuery:
    def __init__(self):
        self.message = types.SimpleNamespace(photo=None)
        self.edits = []

    async def answer(self, text=None, show_alert=False):
        return True

    async def edit_message_text(self, *a, **k):
        self.edits.append({"text": k.get("text") or (a[0] if a else ""),
                           "markup": k.get("reply_markup")})


def test_admin_badge_never_says_quarantine():
    out = admin_mod._admin_summary_line(
        {"countries": 0, "payments": 0, "roles": 0, "quarantined": 22})
    assert "قرنطینه" not in out, f"برچسب قدیمی هنوز هست: {out}"
    assert "بی‌صاحب" in out and "22" in out


def test_visible_admin_texts_have_no_quarantine_word():
    src = open("handlers/admin.py", encoding="utf-8").read()
    # متن زیرمنوی مسدودسازی
    assert "ورود به صف، پذیرش پیشنهاد و استرداد قرنطینه" not in src
    # متن تایید حذف مالکیت
    assert "برخلاف قرنطینه" not in src
    # برچسب خلاصه‌ی پنل
    assert "قرنطینه\"" not in src.split("def _admin_summary_line")[1].split("def ")[0]


def test_ownerless_panel_reads_as_open_shelf(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "shelf.db")
    db.create_country(0, "ترکیه", "🇹🇷", country_key="turkey")
    query = _FakeQuery()
    asyncio.run(admin_mod.show_queue_panel(query, types.SimpleNamespace()))

    body = "\n".join(e["text"] for e in query.edits)
    assert "قرنطینه" not in body, "پنل نباید درباره‌ی قرنطینه حرف بزند"
    assert "(ID: 0)" not in body, "ردیف‌ها نباید (ID: 0) گیج‌کننده داشته باشند"
    assert "/start" in body, "باید معلوم باشد این کشورها در /start بازند"
    assert "ترکیه" in body
