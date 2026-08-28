# -*- coding: utf-8 -*-
"""تست‌های رگرسیون سه ناهماهنگی UI:

1. صفحه‌بندی «کشورهای در معرض سقوط» و «تاریخچه بحران‌ها» در پنل ادمین
2. انعکاس چرخه‌ی داخلی در گزارش روزانه‌ی بازیکن
3. فصل ۹ دانشکده که با فصل ۱۰ همپوشانی داشت و عدد قدیمی می‌داد
"""

import asyncio
import datetime
import inspect

import approval_system
import config
import database as db
import internal_affairs as ia
from handlers import internal_admin


def _fresh_db(monkeypatch, tmp_path, name="ui.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()
    ia.set_enabled(True)
    ia.set_random_crises(False)
    return db


class FakeQuery:
    """کوچک‌ترین چیزی که صفحه‌های ادمین از query می‌خواهند."""

    def __init__(self):
        self.text = ""
        self.markup = None
        self.alerts = []

    async def edit_message_text(self, text, reply_markup=None, parse_mode=None):
        self.text = text
        self.markup = reply_markup

    async def answer(self, text="", show_alert=False):
        self.alerts.append(text)


def _buttons(markup):
    return [button for row in (markup.inline_keyboard if markup else []) for button in row]


def _callbacks(markup):
    return [b.callback_data for b in _buttons(markup)]


# ─────────────────────────────────────────────────────────────────────────────
# ۱. صفحه‌بندی
# ─────────────────────────────────────────────────────────────────────────────

def _many_countries_at_risk(count):
    ids = []
    for index in range(count):
        cid = db.create_country(90_000 + index, f"کشور {index}", "🏳️", country_key=f"risk_{index}")
        db.update_country_field(cid, "approval_rating", 5)
        state = ia.get_state(cid)
        assert state is not None
        conn = db.get_connection()
        with conn:
            conn.execute(
                "UPDATE country_internal SET unrest = 95, unrest_stage = 4, collapse_risk = 1, critical_days = 4 "
                "WHERE country_id = ?",
                (cid,),
            )
        conn.close()
        ids.append(cid)
    return ids


def test_risk_list_is_paginated_and_no_country_falls_off(monkeypatch, tmp_path):
    _fresh_db(monkeypatch, tmp_path, "risk.db")
    _many_countries_at_risk(20)

    seen = set()
    page = 0
    while True:
        query = FakeQuery()
        asyncio.run(internal_admin._risk_page(query, page))
        assert "مجموع: <b>20</b>" in query.text
        for index in range(20):
            if f"کشور {index}</b>" in query.text:
                seen.add(index)
        if f"admin:dom_risk:{page + 1}" not in _callbacks(query.markup):
            break
        page += 1
        assert page < 20, "حلقه‌ی بی‌پایان در صفحه‌بندی"

    assert seen == set(range(20)), "بعضی کشورهای در خطر در هیچ صفحه‌ای دیده نشدند"
    assert page >= 2, "با ۲۰ کشور باید بیش از یک صفحه داشته باشیم"


def test_risk_page_number_is_clamped(monkeypatch, tmp_path):
    _fresh_db(monkeypatch, tmp_path, "risk_clamp.db")
    _many_countries_at_risk(3)

    query = FakeQuery()
    asyncio.run(internal_admin._risk_page(query, 99))
    assert "کشور 0</b>" in query.text  # به آخرین صفحه‌ی موجود برگشت، نه صفحه‌ی خالی
    assert "1/1" in "".join(b.text for b in _buttons(query.markup))


def test_history_list_is_paginated(monkeypatch, tmp_path):
    _fresh_db(monkeypatch, tmp_path, "hist.db")
    cid = db.create_country(91_500, "کشور تاریخ", "🏳️", country_key="hist_land")
    for index in range(35):
        ia.create_crisis(cid, "epidemic", severity="light", origin="admin", force=True)
        # بلافاصله پایان می‌دهیم تا سقف بحران هم‌زمان اجازه‌ی بعدی را بدهد
        active = ia.get_active_crises(cid)
        for crisis in active:
            ia.end_crisis(crisis["id"])

    total = len(ia.get_crisis_history(limit=100))
    assert total >= 30

    ids_seen = set()
    page = 0
    while True:
        query = FakeQuery()
        asyncio.run(internal_admin._history_page(query, page))
        for line in query.text.splitlines():
            if line.startswith("• #"):
                ids_seen.add(line.split()[1])
        if f"admin:dom_hist:{page + 1}" not in _callbacks(query.markup):
            break
        page += 1
        assert page < 20

    assert page >= 1, "تاریخچه‌ی ۳۰+ موردی باید بیش از یک صفحه شود"
    assert len(ids_seen) == total


def test_router_accepts_both_bare_and_paged_callbacks():
    source = inspect.getsource(internal_admin.internal_admin_callback)
    assert 'data == "admin:dom_risk" or data.startswith("admin:dom_risk:")' in source
    assert 'data == "admin:dom_hist" or data.startswith("admin:dom_hist:")' in source
    assert internal_admin._parse_page("admin:dom_risk:4", "admin:dom_risk") == 4
    assert internal_admin._parse_page("admin:dom_risk", "admin:dom_risk") == 0
    assert internal_admin._parse_page("admin:dom_risk:xx", "admin:dom_risk") == 0
    assert internal_admin._parse_page("admin:dom_risk:-3", "admin:dom_risk") == 0


# ─────────────────────────────────────────────────────────────────────────────
# ۲. گزارش روزانه
# ─────────────────────────────────────────────────────────────────────────────

def test_daily_report_shows_the_internal_cycle(monkeypatch, tmp_path):
    _fresh_db(monkeypatch, tmp_path, "report.db")
    cid = db.create_country(92_000, "کشور گزارش", "🏳️", country_key="report_land")
    db.update_country_field(cid, "approval_rating", 45)
    ia.set_tax_policy(cid, "heavy")
    ia.create_crisis(cid, "epidemic", severity="severe", origin="admin", force=True)
    ia.run_daily_cycle(db.get_country_by_id(cid), None)

    country = db.get_country_by_id(cid)
    section = ia.daily_report_section(country)

    assert "جمعیت فعلی" in section
    assert "سیاست مالیاتی" in section and "سنگین" in section
    assert "تمکین مالیاتی مردم" in section
    assert "ناآرامی داخلی" in section
    assert "بحران‌های فعال" in section and "اپیدمی" in section
    # عدد تمکین باید همانی باشد که موتور می‌گوید، نه عدد ثابت متن
    assert f"{int(ia.compliance_for(float(country['approval_rating'])) * 100)}٪" in section


def test_daily_report_section_is_silent_when_system_is_off(monkeypatch, tmp_path):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "off_report.db"))
    db.init_db()
    cid = db.create_country(92_100, "کشور خاموش", "🏳️", country_key="off_land")
    assert ia.is_enabled() is False
    assert ia.daily_report_section(db.get_country_by_id(cid)) == ""


