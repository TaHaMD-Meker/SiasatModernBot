# -*- coding: utf-8 -*-
"""قرنطینه‌ی کشور رهاشده و صف انتظار بازیکنان.

چرا قرنطینه: تا امروز سلب مالکیت، کشور را با تمام تجهیزات، ساختمان‌ها و
تاریخچه‌اش پاک می‌کرد. یعنی بازیکنی که یک شب اینترنت نداشت، ماه‌ها زحمتش
از بین می‌رفت. حالا کشور دو روز در قرنطینه می‌ماند: صاحب قبلی می‌تواند
پسش بگیرد، و اگر برنگشت، دست‌نخورده به نفر اول صف می‌رسد.
"""

from __future__ import annotations

import datetime
import logging

import config
import database as db

logger = logging.getLogger(__name__)

QUARANTINE_HOURS = 24        # مهلت بازپس‌گیری برای صاحب قبلی (ساعت) — طبق دستور مالک
OFFER_HOURS = 6              # مهلت پاسخ نفر اول صف
PRIORITY_PAID = 100          # ورود زودهنگام (خرید تومانی)


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _iso(dt: datetime.datetime | None = None) -> str:
    return (dt or _now()).isoformat()


def _parse(raw):
    if not raw:
        return None
    try:
        value = datetime.datetime.fromisoformat(raw)
        return value if value.tzinfo else value.replace(tzinfo=datetime.timezone.utc)
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# قرنطینه
# ─────────────────────────────────────────────────────────────────────────────
def quarantine_country(country_id: int, reason: str = "inactivity") -> tuple[bool, str]:
    """خلع مالکیت بدون پاک‌سازی دارایی — قرنطینه لغو شده؛ کشور بلافاصله
    آزاد و وارد استخر واگذاری می‌شود (دستور مالک: هیچ دوره‌ی انتظاری نباشد)."""
    country = db.get_country_by_id(country_id)
    if not country:
        return False, "کشور یافت نشد."
    if not country.get("player_id"):
        return False, "این کشور هم‌اکنون بی‌صاحب است."

    owner = country.get("player_id")
    conn = db.get_connection()
    try:
        with conn:
            conn.execute(
                """
                UPDATE countries
                SET previous_player_id = NULL, player_id = 0,
                    quarantined_at = NULL, quarantine_until = NULL
                WHERE id = ?
                """,
                (country_id,),
            )
    finally:
        conn.close()

    db.add_log(f"player:{owner}", "country_revoked", f"country={country_id} reason={reason}")
    return True, "مالکیت لغو شد و کشور بلافاصله به استخر واگذاری رفت."


def detach_country_keep_assets(country_id: int, actor: str = "admin") -> tuple[bool, str]:
    """حذف مالکیت بدون پاک‌سازی (دستور ادمین): تمام تجهیزات، خزانه و مشخصات
    روی همان کشور می‌ماند و بلافاصله به استخر آزاد (واگذاری به بازیکن بعدی)
    می‌رود. برخلاف قرنطینه، مهلت بازپس‌گیری برای صاحب قبلی وجود ندارد."""
    country = db.get_country_by_id(country_id)
    if not country:
        return False, "کشور یافت نشد."
    if not country.get("player_id"):
        return False, "این کشور هم‌اکنون بی‌صاحب است."
    owner = country.get("player_id")
    conn = db.get_connection()
    try:
        with conn:
            conn.execute(
                """
                UPDATE countries
                SET previous_player_id = player_id, player_id = 0,
                    quarantined_at = NULL, quarantine_until = NULL
                WHERE id = ?
                """,
                (country_id,),
            )
    finally:
        conn.close()
    db.add_log(f"player:{owner}", "country_detached_keep_assets",
               f"country={country_id} actor={actor}")
    # تنگه‌های تحت کنترل این کشور بلافاصله بازگشایی می‌شوند — کشور بی‌صاحب
    # نمی‌تواند آبراه استراتژیک را بسته/عوارضی نگه دارد.
    try:
        reopened = db.auto_check_and_reopen_straits_if_navy_destroyed()
    except Exception:
        reopened = []
    extra = ""
    if reopened:
        names = "، ".join(r["strait_info"]["name"] for r in reopened)
        extra = (f"\n🌊 به دلیل بی‌صاحب شدن، کنترل بر {len(reopened)} آبراه استراتژیک لغو و بازگشایی شد: {names}")
    return True, (f"مالکیت کشور {country.get('flag', '')} {country.get('name', '')} حذف شد؛ "
                  "تجهیزات و مشخصات حفظ ماند و کشور به استخر واگذاری رفت." + extra)


def reclaim_country(player_id: int) -> tuple[bool, str, dict | None]:
    """بازپس‌گیری کشور — با لغو قرنطینه دیگر مهلتی وجود ندارد؛ همیشه رد."""
    return False, "سیستم قرنطینه حذف شده است؛ کشور لغوشده مستقیم به صف واگذاری می‌رود.", None


def release_quarantine(country_id: int) -> tuple[bool, str]:
    """(منسوخ) قرنطینه حذف شده — خلع همان لحظه آزاد می‌شود."""
    return False, "سیستم قرنطینه حذف شده است."


