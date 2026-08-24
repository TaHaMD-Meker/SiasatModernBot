# -*- coding: utf-8 -*-
"""
تست‌های سیستم خدمات ویژه ۴ سطحی، اشتراک‌های تومانی و تخفیف نگهداری ارتش (VIP 4-Tier System).
"""

import os
import sys
import json
import tempfile
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402
import database as db  # noqa: E402


@pytest.fixture()
def db_temp(monkeypatch):
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr(config, "DB_PATH", os.path.join(tmpdir, "test.db"))

    import importlib
    importlib.reload(db)
    db.init_db()
    return db


def test_4tier_vip_approval_and_maintenance_discounts(db_temp):
    cid = db_temp.create_country(555, "ایران", "🇮🇷", country_key="iran")
    
    # اضافه کردن تسلیحات نمونه جهت محاسبه هزینه نگهداری
    conn = db_temp.get_connection()
    conn.execute("INSERT INTO country_assets (country_id, country_key, category, equipment_name, equipment_key, amount, maintenance_cost) VALUES (?, 'iran', 'Aircraft', 'F-14', 'f14', 100, 10000)", (cid,))
    conn.commit()
    conn.close()

    # هزینه نگهداری در حالت عادی (بدون VIP)
    maint_normal = db_temp.calculate_country_maintenance_cost(cid)
    assert maint_normal["vip_discount_pct"] == 0

    # ۱. خرید و تایید پلن برنز (۷۹ تومن -> ۵٪ تخفیف)
    req_b = db_temp.create_payment_request(555, cid, "vip_bronze", "🥉 اشتراک برنز", 79_000, tracking_code="TRX-B")
    ok, _, _ = db_temp.approve_payment_request(req_b, admin_id=8052987465)
    assert ok
    maint_bronze = db_temp.calculate_country_maintenance_cost(cid)
    assert maint_bronze["vip_discount_pct"] == 5
    assert maint_bronze["total_maint"] < maint_normal["total_maint"]

    # ۲. خرید و تایید پلن نقره (۱۷۹ تومن -> ۱۰٪ تخفیف)
    req_s = db_temp.create_payment_request(555, cid, "vip_silver", "🥈 اشتراک نقره", 179_000, tracking_code="TRX-S")
    db_temp.approve_payment_request(req_s, admin_id=8052987465)
    maint_silver = db_temp.calculate_country_maintenance_cost(cid)
    assert maint_silver["vip_discount_pct"] == 10

    # ۳. خرید و تایید پلن طلا (۳۴۹ تومن -> ۱۵٪ تخفیف)
    req_g = db_temp.create_payment_request(555, cid, "vip_gold", "🥇 اشتراک طلا", 349_000, tracking_code="TRX-G")
    db_temp.approve_payment_request(req_g, admin_id=8052987465)
    maint_gold = db_temp.calculate_country_maintenance_cost(cid)
    assert maint_gold["vip_discount_pct"] == 15

    # ۴. خرید و تایید پلن الماس (۶۵۰ تومن -> ۲۵٪ تخفیف)
    req_d = db_temp.create_payment_request(555, cid, "vip_diamond", "💎 اشتراک الماس", 650_000, tracking_code="TRX-D")
    db_temp.approve_payment_request(req_d, admin_id=8052987465)
    maint_diamond = db_temp.calculate_country_maintenance_cost(cid)
    assert maint_diamond["vip_discount_pct"] == 25
    assert maint_diamond["total_maint"] < maint_gold["total_maint"]


def test_predefined_faction_creation_with_40_assets(db_temp):
    """تست انتخاب گروه آماده واگنر و دریافت کاتالوگ واقعی ۴۰ عددی."""
    player_id = 998877

    payload = {
        "faction_key": "wagner",
        "name": "واگنر",
        "flag": "💀",
        "hq": "منطقه باخموت",
        "doctrine": "شرکت نظامی خصوصی (PMC)"
    }

    req_id = db_temp.create_payment_request(
        player_id=player_id,
        country_id=None,
        item_type="militia",
        plan_title="🏴‍☠️ هدایت واگنر",
        amount_toman=100_000,
        tracking_code="TRX-WAGNER-101",
        custom_payload=json.dumps(payload, ensure_ascii=False)
    )

    ok, msg, p = db_temp.approve_payment_request(req_id, admin_id=8052987465)
    assert ok

    new_faction = db_temp.get_country_by_player(player_id)
    assert new_faction is not None
    assert new_faction["name"] == "واگنر"
    assert new_faction["flag"] == "💀"

    # بررسی دارایی‌های اختصاصی واگنر (+40 قلم)
    assets = db_temp.get_country_assets(new_faction["id"])
    assert len(assets) >= 40
    asset_names = [a["equipment_name"] for a in assets]
    assert any("T-90M" in name for name in asset_names)
    assert any("Lancet" in name for name in asset_names)


