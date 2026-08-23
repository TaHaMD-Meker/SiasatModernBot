# -*- coding: utf-8 -*-
"""
Unit tests for the Comprehensive Admin Dossier & Deep Inspection System in SiasatModernBot.
"""

import os
import sys
import tempfile
import importlib
import pytest
import asyncio
import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config
import database as db
from handlers.admin_dossier import (
    show_country_dashboard,
    show_country_trades_menu,
    show_country_trade_detail,
    show_country_bases_menu,
    show_country_nuclear_menu,
    show_country_military_menu,
    show_country_economy_menu,
    show_country_diplomacy_menu,
    show_country_intel_menu,
    show_country_losses_menu,
    show_country_statements_menu,
    show_country_vip_finance_menu,
    show_country_godmode_menu,
    handle_dossier_callbacks,
    handle_dossier_inputs
)


class MockQuery:
    def __init__(self, from_user_id=123456):
        self.from_user = type("User", (), {"id": from_user_id})()
        self.last_text = ""
        self.last_reply_markup = None
        self.last_parse_mode = None
        self.answered = False
        self.alert_text = None

    async def answer(self, text=None, show_alert=False):
        self.answered = True
        self.alert_text = text

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
    monkeypatch.setattr(config, "DB_PATH", os.path.join(tmpdir, "test_admin.db"))

    importlib.reload(db)
    db.init_db()
    c1_id = db.create_country(11111, "کشور الف", "🇮🇷", country_key="iran")
    c2_id = db.create_country(22222, "کشور ب", "🇷🇺", country_key="russia")
    return db, c1_id, c2_id


def test_admin_country_dashboard_view(db_temp):
    async def _test():
        db_mod, c1_id, c2_id = db_temp
        query = MockQuery()
        context = MockContext()

        await show_country_dashboard(query, context, c1_id)
        assert "پرونده جامع و مرکز کنترل کشور" in query.last_text
        assert "کشور الف" in query.last_text
        assert query.last_reply_markup is not None

        callbacks = [btn.callback_data for row in query.last_reply_markup.inline_keyboard for btn in row]
        assert f"admin:c_trades:{c1_id}:0" in callbacks
        assert f"admin:c_bases:{c1_id}" in callbacks
        assert f"admin:c_nuclear:{c1_id}" in callbacks
        assert f"admin:c_military:{c1_id}" in callbacks
        assert f"admin:c_economy:{c1_id}" in callbacks
        assert f"admin:c_diplomacy:{c1_id}" in callbacks
        assert f"admin:c_intel:{c1_id}" in callbacks
        assert f"admin:c_losses:{c1_id}:0" in callbacks
        assert f"admin:c_statements:{c1_id}" in callbacks
        assert f"admin:c_vip_finance:{c1_id}" in callbacks
        assert f"admin:c_godmode:{c1_id}" in callbacks
    asyncio.run(_test())


def test_admin_trade_contracts_inspection_and_actions(db_temp):
    async def _test():
        db_mod, c1_id, c2_id = db_temp
        query = MockQuery()
        context = MockContext()

        # Create a trade contract
        contract_id = db_mod.create_trade_contract(
            proposer_id=c1_id,
            recipient_id=c2_id,
            offered_type="oil",
            offered_amount=50000,
            requested_type="treasury",
            requested_amount=5000000,
            transport_payer="seller",
            transport_cost=300000,
            transport_mode="sea"
        )

        # Inspect trades list
        await show_country_trades_menu(query, context, c1_id, 0)
        assert f"قرارداد تجاری #{contract_id}" in query.last_text
        assert "بشکه" in query.last_text
        assert "دلار" in query.last_text

        # Inspect single trade detail
        await show_country_trade_detail(query, context, c1_id, contract_id)
        assert f"جزئیات کامل قرارداد تجاری #{contract_id}" in query.last_text
        assert "در انتظار تایید" in query.last_text

        # Test Admin Force Execute Contract
        db_mod.update_country_field(c1_id, "oil_reserves", 100000)
        db_mod.update_country_field(c2_id, "treasury", 20000000)
        db_mod.update_country_field(c1_id, "treasury", 10000000)

        handled = await handle_dossier_callbacks(query, context, f"admin:c_t_exec:{c1_id}:{contract_id}")
        assert handled is True
        t_after = db_mod.get_trade_contract(contract_id)
        assert t_after["status"] == "accepted"

        # Test Admin Cancel Contract
        handled = await handle_dossier_callbacks(query, context, f"admin:c_t_cancel:{c1_id}:{contract_id}")
        assert handled is True
        t_cancelled = db_mod.get_trade_contract(contract_id)
        assert t_cancelled["status"] == "canceled"

        # Test Admin Delete Contract
        handled = await handle_dossier_callbacks(query, context, f"admin:c_t_del:{c1_id}:{contract_id}")
        assert handled is True
        assert db_mod.get_trade_contract(contract_id) is None
    asyncio.run(_test())


