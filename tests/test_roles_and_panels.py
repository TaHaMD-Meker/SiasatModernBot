"""سیستم نقش‌ها: مالک، داور، لاگ، امتیاز و مرزهای دسترسی."""
import importlib
import config


def _fresh(monkeypatch, tmp_path, name="roles.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    import database as db
    importlib.reload(db)
    db.init_db()
    return db


OWNER = 900001
REF = 900002
RANDOM = 900003


# ─────────────── نقش‌ها ───────────────

def test_owner_comes_from_config_only(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path)
    monkeypatch.setattr(config, "ADMIN_IDS", [OWNER])
    assert db.is_owner(OWNER) and db.user_role(OWNER) == db.ROLE_OWNER
    assert not db.is_owner(RANDOM)


def test_owner_is_automatically_a_referee(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "roles2.db")
    monkeypatch.setattr(config, "ADMIN_IDS", [OWNER])
    assert db.is_referee(OWNER) is True


def test_random_user_has_no_role(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "roles3.db")
    monkeypatch.setattr(config, "ADMIN_IDS", [OWNER])
    assert db.user_role(RANDOM) is None
    assert db.is_referee(RANDOM) is False


def test_add_and_remove_referee(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "roles4.db")
    monkeypatch.setattr(config, "ADMIN_IDS", [OWNER])

    ok, _ = db.add_referee(REF, OWNER, "علی")
    assert ok and db.is_referee(REF)
    assert db.user_role(REF) == db.ROLE_REFEREE

    ok2, _ = db.remove_referee(REF, OWNER)
    assert ok2 and not db.is_referee(REF)
    assert db.user_role(REF) is None


def test_cannot_add_owner_as_referee(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "roles5.db")
    monkeypatch.setattr(config, "ADMIN_IDS", [OWNER])
    ok, msg = db.add_referee(OWNER, OWNER)
    assert not ok and "مالک" in msg


def test_duplicate_add_is_rejected_but_restore_works(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "roles6.db")
    monkeypatch.setattr(config, "ADMIN_IDS", [OWNER])
    assert db.add_referee(REF, OWNER)[0] is True
    assert db.add_referee(REF, OWNER)[0] is False, "دوبار افزودن نباید کار کند"
    db.remove_referee(REF, OWNER)
    assert db.add_referee(REF, OWNER)[0] is True, "بعد از خلع باید بشود برگرداند"


def test_removing_a_non_referee_fails(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "roles7.db")
    monkeypatch.setattr(config, "ADMIN_IDS", [OWNER])
    assert db.remove_referee(RANDOM, OWNER)[0] is False


# ─────────────── لاگ و امتیاز ───────────────

def test_actions_are_logged_with_points(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "roles8.db")
    monkeypatch.setattr(config, "ADMIN_IDS", [OWNER])
    db.add_referee(REF, OWNER, "داور")

    db.log_admin_action(REF, db.ROLE_REFEREE, "report_registered", "iran")
    db.log_admin_action(REF, db.ROLE_REFEREE, "war_action", "uk")

    acts = db.get_admin_actions(REF)
    assert len(acts) == 2
    expected = db.REFEREE_POINTS["report_registered"] + db.REFEREE_POINTS["war_action"]
    assert db.get_game_admin(REF)["points"] == expected


def test_zero_point_actions_do_not_inflate_score(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "roles9.db")
    monkeypatch.setattr(config, "ADMIN_IDS", [OWNER])
    db.add_referee(REF, OWNER)
    for _ in range(5):
        db.log_admin_action(REF, db.ROLE_REFEREE, "inventory_export", "iran")
    assert db.get_game_admin(REF)["points"] == 0
    assert len(db.get_admin_actions(REF)) == 5


def test_adding_a_referee_is_itself_logged(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "roles10.db")
    monkeypatch.setattr(config, "ADMIN_IDS", [OWNER])
    db.add_referee(REF, OWNER)
    owner_acts = db.get_admin_actions(OWNER)
    assert any(a["action"] == "referee_added" for a in owner_acts)


def test_scoreboard_sorts_active_first_then_points(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "roles11.db")
    monkeypatch.setattr(config, "ADMIN_IDS", [OWNER])
    db.add_referee(REF, OWNER, "پرکار")
    db.add_referee(REF + 1, OWNER, "کم‌کار")
    db.add_referee(REF + 2, OWNER, "خلع‌شده")
    db.remove_referee(REF + 2, OWNER)
    for _ in range(3):
        db.log_admin_action(REF, db.ROLE_REFEREE, "report_registered", "x")
    db.log_admin_action(REF + 1, db.ROLE_REFEREE, "report_validated", "x")

    board = db.get_referee_scoreboard()
    assert board[0]["user_id"] == REF
    assert board[-1]["active"] == 0
    assert board[0]["actions"] == 3


def test_log_never_crashes_on_weird_input(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "roles12.db")
    monkeypatch.setattr(config, "ADMIN_IDS", [OWNER])
    db.log_admin_action(REF, None, "unknown_action", "x" * 500, "y" * 900)
    assert db.get_admin_actions(REF)


# ─────────────── مرز دسترسی پنل‌ها ───────────────

def test_owner_only_routes_are_guarded():
    with open("handlers/admin.py", encoding="utf-8") as f:
        src = f.read()
    for route in ("admin:referees", "admin:ref_list", "admin:ref_scores", "admin:ref_add"):
        idx = src.index(f'data == "{route}"') if f'data == "{route}"' in src \
            else src.index(f'data.startswith("{route}')
        window = src[idx:idx + 400]
        assert "is_owner" in window, f"{route} بدون گارد مالک است"


def test_referee_panel_exists_and_is_limited():
    with open("handlers/referee.py", encoding="utf-8") as f:
        src = f.read()
    assert "ref:inv" in src and "ref:war" in src
    # داور نباید به این‌ها دسترسی داشته باشد
    for forbidden in ("update_country_field", "delete_country", "reset_all_countries",
                      "apply_cstat_delta", "grant_cash"):
        assert forbidden not in src, f"پنل داور نباید {forbidden} داشته باشد"


def test_referee_panel_guards_every_callback():
    with open("handlers/referee.py", encoding="utf-8") as f:
        src = f.read()
    cb = src[src.index("async def referee_callback"):]
    assert "if not db.is_referee(uid)" in cb, "کال‌بک داور گارد ندارد"


def test_owner_panel_button_is_in_danger_section():
    with open("handlers/admin.py", encoding="utf-8") as f:
        src = f.read()
    assert 'callback_data="admin:referees"' in src
    assert "وضعیت ادمین‌ها" in src


def test_referee_command_registered_in_main():
    with open("main.py", encoding="utf-8") as f:
        src = f.read()
    assert "referee_panel.register(app)" in src
    assert "ref_awaiting" in src, "ورودی متنی داور به main وصل نشده"
