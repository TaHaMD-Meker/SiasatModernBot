# -*- coding: utf-8 -*-
"""
لایه دیتابیس بازی (SQLite).
شامل مدیریت کشورها، دارایی‌های اختصاصی نظامی (Country Assets System)، همگام‌سازی اتوماتیک دیتابیس با آخرین کاتالوگ و خرید اتومیک.
"""

import os
import re
import glob
import shutil
import json
import sqlite3
import datetime
import logging

logger = logging.getLogger(__name__)
try:
    from zoneinfo import ZoneInfo
    IRAN_TZ = ZoneInfo("Asia/Tehran")
except Exception:
    IRAN_TZ = datetime.timezone(datetime.timedelta(hours=3, minutes=30))
import config
from utils import format_money, format_number, format_oil

def get_connection():
    db_dir = os.path.dirname(config.DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 30000")
    except Exception:
        pass
    return conn


def init_db():
    conn = get_connection()
    cur = conn.cursor()

    # جدول کشورها
    cur.execute("""
    CREATE TABLE IF NOT EXISTS countries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER NOT NULL,
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
        cur.execute("ALTER TABLE countries ADD COLUMN microchips INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN microchips_daily INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN iron_ore INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN iron_ore_daily INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN uranium_ore INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN uranium_ore_daily INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN nuclear_fuel INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN nuclear_fuel_daily INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN warheads INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN enrichment_suspended INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN npt_withdrawn INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN un_sanctioned INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN warhead_cap_override INTEGER DEFAULT -1")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN medical_isotopes INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN medical_isotopes_daily INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN enriched_60 INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN weapons_grade_90 INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN enrichment_tier INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN nuclear_tested INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN firewall_level INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN air_defense_disrupted_until TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN blackout_until TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN r_and_d_frozen_until TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN command_disrupted_until TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN last_intel_op_time TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN intel_ops_today INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN intel_ops_date TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN is_vip INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN vip_expires_at TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN vip_tier TEXT")
    except sqlite3.OperationalError:
        pass

    # ===== ستون‌های جدید فروشگاه مصرفی و خدمات دیده شدن =====
    for _col_def in [
        "ALTER TABLE countries ADD COLUMN custom_title TEXT",
        "ALTER TABLE countries ADD COLUMN title_expires_at TEXT",
        "ALTER TABLE countries ADD COLUMN golden_frame_until TEXT",
        "ALTER TABLE countries ADD COLUMN drill_tickets INTEGER DEFAULT 0",
        "ALTER TABLE countries ADD COLUMN statement_tickets INTEGER DEFAULT 0",
        "ALTER TABLE countries ADD COLUMN golden_stmt_credits INTEGER DEFAULT 0",
        "ALTER TABLE countries ADD COLUMN pin_credits INTEGER DEFAULT 0",
        "ALTER TABLE countries ADD COLUMN contract_boost_until TEXT",
        "ALTER TABLE countries ADD COLUMN bp_booster_until TEXT",
        "ALTER TABLE countries ADD COLUMN bp_booster_mult REAL DEFAULT 1.0",
    ]:
        try:
            cur.execute(_col_def)
        except sqlite3.OperationalError:
            pass

    # خوددرمانی و ترمیم خودکار کلیدهای خارجی آسیب‌دیده از میگریشن‌های قبلی
    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' AND sql LIKE '%_countries_old%'")
        broken_tables = cur.fetchall()
        for b_row in broken_tables:
            tbl_name = b_row[0]
            old_sql = b_row[1]
            new_sql = old_sql.replace('"_countries_old"', 'countries').replace('_countries_old', 'countries')
            cur.execute(f"ALTER TABLE {tbl_name} RENAME TO _temp_fix_{tbl_name}")
            cur.execute(new_sql)
            cur.execute(f"INSERT INTO {tbl_name} SELECT * FROM _temp_fix_{tbl_name}")
            cur.execute(f"DROP TABLE _temp_fix_{tbl_name}")
        conn.commit()
    except Exception:
        pass

    try:
        conn.execute("PRAGMA foreign_keys = OFF")
        cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='countries'")
        row = cur.fetchone()
        if row and "player_id INTEGER UNIQUE" in row[0]:
            cur.execute("ALTER TABLE countries RENAME TO _countries_old")
            cur.execute("""
            CREATE TABLE countries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                player_id INTEGER NOT NULL,
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
                tech_level INTEGER DEFAULT 1,
                last_blockade_date TEXT,
                combat_readiness INTEGER DEFAULT 80,
                last_drill_date TEXT,
                daily_drill_count INTEGER DEFAULT 0,
                microchips INTEGER DEFAULT 0,
                microchips_daily INTEGER DEFAULT 0,
                uranium_ore INTEGER DEFAULT 0,
                uranium_ore_daily INTEGER DEFAULT 0,
                nuclear_fuel INTEGER DEFAULT 0,
                nuclear_fuel_daily INTEGER DEFAULT 0,
                warheads INTEGER DEFAULT 0,
                enrichment_suspended INTEGER DEFAULT 0,
                npt_withdrawn INTEGER DEFAULT 0,
                un_sanctioned INTEGER DEFAULT 0,
                warhead_cap_override INTEGER DEFAULT 0,
                medical_isotopes INTEGER DEFAULT 0,
                medical_isotopes_daily INTEGER DEFAULT 0,
                enriched_60 INTEGER DEFAULT 0,
                weapons_grade_90 INTEGER DEFAULT 0,
                enrichment_tier INTEGER DEFAULT 1,
                nuclear_tested INTEGER DEFAULT 0,
                firewall_level INTEGER DEFAULT 0,
                air_defense_disrupted_until TEXT,
                blackout_until TEXT,
                r_and_d_frozen_until TEXT,
                command_disrupted_until TEXT,
                last_intel_op_time TEXT,
                intel_ops_today INTEGER DEFAULT 0,
                intel_ops_date TEXT,
                is_vip INTEGER DEFAULT 0,
                vip_expires_at TEXT,
                vip_tier TEXT
            )
            """)
            cur.execute("INSERT INTO countries SELECT * FROM _countries_old")
            cur.execute("DROP TABLE _countries_old")
            conn.commit()
    except Exception:
        pass
    finally:
        try:
            conn.execute("PRAGMA foreign_keys = ON")
        except Exception:
            pass

    # جدول سران و کادر فرماندهی نظامی کشورها
    cur.execute("""
    CREATE TABLE IF NOT EXISTS country_commanders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL,
        key TEXT NOT NULL,
        title TEXT NOT NULL,
        status TEXT DEFAULT 'active',
        killed_at TEXT,
        UNIQUE(country_id, key),
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)

    # جدول لاگ و تاریخچه عملیات‌های اطلاعاتی و سایبری
    cur.execute("""
    CREATE TABLE IF NOT EXISTS intel_operations_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attacker_id INTEGER NOT NULL,
        target_id INTEGER NOT NULL,
        op_type TEXT NOT NULL,
        result TEXT NOT NULL,
        details TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY(attacker_id) REFERENCES countries(id) ON DELETE CASCADE,
        FOREIGN KEY(target_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)

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

    try:
        cur.execute("ALTER TABLE trade_contracts ADD COLUMN is_smuggled INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE trade_contracts ADD COLUMN origin_country_key TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE trade_contracts ADD COLUMN license_country_id INTEGER")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("ALTER TABLE trade_contracts ADD COLUMN license_status TEXT DEFAULT 'approved'")
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

    # جدول پایش بیانیه‌ها و فعالیت روزانه کشورها
    cur.execute("""
    CREATE TABLE IF NOT EXISTS daily_statements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL,
        player_id INTEGER NOT NULL,
        statement_type TEXT NOT NULL,
        content TEXT,
        created_at TEXT NOT NULL,
        statement_date TEXT NOT NULL,
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)

    try:
        cur.execute("CREATE INDEX IF NOT EXISTS idx_daily_statements_country_date ON daily_statements(country_id, statement_date)")
    except sqlite3.OperationalError:
        pass

    # جدول درخواست‌ها و فیش‌های پرداخت تومانی (VIP و گروه‌های غیردولتی)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS payment_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER NOT NULL,
        country_id INTEGER,
        item_type TEXT NOT NULL,
        plan_title TEXT NOT NULL,
        amount_toman INTEGER NOT NULL,
        receipt_photo_id TEXT,
        tracking_code TEXT,
        custom_payload TEXT,
        status TEXT DEFAULT 'pending',
        created_at TEXT NOT NULL,
        reviewed_at TEXT,
        admin_id INTEGER,
        admin_note TEXT,
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE SET NULL
    )
    """)

    # جدول سیستم بتل‌پس فصلی و کمپین ماموریت‌های ویژه
    cur.execute("""
    CREATE TABLE IF NOT EXISTS battle_pass (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL UNIQUE,
        season INTEGER DEFAULT 1,
        is_premium INTEGER DEFAULT 0,
        current_xp INTEGER DEFAULT 0,
        current_tier INTEGER DEFAULT 1,
        claimed_free_tiers TEXT DEFAULT '[]',
        claimed_premium_tiers TEXT DEFAULT '[]',
        completed_challenges TEXT DEFAULT '[]',
        challenge_progress TEXT DEFAULT '{}',
        created_at TEXT NOT NULL,
        updated_at TEXT,
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
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
        auto_recover_constructions()
    except Exception as e:
        print(f"[auto-recover-constructions] error: {e}")

    try:
        if not get_setting("rebalance_done_v3"):
            rebalance_existing_countries_income()
            set_setting("rebalance_done_v3", "1")
    except Exception:
        pass

    try:
        fix_nuclear_free_grant_v1()
    except Exception as e:
        print(f"[nuclear-migration] error: {e}")

    try:
        nuclear_compensation_v1()
    except Exception as e:
        print(f"[nuclear-compensation] error: {e}")

    try:
        nuclear_compensation_cap_v2()
    except Exception as e:
        print(f"[nuclear-compensation-cap] error: {e}")

    try:
        nuclear_compensation_v3()
    except Exception as e:
        print(f"[nuclear-compensation-v3] error: {e}")

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


def auto_recover_constructions():
    """بازیابی خودکار ساخت‌وسازها و کارخانجات از فایل‌های پشتیبان و تاریخچه تراکنش‌ها."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            # ۱. بازیابی از فایل‌های پشتیبان backups/*.db
            backup_dir = os.path.join(os.path.dirname(os.path.abspath(config.DB_PATH)), "backups")
            if os.path.exists(backup_dir):
                for b_path in glob.glob(os.path.join(backup_dir, "*.db")):
                    try:
                        b_conn = sqlite3.connect(b_path)
                        b_cur = b_conn.cursor()
                        b_cur.execute("SELECT country_id, item_key, quantity FROM equipment WHERE quantity > 0")
                        for cid, ikey, qty in b_cur.fetchall():
                            cur.execute("SELECT id FROM countries WHERE id = ?", (cid,))
                            if cur.fetchone():
                                cur.execute("SELECT quantity FROM equipment WHERE country_id = ? AND item_key = ?", (cid, ikey))
                                ex = cur.fetchone()
                                if not ex:
                                    cur.execute("INSERT INTO equipment (country_id, item_key, quantity) VALUES (?,?,?)", (cid, ikey, qty))
                                elif ex[0] < qty:
                                    cur.execute("UPDATE equipment SET quantity = ? WHERE country_id = ? AND item_key = ?", (qty, cid, ikey))
                        b_conn.close()
                    except Exception:
                        pass

            # ۲. بازیابی از تاریخچه تراکنش‌های خرید (Transactions)
            name_to_key = {}
            for k, v in config.ALL_SHOP_ITEMS.items():
                clean_name = re.sub(r"[^\w\s]", "", v["name"]).strip()
                name_to_key[clean_name] = k
                name_to_key[v["name"]] = k

            cur.execute("SELECT country_id, description FROM transactions WHERE type='purchase' AND description LIKE 'احداث%'")
            for cid, desc in cur.fetchall():
                m = re.search(r"احداث\s+(.+?)\s+x(\d+)", desc)
                if m:
                    p_name = m.group(1).strip()
                    qty = int(m.group(2))
                    p_clean = re.sub(r"[^\w\s]", "", p_name).strip()
                    ikey = name_to_key.get(p_name) or name_to_key.get(p_clean)
                    if ikey:
                        cur.execute("SELECT quantity FROM equipment WHERE country_id = ? AND item_key = ?", (cid, ikey))
                        ex = cur.fetchone()
                        if not ex:
                            cur.execute("INSERT INTO equipment (country_id, item_key, quantity) VALUES (?,?,?)", (cid, ikey, qty))
                        elif ex[0] < qty:
                            cur.execute("UPDATE equipment SET quantity = ? WHERE country_id = ? AND item_key = ?", (qty, cid, ikey))
    except Exception as e:
        logger.warning(f"Error in auto_recover_constructions: {e}")
    finally:
        conn.close()


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
    silo_bonus = config.ALL_SHOP_ITEMS.get("grain_silo", {}).get("grain_bonus", 0)
    for row in rows:
        cid = row[0]
        ckey = row[1]
        pop = row[2] or 10_000_000
        grain = row[3] or 0
        need_daily = max(10, int((pop / 1_000_000) * 100))
        preset = config.COUNTRY_STARTING_OVERRIDES.get(ckey, {}) if ckey else {}
        cap = preset.get("grain") or (need_daily * 7)
        # 🏢 سیلوهای خریداری‌شده ظرفیت ذخیره‌سازی اضافه می‌کنند؛ سقف‌گذاری نباید
        # پاداش ۵۰٬۰۰۰ تنی هر سیلو را پاک کند (باگ: بازیکن ۱۵M می‌داد و با اولین
        # ری‌استارتِ بعد از مایگریشن، غلاتش به مقدار پایه برمی‌گشت).
        if silo_bonus:
            cur.execute(
                "SELECT quantity FROM equipment WHERE country_id = ? AND item_key = 'grain_silo'",
                (cid,),
            )
            silo_row = cur.fetchone()
            if silo_row and silo_row[0] > 0:
                cap += silo_bonus * silo_row[0]
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

# نگاشت واحدِ «قلم ویژه» → ستون کشور. مرجع مشترک اعمال/بازگردانی تا هیچ‌وقت
# مسیر revert از مسیر apply عقب نیفتد (باگ قدیمی: منابع راهبردی برنمی‌گشتند).
LOSS_SPECIAL_COLUMNS = {
    "money": "treasury",
    "oil": "oil_reserves",
    "mil_kia": "active_personnel",
    "uranium_ore": "uranium_ore",
    "nuclear_fuel": "nuclear_fuel",
    "medical_isotopes": "medical_isotopes",
    "enriched_60": "enriched_60",
    "weapons_grade_90": "weapons_grade_90",
    "warheads": "warheads",
    "microchips": "microchips",
    "gold": "gold",
}

# اقلامی که فقط ثبت گزارشی می‌شوند و روی هیچ موجودی اثر ندارند
LOSS_RECORD_ONLY_SPECIALS = ("wounded", "civ_kia")

_LOSS_SPECIAL_LABELS = {
    "money": "هزینه مالی",
    "oil": "سوخت مصرفی",
    "mil_kia": "تلفات نظامی",
    "uranium_ore": "تلفات اورانیوم",
    "nuclear_fuel": "تلفات سوخت هسته‌ای",
    "warheads": "تلفات کلاهک هسته‌ای",
    "microchips": "تلفات میکروچیپ",
    "iron_ore": "تلفات سنگ آهن و فولاد",
    "gold": "تلفات طلا",
}

_BUILDING_EFFECT_COLUMNS = {
    "elec": "electricity",
    "gold_daily": "gold_daily",
    "oil_prod": "oil_production",
    "grain_daily": "grain_daily",
    "iron_ore_daily": "iron_ore_daily",
    "uranium_ore_daily": "uranium_ore_daily",
    "nuclear_fuel_daily": "nuclear_fuel_daily",
    "medical_isotopes_daily": "medical_isotopes_daily",
    "microchips_daily": "microchips_daily",
}


def _apply_building_effects(cur, country_id: int, effects: dict, sign: int):
    """اعمال (sign=-1) یا بازگردانی (sign=+1) اثرات تولیدی یک ساختمان."""
    if not effects:
        return
    for eff_key, column in _BUILDING_EFFECT_COLUMNS.items():
        delta = int(effects.get(eff_key, 0) or 0)
        if delta:
            cur.execute(
                f"UPDATE countries SET {column} = MAX(0, COALESCE({column}, 0) + ?) WHERE id = ?",
                (sign * delta, country_id),
            )


def _restore_loss_items(cur, country_id: int, items: list):
    """بازگردانی کاملِ اقلام یک گزارش به موجودی کشور یا پایگاه (مشترک بین revert و delete)."""
    for it in items:
        qty = int(it.get("qty", 0) or 0)
        if qty <= 0:
            continue
        special = it.get("special")
        if special in LOSS_RECORD_ONLY_SPECIALS:
            continue
        if special == "building":
            cur.execute(
                "INSERT INTO equipment (country_id, item_key, quantity) VALUES (?,?,?)"
                " ON CONFLICT(country_id, item_key) DO UPDATE SET quantity = quantity + excluded.quantity",
                (country_id, it["key"], qty),
            )
            _apply_building_effects(cur, country_id, it.get("effects", {}), sign=+1)
            continue
        if special == "commander":
            cmd_k = it.get("cmd_key", it["key"].replace("__cmd_", "").replace("__", ""))
            revive_commander(country_id, cmd_k)
            continue
        column = LOSS_SPECIAL_COLUMNS.get(special)
        if column:
            cur.execute(
                f"UPDATE countries SET {column} = COALESCE({column}, 0) + ? WHERE id = ?",
                (qty, country_id),
            )
            continue
        if it.get("base_id"):
            cur.execute(
                "INSERT INTO base_assets (base_id, equipment_key, equipment_name, category, amount) VALUES (?, ?, ?, ?, ?)"
                " ON CONFLICT(base_id, equipment_key) DO UPDATE SET amount = amount + ?",
                (it["base_id"], it["key"], it.get("name", it["key"]), it.get("category", ""), qty, qty)
            )
            continue
        cur.execute(
            "UPDATE country_assets SET amount = amount + ? WHERE country_id = ? AND equipment_key = ?",
            (qty, country_id, it["key"]),
        )


def create_loss_report(country_id: int, items: list, operation_name: str = "", note: str = "", admin_id=None, base_id=None):
    """ثبت و اعمال تراکنشیِ گزارش تلفات — همه یا هیچ (پشتیبانی از تفکیک پایگاه و انبار ملی)."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            # اقلام ویژه: mil_kia از نیروی فعال؛ money از خزانه؛ oil از ذخایر نفت؛ wounded/civ فقط ثبت
            valid_items = [
                it for it in items
                if int(it.get("qty", 0) or 0) > 0
                and it.get("special") not in LOSS_RECORD_ONLY_SPECIALS
            ]
            for it in valid_items:
                if it.get("special") == "building":
                    cur.execute("SELECT quantity FROM equipment WHERE country_id = ? AND item_key = ?", (country_id, it["key"]))
                    erow = cur.fetchone()
                    owned = (erow["quantity"] or 0) if erow else 0
                    if owned <= 0:
                        it["qty"] = 0  # مالکیت ندارد → نادیده گرفته می‌شود (بدون منفی‌شدن موجودی)
                        continue
                    it["qty"] = min(int(it["qty"]), owned)
                    cfg_it = config.ALL_SHOP_ITEMS.get(it["key"], {})
                    q = int(it["qty"])
                    chips_daily = 0
                    if it["key"] == "chip_fab":
                        cur.execute("SELECT country_key FROM countries WHERE id = ?", (country_id,))
                        ckrow = cur.fetchone()
                        ckey = (ckrow["country_key"] if ckrow else "") or ""
                        chips_daily = config.get_chip_fab_effect(ckey).get("chips_daily", 25)
                    it["effects"] = {
                        "elec": int(cfg_it.get("elec_add", 0) or 0) * q,
                        "gold_daily": int(cfg_it.get("gold_daily_add", 0) or 0) * q,
                        "oil_prod": int(cfg_it.get("oil_prod_add", 0) or 0) * q,
                        "grain_daily": int(cfg_it.get("grain_daily_add", 0) or 0) * q,
                        "uranium_ore_daily": int(cfg_it.get("uranium_ore_daily_add", 0) or 0) * q,
                        "nuclear_fuel_daily": int(cfg_it.get("nuclear_fuel_daily_add", 0) or 0) * q,
                        "microchips_daily": int(chips_daily) * q,
                    }
                    continue
                special = it.get("special")
                if special == "commander":
                    continue
                if special in LOSS_SPECIAL_COLUMNS:
                    column = LOSS_SPECIAL_COLUMNS[special]
                    cur.execute(f"SELECT {column} FROM countries WHERE id = ?", (country_id,))
                    crow = cur.fetchone()
                    have = (crow[column] or 0) if crow else 0
                    it["qty"] = min(int(it["qty"]), max(0, have))
                    continue
                target_base_id = it.get("base_id") or base_id
                if target_base_id:
                    cur.execute(
                        "SELECT amount FROM base_assets WHERE base_id = ? AND equipment_key = ?",
                        (target_base_id, it["key"]),
                    )
                    row = cur.fetchone()
                    have = (row["amount"] or 0) if row else 0
                    it["qty"] = min(int(it["qty"]), max(0, have))
                    it["base_id"] = target_base_id
                    continue
                cur.execute(
                    "SELECT amount FROM country_assets WHERE country_id = ? AND equipment_key = ?",
                    (country_id, it["key"]),
                )
                row = cur.fetchone()
                have = (row["amount"] or 0) if row else 0
                it["qty"] = min(int(it["qty"]), max(0, have))
            for it in valid_items:
                if int(it.get("qty", 0) or 0) <= 0:
                    continue
                if it.get("special") == "building":
                    cur.execute("UPDATE equipment SET quantity = MAX(0, quantity - ?) WHERE country_id = ? AND item_key = ?",
                                (int(it["qty"]), country_id, it["key"]))
                    _apply_building_effects(cur, country_id, it.get("effects", {}), sign=-1)
                    continue
                if it.get("special") == "commander":
                    cmd_k = it.get("cmd_key", it["key"].replace("__cmd_", "").replace("__", ""))
                    kill_commander(country_id, cmd_k, f"اصابت در عملیات {operation_name}")
                    continue
                special = it.get("special")
                if special in LOSS_SPECIAL_COLUMNS:
                    column = LOSS_SPECIAL_COLUMNS[special]
                    cur.execute(
                        f"UPDATE countries SET {column} = MAX(0, COALESCE({column}, 0) - ?) WHERE id = ?",
                        (int(it["qty"]), country_id),
                    )
                    continue
                if it.get("base_id"):
                    cur.execute(
                        "UPDATE base_assets SET amount = MAX(0, amount - ?) WHERE base_id = ? AND equipment_key = ?",
                        (int(it["qty"]), it["base_id"], it["key"]),
                    )
                    continue
                cur.execute(
                    "UPDATE country_assets SET amount = MAX(0, amount - ?) WHERE country_id = ? AND equipment_key = ?",
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
            _restore_loss_items(cur, row["country_id"], items)
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
            items = []
            if row["status"] == "applied":
                items = json.loads(row["items_json"])
                _restore_loss_items(cur, row["country_id"], items)
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
    active = 0
    reverted = 0
    for r in rows:
        if r["status"] == "deleted":
            continue
        if r["status"] == "reverted":
            reverted += 1
            continue
        active += 1
        for it in json.loads(r["items_json"]):
            if int(it.get("qty", 0) or 0) > 0:
                by_equip[it.get("name", it.get("key", "?"))] += int(it["qty"])
                by_subcat[it.get("subcat", it.get("category", "?"))] += int(it["qty"])
    # reports = گزارش‌های فعال (اعمال‌شده)؛ total = فعال + بازگردانی‌شده
    return {
        "reports": active,
        "reverted": reverted,
        "total": active + reverted,
        "by_equip": by_equip,
        "by_subcat": by_subcat,
    }




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
            cur.execute("""
                INSERT INTO transactions (country_id, type, description, amount, created_at)
                VALUES (?, 'base_build', ?, ?, ?)
            """, (req["owner_id"], f"ساخت پایگاه «{req['base_name']}»", -int(config.BASE_BUILD_COST.get("money", 0)), now_str))
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
            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute("""
                INSERT INTO transactions (country_id, type, description, amount, created_at)
                VALUES (?, 'base_upgrade', 'ارتقای پایگاه پیشروی', ?, ?)
            """, (req["owner_id"], -int(config.BASE_UPGRADE_COST.get("money", 0)), now_str))
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
        host = get_country_by_id(b["host_id"])
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
                if rent > 0 and host:
                    cur.execute("UPDATE countries SET treasury = treasury + ? WHERE id = ?", (rent, b["host_id"]))
                cur.execute("UPDATE foreign_bases SET unpaid_days = 0 WHERE id = ?", (b["id"],))
            conn.close()
            events.append({
                "base_id": b["id"],
                "base_name": b["name"],
                "owner_id": owner["id"],
                "owner_name": owner["name"],
                "owner_pid": owner.get("player_id"),
                "host_id": b["host_id"],
                "host_name": host["name"] if host else "",
                "host_pid": host.get("player_id") if host else None,
                "rent": rent,
                "total_money": total_money,
                "event": "paid"
            })
        else:
            with conn:
                conn.execute("UPDATE foreign_bases SET unpaid_days = unpaid_days + 1 WHERE id = ?", (b["id"],))
            row = conn.execute("SELECT unpaid_days FROM foreign_bases WHERE id = ?", (b["id"],)).fetchone()
            conn.close()
            unpaid_days_now = row["unpaid_days"] if row else 1
            ev_type = "collapsed" if unpaid_days_now >= 3 else "unpaid"
            if unpaid_days_now >= 3:
                dissolve_base(b["id"], loss_pct=25)
            events.append({
                "base_id": b["id"],
                "base_name": b["name"],
                "owner_id": owner["id"],
                "owner_name": owner["name"],
                "owner_pid": owner.get("player_id"),
                "host_id": b["host_id"],
                "host_name": host["name"] if host else "",
                "host_pid": host.get("player_id") if host else None,
                "rent": rent,
                "total_money": total_money,
                "days": unpaid_days_now,
                "event": ev_type
            })
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
         gold, gold_daily, oil_reserves, oil_production, grain, grain_daily, iron_ore, iron_ore_daily, microchips, microchips_daily,
         uranium_ore, uranium_ore_daily, nuclear_fuel, nuclear_fuel_daily, warheads,
         electricity, active_personnel, reserve_personnel, last_income_date, created_at, country_key, username, approval_rating)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        player_id, name, flag,
        sv["population"], sv["treasury"], sv["tax_income"], sv["daily_income"],
        sv["gold"], sv["gold_daily"], sv["oil_reserves"], sv["oil_production"],
        sv["grain"], sv.get("grain_daily", config.STARTING_VALUES.get("grain_daily", 2500)),
        sv.get("iron_ore", config.STARTING_VALUES.get("iron_ore", 10000)),
        sv.get("iron_ore_daily", config.STARTING_VALUES.get("iron_ore_daily", 500)),
        sv.get("microchips", config.STARTING_VALUES.get("microchips", 1000)),
        sv.get("microchips_daily", config.STARTING_VALUES.get("microchips_daily", 25)),
        # 🧪 چرخه هسته‌ای همیشه از صفر شروع می‌شود (طراحی بازی):
        # اورانیوم/سوخت/کلاهک فقط از مسیر بازی به دست می‌آید (معدن، غنی‌سازی، مونتاژ، بازار)
        # و هرگز از مقادیر اولیه کانفیگ اهداء نمی‌شود.
        0,  # uranium_ore
        0,  # uranium_ore_daily
        0,  # nuclear_fuel
        0,  # nuclear_fuel_daily
        0,  # warheads
        sv["electricity"], sv["active_personnel"], sv["reserve_personnel"],
        None, now_str, country_key, username, sv.get("approval_rating", 80)
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


def get_player_all_entities(player_id: int) -> list[dict]:
    """دریافت کلیه نهادهای تحت فرماندهی بازیکن (دولت رسمی و بازوی مقاومت/شبه‌نظامی)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM countries WHERE player_id = ? ORDER BY id ASC", (player_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_country_by_player(player_id: int):
    """دریافت نهاد فعال جاری بازیکن (با پشتیبانی از سوییچ هوشمند بین کشور رسمی و بازوی نیابتی)."""
    entities = get_player_all_entities(player_id)
    if not entities:
        return None
    if len(entities) == 1:
        c = entities[0]
        if c.get("country_key"):
            seed_country_assets(c["id"], c["country_key"])
        return c

    active_cid_str = get_setting(f"active_entity_{player_id}")
    if active_cid_str and active_cid_str.isdigit():
        active_cid = int(active_cid_str)
        match = next((e for e in entities if e["id"] == active_cid), None)
        if match:
            if match.get("country_key"):
                seed_country_assets(match["id"], match["country_key"])
            return match

    # پیش‌فرض: نهاد دولتی رسمی (اگر هست) یا اولین نهاد
    state_c = next((e for e in entities if not (e.get("country_key") or "").startswith("faction_")), entities[0])
    if state_c.get("country_key"):
        seed_country_assets(state_c["id"], state_c["country_key"])
    return state_c


def switch_player_active_entity(player_id: int, target_country_id: int = None) -> tuple[bool, str, dict]:
    """سوییچ فوری بین دولت رسمی و بازوی نیابتی/شبه‌نظامی بازیکن."""
    entities = get_player_all_entities(player_id)
    if len(entities) < 2:
        return False, "شما در حال حاضر تنها یک کشور/نهاد تحت فرماندهی دارید.", None

    curr = get_country_by_player(player_id)
    if target_country_id:
        target = next((e for e in entities if e["id"] == target_country_id), None)
    else:
        target = next((e for e in entities if e["id"] != curr["id"]), entities[0])

    if not target:
        return False, "نهاد مقصد یافت نشد.", None

    set_setting(f"active_entity_{player_id}", str(target["id"]))
    if target.get("country_key"):
        seed_country_assets(target["id"], target["country_key"])
    return True, f"فرماندهی به {target['flag']} {target['name']} سوییچ شد.", target


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
        "approval_rating", "grain_daily", "microchips", "microchips_daily", "iron_ore", "iron_ore_daily", "tech_level",
        "combat_readiness", "last_drill_date", "daily_drill_count", "username", "country_key", "player_id",
        "last_blockade_date",
        # فیلدهای چرخه هسته‌ای (ویرایش از پنل ادمین)
        "uranium_ore", "uranium_ore_daily", "nuclear_fuel", "nuclear_fuel_daily", "warheads",
        "warhead_cap_override", "enriched_60", "weapons_grade_90", "medical_isotopes", "medical_isotopes_daily",
        "enrichment_tier", "enrichment_suspended", "npt_withdrawn", "un_sanctioned", "nuclear_tested",
        # فیلدهای سایبری و اطلاعات
        "firewall_level", "air_defense_disrupted_until", "blackout_until", "r_and_d_frozen_until", "command_disrupted_until",
        "intel_ops_today", "intel_ops_date", "last_intel_op_time",
        # فیلدهای اشتراک VIP
        "is_vip", "vip_tier", "vip_expires_at",
        # فیلدهای فروشگاه مصرفی و دیده شدن
        "custom_title", "title_expires_at", "golden_frame_until", "drill_tickets", "statement_tickets",
        "golden_stmt_credits", "pin_credits", "contract_boost_until", "bp_booster_until", "bp_booster_mult"
    }
    if field not in allowed:
        raise ValueError(f"فیلد غیرمجاز: {field}")
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE countries SET {field} = ? WHERE id = ?", (value, country_id))
    conn.commit()
    conn.close()


def adjust_iron_ore(country_id: int, delta: int):
    """افزایش یا کاهش موجودی سنگ آهن و فولاد کشور."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET iron_ore = MAX(0, iron_ore + ?) WHERE id = ?", (delta, country_id))
    conn.commit()
    conn.close()


