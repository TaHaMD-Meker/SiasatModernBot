# -*- coding: utf-8 -*-
"""
لایه دیتابیس بازی (SQLite).
شامل مدیریت کشورها، دارایی‌های اختصاصی نظامی (Country Assets System)، همگام‌سازی اتوماتیک دیتابیس با آخرین کاتالوگ و خرید اتومیک.
"""

import os
import re
import math
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
import borders
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

    # سازه‌های خاموش‌شده بر اثر کسری منابع (نگهداری روزانه)
    try:
        cur.execute("ALTER TABLE equipment ADD COLUMN inactive_qty INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

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

    # شناورهای آسیب‌دیده و در حال تعمیر (سیستم آسیب/تعمیر ناوگان)
    for _col, _ddl in (
        ("under_repair_qty", "ALTER TABLE country_assets ADD COLUMN under_repair_qty INTEGER DEFAULT 0"),
        ("repair_ready_at",  "ALTER TABLE country_assets ADD COLUMN repair_ready_at TEXT"),
        ("repair_severity",  "ALTER TABLE country_assets ADD COLUMN repair_severity TEXT"),
    ):
        try:
            cur.execute(_ddl)
        except sqlite3.OperationalError:
            pass

    # قفل ناوگروه اعزامی (اسکورت/مأموریت) — تا انقضا عملیاتی نیست
    cur.execute("""
    CREATE TABLE IF NOT EXISTS naval_locks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL,
        equipment_key TEXT NOT NULL,
        qty INTEGER NOT NULL,
        reason TEXT,
        until_at TEXT NOT NULL,
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_naval_locks_c ON naval_locks(country_id)")

    # درخواست اسکورت دریایی
    cur.execute("""
    CREATE TABLE IF NOT EXISTS escort_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        requester_id INTEGER NOT NULL,
        escort_id INTEGER NOT NULL,
        blocker_id INTEGER,
        payload_json TEXT DEFAULT '{}',
        task_force_json TEXT DEFAULT '{}',
        status TEXT DEFAULT 'pending',
        created_at TEXT,
        expires_at TEXT,
        FOREIGN KEY(requester_id) REFERENCES countries(id) ON DELETE CASCADE,
        FOREIGN KEY(escort_id) REFERENCES countries(id) ON DELETE CASCADE
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
        task_force_json TEXT DEFAULT '{}',
        coalition_json TEXT DEFAULT '[]',
        UNIQUE(blockader_id, target_id),
        FOREIGN KEY(blockader_id) REFERENCES countries(id) ON DELETE CASCADE,
        FOREIGN KEY(target_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)
    try:
        cur.execute("ALTER TABLE naval_blockades ADD COLUMN task_force_json TEXT DEFAULT '{}'")
    except Exception:
        pass
    try:
        cur.execute("ALTER TABLE naval_blockades ADD COLUMN coalition_json TEXT DEFAULT '[]'")
    except Exception:
        pass
    # قواعد درگیری محاصره (بعد از ساخت جدول، وگرنه ALTER بی‌صدا رد می‌شود)
    try:
        cur.execute("ALTER TABLE naval_blockades ADD COLUMN roe TEXT DEFAULT 'seize'")
    except Exception:
        pass

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
        cur.execute("ALTER TABLE countries ADD COLUMN trade_limit_override TEXT DEFAULT ''")
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
    # تحریم‌های هدفمند سازمان ملل — هر نوع جداگانه قابل اعمال/لغو است
    cur.execute("""
    CREATE TABLE IF NOT EXISTS un_targeted_sanctions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL,
        sanction_key TEXT NOT NULL,
        reason TEXT DEFAULT '',
        imposed_by INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        UNIQUE(country_id, sanction_key),
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_un_targeted_country ON un_targeted_sanctions(country_id)")

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

    # تخفیف‌های فروشگاه ویژه (VIP) — ادمین درصد تخفیف هر آیتم را تنظیم می‌کند
    cur.execute("""
        CREATE TABLE IF NOT EXISTS vip_discounts (
        item_key TEXT PRIMARY KEY,
        discount_pct INTEGER NOT NULL DEFAULT 0,
        updated_at TEXT
        )
    """)

    # دفترچه‌ی انتقالات بین‌کشوری — ضدتقلب: وقتی کشوری حذف می‌شود، انتقال‌های
    # اخیرش از کشور مقصد بازگردانده می‌شود (جلوگیری از «پارک دارایی»).
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transfer_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_country_id INTEGER NOT NULL,
        to_country_id INTEGER NOT NULL,
        kind TEXT NOT NULL,               -- aid | trade_asset | trade_resource
        item_key TEXT,
        item_name TEXT,
        qty INTEGER DEFAULT 0,            -- تعداد تجهیز
        resource_type TEXT,               -- oil/grain/treasury/...
        amount INTEGER DEFAULT 0,         -- مقدار منبع
        money_paid INTEGER DEFAULT 0,     -- در معامله: پولی که خریدار داده
        created_at TEXT NOT NULL,
        status TEXT DEFAULT 'active'      -- active | rolled_back
        )
    """)

    # شمارنده‌ی محموله‌های خروجی روزانه هر کشور (سقف ضدتقلب)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS transfer_daily (
        country_id INTEGER NOT NULL,
        day TEXT NOT NULL,
        count INTEGER DEFAULT 0,
        PRIMARY KEY (country_id, day)
        )
    """)

    # شمارنده‌ی تجارت‌های روزانه به تفکیک روش ترابری (سقف پایه ۲ + افزایش با بنادر/فرودگاه‌ها/جاده‌ها)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trade_daily_modes (
        country_id INTEGER NOT NULL,
        day TEXT NOT NULL,
        mode TEXT NOT NULL,
        count INTEGER DEFAULT 0,
        PRIMARY KEY (country_id, day, mode)
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

    # تورنومنت امتیازدهی ترکیبی (پیش‌نویس/فعال/متوقف/پایان‌یافته)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tournament_seasons (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'draft',
        duration_days INTEGER NOT NULL DEFAULT 7,
        starts_at TEXT,
        ends_at TEXT,
        prize_text TEXT DEFAULT '',
        scoring_config TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        activated_at TEXT,
        paused_at TEXT,
        ended_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tournament_players (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        season_id INTEGER NOT NULL,
        country_id INTEGER NOT NULL,
        player_id INTEGER NOT NULL,
        joined_at TEXT NOT NULL,
        baseline_at TEXT,
        baseline_json TEXT NOT NULL DEFAULT '{}',
        last_metrics_json TEXT NOT NULL DEFAULT '{}',
        score REAL NOT NULL DEFAULT 0,
        economy_score REAL NOT NULL DEFAULT 0,
        military_score REAL NOT NULL DEFAULT 0,
        diplomacy_score REAL NOT NULL DEFAULT 0,
        activity_score REAL NOT NULL DEFAULT 0,
        objectives_score REAL NOT NULL DEFAULT 0,
        stability_score REAL NOT NULL DEFAULT 0,
        manual_score REAL NOT NULL DEFAULT 0,
        last_snapshot_at TEXT,
        status TEXT NOT NULL DEFAULT 'active',
        disqualified_reason TEXT,
        UNIQUE(season_id, player_id),
        UNIQUE(season_id, country_id),
        FOREIGN KEY(season_id) REFERENCES tournament_seasons(id) ON DELETE CASCADE,
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tournament_snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        season_id INTEGER NOT NULL,
        country_id INTEGER NOT NULL,
        player_id INTEGER NOT NULL,
        captured_at TEXT NOT NULL,
        total_score REAL NOT NULL DEFAULT 0,
        economy_score REAL NOT NULL DEFAULT 0,
        military_score REAL NOT NULL DEFAULT 0,
        diplomacy_score REAL NOT NULL DEFAULT 0,
        activity_score REAL NOT NULL DEFAULT 0,
        objectives_score REAL NOT NULL DEFAULT 0,
        stability_score REAL NOT NULL DEFAULT 0,
        metrics_json TEXT NOT NULL DEFAULT '{}',
        UNIQUE(season_id, country_id, captured_at),
        FOREIGN KEY(season_id) REFERENCES tournament_seasons(id) ON DELETE CASCADE,
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tournament_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        season_id INTEGER NOT NULL,
        country_id INTEGER NOT NULL,
        player_id INTEGER NOT NULL,
        event_key TEXT NOT NULL,
        event_type TEXT NOT NULL,
        points REAL NOT NULL,
        description TEXT DEFAULT '',
        created_at TEXT NOT NULL,
        admin_id INTEGER,
        UNIQUE(season_id, country_id, event_key),
        FOREIGN KEY(season_id) REFERENCES tournament_seasons(id) ON DELETE CASCADE,
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)

    cur.execute("CREATE INDEX IF NOT EXISTS idx_tournament_players_score ON tournament_players(season_id, status, score DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_tournament_snapshots_lookup ON tournament_snapshots(season_id, country_id, captured_at)")

    # ─────────────────────────────────────────────────────────────────────
    # لاگ عمومی اقدامات (add_log). این جدول قبلاً ساخته نمی‌شد و هر فراخوانی
    # add_log روی دیتابیس تازه با «no such table: logs» کرش می‌کرد — از جمله
    # خرید فروشگاه، ارتقای تکنولوژی، درخواست کشور و تأیید/رد کشور توسط ادمین.
    # ─────────────────────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor TEXT,
        action TEXT NOT NULL,
        details TEXT DEFAULT '',
        created_at TEXT NOT NULL
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_logs_action ON logs(action, created_at DESC)")

    # جداول نقش‌ها: داورها، لاگ و امتیاز
    _init_role_tables(cur)

    # ─────────────────────────────────────────────────────────────────────
    # سیستم جمعیت پویا، مالیات، ناآرامی و بحران (internal_affairs)
    # ─────────────────────────────────────────────────────────────────────
    cur.execute("""
    CREATE TABLE IF NOT EXISTS country_internal (
        country_id INTEGER PRIMARY KEY,
        tax_policy TEXT NOT NULL DEFAULT 'normal',
        tax_policy_changed_at TEXT,
        tax_policy_days INTEGER NOT NULL DEFAULT 0,
        baseline_population INTEGER NOT NULL DEFAULT 0,
        baseline_tax_income INTEGER NOT NULL DEFAULT 0,
        unrest REAL NOT NULL DEFAULT 0,
        unrest_stage INTEGER NOT NULL DEFAULT 0,
        critical_days INTEGER NOT NULL DEFAULT 0,
        collapse_risk INTEGER NOT NULL DEFAULT 0,
        emergency_until TEXT,
        crisis_shield_until TEXT,
        last_cycle_date TEXT,
        created_at TEXT,
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS internal_daily_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL,
        log_date TEXT NOT NULL,
        population_before INTEGER NOT NULL DEFAULT 0,
        population_after INTEGER NOT NULL DEFAULT 0,
        population_delta INTEGER NOT NULL DEFAULT 0,
        tax_before INTEGER NOT NULL DEFAULT 0,
        tax_after INTEGER NOT NULL DEFAULT 0,
        approval INTEGER NOT NULL DEFAULT 0,
        unrest REAL NOT NULL DEFAULT 0,
        unrest_stage INTEGER NOT NULL DEFAULT 0,
        tax_policy TEXT NOT NULL DEFAULT 'normal',
        notes TEXT DEFAULT '',
        details_json TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL,
        UNIQUE(country_id, log_date),
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS country_crises (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL,
        crisis_key TEXT NOT NULL,
        severity TEXT NOT NULL DEFAULT 'medium',
        stage TEXT NOT NULL DEFAULT 'warning',
        origin TEXT NOT NULL DEFAULT 'random',
        duration_days INTEGER NOT NULL DEFAULT 2,
        warned_at TEXT,
        started_at TEXT,
        ends_at TEXT,
        ended_at TEXT,
        mitigation REAL NOT NULL DEFAULT 0,
        escalations INTEGER NOT NULL DEFAULT 0,
        last_escalation_date TEXT,
        last_severity_slot TEXT,
        light_since TEXT,
        contained_days INTEGER NOT NULL DEFAULT 0,
        outcome TEXT,
        damage_json TEXT NOT NULL DEFAULT '{}',
        created_by INTEGER,
        created_at TEXT NOT NULL,
        news_flags TEXT NOT NULL DEFAULT '',
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS crisis_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crisis_id INTEGER NOT NULL,
        country_id INTEGER NOT NULL,
        action_key TEXT NOT NULL,
        actor_id INTEGER,
        cost INTEGER NOT NULL DEFAULT 0,
        mitigation REAL NOT NULL DEFAULT 0,
        action_date TEXT NOT NULL DEFAULT '',
        created_at TEXT NOT NULL,
        UNIQUE(crisis_id, action_key, action_date),
        FOREIGN KEY(crisis_id) REFERENCES country_crises(id) ON DELETE CASCADE,
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)

    # مهاجرت: نسخه‌ی اول UNIQUE(crisis_id, action_key) داشت، یعنی هر اقدام فقط
    # یک‌بار در کل عمر بحران. برای بحران چندروزه باید هر روز دوباره در دسترس
    # باشد، پس جدول با کلید یکتای سه‌ستونی بازسازی می‌شود.
    try:
        columns = {row[1] for row in cur.execute("PRAGMA table_info(crisis_actions)")}
        if "action_date" not in columns:
            cur.execute("ALTER TABLE crisis_actions RENAME TO crisis_actions_old")
            cur.execute("""
            CREATE TABLE crisis_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                crisis_id INTEGER NOT NULL,
                country_id INTEGER NOT NULL,
                action_key TEXT NOT NULL,
                actor_id INTEGER,
                cost INTEGER NOT NULL DEFAULT 0,
                mitigation REAL NOT NULL DEFAULT 0,
                action_date TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                UNIQUE(crisis_id, action_key, action_date),
                FOREIGN KEY(crisis_id) REFERENCES country_crises(id) ON DELETE CASCADE,
                FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
            )
            """)
            cur.execute("""
                INSERT INTO crisis_actions
                (id, crisis_id, country_id, action_key, actor_id, cost, mitigation, action_date, created_at)
                SELECT id, crisis_id, country_id, action_key, actor_id, cost, mitigation,
                       COALESCE(SUBSTR(created_at, 1, 10), ''), created_at
                FROM crisis_actions_old
            """)
            cur.execute("DROP TABLE crisis_actions_old")
    except sqlite3.OperationalError:
        pass


    # ─────────────────────────────────────────────────────────────────────
    # قرنطینه‌ی کشور رهاشده و صف انتظار بازیکنان
    # ─────────────────────────────────────────────────────────────────────
    for column, ddl in (
        ("quarantined_at", "ALTER TABLE countries ADD COLUMN quarantined_at TEXT"),
        ("quarantine_until", "ALTER TABLE countries ADD COLUMN quarantine_until TEXT"),
        ("previous_player_id", "ALTER TABLE countries ADD COLUMN previous_player_id INTEGER"),
        ("absence_insurance_until", "ALTER TABLE countries ADD COLUMN absence_insurance_until TEXT"),
    ):
        try:
            cur.execute(ddl)
        except sqlite3.OperationalError:
            pass

    cur.execute("""
    CREATE TABLE IF NOT EXISTS country_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        player_id INTEGER NOT NULL UNIQUE,
        first_name TEXT,
        username TEXT,
        preferred_country_key TEXT,
        priority INTEGER NOT NULL DEFAULT 0,
        status TEXT NOT NULL DEFAULT 'waiting',
        offered_country_id INTEGER,
        offer_expires_at TEXT,
        joined_at TEXT NOT NULL,
        resolved_at TEXT
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_country_queue_order ON country_queue(status, priority DESC, id ASC)")

    # واکسن: آیتم تولیدی و غیرقابل فروش/انتقال
    try:
        cur.execute("ALTER TABLE countries ADD COLUMN vaccine_doses INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    cur.execute("""
    CREATE TABLE IF NOT EXISTS vaccine_projects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL,
        doses INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'in_progress',
        cost INTEGER NOT NULL DEFAULT 0,
        microchips_used INTEGER NOT NULL DEFAULT 0,
        isotopes_used INTEGER NOT NULL DEFAULT 0,
        started_at TEXT NOT NULL,
        ready_at TEXT NOT NULL,
        collected_at TEXT,
        started_by INTEGER,
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_vaccine_projects_country ON vaccine_projects(country_id, status)")

    # شورش مسلحانه — مغز «بازیکن بات» در برابر دولت (کلید سراسری: insurgency_enabled)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS insurgencies (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL UNIQUE,
        fighters INTEGER NOT NULL DEFAULT 0,
        boldness REAL NOT NULL DEFAULT 55,
        phase INTEGER NOT NULL DEFAULT 1,
        night INTEGER NOT NULL DEFAULT 0,
        last_tick_date TEXT,
        actions_today INTEGER NOT NULL DEFAULT 0,
        last_action_date TEXT,
        neg_cooldown INTEGER NOT NULL DEFAULT 0,
        truce_betray_night INTEGER,
        commander_hostage TEXT NOT NULL DEFAULT '',
        seed_base INTEGER NOT NULL DEFAULT 0,
        slot_key TEXT,
        guard_slots INTEGER NOT NULL DEFAULT 0,
        created_at TEXT,
        updated_at TEXT,
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_insurgencies_country ON insurgencies(country_id)")
    # مهاجرت‌های افزایشی شورش — بعد از CREATE TABLE تا داخل try/except بی‌صدا نباشند
    for ins_column, ins_ddl in (
        ("slot_key", "ALTER TABLE insurgencies ADD COLUMN slot_key TEXT"),
        ("guard_slots", "ALTER TABLE insurgencies ADD COLUMN guard_slots INTEGER NOT NULL DEFAULT 0"),
    ):
        try:
            cur.execute(ins_ddl)
        except sqlite3.OperationalError:
            pass

    # مهاجرت‌های افزایشی country_crises
    for column, ddl in (
        ("escalations", "ALTER TABLE country_crises ADD COLUMN escalations INTEGER NOT NULL DEFAULT 0"),
        ("last_escalation_date", "ALTER TABLE country_crises ADD COLUMN last_escalation_date TEXT"),
        ("contained_days", "ALTER TABLE country_crises ADD COLUMN contained_days INTEGER NOT NULL DEFAULT 0"),
        ("outcome", "ALTER TABLE country_crises ADD COLUMN outcome TEXT"),
    ):
        try:
            cur.execute(ddl)
        except sqlite3.OperationalError:
            pass

    # مهاجرت‌های افزایشی country_internal
    for column, ddl in (
        ("pressure_days", "ALTER TABLE country_internal ADD COLUMN pressure_days INTEGER NOT NULL DEFAULT 0"),
        ("policy_locked", "ALTER TABLE country_internal ADD COLUMN policy_locked INTEGER NOT NULL DEFAULT 0"),
    ):
        try:
            cur.execute(ddl)
        except sqlite3.OperationalError:
            pass

    cur.execute("CREATE INDEX IF NOT EXISTS idx_country_crises_active ON country_crises(country_id, stage)")
    for _col, _decl in (("last_severity_slot", "TEXT"), ("light_since", "TEXT")):
        try:
            cur.execute(f"ALTER TABLE country_crises ADD COLUMN {_col} {_decl}")
        except Exception:
            pass

    cur.execute("CREATE INDEX IF NOT EXISTS idx_internal_daily_log_lookup ON internal_daily_log(country_id, log_date DESC)")

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
        purge_state_equipment_from_militias()
    except Exception as e:
        print(f"[militia-purge] error: {e}")

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

# نگاشت واحدِ «قلم ویژه» → ستون کشور. مرجع مشترک اعمال/بازگردانی تا هیچ‌وقت
# مسیر revert از مسیر apply عقب نیفتد (باگ قدیمی: منابع راهبردی برنمی‌گشتند).
LOSS_SPECIAL_COLUMNS = {
    "money": "treasury",
    "oil": "oil_reserves",
    "mil_kia": "active_personnel",
    "civ_kia": "population",
    "uranium_ore": "uranium_ore",
    "nuclear_fuel": "nuclear_fuel",
    "medical_isotopes": "medical_isotopes",
    "enriched_60": "enriched_60",
    "weapons_grade_90": "weapons_grade_90",
    "warheads": "warheads",
    "microchips": "microchips",
    "gold": "gold",
    # کسر ذخایر از کشور مدافع (متمایز از "oil" که هزینه‌ی سوخت مهاجم است)
    "oil_reserves": "oil_reserves",
    "grain": "grain",
    "electricity": "electricity",
    "vaccine_doses": "vaccine_doses",
}

# اقلامی که فقط ثبت گزارشی می‌شوند و روی هیچ موجودی اثر ندارند
LOSS_RECORD_ONLY_SPECIALS = ("wounded",)

_LOSS_SPECIAL_LABELS = {
    "money": "هزینه مالی",
    "oil": "سوخت مصرفی",
    "mil_kia": "تلفات نظامی",
    "civ_kia": "تلفات غیرنظامی",
    "uranium_ore": "تلفات اورانیوم",
    "nuclear_fuel": "تلفات سوخت هسته‌ای",
    "warheads": "تلفات کلاهک هسته‌ای",
    "microchips": "تلفات میکروچیپ",
    "iron_ore": "تلفات سنگ آهن و فولاد",
    "gold": "تلفات طلا",
    "oil_reserves": "تلفات ذخایر نفت",
    "grain": "تلفات ذخایر غلات",
    "electricity": "خسارت شبکه برق",
    "vaccine_doses": "تلفات ذخایر واکسن",
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


def _kill_commander_with_cur(cur, country_id: int, commander_key: str, reason: str = "ترور اطلاعاتی") -> tuple[bool, str]:
    """تغییر وضعیت فرمانده با cursor تراکنش جاری؛ اتصال دوم باز نمی‌کند."""
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    now_str = now_dt.isoformat()
    until_str = (now_dt + datetime.timedelta(hours=24)).isoformat()
    cur.execute(
        """
        UPDATE country_commanders SET status = 'assassinated', killed_at = ?
        WHERE country_id = ? AND (key = ? OR title LIKE ?) AND status = 'active'
        """,
        (now_str, country_id, commander_key, f"%{commander_key}%"),
    )
    if cur.rowcount <= 0:
        return False, "فرمانده یافت نشد یا قبلاً ترور شده است."

    cur.execute(
        """
        UPDATE countries SET
        combat_readiness = MAX(0, combat_readiness - 15),
        command_disrupted_until = ?
        WHERE id = ?
        """,
        (until_str, country_id),
    )
    cur.execute(
        """
        INSERT INTO transactions (country_id, type, description, amount, created_at)
        VALUES (?, 'commander_killed', ?, 0, ?)
        """,
        (country_id, f"🎖️ شهادت / ترور {commander_key} ({reason})", now_str),
    )
    return True, f"فرمانده {commander_key} مورد اصابت قرار گرفت و وضعیت وی به ترور/شهید تغییر یافت."


def _revive_commander_with_cur(cur, country_id: int, commander_key: str) -> bool:
    """بازگردانی فرمانده با cursor تراکنش جاری؛ اتصال دوم باز نمی‌کند."""
    cur.execute(
        """
        UPDATE country_commanders SET status = 'active', killed_at = NULL
        WHERE country_id = ? AND (key = ? OR title LIKE ?)
        """,
        (country_id, commander_key, f"%{commander_key}%"),
    )
    return cur.rowcount > 0


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
            _revive_commander_with_cur(cur, country_id, cmd_k)
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
    # بازیابی اثر رضایت عمومی در صورت لغو/حذف گزارش با تلفات غیرنظامی ۵۰ نفر به بالا
    civ_kia_total = sum(int(it.get("qty", 0) or 0) for it in items if it.get("special") == "civ_kia")
    if civ_kia_total >= 50:
        cur.execute(
            "UPDATE countries SET approval_rating = MIN(100, COALESCE(approval_rating, 80) + 5) WHERE id = ?",
            (country_id,),
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
                    _kill_commander_with_cur(cur, country_id, cmd_k, f"اصابت در عملیات {operation_name}")
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
            # کسر ۵٪ رضایت عمومی در صورت تلفات غیرنظامی ۵۰ نفر یا بیشتر در عملیات (سیاست داخلی)
            civ_kia_total = sum(int(it.get("qty", 0) or 0) for it in valid_items if it.get("special") == "civ_kia")
            if civ_kia_total >= 50:
                cur.execute(
                    "UPDATE countries SET approval_rating = MAX(0, COALESCE(approval_rating, 80) - 5) WHERE id = ?",
                    (country_id,),
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


def delete_country_by_id(country_id: int, actor: str = "system") -> bool:
    """حذف کامل کشور — عملیات مخرب و برگشت‌ناپذیر؛ قبل از حذف اسنپ‌شات بایگانی
    و بعد از حذف رکورد لاگ می‌شود (audit trail برای داوری)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM countries WHERE id = ?", (country_id,))
    if not cur.fetchone():
        conn.close()
        return False
    cur.execute(
        """
        SELECT id, name, flag, country_key, player_id, username, treasury,
               oil_reserves, active_personnel, reserve_personnel,
               COALESCE(population, 0) AS population, approval_rating
        FROM countries WHERE id = ?
        """, (country_id,))
    snapshot_row = dict(cur.fetchone())
    cur.execute("SELECT COUNT(*) FROM equipment WHERE country_id = ?", (country_id,))
    snapshot_row["equipment_rows"] = cur.fetchone()[0]
    cur.execute("DELETE FROM country_assets WHERE country_id = ?", (country_id,))
    cur.execute("DELETE FROM equipment WHERE country_id = ?", (country_id,))
    cur.execute("DELETE FROM transactions WHERE country_id = ?", (country_id,))
    cur.execute("DELETE FROM countries WHERE id = ?", (country_id,))
    conn.commit()
    conn.close()
    try:
        import json as _json
        add_log(actor, "country_deleted",
                _json.dumps(snapshot_row, ensure_ascii=False)[:4000])
    except Exception:
        print(f"[audit-log] failed to log deletion of country {country_id}")
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
        # سقف دستی تجارت روزانه (JSON هر روش ترابری — پنل مالک)
        "trade_limit_override",
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
        "golden_stmt_credits", "pin_credits", "contract_boost_until", "bp_booster_until", "bp_booster_mult",
        # واکسن: تولیدی و غیرقابل فروش، اما ادمین باید بتواند اصلاحش کند
        "vaccine_doses",
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


# ---------- انتخاب کاتالوگ تجهیزات ----------

def is_militia_country_key(country_key: str) -> bool:
    """آیا این کلید متعلق به یک گروه شبه‌نظامی است؟ (گروه آماده یا سفارشی)"""
    return bool(country_key) and str(country_key).startswith("faction_")


def get_equipment_catalog_for(country_key: str):
    """کاتالوگ تجهیزات درست را برای یک کشور یا گروه شبه‌نظامی برمی‌گرداند.

    گروه‌های شبه‌نظامی (کلید `faction_*`) هرگز نباید تجهیزات کشوری
    (جنگنده نسل ۴.۵، بمب‌افکن استراتژیک، ناوگان و...) دریافت کنند.
    """
    if not country_key:
        return config.DEFAULT_COUNTRY_EQUIPMENT

    if is_militia_country_key(country_key):
        faction_key = str(country_key)[len("faction_"):]
        militia_cats = getattr(config, "MILITIA_EQUIPMENT_CATALOG", {})
        if faction_key in militia_cats:
            return militia_cats[faction_key]
        # گروه سفارشی: کاتالوگ عمومی شبه‌نظامی
        return getattr(config, "DEFAULT_MILITIA_EQUIPMENT", config.DEFAULT_COUNTRY_EQUIPMENT)

    return config.COUNTRY_EQUIPMENT_CATALOG.get(country_key, config.DEFAULT_COUNTRY_EQUIPMENT)


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

        catalog = get_equipment_catalog_for(c_key)
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

                cur.execute("SELECT item_key, quantity, COALESCE(inactive_qty, 0) AS inactive_qty"
                            " FROM equipment WHERE country_id = ?", (c_id,))
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
                    qty = max(0, int(eq["quantity"] or 0) - int(eq["inactive_qty"] or 0))
                    if qty <= 0:
                        continue
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


def apply_building_upkeep(country_id: int, today_str: str | None = None) -> dict:
    """نگهداری روزانه‌ی سازه‌ها: کسر منابع، خاموشی جزئی، بازفعال‌سازی خودکار.

    منطق:
      ۱) نیاز روزانه‌ی همه‌ی سازه‌ها (با فرض فعال بودن همه) محاسبه می‌شود.
      ۲) اگر منابع کافی است → همه فعال، منابع کسر می‌شود، inactive_qty صفر.
      ۳) اگر کم است → سازه‌ها بر اساس «بازده» (درآمد ÷ هزینه) صعودی مرتب
         می‌شوند و از کم‌بازده‌ترین، واحد به واحد خاموش می‌شوند تا موجودی
         کفاف بدهد. سازه‌ی خاموش نه منبع می‌خورد نه بونوس می‌دهد.
      ۴) هر بار از صفر حساب می‌شود، پس idempotent است و بازفعال‌سازی
         خودکار اتفاق می‌افتد؛ نیازی به دکمه نیست.

    برق ظرفیت است نه انبار: سقف برق در دسترس = برق پایه‌ی کشور (بدون
    سهم سازه‌های خاموش) و مصرف سازه‌ها از همان کم می‌شود.

    خروجی: dict گزارش برای نمایش در چرخه‌ی روزانه.
    """
    empty = {"ok": True, "shortages": {}, "shut_down": [], "reactivated": [],
             "consumed": {}, "income_lost": 0, "ramp": 1.0}
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id, country_key, treasury, oil_reserves, grain, iron_ore,"
                        " microchips, nuclear_fuel, electricity FROM countries WHERE id = ?", (country_id,))
            c = cur.fetchone()
            if not c:
                return empty
            c_key = c["country_key"]

            cur.execute("SELECT item_key, quantity, COALESCE(inactive_qty, 0) AS inactive_qty"
                        " FROM equipment WHERE country_id = ? AND quantity > 0", (country_id,))
            rows = [r for r in cur.fetchall() if r["item_key"] in config.ALL_SHOP_ITEMS]
            if not rows:
                return empty

            ramp = config.upkeep_ramp_factor(today_str)
            if ramp <= 0:
                cur.execute("UPDATE equipment SET inactive_qty = 0 WHERE country_id = ?", (country_id,))
                return dict(empty, ramp=0.0)

            # ── موجودی در دسترس
            stock = {
                "money": max(0, int(c["treasury"] or 0)),
                "oil": max(0, int(c["oil_reserves"] or 0)),
                "grain": max(0, int(c["grain"] or 0)),
                "iron_ore": max(0, int((c["iron_ore"] if "iron_ore" in c.keys() else 0) or 0)),
                "microchips": max(0, int((c["microchips"] if "microchips" in c.keys() else 0) or 0)),
                "nuclear_fuel": max(0, int((c["nuclear_fuel"] if "nuclear_fuel" in c.keys() else 0) or 0)),
            }

            ov = config.COUNTRY_STARTING_OVERRIDES.get(c_key, config.STARTING_VALUES)
            base_elec = int(ov.get("electricity", config.STARTING_VALUES["electricity"]))

            # ── واحدها را باز کن: هر واحد یک ردیف، مرتب بر اساس بازده صعودی
            units = []
            for r in rows:
                key = r["item_key"]
                item = config.ALL_SHOP_ITEMS[key]
                up = config.get_building_upkeep(key)
                if not up:
                    continue
                income = int(item.get("income_add", 0) or 0)
                if key == "oil_refinery":
                    income = int(config.get_refinery_effect(c_key).get("income", income))
                cost_weight = float(up.get("money", 0)) + float(up.get("oil", 0)) * 5.0
                efficiency = income / cost_weight if cost_weight > 0 else float("inf")
                for _ in range(int(r["quantity"])):
                    units.append({"key": key, "eff": efficiency, "income": income,
                                  "upkeep": up, "elec_add": float(item.get("elec_add", 0) or 0)})
            if not units:
                return empty
            units.sort(key=lambda u: u["eff"])

            def scaled(u, res):
                raw = float(u["upkeep"].get(res, 0)) * ramp
                if res == "elec":
                    return raw
                return int(math.ceil(raw)) if raw > 0 else 0

            # ── از همه‌فعال شروع کن و از کم‌بازده‌ترین خاموش کن تا جا بیفتد
            active = [True] * len(units)

            def totals():
                need = {k: 0 for k in ("money", "oil", "grain", "iron_ore", "microchips", "nuclear_fuel")}
                elec_need = 0.0
                elec_cap = float(base_elec)
                for u, on in zip(units, active):
                    if not on:
                        continue
                    for res in need:
                        need[res] += scaled(u, res)
                    elec_need += scaled(u, "elec")
                    elec_cap += u["elec_add"]
                return need, elec_need, elec_cap

            shortages = {}
            for _ in range(len(units) + 1):
                need, elec_need, elec_cap = totals()
                lacking = {res: need[res] - stock[res] for res in need if need[res] > stock[res]}
                if elec_need > elec_cap:
                    lacking["elec"] = round(elec_need - elec_cap, 2)
                if not lacking:
                    break
                for res, amount in lacking.items():
                    shortages[res] = max(shortages.get(res, 0), amount)
                # کم‌بازده‌ترین واحدِ فعالی که در این کسری سهم دارد را خاموش کن
                victim = None
                for idx, (u, on) in enumerate(zip(units, active)):
                    if not on:
                        continue
                    if any(scaled(u, res) > 0 for res in lacking):
                        victim = idx
                        break
                if victim is None:
                    victim = next((i for i, on in enumerate(active) if on), None)
                if victim is None:
                    break
                active[victim] = False

            need, elec_need, elec_cap = totals()

            # ── کسر منابع
            consumed = {res: min(need[res], stock[res]) for res in need if need[res] > 0}
            cur.execute("""
                UPDATE countries SET
                    treasury      = treasury - ?,
                    oil_reserves  = MAX(0, oil_reserves - ?),
                    grain         = MAX(0, grain - ?),
                    iron_ore      = MAX(0, COALESCE(iron_ore, 0) - ?),
                    microchips    = MAX(0, COALESCE(microchips, 0) - ?),
                    nuclear_fuel  = MAX(0, COALESCE(nuclear_fuel, 0) - ?)
                WHERE id = ?
            """, (consumed.get("money", 0), consumed.get("oil", 0), consumed.get("grain", 0),
                  consumed.get("iron_ore", 0), consumed.get("microchips", 0),
                  consumed.get("nuclear_fuel", 0), country_id))

            # ── ثبت خاموشی‌ها
            off = {}
            for u, on in zip(units, active):
                if not on:
                    off[u["key"]] = off.get(u["key"], 0) + 1
            prev = {r["item_key"]: int(r["inactive_qty"] or 0) for r in rows}
            for r in rows:
                key = r["item_key"]
                cur.execute("UPDATE equipment SET inactive_qty = ? WHERE country_id = ? AND item_key = ?",
                            (off.get(key, 0), country_id, key))

            shut_down, reactivated, income_lost = [], [], 0
            for key in sorted(set(list(off.keys()) + list(prev.keys()))):
                now_off, was_off = off.get(key, 0), prev.get(key, 0)
                name = config.ALL_SHOP_ITEMS.get(key, {}).get("name", key)
                inc = int(config.ALL_SHOP_ITEMS.get(key, {}).get("income_add", 0) or 0)
                income_lost += inc * now_off
                if now_off > was_off:
                    shut_down.append({"key": key, "name": name, "qty": now_off - was_off,
                                      "total_off": now_off, "income": inc})
                elif now_off < was_off:
                    reactivated.append({"key": key, "name": name, "qty": was_off - now_off, "income": inc})

            return {
                "ok": not shortages,
                "shortages": {k: (round(v, 2) if k == "elec" else int(v)) for k, v in shortages.items()},
                "shut_down": shut_down,
                "reactivated": reactivated,
                "consumed": consumed,
                "income_lost": income_lost,
                "ramp": ramp,
            }
    except Exception as e:
        print(f"[building-upkeep] error for country {country_id}: {e}")
        return empty
    finally:
        conn.close()


def format_upkeep_report(result: dict) -> str:
    """متن هشدار نگهداری برای گزارش روزانه. اگر چیزی برای گفتن نبود، رشته‌ی خالی."""
    if not result:
        return ""
    lines = []
    labels, units = config.UPKEEP_RESOURCE_LABELS, config.UPKEEP_RESOURCE_UNITS

    if result.get("shut_down"):
        total = sum(s["qty"] for s in result["shut_down"])
        lines.append(f"⚠️ <b>کمبود منابع — {total} سازه از کار افتاد</b>")
        for res, amount in result.get("shortages", {}).items():
            amt = f"{amount:,}" if res != "elec" else f"{amount:g}"
            lines.append(f"\n{labels.get(res, res)} کسری: <b>{amt} {units.get(res, '')}</b>")
        for s in result["shut_down"]:
            lines.append(f"   🔴 {s['qty']} × {s['name']} — خاموش")
        if result.get("income_lost"):
            lines.append(f"   💸 درآمد از‌دست‌رفته: <b>{result['income_lost']:,}</b> دلار/روز")
        lines.append("\n💡 با تأمین کسری، سازه‌ها در چرخه‌ی بعد خودکار روشن می‌شوند.")

    if result.get("reactivated"):
        total = sum(s["qty"] for s in result["reactivated"])
        gained = sum(s["qty"] * s["income"] for s in result["reactivated"])
        if lines:
            lines.append("")
        lines.append(f"✅ <b>{total} سازه دوباره وارد مدار شدند</b>")
        for s in result["reactivated"]:
            lines.append(f"   🟢 {s['qty']} × {s['name']}")
        if gained:
            lines.append(f"   💰 درآمد بازگشته: <b>+{gained:,}</b> دلار/روز")

    if lines and result.get("ramp", 1.0) < 1.0:
        lines.append(f"\n<i>ℹ️ دوره‌ی گذار نگهداری: هزینه‌ها فعلاً {int(result['ramp'] * 100)}٪ اعمال می‌شود.</i>")
    return "\n".join(lines)


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

            cur.execute("SELECT item_key, quantity, COALESCE(inactive_qty, 0) AS inactive_qty"
                        " FROM equipment WHERE country_id = ? AND quantity > 0", (country_id,))
            civ = {k: 0 for k in base}
            for eq in cur.fetchall():
                i_key = eq["item_key"]
                # سازه‌های خاموش‌شده بر اثر کسری منابع هیچ بونوسی نمی‌دهند
                qty = max(0, int(eq["quantity"]) - int(eq["inactive_qty"] or 0))
                if qty <= 0:
                    continue
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


def purge_state_equipment_from_militias():
    """مایگریشن: حذف تجهیزات کشوری که اشتباهاً به گروه‌های شبه‌نظامی تزریق شده بود.

    باگ: `seed_country_assets` و `sync_all_country_assets_to_catalog` برای کلیدهای
    `faction_*` (که در COUNTRY_EQUIPMENT_CATALOG نیستند) به DEFAULT_COUNTRY_EQUIPMENT
    fallback می‌کردند و اقلام `gen_*` مثل «جنگنده پیشرفته نسل ۴.۵» را به گروه‌های
    شبه‌نظامی می‌دادند. این تابع یک‌بار آن اقلام را پاک می‌کند.
    """
    if get_setting("militia_state_equipment_purged_v1"):
        return

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT id, name, country_key FROM countries WHERE country_key LIKE 'faction_%'")
    militias = [dict(r) for r in cur.fetchall()]

    purged_rows = 0
    affected = 0
    for m in militias:
        allowed = {i["key"] for i in get_equipment_catalog_for(m["country_key"])}
        cur.execute("SELECT equipment_key, amount FROM country_assets WHERE country_id = ?", (m["id"],))
        rows = [dict(r) for r in cur.fetchall()]
        bad = [r["equipment_key"] for r in rows if r["equipment_key"] not in allowed]
        if not bad:
            continue
        cur.executemany(
            "DELETE FROM country_assets WHERE country_id = ? AND equipment_key = ?",
            [(m["id"], k) for k in bad],
        )
        purged_rows += len(bad)
        affected += 1
        print(f"[militia-purge] {m['name']} ({m['country_key']}): removed {len(bad)} state-grade items")

    conn.commit()
    conn.close()

    set_setting("militia_state_equipment_purged_v1", datetime.datetime.now(datetime.timezone.utc).isoformat())
    if purged_rows:
        print(f"[militia-purge] done: {purged_rows} rows removed from {affected} militia group(s).")


def seed_country_assets(country_id: int, country_key: str):
    conn = get_connection()
    cur = conn.cursor()

    catalog = get_equipment_catalog_for(country_key)

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
    """تولید یک تجهیز بومی به‌صورت اتمیک و با اعتبارسنجی ورودی."""
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        return False, "تعداد تولید باید یک عدد صحیح بزرگ‌تر از صفر باشد.", {}

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
    """خرید ساختمان/پروژه به‌صورت اتمیک.

    قیمت و تعداد از callback تلگرام قابل جعل هستند؛ بنابراین قیمت واقعی از
    کاتالوگ دوباره محاسبه می‌شود و هیچ مقدار ارسالیِ کاربر به‌تنهایی معتبر نیست.
    """
    item = config.ALL_SHOP_ITEMS.get(item_key)
    if not item:
        return False, "این پروژه در کاتالوگ فروشگاه وجود ندارد."
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        return False, "تعداد احداث باید یک عدد صحیح بزرگ‌تر از صفر باشد."

    expected_total_price = int(item["price"]) * quantity
    if total_price != expected_total_price:
        return False, "قیمت سفارش با قیمت فعلی فروشگاه مطابقت ندارد؛ لطفاً دوباره تلاش کنید."

    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
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

            cur.execute("SELECT quantity FROM equipment WHERE country_id = ? AND item_key = ?", (country_id, item_key))
            equipment_row = cur.fetchone()
            current_quantity = (equipment_row["quantity"] or 0) if equipment_row else 0
            max_limit = int(item.get("max_limit", 10) or 10)
            if current_quantity + quantity > max_limit:
                return False, f"سقف مجاز احداث این پروژه پر شده است (حداکثر {max_limit} واحد)."

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


def has_targeted_sanction(country_id: int, sanction_key: str) -> bool:
    """آیا این تحریم هدفمند روی کشور فعال است؟ (هوک‌های اقتصادی، سبک و تک‌کوئری)"""
    conn = get_connection()
    try:
        r = conn.execute(
            "SELECT 1 FROM un_targeted_sanctions WHERE country_id = ? AND sanction_key = ?",
            (int(country_id), str(sanction_key))).fetchone()
        return bool(r)
    finally:
        conn.close()


def get_all_active_targeted_sanctions(limit: int = 200) -> list[dict]:
    """همه‌ی تحریم‌های هدفمند فعال روی همه‌ی کشورها — برای پنل سازمان ملل."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT s.*, c.name AS country_name, c.flag AS country_flag,
                   c.player_id, c.country_key
            FROM un_targeted_sanctions s JOIN countries c ON c.id = s.country_id
            ORDER BY s.created_at DESC LIMIT ?
            """,
            (max(1, min(500, int(limit))),)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_targeted_sanctions(country_id: int) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM un_targeted_sanctions WHERE country_id = ? ORDER BY created_at",
            (int(country_id),)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def apply_targeted_sanction(country_id: int, sanction_key: str, reason: str = "",
                            imposed_by: int = 0) -> tuple[bool, str]:
    """اعمال یک تحریم هدفمند (تک‌نوع). اگر از قبل فعال باشد کاری نمی‌کند."""
    spec = config.UN_TARGETED_SANCTIONS.get(sanction_key)
    if not spec:
        return False, "نوع تحریم نامعتبر است."
    label = spec["label"]
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute(
                "INSERT OR IGNORE INTO un_targeted_sanctions"
                " (country_id, sanction_key, reason, imposed_by, created_at)"
                " VALUES (?, ?, ?, ?, ?)",
                (int(country_id), str(sanction_key), str(reason or "")[:400],
                 int(imposed_by),
                 datetime.datetime.now(datetime.timezone.utc).isoformat()))
            ok = cur.rowcount > 0
    finally:
        conn.close()
    if ok:
        add_transaction(int(country_id), f"un_sanction_{sanction_key}",
                        f"🚫 {label} سازمان ملل علیه کشور اعمال شد."
                        + (f" دلیل: {reason}" if reason else ""), 0)
        try:
            add_log(f"admin:{imposed_by}", "un_sanction_apply",
                    f"{sanction_key} on country_id={int(country_id)}"
                    + (f" | reason={reason}" if reason else ""))
        except Exception:
            pass
        return True, f"{label} اعمال شد."
    return False, f"{label} از قبل فعال است."


def remove_targeted_sanction(country_id: int, sanction_key: str,
                             removed_by: int = 0) -> tuple[bool, str]:
    """لغو یک تحریم هدفمند."""
    spec = config.UN_TARGETED_SANCTIONS.get(sanction_key)
    if not spec:
        return False, "نوع تحریم نامعتبر است."
    label = spec["label"]
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute(
                "DELETE FROM un_targeted_sanctions WHERE country_id = ? AND sanction_key = ?",
                (int(country_id), str(sanction_key)))
            ok = cur.rowcount > 0
    finally:
        conn.close()
    if ok:
        add_transaction(int(country_id), f"un_unsanction_{sanction_key}",
                        f"✅ {label} سازمان ملل لغو شد.", 0)
        try:
            add_log(f"admin:{removed_by}", "un_sanction_remove",
                    f"{sanction_key} on country_id={int(country_id)}")
        except Exception:
            pass
        return True, f"{label} لغو شد."
    return False, f"{label} فعال نبود."


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
    # شمارنده‌ی ترانزیت روزانه موقع پیشنهاد +۱ می‌شود (ضداسپم)؛
    # رد/لغو/شکستِ اجرا آن را آزاد می‌کند (−۱).
    cur.execute("""
        INSERT INTO trade_daily_modes (country_id, day, mode, count) VALUES (?, ?, ?, 1)
        ON CONFLICT(country_id, day, mode) DO UPDATE SET count = count + 1
    """, (proposer_id, now_str[:10], transport_mode))
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


def reject_trade_contract(contract_id: int, actor_country_id: int) -> tuple[bool, str]:
    """رد امن قرارداد فقط توسط کشور دریافت‌کننده و فقط در وضعیت معلق."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT proposer_id, recipient_id, transport_mode, created_at, status FROM trade_contracts WHERE id = ?", (contract_id,))
            row = cur.fetchone()
            if not row:
                return False, "قرارداد یافت نشد."
            if row["recipient_id"] != actor_country_id:
                return False, "فقط کشور دریافت‌کننده قرارداد می‌تواند آن را رد کند."
            if row["status"] != "pending":
                return False, "این قرارداد قبلاً تعیین تکلیف شده است."
            cur.execute("UPDATE trade_contracts SET status = 'rejected' WHERE id = ? AND status = 'pending'", (contract_id,))
            if cur.rowcount != 1:
                return False, "این قرارداد قبلاً تعیین تکلیف شده است."

            # آزادسازی سهمیه روزانه پیشنهاددهنده در صورت رد
            c = dict(row)
            if c.get("proposer_id") and c.get("transport_mode") and c.get("created_at"):
                cur.execute("""
                    INSERT INTO trade_daily_modes (country_id, day, mode, count) VALUES (?, ?, ?, 0)
                    ON CONFLICT(country_id, day, mode) DO UPDATE SET count = MAX(0, count - 1)
                """, (c["proposer_id"], c["created_at"][:10], c["transport_mode"]))
        return True, "قرارداد با موفقیت رد شد."
    except Exception as e:
        return False, f"خطا در رد قرارداد: {e}"


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

            # آزادسازی سهمیه روزانه پیشنهاددهنده در صورت لغو
            if c.get("transport_mode") and c.get("created_at"):
                cur.execute("""
                    INSERT INTO trade_daily_modes (country_id, day, mode, count) VALUES (?, ?, ?, 0)
                    ON CONFLICT(country_id, day, mode) DO UPDATE SET count = MAX(0, count - 1)
                """, (proposer_id, c["created_at"][:10], c["transport_mode"]))
        return True, "پیشنهاد قرارداد تجاری با موفقیت لغو و ابطال گردید."
    except Exception as e:
        return False, f"خطا در لغو قرارداد: {e}"


def execute_trade_contract_transaction(contract_id: int, actor_country_id: int | None = None) -> tuple[bool, str]:
    """اجرای اتمیک قرارداد؛ در مسیر بازیکن فقط کشور دریافت‌کننده مجاز است."""
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

            if actor_country_id is not None and actor_country_id != r_id:
                return False, "فقط کشور دریافت‌کننده قرارداد می‌تواند آن را قبول کند."
            if p_id == r_id:
                return False, "قرارداد بین یک کشور با خودش معتبر نیست."

            trade_resource_cols = {
                "treasury": "treasury",
                "gold": "gold",
                "oil": "oil_reserves",
                "grain": "grain",
                "iron_ore": "iron_ore",
                "microchips": "microchips",
                "uranium_ore": "uranium_ore",
                "nuclear_fuel": "nuclear_fuel",
            }
            off_type = c.get("offered_type")
            req_type = c.get("requested_type")
            off_key = c.get("offered_key")
            t_payer = c.get("transport_payer") or "seller"
            t_mode = c.get("transport_mode") or "sea"
            try:
                off_amt = int(c.get("offered_amount"))
                req_amt = int(c.get("requested_amount"))
                t_cost = int(c.get("transport_cost") or 0)
            except (TypeError, ValueError):
                return False, "اطلاعات عددی قرارداد نامعتبر است."

            if off_type != "military_asset" and off_type not in trade_resource_cols:
                return False, "نوع کالای پیشنهادی قرارداد نامعتبر است."
            if req_type not in trade_resource_cols:
                return False, "نوع کالای درخواستی قرارداد نامعتبر است."
            if off_type == "military_asset" and not off_key:
                return False, "تجهیز نظامی قرارداد مشخص نشده است."
            if off_amt <= 0 or req_amt < 0 or t_cost < 0:
                return False, "مقادیر قرارداد باید معتبر و غیرمنفی باشند."
            if t_payer not in {"seller", "buyer"}:
                return False, "پرداخت‌کننده هزینه ترانزیت نامعتبر است."
            if t_mode not in {"sea", "land", "air"}:
                return False, "روش ترابری قرارداد نامعتبر است."

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
            _bilateral_sanctioned = bool(rel_row and rel_row["status"] == "sanctioned")
            _smuggled = bool(c.get("is_smuggled"))
            if _bilateral_sanctioned and not _smuggled:
                return False, "امکان انعقاد قرارداد یا انتقال تجهیزات با کشور تحریم‌شده وجود ندارد."

            # 🚫 تحریم‌های هدفمند سازمان ملل
            # استثنا: قاچاق سلاح سبک بازار سیاه زیر تحریم تسلیحاتی باز می‌ماند
            # (ریسک رهگیری تشدیدشده در بخش انتقال نظامی). تحریم تجاری مطلق است.
            if has_targeted_sanction(p_id, "trade_embargo") or has_targeted_sanction(r_id, "trade_embargo"):
                return False, "🚫 **تحریم تجاری سازمان ملل:** انعقاد قرارداد با کشور تحت تحریم تجاری ممنوع است."
            _un_arms_embargo = off_type == "military_asset" and has_targeted_sanction(r_id, "arms_embargo")
            if _un_arms_embargo and not _smuggled:
                return False, ("🚫 **تحریم تسلیحاتی سازمان ملل:** انتقال رسمی تجهیز نظامی به کشور تحت تحریم ممنوع است.\n\n"
                               "💡 فقط قاچاق سلاح سبک از بازار سیاه ممکن است (۱.۵ برابر ترانزیت + ریسک رهگیری تشدیدشده).")

            # عوارض تنگه‌ها فقط بعد از موفقیت همه اعتبارسنجی‌ها کسر می‌شود؛
            # تا یک قرارداد نامعتبر باعث پرداخت یک‌طرفه عوارض نشود.
            strait_tolls = []
            if t_mode == "sea":
                p_c_key = p_c.get("country_key")
                r_c_key = r_c.get("country_key")
                if not has_open_sea_access(p_c_key) or not has_open_sea_access(r_c_key):
                    no_sea_c = p_c if not has_open_sea_access(p_c_key) else r_c
                    return False, f"⚓ **امکان ترابری دریایی وجود ندارد:** کشور {no_sea_c['flag']} **{no_sea_c['name']}** محصور در خشکی است و به آب‌های آزاد دسترسی ساحلی ندارد. لطفاً این معاهده با ترابری هوایی یا زمینی صادر شود."

                if is_country_blockaded(p_id) or is_country_blockaded(r_id):
                    return False, "⚓ **امکان اجرای معاهده از طریق ترابری دریایی وجود ندارد:** خطوط مواصلاتی دریایی یکی از دو کشور تحت محاصره کامل دریایی است. لطفا برای این معاهده از ترابری هوایی یا زمینی استفاده بفرمایید."

                # Check Strait Blockades & Tolls based on realistic geographic maritime route
                analysis = get_trade_route_strait_analysis(p_c_key, r_c_key)
                if analysis["is_blocked"]:
                    blocked_str = "، ".join([f"{s['name']} (توسط {s['owner_flag']} {s['owner_name']})" for s in analysis["blocked_straits"]])
                    return False, f"⛔ **امکان ترانزیت دریایی وجود ندارد:** {blocked_str} مسدود گردیده است!\n\n💡 برای عبور موفق از این مسیر، باید معاهده با **ترابری هوایی** یا **زمینی** صادر شود."

                for t_entry in analysis["toll_straits"]:
                    owner_c = t_entry["owner_c"]
                    st_toll = t_entry["toll_amount"]
                    if owner_c and st_toll > 0:
                        strait_tolls.append((owner_c, st_toll, t_entry["name"]))

            # ترابری زمینی: وجود مسیر خشکی پیوسته (مرز مستقیم یا ترانزیت خاکی) الزامی است
            if t_mode == "land":
                p_land_key = p_c.get("country_key")
                r_land_key = r_c.get("country_key")
                if not has_land_trade_route(p_land_key, r_land_key):
                    return False, (
                        f"🚛 **امکان ترابری زمینی وجود ندارد:** هیچ مسیر خشکی پیوسته‌ای (مرز مشترک یا ترانزیت زمینی) بین "
                        f"{p_c['flag']} **{p_c['name']}** و {r_c['flag']} **{r_c['name']}** وجود ندارد.\n"
                        "لطفاً این معاهده با ترابری دریایی یا هوایی صادر شود."
                    )

            # Check capacity limits for commodity transport
            t_limits = getattr(config, "TRANSPORT_CAPACITY_LIMITS", {}).get(t_mode, {}).get("limits", {})
            if off_type in t_limits and off_amt > t_limits[off_type]:
                t_name = getattr(config, "TRANSPORT_CAPACITY_LIMITS", {}).get(t_mode, {}).get("name", t_mode)
                return False, f"⛔ **مازاد ظرفیت بارگیری ناوگان ({t_name}):** حداکثر ظرفیت قابل انتقال در هر محموله برابر با **{t_limits[off_type]:,} واحد** است."

            # ضدتقلب: سقف محموله‌های خروجی روزانه
            if transfer_weight_enabled():
                used, cap = transfer_daily_budget(p_id)
                if used >= cap:
                    return False, (
                        f"⛔ **سقف ارسال روزانه پر شده است:** امروز {used}/{cap} محموله ارسال کرده‌اید. "
                        f"فردا دوباره می‌توانید معاهده صادر کنید."
                    )

            p_extra_cost = t_cost if t_payer == "seller" else 0
            r_extra_cost = t_cost if t_payer == "buyer" else 0
            strait_toll_total = sum(toll[1] for toll in strait_tolls)
            toll_payer_id = p_id if t_payer == "seller" else r_id

            col_map = {"treasury": "treasury", "gold": "gold", "oil": "oil_reserves", "grain": "grain", "iron_ore": "iron_ore", "microchips": "microchips", "uranium_ore": "uranium_ore", "nuclear_fuel": "nuclear_fuel", "vaccine_doses": "vaccine_doses"}

            # Handle Military Asset Transfer
            if off_type == "military_asset":
                cur.execute("SELECT * FROM country_assets WHERE country_id = ? AND equipment_key = ?", (p_id, off_key))
                asset_row = cur.fetchone()
                if not asset_row or asset_row["amount"] < off_amt:
                    return False, f"کشور پیشنهاددهنده ({p_c['name']}) موجودی کافی از این تجهیز برای انتقال ندارد."

                asset_dict = dict(asset_row)

                # ضدتقلب: سقف وزن تجهیزات در هر محموله، وابسته به روش ترابری
                if transfer_weight_enabled():
                    weight = equipment_weight_points(asset_dict.get("category", ""), off_amt)
                    max_w = transfer_weight_capacity(t_mode)
                    if weight > max_w:
                        unit = getattr(config, "ASSET_CATEGORIES", {}).get(
                            asset_dict.get("category", ""), ("", "واحد"))[1]
                        max_units = max_equipment_per_shipment(asset_dict.get("category", ""), t_mode)
                        mode_name = getattr(config, "TRANSPORT_CAPACITY_LIMITS", {}).get(t_mode, {}).get("name", t_mode)
                        return False, (
                            f"⛔ **مازاد بر ظرفیت حمل ({mode_name}):** این محموله {off_amt:,} {unit} "
                            f"({weight:.0f} نقطه) از سقف {max_w} نقطه‌ی هر محموله بیشتر است. "
                            f"با این روش ترابری حداکثر {max_units:,} {unit} در یک محموله می‌فرستید؛ "
                            f"محموله را کوچک‌تر کنید."
                        )

                r_total_needed = req_amt + r_extra_cost + (strait_toll_total if t_payer == "buyer" else 0)
                if (r_c["treasury"] or 0) < r_total_needed:
                    return False, f"کشور خریدار ({r_c['name']}) موجودی کافی در خزانه برای پرداخت قیمت و ترانزیت ندارد."

                seller_route_cost = p_extra_cost + (strait_toll_total if t_payer == "seller" else 0)
                if (p_c["treasury"] or 0) < seller_route_cost:
                    return False, f"کشور فروشنده ({p_c['name']}) موجودی کافی برای پرداخت ترانزیت و عوارض تنگه‌ها ندارد."

                for owner_c, toll_amount, strait_name in strait_tolls:
                    cur.execute("UPDATE countries SET treasury = treasury - ? WHERE id = ?", (toll_amount, toll_payer_id))
                    cur.execute("UPDATE countries SET treasury = treasury + ? WHERE id = ?", (toll_amount, owner_c["id"]))
                    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
                    cur.execute(
                        "INSERT INTO transactions (country_id, type, description, amount, created_at) VALUES (?, 'strait_toll', ?, ?, ?)",
                        (owner_c["id"], f"دریافت عوارض ترانزیت {strait_name} از معاهده {p_c['name']} و {r_c['name']}", toll_amount, now_str),
                    )

                is_smuggled = bool(c.get("is_smuggled"))
                delivered_amt = off_amt
                lost_amt = 0
                is_intercepted = False
                _un_violation = False

                # 🕵️ گیت سمت سرور: قاچاق فقط برای سلاح سبک (ضد callback جعلی)
                if is_smuggled and not config.is_light_weapon(
                        asset_dict.get("category", ""), off_key, asset_dict.get("equipment_name", "")):
                    return False, ("🚫 **قاچاق فقط برای سلاح‌های سبک ممکن است:** پلتفرم‌های سنگین (تانک، جنگنده، ناو، "
                                   "موشک بالستیک) باید از کانال رسمی با مجوز کشور سازنده منتقل شوند.")

                if is_smuggled:
                    import random
                    # ریسک ردگیری و توقیف نیمی از محموله در مرز:
                    # پایه ۲۵٪ — نقض تحریم تسلیحاتی سازمان ملل ۴۰٪ — تحریم دوجانبه ۳۵٪
                    _risk = 0.25
                    if _un_arms_embargo:
                        _risk = 0.40
                        _un_violation = True
                    elif _bilateral_sanctioned:
                        _risk = 0.35
                    if random.random() < _risk:
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

                # ثبت در دفترچه‌ی انتقالات + شمارنده‌ی روزانه (ضدتقلب)
                cur.execute(
                    "INSERT INTO transfer_log (from_country_id, to_country_id, kind, item_key, item_name, "
                    "qty, money_paid, created_at, status) VALUES (?, ?, 'trade_asset', ?, ?, ?, ?, ?, 'active')",
                    (p_id, r_id, off_key, asset_dict["equipment_name"], off_amt, req_amt, now_str),
                )
                cur.execute(
                    "INSERT INTO transfer_daily (country_id, day, count) VALUES (?, ?, 1) "
                    "ON CONFLICT(country_id, day) DO UPDATE SET count = count + 1",
                    (p_id, now_str[:10]),
                )

                if is_intercepted:
                    return True, f"INTERCEPTED:{lost_amt}:{delivered_amt}:{asset_dict['equipment_name']}:{c.get('origin_country_key') or ''}:{1 if _un_violation else 0}"
                elif is_smuggled:
                    return True, f"SMUGGLED_SAFE:{delivered_amt}:{asset_dict['equipment_name']}"
                else:
                    return True, "معاهده انتقال تسلیحات نظامی با موفقیت اجرا شد."

            p_off_col = col_map[off_type]
            r_req_col = col_map[req_type]
            seller_route_cost = p_extra_cost + (strait_toll_total if t_payer == "seller" else 0)
            buyer_route_cost = r_extra_cost + (strait_toll_total if t_payer == "buyer" else 0)

            p_avail = (p_c[p_off_col] or 0) - (seller_route_cost if p_off_col == "treasury" else 0)
            if p_avail < off_amt:
                return False, f"طرف پیشنهاددهنده ({p_c['name']}) موجودی کافی برای اجرای قرارداد ندارد."
            if p_off_col != "treasury" and (p_c["treasury"] or 0) < seller_route_cost:
                return False, f"طرف پیشنهاددهنده ({p_c['name']}) موجودی کافی برای پرداخت هزینه ترانزیت و عوارض تنگه‌ها ندارد."

            r_avail = (r_c[r_req_col] or 0) - (buyer_route_cost if r_req_col == "treasury" else 0)
            if r_avail < req_amt:
                return False, f"طرف قبول‌کننده ({r_c['name']}) موجودی کافی برای اجرای قرارداد ندارد."
            if r_req_col != "treasury" and (r_c["treasury"] or 0) < buyer_route_cost:
                return False, f"طرف قبول‌کننده ({r_c['name']}) موجودی کافی برای پرداخت هزینه ترانزیت ندارد."

            for owner_c, toll_amount, strait_name in strait_tolls:
                cur.execute("UPDATE countries SET treasury = treasury - ? WHERE id = ?", (toll_amount, toll_payer_id))
                cur.execute("UPDATE countries SET treasury = treasury + ? WHERE id = ?", (toll_amount, owner_c["id"]))
                now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
                cur.execute(
                    "INSERT INTO transactions (country_id, type, description, amount, created_at) VALUES (?, 'strait_toll', ?, ?, ?)",
                    (owner_c["id"], f"دریافت عوارض ترانزیت {strait_name} از معاهده {p_c['name']} و {r_c['name']}", toll_amount, now_str),
                )

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

            # ثبت در دفترچه‌ی انتقالات + شمارنده‌ی روزانه (ضدتقلب)
            cur.execute(
                "INSERT INTO transfer_log (from_country_id, to_country_id, kind, resource_type, "
                "amount, money_paid, created_at, status) VALUES (?, ?, 'trade_resource', ?, ?, ?, ?, 'active')",
                (p_id, r_id, off_type, off_amt, req_amt, now_str),
            )
            cur.execute(
                "INSERT INTO transfer_daily (country_id, day, count) VALUES (?, ?, 1) "
                "ON CONFLICT(country_id, day) DO UPDATE SET count = count + 1",
                (p_id, now_str[:10]),
            )

            return True, "قرارداد تجاری با موفقیت اجرا شد."
    except Exception as e:
        return False, f"خطا در اجرای قرارداد: {e}"


def execute_foreign_aid_transaction(donor_id: int, recipient_id: int, resource_type: str, amount: int,
                                    transport_mode: str = "sea", passage_won: bool = False) -> tuple[bool, str]:
    """انتقال اتمیک کمک خارجی با اعتبارسنجی کامل ورودی‌ها.

    passage_won=True یعنی قرعه‌ی عبور از محاصره/تنگه قبلاً برده شده و نباید
    دوباره سد راه شود. بدون این، محموله‌ای که در قرعه پیروز شده بود دوباره
    با پیام «مسیر مسدود است» رد می‌شد.
    """
    resource_cols = {
        "treasury": "treasury",
        "gold": "gold",
        "oil": "oil_reserves",
        "grain": "grain",
        "iron_ore": "iron_ore",
        "microchips": "microchips",
        "vaccine_doses": "vaccine_doses",
        "uranium_ore": "uranium_ore",
        "nuclear_fuel": "nuclear_fuel",
    }
    valid_transport_modes = {"sea", "land", "air", "caspian"}

    if donor_id == recipient_id:
        return False, "ارسال کمک به همان کشور امکان‌پذیر نیست."
    if resource_type not in resource_cols:
        return False, "نوع منبع کمک نامعتبر است."
    if transport_mode not in valid_transport_modes:
        return False, "روش ترابری نامعتبر است."
    if isinstance(amount, bool) or not isinstance(amount, int) or amount <= 0:
        return False, "مقدار کمک باید یک عدد صحیح بزرگ‌تر از صفر باشد."

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

            cost_map = {"air": 2_000_000, "land": 1_000_000, "sea": 300_000,
                        "caspian": config.TRANSPORT_CAPACITY_LIMITS["caspian"]["cost"]}
            t_cost = cost_map.get(transport_mode, 300_000)

            # بررسی سقف ظرفیت بارگیری برای روش ترابری انتخاب‌شده
            t_limits = getattr(config, "TRANSPORT_CAPACITY_LIMITS", {}).get(transport_mode, {}).get("limits", {})
            max_cap = 20_000_000 if resource_type == "treasury" else t_limits.get(resource_type, 100_000)
            if amount > max_cap:
                t_name = getattr(config, "TRANSPORT_CAPACITY_LIMITS", {}).get(transport_mode, {}).get("name", transport_mode)
                return False, f"⛔ **مازاد بر ظرفیت بارگیری ناوگان ({t_name}):** حداکثر سقف ارسال برای این کالا برابر با **{max_cap:,} واحد** در هر محموله است."

            # 🌊 ترابری خزر: فقط بین کشورهای حاشیه‌ی خزر، ولی مصون از محاصره و تنگه
            if transport_mode == "caspian":
                if not caspian_route_available(d_key, r_key):
                    return False, (
                        "🌊 **مسیر دریای خزر در دسترس نیست:** این مسیر فقط بین کشورهای "
                        "حاشیه‌ی خزر (ایران، روسیه، قزاقستان، ترکمنستان، آذربایجان) برقرار است."
                    )

            # بررسی دسترسی دریایی و محاصره در ترابری دریایی
            strait_tolls = []
            if transport_mode == "sea":
                if not has_open_sea_access(d_key) or not has_open_sea_access(r_key):
                    no_sea = d_c if not has_open_sea_access(d_key) else r_c
                    return False, f"⚓ **ترابری دریایی ممکن نیست:** کشور {no_sea['flag']} {no_sea['name']} محصور در خشکی است. لطفاً از ترابری هوایی یا زمینی استفاده فرمایید."

                if not passage_won and (is_country_blockaded(donor_id) or is_country_blockaded(recipient_id)):
                    return False, "⚓ **ترابری دریایی مسدود است:** خطوط کشتیرانی یکی از دو کشور تحت محاصره دریایی است. لطفاً از ترابری هوایی یا زمینی استفاده فرمایید."

                # بررسی انسداد و عوارض تنگه‌ها
                analysis = get_trade_route_strait_analysis(d_key, r_key)
                if analysis["is_blocked"] and not passage_won:
                    blocked_str = "، ".join([f"{s['name']} (توسط {s['owner_flag']} {s['owner_name']})" for s in analysis["blocked_straits"]])
                    return False, f"⛔ **مسیر ترانزیت دریایی مسدود است:** {blocked_str} مسدود گردیده است. از ترابری هوایی یا زمینی استفاده کنید."

                for t_entry in analysis["toll_straits"]:
                    owner_c = t_entry["owner_c"]
                    st_toll = t_entry["toll_amount"]
                    if owner_c and st_toll > 0:
                        strait_tolls.append((owner_c, st_toll, t_entry["name"]))

            # ترابری زمینی: وجود مسیر خشکی پیوسته (مرز مستقیم یا ترانزیت خاکی) الزامی است
            if transport_mode == "land":
                if not has_land_trade_route(d_key, r_key):
                    return False, (
                        f"🚛 **ترابری زمینی ممکن نیست:** مسیر خشکی پیوسته‌ای (مرز مشترک یا ترانزیت زمینی) بین "
                        f"{d_c['flag']} {d_c['name']} و {r_c['flag']} {r_c['name']} وجود ندارد. "
                        "لطفاً از ترابری دریایی یا هوایی استفاده فرمایید."
                    )

            strait_toll_total = sum(t[1] for t in strait_tolls)
            total_transit_cost = t_cost + strait_toll_total

            # ضدتقلب: سقف محموله‌های خروجی روزانه
            if transfer_weight_enabled():
                used, cap = transfer_daily_budget(donor_id)
                if used >= cap:
                    return False, (
                        f"⛔ **سقف ارسال روزانه پر شده است:** امروز {used}/{cap} محموله ارسال کرده‌اید. "
                        f"فردا دوباره می‌توانید کمک ارسال کنید."
                    )

            # بررسی موجودی کالا و هزینه ترانزیت
            col_name = resource_cols[resource_type]

            donor_money_avail = (d_c["treasury"] or 0) - (amount if resource_type == "treasury" else 0)
            if donor_money_avail < total_transit_cost:
                return False, f"💵 **کسری بودجه برای پرداخت هزینه ترانزیت:** هزینه حمل‌ونقل و ترانزیت این محموله برابر با **{format_money(total_transit_cost)}** است و موجودی خزانه شما کافی نیست."

            if (d_c[col_name] or 0) < amount:
                return False, f"موجودی {resource_type} کشور شما برای ارسال این کمک کافی نیست."

            # کسر هزینه ترانزیت از اهداکننده
            if t_cost > 0:
                cur.execute("UPDATE countries SET treasury = treasury - ? WHERE id = ?", (t_cost, donor_id))

            for owner_c, toll_amount, strait_name in strait_tolls:
                cur.execute("UPDATE countries SET treasury = treasury - ? WHERE id = ?", (toll_amount, donor_id))
                cur.execute("UPDATE countries SET treasury = treasury + ? WHERE id = ?", (toll_amount, owner_c["id"]))
                now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
                cur.execute(
                    "INSERT INTO transactions (country_id, type, description, amount, created_at) VALUES (?, 'strait_toll', ?, ?, ?)",
                    (owner_c["id"], f"دریافت عوارض ترانزیت {strait_name} از محموله کمک خارجی {d_c['name']} به {r_c['name']}", toll_amount, now_str)
                )

            cur.execute(f"UPDATE countries SET {col_name} = {col_name} - ? WHERE id = ?", (amount, donor_id))
            cur.execute(f"UPDATE countries SET {col_name} = {col_name} + ? WHERE id = ?", (amount, recipient_id))

            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute("""
                INSERT INTO transactions (country_id, type, description, amount, created_at)
                VALUES (?, 'aid_out', ?, ?, ?)
            """, (donor_id, f"ارسال کمک خارجی ({transport_mode}) به {r_c['name']} (هزینه ترانزیت: {format_money(total_transit_cost)})", -amount if resource_type == "treasury" else 0, now_str))
            cur.execute("""
                INSERT INTO transactions (country_id, type, description, amount, created_at)
                VALUES (?, 'aid_in', ?, ?, ?)
            """, (recipient_id, f"دریافت کمک خارجی ({transport_mode}) از {d_c['name']}", amount if resource_type == "treasury" else 0, now_str))

            # ثبت در دفترچه‌ی انتقالات (برای برگشت در صورت حذف کشور)
            cur.execute(
                "INSERT INTO transfer_log (from_country_id, to_country_id, kind, resource_type, "
                "amount, money_paid, created_at, status) VALUES (?, ?, 'aid', ?, ?, 0, ?, 'active')",
                (donor_id, recipient_id, resource_type, amount, now_str),
            )
            cur.execute(
                "INSERT INTO transfer_daily (country_id, day, count) VALUES (?, ?, 1) "
                "ON CONFLICT(country_id, day) DO UPDATE SET count = count + 1",
                (donor_id, now_str[:10]),
            )

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


# ---------- تخفیف فروشگاه ویژه (VIP) ----------

def get_vip_discount(item_key: str) -> int:
    """درصد تخفیف جاری یک آیتم فروشگاه ویژه؛ ۰ یعنی بدون تخفیف."""
    if not item_key:
        return 0
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT discount_pct FROM vip_discounts WHERE item_key = ?", (item_key,)
        ).fetchone()
        return int(row["discount_pct"] or 0) if row else 0
    except Exception:
        return 0
    finally:
        conn.close()


