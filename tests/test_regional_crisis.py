# -*- coding: utf-8 -*-
"""بحران منطقه‌ای: یک بحران روی کل یک قاره.

خواسته‌ی کارفرما:
۱. ادمین بزند «اروپا» و همه‌ی کشورهای اروپایی درگیر شوند.
۲. کشوری که همان بحران را از قبل دارد، بحران دوم نگیرد؛ فقط یک سطح تشدید شود.
۳. برای هر منطقه یک خبر واحد منتشر شود («کل اروپا رسماً درگیر شد»)، نه یک خبر به‌ازای هر کشور.
"""

import asyncio
import inspect

import config
import database as db
import internal_affairs as ia
from handlers import internal_admin


def _fresh(monkeypatch, tmp_path, name="region.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()
    ia.set_enabled(True)
    ia.set_random_crises(False)


def _build_europe(count=5):
    keys = config.CONTINENTS["europe"]["keys"][:count]
    ids = {}
    for index, key in enumerate(keys):
        ids[key] = db.create_country(70_000 + index, f"کشور {key}", "🏳️", country_key=key)
    return ids


class FakeQuery:
    def __init__(self, user_id=1):
        self.text = ""
        self.markup = None
        self.alerts = []
        self.from_user = type("U", (), {"id": user_id})()

    async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
        self.text = text
        self.markup = reply_markup

    async def answer(self, text="", show_alert=False):
        self.alerts.append(text)


class FakeBot:
    def __init__(self):
        self.messages = []

    async def send_message(self, chat_id, text=None, parse_mode=None, **kwargs):
        self.messages.append({"chat_id": chat_id, "text": text})


class FakeContext:
    def __init__(self):
        self.bot = FakeBot()


# ─────────────────────────────────────────────────────────────────────────────
# موتور
# ─────────────────────────────────────────────────────────────────────────────

def test_regions_come_from_the_game_continent_table():
    keys = [key for key, _ in ia.region_choices()]
    assert "europe" in keys and "mideast" in keys
    assert ia.region_label("europe")


def test_a_regional_crisis_hits_every_country_in_the_region(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    ids = _build_europe(5)
    result = ia.create_regional_crisis("europe", "epidemic", severity="medium", admin_id=1)

    assert result["ok"]
    assert len(result["created"]) == 5
    for cid in ids.values():
        assert [c for c in ia.get_active_crises(cid) if c["crisis_key"] == "epidemic"]


def test_countries_outside_the_region_stay_clean(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "region_outside.db")
    _build_europe(3)
    iran = db.create_country(70_900, "ایران", "🇮🇷", country_key="iran")

    ia.create_regional_crisis("europe", "epidemic", severity="medium", admin_id=1)
    assert ia.get_active_crises(iran) == []


def test_an_existing_crisis_is_escalated_not_duplicated(monkeypatch, tmp_path):
    """قانون اصلی: بحران دوم ساخته نمی‌شود، فقط سطح بالا می‌رود."""
    _fresh(monkeypatch, tmp_path, "region_dup.db")
    ids = _build_europe(4)
    first = list(ids.values())[0]
    ok, _m, existing = ia.create_crisis(first, "epidemic", severity="light", origin="admin", force=True)
    assert ok

    result = ia.create_regional_crisis("europe", "epidemic", severity="medium", admin_id=1)

    active = [c for c in ia.get_active_crises(first) if c["crisis_key"] == "epidemic"]
    assert len(active) == 1, "کشور نباید دو بحران هم‌نوع بگیرد"
    assert active[0]["id"] == existing["id"]
    assert active[0]["severity"] == "medium", "سطحش باید یک پله بالا رفته باشد"
    assert len(result["escalated"]) == 1
    assert len(result["created"]) == 3


def test_a_country_already_at_the_top_level_is_left_alone(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "region_max.db")
    ids = _build_europe(3)
    first = list(ids.values())[0]
    ia.create_crisis(first, "epidemic", severity="severe", origin="admin", force=True)

    result = ia.create_regional_crisis("europe", "epidemic", severity="medium", admin_id=1)
    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["reason"] == "max"
    assert len([c for c in ia.get_active_crises(first) if c["crisis_key"] == "epidemic"]) == 1


def test_a_different_crisis_type_is_still_created(monkeypatch, tmp_path):
    """قحطی نباید به‌خاطر اپیدمیِ موجود رد شود."""
    _fresh(monkeypatch, tmp_path, "region_other.db")
    ids = _build_europe(3)
    first = list(ids.values())[0]
    ia.create_crisis(first, "epidemic", severity="light", origin="admin", force=True)

    ia.create_regional_crisis("europe", "famine", severity="light", admin_id=1)
    kinds = {c["crisis_key"] for c in ia.get_active_crises(first)}
    assert kinds == {"epidemic", "famine"}


def test_repeating_the_same_region_keeps_stepping_up_not_multiplying(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "region_twice.db")
    ids = _build_europe(3)
    ia.create_regional_crisis("europe", "epidemic", severity="light", admin_id=1)
    ia.create_regional_crisis("europe", "epidemic", severity="light", admin_id=1)

    for cid in ids.values():
        active = [c for c in ia.get_active_crises(cid) if c["crisis_key"] == "epidemic"]
        assert len(active) == 1
        assert active[0]["severity"] == "medium"


# ─────────────────────────────────────────────────────────────────────────────
# خبر
# ─────────────────────────────────────────────────────────────────────────────

def test_one_single_news_item_for_the_whole_region(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "region_news.db")
    _build_europe(6)
    result = ia.create_regional_crisis("europe", "epidemic", severity="medium", admin_id=1)
    news = ia.build_regional_news(result)

    assert news is not None
    title, body = news
    assert "سراسری" in title
    assert ia.region_label("europe").split()[-1] in title or "اروپا" in title
    assert "6 کشور" in body or "۶ کشور" in body or "6" in body


def test_regional_news_lists_new_and_worsened_countries(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "region_news2.db")
    ids = _build_europe(4)
    first = list(ids.values())[0]
    ia.create_crisis(first, "epidemic", severity="light", origin="admin", force=True)

    result = ia.create_regional_crisis("europe", "epidemic", severity="medium", admin_id=1)
    _title, body = ia.build_regional_news(result)
    assert "تازه درگیر" in body
    assert "بدتر شد" in body


def test_no_news_when_nothing_actually_changed(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "region_nonews.db")
    ids = _build_europe(2)
    for cid in ids.values():
        ia.create_crisis(cid, "epidemic", severity="severe", origin="admin", force=True)

    result = ia.create_regional_crisis("europe", "epidemic", severity="medium", admin_id=1)
    assert ia.build_regional_news(result) is None


# ─────────────────────────────────────────────────────────────────────────────
# پنل ادمین
# ─────────────────────────────────────────────────────────────────────────────

def test_admin_panel_has_the_regional_button():
    source = inspect.getsource(internal_admin)
    assert 'callback_data="admin:dom_region"' in source
    assert "بحران منطقه‌ای" in source


def test_region_picker_lists_every_region(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "region_ui.db")
    _build_europe(3)
    query = FakeQuery()
    asyncio.run(internal_admin._region_picker(query))
    callbacks = [b.callback_data for row in query.markup.inline_keyboard for b in row]
    assert "admin:dom_rgn:europe" in callbacks
    assert "admin:dom_rgn:mideast" in callbacks


def test_severity_page_shows_how_many_are_already_infected(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "region_ui2.db")
    ids = _build_europe(5)
    ia.create_crisis(list(ids.values())[0], "epidemic", severity="light", origin="admin", force=True)

    query = FakeQuery()
    asyncio.run(internal_admin._region_severity_picker(query, "europe", "epidemic"))
    assert "از قبل درگیر همین بحران" in query.text
    assert "<b>1</b>" in query.text


def test_applying_from_the_panel_notifies_each_player_once(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "region_apply.db")
    ids = _build_europe(4)
    query, context = FakeQuery(), FakeContext()

    asyncio.run(internal_admin._apply_region(query, context, "europe", "epidemic", "medium", False))

    assert "اعمال شد" in query.text
    to_players = [m for m in context.bot.messages if isinstance(m["chat_id"], int)]
    to_channel = [m for m in context.bot.messages if not isinstance(m["chat_id"], int)]
    assert len(to_players) == len(ids), "هر بازیکن دقیقاً یک اطلاع خصوصی می‌گیرد"
    assert len(to_channel) == 1, "برای کل منطقه فقط یک خبر باید برود"
    for cid in ids.values():
        assert len([c for c in ia.get_active_crises(cid) if c["crisis_key"] == "epidemic"]) == 1


def test_router_knows_the_regional_callbacks():
    source = inspect.getsource(internal_admin.internal_admin_callback)
    for key in ("admin:dom_region", "admin:dom_rgn:", "admin:dom_rtype:", "admin:dom_rgo:"):
        assert key in source


def test_news_body_never_carries_html_tags(monkeypatch, tmp_path):
    """کانال با Markdown ارسال می‌شود؛ هر تگ HTML عیناً به‌صورت متن دیده می‌شود."""
    _fresh(monkeypatch, tmp_path, "region_html.db")
    ids = _build_europe(5)
    ia.create_crisis(list(ids.values())[0], "epidemic", severity="light", origin="admin", force=True)

    result = ia.create_regional_crisis("europe", "epidemic", severity="medium", admin_id=1)
    title, body = ia.build_regional_news(result)
    for tag in ("<b>", "</b>", "<i>", "</i>", "<code>"):
        assert tag not in body and tag not in title


def test_crisis_digest_is_also_free_of_html(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "region_digest.db")
    ids = _build_europe(6)
    result = ia.create_regional_crisis("europe", "epidemic", severity="medium", admin_id=1)
    items = []
    for entry in result["created"]:
        items.append({
            "crisis_id": entry["crisis"]["id"], "country": entry["country"],
            "crisis": entry["crisis"], "event": "escalated", "flag": "x",
            "title": "t", "body": "b",
        })
    digest = ia.build_news_digest(items)
    assert digest is not None
    assert "<b>" not in digest[1]
