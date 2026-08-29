# -*- coding: utf-8 -*-
"""
Unit tests for the Seasonal Battle Pass & Strategic Campaigns System (۳۰۰,۰۰۰ Toman COD-style Pass).
"""

import os
import sys
import tempfile
import importlib
import pytest
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import database as db
from handlers.battlepass import (
    battlepass_menu,
    battlepass_claim_all,
    battlepass_view_tiers,
    battlepass_challenges_menu,
    battlepass_buy_pass_prompt,
    battlepass_callback_handler
)


class MockQuery:
    def __init__(self, from_user_id=123456, data="bp:menu"):
        self.from_user = type("User", (), {"id": from_user_id})()
        self.data = data
        self.last_text = ""
        self.last_reply_markup = None
        self.last_parse_mode = None
        self.answered = False

    async def answer(self, text=None, show_alert=False):
        self.answered = True

    async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
        self.last_text = text
        self.last_reply_markup = reply_markup
        self.last_parse_mode = parse_mode


class MockMessage:
    def __init__(self, text="", from_user_id=123456):
        self.text = text
        self.from_user = type("User", (), {"id": from_user_id})()
        self.replies = []

    async def reply_text(self, text, reply_markup=None, parse_mode=None):
        self.replies.append({"text": text, "reply_markup": reply_markup, "parse_mode": parse_mode})


class MockUpdate:
    def __init__(self, message=None, callback_query=None):
        self.message = message
        self.callback_query = callback_query
        self.effective_user = message.from_user if message else (callback_query.from_user if callback_query else None)


class MockContext:
    def __init__(self):
        self.user_data = {}
        self.bot = self

    async def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        pass


