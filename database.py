# -*- coding: utf-8 -*-
"""
لایه دیتابیس بازی (SQLite).
شامل مدیریت کشورها، دارایی‌های اختصاصی نظامی (Country Assets System)، همگام‌سازی اتوماتیک دیتابیس با آخرین کاتالوگ و خرید اتومیک.
"""

import os
import json
import sqlite3
import datetime
import config
from utils import format_money, format_number, format_oil

def get_connection():
    db_dir = os.path.dirname(config.DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # جدول کشورها
    cur.execute("""
    CREATE TABLE IF NOT EXISTS countries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER UNIQUE NOT NULL,
        name TEXT NOT NULL,
        flag TEXT DEFAULT '🏳️',
        population INTEGER DEFAULT 0,
        treasury INTEGER DEFAULT 0,
        tax_income INTEGER DEFAULT 0,
        daily_income INTEGER DEFAULT 0,
        gold INTEGER DEFAULT 0,
        gold_daily INTEGER DEFAULT 0,
        oil_reserves INTEGER DEFAULT 0,
        oil_production INTEGER DEFAULT 0,
        grain INTEGER DEFAULT 0,
        electricity INTEGER DEFAULT 0,
        active_personnel INTEGER DEFAULT 0,
        reserve_personnel INTEGER DEFAULT 0,
        last_income_date TEXT,
        created_at TEXT,
        country_key TEXT UNIQUE,
        approval_rating INTEGER DEFAULT 80,
        grain_daily INTEGER DEFAULT 0,
        username TEXT,
        tech_level INTEGER DEFAULT 1
    )
    """)

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN country_key TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN approval_rating INTEGER DEFAULT 80")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN grain_daily INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN username TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN tech_level INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN last_blockade_date TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN combat_readiness INTEGER DEFAULT 70")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN last_drill_date TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN daily_drill_count INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_countries_country_key ON countries(country_key)")
    except sqlite3.OperationalError:
        pass

    # جدول دارایی‌های اختصاصی نظامی کشورها (Country Assets System)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS country_assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL,
        country_key TEXT NOT NULL,
        category TEXT NOT NULL,
        equipment_name TEXT NOT NULL,
        equipment_key TEXT NOT NULL,
        amount INTEGER DEFAULT 0,
        buy_price INTEGER DEFAULT 0,
        maintenance_cost INTEGER DEFAULT 0,
        producible INTEGER DEFAULT 1,
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE,
        UNIQUE(country_id, equipment_key)
    )
    """)

    try:
        cur.execute("ALTER TABLE country_assets ADD COLUMN producible INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass

    # جدول عمومی غیرنظامی
    cur.execute("""
    CREATE TABLE IF NOT EXISTS equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL,
        item_key TEXT NOT NULL,
        quantity INTEGER DEFAULT 0,
        UNIQUE(country_id, item_key),
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)

    # درخواست‌های معلق انتخاب کشور جهت تایید ادمین
    cur.execute("""
    CREATE TABLE IF NOT EXISTS pending_country_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER NOT NULL,
        first_name TEXT,
        last_name TEXT,
        username TEXT,
        country_key TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TEXT
    )
    """)

    # رول‌های نظامی معلق جهت بررسی و تایید ادمین
    cur.execute("""
    CREATE TABLE IF NOT EXISTS pending_roleplays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL,
        player_id INTEGER NOT NULL,
        role_type TEXT NOT NULL,
        role_text TEXT NOT NULL,
        status TEXT DEFAULT 'pending',
        created_at TEXT,
        created_date TEXT,
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)

    # تراکنش‌ها
    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        description TEXT,
        amount INTEGER,
        created_at TEXT,
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)

    # تنظیمات پویای سیستم
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # محاصره‌های دریایی بین‌المللی
    cur.execute("""
    CREATE TABLE IF NOT EXISTS naval_blockades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        blockader_id INTEGER NOT NULL,
        target_id INTEGER NOT NULL,
        status TEXT DEFAULT 'active',
        created_at TEXT,
        UNIQUE(blockader_id, target_id),
        FOREIGN KEY(blockader_id) REFERENCES countries(id) ON DELETE CASCADE,
        FOREIGN KEY(target_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)

    # روابط دیپلماتیک بین کشورها
    cur.execute("""
    CREATE TABLE IF NOT EXISTS diplomatic_relations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country1_id INTEGER NOT NULL,
        country2_id INTEGER NOT NULL,
        status TEXT DEFAULT 'normal',
        sanctioned_by INTEGER DEFAULT 0,
        created_at TEXT,
        UNIQUE(country1_id, country2_id),
        FOREIGN KEY(country1_id) REFERENCES countries(id) ON DELETE CASCADE,
        FOREIGN KEY(country2_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)

    # قراردادهای تجاری
    cur.execute("""
    CREATE TABLE IF NOT EXISTS trade_contracts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        proposer_id INTEGER NOT NULL,
        recipient_id INTEGER NOT NULL,
        offered_type TEXT NOT NULL,
        offered_key TEXT,
        offered_amount INTEGER NOT NULL,
        requested_type TEXT NOT NULL,
        requested_amount INTEGER NOT NULL,
        transport_payer TEXT DEFAULT 'seller',
        transport_cost INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        created_at TEXT,
        FOREIGN KEY(proposer_id) REFERENCES countries(id) ON DELETE CASCADE,
        FOREIGN KEY(recipient_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)

    try:
        cur.execute("ALTER TABLE trade_contracts ADD COLUMN offered_key TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE trade_contracts ADD COLUMN transport_mode TEXT DEFAULT 'sea'")
    except sqlite3.OperationalError:
        pass

    # بازار بورس بین‌المللی کالاها (Global Commodities Exchange)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS market_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seller_id INTEGER NOT NULL,
        resource_type TEXT NOT NULL,
        amount INTEGER NOT NULL,
        unit_price INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(seller_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS market_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seller_id INTEGER NOT NULL,
        buyer_id INTEGER NOT NULL,
        resource_type TEXT NOT NULL,
        amount INTEGER NOT NULL,
        unit_price INTEGER NOT NULL,
        total_price INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(seller_id) REFERENCES countries(id) ON DELETE CASCADE,
        FOREIGN KEY(buyer_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)

    # شورای امنیت و رای‌گیری‌های سازمان ملل متحد (UN Resolutions)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS un_resolutions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        creator_id INTEGER NOT NULL,
        status TEXT DEFAULT 'active',
        created_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS un_votes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        resolution_id INTEGER NOT NULL,
        voter_country_id INTEGER NOT NULL,
        vote_option TEXT NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE(resolution_id, voter_country_id),
        FOREIGN KEY(resolution_id) REFERENCES un_resolutions(id) ON DELETE CASCADE,
        FOREIGN KEY(voter_country_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)

    # جدول ثبت نتایج نبردها جهت مشاهده تعاملی با دکمه‌های شیشه‌ای
    cur.execute("""
        CREATE TABLE IF NOT EXISTS daily_missions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL,
        mission_date TEXT NOT NULL,
        missions_json TEXT NOT NULL,
        UNIQUE(country_id, mission_date)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS foreign_bases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        owner_id INTEGER NOT NULL,
        host_id INTEGER NOT NULL,
        name TEXT NOT NULL,
        capacity INTEGER DEFAULT 20,
        level INTEGER DEFAULT 1,
        daily_rent INTEGER DEFAULT 0,
        unpaid_days INTEGER DEFAULT 0,
        created_at TEXT,
        FOREIGN KEY(owner_id) REFERENCES countries(id) ON DELETE CASCADE,
        FOREIGN KEY(host_id) REFERENCES countries(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS base_assets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        base_id INTEGER NOT NULL,
        equipment_key TEXT NOT NULL,
        equipment_name TEXT,
        category TEXT,
        amount INTEGER DEFAULT 0,
        UNIQUE(base_id, equipment_key)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS base_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        rtype TEXT DEFAULT 'create',
        owner_id INTEGER NOT NULL,
        host_id INTEGER NOT NULL,
        base_name TEXT,
        base_id INTEGER,
        message TEXT,
        daily_rent INTEGER DEFAULT 0,
        status TEXT DEFAULT 'pending',
        created_at TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS loss_reports (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL,
        operation_name TEXT DEFAULT '',
        note TEXT DEFAULT '',
        admin_id INTEGER,
        status TEXT DEFAULT 'applied',
        items_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
        )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS war_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attacker_id INTEGER NOT NULL,
        defender_id INTEGER NOT NULL,
        operation_type TEXT NOT NULL,
        summary_text TEXT NOT NULL,
        timeline_text TEXT NOT NULL,
        targets_text TEXT NOT NULL,
        territory_text TEXT NOT NULL,
        losses_json TEXT NOT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY(attacker_id) REFERENCES countries(id) ON DELETE CASCADE,
        FOREIGN KEY(defender_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)

    conn.commit()
    conn.close()

    # همگام‌سازی خودکار دیتابیس با جدیدترین کاتالوگ در زمان راه‌اندازی
    try:
        sync_all_country_assets_to_catalog()
    except Exception:
        pass

    try:
        rebalance_existing_countries_income()
    except Exception:
        pass

    try:
        fix_legacy_grain_scale()
    except Exception:
        pass

    try:
        fix_grain_scale_v2()
    except Exception:
        pass

    try:
        fix_refinery_oil_production()
    except Exception:
        pass

    try:
        fix_refinery_oil_production_v2()
    except Exception:
        pass

    try:
        fix_india_oil_reserves()
    except Exception:
        pass

    try:
        fix_bab_el_mandeb_status()
    except Exception:
        pass


def fix_legacy_grain_scale():
    """مایگریشن یک‌باره (v1): اصلاح موجودی غلات کشورهای ساخته‌شده با مقیاس قدیمی.

    واحد رسمی غلات در بازی «تن» است، اما کشورهای قدیمی با مقادیر ۱۵ تا ۱۰۰ تن
    (کمتر از یک روز نیاز!) ساخته شده بودند و برای همیشه در حالت قحطی می‌ماندند.
    این تابع فقط یک بار اجرا می‌شود و ذخیره کشورها را در صورت کمتر بودن از
    مقدار استاندارد جدید (بر اساس کانفیگ)، به بالا ارتقا می‌دهد.
    """
    if get_setting("grain_scale_fixed_v1"):
        return
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, country_key, population, grain FROM countries")
    rows = cur.fetchall()
    fixed_count = 0
    for row in rows:
        cid = row[0]
        ckey = row[1]
        pop = row[2] or 10_000_000
        grain = row[3] or 0
        need_daily = max(10, int((pop / 1_000_000) * 100))
        preset = config.COUNTRY_STARTING_OVERRIDES.get(ckey, {}) if ckey else {}
        target = preset.get("grain") or (need_daily * 25)
        if grain < target:
            cur.execute("UPDATE countries SET grain = ? WHERE id = ?", (target, cid))
            fixed_count += 1
    conn.commit()
    conn.close()
    set_setting("grain_scale_fixed_v1", datetime.datetime.now(datetime.timezone.utc).isoformat())
    if fixed_count:
        print(f"[grain-migration] {fixed_count} country grain stocks upgraded to ton-scale.")


def fix_grain_scale_v2():
    """مایگریشن v2: فشرده‌سازی ذخایر غلات به مقیاس هفته‌ای بازی (۳ تا ۱۰ روز ذخیره).

    طبق بازطراحی بالانس، ذخیره غلات کشورها باید در بازه‌ی ریتم هفته‌ای بازی باشد.
    این تابع یک بار اجرا می‌شود و ذخایر بالاتر از سقف استاندارد جدید را فقط تا سقف
    پایین می‌آورد (کشورهایی که ذخیره‌شان کمتر از سقف است دست نمی‌خورند).
    """
    if get_setting("grain_scale_fixed_v2"):
        return
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, country_key, population, grain FROM countries")
    rows = cur.fetchall()
    changed = 0
    for row in rows:
        cid = row[0]
        ckey = row[1]
        pop = row[2] or 10_000_000
        grain = row[3] or 0
        need_daily = max(10, int((pop / 1_000_000) * 100))
        preset = config.COUNTRY_STARTING_OVERRIDES.get(ckey, {}) if ckey else {}
        cap = preset.get("grain") or (need_daily * 7)
        if grain > cap:
            cur.execute("UPDATE countries SET grain = ? WHERE id = ?", (cap, cid))
            changed += 1
    conn.commit()
    conn.close()
    set_setting("grain_scale_fixed_v2", datetime.datetime.now(datetime.timezone.utc).isoformat())
    if changed:
        print(f"[grain-migration-v2] {changed} country grain stocks capped to weekly scale.")


def fix_refinery_oil_production():
    """مایگریشن v3: ترمیم تولید نفت از دست‌رفته.

    باگ قدیمی rebalance (قبل از اصلاح) با هر ری‌استارت، oil_production کشورها را
    به مقدار پایه کانفیگ برمی‌گرداند؛ برای کشورهای بدون نفت مانند سوئد (پایه صفر)
    این یعنی تولیدِ پالایشگاه‌های خریداری‌شده بازیکن همیشه پاک می‌شد.
    این تابع یک بار اجرا می‌شود و تولید هر کشور را به
    (پایه کانفیگ + مجموع oil_prod_add ساختمان‌های موجود) ارتقا می‌دهد — فقط به بالا.
    """
    if get_setting("oil_prod_repair_v1"):
        return
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id, country_key, oil_production FROM countries")
            rows = cur.fetchall()
            repaired = 0
            for r in rows:
                overrides = config.COUNTRY_STARTING_OVERRIDES.get(r["country_key"], config.STARTING_VALUES)
                base_prod = overrides.get("oil_production", 0)
                bonus = 0
                cur.execute("SELECT item_key, quantity FROM equipment WHERE country_id = ?", (r["id"],))
                for eq in cur.fetchall():
                    bonus += config.ALL_SHOP_ITEMS.get(eq["item_key"], {}).get("oil_prod_add", 0) * eq["quantity"]
                target = base_prod + bonus
                if (r["oil_production"] or 0) < target:
                    cur.execute("UPDATE countries SET oil_production = ? WHERE id = ?", (target, r["id"]))
                    repaired += 1
        conn.close()
        if repaired:
            print(f"[oil-prod-repair] {repaired} country oil production restored from owned refineries.")
        # فلگ باید بیرون از تراکنشِ کانکشن اصلی ست شود (نباید کانکشن دوم داخل قفل باز شود)
        set_setting("oil_prod_repair_v1", datetime.datetime.now(datetime.timezone.utc).isoformat())
        return
    except Exception as e:
        print(f"Error in fix_refinery_oil_production: {e}")
        try:
            conn.close()
        except Exception:
            pass


def fix_refinery_oil_production_v2():
    """مایگریشن v4: اعمال تمایز نفتی/غیرنفتی روی تولید پالایشگاه‌های موجود.

    کشورهای غیرنفتی از هر پالایشگاه فقط +۲۵هزار بشکه می‌گیرند؛ اگر ترمیم قبلی
    به آن‌ها +۱۰۰هزار داده باشد (فرمول قدیمی)، به مقدار درست جدید اصلاح می‌شود.
    مقادیر آسیب‌دیده از جنگ که با فرمول‌ها مطابقت ندارند، دست نمی‌خورند.
    """
    if get_setting("oil_prod_repair_v2"):
        return
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id, country_key, oil_production FROM countries")
            rows = cur.fetchall()
            changed = 0
            for r in rows:
                cur.execute(
                    "SELECT COALESCE(SUM(quantity), 0) AS q FROM equipment WHERE country_id = ? AND item_key = 'oil_refinery'",
                    (r["id"],),
                )
                qty = cur.fetchone()["q"]
                if not qty:
                    continue
                base = config.get_country_base_oil_production(r["country_key"])
                eff = config.get_refinery_effect(r["country_key"])
                expected_new = base + eff["oil_prod"] * qty
                expected_old = base + 100_000 * qty
                current = r["oil_production"] or 0
                if not config.is_oil_country(r["country_key"]) and current == expected_old:
                    cur.execute("UPDATE countries SET oil_production = ? WHERE id = ?", (expected_new, r["id"]))
                    changed += 1
                elif current < expected_new:
                    cur.execute("UPDATE countries SET oil_production = ? WHERE id = ?", (expected_new, r["id"]))
                    changed += 1
        conn.close()
        if changed:
            print(f"[oil-prod-repair-v2] {changed} countries adjusted for oil/non-oil refinery rules.")
        set_setting("oil_prod_repair_v2", datetime.datetime.now(datetime.timezone.utc).isoformat())
        return
    except Exception as e:
        print(f"Error in fix_refinery_oil_production_v2: {e}")
        try:
            conn.close()
        except Exception:
            pass


def fix_india_oil_reserves():
    """مایگریشن v5: به‌روزرسانی ذخیره نفت هند مطابق رتبه جهانی (تنها کشورِ تغییرکرده).

    ذخایر اثبات‌شده واقعی هند ~۵ میلیارد بشکه (رتبه ۲۲ جهان) است که در مقیاس بازی
    و با توجه به جایگاهش (زیر چین، هم‌رده قطر) معادل ۵۰ میلیون بشکه در نظر گرفته شد.
    فقط اگر ذخیره فعلی بازیکن هند کمتر از مقدار جدید باشد، به بالا ارتقا می‌یابد.
    """
    if get_setting("india_oil_v1"):
        return
    target = config.COUNTRY_STARTING_OVERRIDES.get("india", {}).get("oil_reserves")
    if not target:
        return
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id, oil_reserves FROM countries WHERE country_key = 'india'")
            rows = cur.fetchall()
            for r in rows:
                if (r["oil_reserves"] or 0) < target:
                    cur.execute("UPDATE countries SET oil_reserves = ? WHERE id = ?", (target, r["id"]))
        conn.close()
        set_setting("india_oil_v1", datetime.datetime.now(datetime.timezone.utc).isoformat())
    except Exception as e:
        print(f"Error in fix_india_oil_reserves: {e}")
        try:
            conn.close()
        except Exception:
            pass


def fix_bab_el_mandeb_status():
    """مایگریشن v6: بازگردانی باب‌المندب.

    مالکیت اشتباه باب‌المندب به حزب‌الله داده شده بود (کشور بدون ساحل دریای سرخ)؛
    با حذف آن مالکیت، هر وضعیت انسداد/عوارض باقی‌مانده از آن دوران یک‌بار بازنشانی می‌شود.
    """
    if get_setting("bab_el_mandeb_reset_v1"):
        return
    if get_setting("strait_status_bab_el_mandeb") in ("blocked", "toll"):
        set_setting("strait_status_bab_el_mandeb", "open")
        print("[bab-el-mandeb] strait status reset to open (invalid owner removed).")
    set_setting("bab_el_mandeb_reset_v1", datetime.datetime.now(datetime.timezone.utc).isoformat())




# ==================== سیستم مدیریت تلفات تجهیزات (Losses System) ====================
# معماری ماژولار: بات فقط ثبت/اعمال/بازگردانی می‌کند؛ تعیین تلفات با مدیریت بازی است.
# برای افزودن «خسارت زیرساخت/اقتصادی/مصرف مهمات» در آینده، همین الگو با ستون type قابل توسعه است.

def create_loss_report(country_id: int, items: list, operation_name: str = "", note: str = "", admin_id=None):
    """ثبت و اعمال تراکنشیِ گزارش تلفات — همه یا هیچ.

    items = [{key, name, category, subcat, emoji, unit, qty}, ...]
    اعتبارسنجی کامل همه‌ی اقلام قبل از اعمال انجام می‌شود؛ اگر حتی یک قلم
    نامعتبر باشد (ناموجود یا بیش از موجودی)، هیچ تغییری اعمال نمی‌شود.
    قلم با qty=0 فقط در گزارش ثبت می‌شود و تغییری در موجودی نمی‌دهد.
    """
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            # اقلام ویژه: mil_kia از نیروی فعال؛ money از خزانه؛ oil از ذخایر نفت؛ wounded/civ فقط ثبت
            valid_items = [it for it in items if int(it.get("qty", 0) or 0) > 0 and it.get("special") != "wounded" and it.get("special") != "civ_kia"]
            for it in valid_items:
                if it.get("special") == "building":
                    cur.execute("SELECT quantity FROM equipment WHERE country_id = ? AND item_key = ?", (country_id, it["key"]))
                    erow = cur.fetchone()
                    owned = (erow["quantity"] or 0) if erow else 0
                    if owned <= 0:
                        continue  # مالکیت ندارد → نادیده گرفته می‌شود
                    it["qty"] = min(int(it["qty"]), owned)
                    cfg_it = config.ALL_SHOP_ITEMS.get(it["key"], {})
                    q = int(it["qty"])
                    it["effects"] = {
                        "elec": int(cfg_it.get("elec_add", 0) or 0) * q,
                        "gold_daily": int(cfg_it.get("gold_daily_add", 0) or 0) * q,
                        "oil_prod": int(cfg_it.get("oil_prod_add", 0) or 0) * q,
                        "grain_daily": int(cfg_it.get("grain_daily_add", 0) or 0) * q,
                    }
                    continue
                if it.get("special") == "money":
                    cur.execute("SELECT treasury FROM countries WHERE id = ?", (country_id,))
                    trow = cur.fetchone()
                    tr = (trow["treasury"] or 0) if trow else 0
                    if int(it["qty"]) > tr:
                        raise ValueError(f"هزینه مالی ({int(it['qty']):,}) بیشتر از خزانه کشور ({tr:,}) است.")
                    continue
                if it.get("special") == "oil":
                    cur.execute("SELECT oil_reserves FROM countries WHERE id = ?", (country_id,))
                    orow = cur.fetchone()
                    ores = (orow["oil_reserves"] or 0) if orow else 0
                    if int(it["qty"]) > ores:
                        raise ValueError(f"سوخت مصرفی ({int(it['qty']):,}) بیشتر از ذخایر نفت کشور ({ores:,}) است.")
                    continue
                if it.get("special") == "mil_kia":
                    cur.execute("SELECT active_personnel FROM countries WHERE id = ?", (country_id,))
                    prow = cur.fetchone()
                    ap = (prow["active_personnel"] or 0) if prow else 0
                    if int(it["qty"]) > ap:
                        raise ValueError(f"تلفات نظامی ({int(it['qty']):,}) بیشتر از نیروی فعال کشور ({ap:,}) است.")
                    continue
                cur.execute(
                    "SELECT amount FROM country_assets WHERE country_id = ? AND equipment_key = ?",
                    (country_id, it["key"]),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError(f"تجهیز «{it.get('name', it['key'])}» در انبار این کشور یافت نشد.")
                if int(it["qty"]) > (row["amount"] or 0):
                    raise ValueError(
                        f"تلفات «{it.get('name', it['key'])}» ({it['qty']:,}) بیشتر از موجودی ({(row['amount'] or 0):,}) است."
                    )
            for it in valid_items:
                if it.get("special") == "building":
                    cur.execute("UPDATE equipment SET quantity = quantity - ? WHERE country_id = ? AND item_key = ?",
                                (int(it["qty"]), country_id, it["key"]))
                    eff = it.get("effects", {})
                    cur.execute(
                        "UPDATE countries SET electricity = MAX(0, electricity - ?), gold_daily = MAX(0, gold_daily - ?),"
                        " oil_production = MAX(0, oil_production - ?), grain_daily = MAX(0, grain_daily - ?) WHERE id = ?",
                        (eff.get("elec", 0), eff.get("gold_daily", 0), eff.get("oil_prod", 0), eff.get("grain_daily", 0), country_id))
                    continue
                if it.get("special") == "money":
                    cur.execute("UPDATE countries SET treasury = treasury - ? WHERE id = ?", (int(it["qty"]), country_id))
                    continue
                if it.get("special") == "oil":
                    cur.execute("UPDATE countries SET oil_reserves = oil_reserves - ? WHERE id = ?", (int(it["qty"]), country_id))
                    continue
                if it.get("special") == "mil_kia":
                    cur.execute("UPDATE countries SET active_personnel = active_personnel - ? WHERE id = ?", (int(it["qty"]), country_id))
                    continue
                cur.execute(
                    "UPDATE country_assets SET amount = amount - ? WHERE country_id = ? AND equipment_key = ?",
                    (int(it["qty"]), country_id, it["key"]),
                )
            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute(
                "INSERT INTO loss_reports (country_id, operation_name, note, admin_id, status, items_json, created_at) VALUES (?,?,?,?,?,?,?)",
                (country_id, operation_name or "", note or "", admin_id, "applied", json.dumps(items, ensure_ascii=False), now_str),
            )
            report_id = cur.lastrowid
        # تخریب ساختمان → بازسازی درآمد روزانه (کارخانه بسوزد، درآمدش قطع شود)
        if any(it.get("special") == "building" for it in valid_items):
            try:
                rebalance_existing_countries_income()
            except Exception:
                pass
        return True, report_id, None
    except Exception as e:
        return False, None, str(e)


def get_loss_reports(country_id: int = None, limit: int = 15, query: str = None):
    """تاریخچه تلفات (اختیاراً برای یک کشور یا با جستجو)."""
    conn = get_connection()
    cur = conn.cursor()
    sql = "SELECT l.*, c.name AS country_name, c.flag AS country_flag FROM loss_reports l LEFT JOIN countries c ON c.id = l.country_id WHERE l.status != 'deleted'"
    params = []
    if country_id:
        sql += " AND l.country_id = ?"
        params.append(country_id)
    if query:
        sql += " AND (l.operation_name LIKE ? OR l.items_json LIKE ? OR l.note LIKE ?)"
        params.extend([f"%{query}%"] * 3)
    sql += " ORDER BY l.id DESC LIMIT ?"
    params.append(limit)
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_loss_report_by_id(report_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT l.*, c.name AS country_name, c.flag AS country_flag FROM loss_reports l LEFT JOIN countries c ON c.id = l.country_id WHERE l.id = ?",
        (report_id,),
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def revert_loss_report(report_id: int):
    """بازگردانی یک گزارش: تجهیزات به موجودی برمی‌گردند و وضعیت reverted می‌شود."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT status, items_json, country_id FROM loss_reports WHERE id = ?", (report_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError("گزارش یافت نشد.")
            if row["status"] != "applied":
                raise ValueError("این گزارش قبلاً بازگردانی شده است.")
            items = json.loads(row["items_json"])
            for it in items:
                if int(it.get("qty", 0) or 0) > 0:
                    if it.get("special") == "building":
                        cur.execute("INSERT INTO equipment (country_id, item_key, quantity) VALUES (?,?,?)"
                                    " ON CONFLICT(country_id, item_key) DO UPDATE SET quantity = quantity + excluded.quantity",
                                    (row["country_id"], it["key"], int(it["qty"])))
                        eff = it.get("effects", {})
                        cur.execute(
                            "UPDATE countries SET electricity = electricity + ?, gold_daily = gold_daily + ?,"
                            " oil_production = oil_production + ?, grain_daily = grain_daily + ? WHERE id = ?",
                            (eff.get("elec", 0), eff.get("gold_daily", 0), eff.get("oil_prod", 0), eff.get("grain_daily", 0), row["country_id"]))
                        continue
                    if it.get("special") == "money":
                        cur.execute("UPDATE countries SET treasury = treasury + ? WHERE id = ?", (int(it["qty"]), row["country_id"]))
                        continue
                    if it.get("special") == "oil":
                        cur.execute("UPDATE countries SET oil_reserves = oil_reserves + ? WHERE id = ?", (int(it["qty"]), row["country_id"]))
                        continue
                    if it.get("special") == "mil_kia":
                        cur.execute("UPDATE countries SET active_personnel = active_personnel + ? WHERE id = ?", (int(it["qty"]), row["country_id"]))
                        continue
                    cur.execute(
                        "UPDATE country_assets SET amount = amount + ? WHERE country_id = ? AND equipment_key = ?",
                        (int(it["qty"]), row["country_id"], it["key"]),
                    )
            cur.execute("UPDATE loss_reports SET status = 'reverted' WHERE id = ?", (report_id,))
        if any(it.get("special") == "building" for it in items):
            try:
                rebalance_existing_countries_income()
            except Exception:
                pass
        return True, None
    except Exception as e:
        return False, str(e)


def delete_loss_report(report_id: int):
    """حذف گزارش از تاریخچه؛ اگر اعمال‌شده باشد ابتدا موجودی بازگردانی می‌شود."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT status, items_json, country_id FROM loss_reports WHERE id = ?", (report_id,))
            row = cur.fetchone()
            if not row:
                raise ValueError("گزارش یافت نشد.")
            if row["status"] == "applied":
                items = json.loads(row["items_json"])
                for it in items:
                    if int(it.get("qty", 0) or 0) > 0:
                        if it.get("special") == "building":
                            cur.execute("INSERT INTO equipment (country_id, item_key, quantity) VALUES (?,?,?)"
                                        " ON CONFLICT(country_id, item_key) DO UPDATE SET quantity = quantity + excluded.quantity",
                                        (row["country_id"], it["key"], int(it["qty"])))
                            eff = it.get("effects", {})
                            cur.execute(
                                "UPDATE countries SET electricity = electricity + ?, gold_daily = gold_daily + ?,"
                                " oil_production = oil_production + ?, grain_daily = grain_daily + ? WHERE id = ?",
                                (eff.get("elec", 0), eff.get("gold_daily", 0), eff.get("oil_prod", 0), eff.get("grain_daily", 0), row["country_id"]))
                            continue
                        if it.get("special") == "money":
                            cur.execute("UPDATE countries SET treasury = treasury + ? WHERE id = ?", (int(it["qty"]), row["country_id"]))
                            continue
                        if it.get("special") == "oil":
                            cur.execute("UPDATE countries SET oil_reserves = oil_reserves + ? WHERE id = ?", (int(it["qty"]), row["country_id"]))
                            continue
                        if it.get("special") == "mil_kia":
                            cur.execute("UPDATE countries SET active_personnel = active_personnel + ? WHERE id = ?", (int(it["qty"]), row["country_id"]))
                            continue
                        cur.execute(
                            "UPDATE country_assets SET amount = amount + ? WHERE country_id = ? AND equipment_key = ?",
                            (int(it["qty"]), row["country_id"], it["key"]),
                        )
            cur.execute("UPDATE loss_reports SET status = 'deleted' WHERE id = ?", (report_id,))
        if row["status"] == "applied" and any(it.get("special") == "building" for it in items):
            try:
                rebalance_existing_countries_income()
            except Exception:
                pass
        return True, None
    except Exception as e:
        return False, str(e)


def get_loss_stats(country_id: int):
    """آمار تلفات یک کشور: تعداد گزارش‌ها و مجموع تلفات به تفکیک تجهیز/دسته."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT items_json, status FROM loss_reports WHERE country_id = ?", (country_id,))
    rows = cur.fetchall()
    conn.close()
    from collections import Counter
    by_equip = Counter()
    by_subcat = Counter()
    reports = 0
    reverted = 0
    for r in rows:
        if r["status"] == "deleted":
            continue
        reports += 1
        if r["status"] == "reverted":
            reverted += 1
            continue
        for it in json.loads(r["items_json"]):
            if int(it.get("qty", 0) or 0) > 0:
                by_equip[it.get("name", it.get("key", "?"))] += int(it["qty"])
                by_subcat[it.get("subcat", it.get("category", "?"))] += int(it["qty"])
    return {"reports": reports, "reverted": reverted, "by_equip": by_equip, "by_subcat": by_subcat}




def get_today_missions(country_id: int) -> dict:
    """وضعیت مأموریت‌های روزانه امروز کشور (در صورت نبود، سطر جدید می‌سازد)."""
    today = datetime.date.today().isoformat()
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT missions_json FROM daily_missions WHERE country_id = ? AND mission_date = ?", (country_id, today))
    row = cur.fetchone()
    if row:
        conn.close()
        return json.loads(row["missions_json"])
    defaults = {k: 0 for k in config.DAILY_MISSIONS}
    cur.execute("INSERT OR IGNORE INTO daily_missions (country_id, mission_date, missions_json) VALUES (?,?,?)",
                (country_id, today, json.dumps(defaults)))
    conn.commit()
    conn.close()
    return dict(defaults)


def complete_daily_mission(country_id: int, key: str):
    """تکمیل مأموریت روزانه (فقط بار اول در روز) + واریز پاداش. خروجی: (انجام شد؟, مبلغ پاداش)"""
    if key not in config.DAILY_MISSIONS:
        return False, 0
    today = datetime.date.today().isoformat()
    ms = get_today_missions(country_id)
    if ms.get(key):
        return False, 0
    ms[key] = 1
    reward = int(config.DAILY_MISSIONS[key][1])
    conn = get_connection()
    with conn:
        cur = conn.cursor()
        cur.execute("UPDATE daily_missions SET missions_json = ? WHERE country_id = ? AND mission_date = ?",
                    (json.dumps(ms), country_id, today))
    adjust_treasury(country_id, reward)
    add_transaction(country_id, "mission", f"پاداش مأموریت روزانه: {config.DAILY_MISSIONS[key][0]}", reward)
    return True, reward




# ==================== سیستم پایگاه پیشروی (Forward Bases) ====================

def create_base_request(rtype, owner_id, host_id, base_name, base_id, message, daily_rent):
    conn = get_connection()
    cur = conn.cursor()
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur.execute(
        "INSERT INTO base_requests (rtype, owner_id, host_id, base_name, base_id, message, daily_rent, status, created_at) VALUES (?,?,?,?,?,?,?, 'pending', ?)",
        (rtype, owner_id, host_id, base_name, base_id, message or "", int(daily_rent or 0), now_str),
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def get_base_request(req_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM base_requests WHERE id = ?", (req_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def set_base_request_status(req_id, status):
    conn = get_connection()
    conn.execute("UPDATE base_requests SET status = ? WHERE id = ?", (status, req_id))
    conn.commit()
    conn.close()


def _can_afford(c, cost):
    return (
        (c.get("treasury", 0) or 0) >= cost.get("money", 0)
        and (c.get("gold", 0) or 0) >= cost.get("gold", 0)
        and (c.get("grain", 0) or 0) >= cost.get("grain", 0)
        and (c.get("oil_reserves", 0) or 0) >= cost.get("oil", 0)
    )


def _deduct_base_cost(cur, country_id, cost):
    cur.execute(
        "UPDATE countries SET treasury = treasury - ?, gold = gold - ?, grain = grain - ?, oil_reserves = oil_reserves - ? WHERE id = ?",
        (cost.get("money", 0), cost.get("gold", 0), cost.get("grain", 0), cost.get("oil", 0), country_id),
    )


def approve_base_create(req_id, auto=True):
    """اعتبارسنجی و (در صورت auto) ساخت پایگاه با کسر هزینه‌ها — اتمیک."""
    req = get_base_request(req_id)
    if not req or req["status"] != "pending":
        return False, "درخواست معتبر نیست.", None
    owner = get_country_by_id(req["owner_id"])
    if not owner:
        return False, "کشور درخواست‌کننده یافت نشد.", None
    if not _can_afford(owner, config.BASE_BUILD_COST):
        return False, "منابع کافی برای هزینه ساخت پایگاه ندارید:\n" + str(config.BASE_BUILD_COST), None
    if not auto:
        return True, "قابل پرداخت", None
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            _deduct_base_cost(cur, req["owner_id"], config.BASE_BUILD_COST)
            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute(
                "INSERT INTO foreign_bases (owner_id, host_id, name, capacity, level, daily_rent, unpaid_days, created_at) VALUES (?,?,?,?,?,?,0,?)",
                (req["owner_id"], req["host_id"], req["base_name"], config.BASE_DEFAULT_CAPACITY, 1, int(req["daily_rent"] or 0), now_str),
            )
            base_id = cur.lastrowid
            cur.execute("UPDATE base_requests SET status = 'accepted' WHERE id = ?", (req_id,))
            add_transaction(req["owner_id"], "base_build", f"ساخت پایگاه «{req['base_name']}»", -int(config.BASE_BUILD_COST.get("money", 0)))
        return True, "ساخته شد", base_id
    except Exception as e:
        return False, str(e), None


def approve_base_upgrade(req_id):
    req = get_base_request(req_id)
    if not req or req["status"] != "pending" or req["rtype"] != "upgrade":
        return False, "درخواست معتبر نیست."
    owner = get_country_by_id(req["owner_id"])
    if not owner or not _can_afford(owner, config.BASE_UPGRADE_COST):
        return False, "صاحب پایگاه منابع کافی برای ارتقا ندارد."
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            _deduct_base_cost(cur, req["owner_id"], config.BASE_UPGRADE_COST)
            cur.execute("UPDATE foreign_bases SET capacity = capacity + ?, level = level + 1 WHERE id = ?",
                        (config.BASE_UPGRADE_STEP, req["base_id"]))
            cur.execute("UPDATE base_requests SET status = 'accepted' WHERE id = ?", (req_id,))
        return True, "ارتقا یافت"
    except Exception as e:
        return False, str(e)


def get_bases(owner_id=None, host_id=None):
    conn = get_connection()
    cur = conn.cursor()
    sql = ("SELECT b.*, o.name AS oname, o.flag AS oflag, h.name AS hname, h.flag AS hflag "
           "FROM foreign_bases b JOIN countries o ON o.id = b.owner_id JOIN countries h ON h.id = b.host_id WHERE 1=1")
    params = []
    if owner_id:
        sql += " AND b.owner_id = ?"
        params.append(owner_id)
    if host_id:
        sql += " AND b.host_id = ?"
        params.append(host_id)
    sql += " ORDER BY b.id DESC"
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_base(base_id):
    rows = get_bases()
    for r in rows:
        if r["id"] == base_id:
            return r
    return None


def get_base_assets(base_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM base_assets WHERE base_id = ? AND amount > 0", (base_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def deploy_to_base(base_id, equipment_key, amount):
    """انتقال اتمیک تجهیز از انبار صاحب پایگاه به پایگاه (با کنترل ظرفیت قلم)."""
    b = get_base(base_id)
    if not b:
        return False, "پایگاه یافت نشد."
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT amount FROM country_assets WHERE country_id = ? AND equipment_key = ?", (b["owner_id"], equipment_key))
            row = cur.fetchone()
            if not row or (row["amount"] or 0) < amount:
                return False, "موجودی انبار شما کافی نیست."
            cur.execute("SELECT COUNT(*) AS n FROM base_assets WHERE base_id = ? AND amount > 0", (base_id,))
            lines = cur.fetchone()["n"]
            cur.execute("SELECT amount FROM base_assets WHERE base_id = ? AND equipment_key = ?", (base_id, equipment_key))
            existing = cur.fetchone()
            if not existing and lines >= b["capacity"]:
                return False, f"ظرفیت پایگاه پر است ({b['capacity']} قلم). اول ارتقا بده یا تجهیز برگردان."
            cur.execute("UPDATE country_assets SET amount = amount - ? WHERE country_id = ? AND equipment_key = ?", (amount, b["owner_id"], equipment_key))
            a = get_asset_by_key(b["owner_id"], equipment_key)
            cur.execute(
                "INSERT INTO base_assets (base_id, equipment_key, equipment_name, category, amount) VALUES (?,?,?,?,?)"
                " ON CONFLICT(base_id, equipment_key) DO UPDATE SET amount = amount + ?",
                (base_id, equipment_key, a["equipment_name"] if a else equipment_key, a["category"] if a else "", amount, amount),
            )
        return True, "منتقل شد"
    except Exception as e:
        return False, str(e)


def recall_from_base(base_id, equipment_key, amount=None):
    """بازگشت تجهیزات از پایگاه به انبار صاحب."""
    b = get_base(base_id)
    if not b:
        return False, "پایگاه یافت نشد."
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT amount FROM base_assets WHERE base_id = ? AND equipment_key = ?", (base_id, equipment_key))
            row = cur.fetchone()
            if not row or (row["amount"] or 0) <= 0:
                return False, "این تجهیز در پایگاه نیست."
            amt = row["amount"] if amount is None else min(int(amount), row["amount"])
            cur.execute("UPDATE base_assets SET amount = amount - ? WHERE base_id = ? AND equipment_key = ?", (amt, base_id, equipment_key))
            cur.execute(
                "UPDATE country_assets SET amount = amount + ? WHERE country_id = ? AND equipment_key = ?",
                (amt, b["owner_id"], equipment_key),
            )
        return True, "برگشت"
    except Exception as e:
        return False, str(e)


def dissolve_base(base_id, loss_pct=0):
    """انحلال پایگاه؛ تجهیزات با کسر loss_pct به انبار صاحب برمی‌گردد."""
    b = get_base(base_id)
    if not b:
        return
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT equipment_key, amount FROM base_assets WHERE base_id = ? AND amount > 0", (base_id,))
            for r in cur.fetchall():
                keep = int(r["amount"] * (100 - loss_pct) / 100)
                if keep > 0:
                    cur.execute("UPDATE country_assets SET amount = amount + ? WHERE country_id = ? AND equipment_key = ?",
                                (keep, b["owner_id"], r["equipment_key"]))
            cur.execute("DELETE FROM base_assets WHERE base_id = ?", (base_id,))
            cur.execute("DELETE FROM foreign_bases WHERE id = ?", (base_id,))
    except Exception as e:
        print(f"dissolve_base error: {e}")


def evict_base(base_id):
    """اخراج پایگاه توسط میزبان؛ ۲۵٪ تجهیزات تلف می‌شود."""
    dissolve_base(base_id, loss_pct=25)


def get_base_daily_cost(base_id):
    """هزینه روزانه پویا: ثابت + به‌ازای هر قلم تجهیزات مستقر."""
    items = get_base_assets(base_id)
    n_items = len(items)
    cost = {}
    for k in ("money", "grain", "oil"):
        cost[k] = config.BASE_DAILY_FLAT.get(k, 0) + n_items * config.BASE_DAILY_PER_ITEM.get(k, 0)
    return cost


def process_base_daily_costs():
    """هزینه روزانه پایگاه‌ها + اجاره میزبان؛ ۳ روز پرداخت‌نشده = انحلال با ۲۵٪ تلفات."""
    events = []
    for b in get_bases():
        owner = get_country_by_id(b["owner_id"])
        if not owner:
            continue
        cost = get_base_daily_cost(b["id"])
        rent = int(b.get("daily_rent") or 0)
        total_money = cost.get("money", 0) + rent
        affordable = (
            (owner.get("treasury", 0) or 0) >= total_money
            and (owner.get("grain", 0) or 0) >= cost.get("grain", 0)
            and (owner.get("oil_reserves", 0) or 0) >= cost.get("oil", 0)
        )
        conn = get_connection()
        if affordable:
            with conn:
                cur = conn.cursor()
                cur.execute("UPDATE countries SET treasury = treasury - ?, grain = grain - ?, oil_reserves = oil_reserves - ? WHERE id = ?",
                            (total_money, cost.get("grain", 0), cost.get("oil", 0), owner["id"]))
                if rent > 0:
                    cur.execute("UPDATE countries SET treasury = treasury + ? WHERE id = ?", (rent, b["host_id"]))
                cur.execute("UPDATE foreign_bases SET unpaid_days = 0 WHERE id = ?", (b["id"],))
            conn.close()
            events.append({"base": b["name"], "event": "paid", "rent": rent, "host_pid": None})
        else:
            with conn:
                conn.execute("UPDATE foreign_bases SET unpaid_days = unpaid_days + 1 WHERE id = ?", (b["id"],))
            row = conn.execute("SELECT unpaid_days FROM foreign_bases WHERE id = ?", (b["id"],)).fetchone()
            conn.close()
            events.append({"base": b["name"], "event": "unpaid", "days": row["unpaid_days"] if row else "?"})
            if row and row["unpaid_days"] >= 3:
                dissolve_base(b["id"], loss_pct=25)
                events.append({"base": b["name"], "event": "collapsed"})
    return events


# ---------- کشورها ----------

def create_country(player_id: int, name: str, flag: str = "🏳️", country_key: str = None, username: str = None):
    conn = get_connection()
    cur = conn.cursor()

    sv = config.COUNTRY_STARTING_OVERRIDES.get(country_key, config.STARTING_VALUES)

    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur.execute("""
        INSERT INTO countries
        (player_id, name, flag, population, treasury, tax_income, daily_income,
         gold, gold_daily, oil_reserves, oil_production, grain, electricity,
         active_personnel, reserve_personnel, last_income_date, created_at, country_key, username)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        player_id, name, flag,
        sv["population"], sv["treasury"], sv["tax_income"], sv["daily_income"],
        sv["gold"], sv["gold_daily"], sv["oil_reserves"], sv["oil_production"],
        sv["grain"], sv["electricity"], sv["active_personnel"], sv["reserve_personnel"],
        None, now_str, country_key, username
    ))
    country_id = cur.lastrowid
    conn.commit()
    conn.close()

    if country_id and country_key:
        seed_country_assets(country_id, country_key)

    return country_id


def get_country_by_id(country_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM countries WHERE id = ?", (country_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_country_by_key(country_key: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM countries WHERE country_key = ?", (country_key,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_taken_country_keys():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT country_key FROM countries WHERE country_key IS NOT NULL")
    rows = cur.fetchall()
    conn.close()
    return {r["country_key"] for r in rows}


def delete_country_by_id(country_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM countries WHERE id = ?", (country_id,))
    if not cur.fetchone():
        conn.close()
        return False
    cur.execute("DELETE FROM country_assets WHERE country_id = ?", (country_id,))
    cur.execute("DELETE FROM equipment WHERE country_id = ?", (country_id,))
    cur.execute("DELETE FROM transactions WHERE country_id = ?", (country_id,))
    cur.execute("DELETE FROM countries WHERE id = ?", (country_id,))
    conn.commit()
    conn.close()
    return True


def delete_country_by_player(player_id: int) -> bool:
    country = get_country_by_player(player_id)
    if not country:
        return False
    return delete_country_by_id(country["id"])


def get_country_by_player(player_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM countries WHERE player_id = ?", (player_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        c = dict(row)
        if c.get("country_key"):
            seed_country_assets(c["id"], c["country_key"])
        return c
    return None


def get_all_countries():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM countries ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_country_field(country_id: int, field: str, value):
    allowed = {
        "population", "treasury", "tax_income", "daily_income", "gold", "gold_daily",
        "oil_reserves", "oil_production", "grain", "electricity",
        "active_personnel", "reserve_personnel", "last_income_date", "name", "flag",
        "approval_rating", "grain_daily", "tech_level",
        "combat_readiness", "last_drill_date", "daily_drill_count", "username", "country_key", "player_id",
        "last_blockade_date"
    }
    if field not in allowed:
        raise ValueError(f"فیلد غیرمجاز: {field}")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE countries SET {field} = ? WHERE id = ?", (value, country_id))
    conn.commit()
    conn.close()


def adjust_treasury(country_id: int, delta: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET treasury = treasury + ? WHERE id = ?", (delta, country_id))
    conn.commit()
    conn.close()


def adjust_gold(country_id: int, delta: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET gold = gold + ? WHERE id = ?", (delta, country_id))
    conn.commit()
    conn.close()


def adjust_oil(country_id: int, delta: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET oil_reserves = oil_reserves + ? WHERE id = ?", (delta, country_id))
    conn.commit()
    conn.close()


def adjust_oil_production(country_id: int, delta: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET oil_production = oil_production + ? WHERE id = ?", (delta, country_id))
    conn.commit()
    conn.close()


# ---------- همگام‌سازی و به‌روزرسانی کلی کشورها ----------

def sync_all_country_assets_to_catalog():
    """به‌روزرسانی همگام‌سازی تجهیزات کاتالوگ بدون دست‌زدن به ذخایر اقتصادی و خریدهای قبلی بازیکنان."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM countries")
    rows = cur.fetchall()

    for r in rows:
        c = dict(r)
        c_id = c["id"]
        c_key = c["country_key"]
        if not c_key:
            continue

        catalog = config.COUNTRY_EQUIPMENT_CATALOG.get(c_key, config.DEFAULT_COUNTRY_EQUIPMENT)
        for item in catalog:
            producible_val = 1 if item.get("producible", True) else 0
            cur.execute("""
                INSERT INTO country_assets
                (country_id, country_key, category, equipment_name, equipment_key, amount, buy_price, maintenance_cost, producible)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(country_id, equipment_key) DO UPDATE SET
                category = excluded.category,
                equipment_name = excluded.equipment_name,
                buy_price = excluded.buy_price,
                maintenance_cost = excluded.maintenance_cost,
                producible = excluded.producible
            """, (
                c_id, c_key, item["category"], item["name"], item["key"],
                item["initial"], item["price"], item.get("maint", 0), producible_val
            ))

    conn.commit()
    conn.close()


def rebalance_existing_countries_income():
    """به‌روزرسانی و بالانس درآمد روزانه و مالیاتی تمام کشورها بر اساس آخرین مقادیر بالانس‌شده در config."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id, country_key FROM countries")
            countries = cur.fetchall()

            for c in countries:
                c_id = c["id"]
                c_key = c["country_key"]
                
                overrides = config.COUNTRY_STARTING_OVERRIDES.get(c_key, config.STARTING_VALUES)
                base_daily = overrides.get("daily_income", config.STARTING_VALUES["daily_income"])
                base_tax = overrides.get("tax_income", config.STARTING_VALUES["tax_income"])
                base_oil_res = overrides.get("oil_reserves", config.STARTING_VALUES["oil_reserves"])
                base_oil_prod = overrides.get("oil_production", config.STARTING_VALUES["oil_production"])

                cur.execute("SELECT item_key, quantity FROM equipment WHERE country_id = ?", (c_id,))
                eq_rows = cur.fetchall()
                civ_income = 0
                for eq in eq_rows:
                    i_key = eq["item_key"]
                    qty = eq["quantity"]
                    item = config.ALL_SHOP_ITEMS.get(i_key, {})
                    inc = item.get("income_add", 0)
                    if i_key == "oil_refinery":
                        inc = config.get_refinery_effect(c_key).get("income", inc)
                    civ_income += inc * qty

                new_total_daily = base_daily + civ_income

                # نکته بالانس: oil_reserves و oil_production عمداً دست نمی‌خشوند تا
                # خریدهای بازیکن‌ها و خسارت جنگی با ری‌استارت پاک نشود.
                cur.execute("""
                    UPDATE countries SET
                    tax_income = ?,
                    daily_income = ?
                    WHERE id = ?
                """, (base_tax, new_total_daily, c_id))
    except Exception as e:
        print(f"Error rebalancing country incomes: {e}")


def seed_country_assets(country_id: int, country_key: str):
    conn = get_connection()
    cur = conn.cursor()

    catalog = config.COUNTRY_EQUIPMENT_CATALOG.get(country_key, config.DEFAULT_COUNTRY_EQUIPMENT)

    for item in catalog:
        producible_val = 1 if item.get("producible", True) else 0
        cur.execute("""
            INSERT INTO country_assets
            (country_id, country_key, category, equipment_name, equipment_key, amount, buy_price, maintenance_cost, producible)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(country_id, equipment_key) DO UPDATE SET
            category = excluded.category,
            equipment_name = excluded.equipment_name,
            buy_price = excluded.buy_price,
            maintenance_cost = excluded.maintenance_cost,
            producible = excluded.producible
        """, (
            country_id, country_key, item["category"], item["name"], item["key"],
            item["initial"], item["price"], item.get("maint", 0), producible_val
        ))

    conn.commit()
    conn.close()


def get_country_assets(country_id: int, category: str = None, producible_only: bool = False):
    conn = get_connection()
    cur = conn.cursor()

    query = "SELECT * FROM country_assets WHERE country_id = ?"
    params = [country_id]

    if category and category != "all":
        query += " AND category = ?"
        params.append(category)

    if producible_only:
        query += " AND producible = 1"

    query += " ORDER BY category, id ASC"

    cur.execute(query, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_asset_by_key(country_id: int, equipment_key: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM country_assets WHERE country_id = ? AND equipment_key = ?", (country_id, equipment_key))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def buy_country_asset_transaction(country_id: int, equipment_key: str, quantity: int) -> tuple[bool, str, dict]:
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()

            cur.execute("SELECT * FROM country_assets WHERE country_id = ? AND equipment_key = ?", (country_id, equipment_key))
            asset = cur.fetchone()
            if not asset:
                return False, "این تجهیز برای کشور شما تعریف نشده است.", {}

            asset_dict = dict(asset)

            if asset_dict.get("producible", 1) != 1:
                return False, f"⚠️ تجهیز *{asset_dict['equipment_name']}* یک سلاح وارداتی است و کشور شما خط تولید بومی آن را ندارد. امکان خرید مجدد در فروشگاه وجود ندارد.", asset_dict

            total_cost = asset_dict["buy_price"] * quantity

            cur.execute("SELECT treasury FROM countries WHERE id = ?", (country_id,))
            c_row = cur.fetchone()
            if not c_row:
                return False, "کشور یافت نشد.", {}

            if c_row["treasury"] < total_cost:
                return False, f"موجودی خزانه کافی نیست!\nقیمت کل: {total_cost:,} دلار\nموجودی خزانه: {c_row['treasury']:,} دلار", asset_dict

            cur.execute("UPDATE countries SET treasury = treasury - ? WHERE id = ?", (total_cost, country_id))
            cur.execute("UPDATE country_assets SET amount = amount + ? WHERE id = ?", (quantity, asset_dict["id"]))

            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute("""
                INSERT INTO transactions (country_id, type, description, amount, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (country_id, "asset_purchase", f"خرید {asset_dict['equipment_name']} x{quantity}", -total_cost, now_str))

            asset_dict["amount"] += quantity
            return True, "خرید با موفقیت انجام شد.", asset_dict

    except Exception as e:
        return False, f"خطا در دیتابیس: {e}", {}
    finally:
        conn.close()


def set_asset_amount(country_id: int, equipment_key: str, new_amount: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE country_assets SET amount = ? WHERE country_id = ? AND equipment_key = ?",
                (max(0, new_amount), country_id, equipment_key))
    conn.commit()
    conn.close()


# ---------- سیستم خریدهای غیرنظامی ----------

def buy_item_transaction(country_id: int, item_key: str, quantity: int, total_price: int, item_name: str) -> tuple[bool, str]:
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            item = config.ALL_SHOP_ITEMS.get(item_key, {})
            oil_req = item.get("oil_req", 0) * quantity
            income_add = item.get("income_add", 0) * quantity
            elec_add = item.get("elec_add", 0) * quantity
            gold_daily_add = item.get("gold_daily_add", 0) * quantity
            oil_prod_add = item.get("oil_prod_add", 0) * quantity
            grain_daily_add = item.get("grain_daily_add", 0) * quantity
            grain_bonus = item.get("grain_bonus", 0) * quantity

            cur.execute("SELECT treasury, oil_reserves, country_key FROM countries WHERE id = ?", (country_id,))
            row = cur.fetchone()
            if not row:
                return False, "کشور پیدا نشد."

            # تمایز نفتی/غیرنفتی: اثر پالایشگاه به نوع کشور بستگی دارد
            if item_key == "oil_refinery" and row["country_key"]:
                eff = config.get_refinery_effect(row["country_key"])
                income_add = eff["income"] * quantity
                oil_prod_add = eff["oil_prod"] * quantity

            if row["treasury"] < total_price:
                return False, f"موجودی خزانه کافی نیست!\nقیمت کل: {total_price:,} دلار\nخزانه فعلی: {row['treasury']:,} دلار"

            if oil_req > 0 and row["oil_reserves"] < oil_req:
                return False, f"🛢️ ذخیره نفت کافی نیست!\nنفت مورد نیاز برای احداث: {oil_req:,} بشکه\nذخیره موجود: {row['oil_reserves']:,} بشکه"

            cur.execute("""
                UPDATE countries SET
                treasury = treasury - ?,
                oil_reserves = MAX(0, oil_reserves - ?),
                daily_income = daily_income + ?,
                electricity = electricity + ?,
                gold_daily = gold_daily + ?,
                oil_production = oil_production + ?,
                grain_daily = grain_daily + ?,
                grain = grain + ?
                WHERE id = ?
            """, (total_price, oil_req, income_add, elec_add, gold_daily_add, oil_prod_add, grain_daily_add, grain_bonus, country_id))

            cur.execute("SELECT quantity FROM equipment WHERE country_id=? AND item_key=?", (country_id, item_key))
            eq_row = cur.fetchone()
            if eq_row:
                cur.execute("UPDATE equipment SET quantity = quantity + ? WHERE country_id=? AND item_key=?",
                            (quantity, country_id, item_key))
            else:
                cur.execute("INSERT INTO equipment (country_id, item_key, quantity) VALUES (?,?,?)",
                            (country_id, item_key, quantity))

            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute("""
                INSERT INTO transactions (country_id, type, description, amount, created_at)
                VALUES (?,?,?,?,?)
            """, (country_id, "purchase", f"احداث {item_name} x{quantity}", -total_price, now_str))

        return True, "پروژه احداث با موفقیت ثبت گردید."
    except Exception as e:
        return False, f"خطا در دیتابیس: {e}"
    finally:
        conn.close()


def add_equipment(country_id: int, item_key: str, quantity: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT quantity FROM equipment WHERE country_id=? AND item_key=?", (country_id, item_key))
    row = cur.fetchone()
    if row:
        new_qty = max(0, row["quantity"] + quantity)
        cur.execute("UPDATE equipment SET quantity = ? WHERE country_id=? AND item_key=?",
                    (new_qty, country_id, item_key))
    else:
        if quantity > 0:
            cur.execute("INSERT INTO equipment (country_id, item_key, quantity) VALUES (?,?,?)",
                        (country_id, item_key, quantity))
    conn.commit()
    conn.close()


def get_equipment(country_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT item_key, quantity FROM equipment WHERE country_id=? AND quantity > 0", (country_id,))
    rows = cur.fetchall()
    conn.close()
    return {r["item_key"]: r["quantity"] for r in rows}


# ---------- آمار کلی و لاگ‌ها ----------

def get_game_stats():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) as count, SUM(treasury) as total_treasury, SUM(gold) as total_gold, SUM(oil_reserves) as total_oil FROM countries")
    row = cur.fetchone()

    cur.execute("SELECT SUM(amount) as total_assets FROM country_assets")
    asset_row = cur.fetchone()

    conn.close()

    return {
        "countries_count": row["count"] or 0,
        "total_treasury": row["total_treasury"] or 0,
        "total_gold": row["total_gold"] or 0,
        "total_oil": row["total_oil"] or 0,
        "total_equipment": asset_row["total_assets"] or 0,
    }


def add_transaction(country_id: int, type_: str, description: str, amount: int):
    conn = get_connection()
    cur = conn.cursor()
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur.execute("""
        INSERT INTO transactions (country_id, type, description, amount, created_at)
        VALUES (?,?,?,?,?)
    """, (country_id, type_, description, amount, now_str))
    conn.commit()
    conn.close()


def add_log(actor: str, action: str, details: str = ""):
    conn = get_connection()
    cur = conn.cursor()
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur.execute("""
        INSERT INTO logs (actor, action, details, created_at)
        VALUES (?,?,?,?)
    """, (actor, action, details, now_str))
    conn.commit()
    conn.close()


# ---------- درخواست‌های انتخاب کشور جهت تایید ادمین ----------

def create_pending_country_request(player_id: int, first_name: str, last_name: str, username: str, country_key: str) -> int:
    conn = get_connection()
    cur = conn.cursor()
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    cur.execute("DELETE FROM pending_country_requests WHERE player_id = ?", (player_id,))

    cur.execute("""
        INSERT INTO pending_country_requests (player_id, first_name, last_name, username, country_key, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
    """, (player_id, first_name, last_name, username, country_key, now_str))
    req_id = cur.lastrowid
    conn.commit()
    conn.close()
    return req_id


def get_pending_country_request(request_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM pending_country_requests WHERE id = ?", (request_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_pending_request_by_player(player_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM pending_country_requests WHERE player_id = ? AND status = 'pending'", (player_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_pending_country_requests():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM pending_country_requests WHERE status = 'pending' ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_pending_country_request(request_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM pending_country_requests WHERE id = ?", (request_id,))
    conn.commit()
    conn.close()


def get_taken_and_pending_country_keys():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT country_key FROM countries WHERE country_key IS NOT NULL")
    taken_rows = cur.fetchall()

    cur.execute("SELECT country_key FROM pending_country_requests WHERE status = 'pending'")
    pending_rows = cur.fetchall()
    conn.close()

    keys = {r["country_key"] for r in taken_rows}
    keys.update({r["country_key"] for r in pending_rows})
    return keys


# ---------- سیستم دیپلماسی و معاهدات بین‌المللی ----------

def _ordered_pair(c1_id: int, c2_id: int):
    return (min(c1_id, c2_id), max(c1_id, c2_id))


def get_diplomatic_relation(c1_id: int, c2_id: int) -> dict:
    if c1_id == c2_id:
        return {"status": "self", "sanctioned_by": 0}
    c_min, c_max = _ordered_pair(c1_id, c2_id)
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM diplomatic_relations WHERE country1_id = ? AND country2_id = ?", (c_min, c_max))
    row = cur.fetchone()
    conn.close()
    if row:
        return dict(row)
    return {"status": "normal", "sanctioned_by": 0}


def set_diplomatic_relation(c1_id: int, c2_id: int, status: str, sanctioned_by: int = 0):
    c_min, c_max = _ordered_pair(c1_id, c2_id)
    conn = get_connection()
    cur = conn.cursor()
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur.execute("""
        INSERT INTO diplomatic_relations (country1_id, country2_id, status, sanctioned_by, created_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(country1_id, country2_id) DO UPDATE SET
        status = excluded.status,
        sanctioned_by = excluded.sanctioned_by
    """, (c_min, c_max, status, sanctioned_by, now_str))
    conn.commit()
    conn.close()


def are_sanctioned(c1_id: int, c2_id: int) -> bool:
    rel = get_diplomatic_relation(c1_id, c2_id)
    return rel.get("status") == "sanctioned"


def create_trade_contract(proposer_id: int, recipient_id: int, offered_type: str, offered_amount: int, requested_type: str, requested_amount: int, transport_payer: str = "seller", transport_cost: int = 0, offered_key: str = None, transport_mode: str = "sea") -> int:
    conn = get_connection()
    cur = conn.cursor()
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur.execute("""
        INSERT INTO trade_contracts
        (proposer_id, recipient_id, offered_type, offered_key, offered_amount, requested_type, requested_amount, transport_payer, transport_cost, transport_mode, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
    """, (proposer_id, recipient_id, offered_type, offered_key, offered_amount, requested_type, requested_amount, transport_payer, transport_cost, transport_mode, now_str))
    contract_id = cur.lastrowid
    conn.commit()
    conn.close()
    return contract_id


def get_trade_contract(contract_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM trade_contracts WHERE id = ?", (contract_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def update_contract_status(contract_id: int, status: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE trade_contracts SET status = ? WHERE id = ?", (status, contract_id))
    conn.commit()
    conn.close()


def execute_trade_contract_transaction(contract_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM trade_contracts WHERE id = ?", (contract_id,))
            contract = cur.fetchone()
            if not contract:
                return False, "قرارداد یافت نشد."

            c = dict(contract)
            if c["status"] != "pending":
                return False, "این قرارداد قبلاً تعیین تکلیف شده است."

            p_id = c["proposer_id"]
            r_id = c["recipient_id"]

            cur.execute("SELECT * FROM countries WHERE id = ?", (p_id,))
            prop_c = cur.fetchone()
            cur.execute("SELECT * FROM countries WHERE id = ?", (r_id,))
            recip_c = cur.fetchone()

            if not prop_c or not recip_c:
                return False, "یکی از طرفین قرارداد یافت نشد."

            p_c = dict(prop_c)
            r_c = dict(recip_c)

            c_min, c_max = _ordered_pair(p_id, r_id)
            cur.execute("SELECT status FROM diplomatic_relations WHERE country1_id = ? AND country2_id = ?", (c_min, c_max))
            rel_row = cur.fetchone()
            if rel_row and rel_row["status"] == "sanctioned":
                return False, "امکان انعقاد قرارداد یا انتقال تجهیزات با کشور تحریم‌شده وجود ندارد."

            t_mode = c.get("transport_mode", "sea") or "sea"
            if t_mode == "sea":
                if is_country_blockaded(p_id) or is_country_blockaded(r_id):
                    return False, "⚓ **امکان اجرای معاهده از طریق ترابری دریایی وجود ندارد:** خطوط مواصلاتی دریایی یکی از دو کشور تحت محاصره کامل دریایی است. لطفا برای این معاهده از ترابری هوایی یا زمینی استفاده بفرمایید."

                # Check Strait Blockades & Tolls
                for owner_key, strait_info in STRAITS_MAPPING.items():
                    s_key = strait_info["strait_key"]
                    st_data = get_strait_status(s_key)
                    st_status = st_data["status"]
                    st_toll = st_data["toll"]

                    p_c_key = p_c.get("country_key")
                    r_c_key = r_c.get("country_key")

                    if p_c_key in strait_info["affected_keys"] or r_c_key in strait_info["affected_keys"]:
                        if st_status == "blocked" and owner_key not in [p_c_key, r_c_key]:
                            owner_c = get_country_by_key(owner_key)
                            owner_name = owner_c["name"] if owner_c else owner_key
                            return False, f"⛔ **امکان ترانزیت دریایی وجود ندارد:** {strait_info['name']} توسط کشور {owner_name} مسدود گردیده است!\n\n💡 برای عبور موفق از این تنگه، باید معاهده با **ترابری هوایی** یا **زمینی** صادر شود."

                        elif st_status == "toll" and owner_key not in [p_c_key, r_c_key]:
                            owner_c = get_country_by_key(owner_key)
                            if owner_c:
                                if p_c["treasury"] >= st_toll:
                                    cur.execute("UPDATE countries SET treasury = treasury - ? WHERE id = ?", (st_toll, p_id))
                                    cur.execute("UPDATE countries SET treasury = treasury + ? WHERE id = ?", (st_toll, owner_c["id"]))
                                    p_c["treasury"] -= st_toll
                                    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
                                    cur.execute("INSERT INTO transactions (country_id, type, description, amount, created_at) VALUES (?, 'strait_toll', ?, ?, ?)", (owner_c["id"], f"دریافت عوارض ترانزیت {strait_info['name']} از معاهده {p_c['name']} و {r_c['name']}", st_toll, now_str))
                                else:
                                    return False, f"⛔ **امکان پرداخت عوارض وجود ندارد:** خزانه کشور {p_c['name']} برای پرداخت عوارض ترانزیت {strait_info['name']} ({format_money(st_toll)}) کافی نیست."

            off_type = c["offered_type"]
            off_key = c.get("offered_key")
            off_amt = c["offered_amount"]
            req_type = c["requested_type"]
            req_amt = c["requested_amount"]
            t_payer = c["transport_payer"]
            t_cost = c["transport_cost"]

            p_extra_cost = t_cost if t_payer == "seller" else 0
            r_extra_cost = t_cost if t_payer == "buyer" else 0

            col_map = {"treasury": "treasury", "gold": "gold", "oil": "oil_reserves", "grain": "grain"}

            # Handle Military Asset Transfer
            if off_type == "military_asset":
                cur.execute("SELECT * FROM country_assets WHERE country_id = ? AND equipment_key = ?", (p_id, off_key))
                asset_row = cur.fetchone()
                if not asset_row or asset_row["amount"] < off_amt:
                    return False, f"کشور پیشنهاددهنده ({p_c['name']}) موجودی کافی از این تجهیز برای انتقال ندارد."

                asset_dict = dict(asset_row)

                r_total_needed = req_amt + r_extra_cost
                if r_c["treasury"] < r_total_needed:
                    return False, f"کشور خریدار ({r_c['name']}) موجودی کافی در خزانه برای پرداخت قیمت و ترانزیت ندارد."

                if p_extra_cost > 0 and p_c["treasury"] < p_extra_cost:
                    return False, f"کشور فروشنده ({p_c['name']}) موجودی کافی برای پرداخت ترانزیت ندارد."

                # 1. Deduct asset from proposer
                cur.execute("UPDATE country_assets SET amount = amount - ? WHERE id = ?", (off_amt, asset_dict["id"]))

                # 2. Add asset to recipient (producible=0)
                cur.execute("""
                    INSERT INTO country_assets
                    (country_id, country_key, category, equipment_name, equipment_key, amount, buy_price, maintenance_cost, producible)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                    ON CONFLICT(country_id, equipment_key) DO UPDATE SET amount = amount + ?
                """, (r_id, r_c["country_key"], asset_dict["category"], asset_dict["equipment_name"], off_key, off_amt, asset_dict["buy_price"], asset_dict["maintenance_cost"], off_amt))

                # 3. Transfer price from recipient to proposer
                if req_amt > 0:
                    cur.execute("UPDATE countries SET treasury = treasury + ? WHERE id = ?", (req_amt, p_id))
                    cur.execute("UPDATE countries SET treasury = treasury - ? WHERE id = ?", (req_amt, r_id))

                # 4. Deduct transport costs
                if p_extra_cost > 0:
                    cur.execute("UPDATE countries SET treasury = treasury - ? WHERE id = ?", (p_extra_cost, p_id))
                if r_extra_cost > 0:
                    cur.execute("UPDATE countries SET treasury = treasury - ? WHERE id = ?", (r_extra_cost, r_id))

                cur.execute("UPDATE trade_contracts SET status = 'accepted' WHERE id = ?", (contract_id,))

                now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
                cur.execute("""
                    INSERT INTO transactions (country_id, type, description, amount, created_at)
                    VALUES (?, 'asset_transfer_out', ?, ?, ?)
                """, (p_id, f"انتقال نظامی {asset_dict['equipment_name']} x{off_amt} به {r_c['name']}", req_amt, now_str))
                cur.execute("""
                    INSERT INTO transactions (country_id, type, description, amount, created_at)
                    VALUES (?, 'asset_transfer_in', ?, ?, ?)
                """, (r_id, f"دریافت تسلیحات نظامی {asset_dict['equipment_name']} x{off_amt} از {p_c['name']}", -req_amt, now_str))

                return True, "معاهده انتقال تسلیحات نظامی با موفقیت اجرا شد."

            p_off_col = col_map.get(off_type, "treasury")
            r_req_col = col_map.get(req_type, "treasury")

            p_avail = p_c[p_off_col] - (p_extra_cost if p_off_col == "treasury" else 0)
            if p_avail < off_amt:
                return False, f"طرف پیشنهاددهنده ({p_c['name']}) موجودی کافی برای اجرای قرارداد ندارد."

            r_avail = r_c[r_req_col] - (r_extra_cost if r_req_col == "treasury" else 0)
            if r_avail < req_amt:
                return False, f"طرف قبول‌کننده ({r_c['name']}) موجودی کافی برای اجرای قرارداد ندارد."

            cur.execute(f"UPDATE countries SET {p_off_col} = {p_off_col} - ? WHERE id = ?", (off_amt, p_id))
            cur.execute(f"UPDATE countries SET {r_req_col} = {r_req_col} + ? WHERE id = ?", (req_amt, p_id))
            if p_extra_cost > 0:
                cur.execute("UPDATE countries SET treasury = treasury - ? WHERE id = ?", (p_extra_cost, p_id))

            cur.execute(f"UPDATE countries SET {r_req_col} = {r_req_col} - ? WHERE id = ?", (req_amt, r_id))
            cur.execute(f"UPDATE countries SET {p_off_col} = {p_off_col} + ? WHERE id = ?", (off_amt, r_id))
            if r_extra_cost > 0:
                cur.execute("UPDATE countries SET treasury = treasury - ? WHERE id = ?", (r_extra_cost, r_id))

            cur.execute("UPDATE trade_contracts SET status = 'accepted' WHERE id = ?", (contract_id,))

            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute("""
                INSERT INTO transactions (country_id, type, description, amount, created_at)
                VALUES (?, 'trade', ?, ?, ?)
            """, (p_id, f"قرارداد تجاری با {r_c['name']}", -off_amt if off_type == "treasury" else 0, now_str))
            cur.execute("""
                INSERT INTO transactions (country_id, type, description, amount, created_at)
                VALUES (?, 'trade', ?, ?, ?)
            """, (r_id, f"قرارداد تجاری با {p_c['name']}", req_amt if req_type == "treasury" else 0, now_str))

            return True, "قرارداد تجاری با موفقیت اجرا شد."
    except Exception as e:
        return False, f"خطا در اجرای قرارداد: {e}"


def execute_foreign_aid_transaction(donor_id: int, recipient_id: int, resource_type: str, amount: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()

            if are_sanctioned(donor_id, recipient_id):
                return False, "امکان ارسال کمک به کشور تحریم‌شده یا کشوری که شما را تحریم کرده وجود ندارد."

            cur.execute("SELECT * FROM countries WHERE id = ?", (donor_id,))
            donor_c = cur.fetchone()
            cur.execute("SELECT * FROM countries WHERE id = ?", (recipient_id,))
            recip_c = cur.fetchone()

            if not donor_c or not recip_c:
                return False, "کشور اهداکننده یا دریافت‌کننده یافت نشد."

            d_c = dict(donor_c)
            r_c = dict(recip_c)

            col_map = {"treasury": "treasury", "gold": "gold", "oil": "oil_reserves", "grain": "grain"}
            col_name = col_map.get(resource_type, "treasury")

            if d_c[col_name] < amount:
                return False, f"موجودی {resource_type} کشور شما برای ارسال این کمک کافی نیست."

            cur.execute(f"UPDATE countries SET {col_name} = {col_name} - ? WHERE id = ?", (amount, donor_id))
            cur.execute(f"UPDATE countries SET {col_name} = {col_name} + ? WHERE id = ?", (amount, recipient_id))

            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute("""
                INSERT INTO transactions (country_id, type, description, amount, created_at)
                VALUES (?, 'aid_out', ?, ?, ?)
            """, (donor_id, f"ارسال کمک خارجی به {r_c['name']}", -amount if resource_type == "treasury" else 0, now_str))
            cur.execute("""
                INSERT INTO transactions (country_id, type, description, amount, created_at)
                VALUES (?, 'aid_in', ?, ?, ?)
            """, (recipient_id, f"دریافت کمک خارجی از {d_c['name']}", amount if resource_type == "treasury" else 0, now_str))

            cur.execute("""
                INSERT INTO logs (actor, action, details, created_at)
                VALUES (?, 'foreign_aid', ?, ?)
            """, (str(donor_id), f"Aid {resource_type} x{amount} to {recipient_id}", now_str))

            return True, "کمک خارجی با موفقیت ارسال شد."
    except Exception as e:
        return False, f"خطا در ارسال کمک: {e}"


# ---------- تنظیمات پویا ----------

def get_setting(key: str, default_val: str = None) -> str:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = cur.fetchone()
    conn.close()
    if row and row["value"]:
        return row["value"]
    return default_val


def set_setting(key: str, value: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO settings (key, value) VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, str(value)))
    conn.commit()
    conn.close()


# ---------- سیستم محاصره دریایی بین‌المللی ----------

def has_open_sea_access(country_key: str) -> bool:
    """آیا کشور به آب‌های آزاد/اقیانوس دسترسی دارد (قابل شرکت در محاصره دریایی)؟"""
    if not country_key:
        return True
    return country_key not in config.NO_SEA_ACCESS_COUNTRIES


def create_naval_blockade(blockader_id: int, target_id: int) -> int:
    conn = get_connection()
    cur = conn.cursor()
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur.execute("""
        INSERT INTO naval_blockades (blockader_id, target_id, status, created_at)
        VALUES (?, ?, 'active', ?)
        ON CONFLICT(blockader_id, target_id) DO UPDATE SET status = 'active'
    """, (blockader_id, target_id, now_str))
    blockade_id = cur.lastrowid
    conn.commit()
    conn.close()
    return blockade_id


def is_country_blockaded(country_id: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM naval_blockades WHERE target_id = ? AND status = 'active'", (country_id,))
    row = cur.fetchone()
    conn.close()
    return bool(row)


def get_all_active_blockades() -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM naval_blockades WHERE status = 'active'")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_active_blockades_for_country(country_id: int) -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM naval_blockades WHERE (target_id = ? OR blockader_id = ?) AND status = 'active'", (country_id, country_id))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def lift_naval_blockade(blockader_id: int, target_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE naval_blockades SET status = 'lifted' WHERE blockader_id = ? AND target_id = ? AND status = 'active'", (blockader_id, target_id))
    conn.commit()
    conn.close()


def break_naval_blockade(target_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE naval_blockades SET status = 'broken' WHERE target_id = ? AND status = 'active'", (target_id,))
    conn.commit()
    conn.close()


ANTISHIP_TOKENS = (
    "antiship", "noor", "qader", "qadir", "harpoon", "exocet", "yakhont",
    "cruise", "khalij", "mandab", "almandab", "bahr", "onslow", "neptune",
)


def _is_antiship_key(name: str) -> bool:
    n = (name or "").lower()
    return any(t in n for t in ANTISHIP_TOKENS)


def get_antiship_missile_stock(country_id: int) -> int:
    """مجموع موشک‌های ضدکشتی/کروز دریایی موجود در انبار کشور (برای نبرد شکستن محاصره)."""
    assets = get_country_assets(country_id, category="Missiles")
    total = 0
    for a in assets:
        if _is_antiship_key(a.get("equipment_key")) or _is_antiship_key(a.get("equipment_name")):
            total += a.get("amount") or 0
    return total


def consume_antiship_missiles(country_id: int, qty: int) -> int:
    """کسر qty موشک ضدکشتی از انبار کشور (از تجهیزات دارای موجودی). خروجی: تعداد واقعی کسرشده."""
    if qty <= 0:
        return 0
    assets = get_country_assets(country_id, category="Missiles")
    targets = [
        a for a in assets
        if (_is_antiship_key(a.get("equipment_key")) or _is_antiship_key(a.get("equipment_name")))
        and (a.get("amount") or 0) > 0
    ]
    remaining = qty
    consumed = 0
    for a in targets:
        if remaining <= 0:
            break
        amt = a["amount"]
        take = min(amt, remaining)
        set_asset_amount(country_id, a["equipment_key"], amt - take)
        remaining -= take
        consumed += take
    return consumed


def get_country_transactions(country_id: int, limit: int = 20) -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM transactions WHERE country_id = ? ORDER BY id DESC LIMIT ?", (country_id, limit))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_diplomatic_logs(limit: int = 20) -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM transactions WHERE type IN ('trade', 'aid_out', 'aid_in', 'asset_transfer_out', 'asset_transfer_in') ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_recent_logs(limit: int = 20) -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_country_rankings() -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM countries ORDER BY treasury DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def calculate_naval_power(country_id: int) -> int:
    """محاسبه متوازن و واقعی امتیاز قدرت رزمی نیروی دریایی آب‌های آزاد."""
    assets = get_country_assets(country_id, category="Navy")
    if not assets:
        return 0

    total_power = 0
    for a in assets:
        eq_name = a["equipment_name"].lower()
        amount = a["amount"]
        if amount <= 0:
            continue

        # گارد: شناورهای سبک/گشتی/تندرو نباید با نام مشابه ناوهای بزرگ اشتباه گرفته شوند
        # (مثلاً قایق گشتی Wasp نباید با ناو بالگردبر Wasp کلاس اشتباه شود)
        if any(t in eq_name for t in ["boat", "craft", "شناور", "قایق", "تندرو", "گشتی", "patrol", "موشک‌انداز", "موشک انداز"]):
            total_power += int(amount * 0.2)
            continue

        if any(c in eq_name for c in ["ford", "nimitz", "fujian", "shandong", "liaoning", "kuznetsov", "charles de gaulle", "queen elizabeth", "carrier", "هواپیمابر"]):
            total_power += int(amount * 500)
        elif any(l in eq_name for l in ["america", "wasp", "dokdo", "anadolu", "trieste", "lha", "lhd", "lph", "بالگردبر", "ناو بالگردبر"]):
            total_power += int(amount * 200)
        elif any(d in eq_name for d in ["destroyer", "burke", "zumwalt", "ticonderoga", "cruiser", "type 055", "type 052", "type 45", "visakhapatnam", "kirov", "gorshkov", "slava", "maya", "atago", "kongo", "sejong", "کلاس کیروف", "رزم‌پناو", "ناوشکن"]):
            total_power += int(amount * 80)
        elif any(s in eq_name for s in ["virginia", "ohio", "los angeles", "seawolf", "yasen", "borei", "type 094", "type 093", "astute", "vanguard", "suffren", "arihant", "dreadnought", "ssn", "ssbn", "هسته‌ای"]):
            total_power += int(amount * 70)
        elif any(f in eq_name for f in ["frigate", "constellation", "fremm", "f125", "f124", "type 054", "gotland", "type 214", "dolphin", "halifax", "hobart", "miecznik", "perry", "برگامینی", "جماران", "سهند", "دنا", "دماوند", "ناوچه"]):
            total_power += int(amount * 30)
        elif any(c in eq_name for c in ["corvette", "buyan", "steregushchiy", "sa'ar", "baynunah", "soleimani", "شهید سلیمانی", "فاتح", "پیروز"]):
            total_power += int(amount * 12)
        elif any(s in eq_name for s in ["sub", "kilo", "ghadir", "midget", "زیردریایی"]):
            total_power += int(amount * 10)
        else:
            total_power += int(amount * 0.2)

    return total_power


# ---------- مصرف سوخت روزانه نیروهای مسلح (واقع‌گرایی اقتصادی) ----------

def _fuel_per_unit(equipment_name: str, category: str) -> int:
    """برآورد مصرف سوخت روزانه هر واحد تجهیز نظامی (بشکه/روز)."""
    n = (equipment_name or "").lower()
    if category == "Navy":
        if any(k in n for k in ["carrier", "هواپیمابر", "بالگردبر", "lhd", "lha", "lph"]):
            return 500
        if any(k in n for k in ["destroyer", "cruiser", "ناوشکن", "رزم‌ناو", "aegis", "ایجیس"]):
            return 300
        if any(k in n for k in ["frigate", "ناوچه", "corvette", "کوروت", "برگامینی"]):
            return 100
        if any(k in n for k in ["sub", "زیردریایی"]):
            return 50
        return 10
    if category == "Aircraft":
        if any(k in n for k in ["heli", "بالگرد", "chinook", "apache", "cobra", "ka-52", "mi-28", "mi-35", "شینوک", "طوفان", "mi-8", "mi-17", "mi8", "mi17"]):
            return 8
        if any(k in n for k in ["transport", "ترابری", "c-130", "c-17", "il-76", "a400m", "awacs", "tanker", "سوخت‌رسان", "c-390", "c-295"]):
            return 25
        return 20
    if category == "Ground Forces":
        if any(k in n for k in ["tank", "تانک", "abrams", "leopard", "merkava", "challenger", "armata", "type 99", "type 90", "type 10", "t-90", "t-80", "t-72", "t-64", "t-62", "t-55"]):
            return 12
        return 4
    if category == "Artillery":
        return 3
    if category == "Air Defense":
        return 2
    if category == "UAV":
        return 1
    return 0


def calculate_military_fuel_consumption(country_id: int) -> int:
    """مجموع مصرف سوخت روزانه نیروهای مسلح کشور (بشکه/روز)."""
    assets = get_country_assets(country_id)
    total = 0
    for a in assets:
        amt = a.get("amount") or 0
        if amt <= 0:
            continue
        total += amt * _fuel_per_unit(a.get("equipment_name"), a.get("category"))
    return total


def sell_oil_to_global_market(country_id: int, amount: int) -> tuple[bool, str]:
    """فروش مستقیم نفت خام به بازار جهانی با قیمت کف (OIL_GLOBAL_PRICE)."""
    if amount <= 0:
        return False, "مقدار نفت باید بزرگ‌تر از صفر باشد."
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT oil_reserves, treasury FROM countries WHERE id = ?", (country_id,))
            row = cur.fetchone()
            if not row:
                return False, "کشور یافت نشد."
            if (row["oil_reserves"] or 0) < amount:
                return False, f"ذخیره نفت کافی نیست! (موجودی فعلی: {(row['oil_reserves'] or 0):,} بشکه)"
            revenue = amount * config.OIL_GLOBAL_PRICE
            cur.execute(
                "UPDATE countries SET oil_reserves = oil_reserves - ?, treasury = treasury + ? WHERE id = ?",
                (amount, revenue, country_id),
            )
            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute(
                "INSERT INTO transactions (country_id, type, description, amount, created_at) VALUES (?,?,?,?,?)",
                (country_id, "oil_export", f"صادرات نفت به بازار جهانی ({amount:,} بشکه × {config.OIL_GLOBAL_PRICE:,} $)", revenue, now_str),
            )
        return True, f"{revenue}"
    except Exception as e:
        return False, f"خطا در فروش به بازار جهانی: {e}"


def has_active_oil_import_contract(country_id: int) -> bool:
    """بررسی وجود قرارداد فعال واردات نفت خام برای کشورهای صنعتی فاقد نفت."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as count FROM trade_contracts WHERE recipient_id = ? AND offered_type = 'oil' AND status = 'accepted'", (country_id,))
    row = cur.fetchone()
    conn.close()
    return bool(row and row["count"] > 0)


def get_industrial_oil_consumption(country_id: int) -> int:
    """محاسبه مصرف روزانه سوخت صنعتی نیروگاه‌ها و کارخانجات کشور."""
    equipment = get_equipment(country_id)
    fossil_count = equipment.get("fossil_plant", 0)
    factories_count = equipment.get("small_factory", 0) + equipment.get("medium_factory", 0) + equipment.get("large_factory", 0) + equipment.get("industrial_complex", 0)
    refinery_count = equipment.get("oil_refinery", 0)

    ind_oil_need = (fossil_count * 200_000) + (factories_count * 50_000) + (refinery_count * 300_000)
    return ind_oil_need


def calculate_country_maintenance_cost(country_id: int) -> dict:
    """محاسبه متوازن هزینه نگهداری روزانه تسلیحات و ارتش با تخفیف سطح فناوری (Tech Level)."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT active_personnel, tech_level FROM countries WHERE id = ?", (country_id,))
    c_row = cur.fetchone()
    if not c_row:
        conn.close()
        return {"assets_maint": 0, "personnel_maint": 0, "total_maint": 0, "discount_pct": 0, "tech_level": 1}

    active_p = c_row["active_personnel"] or 0
    tech_lvl = c_row["tech_level"] or 1

    discount_pct = min(40, (tech_lvl - 1) * 10)

    cur.execute("SELECT amount, maintenance_cost FROM country_assets WHERE country_id = ? AND amount > 0", (country_id,))
    asset_rows = cur.fetchall()
    conn.close()

    raw_assets_maint = sum(r["amount"] * (r["maintenance_cost"] or 0) for r in asset_rows)
    scaled_maint = int(raw_assets_maint * 0.01)  # بالانس v2: نصف شدن هزینه نگهداری
    assets_maint = int(scaled_maint * (1 - (discount_pct / 100.0)))

    personnel_maint = int(active_p * 0.5)
    total_maint = assets_maint + personnel_maint

    return {
        "assets_maint": assets_maint,
        "personnel_maint": personnel_maint,
        "total_maint": total_maint,
        "discount_pct": discount_pct,
        "tech_level": tech_lvl
    }


# ---------- سیستم ثبت و بررسی رول‌های نظامی (Roleplay System) ----------

def create_pending_roleplay(country_id: int, player_id: int, role_type: str, role_text: str) -> int:
    conn = get_connection()
    cur = conn.cursor()
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    now_str = now_dt.isoformat()
    today_str = datetime.date.today().isoformat()

    cur.execute("""
        INSERT INTO pending_roleplays (country_id, player_id, role_type, role_text, status, created_at, created_date)
        VALUES (?, ?, ?, ?, 'pending', ?, ?)
    """, (country_id, player_id, role_type, role_text, now_str, today_str))
    role_id = cur.lastrowid
    conn.commit()
    conn.close()
    return role_id


def get_daily_roleplay_count(country_id: int, today_str: str) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as count FROM pending_roleplays WHERE country_id = ? AND created_date = ?", (country_id, today_str))
    row = cur.fetchone()
    conn.close()
    return row["count"] if row else 0


def get_pending_roleplays() -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM pending_roleplays WHERE status = 'pending' ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_roleplay_by_id(role_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM pending_roleplays WHERE id = ?", (role_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_country_roleplays(country_id: int) -> list:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM pending_roleplays WHERE country_id = ? ORDER BY id DESC LIMIT 10", (country_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_roleplay_status(role_id: int, status: str):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE pending_roleplays SET status = ? WHERE id = ?", (status, role_id))
    conn.commit()
    conn.close()


STRAITS_MAPPING = {
    "iran": {
        "strait_key": "hormuz",
        "name": "تنگه استراتژیک هرمز",
        "desc": "شریان حیاتی انرژی خلیج فارس (مسیر اصلی صادرات نفت امارات، قطر، عربستان، کویت، عراق و بحرین)",
        "affected_keys": ["uae", "qatar", "saudi", "iraq", "kuwait", "bahrain", "israel"]
    },
    "oman": {
        "strait_key": "hormuz_south",
        "name": "تنگه هرمز و دریای عمان (ضلع جنوبی)",
        "desc": "شاهراه ترانزیت نفت خلیج فارس به اقیانوس هند",
        "affected_keys": ["uae", "qatar", "saudi", "iraq", "kuwait", "bahrain", "iran"]
    },
    "egypt": {
        "strait_key": "suez",
        "name": "کانال استراتژیک سوئز",
        "desc": "شاهراه ترانزیت دریایی آسیا به اروپا و دریای مدیترانه",
        "affected_keys": ["uk", "france", "germany", "italy", "india", "china", "israel", "jordan"]
    },
    "yemen": {
        "strait_key": "bab_el_mandeb",
        "name": "تنگه استراتژیک باب‌المندب و دریای سرخ",
        "desc": "گلوگاه ترانزیت دریای سرخ و باب‌المندب (کلید امنیت کشتیرانی تجاری به کانال سوئز)",
        "affected_keys": ["israel", "usa", "uk", "france", "germany", "egypt", "saudi", "jordan"]
    },
    "turkey": {
        "strait_key": "bosphorus",
        "name": "تنگه بسفر و دردانل (پیمان مونترو)",
        "desc": "دروازه انحصاری عبور و مرور دریای سیاه به آب‌های آزاد",
        "affected_keys": ["russia", "ukraine", "poland"]
    },
    "india": {
        "strait_key": "malacca",
        "name": "تنگه مالاکا و اقیانوس هند",
        "desc": "مسیر اصلی ترانزیت انرژی و تجارت شرق آسیا",
        "affected_keys": ["china", "japan", "south_korea", "taiwan"]
    },
    "china": {
        "strait_key": "taiwan_strait_cn",
        "name": "تنگه تایوان",
        "desc": "گلوگاه ترانزیت دریای چین جنوبی",
        "affected_keys": ["taiwan", "japan", "usa", "south_korea"]
    },
    "taiwan": {
        "strait_key": "taiwan_strait_tw",
        "name": "تنگه تایوان (ضلع شرقی)",
        "desc": "خط ترانزیت و پدافند دریایی تایوان",
        "affected_keys": ["china"]
    }
}


def get_strait_info_by_country_key(country_key: str):
    return STRAITS_MAPPING.get(country_key)


def get_strait_status(strait_key: str) -> dict:
    status = get_setting(f"strait_status_{strait_key}", "open")
    toll = int(get_setting(f"strait_toll_{strait_key}", "1000000"))
    return {"status": status, "toll": toll}


def set_strait_status(strait_key: str, status: str, toll_amount: int = 1000000):
    set_setting(f"strait_status_{strait_key}", status)
    set_setting(f"strait_toll_{strait_key}", str(toll_amount))


def delete_roleplay(role_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM pending_roleplays WHERE id = ?", (role_id,))
    conn.commit()
    conn.close()


# ---------- بازار بورس بین‌المللی کالاها (Global Commodities Exchange) ----------

def create_market_order(seller_id: int, resource_type: str, amount: int, unit_price: int) -> tuple[bool, str]:
    """ثبت یک عرضه جدید در بورس کالا. کالا از انبار فروشنده کسر شده و سپرده‌گذاری می‌شود."""
    if amount <= 0 or unit_price <= 0:
        return False, "تعداد و قیمت واحد باید بزرگتر از صفر باشند."

    # قیمت کف بازار جهانی: نفت را نمی‌توان زیر قیمت پایه عرضه کرد
    if resource_type == "oil" and unit_price < config.OIL_GLOBAL_PRICE:
        return False, (
            f"⛔ **قیمت هر بشکه نفت نمی‌تواند کمتر از قیمت کف بازار جهانی باشد.**\n\n"
            f"• قیمت کف بازار جهانی نفت: **{config.OIL_GLOBAL_PRICE:,} $/بشکه**\n"
            f"• قیمت پیشنهادی شما: {unit_price:,} $/بشکه\n\n"
            f"💡 می‌توانید نفت خود را مستقیم با قیمت پایه از گزینه «فروش به بازار جهانی» بفروشید."
        )

    resource_cols = {
        "oil": "oil_reserves",
        "gold": "gold",
        "grain": "grain"
    }
    col = resource_cols.get(resource_type)
    if not col:
        return False, "نوع کالای درخواستی نامعتبر است."

    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(f"SELECT {col} FROM countries WHERE id = ?", (seller_id,))
            row = cur.fetchone()
            if not row:
                return False, "کشور فروشنده یافت نشد."

            current_qty = row[col]
            if current_qty < amount:
                res_names = {"oil": "نفت", "gold": "طلا", "grain": "غلات"}
                return False, f"موجودی {res_names[resource_type]} کافی نیست! (موجودی فعلی: {current_qty:,})"

            cur.execute(f"UPDATE countries SET {col} = {col} - ? WHERE id = ?", (amount, seller_id))

            now_str = datetime.datetime.now().isoformat()
            cur.execute("""
                INSERT INTO market_orders (seller_id, resource_type, amount, unit_price, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (seller_id, resource_type, amount, unit_price, now_str))

        return True, "عرضه با موفقیت در بازار بورس جهانی ثبت گردید."
    except Exception as e:
        return False, f"خطا در ثبت عرضه: {e}"


def get_market_orders(resource_type: str = None) -> list[dict]:
    """دریافت لیست عرضه‌های فعال بورس کالا (مرتب‌شده بر اساس ارزان‌ترین قیمت واحد)."""
    conn = get_connection()
    cur = conn.cursor()

    if resource_type:
        cur.execute("""
            SELECT m.*, c.name as seller_name, c.flag as seller_flag, c.country_key as seller_key
            FROM market_orders m
            JOIN countries c ON m.seller_id = c.id
            WHERE m.resource_type = ? AND m.amount > 0
            ORDER BY m.unit_price ASC, m.id ASC
        """, (resource_type,))
    else:
        cur.execute("""
            SELECT m.*, c.name as seller_name, c.flag as seller_flag, c.country_key as seller_key
            FROM market_orders m
            JOIN countries c ON m.seller_id = c.id
            WHERE m.amount > 0
            ORDER BY m.unit_price ASC, m.id ASC
        """)

    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_market_order_by_id(order_id: int) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT m.*, c.name as seller_name, c.flag as seller_flag, c.country_key as seller_key, c.player_id as seller_player_id
        FROM market_orders m
        JOIN countries c ON m.seller_id = c.id
        WHERE m.id = ?
    """, (order_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_country_market_orders(seller_id: int) -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT * FROM market_orders WHERE seller_id = ? AND amount > 0 ORDER BY id DESC
    """, (seller_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def cancel_market_order(seller_id: int, order_id: int) -> tuple[bool, str]:
    """لغو عرضه فعال بورس و عودت باقی‌مانده کالا به انبار کشور."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM market_orders WHERE id = ? AND seller_id = ?", (order_id, seller_id))
            order = cur.fetchone()
            if not order:
                return False, "سفارش مورد نظر یافت نشد یا متعلق به کشور شما نیست."

            ord_dict = dict(order)
            rem_amount = ord_dict["amount"]
            res_type = ord_dict["resource_type"]

            resource_cols = {"oil": "oil_reserves", "gold": "gold", "grain": "grain"}
            col = resource_cols.get(res_type)

            if col and rem_amount > 0:
                cur.execute(f"UPDATE countries SET {col} = {col} + ? WHERE id = ?", (rem_amount, seller_id))

            cur.execute("DELETE FROM market_orders WHERE id = ?", (order_id,))

        return True, "عرضه با موفقیت لغو شد و کالای باقی‌مانده به انبار کشور عودت داده گردید."
    except Exception as e:
        return False, f"خطا در لغو سفارش: {e}"


def execute_market_buy_transaction(buyer_id: int, order_id: int, buy_amount: int, transport_mode: str = "sea") -> tuple[bool, str, dict]:
    """خرید فوری و مستقیم کالا از بورس جهانی توسط کشور خریدار."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM market_orders WHERE id = ?", (order_id,))
            order_row = cur.fetchone()
            if not order_row:
                return False, "سفارش مورد نظر در بازار بورس یافت نشد یا منقضی شده است.", {}

            order = dict(order_row)
            seller_id = order["seller_id"]

            if seller_id == buyer_id:
                return False, "امکان خرید از عرضه متعلق به کشور خودتان وجود ندارد.", {}

            if buy_amount <= 0 or buy_amount > order["amount"]:
                return False, f"حداکثر مقدار قابل خرید از این عرضه {order['amount']:,} واحد می‌باشد.", {}

            cur.execute("SELECT * FROM countries WHERE id = ?", (seller_id,))
            seller = cur.fetchone()
            cur.execute("SELECT * FROM countries WHERE id = ?", (buyer_id,))
            buyer = cur.fetchone()

            if not seller or not buyer:
                return False, "کشور خریدار یا فروشنده یافت نشد.", {}

            seller_c = dict(seller)
            buyer_c = dict(buyer)

            c_min, c_max = _ordered_pair(seller_id, buyer_id)
            cur.execute("SELECT status FROM diplomatic_relations WHERE country1_id = ? AND country2_id = ?", (c_min, c_max))
            rel_row = cur.fetchone()
            if rel_row and rel_row["status"] == "sanctioned":
                return False, "امکان معامله تجاری با کشور تحریم‌شده وجود ندارد.", {}

            if transport_mode == "sea":
                if is_country_blockaded(seller_id) or is_country_blockaded(buyer_id):
                    return False, "⚓ **ترابری دریایی مسدود است:** یکی از دو کشور تحت محاصره کامل دریایی است. لطفاً از ترابری هوایی یا زمینی استفاده بفرمایید.", {}

                for owner_key, strait_info in STRAITS_MAPPING.items():
                    affected_keys = strait_info.get("affected_keys", [])
                    s_key = seller_c.get("country_key")
                    b_key = buyer_c.get("country_key")
                    if (s_key in affected_keys or b_key in affected_keys) and owner_key not in (s_key, b_key):
                        st_status = get_strait_status(strait_info["strait_key"])
                        if st_status["status"] == "closed":
                            return False, f"⚓ **گلوگاه دریایی مسدود است:** مسیر ترانزیت دریایی از {strait_info['name']} مسدود شده است.", {}

            transport_costs = {"sea": 300_000, "land": 1_000_000, "air": 2_000_000}
            t_cost = transport_costs.get(transport_mode, 300_000)

            unit_price = order["unit_price"]
            commodity_cost = buy_amount * unit_price
            total_buyer_cost = commodity_cost + t_cost

            if buyer_c["treasury"] < total_buyer_cost:
                return False, f"موجودی خزانه کافی نیست!\nارزش کالا: {format_money(commodity_cost)}\nهزینه ترابری: {format_money(t_cost)}\nمجموع هزینه: {format_money(total_buyer_cost)}\nخزانه شما: {format_money(buyer_c['treasury'])}", {}

            res_type = order["resource_type"]
            resource_cols = {"oil": "oil_reserves", "gold": "gold", "grain": "grain"}
            col = resource_cols[res_type]

            cur.execute(f"UPDATE countries SET treasury = treasury - ?, {col} = {col} + ? WHERE id = ?", (total_buyer_cost, buy_amount, buyer_id))
            cur.execute("UPDATE countries SET treasury = treasury + ? WHERE id = ?", (commodity_cost, seller_id))

            rem_amount = order["amount"] - buy_amount
            if rem_amount <= 0:
                cur.execute("DELETE FROM market_orders WHERE id = ?", (order_id,))
            else:
                cur.execute("UPDATE market_orders SET amount = ? WHERE id = ?", (rem_amount, order_id))

            now_str = datetime.datetime.now().isoformat()
            cur.execute("""
                INSERT INTO market_history (seller_id, buyer_id, resource_type, amount, unit_price, total_price, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (seller_id, buyer_id, res_type, buy_amount, unit_price, commodity_cost, now_str))

            res_names = {"oil": "نفت", "gold": "طلا", "grain": "غلات"}
            res_label = res_names.get(res_type, res_type)

            cur.execute("""
                INSERT INTO transactions (country_id, type, description, amount, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (buyer_id, "market_buy", f"خرید {buy_amount:,} واحد {res_label} از بورس جهانی", -total_buyer_cost, now_str))

            cur.execute("""
                INSERT INTO transactions (country_id, type, description, amount, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (seller_id, "market_sell", f"فروش {buy_amount:,} واحد {res_label} در بورس جهانی", commodity_cost, now_str))

            result_meta = {
                "seller": seller_c,
                "buyer": buyer_c,
                "commodity_cost": commodity_cost,
                "transport_cost": t_cost,
                "total_buyer_cost": total_buyer_cost,
                "res_type": res_type,
                "res_label": res_label,
                "buy_amount": buy_amount,
                "unit_price": unit_price
            }

            return True, "معامله بورس با موفقیت انجام شد.", result_meta

    except Exception as e:
        return False, f"خطا در اجرای معامله بورس: {e}", {}


def get_market_stats() -> dict:
    """دریافت آمار کلی حجم معاملات و میانگین قیمت‌های بورس جهانی."""
    conn = get_connection()
    cur = conn.cursor()

    stats = {}
    for r_type in ("oil", "gold", "grain"):
        cur.execute("""
            SELECT COUNT(*) as trade_count, SUM(amount) as total_volume, AVG(unit_price) as avg_price, MIN(unit_price) as min_price, MAX(unit_price) as max_price
            FROM market_history
            WHERE resource_type = ?
        """, (r_type,))
        row = cur.fetchone()
        stats[r_type] = dict(row) if row else {}

        cur.execute("SELECT MIN(unit_price) as lowest_active FROM market_orders WHERE resource_type = ? AND amount > 0", (r_type,))
        low_row = cur.fetchone()
        stats[r_type]["lowest_active"] = low_row["lowest_active"] if low_row and low_row["lowest_active"] else None

    conn.close()
    return stats


# ---------- سازمان ملل متحد (United Nations) ----------

def claim_un_country(admin_player_id: int) -> tuple[bool, str]:
    """فعال‌سازی و واگذاری کشور/نقش سازمان ملل متحد (🇺🇳) اختصاصی ادمین اصلی."""
    conn = get_connection()
    new_un_id = None
    try:
        with conn:
            cur = conn.cursor()
            # بررسی اینکه آیا ادمین قبلاً کشوری دارد یا خیر
            cur.execute("SELECT id, name, country_key FROM countries WHERE player_id = ?", (admin_player_id,))
            existing = cur.fetchone()
            if existing:
                ex_c = dict(existing)
                if ex_c["country_key"] == "un":
                    return False, "نقش سازمان ملل متحد از قبل برای شما فعال است."
                return False, f"شما در حال حاضر هدایت کشور {ex_c['name']} را بر عهده دارید.\nلطفاً ابتدا کشور فعلی خود را با دستور /resetme یا دکمه حذف کشور لغو فرمایید."

            un_overrides = config.COUNTRY_STARTING_OVERRIDES.get("un", {})
            now_str = datetime.datetime.now().isoformat()

            cur.execute("""
                INSERT INTO countries
                (player_id, name, flag, population, treasury, tax_income, daily_income,
                gold, gold_daily, oil_reserves, oil_production, grain, electricity,
                active_personnel, reserve_personnel, created_at, country_key, approval_rating)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                admin_player_id, "سازمان ملل متحد", "🇺🇳",
                un_overrides.get("population", 0), un_overrides.get("treasury", 100_000_000),
                un_overrides.get("tax_income", 0), un_overrides.get("daily_income", 5_000_000),
                un_overrides.get("gold", 1000), un_overrides.get("gold_daily", 0),
                un_overrides.get("oil_reserves", 10_000_000), un_overrides.get("oil_production", 0),
                un_overrides.get("grain", 500_000), un_overrides.get("electricity", 100),
                un_overrides.get("active_personnel", 100_000), un_overrides.get("reserve_personnel", 200_000),
                now_str, "un", un_overrides.get("approval_rating", 95)
            ))

            cur.execute("SELECT id FROM countries WHERE player_id = ?", (admin_player_id,))
            new_un = cur.fetchone()
            if new_un:
                new_un_id = new_un["id"]

        if new_un_id:
            seed_country_assets(new_un_id, "un")

        return True, "🇺🇳 **نقش سازمان ملل متحد با موفقیت برای شما فعال گردید!**"
    except Exception as e:
        return False, f"خطا در فعال‌سازی نقش سازمان ملل: {e}"


def create_un_resolution(title: str, description: str, creator_id: int) -> int:
    """ثبت قطعنامه جدید شورای امنیت سازمان ملل."""
    conn = get_connection()
    cur = conn.cursor()
    now_str = datetime.datetime.now().isoformat()
    cur.execute("""
        INSERT INTO un_resolutions (title, description, creator_id, status, created_at)
        VALUES (?, ?, ?, 'active', ?)
    """, (title, description, creator_id, now_str))
    res_id = cur.lastrowid
    conn.commit()
    conn.close()
    return res_id


def get_un_resolutions(status: str = "active") -> list[dict]:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM un_resolutions WHERE status = ? ORDER BY id DESC", (status,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_un_resolution_by_id(res_id: int) -> dict:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM un_resolutions WHERE id = ?", (res_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def cast_un_vote(resolution_id: int, voter_country_id: int, vote_option: str) -> tuple[bool, str]:
    """ثبت رای کشور در رای‌گیری قطعنامه سازمان ملل."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT status FROM un_resolutions WHERE id = ?", (resolution_id,))
            res = cur.fetchone()
            if not res or res["status"] != "active":
                return False, "این رای‌گیری بسته یا منقضی شده است."

            now_str = datetime.datetime.now().isoformat()
            cur.execute("""
                INSERT INTO un_votes (resolution_id, voter_country_id, vote_option, created_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(resolution_id, voter_country_id) DO UPDATE SET
                vote_option = excluded.vote_option,
                created_at = excluded.created_at
            """, (resolution_id, voter_country_id, vote_option, now_str))

        return True, "رای شما با موفقیت در شورای امنیت ثبت گردید."
    except Exception as e:
        return False, f"خطا در ثبت رای: {e}"


def get_un_resolution_votes(resolution_id: int) -> dict:
    """دریافت آمار رای‌گیری قطعنامه به همراه تفکیک کشورها."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT v.*, c.name, c.flag, c.country_key
        FROM un_votes v
        JOIN countries c ON v.voter_country_id = c.id
        WHERE v.resolution_id = ?
    """, (resolution_id,))
    rows = cur.fetchall()
    conn.close()

    votes = {"yes": [], "no": [], "abstain": []}
    for r in rows:
        v_dict = dict(r)
        opt = v_dict["vote_option"]
        if opt in votes:
            votes[opt].append(v_dict)

    return votes


def close_un_resolution(resolution_id: int, final_status: str) -> bool:
    """بستن یا اعلام نتیجه قطعنامه (passed, vetoed, failed)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE un_resolutions SET status = ? WHERE id = ?", (final_status, resolution_id))
    conn.commit()
    conn.close()
    return True


# ---------- ثبت و بازیابی سناریوهای نبرد ----------

def save_war_result(attacker_id: int, defender_id: int, operation_type: str, summary_text: str, timeline_text: str, targets_text: str, territory_text: str, losses_json: str) -> int:
    """ذخیره سناریوی کامل نبرد جهت نمایش تعاملی با دکمه‌های شیشه‌ای."""
    conn = get_connection()
    cur = conn.cursor()
    now_str = datetime.datetime.now().isoformat()
    cur.execute("""
        INSERT INTO war_results
        (attacker_id, defender_id, operation_type, summary_text, timeline_text, targets_text, territory_text, losses_json, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (attacker_id, defender_id, operation_type, summary_text, timeline_text, targets_text, territory_text, losses_json, now_str))
    war_id = cur.lastrowid
    conn.commit()
    conn.close()
    return war_id


def get_war_result_by_id(war_id: int) -> dict:
    """بازیابی داده‌های کامل نبرد با شناسه جنگ."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT w.*,
               a.name as att_name, a.flag as att_flag, a.country_key as att_key,
               d.name as def_name, d.flag as def_flag, d.country_key as def_key
        FROM war_results w
        JOIN countries a ON w.attacker_id = a.id
        JOIN countries d ON w.defender_id = d.id
        WHERE w.id = ?
    """, (war_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None