def adjust_treasury(country_id: int, delta: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET treasury = treasury + ? WHERE id = ?", (delta, country_id))
    conn.commit()
    conn.close()


def adjust_microchips(country_id: int, amount: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET microchips = MAX(0, microchips + ?) WHERE id = ?", (amount, country_id))
    conn.commit()
    conn.close()


def adjust_gold(country_id: int, delta: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET gold = MAX(0, gold + ?) WHERE id = ?", (delta, country_id))
    conn.commit()
    conn.close()


def adjust_oil(country_id: int, delta: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET oil_reserves = MAX(0, oil_reserves + ?) WHERE id = ?", (delta, country_id))
    conn.commit()
    conn.close()


def adjust_oil_production(country_id: int, delta: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET oil_production = MAX(0, oil_production + ?) WHERE id = ?", (delta, country_id))
    conn.commit()
    conn.close()


def adjust_uranium_ore(country_id: int, delta: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET uranium_ore = MAX(0, uranium_ore + ?) WHERE id = ?", (delta, country_id))
    conn.commit()
    conn.close()



def adjust_medical_isotopes(country_id: int, delta: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET medical_isotopes = MAX(0, medical_isotopes + ?) WHERE id = ?", (delta, country_id))
    conn.commit()
    conn.close()


def adjust_enriched_60(country_id: int, delta: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET enriched_60 = MAX(0, enriched_60 + ?) WHERE id = ?", (delta, country_id))
    conn.commit()
    conn.close()


def adjust_weapons_grade_90(country_id: int, delta: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET weapons_grade_90 = MAX(0, weapons_grade_90 + ?) WHERE id = ?", (delta, country_id))
    conn.commit()
    conn.close()


def set_country_enrichment_tier(country_id: int, tier: int) -> tuple[bool, str]:
    """تنظیم دکترین و پله غنی‌سازی سانتریفیوژها (۱=۳.۵٪، ۲=۲۰٪، ۳=۶۰٪، ۴=۹۰٪)."""
    tier = max(1, min(4, tier))
    tier_info = config.ENRICHMENT_TIERS.get(tier, {})
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT tech_level, country_key, enrichment_suspended FROM countries WHERE id = ?", (country_id,))
            c = cur.fetchone()
            if not c:
                return False, "کشور یافت نشد."

            tech_lvl = c["tech_level"] or 1
            if tech_lvl < tier_info.get("tech_req", 3):
                return False, f"🔬 برای این پله غنی‌سازی نیاز به سطح فناوری {tier_info.get('tech_req', 3)} دارید."

            cur.execute("SELECT quantity FROM equipment WHERE country_id = ? AND item_key = 'enrichment_facility'", (country_id,))
            eq = cur.fetchone()
            fac_count = (eq["quantity"] or 0) if eq else 0
            is_p5 = c["country_key"] in ("usa", "russia", "china", "france", "uk", "pakistan", "india", "israel", "north_korea")

            if fac_count < 1 and not is_p5:
                return False, "❌ کشور شما فاقد مجتمع غنی‌سازی و سانتریفیوژ فعال است."

            fuel_d = (tier_info.get("fuel_prod", 0) * max(1, fac_count)) if not c["enrichment_suspended"] else 0
            med_d = (tier_info.get("medical_prod", 0) * max(1, fac_count)) if not c["enrichment_suspended"] else 0

            cur.execute("""
                UPDATE countries SET
                enrichment_tier = ?,
                nuclear_fuel_daily = ?,
                medical_isotopes_daily = ?
                WHERE id = ?
            """, (tier, fuel_d, med_d, country_id))

        return True, f"✅ دکترین غنی‌سازی سانتریفیوژها بر روی «{tier_info.get('name')}» تنظیم گردید."
    except Exception as e:
        return False, f"خطا: {e}"


def build_enrichment_facility_transaction(country_id: int) -> tuple[bool, str]:
    """احداث مجتمع غنی‌سازی و آبشار سانتریفیوژهای زیرزمینی."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM countries WHERE id = ?", (country_id,))
            row = cur.fetchone()
            if not row:
                return False, "کشور یافت نشد."
            c = dict(row)

            tech_lvl = c["tech_level"] or 1
            if tech_lvl < getattr(config, "ENRICHMENT_FACILITY_TECH_REQ", 3):
                return False, f"🔬 **پیش‌نیاز فناوری نامعتبر:** برای احداث مجتمع غنی‌سازی زیرزمینی نیاز به سطح فناوری ۳ به بالا دارید."

            cur.execute("SELECT quantity FROM equipment WHERE country_id = ? AND item_key = 'enrichment_facility'", (country_id,))
            eq = cur.fetchone()
            curr_qty = (eq["quantity"] or 0) if eq else 0
            if curr_qty >= 2:
                return False, "🔒 سقف مجاز احداث مجتمع غنی‌سازی (حداکثر ۲ واحد) تکمیل است."

            price = getattr(config, "ENRICHMENT_FACILITY_PRICE", 60_000_000)
            gold_req = getattr(config, "ENRICHMENT_FACILITY_GOLD", 150)
            chips_req = getattr(config, "ENRICHMENT_FACILITY_CHIPS", 250)

            if (c["treasury"] or 0) < price:
                return False, f"💵 موجودی خزانه کافی نیست! نیاز: {format_money(price)}"
            if (c["gold"] or 0) < gold_req:
                return False, f"🪙 شمش طلا کافی نیست! نیاز: {gold_req} شمش"
            if (c["microchips"] or 0) < chips_req:
                return False, f"💻 میکروچیپ کافی نیست! نیاز: {chips_req:,} عدد"

            cur.execute("""
                UPDATE countries SET
                treasury = treasury - ?,
                gold = gold - ?,
                microchips = microchips - ?,
                nuclear_fuel_daily = nuclear_fuel_daily + 25
                WHERE id = ?
            """, (price, gold_req, chips_req, country_id))

            if eq:
                cur.execute("UPDATE equipment SET quantity = quantity + 1 WHERE country_id = ? AND item_key = 'enrichment_facility'", (country_id,))
            else:
                cur.execute("INSERT INTO equipment (country_id, item_key, quantity) VALUES (?, 'enrichment_facility', 1)", (country_id,))

            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute("""
                INSERT INTO transactions (country_id, type, description, amount, created_at)
                VALUES (?, 'enrichment_build', 'احداث مجتمع غنی‌سازی و سانتریفیوژ زیرزمینی', ?, ?)
            """, (country_id, -price, now_str))

        return True, "🔬 **مجتمع غنی‌سازی و سانتریفیوژ زیرزمینی با موفقیت احداث و راه‌اندازی شد!**"
    except Exception as e:
        return False, f"خطای دیتابیس: {e}"


def conduct_nuclear_test_transaction(country_id: int) -> tuple[bool, str]:
    """انجام موفقیت‌آمیز آزمایش انفجار هسته‌ای زیرزمینی."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM countries WHERE id = ?", (country_id,))
            row = cur.fetchone()
            if not row:
                return False, "کشور یافت نشد."
            c = dict(row)

            if c.get("nuclear_tested"):
                return False, "🌟 کشور شما قبلاً آزمایش انفجار هسته‌ای را با موفقیت انجام داده است."

            tech_lvl = c["tech_level"] or 1
            if tech_lvl < 4:
                return False, "🔬 برای انجام آزمایش هسته‌ای نیاز به سطح فناوری ۴ به بالا دارید."

            w90_req = getattr(config, "NUCLEAR_TEST_WEAPONS_GRADE", 50)
            cost_money = getattr(config, "NUCLEAR_TEST_COST_MONEY", 50_000_000)
            cost_gold = getattr(config, "NUCLEAR_TEST_COST_GOLD", 50)
            cost_chips = getattr(config, "NUCLEAR_TEST_COST_CHIPS", 200)

            if (c["weapons_grade_90"] or 0) < w90_req:
                return False, f"🔴 اورانیوم تسلیحاتی ۹۰٪ کافی نیست! نیاز: {w90_req} کیلوگرم (موجودی: {c['weapons_grade_90'] or 0} ک‌گ)"
            if (c["treasury"] or 0) < cost_money:
                return False, f"💵 موجودی خزانه کافی نیست! نیاز: {format_money(cost_money)}"
            if (c["gold"] or 0) < cost_gold:
                return False, f"🪙 طلا کافی نیست! نیاز: {cost_gold} شمش"
            if (c["microchips"] or 0) < cost_chips:
                return False, f"💻 میکروچیپ کافی نیست! نیاز: {cost_chips:,} عدد"

            cur.execute("""
                UPDATE countries SET
                treasury = treasury - ?,
                gold = gold - ?,
                microchips = microchips - ?,
                weapons_grade_90 = weapons_grade_90 - ?,
                nuclear_tested = 1
                WHERE id = ?
            """, (cost_money, cost_gold, cost_chips, w90_req, country_id))

            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute("""
                INSERT INTO transactions (country_id, type, description, amount, created_at)
                VALUES (?, 'nuclear_test', 'انجام نخستین آزمایش انفجار هسته‌ای زیرزمینی', ?, ?)
            """, (country_id, -cost_money, now_str))

        return True, "💥 **نخستین آزمایش انفجار هسته‌ای زیرزمینی کشور با موفقیت کامل انجام شد!**"
    except Exception as e:
        return False, f"خطای دیتابیس: {e}"


def assemble_strategic_warhead_transaction(country_id: int) -> tuple[bool, str]:
    """کوچک‌سازی و مونتاژ کلاهک راهبردی بازدارنده هسته‌ای."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM countries WHERE id = ?", (country_id,))
            row = cur.fetchone()
            if not row:
                return False, "کشور یافت نشد."
            c = dict(row)

            tech_lvl = c["tech_level"] or 1
            if tech_lvl < 5:
                return False, "🔬 برای کوچک‌سازی و مونتاژ کلاهک موشکی نیاز به بالاترین سطح فناوری (سطح ۵) دارید."

            is_p5 = c["country_key"] in ("usa", "russia", "china", "france", "uk", "pakistan", "india", "israel", "north_korea")
            if not c.get("nuclear_tested") and not is_p5:
                return False, "💥 ابتدا باید آزمایش انفجار هسته‌ای زیرزمینی (فاز ۴) را با موفقیت پشت سر بگذارید."

            eff_cap = get_effective_warhead_cap(c)
            curr_wh = c["warheads"] or 0
            if eff_cap is not None and curr_wh >= eff_cap:
                return False, f"⛔ **سقف مجاز نگهداری کلاهک تکمیل است:** سقف شما حداکثر {eff_cap} عدد می‌باشد."

            w90_req = getattr(config, "NUCLEAR_WARHEAD_WEAPONS_GRADE", 100)
            cost_money = getattr(config, "NUCLEAR_WARHEAD_COST_MONEY", 100_000_000)
            cost_gold = getattr(config, "NUCLEAR_WARHEAD_COST_GOLD", 100)
            cost_chips = getattr(config, "NUCLEAR_WARHEAD_COST_CHIPS", 500)

            if (c["weapons_grade_90"] or 0) < w90_req:
                return False, f"🔴 اورانیوم تسلیحاتی ۹۰٪ کافی نیست! نیاز: {w90_req} کیلوگرم (موجودی: {c['weapons_grade_90'] or 0} ک‌گ)"
            if (c["treasury"] or 0) < cost_money:
                return False, f"💵 موجودی خزانه کافی نیست! نیاز: {format_money(cost_money)}"
            if (c["gold"] or 0) < cost_gold:
                return False, f"🪙 طلا کافی نیست! نیاز: {cost_gold} شمش"
            if (c["microchips"] or 0) < cost_chips:
                return False, f"💻 میکروچیپ کافی نیست! نیاز: {cost_chips:,} عدد"

            cur.execute("""
                UPDATE countries SET
                treasury = treasury - ?,
                gold = gold - ?,
                microchips = microchips - ?,
                weapons_grade_90 = weapons_grade_90 - ?,
                warheads = warheads + 1
                WHERE id = ?
            """, (cost_money, cost_gold, cost_chips, w90_req, country_id))

            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute("""
                INSERT INTO transactions (country_id, type, description, amount, created_at)
                VALUES (?, 'warhead_assembly', 'مونتاژ و مسلح‌سازی ۱ کلاهک راهبردی هسته‌ای', ?, ?)
            """, (country_id, -cost_money, now_str))

        return True, f"🚀 **کلاهک راهبردی هسته‌ای با موفقیت مونتاژ و در زرادخانه مستقر شد!**\nتعداد کلاهک‌های فعال: **{curr_wh + 1} عدد**"
    except Exception as e:
        return False, f"خطای دیتابیس: {e}"

def adjust_nuclear_fuel(country_id: int, delta: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET nuclear_fuel = MAX(0, nuclear_fuel + ?) WHERE id = ?", (delta, country_id))
    conn.commit()
    conn.close()


def adjust_warheads(country_id: int, delta: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET warheads = MAX(0, warheads + ?) WHERE id = ?", (delta, country_id))
    conn.commit()
    conn.close()


def set_enrichment_suspended(country_id: int, suspended: bool):
    """تعلیق/رفع تعلیق برنامه غنی‌سازی (اختیار آژانس انرژی اتمی).

    هنگام تعلیق: تولید سوخت غنی‌شدهٔ روزانه صفر می‌شود.
    هنگام رفع تعلیق: تولید روزانه از روی مجتمع‌های غنی‌سازی مالکیت کشور بازمحاسبه می‌شود.
    (پایدار است — rebalance نیز این ستون را رعایت می‌کند.)
    """
    conn = get_connection()
    cur = conn.cursor()
    if suspended:
        cur.execute("UPDATE countries SET enrichment_suspended = 1, nuclear_fuel_daily = 0 WHERE id = ?", (country_id,))
    else:
        cur.execute("SELECT quantity FROM equipment WHERE country_id = ? AND item_key = 'enrichment_facility'", (country_id,))
        row = cur.fetchone()
        qty = (row["quantity"] or 0) if row else 0
        item = config.ALL_SHOP_ITEMS.get("enrichment_facility", {})
        daily = qty * item.get("nuclear_fuel_daily_add", 20)
        cur.execute("UPDATE countries SET enrichment_suspended = 0, nuclear_fuel_daily = ? WHERE id = ?", (daily, country_id))
    conn.commit()
    conn.close()


def confiscate_warheads(country_id: int, reason: str) -> int:
    """خلع سلاح هسته‌ای توسط آژانس — تمام کلاهک‌ها ضبط و رسید ثبت می‌شود. خروجی: تعداد ضبط‌شده."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT warheads FROM countries WHERE id = ?", (country_id,))
    row = cur.fetchone()
    count = (row["warheads"] or 0) if row else 0
    if count > 0:
        cur.execute("UPDATE countries SET warheads = 0 WHERE id = ?", (country_id,))
        conn.commit()
    conn.close()
    if count > 0:
        add_transaction(country_id, "iaea_disarm", f"☢️ {reason}", -count)
    return count


def set_npt_withdrawn(country_id: int, withdrawn: bool) -> tuple:
    """خروج/بازگشت به پیمان عدم اشاعه (NPT).

    خروج: سقف کلاهکِ غیر P5 برداشته می‌شود و هر تعلیق آژانسی غنی‌سازی بی‌اثر و لغو می‌گردد
          (آژانس بر کشور غیرعضو اختیاری ندارد).
    بازگشت: تنها در صورتی مجاز است تعداد کلاهک‌ها حداکثر برابر سقف مجاز باشد.
    خروجی: (موفق؟, پیام)
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM countries WHERE id = ?", (country_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return False, "کشور یافت نشد."
    c = dict(row)

    if withdrawn:
        cur.execute("""
            UPDATE countries SET npt_withdrawn = 1, enrichment_suspended = 0
            WHERE id = ?
        """, (country_id,))
        conn.commit()
        # بازمحاسبه تولید سوخت از مجتمع‌های غنی‌سازی (تعلیق لغو شده است)
        set_enrichment_suspended(country_id, False)
        add_transaction(country_id, "npt_withdraw", "🚪 خروج رسمی از پیمان عدم اشاعه (NPT) — سقف کلاهک برداشته و اختیارات آژانس لغو گردید.", 0)
        return True, "خروج از NPT ثبت شد."

    # بازگشت به پیمان — تنها با رعایت سقف مؤثر (اختصاصی یا پیش‌فرض)
    eff_cap = get_effective_warhead_cap(c)
    if eff_cap is not None and (c["warheads"] or 0) > eff_cap:
        conn.close()
        return False, f"برای بازگشت به NPT باید ابتدا زرادخانه خود را به سقف مجاز ({eff_cap} کلاهک) کاهش دهید. کلاهک فعلی: {c['warheads'] or 0}"

    cur.execute("UPDATE countries SET npt_withdrawn = 0 WHERE id = ?", (country_id,))
    conn.commit()
    conn.close()
    add_transaction(country_id, "npt_rejoin", "🕊️ بازگشت رسمی به پیمان عدم اشاعه (NPT) — سقف کلاهک و نظارت آژانس مجدداً برقرار شد.", 0)
    return True, "بازگشت به NPT ثبت شد."


def set_un_sanctioned(country_id: int, sanctioned: bool, reason: str = ""):
    """اعمال/لغو تحریم جامع سازمان ملل — درآمد روزانه نصف می‌شود و بازار جهانی بسته می‌گردد."""
    conn = get_connection()
    cur = conn.cursor()
    val = 1 if sanctioned else 0
    cur.execute("UPDATE countries SET un_sanctioned = ? WHERE id = ?", (val, country_id))
    conn.commit()
    conn.close()
    if sanctioned:
        add_transaction(country_id, "un_sanction", f"🚫 تحریم جامع سازمان ملل: {reason}", 0)
    else:
        add_transaction(country_id, "un_unsanction", "✅ لغو تحریم جامع سازمان ملل.", 0)


# قدرت‌های هسته‌ای رسمی (P5+) — سقف کلاهک پیش‌فرض: نامحدود
WARHEAD_P5 = ("usa", "russia", "china", "france", "uk", "pakistan", "india", "israel", "north_korea")


def get_effective_warhead_cap(c: dict):
    """سقف مؤثر نگهداری کلاهک کشور (خروجی None = نامحدود).

    اولویت:
      ۱) سقف اختصاصی مصوب آژانس/شورای امنیت (warhead_cap_override ≥ 0) — بر همه قوانین مقدم است
      ۲) قدرت هسته‌ای P5 → نامحدود
      ۳) خارج از پیمان عدم اشاعه → نامحدود
      ۴) بقیه کشورها → WARHEAD_MAX_NON_SUPERPOWER
    """
    if not c:
        return getattr(config, "WARHEAD_MAX_NON_SUPERPOWER", 5)
    override = c["warhead_cap_override"] if "warhead_cap_override" in c.keys() else None
    if override is not None and override >= 0:
        return int(override)
    key = c["country_key"] if "country_key" in c.keys() else None
    if key in WARHEAD_P5:
        return None
    if (c["npt_withdrawn"] or 0) if "npt_withdrawn" in c.keys() else 0:
        return None
    return int(getattr(config, "WARHEAD_MAX_NON_SUPERPOWER", 5))


def set_warhead_cap_override(country_id: int, value: int):
    """تنظیم سقف اختصاصی کلاهک توسط آژانس/شورای امنیت (مقدار -1 = بازگشت به قانون پیش‌فرض)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET warhead_cap_override = ? WHERE id = ?", (int(value), country_id))
    conn.commit()
    conn.close()


def adjust_grain(country_id: int, delta: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET grain = MAX(0, grain + ?) WHERE id = ?", (delta, country_id))
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
    import approval_system
    """به‌روزرسانی و بالانس درآمد روزانه، غلات، برق، نفت، تراشه‌ها و معادن تمام کشورها بر اساس مقادیر config."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id, country_key, oil_reserves, grain, population, microchips, iron_ore, uranium_ore, nuclear_fuel, warheads, enrichment_suspended FROM countries")
            countries = cur.fetchall()

            for c in countries:
                c_id = c["id"]
                c_key = c["country_key"]
                
                overrides = config.COUNTRY_STARTING_OVERRIDES.get(c_key, config.STARTING_VALUES)
                base_daily = overrides.get("daily_income", config.STARTING_VALUES["daily_income"])
                base_tax = overrides.get("tax_income", config.STARTING_VALUES["tax_income"])
                base_grain_daily = overrides.get("grain_daily", config.STARTING_VALUES.get("grain_daily", 2500))
                base_elec = overrides.get("electricity", config.STARTING_VALUES["electricity"])
                base_gold_daily = overrides.get("gold_daily", config.STARTING_VALUES["gold_daily"])
                base_oil_prod = overrides.get("oil_production", config.STARTING_VALUES.get("oil_production", 1_000_000))
                base_oil_res = overrides.get("oil_reserves", config.STARTING_VALUES.get("oil_reserves", 50_000_000))
                base_grain = overrides.get("grain", config.STARTING_VALUES.get("grain", 35_000))
                base_iron = overrides.get("iron_ore", config.STARTING_VALUES.get("iron_ore", 10_000))
                base_iron_daily = overrides.get("iron_ore_daily", config.STARTING_VALUES.get("iron_ore_daily", 500))
                base_chips = overrides.get("microchips", config.STARTING_VALUES.get("microchips", 1000))
                base_chips_daily = overrides.get("microchips_daily", config.STARTING_VALUES.get("microchips_daily", 25))
                base_uranium_ore = overrides.get("uranium_ore", config.STARTING_VALUES.get("uranium_ore", 0))
                base_uranium_ore_daily = overrides.get("uranium_ore_daily", config.STARTING_VALUES.get("uranium_ore_daily", 0))
                base_nuclear_fuel = overrides.get("nuclear_fuel", config.STARTING_VALUES.get("nuclear_fuel", 0))
                base_nuclear_fuel_daily = overrides.get("nuclear_fuel_daily", config.STARTING_VALUES.get("nuclear_fuel_daily", 0))
                base_warheads = overrides.get("warheads", config.STARTING_VALUES.get("warheads", 0))

                cur.execute("SELECT item_key, quantity FROM equipment WHERE country_id = ?", (c_id,))
                eq_rows = cur.fetchall()
                civ_income = 0
                civ_elec = 0
                civ_grain_daily = 0
                civ_gold_daily = 0
                civ_oil_prod = 0
                civ_iron_daily = 0
                civ_chips_daily = 0
                civ_uranium_ore_daily = 0
                civ_nuclear_fuel_daily = 0

                for eq in eq_rows:
                    i_key = eq["item_key"]
                    qty = eq["quantity"]
                    item = config.ALL_SHOP_ITEMS.get(i_key, {})
                    inc = item.get("income_add", 0)
                    oil_p = item.get("oil_prod_add", 0)
                    if i_key == "oil_refinery":
                        eff = config.get_refinery_effect(c_key)
                        inc = eff.get("income", inc)
                        oil_p = eff.get("oil_prod", oil_p)
                    elif i_key == "chip_fab":
                        eff = config.get_chip_fab_effect(c_key)
                        civ_chips_daily += eff.get("chips_daily", 25) * qty
                    elif i_key == "iron_mine":
                        civ_iron_daily += item.get("iron_ore_daily_add", 1_000) * qty
                    elif i_key == "uranium_mine":
                        civ_uranium_ore_daily += item.get("uranium_ore_daily_add", 50) * qty
                    elif i_key == "enrichment_facility":
                        civ_nuclear_fuel_daily += item.get("nuclear_fuel_daily_add", 20) * qty
                    
                    civ_income += inc * qty
                    civ_oil_prod += oil_p * qty
                    civ_elec += item.get("elec_add", 0) * qty
                    civ_grain_daily += item.get("grain_daily_add", 0) * qty
                    civ_gold_daily += item.get("gold_daily_add", 0) * qty

                new_total_daily = base_daily + civ_income
                new_grain_daily = base_grain_daily + civ_grain_daily
                new_elec = base_elec + civ_elec
                new_gold_daily = base_gold_daily + civ_gold_daily
                new_oil_prod = base_oil_prod + civ_oil_prod
                new_iron_daily = base_iron_daily + civ_iron_daily
                new_chips_daily = base_chips_daily + civ_chips_daily
                new_uranium_ore_daily = base_uranium_ore_daily + civ_uranium_ore_daily
                new_nuclear_fuel_daily = base_nuclear_fuel_daily + civ_nuclear_fuel_daily

                curr_oil_res = c["oil_reserves"] or 0
                curr_grain = c["grain"] or 0
                curr_iron = (c["iron_ore"] or 0) if "iron_ore" in c.keys() else 0
                curr_chips = (c["microchips"] or 0) if "microchips" in c.keys() else 0
                curr_uranium_ore = (c["uranium_ore"] or 0) if "uranium_ore" in c.keys() else 0
                curr_nuclear_fuel = (c["nuclear_fuel"] or 0) if "nuclear_fuel" in c.keys() else 0
                curr_warheads = (c["warheads"] or 0) if "warheads" in c.keys() else 0
                
                reqs = approval_system.calculate_country_requirements({'population': c['population'], 'id': c_id})
                # ذخایر و انبارها دارایی واقعی بازیکن هستند و در ری‌بالانس هرگز نباید ریست یا اوررایت شوند
                new_oil_res = curr_oil_res
                new_grain = curr_grain
                new_iron = curr_iron
                new_chips = curr_chips
                # 🧪 چرخه هسته‌ای: ذخایر هرگز از کانفیگ اهداء نمی‌شوند (فقط مقدار فعلی حفظ می‌شود)
                # و تولید روزانه فقط از تأسیسات خریداری‌شده (معدن اورانیوم / سایت غنی‌سازی) محاسبه می‌شود.
                # باگ قدیمی: max(curr, base) با هر ری‌استارت به‌صورت مجانی کلاهک/سوخت واقع‌گرایانه
                # (مثل ۱۷۷۰ کلاهک آمریکا) به کشورها می‌داد و هزینه نگهداری خزانه‌ها را منفی می‌کرد.
                new_uranium_ore = curr_uranium_ore
                new_nuclear_fuel = curr_nuclear_fuel
                new_warheads = curr_warheads
                # ⛔ تعلیق آژانسی غنی‌سازی (IAEA): تولید سوخت روزانه صفر می‌ماند
                suspended = (c["enrichment_suspended"] or 0) if "enrichment_suspended" in c.keys() else 0
                new_uranium_ore_daily = civ_uranium_ore_daily
                new_nuclear_fuel_daily = 0 if suspended else civ_nuclear_fuel_daily

                cur.execute("""
                    UPDATE countries SET
                    tax_income = ?,
                    daily_income = ?,
                    grain_daily = ?,
                    electricity = ?,
                    gold_daily = ?,
                    oil_production = ?,
                    oil_reserves = ?,
                    grain = ?,
                    iron_ore = ?,
                    iron_ore_daily = ?,
                    microchips = ?,
                    microchips_daily = ?,
                    uranium_ore = ?,
                    uranium_ore_daily = ?,
                    nuclear_fuel = ?,
                    nuclear_fuel_daily = ?,
                    warheads = ?
                    WHERE id = ?
                """, (base_tax, new_total_daily, new_grain_daily, new_elec, new_gold_daily, new_oil_prod, new_oil_res, new_grain, new_iron, new_iron_daily, new_chips, new_chips_daily, new_uranium_ore, new_uranium_ore_daily, new_nuclear_fuel, new_nuclear_fuel_daily, new_warheads, c_id))
    except Exception as e:
        print(f"Error rebalancing country incomes: {e}")


ONE_TIME_STOCK_BONUSES = {
    # item_key -> (ستون ذخیره، کلید کانفیگ مقدار پاداش)
    "grain_silo": ("grain", "grain_bonus"),
}


def apply_one_time_stock_bonus(country_id: int, item_key: str, delta_qty: int) -> dict:
    """اعمال پاداش «ذخیره فوری» هنگام تغییر تعداد ساخت‌وساز از پنل ادمین.

    باگ: برخی زیرساخت‌ها (مثل سیلوی غلات) علاوه بر درآمد روزانه، یک پاداش
    یک‌باره‌ی انبار دارند (grain_bonus = ۵۰٬۰۰۰ تن). این پاداش فقط داخل
    buy_item_transaction اعمال می‌شد؛ یعنی وقتی ادمین از پنل سیلو می‌داد،
    بازیکن هیچ غله‌ای نمی‌گرفت. برعکس، حذف سیلو هم غله را پس نمی‌گرفت.

    delta_qty مثبت → افزودن پاداش، منفی → پس گرفتن آن (با کف صفر).
    """
    spec = ONE_TIME_STOCK_BONUSES.get(item_key)
    if not spec or not delta_qty:
        return {}
    column, cfg_key = spec
    per_unit = config.ALL_SHOP_ITEMS.get(item_key, {}).get(cfg_key, 0)
    if not per_unit:
        return {}
    amount = per_unit * delta_qty
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                f"UPDATE countries SET {column} = MAX(0, {column} + ?) WHERE id = ?",
                (amount, country_id),
            )
        return {"column": column, "amount": amount}
    except Exception as e:
        print(f"[one-time-bonus] error for country {country_id}/{item_key}: {e}")
        return {}
    finally:
        conn.close()


def recalc_country_civ_effects(country_id: int) -> dict:
    """بازمحاسبهٔ عواید روزانهٔ یک کشور از روی ساخت‌وسازهای فعلی‌اش.

    باگ: دکمه‌های ±/صفر/تعیین عدد در پنل ادمین فقط جدول equipment را عوض
    می‌کردند و daily_income / grain_daily / electricity / ... دست‌نخورده
    می‌ماند. یعنی ادمین ۱۰ سیلو می‌داد و درآمد کشور تکان نمی‌خورد، یا ۳۰۵
    سیلوی اشتباهی را صفر می‌کرد ولی درآمد باد‌کردهٔ ناشی از آن‌ها برای همیشه
    در خزانه می‌ماند. rebalance سراسری هم فقط یک بار (فلگ rebalance_done_v3)
    اجرا می‌شود و قابل اتکا نیست.

    این تابع مقدار پایهٔ کانفیگ کشور + مجموع اثر تجهیزات را دقیقاً set می‌کند
    (نه MAX، نه جمع تجمعی) تا هر بار قابل اجرای مکرر و idempotent باشد.
    ذخایر انبار (grain, oil_reserves, ...) دارایی بازیکن‌اند و دست نمی‌خورند.
    """
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id, country_key, enrichment_suspended FROM countries WHERE id = ?", (country_id,))
            c = cur.fetchone()
            if not c:
                return {}
            c_key = c["country_key"]
            suspended = (c["enrichment_suspended"] or 0) if "enrichment_suspended" in c.keys() else 0

            ov = config.COUNTRY_STARTING_OVERRIDES.get(c_key, config.STARTING_VALUES)
            sv = config.STARTING_VALUES
            base = {
                "daily_income": ov.get("daily_income", sv["daily_income"]),
                "grain_daily": ov.get("grain_daily", sv.get("grain_daily", 2500)),
                "electricity": ov.get("electricity", sv["electricity"]),
                "gold_daily": ov.get("gold_daily", sv["gold_daily"]),
                "oil_production": ov.get("oil_production", sv.get("oil_production", 1_000_000)),
                "iron_ore_daily": ov.get("iron_ore_daily", sv.get("iron_ore_daily", 500)),
                "microchips_daily": ov.get("microchips_daily", sv.get("microchips_daily", 25)),
                "uranium_ore_daily": ov.get("uranium_ore_daily", sv.get("uranium_ore_daily", 0)),
                "nuclear_fuel_daily": ov.get("nuclear_fuel_daily", sv.get("nuclear_fuel_daily", 0)),
            }

            cur.execute("SELECT item_key, quantity FROM equipment WHERE country_id = ? AND quantity > 0", (country_id,))
            civ = {k: 0 for k in base}
            for eq in cur.fetchall():
                i_key, qty = eq["item_key"], eq["quantity"]
                item = config.ALL_SHOP_ITEMS.get(i_key, {})
                inc = item.get("income_add", 0)
                oil_p = item.get("oil_prod_add", 0)
                if i_key == "oil_refinery":
                    eff = config.get_refinery_effect(c_key)
                    inc = eff.get("income", inc)
                    oil_p = eff.get("oil_prod", oil_p)
                elif i_key == "chip_fab":
                    eff = config.get_chip_fab_effect(c_key)
                    civ["microchips_daily"] += eff.get("chips_daily", 25) * qty
                elif i_key == "iron_mine":
                    civ["iron_ore_daily"] += item.get("iron_ore_daily_add", 1_000) * qty
                elif i_key == "uranium_mine":
                    civ["uranium_ore_daily"] += item.get("uranium_ore_daily_add", 50) * qty
                elif i_key == "enrichment_facility":
                    civ["nuclear_fuel_daily"] += item.get("nuclear_fuel_daily_add", 20) * qty

                civ["daily_income"] += inc * qty
                civ["oil_production"] += oil_p * qty
                civ["electricity"] += item.get("elec_add", 0) * qty
                civ["grain_daily"] += item.get("grain_daily_add", 0) * qty
                civ["gold_daily"] += item.get("gold_daily_add", 0) * qty

            new = {k: max(0, base[k] + civ[k]) for k in base}
            # ⛔ تعلیق آژانسی غنی‌سازی: تولید سوخت روزانه صفر می‌ماند
            if suspended:
                new["nuclear_fuel_daily"] = 0

            cur.execute("""
                UPDATE countries SET
                daily_income = ?, grain_daily = ?, electricity = ?, gold_daily = ?,
                oil_production = ?, iron_ore_daily = ?, microchips_daily = ?,
                uranium_ore_daily = ?, nuclear_fuel_daily = ?
                WHERE id = ?
            """, (new["daily_income"], new["grain_daily"], new["electricity"], new["gold_daily"],
                  new["oil_production"], new["iron_ore_daily"], new["microchips_daily"],
                  new["uranium_ore_daily"], new["nuclear_fuel_daily"], country_id))
            return new
    except Exception as e:
        print(f"[recalc-civ-effects] error for country {country_id}: {e}")
        return {}


def fix_nuclear_free_grant_v1():
    """مایگریشن اصلاح باگ اهدای مجانی ذخایر هسته‌ای.

    باگ (کامیت چرخه سوخت اورانیوم): rebalance با max(curr, base) مقادیر واقع‌گرایانه‌ی
    کانفیگ (مثل ۱۷۷۰ کلاهک آمریکا، ۹۵هزار ک‌گ سوخت روسیه) را با هر ری‌استارت به‌صورت
    مجانی به کشورها اهداء می‌کرد؛ سپس هزینه نگهداری ۵,۰۰۰,۰۰۰ دلاریِ هر کلاهک
    خزانه بازیکنان را تا صدها میلیون منفی می‌کرد.

    اصلاح یک‌باره:
      ۱) صفر کردن ذخایر اورانیوم/سوخت غنی‌شده/کلاهک همه کشورها (طبق طراحی: همه از صفر)
      ۲) بازمحاسبه تولید روزانه فقط از تأسیسات خریداری‌شده (معدن/غنی‌سازی)
      ۳) بخشیدن بدهی خزانه‌های منفیِ ناشی از هزینه نگهداری اشتباه
    """
    if get_setting("nuclear_free_grant_fixed_v1"):
        return
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id, treasury, enrichment_suspended FROM countries")
    rows = cur.fetchall()
    fixed_stock = 0
    fixed_debt = 0
    affected = []       # (country_id, debt_relief) — تراکنش‌ها بعد از commit ثبت می‌شوند (جلوگیری از ددلاک)
    affected_stock_ids = []  # کشورهایی که ذخایر هسته‌ای مجانی گرفته بودند (برای جبرانه)
    for r in rows:
        c_id = r["id"]
        had_debt = (r["treasury"] or 0) < 0
        debt_relief = abs(r["treasury"]) if had_debt else 0

        # تولید روزانه فقط از تأسیسات خریداری‌شده (تعلیق آژانسی غنی‌سازی رعایت می‌شود)
        is_suspended = (r["enrichment_suspended"] or 0) if "enrichment_suspended" in r.keys() else 0
        cur.execute("SELECT item_key, quantity FROM equipment WHERE country_id = ?", (c_id,))
        u_daily = 0
        f_daily = 0
        for eq in cur.fetchall():
            item = config.ALL_SHOP_ITEMS.get(eq["item_key"], {})
            if eq["item_key"] == "uranium_mine":
                u_daily += item.get("uranium_ore_daily_add", 50) * eq["quantity"]
            elif eq["item_key"] == "enrichment_facility":
                f_daily += item.get("nuclear_fuel_daily_add", 20) * eq["quantity"]
        if is_suspended:
            f_daily = 0

        cur.execute("SELECT uranium_ore, nuclear_fuel, warheads FROM countries WHERE id = ?", (c_id,))
        pre = cur.fetchone()
        had_stock = any([(pre["uranium_ore"] or 0), (pre["nuclear_fuel"] or 0), (pre["warheads"] or 0)])

        cur.execute("""
            UPDATE countries SET
                uranium_ore = 0, nuclear_fuel = 0, warheads = 0,
                uranium_ore_daily = ?, nuclear_fuel_daily = ?,
                treasury = CASE WHEN treasury < 0 THEN 0 ELSE treasury END
            WHERE id = ?
        """, (u_daily, f_daily, c_id))

        if had_stock:
            fixed_stock += 1
            affected_stock_ids.append(c_id)
        if had_debt:
            fixed_debt += 1
        if had_stock or had_debt:
            affected.append((c_id, debt_relief))

    conn.commit()
    conn.close()

    # فهرست کشورهای آسیب‌دیده برای مایگریشن جبرانه
    if affected_stock_ids:
        set_setting("nuclear_bug_affected_ids", json.dumps(affected_stock_ids))

    # ثبت رسید تراکنش برای شفافیت — خارج از ترنزکشن اصلی (بدون قفل)
    for c_id, debt_relief in affected:
        desc = "🧪 اصلاحیه باگ هسته‌ای: ذخایر اورانیوم/سوخت/کلاهک به صفر بازنشانی شد"
        if debt_relief > 0:
            desc += f" و بدهی خزانه ({format_money(debt_relief)}) بخشیده شد"
        add_transaction(c_id, "nuclear_bug_fix", desc + ".", debt_relief)

    set_setting("nuclear_free_grant_fixed_v1", datetime.datetime.now(datetime.timezone.utc).isoformat())
    if fixed_stock or fixed_debt:
        print(f"[nuclear-migration] {fixed_stock} country nuclear stocks reset, {fixed_debt} negative treasuries rescued.")


def _get_nuclear_affected_ids():
    """فهرست کشورهایی که از باگ ذخایر هسته‌ای مجانی گرفته بودند.

    اولویت: setting مایگریشن ترمیم (nuclear_bug_affected_ids)،
    فالبک: رسیدهای تراکنش nuclear_bug_fix (اگر نسخهٔ قدیمیِ ترمیم اجرا شده باشد).
    """
    raw_ids = get_setting("nuclear_bug_affected_ids")
    if raw_ids:
        try:
            ids = [int(x) for x in json.loads(raw_ids)]
            if ids:
                return ids
        except Exception:
            pass
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT country_id FROM transactions WHERE type = 'nuclear_bug_fix'")
    ids = [r["country_id"] for r in cur.fetchall()]
    conn.close()
    return ids


def _get_zeroed_country_ids():
    """کشورهایی که خزانه‌شان با باگِ هزینه نگهداری هسته‌ای منفی/صفر شده
    و بدهی‌شان در مایگریشن ترمیم بخشیده شد (رسید با مبلغ مثبت)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT country_id FROM transactions WHERE type = 'nuclear_bug_fix' AND amount > 0")
    ids = [r["country_id"] for r in cur.fetchall()]
    conn.close()
    return ids


def _nuclear_comp_amount(row):
    """فرمول جبرانهٔ نهایی: حداقلِ سقف و (ضریب × درآمد روزانه + مالیات)."""
    cap = int(getattr(config, "NUCLEAR_COMPENSATION_CAP", 30_000_000))
    mult = int(getattr(config, "NUCLEAR_COMPENSATION_ECONOMY_MULT", 3))
    economy = (row["daily_income"] or 0) + (row["tax_income"] or 0)
    return min(cap, mult * economy)


def nuclear_compensation_v1():
    """🎁 جبرانهٔ اختلال هسته‌ای — فقط کشورهای صفرشده.

    قانون نهایی: فقط کشورهایی که خزانه‌شان با باگ صفر/منفی شده بود مشمول جبرانه‌اند.
    مبلغ = min(سقف، NUCLEAR_COMPENSATION_ECONOMY_MULT × درآمد روزانه + مالیات)
    (کشورهای اقتصادی قوی به سقف می‌رسند، بقیه متناسب با اقتصادشان کمتر می‌گیرند.)
    """
    if get_setting("nuclear_compensation_v1"):
        return

    target_ids = _get_zeroed_country_ids()
    if not target_ids:
        set_setting("nuclear_compensation_v1", datetime.datetime.now(datetime.timezone.utc).isoformat())
        return

    conn = get_connection()
    cur = conn.cursor()
    comp_list = []
    for c_id in target_ids:
        cur.execute("SELECT id, country_key, treasury, daily_income, tax_income FROM countries WHERE id = ?", (c_id,))
        row = cur.fetchone()
        if not row or row["country_key"] == "un":
            continue  # حذف‌شده یا actor سیستمی
        amount = _nuclear_comp_amount(row)
        if amount <= 0:
            continue
        cur.execute("UPDATE countries SET treasury = treasury + ? WHERE id = ?", (amount, c_id))
        comp_list.append((c_id, amount))
    conn.commit()
    conn.close()

    for c_id, amt in comp_list:
        add_transaction(
            c_id, "nuclear_compensation",
            f"🎁 جبرانهٔ اختلال هسته‌ای: {format_money(amt)} به خزانه اضافه شد (متناسب با اقتصاد، سقف {format_money(int(getattr(config, 'NUCLEAR_COMPENSATION_CAP', 30_000_000)))}).",
            amt
        )

    set_setting("nuclear_compensation_v1", datetime.datetime.now(datetime.timezone.utc).isoformat())
    if comp_list:
        print(f"[nuclear-compensation] {len(comp_list)} zeroed countries compensated (economy-based, capped).")


def nuclear_compensation_cap_v2():
    """♻️ سقف‌گذاری خزانهٔ کشورهای صفرشده (نسخهٔ محدودشده).

    فقط کشورهای صفرشده (بدهی‌بخشیده‌شده) را اگر خزانه‌شان بالای سقف جبرانه باشد
    به سقف برمی‌گرداند. کشورهای دیگر بهیچ‌وجه دست نمی‌خورند.
    """
    if get_setting("nuclear_compensation_cap_v2"):
        return
    cap = int(getattr(config, "NUCLEAR_COMPENSATION_CAP", 30_000_000))

    target_ids = _get_zeroed_country_ids()
    if not target_ids:
        set_setting("nuclear_compensation_cap_v2", datetime.datetime.now(datetime.timezone.utc).isoformat())
        return

    conn = get_connection()
    cur = conn.cursor()
    clamped = []
    for c_id in target_ids:
        cur.execute("SELECT id, country_key, treasury FROM countries WHERE id = ?", (c_id,))
        row = cur.fetchone()
        if not row or row["country_key"] == "un":
            continue
        tr = row["treasury"] or 0
        if tr > cap:
            cur.execute("UPDATE countries SET treasury = ? WHERE id = ?", (cap, c_id))
            clamped.append((c_id, tr - cap))
    conn.commit()
    conn.close()

    for c_id, excess in clamped:
        add_transaction(
            c_id, "nuclear_compensation_cap",
            f"♻️ تعدیل جبرانهٔ هسته‌ای: سقف جبرانه {format_money(cap)} بود و مبلغ اضافه ({format_money(excess)}) از خزانه کسر شد.",
            -excess
        )

    set_setting("nuclear_compensation_cap_v2", datetime.datetime.now(datetime.timezone.utc).isoformat())
    if clamped:
        print(f"[nuclear-compensation-cap] {len(clamped)} zeroed countries clamped to cap {format_money(cap)}.")


def nuclear_compensation_v3():
    """🧮 اصلاح نهایی جبرانهٔ قدیمی (پرداخت ثابت ۳۰M به همهٔ آسیب‌دیده‌ها).

    طبق تصمیم نهایی:
      ۱) کشورهای آسیب‌دیده‌ای که صفر نشده بودند (مثل عربستان) — کل جبرانهٔ دریافتی
         به آن‌ها برمی‌گردد (با احتساب هر مبلغی که قبلاً در تعدیل v2 کسر شده).
      ۲) کشورهای صفرشده — جبرانه‌شان دقیقاً طبق فرمول نهایی تنظیم می‌شود:
         min(سقف، ضریب × درآمد روزانه) — اگر کمتر از ۳۰M دریافتی‌شان باشد، مازاد کسر می‌شود.
    تشخیص پرداختِ قدیمی از روی رسیدهای nuclear_compensation بدون واژهٔ «سقف» است؛
    اگر چنین رسیدی وجود نداشته باشد (اجرای تازه)، این مایگریشن کاری نمی‌کند.
    """
    if get_setting("nuclear_compensation_v3"):
        return
    conn = get_connection()
    cur = conn.cursor()

    # پرداخت‌های جبرانهٔ قدیمی (ثابت ۳۰M) — رسیدهای بدون واژهٔ «سقف»
    cur.execute("""
        SELECT country_id, SUM(amount) AS s FROM transactions
        WHERE type = 'nuclear_compensation' AND description NOT LIKE '%سقف%'
        GROUP BY country_id
    """)
    flat_rows = cur.fetchall()
    if not flat_rows:
        conn.close()
        set_setting("nuclear_compensation_v3", datetime.datetime.now(datetime.timezone.utc).isoformat())
        return

    # مبالغی که قبلاً در تعدیل v2 کسر شده‌اند
    cur.execute("""
        SELECT country_id, SUM(amount) AS s FROM transactions
        WHERE type = 'nuclear_compensation_cap'
        GROUP BY country_id
    """)
    prev_removed = {r["country_id"]: -(r["s"] or 0) for r in cur.fetchall()}

    zeroed = set(_get_zeroed_country_ids())
    cap = int(getattr(config, "NUCLEAR_COMPENSATION_CAP", 30_000_000))

    returns_count = 0
    adjust_count = 0
    receipts = []  # (kind, country_id, remove, target) — بعد از commit ثبت می‌شوند
    for fr in flat_rows:
        c_id = fr["country_id"]
        given = fr["s"] or 0
        cur.execute("SELECT id, country_key, treasury, daily_income, tax_income FROM countries WHERE id = ?", (c_id,))
        row = cur.fetchone()
        if not row or row["country_key"] == "un":
            continue
        tr = row["treasury"] or 0

        if c_id in zeroed:
            # ۲) تنظیم دقیق طبق فرمول (فقط اگر دریافتی بیشتر از فرمول باشد کسر می‌شود)
            target = _nuclear_comp_amount(row)
            excess = given - target
            if excess > 0:
                remove = min(excess, max(tr, 0))
                if remove > 0:
                    cur.execute("UPDATE countries SET treasury = treasury - ? WHERE id = ?", (remove, c_id))
                    receipts.append(("adjust", c_id, remove, target))
                    adjust_count += 1
        else:
            # ۱) برگشت کامل جبرانهٔ نادرست (منهای کسرشدهٔ قبلی)
            to_remove = max(0, given - prev_removed.get(c_id, 0))
            remove = min(to_remove, max(tr, 0))
            if remove > 0:
                cur.execute("UPDATE countries SET treasury = treasury - ? WHERE id = ?", (remove, c_id))
                receipts.append(("return", c_id, remove, None))
                returns_count += 1

    conn.commit()
    conn.close()

    for kind, c_id, remove, target in receipts:
        if kind == "adjust":
            add_transaction(
                c_id, "nuclear_compensation_adjust",
                f"♻️ تنظیم دقیق جبرانهٔ هسته‌ای طبق اقتصاد کشور: سهم شما {format_money(target)} بود و مازاد ({format_money(remove)}) از خزانه کسر شد.",
                -remove
            )
        else:
            add_transaction(
                c_id, "nuclear_compensation_return",
                f"↩️ برگشت جبرانهٔ نادرست ({format_money(remove)}): فقط کشورهایی که خزانه‌شان صفر شده بود مشمول جبرانهٔ اختلال هسته‌ای هستند.",
                -remove
            )

    set_setting("nuclear_compensation_v3", datetime.datetime.now(datetime.timezone.utc).isoformat())
    print(f"[nuclear-compensation-v3] {returns_count} non-zeroed comp returned, {adjust_count} zeroed adjusted to formula.")


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

            # بررسی نیاز به میکروچیپ برای تجهیزات های‌تک
            chips_per_unit = config.get_equipment_chips_req(asset_dict)
            total_chips_needed = chips_per_unit * quantity

            # بررسی نیاز به سنگ آهن و فولاد برای ادوات زرهی، توپخانه و شناورها
            iron_per_unit = config.get_equipment_iron_req(asset_dict)
            total_iron_needed = iron_per_unit * quantity

            cur.execute("SELECT treasury, microchips, iron_ore FROM countries WHERE id = ?", (country_id,))
            c_row = cur.fetchone()
            if not c_row:
                return False, "کشور یافت نشد.", {}

            if c_row["treasury"] < total_cost:
                return False, f"موجودی خزانه کافی نیست!\nقیمت کل: {total_cost:,} دلار\nموجودی خزانه: {c_row['treasury']:,} دلار", asset_dict

            curr_chips = (c_row["microchips"] or 0) if "microchips" in c_row.keys() else 0
            if total_chips_needed > 0 and curr_chips < total_chips_needed:
                return False, (
                    f"❌ **کسری میکروچیپ پیشرفته:**\n\n"
                    f"برای ساخت {quantity:,} واحد از سلاح های‌تک *{asset_dict['equipment_name']}* به **{total_chips_needed:,} عدد تراشه پردازشی** نیاز دارید.\n"
                    f"• موجودی تراشه کشور شما: `{curr_chips:,} عدد`\n\n"
                    "💡 می‌توانید تراشه را از **بازار بورس کالا (/market)** یا **معاهدات دیپلماتیک (/trade)** از کشورهای تراشه‌ساز تهیه فرمایید."
                ), asset_dict

            curr_iron = (c_row["iron_ore"] or 0) if "iron_ore" in c_row.keys() else 0
            if total_iron_needed > 0 and curr_iron < total_iron_needed:
                return False, (
                    f"❌ **کسری آهن و فولاد:**\n\n"
                    f"برای ساخت {quantity:,} واحد از *{asset_dict['equipment_name']}* به **{total_iron_needed:,} تن آهن و فولاد** نیاز دارید.\n"
                    f"• موجودی آهن کشور شما: `{curr_iron:,} تن`\n\n"
                    "💡 می‌توانید سنگ آهن و فولاد را از **بازار بورس کالا (/market)**، **معاهدات دیپلماتیک (/trade)** یا با احداث **معدن آهن (/shop)** تأمین فرمایید."
                ), asset_dict

            cur.execute("""
                UPDATE countries SET
                treasury = treasury - ?,
                microchips = MAX(0, microchips - ?),
                iron_ore = MAX(0, iron_ore - ?)
                WHERE id = ?
            """, (total_cost, total_chips_needed, total_iron_needed, country_id))
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
            gold_req = item.get("gold_req", 0) * quantity
            chips_req = item.get("chips_req", 0) * quantity
            iron_req = item.get("iron_req", 0) * quantity
            income_add = item.get("income_add", 0) * quantity
            elec_add = item.get("elec_add", 0) * quantity
            gold_daily_add = item.get("gold_daily_add", 0) * quantity
            oil_prod_add = item.get("oil_prod_add", 0) * quantity
            grain_daily_add = item.get("grain_daily_add", 0) * quantity
            grain_bonus = item.get("grain_bonus", 0) * quantity
            iron_ore_daily_add = item.get("iron_ore_daily_add", 0) * quantity
            uranium_ore_daily_add = item.get("uranium_ore_daily_add", 0) * quantity
            nuclear_fuel_daily_add = item.get("nuclear_fuel_daily_add", 0) * quantity

            cur.execute("SELECT treasury, gold, microchips, oil_reserves, iron_ore, country_key, tech_level FROM countries WHERE id = ?", (country_id,))
            row = cur.fetchone()
            if not row:
                return False, "کشور پیدا نشد."

            c_key = row["country_key"]
            tech_lvl = row["tech_level"] or 1
            chips_daily_add = 0

            # بررسی پیش‌نیازهای اختصاصی معادن و صنایع خاص
            if item_key == "oil_refinery" and c_key:
                eff = config.get_refinery_effect(c_key)
                income_add = eff["income"] * quantity
                oil_prod_add = eff["oil_prod"] * quantity
            elif item_key == "chip_fab" and c_key:
                if tech_lvl < 2:
                    return False, "🔬 **پیش‌نیاز فناوری نامعتبر:** برای احداث کارخانه فب ساخت نیمه‌هادی، کشور شما ابتدا باید به سطح فناوری ۲ به بالا ارتقا یابد."
                eff = config.get_chip_fab_effect(c_key)
                income_add = eff["income"] * quantity
                chips_daily_add = eff["chips_daily"] * quantity
            elif item_key == "uranium_mine":
                allowed = item.get("allowed_countries", [])
                if c_key and allowed and c_key not in allowed:
                    return False, "⛔ **عدم وجود ذخایر طبیعی اورانیوم:** طبق ارزیابی‌های زمین‌شناسی، کشور شما دارای ذخایر معدنی قابل استخراج اورانیوم نیست. می‌توانید کیک زرد را از بورس کالا یا قراردادهای تجاری تامین فرمایید."
                if tech_lvl < item.get("tech_req", 2):
                    return False, f"🔬 **پیش‌نیاز فناوری:** برای تجهیز معدن اورانیوم نیاز به سطح فناوری {item.get('tech_req', 2)} به بالا دارید."
            elif item_key == "enrichment_facility":
                if tech_lvl < item.get("tech_req", 3):
                    return False, f"🔬 **پیش‌نیاز فناوری:** برای احداث مجتمع غنی‌سازی سانتریفیوژ نیاز به سطح فناوری {item.get('tech_req', 3)} به بالا دارید."

            if row["treasury"] < total_price:
                return False, f"موجودی خزانه کافی نیست!\nقیمت کل: {total_price:,} دلار\nخزانه فعلی: {row['treasury']:,} دلار"

            if oil_req > 0 and (row["oil_reserves"] or 0) < oil_req:
                return False, f"🛢️ ذخیره نفت کافی نیست!\nنفت مورد نیاز برای احداث: {oil_req:,} بشکه\nذخیره موجود: {(row['oil_reserves'] or 0):,} بشکه"

            if gold_req > 0 and (row["gold"] or 0) < gold_req:
                return False, f"🪙 طلا کافی نیست!\nطلا مورد نیاز: {gold_req:,} شمش\nموجودی فعلی: {(row['gold'] or 0):,} شمش"

            if chips_req > 0 and (row["microchips"] or 0) < chips_req:
                return False, f"💻 میکروچیپ کافی نیست!\nتراشه مورد نیاز: {chips_req:,} عدد\nموجودی فعلی: {(row['microchips'] or 0):,} عدد"

            if iron_req > 0 and (row["iron_ore"] or 0) < iron_req:
                return False, f"⛏️ آهن و فولاد کافی نیست!\nآهن مورد نیاز برای احداث: {iron_req:,} تن\nموجودی فعلی: {(row['iron_ore'] or 0):,} تن"

            cur.execute("""
                UPDATE countries SET
                treasury = treasury - ?,
                gold = MAX(0, gold - ?),
                microchips = MAX(0, microchips - ?),
                oil_reserves = MAX(0, oil_reserves - ?),
                iron_ore = MAX(0, iron_ore - ?),
                daily_income = daily_income + ?,
                electricity = electricity + ?,
                gold_daily = gold_daily + ?,
                oil_production = oil_production + ?,
                grain_daily = grain_daily + ?,
                grain = grain + ?,
                microchips_daily = microchips_daily + ?,
                iron_ore_daily = iron_ore_daily + ?,
                uranium_ore_daily = uranium_ore_daily + ?,
                nuclear_fuel_daily = nuclear_fuel_daily + ?
                WHERE id = ?
            """, (total_price, gold_req, chips_req, oil_req, iron_req, income_add, elec_add, gold_daily_add, oil_prod_add, grain_daily_add, grain_bonus, chips_daily_add, iron_ore_daily_add, uranium_ore_daily_add, nuclear_fuel_daily_add, country_id))

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

        return True, f"احداث {quantity} واحد **{item_name}** با موفقیت به پایان رسید و به زیرساخت‌های کشور اضافه گردید."
    except Exception as e:
        return False, f"خطا در دیتابیس: {e}"
    finally:
        conn.close()


def assemble_nuclear_warhead_transaction(country_id: int) -> tuple[bool, str]:
    """تولید و تسلیح ۱ کلاهک بازدارنده هسته‌ای با شرایط بسیار سخت‌گیرانه و ثبت در دیتابیس."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM countries WHERE id = ?", (country_id,))
            row = cur.fetchone()
            if not row:
                return False, "کشور یافت نشد."
            c = dict(row)

            tech_lvl = c["tech_level"] or 1
            if tech_lvl < getattr(config, "WARHEAD_PROD_TECH_REQ", 5):
                return False, f"🔬 **پیش‌نیاز فناوری نامعتبر:** برای مونتاژ کلاهک هسته‌ای، کشور شما باید به بالاترین سطح فناوری (سطح {getattr(config, 'WARHEAD_PROD_TECH_REQ', 5)}) دست یافته باشد."

            cur.execute("SELECT quantity FROM equipment WHERE country_id = ? AND item_key = 'enrichment_facility'", (country_id,))
            ef_row = cur.fetchone()
            has_enrichment = (ef_row and (ef_row["quantity"] or 0) > 0)
            is_p5 = c["country_key"] in ("usa", "russia", "china", "france", "uk", "pakistan", "india", "israel", "north_korea")

            if not has_enrichment and not is_p5:
                return False, "🔬 **عدم وجود مجتمع غنی‌سازی:** شما باید ابتدا حداقل ۱ واحد «مجتمع غنی‌سازی و سانتریفیوژ» احداث فرمایید."

            curr_warheads = c["warheads"] or 0
            eff_cap = get_effective_warhead_cap(c)
            if eff_cap is not None and curr_warheads >= eff_cap:
                return False, f"⛔ **سقف مجاز بازدارندگی هسته‌ای:** طبق پیمان‌های بین‌المللی و مصوبات آژانس/شورای امنیت، سقف نگهداری کلاهک فعال برای کشور شما حداکثر {eff_cap} عدد می‌باشد."

            cost_money = getattr(config, "WARHEAD_PROD_COST_MONEY", 150_000_000)
            cost_gold = getattr(config, "WARHEAD_PROD_COST_GOLD", 100)
            cost_chips = getattr(config, "WARHEAD_PROD_COST_CHIPS", 500)
            cost_ore = getattr(config, "WARHEAD_PROD_URANIUM_ORE", 500)

            if (c["treasury"] or 0) < cost_money:
                return False, f"💵 موجودی خزانه کافی نیست!\nهزینه مونتاژ: {format_money(cost_money)}\nخزانه شما: {format_money(c['treasury'] or 0)}"

            if (c["gold"] or 0) < cost_gold:
                return False, f"🪙 طلا کافی نیست!\nطلا مورد نیاز: {cost_gold} شمش\nموجودی فعلی: {c['gold'] or 0} شمش"

            if (c["microchips"] or 0) < cost_chips:
                return False, f"💻 میکروچیپ فوق‌پیشرفته کافی نیست!\nتراشه مورد نیاز: {cost_chips:,} عدد\nموجودی فعلی: {(c['microchips'] or 0):,} عدد"

            if (c["uranium_ore"] or 0) < cost_ore:
                return False, f"☢️ کیک زرد اورانیوم کافی نیست!\nاورانیوم مورد نیاز: {cost_ore:,} تن\nموجودی فعلی: {(c['uranium_ore'] or 0):,} تن"

            cur.execute("""
                UPDATE countries SET
                treasury = treasury - ?,
                gold = gold - ?,
                microchips = microchips - ?,
                uranium_ore = uranium_ore - ?,
                warheads = warheads + 1
                WHERE id = ?
            """, (cost_money, cost_gold, cost_chips, cost_ore, country_id))

            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute("""
                INSERT INTO transactions (country_id, type, description, amount, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (country_id, "warhead_assembly", "مونتاژ و تسلیح ۱ کلاهک راهبردی هسته‌ای", -cost_money, now_str))

            return True, f"🚀 **پروژه ساخت و تسلیح کلاهک هسته‌ای با موفقیت انجام شد!**\n\nتعداد کلاهک‌های فعال کشور: **{curr_warheads + 1} عدد**\n⚠️ هزینه نگهداری روزانه: ۵,۰۰۰,۰۰۰ دلار و ۲ میکروچیپ/روز"
    except Exception as e:
        return False, f"خطای دیتابیس: {e}"


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


def create_trade_contract(
    proposer_id: int,
    recipient_id: int,
    offered_type: str,
    offered_amount: int,
    requested_type: str,
    requested_amount: int,
    transport_payer: str = "seller",
    transport_cost: int = 0,
    offered_key: str = None,
    transport_mode: str = "sea",
    is_smuggled: int = 0,
    origin_country_key: str = None,
    license_country_id: int = None,
    license_status: str = "approved"
) -> int:
    conn = get_connection()
    cur = conn.cursor()
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    status = "pending_license" if license_status == "pending" else "pending"
    cur.execute("""
        INSERT INTO trade_contracts
        (proposer_id, recipient_id, offered_type, offered_key, offered_amount, requested_type, requested_amount, transport_payer, transport_cost, transport_mode, is_smuggled, origin_country_key, license_country_id, license_status, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (proposer_id, recipient_id, offered_type, offered_key, offered_amount, requested_type, requested_amount, transport_payer, transport_cost, transport_mode, is_smuggled, origin_country_key, license_country_id, license_status, status, now_str))
    contract_id = cur.lastrowid
    conn.commit()
    conn.close()
    return contract_id


def approve_export_license(contract_id: int, licenser_country_id: int) -> tuple[bool, str, dict]:
    """تایید و صدور مجوز صادرات تسلیحات توسط کشور سازنده."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM trade_contracts WHERE id = ?", (contract_id,))
            row = cur.fetchone()
            if not row:
                return False, "معاهده یافت نشد.", None
            c = dict(row)
            if c.get("license_country_id") != licenser_country_id:
                return False, "شما صلاحیت صدور مجوز این معاهده را ندارید.", None
            if c.get("status") != "pending_license":
                return False, "این معاهده قبلاً تعیین تکلیف شده است.", None

            cur.execute("""
                UPDATE trade_contracts
                SET license_status = 'approved', status = 'pending'
                WHERE id = ?
            """, (contract_id,))
            c["license_status"] = "approved"
            c["status"] = "pending"
            return True, "مجوز صادرات با موفقیت صادر گردید و معاهده جهت امضا به کشور خریدار ارسال شد.", c
    except Exception as e:
        return False, f"خطا در دیتابیس: {e}", None
    finally:
        conn.close()


def veto_export_license(contract_id: int, licenser_country_id: int) -> tuple[bool, str, dict]:
    """وتوی معاهده تسلیحاتی و ممانعت از انتقال سلاح توسط کشور سازنده."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM trade_contracts WHERE id = ?", (contract_id,))
            row = cur.fetchone()
            if not row:
                return False, "معاهده یافت نشد.", None
            c = dict(row)
            if c.get("license_country_id") != licenser_country_id:
                return False, "شما صلاحیت وتوی این معاهده را ندارید.", None
            if c.get("status") != "pending_license":
                return False, "این معاهده قبلاً تعیین تکلیف شده است.", None

            cur.execute("""
                UPDATE trade_contracts
                SET license_status = 'vetoed', status = 'vetoed'
                WHERE id = ?
            """, (contract_id,))
            c["license_status"] = "vetoed"
            c["status"] = "vetoed"
            return True, "معاهده تسلیحاتی وتو شد و از انتقال جنگ‌افزار ممانعت به عمل آمد.", c
    except Exception as e:
        return False, f"خطا در دیتابیس: {e}", None
    finally:
        conn.close()


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


def get_country_pending_sent_contracts(country_id: int) -> list:
    """دریافت لیست قراردادهای معلق ارسالی که هنوز پاسخ داده نشده‌اند."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.*, c.name as target_name, c.flag as target_flag, c.country_key as target_key
        FROM trade_contracts t
        JOIN countries c ON t.recipient_id = c.id
        WHERE t.proposer_id = ? AND t.status = 'pending'
        ORDER BY t.id DESC
    """, (country_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_country_pending_received_contracts(country_id: int) -> list:
    """دریافت لیست قراردادهای معلق دریافتی که منتظر تصمیم این کشور هستند."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.*, c.name as sender_name, c.flag as sender_flag, c.country_key as sender_key
        FROM trade_contracts t
        JOIN countries c ON t.proposer_id = c.id
        WHERE t.recipient_id = ? AND t.status = 'pending'
        ORDER BY t.id DESC
    """, (country_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def cancel_pending_contract_by_proposer(proposer_id: int, contract_id: int) -> tuple[bool, str]:
    """لغو قرارداد معلق توسط پیشنهاددهنده و آزادسازی آن."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM trade_contracts WHERE id = ? AND proposer_id = ?", (contract_id, proposer_id))
            row = cur.fetchone()
            if not row:
                return False, "قرارداد مورد نظر یافت نشد یا متعلق به شما نیست."

            c = dict(row)
            if c["status"] != "pending":
                return False, f"این قرارداد قبلاً تعیین تکلیف شده است (وضعیت: {c['status']})."

            cur.execute("UPDATE trade_contracts SET status = 'canceled' WHERE id = ?", (contract_id,))
        return True, "پیشنهاد قرارداد تجاری با موفقیت لغو و ابطال گردید."
    except Exception as e:
        return False, f"خطا در لغو قرارداد: {e}"


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
            if c.get("status") == "pending_license":
                return False, "این معاهده هنوز در انتظار صدور مجوز صادرات از سوی کشور سازنده است."
            if c.get("status") == "vetoed":
                return False, "این معاهده توسط کشور سازنده وتو شده و فاقد اعتبار قانونی است."
            if c.get("status") != "pending":
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
                p_c_key = p_c.get("country_key")
                r_c_key = r_c.get("country_key")
                if not has_open_sea_access(p_c_key) or not has_open_sea_access(r_c_key):
                    no_sea_c = p_c if not has_open_sea_access(p_c_key) else r_c
                    return False, f"⚓ **امکان ترابری دریایی وجود ندارد:** کشور {no_sea_c['flag']} **{no_sea_c['name']}** محصور در خشکی است و به آب‌های آزاد دسترسی ساحلی ندارد. لطفاً این معاهده با ترابری هوایی یا زمینی صادر شود."

                if is_country_blockaded(p_id) or is_country_blockaded(r_id):
                    return False, "⚓ **امکان اجرای معاهده از طریق ترابری دریایی وجود ندارد:** خطوط مواصلاتی دریایی یکی از دو کشور تحت محاصره کامل دریایی است. لطفا برای این معاهده از ترابری هوایی یا زمینی استفاده بفرمایید."

                # Check Strait Blockades & Tolls based on realistic geographic maritime route
                for owner_key, strait_info in STRAITS_MAPPING.items():
                    s_key = strait_info["strait_key"]
                    st_data = get_strait_status(s_key)
                    st_status = st_data["status"]
                    st_toll = st_data["toll"]

                    p_c_key = p_c.get("country_key")
                    r_c_key = r_c.get("country_key")

                    if is_trade_route_crossing_strait(p_c_key, r_c_key, s_key):
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

            # Check capacity limits for commodity transport
            t_limits = getattr(config, "TRANSPORT_CAPACITY_LIMITS", {}).get(t_mode, {}).get("limits", {})
            if off_type in t_limits and off_amt > t_limits[off_type]:
                t_name = getattr(config, "TRANSPORT_CAPACITY_LIMITS", {}).get(t_mode, {}).get("name", t_mode)
                return False, f"⛔ **مازاد ظرفیت بارگیری ناوگان ({t_name}):** حداکثر ظرفیت قابل انتقال در هر محموله برابر با **{t_limits[off_type]:,} واحد** است."

            p_extra_cost = t_cost if t_payer == "seller" else 0
            r_extra_cost = t_cost if t_payer == "buyer" else 0

            col_map = {"treasury": "treasury", "gold": "gold", "oil": "oil_reserves", "grain": "grain", "iron_ore": "iron_ore", "microchips": "microchips", "uranium_ore": "uranium_ore", "nuclear_fuel": "nuclear_fuel"}

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

                is_smuggled = bool(c.get("is_smuggled"))
                delivered_amt = off_amt
                lost_amt = 0
                is_intercepted = False

                if is_smuggled:
                    import random
                    # ۲۵٪ ریسک ردگیری اطلاعاتی و توقیف نیمی از محموله در مرز
                    if random.random() < 0.25:
                        is_intercepted = True
                        delivered_amt = max(1, off_amt // 2)
                        lost_amt = off_amt - delivered_amt
                        cur.execute("UPDATE countries SET approval_rating = MAX(0, approval_rating - 3) WHERE id = ?", (p_id,))

                # 1. Deduct asset from proposer
                cur.execute("UPDATE country_assets SET amount = amount - ? WHERE id = ?", (off_amt, asset_dict["id"]))

                # 2. Add delivered asset to recipient (producible=0)
                cur.execute("""
                    INSERT INTO country_assets
                    (country_id, country_key, category, equipment_name, equipment_key, amount, buy_price, maintenance_cost, producible)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
                    ON CONFLICT(country_id, equipment_key) DO UPDATE SET amount = amount + ?
                """, (r_id, r_c["country_key"], asset_dict["category"], asset_dict["equipment_name"], off_key, delivered_amt, asset_dict["buy_price"], asset_dict["maintenance_cost"], delivered_amt))

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
                """, (p_id, f"انتقال نظامی {asset_dict['equipment_name']} x{off_amt} به {r_c['name']}{' (قاچاق مخفیانه)' if is_smuggled else ''}", req_amt, now_str))
                cur.execute("""
                    INSERT INTO transactions (country_id, type, description, amount, created_at)
                    VALUES (?, 'asset_transfer_in', ?, ?, ?)
                """, (r_id, f"دریافت تسلیحات نظامی {asset_dict['equipment_name']} x{delivered_amt} از {p_c['name']}", -req_amt, now_str))

                if is_intercepted:
                    return True, f"INTERCEPTED:{lost_amt}:{delivered_amt}:{asset_dict['equipment_name']}:{c.get('origin_country_key') or ''}"
                elif is_smuggled:
                    return True, f"SMUGGLED_SAFE:{delivered_amt}:{asset_dict['equipment_name']}"
                else:
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


def execute_foreign_aid_transaction(donor_id: int, recipient_id: int, resource_type: str, amount: int, transport_mode: str = "sea") -> tuple[bool, str]:
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
            d_key = d_c.get("country_key")
            r_key = r_c.get("country_key")

            cost_map = {"air": 2_000_000, "land": 1_000_000, "sea": 300_000}
            t_cost = cost_map.get(transport_mode, 300_000)

            # بررسی سقف ظرفیت بارگیری برای روش ترابری انتخاب‌شده
            t_limits = getattr(config, "TRANSPORT_CAPACITY_LIMITS", {}).get(transport_mode, {}).get("limits", {})
            max_cap = 20_000_000 if resource_type == "treasury" else t_limits.get(resource_type, 100_000)
            if amount > max_cap:
                t_name = getattr(config, "TRANSPORT_CAPACITY_LIMITS", {}).get(transport_mode, {}).get("name", transport_mode)
                return False, f"⛔ **مازاد بر ظرفیت بارگیری ناوگان ({t_name}):** حداکثر سقف ارسال برای این کالا برابر با **{max_cap:,} واحد** در هر محموله است."

            # بررسی دسترسی دریایی و محاصره در ترابری دریایی
            if transport_mode == "sea":
                if not has_open_sea_access(d_key) or not has_open_sea_access(r_key):
                    no_sea = d_c if not has_open_sea_access(d_key) else r_c
                    return False, f"⚓ **ترابری دریایی ممکن نیست:** کشور {no_sea['flag']} {no_sea['name']} محصور در خشکی است. لطفاً از ترابری هوایی یا زمینی استفاده فرمایید."

                if is_country_blockaded(donor_id) or is_country_blockaded(recipient_id):
                    return False, "⚓ **ترابری دریایی مسدود است:** خطوط کشتیرانی یکی از دو کشور تحت محاصره دریایی است. لطفاً از ترابری هوایی یا زمینی استفاده فرمایید."

                # بررسی انسداد و عوارض تنگه‌ها
                for owner_key, strait_info in STRAITS_MAPPING.items():
                    s_key = strait_info["strait_key"]
                    if is_trade_route_crossing_strait(d_key, r_key, s_key):
                        st_data = get_strait_status(s_key)
                        if st_data.get("status") == "blocked" and owner_key not in (d_key, r_key):
                            return False, f"⛔ **مسیر ترانزیت دریایی مسدود است:** {strait_info['name']} توسط کشور {owner_key} مسدود گردیده است. از ترابری هوایی یا زمینی استفاده کنید."
                        elif st_data.get("status") == "toll" and owner_key not in (d_key, r_key):
                            st_toll = st_data.get("toll", 0)
                            if st_toll > 0:
                                t_cost += st_toll

            # بررسی موجودی کالا و هزینه ترانزیت
            col_map = {"treasury": "treasury", "gold": "gold", "oil": "oil_reserves", "grain": "grain", "iron_ore": "iron_ore", "microchips": "microchips", "uranium_ore": "uranium_ore", "nuclear_fuel": "nuclear_fuel"}
            col_name = col_map.get(resource_type, "treasury")

            donor_money_avail = d_c["treasury"] - (amount if resource_type == "treasury" else 0)
            if donor_money_avail < t_cost:
                return False, f"💵 **کسری بودجه برای پرداخت هزینه ترانزیت:** هزینه حمل‌ونقل و ترانزیت این محموله برابر با **{format_money(t_cost)}** است و موجودی خزانه شما کافی نیست."

            if d_c[col_name] < amount:
                return False, f"موجودی {resource_type} کشور شما برای ارسال این کمک کافی نیست."

            # کسر هزینه ترانزیت از اهداکننده
            if t_cost > 0:
                cur.execute("UPDATE countries SET treasury = treasury - ? WHERE id = ?", (t_cost, donor_id))

            cur.execute(f"UPDATE countries SET {col_name} = {col_name} - ? WHERE id = ?", (amount, donor_id))
            cur.execute(f"UPDATE countries SET {col_name} = {col_name} + ? WHERE id = ?", (amount, recipient_id))

            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute("""
                INSERT INTO transactions (country_id, type, description, amount, created_at)
                VALUES (?, 'aid_out', ?, ?, ?)
            """, (donor_id, f"ارسال کمک خارجی ({transport_mode}) به {r_c['name']} (هزینه ترانزیت: {format_money(t_cost)})", -amount if resource_type == "treasury" else 0, now_str))
            cur.execute("""
                INSERT INTO transactions (country_id, type, description, amount, created_at)
                VALUES (?, 'aid_in', ?, ?, ?)
            """, (recipient_id, f"دریافت کمک خارجی ({transport_mode}) از {d_c['name']}", amount if resource_type == "treasury" else 0, now_str))

            return True, "کمک خارجی با موفقیت و پرداخت هزینه ترانزیت ارسال شد."
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
        elif any(c in eq_name for c in ["corvette", "کوروت", "buyan", "steregushchiy", "sa'ar", "baynunah", "soleimani", "شهید سلیمانی", "فاتح", "پیروز"]):
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


def has_active_oil_import_contract(country_id: int) -> bool:
    """بررسی وجود قرارداد فعال واردات نفت خام برای کشورهای صنعتی فاقد نفت."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) as count FROM trade_contracts WHERE recipient_id = ? AND offered_type = 'oil' AND status = 'accepted'", (country_id,))
    row = cur.fetchone()
    conn.close()
    return bool(row and row["count"] > 0)


