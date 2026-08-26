"""Regression tests for transaction validation and callback-safe invariants."""

import asyncio

import config
import database as db
import news_engine


class FakeBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, **kwargs):
        self.messages.append(kwargs)


def _fresh_db(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "integrity.db"))
    db.init_db()
    return db


def test_shop_transactions_reject_negative_quantity_and_forged_price(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    country_id = database.create_country(7001, "کشور تست", "🏳️", country_key="iran")
    before = database.get_country_by_id(country_id)
    asset = next(a for a in database.get_country_assets(country_id) if a["producible"] == 1)

    ok_asset, _msg_asset, _ = database.buy_country_asset_transaction(country_id, asset["equipment_key"], -1)
    assert not ok_asset

    ok_civil, _msg_civil = database.buy_item_transaction(
        country_id, "wheat_farm", -1, -3_000_000, "مزرعه"
    )
    assert not ok_civil

    ok_price, _msg_price = database.buy_item_transaction(
        country_id, "wheat_farm", 1, 0, "مزرعه"
    )
    assert not ok_price

    after = database.get_country_by_id(country_id)
    assert after["treasury"] == before["treasury"]
    assert database.get_asset_by_key(country_id, asset["equipment_key"])["amount"] == asset["amount"]


def test_foreign_aid_rejects_negative_and_unknown_inputs(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    donor_id = database.create_country(7002, "اهداکننده", "🏳️", country_key="usa")
    recipient_id = database.create_country(7003, "دریافت‌کننده", "🏳️", country_key="uk")
    before_donor = database.get_country_by_id(donor_id)
    before_recipient = database.get_country_by_id(recipient_id)

    for resource_type, mode in (("oil", "land"), ("not_a_resource", "land"), ("oil", "teleport")):
        ok, _msg = database.execute_foreign_aid_transaction(
            donor_id, recipient_id, resource_type, -100, transport_mode=mode
        )
        assert not ok

    ok_invalid_resource, _ = database.execute_foreign_aid_transaction(
        donor_id, recipient_id, "not_a_resource", 100, transport_mode="land"
    )
    ok_invalid_mode, _ = database.execute_foreign_aid_transaction(
        donor_id, recipient_id, "oil", 100, transport_mode="teleport"
    )
    ok_self, _ = database.execute_foreign_aid_transaction(
        donor_id, donor_id, "oil", 100, transport_mode="land"
    )
    assert not ok_invalid_resource
    assert not ok_invalid_mode
    assert not ok_self

    assert database.get_country_by_id(donor_id)["treasury"] == before_donor["treasury"]
    assert database.get_country_by_id(recipient_id)["treasury"] == before_recipient["treasury"]


def test_market_rejects_unknown_transport_mode(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    seller_id = database.create_country(7004, "فروشنده", "🏳️", country_key="usa")
    buyer_id = database.create_country(7005, "خریدار", "🏳️", country_key="uk")
    database.update_country_field(seller_id, "gold", 100)

    ok_order, _ = database.create_market_order(seller_id, "gold", 10, 100)
    assert ok_order
    order = database.get_country_market_orders(seller_id)[0]
    ok_buy, _msg, _meta = database.execute_market_buy_transaction(
        buyer_id, order["id"], 1, transport_mode="teleport"
    )
    assert not ok_buy
    assert database.get_market_order_by_id(order["id"]) is not None


def test_trade_accept_and_reject_are_recipient_only_and_one_shot(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    proposer_id = database.create_country(7006, "پیشنهاددهنده", "🏳️", country_key="usa")
    recipient_id = database.create_country(7007, "دریافت‌کننده", "🏳️", country_key="uk")

    contract_id = database.create_trade_contract(
        proposer_id,
        recipient_id,
        "gold",
        1,
        "treasury",
        1_000,
        transport_payer="seller",
        transport_cost=0,
        transport_mode="land",
    )
    ok_reject, _ = database.reject_trade_contract(contract_id, proposer_id)
    assert not ok_reject
    ok_accept, _ = database.execute_trade_contract_transaction(
        contract_id, actor_country_id=proposer_id
    )
    assert not ok_accept
    assert database.get_trade_contract(contract_id)["status"] == "pending"

    ok_reject, _ = database.reject_trade_contract(contract_id, recipient_id)
    assert ok_reject
    assert database.get_trade_contract(contract_id)["status"] == "rejected"
    ok_reject_again, _ = database.reject_trade_contract(contract_id, recipient_id)
    assert not ok_reject_again

    accepted_id = database.create_trade_contract(
        proposer_id,
        recipient_id,
        "gold",
        1,
        "treasury",
        0,
        transport_payer="seller",
        transport_cost=0,
        transport_mode="land",
    )
    ok_accept, _ = database.execute_trade_contract_transaction(
        accepted_id, actor_country_id=recipient_id
    )
    assert ok_accept
    ok_reject_after_accept, _ = database.reject_trade_contract(accepted_id, recipient_id)
    assert not ok_reject_after_accept
    assert database.get_trade_contract(accepted_id)["status"] == "accepted"


def test_intel_operation_rejects_self_target_and_forged_chip_boost(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    country_a = database.create_country(7008, "مهاجم", "🏳️", country_key="usa")
    country_b = database.create_country(7009, "هدف", "🏳️", country_key="uk")

    ok_self, _msg, _meta = database.execute_intel_operation(
        country_a, country_a, "espionage_military", chips_boost=0
    )
    ok_negative, _msg, _meta = database.execute_intel_operation(
        country_a, country_b, "espionage_military", chips_boost=-5
    )
    ok_arbitrary, _msg, _meta = database.execute_intel_operation(
        country_a, country_b, "espionage_military", chips_boost=4
    )
    assert not ok_self
    assert not ok_negative
    assert not ok_arbitrary


def test_un_vote_and_resolution_status_are_validated(monkeypatch, tmp_path):
    database = _fresh_db(monkeypatch, tmp_path)
    country_id = database.create_country(7010, "کشور رای‌دهنده", "🏳️", country_key="usa")
    resolution_id = database.create_un_resolution("عنوان", "شرح", 1)

    ok_vote, _ = database.cast_un_vote(resolution_id, country_id, "invalid")
    assert not ok_vote
    assert database.close_un_resolution(resolution_id, "invalid") is False
    assert database.close_un_resolution(resolution_id, "passed") is True
    assert database.close_un_resolution(resolution_id, "vetoed") is False


def test_breaking_news_accepts_legacy_and_current_call_styles(monkeypatch):
    bot = FakeBot()
    monkeypatch.setattr(news_engine.config, "get_channel_id", lambda: "@test_channel")

    async def run():
        current = await news_engine.post_breaking_news(bot, "عنوان جدید", "متن خبر", "امنیت")
        legacy = await news_engine.post_breaking_news(
            bot, news_title="عنوان قدیمی", news_body="متن قدیمی", event_category="دیپلماسی"
        )
        return current, legacy

    current, legacy = asyncio.run(run())
    assert current and legacy
    assert len(bot.messages) == 2
    assert "امنیت" in bot.messages[0]["text"]
    assert "عنوان قدیمی" in bot.messages[1]["text"]
