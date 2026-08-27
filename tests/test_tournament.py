"""تست‌های سیستم تورنومنت فصلی و امتیازدهی ترکیبی."""

import json

import config
import database as db
import tournament_system as tournament
from utils import get_main_keyboard


def _fresh_db(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "tournament.db"))
    db.init_db()
    return db


def test_tournament_stays_draft_until_admin_starts_it(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    country_id = database.create_country(8101, "کشور تورنومنت", "🏳️", country_key="iran")

    ok, _message, season = tournament.create_draft()
    assert ok
    assert season["status"] == tournament.DRAFT
    assert tournament.get_active_season() is None

    joined, _message, entry = tournament.join_tournament(8101, country_id)
    assert joined
    assert json.loads(entry["baseline_json"]) == {}

    started, _message, season = tournament.start_season(season["id"])
    assert started
    assert season["status"] == tournament.ACTIVE

    entry = tournament.get_player_entry(season["id"], player_id=8101)
    baseline = json.loads(entry["baseline_json"])
    assert baseline["country"]["treasury"] == database.get_country_by_id(country_id)["treasury"]
    assert float(entry["score"]) == 0


def test_combined_score_grows_from_verified_game_activity(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    country_id = database.create_country(8102, "کشور فعال", "🏳️", country_key="iran")
    ok, _message, season = tournament.create_draft(duration_days=7)
    assert ok
    assert tournament.join_tournament(8102, country_id)[0]
    assert tournament.start_season(season["id"])[0]

    # توسعه اقتصادی/نظامی بعد از ثبت baseline
    database.update_country_field(country_id, "treasury", 70_000_000)
    database.update_country_field(country_id, "daily_income", 5_000_000)
    database.update_country_field(country_id, "combat_readiness", 92)
    database.add_equipment(country_id, "small_factory", 2)
    database.record_country_statement(country_id, 8102, content="بیانیه اول")
    database.record_country_statement(country_id, 8102, content="بیانیه دوم")
    database.record_country_statement(country_id, 8102, content="اسپم؛ نباید امتیاز کامل بگیرد")

    conn = database.get_connection()
    conn.execute(
        "INSERT INTO pending_roleplays (country_id, player_id, role_type, role_text, status, created_at, created_date) VALUES (?, ?, ?, ?, 'approved', ?, ?)",
        (country_id, 8102, "defense", "رول دفاعی تأییدشده", "2026-08-27T01:00:00+00:00", "2026-08-27"),
    )
    conn.commit()
    conn.close()

    updated = tournament.refresh_season(season["id"], force=True)
    assert updated == 1
    details = tournament.get_score_details(season["id"], 8102)
    assert details["score"] > 0
    assert details["economy_score"] > 0
    assert details["military_score"] > 0
    assert details["activity_score"] > 0
    assert details["rank"] == 1

    first_score = details["score"]
    # رویداد مدیریتی باید به امتیاز اضافه شود و امتیاز سقف ۱۰۰۰ نداشته باشد.
    event_ok, _ = tournament.add_manual_event(season["id"], country_id, 8052987465, 2500, "پیروزی دفاعی تأییدشده")
    assert event_ok
    tournament.refresh_player(season["id"], country_id=country_id, force=True)
    assert tournament.get_score_details(season["id"], 8102)["score"] > first_score


def test_tournament_pause_and_end_freeze_score(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    country_id = database.create_country(8103, "کشور پایان فصل", "🏳️", country_key="uk")
    ok, _message, season = tournament.create_draft()
    assert ok
    assert tournament.join_tournament(8103, country_id)[0]
    assert tournament.start_season(season["id"])[0]

    assert tournament.pause_season(season["id"])[0]
    assert tournament.get_season(season["id"])["status"] == tournament.PAUSED
    assert tournament.resume_season(season["id"])[0]
    assert tournament.end_season(season["id"])[0]
    assert tournament.get_season(season["id"])["status"] == tournament.ENDED
    assert tournament.get_active_season() is None


def test_player_keyboard_contains_tournament_entry_point():
    keyboard = get_main_keyboard(8104)
    texts = {button.text for row in keyboard.keyboard for button in row}
    assert "🏆 تورنومنت فصل" in texts