def set_vip_discount(item_key: str, discount_pct: int):
    """تنظیم درصد تخفیف یک آیتم؛ ۰ یعنی حذف تخفیف."""
    if not item_key:
        return
    discount_pct = max(0, min(90, int(discount_pct or 0)))
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO vip_discounts (item_key, discount_pct, updated_at) VALUES (?, ?, ?) "
                "ON CONFLICT(item_key) DO UPDATE SET discount_pct = excluded.discount_pct, "
                "updated_at = excluded.updated_at",
                (item_key, discount_pct, datetime.datetime.now(datetime.timezone.utc).isoformat()),
            )
    finally:
        conn.close()


def get_all_vip_discounts() -> dict[str, int]:
    """همه‌ی تخفیف‌ها: {item_key: percent}. فقط آیتم‌های دارای تخفیف."""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT item_key, discount_pct FROM vip_discounts").fetchall()
        return {row["item_key"]: int(row["discount_pct"] or 0) for row in rows}
    except Exception:
        return {}
    finally:
        conn.close()


# ---------- دفترچه‌ی انتقالات و ضدتقلب (وزن/ظرفیت/برگشت) ----------

def transfer_weight_enabled() -> bool:
    return get_setting(config.TRANSFER_WEIGHT_SETTING_KEY, "1") == "1"


