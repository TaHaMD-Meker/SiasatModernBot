# -*- coding: utf-8 -*-
"""🚧 تنش کند و سخت ساخته می‌شود — قرارداد مالک: «تنش خیلی سخت‌تر/کندتر (~۳ روز تا اوج)».

- سقف روزانه‌ی ساخت تنش هر جفت: TENSION_MAX_GAIN_PER_DAY (مازاد اعمال نمی‌شود)
- 🧠 ترس عمومی: تنش ≥ TENSION_FEAR_LEVEL → هر رویداد تنش‌ساز −۱ رضایت دو طرف
- 😱 صف پمپ‌بنزین: تنش ≥ TENSION_FUEL_QUEUE_LEVEL → سوزاندن نفت روزانه
  + خبر زنده، فقط یک‌بار در روز (اجرای force ادمین دوباره نمی‌سوزاند)
- آستانه‌ی جنگ (۴۰) با بازی فعال ≈ ۳ روز؛ نه با یک دکمه
"""
import asyncio
import types

import config
import database as db


def _fresh(monkeypatch, tmp_path, name="pace.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


def _mk(name, flag, key):
    return db.create_country(8100 + abs(hash(key)) % 99999, name, flag, country_key=key)


class _FakeBot:
    def __init__(self):
        self.sent = []

    async def send_message(self, chat_id=None, text=None, **k):
        self.sent.append(str(text))
        return True


# ───────────── ۱) مسیر ۳ روزه تا آستانه‌ی جنگ ─────────────

def test_three_active_days_to_war_threshold(monkeypatch, tmp_path):
    """بیانیه/عملیات/تحریم اسپم‌شده در یک روز نمی‌تواند جنگ باز کند."""
    _fresh(monkeypatch, tmp_path, "d3.db")
    a, b = _mk("ایران", "🇮🇷", "iran_p3"), _mk("امارات", "🇦🇪", "uae_p3")
    days_needed = None
    for day in range(1, 8):
        while True:
            before = db.get_tension(a, b)
            after = db.add_tension(a, b, config.TENSION_STATEMENT_DELTA, "بیانیه تند")
            if after == before:      # سقف روزانه پر شد
                break
            if after >= config.TENSION_ATTACK_THRESHOLD:
                break
        if db.get_tension(a, b) >= config.TENSION_ATTACK_THRESHOLD:
            days_needed = day
            break
        db.decay_all_tensions(config.TENSION_DAILY_DECAY)   # شب: سردشدن
        con = db.get_connection()
        with con:
            con.execute("UPDATE country_tensions SET gain_date='2000-01-01'")  # روز بعد
        con.close()
    assert days_needed is not None, "بالاخره باید به آستانه برسد"
    assert days_needed <= 4, f"خیلی هم کند نشود (شد: روز {days_needed})"
    assert days_needed >= 3, f"🚧 یک/دو روزه باز شدن جنگ ممنوع (شد: روز {days_needed})"


def test_spam_in_single_day_cannot_reach_threshold(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "spam.db")
    a, b = _mk("مصر", "🇪🇬", "egypt_p3"), _mk("اتریش", "🇦🇹", "austria_p3")
    for _ in range(30):
        db.add_tension(a, b, config.TENSION_STATEMENT_DELTA, "بیانیه")
    assert db.get_tension(a, b) <= config.TENSION_MAX_GAIN_PER_DAY < config.TENSION_ATTACK_THRESHOLD


# ───────────── ۲) ترس عمومی ─────────────

def test_public_fear_burns_approval_only_above_fear_level(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "fear.db")
    a, b = _mk("ترکیه", "🇹🇷", "turkey_p3"), _mk("یونان", "🇬🇷", "greece_p3")
    con = db.get_connection()
    with con:
        con.execute("UPDATE countries SET approval_rating=60 WHERE id IN (?,?)", (a, b))
    con.close()

    db.add_tension(a, b, 5, "کم")           # زیر سطح ترس → بی‌اثر
    assert db.get_country_by_id(a)["approval_rating"] == 60

    db.add_tension(a, b, config.TENSION_FEAR_LEVEL, "بحران", bypass_daily_cap=True)  # → ۴۵
    assert db.get_country_by_id(a)["approval_rating"] == 59, "ترس عمومی: −۱ رضایت"
    assert db.get_country_by_id(b)["approval_rating"] == 59, "دو طرف می‌ترسند"

    db.add_tension(a, b, 3, "تنش بیشتر", bypass_daily_cap=True)  # همچنان ≥ ترس
    assert db.get_country_by_id(a)["approval_rating"] == 58

    db.add_tension(a, b, -10, "آرام‌سازی")   # منفی هرگز نمی‌سوزاند
    assert db.get_country_by_id(a)["approval_rating"] == 58


# ───────────── ۳) صف پمپ‌بنزین (طعم اقتصادی پیش از جنگ) ─────────────

def test_fuel_queue_drains_oil_once_daily_and_breaks_news(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "fuel.db")
    a, b = _mk("عربستان", "🇸🇦", "saudi_p3"), _mk("قطر", "🇶🇦", "qatar_p3")
    lone = _mk("آرژانتین", "🇦🇷", "argentina_p3")   # شاهدِ بی‌تنش
    db.set_setting("channel_id", "-100999")
    db.add_tension(a, b, config.TENSION_FUEL_QUEUE_LEVEL + 10, "بحران", bypass_daily_cap=True)
    con = db.get_connection()
    with con:
        con.execute("UPDATE countries SET oil_reserves=1_000_000 WHERE id IN (?,?,?)", (a, b, lone))
    con.close()

    bot = _FakeBot()
    import main as main_mod
    asyncio.run(main_mod.daily_income_job(types.SimpleNamespace(bot=bot), force=False))

    oil_a = db.get_country_by_id(a)["oil_reserves"]
    oil_lone = db.get_country_by_id(lone)["oil_reserves"]
    # شاهد همان درآمد/مصرف عادی را دارد؛ اختلاف نهایی = پانیک صف پمپ‌بنزین
    assert oil_lone - oil_a == config.TENSION_SCARE_OIL_DAILY, "تنش بالا باید نفت اضافه بسوزاند"
    assert any("پمپ‌بنزین" in t for t in bot.sent), "خبر زنده‌ی صف پمپ‌بنزین"

    # اجرای دوم همان روز (force ادمین): نه نفت دوباره، نه خبر دوباره
    n_before = len(bot.sent)
    asyncio.run(main_mod.daily_income_job(types.SimpleNamespace(bot=bot), force=True))
    oil_a2 = db.get_country_by_id(a)["oil_reserves"]
    oil_lone2 = db.get_country_by_id(lone)["oil_reserves"]
    assert oil_lone2 - oil_a2 == config.TENSION_SCARE_OIL_DAILY, "اجرای دومِ همان روز نفت نمی‌سوزاند"
    assert len([t for t in bot.sent if "عربستان" in t and "پمپ‌بنزین" in t]) == 1, "خبر صف هر کشور فقط یک‌بار در روز"