@pytest.fixture()
def db_temp(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr(config, "DB_PATH", os.path.join(tmpdir, "test_bp.db"))

    importlib.reload(db)
    db.init_db()
    c_id = db.create_country(888999, "ایران", "🇮🇷", country_key="iran")
    return db, c_id


def test_battle_pass_creation_and_xp_level_up(db_temp):
    db_mod, c_id = db_temp

    # ۱. ایجاد و دریافت بتل‌پس پیش‌فرض
    bp = db_mod.get_or_create_battle_pass(c_id)
    assert bp["current_tier"] == 1
    assert bp["current_xp"] == 0
    assert bp["is_premium"] == 0

    # ۲. کسب ۸۰۰ XP -> هنوز لول ۱ است
    new_xp, new_tier, tier_up = db_mod.add_battle_pass_xp(c_id, 800)
    assert new_xp == 800
    assert new_tier == 1
    assert not tier_up

    # ۳. کسب ۴۰۰ XP دیگر -> مجموع ۱۲۰۰ XP -> لول ۲ (Tier 2) باز می‌شود
    new_xp, new_tier, tier_up = db_mod.add_battle_pass_xp(c_id, 400)
    assert new_xp == 1200
    assert new_tier == 2
    assert tier_up is True


def test_battle_pass_claiming_free_and_premium_rewards(db_temp):
    db_mod, c_id = db_temp

    # رساندن لول به Tier 3
    db_mod.add_battle_pass_xp(c_id, 2500)
    bp = db_mod.get_or_create_battle_pass(c_id)
    assert bp["current_tier"] == 3

    # دریافت جوایز ردیف رایگان برای پله‌های ۱، ۲ و ۳
    c_before = db_mod.get_country_by_id(c_id)
    tr_before = c_before["treasury"]

    ok, msg, totals = db_mod.claim_all_unlocked_battle_pass_rewards(c_id)
    assert ok is True
    assert totals["free_count"] == 3
    assert totals["premium_count"] == 0

    c_after = db_mod.get_country_by_id(c_id)
    # Tier 1 free: 500k, Tier 3 free: 500k -> +1M treasury total
    assert c_after["treasury"] == tr_before + 1_000_000

    # تلاش مجدد برای دریافت وقتی همه دریافت شده‌اند
    ok_again, msg_again, _ = db_mod.claim_all_unlocked_battle_pass_rewards(c_id)
    assert not ok_again
    assert "قبلاً تمام پاداش‌ها" in msg_again

    # فعال‌سازی ردیف پرمیوم (۳۰۰ هزار تومانی)
    ok_prem, msg_prem = db_mod.unlock_premium_battle_pass(c_id)
    assert ok_prem is True

    # اکنون جوایز ردیف پرمیوم پله‌های ۱، ۲ و ۳ قابل دریافت هستند
    ok_claim_prem, msg_cp, totals_prem = db_mod.claim_all_unlocked_battle_pass_rewards(c_id)
    assert ok_claim_prem is True
    assert totals_prem["premium_count"] == 3

    c_final = db_mod.get_country_by_id(c_id)
    # Tier 1 premium: 2M, Tier 3 premium: 2.5M -> +4.5M more
    assert c_final["treasury"] == c_after["treasury"] + 4_500_000
    # Oil gained: Tier 1 premium (500k) + Tier 3 premium (500k) -> +1M bbl oil
    assert c_final["oil_reserves"] >= 1_000_000


def test_battle_pass_challenges_progression(db_temp):
    db_mod, c_id = db_temp

    # چالش ثبت ۳ بیانیه (c_stmt_3 -> +400 XP)
    # ثبت بیانیه اول و دوم
    db_mod.progress_battle_pass_challenge(c_id, "statement", 1)
    db_mod.progress_battle_pass_challenge(c_id, "statement", 1)
    bp = db_mod.get_or_create_battle_pass(c_id)
    assert bp["current_xp"] == 0

    # ثبت بیانیه سوم -> چالش تکمیل شده و ۴۰۰ XP اهدا می‌شود
    ok, xp_earned, title = db_mod.progress_battle_pass_challenge(c_id, "statement", 1)
    assert ok is True
    assert xp_earned == 400
    assert "حاکمیت" in title

    bp_after = db_mod.get_or_create_battle_pass(c_id)
    assert bp_after["current_xp"] == 400


def test_battle_pass_readiness_and_export_challenge_sync(db_temp):
    """تست اعطای اتوماتیک XP برای آمادگی رزمی بالای ۸۵٪ و صادرات نفت در بورس."""
    db_mod, c_id = db_temp

    # ۱. افزایش آمادگی رزمی به ۹۶٪
    db_mod.update_country_field(c_id, "combat_readiness", 96)

    # همگام‌سازی چالش‌ها -> باید چالش آمادگی (c_drill_90) فوراً تکمیل و ۴۰۰ XP اهدا شود
    xp_gained, titles = db_mod.sync_and_check_all_challenges(c_id)
    assert xp_gained == 400
    assert "رژه اقتدار" in titles[0]

    bp = db_mod.get_or_create_battle_pass(c_id)
    assert bp["current_xp"] == 400
    assert "c_drill_90" in bp["completed_challenges"]

    # ۲. ثبت عرضه و صادرات ۵۰ هزار بشکه نفت
    db_mod.adjust_oil(c_id, 100_000)
    ok_sell, msg_sell = db_mod.create_market_order(c_id, "oil", 50_000, 10)
    assert ok_sell is True

    # پیشرفت چالش صادرات نفت (تجمعی: تناژ واقعی ثبت می‌شود)
    ok_exp, xp_exp, exp_title = db_mod.progress_battle_pass_challenge(c_id, "export", 50_000)
    assert ok_exp is True
    assert xp_exp == 600
    assert "صادرات انرژی" in exp_title

    bp2 = db_mod.get_or_create_battle_pass(c_id)
    assert bp2["current_xp"] == 1000  # 400 + 600 = 1000 -> Level Up to Tier 2!
    assert bp2["current_tier"] == 2


def test_export_challenge_accumulates_across_small_sales(db_temp):
    """چالش صادرات باید مجموع فروش‌های کوچک را بشمارد، نه فقط معاملات بزرگ.

    باگ گزارش‌شده: بازیکنی سه محموله نفت (۲۴٬۳۰۰ + ۲۱٬۸۷۰ + ۱۹٬۶۸۳ = ۶۵٬۸۵۳ بشکه)
    در بورس فروخت، اما چون هیچ‌کدام به‌تنهایی به ۵۰٬۰۰۰ نمی‌رسید، چالش روی «۰ از ۱» ماند.
    """
    db_mod, c_id = db_temp

    shipments = [24_300, 21_870, 19_683]

    # دو محموله‌ی اول نباید چالش را تکمیل کنند (مجموع ۴۶٬۱۷۰ < ۵۰٬۰۰۰)
    for qty in shipments[:2]:
        done, xp, _ = db_mod.progress_battle_pass_challenge(c_id, "export", qty)
        assert done is False
        assert xp == 0

    bp_mid = db_mod.get_or_create_battle_pass(c_id)
    assert bp_mid["challenge_progress"]["c_export_50k"] == 46_170
    assert "c_export_50k" not in bp_mid["completed_challenges"]

    # محموله‌ی سوم از آستانه عبور می‌کند -> چالش تکمیل و ۶۰۰ XP اهدا می‌شود
    done, xp, title = db_mod.progress_battle_pass_challenge(c_id, "export", shipments[2])
    assert done is True
    assert xp == 600
    assert "صادرات انرژی" in title

    bp_end = db_mod.get_or_create_battle_pass(c_id)
    assert bp_end["challenge_progress"]["c_export_50k"] == 65_853
    assert "c_export_50k" in bp_end["completed_challenges"]

    # صادرات بیشتر نباید XP تکراری بدهد
    done_again, xp_again, _ = db_mod.progress_battle_pass_challenge(c_id, "export", 80_000)
    assert done_again is False
    assert xp_again == 0


def test_battle_pass_300k_payment_approval_workflow(db_temp):
    db_mod, c_id = db_temp
    player_id = 888999

    # ثبت فیش خرید بتل‌پس ۳۰۰ هزار تومانی
    req_id = db_mod.create_payment_request(
        player_id=player_id,
        country_id=c_id,
        item_type="battle_pass",
        plan_title="⭐️ بتل‌پس فصلی استراتژیک (Season 1 Pass)",
        amount_toman=300_000,
        receipt_photo_id="receipt_photo_bp_101",
        tracking_code="TRX-BP-300K"
    )

    # تایید فیش توسط ادمین
    ok, msg, p = db_mod.approve_payment_request(req_id, admin_id=8052987465)
    assert ok is True

    # بتل‌پس پرمیوم باید برای کشور فعال شده باشد
    bp = db_mod.get_or_create_battle_pass(c_id)
    assert bp["is_premium"] == 1
    assert bp["current_xp"] >= 500  # دارای بانس آغازین


def test_battle_pass_ui_navigation_and_views(db_temp):
    async def _test():
        db_mod, c_id = db_temp
        query = MockQuery(from_user_id=888999)
        context = MockContext()

        # ۱. باز کردن منوی اصلی بتل‌پس
        upd = MockUpdate(callback_query=query)
        await battlepass_callback_handler(upd, context)
        assert "بتل‌پس استراتژیک" in query.last_text
        assert "Tier 1 / 20" in query.last_text

        # ۲. مشاهده جدول پله‌ها
        query_tiers = MockQuery(from_user_id=888999)
        upd_tiers = MockUpdate(callback_query=query_tiers)
        query_tiers.data = "bp:view_tiers:1"
        await battlepass_callback_handler(upd_tiers, context)
        assert "جدول سطوح و جوایز بتل‌پس" in query_tiers.last_text
        assert "پله ۱" in query_tiers.last_text

        # ۳. مشاهده چالش‌های هفتگی
        query_ch = MockQuery(from_user_id=888999)
        upd_ch = MockUpdate(callback_query=query_ch)
        query_ch.data = "bp:challenges"
        await battlepass_callback_handler(upd_ch, context)
        assert "چالش‌های ویژه کسب XP" in query_ch.last_text

        # ۴. صفحه خرید ۳۰۰ هزار تومانی
        query_buy = MockQuery(from_user_id=888999)
        upd_buy = MockUpdate(callback_query=query_buy)
        query_buy.data = "bp:buy_pass"
        await battlepass_callback_handler(upd_buy, context)
        assert "۳۰۰٬۰۰۰" in query_buy.last_text  # قیمت پایه با جداکننده‌ی فارسی
        assert "مبلغ قابل پرداخت" in query_buy.last_text
        assert "۵۸۹۲-۱۰۱۴-۶۷۲۲-۷۲۲۵" in query_buy.last_text

    asyncio.run(_test())
