# -*- coding: utf-8 -*-
"""درخواست مالک: به‌جای متن بلند در گزارش روزانه، یک «دکمه» جزئیات خاموشی را باز کند.

طرح نهایی:
• متن گزارش روزانه کوتاه می‌ماند (کسری + خاموش‌ها + دوز نجات) و Markdown است.
• زیر گزارش روزانه، دکمه‌ی «🏭 چرا سازه‌ها خاموش شدند؟» می‌آید (callback upkeep_why:).
• کلیک روی دکمه → پیام جزئیات کامل: چرا این سازه (کم‌بازده‌ترین)، مصرف روزانه‌ی
  هر واحدش، انبار در برابر نیاز روزانه و دقیقاً چقدر منبع بیشتر لازم است.
• نتیجه‌ی آخرین چرخه در DB ذخیره می‌شود؛ فقط رهبر همان کشور یا ادمین می‌بیند.
"""
import asyncio
import json
import types

import config
import database as db


def _fresh(monkeypatch, tmp_path, name="upkeep_btn.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()
    cid = db.create_country(7001, "مالزی", "🇲🇾", country_key="malaysia")
    db.update_country_field(cid, "treasury", 50_000_000)
    db.update_country_field(cid, "iron_ore", 10)  # عمداً ناچیز → کسری آهن
    conn = db.get_connection()
    with conn:
        conn.execute("INSERT INTO equipment (country_id, item_key, quantity) VALUES (?,?,1)",
                     (cid, "industrial_complex"))
    conn.close()
    return cid


def test_short_report_stays_compact_but_markdown(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    res = db.apply_building_upkeep(db.get_country_by_player(7001)["id"])
    assert res["shut_down"]

    text = db.format_upkeep_report(res)
    assert "<b>" not in text and "</b>" not in text, "تگ HTML خام در پیام Markdown می‌شکند"
    assert "کمبود منابع" in text and "خاموش" in text
    # جزئیات «چرا» دیگر داخل متن نیست — پشت دکمه است
    assert "چرا؟" not in text and "مصرف روزانه‌ی هر واحدش" not in text


def test_result_is_persisted_for_the_button(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = db.get_country_by_player(7001)["id"]
    db.apply_building_upkeep(cid)

    saved = db.get_saved_upkeep_report(cid)
    assert saved, "نتیجه‌ی چرخه باید برای دکمه ذخیره شود"
    assert saved["shut_down"], "خاموشی ذخیره‌شده باید در دسترس باشد"
    assert saved["shut_down"][0]["consumption"].get("iron_ore", 0) > 0
    assert saved["supply_line"]["iron_ore"]["need"] > 0


def test_details_view_explains_why(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = db.get_country_by_player(7001)["id"]
    db.apply_building_upkeep(cid)
    saved = db.get_saved_upkeep_report(cid)

    text = db.format_upkeep_details(saved)

    assert "<b>" not in text
    assert "چرا؟" in text and "کم‌بازده" in text
    assert "مصرف روزانه" in text
    assert "انبار" in text and "نیاز روزانه" in text
    assert "برای روشن‌ماندن همه" in text
    assert "آهن و فولاد" in text


def test_daily_report_has_the_details_button(monkeypatch, tmp_path):
    src = open("main.py", encoding="utf-8").read()
    assert 'callback_data=f"upkeep_why:{c[\'id\']}"' in src or "upkeep_why:" in src, \
        "گزارش روزانه باید دکمه‌ی جزئیات خاموشی داشته باشد"
    assert 'pattern=r"^upkeep_why:"' in src, "هندلر دکمه باید ثبت شود"


def test_button_callback_owner_only_and_renders(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = db.get_country_by_player(7001)["id"]
    db.apply_building_upkeep(cid)

    from main import upkeep_why_callback

    class _Bot:
        def __init__(self):
            self.sent = []

        async def send_message(self, chat_id, text, **k):
            self.sent.append((chat_id, text))

    async def _click(uid):
        q = types.SimpleNamespace(
            from_user=types.SimpleNamespace(id=uid),
            data=f"upkeep_why:{cid}",
            alerts=[])
        async def _answer(*a, **k):
            q.alerts.append(a[0] if a else k.get("text") or "")
        q.answer = _answer
        update = types.SimpleNamespace(callback_query=q)
        ctx = types.SimpleNamespace(bot=_Bot())
        await upkeep_why_callback(update, ctx)
        return q, ctx

    # رهبر کشور: جزئیات برایش ارسال می‌شود
    q1, ctx1 = asyncio.run(_click(7001))
    assert ctx1.bot.sent, "رهبر باید پیام جزئیات بگیرد"
    assert "چرا؟" in ctx1.bot.sent[0][1]

    # غریبه: پیام نمی‌گیرد
    q2, ctx2 = asyncio.run(_click(999999))
    assert not ctx2.bot.sent, "غریبه نباید جزئیات را ببیند"

    # کشور بدون رویداد: پیام «چیزی ثبت نشده»
    cid2 = db.create_country(7002, "عمان", "🇴🇲", country_key="oman")
    q3, ctx3 = _click_click_alt(cid2)

    assert not ctx3.bot.sent


def _click_click_alt(cid):
    from main import upkeep_why_callback

    async def _go():
        q = types.SimpleNamespace(
            from_user=types.SimpleNamespace(id=7002),
            data=f"upkeep_why:{cid}", alerts=[])
        async def _answer(*a, **k):
            q.alerts.append(a[0] if a else k.get("text") or "")
        q.answer = _answer
        update = types.SimpleNamespace(callback_query=q)
        ctx = types.SimpleNamespace(bot=types.SimpleNamespace(send_message=_no_send, sent=[]))
        await upkeep_why_callback(update, ctx)
        return q, ctx

    return asyncio.run(_go())


async def _no_send(*a, **k):
    raise AssertionError("برای کشور بدون رویداد نباید پیام جزئیات برود")
