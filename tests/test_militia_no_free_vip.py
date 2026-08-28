# -*- coding: utf-8 -*-
"""مجوز گروه غیردولتی نباید اشتراک VIP بدهد.

قبلاً هر گروه با `is_vip = 1` ساخته می‌شد؛ یعنی خریدار با ۱۰۰ هزار تومان
برای همیشه تخفیف نگهداری ارتش و سقف مانور بالاتر می‌گرفت. آن مزیت حذف شد.
"""

import inspect

import config
import database as db
from handlers import operations, vip


def _fresh(monkeypatch, tmp_path, name="militia.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


def _make_militia(player_id=55_001, name="گروه آزمون"):
    conn = db.get_connection()
    try:
        with conn:
            cur = conn.cursor()
            cid = db._create_custom_militia_with_cur(cur, player_id, name)
    finally:
        conn.close()
    return cid


def test_new_militia_is_not_vip(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _make_militia()
    country = db.get_country_by_id(cid)
    assert int(country.get("is_vip") or 0) == 0
    assert not country.get("vip_tier")
    assert not country.get("vip_expires_at")


def test_militia_gets_one_drill_like_everyone_else(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "militia_drill.db")
    cid = _make_militia(55_002)
    country = db.get_country_by_id(cid)
    assert operations.get_country_max_drills(country) == 1


def test_militia_pays_full_maintenance(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "militia_maint.db")
    cid = _make_militia(55_003)
    info = db.calculate_country_maintenance_cost(cid)
    # تخفیف فقط از فناوری می‌آید؛ گروه تازه tech_level = 1 دارد پس صفر است
    assert info["discount_pct"] == 0


def test_militia_keeps_its_real_package(monkeypatch, tmp_path):
    """حذف VIP نباید به بودجه، نیرو یا تجهیزات گروه دست بزند."""
    _fresh(monkeypatch, tmp_path, "militia_pack.db")
    cid = _make_militia(55_004)
    country = db.get_country_by_id(cid)
    assert country["treasury"] == 25_000_000
    assert country["active_personnel"] == 60_000
    assert country["daily_income"] == 2_800_000
    assets = db.get_country_assets(cid) if hasattr(db, "get_country_assets") else []
    assert len(assets) > 0


def test_vip_can_still_be_bought_separately(monkeypatch, tmp_path):
    """مسیر خرید VIP دست‌نخورده است."""
    _fresh(monkeypatch, tmp_path, "militia_vip_path.db")
    cid = _make_militia(55_005)
    ok, msg = db.admin_grant_item(cid, "vip_1month", admin_id=1)
    assert ok, msg
    country = db.get_country_by_id(cid)
    assert int(country["is_vip"]) == 1


def test_purchase_pages_no_longer_promise_a_free_vip():
    source = inspect.getsource(vip)
    assert "VIP هدیه" not in source, "صفحه‌ی خرید هنوز اشتراک VIP رایگان وعده می‌دهد"


def test_creator_docstring_records_the_decision():
    assert "اشتراک VIP نمی‌دهد" in (db._create_custom_militia_with_cur.__doc__ or "")