def release_all_quarantines() -> tuple[int, list]:
    """(منسوخ) قرنطینه حذف شده."""
    return 0, []


def get_quarantined_countries(limit: int = 100) -> list[dict]:
    """(منسوخ) قرنطینه حذف شده — همیشه خالی."""
    return []


def release_expired_quarantines(now_dt: datetime.datetime | None = None) -> list[dict]:
    """(منسوخ) قرنطینه حذف شده؛ فقط رکوردهای میراثی قدیمی را پاک می‌کند."""
    released = []
    for country in db.get_all_countries():
        if country.get("quarantine_until"):
            conn = db.get_connection()
            try:
                with conn:
                    conn.execute(
                        "UPDATE countries SET quarantine_until = NULL, quarantined_at = NULL,"
                        " previous_player_id = NULL WHERE id = ?",
                        (country["id"],),
                    )
            finally:
                conn.close()
            released.append(db.get_country_by_id(country["id"]))
    return released


def get_free_countries(limit: int | None = None) -> list[dict]:
    """کشورهای بی‌صاحب، آماده‌ی واگذاری فوری (قرنطینه لغو شده)."""
    conn = db.get_connection()
    try:
        q = ("SELECT * FROM countries WHERE player_id = 0 AND quarantine_until IS NULL"
             " AND country_key NOT LIKE 'faction_%' ORDER BY id ASC")
        if limit:
            q += f" LIMIT {max(1, min(200, int(limit)))}"
        rows = conn.execute(q).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# صف انتظار
# ─────────────────────────────────────────────────────────────────────────────
def join_queue(player_id: int, first_name: str = "", username: str = "",
               preferred_country_key: str | None = None, priority: int = 0):
    """افزودن بازیکن به صف. اگر از قبل در صف باشد، جایگاهش حفظ می‌شود."""
    if db.is_banned(player_id):
        return False, db.BANNED_MESSAGE, None
    if db.is_playing_restricted(player_id):
        return False, db.PLAY_RESTRICTED_MESSAGE, None
    if db.get_country_by_player(player_id):
        return False, "شما هم‌اکنون کشور دارید.", None
    conn = db.get_connection()
    try:
        with conn:
            existing = conn.execute(
                "SELECT * FROM country_queue WHERE player_id = ?", (player_id,)
            ).fetchone()
            if existing and existing["status"] in ("waiting", "offered"):
                return False, "شما از قبل در صف هستید.", dict(existing)
            conn.execute(
                """
                INSERT INTO country_queue (player_id, first_name, username, preferred_country_key, priority, status, joined_at)
                VALUES (?, ?, ?, ?, ?, 'waiting', ?)
                ON CONFLICT(player_id) DO UPDATE SET
                    status = 'waiting', priority = excluded.priority,
                    preferred_country_key = excluded.preferred_country_key,
                    offered_country_id = NULL, offer_expires_at = NULL,
                    joined_at = excluded.joined_at, resolved_at = NULL
                """,
                (player_id, first_name, username, preferred_country_key, int(priority), _iso()),
            )
    finally:
        conn.close()
    return True, "به صف انتظار اضافه شدید.", get_queue_entry(player_id)


def leave_queue(player_id: int) -> bool:
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.execute("DELETE FROM country_queue WHERE player_id = ?", (player_id,))
            return cur.rowcount > 0
    finally:
        conn.close()


def get_queue_entry(player_id: int) -> dict | None:
    conn = db.get_connection()
    try:
        row = conn.execute("SELECT * FROM country_queue WHERE player_id = ?", (player_id,)).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_queue(status: str = "waiting", limit: int = 200) -> list[dict]:
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM country_queue WHERE status = ? ORDER BY priority DESC, id ASC LIMIT ?",
            (status, max(1, min(500, int(limit)))),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def queue_position(player_id: int) -> int | None:
    entry = get_queue_entry(player_id)
    if not entry or entry["status"] != "waiting":
        return None
    conn = db.get_connection()
    try:
        row = conn.execute(
            """
            SELECT COUNT(*) AS n FROM country_queue
            WHERE status = 'waiting'
              AND (priority > ? OR (priority = ? AND id < ?))
            """,
            (entry["priority"], entry["priority"], entry["id"]),
        ).fetchone()
        return int(row["n"] or 0) + 1
    finally:
        conn.close()


def set_priority(player_id: int, priority: int = PRIORITY_PAID) -> bool:
    """ورود زودهنگام — بازیکن به ابتدای صف می‌رود."""
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.execute(
                "UPDATE country_queue SET priority = ? WHERE player_id = ? AND status = 'waiting'",
                (int(priority), player_id),
            )
            return cur.rowcount > 0
    finally:
        conn.close()


def _pick_country_for(entry: dict, free: list[dict]) -> dict | None:
    """کشور مناسب برای این بازیکن؛ اگر کشور دلخواه خریده باشد، همان اولویت دارد."""
    preferred = entry.get("preferred_country_key")
    if preferred:
        for country in free:
            if country.get("country_key") == preferred:
                return country
    return free[0] if free else None


