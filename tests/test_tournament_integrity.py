# -*- coding: utf-8 -*-
"""تست‌های رگرسیون یکپارچگی و ضدتقلب تورنومنت فصلی.

هر تست این فایل دقیقاً به یک باگ واقعی گره خورده که در ممیزی ۲۰۲۶-۰۸-۲۷ پیدا شد.
"""

import datetime

import config
import database as db
import tournament_system as tournament


def _fresh_db(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "tournament_integrity.db"))
    db.init_db()
    return db


def _started_season(monkeypatch, tmp_path, player_id=9001, treasury=50_000_000):
    database = _fresh_db(monkeypatch, tmp_path)
    country_id = database.create_country(player_id, "کشور آزمون", "🏳️", country_key="iran")
    database.update_country_field(country_id, "treasury", treasury)
    ok, _msg, season = tournament.create_draft(duration_days=7)
    assert ok
    assert tournament.join_tournament(player_id, country_id)[0]
    started, _msg, season = tournament.start_season(season["id"])
    assert started
    return database, season, country_id, player_id


def _score(season_id, player_id):
    return tournament.get_score_details(season_id, player_id)["score"]


# ─────────────────────────────────────────────────────────────────────────────
# ۱. ضدتقلب: تزریق پول از بیرونِ گیم‌پلی نباید امتیاز اقتصادی بسازد
# ─────────────────────────────────────────────────────────────────────────────

def test_admin_cash_grant_does_not_create_tournament_points(monkeypatch, tmp_path):
    """واریز گروهی ادمین (compensation_grant) نباید امتیاز اقتصاد بدهد."""
    database, season, country_id, player_id = _started_season(monkeypatch, tmp_path)

    database.adjust_treasury(country_id, 200_000_000)
    database.add_transaction(country_id, "compensation_grant", "واریز جبرانی مدیریت", 200_000_000)

    tournament.refresh_player(season["id"], country_id=country_id, force=True)
    details = tournament.get_score_details(season["id"], player_id)
    assert details["economy_score"] == 0, "تزریق ادمین نباید به امتیاز اقتصاد تبدیل شود"


def test_paid_survival_pack_does_not_create_tournament_points(monkeypatch, tmp_path):
    """بسته بقای خریدنی (پول + منابع) نباید تورنومنت را pay-to-win کند."""
    database, season, country_id, player_id = _started_season(monkeypatch, tmp_path)

    pack_cash = 18_000_000
    pack = tournament.SURVIVAL_PACK_CONTENTS[pack_cash]
    database.adjust_treasury(country_id, pack_cash)
    conn = database.get_connection()
    with conn:
        conn.execute(
            "UPDATE countries SET oil_reserves = oil_reserves + ?, grain = grain + ?, "
            "iron_ore = iron_ore + ?, microchips = microchips + ?, gold = gold + ? WHERE id = ?",
            (
                pack.get("oil_reserves", 0), pack.get("grain", 0), pack.get("iron_ore", 0),
                pack.get("microchips", 0), pack.get("gold", 0), country_id,
            ),
        )
    conn.close()
    database.add_transaction(country_id, "survival_pack", "بسته بقا فوق‌سنگین", pack_cash)

    tournament.refresh_player(season["id"], country_id=country_id, force=True)
    details = tournament.get_score_details(season["id"], player_id)
    assert details["economy_score"] == 0, "خرید بسته نباید امتیاز اقتصاد بسازد"


def test_organic_growth_still_scores(monkeypatch, tmp_path):
    """کنترل: رشد واقعی از گیم‌پلی همچنان باید امتیاز بدهد."""
    database, season, country_id, player_id = _started_season(monkeypatch, tmp_path)

    database.adjust_treasury(country_id, 200_000_000)  # بدون تراکنش تزریق بیرونی

    tournament.refresh_player(season["id"], country_id=country_id, force=True)
    details = tournament.get_score_details(season["id"], player_id)
    assert details["economy_score"] > 0