def test_custom_militia_admin_renaming_approval(db_temp):
    """تست تغییر نام گروه سفارشی توسط ادمین در لحظه تایید."""
    player_id = 333444

    payload = {
        "name": "گنگ خفن محله",
        "flag": "⚔️",
        "hq": "شمال حلب",
        "doctrine": "جنگ چریکی"
    }

    req_id = db_temp.create_payment_request(
        player_id=player_id,
        country_id=None,
        item_type="militia",
        plan_title="🏴‍☠️ مجوز گروه سفارشی",
        amount_toman=100_000,
        tracking_code="TRX-CUSTOM-101",
        custom_payload=json.dumps(payload, ensure_ascii=False)
    )

    # ادمین اسم را به نام رسمی و شیک تغییر داده و تایید می‌کند
    refined_name = "تیپ ذوالفقار مقاومت"
    ok, msg, p = db_temp.approve_payment_request(req_id, admin_id=8052987465, override_name=refined_name)
    assert ok

    created = db_temp.get_country_by_player(player_id)
    assert created["name"] == "تیپ ذوالفقار مقاومت"
    assert created["flag"] == "⚔️"


def test_user_receipt_submission_flow_and_admin_notification(db_temp, monkeypatch):
    """تست ارسال فیش واریزی توسط کاربر و دریافت پیام توسط ادمین به همراه دکمه‌های تایید/رد."""
    import asyncio
    from handlers.vip import vip_input_handler

    async def _test():
        cid = db_temp.create_country(777888, "ایران", "🇮🇷", country_key="iran")

        sent_messages = []

        class MockBot:
            async def send_photo(self, chat_id, photo, caption, reply_markup=None, parse_mode=None):
                sent_messages.append({"type": "photo", "chat_id": chat_id, "photo": photo, "caption": caption, "reply_markup": reply_markup})

            async def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
                sent_messages.append({"type": "text", "chat_id": chat_id, "text": text, "reply_markup": reply_markup})

        class MockPhotoSize:
            def __init__(self, file_id):
                self.file_id = file_id

        class MockMsg:
            def __init__(self, photo=None, caption=None, text=None):
                self.photo = photo
                self.caption = caption
                self.text = text
                self.replies = []

            async def reply_text(self, text, reply_markup=None, parse_mode=None):
                self.replies.append({"text": text, "reply_markup": reply_markup, "parse_mode": parse_mode})

        class MockUser:
            def __init__(self):
                self.id = 777888
                self.full_name = "کاربر تستی"
                self.username = "test_player"

        class MockCtx:
            def __init__(self):
                self.user_data = {"vip_input": {"plan_key": "vip_diamond"}}
                self.bot = MockBot()

        class MockUpd:
            def __init__(self, msg, user):
                self.message = msg
                self.effective_user = user

        # ۱. ارسال فیش تصویری
        msg = MockMsg(photo=[MockPhotoSize("photo_file_12345")], caption="کد رهگیری: 99887766")
        user = MockUser()
        ctx = MockCtx()
        upd = MockUpd(msg, user)

        handled = await vip_input_handler(upd, ctx)
        assert handled is True

        # کاربر پیام تایید ثبت فیش را دریافت می‌کند
        assert len(msg.replies) == 1
        assert "فیش واریزی شما با موفقیت ثبت شد" in msg.replies[0]["text"]

        # ادمین عکس فیش و پیام اعلان را دریافت می‌کند
        assert len(sent_messages) == len(config.ADMIN_IDS)
        admin_alert = sent_messages[0]
        assert admin_alert["type"] == "photo"
        assert admin_alert["photo"] == "photo_file_12345"
        assert "درخواست جدید پرداخت تومانی" in admin_alert["caption"]
        assert "کاربر تستی" in admin_alert["caption"]
        assert "99887766" in admin_alert["caption"]
        assert "💎" in admin_alert["caption"] or "الماس" in admin_alert["caption"]

        # دکمه‌های تایید و رد همراه پیام ادمین است
        kb = admin_alert["reply_markup"]
        assert kb is not None
        callbacks = [btn.callback_data for row in kb.inline_keyboard for btn in row]
        assert any(cb.startswith("admin:pay_app:") for cb in callbacks)
        assert any(cb.startswith("admin:pay_rej:") for cb in callbacks)

    asyncio.run(_test())


