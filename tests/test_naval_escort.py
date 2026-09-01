"""اسکورت، قفل ناوگروه، قواعد درگیری و قرعه‌ی عبور از محاصره."""
import datetime
import importlib
import random
import config


def _fresh(monkeypatch, tmp_path, name="escort.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    import database as db
    importlib.reload(db)
    db.init_db()
    return db


def _c(db, uid, key, name, **f):
    cid = db.create_country(uid, name, "🏳️", country_key=key)
    for k, v in f.items():
        db.update_country_field(cid, k, v)
    return cid


def _avail(db, cid, key, now=None):
    """چند فروند از این قلم خاص آزاد است. create_country انبار کاتالوگ را هم
    پر می‌کند، پس نباید به ایندکس لیست تکیه کرد."""
    for d in db.get_deployable_ships(cid, now):
        if d["equipment_key"] == key:
            return d["available"]
    return 0


def _navy(db, cid, ckey, key, name, qty, price=20_000_000):
    conn = db.get_connection()
    with conn:
        conn.execute(
            "INSERT INTO country_assets (country_id, country_key, category, equipment_name,"
            " equipment_key, amount, buy_price, under_repair_qty) VALUES (?,?,?,?,?,?,?,0)",
            (cid, ckey, "Navy", name, key, qty, price))
    conn.close()


# ───────────────────── فرمول احتمال ─────────────────────

def test_passage_chance_never_zero_never_certain():
    assert config.passage_chance(0, 10_000) >= 0.02
    assert config.passage_chance(10 ** 9, 10_000) <= config.PASSAGE_MAX_CHANCE
    assert config.passage_chance(0, 0) == 1.0, "بدون مسدودکننده عبور آزاد است"


def test_more_escort_means_better_odds():
    prev = -1
    for r in (0, 0.5, 1, 2, 5, 20):
        ch = config.passage_chance(r * 1000, 1000)
        assert ch > prev
        prev = ch


def test_roe_shifts_the_odds_in_the_right_direction():
    base = config.passage_chance(1000, 1000, "seize")
    assert config.passage_chance(1000, 1000, "inspect") > base
    assert config.passage_chance(1000, 1000, "fire") < base


def test_unknown_roe_falls_back_to_default():
    assert config.passage_chance(1000, 1000, "nonsense") == config.passage_chance(
        1000, 1000, config.NAVAL_ROE_DEFAULT)


# ───────────────────── قفل ناوگروه ─────────────────────

def test_locked_ships_cannot_be_sent_twice(monkeypatch, tmp_path):
    """بدون قفل، اسکورت به یک مالیات ساده تبدیل می‌شود."""
    db = _fresh(monkeypatch, tmp_path)
    cid = _c(db, 1, "usa", "آمریکا")
    _navy(db, cid, "usa", "burke", "Arleigh Burke Destroyer", 5, 30_000_000)
    now = datetime.datetime(2026, 9, 1, 8, 0, 0)

    ok, _ = db.lock_task_force(cid, {"burke": 4}, config.ESCORT_LOCK_HOURS, "escort", now)
    assert ok
    ok2, msg = db.lock_task_force(cid, {"burke": 3}, config.ESCORT_LOCK_HOURS, "escort", now)
    assert not ok2 and "آزاد است" in msg

    assert _avail(db, cid, "burke", now) == 1


def test_locks_expire_on_their_own(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "escort_exp.db")
    cid = _c(db, 1, "usa", "آمریکا")
    _navy(db, cid, "usa", "burke", "Arleigh Burke Destroyer", 5, 30_000_000)
    now = datetime.datetime(2026, 9, 1, 8, 0, 0)
    db.lock_task_force(cid, {"burke": 5}, 8, "escort", now)

    assert _avail(db, cid, "burke", now) == 0
    later = now + datetime.timedelta(hours=9)
    assert _avail(db, cid, "burke", later) == 5
    assert db.purge_expired_naval_locks(later) == 1


def test_ships_in_repair_cannot_be_deployed(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "escort_rep.db")
    cid = _c(db, 1, "usa", "آمریکا")
    _navy(db, cid, "usa", "burke", "Arleigh Burke Destroyer", 6, 30_000_000)
    db.damage_ships(cid, "burke", 4)

    assert _avail(db, cid, "burke") == 2
    ok, msg = db.lock_task_force(cid, {"burke": 3}, 8)
    assert not ok


def test_empty_task_force_is_rejected(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "escort_empty.db")
    cid = _c(db, 1, "usa", "آمریکا")
    assert db.lock_task_force(cid, {}, 8)[0] is False
    assert db.lock_task_force(cid, {"burke": 0}, 8)[0] is False


# ───────────────────── درخواست اسکورت ─────────────────────

def test_escort_request_accept_charges_and_locks(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "escort_req.db")
    saudi = _c(db, 1, "saudi", "عربستان")
    usa = _c(db, 2, "usa", "آمریکا", treasury=500_000_000, oil_reserves=90_000_000)
    iran = _c(db, 3, "iran", "ایران")
    _navy(db, usa, "usa", "burke", "Arleigh Burke Destroyer", 6, 30_000_000)
    now = datetime.datetime(2026, 9, 1, 8, 0, 0)

    ok, _msg, rid = db.create_escort_request(saudi, usa, iran, {"kind": "aid"}, now)
    assert ok and rid > 0

    before = db.get_country_by_id(usa)
    ok, msg = db.accept_escort_request(rid, {"burke": 3}, now)
    after = db.get_country_by_id(usa)

    assert ok, msg
    assert after["treasury"] < before["treasury"]
    assert after["oil_reserves"] < before["oil_reserves"]
    assert db.get_escort_request(rid)["status"] == "accepted"
    assert _avail(db, usa, "burke", now) == 3


def test_escort_rejected_when_escort_cannot_pay(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "escort_poor.db")
    saudi = _c(db, 1, "saudi", "عربستان")
    usa = _c(db, 2, "usa", "آمریکا", treasury=0, oil_reserves=0)
    _navy(db, usa, "usa", "nimitz", "Nimitz Class Carrier", 2, 46_000_000)
    ok, _m, rid = db.create_escort_request(saudi, usa, None, {})

    ok2, msg = db.accept_escort_request(rid, {"nimitz": 1})

    assert not ok2 and ("خزانه" in msg or "سوخت" in msg)
    assert db.get_escort_request(rid)["status"] == "pending"
    assert _avail(db, usa, "nimitz") == 2, "نباید قفل شده باشد"


def test_cannot_escort_yourself(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "escort_self.db")
    cid = _c(db, 1, "usa", "آمریکا")
    assert db.create_escort_request(cid, cid, None, {})[0] is False


def test_duplicate_pending_request_is_blocked(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "escort_dup.db")
    a = _c(db, 1, "saudi", "عربستان")
    b = _c(db, 2, "usa", "آمریکا")
    assert db.create_escort_request(a, b, None, {})[0] is True
    assert db.create_escort_request(a, b, None, {})[0] is False


def test_expired_request_cannot_be_accepted(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "escort_ttl.db")
    a = _c(db, 1, "saudi", "عربستان")
    b = _c(db, 2, "usa", "آمریکا", treasury=10 ** 9, oil_reserves=10 ** 8)
    _navy(db, b, "usa", "burke", "Arleigh Burke Destroyer", 3, 30_000_000)
    now = datetime.datetime(2026, 9, 1, 8, 0, 0)
    _ok, _m, rid = db.create_escort_request(a, b, None, {}, now)

    late = now + datetime.timedelta(hours=config.ESCORT_REQUEST_TTL_HOURS + 1)
    ok, msg = db.accept_escort_request(rid, {"burke": 1}, late)
    assert not ok and "مهلت" in msg

    assert db.expire_stale_escort_requests(late) == 1
    assert db.get_escort_request(rid)["status"] == "expired"


def test_rejecting_a_request(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "escort_rej.db")
    a = _c(db, 1, "saudi", "عربستان")
    b = _c(db, 2, "usa", "آمریکا")
    _ok, _m, rid = db.create_escort_request(a, b, None, {})
    assert db.reject_escort_request(rid)[0] is True
    assert db.get_escort_request(rid)["status"] == "rejected"
    assert db.reject_escort_request(rid)[0] is False, "دوبار رد کردن نباید کار کند"


# ───────────────────── قواعد درگیری ─────────────────────

def test_roe_defaults_and_is_settable(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "roe.db")
    iran = _c(db, 1, "iran", "ایران")
    saudi = _c(db, 2, "saudi", "عربستان")
    db.create_naval_blockade(iran, saudi, {"boat": 10})

    assert db.get_blockade_roe(iran, saudi) == config.NAVAL_ROE_DEFAULT
    assert db.set_blockade_roe(iran, saudi, "fire") is True
    assert db.get_blockade_roe(iran, saudi) == "fire"
    assert db.set_blockade_roe(iran, saudi, "bogus") is False
    assert db.get_blockade_roe(iran, saudi) == "fire"


def test_strait_roe_roundtrip(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "roe2.db")
    assert db.get_strait_roe("hormuz") == config.NAVAL_ROE_DEFAULT
    assert db.set_strait_roe("hormuz", "inspect") is True
    assert db.get_strait_roe("hormuz") == "inspect"
    assert db.set_strait_roe("hormuz", "nope") is False


# ───────────────────── قرعه‌ی عبور ─────────────────────

def test_weak_runner_usually_fails_strong_blockade(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "pass1.db")
    sender = _c(db, 1, "saudi", "عربستان")
    rng = random.Random(7)
    wins = sum(db.resolve_sea_passage(sender, None, blocker_power=100_000, rng=rng)["passed"]
               for _ in range(400))
    assert 20 < wins < 120, f"نرخ عبور بی‌اسکورت غیرمنطقی: {wins}/400"


def test_strong_escort_usually_gets_through(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "pass2.db")
    sender = _c(db, 1, "saudi", "عربستان")
    usa = _c(db, 2, "usa", "آمریکا")
    _navy(db, usa, "usa", "burke", "Arleigh Burke Destroyer", 40, 30_000_000)
    rng = random.Random(11)
    wins = sum(db.resolve_sea_passage(sender, None, usa, {"burke": 40}, "seize",
                                      blocker_power=500, rng=rng)["passed"] for _ in range(300))
    assert wins > 200, f"اسکورت قوی باید معمولاً رد شود: {wins}/300"


def test_outcome_is_always_a_known_label(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "pass3.db")
    sender = _c(db, 1, "saudi", "عربستان")
    rng = random.Random(3)
    for roe in ("inspect", "seize", "fire"):
        for _ in range(60):
            r = db.resolve_sea_passage(sender, None, roe=roe, blocker_power=5_000, rng=rng)
            assert r["outcome"] in config.PASSAGE_OUTCOMES
            assert 0.0 <= r["cargo_ratio"] <= 1.0


def test_inspect_roe_never_seizes_or_strikes(monkeypatch, tmp_path):
    """با «فقط بازرسی» نباید محموله مصادره یا منهدم شود."""
    db = _fresh(monkeypatch, tmp_path, "pass4.db")
    sender = _c(db, 1, "saudi", "عربستان")
    rng = random.Random(5)
    outs = {db.resolve_sea_passage(sender, None, roe="inspect", blocker_power=200_000,
                                   rng=rng)["outcome"] for _ in range(300)}
    assert "seized" not in outs and "struck" not in outs


def test_capital_escort_never_sinks_in_an_incident(monkeypatch, tmp_path):
    """قلب درخواست بازیکن، این بار در مسیر واقعی درگیری."""
    db = _fresh(monkeypatch, tmp_path, "pass5.db")
    sender = _c(db, 1, "saudi", "عربستان")
    usa = _c(db, 2, "usa", "آمریکا")
    _navy(db, usa, "usa", "nimitz", "Nimitz Class Carrier", 30, 46_000_000)
    rng = random.Random(13)
    for _ in range(120):
        db.resolve_sea_passage(sender, None, usa, {"nimitz": 2}, "fire",
                               blocker_power=200_000, rng=rng)
    row = next(r for r in db.get_country_assets(usa, category="Navy") if r["equipment_key"] == "nimitz")
    assert row["amount"] == 30, "ناو هواپیمابر نباید در حادثه غرق شود"
    assert row["under_repair_qty"] > 0, "ولی باید آسیب دیده باشد"


def test_light_boats_do_sink(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "pass6.db")
    sender = _c(db, 1, "saudi", "عربستان")
    usa = _c(db, 2, "usa", "آمریکا")
    _navy(db, usa, "usa", "boat", "قایق تندرو گشتی", 200, 500_000)
    rng = random.Random(17)
    for _ in range(60):
        db.resolve_sea_passage(sender, None, usa, {"boat": 3}, "fire",
                               blocker_power=200_000, rng=rng)
    row = next(r for r in db.get_country_assets(usa, category="Navy") if r["equipment_key"] == "boat")
    assert row["amount"] < 200, "قایق سبک باید بتواند غرق شود"


def test_blockader_can_also_take_losses(monkeypatch, tmp_path):
    """درگیری دوطرفه است، نه یک‌طرفه."""
    db = _fresh(monkeypatch, tmp_path, "pass7.db")
    sender = _c(db, 1, "saudi", "عربستان")
    usa = _c(db, 2, "usa", "آمریکا")
    iran = _c(db, 3, "iran", "ایران")
    _navy(db, usa, "usa", "burke", "Arleigh Burke Destroyer", 60, 30_000_000)
    _navy(db, iran, "iran", "boat", "قایق تندرو رزمی", 300, 500_000)
    db.create_naval_blockade(iran, sender, {"boat": 100})

    rng = random.Random(23)
    hurt = 0
    for _ in range(40):
        r = db.resolve_sea_passage(sender, iran, usa, {"burke": 10}, "fire",
                                   blocker_power=800, rng=rng)
        hurt += len(r["blocker_losses"])
    assert hurt > 0, "مسدودکننده هم باید تلفات بدهد"


def test_no_blocker_means_free_passage(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "pass8.db")
    sender = _c(db, 1, "saudi", "عربستان")
    # ۲۰٪ مواقع «عبور با آسیب» است، پس cargo_ratio همیشه ۱.۰ نیست
    for _ in range(30):
        r = db.resolve_sea_passage(sender, None, blocker_power=0)
        assert r["passed"] is True
        assert r["outcome"] in ("passed", "passed_hurt")
        assert r["cargo_ratio"] > 0