def get_industrial_oil_consumption(country_id: int) -> int:
    """محاسبه متوازن و واقعی مصرف روزانه سوخت صنعتی نیروگاه‌ها و کارخانجات کشور."""
    equipment = get_equipment(country_id)
    fossil_count = equipment.get("fossil_plant", 0)
    small_f = equipment.get("small_factory", 0)
    med_f = equipment.get("medium_factory", 0)
    large_f = equipment.get("large_factory", 0)
    ind_comp = equipment.get("industrial_complex", 0)

    # مصرف سوخت صنعتی نیروگاه فسیلی (۱۰k بشکه)، کارخانجات (۵۰۰ تا ۶k بشکه)
    ind_oil_need = (fossil_count * 10_000) + (small_f * 500) + (med_f * 1_500) + (large_f * 3_000) + (ind_comp * 6_000)
    return ind_oil_need


def calculate_country_maintenance_cost(country_id: int) -> dict:
    """محاسبه متوازن هزینه نگهداری روزانه تسلیحات و ارتش با تخفیف سطح فناوری (Tech Level) و اشتراک VIP."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT active_personnel, tech_level, warheads, is_vip, vip_tier FROM countries WHERE id = ?", (country_id,))
    c_row = cur.fetchone()
    if not c_row:
        conn.close()
        return {"assets_maint": 0, "personnel_maint": 0, "warheads_maint": 0, "warheads_chips_maint": 0, "total_maint": 0, "discount_pct": 0, "vip_discount_pct": 0, "tech_level": 1, "warheads": 0}

    c_data = dict(c_row)
    active_p = c_data.get("active_personnel") or 0
    tech_lvl = c_data.get("tech_level") or 1
    warheads_count = c_data.get("warheads") or 0

    discount_pct = min(40, (tech_lvl - 1) * 10)

    # تخفیف نگهداری ارتش سطح VIP
    vip_discount_pct = 0
    if c_data.get("is_vip"):
        vt = c_data.get("vip_tier") or ""
        if vt == "diamond":
            vip_discount_pct = 25
        elif vt == "gold":
            vip_discount_pct = 15
        elif vt == "silver":
            vip_discount_pct = 10
        elif vt == "bronze":
            vip_discount_pct = 5
        else:
            vip_discount_pct = 10

    cur.execute("SELECT amount, maintenance_cost FROM country_assets WHERE country_id = ? AND amount > 0", (country_id,))
    asset_rows = cur.fetchall()
    conn.close()

    raw_assets_maint = sum(r["amount"] * (r["maintenance_cost"] or 0) for r in asset_rows)
    scaled_maint = int(raw_assets_maint * 0.01)
    tech_factor = (1 - (discount_pct / 100.0))
    vip_factor = (1 - (vip_discount_pct / 100.0))

    assets_maint = int(scaled_maint * tech_factor * vip_factor)
    personnel_maint = int(active_p * 0.5 * vip_factor)
    warheads_maint = int(warheads_count * getattr(config, "WARHEAD_MAINTENANCE_COST", 5_000_000))
    warheads_chips_maint = int(warheads_count * getattr(config, "WARHEAD_CHIPS_MAINTENANCE", 2))
    total_maint = assets_maint + personnel_maint + warheads_maint

    return {
        "assets_maint": assets_maint,
        "personnel_maint": personnel_maint,
        "warheads_maint": warheads_maint,
        "warheads_chips_maint": warheads_chips_maint,
        "total_maint": total_maint,
        "discount_pct": discount_pct,
        "vip_discount_pct": vip_discount_pct,
        "tech_level": tech_lvl,
        "warheads": warheads_count
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


def get_roleplays_by_filter(status: str = None, is_vip_only: bool = False, limit: int = 10, offset: int = 0) -> tuple[list, int]:
    """دریافت رول‌ها بر اساس وضعیت و فیلتر VIP با صفحه‌بندی و شمارش کل."""
    conn = get_connection()
    cur = conn.cursor()
    base_where = "WHERE 1=1"
    params = []
    if status:
        base_where += " AND r.status = ?"
        params.append(status)
    if is_vip_only:
        base_where += " AND COALESCE(c.is_vip, 0) = 1 AND r.status IN ('pending', 'approved')"

    # شمارش کل
    count_sql = f"SELECT COUNT(*) as total FROM pending_roleplays r LEFT JOIN countries c ON r.country_id = c.id {base_where}"
    cur.execute(count_sql, params)
    crow = cur.fetchone()
    total = (crow["total"] or 0) if crow else 0

    # دریافت ردیف‌ها
    data_sql = f"""
        SELECT r.*, c.name as country_name, c.flag as country_flag, COALESCE(c.is_vip, 0) as is_vip
        FROM pending_roleplays r
        LEFT JOIN countries c ON r.country_id = c.id
        {base_where}
        ORDER BY r.id DESC LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    cur.execute(data_sql, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows], total


