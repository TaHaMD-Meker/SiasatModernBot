# -*- coding: utf-8 -*-
"""لغو مالکیت کشور و استخر واگذاری — نسخه‌ی بدون صف.

سیستم صف انتظار (q:join / پیشنهاد ۶ ساعته / اولویت خرید تومانی) به‌طور کامل
حذف شد (دستور مالک). مسیر گرفتن کشور فقط: ‎/start ← انتخاب کشور ← درخواست
معلق ← تایید ادمین. کشورهای لغوشده بلافاصله در استخر آزاد و در منوی انتخاب
کشور قابل درخواست‌اند.

قرنطینه هم حذف شده است: خلع = آزاد فوری، بدون دوره‌ی انتظار و بدون /reclaim.
"""

from __future__ import annotations

import datetime

import database as db


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
# لغو مالکیت
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
    روی همان کشور می‌ماند و بلافاصله به استخر آزاد می‌رود."""
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
    return False, "سیستم قرنطینه حذف شده است؛ کشور لغوشده مستقیم به استخر واگذاری می‌رود.", None


def release_quarantine(country_id: int) -> tuple[bool, str]:
    """(منسوخ) قرنطینه حذف شده — خلع همان لحظه آزاد می‌شود."""
    return False, "سیستم قرنطینه حذف شده است."


def release_all_quarantines() -> tuple[int, list]:
    """(منسوخ) قرنطینه حذف شده."""
    return 0, []


def get_quarantined_countries(limit: int = 100) -> list[dict]:
    """(منسوخ) قرنطینه حذف شده — همیشه خالی."""
    return []


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
