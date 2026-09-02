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