def set_transfer_weight_enabled(value: bool):
    set_setting(config.TRANSFER_WEIGHT_SETTING_KEY, "1" if value else "0")


def equipment_weight_points(category: str, qty: int) -> float:
    """نقطه وزن یک محموله تجهیزات بر اساس دسته (مدل سبک)."""
    per = getattr(config, "EQUIPMENT_WEIGHT_POINTS", {}).get(category or "", 1.0)
    return float(per) * max(0, int(qty or 0))


def transfer_weight_capacity(mode: str) -> int:
    """سقف نقطه‌ی وزن هر محموله برای یک روش ترابری (sea/land/air)."""
    caps = getattr(config, "TRANSFER_WEIGHT_CAPACITY", {})
    return int(caps.get(mode, caps.get("sea", 150)) or 0)


def max_equipment_per_shipment(category: str, mode: str) -> int:
    """حداکثر تعداد قابل ارسال از یک تجهیز در یک محموله با این روش ترابری."""
    cap = transfer_weight_capacity(mode)
    per = getattr(config, "EQUIPMENT_WEIGHT_POINTS", {}).get(category or "", 1.0)
    if per <= 0:
        return cap
    # floor با تلورانس اعشاری: ۱۰۰۰/۱۵ = ۶۶، و ۴۰/۰.۴ = ۱۰۰ (نه ۹۹)
    return int((cap + 1e-9) / per)