def test_full_daily_report_message_contains_the_domestic_block(monkeypatch, tmp_path):
    _fresh_db(monkeypatch, tmp_path, "full_report.db")
    cid = db.create_country(92_200, "کشور کامل", "🏳️", country_key="full_land")
    db.update_country_field(cid, "approval_rating", 70)
    ia.run_daily_cycle(db.get_country_by_id(cid), None)

    country = db.get_country_by_id(cid)
    app_res = {
        "grain_ok": True,
        "oil_ok": True,
        "elec_ok": True,
        "net_change": 0,
        "new_approval": 70,
        "emig_count": 0,
    }
    message = approval_system.build_daily_country_report_message(
        country, app_res, datetime.date.today().isoformat()
    )
    assert "وضعیت داخلی کشور" in message
    assert "روایت روزانه کشور" in message  # بخش قدیمی حذف نشده باشد


def test_daily_report_never_changes_player_money(monkeypatch, tmp_path):
    """گزارش فقط می‌خواند؛ هیچ دارایی‌ای را نباید لمس کند."""
    _fresh_db(monkeypatch, tmp_path, "readonly_report.db")
    cid = db.create_country(92_300, "کشور امن", "🏳️", country_key="safe_land")
    ia.run_daily_cycle(db.get_country_by_id(cid), None)

    before = db.get_country_by_id(cid)
    snapshot = {k: before[k] for k in ("treasury", "daily_income", "tax_income", "population", "oil_reserves", "gold")}
    ia.daily_report_section(before)
    after = db.get_country_by_id(cid)
    assert {k: after[k] for k in snapshot} == snapshot


# ─────────────────────────────────────────────────────────────────────────────
# ۳. فصل ۹ دانشکده
# ─────────────────────────────────────────────────────────────────────────────

def test_chapter_nine_no_longer_repeats_a_stale_tax_rule():
    source = inspect.getsource(__import__("handlers.guide", fromlist=["guide"]))
    assert "کاهش ۵۰٪ درآمد مالیاتی کشور" not in source, "قانون قدیمی و غلط مالیات هنوز در راهنماست"


def test_chapter_nine_reads_compliance_from_the_engine_and_links_to_chapter_ten():
    source = inspect.getsource(__import__("handlers.guide", fromlist=["guide"]))
    assert "ia.compliance_for(value)" in source
    assert 'callback_data="help:cat:domestic"' in source
    assert 'callback_data="dom:unrest"' in source


def test_stage_labels_have_one_source_of_truth():
    assert internal_admin._stage_fa("impact") == ia.crisis_stage_label("impact")
    assert ia.crisis_stage_label("warning") == "هشدار"
    assert ia.crisis_stage_label("ended") == "پایان‌یافته"