def test_mixed_growth_only_counts_organic_part(monkeypatch, tmp_path):
    """اگر بخشی از رشد تزریقی و بخشی واقعی باشد، فقط بخش واقعی امتیاز می‌گیرد."""
    database, season, country_id, player_id = _started_season(monkeypatch, tmp_path)

    database.adjust_treasury(country_id, 100_000_000)
    database.add_transaction(country_id, "admin_boost", "تزریق ادمین", 100_000_000)
    tournament.refresh_player(season["id"], country_id=country_id, force=True)
    injected_only = tournament.get_score_details(season["id"], player_id)["economy_score"]

    database.adjust_treasury(country_id, 100_000_000)  # این یکی واقعی است
    tournament.refresh_player(season["id"], country_id=country_id, force=True)
    with_organic = tournament.get_score_details(season["id"], player_id)["economy_score"]

    assert injected_only == 0
    assert with_organic > 0


# ─────────────────────────────────────────────────────────────────────────────
# ۲. امتیاز نباید با فشار دادن دکمه‌ی ادمین تورم بگیرد
# ─────────────────────────────────────────────────────────────────────────────

def test_repeated_force_refresh_does_not_inflate_score(monkeypatch, tmp_path):
    """«جدول زنده»‌ی ادمین با force اجرا می‌شود؛ نباید امتیاز همه را بالا ببرد."""
    database, season, country_id, player_id = _started_season(monkeypatch, tmp_path)
    database.adjust_treasury(country_id, 20_000_000)

    tournament.refresh_player(season["id"], country_id=country_id, force=True)
    first = _score(season["id"], player_id)
    for _ in range(5):
        tournament.refresh_player(season["id"], country_id=country_id, force=True)
    last = _score(season["id"], player_id)

    assert last == first, "تعداد snapshot نباید روی امتیاز اثر بگذارد"


def test_score_is_never_negative(monkeypatch, tmp_path):
    """جریمه‌ی سنگین مدیریتی نباید جدول را با امتیاز منفی خراب کند."""
    database, season, country_id, player_id = _started_season(monkeypatch, tmp_path)

    ok, _msg = tournament.add_manual_event(
        season["id"], country_id, 8052987465, -90_000, "جریمه تخلف سنگین"
    )
    assert ok
    tournament.refresh_player(season["id"], country_id=country_id, force=True)
    assert _score(season["id"], player_id) == 0


# ─────────────────────────────────────────────────────────────────────────────
# ۳. توقف موقت نباید از وقت بازیکنان کم کند
# ─────────────────────────────────────────────────────────────────────────────

def test_pause_extends_season_end_time(monkeypatch, tmp_path):
    database, season, country_id, player_id = _started_season(monkeypatch, tmp_path)
    original_end = tournament._parse_dt(tournament.get_season(season["id"])["ends_at"])

    assert tournament.pause_season(season["id"])[0]
    # وانمود می‌کنیم فصل ۳ ساعت متوقف بوده است
    paused_at = tournament._now() - datetime.timedelta(hours=3)
    conn = database.get_connection()
    with conn:
        conn.execute(
            "UPDATE tournament_seasons SET paused_at = ? WHERE id = ?",
            (tournament._iso(paused_at), season["id"]),
        )
    conn.close()

    assert tournament.resume_season(season["id"])[0]
    refreshed = tournament.get_season(season["id"])
    new_end = tournament._parse_dt(refreshed["ends_at"])

    assert refreshed["status"] == tournament.ACTIVE
    assert refreshed["paused_at"] is None
    delta_hours = (new_end - original_end).total_seconds() / 3600
    assert 2.9 < delta_hours < 3.1, f"پایان فصل باید ~۳ ساعت تمدید شود، شد {delta_hours}"


