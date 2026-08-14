# -*- coding: utf-8 -*-
"""
لایه دیتابیس بازی.
از SQLite استفاده می‌کنیم چون فایلیه و نیاز به سرور جدا نداره.
"""

import sqlite3
import json
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
        created_at TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS equipment (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL,
        item_key TEXT NOT NULL,
        quantity INTEGER DEFAULT 0,
        UNIQUE(country_id, item_key),
        FOREIGN KEY(country_id) REFERENCES countries(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        country_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        description TEXT,
        amount INTEGER,
        created_at TEXT,
        FOREIGN KEY(country_id) REFERENCES countries(id)
    )
    """)

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

def create_country(player_id: int, name: str, flag: str = "🏳️"):
    conn = get_connection()
    cur = conn.cursor()
    sv = config.STARTING_VALUES
    cur.execute("""
        INSERT INTO countries
        (player_id, name, flag, population, treasury, tax_income, daily_income,
         gold, gold_daily, oil_reserves, oil_production, grain, electricity,
         active_personnel, reserve_personnel, last_income_date, created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        player_id, name, flag,
        sv["population"], sv["treasury"], sv["tax_income"], sv["daily_income"],
        sv["gold"], sv["gold_daily"], sv["oil_reserves"], sv["oil_production"],
        sv["grain"], sv["electricity"], sv["active_personnel"], sv["reserve_personnel"],
        None, datetime.datetime.utcnow().isoformat()
    ))
    conn.commit()
    conn.close()


def get_country_by_player(player_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM countries WHERE player_id = ?", (player_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_countries():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM countries")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_country_field(country_id: int, field: str, value):
    # لیست سفید فیلدهای مجاز، برای جلوگیری از SQL injection
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
    """مبلغ delta رو به خزانه اضافه می‌کنه (می‌تونه منفی باشه برای کسر)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET treasury = treasury + ? WHERE id = ?", (delta, country_id))
    conn.commit()
    conn.close()


def adjust_oil(country_id: int, delta: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET oil_reserves = oil_reserves + ? WHERE id = ?", (delta, country_id))
    conn.commit()
    conn.close()


# ---------- تجهیزات ----------

def add_equipment(country_id: int, item_key: str, quantity: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT quantity FROM equipment WHERE country_id=? AND item_key=?", (country_id, item_key))
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE equipment SET quantity = quantity + ? WHERE country_id=? AND item_key=?",
                    (quantity, country_id, item_key))
    else:
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


def remove_equipment(country_id: int, item_key: str, quantity: int) -> bool:
    """اگر موجودی کافی نبود False برمی‌گردونه و چیزی کم نمی‌کنه."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT quantity FROM equipment WHERE country_id=? AND item_key=?", (country_id, item_key))
    row = cur.fetchone()
    if not row or row["quantity"] < quantity:
        conn.close()
        return False
    cur.execute("UPDATE equipment SET quantity = quantity - ? WHERE country_id=? AND item_key=?",
                (quantity, country_id, item_key))
    conn.commit()
    conn.close()
    return True


# ---------- تراکنش‌ها و لاگ ----------

def add_transaction(country_id: int, type_: str, description: str, amount: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO transactions (country_id, type, description, amount, created_at)
        VALUES (?,?,?,?,?)
    """, (country_id, type_, description, amount, datetime.datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()


def add_log(actor: str, action: str, details: str = ""):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO logs (actor, action, details, created_at)
        VALUES (?,?,?,?)
    """, (actor, action, details, datetime.datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()
