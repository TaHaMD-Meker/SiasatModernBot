# -*- coding: utf-8 -*-
"""درخواست مالک: در «🏛️ سیاست داخلی» باید دکمه‌ای باشد که ساختار سازه‌های کشور
را نشان دهد — کدام‌ها خاموش‌اند (🔴) و کدام روشن (🟢) — و با کلیک روی هر
سازه‌ی خاموش، دلیل کاملش (چرا؟ کم‌بازده‌ترین بودن، مصرف، انبار/نیاز، دوز رفع)
باز شود.

دسترسی: dom:buildings (صفحه‌ی فهرست) و dom:bwhy:<key> (جزئیات یک سازه).
منبع داده: آخرین چرخه‌ی نگهداری ذخیره‌شده (db.get_saved_upkeep_report) +
وضعیت لحظه‌ای equipment.inactive_qty.
"""
import asyncio
import types

import config
import database as db
from handlers import internal_affairs as ia_mod


def _fresh(monkeypatch, tmp_path, name="dom_bld.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()
    cid = db.create_country(7100, "مالزی", "🇲🇾", country_key="malaysia")
    db.update_country_field(cid, "treasury", 50_000_000)
    # نفت صفر → همه‌ی نفت‌خورها (مجتمع صنعتی + کارخانه متوسط) خاموش می‌شوند؛
    # نیروگاه بادی فقط آهن می‌خواهد → با آهن فراوان روشن می‌ماند.
    db.update_country_field(cid, "oil_reserves", 0)
    db.update_country_field(cid, "iron_ore", 9_000_000)
    conn = db.get_connection()
    with conn:
        conn.execute("INSERT INTO equipment (country_id, item_key, quantity) VALUES (?,?,1)",
                     (cid, "industrial_complex"))
        conn.execute("INSERT INTO equipment (country_id, item_key, quantity) VALUES (?,?,3)",
                     (cid, "medium_factory"))
        conn.execute("INSERT INTO equipment (country_id, item_key, quantity) VALUES (?,?,2)",
                     (cid, "wind_plant"))
    conn.close()
    db.apply_building_upkeep(cid)
    return cid


class _FakeQuery:
    def __init__(self, data, uid=7100):
        self.from_user = types.SimpleNamespace(id=uid)
        self.data = data
        self.alerts = []
        self.edits = []

    async def answer(self, text=None, show_alert=False):
        self.alerts.append(text or "")

    async def edit_message_text(self, *a, **k):
        self.edits.append({"text": k.get("text") or (a[0] if a else ""),
                           "markup": k.get("reply_markup")})


def _buttons(markup):
    out = []
    if markup is None:
        return out
    for row in getattr(markup, "inline_keyboard", []):
        for btn in row:
            out.append((btn.text, btn.callback_data))
    return out


def _click(update_parts, uid=7100):
    q = _FakeQuery(update_parts, uid)
    update = types.SimpleNamespace(callback_query=q,
                                   effective_user=types.SimpleNamespace(id=uid))
    ctx = types.SimpleNamespace(bot=types.SimpleNamespace(send_message=None))
    asyncio.run(ia_mod.domestic_callback_handler(update, ctx))
    return q


def test_domestic_menu_has_buildings_button(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    kb = ia_mod._menu_keyboard(0, 0)
    pairs = [(b.text, b.callback_data) for row in kb.inline_keyboard for b in row]
    assert any("سازه" in t and cb == "dom:buildings" for t, cb in pairs), \
        "منوی سیاست داخلی باید دکمه‌ی وضعیت سازه‌ها داشته باشد"


def test_buildings_page_lists_on_and_off(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    q = _click("dom:buildings")

    assert q.edits, "صفحه‌ی سازه‌ها باید رندر شود"
    text = "\n".join(e["text"] for e in q.edits)
    assert "🔴" in text and "مجتمع عظیم صنعتی" in text, "خاموش باید لیست شود"
    assert "🟢" in text and "نیروگاه بادی" in text, "روشن هم باید لیست شود"
    pairs = _buttons(q.edits[-1]["markup"])
    assert any(cb == "dom:bwhy:industrial_complex" for _, cb in pairs), \
        "روی هر سازه‌ی خاموش باید دکمه‌ی «چرا؟» باشد"
    assert any(cb == "dom:menu" for _, cb in pairs), "باید دکمه‌ی بازگشت داشته باشد"


def test_building_why_view_shows_full_reason(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    q = _click("dom:bwhy:industrial_complex")

    assert q.edits, "نمای چرا باید رندر شود"
    text = "\n".join(e["text"] for e in q.edits)
    assert "مجتمع عظیم صنعتی" in text
    assert "چرا؟" in text and "کم‌بازده" in text, "دلیل انتخاب باید توضیح داده شود"
    assert "مصرف روزانه" in text, "مصرف روزانه‌ی سازه باید بیاید"
    assert "انبار" in text and "نیاز روزانه" in text, "انبار در برابر نیاز باید بیاید"
    assert "برای روشن‌ماندن همه" in text, "دوز رفع کسری باید بیاید"
    assert any(cb == "dom:buildings" for _, cb in _buttons(q.edits[-1]["markup"])), \
        "باید دکمه‌ی بازگشت به فهرست سازه‌ها باشد"


def test_building_why_for_running_building_is_polite(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    q = _click("dom:bwhy:wind_plant")
    # روتر یک‌بار answer خالی کرده؛ پیام حالت خاص باید با edit بیاید نه answer دوم
    assert q.edits, "باید صفحه با پیام حالت خاص رندر شود"
    text = "\n".join(e["text"] for e in q.edits)
    assert "روشن" in text and "نیروگاه بادی" in text
    assert any(cb == "dom:buildings" for _, cb in _buttons(q.edits[-1]["markup"]))