# ─────────────────────────────────────────────────────────────────────────────
# ۴. رتبه در «جدول رتبه‌بندی» و «جزئیات امتیاز» باید یکی باشد
# ─────────────────────────────────────────────────────────────────────────────

def test_rank_is_consistent_between_table_and_details(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    ok, _msg, season = tournament.create_draft()
    assert ok

    countries = []
    for index in range(4):
        player_id = 9100 + index
        country_id = database.create_country(player_id, f"کشور {index}", "🏳️", country_key=f"c{index}")
        assert tournament.join_tournament(player_id, country_id)[0]
        countries.append((player_id, country_id))
    assert tournament.start_season(season["id"])[0]

    # دو کشور دقیقاً هم‌امتیاز، دو کشور متفاوت
    scores = [500.0, 500.0, 300.0, 100.0]
    conn = database.get_connection()
    with conn:
        for (_pid, cid), value in zip(countries, scores):
            conn.execute(
                "UPDATE tournament_players SET score = ? WHERE season_id = ? AND country_id = ?",
                (value, season["id"], cid),
            )
    conn.close()

    table = {row["player_id"]: row["rank"] for row in tournament.get_rankings(season["id"], limit=50)}
    for player_id, _cid in countries:
        assert tournament.get_rank_for_player(season["id"], player_id) == table[player_id]
    assert sorted(table.values()) == [1, 1, 3, 4]


# ─────────────────────────────────────────────────────────────────────────────
# ۵. سقف ضدتقلب روی فعالیت‌های قابل فارم با حساب دوم
# ─────────────────────────────────────────────────────────────────────────────

def test_aid_out_farming_is_capped(monkeypatch, tmp_path):
    database, season, country_id, player_id = _started_season(monkeypatch, tmp_path)

    for index in range(tournament.MAX_SCORED_AID_OUT * 4):
        database.add_transaction(country_id, "aid_out", f"کمک {index}", 1_000_000)

    tournament.refresh_player(season["id"], country_id=country_id, force=True)
    metrics = tournament._json_load(
        tournament.get_player_entry(season["id"], player_id=player_id)["last_metrics_json"], {}
    )
    expected_cap = tournament.MAX_SCORED_AID_OUT * 35.0
    assert metrics["counts"]["aid_count"] == tournament.MAX_SCORED_AID_OUT * 4
    assert metrics["raw"]["diplomacy"] <= expected_cap + 1e-6


# ─────────────────────────────────────────────────────────────────────────────
# ۶. تضمین‌های پایه‌ای که نباید بشکنند
# ─────────────────────────────────────────────────────────────────────────────

def test_no_season_is_created_automatically_on_fresh_database(monkeypatch, tmp_path):
    _fresh_db(monkeypatch, tmp_path)
    assert tournament.get_active_season() is None
    assert tournament.get_open_season() is None
    assert tournament.list_seasons(50) == []


def test_snapshot_interval_is_enforced_without_force(monkeypatch, tmp_path):
    database, season, country_id, player_id = _started_season(monkeypatch, tmp_path)
    assert tournament.refresh_player(season["id"], country_id=country_id, force=True)[0]
    ok, message, _entry = tournament.refresh_player(season["id"], country_id=country_id, force=False)
    assert not ok
    assert "snapshot" in message


def test_ended_season_scores_are_frozen(monkeypatch, tmp_path):
    database, season, country_id, player_id = _started_season(monkeypatch, tmp_path)
    database.adjust_treasury(country_id, 50_000_000)
    tournament.refresh_player(season["id"], country_id=country_id, force=True)
    assert tournament.end_season(season["id"])[0]
    frozen = _score(season["id"], player_id)

    database.adjust_treasury(country_id, 500_000_000)
    ok, _msg, _entry = tournament.refresh_player(season["id"], country_id=country_id, force=True)
    assert not ok
    assert tournament.refresh_active_tournament(force=True) == 0
    assert _score(season["id"], player_id) == frozen
