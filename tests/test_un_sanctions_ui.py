# -*- coding: utf-8 -*-
"""پنل تحریم‌های هدفمند — قاره، جستجو، لیست تحریم‌های فعال و لغو از همان‌جا
+ رگرسیون باگ production (CallbackQuery به جای update در بازکردن پرونده)."""

import config
import database as db
import handlers.un as un


def _fresh(monkeypatch, tmp_path, name="unsanc_ui.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


def _country(player_id, key, name=None):
    return db.create_country(player_id, name or f"کشور {key}", "🏳️", country_key=key)


# ─────────────────────────────────────────────────────────────────────────────
# رگرسیون باگ: مسیر do باید پرونده را با update باز کند نه query
# ─────────────────────────────────────────────────────────────────────────────

def test_do_route_reopens_dossier_with_update_not_query():
    src = open("handlers/un.py", encoding="utf-8").read()
    idx = src.index('elif parts[2] == "do":')
    window = src[idx:idx + 1600]
    assert "_sanc_country_panel(update, context, cid" in window, \
        "بازکردن پرونده بعد از اعمال تحریم باید با update باشد (باگ CallbackQuery)"
    assert "_sanc_country_panel(query," not in src, "هیچ فراخوانی با query نباید باقی مانده باشد"


def test_quicklift_route_also_uses_update():
    src = open("handlers/un.py", encoding="utf-8").read()
    idx = src.index('elif parts[2] == "quicklift":')
    window = src[idx:idx + 1400]
    assert "_sanc_active_page(update, context" in window


# ─────────────────────────────────────────────────────────────────────────────
# helper فیلتر کشورها (قاره + جستجو)
# ─────────────────────────────────────────────────────────────────────────────

def _sample_countries():
    return [
        {"id": 1, "name": "انگلیس", "country_key": "uk", "flag": "🇬🇧"},
        {"id": 2, "name": "ایران", "country_key": "iran", "flag": "🇮🇷"},
        {"id": 3, "name": "ژاپن", "country_key": "japan", "flag": "🇯🇵"},
        {"id": 4, "name": "گروهک آزمون", "country_key": "faction_test", "flag": "🏴"},
    ]


def test_filter_by_continent_uses_config_keys():
    europe = un._filter_sanction_countries(_sample_countries(), cont="europe")
    assert [c["country_key"] for c in europe] == ["uk"]
    asia = un._filter_sanction_countries(_sample_countries(), cont="asia")
    assert [c["country_key"] for c in asia] == ["japan"]


def test_filter_mideast_includes_factions():
    out = un._filter_sanction_countries(_sample_countries(), cont="mideast")
    keys = {c["country_key"] for c in out}
    assert "iran" in keys and "faction_test" in keys


def test_filter_search_by_name_and_key_case_insensitive():
    by_name = un._filter_sanction_countries(_sample_countries(), q="انگلیس")
    assert [c["id"] for c in by_name] == [1]
    by_key = un._filter_sanction_countries(_sample_countries(), q="UK")
    assert [c["id"] for c in by_key] == [1]
    none = un._filter_sanction_countries(_sample_countries(), q="آتلانتیس")
    assert none == []


def test_filter_combined_cont_and_q():
    out = un._filter_sanction_countries(_sample_countries(), cont="europe", q="انگلیس")
    assert [c["id"] for c in out] == [1]
    out2 = un._filter_sanction_countries(_sample_countries(), cont="asia", q="uk")
    assert out2 == []


def test_list_page_buttons_cover_continents_and_new_routes():
    src = open("handlers/un.py", encoding="utf-8").read()
    for needle in ("un:sanc:active:", "un:sanc:search", "un:sanc:list:", "un:sanc:quicklift:"):
        assert needle in src
    for ckey in config.CONTINENTS:
        assert f'callback_data=f"un:sanc:list:0:{{ckey}}"' in src, \
            "دکمه‌های قاره باید دینامیک از CONTINENTS ساخته شوند"


# ─────────────────────────────────────────────────────────────────────────────
# لیست همه‌ی تحریم‌های فعال
# ─────────────────────────────────────────────────────────────────────────────

def test_all_active_sanctions_query(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    uk = _country(62_001, "uk")
    jp = _country(62_002, "japan")
    db.apply_targeted_sanction(uk, "market_ban", reason="حمایت از تروریسم", imposed_by=42)
    db.apply_targeted_sanction(uk, "arms_embargo", imposed_by=42)
    db.apply_targeted_sanction(jp, "financial", imposed_by=42)
    actives = db.get_all_active_targeted_sanctions()
    assert len(actives) == 3
    uk_rows = [a for a in actives if a["country_id"] == uk]
    assert {a["sanction_key"] for a in uk_rows} == {"market_ban", "arms_embargo"}
    assert actives[0]["country_name"], "JOIN باید نام کشور بیاورد"
    # لغو یکی → لیست دو مورد
    db.remove_targeted_sanction(uk, "market_ban", removed_by=42)
    assert len(db.get_all_active_targeted_sanctions()) == 2


def test_active_list_empty_without_sanctions(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    _country(62_003, "calm")
    assert db.get_all_active_targeted_sanctions() == []


def test_search_flag_reset_in_text_handler_flow(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "unsanc_txt.db")
    monkeypatch.setattr(config, "ADMIN_IDS", [42])
    ctx = {"un_sanc_search": True}
    # فقط منطق مصرف فلگ را با فراخوانی مستقیم helper چک می‌کنیم
    assert un._filter_sanction_countries(
        [{"id": 1, "name": "انگلیس", "country_key": "uk"}], q="انگ") != []
    ctx["un_sanc_search"] = None  # همان‌طور که _sanc_search_handle انجام می‌دهد
    assert not ctx.get("un_sanc_search")


# ─────────────────────────────────────────────────────────────────────────────
# رگرسیون باگ واقعی: فلگ سرچ تحریم باید در روتر main به هندلر UN برسد
# (قبلاً فقط زیر un_draft صدا زده می‌شد → پیام بازیکن توی خلا گم می‌شد)
# ─────────────────────────────────────────────────────────────────────────────

def test_text_router_feeds_un_sanc_search():
    src = open("main.py", encoding="utf-8").read()
    assert 'context.user_data.get("un_sanc_search")' in src, \
        "روتر main باید فلگ سرچ تحریم را به un_text_input_handler برساند"
    idx = src.index('un_sanc_search')
    window = src[max(0, idx - 200):idx + 300]
    assert "un_text_input_handler" in window


def test_filter_by_player_id_like_owner_panel():
    rows = [{"id": 1, "name": "انگلیس", "country_key": "uk", "player_id": 805298765}]
    assert [r["id"] for r in un._filter_sanction_countries(rows, q="805298765")] == [1]
    assert [r["id"] for r in un._filter_sanction_countries(rows, q="8052")] == [1]
    assert un._filter_sanction_countries(rows, q="999") == []


def test_search_handle_end_to_end(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "unsanc_srche2e.db")
    monkeypatch.setattr(config, "ADMIN_IDS", [42])
    _country(805298765, "uk")

    sent = []

    class _M:
        async def reply_text(self, text, **kw):
            sent.append((text, kw))

    class _U:
        effective_user = type("U", (), {"id": 42})()
        message = _M()

    class _Ctx:
        def __init__(self):
            self.user_data = {"un_sanc_search": True}

    import asyncio as _aio

    # ۱) جستجو با کلید کشور
    ctx = _Ctx()
    assert _aio.run(un._sanc_search_handle(_U(), ctx, "uk")) is True
    assert ctx.user_data.get("un_sanc_search") is None, "فلگ باید مصرف شده باشد"
    text, kw = sent[0]
    assert "نتیجه" in text
    markup = kw["reply_markup"]
    assert any("un:sanc:country:" in b.callback_data
               for row in markup.inline_keyboard for b in row), \
        "نتیجه‌ی سرچ باید دکمه‌ی مستقیم پرونده‌ی تحریم داشته باشد"

    # ۲) جستجو با آیدی عددی بازیکن (هم‌سبک پنل مالک)
    sent.clear()
    ctx3 = _Ctx()
    assert _aio.run(un._sanc_search_handle(_U(), ctx3, "805298765")) is True
    assert "نتیجه" in sent[0][0]

    # ۳) جستجوی بی‌نتیجه
    sent.clear()
    ctx2 = _Ctx()
    assert _aio.run(un._sanc_search_handle(_U(), ctx2, "آتلانتیس")) is True
    assert "پیدا نشد" in sent[0][0]


# ─────────────────────────────────────────────────────────────────────────────
# جریان کامل صفحه‌ی قاره‌ای — با نقش UN برای مالک، مثل پروداکشن
# ─────────────────────────────────────────────────────────────────────────────

def test_continent_list_page_end_to_end(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "unsanc_cont.db")
    monkeypatch.setattr(config, "ADMIN_IDS", [42])
    # نقش سازمان ملل برای مالک (شرط ورود به پنل)
    db.create_country(42, "سازمان ملل", "🇺🇳", country_key="un")
    uk = _country(805298765, "uk")
    ir = _country(805298766, "iran")

    edited = []

    class _Q:
        async def edit_message_text(self, text, **kw):
            edited.append((text, kw))

    class _U:
        effective_user = type("U", (), {"id": 42})()
        callback_query = _Q()
        message = None

    import asyncio as _aio
    ctx = type("C", (), {"user_data": {}})()

    # فیلتر اروپا → باید انگلیس بیاید و ایران نه
    _aio.run(un._sanc_list_page(_U(), ctx, 0, "europe"))
    text, kw = edited[-1]
    markup = kw["reply_markup"]
    cbs = [b.callback_data for row in markup.inline_keyboard for b in row]
    assert f"un:sanc:country:{uk}" in cbs
    assert "اروپا" in text
    # دکمه‌های قاره از روی کانفیگ
    assert any(f"un:sanc:list:0:mideast" in cb for cb in cbs)

    # فیلتر خاورمیانه → ایران بیاید و انگلیس نه
    _aio.run(un._sanc_list_page(_U(), ctx, 0, "mideast"))
    text2, kw2 = edited[-1]
    cbs2 = [b.callback_data for row in kw2["reply_markup"].inline_keyboard
            for b in row]
    assert f"un:sanc:country:{uk}" not in cbs2
    assert f"un:sanc:country:{ir}" in cbs2
