# -*- coding: utf-8 -*-
"""تست‌های قرنطینه‌ی کشور رهاشده و صف انتظار."""

import datetime

import config
import country_queue as cq
import database as db


def _fresh(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "queue.db"))
    db.init_db()
    return db


def _country(database, player_id, key="iran", name="ایران"):
    return database.create_country(player_id, name, "🏳️", country_key=key)


# ─────────────────────────────────────────────────────────────────────────────
# قرنطینه
# ─────────────────────────────────────────────────────────────────────────────

def test_quarantine_keeps_everything_instead_of_deleting(monkeypatch, tmp_path):
    """رگرسیون: سلب مالکیت قبلاً کشور را با تمام دارایی‌هایش DELETE می‌کرد."""
    database = _fresh(monkeypatch, tmp_path)
    cid = _country(database, 5001)
    database.add_equipment(cid, "small_factory", 7)
    database.update_country_field(cid, "treasury", 42_000_000)
    database.add_transaction(cid, "daily_income", "واریز", 1_000_000)

    ok, _msg = cq.quarantine_country(cid)
    assert ok

    country = database.get_country_by_id(cid)
    assert country is not None, "کشور نباید حذف شود"
    assert country["player_id"] == 0
    assert country["previous_player_id"] == 5001
    assert country["treasury"] == 42_000_000
    assert (database.get_equipment(cid) or {}).get("small_factory") == 7


def test_owner_can_reclaim_during_quarantine(monkeypatch, tmp_path):
    database = _fresh(monkeypatch, tmp_path)
    cid = _country(database, 5002)
    database.update_country_field(cid, "treasury", 33_000_000)
    cq.quarantine_country(cid)

    ok, message, country = cq.reclaim_country(5002)
    assert ok, message
    assert country["player_id"] == 5002
    assert country["treasury"] == 33_000_000
    assert country["quarantine_until"] is None
    assert database.get_country_by_player(5002) is not None


def test_reclaim_fails_after_the_window_closes(monkeypatch, tmp_path):
    database = _fresh(monkeypatch, tmp_path)
    cid = _country(database, 5003)
    cq.quarantine_country(cid)

    past = cq._iso(cq._now() - datetime.timedelta(hours=1))
    conn = database.get_connection()
    with conn:
        conn.execute("UPDATE countries SET quarantine_until = ? WHERE id = ?", (past, cid))
    conn.close()

    ok, message, _c = cq.reclaim_country(5003)
    assert not ok and "مهلت" in message


def test_quarantine_lasts_24h_by_default(monkeypatch, tmp_path):
    database = _fresh(monkeypatch, tmp_path)
    cid = _country(database, 5004)
    before = cq._now()
    cq.quarantine_country(cid)

    until = cq._parse(database.get_country_by_id(cid)["quarantine_until"])
    hours = (until - before).total_seconds() / 3600
    assert cq.QUARANTINE_HOURS == 24
    assert 23.9 < hours < 24.1


def test_expired_quarantine_moves_the_country_into_the_free_pool(monkeypatch, tmp_path):
    database = _fresh(monkeypatch, tmp_path)
    cid = _country(database, 5005)
    cq.quarantine_country(cid)
    assert cq.get_free_countries() == []

    released = cq.release_expired_quarantines(cq._now() + datetime.timedelta(days=3))
    assert len(released) == 1
    free = cq.get_free_countries()
    assert len(free) == 1 and free[0]["id"] == cid
    assert free[0]["previous_player_id"] is None


# ─────────────────────────────────────────────────────────────────────────────
# صف
# ─────────────────────────────────────────────────────────────────────────────