def get_roleplay_counts() -> dict:
    """دریافت آمار زنده دسته‌بندی‌های مختلف رول‌ها جهت نمایش در منو."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT status, COUNT(*) as cnt FROM pending_roleplays GROUP BY status")
    rows = cur.fetchall()
    counts = {r["status"]: r["cnt"] for r in rows}

    cur.execute("""
        SELECT COUNT(*) as cnt FROM pending_roleplays r
        JOIN countries c ON r.country_id = c.id
        WHERE COALESCE(c.is_vip, 0) = 1 AND r.status IN ('pending', 'approved')
    """)
    vip_row = cur.fetchone()
    vip_cnt = (vip_row["cnt"] or 0) if vip_row else 0
    conn.close()
    return {
        "pending": counts.get("pending", 0),
        "approved": counts.get("approved", 0),
        "rejected": counts.get("rejected", 0),
        "archived": counts.get("archived", 0),
        "vip": vip_cnt
    }


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
        "affected_keys": ["uae", "qatar", "saudi", "iraq", "kuwait", "bahrain"]
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
        "affected_keys": [
            "uk", "france", "germany", "italy", "greece", "cyprus", "turkey", "romania", "bulgaria",
            "georgia", "russia", "ukraine", "israel", "jordan", "saudi", "sudan", "eritrea", "somalia",
            "india", "pakistan", "china", "japan", "south_korea", "singapore", "malaysia", "thailand",
            "vietnam", "bangladesh", "sri_lanka"
        ]
    },
    "yemen": {
        "strait_key": "bab_el_mandeb",
        "name": "تنگه استراتژیک باب‌المندب و دریای سرخ",
        "desc": "گلوگاه ترانزیت دریای سرخ و باب‌المندب (کلید امنیت کشتیرانی تجاری به کانال سوئز)",
        "affected_keys": [
            "israel", "jordan", "sudan", "egypt", "saudi", "usa", "uk", "france", "germany",
            "italy", "china", "india", "japan", "south_korea", "somalia"
        ]
    },
    "eritrea": {
        "strait_key": "bab_el_mandeb_west",
        "name": "تنگه باب‌المندب و جزایر دهلک (ضلع غربی)",
        "desc": "گذرگاه غربی ورودی دریای سرخ و آبراه‌های شاخ آفریقا",
        "affected_keys": ["israel", "jordan", "sudan", "egypt", "saudi", "yemen", "usa", "uk", "france"]
    },
    "turkey": {
        "strait_key": "bosphorus",
        "name": "تنگه بسفر و دردانل (پیمان مونترو)",
        "desc": "دروازه انحصاری عبور و مرور دریای سیاه به آب‌های آزاد و مدیترانه",
        "affected_keys": ["russia", "ukraine", "romania", "bulgaria", "georgia"]
    },
    "morocco": {
        "strait_key": "gibraltar_south",
        "name": "تنگه استراتژیک جبل‌الطارق (ضلع جنوبی)",
        "desc": "دروازه ورود و خروج اقیانوس اطلس به دریای مدیترانه",
        "affected_keys": [
            "italy", "greece", "cyprus", "turkey", "romania", "bulgaria", "georgia", "russia", "ukraine",
            "egypt", "israel", "tunisia", "algeria", "libya", "syria", "lebanon", "croatia"
        ]
    },
    "spain": {
        "strait_key": "gibraltar_north",
        "name": "تنگه استراتژیک جبل‌الطارق (ضلع شمالی)",
        "desc": "دروازه ورود و خروج اقیانوس اطلس به دریای مدیترانه",
        "affected_keys": [
            "italy", "greece", "cyprus", "turkey", "romania", "bulgaria", "georgia", "russia", "ukraine",
            "egypt", "israel", "tunisia", "algeria", "libya", "syria", "lebanon", "croatia"
        ]
    },
    "denmark": {
        "strait_key": "danish_straits",
        "name": "تنگه‌های بالتیک (اورسوند و گریت بلت)",
        "desc": "شریان حیاتی ورود و خروج دریای شمال به دریای بالتیک",
        "affected_keys": ["sweden", "finland", "poland", "germany", "russia"]
    },
    "indonesia": {
        "strait_key": "malacca",
        "name": "تنگه مالاکا و سوندا",
        "desc": "گلوگاه ترانزیت انرژی و تجارت شرق آسیا و اقیانوس آرام",
        "affected_keys": [
            "china", "japan", "south_korea", "taiwan", "thailand", "vietnam", "cambodia",
            "philippines", "myanmar", "bangladesh", "australia", "new_zealand"
        ]
    },
    "malaysia": {
        "strait_key": "malacca_north",
        "name": "تنگه مالاکا (ضلع شمالی)",
        "desc": "مسیر اصلی کشتیرانی بین‌المللی شرق آسیا",
        "affected_keys": [
            "china", "japan", "south_korea", "taiwan", "thailand", "vietnam", "cambodia",
            "philippines", "singapore", "indonesia"
        ]
    },
    "singapore": {
        "strait_key": "singapore_strait",
        "name": "گلوگاه تنگه سنگاپور",
        "desc": "پرترافیک‌ترین تقاطع و شریان کانتینری و نفتی جهان",
        "affected_keys": [
            "china", "japan", "south_korea", "taiwan", "vietnam", "thailand", "cambodia",
            "philippines", "indonesia", "malaysia"
        ]
    },
    "china": {
        "strait_key": "taiwan_strait_cn",
        "name": "تنگه تایوان (ضلع غربی)",
        "desc": "گلوگاه ترانزیت دریای چین جنوبی و شرقی",
        "affected_keys": ["taiwan", "japan", "south_korea", "philippines", "usa"]
    },
    "taiwan": {
        "strait_key": "taiwan_strait_tw",
        "name": "تنگه تایوان (ضلع شرقی)",
        "desc": "خط ترانزیت و پدافند دریایی تایوان",
        "affected_keys": ["china"]
    },
    "india": {
        "strait_key": "andaman_malacca",
        "name": "آبراه استراتژیک آندامان و ورودی مالاکا (Andaman & Nicobar Command)",
        "desc": "شاهراه ترانزیت انرژی خلیج فارس به شرق آسیا و دهانه ورودی غربی تنگه مالاکا",
        "affected_keys": [
            "china", "japan", "south_korea", "taiwan", "singapore", "malaysia", "thailand",
            "vietnam", "indonesia", "cambodia"
        ]
    },
    "chile": {
        "strait_key": "magellan_drake",
        "name": "تنگه ماژلان و گذرگاه دریک",
        "desc": "شاهراه ترانزیت بین اقیانوس اطلس و اقیانوس آرام در جنوب قاره آمریکا",
        "affected_keys": ["argentina", "brazil", "peru", "ecuador", "colombia", "usa"]
    }
}


def is_trade_route_crossing_strait(country1_key: str, country2_key: str, strait_key: str) -> bool:
    """بررسی واقعی عبور مسیر دریایی بین دو کشور از یک تنگه یا کانال استراتژیک بر اساس جغرافیای دریایی."""
    if not country1_key or not country2_key:
        return False

    c1, c2 = country1_key.lower(), country2_key.lower()
    if c1 == c2:
        return False

    # حوزه خلیج فارس
    PERSIAN_GULF = {"iran", "iraq", "kuwait", "saudi", "bahrain", "qatar", "uae", "oman"}

    # حوزه غرب/شمال سوئز (اروپا، مدیترانه، قاره آمریکا، اقیانوس اطلس)
    SUEZ_WEST = {
        "uk", "france", "germany", "italy", "spain", "portugal", "belgium", "netherlands", "denmark",
        "norway", "sweden", "finland", "poland", "croatia", "greece", "cyprus", "turkey", "romania",
        "bulgaria", "russia", "ukraine", "georgia", "algeria", "tunisia", "libya", "morocco", "syria",
        "lebanon", "israel", "usa", "canada", "mexico", "brazil", "argentina", "chile", "colombia",
        "peru", "ecuador", "nigeria", "angola", "south_africa", "cuba", "venezuela", "austria", "belarus",
        "czech", "hungary", "serbia", "slovakia"
    }

    # حوزه شرق/جنوب سوئز (دریای سرخ، خلیج فارس، اقیانوس هند، آسیای جنوبی و شرقی، اقیانوسیه)
    SUEZ_EAST = {
        "saudi", "yemen", "oman", "uae", "qatar", "kuwait", "iraq", "iran", "sudan", "eritrea",
        "somalia", "kenya", "ethiopia", "pakistan", "india", "sri_lanka", "bangladesh", "myanmar",
        "thailand", "cambodia", "vietnam", "malaysia", "singapore", "indonesia", "philippines",
        "taiwan", "china", "japan", "south_korea", "north_korea", "australia", "new_zealand"
    }

    # کشورهای ساحلی دریای سرخ
    RED_SEA_LITTORAL = {"jordan", "sudan", "egypt", "israel", "saudi", "yemen", "eritrea"}

    # حوزه دریای سیاه
    BLACK_SEA = {"russia", "ukraine", "romania", "bulgaria", "georgia"}

    # حوزه دریای مدیترانه
    MEDITERRANEAN = {
        "italy", "greece", "cyprus", "croatia", "turkey", "romania", "bulgaria", "georgia",
        "russia", "ukraine", "egypt", "israel", "lebanon", "syria", "libya", "tunisia", "algeria"
    }

    # کشورهای اقیانوس اطلس و آمریکا (خارج از مدیترانه)
    ATLANTIC_OUTSIDE = {
        "usa", "canada", "mexico", "cuba", "venezuela", "brazil", "argentina", "chile", "colombia",
        "peru", "ecuador", "uk", "norway", "sweden", "finland", "denmark", "germany", "netherlands",
        "belgium", "poland", "portugal", "south_africa", "nigeria", "angola"
    }

    # حوزه غرب مالاکا (اقیانوس هند، خاورمیانه، آفریقا، اروپا)
    MALACCA_WEST = {
        "india", "pakistan", "sri_lanka", "bangladesh", "iran", "iraq", "kuwait", "saudi", "qatar",
        "uae", "oman", "yemen", "egypt", "sudan", "somalia", "kenya", "south_africa",
        "uk", "france", "germany", "italy", "spain", "netherlands", "turkey", "russia", "greece"
    }

    # حوزه شرق مالاکا (شرق و جنوب شرق آسیا در اقیانوس آرام)
    MALACCA_EAST = {
        "china", "japan", "south_korea", "north_korea", "taiwan", "philippines", "vietnam", "cambodia", "thailand"
    }

    if strait_key in ("hormuz", "hormuz_south"):
        return (c1 in PERSIAN_GULF) != (c2 in PERSIAN_GULF)

    elif strait_key == "suez":
        # کانال سوئز تنها زمانی طی می‌شود که یک طرف در غرب/شمال سوئز و طرف دیگر در شرق/جنوب سوئز باشد
        return (c1 in SUEZ_WEST and c2 in SUEZ_EAST) or (c1 in SUEZ_EAST and c2 in SUEZ_WEST)

    elif strait_key in ("bab_el_mandeb", "bab_el_mandeb_west"):
        # باب‌المندب اتصال دریای سرخ/اروپا به اقیانوس هند و آسیا است
        is_c1_north = c1 in RED_SEA_LITTORAL or c1 in SUEZ_WEST
        is_c2_north = c2 in RED_SEA_LITTORAL or c2 in SUEZ_WEST
        is_c1_south = c1 in SUEZ_EAST and c1 not in RED_SEA_LITTORAL
        is_c2_south = c2 in SUEZ_EAST and c2 not in RED_SEA_LITTORAL
        return (is_c1_north and is_c2_south) or (is_c2_north and is_c1_south)

    elif strait_key == "bosphorus":
        return (c1 in BLACK_SEA) != (c2 in BLACK_SEA)

    elif strait_key in ("gibraltar_north", "gibraltar_south"):
        # جبل‌الطارق دروازه ورود/خروج مدیترانه به اقیانوس اطلس است
        return (c1 in MEDITERRANEAN and c2 in ATLANTIC_OUTSIDE) or (c1 in ATLANTIC_OUTSIDE and c2 in MEDITERRANEAN)

    elif strait_key == "danish_straits":
        baltic_countries = {"sweden", "finland", "poland"}
        return (c1 in baltic_countries and c2 not in baltic_countries and c2 not in MEDITERRANEAN) or \
               (c2 in baltic_countries and c1 not in baltic_countries and c1 not in MEDITERRANEAN)

    elif strait_key in ("malacca", "malacca_north", "singapore_strait", "andaman_malacca"):
        return (c1 in MALACCA_WEST and c2 in MALACCA_EAST) or (c1 in MALACCA_EAST and c2 in MALACCA_WEST)

    elif strait_key in ("taiwan_strait_cn", "taiwan_strait_tw"):
        return (c1 == "taiwan" and c2 == "china") or (c1 == "china" and c2 == "taiwan")

    elif strait_key == "magellan_drake":
        return (c1 in {"argentina", "brazil"} and c2 in {"chile", "peru", "ecuador"}) or \
               (c2 in {"argentina", "brazil"} and c1 in {"chile", "peru", "ecuador"})

    return False


def get_strait_info_by_country_key(country_key: str):
    return STRAITS_MAPPING.get(country_key)


def get_strait_status(strait_key: str) -> dict:
    status = get_setting(f"strait_status_{strait_key}", "open")
    toll = int(get_setting(f"strait_toll_{strait_key}", "1000000"))
    return {"status": status, "toll": toll}


def set_strait_status(strait_key: str, status: str, toll_amount: int = 1000000):
    set_setting(f"strait_status_{strait_key}", status)
    set_setting(f"strait_toll_{strait_key}", str(toll_amount))


def check_strait_navy_qualification(country_id: int) -> tuple[bool, int, int]:
    """بررسی برخورداری از حداقل توان دریایی لازم جهت اعمال اقتدار و مسدودسازی تنگه.
    
    حداقل شرایط: حداقل ۵ شناور/واحد رزمی دریایی فعال و ارزش کل حداقل ۱۰ میلیون دلار.
    """
    assets = get_country_assets(country_id, category="Navy") or []
    units = sum((a.get("amount", 0) or 0) for a in assets)
    val = sum((a.get("amount", 0) or 0) * (a.get("buy_price", 0) or 0) for a in assets)
    qualified = (units >= 5 and val >= 10_000_000)
    return qualified, units, val


def auto_check_and_reopen_straits_if_navy_destroyed() -> list:
    """بررسی وضعیت تمام تنگه‌ها و محاصره‌های دریایی و بازگشایی خودکار در صورت نابودی یا تضعیف ناوگان دریایی کشور کنترل‌کننده."""
    reopened = []
    for owner_key, strait_info in STRAITS_MAPPING.items():
        s_key = strait_info["strait_key"]
        st_data = get_strait_status(s_key)

        if st_data["status"] in ("blocked", "toll"):
            owner_c = get_country_by_key(owner_key)
            if not owner_c:
                continue

            qualified, units, val = check_strait_navy_qualification(owner_c["id"])
            if not qualified:
                set_strait_status(s_key, "open", 0)
                reopened.append({
                    "owner": owner_c,
                    "strait_info": strait_info,
                    "prev_status": st_data["status"],
                    "units": units,
                    "val": val
                })

    # بررسی و لغو خودکار محاصره‌های دریایی در صورت نابودی ناوگان محاصره‌کننده
    try:
        active_blks = get_all_active_blockades()
        for blk in active_blks:
            b_id = blk["blockader_id"]
            t_id = blk["target_id"]
            qualified, units, val = check_strait_navy_qualification(b_id)
            if not qualified:
                lift_naval_blockade(b_id, t_id)
                t_c = get_country_by_id(t_id)
                if t_c and not is_country_blockaded(t_id):
                    new_app = min(100, (t_c.get("approval_rating") or 80) + 15)
                    update_country_field(t_id, "approval_rating", new_app)
    except Exception:
        pass

    return reopened


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

    # 🚫 تحریم جامع سازمان ملل: بازار جهانی برای کشور تحریمی بسته است
    conn0 = get_connection()
    cur0 = conn0.cursor()
    cur0.execute("SELECT un_sanctioned FROM countries WHERE id = ?", (seller_id,))
    s_row = cur0.fetchone()
    conn0.close()
    if s_row and (s_row["un_sanctioned"] or 0):
        return False, "🚫 **تحریم جامع سازمان ملل:** امکان عرضه کالا در بورس جهانی برای کشور شما مسدود است."

    # قیمت کف: نفت را نمی‌توان زیر قیمت پایه در بورس عرضه کرد
    if resource_type == "oil" and unit_price < config.OIL_GLOBAL_PRICE:
        return False, (
            f"⛔ **قیمت هر بشکه نفت نمی‌تواند کمتر از قیمت کف بازار باشد.**\n\n"
            f"• قیمت کف نفت در بورس: **{config.OIL_GLOBAL_PRICE:,} $/بشکه**\n"
            f"• قیمت پیشنهادی شما: {unit_price:,} $/بشکه\n\n"
            f"💡 لطفاً نفت خود را در بورس با قیمتی برابر یا بالاتر از کف عرضه کنید."
        )

    resource_cols = {
        "oil": "oil_reserves",
        "gold": "gold",
        "grain": "grain",
        "iron_ore": "iron_ore",
        "microchips": "microchips",
        "uranium_ore": "uranium_ore",
        "nuclear_fuel": "nuclear_fuel"
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
                res_names = {"oil": "نفت", "gold": "طلا", "grain": "غلات", "iron_ore": "آهن و فولاد", "microchips": "میکروچیپ", "uranium_ore": "کیک زرد", "nuclear_fuel": "سوخت هسته‌ای"}
                return False, f"موجودی {res_names.get(resource_type, resource_type)} کافی نیست! (موجودی فعلی: {current_qty:,})"

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

            resource_cols = {"oil": "oil_reserves", "gold": "gold", "grain": "grain", "iron_ore": "iron_ore", "microchips": "microchips", "uranium_ore": "uranium_ore", "nuclear_fuel": "nuclear_fuel"}
            col = resource_cols.get(res_type)

            if col and rem_amount > 0:
                cur.execute(f"UPDATE countries SET {col} = {col} + ? WHERE id = ?", (rem_amount, seller_id))

            cur.execute("DELETE FROM market_orders WHERE id = ?", (order_id,))

        return True, "عرضه با موفقیت لغو شد و کالای باقی‌مانده به انبار کشور عودت داده گردید."
    except Exception as e:
        return False, f"خطا در لغو سفارش: {e}"


def reset_all_market_orders() -> tuple[bool, int, dict]:
    """ریست کامل بازار بورس توسط مدیریت و بازگردانی ۱۰۰٪ تمام کالاهای عرضه‌شده به انبار کشورهای فروشنده."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                SELECT m.*, c.name as seller_name, c.flag as seller_flag, c.player_id
                FROM market_orders m
                JOIN countries c ON m.seller_id = c.id
            """)
            orders = cur.fetchall()

            if not orders:
                return True, 0, {"oil": 0, "gold": 0, "grain": 0, "iron_ore": 0, "countries_affected": 0, "player_ids": []}

            refunded = {"oil": 0, "gold": 0, "grain": 0, "iron_ore": 0, "microchips": 0, "uranium_ore": 0, "nuclear_fuel": 0, "affected_countries": set(), "player_ids": set()}
            resource_cols = {"oil": "oil_reserves", "gold": "gold", "grain": "grain", "iron_ore": "iron_ore", "microchips": "microchips", "uranium_ore": "uranium_ore", "nuclear_fuel": "nuclear_fuel"}

            for ord_row in orders:
                o = dict(ord_row)
                seller_id = o["seller_id"]
                res_type = o["resource_type"]
                amount = o["amount"]

                col = resource_cols.get(res_type)
                if col and amount > 0:
                    cur.execute(f"UPDATE countries SET {col} = {col} + ? WHERE id = ?", (amount, seller_id))
                    refunded[res_type] = refunded.get(res_type, 0) + amount
                    refunded["affected_countries"].add(seller_id)
                    if o.get("player_id"):
                        refunded["player_ids"].add(o["player_id"])

            cur.execute("DELETE FROM market_orders")

        summary = {
            "oil": refunded.get("oil", 0),
            "gold": refunded.get("gold", 0),
            "grain": refunded.get("grain", 0),
            "iron_ore": refunded.get("iron_ore", 0),
            "microchips": refunded.get("microchips", 0),
            "uranium_ore": refunded.get("uranium_ore", 0),
            "nuclear_fuel": refunded.get("nuclear_fuel", 0),
            "countries_affected": len(refunded["affected_countries"]),
            "player_ids": list(refunded["player_ids"]),
            "total_orders": len(orders)
        }
        return True, len(orders), summary
    except Exception as e:
        return False, 0, {"error": str(e)}


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

            # 🚫 تحریم جامع سازمان ملل: بازار برای کشورهای تحریمی (خریدار یا فروشنده) بسته است
            if seller and (seller["un_sanctioned"] or 0):
                return False, "🚫 **تحریم جامع سازمان ملل:** امکان خرید از این عرضه وجود ندارد — کشور فروشنده تحت تحریم جامع است.", {}
            if buyer and (buyer["un_sanctioned"] or 0):
                return False, "🚫 **تحریم جامع سازمان ملل:** بورس جهانی برای کشور شما مسدود است و امکان خرید وجود ندارد.", {}

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
                    s_key = seller_c.get("country_key")
                    b_key = buyer_c.get("country_key")
                    if is_trade_route_crossing_strait(s_key, b_key, strait_info["strait_key"]) and owner_key not in (s_key, b_key):
                        st_status = get_strait_status(strait_info["strait_key"])
                        if st_status["status"] in ("blocked", "closed"):
                            return False, f"⚓ **گلوگاه دریایی مسدود است:** مسیر ترانزیت دریایی از {strait_info['name']} توسط کشور {owner_key} مسدود شده است.", {}

            res_type = order["resource_type"]
            res_names = {"oil": "نفت", "gold": "طلا", "grain": "غلات", "iron_ore": "آهن و فولاد", "microchips": "میکروچیپ", "uranium_ore": "کیک زرد", "nuclear_fuel": "سوخت هسته‌ای"}
            unit_names = {"oil": "بشکه", "gold": "شمش", "grain": "تن", "iron_ore": "تن", "microchips": "عدد", "uranium_ore": "تن", "nuclear_fuel": "کیلوگرم"}
            res_label = res_names.get(res_type, res_type)

            # بررسی سقف ظرفیت بارگیری ناوگان ترابری
            t_limits = getattr(config, "TRANSPORT_CAPACITY_LIMITS", {}).get(transport_mode, {}).get("limits", {})
            max_cap = t_limits.get(res_type, 999_999_999)
            if buy_amount > max_cap:
                t_name = getattr(config, "TRANSPORT_CAPACITY_LIMITS", {}).get(transport_mode, {}).get("name", transport_mode)
                return False, f"⛔ **مازاد ظرفیت بارگیری ناوگان:**\n\nحداکثر ظرفیت قابل حمل برای **{res_label}** در {t_name} برابر با **{max_cap:,} {unit_names.get(res_type, 'واحد')}** در هر محموله است.\n\n💡 لطفاً روش ترابری با ظرفیت بالاتر (مثل دریایی/زمینی) انتخاب فرمایید یا حجم خرید را کاهش دهید.", {}

            transport_costs = {"sea": 300_000, "land": 1_000_000, "air": 2_000_000}
            t_cost = transport_costs.get(transport_mode, 300_000)

            unit_price = order["unit_price"]
            commodity_cost = buy_amount * unit_price
            total_buyer_cost = commodity_cost + t_cost

            if buyer_c["treasury"] < total_buyer_cost:
                return False, f"موجودی خزانه کافی نیست!\nارزش کالا: {format_money(commodity_cost)}\nهزینه ترابری: {format_money(t_cost)}\nمجموع هزینه: {format_money(total_buyer_cost)}\nخزانه شما: {format_money(buyer_c['treasury'])}", {}

            resource_cols = {"oil": "oil_reserves", "gold": "gold", "grain": "grain", "iron_ore": "iron_ore", "microchips": "microchips", "uranium_ore": "uranium_ore", "nuclear_fuel": "nuclear_fuel"}
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
    for r_type in ("oil", "gold", "grain", "iron_ore", "microchips", "uranium_ore", "nuclear_fuel"):
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

# ---------- 🕵️‍♂️ سیستم اطلاعات، امنیت ملی و کادر فرماندهی ----------

def get_intel_agency_info(country_key: str) -> dict:
    """دریافت مشخصات رسمی و رتبه اطلاعاتی سازمان امنیت کشور."""
    if not country_key:
        return config.DEFAULT_INTELLIGENCE_AGENCY
    return config.INTELLIGENCE_AGENCIES.get(country_key, config.DEFAULT_INTELLIGENCE_AGENCY)


def seed_country_commanders(country_id: int, country_key: str):
    """ثبت و همگام‌سازی کادر فرماندهی اختصاصی هر کشور."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            presets = config.COUNTRY_COMMANDERS_PRESETS.get(country_key, config.DEFAULT_COMMANDERS)
            for cmd in presets:
                cur.execute("""
                    INSERT INTO country_commanders (country_id, key, title, status)
                    VALUES (?, ?, ?, 'active')
                    ON CONFLICT(country_id, key) DO UPDATE SET title = excluded.title
                """, (country_id, cmd["key"], cmd["title"]))
    except Exception as e:
        print(f"Error seeding commanders: {e}")


