# -*- coding: utf-8 -*-
"""هسته‌ی تورنومنت فصلی «سیاست مدرن».

این ماژول عمداً فصل را خودکار فعال نمی‌کند. ادمین یک پیش‌نویس می‌سازد و
فقط با دکمه‌ی فعال‌سازی آن را شروع می‌کند. امتیازها سقف نهایی ندارند و از
رشد کشور، رویدادهای تأییدشده و snapshotهای دوره‌ای ساخته می‌شوند.
"""

from __future__ import annotations

import datetime
import json
import logging
import uuid

import config
import database as db

logger = logging.getLogger(__name__)

DRAFT = "draft"
ACTIVE = "active"
PAUSED = "paused"
ENDED = "ended"
OPEN_STATUSES = (DRAFT, ACTIVE, PAUSED)

RESOURCE_FIELDS = (
    "treasury",
    "daily_income",
    "tax_income",
    "gold",
    "oil_reserves",
    "grain",
    "iron_ore",
    "microchips",
    "uranium_ore",
    "nuclear_fuel",
)

FORCE_FACTORS = {
    "Aircraft": 1.50,
    "UAV": 0.85,
    "Ground Forces": 1.00,
    "Artillery": 1.10,
    "Navy": 1.40,
    "Missiles": 1.25,
    "Air Defense": 1.35,
}

CATEGORY_LABELS = {
    "economy": "اقتصاد و توسعه",
    "military": "قدرت نظامی و دفاع",
    "diplomacy": "دیپلماسی و تجارت",
    "activity": "فعالیت و رول‌پلی",
    "objectives": "اهداف استراتژیک",
    "stability": "ثبات و مدیریت بحران",
}


def _now() -> datetime.datetime:
    return datetime.datetime.now(datetime.timezone.utc)


def _iso(dt: datetime.datetime | None = None) -> str:
    return (dt or _now()).isoformat()


def _parse_dt(raw: str | None) -> datetime.datetime | None:
    if not raw:
        return None
    try:
        value = datetime.datetime.fromisoformat(raw)
        if value.tzinfo is None:
            value = value.replace(tzinfo=datetime.timezone.utc)
        return value.astimezone(datetime.timezone.utc)
    except (TypeError, ValueError):
        return None


def _json_load(raw, default):
    try:
        value = json.loads(raw or "")
        return value if value is not None else default
    except (TypeError, ValueError, json.JSONDecodeError):
        return default


def _season_dict(row):
    return dict(row) if row else None


def _default_scoring_config() -> dict:
    return dict(getattr(config, "TOURNAMENT_SCORE_WEIGHTS", {
        "economy": 30,
        "military": 30,
        "diplomacy": 18,
        "activity": 12,
        "objectives": 7,
        "stability": 3,
    }))


def get_season(season_id: int):
    conn = db.get_connection()
    try:
        row = conn.execute("SELECT * FROM tournament_seasons WHERE id = ?", (season_id,)).fetchone()
        return _season_dict(row)
    finally:
        conn.close()


def get_open_season():
    conn = db.get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM tournament_seasons WHERE status IN ('draft', 'active', 'paused') ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return _season_dict(row)
    finally:
        conn.close()


def get_active_season():
    conn = db.get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM tournament_seasons WHERE status = 'active' ORDER BY id DESC LIMIT 1"
        ).fetchone()
        return _season_dict(row)
    finally:
        conn.close()


def get_latest_season():
    """آخرین فصل برای نمایش جدول نهایی پس از پایان مسابقه."""
    conn = db.get_connection()
    try:
        row = conn.execute("SELECT * FROM tournament_seasons ORDER BY id DESC LIMIT 1").fetchone()
        return _season_dict(row)
    finally:
        conn.close()