def get_transfer_day_count(country_id: int, day: str | None = None) -> int:
    day = day or datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT count FROM transfer_daily WHERE country_id = ? AND day = ?",
            (country_id, day),
        ).fetchone()
        return int(row["count"] or 0) if row else 0
    except Exception:
        return 0
    finally:
        conn.close()


def bump_transfer_day_count(country_id: int, day: str | None = None):
    day = day or datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO transfer_daily (country_id, day, count) VALUES (?, ?, 1) "
                "ON CONFLICT(country_id, day) DO UPDATE SET count = count + 1",
                (country_id, day),
            )
    finally:
        conn.close()


def free_trade_slot_for_contract(contract_id: int) -> None:
    """آزادسازی سهمیه‌ی روزانه‌ی ترانزیت قراردادی که در لحظه‌ی اجرا رد شد
    (هم‌سنگ با رد/لغو؛ وگرنه سهمیه‌ی پیشنهاددهنده بدون جابجایی واقعی می‌سوزد)."""
    c = get_trade_contract(contract_id)
    if not c:
        return
    bump_trade_mode_day_count(c["proposer_id"], c.get("transport_mode") or "sea", delta=-1)


def shipment_capacity(off_type: str, mode: str) -> tuple[int, str]:
    """(حداکثر واحد قابل حمل در هر محموله، نام روش) برای نمایش و ولیدیشن زودهنگام."""
    spec = getattr(config, "TRANSPORT_CAPACITY_LIMITS", {}).get(mode, {})
    limits = spec.get("limits", {})
    max_cap = 20_000_000 if off_type == "treasury" else int(limits.get(off_type, 100_000))
    return max_cap, spec.get("name", mode)


def transfer_daily_budget(country_id: int) -> tuple[int, int]:
    """(استفاده‌شده, سقف) محموله‌های خروجی امروز — اورراید مالک بر کانفیگ مقدم است."""
    used = get_transfer_day_count(country_id)
    ov = get_trade_limit_override(country_id).get("total")
    cap = int(ov) if ov is not None else int(getattr(config, "TRANSFER_DAILY_SHIPMENTS", 3) or 0)
    return used, cap


# ---------- سقف تجارت روزانه بر اساس زیرساخت (دریایی/هوایی/زمینی) ----------

TRADE_TRANSPORT_MODES = ("sea", "caspian", "land", "air")
TRADE_LIMIT_MIN, TRADE_LIMIT_MAX = 0, 50


def get_trade_limit_override(country_id: int) -> dict:
    """سقف دستی این کشور برای هر روش ترابری؛ {} یعنی همه از فرمول زیرساخت."""
    c = get_country_by_id(country_id)
    raw = (c.get("trade_limit_override") or "") if c else ""
    try:
        data = json.loads(raw) if raw else {}
        allowed = set(TRADE_TRANSPORT_MODES) | {"total"}   # total = کل محموله‌های خروجی روزانه
        return {k: int(v) for k, v in data.items()
                if k in allowed and TRADE_LIMIT_MIN <= int(v) <= TRADE_LIMIT_MAX}
    except Exception:
        return {}


def set_trade_limit_override(country_id: int, mode: str, value) -> bool:
    """تنظیم سقف دستی یک روش (int در بازه ۰..۵۰) یا حذف آن (value=None → فرمولی)."""
    if mode not in TRADE_TRANSPORT_MODES and mode != "total":
        return False
    ov = get_trade_limit_override(country_id)
    if value is None:
        ov.pop(mode, None)
    else:
        ov[mode] = max(TRADE_LIMIT_MIN, min(TRADE_LIMIT_MAX, int(value)))
    update_country_field(country_id, "trade_limit_override",
                         json.dumps(ov, ensure_ascii=False))
    return True


def get_trade_mode_daily_limit(country_id: int, mode: str) -> int:
    """محاسبه سقف مجاز تجارت روزانه بر اساس زیرساخت‌های احداث‌شده.

    * اگر مالک برای این کشور سقف دستی ثبت کرده باشد، همان ملاک است.
    * سقف پایه برای کشور فابریک: ۲ تجارت در روز برای هر روش (دریایی، هوایی، زمینی)
    * دریایی (sea): ۲ + تعداد بنادر تجاری و استراتژیک (port + mega_port)
    * هوایی (air): ۲ + تعداد فرودگاه‌های بین‌المللی (airport)
    * زمینی (land): ۲ + تعداد بزرگراه‌ها/جاده‌ها (highway)
    * خزر (caspian): ۱ + تعداد بنادر — دریای بسته با ناوگان کوچک‌تر
    """
    ov = get_trade_limit_override(country_id)
    if mode in ov:
        return int(ov[mode])
    base_cap = 2
    eq = get_equipment(country_id)
    if mode == "sea":
        return base_cap + int(eq.get("port", 0) or 0) + int(eq.get("mega_port", 0) or 0)
    elif mode == "air":
        return base_cap + int(eq.get("airport", 0) or 0)
    elif mode == "land":
        return base_cap + int(eq.get("highway", 0) or 0)
    elif mode == "caspian":
        # خزر سقف کمتری دارد چون ناوگان دریاچه‌ای کوچک است
        return max(1, 1 + int(eq.get("port", 0) or 0))
    return base_cap


def get_trade_mode_day_count(country_id: int, mode: str, day: str | None = None) -> int:
    """تعداد تجارت‌های انجام‌شده در روز جاری با روش ترابری مشخص."""
    day = day or datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT count FROM trade_daily_modes WHERE country_id = ? AND day = ? AND mode = ?",
            (country_id, day, mode),
        ).fetchone()
        return int(row["count"] or 0) if row else 0
    except Exception:
        return 0
    finally:
        conn.close()


def bump_trade_mode_day_count(country_id: int, mode: str, day: str | None = None, delta: int = 1):
    """افزایش یا کاهش شمارنده تجارت روزانه یک روش ترابری."""
    day = day or datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO trade_daily_modes (country_id, day, mode, count) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(country_id, day, mode) DO UPDATE SET count = MAX(0, count + ?)",
                (country_id, day, mode, max(0, delta), delta),
            )
    finally:
        conn.close()


def get_trade_mode_budget(country_id: int, mode: str, day: str | None = None) -> tuple[int, int]:
    """(مصرف‌شده, سقف مجاز) تجارت امروز برای روش ترابری مشخص."""
    used = get_trade_mode_day_count(country_id, mode, day)
    cap = get_trade_mode_daily_limit(country_id, mode)
    return used, cap


def check_trade_mode_limit(country_id: int, mode: str, day: str | None = None) -> tuple[bool, str]:
    """بررسی سقف تجارت روزانه برای یک روش ترابری و ساخت پیام راهنما در صورت تکمیل ظرفیت."""
    used, cap = get_trade_mode_budget(country_id, mode, day)
    if used < cap:
        return True, ""

    mode_info = {
        "sea": {
            "name": "دریایی",
            "infra": "بندر تجاری",
            "help": (
                "برای افزایش سقف تجارت دریایی، از بخش فروشگاه (/shop ⬅️ حمل‌ونقل و ترابری) اقدام به احداث **بندر تجاری** یا **بندر بزرگ استراتژیک** نمایید. "
                "هر ۱ بندر جدید در روز **+۱ سقف تجارت دریایی** به ظرفیت روزانه شما اضافه می‌کند (مثلاً با ۲ بندر، سقف شما به ۴ تجارت در روز افزایش می‌یابد)."
            ),
        },
        "air": {
            "name": "هوایی",
            "infra": "فرودگاه بین‌المللی",
            "help": (
                "برای افزایش سقف تجارت هوایی، از بخش فروشگاه (/shop ⬅️ حمل‌ونقل و ترابری) اقدام به احداث **فرودگاه بین‌المللی** نمایید. "
                "هر ۱ فرودگاه جدید در روز **+۱ سقف تجارت هوایی** به ظرفیت روزانه شما اضافه می‌کند."
            ),
        },
        "land": {
            "name": "زمینی",
            "infra": "بزرگراه سراسری (جاده)",
            "help": (
                "برای افزایش سقف تجارت زمینی، از بخش فروشگاه (/shop ⬅️ حمل‌ونقل و ترابری) اقدام به احداث **بزرگراه سراسری (جاده)** نمایید. "
                "هر ۱ بزرگراه جدید در روز **+۱ سقف تجارت زمینی** به ظرفیت روزانه شما اضافه می‌کند."
            ),
        },
    }
    info = mode_info.get(mode, {
        "name": mode,
        "infra": "زیرساخت ترابری",
        "help": "برای افزایش سقف، زیرساخت‌های مربوطه را در /shop ارتقا دهید.",
    })

    msg = (
        f"⛔ **سقف مجاز تجارت {info['name']} امروز پر شده است! (لیمیت)**\n\n"
        f"📊 **وضعیت سقف امروز:** `{used}` از `{cap}` معاهده مجاز مصرف شده است.\n\n"
        f"💡 **راهنمای افزایش لیمیت:**\n{info['help']}"
    )
    return False, msg


def log_transfer(
    from_id: int, to_id: int, kind: str,
    item_key: str = "", item_name: str = "", qty: int = 0,
    resource_type: str = "", amount: int = 0, money_paid: int = 0,
):
    """ثبت یک انتقال در دفترچه؛ باید داخل تراکنش همان انتقال صدا زده شود."""
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO transfer_log (from_country_id, to_country_id, kind, item_key, item_name, "
                "qty, resource_type, amount, money_paid, created_at, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')",
                (from_id, to_id, kind, item_key or "", item_name or "", int(qty or 0),
                 resource_type or "", int(amount or 0), int(money_paid or 0),
                 datetime.datetime.now(datetime.timezone.utc).isoformat()),
            )
    finally:
        conn.close()


def get_active_transfers_from(country_id: int, window_hours: int = 72) -> list[dict]:
    """انتقال‌های فعالِ خروجی از یک کشور در بازه‌ی اخیر (برای برگشت/پیش‌نمایش)."""
    conn = get_connection()
    try:
        cutoff = (datetime.datetime.now(datetime.timezone.utc)
                  - datetime.timedelta(hours=max(1, int(window_hours)))).isoformat()
        rows = conn.execute(
            "SELECT * FROM transfer_log WHERE from_country_id = ? AND status = 'active' "
            "AND created_at >= ? ORDER BY id ASC",
            (country_id, cutoff),
        ).fetchall()
        return [dict(r) for r in rows]
    except Exception:
        return []
    finally:
        conn.close()