def get_country_commanders(country_id: int) -> list:
    """دریافت فهرست کادر فرماندهی و وضعیت حیات آنان."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM country_commanders WHERE country_id = ? ORDER BY id ASC", (country_id,))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        c = get_country_by_id(country_id)
        if c and c.get("country_key"):
            seed_country_commanders(country_id, c["country_key"])
            return get_country_commanders(country_id)
    return [dict(r) for r in rows]


def kill_commander(country_id: int, commander_key: str, reason: str = "ترور اطلاعاتی") -> tuple[bool, str]:
    """شهادت یا ترور یکی از سران نظامی و فعال شدن شوک خلاء فرماندهی."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            now_dt = datetime.datetime.now(datetime.timezone.utc)
            now_str = now_dt.isoformat()
            until_dt = now_dt + datetime.timedelta(hours=24)
            until_str = until_dt.isoformat()

            cur.execute("""
                UPDATE country_commanders SET status = 'assassinated', killed_at = ?
                WHERE country_id = ? AND (key = ? OR title LIKE ?) AND status = 'active'
            """, (now_str, country_id, commander_key, f"%{commander_key}%"))

            affected = cur.rowcount
            if affected > 0:
                cur.execute("""
                    UPDATE countries SET
                    combat_readiness = MAX(0, combat_readiness - 15),
                    command_disrupted_until = ?
                    WHERE id = ?
                """, (until_str, country_id))
                cur.execute("""
                    INSERT INTO transactions (country_id, type, description, amount, created_at)
                    VALUES (?, 'commander_killed', ?, 0, ?)
                """, (country_id, f"🎖️ شهادت / ترور {commander_key} ({reason})", now_str))
                return True, f"فرمانده {commander_key} مورد اصابت قرار گرفت و وضعیت وی به ترور/شهید تغییر یافت."
            return False, "فرمانده یافت نشد یا قبلاً ترور شده است."
    except Exception as e:
        return False, str(e)