def list_seasons(limit: int = 10) -> list[dict]:
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM tournament_seasons ORDER BY id DESC LIMIT ?", (max(1, min(50, int(limit))),)
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def create_draft(title: str | None = None, duration_days: int | None = None, prize_text: str | None = None):
    """ساخت پیش‌نویس؛ در صورت وجود فصل باز، فصل دوم ساخته نمی‌شود."""
    existing = get_open_season()
    if existing:
        return False, "یک فصل پیش‌نویس یا فعال از قبل وجود دارد.", existing

    try:
        duration = int(duration_days or getattr(config, "TOURNAMENT_DEFAULT_DURATION_DAYS", 7))
    except (TypeError, ValueError):
        duration = 7
    if duration < 1 or duration > 30:
        return False, "مدت فصل باید بین ۱ تا ۳۰ روز باشد.", None

    title = (title or getattr(config, "TOURNAMENT_DEFAULT_TITLE", "فصل اول رقابت سیاست مدرن")).strip()[:120]
    prize_text = (prize_text or getattr(config, "TOURNAMENT_DEFAULT_PRIZE_TEXT", "جایزه نقدی طبق اطلاعیه رسمی مدیریت")).strip()[:300]
    if not title:
        return False, "عنوان فصل نمی‌تواند خالی باشد.", None

    now = _iso()
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO tournament_seasons
                (title, status, duration_days, prize_text, scoring_config, created_at)
                VALUES (?, 'draft', ?, ?, ?, ?)
                """,
                (title, duration, prize_text, json.dumps(_default_scoring_config()), now),
            )
            season_id = cur.lastrowid
        return True, "پیش‌نویس فصل تورنومنت ساخته شد.", get_season(season_id)
    except Exception as exc:
        logger.exception("Could not create tournament draft")
        return False, f"خطا در ساخت فصل: {exc}", None


def update_draft(season_id: int, title: str | None = None, duration_days: int | None = None, prize_text: str | None = None):
    season = get_season(season_id)
    if not season:
        return False, "فصل یافت نشد.", None
    if season["status"] != DRAFT:
        return False, "فقط پیش‌نویس فصل قابل ویرایش است.", season

    new_title = (title if title is not None else season["title"]).strip()[:120]
    new_prize = (prize_text if prize_text is not None else season.get("prize_text", "")).strip()[:300]
    try:
        new_duration = int(duration_days if duration_days is not None else season["duration_days"])
    except (TypeError, ValueError):
        return False, "مدت فصل باید عدد صحیح باشد.", season
    if not new_title:
        return False, "عنوان فصل نمی‌تواند خالی باشد.", season
    if new_duration < 1 or new_duration > 30:
        return False, "مدت فصل باید بین ۱ تا ۳۰ روز باشد.", season

    conn = db.get_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE tournament_seasons SET title = ?, duration_days = ?, prize_text = ? WHERE id = ? AND status = 'draft'",
                (new_title, new_duration, new_prize, season_id),
            )
        return True, "تنظیمات پیش‌نویس ذخیره شد.", get_season(season_id)
    except Exception as exc:
        return False, f"خطا در ذخیره تنظیمات: {exc}", season


def delete_draft(season_id: int):
    season = get_season(season_id)
    if not season:
        return False, "فصل یافت نشد."
    if season["status"] != DRAFT:
        return False, "فقط پیش‌نویس را می‌توان حذف کرد."
    conn = db.get_connection()
    try:
        with conn:
            conn.execute("DELETE FROM tournament_seasons WHERE id = ? AND status = 'draft'", (season_id,))
        return True, "پیش‌نویس تورنومنت حذف شد."
    except Exception as exc:
        return False, f"خطا در حذف پیش‌نویس: {exc}"


def _country_snapshot(cur, country_id: int) -> dict | None:
    row = cur.execute("SELECT * FROM countries WHERE id = ?", (country_id,)).fetchone()
    if not row:
        return None
    country = dict(row)
    assets = [dict(item) for item in cur.execute(
        "SELECT equipment_key, equipment_name, category, amount, buy_price, maintenance_cost FROM country_assets WHERE country_id = ?",
        (country_id,),
    ).fetchall()]
    equipment_rows = cur.execute(
        "SELECT item_key, quantity FROM equipment WHERE country_id = ?", (country_id,)
    ).fetchall()
    equipment = {item["item_key"]: int(item["quantity"] or 0) for item in equipment_rows}
    alliance_count = cur.execute(
        """
        SELECT COUNT(*) AS n FROM diplomatic_relations
        WHERE status = 'allied' AND (country1_id = ? OR country2_id = ?)
        """,
        (country_id, country_id),
    ).fetchone()["n"]
    base_count = cur.execute(
        "SELECT COUNT(*) AS n FROM foreign_bases WHERE owner_id = ?", (country_id,)
    ).fetchone()["n"]
    return {
        "country": {
            key: country.get(key, 0) or 0
            for key in (
                "treasury", "daily_income", "tax_income", "gold", "oil_reserves", "grain",
                "iron_ore", "microchips", "uranium_ore", "nuclear_fuel", "active_personnel",
                "reserve_personnel", "approval_rating", "combat_readiness", "tech_level", "electricity",
            )
        },
        "assets": assets,
        "equipment": equipment,
        "alliance_count": int(alliance_count or 0),
        "base_count": int(base_count or 0),
    }


def _force_index(assets: list[dict]) -> float:
    total = 0.0
    for asset in assets or []:
        amount = max(0, int(asset.get("amount", 0) or 0))
        price = max(1, int(asset.get("buy_price", 0) or 0))
        factor = FORCE_FACTORS.get(asset.get("category"), 1.0)
        total += amount * price * factor
    return total


def _infra_count(equipment: dict) -> int:
    keys = set(getattr(config, "ALL_SHOP_ITEMS", {}).keys())
    return sum(max(0, int(qty or 0)) for key, qty in equipment.items() if key in keys)


def _resource_growth_pct(current: dict, baseline: dict) -> float:
    values = []
    for field in RESOURCE_FIELDS:
        base = float(baseline.get(field, 0) or 0)
        now = float(current.get(field, 0) or 0)
        if base > 0:
            values.append(max(-100.0, (now - base) / base * 100.0))
    return sum(values) / len(values) if values else 0.0


def _activity_counts(cur, country_id: int, since: str) -> dict:
    statement_rows = cur.execute(
        "SELECT statement_date, COUNT(*) AS n FROM daily_statements WHERE country_id = ? AND created_at >= ? GROUP BY statement_date",
        (country_id, since),
    ).fetchall()
    statement_days = sum(min(2, int(row["n"] or 0)) for row in statement_rows)
    approved_roles = cur.execute(
        "SELECT COUNT(*) AS n FROM pending_roleplays WHERE country_id = ? AND status = 'approved' AND created_at >= ?",
        (country_id, since),
    ).fetchone()["n"]
    missions = cur.execute(
        "SELECT COUNT(*) AS n FROM transactions WHERE country_id = ? AND type = 'mission' AND created_at >= ?",
        (country_id, since),
    ).fetchone()["n"]
    accepted_trades = cur.execute(
        """
        SELECT COUNT(*) AS n FROM trade_contracts
        WHERE status = 'accepted' AND created_at >= ? AND (proposer_id = ? OR recipient_id = ?)
        """,
        (since, country_id, country_id),
    ).fetchone()["n"]
    market_trades = cur.execute(
        """
        SELECT COUNT(*) AS n FROM market_history
        WHERE created_at >= ? AND (seller_id = ? OR buyer_id = ?)
        """,
        (since, country_id, country_id),
    ).fetchone()["n"]
    aid_count = cur.execute(
        "SELECT COUNT(*) AS n FROM transactions WHERE country_id = ? AND type = 'aid_out' AND created_at >= ?",
        (country_id, since),
    ).fetchone()["n"]
    return {
        "statement_days": int(statement_days),
        "approved_roles": int(approved_roles or 0),
        "missions": int(missions or 0),
        "accepted_trades": int(accepted_trades or 0),
        "market_trades": int(market_trades or 0),
        "aid_count": int(aid_count or 0),
    }


def _calculate_metrics(cur, entry: dict, current_snapshot: dict, snapshot_count: int) -> dict:
    baseline_snapshot = _json_load(entry.get("baseline_json"), {})
    base_country = baseline_snapshot.get("country", {})
    current_country = current_snapshot["country"]
    since = entry.get("baseline_at") or entry.get("joined_at") or _iso()
    counts = _activity_counts(cur, entry["country_id"], since)

    current_force = _force_index(current_snapshot.get("assets", []))
    baseline_force = _force_index(baseline_snapshot.get("assets", []))
    force_growth_pct = ((current_force - baseline_force) / baseline_force * 100.0) if baseline_force > 0 else 0.0
    readiness_delta = float(current_country.get("combat_readiness", 0) or 0) - float(base_country.get("combat_readiness", 0) or 0)
    personnel_base = float(base_country.get("active_personnel", 0) or 0)
    personnel_growth_pct = ((float(current_country.get("active_personnel", 0) or 0) - personnel_base) / personnel_base * 100.0) if personnel_base > 0 else 0.0
    treasury_base = float(base_country.get("treasury", 0) or 0)
    treasury_growth_pct = ((float(current_country.get("treasury", 0) or 0) - treasury_base) / treasury_base * 100.0) if treasury_base > 0 else 0.0
    income_base = float(base_country.get("daily_income", 0) or 0)
    income_growth_pct = ((float(current_country.get("daily_income", 0) or 0) - income_base) / income_base * 100.0) if income_base > 0 else 0.0
    tech_delta = int(current_country.get("tech_level", 1) or 1) - int(base_country.get("tech_level", 1) or 1)
    infra_delta = max(0, _infra_count(current_snapshot.get("equipment", {})) - _infra_count(baseline_snapshot.get("equipment", {})))
    base_delta = max(0, current_snapshot.get("base_count", 0) - baseline_snapshot.get("base_count", 0))
    alliance_delta = max(0, current_snapshot.get("alliance_count", 0) - baseline_snapshot.get("alliance_count", 0))
    approval_delta = float(current_country.get("approval_rating", 0) or 0) - float(base_country.get("approval_rating", 0) or 0)
    resource_growth_pct = _resource_growth_pct(current_country, base_country)

    current_categories = {asset.get("category") for asset in current_snapshot.get("assets", []) if int(asset.get("amount", 0) or 0) > 0}
    baseline_categories = {asset.get("category") for asset in baseline_snapshot.get("assets", []) if int(asset.get("amount", 0) or 0) > 0}
    coverage_delta = len(current_categories) - len(baseline_categories)

    economy_raw = (
        max(0.0, treasury_growth_pct) * 1.20
        + max(0.0, income_growth_pct) * 1.00
        + infra_delta * 18.0
        + max(0, tech_delta) * 90.0
        + max(0.0, resource_growth_pct) * 0.40
    )
    military_raw = (
        force_growth_pct * 1.50
        + readiness_delta * 3.00
        + personnel_growth_pct * 0.40
        + coverage_delta * 35.0
    )
    diplomacy_raw = (
        counts["accepted_trades"] * 45.0
        + counts["market_trades"] * 15.0
        + alliance_delta * 100.0
        + counts["aid_count"] * 35.0
    )
    activity_raw = (
        counts["statement_days"] * 25.0
        + counts["approved_roles"] * 65.0
        + counts["missions"] * 40.0
        + snapshot_count * 6.0
    )
    objectives_raw = (
        max(0, tech_delta) * 100.0
        + infra_delta * 15.0
        + base_delta * 80.0
    )
    resource_health = sum(
        1 for field in ("oil_reserves", "grain", "electricity") if float(current_country.get(field, 0) or 0) > 0
    )
    stability_raw = (
        approval_delta * 4.0
        + resource_health * 15.0
        + (25.0 if float(current_country.get("treasury", 0) or 0) >= 0 else -25.0)
        + snapshot_count * 8.0
    )

    event_row = cur.execute(
        "SELECT COALESCE(SUM(points), 0) AS points FROM tournament_events WHERE season_id = ? AND country_id = ?",
        (entry["season_id"], entry["country_id"]),
    ).fetchone()
    manual_score = float(event_row["points"] or 0) if event_row else 0.0
    weights = _json_load(entry.get("scoring_config"), None)
    if not weights:
        season_row = cur.execute(
            "SELECT scoring_config FROM tournament_seasons WHERE id = ?", (entry["season_id"],)
        ).fetchone()
        weights = _json_load(season_row["scoring_config"] if season_row else "{}", _default_scoring_config())

    raw_scores = {
        "economy": economy_raw,
        "military": military_raw,
        "diplomacy": diplomacy_raw,
        "activity": activity_raw,
        "objectives": objectives_raw,
        "stability": stability_raw,
    }
    weighted_scores = {
        key: raw_scores[key] * float(weights.get(key, 0) or 0) / 100.0
        for key in raw_scores
    }
    total = sum(weighted_scores.values()) + manual_score + snapshot_count * 5.0

    return {
        "economy": weighted_scores["economy"],
        "military": weighted_scores["military"],
        "diplomacy": weighted_scores["diplomacy"],
        "activity": weighted_scores["activity"],
        "objectives": weighted_scores["objectives"],
        "stability": weighted_scores["stability"],
        "manual_score": manual_score,
        "total": total,
        "raw": raw_scores,
        "counts": counts,
        "current_force": current_force,
        "baseline_force": baseline_force,
        "force_growth_pct": force_growth_pct,
        "readiness_delta": readiness_delta,
        "treasury_growth_pct": treasury_growth_pct,
        "income_growth_pct": income_growth_pct,
        "resource_growth_pct": resource_growth_pct,
        "tech_delta": tech_delta,
        "infra_delta": infra_delta,
        "base_delta": base_delta,
        "alliance_delta": alliance_delta,
        "approval_delta": approval_delta,
        "snapshot_count": snapshot_count,
    }


def _get_player_row(cur, season_id: int, country_id: int | None = None, player_id: int | None = None):
    if country_id is not None:
        return cur.execute(
            "SELECT * FROM tournament_players WHERE season_id = ? AND country_id = ?",
            (season_id, country_id),
        ).fetchone()
    return cur.execute(
        "SELECT * FROM tournament_players WHERE season_id = ? AND player_id = ?",
        (season_id, player_id),
    ).fetchone()


def start_season(season_id: int):
    season = get_season(season_id)
    if not season:
        return False, "فصل یافت نشد.", None
    if season["status"] != DRAFT:
        return False, "فقط پیش‌نویس را می‌توان فعال کرد.", season
    if get_active_season():
        return False, "یک فصل دیگر در حال حاضر فعال است.", season

    now_dt = _now()
    now = _iso(now_dt)
    end = _iso(now_dt + datetime.timedelta(days=int(season["duration_days"] or 7)))
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE tournament_seasons SET status = 'active', starts_at = ?, ends_at = ?, activated_at = ? WHERE id = ? AND status = 'draft'",
                (now, end, now, season_id),
            )
            if cur.rowcount != 1:
                return False, "فصل قبلاً تغییر وضعیت داده است.", get_season(season_id)
            players = cur.execute(
                "SELECT id, country_id FROM tournament_players WHERE season_id = ? AND status = 'active'",
                (season_id,),
            ).fetchall()
            for player in players:
                snapshot = _country_snapshot(cur, player["country_id"])
                if not snapshot:
                    cur.execute(
                        "UPDATE tournament_players SET status = 'disqualified', disqualified_reason = ? WHERE id = ?",
                        ("کشور قبل از شروع فصل حذف شده است.", player["id"]),
                    )
                    continue
                cur.execute(
                    """
                    UPDATE tournament_players
                    SET baseline_at = ?, baseline_json = ?, last_metrics_json = '{}',
                        score = 0, economy_score = 0, military_score = 0,
                        diplomacy_score = 0, activity_score = 0, objectives_score = 0,
                        stability_score = 0, manual_score = 0, last_snapshot_at = NULL
                    WHERE id = ?
                    """,
                    (now, json.dumps(snapshot, ensure_ascii=False), player["id"]),
                )
        return True, "فصل تورنومنت فعال شد.", get_season(season_id)
    except Exception as exc:
        logger.exception("Could not start tournament")
        return False, f"خطا در فعال‌سازی فصل: {exc}", season


def pause_season(season_id: int):
    return _change_status(season_id, ACTIVE, PAUSED, "فصل موقتاً متوقف شد.")


def resume_season(season_id: int):
    return _change_status(season_id, PAUSED, ACTIVE, "فصل دوباره فعال شد.")


def _change_status(season_id: int, expected: str, target: str, message: str):
    season = get_season(season_id)
    if not season:
        return False, "فصل یافت نشد.", None
    if season["status"] != expected:
        return False, "وضعیت فعلی فصل اجازه این عملیات را نمی‌دهد.", season
    conn = db.get_connection()
    try:
        with conn:
            now = _iso()
            conn.execute(
                "UPDATE tournament_seasons SET status = ?, paused_at = ? WHERE id = ? AND status = ?",
                (target, now if target == PAUSED else season.get("paused_at"), season_id, expected),
            )
        return True, message, get_season(season_id)
    except Exception as exc:
        return False, f"خطا در تغییر وضعیت فصل: {exc}", season


def end_season(season_id: int):
    season = get_season(season_id)
    if not season:
        return False, "فصل یافت نشد.", None
    if season["status"] not in (ACTIVE, PAUSED):
        return False, "این فصل قابل پایان‌دادن نیست.", season
    if season["status"] == ACTIVE:
        refresh_season(season_id, force=True)
    conn = db.get_connection()
    try:
        with conn:
            conn.execute(
                "UPDATE tournament_seasons SET status = 'ended', ended_at = ? WHERE id = ? AND status IN ('active', 'paused')",
                (_iso(), season_id),
            )
        return True, "فصل تورنومنت پایان یافت و جدول نهایی قفل شد.", get_season(season_id)
    except Exception as exc:
        return False, f"خطا در پایان فصل: {exc}", season


def join_tournament(player_id: int, country_id: int):
    season = get_open_season()
    if not season:
        return False, "در حال حاضر فصل تورنومنتی برای ثبت‌نام وجود ندارد.", None
    if season["status"] not in (DRAFT, ACTIVE):
        return False, "ثبت‌نام در این فصل بسته است.", season

    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            country = cur.execute(
                "SELECT id, player_id, name, flag, country_key FROM countries WHERE id = ?", (country_id,)
            ).fetchone()
            if not country or int(country["player_id"]) != int(player_id):
                return False, "این کشور متعلق به بازیکن فعلی نیست.", season
            existing = cur.execute(
                "SELECT * FROM tournament_players WHERE season_id = ? AND player_id = ?",
                (season["id"], player_id),
            ).fetchone()
            if existing:
                return False, "شما قبلاً در این فصل ثبت‌نام کرده‌اید.", dict(existing)
            existing_country = cur.execute(
                "SELECT id FROM tournament_players WHERE season_id = ? AND country_id = ?",
                (season["id"], country_id),
            ).fetchone()
            if existing_country:
                return False, "این کشور قبلاً در فصل ثبت‌نام شده است.", season

            baseline = _country_snapshot(cur, country_id) if season["status"] == ACTIVE else {}
            now = _iso()
            cur.execute(
                """
                INSERT INTO tournament_players
                (season_id, country_id, player_id, joined_at, baseline_at, baseline_json, status)
                VALUES (?, ?, ?, ?, ?, ?, 'active')
                """,
                (
                    season["id"], country_id, player_id, now,
                    now if season["status"] == ACTIVE else None,
                    json.dumps(baseline, ensure_ascii=False),
                ),
            )
        return True, "ثبت‌نام شما در تورنومنت انجام شد.", get_player_entry(season["id"], player_id=player_id)
    except Exception as exc:
        return False, f"خطا در ثبت‌نام تورنومنت: {exc}", season


def get_player_entry(season_id: int | None = None, player_id: int | None = None, country_id: int | None = None):
    season = get_season(season_id) if season_id else get_open_season()
    if not season:
        return None
    conn = db.get_connection()
    try:
        if country_id is not None:
            row = conn.execute(
                "SELECT p.*, c.name AS country_name, c.flag AS country_flag, c.country_key FROM tournament_players p JOIN countries c ON c.id = p.country_id WHERE p.season_id = ? AND p.country_id = ?",
                (season["id"], country_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT p.*, c.name AS country_name, c.flag AS country_flag, c.country_key FROM tournament_players p JOIN countries c ON c.id = p.country_id WHERE p.season_id = ? AND p.player_id = ?",
                (season["id"], player_id),
            ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_participant_count(season_id: int | None = None) -> int:
    season = get_season(season_id) if season_id else get_open_season()
    if not season:
        return 0
    conn = db.get_connection()
    try:
        return int(conn.execute(
            "SELECT COUNT(*) AS n FROM tournament_players WHERE season_id = ? AND status = 'active'", (season["id"],)
        ).fetchone()["n"])
    finally:
        conn.close()


def get_participants(season_id: int, include_disqualified: bool = False) -> list[dict]:
    conn = db.get_connection()
    try:
        where = "" if include_disqualified else " AND p.status != 'disqualified'"
        rows = conn.execute(
            f"""
            SELECT p.*, c.name AS country_name, c.flag AS country_flag, c.country_key
            FROM tournament_players p JOIN countries c ON c.id = p.country_id
            WHERE p.season_id = ?{where}
            ORDER BY p.id ASC
            """,
            (season_id,),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def get_rankings(season_id: int | None = None, limit: int = 10, offset: int = 0) -> list[dict]:
    season = get_season(season_id) if season_id else get_open_season()
    if not season:
        return []
    conn = db.get_connection()
    try:
        rows = conn.execute(
            """
            SELECT p.*, c.name AS country_name, c.flag AS country_flag, c.country_key
            FROM tournament_players p
            JOIN countries c ON c.id = p.country_id
            WHERE p.season_id = ? AND p.status != 'disqualified'
            ORDER BY p.score DESC, p.stability_score DESC, p.id ASC
            LIMIT ? OFFSET ?
            """,
            (season["id"], max(1, min(50, int(limit))), max(0, int(offset))),
        ).fetchall()
        result = []
        previous_score = None
        current_rank = 0
        for index, row in enumerate(rows):
            item = dict(row)
            score = round(float(item.get("score", 0) or 0), 2)
            if previous_score is None or score != previous_score:
                current_rank = offset + index + 1
            item["rank"] = current_rank
            item["score"] = score
            previous_score = score
            result.append(item)
        return result
    finally:
        conn.close()


def get_rank_for_player(season_id: int, player_id: int) -> int | None:
    entry = get_player_entry(season_id, player_id=player_id)
    if not entry:
        return None
    conn = db.get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) AS n FROM tournament_players WHERE season_id = ? AND status != 'disqualified' AND (score > ? OR (score = ? AND id < ?))",
            (season_id, entry["score"], entry["score"], entry["id"]),
        ).fetchone()
        return int(row["n"] or 0) + 1
    finally:
        conn.close()


def get_score_details(season_id: int, player_id: int):
    entry = get_player_entry(season_id, player_id=player_id)
    if not entry:
        return None
    rank = get_rank_for_player(season_id, player_id)
    details = dict(entry)
    details["rank"] = rank
    for key in ("score", "economy_score", "military_score", "diplomacy_score", "activity_score", "objectives_score", "stability_score", "manual_score"):
        details[key] = round(float(details.get(key, 0) or 0), 2)
    return details


def add_manual_event(season_id: int, country_id: int, admin_id: int, points: float, description: str, event_type: str = "admin_award", event_key: str | None = None):
    entry = get_player_entry(season_id, country_id=country_id)
    if not entry:
        return False, "این کشور در تورنومنت ثبت‌نام نکرده است."
    try:
        points = float(points)
    except (TypeError, ValueError):
        return False, "امتیاز باید عددی باشد."
    if points == 0 or points < -100000 or points > 100000:
        return False, "امتیاز دستی باید بین ۱۰۰٬۰۰۰- و ۱۰۰٬۰۰۰ باشد و صفر نباشد."
    event_key = event_key or f"admin_{admin_id}_{uuid.uuid4().hex}"
    conn = db.get_connection()
    try:
        with conn:
            conn.execute(
                """
                INSERT INTO tournament_events
                (season_id, country_id, player_id, event_key, event_type, points, description, created_at, admin_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (season_id, country_id, entry["player_id"], event_key, event_type, points, (description or "")[:300], _iso(), admin_id),
            )
        return True, "رویداد امتیازی ثبت شد."
    except Exception as exc:
        return False, f"خطا در ثبت امتیاز دستی: {exc}"


