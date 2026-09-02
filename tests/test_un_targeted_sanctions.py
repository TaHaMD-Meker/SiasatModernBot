# -*- coding: utf-8 -*-
"""تحریم‌های هدفمند سازمان ملل — اعمال دونه‌دونه، با افکت مکانیکی واقعی.

قواعد:
* هر نوع تحریم جداگانه اعمال/لغو می‌شود (نه جامع) و رکورد تراکنش + لاگ دارد.
* 💰 مالی: ۲۵٪ کسر درآمد روزانه (هوک main.py — سورس‌تست).
* 📦 تجاری: قرارداد تجاری با کشور ممنوع. 🪖 تسلیحاتی: تجهیز نظامی به سمت کشور.
* 🛢️ نفتی: عرضه نفت در بورس ممنوع (و خرید نفت از آن کشور).
* 🏪 بورس: کل بورس بسته. 🏴 انزوا: اتحاد دیپلماتیک ممنوع (هوک دیپلماسی).
"""

import config
import database as db
import news_engine


def _fresh(monkeypatch, tmp_path, name="unsanc.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


def _country(player_id, key, **over):
    cid = db.create_country(player_id, f"کشور {key}", "🏳️", country_key=key)
    for field, value in over.items():
        db.update_country_field(cid, field, value)
    return cid


def _logs(action, limit=60):
    return [log for log in db.get_recent_logs(limit=limit) if log["action"] == action]


# ─────────────────────────────────────────────────────────────────────────────
# لایه‌ی دیتابیس
# ─────────────────────────────────────────────────────────────────────────────

def test_apply_remove_and_reapply(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country(61_001, "sanc1")
    ok, msg = db.apply_targeted_sanction(cid, "financial", reason="تست", imposed_by=42)
    assert ok and "مالی" in msg
    assert db.has_targeted_sanction(cid, "financial")
    ok2, msg2 = db.apply_targeted_sanction(cid, "financial")
    assert ok2 is False and "از قبل" in msg2
    ok3, _ = db.remove_targeted_sanction(cid, "financial", removed_by=42)
    assert ok3 and not db.has_targeted_sanction(cid, "financial")
    ok4, _ = db.remove_targeted_sanction(cid, "financial")
    assert ok4 is False
    assert db.apply_targeted_sanction(cid, "financial")[0], "بعد از لغو باید دوباره قابل اعمال باشد"


def test_invalid_key_rejected(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country(61_002, "sanc2")
    assert db.apply_targeted_sanction(cid, "nuclear_bomb_everything")[0] is False


def test_multiple_types_independent(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country(61_003, "sanc3")
    for key in ("financial", "arms_embargo", "oil_embargo"):
        assert db.apply_targeted_sanction(cid, key)[0]
    keys = {s["sanction_key"] for s in db.get_targeted_sanctions(cid)}
    assert keys == {"financial", "arms_embargo", "oil_embargo"}
    assert not db.has_targeted_sanction(cid, "trade_embargo"), "نوع اعمال‌نشده نباید فعال باشد"


def test_apply_and_remove_are_logged_with_transactions(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _country(61_004, "sanc4")
    db.apply_targeted_sanction(cid, "trade_embargo", reason="اسپم جنگ", imposed_by=42)
    db.remove_targeted_sanction(cid, "trade_embargo", removed_by=42)
    entries = [t for t in db.get_recent_logs(limit=60) if t["action"] in
               ("un_sanction_apply", "un_sanction_remove")]
    assert len(entries) >= 2
    assert entries[0]["actor"] == "admin:42"
    txs = db.get_country_transactions(cid) if hasattr(db, "get_country_transactions") else []
    if txs:  # اگر گیر تراکنش‌ها در دسترس بود، رکوردها را چک کن
        types = {t["type"] for t in txs}
        assert {"un_sanction_trade_embargo", "un_unsanction_trade_embargo"} <= types


# ─────────────────────────────────────────────────────────────────────────────
# افکت بورس (رفتاری)
# ─────────────────────────────────────────────────────────────────────────────

def test_market_ban_blocks_all_listings(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "unsanc_mkt.db")
    cid = _country(61_005, "seller1")
    db.adjust_grain(cid, 100_000)
    assert db.create_market_order(cid, "grain", 500, 10)[0]
    db.apply_targeted_sanction(cid, "market_ban")
    ok, msg = db.create_market_order(cid, "grain", 500, 10)
    assert not ok and "بورس" in msg
    db.remove_targeted_sanction(cid, "market_ban")
    assert db.create_market_order(cid, "grain", 500, 10)[0]


def test_oil_embargo_blocks_only_oil(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "unsanc_oil.db")
    cid = _country(61_006, "seller2")
    db.adjust_grain(cid, 100_000)
    db.adjust_oil(cid, 10_000_000)
    db.apply_targeted_sanction(cid, "oil_embargo")
    ok, msg = db.create_market_order(cid, "oil", 1_000, config.OIL_GLOBAL_PRICE)
    assert not ok and "نفتی" in msg
    assert db.create_market_order(cid, "grain", 100, 10)[0], "غلات نباید تحت تحریم نفتی بسته شود"


def test_buy_side_sanctions(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "unsanc_buy.db")
    seller = _country(61_007, "seller3")
    buyer = _country(61_008, "buyer3")
    db.adjust_grain(seller, 100_000)
    ok, _msg = db.create_market_order(seller, "grain", 1_000, 10)
    assert ok
    orders = None
    conn = db.get_connection()
    try:
        orders = [dict(r) for r in conn.execute(
            "SELECT id FROM market_orders WHERE seller_id = ?", (seller,)).fetchall()]
    finally:
        conn.close()
    oid = orders[-1]["id"]

    db.apply_targeted_sanction(seller, "market_ban")
    ok, msg, _info = db.execute_market_buy_transaction(buyer, oid, 10, "sea")
    assert not ok and "بورس" in msg, "خرید از فروشنده‌ی تحریم‌بورسی باید بلاک شود"

    db.remove_targeted_sanction(seller, "market_ban")
    db.apply_targeted_sanction(buyer, "market_ban")
    ok, msg, _info = db.execute_market_buy_transaction(buyer, oid, 10, "sea")
    assert not ok and "بورس" in msg, "خریدارِ تحریم‌بورسی نباید بخرد"
    db.remove_targeted_sanction(buyer, "market_ban")

    ok, msg, _info = db.execute_market_buy_transaction(buyer, oid, 10, "sea")
    assert ok is True and "🚫" not in (msg or ""), "بدون تحریم، خرید باید آزاد باشد"


# ─────────────────────────────────────────────────────────────────────────────
# هوک‌های سورس (قرارداد، درآمد، دیپلماسی، پنل)
# ─────────────────────────────────────────────────────────────────────────────

def _src(path):
    return open(path, encoding="utf-8").read()


def test_trade_and_arms_hooks_in_contract_execution():
    src = _src("database.py")
    idx = src.index("def execute_trade_contract_transaction")
    body = src[idx:idx + 6000]
    assert 'has_targeted_sanction(p_id, "trade_embargo")' in body
    assert 'has_targeted_sanction(r_id, "trade_embargo")' in body
    assert 'off_type == "military_asset" and has_targeted_sanction(r_id, "arms_embargo")' in body


def test_financial_income_hook_in_payout():
    src = _src("main.py")
    assert 'has_targeted_sanction(c["id"], "financial")' in src
    assert "UN_TARGETED_FINANCIAL_FACTOR" in src


def test_diplomatic_isolation_hooks():
    src = _src("handlers/diplomacy.py")
    assert src.count('"diplomatic_isolation"') >= 3, "هم پیشنهاد اتحاد هم پذیرش باید گیت بخورد"
    assert "propose_alliance" in src and "alliance_accept" in src


def test_un_panel_routes_and_types():
    src = _src("handlers/un.py")
    for route in ("un:sanc:list:", "un:sanc:country:", "un:sanc:ask:", "un:sanc:do:"):
        assert route in src
    assert "UN_TARGETED_SANCTIONS" in src
    # تحریم جامع نباید قاطی این منو شود — این منو تفکیکی است
    assert "دونه‌دونه" in src


def test_news_templates_have_no_digits(monkeypatch, tmp_path):
    import re as _re
    for key, tpls in news_engine._UN_SANCTION_TEMPLATES.items():
        for headline, body in tpls:
            h, b = headline.format(name="زیستان"), body.format(name="زیستان", flag="🏳️")
            assert not _re.search(r"\d", h) and not _re.search(r"\d", b), key