def revive_commander(country_id: int, commander_key: str) -> bool:
    """انتصاب فرمانده جدید پس از پایان دوره سوگواری و بازسازی فرماندهی."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE country_commanders SET status = 'active', killed_at = NULL
                WHERE country_id = ? AND (key = ? OR title LIKE ?)
            """, (country_id, commander_key, f"%{commander_key}%"))
        return True
    except Exception:
        return False


def get_country_intel_attack_defense(country_id: int) -> tuple[int, int]:
    """محاسبه نمرات قدرت سایبری تهاجمی و پدافند ضدجاسوسی با فایروال و فناوری."""
    c = get_country_by_id(country_id)
    if not c:
        return 50, 50
    agency = get_intel_agency_info(c.get("country_key"))
    tech_lvl = c.get("tech_level", 1) or 1
    fw_lvl = c.get("firewall_level", 1) or 1
    fw_bonus = config.FIREWALL_UPGRADES.get(fw_lvl, {}).get("defense_bonus", 0)

    offense = agency["base_offense"] + (tech_lvl * 5)
    defense = agency["base_defense"] + (tech_lvl * 5) + fw_bonus
    return offense, defense


def upgrade_firewall_transaction(country_id: int) -> tuple[bool, str]:
    """ارتقای سطح فایروال و پدافند سایبری ملی با مصرف میکروچیپ و بودجه."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM countries WHERE id = ?", (country_id,))
            row = cur.fetchone()
            if not row:
                return False, "کشور یافت نشد."
            c = dict(row)

            curr_lvl = c.get("firewall_level", 1) or 1
            if curr_lvl >= 5:
                return False, "🛡️ پدافند سایبری کشور شما در بالاترین سطح (سطح ۵ - قلعه نفوذناپذیر) قرار دارد."

            next_lvl = curr_lvl + 1
            up_info = config.FIREWALL_UPGRADES[next_lvl]
            cost_money = up_info["cost_money"]
            cost_chips = up_info["cost_chips"]

            if (c["treasury"] or 0) < cost_money:
                return False, f"💵 موجودی خزانه کافی نیست! نیاز: {format_money(cost_money)}"
            if (c["microchips"] or 0) < cost_chips:
                return False, f"💻 میکروچیپ کافی نیست! نیاز: {cost_chips} عدد"

            cur.execute("""
                UPDATE countries SET
                treasury = treasury - ?,
                microchips = microchips - ?,
                firewall_level = ?
                WHERE id = ?
            """, (cost_money, cost_chips, next_lvl, country_id))

            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute("""
                INSERT INTO transactions (country_id, type, description, amount, created_at)
                VALUES (?, 'firewall_upgrade', ?, ?, ?)
            """, (country_id, f"ارتقای فایروال ملی به {up_info['label']}", -cost_money, now_str))

        return True, f"🛡️ **سپر سایبری با موفقیت ارتقا یافت!**\nسطح جدید: **{up_info['label']}** (+{up_info['defense_bonus']}٪ مقاومت)"
    except Exception as e:
        return False, str(e)


def execute_intel_operation(attacker_id: int, target_id: int, op_type: str, chips_boost: int = 0) -> tuple[bool, str, dict]:
    """اجرای عملیات اطلاعاتی/سایبری با محاسبه شانس، پیامدها، گمنامی و رسوایی بین‌المللی."""
    import random
    op_cfg = config.INTEL_OPERATIONS_CONFIG.get(op_type)
    if not op_cfg:
        return False, "نوع عملیات نامعتبر است.", {}

    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM countries WHERE id = ?", (attacker_id,))
            att = cur.fetchone()
            cur.execute("SELECT * FROM countries WHERE id = ?", (target_id,))
            tgt = cur.fetchone()

            if not att or not tgt:
                return False, "کشور مهاجم یا هدف یافت نشد.", {}

            att_c = dict(att)
            tgt_c = dict(tgt)

            today_str = datetime.date.today().isoformat()
            last_date = att_c.get("intel_ops_date")
            ops_today = att_c.get("intel_ops_today", 0) if last_date == today_str else 0

            if ops_today >= config.INTEL_DAILY_OPERATION_LIMIT:
                return False, f"⏳ **سقف مجاز روزانه:** هر سازمان اطلاعاتی حداکثر مجاز به اجرای {config.INTEL_DAILY_OPERATION_LIMIT} عملیات در هر ۲۴ ساعت می‌باشد.", {}

            now_dt = datetime.datetime.now(datetime.timezone.utc)
            last_time_raw = att_c.get("last_intel_op_time")
            if last_time_raw:
                try:
                    last_time = datetime.datetime.fromisoformat(last_time_raw)
                    diff_h = (now_dt - last_time).total_seconds() / 3600.0
                    if diff_h < config.INTEL_OPERATION_COOLDOWN_HOURS:
                        rem_h = config.INTEL_OPERATION_COOLDOWN_HOURS - diff_h
                        return False, f"⏳ **زمان بازسازی شبکه نفوذ (Cooldown):** تیم‌های اطلاعاتی در حال ریکاوری هستند. زمان باقی‌مانده: {rem_h:.1f} ساعت.", {}
                except Exception:
                    pass

            cost_money = op_cfg["cost_money"]
            cost_chips = op_cfg["cost_chips"] + chips_boost

            if (att_c["treasury"] or 0) < cost_money:
                return False, f"💵 بودجه سیاه کافی نیست! نیاز: {format_money(cost_money)}", {}
            if (att_c["microchips"] or 0) < cost_chips:
                return False, f"💻 میکروچیپ کافی نیست! نیاز: {cost_chips} عدد", {}

            # کسر منابع عملیات
            cur.execute("""
                UPDATE countries SET
                treasury = treasury - ?,
                microchips = microchips - ?,
                last_intel_op_time = ?,
                intel_ops_today = ?,
                intel_ops_date = ?
                WHERE id = ?
            """, (cost_money, cost_chips, now_dt.isoformat(), ops_today + 1, today_str, attacker_id))

            # محاسبه شانس موفقیت و خروجی عملیات
            att_off, _ = get_country_intel_attack_defense(attacker_id)
            _, tgt_def = get_country_intel_attack_defense(target_id)
            att_off += chips_boost * 2

            score_diff = att_off - tgt_def
            success_prob = max(15, min(85, 50 + int(score_diff * 0.8)))
            roll = random.randint(1, 100)

            att_agency = get_intel_agency_info(att_c.get("country_key"))

            meta = {
                "attacker": att_c,
                "target": tgt_c,
                "op_cfg": op_cfg,
                "op_type": op_type,
                "success_prob": success_prob,
                "roll": roll,
                "agency": att_agency,
            }

            now_str = now_dt.isoformat()

            if roll <= success_prob:
                # موفقیت کامل (Clean Strike)
                result_code = "clean_success"
                dur = op_cfg.get("duration_hours", 24)
                until_str = (now_dt + datetime.timedelta(hours=dur)).isoformat()

                if op_type == "cyber_air_defense":
                    cur.execute("UPDATE countries SET air_defense_disrupted_until = ? WHERE id = ?", (until_str, target_id))
                elif op_type == "cyber_blackout":
                    cur.execute("UPDATE countries SET blackout_until = ?, approval_rating = MAX(0, approval_rating - 5) WHERE id = ?", (until_str, target_id))
                elif op_type == "cyber_centrifuge":
                    cur.execute("UPDATE countries SET nuclear_fuel = MAX(0, nuclear_fuel - 50), enrichment_suspended = 1 WHERE id = ?", (target_id,))
                elif op_type == "sabotage_pipeline":
                    cur.execute("UPDATE countries SET oil_reserves = MAX(0, oil_reserves - 150000) WHERE id = ?", (target_id,))
                elif op_type == "assassination_scientist":
                    cur.execute("UPDATE countries SET r_and_d_frozen_until = ? WHERE id = ?", ((now_dt + datetime.timedelta(hours=48)).isoformat(), target_id))
                elif op_type == "assassination_commander":
                    cmds = get_country_commanders(target_id)
                    alive = [cm for cm in cmds if cm["status"] == "active"]
                    if alive:
                        chosen_cmd = random.choice(alive)
                        kill_commander(target_id, chosen_cmd["key"], "عملیات ترور هدفمند")
                        meta["killed_commander"] = chosen_cmd

                meta["result"] = result_code
                cur.execute("""
                    INSERT INTO intel_operations_history (attacker_id, target_id, op_type, result, details, created_at)
                    VALUES (?, ?, ?, ?, 'موفقیت کامل و گمنام', ?)
                """, (attacker_id, target_id, op_type, result_code, now_str))
                return True, "عملیات اطلاعاتی با موفقیت کامل و بدون بر جای گذاشتن ردپا اجرا گردید.", meta

            else:
                # شکست: بررسی لو رفتن هویت یا دفع ناشناس
                expose_roll = random.randint(1, 100)
                if expose_roll <= 35:
                    # رسوایی بین‌المللی (Busted & Exposed)
                    result_code = "busted_exposed"
                    cur.execute("UPDATE countries SET approval_rating = MAX(0, approval_rating - 5) WHERE id = ?", (attacker_id,))
                    meta["result"] = result_code
                    cur.execute("""
                        INSERT INTO intel_operations_history (attacker_id, target_id, op_type, result, details, created_at)
                        VALUES (?, ?, ?, ?, 'شکست و افشای هویت در کانال اخبار', ?)
                    """, (attacker_id, target_id, op_type, result_code, now_str))
                    return False, "عملیات شکست خورد و هویت سازمان اطلاعاتی شما افشا گردید!", meta
                else:
                    # دفع ناشناس (Blocked Unattributed)
                    result_code = "blocked_unattributed"
                    meta["result"] = result_code
                    cur.execute("""
                        INSERT INTO intel_operations_history (attacker_id, target_id, op_type, result, details, created_at)
                        VALUES (?, ?, ?, ?, 'خنثی‌سازی بدون لو رفتن هویت', ?)
                    """, (attacker_id, target_id, op_type, result_code, now_str))
                    return False, "عملیات توسط فایروال و پدافند ضدجاسوسی حریف خنثی گردید، اما هویت شما ناشناس باقی ماند.", meta

    except Exception as e:
        return False, f"خطای دیتابیس: {e}", {}


def get_country_intel_history(country_id: int, limit: int = 10) -> list:
    """دریافت سوابق و تاریخچه عملیات‌های اطلاعاتی کشور."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT h.*, c.name as target_name, c.flag as target_flag
        FROM intel_operations_history h
        JOIN countries c ON h.target_id = c.id
        WHERE h.attacker_id = ?
        ORDER BY h.id DESC LIMIT ?
    """, (country_id, limit))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==================== 🛡️ ماژول‌های امنیت، بک‌آپ و رادار ضدتقلب ====================

def backup_database() -> tuple[bool, str]:
    """تهیه نسخه پشتیبان امن از دیتابیس SQLite با حفظ آخرین ۱۰ بک‌آپ."""
    try:
        backup_dir = os.path.join(os.path.dirname(os.path.abspath(config.DB_PATH)), "backups")
        os.makedirs(backup_dir, exist_ok=True)
        now_tag = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_filename = f"game_backup_{now_tag}.db"
        backup_filepath = os.path.join(backup_dir, backup_filename)

        src_conn = get_connection()
        dst_conn = sqlite3.connect(backup_filepath)
        with dst_conn:
            src_conn.backup(dst_conn)
        dst_conn.close()
        src_conn.close()

        # حذف بک‌آپ‌های قدیمی و نگه داشتن ۱۰ فایل اخیر
        all_backups = sorted(glob.glob(os.path.join(backup_dir, "game_backup_*.db")))
        if len(all_backups) > 10:
            for old_f in all_backups[:-10]:
                try:
                    os.remove(old_f)
                except Exception:
                    pass

        return True, backup_filepath
    except Exception as e:
        return False, str(e)


def get_suspicious_activities(limit: int = 20) -> list[dict]:
    """استخراج تراکنش‌ها و رویدادهای مشکوک برای رادار ضدتقلب ادمین."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.id, t.country_id, t.type, t.description, t.amount, t.created_at,
               c.name as country_name, c.flag as country_flag, c.player_id, c.username
        FROM transactions t
        LEFT JOIN countries c ON t.country_id = c.id
        WHERE (t.type IN ('aid', 'grant', 'direct_transfer') AND (t.amount >= 20000000 OR t.amount <= -20000000))
           OR (t.description LIKE '%مشکوک%' OR t.description LIKE '%هشدار%' OR t.description LIKE '%انتقال%')
        ORDER BY t.id DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ==================== پایش بیانیه‌ها و فعالیت روزانه ====================

def record_country_statement(country_id: int, player_id: int, statement_type: str = "statement", content: str = "") -> int:
    """ثبت بیانیه یا توییت رسمی با تاریخ روز (به وقت ایران) جهت پایش فعالیت روزانه."""
    conn = get_connection()
    cur = conn.cursor()
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    stmt_date = now_utc.astimezone(IRAN_TZ).date().isoformat()
    now_str = now_utc.isoformat()
    cur.execute(
        "INSERT INTO daily_statements (country_id, player_id, statement_type, content, created_at, statement_date) VALUES (?, ?, ?, ?, ?, ?)",
        (country_id, player_id, statement_type, content[:500] if content else "", now_str, stmt_date)
    )
    stmt_id = cur.lastrowid
    conn.commit()
    conn.close()
    return stmt_id


def get_country_statement_count_today(country_id: int) -> int:
    """دریافت تعداد بیانیه‌ها و توییت‌های ثبت‌شده امروز کشور به وقت ایران."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    stmt_date = now_utc.astimezone(IRAN_TZ).date().isoformat()
    return get_country_statement_count_for_date(country_id, stmt_date)


def get_country_statement_count_for_date(country_id: int, date_str: str) -> int:
    """دریافت تعداد بیانیه‌ها و توییت‌های ثبت‌شده کشور در یک تاریخ مشخص (YYYY-MM-DD)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) AS cnt FROM daily_statements WHERE country_id = ? AND statement_date = ?",
        (country_id, date_str)
    )
    row = cur.fetchone()
    count = row["cnt"] if row else 0
    conn.close()
    return count