def rollback_transfers_from(country_id: int, window_hours: int = 72) -> dict:
    """برگشت انتقال‌های اخیرِ یک کشورِ در حال حذف از کشورهای مقصد.

    قوانین (تصمیم کارفرما):
    * کمک خارجی رایگان: منابع/اقلام تا سقف موجودیِ مقصد برگردانده می‌شود (برگشت کامل).
    * معامله‌ی تجاری: جنسِ منتقل‌شده تا سقف موجودیِ مقصد برمی‌گردد و **۵۰٪ پول
      پرداختیِ خریدار** از خزانه‌ی کشورِ در حال حذف به خریدار بازگردانده می‌شود
      (تا سقف خزانه‌ی حذف‌شونده — پولِ خلق‌شده از هیچ نمی‌سازیم).
    خروجی: خلاصه‌ی عملیات برای نمایش به ادمین.
    """
    transfers = get_active_transfers_from(country_id, window_hours)
    if not transfers:
        return {"total": 0, "items": [], "refunded_total": 0}

    resource_cols = {
        "treasury": "treasury", "gold": "gold", "oil": "oil_reserves",
        "grain": "grain", "iron_ore": "iron_ore", "microchips": "microchips",
        "vaccine_doses": "vaccine_doses", "uranium_ore": "uranium_ore",
        "nuclear_fuel": "nuclear_fuel",
    }
    conn = get_connection()
    summary_items = []
    refunded_total = 0
    try:
        with conn:  # commit خودکار در پایان — بدون آن همه‌چیز با close برگشت می‌خورد
            # خزانه‌ی کشورِ در حال حذف برای بازپرداخت نیمی از پول معاملات
            row = conn.execute("SELECT treasury FROM countries WHERE id = ?", (country_id,)).fetchone()
            deleter_treasury = int(row["treasury"] or 0) if row else 0

            ids = [t["id"] for t in transfers]
            for t in transfers:
                to_id = int(t["to_country_id"])
                exists = conn.execute("SELECT 1 FROM countries WHERE id = ?", (to_id,)).fetchone()
                if not exists:
                    continue
                entry = {"kind": t["kind"], "to_id": to_id}
                if t["kind"] in ("aid", "trade_resource"):
                    rtype = t.get("resource_type") or ""
                    col = resource_cols.get(rtype)
                    entry["what"] = f"{rtype} {t.get('amount') or 0}"
                    if col:
                        conn.execute(
                            f"UPDATE countries SET {col} = MAX(0, COALESCE({col}, 0) - ?) WHERE id = ?",
                            (int(t.get("amount") or 0), to_id),
                        )
                elif t["kind"] == "trade_asset":
                    entry["what"] = f"{t.get('item_name') or t.get('item_key')} x{t.get('qty') or 0}"
                    conn.execute(
                        "UPDATE country_assets SET amount = MAX(0, amount - ?) "
                        "WHERE country_id = ? AND equipment_key = ?",
                        (int(t.get("qty") or 0), to_id, t.get("item_key") or ""),
                    )

                # بازپرداخت ۵۰٪ پول معامله از خزانه‌ی کشور حذف‌شونده به خریدار
                if t["kind"] in ("trade_asset", "trade_resource") and int(t.get("money_paid") or 0) > 0:
                    half = int(t["money_paid"] // 2)
                    refund = min(half, deleter_treasury)
                    if refund > 0:
                        conn.execute("UPDATE countries SET treasury = treasury - ? WHERE id = ?",
                                     (refund, country_id))
                        conn.execute("UPDATE countries SET treasury = treasury + ? WHERE id = ?",
                                     (refund, to_id))
                        deleter_treasury -= refund
                        refunded_total += refund
                        entry["refund"] = refund

                summary_items.append(entry)

            conn.executemany(
                "UPDATE transfer_log SET status = 'rolled_back' WHERE id = ?",
                [(i,) for i in ids],
            )
    finally:
        conn.close()
    return {"total": len(summary_items), "items": summary_items, "refunded_total": refunded_total}


def format_transfer_rollback_summary(result: dict) -> str:
    """متن فارسی خلاصه‌ی برگشت برای نمایش به ادمین."""
    if not result or result.get("total", 0) == 0:
        return "ℹ️ هیچ انتقالِ قابل‌برگشتی در ۷۲ ساعت اخیر یافت نشد."
    lines = [f"♻️ {result['total']} انتقال اخیر از کشور مقصد بازگردانده شد:"]
    for item in result.get("items") or []:
        kind_label = {"aid": "کمک", "trade_asset": "معامله تجهیز", "trade_resource": "معامله منبع"}.get(
            item.get("kind"), item.get("kind"))
        line = f"• {kind_label}: {item.get('what')} ← کشور #{item.get('to_id')}"
        if item.get("refund"):
            line += f" (بازپرداخت {item['refund']:,} تومان)"
        lines.append(line)
    if result.get("refunded_total"):
        lines.append(f"💰 کل بازپرداخت پول به خریداران: {result['refunded_total']:,} تومان")
    return "\n".join(lines)


# ---------- سیستم محاصره دریایی بین‌المللی ----------

def has_open_sea_access(country_key: str) -> bool:
    """آیا کشور به آب‌های آزاد/اقیانوس دسترسی دارد (قابل شرکت در محاصره دریایی)؟"""
    if not country_key:
        return True
    return country_key not in config.NO_SEA_ACCESS_COUNTRIES


def has_land_trade_route(country1_key: str, country2_key: str) -> bool:
    """آیا بین دو کشور «مسیر خشکی پیوسته» برای ترابری زمینی وجود دارد؟

    بر پایه‌ی نقشه‌ی خالص زمینی borders (پیوندهای دریایی-نزدیک مثل آمریکا↔کوبا
    محسوب نمی‌شوند). مرز مستقیم یا ترانزیت خاکی از کشورهای میانی هر دو معتبرند.

    سیاست fail-open هم‌راستا با has_open_sea_access: کشور خارج از کاتالوگ
    جغرافیایی بازی (کلید نامعتبر/ساختگی) محدودیت مسیر ندارد.
    """
    valid_keys = list((getattr(config, "COUNTRY_STARTING_OVERRIDES", {}) or {}).keys())
    known = set(valid_keys)
    if country1_key not in known or country2_key not in known:
        return True
    return borders.has_land_route(country1_key, country2_key, valid_keys)


def calculate_blockade_defense_power(target_id: int) -> tuple[int, list[dict]]:
    """محاسبه مجموع قدرت دفاعی ائتلاف محاصره‌کننده علیه یک کشور (شامل رهبر و کلیه متحدین).

    خروجی: (مجموع کل قدرت ائتلاف, لیست جزئیات مشارکت‌کنندگان)
    """
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM naval_blockades WHERE target_id = ? AND status = 'active'", (target_id,))
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return 0, []

    total_power = 0
    participants = []

    for r in rows:
        b = dict(r)
        lead_c = get_country_by_id(b["blockader_id"])
        if not lead_c:
            continue

        try:
            lead_tf = json.loads(b.get("task_force_json") or "{}")
        except Exception:
            lead_tf = {}

        lead_pwr = calculate_task_force_naval_power(lead_c["id"], lead_tf)
        total_power += lead_pwr
        participants.append({
            "country_id": lead_c["id"],
            "name": lead_c["name"],
            "flag": lead_c["flag"],
            "role": "leader",
            "power": lead_pwr,
            "task_force": lead_tf,
        })

        # محاسبه قدرت متحدین حاضر در coalition_json
        try:
            coalition = json.loads(b.get("coalition_json") or "[]")
        except Exception:
            coalition = []

        for ally in coalition:
            ally_id = int(ally.get("country_id", 0) or 0)
            ally_c = get_country_by_id(ally_id)
            if not ally_c:
                continue
            ally_tf = ally.get("task_force") or {}
            ally_pwr = calculate_task_force_naval_power(ally_id, ally_tf)
            total_power += ally_pwr
            participants.append({
                "country_id": ally_id,
                "name": ally_c["name"],
                "flag": ally_c["flag"],
                "role": "ally",
                "power": ally_pwr,
                "task_force": ally_tf,
            })

    return total_power, participants


def create_naval_blockade(blockader_id: int, target_id: int, task_force: dict | None = None) -> int:
    conn = get_connection()
    cur = conn.cursor()
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    tf_json = json.dumps(task_force or {})
    cur.execute("""
        INSERT INTO naval_blockades (blockader_id, target_id, status, created_at, task_force_json, coalition_json)
        VALUES (?, ?, 'active', ?, ?, '[]')
        ON CONFLICT(blockader_id, target_id) DO UPDATE SET
            status = 'active',
            created_at = excluded.created_at,
            task_force_json = excluded.task_force_json,
            coalition_json = '[]'
    """, (blockader_id, target_id, now_str, tf_json))
    blockade_id = cur.lastrowid
    conn.commit()
    conn.close()
    return blockade_id


def join_naval_blockade(blockader_id: int, target_id: int, ally_country_id: int, task_force: dict | None = None) -> tuple[bool, str]:
    """پیوستن یک کشور متحد نظامی به ائتلاف محاصره دریایی فعال."""
    if blockader_id == ally_country_id or target_id == ally_country_id:
        return False, "کشور انتخابی نمی‌تواند به عنوان متحد به محاصره بپیوندد."

    # ۱. بررسی رابطه اتحاد رسمی
    rel = get_diplomatic_relation(blockader_id, ally_country_id)
    if rel.get("status") != "allied":
        return False, "فقط کشورهایی که دارای پیمان اتحاد نظامی رسمی (Allied) با رهبر محاصره هستند می‌توانند به ائتلاف محاصره بپیوندند."

    # ۲. دسترسی به آب‌های آزاد
    ally_c = get_country_by_id(ally_country_id)
    if not ally_c or not has_open_sea_access(ally_c.get("country_key")):
        return False, "کشور متحد به آب‌های آزاد دسترسی ندارد و امکان اعزام ناوگروه دریایی ندارد."

    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM naval_blockades WHERE blockader_id = ? AND target_id = ? AND status = 'active'", (blockader_id, target_id))
            row = cur.fetchone()
            if not row:
                return False, "محاصره دریایی فعالی با این مشخصات یافت نشد."

            b = dict(row)
            try:
                coalition = json.loads(b.get("coalition_json") or "[]")
            except Exception:
                coalition = []

            # اگر قبلاً در ائتلاف است، بروزرسانی ناوگروه
            existing = [c for c in coalition if c.get("country_id") == ally_country_id]
            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            tf = task_force or {}
            if existing:
                existing[0]["task_force"] = tf
                existing[0]["updated_at"] = now_str
            else:
                coalition.append({
                    "country_id": ally_country_id,
                    "name": ally_c["name"],
                    "flag": ally_c["flag"],
                    "task_force": tf,
                    "joined_at": now_str,
                })

            cur.execute("UPDATE naval_blockades SET coalition_json = ? WHERE id = ?", (json.dumps(coalition), b["id"]))
        return True, f"کشور {ally_c['flag']} {ally_c['name']} با موفقیت به ائتلاف محاصره دریایی پیوست."
    except Exception as e:
        return False, f"خطا در ثبت مشارکت ائتلاف: {e}"
    finally:
        conn.close()


def leave_naval_blockade(blockader_id: int, target_id: int, ally_country_id: int) -> tuple[bool, str]:
    """خروج کشور متحد از ائتلاف محاصره دریایی."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM naval_blockades WHERE blockader_id = ? AND target_id = ? AND status = 'active'", (blockader_id, target_id))
            row = cur.fetchone()
            if not row:
                return False, "محاصره دریایی فعال یافت نشد."

            b = dict(row)
            try:
                coalition = json.loads(b.get("coalition_json") or "[]")
            except Exception:
                coalition = []

            new_coalition = [c for c in coalition if c.get("country_id") != ally_country_id]
            cur.execute("UPDATE naval_blockades SET coalition_json = ? WHERE id = ?", (json.dumps(new_coalition), b["id"]))
        return True, "ناوگروه با موفقیت از ائتلاف محاصره خارج شد."
    except Exception as e:
        return False, f"خطا در خروج از ائتلاف: {e}"
    finally:
        conn.close()


def get_allied_countries_for_blockade(leader_country_id: int) -> list[dict]:
    """لیست کشورهای دارای پیمان اتحاد نظامی رسمی (Allied) با دسترسی به آب‌های آزاد."""
    relations = get_country_diplomatic_relations_all(leader_country_id)
    allies = []
    for r in relations:
        if r.get("status") == "allied":
            other_id = r["country2_id"] if r["country1_id"] == leader_country_id else r["country1_id"]
            other_c = get_country_by_id(other_id)
            if other_c and has_open_sea_access(other_c.get("country_key")):
                allies.append(other_c)
    return allies


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


def break_naval_blockade(target_id: int, apply_task_force_losses: bool = True) -> list[dict]:
    """شکستن محاصره دریایی با تغییر وضعیت به 'broken' و اعمال تلفات عقب‌نشینی به ناوگروه‌های درگیر."""
    conn = get_connection()
    retreated_losses = []
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT * FROM naval_blockades WHERE target_id = ? AND status = 'active'", (target_id,))
            rows = cur.fetchall()
            for r in rows:
                b = dict(r)
                if apply_task_force_losses:
                    # اعمال تلفات جزئی به ناوگروه اعزامی رهبر
                    try:
                        lead_tf = json.loads(b.get("task_force_json") or "{}")
                    except Exception:
                        lead_tf = {}
                    for eq_key, qty in lead_tf.items():
                        loss_qty = max(1, int(qty * 0.10)) if qty >= 2 else 1
                        cur.execute(
                            "UPDATE country_assets SET amount = MAX(0, amount - ?) WHERE country_id = ? AND equipment_key = ?",
                            (loss_qty, b["blockader_id"], eq_key),
                        )
                        retreated_losses.append({"country_id": b["blockader_id"], "equipment_key": eq_key, "qty": loss_qty})

                    # اعمال تلفات جزئی به ناوگروه متحدین
                    try:
                        coalition = json.loads(b.get("coalition_json") or "[]")
                    except Exception:
                        coalition = []
                    for ally in coalition:
                        a_id = ally.get("country_id")
                        a_tf = ally.get("task_force") or {}
                        for eq_key, qty in a_tf.items():
                            loss_qty = max(1, int(qty * 0.10)) if qty >= 2 else 1
                            cur.execute(
                                "UPDATE country_assets SET amount = MAX(0, amount - ?) WHERE country_id = ? AND equipment_key = ?",
                                (loss_qty, a_id, eq_key),
                            )
                            retreated_losses.append({"country_id": a_id, "equipment_key": eq_key, "qty": loss_qty})

            cur.execute("UPDATE naval_blockades SET status = 'broken' WHERE target_id = ? AND status = 'active'", (target_id,))
    finally:
        conn.close()
    return retreated_losses


ANTISHIP_TOKENS = (
    "antiship", "anti-ship", "anti_ship", "ضدکشتی", "noor", "qader", "qadir", "harpoon", "exocet",
    "yakhont", "cruise", "کروز", "khalij", "mandab", "almandab", "bahr", "onslow", "neptune",
    "zircon", "brahmos", "c802", "c-802", "nsm", "otomat", "rbs15", "rbs-15", "yj12", "yj18",
    "yj-12", "yj-18", "lrasm", "cstar", "haeseong", "penguin", "gabriel", "kh35", "kh-35",
    "kh32", "kh-32", "oniks", "bastion", "kalibr", "tomahawk", "scalp", "taurus", "paveh",
    "soumar", "hoveyzeh", "asm3", "hf3", "hsiung", "marte", "martlet", "tankil", "babur",
    "raad", "delilah", "popeye", "kumsong", "termit", "seaskua", "abu_mahdi", "zolfaghar_nav",
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


def calculate_blockade_break_power(country_id: int) -> tuple[int, int, int]:
    """محاسبه تفکیکی قدرت شکستن محاصره دریایی: (قدرت ناوگان, قدرت موشک‌های ضدکشتی, مجموع توان رزمی)."""
    navy_power = calculate_naval_power(country_id)
    antiship_stock = get_antiship_missile_stock(country_id)
    # هر موشک ضدکشتی/کروز ۱ امتیاز قدرت پشتیبانی آتش ساحلی/دریایی دارد
    antiship_power = antiship_stock * 1
    total_power = navy_power + antiship_power
    return navy_power, antiship_power, total_power


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


def _score_single_naval_asset(eq_name: str, amount: int) -> float:
    eq_name = (eq_name or "").lower()
    if amount <= 0:
        return 0

    if any(t in eq_name for t in ["boat", "craft", "شناور", "قایق", "تندرو", "گشتی", "patrol", "موشک‌انداز", "موشک انداز"]):
        return amount * 0.2

    if any(c in eq_name for c in ["ford", "nimitz", "fujian", "shandong", "liaoning", "kuznetsov", "charles de gaulle", "queen elizabeth", "carrier", "هواپیمابر"]):
        return amount * 500
    elif any(l in eq_name for l in ["america", "wasp", "dokdo", "anadolu", "trieste", "lha", "lhd", "lph", "بالگردبر", "ناو بالگردبر"]):
        return amount * 200
    elif any(d in eq_name for d in ["destroyer", "burke", "zumwalt", "ticonderoga", "cruiser", "type 055", "type 052", "type 45", "visakhapatnam", "kirov", "gorshkov", "slava", "maya", "atago", "kongo", "sejong", "کلاس کیروف", "رزم‌پناو", "ناوشکن"]):
        return amount * 80
    elif any(s in eq_name for s in ["virginia", "ohio", "los angeles", "seawolf", "yasen", "borei", "type 094", "type 093", "astute", "vanguard", "suffren", "arihant", "dreadnought", "ssn", "ssbn", "هسته‌ای"]):
        return amount * 70
    elif any(f in eq_name for f in ["frigate", "constellation", "fremm", "f125", "f124", "type 054", "gotland", "type 214", "dolphin", "halifax", "hobart", "miecznik", "perry", "برگامینی", "جماران", "سهند", "دنا", "دماوند", "ناوچه"]):
        return amount * 30
    elif any(c in eq_name for c in ["corvette", "کوروت", "buyan", "steregushchiy", "sa'ar", "baynunah", "soleimani", "شهید سلیمانی", "فاتح", "پیروز"]):
        return amount * 12
    elif any(s in eq_name for s in ["sub", "kilo", "ghadir", "midget", "زیردریایی"]):
        return amount * 10
    else:
        return amount * 0.2


def calculate_task_force_naval_power(country_id: int, task_force: dict | None = None) -> int:
    """محاسبه قدرت رزمی ناوگروه انتخابی (Task Force). اگر خالی یا None باشد کل ناوگان کشور محاسبه می‌شود."""
    if not task_force:
        return calculate_naval_power(country_id)

    assets = get_country_assets(country_id, category="Navy")
    asset_map = {a["equipment_key"]: a for a in assets}
    total_power = 0.0
    for eq_key, count in task_force.items():
        qty = max(0, int(count or 0))
        if qty <= 0:
            continue
        real_asset = asset_map.get(eq_key)
        if real_asset:
            real_amt = int(real_asset.get("amount", 0) or 0)
            actual_qty = min(qty, real_amt)
            if actual_qty > 0:
                total_power += _score_single_naval_asset(real_asset.get("equipment_name", eq_key), actual_qty)
        else:
            total_power += _score_single_naval_asset(eq_key, qty)
    return int(total_power)


# ---------- دریای خزر ----------

def caspian_route_available(country1_key: str, country2_key: str) -> bool:
    """مسیر خزر فقط بین پنج کشور حاشیه‌ی آن باز است."""
    return config.is_caspian_pair(country1_key, country2_key)


def caspian_route_info(country1_key: str, country2_key: str) -> dict | None:
    """اطلاعات مسیر خزر، یا None اگر این جفت کشور به خزر راه ندارند.

    خزر دریای بسته است: هیچ محاصره‌ی اقیانوسی و هیچ تنگه‌ای رویش اثر ندارد.
    """
    if not caspian_route_available(country1_key, country2_key):
        return None
    info = dict(config.CASPIAN_TRANSPORT)
    info["immune_to_blockade"] = True
    info["immune_to_straits"] = True
    return info


# ---------- قفل ناوگروه، اسکورت و عبور از محاصره ----------

def _now_iso(dt=None):
    return (dt or datetime.datetime.now()).isoformat(timespec="seconds")


def purge_expired_naval_locks(now_dt=None) -> int:
    """قفل‌های منقضی‌شده را آزاد می‌کند. idempotent."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute("DELETE FROM naval_locks WHERE until_at <= ?", (_now_iso(now_dt),))
            return cur.rowcount or 0
    finally:
        conn.close()


def get_locked_ship_counts(country_id: int, now_dt=None) -> dict:
    """چند فروند از هر شناور هم‌اکنون در مأموریت قفل است."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT equipment_key, SUM(qty) AS q FROM naval_locks"
            " WHERE country_id = ? AND until_at > ? GROUP BY equipment_key",
            (country_id, _now_iso(now_dt))).fetchall()
        return {r["equipment_key"]: int(r["q"] or 0) for r in rows}
    finally:
        conn.close()


def get_deployable_ships(country_id: int, now_dt=None) -> list[dict]:
    """شناورهای قابل اعزام: کل منهای در تعمیر منهای قفل‌شده."""
    locks = get_locked_ship_counts(country_id, now_dt)
    out = []
    for a in get_country_assets(country_id, category="Navy"):
        free = available_ship_count(a) - locks.get(a["equipment_key"], 0)
        if free <= 0:
            continue
        out.append({
            "equipment_key": a["equipment_key"],
            "equipment_name": a["equipment_name"],
            "tier": config.ship_tier(a["equipment_name"]),
            "available": free,
            "buy_price": int(a["buy_price"] or 0),
        })
    return sorted(out, key=lambda x: -x["buy_price"])


def lock_task_force(country_id: int, task_force: dict, hours: int, reason: str = "escort",
                    now_dt=None) -> tuple[bool, str]:
    """ناوگروه را برای مدت مشخص قفل می‌کند. اگر فروند کافی آزاد نباشد رد می‌شود."""
    task_force = {k: int(v or 0) for k, v in (task_force or {}).items() if int(v or 0) > 0}
    if not task_force:
        return False, "هیچ شناوری انتخاب نشده است."
    deployable = get_deployable_ships(country_id, now_dt)
    free = {d["equipment_key"]: d["available"] for d in deployable}
    names = {d["equipment_key"]: d["equipment_name"] for d in deployable}
    for key, qty in task_force.items():
        if free.get(key, 0) < qty:
            nm = names.get(key, key)
            return False, f"⛔ فقط {free.get(key, 0)} فروند «{nm}» آزاد است (بقیه در تعمیر یا مأموریت‌اند)."
    until = (now_dt or datetime.datetime.now()) + datetime.timedelta(hours=max(1, int(hours)))
    conn = get_connection()
    try:
        with conn:
            for key, qty in task_force.items():
                conn.execute(
                    "INSERT INTO naval_locks (country_id, equipment_key, qty, reason, until_at)"
                    " VALUES (?,?,?,?,?)",
                    (country_id, key, qty, reason, until.isoformat(timespec="seconds")))
        return True, until.isoformat(timespec="seconds")
    finally:
        conn.close()


def task_force_power(country_id: int, task_force: dict) -> int:
    """توان رزمی یک ناوگروه انتخابی."""
    names = {a["equipment_key"]: a["equipment_name"]
             for a in get_country_assets(country_id, category="Navy")}
    total = 0
    for key, qty in (task_force or {}).items():
        qty = max(0, int(qty or 0))
        if qty <= 0:
            continue
        total += _score_single_naval_asset(names.get(key, key), qty)
    return int(total)


def task_force_escort_cost(country_id: int, task_force: dict) -> dict:
    names = {a["equipment_key"]: a["equipment_name"]
             for a in get_country_assets(country_id, category="Navy")}
    return config.escort_cost(task_force, lambda k: names.get(k, ""))


# ---------- درخواست اسکورت ----------

def create_escort_request(requester_id: int, escort_id: int, blocker_id: int | None,
                          payload: dict | None = None, now_dt=None) -> tuple[bool, str, int]:
    if requester_id == escort_id:
        return False, "نمی‌توانید از خودتان درخواست اسکورت کنید.", 0
    now = now_dt or datetime.datetime.now()
    exp = now + datetime.timedelta(hours=config.ESCORT_REQUEST_TTL_HOURS)
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute(
                "SELECT id FROM escort_requests WHERE requester_id = ? AND escort_id = ?"
                " AND status = 'pending' AND expires_at > ?",
                (requester_id, escort_id, _now_iso(now)))
            if cur.fetchone():
                return False, "یک درخواست اسکورت باز برای همین کشور دارید.", 0
            cur = conn.execute(
                "INSERT INTO escort_requests (requester_id, escort_id, blocker_id, payload_json,"
                " status, created_at, expires_at) VALUES (?,?,?,?,'pending',?,?)",
                (requester_id, escort_id, blocker_id, json.dumps(payload or {}, ensure_ascii=False),
                 _now_iso(now), exp.isoformat(timespec="seconds")))
            return True, "درخواست اسکورت ارسال شد.", int(cur.lastrowid)
    finally:
        conn.close()


def get_escort_request(request_id: int) -> dict | None:
    conn = get_connection()
    try:
        r = conn.execute("SELECT * FROM escort_requests WHERE id = ?", (request_id,)).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def get_pending_escort_requests(escort_id: int, now_dt=None) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM escort_requests WHERE escort_id = ? AND status = 'pending'"
            " AND expires_at > ? ORDER BY id DESC", (escort_id, _now_iso(now_dt))).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def accept_escort_request(request_id: int, task_force: dict, now_dt=None) -> tuple[bool, str]:
    """پذیرش اسکورت: هزینه کسر و ناوگروه قفل می‌شود."""
    req = get_escort_request(request_id)
    if not req:
        return False, "درخواست یافت نشد."
    if req["status"] != "pending":
        return False, "این درخواست دیگر باز نیست."
    now = now_dt or datetime.datetime.now()
    try:
        if datetime.datetime.fromisoformat(req["expires_at"]) <= now:
            return False, "مهلت این درخواست تمام شده است."
    except (ValueError, TypeError):
        pass

    escort_id = req["escort_id"]
    cost = task_force_escort_cost(escort_id, task_force)
    c = get_country_by_id(escort_id)
    if not c:
        return False, "کشور اسکورت‌کننده یافت نشد."
    if int(c["treasury"] or 0) < cost["money"]:
        return False, f"⛔ خزانه کافی نیست. هزینه اعزام: {cost['money']:,} دلار"
    if int(c["oil_reserves"] or 0) < cost["oil"]:
        return False, f"⛔ سوخت کافی نیست. نیاز: {cost['oil']:,} بشکه"

    ok, msg = lock_task_force(escort_id, task_force, config.ESCORT_LOCK_HOURS, "escort", now)
    if not ok:
        return False, msg

    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE countries SET treasury = treasury - ?, oil_reserves = MAX(0, oil_reserves - ?)"
                " WHERE id = ?", (cost["money"], cost["oil"], escort_id))
            conn.execute(
                "UPDATE escort_requests SET status = 'accepted', task_force_json = ? WHERE id = ?",
                (json.dumps(task_force, ensure_ascii=False), request_id))
    finally:
        conn.close()
    return True, (f"✅ اسکورت پذیرفته شد. ناوگروه تا {config.ESCORT_LOCK_HOURS} ساعت "
                  f"در مأموریت قفل است.\n💵 {cost['money']:,} دلار | 🛢️ {cost['oil']:,} بشکه")


def reject_escort_request(request_id: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute(
                "UPDATE escort_requests SET status = 'rejected' WHERE id = ? AND status = 'pending'",
                (request_id,))
        return (cur.rowcount or 0) > 0, "درخواست رد شد."
    finally:
        conn.close()


def expire_stale_escort_requests(now_dt=None) -> int:
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute(
                "UPDATE escort_requests SET status = 'expired'"
                " WHERE status = 'pending' AND expires_at <= ?", (_now_iso(now_dt),))
            return cur.rowcount or 0
    finally:
        conn.close()


# ---------- قواعد درگیری ----------

def get_blockade_roe(blockader_id: int, target_id: int) -> str:
    conn = get_connection()
    try:
        r = conn.execute("SELECT roe FROM naval_blockades WHERE blockader_id = ? AND target_id = ?",
                         (blockader_id, target_id)).fetchone()
        roe = (r["roe"] if r else None) or config.NAVAL_ROE_DEFAULT
        return roe if roe in config.NAVAL_ROE else config.NAVAL_ROE_DEFAULT
    finally:
        conn.close()


def set_blockade_roe(blockader_id: int, target_id: int, roe: str) -> bool:
    if roe not in config.NAVAL_ROE:
        return False
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute(
                "UPDATE naval_blockades SET roe = ? WHERE blockader_id = ? AND target_id = ?",
                (roe, blockader_id, target_id))
        return (cur.rowcount or 0) > 0
    finally:
        conn.close()


def get_strait_roe(strait_key: str) -> str:
    roe = get_setting(f"strait_roe_{strait_key}", config.NAVAL_ROE_DEFAULT)
    return roe if roe in config.NAVAL_ROE else config.NAVAL_ROE_DEFAULT


def set_strait_roe(strait_key: str, roe: str) -> bool:
    if roe not in config.NAVAL_ROE:
        return False
    set_setting(f"strait_roe_{strait_key}", roe)
    return True


# ---------- قرعه‌ی عبور ----------

def _apply_incident_damage(country_id: int, task_force: dict, hit_ratio: float,
                           rng, now_dt=None) -> list[dict]:
    """آسیب/غرق به یک ناوگروه طبق رده‌ی هر شناور. ناو سرمایه‌ای هرگز غرق نمی‌شود."""
    names = {a["equipment_key"]: a["equipment_name"]
             for a in get_country_assets(country_id, category="Navy")}
    report = []
    for key, qty in (task_force or {}).items():
        qty = max(0, int(qty or 0))
        if qty <= 0:
            continue
        hits = sum(1 for _ in range(qty) if rng.random() < hit_ratio)
        if hits <= 0:
            continue
        tier = config.ship_tier(names.get(key, ""))
        sink_p = config.SHIP_SINK_CHANCE.get(tier, 0.0)
        sunk = sum(1 for _ in range(hits) if rng.random() < sink_p)
        hurt = hits - sunk
        if sunk:
            sunk = sink_ships(country_id, key, sunk)
        if hurt:
            sev = "heavy" if rng.random() < 0.5 else "light"
            hurt = damage_ships(country_id, key, hurt, sev, now_dt).get("damaged", 0)
        if sunk or hurt:
            report.append({"equipment_key": key, "equipment_name": names.get(key, key),
                           "tier": tier, "sunk": sunk, "damaged": hurt})
    return report


def resolve_sea_passage(sender_id: int, blocker_id: int | None, escort_id: int | None = None,
                        escort_task_force: dict | None = None, roe: str = None,
                        blocker_power: int | None = None, now_dt=None, rng=None) -> dict:
    """قرعه‌ی عبور از محاصره یا تنگه‌ی بسته.

    برنده‌ی قطعی وجود ندارد: کف عبور ۱۵٪ و سقف ۸۵٪ است. درگیری دوطرفه است،
    یعنی ناوگروه مسدودکننده هم می‌تواند آسیب ببیند.
    """
    import random as _random
    rng = rng or _random.Random()
    roe = roe if roe in config.NAVAL_ROE else config.NAVAL_ROE_DEFAULT
    spec = config.NAVAL_ROE[roe]
    escort_task_force = escort_task_force or {}

    if blocker_power is None:
        blocker_power = calculate_blockade_break_power(blocker_id)[2] if blocker_id else 0
    blocker_power = max(0, int(blocker_power or 0))

    escort_power = 0
    if escort_id and escort_task_force:
        escort_power += task_force_power(escort_id, escort_task_force)
    escort_power += int(calculate_naval_power(sender_id) * config.PASSAGE_OWN_NAVY_SHARE)

    chance = config.passage_chance(escort_power, blocker_power, roe)
    roll = rng.random()
    passed = roll < chance

    if passed:
        outcome = "passed_hurt" if rng.random() < 0.20 else "passed"
    else:
        weights = [("turned_back", 1.0),
                   ("seized", spec["seize_weight"]),
                   ("struck", spec["strike_weight"])]
        weights = [(k, w) for k, w in weights if w > 0]
        total = sum(w for _, w in weights)
        pick = rng.random() * total
        outcome = weights[-1][0]
        acc = 0.0
        for k, w in weights:
            acc += w
            if pick <= acc:
                outcome = k
                break

    # درگیری دوطرفه — هرچه نبرد سخت‌تر، آسیب بیشتر
    escort_losses, blocker_losses = [], []
    intensity = {"inspect": 0.0, "seize": 0.10, "fire": 0.30}[roe]
    if intensity > 0 and escort_id and escort_task_force:
        if outcome in ("struck", "seized", "passed_hurt"):
            escort_losses = _apply_incident_damage(escort_id, escort_task_force,
                                                   intensity, rng, now_dt)
        if outcome in ("passed", "passed_hurt") and blocker_id:
            bl_tf = _blockade_lead_task_force(blocker_id)
            if bl_tf:
                ratio = min(0.35, intensity * (escort_power / max(1, blocker_power)))
                blocker_losses = _apply_incident_damage(blocker_id, bl_tf, ratio, rng, now_dt)

    return {
        "passed": passed,
        "outcome": outcome,
        "outcome_label": config.PASSAGE_OUTCOMES[outcome],
        "chance": round(chance, 4),
        "roll": round(roll, 4),
        "escort_power": escort_power,
        "blocker_power": blocker_power,
        "roe": roe,
        "escort_losses": escort_losses,
        "blocker_losses": blocker_losses,
        "cargo_ratio": 1.0 if outcome == "passed" else (0.6 if outcome == "passed_hurt" else 0.0),
    }


def _blockade_lead_task_force(blockader_id: int) -> dict:
    """ناوگروه اعزامی رهبر محاصره (برای اعمال تلفات متقابل)."""
    conn = get_connection()
    try:
        r = conn.execute(
            "SELECT task_force_json FROM naval_blockades WHERE blockader_id = ? AND status = 'active'"
            " LIMIT 1", (blockader_id,)).fetchone()
        if not r:
            return {}
        try:
            return {k: int(v or 0) for k, v in (json.loads(r["task_force_json"] or "{}")).items()}
        except (ValueError, TypeError):
            return {}
    finally:
        conn.close()


# ---------- آسیب و تعمیر شناور ----------

def available_ship_count(asset: dict | sqlite3.Row) -> int:
    """تعداد فروند عملیاتی این قلم (کل منهای در حال تعمیر)."""
    try:
        total = int(asset["amount"] or 0)
    except (KeyError, IndexError, TypeError):
        total = 0
    try:
        repairing = int(asset["under_repair_qty"] or 0)
    except (KeyError, IndexError, TypeError):
        repairing = 0
    return max(0, total - max(0, repairing))


def damage_ships(country_id: int, equipment_key: str, qty: int,
                 severity: str = "heavy", now_dt=None) -> dict:
    """چند فروند از یک شناور را آسیب‌دیده و از رده خارج می‌کند.

    شناور آسیب‌دیده از انبار حذف نمی‌شود؛ فقط تا پایان تعمیر عملیاتی نیست.
    اگر قبلاً فروندی در تعمیر باشد، زمان آمادگی به دیرترین موعد کشیده می‌شود
    تا آسیب جدید موعد قبلی را عقب نیندازد.
    """
    qty = max(0, int(qty or 0))
    if qty <= 0:
        return {"damaged": 0}
    severity = severity if severity in ("light", "heavy") else "heavy"
    now_dt = now_dt or datetime.datetime.now()

    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "SELECT equipment_name, amount, COALESCE(under_repair_qty,0) AS under_repair_qty,"
                " repair_ready_at, buy_price FROM country_assets"
                " WHERE country_id = ? AND equipment_key = ?",
                (country_id, equipment_key))
            row = cur.fetchone()
            if not row:
                return {"damaged": 0}

            free = max(0, int(row["amount"] or 0) - int(row["under_repair_qty"] or 0))
            hurt = min(qty, free)
            if hurt <= 0:
                return {"damaged": 0}

            spec = config.ship_repair_spec(row["equipment_name"], row["buy_price"], severity)
            ready = now_dt + datetime.timedelta(hours=spec["hours"])
            prev = row["repair_ready_at"]
            if prev:
                try:
                    prev_dt = datetime.datetime.fromisoformat(prev)
                    ready = max(ready, prev_dt)
                except (ValueError, TypeError):
                    pass

            cur.execute(
                "UPDATE country_assets SET under_repair_qty = COALESCE(under_repair_qty,0) + ?,"
                " repair_ready_at = ?, repair_severity = ?"
                " WHERE country_id = ? AND equipment_key = ?",
                (hurt, ready.isoformat(timespec="seconds"), severity, country_id, equipment_key))

            return {"damaged": hurt, "tier": spec["tier"], "severity": severity,
                    "hours": spec["hours"], "ready_at": ready.isoformat(timespec="seconds"),
                    "equipment_name": row["equipment_name"],
                    "repair_money": spec["money"] * hurt,
                    "repair_iron": spec["iron_ore"] * hurt}
    finally:
        conn.close()


def sink_ships(country_id: int, equipment_key: str, qty: int) -> int:
    """غرق کردن قطعی: از انبار حذف می‌شود. اول از فروندهای سالم."""
    qty = max(0, int(qty or 0))
    if qty <= 0:
        return 0
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT amount, COALESCE(under_repair_qty,0) AS ur FROM country_assets"
                        " WHERE country_id = ? AND equipment_key = ?", (country_id, equipment_key))
            row = cur.fetchone()
            if not row:
                return 0
            total = int(row["amount"] or 0)
            lost = min(qty, total)
            if lost <= 0:
                return 0
            new_total = total - lost
            # اگر فروند سالم کم آمد، از فروندهای در تعمیر هم کم می‌شود
            new_ur = min(int(row["ur"] or 0), new_total)
            cur.execute("UPDATE country_assets SET amount = ?, under_repair_qty = ?"
                        " WHERE country_id = ? AND equipment_key = ?",
                        (new_total, new_ur, country_id, equipment_key))
            if new_ur == 0:
                cur.execute("UPDATE country_assets SET repair_ready_at = NULL, repair_severity = NULL"
                            " WHERE country_id = ? AND equipment_key = ?", (country_id, equipment_key))
            return lost
    finally:
        conn.close()


def get_ships_under_repair(country_id: int) -> list[dict]:
    """فهرست شناورهای در حال تعمیر با زمان باقی‌مانده."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT equipment_key, equipment_name, amount,"
                    " COALESCE(under_repair_qty,0) AS under_repair_qty,"
                    " repair_ready_at, repair_severity, buy_price"
                    " FROM country_assets WHERE country_id = ? AND category = 'Navy'"
                    " AND COALESCE(under_repair_qty,0) > 0", (country_id,))
        now = datetime.datetime.now()
        out = []
        for r in cur.fetchall():
            remaining = 0
            if r["repair_ready_at"]:
                try:
                    ready = datetime.datetime.fromisoformat(r["repair_ready_at"])
                    remaining = max(0, int((ready - now).total_seconds() // 3600))
                except (ValueError, TypeError):
                    remaining = 0
            out.append({
                "equipment_key": r["equipment_key"],
                "equipment_name": r["equipment_name"],
                "tier": config.ship_tier(r["equipment_name"]),
                "qty": int(r["under_repair_qty"]),
                "operational": max(0, int(r["amount"] or 0) - int(r["under_repair_qty"])),
                "severity": r["repair_severity"] or "heavy",
                "hours_left": remaining,
                "ready_at": r["repair_ready_at"],
            })
        return out
    finally:
        conn.close()


def process_ship_repairs(country_id: int, now_dt=None) -> list[dict]:
    """شناورهایی که موعد تعمیرشان رسیده را عملیاتی می‌کند.

    هزینه‌ی تعمیر (پول + آهن) همین‌جا کسر می‌شود. اگر کشور توان پرداخت
    نداشته باشد، تعمیر انجام نمی‌شود و شناور در تعمیرگاه می‌ماند تا وقتی
    منابع تأمین شود — پس تعمیر رایگان نیست و آهن واقعاً راهبردی می‌شود.
    """
    now_dt = now_dt or datetime.datetime.now()
    conn = get_connection()
    restored = []
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT equipment_key, equipment_name, buy_price,"
                        " COALESCE(under_repair_qty,0) AS ur, repair_ready_at, repair_severity"
                        " FROM country_assets WHERE country_id = ? AND category = 'Navy'"
                        " AND COALESCE(under_repair_qty,0) > 0", (country_id,))
            rows = [dict(r) for r in cur.fetchall()]
            if not rows:
                return []

            cur.execute("SELECT treasury, COALESCE(iron_ore,0) AS iron_ore FROM countries WHERE id = ?",
                        (country_id,))
            c = cur.fetchone()
            if not c:
                return []
            money_left = int(c["treasury"] or 0)
            iron_left = int(c["iron_ore"] or 0)

            for r in rows:
                if not r["repair_ready_at"]:
                    continue
                try:
                    ready = datetime.datetime.fromisoformat(r["repair_ready_at"])
                except (ValueError, TypeError):
                    continue
                if ready > now_dt:
                    continue

                spec = config.ship_repair_spec(r["equipment_name"], r["buy_price"],
                                               r["repair_severity"] or "heavy")
                qty = int(r["ur"])
                # هر فروندی که توان پرداختش هست تعمیر می‌شود، نه همه‌یا‌هیچ
                per_money, per_iron = spec["money"], spec["iron_ore"]
                affordable = qty
                if per_money > 0:
                    affordable = min(affordable, money_left // per_money)
                if per_iron > 0:
                    affordable = min(affordable, iron_left // per_iron)
                affordable = max(0, int(affordable))
                if affordable <= 0:
                    continue

                money_left -= per_money * affordable
                iron_left -= per_iron * affordable
                remaining_ur = qty - affordable
                cur.execute(
                    "UPDATE country_assets SET under_repair_qty = ?,"
                    " repair_ready_at = CASE WHEN ? = 0 THEN NULL ELSE repair_ready_at END,"
                    " repair_severity = CASE WHEN ? = 0 THEN NULL ELSE repair_severity END"
                    " WHERE country_id = ? AND equipment_key = ?",
                    (remaining_ur, remaining_ur, remaining_ur, country_id, r["equipment_key"]))
                restored.append({
                    "equipment_key": r["equipment_key"],
                    "equipment_name": r["equipment_name"],
                    "qty": affordable,
                    "still_waiting": remaining_ur,
                    "money": per_money * affordable,
                    "iron_ore": per_iron * affordable,
                })

            if restored:
                cur.execute("UPDATE countries SET treasury = ?, iron_ore = ? WHERE id = ?",
                            (money_left, iron_left, country_id))
        return restored
    finally:
        conn.close()


def calculate_naval_power(country_id: int) -> int:
    """محاسبه متوازن و واقعی امتیاز قدرت رزمی نیروی دریایی آب‌های آزاد."""
    assets = get_country_assets(country_id, category="Navy")
    if not assets:
        return 0

    # شناور در حال تعمیر عملیاتی نیست و در توان رزمی حساب نمی‌شود
    total_power = sum(
        _score_single_naval_asset(a["equipment_name"], available_ship_count(a))
        for a in assets if available_ship_count(a) > 0
    )
    return int(total_power)


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
        "czech", "hungary", "serbia", "slovakia", "ireland", "lithuania", "slovenia", "albania", "bosnia"
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
        "russia", "ukraine", "egypt", "israel", "lebanon", "syria", "libya", "tunisia", "algeria",
        "slovenia", "albania", "bosnia"
    }

    # کشورهای اقیانوس اطلس و آمریکا (خارج از مدیترانه)
    ATLANTIC_OUTSIDE = {
        "usa", "canada", "mexico", "cuba", "venezuela", "brazil", "argentina", "chile", "colombia",
        "peru", "ecuador", "uk", "norway", "sweden", "finland", "denmark", "germany", "netherlands",
        "belgium", "poland", "portugal", "south_africa", "nigeria", "angola", "ireland", "lithuania"
    }

    # حوزه غرب مالاکا (اقیانوس هند، خاورمیانه، آفریقا، اروپا)
    MALACCA_WEST = {
        "india", "pakistan", "sri_lanka", "bangladesh", "iran", "iraq", "kuwait", "saudi", "qatar",
        "uae", "oman", "yemen", "egypt", "sudan", "somalia", "kenya", "south_africa",
        "uk", "france", "germany", "italy", "spain", "netherlands", "turkey", "russia", "greece",
        "ireland", "lithuania", "slovenia", "albania", "bosnia"
    }

    # حوزه شرق مالاکا (شرق و جنوب شرق آسیا در اقیانوس آرام)
    MALACCA_EAST = {
        "china", "japan", "south_korea", "north_korea", "taiwan", "philippines", "vietnam", "cambodia", "thailand"
    }

    # حوضه‌ی اقیانوس آرام: کشورهایی که سواحل اقیانوس آرام دارند.
    # بدون این مفهوم، منطق مبتنی بر «غرب/شرق سوئز» نتیجه‌های نادرست می‌داد:
    # آمریکا (غرب سوئز) ↔ ژاپن (شرق سوئز) از سوئز و باب‌المندب رد می‌شد، در
    # حالی که مسیر واقعی اقیانوس آرام است؛ و روسیه ↔ چین که هم مرز زمینی
    # دارند و هم هر دو بندر اقیانوس آرام، از سوئز و بسفر و مالاکا می‌گذشت.
    PACIFIC_BASIN = {
        "usa", "canada", "mexico", "guatemala", "colombia", "ecuador", "peru", "chile",
        "russia", "china", "japan", "south_korea", "north_korea", "taiwan",
        "philippines", "vietnam", "indonesia", "malaysia", "singapore", "thailand",
        "cambodia", "brunei", "australia", "new_zealand", "papua_new_guinea",
    }
    both_pacific = c1 in PACIFIC_BASIN and c2 in PACIFIC_BASIN

    if strait_key in ("hormuz", "hormuz_south"):
        return (c1 in PERSIAN_GULF) != (c2 in PERSIAN_GULF)

    elif strait_key == "suez":
        # کانال سوئز تنها زمانی طی می‌شود که یک طرف در غرب/شمال سوئز و طرف دیگر در شرق/جنوب سوئز باشد
        if both_pacific:
            return False        # مسیر اقیانوس آرام، نیازی به سوئز نیست
        return (c1 in SUEZ_WEST and c2 in SUEZ_EAST) or (c1 in SUEZ_EAST and c2 in SUEZ_WEST)

    elif strait_key in ("bab_el_mandeb", "bab_el_mandeb_west"):
        # باب‌المندب اتصال دریای سرخ/اروپا به اقیانوس هند و آسیا است
        if both_pacific:
            return False
        is_c1_north = c1 in RED_SEA_LITTORAL or c1 in SUEZ_WEST
        is_c2_north = c2 in RED_SEA_LITTORAL or c2 in SUEZ_WEST
        is_c1_south = c1 in SUEZ_EAST and c1 not in RED_SEA_LITTORAL
        is_c2_south = c2 in SUEZ_EAST and c2 not in RED_SEA_LITTORAL
        return (is_c1_north and is_c2_south) or (is_c2_north and is_c1_south)

    elif strait_key == "bosphorus":
        if both_pacific:
            return False        # روسیه از بنادر اقیانوس آرامش استفاده می‌کند
        return (c1 in BLACK_SEA) != (c2 in BLACK_SEA)

    elif strait_key in ("gibraltar_north", "gibraltar_south"):
        # جبل‌الطارق دروازه ورود/خروج مدیترانه به اقیانوس اطلس است
        return (c1 in MEDITERRANEAN and c2 in ATLANTIC_OUTSIDE) or (c1 in ATLANTIC_OUTSIDE and c2 in MEDITERRANEAN)

    elif strait_key == "danish_straits":
        baltic_countries = {"sweden", "finland", "poland", "lithuania"}
        return (c1 in baltic_countries and c2 not in baltic_countries and c2 not in MEDITERRANEAN) or \
               (c2 in baltic_countries and c1 not in baltic_countries and c1 not in MEDITERRANEAN)

    elif strait_key in ("malacca", "malacca_north", "singapore_strait", "andaman_malacca"):
        if both_pacific:
            return False        # هر دو در حوضه‌ی اقیانوس آرام‌اند
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


def get_trade_route_strait_analysis(country1_key: str, country2_key: str) -> dict:
    """تحلیل جامع وضعیت آبراه‌ها و تنگه‌های استراتژیک در طول مسیر ترانزیت دریایی بین دو کشور."""
    if not country1_key or not country2_key:
        return {
            "is_blocked": False,
            "blocked_straits": [],
            "has_tolls": False,
            "total_toll": 0,
            "toll_straits": [],
            "all_crossed": [],
        }

    c1_k = country1_key.lower()
    c2_k = country2_key.lower()

    blocked_straits = []
    toll_straits = []
    all_crossed = []

    for owner_key, strait_info in STRAITS_MAPPING.items():
        s_key = strait_info["strait_key"]
        if is_trade_route_crossing_strait(c1_k, c2_k, s_key):
            st_data = get_strait_status(s_key)
            st_status = st_data.get("status", "open")
            st_toll = int(st_data.get("toll", 0) or 0)

            owner_c = get_country_by_key(owner_key)
            owner_name = owner_c["name"] if owner_c else owner_key
            owner_flag = owner_c.get("flag", "") if owner_c else ""

            strait_entry = {
                "strait_key": s_key,
                "name": strait_info["name"],
                "owner_key": owner_key,
                "owner_name": owner_name,
                "owner_flag": owner_flag,
                "owner_c": owner_c,
                "status": st_status,
                "toll_amount": st_toll,
            }
            all_crossed.append(strait_entry)

            if owner_key not in (c1_k, c2_k):
                if st_status in ("blocked", "closed"):
                    blocked_straits.append(strait_entry)
                elif st_status == "toll" and st_toll > 0:
                    toll_straits.append(strait_entry)

    total_toll = sum(s["toll_amount"] for s in toll_straits)

    return {
        "is_blocked": len(blocked_straits) > 0,
        "blocked_straits": blocked_straits,
        "has_tolls": len(toll_straits) > 0,
        "total_toll": total_toll,
        "toll_straits": toll_straits,
        "all_crossed": all_crossed,
    }


def list_strait_statuses() -> list[dict]:
    """وضعیت همه‌ی تنگه‌ها به‌همراه مالکشان — برای پنل ادمین و عیب‌یابی.

    یک تنگه‌ی فراموش‌شده در حالت «بسته» مسیر دریایی حدود ۲۱٪ از جفت‌کشورها
    را بی‌صدا قطع می‌کند و بازیکن فقط می‌بیند «دریایی کار نمی‌کند».
    """
    out = []
    for owner_key, info in STRAITS_MAPPING.items():
        st = get_strait_status(info["strait_key"])
        owner = get_country_by_key(owner_key)
        out.append({
            "strait_key": info["strait_key"],
            "name": info["name"],
            "owner_key": owner_key,
            "owner_name": owner["name"] if owner else owner_key,
            "owner_flag": (owner.get("flag", "") if owner else ""),
            "status": st.get("status", "open"),
            "toll": int(st.get("toll", 0) or 0),
            "roe": get_strait_roe(info["strait_key"]),
        })
    return out


def reopen_all_straits() -> int:
    """باز کردن همه‌ی تنگه‌های بسته/عوارضی. برای رفع قفل‌شدگی تجارت دریایی."""
    changed = 0
    for entry in list_strait_statuses():
        if entry["status"] != "open":
            set_strait_status(entry["strait_key"], "open", 0)
            changed += 1
    return changed


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

    # 🚫 تحریم‌های هدفمند سازمان ملل
    if has_targeted_sanction(seller_id, "market_ban"):
        return False, "🚫 **ممنوعیت بورس جهانی (سازمان ملل):** دسترسی کشور شما به بورس قطع است."
    if resource_type == "oil" and has_targeted_sanction(seller_id, "oil_embargo"):
        return False, "🚫 **تحریم نفتی سازمان ملل:** عرضه‌ی نفت این کشور در بورس جهانی ممنوع است."

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
        "vaccine_doses": "vaccine_doses",
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
    if transport_mode not in {"sea", "land", "air", "caspian"}:
        return False, "روش ترابری نامعتبر است.", {}
    if isinstance(buy_amount, bool) or not isinstance(buy_amount, int) or buy_amount <= 0:
        return False, "مقدار خرید باید یک عدد صحیح بزرگ‌تر از صفر باشد.", {}

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

            # 🚫 تحریم‌های هدفمند سازمان ملل
            if seller and has_targeted_sanction(seller_id, "market_ban"):
                return False, "🚫 **ممنوعیت بورس جهانی (سازمان ملل):** فروشنده تحت تحریم بورس است.", {}
            if buyer and has_targeted_sanction(buyer_id, "market_ban"):
                return False, "🚫 **ممنوعیت بورس جهانی (سازمان ملل):** دسترسی کشور شما به بورس قطع است.", {}
            if (seller and buyer and order.get("resource_type") == "oil"
                    and has_targeted_sanction(seller_id, "oil_embargo")):
                return False, "🚫 **تحریم نفتی سازمان ملل:** خرید نفت از کشور تحت تحریم نفتی ممنوع است.", {}

            if not seller or not buyer:
                return False, "کشور خریدار یا فروشنده یافت نشد.", {}

            seller_c = dict(seller)
            buyer_c = dict(buyer)

            c_min, c_max = _ordered_pair(seller_id, buyer_id)
            cur.execute("SELECT status FROM diplomatic_relations WHERE country1_id = ? AND country2_id = ?", (c_min, c_max))
            rel_row = cur.fetchone()
            if rel_row and rel_row["status"] == "sanctioned":
                return False, "امکان معامله تجاری با کشور تحریم‌شده وجود ندارد.", {}

            strait_tolls = []
            if transport_mode == "caspian":
                if not caspian_route_available(seller_c.get("country_key"), buyer_c.get("country_key")):
                    return False, ("🌊 **مسیر دریای خزر در دسترس نیست:** این مسیر فقط بین کشورهای "
                                   "حاشیه‌ی خزر (ایران، روسیه، قزاقستان، ترکمنستان، آذربایجان) برقرار است."), {}

            if transport_mode == "sea":
                if is_country_blockaded(seller_id) or is_country_blockaded(buyer_id):
                    return False, "⚓ **ترابری دریایی مسدود است:** یکی از دو کشور تحت محاصره کامل دریایی است. لطفاً از ترابری هوایی یا زمینی استفاده بفرمایید.", {}

                s_key = seller_c.get("country_key")
                b_key = buyer_c.get("country_key")
                analysis = get_trade_route_strait_analysis(s_key, b_key)
                if analysis["is_blocked"]:
                    blocked_str = "، ".join([f"{s['name']} (توسط {s['owner_flag']} {s['owner_name']})" for s in analysis["blocked_straits"]])
                    return False, f"⚓ **گلوگاه دریایی مسدود است:** مسیر ترانزیت دریایی از {blocked_str} مسدود شده است.", {}

                for t_entry in analysis["toll_straits"]:
                    owner_c = t_entry["owner_c"]
                    st_toll = t_entry["toll_amount"]
                    if owner_c and st_toll > 0:
                        strait_tolls.append((owner_c, st_toll, t_entry["name"]))

            # ترابری زمینی: وجود مسیر خشکی پیوسته (مرز مستقیم یا ترانزیت خاکی) الزامی است
            if transport_mode == "land":
                s_land_key = seller_c.get("country_key")
                b_land_key = buyer_c.get("country_key")
                if not has_land_trade_route(s_land_key, b_land_key):
                    return False, (
                        f"🚛 **ترابری زمینی ممکن نیست:** مسیر خشکی پیوسته‌ای (مرز مشترک یا ترانزیت زمینی) بین "
                        f"{seller_c['flag']} **{seller_c['name']}** و {buyer_c['flag']} **{buyer_c['name']}** وجود ندارد. "
                        "لطفاً این خرید با ترابری دریایی یا هوایی انجام شود."
                    ), {}

            strait_toll_total = sum(t[1] for t in strait_tolls)
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

            transport_costs = {"sea": 300_000, "land": 1_000_000, "air": 2_000_000,
                               "caspian": config.TRANSPORT_CAPACITY_LIMITS["caspian"]["cost"]}
            t_cost = transport_costs.get(transport_mode, 300_000)

            unit_price = order["unit_price"]
            commodity_cost = buy_amount * unit_price
            total_buyer_cost = commodity_cost + t_cost + strait_toll_total

            if buyer_c["treasury"] < total_buyer_cost:
                return False, f"موجودی خزانه کافی نیست!\nارزش کالا: {format_money(commodity_cost)}\nهزینه ترابری و عوارض: {format_money(t_cost + strait_toll_total)}\nمجموع هزینه: {format_money(total_buyer_cost)}\nخزانه شما: {format_money(buyer_c['treasury'])}", {}

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
            for owner_c, toll_amount, strait_name in strait_tolls:
                cur.execute("UPDATE countries SET treasury = treasury + ? WHERE id = ?", (toll_amount, owner_c["id"]))
                cur.execute(
                    "INSERT INTO transactions (country_id, type, description, amount, created_at) VALUES (?, 'strait_toll', ?, ?, ?)",
                    (owner_c["id"], f"دریافت عوارض ترانزیت {strait_name} از خرید بورس {buyer_c['name']} و {seller_c['name']}", toll_amount, now_str)
                )

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
                "transport_cost": t_cost + strait_toll_total,
                "strait_toll_total": strait_toll_total,
                "total_buyer_cost": total_buyer_cost,
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
    for r_type in ("oil", "gold", "grain", "iron_ore", "microchips", "uranium_ore", "nuclear_fuel", "vaccine_doses"):
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
    if vote_option not in {"yes", "no", "abstain"}:
        return False, "گزینه رای‌گیری نامعتبر است."

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
    """بستن قطعنامه فعال با وضعیت نهایی معتبر."""
    if final_status not in {"passed", "vetoed", "failed"}:
        return False
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE un_resolutions SET status = ? WHERE id = ? AND status = 'active'",
                (final_status, resolution_id),
            )
            return cur.rowcount == 1
    finally:
        conn.close()


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
            return _kill_commander_with_cur(conn.cursor(), country_id, commander_key, reason)
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def revive_commander(country_id: int, commander_key: str) -> bool:
    """انتصاب فرمانده جدید پس از پایان دوره سوگواری و بازسازی فرماندهی."""
    conn = get_connection()
    try:
        with conn:
            return _revive_commander_with_cur(conn.cursor(), country_id, commander_key)
    except Exception:
        return False
    finally:
        conn.close()


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
    if attacker_id == target_id:
        return False, "کشور مهاجم و هدف نمی‌توانند یکسان باشند.", {}
    if isinstance(chips_boost, bool) or not isinstance(chips_boost, int) or chips_boost not in {0, 5}:
        return False, "تقویت عملیاتی نامعتبر است.", {}

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
        (country_id, player_id, statement_type, content[:4000] if content else "", now_str, stmt_date)
    )
    stmt_id = cur.lastrowid
    conn.commit()
    conn.close()
    return stmt_id


