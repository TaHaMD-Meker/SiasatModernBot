# -*- coding: utf-8 -*-
"""دکمه‌ی ادمین «پاک‌سازی کامل بی‌صاحب‌ها»: ریست فکتوری کشورهای player_id=0.

کشور بی‌صاحب با تمام میراث (خزانه تغییرکرده، ساختمان، انبار جنگی، بیانیه‌ها،
فرمانده‌ها) حذف و با مقادیر پیش‌فرض کانفیگ + انبار استاندارد از نو ساخته می‌شود.
گروهک‌های faction_* و سازمان ملل دست‌نخورده می‌مانند؛ کشور صاحب‌دار هم.
"""
import pytest

import config
import database as db
import country_queue as cq


def _fresh(monkeypatch, tmp_path, name="wipe.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


def test_ownerless_countries_get_factory_reset(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    # بی‌صاحب آلوده: خزانه/انبار/ساختمان/بیانیه/فرمانده تغییرکرده
    cid = db.create_country(7001, "ایران", "🇮🇷", country_key="iran")
    db.update_country_field(cid, "player_id", 0)
    db.update_country_field(cid, "treasury", 123)
    conn = db.get_connection()
    with conn:
        conn.execute("INSERT INTO equipment (country_id, item_key, quantity) VALUES (?, 'small_factory', 3)", (cid,))
        conn.execute(
            "INSERT INTO daily_statements (country_id, player_id, statement_type, content, created_at, statement_date)"
            " VALUES (?, 7001, 'statement', 'متن', '2026-09-05T00:00:00+00:00', '2026-09-05')", (cid,))
    conn.close()

    ok, count, msg = db.hard_reset_ownerless_countries(actor="test")
    assert ok and count >= 1

    fresh = db.get_country_by_key("iran")
    assert fresh and fresh["player_id"] == 0, "بازسازی‌شده باید همچنان بی‌صاحب و «باز» باشد"
    expected_treasury = config.COUNTRY_STARTING_OVERRIDES.get(
        "iran", config.STARTING_VALUES)["treasury"]
    assert fresh["treasury"] == expected_treasury, "خزانه باید پیش‌فرض فکتوری باشد"
    assert fresh["warheads"] == 0

    # ساختمان‌ها و بیانیه‌های میراثی پاک شده‌اند
    conn = db.get_connection()
    eq = conn.execute("SELECT COUNT(*) AS n FROM equipment WHERE country_id = ?",
                      (fresh["id"],)).fetchone()["n"]
    stmts = conn.execute("SELECT COUNT(*) AS n FROM daily_statements WHERE country_id = ?",
                         (fresh["id"],)).fetchone()["n"]
    conn.close()
    assert eq == 0
    assert stmts == 0

    # انبار استاندارد سید شده (شاهد-۱۳۶ ایران)
    assets = db.get_country_assets(fresh["id"])
    assert assets, "انبار کشور بازسازی‌شده نباید خالی باشد"
    assert all(int(a["amount"] or 0) >= 0 for a in assets)


def test_owned_faction_and_un_are_untouched(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "wipe2.db")
    owned_id = db.create_country(7002, "عراق", "🇮🇶", country_key="iraq")
    faction_id = db.create_country(7003, "گروهک", "🏳️", country_key="faction_x")
    un_id = db.create_country(7004, "سازمان ملل", "🇺🇳", country_key="un")

    ok, count, msg = db.hard_reset_ownerless_countries(actor="test")
    assert ok and count == 0, "اگر همه صاحب دارند کاری نکند"

    # بی‌صاحب کن و ریست کن
    db.update_country_field(owned_id, "player_id", 0)
    ok, count, msg = db.hard_reset_ownerless_countries(actor="test")
    assert ok and count == 1

    assert db.get_country_by_id(faction_id) is not None, "گروهک نباید حذف شود"
    assert db.get_country_by_id(un_id) is not None, "سازمان ملل نباید حذف شود"
    assert db.get_country_by_id(owned_id) is None, "بی‌صاحب باید حذف و بازسازی شود"


def test_panel_has_wipe_button_with_confirm_step():
    src = open("handlers/admin.py", encoding="utf-8").read()
    assert "admin:wipe_free_confirm" in src, "دکمه‌ی پاک‌سازی باید در پنل بی‌صاحب‌ها باشد"
    confirm = src.index("async def wipe_free_confirm")
    assert "غیرقابل بازگشت" in src[confirm:confirm + 1500], "تایید مخرب بودن الزامی است"
    assert "admin:wipe_free_run" in src
    run_idx = src.index('data == "admin:wipe_free_run"')
    window = src[run_idx:run_idx + 700]
    assert "hard_reset_ownerless_countries" in window, "اجرای واقعی باید تابع ریست را صدا بزند"


# ----------------------------------------------------------------------------
# رگرسیون: «دکمه بله همه را پاک و بازسازی کن کار نمیکنه»
# علت: متن query.answer بلندتر از سقف ۲۰۰ کاراکتری تلگرام (لیست نام کشورها)
# → BadRequest → هیچ بازخوردی به ادمین نمی‌رسید. دکمه باید همیشه پاسخ کوتاه
# بدهد و کشورهای با کلید خارج از کاتالوگ هم باید فکتوری بازسازی شوند.
import asyncio
import types

import pytest
from telegram.error import BadRequest


class _FakeQuery:
    """کوئری تقلبی که قانون سخت تلگرام را رعایت می‌کند: پاسخ حداکثر ۲۰۰ کاراکتر."""

    def __init__(self):
        self.from_user = types.SimpleNamespace(id=999001)
        self.data = "admin:wipe_free_run"
        self.message = types.SimpleNamespace(photo=None)
        self.alerts = []
        self.edits = 0
        self.edit_texts = []

    async def answer(self, text=None, show_alert=False):
        self.alerts.append(text or "")
        if text and len(text) > 200:
            raise BadRequest("MESSAGE_TOO_LONG: text is too long")
        return True

    async def edit_message_text(self, *a, **k):
        self.edits += 1
        self.edit_texts.append(k.get("text") or (a[0] if a else ""))
        return True


def test_wipe_run_button_always_answers_within_telegram_limit(monkeypatch, tmp_path):
    from handlers import admin as admin_mod

    _fresh(monkeypatch, tmp_path, "wipe_btn.db")
    monkeypatch.setattr(admin_mod, "is_admin", lambda uid: True)

    # ۲۰ کشور کاتالوگی + ۵ کشور با کلید خارج از کاتالوگ (سفارشیِ ادمین)
    catalog_keys = [k for k in config.COUNTRIES if k != "un"][:20]
    assert len(catalog_keys) == 20
    for k in catalog_keys:
        db.create_country(0, "موقت", "🏳️", country_key=k)
    custom_names = {}
    for i in range(1, 6):
        key = f"custom_admin_country_{i}"
        name = f"شاهنشاهی سفارشیِ آزمایشی شماره‌ی {i} با نام بلند"
        custom_names[key] = name
        db.create_country(0, name, "🏳️", country_key=key)

    query = _FakeQuery()
    update = types.SimpleNamespace(callback_query=query)
    context = types.SimpleNamespace()

    # نباید هیچ استثنایی بالا بیاید (قبلاً BadRequest از query.answer می‌آمد)
    asyncio.run(admin_mod.admin_callback_handler(update, context))

    assert query.alerts, "ادمین باید بلافاصله بازخورد بگیرد"
    for text in query.alerts:
        assert len(text) <= 200, f"پاسخ {len(text)} کاراکتری سقف تلگرام را می‌شکند"
    assert any(text.startswith("✅") and "25" in text for text in query.alerts)
    assert query.edits >= 1, "پنل باید بعد از پاک‌سازی رفرش شود"

    # پنلِ بعد از پاک‌سازی نباید همان پنل قبل باشد: باید بنر موفقیت داشته باشد و
    # کشورهای تازه‌فکتوری با 🆕 مشخص شوند — وگرنه ادمین فکر می‌کند دکمه کار نکرد.
    panel = "\n".join(query.edit_texts)
    assert "پاک‌سازی کامل انجام شد" in panel, "پنل باید بنر موفقیت پاک‌سازی را نشان دهد"
    assert "25" in panel and "🆕" in panel, "کشورهای تازه‌ریست‌شده باید علامت 🆕 داشته باشند"

    # هر ۲۵ کشور فکتوری بازسازی شده‌اند و باز هم «باز» هستند (player_id=0)
    for k in catalog_keys + list(custom_names):
        row = db.get_country_by_key(k)
        assert row is not None, f"{k} باید بازسازی می‌شد"
        assert (row["player_id"] or 0) == 0
    # کشورهای خارج از کاتالوگ هم با نام اصلی خودشان بازسازی می‌شوند
    for key, name in custom_names.items():
        assert db.get_country_by_key(key)["name"] == name