def get_all_country_statement_counts_for_date(date_str: str) -> dict:
    """نگاشت شناسه کشور → تعداد بیانیه‌های ثبت‌شده در تاریخ مشخص."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT country_id, COUNT(*) AS cnt FROM daily_statements WHERE statement_date = ? GROUP BY country_id",
        (date_str,)
    )
    rows = cur.fetchall()
    counts = {r["country_id"]: r["cnt"] for r in rows}
    conn.close()
    return counts


# ==================== پرداخت‌های تومانی و سیستم VIP ====================

def create_payment_request(player_id: int, country_id: int, item_type: str, plan_title: str, amount_toman: int, receipt_photo_id: str = None, tracking_code: str = "", custom_payload: str = "") -> int:
    """ثبت درخواست و فیش پرداخت تومانی برای بررسی توسط مدیریت."""
    conn = get_connection()
    cur = conn.cursor()
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur.execute("""
        INSERT INTO payment_requests
        (player_id, country_id, item_type, plan_title, amount_toman, receipt_photo_id, tracking_code, custom_payload, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
    """, (player_id, country_id, item_type, plan_title, amount_toman, receipt_photo_id, tracking_code, custom_payload, now_str))
    req_id = cur.lastrowid
    conn.commit()
    conn.close()
    return req_id


def get_pending_payment_requests() -> list:
    """دریافت تمام فیش‌های پرداخت در انتظار تایید مدیریت."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.*, c.name as country_name, c.flag as country_flag, c.username as country_username
        FROM payment_requests p
        LEFT JOIN countries c ON p.country_id = c.id
        WHERE p.status = 'pending'
        ORDER BY p.id ASC
    """)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_payment_request_by_id(req_id: int):
    """دریافت اطلاعات یک فیش پرداخت بر اساس شناسه."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.*, c.name as country_name, c.flag as country_flag, c.username as country_username
        FROM payment_requests p
        LEFT JOIN countries c ON p.country_id = c.id
        WHERE p.id = ?
    """, (req_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def _create_custom_militia_with_cur(cur, player_id: int, name: str, flag: str = "🏴‍☠️", hq_desc: str = "", doctrine: str = "", faction_key: str = None, username: str = None) -> int:
    c_key = f"faction_{faction_key}" if faction_key and faction_key in getattr(config, "PREDEFINED_MILITIA_FACTIONS", {}) else f"faction_{player_id}"
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    cur.execute("""
        INSERT INTO countries
        (player_id, name, flag, population, treasury, tax_income, daily_income,
         gold, gold_daily, oil_reserves, oil_production, grain, electricity,
         active_personnel, reserve_personnel, last_income_date, created_at, country_key,
         approval_rating, grain_daily, username, tech_level, combat_readiness, microchips, microchips_daily, is_vip)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
    """, (
        player_id, name, flag or "🏴‍☠️",
        2_500_000,   # population
        25_000_000,  # treasury $25M
        300_000,     # tax_income
        2_800_000,   # daily_income $2.8M
        150,         # gold
        20,          # gold_daily
        500_000,     # oil_reserves 500k bbl
        20_000,      # oil_production
        12_000,      # grain 12k tons
        90,          # electricity 90%
        60_000,      # active_personnel 60k fighters
        80_000,      # reserve_personnel 80k fighters
        now_str,
        now_str,
        c_key,
        90,          # approval_rating 90%
        1_200,       # grain_daily
        username or "",
        1,           # tech_level
        85,          # combat_readiness 85%
        300,         # microchips
        10           # microchips_daily
    ))
    country_id = cur.lastrowid

    # ثبت تسلیحات و ادوات اختصاصی شبه‌نظامی (از کاتالوگ گروه آماده یا کاتالوگ پیش‌فرض)
    militia_cats = getattr(config, "MILITIA_EQUIPMENT_CATALOG", {})
    if faction_key and faction_key in militia_cats:
        catalog = militia_cats[faction_key]
    else:
        catalog = getattr(config, "DEFAULT_MILITIA_EQUIPMENT", config.DEFAULT_COUNTRY_EQUIPMENT)

    for item in catalog:
        producible_val = 1 if item.get("producible", True) else 0
        eq_key = item.get("key", f"item_{country_id}")
        cur.execute("""
            INSERT INTO country_assets
            (country_id, country_key, category, equipment_name, equipment_key, amount, buy_price, maintenance_cost, producible)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            country_id, c_key, item["category"], item["name"], eq_key,
            item["initial"], item["price"], item.get("maint", 0), producible_val
        ))

    # ایجاد فرماندهان کادر عملیاتی
    commanders = [
        ("leader", f"فرمانده کل {name}"),
        ("chief_of_staff", "رئیس ستاد عملیات و اطلاعات"),
        ("air_defense", "فرمانده یگان پدافند و راکتی"),
        ("logistics", "مسئول لجستیک و تسلیحات"),
        ("security", "فرمانده امنیت داخلی و ضداطلاعات"),
    ]
    for c_key_cmd, c_title in commanders:
        cur.execute("""
            INSERT OR IGNORE INTO country_commanders (country_id, key, title, status)
            VALUES (?, ?, ?, 'active')
        """, (country_id, c_key_cmd, c_title))

    return country_id


def create_custom_militia_faction(player_id: int, name: str, flag: str = "🏴‍☠️", hq_desc: str = "", doctrine: str = "", faction_key: str = None, username: str = None) -> int:
    """ایجاد گروه / سازمان شبه‌نظامی غیردولتی اختصاصی برای بازیکن (به صورت مستقل یا بازوی نیابتی کشورش)."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM countries WHERE player_id = ? AND country_key LIKE 'faction_%'", (player_id,))
            old_militia = cur.fetchone()
            if old_militia:
                delete_country_by_id(old_militia["id"])

            country_id = _create_custom_militia_with_cur(cur, player_id, name, flag, hq_desc, doctrine, faction_key, username)
        return country_id
    finally:
        conn.close()


def get_taken_militia_faction_keys() -> set:
    """دریافت کلید تمام گروه‌های غیردولتی که قبلاً توسط بازیکنان انتخاب شده‌اند."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT country_key FROM countries WHERE country_key LIKE 'faction_%'")
    rows = cur.fetchall()
    conn.close()
    taken = set()
    for r in rows:
        k = r["country_key"].replace("faction_", "")
        taken.add(k)
    return taken


def _apply_purchase_with_cur(cur, item_type: str, c_id, player_id: int, p: dict,
                             now_dt, now_str: str, override_name: str = None,
                             bypass_limits: bool = False) -> tuple[bool, str]:
    """اعمال اثر یک آیتم خریدنی روی کشور/بازیکن، با کرسر باز.

    منطق مشترک بین تایید فیش پرداخت (approve_payment_request) و اعطای دستی توسط
    ادمین از منوی «پرونده مالی» (admin_grant_item). خروجی: (ok, error_message).
    دیکشنری p در صورت نیاز به‌روزرسانی می‌شود (granted_pack، created_country_id و ...).
    """
    if item_type.startswith("vip_") or item_type in ("vip_1month", "vip_3month"):
        tier = "gold" if item_type == "vip_3month" else (item_type.replace("vip_", "") if item_type.startswith("vip_") else "silver")
        if tier not in ("bronze", "silver", "gold", "diamond"):
            tier = "silver"
        days = 90 if item_type == "vip_3month" else 30
        exp_dt = now_dt + datetime.timedelta(days=days)
        if c_id:
            cur.execute(
                "UPDATE countries SET is_vip = 1, vip_tier = ?, vip_expires_at = ? WHERE id = ?",
                (tier, exp_dt.isoformat(), c_id)
            )
    elif item_type in ("battle_pass", "vip_battlepass", "pass"):
        if c_id:
            cur.execute("""
                INSERT INTO battle_pass (country_id, season, is_premium, current_xp, current_tier, created_at, updated_at)
                VALUES (?, 1, 1, 500, 1, ?, ?)
                ON CONFLICT(country_id) DO UPDATE SET
                is_premium = 1,
                updated_at = excluded.updated_at
            """, (c_id, now_str, now_str))
    # ===== بسته‌های بقا و لجستیک (مصرفی - چند بار خرید) =====
    elif item_type.startswith("survival_"):
        if not c_id:
            return False, "کشور یافت نشد."
        # سقف روزانه ۳ بسته برای جلوگیری از اسپم وال‌ها
        # (اعطای مستقیم ادمین با bypass_limits از این سقف مستثناست)
        if not bypass_limits:
            try:
                today_str = now_dt.date().isoformat()
                cur.execute("SELECT COUNT(*) as cnt FROM transactions WHERE country_id = ? AND type = 'survival_pack' AND created_at LIKE ?", (c_id, f"{today_str}%"))
                cnt_row = cur.fetchone()
                if cnt_row and (cnt_row["cnt"] or 0) >= 3:
                    return False, "⛔ سقف روزانه ۳ بسته بقا پر شده. فردا می‌تونی دوباره بخری."
            except Exception:
                pass
        # مقادیر بسته‌ها
        packs = {
            "survival_small": {"treasury": 3_000_000, "oil": 400_000, "grain": 15_000, "iron": 0, "chips": 0, "desc": "بسته بقا کوچک"},
            "survival_medium": {"treasury": 6_000_000, "oil": 900_000, "grain": 30_000, "iron": 8_000, "chips": 300, "desc": "بسته بقا متوسط"},
            "survival_large": {"treasury": 10_000_000, "oil": 1_800_000, "grain": 60_000, "iron": 15_000, "chips": 800, "desc": "بسته بقا بزرگ"},
            "survival_ultra": {"treasury": 18_000_000, "oil": 3_000_000, "grain": 100_000, "iron": 30_000, "chips": 1_500, "gold": 50, "desc": "بسته بقا فوق‌سنگین"},
        }
        pack = packs.get(item_type)
        if not pack:
            return False, "بسته نامعتبر."
        cur.execute("UPDATE countries SET treasury = treasury + ?, oil_reserves = oil_reserves + ?, grain = grain + ?, iron_ore = iron_ore + ?, microchips = microchips + ?, gold = gold + ? WHERE id = ?",
            (pack.get("treasury",0), pack.get("oil",0), pack.get("grain",0), pack.get("iron",0), pack.get("chips",0), pack.get("gold",0), c_id))
        cur.execute("INSERT INTO transactions (country_id, type, description, amount, created_at) VALUES (?, 'survival_pack', ?, ?, ?)",
            (c_id, f"🎁 {pack['desc']} - {pack.get('oil',0):,} نفت + {pack.get('grain',0):,} غلات", pack.get("treasury",0), now_str))
        p["granted_pack"] = pack
    elif item_type.startswith("ticket_"):
        if not c_id:
            return False, "کشور یافت نشد."
        tickets = {
            "ticket_drill": {"drill": 1, "desc": "بلیط مانور اضافه"},
            "ticket_drill_3": {"drill": 3, "desc": "پک ۳ تایی مانور"},
            "ticket_statement": {"statement": 1, "desc": "بلیط بیانیه اضافه"},
            "ticket_statement_5": {"statement": 5, "desc": "پک ۵ تایی بیانیه"},
            "ticket_contract_3d": {"contract_3d": 1, "desc": "بوست اسلات قرارداد ۳ روزه"},
            "ticket_contract_7d": {"contract_7d": 1, "desc": "بوست اسلات قرارداد ۷ روزه"},
        }
        t = tickets.get(item_type)
        if not t:
            return False, "بلیط نامعتبر."
        if "drill" in t:
            cur.execute("UPDATE countries SET drill_tickets = COALESCE(drill_tickets,0) + ? WHERE id = ?", (t["drill"], c_id))
        if "statement" in t:
            cur.execute("UPDATE countries SET statement_tickets = COALESCE(statement_tickets,0) + ? WHERE id = ?", (t["statement"], c_id))
        if "contract_3d" in t or "contract_7d" in t:
            days = 3 if "3d" in item_type else 7
            until = now_dt + datetime.timedelta(days=days)
            cur.execute("UPDATE countries SET contract_boost_until = ? WHERE id = ?", (until.isoformat(), c_id))
        cur.execute("INSERT INTO transactions (country_id, type, description, amount, created_at) VALUES (?, 'ticket', ?, 0, ?)",
            (c_id, f"🎫 {t['desc']}", now_str))
    elif item_type.startswith("bp_booster_"):
        if not c_id:
            return False, "کشور یافت نشد."
        boosters = {
            "bp_booster_3d": {"days": 3, "mult": 2.0, "desc": "بوستر بتل‌پس ۳ روزه ۲x"},
            "bp_booster_7d": {"days": 7, "mult": 2.0, "desc": "بوستر بتل‌پس ۷ روزه ۲x"},
            "bp_booster_30d": {"days": 30, "mult": 2.0, "desc": "بوستر بتل‌پس ماهانه ۲x"},
        }
        b = boosters.get(item_type)
        if not b:
            return False, "بوستر نامعتبر."
        until = now_dt + datetime.timedelta(days=b["days"])
        cur.execute("UPDATE countries SET bp_booster_until = ?, bp_booster_mult = ? WHERE id = ?", (until.isoformat(), b["mult"], c_id))
        cur.execute("INSERT INTO transactions (country_id, type, description, amount, created_at) VALUES (?, 'bp_booster', ?, 0, ?)",
            (c_id, f"⭐️ {b['desc']}", now_str))
    elif item_type.startswith("cosmetic_") or item_type.startswith("title_") or item_type.startswith("frame_") or item_type.startswith("golden_") or item_type.startswith("pin_") or item_type in ("rename_country", "flag_change"):
        if not c_id:
            return False, "کشور یافت نشد."
        # خدمات دیده شدن
        if item_type.startswith("title_"):
            # title_7d, title_30d
            days = 30 if "30d" in item_type else 7
            # custom_payload حاوی عنوان است
            try:
                payload = json.loads(p.get("custom_payload") or "{}")
                title_text = payload.get("custom_title") or payload.get("title") or "عنوان تشریفاتی"
            except Exception:
                title_text = "عنوان تشریفاتی"
            until = now_dt + datetime.timedelta(days=days)
            cur.execute("UPDATE countries SET custom_title = ?, title_expires_at = ? WHERE id = ?", (title_text[:50], until.isoformat(), c_id))
        elif item_type.startswith("frame_"):
            days = 30 if "30d" in item_type else 7
            until = now_dt + datetime.timedelta(days=days)
            cur.execute("UPDATE countries SET golden_frame_until = ? WHERE id = ?", (until.isoformat(), c_id))
        elif item_type.startswith("golden_stmt"):
            # golden_stmt_1, golden_stmt_3, golden_stmt_10
            qty = 1
            if "_3" in item_type:
                qty = 3
            elif "_10" in item_type:
                qty = 10
            cur.execute("UPDATE countries SET golden_stmt_credits = COALESCE(golden_stmt_credits,0) + ? WHERE id = ?", (qty, c_id))
        elif item_type.startswith("pin_"):
            qty = 1
            if "_3" in item_type:
                qty = 3
            cur.execute("UPDATE countries SET pin_credits = COALESCE(pin_credits,0) + ? WHERE id = ?", (qty, c_id))
        # تغییر نام و پرچم حذف شد - غیر واقعی (درخواست‌های قدیمی نادیده گرفته میشن)
        cur.execute("INSERT INTO transactions (country_id, type, description, amount, created_at) VALUES (?, 'cosmetic', ?, 0, ?)",
            (c_id, f"🎨 {item_type} - خدمات دیده شدن", now_str))
    elif item_type == "militia":
        payload_str = p.get("custom_payload") or "{}"
        try:
            payload = json.loads(payload_str)
        except Exception:
            payload = {}
        f_name = override_name or payload.get("name") or "گروه مقاومت اختصاصی"
        f_flag = payload.get("flag") or "🏴‍☠️"
        f_hq = payload.get("hq") or ""
        f_doc = payload.get("doctrine") or ""
        f_key = payload.get("faction_key")
        
        # اگر قبلاً گروه شبه‌نظامی داشت، گروه قبلی را پاک کن تا کشور اصلی حفظ شود
        cur.execute("SELECT id FROM countries WHERE player_id = ? AND country_key LIKE 'faction_%'", (player_id,))
        old_m = cur.fetchone()
        if old_m:
            delete_country_by_id(old_m["id"])

        c_id = _create_custom_militia_with_cur(cur, player_id, f_name, f_flag, f_hq, f_doc, f_key)
        p["created_country_id"] = c_id
        p["final_faction_name"] = f_name
    return True, ""


def admin_grant_item(country_id: int, item_type: str, admin_id: int, custom_payload: dict = None,
                     override_name: str = None, bypass_limits: bool = True) -> tuple[bool, str]:
    """اعطای مستقیم یک آیتم فروشگاهی به کشور توسط ادمین (بدون فیش پرداخت).

    از همان منطق تایید فیش استفاده می‌کند تا رفتار دو مسیر همیشه یکسان بماند، و یک
    رکورد با مبلغ صفر در payment_requests ثبت می‌شود تا در تاریخچه مالی قابل ردیابی باشد.
    """
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id, player_id FROM countries WHERE id = ?", (country_id,))
            crow = cur.fetchone()
            if not crow:
                return False, "کشور یافت نشد."
            player_id = crow["player_id"]

            now_dt = datetime.datetime.now(datetime.timezone.utc)
            now_str = now_dt.isoformat()
            payload_json = json.dumps(custom_payload or {}, ensure_ascii=False)
            # عنوان خوانا برای نمایش در سوابق مالی
            try:
                from handlers.vip import PLANS_METADATA
                plan_title = PLANS_METADATA.get(item_type, {}).get("title") or item_type
            except Exception:
                plan_title = item_type
            p = {"custom_payload": payload_json, "player_id": player_id, "country_id": country_id}

            ok, err = _apply_purchase_with_cur(cur, item_type, country_id, player_id, p,
                                               now_dt, now_str, override_name=override_name,
                                               bypass_limits=bypass_limits)
            if not ok:
                return False, err

            cur.execute("""
                INSERT INTO payment_requests
                (player_id, country_id, item_type, plan_title, amount_toman, tracking_code,
                 custom_payload, status, created_at, reviewed_at, admin_id)
                VALUES (?, ?, ?, ?, 0, ?, ?, 'approved', ?, ?, ?)
            """, (player_id, country_id, item_type, f"🎁 اعطای ادمین — {plan_title}",
                  "ADMIN_GRANT", payload_json, now_str, now_str, admin_id))
            return True, "آیتم با موفقیت برای کشور فعال شد."
    except Exception as e:
        return False, f"خطا در اعطای آیتم: {e}"


def approve_payment_request(req_id: int, admin_id: int, override_name: str = None) -> tuple[bool, str, dict]:
    """تایید رسمی فیش پرداخت و فعال‌سازی اشتراک VIP یا ایجاد گروه غیردولتی با نام نهایی."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM payment_requests WHERE id = ?", (req_id,))
            row = cur.fetchone()
            if not row:
                return False, "درخواست پرداخت یافت نشد.", {}

            p = dict(row)
            if p["status"] != "pending":
                return False, f"این درخواست قبلاً تعیین تکلیف شده است (وضعیت: {p['status']}).", p

            now_dt = datetime.datetime.now(datetime.timezone.utc)
            now_str = now_dt.isoformat()

            item_type = p["item_type"]
            c_id = p.get("country_id")
            player_id = p["player_id"]

            ok_apply, err_apply = _apply_purchase_with_cur(
                cur, item_type, c_id, player_id, p, now_dt, now_str, override_name=override_name
            )
            if not ok_apply:
                return False, err_apply, p
            c_id = p.get("created_country_id", c_id)

            cur.execute("""
                UPDATE payment_requests
                SET status = 'approved', reviewed_at = ?, admin_id = ?
                WHERE id = ?
            """, (now_str, admin_id, req_id))

            p["status"] = "approved"
            return True, "پرداخت با موفقیت تایید و گروه/خدمت برای کاربر فعال گردید.", p
    except Exception as e:
        return False, f"خطا در تایید پرداخت: {e}", {}


def reject_payment_request(req_id: int, admin_id: int, reason: str = "") -> tuple[bool, str, dict]:
    """رد فیش پرداخت به دلیل نامعتبر بودن یا عدم واریز."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM payment_requests WHERE id = ?", (req_id,))
            row = cur.fetchone()
            if not row:
                return False, "درخواست پرداخت یافت نشد.", {}

            p = dict(row)
            if p["status"] != "pending":
                return False, f"این درخواست قبلاً تعیین تکلیف شده است (وضعیت: {p['status']}).", p

            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute("""
                UPDATE payment_requests
                SET status = 'rejected', reviewed_at = ?, admin_id = ?, admin_note = ?
                WHERE id = ?
            """, (now_str, admin_id, reason or "عدم واریز وجه یا فیش نامعتبر", req_id))

            p["status"] = "rejected"
            p["admin_note"] = reason or "عدم واریز وجه یا فیش نامعتبر"
            return True, "درخواست پرداخت رد شد.", p
    except Exception as e:
        return False, f"خطا در رد پرداخت: {e}", {}


# ==================== توابع پرونده جامع و دسترسی همه‌جانبه ادمین به کشورها ====================

def get_country_all_trade_contracts(country_id: int, limit: int = 50) -> list:
    """دریافت کلیه قراردادهای تجاری (معلق، انجام‌شده، لغو‌شده) مربوط به یک کشور به همراه مشخصات کامل طرفین."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.*,
               cp.name as proposer_name, cp.flag as proposer_flag, cp.country_key as proposer_key,
               cr.name as recipient_name, cr.flag as recipient_flag, cr.country_key as recipient_key
        FROM trade_contracts t
        LEFT JOIN countries cp ON t.proposer_id = cp.id
        LEFT JOIN countries cr ON t.recipient_id = cr.id
        WHERE t.proposer_id = ? OR t.recipient_id = ?
        ORDER BY t.id DESC
        LIMIT ?
    """, (country_id, country_id, limit))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def admin_cancel_trade_contract(contract_id: int) -> tuple[bool, str]:
    """ابطال قرارداد تجاری توسط ادمین."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM trade_contracts WHERE id = ?", (contract_id,))
            row = cur.fetchone()
            if not row:
                return False, "قرارداد مورد نظر یافت نشد."
            cur.execute("UPDATE trade_contracts SET status = 'canceled' WHERE id = ?", (contract_id,))
        return True, f"قرارداد تجاری #{contract_id} با موفقیت توسط ادمین ابطال شد."
    except Exception as e:
        return False, f"خطا در ابطال قرارداد: {e}"


def admin_delete_trade_contract(contract_id: int) -> tuple[bool, str]:
    """حذف کامل رکورد قرارداد تجاری از سیستم توسط ادمین."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM trade_contracts WHERE id = ?", (contract_id,))
        return True, f"قرارداد #{contract_id} با موفقیت از دیتابیس حذف گردید."
    except Exception as e:
        return False, f"خطا در حذف قرارداد: {e}"


def admin_cancel_market_order(order_id: int) -> tuple[bool, str]:
    """لغو سفارش بورس کالا توسط ادمین و عودت اقلام به انبار کشور فروشنده."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM market_orders WHERE id = ?", (order_id,))
            order = cur.fetchone()
            if not order:
                return False, "سفارش بورس یافت نشد."

            ord_dict = dict(order)
            seller_id = ord_dict["seller_id"]
            rem_amount = ord_dict["amount"]
            res_type = ord_dict["resource_type"]

            resource_cols = {
                "oil": "oil_reserves",
                "gold": "gold",
                "grain": "grain",
                "microchips": "microchips",
                "uranium_ore": "uranium_ore",
                "nuclear_fuel": "nuclear_fuel"
            }
            col = resource_cols.get(res_type)

            if col and rem_amount > 0 and seller_id:
                cur.execute(f"UPDATE countries SET {col} = {col} + ? WHERE id = ?", (rem_amount, seller_id))

            cur.execute("DELETE FROM market_orders WHERE id = ?", (order_id,))
        return True, "سفارش بورس با موفقیت لغو و اقلام به انبار کشور بازگردانده شد."
    except Exception as e:
        return False, f"خطا در لغو سفارش بورس: {e}"


def get_country_diplomatic_relations_all(country_id: int) -> list:
    """دریافت کلیه وضعیت‌ها و روابط دیپلماتیک ثبت‌شده یک کشور با سایر کشورها."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT d.*,
               c1.name as c1_name, c1.flag as c1_flag, c1.country_key as c1_key,
               c2.name as c2_name, c2.flag as c2_flag, c2.country_key as c2_key
        FROM diplomatic_relations d
        JOIN countries c1 ON d.country1_id = c1.id
        JOIN countries c2 ON d.country2_id = c2.id
        WHERE d.country1_id = ? OR d.country2_id = ?
        ORDER BY d.id DESC
    """, (country_id, country_id))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def admin_set_country_vip(country_id: int, tier: str, days: int = 30) -> tuple[bool, str]:
    """تنظیم مستقیم سطح VIP و تاریخ انقضا برای یک کشور توسط ادمین."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM countries WHERE id = ?", (country_id,))
            c = cur.fetchone()
            if not c:
                return False, "کشور مورد نظر یافت نشد."
            now = datetime.datetime.now(datetime.timezone.utc)
            expires_at = (now + datetime.timedelta(days=days)).isoformat()
            tier_clean = tier.replace("vip_", "")
            cur.execute("UPDATE countries SET is_vip = 1, vip_tier = ?, vip_expires_at = ? WHERE id = ?", (tier_clean, expires_at, country_id))
        return True, f"اشتراک {tier} با موفقیت به مدت {days} روز فعال گردید."
    except Exception as e:
        return False, f"خطا در فعال‌سازی اشتراک: {e}"


def admin_revoke_country_vip(country_id: int) -> tuple[bool, str]:
    """لغو اشتراک VIP کشور توسط ادمین."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("UPDATE countries SET is_vip = 0, vip_tier = NULL, vip_expires_at = NULL WHERE id = ?", (country_id,))
        return True, "اشتراک VIP کشور با موفقیت لغو شد."
    except Exception as e:
        return False, f"خطا: {e}"


def admin_transfer_country_ownership(country_id: int, new_player_id: int, new_username: str = "") -> tuple[bool, str]:
    """واگذاری و انتقال کامل مالکیت یک کشور به بازیکن جدید."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name, flag FROM countries WHERE player_id = ? AND id != ?", (new_player_id, country_id))
            existing = cur.fetchone()
            if existing:
                return False, f"این بازیکن در حال حاضر رهبر کشور {existing['flag']} {existing['name']} (شناسه {existing['id']}) است."
            cur.execute("UPDATE countries SET player_id = ?, username = ? WHERE id = ?", (new_player_id, new_username or "", country_id))
        return True, f"مالکیت کشور با موفقیت به بازیکن با شناسه `{new_player_id}` واگذار شد."
    except Exception as e:
        return False, f"خطا در انتقال مالکیت: {e}"