def test_admin_market_orders_cancel_and_refund(db_temp):
    async def _test():
        db_mod, c1_id, _ = db_temp
        query = MockQuery()
        context = MockContext()

        # Set initial oil
        db_mod.update_country_field(c1_id, "oil_reserves", 500000)
        # Create market order
        ok, msg = db_mod.create_market_order(c1_id, "oil", 100000, 80)
        assert ok is True
        orders = db_mod.get_country_market_orders(c1_id)
        assert len(orders) == 1
        order_id = orders[0]["id"]
        c1_after_order = db_mod.get_country_by_id(c1_id)
        assert c1_after_order["oil_reserves"] == 400000

        # Inspect trades menu where market orders are displayed
        await show_country_trades_menu(query, context, c1_id, 0)
        assert f"#{order_id}" in query.last_text

        # Admin cancels market order -> should refund 100k oil back to c1
        handled = await handle_dossier_callbacks(query, context, f"admin:c_morder_cancel:{c1_id}:{order_id}")
        assert handled is True
        c1_refunded = db_mod.get_country_by_id(c1_id)
        assert c1_refunded["oil_reserves"] == 500000
    asyncio.run(_test())


def test_admin_nuclear_and_strategic_controls(db_temp):
    async def _test():
        db_mod, c1_id, _ = db_temp
        query = MockQuery()
        context = MockContext()

        # View nuclear menu
        await show_country_nuclear_menu(query, context, c1_id)
        assert "پرونده استراتژیک و چرخه سوخت هسته‌ای" in query.last_text

        # Set tier 3
        handled = await handle_dossier_callbacks(query, context, f"admin:c_nuc_tier:{c1_id}:3")
        assert handled is True
        c = db_mod.get_country_by_id(c1_id)
        assert c["enrichment_tier"] == 3

        # Toggle NPT withdrawn
        handled = await handle_dossier_callbacks(query, context, f"admin:c_nuc_npt:{c1_id}")
        assert handled is True
        c = db_mod.get_country_by_id(c1_id)
        assert c["npt_withdrawn"] == 1

        # Toggle UN Sanctions
        handled = await handle_dossier_callbacks(query, context, f"admin:c_nuc_sanction:{c1_id}")
        assert handled is True
        c = db_mod.get_country_by_id(c1_id)
        assert c["un_sanctioned"] == 1

        # Add warheads and confiscate
        db_mod.update_country_field(c1_id, "warheads", 10)
        handled = await handle_dossier_callbacks(query, context, f"admin:c_nuc_confiscate:{c1_id}")
        assert handled is True
        c = db_mod.get_country_by_id(c1_id)
        assert c["warheads"] == 0
    asyncio.run(_test())