def test_queue_is_first_in_first_out(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    for player in (6001, 6002, 6003):
        assert cq.join_queue(player)[0]
    assert cq.queue_position(6001) == 1
    assert cq.queue_position(6003) == 3


def test_paid_priority_jumps_the_queue(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    for player in (6101, 6102, 6103):
        cq.join_queue(player)
    assert cq.queue_position(6103) == 3

    assert cq.set_priority(6103, cq.PRIORITY_PAID)
    assert cq.queue_position(6103) == 1
    assert cq.queue_position(6101) == 2


def test_a_player_with_a_country_cannot_join(monkeypatch, tmp_path):
    database = _fresh(monkeypatch, tmp_path)
    _country(database, 6201)
    ok, message, _e = cq.join_queue(6201)
    assert not ok and "کشور دارید" in message


def test_free_country_is_offered_to_the_first_in_line(monkeypatch, tmp_path):
    database = _fresh(monkeypatch, tmp_path)
    cid = _country(database, 6301)
    cq.quarantine_country(cid)
    cq.join_queue(6401)
    cq.join_queue(6402)

    result = cq.process_queue(cq._now() + datetime.timedelta(days=3))
    assert len(result["released"]) == 1
    assert len(result["offered"]) == 1
    assert result["offered"][0]["entry"]["player_id"] == 6401

    entry = cq.get_queue_entry(6401)
    assert entry["status"] == "offered" and entry["offered_country_id"] == cid
    assert cq.get_queue_entry(6402)["status"] == "waiting"


def test_accepting_an_offer_hands_over_the_country(monkeypatch, tmp_path):
    database = _fresh(monkeypatch, tmp_path)
    cid = _country(database, 6501)
    database.update_country_field(cid, "treasury", 77_000_000)
    cq.quarantine_country(cid)
    cq.join_queue(6601)
    cq.process_queue(cq._now() + datetime.timedelta(days=3))

    ok, message, country = cq.accept_offer(6601)
    assert ok, message
    assert country["player_id"] == 6601
    assert country["treasury"] == 77_000_000, "کشور با دارایی‌هایش تحویل می‌شود"
    assert cq.get_queue_entry(6601)["status"] == "done"


def test_two_players_cannot_take_the_same_country(monkeypatch, tmp_path):
    """خطرناک‌ترین حالت: پذیرش همزمان دو نفر روی یک کشور."""
    database = _fresh(monkeypatch, tmp_path)
    cid = _country(database, 6701)
    cq.quarantine_country(cid)
    cq.join_queue(6801)
    cq.join_queue(6802)
    cq.process_queue(cq._now() + datetime.timedelta(days=3))

    # هر دو را دستی روی همان کشور «پیشنهادشده» می‌کنیم تا رقابت شبیه‌سازی شود
    conn = database.get_connection()
    with conn:
        conn.execute(
            "UPDATE country_queue SET status = 'offered', offered_country_id = ?, offer_expires_at = ?",
            (cid, cq._iso(cq._now() + datetime.timedelta(hours=6))),
        )
    conn.close()

    first_ok, _m1, _c1 = cq.accept_offer(6801)
    second_ok, message, _c2 = cq.accept_offer(6802)
    assert first_ok
    assert not second_ok, "نفر دوم نباید همان کشور را بگیرد"
    assert "در دسترس نیست" in message
    assert database.get_country_by_id(cid)["player_id"] == 6801
    assert cq.get_queue_entry(6802)["status"] == "waiting"


def test_an_unanswered_offer_expires_and_frees_the_queue(monkeypatch, tmp_path):
    database = _fresh(monkeypatch, tmp_path)
    cid = _country(database, 6901)
    cq.quarantine_country(cid)
    cq.join_queue(7001)
    cq.join_queue(7002)
    start = cq._now() + datetime.timedelta(days=3)
    cq.process_queue(start)
    assert cq.get_queue_entry(7001)["status"] == "offered"

    later = start + datetime.timedelta(hours=cq.OFFER_HOURS + 1)
    result = cq.process_queue(later)
    assert result["expired"], "پیشنهاد بی‌پاسخ باید منقضی شود"
    assert cq.get_queue_entry(7002)["status"] == "offered", "کشور به نفر بعدی می‌رسد"


def test_preferred_country_is_honoured_when_available(monkeypatch, tmp_path):
    database = _fresh(monkeypatch, tmp_path)
    iran = _country(database, 7101, key="iran", name="ایران")
    japan = _country(database, 7102, key="japan", name="ژاپن")
    cq.quarantine_country(iran)
    cq.quarantine_country(japan)
    cq.join_queue(7201, preferred_country_key="japan")

    cq.process_queue(cq._now() + datetime.timedelta(days=3))
    entry = cq.get_queue_entry(7201)
    assert entry["offered_country_id"] == japan, "کشور دلخواه باید اولویت داشته باشد"


def test_declining_returns_the_player_to_the_queue(monkeypatch, tmp_path):
    database = _fresh(monkeypatch, tmp_path)
    cid = _country(database, 7301)
    cq.quarantine_country(cid)
    cq.join_queue(7401)
    cq.process_queue(cq._now() + datetime.timedelta(days=3))

    assert cq.decline_offer(7401)
    entry = cq.get_queue_entry(7401)
    assert entry["status"] == "waiting" and entry["offered_country_id"] is None


def test_inactivity_job_quarantines_instead_of_deleting():
    import inspect
    import main as main_module

    source = inspect.getsource(main_module.check_daily_inactivity_job)
    assert "quarantine_country" in source
    assert "delete_country_by_id" not in source, "سلب مالکیت دیگر نباید کشور را پاک کند"


def test_admin_panel_exposes_quick_approve_and_queue():
    import inspect
    from handlers import admin as admin_handlers

    # «صف انتظار» حالا در زیرمنوی «بازیکنان و کشورها» است
    players = inspect.getsource(admin_handlers._players_submenu)
    assert "admin:queue" in players
    handler = inspect.getsource(admin_handlers.admin_callback_handler)
    assert "admin:quick_approve" in handler
    assert "admin:queue_run" in handler


def test_a_no_show_goes_to_the_back_of_the_queue(monkeypatch, tmp_path):
    """رگرسیون: بازیکن بی‌پاسخ بلافاصله دوباره اول صف می‌شد و صف قفل می‌ماند."""
    database = _fresh(monkeypatch, tmp_path)
    cid = _country(database, 7501)
    cq.quarantine_country(cid)
    cq.join_queue(7601)
    cq.join_queue(7602)

    start = cq._now() + datetime.timedelta(days=3)
    cq.process_queue(start)
    assert cq.get_queue_entry(7601)["status"] == "offered"

    cq.process_queue(start + datetime.timedelta(hours=cq.OFFER_HOURS + 1))
    assert cq.get_queue_entry(7602)["status"] == "offered", "نوبت باید به نفر بعدی برسد"
    assert cq.get_queue_entry(7601)["priority"] < cq.get_queue_entry(7602)["priority"]


# ─────────────────────────────────────────────────────────────────────────────
# ضد «کشور خلع‌شده بی‌صاحب می‌ماند»: پیوستن به صف باید همان لحظه موتور صف را
# روشن کند تا کشور آزاد (از جمله خلع‌شده/قرنطینه‌گذشته) فوراً پیشنهاد شود.
# ─────────────────────────────────────────────────────────────────────────────

def test_join_flow_offers_free_country_immediately(monkeypatch, tmp_path):
    database = _fresh(monkeypatch, tmp_path)
    cid = _country(database, 6001, key="instant_free_c", name="کشور آزاد")
    cq.quarantine_country(cid)   # مثل چرخه‌ی کامل: قرنطینه → انقضا → آزاد
    cq.release_expired_quarantines(cq._now() + datetime.timedelta(days=2))
    assert len(cq.get_free_countries()) == 1
    assert cq.queue_stats()["waiting"] == 0

    # بازیکن به صف می‌پیوندد (همان کاری که q:join انجام می‌دهد)…
    cq.join_queue(6002, first_name="ب", username="b")
    assert cq.queue_stats()["waiting"] == 1
    # …و پردازش فوری (که حالا در هندلر q:join صدا زده می‌شود) باید
    # بلافاصله پیشنهاد بسازد — نه اینکه تا جاب بعدی صبر کند.
    result = cq.process_queue()
    assert len(result["offered"]) == 1
    entry = cq.get_queue_entry(6002)
    assert entry["status"] == "offered"
    assert entry["offered_country_id"] == cid


def test_source_guard_join_triggers_process_and_refresh():
    src = open("handlers/queue.py", encoding="utf-8").read()
    idx = src.index('if data == "q:join":')
    window = src[idx:src.index("elif data", idx)]
    assert "process_queue" in window, "q:join باید فوراً موتور صف را اجرا کند"
    assert "queue_status(update, context)" in window, "بعد از join باید صفحه رندر شود"
