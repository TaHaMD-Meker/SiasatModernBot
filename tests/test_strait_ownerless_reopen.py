"""باگ گزارش‌شده: تنگه‌ی بسته بعد از رفتن پلیر باز نمی‌شود.

قاعده: تنگه ابزار اقتدار یک بازیکن است — کشور بی‌صاحب یا حذف‌شده نمی‌تواند
تنگه‌ای را بسته/عوارضی نگه دارد؛ sweep باید فوراً بازگشایی کند.
"""
import importlib

import pytest

import config


def _fresh(monkeypatch, tmp_path, name="straits.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    import database as db
    importlib.reload(db)
    db.init_db()
    return db


def _navy(db, cid, units=6, price=3_000_000):
    """ناوگانِ واجد شرایط تنگه (≥۵ فروند و ≥۱۰M دلار) می‌سازد."""
    conn = db.get_connection()
    with conn:
        conn.execute(
            "INSERT INTO country_assets (country_id, country_key, category, equipment_name,"
            " equipment_key, amount, buy_price) VALUES (?,'iran','Navy','ناوچه آزمون',"
            "'test_frigate',?,?)",
            (cid, units, price))
    conn.close()


def test_detached_owner_cannot_keep_strait_blocked(monkeypatch, tmp_path):
    """پلیر می‌رود (مالکیت صفر ولی ناوگان سر جایش) → تنگه باید باز شود."""
    db = _fresh(monkeypatch, tmp_path)
    cid = db.create_country(8801, "ایران", "🇮🇷", country_key="iran")
    _navy(db, cid)
    db.set_strait_status("hormuz", "blocked")
    assert db.get_strait_status("hormuz")["status"] == "blocked"

    # لغو مالکیت با حفظ تجهیزات
    import country_queue
    importlib.reload(country_queue)
    ok, msg = country_queue.detach_country_keep_assets(cid)
    assert ok, msg

    # ۱) detach خودش بلافاصله بازگشایی کرده باشد
    assert db.get_strait_status("hormuz")["status"] == "open", (
        "بعد از لغو مالکیت، تنگه باید همان لحظه باز شود")

    # ۲) مسیر sweep مستقل: وضعیت میراثیِ بسته‌ی کشور بی‌صاحب را بازگشایی کند
    db.set_strait_status("hormuz", "toll", 3_000_000)
    reopened = db.auto_check_and_reopen_straits_if_navy_destroyed()
    keys = [r["strait_info"]["strait_key"] for r in reopened]
    assert "hormuz" in keys, "تنگه‌ی کشور بی‌صاحب باید بازگشایی شود"
    assert db.get_strait_status("hormuz")["status"] == "open"


def test_deleted_owner_cannot_keep_strait_blocked(monkeypatch, tmp_path):
    """کشور کاملاً حذف شده → تنگه‌اش نباید برای همیشه بسته بماند."""
    db = _fresh(monkeypatch, tmp_path)
    cid = db.create_country(8802, "عمان", "🇴🇲", country_key="oman")
    _navy(db, cid)
    db.set_strait_status("hormuz_south", "toll", 2_000_000)

    db.delete_country_by_id(cid)
    assert db.get_country_by_key("oman") is None

    reopened = db.auto_check_and_reopen_straits_if_navy_destroyed()
    keys = [r["strait_info"]["strait_key"] for r in reopened]
    assert "hormuz_south" in keys
    st = db.get_strait_status("hormuz_south")
    assert st["status"] == "open" and int(st["toll"]) == 0


def test_active_owner_with_navy_keeps_control(monkeypatch, tmp_path):
    """کشور صاحب‌دار با ناوگان معتبر همچنان حق کنترل تنگه را دارد."""
    db = _fresh(monkeypatch, tmp_path)
    cid = db.create_country(8803, "ایران", "🇮🇷", country_key="iran")
    _navy(db, cid)
    db.set_strait_status("hormuz", "blocked")

    db.auto_check_and_reopen_straits_if_navy_destroyed()
    assert db.get_strait_status("hormuz")["status"] == "blocked"