def process_queue(now_dt: datetime.datetime | None = None) -> dict:
    """موتور صف: انقضای پیشنهادها، آزادسازی قرنطینه و پیشنهاد به نفر بعدی.

    خروجی برای اطلاع‌رسانی استفاده می‌شود؛ خود این تابع پیامی نمی‌فرستد.
    """
    now_dt = now_dt or _now()
    result = {"released": [], "expired": [], "offered": []}

    result["released"] = [c for c in release_expired_quarantines(now_dt) if c]

    # پیشنهادهای بی‌پاسخ آزاد می‌شوند تا صف قفل نشود
    for entry in get_queue("offered", 200):
        expires = _parse(entry.get("offer_expires_at"))
        if expires and now_dt >= expires:
            conn = db.get_connection()
            try:
                with conn:
                    # بی‌پاسخ‌گذاشتن پیشنهاد، بازیکن را به ته صف می‌برد.
                    # بدون این، همان نفر بلافاصله دوباره اول صف می‌شد و صف قفل می‌ماند.
                    conn.execute(
                        "UPDATE country_queue SET status = 'waiting', offered_country_id = NULL,"
                        " offer_expires_at = NULL, priority = priority - 1 WHERE id = ?",
                        (entry["id"],),
                    )
            finally:
                conn.close()
            result["expired"].append(entry)

    free = get_free_countries()
    if not free:
        return result

    reserved = {e["offered_country_id"] for e in get_queue("offered", 200) if e.get("offered_country_id")}
    free = [c for c in free if c["id"] not in reserved]

    for entry in get_queue("waiting", 200):
        if not free:
            break
        country = _pick_country_for(entry, free)
        if not country:
            break
        conn = db.get_connection()
        try:
            with conn:
                cur = conn.execute(
                    """
                    UPDATE country_queue SET status = 'offered', offered_country_id = ?, offer_expires_at = ?
                    WHERE id = ? AND status = 'waiting'
                    """,
                    (country["id"], _iso(now_dt + datetime.timedelta(hours=OFFER_HOURS)), entry["id"]),
                )
                claimed = cur.rowcount == 1
        finally:
            conn.close()
        if claimed:
            free = [c for c in free if c["id"] != country["id"]]
            result["offered"].append({"entry": get_queue_entry(entry["player_id"]), "country": country})
    return result


def accept_offer(player_id: int) -> tuple[bool, str, dict | None]:
    """پذیرش پیشنهاد توسط بازیکن. اتمیک است تا دو نفر یک کشور نگیرند."""
    if db.is_banned(player_id):
        return False, db.BANNED_MESSAGE, None
    if db.is_playing_restricted(player_id):
        return False, db.PLAY_RESTRICTED_MESSAGE, None
    entry = get_queue_entry(player_id)
    if not entry or entry["status"] != "offered":
        return False, "پیشنهاد فعالی برای شما وجود ندارد.", None
    expires = _parse(entry.get("offer_expires_at"))
    if expires and _now() > expires:
        return False, "مهلت پذیرش این پیشنهاد تمام شده است.", None
    if db.get_country_by_player(player_id):
        return False, "شما هم‌اکنون کشور دارید.", None

    country_id = entry.get("offered_country_id")
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.execute(
                "UPDATE countries SET player_id = ? WHERE id = ? AND player_id = 0 AND quarantine_until IS NULL",
                (player_id, country_id),
            )
            if cur.rowcount != 1:
                conn.execute(
                    "UPDATE country_queue SET status = 'waiting', offered_country_id = NULL,"
                    " offer_expires_at = NULL WHERE player_id = ?",
                    (player_id,),
                )
                return False, "این کشور دیگر در دسترس نیست. دوباره در صف قرار گرفتید.", None
            conn.execute(
                "UPDATE country_queue SET status = 'done', resolved_at = ? WHERE player_id = ?",
                (_iso(), player_id),
            )
    finally:
        conn.close()

    db.add_log(f"player:{player_id}", "queue_country_claimed", f"country={country_id}")
    return True, "کشور به شما واگذار شد.", db.get_country_by_id(country_id)


def decline_offer(player_id: int) -> bool:
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.execute(
                "UPDATE country_queue SET status = 'waiting', offered_country_id = NULL,"
                " offer_expires_at = NULL WHERE player_id = ? AND status = 'offered'",
                (player_id,),
            )
            return cur.rowcount > 0
    finally:
        conn.close()


def queue_stats() -> dict:
    conn = db.get_connection()
    try:
        waiting = conn.execute("SELECT COUNT(*) AS n FROM country_queue WHERE status = 'waiting'").fetchone()["n"]
        offered = conn.execute("SELECT COUNT(*) AS n FROM country_queue WHERE status = 'offered'").fetchone()["n"]
        done = conn.execute("SELECT COUNT(*) AS n FROM country_queue WHERE status = 'done'").fetchone()["n"]
    finally:
        conn.close()
    return {
        "waiting": int(waiting or 0),
        "offered": int(offered or 0),
        "done": int(done or 0),
        "free_countries": len(get_free_countries()),
        "quarantined": len(get_quarantined_countries(200)),
    }
