# -*- coding: utf-8 -*-
"""قرنطینه کلاً حذف شده: خلع = آزاد فوری. پنل صف، کشورهای بی‌صاحب را نشان می‌دهد."""

import pytest
import config
import database as db
import country_queue as cq


def _fresh(monkeypatch, tmp_path, name="qfree.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


def test_revoked_country_is_instantly_free(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = db.create_country(1001, "کشور خلعی", "🏳️", country_key="instant_q_c")
    ok, msg = cq.quarantine_country(cid)
    assert ok
    assert any(c["id"] == cid for c in cq.get_free_countries()), \
        "کشور لغوشده باید همان لحظه در استخر واگذاری باشد"
    assert cq.get_quarantined_countries() == []
    assert cq.release_all_quarantines() == (0, [])


def test_panel_shows_free_countries_and_retired_buttons():
    src = open("handlers/admin.py", encoding="utf-8").read()
    assert "کشورهای بی‌صاحبِ آماده‌ی واگذاری" in src, "پنل باید بی‌صاحب‌ها را نشان دهد"
    assert "آزادسازی همه‌ی قرنطینه‌ها" not in src.split("def show_queue_panel")[1], \
        "دکمه‌های منسوخ قرنطینه نباید در پنل رندر شوند"
    idx = src.index('data.startswith("admin:q_release:")')
    window = src[idx:idx + 300]
    assert "حذف شده" in window