def disqualify_player(season_id: int, country_id: int, reason: str = "نقض قوانین"):
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cur.execute(
                "UPDATE tournament_players SET status = 'disqualified', disqualified_reason = ? WHERE season_id = ? AND country_id = ? AND status != 'disqualified'",
                ((reason or "نقض قوانین")[:300], season_id, country_id),
            )
            if cur.rowcount != 1:
                return False, "شرکت‌کننده یافت نشد یا قبلاً حذف شده است."
        return True, "شرکت‌کننده از تورنومنت حذف شد."
    except Exception as exc:
        return False, f"خطا در حذف شرکت‌کننده: {exc}"


def refresh_player(season_id: int, player_id: int | None = None, country_id: int | None = None, force: bool = False):
    season = get_season(season_id)
    if not season or season["status"] not in (ACTIVE, PAUSED):
        return False, "فصل برای امتیازدهی فعال نیست.", None

    conn = db.get_connection()
    try:
        cur = conn.cursor()
        row = _get_player_row(cur, season_id, country_id=country_id, player_id=player_id)
        if not row or row["status"] != "active":
            return False, "شرکت‌کننده فعال یافت نشد.", None
        entry = dict(row)
        now_dt = _now()
        last_dt = _parse_dt(entry.get("last_snapshot_at"))
        interval = int(getattr(config, "TOURNAMENT_SNAPSHOT_INTERVAL_MINUTES", 360))
        if not force and last_dt and (now_dt - last_dt).total_seconds() < interval * 60:
            return False, "snapshot هنوز به‌روز است.", entry

        snapshot = _country_snapshot(cur, entry["country_id"])
        if not snapshot:
            cur.execute(
                "UPDATE tournament_players SET status = 'disqualified', disqualified_reason = ? WHERE id = ?",
                ("کشور حذف شده است.", entry["id"]),
            )
            conn.commit()
            return False, "کشور شرکت‌کننده حذف شده است.", None

        snapshot_count = cur.execute(
            "SELECT COUNT(*) AS n FROM tournament_snapshots WHERE season_id = ? AND country_id = ?",
            (season_id, entry["country_id"]),
        ).fetchone()["n"]
        metrics = _calculate_metrics(cur, entry, snapshot, int(snapshot_count or 0))
        captured_at = _iso(now_dt)
        cur.execute(
            """
            INSERT INTO tournament_snapshots
            (season_id, country_id, player_id, captured_at, total_score, economy_score, military_score,
             diplomacy_score, activity_score, objectives_score, stability_score, metrics_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                season_id, entry["country_id"], entry["player_id"], captured_at,
                metrics["total"], metrics["economy"], metrics["military"], metrics["diplomacy"],
                metrics["activity"], metrics["objectives"], metrics["stability"],
                json.dumps(metrics, ensure_ascii=False),
            ),
        )
        cur.execute(
            """
            UPDATE tournament_players SET
                score = ?, economy_score = ?, military_score = ?, diplomacy_score = ?,
                activity_score = ?, objectives_score = ?, stability_score = ?, manual_score = ?,
                last_metrics_json = ?, last_snapshot_at = ?
            WHERE id = ? AND status = 'active'
            """,
            (
                metrics["total"], metrics["economy"], metrics["military"], metrics["diplomacy"],
                metrics["activity"], metrics["objectives"], metrics["stability"], metrics["manual_score"],
                json.dumps(metrics, ensure_ascii=False), captured_at, entry["id"],
            ),
        )
        conn.commit()
        updated = get_score_details(season_id, entry["player_id"])
        return True, "امتیاز به‌روزرسانی شد.", updated
    except Exception as exc:
        logger.exception("Could not refresh tournament player")
        return False, f"خطا در محاسبه امتیاز: {exc}", None
    finally:
        conn.close()


def refresh_season(season_id: int, force: bool = False) -> int:
    season = get_season(season_id)
    if not season or season["status"] not in (ACTIVE, PAUSED):
        return 0
    conn = db.get_connection()
    try:
        rows = conn.execute(
            "SELECT country_id FROM tournament_players WHERE season_id = ? AND status = 'active'", (season_id,)
        ).fetchall()
    finally:
        conn.close()
    count = 0
    for row in rows:
        ok, _, _ = refresh_player(season_id, country_id=row["country_id"], force=force)
        if ok:
            count += 1
    return count


def refresh_active_tournament(force: bool = False) -> int:
    season = get_active_season()
    if not season:
        return 0
    end_dt = _parse_dt(season.get("ends_at"))
    if end_dt and _now() >= end_dt:
        refresh_season(season["id"], force=True)
        conn = db.get_connection()
        try:
            with conn:
                conn.execute(
                    "UPDATE tournament_seasons SET status = 'ended', ended_at = ? WHERE id = ? AND status = 'active'",
                    (_iso(), season["id"]),
                )
        finally:
            conn.close()
        return 0
    return refresh_season(season["id"], force=force)


def get_event_history(season_id: int, country_id: int | None = None, limit: int = 20) -> list[dict]:
    conn = db.get_connection()
    try:
        if country_id is None:
            rows = conn.execute(
                "SELECT e.*, c.name AS country_name, c.flag AS country_flag FROM tournament_events e JOIN countries c ON c.id = e.country_id WHERE e.season_id = ? ORDER BY e.id DESC LIMIT ?",
                (season_id, max(1, min(100, int(limit)))),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT e.*, c.name AS country_name, c.flag AS country_flag FROM tournament_events e JOIN countries c ON c.id = e.country_id WHERE e.season_id = ? AND e.country_id = ? ORDER BY e.id DESC LIMIT ?",
                (season_id, country_id, max(1, min(100, int(limit)))),
            ).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def season_summary(season_id: int) -> dict | None:
    season = get_season(season_id)
    if not season:
        return None
    season["scoring"] = _json_load(season.get("scoring_config"), _default_scoring_config())
    season["participant_count"] = get_participant_count(season_id)
    season["top"] = get_rankings(season_id, limit=3)
    return season


def format_score(value) -> str:
    try:
        number = float(value or 0)
        if number.is_integer():
            return f"{int(number):,}"
        return f"{number:,.1f}"
    except (TypeError, ValueError):
        return "0"
