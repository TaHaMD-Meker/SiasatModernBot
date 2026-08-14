# -*- coding: utf-8 -*-
"""
لایه دیتابیس بازی (SQLite).
شامل توابع ساخت دیتابیس، مدیریت کشورها، تجهیزات، تراکنش‌ها و پنل ادمین.
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

    # مهاجرت ساده: اگر دیتابیس قبلاً بدون این ستون یا ایندکس ساخته شده
    try:
        cur.execute("ALTER TABLE countries ADD COLUMN country_key TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cur.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_countries_country_key ON countries(country_key)")
    except sqlite3.OperationalError:
        pass

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
    sv = config.STARTING_VALUES
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
    conn.commit()
    conn.close()


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
    """کشور را با country_id همراه تمامی تجهیزات و تراکنش‌هایش حذف می‌کند."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM countries WHERE id = ?", (country_id,))
    if not cur.fetchone():
        conn.close()
        return False
    cur.execute("DELETE FROM equipment WHERE country_id = ?", (country_id,))
    cur.execute("DELETE FROM transactions WHERE country_id = ?", (country_id,))
    cur.execute("DELETE FROM countries WHERE id = ?", (country_id,))
    conn.commit()
    conn.close()
    return True


def delete_country_by_player(player_id: int) -> bool:
    """کشور یک بازیکن را با player_id حذف می‌کند."""
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
    return dict(row) if row else None


def get_all_countries():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM countries ORDER BY id ASC")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_country_field(country_id: int, field: str, value):
    """به‌روزرسانی امن یک فیلد مشخص از جدول کشورهای یک کشور."""
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
    """مبلغ delta رو به خزانه اضافه می‌کنه (می‌تونه منفی باشه)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET treasury = treasury + ? WHERE id = ?", (delta, country_id))
    conn.commit()
    conn.close()


def adjust_gold(country_id: int, delta: int):
    """مقدار delta رو به طلا اضافه می‌کنه."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET gold = gold + ? WHERE id = ?", (delta, country_id))
    conn.commit()
    conn.close()


def adjust_oil(country_id: int, delta: int):
    """مقدار delta رو به ذخایر نفت اضافه می‌کنه."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET oil_reserves = oil_reserves + ? WHERE id = ?", (delta, country_id))
    conn.commit()
    conn.close()


def adjust_oil_production(country_id: int, delta: int):
    """مقدار delta رو به نرخ تولید روزانه نفت اضافه می‌کنه."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE countries SET oil_production = oil_production + ? WHERE id = ?", (delta, country_id))
    conn.commit()
    conn.close()


# ---------- خرید امن کالا (Atomic Transaction) ----------

def buy_item_transaction(country_id: int, item_key: str, quantity: int, total_price: int, item_name: str) -> tuple[bool, str]:
    """
    خرید امن و اتومیک با تراکنش یکپارچه SQLite برای جلوگیری از Race Condition و کسر پول بدون اعطای کالا.
    خروجی: (موفقیت: bool, پیام: str)
    """
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
                            (country_id, item_key, quantity))

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


# ---------- تجهیزات ----------

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


def set_equipment_quantity(country_id: int, item_key: str, quantity: int):
    """تنظیم دقیق تعداد تجهیزات (برای ادمین)."""
    conn = get_connection()
    cur = conn.cursor()
    quantity = max(0, quantity)
    cur.execute("SELECT quantity FROM equipment WHERE country_id=? AND item_key=?", (country_id, item_key))
    row = cur.fetchone()
    if row:
        if quantity == 0:
            cur.execute("DELETE FROM equipment WHERE country_id=? AND item_key=?", (country_id, item_key))
        else:
            cur.execute("UPDATE equipment SET quantity = ? WHERE country_id=? AND item_key=?",
                        (quantity, country_id, item_key))
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


def remove_equipment(country_id: int, item_key: str, quantity: int) -> bool:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT quantity FROM equipment WHERE country_id=? AND item_key=?", (country_id, item_key))
    row = cur.fetchone()
    if not row or row["quantity"] < quantity:
        conn.close()
        return False
    new_qty = row["quantity"] - quantity
    if new_qty <= 0:
        cur.execute("DELETE FROM equipment WHERE country_id=? AND item_key=?", (country_id, item_key))
    else:
        cur.execute("UPDATE equipment SET quantity = ? WHERE country_id=? AND item_key=?",
                    (new_qty, country_id, item_key))
    conn.commit()
    conn.close()
    return True


# ---------- تراکنش‌ها، آمار و لاگ ----------

def get_game_stats():
    """محاسبه آمار کلی بازی برای ادمین."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) as count, SUM(treasury) as total_treasury, SUM(gold) as total_gold, SUM(oil_reserves) as total_oil FROM countries")
    row = cur.fetchone()

    cur.execute("SELECT SUM(quantity) as total_equip FROM equipment")
    eq_row = cur.fetchone()

    conn.close()

    return {
        "countries_count": row["count"] or 0,
        "total_treasury": row["total_treasury"] or 0,
        "total_gold": row["total_gold"] or 0,
        "total_oil": row["total_oil"] or 0,
        "total_equipment": eq_row["total_equip"] or 0,
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
