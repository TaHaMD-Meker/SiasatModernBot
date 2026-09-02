# -*- coding: utf-8 -*-
"""
دکمه‌ی دوم حذف کشور: «حذف مالکیت با حفظ تجهیزات» — مالک می‌رود، همه‌چیز می‌ماند
و کشور بلافاصله به استخر واگذاری (نفر بعدی با همان امکانات) می‌رود.
"""

import pytest
import config
import database as db
import country_queue as cq


def _fresh(monkeypatch, tmp_path, name):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()
    monkeypatch.setattr(config, "ADMIN_IDS", [42])


def test_detach_keeps_assets_and_frees_country(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "detach.db")
    conn = db.get_connection(); cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO countries (id, player_id, name, flag, country_key, treasury, gold) "
        "VALUES (1, 555, 'کشور آرین', '🦁', 'aryan', 77_000_000, 120)")
    conn.commit(); conn.close()

    ok, msg = cq.detach_country_keep_assets(1, actor="admin:42")
    assert ok

    c = db.get_country_by_id(1)
    assert c["player_id"] == 0, "مالکیت حذف شود"
    assert c["previous_player_id"] == 555
    assert c["quarantine_until"] is None, "مهلت بازپس‌گیری نباشد — استخر آزاد فوری"
    assert c["treasury"] == 77_000_000 and c["gold"] == 120, "دارایی‌ها دست‌نخورده"

    # بلافاصله در استخر واگذاری است
    free = {x["id"] for x in cq.get_free_countries()}
    assert 1 in free

    # صاحب قبلی حق بازپس‌گیری ندارد
    ok_r, msg_r, _ = cq.reclaim_country(555)
    assert not ok_r, "برخلاف قرنطینه، /reclaim نباید جواب دهد"


def test_detach_rejects_ownerless_and_missing(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "detach2.db")
    conn = db.get_connection(); cur = conn.cursor()
    cur.execute(
        "INSERT OR REPLACE INTO countries (id, player_id, name, flag, country_key, treasury) "
        "VALUES (2, 0, 'بی‌صاحب', '🏳️', 'free_c', 1000)")
    conn.commit(); conn.close()

    ok, msg = cq.detach_country_keep_assets(2)
    assert not ok and "بی‌صاحب" in msg
    ok2, _ = cq.detach_country_keep_assets(999)
    assert not ok2


# ─────────────────────────── source guards ───────────────────────────

def test_delete_confirm_page_has_both_options():
    src = open("handlers/admin.py", encoding="utf-8").read()
    assert 'admin:detachconfirm:' in src, "دکمه‌ی دوم در صفحه‌ی حذف"
    assert 'admin:detachfinal:' in src
    idx = src.index("admin:detachfinal:")
    window = src[idx:idx + 900]
    assert "rollback_transfers_from" in window, "ضدتقلب: برگشت انتقال‌های اخیر"
    assert "detach_country_keep_assets" in window


def test_router_index_safety():
    """درس list index out of range: فرمت سه‌تکه‌ی detach درست پارس شود."""
    for data, cid in [("admin:detachconfirm:7", 7), ("admin:detachfinal:9", 9)]:
        parts = data.split(":")
        assert parts[2] == str(cid)
    src = open("handlers/admin.py", encoding="utf-8").read()
    assert src.count('data.startswith("admin:detachconfirm:")') == 1
    assert src.count('data.startswith("admin:detachfinal:")') == 1
