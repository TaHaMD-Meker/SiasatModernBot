# -*- coding: utf-8 -*-
"""
لایه دیتابیس بازی (SQLite).
شامل مدیریت کشورها، دارایی‌های اختصاصی نظامی (Country Assets)، خرید اتومیک، و پنل ادمین.
"""

import sqlite3
import datetime
import config

def get_connection():
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
        country_key TEXT UNIQUE
    )
    """)

    try:
        cur.execute("ALTER TABLE countries ADD COLUMN country_key TEXT")
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
        FOREIGN KEY(country_id) REFERENCES countries(id) ON DELETE CASCADE,
        UNIQUE(country_id, equipment_key)
    )
    """)

    # جدول عمومی غیرنظامی/قدیمی تجهیزات
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

    # لاگ‌ها
    cur.execute("""
    CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        actor TEXT,
        action TEXT,
        details TEXT,
        created_at TEXT
    )
    """)

    conn.commit()
    conn.close()


# ---------- کشورها ----------

def create_country(player_id: int, name: str, flag: str = "🏳️", country_key: str = None):
    conn = get_connection()
    cur = conn.cursor()

    # بررسی مقادیر اولیه اختصاصی کشور یا مقادیر پیش‌فرض
    sv = config.COUNTRY_STARTING_OVERRIDES.get(country_key, config.STARTING_VALUES)

    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur.execute("""
        INSERT INTO countries
        (player_id, name, flag, population, treasury, tax_income, daily_income,
         gold, gold_daily, oil_reserves, oil_production, grain, electricity,
         active_personnel, reserve_personnel, last_income_date, created_at, country_key)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        player_id, name, flag,
        sv["population"], sv["treasury"], sv["tax_income"], sv["daily_income"],
        sv["gold"], sv["gold_daily"], sv["oil_reserves"], sv["oil_production"],
        sv["grain"], sv["electricity"], sv["active_personnel"], sv["reserve_personnel"],
        None, now_str, country_key
    ))
    country_id = cur.lastrowid
    conn.commit()
    conn.close()

    # سیید کردن اولیه دارایی‌های تخصصی کشور
    if country_id and country_key:
        seed_country_assets(country_id, country_key)


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
        "active_personnel", "reserve_personnel", "last_income_date", "name", "flag"
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


# ---------- سیستم دارایی‌های اختصاصی کشورها (Country Assets System) ----------

def seed_country_assets(country_id: int, country_key: str):
    conn = get_connection()
    cur = conn.cursor()

    catalog = config.COUNTRY_EQUIPMENT_CATALOG.get(country_key, config.DEFAULT_COUNTRY_EQUIPMENT)

    for item in catalog:
        cur.execute("""
            INSERT OR IGNORE INTO country_assets
            (country_id, country_key, category, equipment_name, equipment_key, amount, buy_price, maintenance_cost)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            country_id, country_key, item["category"], item["name"], item["key"],
            item["initial"], item["price"], item.get("maint", 0)
        ))

    conn.commit()
    conn.close()


def get_country_assets(country_id: int, category: str = None):
    conn = get_connection()
    cur = conn.cursor()
    if category and category != "all":
        cur.execute("SELECT * FROM country_assets WHERE country_id = ? AND category = ? ORDER BY id ASC", (country_id, category))
    else:
        cur.execute("SELECT * FROM country_assets WHERE country_id = ? ORDER BY category, id ASC", (country_id,))
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
            cur.execute("SELECT treasury FROM countries WHERE id = ?", (country_id,))
            row = cur.fetchone()
            if not row:
                return False, "کشور پیدا نشد."

            if row["treasury"] < total_price:
                return False, f"موجودی کافی نیست! قیمت: {total_price} | خزانه: {row['treasury']}"

            cur.execute("UPDATE countries SET treasury = treasury - ? WHERE id = ?", (total_price, country_id))

            cur.execute("SELECT quantity FROM equipment WHERE country_id=? AND item_key=?", (country_id, item_key))
            eq_row = cur.fetchone()
            if eq_row:
                cur.execute("UPDATE equipment SET quantity = quantity + ? WHERE country_id=? AND item_key=?",
                            (quantity, country_id, item_key))
            else:
                cur.execute("INSERT INTO equipment (country_id, item_key, quantity) VALUES (?,?,?)",
                            (quantity, country_id, item_key))

            now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
            cur.execute("""
                INSERT INTO transactions (country_id, type, description, amount, created_at)
                VALUES (?,?,?,?,?)
            """, (country_id, "purchase", f"خرید {item_name} x{quantity}", -total_price, now_str))

        return True, "خرید با موفقیت انجام شد."
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
                        (quantity, country_id, item_key))
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