def admin_rename_country(country_id: int, new_name: str, new_flag: str = None) -> tuple[bool, str]:
    """تغییر نام و پرچم کشور توسط ادمین."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            if new_flag:
                cur.execute("UPDATE countries SET name = ?, flag = ? WHERE id = ?", (new_name, new_flag, country_id))
            else:
                cur.execute("UPDATE countries SET name = ? WHERE id = ?", (new_name, country_id))
        return True, f"مشخصات کشور به {new_flag or ''} {new_name} تغییر یافت."
    except Exception as e:
        return False, f"خطا در تغییر نام: {e}"


def get_country_statements_history(country_id: int, limit: int = 20) -> list:
    """دریافت تاریخچه بیانیه‌ها و توییت‌های ثبت‌شده توسط یک کشور."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM daily_statements WHERE country_id = ? ORDER BY id DESC LIMIT ?", (country_id, limit))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def admin_force_add_statement(country_id: int, player_id: int, content: str = "بیانیه رسمی ثبت‌شده توسط مدیریت ستاد") -> tuple[bool, str]:
    """ثبت دستی یک بیانیه رسمی برای کشور جهت تکمیل حدنصاب روزانه."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            now = datetime.datetime.now(IRAN_TZ)
            today_str = now.strftime("%Y-%m-%d")
            now_iso = now.isoformat()
            cur.execute("""
                INSERT INTO daily_statements (country_id, player_id, statement_type, content, statement_date, created_at)
                VALUES (?, ?, 'statement', ?, ?, ?)
            """, (country_id, player_id, content, today_str, now_iso))
        return True, "بیانیه رسمی با موفقیت ثبت گردید و حدنصاب فعالیت روزانه افزایش یافت."
    except Exception as e:
        return False, f"خطا: {e}"


def admin_clear_cyber_disruptions(country_id: int) -> tuple[bool, str]:
    """پاکسازی و لغو کلیه اختلالات و خاموشی‌های سایبری اعمال‌شده روی کشور."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE countries
                SET air_defense_disrupted_until = NULL,
                    blackout_until = NULL,
                    r_and_d_frozen_until = NULL,
                    command_disrupted_until = NULL
                WHERE id = ?
            """, (country_id,))
        return True, "تمامی اختلالات و خاموشی‌های سایبری کشور پاکسازی گردید."
    except Exception as e:
        return False, f"خطا: {e}"


def get_country_payment_history(country_id: int, limit: int = 20) -> list:
    """دریافت سوابق فیش‌ها و خریدهای تومانی بازیکن این کشور."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM payment_requests WHERE country_id = ? ORDER BY id DESC LIMIT ?", (country_id, limit))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def admin_add_commander(country_id: int, key: str, title: str) -> tuple[bool, str]:
    """افزودن یا انتصاب فرمانده جدید برای کشور توسط ادمین."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("INSERT OR REPLACE INTO country_commanders (country_id, key, title, status) VALUES (?, ?, ?, 'active')", (country_id, key, title))
        return True, f"فرمانده «{title}» با موفقیت منصوب و فعال گردید."
    except Exception as e:
        return False, f"خطا: {e}"


def admin_delete_commander(country_id: int, commander_key: str) -> tuple[bool, str]:
    """حذف رکورد فرمانده از کشور توسط ادمین."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM country_commanders WHERE country_id = ? AND key = ?", (country_id, commander_key))
        return True, f"فرمانده با شناسه {commander_key} حذف گردید."
    except Exception as e:
        return False, f"خطا: {e}"


# ==================== سیستم بتل‌پس فصلی و کمپین‌های استراتژیک (Battle Pass) ====================

def get_or_create_battle_pass(country_id: int) -> dict:
    """دریافت یا ساخت وضعیت بتل‌پس فصلی برای یک کشور."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM battle_pass WHERE country_id = ?", (country_id,))
    row = cur.fetchone()
    if row:
        d = dict(row)
        conn.close()
        d["claimed_free_tiers"] = json.loads(d.get("claimed_free_tiers") or "[]")
        d["claimed_premium_tiers"] = json.loads(d.get("claimed_premium_tiers") or "[]")
        d["completed_challenges"] = json.loads(d.get("completed_challenges") or "[]")
        d["challenge_progress"] = json.loads(d.get("challenge_progress") or "{}")
        return d

    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur.execute("""
        INSERT INTO battle_pass
        (country_id, season, is_premium, current_xp, current_tier, claimed_free_tiers, claimed_premium_tiers, completed_challenges, challenge_progress, created_at, updated_at)
        VALUES (?, ?, 0, 0, 1, '[]', '[]', '[]', '{}', ?, ?)
    """, (country_id, getattr(config, "BATTLE_PASS_SEASON", 1), now_str, now_str))
    conn.commit()
    conn.close()
    return {
        "country_id": country_id,
        "season": getattr(config, "BATTLE_PASS_SEASON", 1),
        "is_premium": 0,
        "current_xp": 0,
        "current_tier": 1,
        "claimed_free_tiers": [],
        "claimed_premium_tiers": [],
        "completed_challenges": [],
        "challenge_progress": {},
        "created_at": now_str,
        "updated_at": now_str
    }


def add_battle_pass_xp(country_id: int, xp_amount: int) -> tuple[int, int, bool]:
    """افزودن XP به بتل‌پس کشور، محاسبه لول‌آپ و ارتقای پله‌ها."""
    bp = get_or_create_battle_pass(country_id)
    multiplier = 1.25 if bp.get("is_premium") else 1.0
    # بوستر بتل‌پس مصرفی ۲x
    try:
        c = get_country_by_id(country_id)
        if c:
            booster_until = c.get("bp_booster_until")
            booster_mult = c.get("bp_booster_mult", 1.0) or 1.0
            if booster_until:
                bu_dt = datetime.datetime.fromisoformat(booster_until)
                now_dt = datetime.datetime.now(datetime.timezone.utc)
                if bu_dt > now_dt and booster_mult > 1.0:
                    multiplier *= float(booster_mult)
    except Exception:
        pass
    effective_xp = int(xp_amount * multiplier)

    new_xp = bp["current_xp"] + effective_xp
    xp_per_tier = getattr(config, "BATTLE_PASS_XP_PER_TIER", 1000)
    new_tier = min(20, 1 + (new_xp // xp_per_tier))
    old_tier = bp["current_tier"]
    tier_up = new_tier > old_tier

    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = get_connection()
    with conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE battle_pass
            SET current_xp = ?, current_tier = ?, updated_at = ?
            WHERE country_id = ?
        """, (new_xp, new_tier, now_str, country_id))

    return new_xp, new_tier, tier_up


def unlock_premium_battle_pass(country_id: int) -> tuple[bool, str]:
    """فعال‌سازی ردیف پرمیوم بتل‌پس برای یک کشور."""
    bp = get_or_create_battle_pass(country_id)
    if bp.get("is_premium"):
        return True, "بتل‌پس پرمیوم قبلاً برای این کشور فعال بوده است."

    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = get_connection()
    with conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE battle_pass
            SET is_premium = 1, current_xp = current_xp + 500, updated_at = ?
            WHERE country_id = ?
        """, (now_str, country_id))
    add_transaction(country_id, "battle_pass", "فعال‌سازی بتل‌پس پرمیوم فصل ۱ (Season 1 Pass)", 0)
    return True, "⭐️ بتل‌پس پرمیوم با موفقیت فعال شد! دسترسی به تمام ۲۰ ردیف جوایز پرمیوم باز گردید."


def _grant_bp_reward_dict(cur, country_id: int, r_dict: dict):
    """اعطای منابع اقتصادی یک پله بتل‌پس (خزانه، نفت، طلا، غلات، میکروچیپ، اورانیوم)."""
    if not r_dict:
        return
    if "treasury" in r_dict:
        cur.execute("UPDATE countries SET treasury = treasury + ? WHERE id = ?", (r_dict["treasury"], country_id))
    if "oil" in r_dict:
        cur.execute("UPDATE countries SET oil_reserves = oil_reserves + ? WHERE id = ?", (r_dict["oil"], country_id))
    if "gold" in r_dict:
        cur.execute("UPDATE countries SET gold = gold + ? WHERE id = ?", (r_dict["gold"], country_id))
    if "grain" in r_dict:
        cur.execute("UPDATE countries SET grain = grain + ? WHERE id = ?", (r_dict["grain"], country_id))
    if "microchips" in r_dict:
        cur.execute("UPDATE countries SET microchips = microchips + ? WHERE id = ?", (r_dict["microchips"], country_id))
    if "uranium_ore" in r_dict:
        cur.execute("UPDATE countries SET uranium_ore = uranium_ore + ? WHERE id = ?", (r_dict["uranium_ore"], country_id))
    if "nuclear_fuel" in r_dict:
        cur.execute("UPDATE countries SET nuclear_fuel = nuclear_fuel + ? WHERE id = ?", (r_dict["nuclear_fuel"], country_id))


def claim_all_unlocked_battle_pass_rewards(country_id: int) -> tuple[bool, str, dict]:
    """دریافت یکجای تمامی پاداش‌های باز شده (رایگان + پرمیوم) تا پله فعلی."""
    bp = get_or_create_battle_pass(country_id)
    curr_tier = bp["current_tier"]
    is_premium = bp["is_premium"]

    claimed_free = set(bp["claimed_free_tiers"])
    claimed_prem = set(bp["claimed_premium_tiers"])

    tiers_config = getattr(config, "BATTLE_PASS_TIERS", {})
    new_free_claimed = []
    new_prem_claimed = []
    claimed_items_summary = []

    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            for t_num in range(1, curr_tier + 1):
                t_info = tiers_config.get(t_num)
                if not t_info:
                    continue

                # ردیف رایگان
                if t_num not in claimed_free:
                    free_r = t_info.get("free", {})
                    _grant_bp_reward_dict(cur, country_id, free_r)
                    claimed_free.add(t_num)
                    new_free_claimed.append(t_num)
                    claimed_items_summary.append(f"• پله {t_num} (رایگان): {free_r.get('desc','')}")

                # ردیف پرمیوم
                if is_premium and (t_num not in claimed_prem):
                    prem_r = t_info.get("premium", {})
                    _grant_bp_reward_dict(cur, country_id, prem_r)
                    claimed_prem.add(t_num)
                    new_prem_claimed.append(t_num)
                    claimed_items_summary.append(f"• پله {t_num} (👑 پرمیوم): {prem_r.get('desc','')}")

            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute("""
                UPDATE battle_pass
                SET claimed_free_tiers = ?, claimed_premium_tiers = ?, updated_at = ?
                WHERE country_id = ?
            """, (json.dumps(sorted(list(claimed_free))), json.dumps(sorted(list(claimed_prem))), now_str, country_id))

        if not new_free_claimed and not new_prem_claimed:
            return False, "شما قبلاً تمام پاداش‌های در دسترس پله‌های فعلی را دریافت نموده‌اید. برای باز کردن پله‌های بعدی، با فعالیت در بازی XP کسب کنید!", {}

        total_claimed = len(new_free_claimed) + len(new_prem_claimed)
        summary_text = (
            f"🎉 <b>دریافت موفق جوایز بتل‌پس ({total_claimed} پاداش):</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            + "\n".join(claimed_items_summary[:8]) +
            (f"\n... و {len(claimed_items_summary)-8} جایزه دیگر" if len(claimed_items_summary) > 8 else "") +
            "\n\n✅ تمام وجوه، نفت، طلا و ادوات تسلیحاتی به انبار و خزانه کشورتان اضافه شد."
        )
        return True, summary_text, {"free_count": len(new_free_claimed), "premium_count": len(new_prem_claimed)}
    except Exception as e:
        return False, f"خطا در دریافت جوایز بتل‌پس: {e}", {}


def progress_battle_pass_challenge(country_id: int, action_type: str, qty: int = 1) -> tuple[bool, int, str]:
    """بررسی و ارتقای پیشرفت چالش‌های هفتگی کسب XP بتل‌پس."""
    bp = get_or_create_battle_pass(country_id)
    completed = set(bp.get("completed_challenges", []))
    prog_map = bp.get("challenge_progress", {})

    challenges = getattr(config, "BATTLE_PASS_CHALLENGES", {})
    xp_gained = 0
    completed_titles = []

    for c_key, c_info in challenges.items():
        if c_info.get("action") == action_type and c_key not in completed:
            current_val = prog_map.get(c_key, 0) + qty
            prog_map[c_key] = current_val
            target = c_info.get("target", 1)
            if current_val >= target:
                completed.add(c_key)
                xp_val = c_info.get("xp", 400)
                xp_gained += xp_val
                completed_titles.append(c_info.get("title", c_key))

    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = get_connection()
    with conn:
        cur = conn.cursor()
        cur.execute("""
            UPDATE battle_pass
            SET completed_challenges = ?, challenge_progress = ?, updated_at = ?
            WHERE country_id = ?
        """, (json.dumps(sorted(list(completed))), json.dumps(prog_map), now_str, country_id))

    if xp_gained > 0:
        add_battle_pass_xp(country_id, xp_gained)
        return True, xp_gained, ", ".join(completed_titles)

    return False, 0, ""


def sync_and_check_all_challenges(country_id: int) -> tuple[int, list[str]]:
    """همگام‌سازی و بررسی هوشمند وضعیت واقعی کشور با تمام تسک‌های بتل‌پس."""
    c = get_country_by_id(country_id)
    if not c:
        return 0, []

    bp = get_or_create_battle_pass(country_id)
    completed = set(bp.get("completed_challenges", []))
    prog_map = bp.get("challenge_progress", {})

    total_xp_gained = 0
    newly_completed = []
    challenges = getattr(config, "BATTLE_PASS_CHALLENGES", {})

    # ۱. بررسی آمادگی رزمی ( بالای ۸۵٪ )
    readiness = c.get("combat_readiness", 70) or 0
    if "c_drill_90" not in completed:
        prog_map["c_drill_90"] = 1 if readiness >= 85 else 0
        if readiness >= 85:
            completed.add("c_drill_90")
            xp_val = challenges.get("c_drill_90", {}).get("xp", 400)
            total_xp_gained += xp_val
            newly_completed.append(challenges.get("c_drill_90", {}).get("title", "⚔️ رژه اقتدار"))

    # ۲. بررسی بیانیه‌های ثبت‌شده امروز (حداقل ۳ بیانیه)
    stmt_cnt = get_country_statement_count_today(country_id)
    if "c_stmt_3" not in completed:
        prog_map["c_stmt_3"] = max(prog_map.get("c_stmt_3", 0), stmt_cnt)
        if stmt_cnt >= 3:
            completed.add("c_stmt_3")
            xp_val = challenges.get("c_stmt_3", {}).get("xp", 400)
            total_xp_gained += xp_val
            newly_completed.append(challenges.get("c_stmt_3", {}).get("title", "📢 صدای حاکمیت"))

    # ۳. بررسی احداث زیرساخت‌ها و کارخانجات در فروشگاه
    eq = get_equipment(country_id)
    if "c_shop_1" not in completed and len(eq) > 0:
        completed.add("c_shop_1")
        prog_map["c_shop_1"] = 1
        xp_val = challenges.get("c_shop_1", {}).get("xp", 500)
        total_xp_gained += xp_val
        newly_completed.append(challenges.get("c_shop_1", {}).get("title", "🏗️ توسعه صنعتی"))

    if total_xp_gained > 0:
        now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
        conn = get_connection()
        with conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE battle_pass
                SET completed_challenges = ?, challenge_progress = ?, updated_at = ?
                WHERE country_id = ?
            """, (json.dumps(sorted(list(completed))), json.dumps(prog_map), now_str, country_id))
        add_battle_pass_xp(country_id, total_xp_gained)

    return total_xp_gained, newly_completed


def admin_set_battle_pass_tier(country_id: int, tier: int) -> tuple[bool, str]:
    """تنظیم مستقیم پله بتل‌پس کشور توسط ادمین."""
    tier = max(1, min(20, tier))
    xp_val = (tier - 1) * getattr(config, "BATTLE_PASS_XP_PER_TIER", 1000)
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE battle_pass
                SET current_tier = ?, current_xp = ?, updated_at = ?
                WHERE country_id = ?
            """, (tier, xp_val, now_str, country_id))
        return True, f"پله بتل‌پس کشور به Tier {tier} تنظیم شد."
    except Exception as e:
        return False, f"خطا: {e}"


# ==================== سامانه‌های جبران و بازیابی درآمد بازیکنان ====================

def boost_all_player_countries_income(delta_income: int) -> int:
    """افزایش همگانی درآمد روزانه برای تمامی بازیکنان فعال."""
    conn = get_connection()
    count = 0
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                UPDATE countries
                SET daily_income = MAX(100000, daily_income + ?)
                WHERE player_id > 0
            """, (delta_income,))
            count = cur.rowcount
    except Exception as e:
        logger.warning(f"Error boosting country incomes: {e}")
    finally:
        conn.close()
    return count


def grant_cash_to_all_player_countries(amount: int, description: str = "بسته حمایتی و هدیه جبرانی مدیریت ستاد") -> int:
    """واریز فوری پول نقد به خزانه تمامی بازیکنان فعال همراه با ثبت تراکنش."""
    conn = get_connection()
    count = 0
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id FROM countries WHERE player_id > 0")
            c_rows = cur.fetchall()
            for r in c_rows:
                cid = r["id"]
                cur.execute("UPDATE countries SET treasury = treasury + ? WHERE id = ?", (amount, cid))
                cur.execute("""
                    INSERT INTO transactions (country_id, type, description, amount, created_at)
                    VALUES (?, 'compensation_grant', ?, ?, ?)
                """, (cid, description, amount, now_str))
                count += 1
    except Exception as e:
        logger.warning(f"Error granting cash to countries: {e}")
    finally:
        conn.close()
    return count


def recalculate_all_countries_income_from_equipment() -> int:
    """بازمحاسبه و همگام‌سازی کامل عواید و درآمد تمام کشورها بر اساس پروژه‌ها و کارخانجات احداث‌شده."""
    conn = get_connection()
    count = 0
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id, country_key FROM countries")
            countries = cur.fetchall()

            for c in countries:
                cid = c["id"]
                ckey = c["country_key"]
                overrides = config.COUNTRY_STARTING_OVERRIDES.get(ckey, config.STARTING_VALUES)
                base_daily = overrides.get("daily_income", config.STARTING_VALUES["daily_income"])
                base_grain_daily = overrides.get("grain_daily", config.STARTING_VALUES.get("grain_daily", 2500))
                base_elec = overrides.get("electricity", config.STARTING_VALUES["electricity"])
                base_gold_daily = overrides.get("gold_daily", config.STARTING_VALUES["gold_daily"])
                base_oil_prod = overrides.get("oil_production", config.STARTING_VALUES.get("oil_production", 1_000_000))
                base_iron_daily = overrides.get("iron_ore_daily", config.STARTING_VALUES.get("iron_ore_daily", 500))
                base_chips_daily = overrides.get("microchips_daily", config.STARTING_VALUES.get("microchips_daily", 25))

                cur.execute("SELECT item_key, quantity FROM equipment WHERE country_id = ? AND quantity > 0", (cid,))
                eq_rows = cur.fetchall()
                civ_income = 0
                civ_elec = 0
                civ_grain_daily = 0
                civ_gold_daily = 0
                civ_oil_prod = 0
                civ_iron_daily = 0
                civ_chips_daily = 0

                for eq in eq_rows:
                    i_key = eq["item_key"]
                    qty = eq["quantity"]
                    item = config.ALL_SHOP_ITEMS.get(i_key, {})
                    inc = item.get("income_add", 0)
                    oil_p = item.get("oil_prod_add", 0)
                    if i_key == "oil_refinery":
                        eff = config.get_refinery_effect(ckey)
                        inc = eff.get("income", inc)
                        oil_p = eff.get("oil_prod", oil_p)
                    elif i_key == "chip_fab":
                        eff = config.get_chip_fab_effect(ckey)
                        civ_chips_daily += eff.get("chips_daily", 25) * qty
                    elif i_key == "iron_mine":
                        civ_iron_daily += item.get("iron_ore_daily_add", 1_000) * qty

                    civ_income += inc * qty
                    civ_oil_prod += oil_p * qty
                    civ_elec += item.get("elec_add", 0) * qty
                    civ_grain_daily += item.get("grain_daily_add", 0) * qty
                    civ_gold_daily += item.get("gold_daily_add", 0) * qty

                new_daily = base_daily + civ_income
                new_grain_daily = base_grain_daily + civ_grain_daily
                new_elec = base_elec + civ_elec
                new_gold_daily = base_gold_daily + civ_gold_daily
                new_oil_prod = base_oil_prod + civ_oil_prod
                new_iron_daily = base_iron_daily + civ_iron_daily
                new_chips_daily = base_chips_daily + civ_chips_daily

                cur.execute("""
                    UPDATE countries SET
                    daily_income = MAX(daily_income, ?),
                    grain_daily = MAX(grain_daily, ?),
                    electricity = MAX(electricity, ?),
                    gold_daily = MAX(gold_daily, ?),
                    oil_production = MAX(oil_production, ?),
                    iron_ore_daily = MAX(iron_ore_daily, ?),
                    microchips_daily = MAX(microchips_daily, ?)
                    WHERE id = ?
                """, (new_daily, new_grain_daily, new_elec, new_gold_daily, new_oil_prod, new_iron_daily, new_chips_daily, cid))
                count += 1
    except Exception as e:
        logger.warning(f"Error recalculating countries income: {e}")
    finally:
        conn.close()
    return count


def grant_infrastructure_package_to_all(is_add: bool = True) -> int:
    """اعطا یا کسر همگانی بسته زیرساخت (۲ کارخانه متوسط + ۲ مزرعه گندم + ۱ نیروگاه) از تمامی بازیکنان فعال."""
    conn = get_connection()
    count = 0
    mult = 1 if is_add else -1
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id, country_key FROM countries WHERE player_id > 0")
            c_rows = cur.fetchall()

            for r in c_rows:
                cid = r["id"]
                if is_add:
                    # 2x medium factory (+800k income)
                    cur.execute("INSERT INTO equipment (country_id, item_key, quantity) VALUES (?, 'medium_factory', 2) ON CONFLICT(country_id, item_key) DO UPDATE SET quantity = quantity + 2", (cid,))
                    # 2x wheat farm (+350k income, +4k grain)
                    cur.execute("INSERT INTO equipment (country_id, item_key, quantity) VALUES (?, 'wheat_farm', 2) ON CONFLICT(country_id, item_key) DO UPDATE SET quantity = quantity + 2", (cid,))
                    # 1x fossil plant (+50 MW)
                    cur.execute("INSERT INTO equipment (country_id, item_key, quantity) VALUES (?, 'fossil_plant', 1) ON CONFLICT(country_id, item_key) DO UPDATE SET quantity = quantity + 1", (cid,))
                else:
                    cur.execute("UPDATE equipment SET quantity = MAX(0, quantity - 2) WHERE country_id = ? AND item_key = 'medium_factory'", (cid,))
                    cur.execute("UPDATE equipment SET quantity = MAX(0, quantity - 2) WHERE country_id = ? AND item_key = 'wheat_farm'", (cid,))
                    cur.execute("UPDATE equipment SET quantity = MAX(0, quantity - 1) WHERE country_id = ? AND item_key = 'fossil_plant'", (cid,))

                # اعمال افزایش/کاهش روی شاخص‌های کشور
                cur.execute("""
                    UPDATE countries SET
                    daily_income = MAX(100000, daily_income + ?),
                    grain_daily = MAX(0, grain_daily + ?),
                    electricity = MAX(0, electricity + ?)
                    WHERE id = ?
                """, (1150000 * mult, 4000 * mult, 50 * mult, cid))
                count += 1
    except Exception as e:
        logger.warning(f"Error updating infra package: {e}")
    finally:
        conn.close()
    return count


def reset_all_countries_for_new_season() -> tuple[bool, int, str]:
    """سلب مالکیت کامل تمام کشورها و پاکسازی داده‌های فصلی جهت شروع رسمی و عادلانه فصل جدید."""
    conn = get_connection()
    count = 0
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM countries WHERE player_id > 0 AND country_key != 'un'")
            count = cur.fetchone()[0]

            # پاکسازی تمامی جداول فصلی
            cur.execute("DELETE FROM country_assets")
            cur.execute("DELETE FROM equipment")
            cur.execute("DELETE FROM base_assets")
            cur.execute("DELETE FROM foreign_bases")
            cur.execute("DELETE FROM naval_blockades")
            cur.execute("DELETE FROM trade_contracts")
            cur.execute("DELETE FROM market_orders")
            cur.execute("DELETE FROM diplomatic_relations")
            cur.execute("DELETE FROM loss_reports")
            cur.execute("DELETE FROM pending_roleplays")
            cur.execute("DELETE FROM daily_statements")
            cur.execute("DELETE FROM pending_country_requests")
            cur.execute("DELETE FROM un_votes")
            cur.execute("DELETE FROM war_results")
            cur.execute("DELETE FROM country_commanders")
            cur.execute("DELETE FROM intel_operations_history")
            cur.execute("DELETE FROM battle_pass")

            # حذف کشورها (به جز نقش سازمان ملل در صورت وجود)
            cur.execute("DELETE FROM countries WHERE country_key != 'un'")

            # بازنشانی سوییچرها و تاریخ‌های پرداخت
            cur.execute("DELETE FROM settings WHERE key LIKE 'active_entity_%'")
            cur.execute("DELETE FROM settings WHERE key IN ('base_cost_cycle_date', 'blockade_cycle_date', 'strait_blockade_cost_date')")

        return True, count, f"مالکیت تمام {count} کشور با موفقیت سلب شد و بازی ریست گردید."
    except Exception as e:
        logger.warning(f"Error in reset_all_countries_for_new_season: {e}")
        return False, 0, f"خطا در ریست همگانی: {e}"
    finally:
        conn.close()