def test_admin_receipt_viewing_and_callback_navigation(db_temp):
    """تست باز کردن و مشاهده فیش در پنل ادمین و سوییچ بین لیست و پرونده فیش."""
    import asyncio
    from handlers.admin import admin_callback_handler

    async def _test():
        cid = db_temp.create_country(999888, "روسیه", "🇷🇺", country_key="russia")
        req_id = db_temp.create_payment_request(
            player_id=999888,
            country_id=cid,
            item_type="vip_gold",
            plan_title="🥇 اشتراک طلایی رهبری",
            amount_toman=349_000,
            receipt_photo_id="test_receipt_file_999",
            tracking_code="TRX-VIEW-TEST-77"
        )

        class MockUser:
            id = 8052987465

        class MockMessage:
            def __init__(self, photo=None):
                self.photo = photo
                self.last_text = ""
                self.last_caption = ""
                self.last_reply_markup = None
                self.deleted = False

            async def reply_photo(self, photo, caption=None, reply_markup=None, parse_mode=None):
                self.photo = photo
                self.last_caption = caption
                self.last_reply_markup = reply_markup

            async def reply_text(self, text, reply_markup=None, parse_mode=None):
                self.last_text = text
                self.last_reply_markup = reply_markup

        class MockCallbackQuery:
            def __init__(self, data, msg=None):
                self.data = data
                self.from_user = MockUser()
                self.message = msg or MockMessage()
                self.answered = False

            async def answer(self, text=None, show_alert=False):
                self.answered = True

            async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
                self.message.last_text = text
                self.message.last_reply_markup = reply_markup

            async def edit_message_caption(self, caption, reply_markup=None, parse_mode=None):
                self.message.last_caption = caption
                self.message.last_reply_markup = reply_markup

            async def delete_message(self):
                self.message.deleted = True

        class MockBot:
            async def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
                pass

        class MockContext:
            user_data = {}
            bot = MockBot()

        class MockUpdate:
            def __init__(self, query):
                self.callback_query = query
                self.effective_user = query.from_user

        # ۱. باز کردن لیست فیش‌های تومانی در پنل ادمین
        q_list = MockCallbackQuery("admin:toman_requests")
        upd_list = MockUpdate(q_list)
        ctx = MockContext()
        await admin_callback_handler(upd_list, ctx)
        assert "لیست فیش‌های واریزی" in q_list.message.last_text
        assert f"admin:view_pay:{req_id}" in [btn.callback_data for row in q_list.message.last_reply_markup.inline_keyboard for btn in row]

        # ۲. کلیک روی فیش برای مشاهده پرونده و عکس آن
        q_view = MockCallbackQuery(f"admin:view_pay:{req_id}", msg=q_list.message)
        upd_view = MockUpdate(q_view)
        await admin_callback_handler(upd_view, ctx)
        assert "پرونده پرداخت تومانی" in (q_view.message.last_caption or q_view.message.last_text)
        assert "TRX-VIEW-TEST-77" in (q_view.message.last_caption or q_view.message.last_text)

        # ۳. کلیک تایید فیش
        q_app = MockCallbackQuery(f"admin:pay_app:{req_id}", msg=q_view.message)
        upd_app = MockUpdate(q_app)
        await admin_callback_handler(upd_app, ctx)
        assert ("تایید" in q_app.message.last_text) or ("تایید" in q_app.message.last_caption)

        # بررسی اعمال اشتراک روی کشور
        c = db_temp.get_country_by_id(cid)
        assert c["is_vip"] == 1
        assert c["vip_tier"] == "gold"

    asyncio.run(_test())


def test_dual_state_and_militia_switching(db_temp):
    """تست فرماندهی همزمان دولت رسمی و گروه نیابتی و سوییچ حساب."""
    player_id = 666777

    # ۱. بازیکن ابتدا کشور رسمی ایران را دارد
    state_id = db_temp.create_country(player_id, "ایران", "🇮🇷", country_key="iran")
    assert db_temp.get_country_by_player(player_id)["id"] == state_id

    # ۲. بازیکن گروه نیابتی نیروی قدس را با ۱۰۰ هزار تومان ثبت می‌کند
    militia_id = db_temp.create_custom_militia_faction(
        player_id=player_id,
        name="سپاه قدس",
        flag="🟢",
        hq_desc="پایگاه‌های برون‌مرزی",
        doctrine="جنگ نامتقارن و موشکی",
        faction_key="irgc_quds"
    )

    # ۳. هر دو نهاد همزمان در دیتابیس بدون حذف کشور اصلی وجود دارند
    all_entities = db_temp.get_player_all_entities(player_id)
    assert len(all_entities) == 2
    ids = [e["id"] for e in all_entities]
    assert state_id in ids
    assert militia_id in ids

    # ۴. پیش‌فرض روی دولت رسمی است
    curr = db_temp.get_country_by_player(player_id)
    assert curr["id"] == state_id

    # ۵. سوییچ به بازوی نیابتی
    ok, msg, target = db_temp.switch_player_active_entity(player_id)
    assert ok is True
    assert target["id"] == militia_id
    assert db_temp.get_country_by_player(player_id)["id"] == militia_id
    assert db_temp.get_country_by_player(player_id)["name"] == "سپاه قدس"

    # ۶. سوییچ مجدد به دولت رسمی
    ok2, msg2, target2 = db_temp.switch_player_active_entity(player_id)
    assert ok2 is True
    assert target2["id"] == state_id
    assert db_temp.get_country_by_player(player_id)["id"] == state_id
    assert db_temp.get_country_by_player(player_id)["name"] == "ایران"
