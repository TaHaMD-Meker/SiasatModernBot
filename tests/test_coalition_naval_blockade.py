# -*- coding: utf-8 -*-
"""تست‌های سیستم محاصره دریایی ائتلافی (Coalition Blockade) و انتخاب ناوگروه (Task Force)."""

import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import database as db  # noqa: E402


@pytest.fixture(autouse=True)
def setup_test_db(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    test_db_path = os.path.join(tmpdir, "test_coalition_blockade.db")
    monkeypatch.setattr(config, "DB_PATH", test_db_path)
    import importlib
    importlib.reload(db)
    db.init_db()
    yield test_db_path


def test_task_force_naval_power_calculation():
    """قدرت ناوگروه انتخابی فقط بر اساس شناورهای تخصیص‌داده‌شده محاسبه می‌شود."""
    usa_id = db.create_country(9001, "آمریکا", "🇺🇸", country_key="usa")
    full_power = db.calculate_naval_power(usa_id)
    assert full_power > 15000

    # تخصیص ناوگروه محدود: فقط ۲ ناوشکن آرلی بورک (هر کدام ۸۰ امتیاز)
    task_force = {"burke_class": 2}
    tf_power = db.calculate_task_force_naval_power(usa_id, task_force)
    assert tf_power == 160
    assert tf_power < full_power


def test_coalition_requires_official_military_alliance():
    """فقط کشورهای دارای پیمان اتحاد نظامی رسمی (Allied) مجاز به پیوستن به ائتلاف محاصره هستند."""
    leader_id = db.create_country(9002, "بریتانیا", "🇬🇧", country_key="uk")
    ally_id = db.create_country(9003, "فرانسه", "🇫🇷", country_key="france")
    target_id = db.create_country(9004, "یمن", "🇾🇪", country_key="yemen")

    # بدون اتحاد رسمی
    db.create_naval_blockade(leader_id, target_id)
    ok_non_allied, msg = db.join_naval_blockade(leader_id, target_id, ally_id)
    assert not ok_non_allied
    assert "پیمان اتحاد نظامی رسمی" in msg

    # ثبت پیمان اتحاد رسمی
    db.set_diplomatic_relation(leader_id, ally_id, "allied")
    ok_allied, msg_allied = db.join_naval_blockade(leader_id, target_id, ally_id, {"fremm_frigate": 2})
    assert ok_allied
    assert "با موفقیت به ائتلاف محاصره دریایی پیوست" in msg_allied


def test_coalition_power_aggregates_all_allies():
    """قدرت دفاعی محاصره مجموع توان رزمی رهبر و تمام متحدان پیوسته به ائتلاف است."""
    leader_id = db.create_country(9005, "بریتانیا", "🇬🇧", country_key="uk")
    ally1_id = db.create_country(9006, "فرانسه", "🇫🇷", country_key="france")
    target_id = db.create_country(9007, "هدف", "🏳️", country_key="iran")

    # رهبر با ناوگروه اولیه: ۴ ناوشکن تایپ ۴۵ (۴ * ۸۰ = ۳۲۰)
    lead_tf = {"type_45_destroyer": 4}
    db.create_naval_blockade(leader_id, target_id, lead_tf)

    pwr1, parts1 = db.calculate_blockade_defense_power(target_id)
    assert pwr1 == 320
    assert len(parts1) == 1

    # پیوستن فرانسه با ۳ ناوچه فرم (۳ * ۳۰ = ۹۰)
    db.set_diplomatic_relation(leader_id, ally1_id, "allied")
    ally_tf = {"fremm_frigate": 3}
    ok, _ = db.join_naval_blockade(leader_id, target_id, ally1_id, ally_tf)
    assert ok

    pwr2, parts2 = db.calculate_blockade_defense_power(target_id)
    assert pwr2 == 320 + 90  # 410
    assert len(parts2) == 2


def test_leave_coalition_reduces_blockade_power():
    """با خروج متحد از ائتلاف، توان رزمی محاصره به همان میزان کسر می‌گردد."""
    leader_id = db.create_country(9008, "رهبر", "🇬🇧", country_key="uk")
    ally_id = db.create_country(9009, "متحد", "🇫🇷", country_key="france")
    target_id = db.create_country(9010, "هدف", "🏳️", country_key="iran")

    db.set_diplomatic_relation(leader_id, ally_id, "allied")
    db.create_naval_blockade(leader_id, target_id, {"type_45_destroyer": 2})
    db.join_naval_blockade(leader_id, target_id, ally_id, {"fremm_frigate": 2})

    pwr_before, _ = db.calculate_blockade_defense_power(target_id)
    assert pwr_before == 160 + 60

    # خروج متحد
    ok, _ = db.leave_naval_blockade(leader_id, target_id, ally_id)
    assert ok

    pwr_after, parts = db.calculate_blockade_defense_power(target_id)
    assert pwr_after == 160
    assert len(parts) == 1


def test_breaking_coalition_blockade_inflicts_retreat_losses():
    """شکستن محاصره ائتلافی، تلفات عقب‌نشینی را بین رهبر و متحدان اعمال می‌کند."""
    leader_id = db.create_country(9011, "رهبر", "🇬🇧", country_key="uk")
    ally_id = db.create_country(9012, "متحد", "🇫🇷", country_key="france")
    target_id = db.create_country(9013, "هدف", "🇮🇷", country_key="iran")

    db.set_diplomatic_relation(leader_id, ally_id, "allied")
    db.create_naval_blockade(leader_id, target_id, {"type_45_destroyer": 4})
    db.join_naval_blockade(leader_id, target_id, ally_id, {"fremm_frigate": 4})

    lead_before = db.get_asset_by_key(leader_id, "type_45_destroyer")["amount"]
    ally_before = db.get_asset_by_key(ally_id, "fremm_frigate")["amount"]

    losses = db.break_naval_blockade(target_id, apply_task_force_losses=True)
    assert len(losses) >= 2
    assert not db.is_country_blockaded(target_id)

    lead_after = db.get_asset_by_key(leader_id, "type_45_destroyer")["amount"]
    ally_after = db.get_asset_by_key(ally_id, "fremm_frigate")["amount"]
    assert lead_after < lead_before
    assert ally_after < ally_before