def test_admin_commanders_and_military(db_temp):
    async def _test():
        db_mod, c1_id, _ = db_temp
        query = MockQuery()
        context = MockContext()

        # Seed commanders
        db_mod.seed_country_commanders(c1_id, "iran")
        commanders = db_mod.get_country_commanders(c1_id)
        assert len(commanders) >= 1
        first_cmd = commanders[0]

        # Inspect military menu
        await show_country_military_menu(query, context, c1_id)
        assert "پرونده تسلیحات، پدافند و فرماندهان" in query.last_text

        # Kill commander
        handled = await handle_dossier_callbacks(query, context, f"admin:c_cmd_kill:{c1_id}:{first_cmd['key']}")
        assert handled is True
        cmds = db_mod.get_country_commanders(c1_id)
        dead_cmd = next(cm for cm in cmds if cm["key"] == first_cmd["key"])
        assert dead_cmd["status"] in ("killed", "assassinated")

        # Revive commander
        handled = await handle_dossier_callbacks(query, context, f"admin:c_cmd_revive:{c1_id}:{first_cmd['key']}")
        assert handled is True
        cmds = db_mod.get_country_commanders(c1_id)
        alive_cmd = next(cm for cm in cmds if cm["key"] == first_cmd["key"])
        assert alive_cmd["status"] == "active"

        # Add new commander via input
        msg = MockMessage(text="ژنرال شهید سلیمانی")
        update = MockUpdate(message=msg)
        input_state = {"type": "add_commander_title", "country_id": c1_id}
        handled = await handle_dossier_inputs(update, context, "add_commander_title", msg.text, input_state)
        assert handled is True
        cmds = db_mod.get_country_commanders(c1_id)
        assert any(cm["title"] == "ژنرال شهید سلیمانی" for cm in cmds)
    asyncio.run(_test())


def test_admin_cyber_and_intel(db_temp):
    async def _test():
        db_mod, c1_id, _ = db_temp
        query = MockQuery()
        context = MockContext()

        # Set cyber disruptions
        future_iso = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5)).isoformat()
        db_mod.update_country_field(c1_id, "blackout_until", future_iso)
        db_mod.update_country_field(c1_id, "air_defense_disrupted_until", future_iso)

        # View intel menu
        await show_country_intel_menu(query, context, c1_id)
        assert "خاموشی تا" in query.last_text
        assert "پدافند هوایی: 🔴 مختل تا" in query.last_text

        # Clear cyber disruptions
        handled = await handle_dossier_callbacks(query, context, f"admin:c_clear_cyber:{c1_id}")
        assert handled is True
        c = db_mod.get_country_by_id(c1_id)
        assert c["blackout_until"] is None
        assert c["air_defense_disrupted_until"] is None
    asyncio.run(_test())


def test_admin_vip_and_godmode_transfer(db_temp):
    async def _test():
        db_mod, c1_id, _ = db_temp
        query = MockQuery()
        context = MockContext()

        # Set VIP Diamond
        handled = await handle_dossier_callbacks(query, context, f"admin:c_set_vip:{c1_id}:vip_diamond:30")
        assert handled is True
        c = db_mod.get_country_by_id(c1_id)
        assert c["is_vip"] == 1
        assert c["vip_tier"] == "diamond"

        # Revoke VIP
        handled = await handle_dossier_callbacks(query, context, f"admin:c_revoke_vip:{c1_id}")
        assert handled is True
        c = db_mod.get_country_by_id(c1_id)
        assert c["is_vip"] == 0

        # Economic & Military Boost
        handled = await handle_dossier_callbacks(query, context, f"admin:c_boost_econ:{c1_id}")
        assert handled is True
        c = db_mod.get_country_by_id(c1_id)
        assert c["treasury"] >= 100000000

        # Transfer Ownership
        msg = MockMessage(text="987654321 @new_leader")
        update = MockUpdate(message=msg)
        input_state = {"type": "transfer_player_id", "country_id": c1_id}
        handled = await handle_dossier_inputs(update, context, "transfer_player_id", msg.text, input_state)
        assert handled is True
        c = db_mod.get_country_by_id(c1_id)
        assert c["player_id"] == 987654321
        assert c["username"] == "new_leader"

        # Rename Country
        msg_rename = MockMessage(text="☀️ امپراتوری نوین")
        input_state_rename = {"type": "rename_country_name", "country_id": c1_id}
        handled = await handle_dossier_inputs(update, context, "rename_country_name", msg_rename.text, input_state_rename)
        assert handled is True
        c = db_mod.get_country_by_id(c1_id)
        assert "امپراتوری نوین" in c["name"]
    asyncio.run(_test())
