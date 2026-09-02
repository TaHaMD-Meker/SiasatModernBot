# -*- coding: utf-8 -*-
"""
سقف تجارت روزانه (همان ۳/۳ بازیکنان) — قابل تنظیم دستی برای هر کشور از پرونده‌ی
کشور در پنل مالک. اورراید مالک بر فرمول زیرساخت اولویت دارد.
"""

import pytest
import config
import database as db


def _fresh(monkeypatch, tmp_path, name):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


def _country(tmp_path, monkeypatch, name, key):
    _fresh(monkeypatch, tmp_path, name + ".db")
    return db.create_country(7001, name, "🏳️", country_key=key)


# ─────────────────────────── behavioral ───────────────────────────

def test_default_formula_limits(monkeypatch, tmp_path):
    cid = _country(tmp_path, monkeypatch, "کشور فابریک", "fabric_tl")
    assert db.get_trade_mode_daily_limit(cid, "sea") == 2
    assert db.get_trade_mode_daily_limit(cid, "land") == 2
    assert db.get_trade_mode_daily_limit(cid, "air") == 2
    assert db.get_trade_mode_daily_limit(cid, "caspian") == 1


def test_override_wins_over_formula(monkeypatch, tmp_path):
    cid = _country(tmp_path, monkeypatch, "کشور اورراید", "override_tl")
    assert db.set_trade_limit_override(cid, "sea", 5)
    assert db.get_trade_mode_daily_limit(cid, "sea") == 5, "اورراید مالک باید ملاک باشد"
    assert db.get_trade_mode_daily_limit(cid, "air") == 2, "بقیه روش‌ها فرمولی می‌مانند"

    assert db.set_trade_limit_override(cid, "sea", None)
    assert db.get_trade_mode_daily_limit(cid, "sea") == 2, "reset باید به فرمول برگردد"


def test_clamp_and_invalid_mode(monkeypatch, tmp_path):
    cid = _country(tmp_path, monkeypatch, "کشور کلمپ", "clamp_tl")
    db.set_trade_limit_override(cid, "air", 999)
    assert db.get_trade_limit_override(cid)["air"] == 50, "سقف بالایی ۵۰"
    db.set_trade_limit_override(cid, "air", -3)
    assert db.get_trade_limit_override(cid)["air"] == 0, "کف صفر"
    assert db.set_trade_limit_override(cid, "teleport", 5) is False


def test_check_trade_mode_limit_respects_override(monkeypatch, tmp_path):
    """با سقف دستی ۳، چهارمین معامله‌ی دریایی باید بلاک شود؛ با صفر هیچ."""
    cid = _country(tmp_path, monkeypatch, "کشور بودجه", "budget_tl")
    db.set_trade_limit_override(cid, "sea", 3)
    for _ in range(3):
        can, _ = db.check_trade_mode_limit(cid, "sea")
        assert can
        db.bump_trade_mode_day_count(cid, "sea")
    can, msg = db.check_trade_mode_limit(cid, "sea")
    assert not can and msg  # پیام راهنما

    db.set_trade_limit_override(cid, "sea", 0)
    can, _ = db.check_trade_mode_limit(cid, "sea")
    assert not can, "سقف صفر = ممنوعیت کامل این روش"


# ─────────────────────────── source guards ───────────────────────────

def test_dashboard_has_trade_limits_button():
    src = open("handlers/admin_dossier.py", encoding="utf-8").read()
    assert 'callback_data=f"admin:tl:{c[' + "'" + 'id' + "'" + ']}"' in src
    assert "async def show_trade_limits" in src
    assert "update.callback_query.edit_message_text" not in src.split("def show_trade_limits")[1], \
        "پارامتر query همان query است — الگوی query.edit_message_text"


def test_route_parses_format_correctly():
    """فرمت دکمه: admin:tl:<cid>:<mode>:<action> — درس list index out of range."""
    parts = "admin:tl:12:sea:inc".split(":")
    assert parts[2] == "12" and parts[3] == "sea" and parts[4] == "inc"
    parts2 = "admin:tl:12".split(":")
    assert parts2[2] == "12" and len(parts2) == 3

    src = open("handlers/admin.py", encoding="utf-8").read()
    idx = src.index('data.startswith("admin:tl:")')
    window = src[idx:idx + 1200]
    assert "parts[2]" in window and "parts[3]" in window and "parts[4]" in window
    assert "show_trade_limits(query, context, c_id" in window, \
        "روتر باید query را مستقیم پاس دهد (نه query.callback_query)"
    assert "show_trade_limits(query.callback_query" not in src


def test_player_limit_message_uses_effective_limit():
    """پیام مسدودی بازیکن باید همان سقف مؤثر (اوررایدشده) را نشان دهد."""
    src = open("database.py", encoding="utf-8").read()
    assert "get_trade_mode_budget" in src and "get_trade_mode_daily_limit" in src


# ─────────────────────────────────────────────────────────────────────────────
# سقف کل محموله‌های خروجی (همان «امروز 3/3 محموله ارسال کرده‌اید») — قابل تنظیم
# ─────────────────────────────────────────────────────────────────────────────

def test_total_shipment_override_changes_budget(monkeypatch, tmp_path):
    cid = _country(tmp_path, monkeypatch, "کشور کل", "total_tl")
    used, cap = db.transfer_daily_budget(cid)
    assert cap == config.TRANSFER_DAILY_SHIPMENTS == 3

    assert db.set_trade_limit_override(cid, "total", 7)
    assert db.transfer_daily_budget(cid)[1] == 7, "پیام ۳/۳ باید عدد دستی را نشان دهد"

    db.set_trade_limit_override(cid, "total", None)
    assert db.transfer_daily_budget(cid)[1] == 3, "♻️ به پیش‌فرض کانفیگ برگردد"


def test_zero_total_blocks_all_outbound(monkeypatch, tmp_path):
    cid = _country(tmp_path, monkeypatch, "کشور قفل کل", "zero_total")
    db.set_trade_limit_override(cid, "total", 0)
    used, cap = db.transfer_daily_budget(cid)
    assert cap == 0 and used >= cap


def test_panel_has_total_row():
    src = open("handlers/admin_dossier.py", encoding="utf-8").read()
    assert "کل محموله‌های خروجی در روز" in src
    assert "admin:tl:{country_id}:total:inc" in src or "admin:tl:{country_id}:total:dec" in src
