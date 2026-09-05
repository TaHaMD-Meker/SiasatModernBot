# -*- coding: utf-8 -*-
"""باگ گزارش مالک: «موقع تایید فیش گروهک یکی این میاد:
❌ خطا: خطا در تایید پرداخت: UNIQUE constraint failed: countries.country_key»

ریشه: شاخه‌ی militia در تایید فیش هیچ چکی روی کلید کشور ندارد؛ اگر
• گروهک ازپیش‌تعریف‌شده (faction_sepah…) به بازیکن دیگری رسیده باشد
  (دو فیش هم‌زمان قبل از تایید هر دو، فروشگاه هر دو را آزاد نشان داده بود)، یا
• کلید faction_{player_id} با ردیف یتیم/بازواگذاری‌شده اشغال باشد،
INSERT خام روی قید UNIQUE می‌ترکد و متن SQL به ادمین نشان داده می‌شود.

قرارداد:
• تاییدِ فیشِ گروهکِ تکراری = پیام فارسی تمیز (نه کرش) — ادمین فیش را رد می‌کند.
• خرید مجدد گروهکِ خودِ بازیکن = جایگزینی (رفتار قبلی، حفظ شود).
• کلید id-محور اشغال‌شده توسط ردیف دیگر = کلید آزادِ پسونددار، بدون دست‌زدن
  به ردیف غریبه.
"""
import asyncio
import json

import config
import database as db


def _fresh(monkeypatch, tmp_path, name="militia.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


def _receipt(player_id, faction_key=None, name="گروه آزمون"):
    """ثبت یک فیش پرداخت ماقبل‌تایید (militia) — مثل مسیر واقعی خرید."""
    payload = {"name": name, "flag": "🏴‍☠️"}
    if faction_key:
        payload["faction_key"] = faction_key
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO payment_requests
                (player_id, item_type, plan_title, amount_toman, tracking_code,
                 custom_payload, status, created_at)
                VALUES (?, 'militia', 'گروه غیردولتی', 100000, ?, ?, 'pending', '2026-01-01')
            """, (player_id, f"TRK-{player_id}-{faction_key}", json.dumps(payload, ensure_ascii=False)))
            return cur.lastrowid
    finally:
        conn.close()


def _approve(req_id):
    return db.approve_payment_request(req_id, 999)


# ───────────── ۱) گروهک ازپیش‌تعریف‌شده‌ی گرفته‌شده → پیام تمیز، نه کرش ─────────────

def test_predefined_faction_taken_by_other_returns_clean_error(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    ra = _receipt(8700, faction_key="sepah", name="قدس الف")
    ok_a, msg_a, _p = _approve(ra)
    assert ok_a, msg_a

    rb = _receipt(8701, faction_key="sepah", name="قدس ب")
    ok_b, msg_b, _p2 = _approve(rb)
    assert not ok_b, "فیش دوم برای گروهک گرفته‌شده نباید تایید شود"
    assert "UNIQUE" not in msg_b and "constraint" not in msg_b.lower(), \
        f"متن خام SQL به ادمین نشان داده نشود: {msg_b}"
    assert "قبلاً" in msg_b, "پیام فارسی تمیز: گروهک قبلاً واگذار شده"

    # بازیکن اول دست‌نخورده
    a_row = db.get_country_by_player(8700)
    assert a_row and a_row["country_key"] == "faction_sepah"


# ───────────── ۲) خرید مجدد گروهک خودی = جایگزینی ─────────────

def test_repurchasing_own_militia_replaces_it(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "militia2.db")
    r1 = _receipt(8710, faction_key="sepah", name="نخست")
    ok1, msg1, _ = _approve(r1)
    assert ok1, msg1
    old_id = db.get_country_by_player(8710)["id"]

    r2 = _receipt(8710, faction_key="sepah", name="دوم")
    ok2, msg2, p2 = _approve(r2)
    assert ok2, msg2

    conn = db.get_connection()
    rows = conn.execute(
        "SELECT id, name FROM countries WHERE player_id=8710 AND country_key LIKE 'faction_%'").fetchall()
    conn.close()
    assert len(rows) == 1, "فقط یک گروهک برای بازیکن"
    assert rows[0]["name"] == "دوم", "نسخه‌ی جدید جایگزین شده"


# ───────────── ۳) کلید id-محور اشغال‌شده توسط ردیف غریبه → پسوند آزاد ─────────────

def test_squatted_id_key_falls_back_to_free_suffix(monkeypatch, tmp_path, ):
    _fresh(monkeypatch, tmp_path, "militia3.db")
    # ردیف غریبه: کشورِ بازواگذاری‌شده با کلید faction_8720 ولی مالک ۸۷۱۱
    conn = db.get_connection()
    with conn:
        conn.execute("""
            INSERT INTO countries (player_id, name, flag, country_key, population, treasury)
            VALUES (8711, 'کشور واگذارشده', '🏳️', 'faction_8720', 1000000, 1000000)
        """)
    conn.close()

    r = _receipt(8720, name="گروه تازه")
    ok, msg, p = _approve(r)
    assert ok, msg

    squatted = db.get_country_by_player(8711)
    assert squatted and squatted["country_key"] == "faction_8720", "ردیف غریبه دست نخورد"

    mine = db.get_country_by_player(8720)
    assert mine and mine["country_key"].startswith("faction_8720"), \
        "کلید آزاد (پسونددار) برای خریدار"


# ───────────── ۴) مسیر اعطای ادمین هم همین قرارداد را دارد ─────────────

def test_admin_grant_militia_with_taken_predefined_also_clean(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "militia4.db")
    r1 = _receipt(8730, faction_key="sepah", name="الف")
    ok1, msg1, p1 = _approve(r1)
    assert ok1, msg1

    # کشورِ بازیکن دوم — اعطای همان گروهکِ گرفته‌شده به او باید تمیز رد شود
    cid_b = db.create_country(8731, "بلاد ب", "🏳️", country_key="bladia_m")
    db.update_country_field(cid_b, "player_id", 8731)
    payload = {"name": "ب", "flag": "🏴‍☠️", "faction_key": "sepah"}
    ok2, err2 = db.admin_grant_item(cid_b, "militia", 999, custom_payload=payload)
    assert not ok2 and "UNIQUE" not in err2 and "قبلاً" in err2, err2
    # و بازیکن اول دست‌نخورده
    assert db.get_country_by_player(8730)["country_key"] == "faction_sepah"