def get_recent_statements(limit: int = 50, hours: int | None = 24) -> list[dict]:
    """دریافت لیست تمام بیانیه‌ها و توییت‌های ثبت‌شده در ۲۴ ساعت اخیر یا به ترتیب نزولی با مشخصات کشور."""
    conn = get_connection()
    cur = conn.cursor()
    if hours:
        since = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)).isoformat()
        cur.execute("""
            SELECT s.id, s.country_id, s.player_id, s.statement_type, s.content, s.created_at, s.statement_date,
                   c.name AS country_name, c.flag AS country_flag, c.country_key, c.player_id AS country_owner_id
            FROM daily_statements s
            LEFT JOIN countries c ON s.country_id = c.id
            WHERE s.created_at >= ?
            ORDER BY s.id DESC
            LIMIT ?
        """, (since, limit))
    else:
        cur.execute("""
            SELECT s.id, s.country_id, s.player_id, s.statement_type, s.content, s.created_at, s.statement_date,
                   c.name AS country_name, c.flag AS country_flag, c.country_key, c.player_id AS country_owner_id
            FROM daily_statements s
            LEFT JOIN countries c ON s.country_id = c.id
            ORDER BY s.id DESC
            LIMIT ?
        """, (limit,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_statement_by_id(stmt_id: int) -> dict | None:
    """دریافت مشخصات کامل یک بیانیه با شناسه."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT s.id, s.country_id, s.player_id, s.statement_type, s.content, s.created_at, s.statement_date,
               c.name AS country_name, c.flag AS country_flag, c.country_key, c.player_id AS country_owner_id
        FROM daily_statements s
        LEFT JOIN countries c ON s.country_id = c.id
        WHERE s.id = ?
    """, (stmt_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def delete_statement_by_id(stmt_id: int) -> bool:
    """حذف یک بیانیه از دیتابیس توسط ادمین."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM daily_statements WHERE id = ?", (stmt_id,))
    deleted = cur.rowcount > 0
    conn.commit()
    conn.close()
    return deleted


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
    """ساخت گروه غیردولتی.

    نکته: مجوز گروه، اشتراک VIP نمی‌دهد. قبلاً هر گروه با is_vip = 1 ساخته می‌شد و
    خریدار با یک پرداخت ۱۰۰ هزار تومانی، برای همیشه تخفیف نگهداری ارتش و سقف
    مانور بالاتر می‌گرفت؛ این مزیت حذف شد. اشتراک VIP فقط از مسیر خودش خریداری می‌شود.
    """
    c_key = f"faction_{faction_key}" if faction_key and faction_key in getattr(config, "PREDEFINED_MILITIA_FACTIONS", {}) else f"faction_{player_id}"
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()

    cur.execute("""
        INSERT INTO countries
        (player_id, name, flag, population, treasury, tax_income, daily_income,
         gold, gold_daily, oil_reserves, oil_production, grain, electricity,
         active_personnel, reserve_personnel, last_income_date, created_at, country_key,
         approval_rating, grain_daily, username, tech_level, combat_readiness, microchips, microchips_daily, is_vip)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
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
    catalog = get_equipment_catalog_for(c_key)

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


def get_active_offer_for_country(country_id: int):
    """قفل پیشنهاد فعال صف انتظار روی یک کشور (یا None)."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT player_id, offer_expires_at FROM country_queue "
            "WHERE offered_country_id = ? AND status = 'offered' LIMIT 1",
            (country_id,),
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def release_country_offer(country_id: int) -> int:
    """آزادسازی قفل پیشنهاد صف روی یک کشور؛ خروجی: تعداد ردیف‌های آزادشده."""
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute(
                "UPDATE country_queue SET status = 'waiting', offered_country_id = NULL, "
                "offer_expires_at = NULL WHERE offered_country_id = ? AND status = 'offered'",
                (country_id,),
            )
            return cur.rowcount or 0
    finally:
        conn.close()


def admin_transfer_country_ownership(country_id: int, new_player_id: int, new_username: str = "") -> tuple[bool, str]:
    """واگذاری و انتقال کامل مالکیت یک کشور به بازیکن جدید.

    مرجع نهایی دست ادمین است: قفل پیشنهاد صف، قرنطینه و ردپای مالک قبلی
    همه پاک می‌شوند تا کشور بلافاصله و بدون «قفل» در اختیار بازیکن جدید باشد.
    """
    if is_banned(new_player_id):
        return False, BANNED_MESSAGE
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT id, name, flag FROM countries WHERE player_id = ? AND id != ?", (new_player_id, country_id))
            existing = cur.fetchone()
            if existing:
                return False, f"این بازیکن در حال حاضر رهبر کشور {existing['flag']} {existing['name']} (شناسه {existing['id']}) است."
            cur.execute(
                "UPDATE countries SET player_id = ?, username = ?, previous_player_id = NULL, "
                "quarantined_at = NULL, quarantine_until = NULL WHERE id = ?",
                (new_player_id, new_username or "", country_id))
            cur.execute(
                "UPDATE country_queue SET status = 'waiting', offered_country_id = NULL, "
                "offer_expires_at = NULL WHERE offered_country_id = ? AND status = 'offered'",
                (country_id,))
        add_log(f"admin:{new_player_id}", "admin_country_assign", f"country={country_id} new_player={new_player_id}")
        return True, (f"مالکیت کشور با موفقیت به بازیکن با شناسه `{new_player_id}` واگذار شد.\n"
                      "🔓 هر قفل پیشنهاد صف و قرنطینه روی این کشور آزاد شد.")
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
    """دریافت یا ساخت وضعیت بتل‌پس فصلی برای یک کشور.

    اگر کشور وجود نداشته باشد (حذف‌شده/خیالی)، None برمی‌گرداند تا INSERT با
    کلید خارجی نامعتبر انجام نشود (باگ FOREIGN KEY constraint failed).
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM countries WHERE id = ?", (country_id,))
        if not cur.fetchone():
            return None
        cur.execute("SELECT * FROM battle_pass WHERE country_id = ?", (country_id,))
        row = cur.fetchone()
        if row:
            d = dict(row)
            d["claimed_free_tiers"] = json.loads(d.get("claimed_free_tiers") or "[]")
            d["claimed_premium_tiers"] = json.loads(d.get("claimed_premium_tiers") or "[]")
            d["completed_challenges"] = json.loads(d.get("completed_challenges") or "[]")
            d["challenge_progress"] = json.loads(d.get("challenge_progress") or "{}")
            return d
    finally:
        conn.close()

    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO battle_pass
                (country_id, season, is_premium, current_xp, current_tier, claimed_free_tiers, claimed_premium_tiers, completed_challenges, challenge_progress, created_at, updated_at)
                VALUES (?, ?, 0, 0, 1, '[]', '[]', '[]', '{}', ?, ?)
            """, (country_id, getattr(config, "BATTLE_PASS_SEASON", 1), now_str, now_str))
    finally:
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
    """افزودن XP به بتل‌پس کشور، محاسبه لول‌آپ و ارتقای پله‌ها.

    اگر کشور وجود نداشته باشد (حذف‌شده)، بی‌سروصدا رد می‌شود تا خطای FK ندهد.
    """
    bp = get_or_create_battle_pass(country_id)
    if bp is None:
        return 0, 0, False
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
                    qty = max(0, int(eq["quantity"] or 0) - int(eq["inactive_qty"] or 0))
                    if qty <= 0:
                        continue
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


def reset_all_countries_for_new_season(actor: str = "system") -> tuple[bool, int, str]:
    """سلب مالکیت کامل تمام کشورها و پاکسازی داده‌های فصلی جهت شروع رسمی و عادلانه فصل جدید.

    مخرب‌ترین عملیات بازی — فهرست کشورها/مالک‌ها قبل از پاک شدن بایگانی و لاگ می‌شود.
    """
    conn = get_connection()
    count = 0
    snapshot_summary = ""
    try:
        with conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM countries WHERE player_id > 0 AND country_key != 'un'")
            count = cur.fetchone()[0]

            # بایگانی برای داوری: چه کشورهایی با چه مالک‌هایی ریست می‌شوند
            try:
                import json as _json
                cur.execute(
                    "SELECT id, name, country_key, player_id FROM countries"
                    " WHERE country_key != 'un' ORDER BY id")
                snapshot_summary = _json.dumps(
                    [dict(r) for r in cur.fetchall()], ensure_ascii=False)[:4000]
            except Exception:
                snapshot_summary = "snapshot-failed"

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

        try:
            add_log(actor, "season_reset",
                    f"count={count} | countries={snapshot_summary}")
        except Exception:
            print("[audit-log] failed to log season reset")
        return True, count, f"مالکیت تمام {count} کشور با موفقیت سلب شد و بازی ریست گردید."
    except Exception as e:
        logger.warning(f"Error in reset_all_countries_for_new_season: {e}")
        return False, 0, f"خطا در ریست همگانی: {e}"
    finally:
        conn.close()


# ---------- ابزارهای داوری: خروجی انبار و اعتبارسنجی گزارش ----------

def export_country_inventory_text(country_id: int) -> str:
    """انبار کشور به شکل متنی آماده‌ی کپی در پرامپت هوش مصنوعی.

    همان خروجی `tools/loss_tool.py export` است ولی روی دیتابیس زنده و
    قابل استفاده در پنل تلگرام، چون داور دسترسی ترمینال ندارد.
    """
    c = get_country_by_id(country_id)
    if not c:
        return ""
    assets = get_country_assets(country_id)

    by_cat = {}
    for a in assets:
        if int(a["amount"] or 0) <= 0:
            continue
        by_cat.setdefault(a["category"], []).append(a)

    out = [f"### انبار {c.get('flag', '')} {c['name']}",
           f"خزانه: {int(c['treasury'] or 0):,} دلار | "
           f"پرسنل فعال: {int(c['active_personnel'] or 0):,} نفر | "
           f"ذخایر نفت: {int(c['oil_reserves'] or 0):,} بشکه | "
           f"کلاهک هسته‌ای: {int(c['warheads'] or 0)}", ""]

    for cat, items in by_cat.items():
        label, unit = config.ASSET_CATEGORIES.get(cat, (cat, "عدد"))
        out.append(f"**{label}** (واحد: {unit})")
        for it in sorted(items, key=lambda x: -int(x["amount"] or 0)):
            out.append(f"- {it['equipment_name']} = {int(it['amount']):,}")
        out.append("")

    owned = {k: v for k, v in (get_equipment(country_id) or {}).items() if v}
    if owned:
        out.append("**زیرساخت و صنایع** (واحد: واحد)")
        for k, v in owned.items():
            nm = config.ALL_SHOP_ITEMS.get(k, {}).get("name", k)
            out.append(f"- {nm} = {v}")
        out.append("")

    cmds = get_country_commanders(country_id) or []
    if cmds:
        out.append("**رده فرماندهی** (فقط در صورت ترور صریح در رول)")
        for cm in cmds:
            out.append(f"- {cm['title']}")
        out.append("")

    return "\n".join(out).strip()


def validate_loss_report_text(text: str) -> dict:
    """اعتبارسنجی متن گزارش تلفات — همان بررسی‌های `loss_tool check`.

    خروجی: dict با کلیدهای ok، errors، warnings، info و خلاصه‌ی اثر.
    داور می‌تواند قبل از ثبت، گزارش هوش مصنوعی را با این بسنجد.
    """
    from handlers.losses import (parse_loss_report_text, match_country_by_name,
                                 match_asset_by_name, match_strategic_resource,
                                 is_explicit_strategic, match_commander)

    res = {"ok": False, "errors": [], "warnings": [], "info": [],
           "country": None, "items": 0, "effects": {}}
    try:
        p = parse_loss_report_text(text or "")
    except Exception as e:
        res["errors"].append(f"متن گزارش قابل خواندن نبود: {e}")
        return res

    c = match_country_by_name(p.get("country") or "")
    if not c:
        res["errors"].append(
            f"نام کشور «{p.get('country')}» شناسایی نشد — بات گزارش را رد می‌کند. "
            "نام را دقیقاً مطابق نام داخل بازی بنویسید (مثلاً «انگلیس» نه «بریتانیا»).")
        return res
    res["country"] = f"{c.get('flag', '')} {c['name']}"

    assets = get_country_assets(c["id"])
    commanders = get_country_commanders(c["id"]) or []
    stock = {a["equipment_key"]: int(a["amount"] or 0) for a in assets}
    items = p.get("items") or []
    res["items"] = len(items)
    if not items:
        res["warnings"].append("هیچ قلم تجهیزاتی در گزارش پیدا نشد.")

    used = {}
    for it in items:
        # parse_loss_report_text اقلام را به‌صورت tuple برمی‌گرداند: (نام، تعداد، واحد)
        if isinstance(it, (tuple, list)):
            name = str(it[0]) if len(it) > 0 else ""
            qty = int(it[1] or 0) if len(it) > 1 else 0
        else:
            name = it.get("name") or ""
            qty = int(it.get("qty") or 0)
        if qty <= 0:
            res["warnings"].append(f"«{name}»: مقدار صفر یا نامعتبر — نادیده گرفته می‌شود.")
            continue

        if is_explicit_strategic(name):
            sres = match_strategic_resource(name)
            if sres:
                res["info"].append(f"☢️ {name} → منبع راهبردی ({sres['name']})")
                continue

        cmd = match_commander(name, commanders)
        if cmd:
            res["info"].append(f"🎖️ {name} → فرمانده ({cmd.get('title', '')})")
            continue

        a = match_asset_by_name(name, assets)
        if not a:
            res["errors"].append(f"«{name}» در انبار {c['name']} پیدا نشد.")
            continue

        key = a["equipment_key"]
        used[key] = used.get(key, 0) + qty
        have = stock.get(key, 0)
        if used[key] > have:
            res["errors"].append(
                f"«{a['equipment_name']}»: کسر {used[key]:,} ولی موجودی فقط {have:,} است.")

    human = p.get("human") or {}
    killed = int(human.get("mil") or 0)
    wounded = int(human.get("wounded") or 0)
    civ = int(human.get("civilians") or 0)
    if killed > 0:
        ratio = wounded / killed
        if ratio < 2.0 or ratio > 3.5:
            res["warnings"].append(
                f"نسبت مجروح به کشته {ratio:.1f} به ۱ است — بازه‌ی واقع‌گرایانه ۲.۵ تا ۳.")
        else:
            res["info"].append(f"نسبت مجروح به کشته {ratio:.1f} به ۱ ✅")
    if killed > int(c["active_personnel"] or 0):
        res["errors"].append("تعداد کشته از کل پرسنل فعال کشور بیشتر است.")
    if civ > 50:
        res["warnings"].append(f"غیرنظامی {civ} نفر — بالای سقف عرفی ۵۰ نفر.")

    res["effects"] = {"killed": killed, "wounded": wounded, "civilians": civ}
    res["ok"] = not res["errors"]
    return res


def format_validation_report(v: dict) -> str:
    """متن خوانا از خروجی validate_loss_report_text برای نمایش در تلگرام."""
    if not v:
        return "❌ خطای نامشخص."
    lines = ["🔍 <b>اعتبارسنجی گزارش تلفات</b>", "━━━━━━━━━━━━━━━━━━", ""]
    if v.get("country"):
        lines.append(f"🏳️ کشور: <b>{v['country']}</b>")
        lines.append(f"📦 اقلام شناسایی‌شده: <b>{v['items']}</b>")
        e = v.get("effects") or {}
        if e.get("killed"):
            lines.append(f"👥 {e['killed']:,} کشته | {e['wounded']:,} مجروح | "
                         f"{e.get('civilians', 0):,} غیرنظامی")
        lines.append("")
    for err in v.get("errors", []):
        lines.append(f"❌ {err}")
    for w in v.get("warnings", []):
        lines.append(f"⚠️ {w}")
    for i in v.get("info", []):
        lines.append(f"ℹ️ {i}")
    lines.append("")
    lines.append("✅ <b>گزارش سالم است و قابل ثبت.</b>" if v.get("ok")
                 else "🛑 <b>گزارش ایراد دارد — قبل از ثبت اصلاح شود.</b>")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════
#  سیستم نقش‌ها: مالک، داور
# ═══════════════════════════════════════════════════════════════════
# مالک = config.ADMIN_IDS (تغییرناپذیر از داخل بات، فقط از env)
# داور = رکورد فعال در جدول game_admins، دسترسی محدود

ROLE_OWNER = "owner"
ROLE_REFEREE = "referee"

ROLE_LABELS = {ROLE_OWNER: "👑 مالک", ROLE_REFEREE: "⚖️ داور"}

# امتیاز هر عمل داور
REFEREE_POINTS = {
    "report_validated": 1,     # اعتبارسنجی گزارش
    "report_registered": 5,    # ثبت نهایی گزارش تلفات
    "inventory_export": 0,     # کار روزمره، امتیاز ندارد
    "war_action": 3,           # اقدام در بخش مدیریت جنگ
}


def _init_role_tables(cur):
    cur.execute("""
    CREATE TABLE IF NOT EXISTS game_admins (
        user_id INTEGER PRIMARY KEY,
        role TEXT NOT NULL DEFAULT 'referee',
        display_name TEXT DEFAULT '',
        added_by INTEGER,
        added_at TEXT,
        active INTEGER DEFAULT 1,
        points INTEGER DEFAULT 0,
        note TEXT DEFAULT ''
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS admin_actions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        role TEXT,
        action TEXT NOT NULL,
        target TEXT DEFAULT '',
        details TEXT DEFAULT '',
        points INTEGER DEFAULT 0,
        created_at TEXT NOT NULL
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_admin_actions_user"
                " ON admin_actions(user_id, created_at DESC)")

    # مسدودسازی بازیکنان — فقط مالک (جلوگیری از اسپم درخواست کشور و...)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS banned_players (
        user_id INTEGER PRIMARY KEY,
        reason TEXT DEFAULT '',
        banned_by INTEGER,
        banned_at TEXT NOT NULL,
        active INTEGER NOT NULL DEFAULT 1
    )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_banned_active ON banned_players(active)")


def is_owner(user_id: int) -> bool:
    return int(user_id) in (config.ADMIN_IDS or [])


def get_game_admin(user_id: int) -> dict | None:
    conn = get_connection()
    try:
        r = conn.execute("SELECT * FROM game_admins WHERE user_id = ?", (int(user_id),)).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def is_referee(user_id: int) -> bool:
    """داور فعال است؟ مالک به‌صورت خودکار داور هم هست."""
    if is_owner(user_id):
        return True
    a = get_game_admin(user_id)
    return bool(a and a.get("active") and a.get("role") == ROLE_REFEREE)


def is_playing_restricted(user_id: int) -> bool:
    """این کاربر اجازه ندارد کشور بگیرد؟ داورهای فعال (غیرمالک) محروم‌اند —
    داور نباید همزمان بازیکن باشد تا بی‌طرفی حفظ شود. مالک همیشه آزاد است."""
    if is_owner(user_id):
        return False
    a = get_game_admin(user_id)
    return bool(a and a.get("active") and a.get("role") == ROLE_REFEREE)


PLAY_RESTRICTED_MESSAGE = (
    "⚖️ داورهای فعال نمی‌توانند کشور بگیرند.\n\n"
    "برای بازی، باید ابتدا نقش داوری شما توسط مالک غیرفعال شود."
)


# ─────────────────────────────────────────────────────────────────────────────
# مسدودسازی بازیکن (فقط مالک) — محروم از هر مسیر دریافت کشور
# ─────────────────────────────────────────────────────────────────────────────
def ban_player(user_id: int, reason: str = "", banned_by: int = 0) -> tuple[bool, str]:
    conn = get_connection()
    try:
        with conn:
            row = conn.execute("SELECT active FROM banned_players WHERE user_id = ?",
                               (int(user_id),)).fetchone()
            if row and row["active"]:
                return False, "این کاربر از قبل مسدود است."
            if row:
                conn.execute(
                    "UPDATE banned_players SET active = 1, reason = ?, banned_by = ?,"
                    " banned_at = ? WHERE user_id = ?",
                    (str(reason or "")[:500], int(banned_by),
                     datetime.datetime.now(datetime.timezone.utc).isoformat(),
                     int(user_id)))
            else:
                conn.execute(
                    "INSERT INTO banned_players (user_id, reason, banned_by, banned_at, active)"
                    " VALUES (?, ?, ?, ?, 1)",
                    (int(user_id), str(reason or "")[:500], int(banned_by),
                     datetime.datetime.now(datetime.timezone.utc).isoformat()))
    finally:
        conn.close()
    try:
        add_log(f"admin:{banned_by}", "player_ban",
                f"user_id={int(user_id)} | reason={str(reason or '')[:200]}")
    except Exception:
        pass
    return True, "کاربر مسدود شد."


def unban_player(user_id: int, unbanned_by: int = 0) -> tuple[bool, str]:
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute(
                "UPDATE banned_players SET active = 0 WHERE user_id = ? AND active = 1",
                (int(user_id),))
            ok = cur.rowcount > 0
    finally:
        conn.close()
    if ok:
        try:
            add_log(f"admin:{unbanned_by}", "player_unban", f"user_id={int(user_id)}")
        except Exception:
            pass
        return True, "مسدودی کاربر برداشته شد."
    return False, "این کاربر مسدود نیست."


def is_banned(user_id: int) -> bool:
    conn = get_connection()
    try:
        r = conn.execute("SELECT 1 FROM banned_players WHERE user_id = ? AND active = 1",
                         (int(user_id),)).fetchone()
        return bool(r)
    finally:
        conn.close()


def get_ban_info(user_id: int) -> dict | None:
    conn = get_connection()
    try:
        r = conn.execute("SELECT * FROM banned_players WHERE user_id = ? AND active = 1",
                         (int(user_id),)).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def get_banned_players(limit: int = 100) -> list[dict]:
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM banned_players WHERE active = 1"
            " ORDER BY banned_at DESC LIMIT ?", (max(1, min(500, int(limit))),)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


BANNED_MESSAGE = "🚫 شما از دریافت کشور در بازی «سیاست مدرن» مسدود شده‌اید."


def user_role(user_id: int) -> str | None:
    if is_owner(user_id):
        return ROLE_OWNER
    a = get_game_admin(user_id)
    if a and a.get("active"):
        return a.get("role")
    return None


def add_referee(user_id: int, added_by: int, display_name: str = "") -> tuple[bool, str]:
    user_id = int(user_id)
    if is_owner(user_id):
        return False, "این آیدی مالک بازی است و نیازی به افزودن ندارد."
    now = datetime.datetime.now().isoformat(timespec="seconds")
    conn = get_connection()
    try:
        with conn:
            existing = conn.execute("SELECT active FROM game_admins WHERE user_id = ?",
                                    (user_id,)).fetchone()
            if existing and existing["active"]:
                return False, "این کاربر از قبل داور فعال است."
            conn.execute(
                "INSERT INTO game_admins (user_id, role, display_name, added_by, added_at, active)"
                " VALUES (?,?,?,?,?,1)"
                " ON CONFLICT(user_id) DO UPDATE SET active = 1, role = excluded.role,"
                " display_name = excluded.display_name, added_by = excluded.added_by,"
                " added_at = excluded.added_at",
                (user_id, ROLE_REFEREE, display_name or "", int(added_by), now))
        log_admin_action(added_by, ROLE_OWNER, "referee_added", str(user_id))
        return True, "داور با موفقیت اضافه شد."
    finally:
        conn.close()


def remove_referee(user_id: int, removed_by: int) -> tuple[bool, str]:
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute("UPDATE game_admins SET active = 0 WHERE user_id = ? AND active = 1",
                               (int(user_id),))
        if not cur.rowcount:
            return False, "این کاربر داور فعال نیست."
        log_admin_action(removed_by, ROLE_OWNER, "referee_removed", str(user_id))
        return True, "دسترسی داور سلب شد."
    finally:
        conn.close()


def list_referees(include_inactive: bool = True) -> list[dict]:
    conn = get_connection()
    try:
        q = "SELECT * FROM game_admins"
        if not include_inactive:
            q += " WHERE active = 1"
        q += " ORDER BY active DESC, points DESC, user_id"
        return [dict(r) for r in conn.execute(q).fetchall()]
    finally:
        conn.close()


def log_admin_action(user_id: int, role: str, action: str,
                     target: str = "", details: str = "", points: int = None) -> None:
    """ثبت عمل ادمین/داور و افزودن امتیاز مربوطه."""
    pts = REFEREE_POINTS.get(action, 0) if points is None else int(points)
    now = datetime.datetime.now().isoformat(timespec="seconds")
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                "INSERT INTO admin_actions (user_id, role, action, target, details, points, created_at)"
                " VALUES (?,?,?,?,?,?,?)",
                (int(user_id), role or "", action, str(target)[:200], str(details)[:400], pts, now))
            if pts:
                conn.execute("UPDATE game_admins SET points = COALESCE(points,0) + ?"
                             " WHERE user_id = ?", (pts, int(user_id)))
    except Exception as e:
        print(f"[admin-log] {e}")
    finally:
        conn.close()


def get_admin_actions(user_id: int = None, limit: int = 30) -> list[dict]:
    conn = get_connection()
    try:
        if user_id:
            rows = conn.execute(
                "SELECT * FROM admin_actions WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (int(user_id), int(limit))).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM admin_actions ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def get_referee_scoreboard() -> list[dict]:
    """امتیاز و آمار فعالیت داورها."""
    out = []
    for a in list_referees():
        conn = get_connection()
        try:
            row = conn.execute(
                "SELECT COUNT(*) AS n, COALESCE(SUM(points),0) AS p,"
                " MAX(created_at) AS last FROM admin_actions WHERE user_id = ?",
                (a["user_id"],)).fetchone()
        finally:
            conn.close()
        out.append({**a,
                    "actions": int(row["n"] or 0),
                    "earned": int(row["p"] or 0),
                    "last_active": row["last"] or "—"})
    return sorted(out, key=lambda x: (-x["active"], -x["points"]))


# ─────────────────────────────────────────────────────────────────────────────
# شورش مسلحانه (insurgency.py) — CRUD و اعمال افکت‌ها
# ─────────────────────────────────────────────────────────────────────────────
def get_insurgency(country_id: int) -> dict | None:
    conn = get_connection()
    try:
        r = conn.execute("SELECT * FROM insurgencies WHERE country_id = ?", (int(country_id),)).fetchone()
        return dict(r) if r else None
    finally:
        conn.close()


def get_active_insurgencies(limit: int = 200) -> list[dict]:
    """همه‌ی شورش‌های زنده به‌همراه مشخصات کشورشان (برای پنل ادمین و سقف خبر)."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT i.*, c.name AS country_name, c.flag AS country_flag,
                   c.player_id, c.active_personnel
            FROM insurgencies i JOIN countries c ON c.id = i.country_id
            ORDER BY i.phase DESC, i.fighters DESC LIMIT ?
            """,
            (max(1, min(500, int(limit))),),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def create_insurgency(country_id: int, fighters: int, seed_base: int = 0,
                      now_str: str = None) -> dict:
    conn = get_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO insurgencies (country_id, fighters, boldness, phase, night,
                                          seed_base, created_at, updated_at)
                VALUES (?, ?, 55, 1, 0, ?, ?, ?)
                ON CONFLICT(country_id) DO NOTHING
                """,
                (int(country_id), int(fighters), int(seed_base),
                 now_str or datetime.datetime.now(datetime.timezone.utc).isoformat(),
                 now_str or datetime.datetime.now(datetime.timezone.utc).isoformat()),
            )
    finally:
        conn.close()
    return get_insurgency(country_id)


def delete_insurgency(country_id: int) -> bool:
    conn = get_connection()
    try:
        with conn:
            cur = conn.execute("DELETE FROM insurgencies WHERE country_id = ?", (int(country_id),))
            return cur.rowcount > 0
    finally:
        conn.close()


def insurgency_apply_effects(country_id: int, *, fighters_delta: int = 0,
                             boldness_delta: float = 0.0, approval_delta: int = 0,
                             unrest_floor: float = None, unrest_add: float = 0.0,
                             personnel_delta: int = 0, treasury_delta: int = 0,
                             oil_delta_pct: float = 0.0, oil_delta_units: int = 0,
                             grain_delta_pct: float = 0.0, chips_delta_pct: float = 0.0,
                             outage_item: str = None, phase: int = None,
                             night: int = None, last_tick_date: str = None,
                             actions_count: int = 0, action_date: str = None,
                             neg_cooldown: int = None,
                             truce_betray_night: int = None,
                             slot_key: str = None,
                             guard_slots: int = None) -> dict:
    """اعمال یک‌جای همه‌ی افکت‌های شورش روی کشور + به‌روزرسانی ردیف شورش.

    همه‌ی پارامترها اختیاری‌اند؛ فقط همان‌ها اعمال می‌شوند. خروجی برای لاگ.
    نکته: last_tick_date فقط توسط چرخه‌ی شبانه ست می‌شود تا idempotent بماند؛
    اقدامات دستی (سرکوب/مذاکره) آن را دست نمی‌زنند.
    """
    summary: dict = {}
    conn = get_connection()
    try:
        with conn:
            # ── کشور
            row = conn.execute(
                "SELECT active_personnel, treasury, oil_reserves, grain, microchips"
                " FROM countries WHERE id = ?", (int(country_id),)).fetchone()
            if row:
                new_p = max(0, int(row["active_personnel"] or 0) + int(personnel_delta))
                new_t = int(row["treasury"] or 0) + int(treasury_delta)
                new_o = int(float(row["oil_reserves"] or 0) * (1.0 - float(oil_delta_pct or 0))) + int(oil_delta_units or 0)
                new_o = max(0, new_o)
                new_g = max(0, int(float(row["grain"] or 0) * (1.0 - float(grain_delta_pct or 0))))
                new_c = max(0, int(float(row["microchips"] or 0) * (1.0 - float(chips_delta_pct or 0))))
                conn.execute(
                    "UPDATE countries SET active_personnel = ?, treasury = ?,"
                    " oil_reserves = ?, grain = ?, microchips = ? WHERE id = ?",
                    (new_p, new_t, new_o, new_g, new_c, int(country_id)))
                summary.update(personnel=new_p, treasury=new_t, oil=new_o)

            # ── رضایت و ناآرامی (country_internal)
            ci_row = conn.execute(
                "SELECT unrest FROM country_internal WHERE country_id = ?",
                (int(country_id),)).fetchone()
            if ci_row and (unrest_add or unrest_floor is not None):
                new_unrest = float(ci_row["unrest"] or 0) + float(unrest_add or 0)
                if unrest_floor is not None:
                    new_unrest = max(new_unrest, float(unrest_floor))
                conn.execute("UPDATE country_internal SET unrest = ? WHERE country_id = ?",
                             (new_unrest, int(country_id)))
                summary["unrest"] = new_unrest

            if approval_delta:
                conn.execute(
                    "UPDATE countries SET approval_rating = MAX(0, MIN(100,"
                    " COALESCE(approval_rating, 50) + ?)) WHERE id = ?",
                    (int(approval_delta), int(country_id)))

            # ── خرابکاری: یک واحد از یک سازه خاموش می‌شود
            if outage_item:
                conn.execute(
                    "UPDATE equipment SET inactive_qty = MIN(quantity, COALESCE(inactive_qty,0) + 1)"
                    " WHERE country_id = ? AND item_key = ?",
                    (int(country_id), str(outage_item)))
                summary["outage"] = outage_item

            # ── ردیف شورش
            sets, args = [], []
            if fighters_delta:
                sets.append("fighters = MAX(1, fighters + ?)")
                args.append(int(fighters_delta))
            if boldness_delta:
                sets.append("boldness = MAX(0, MIN(100, boldness + ?))")
                args.append(float(boldness_delta))
            if phase is not None:
                sets.append("phase = ?")
                args.append(int(phase))
            if night is not None:
                sets.append("night = ?")
                args.append(int(night))
            if last_tick_date is not None:
                sets.append("last_tick_date = ?")
                args.append(last_tick_date)
            if actions_count:
                sets.append("actions_today = COALESCE(actions_today,0) + ?")
                args.append(int(actions_count))
            if action_date is not None:
                sets.append("last_action_date = ?")
                args.append(action_date)
            if neg_cooldown is not None:
                sets.append("neg_cooldown = ?")
                args.append(int(neg_cooldown))
            if truce_betray_night is not None:
                sets.append("truce_betray_night = ?")
                args.append(int(truce_betray_night))
            if slot_key is not None:
                sets.append("slot_key = ?")
                args.append(str(slot_key))
            if guard_slots is not None:
                sets.append("guard_slots = ?")
                args.append(int(guard_slots))
            if sets:
                sets.append("updated_at = ?")
                args.append(datetime.datetime.now(datetime.timezone.utc).isoformat())
                args.append(int(country_id))
                conn.execute(f"UPDATE insurgencies SET {', '.join(sets)} WHERE country_id = ?", tuple(args))
    finally:
        conn.close()
    return summary


def insurgency_set_fighters(country_id: int, fighters: int):
    conn = get_connection()
    try:
        with conn:
            conn.execute("UPDATE insurgencies SET fighters = MAX(0, ?), updated_at = ? WHERE country_id = ?",
                         (int(fighters),
                          datetime.datetime.now(datetime.timezone.utc).isoformat(),
                          int(country_id)))
    finally:
        conn.close()


def insurgency_take_hostage(country_id: int) -> str | None:
    """گروگان‌گیری موقت یک فرمانده (بدون مرگ — قاعده‌ی MVP)."""
    conn = get_connection()
    try:
        with conn:
            r = conn.execute(
                "SELECT title FROM country_commanders WHERE country_id = ? AND status = 'active'"
                " ORDER BY id ASC LIMIT 1", (int(country_id),)).fetchone()
            if not r:
                return None
            conn.execute("UPDATE insurgencies SET commander_hostage = ?, updated_at = ?"
                         " WHERE country_id = ?",
                         (r["title"],
                          datetime.datetime.now(datetime.timezone.utc).isoformat(),
                          int(country_id)))
            return r["title"]
    finally:
        conn.close()


def insurgency_free_hostage(country_id: int) -> str | None:
    conn = get_connection()
    try:
        with conn:
            r = conn.execute("SELECT commander_hostage FROM insurgencies WHERE country_id = ?",
                             (int(country_id),)).fetchone()
            if not r or not r["commander_hostage"]:
                return None
            conn.execute("UPDATE insurgencies SET commander_hostage = '', updated_at = ?"
                         " WHERE country_id = ?",
                         (datetime.datetime.now(datetime.timezone.utc).isoformat(),
                          int(country_id)))
            return r["commander_hostage"]
    finally:
        conn.close()


def pick_random_structure_item(country_id: int) -> str | None:
    """یک سازه‌ی فعال تصادفی برای خرابکاری (فقط اقلام فروشگاه = سازه)."""
    import random as _random
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT item_key FROM equipment WHERE country_id = ? AND quantity > 0",
            (int(country_id),)).fetchall()
    finally:
        conn.close()
    import config as _config
    keys = [r["item_key"] for r in rows if r["item_key"] in _config.ALL_SHOP_ITEMS]
    return _random.choice(keys) if keys else None


def country_has_active_war(country_id: int) -> bool:
    """جنگ خارجی فعال: نبرد ثبت‌شده در ۳ روز اخیر (پیش/بعد از این کشور)."""
    cutoff = (datetime.datetime.now(datetime.timezone.utc) -
              datetime.timedelta(days=3)).isoformat()
    conn = get_connection()
    try:
        r = conn.execute(
            """
            SELECT 1 FROM war_results
            WHERE created_at >= ? AND (attacker_id = ? OR defender_id = ?)
            LIMIT 1
            """,
            (cutoff, int(country_id), int(country_id)),
        ).fetchone()
        return bool(r)
    finally:
        conn.close()


def get_internal_state_baseline(country_id: int) -> int:
    """درآمد مالیاتی پایه (روزانه) از country_internal برای محاسبه‌ی هزینه‌ی مذاکره."""
    conn = get_connection()
    try:
        r = conn.execute("SELECT baseline_tax_income FROM country_internal WHERE country_id = ?",
                         (int(country_id),)).fetchone()
        return int(r["baseline_tax_income"] or 0) if r else 0
    finally:
        conn.close()
