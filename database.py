# -*- coding: utf-8 -*-
"""
لایه دیتابیس بازی (SQLite).
شامل مدیریت کشورها، دارایی‌های اختصاصی نظامی (Country Assets System)، همگام‌سازی اتوماتیک دیتابیس با آخرین کاتالوگ و خرید اتومیک.
"""

import os
import sqlite3
import datetime
import config

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
        username TEXT
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

    conn.commit()
    conn.close()

    # همگام‌سازی خودکار دیتابیس با جدیدترین کاتالوگ در زمان راه‌اندازی
    try:
        sync_all_country_assets_to_catalog()
    except Exception:
        pass


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
        "approval_rating", "grain_daily"
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
                return False, f"⚠️ تجهیز **{asset_dict['equipment_name']}** یک سلاح وارداتی است و کشور شما خط تولید بومی آن را ندارد. امکان خرید مجدد در فروشگاه وجود ندارد.", asset_dict

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

            cur.execute("SELECT treasury, oil_reserves FROM countries WHERE id = ?", (country_id,))
            row = cur.fetchone()
            if not row:
                return False, "کشور پیدا نشد."

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


def create_trade_contract(proposer_id: int, recipient_id: int, offered_type: str, offered_amount: int, requested_type: str, requested_amount: int, transport_payer: str = "seller", transport_cost: int = 0, offered_key: str = None) -> int:
    conn = get_connection()
    cur = conn.cursor()
    now_str = datetime.datetime.now(datetime.timezone.utc).isoformat()
    cur.execute("""
        INSERT INTO trade_contracts
        (proposer_id, recipient_id, offered_type, offered_key, offered_amount, requested_type, requested_amount, transport_payer, transport_cost, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
    """, (proposer_id, recipient_id, offered_type, offered_key, offered_amount, requested_type, requested_amount, transport_payer, transport_cost, now_str))
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

            c_min, c_max = _ordered_pair(p_id, r_id)
            cur.execute("SELECT status FROM diplomatic_relations WHERE country1_id = ? AND country2_id = ?", (c_min, c_max))
            rel_row = cur.fetchone()
            if rel_row and rel_row["status"] == "sanctioned":
                return False, "امکان انعقاد قرارداد یا انتقال تجهیزات با کشور تحریم‌شده وجود ندارد."

            cur.execute("SELECT * FROM countries WHERE id = ?", (p_id,))
            prop_c = cur.fetchone()
            cur.execute("SELECT * FROM countries WHERE id = ?", (r_id,))
            recip_c = cur.fetchone()

            if not prop_c or not recip_c:
                return False, "یکی از طرفین قرارداد یافت نشد."

            p_c = dict(prop_c)
            r_c = dict(recip_c)

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
