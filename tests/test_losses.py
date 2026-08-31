# -*- coding: utf-8 -*-
"""
تست‌های سیستم مدیریت تلفات (Losses System).

اجرا:
    pip install pytest
    python -m pytest tests/ -v

این تست‌ها باگ‌های رفع‌شده را قفل می‌کنند تا در تغییرات بعدی برنگردند.
"""

import os
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402


@pytest.fixture()
def db(monkeypatch):
    """یک دیتابیس موقت و ایزوله برای هر تست."""
    tmpdir = tempfile.mkdtemp()
    monkeypatch.setattr(config, "DB_PATH", os.path.join(tmpdir, "test.db"))

    import importlib
    import database
    importlib.reload(database)

    database.init_db()
    database.create_country(111111, "ایران", "🇮🇷", country_key="iran")
    return database


@pytest.fixture()
def country(db):
    return db.get_all_countries()[0]


def _seed(db, cid, **cols):
    """مقداردهی مستقیم ستون‌های کشور + افزودن دارایی/ساختمان نمونه."""
    conn = db.get_connection()
    cur = conn.cursor()
    if cols:
        sets = ", ".join(f"{k} = ?" for k in cols)
        cur.execute(f"UPDATE countries SET {sets} WHERE id = ?", (*cols.values(), cid))
    cur.execute(
        "INSERT OR REPLACE INTO country_assets"
        " (country_id, country_key, equipment_key, equipment_name, category, amount)"
        " VALUES (?,?,?,?,?,?)",
        (cid, "iran", "f14", "جنگنده F-14 تامکت", "Aircraft", 24),
    )
    cur.execute(
        "INSERT OR REPLACE INTO equipment (country_id, item_key, quantity) VALUES (?,?,?)",
        (cid, "chip_fab", 2),
    )
    conn.commit()
    conn.close()


def _snapshot(db, cid):
    c = db.get_country_by_id(cid)
    asset = db.get_asset_by_key(cid, "f14")
    return {
        "f14": asset["amount"] if asset else 0,
        "warheads": c["warheads"],
        "microchips": c["microchips"],
        "gold": c["gold"],
        "uranium_ore": c["uranium_ore"],
        "nuclear_fuel": c["nuclear_fuel"],
        "medical_isotopes": c.get("medical_isotopes", 0) or 0,
        "enriched_60": c.get("enriched_60", 0) or 0,
        "weapons_grade_90": c.get("weapons_grade_90", 0) or 0,
        "treasury": c["treasury"],
        "oil_reserves": c["oil_reserves"],
        "active_personnel": c["active_personnel"],
        "chip_fab": db.get_equipment(cid).get("chip_fab", 0),
    }


FULL_ITEMS = [
    {"key": "f14", "name": "جنگنده F-14", "subcat": "جنگنده‌ها", "emoji": "✈️", "unit": "فروند", "qty": 4},
    {"key": "__warheads__", "name": "کلاهک", "special": "warheads", "subcat": "هسته‌ای", "emoji": "🚀", "unit": "عدد", "qty": 3},
    {"key": "__microchips__", "name": "تراشه", "special": "microchips", "subcat": "فناوری", "emoji": "💻", "unit": "عدد", "qty": 100},
    {"key": "__gold__", "name": "طلا", "special": "gold", "subcat": "مالی", "emoji": "🪙", "unit": "شمش", "qty": 20},
    {"key": "__uranium_ore__", "name": "اورانیوم", "special": "uranium_ore", "subcat": "منابع", "emoji": "☢️", "unit": "تن", "qty": 10},
    {"key": "__nuclear_fuel__", "name": "سوخت هسته‌ای", "special": "nuclear_fuel", "subcat": "منابع", "emoji": "🟢", "unit": "کیلوگرم", "qty": 15},
    {"key": "__medical_isotopes__", "name": "ایزوتوپ پزشکی", "special": "medical_isotopes", "subcat": "منابع", "emoji": "🟡", "unit": "کیلوگرم", "qty": 5},
    {"key": "__enriched_60__", "name": "اورانیوم ۶۰٪", "special": "enriched_60", "subcat": "منابع", "emoji": "🟠", "unit": "کیلوگرم", "qty": 2},
    {"key": "__weapons_grade_90__", "name": "اورانیوم تسلیحاتی", "special": "weapons_grade_90", "subcat": "منابع", "emoji": "🔴", "unit": "کیلوگرم", "qty": 4},
    {"key": "__cost_money__", "name": "هزینه", "special": "money", "subcat": "هزینه", "emoji": "💵", "unit": "دلار", "qty": 5_000_000},
    {"key": "__cost_oil__", "name": "سوخت", "special": "oil", "subcat": "هزینه", "emoji": "🛢️", "unit": "بشکه", "qty": 100_000},
    {"key": "__personnel_mil__", "name": "کشته", "special": "mil_kia", "subcat": "انسانی", "emoji": "🪖", "unit": "نفر", "qty": 500},
    {"key": "__personnel_wounded__", "name": "مجروح", "special": "wounded", "subcat": "انسانی", "emoji": "🏥", "unit": "نفر", "qty": 1200},
]


# ---------------------------------------------------------------- دیتابیس


class TestApplyAndRevert:
    def test_apply_deducts_every_resource(self, db, country):
        cid = country["id"]
        _seed(db, cid, warheads=10, microchips=500, gold=100, uranium_ore=50, nuclear_fuel=80, medical_isotopes=30, enriched_60=20, weapons_grade_90=25)
        before = _snapshot(db, cid)

        ok, rid, err = db.create_loss_report(cid, [dict(i) for i in FULL_ITEMS], "عملیات", "", 1)
        assert ok, err

        after = _snapshot(db, cid)
        assert after["f14"] == before["f14"] - 4
        assert after["warheads"] == before["warheads"] - 3
        assert after["microchips"] == before["microchips"] - 100
        assert after["gold"] == before["gold"] - 20
        assert after["uranium_ore"] == before["uranium_ore"] - 10
        assert after["nuclear_fuel"] == before["nuclear_fuel"] - 15
        assert after["treasury"] == before["treasury"] - 5_000_000
        assert after["oil_reserves"] == before["oil_reserves"] - 100_000
        assert after["active_personnel"] == before["active_personnel"] - 500

    def test_revert_restores_everything(self, db, country):
        """رگرسیون: بازگردانی باید منابع راهبردی را هم برگرداند."""
        cid = country["id"]
        _seed(db, cid, warheads=10, microchips=500, gold=100, uranium_ore=50, nuclear_fuel=80, medical_isotopes=30, enriched_60=20, weapons_grade_90=25)
        before = _snapshot(db, cid)

        ok, rid, _ = db.create_loss_report(cid, [dict(i) for i in FULL_ITEMS], "عملیات", "", 1)
        assert ok
        assert _snapshot(db, cid) != before

        ok, err = db.revert_loss_report(rid)
        assert ok, err
        assert _snapshot(db, cid) == before

    def test_delete_restores_everything(self, db, country):
        cid = country["id"]
        _seed(db, cid, warheads=10, microchips=500, gold=100, uranium_ore=50, nuclear_fuel=80, medical_isotopes=30, enriched_60=20, weapons_grade_90=25)
        before = _snapshot(db, cid)

        ok, rid, _ = db.create_loss_report(cid, [dict(i) for i in FULL_ITEMS], "عملیات", "", 1)
        assert ok
        ok, err = db.delete_loss_report(rid)
        assert ok, err
        assert _snapshot(db, cid) == before

    def test_double_revert_is_rejected(self, db, country):
        cid = country["id"]
        _seed(db, cid, warheads=10)
        items = [{"key": "__warheads__", "name": "کلاهک", "special": "warheads",
                  "subcat": "ه", "emoji": "🚀", "unit": "عدد", "qty": 3}]
        ok, rid, _ = db.create_loss_report(cid, items, "op", "", 1)
        assert db.revert_loss_report(rid)[0] is True
        ok2, err = db.revert_loss_report(rid)
        assert ok2 is False
        assert db.get_country_by_id(cid)["warheads"] == 10


class TestStockClamping:
    def test_loss_exceeding_stock_clamps_to_zero(self, db, country):
        """اگر تلفات بیشتر از موجودی انبار باشد، موجودی صفر می‌شود و ارور نمی‌دهد."""
        cid = country["id"]
        _seed(db, cid, warheads=2)
        # F-14 has 24 units, warheads has 2 units
        items = [
            {"key": "f14", "name": "F-14", "subcat": "ج", "emoji": "✈️", "unit": "فروند", "qty": 30},  # 30 > 24
            {"key": "__warheads__", "name": "کلاهک", "special": "warheads",
             "subcat": "ه", "emoji": "🚀", "unit": "عدد", "qty": 10},  # 10 > 2
        ]
        ok, rid, err = db.create_loss_report(cid, items, "عملیات سنگین", "", 1)
        assert ok is True, f"گزارش نباید ریجکت شود: {err}"
        assert db.get_asset_by_key(cid, "f14")["amount"] == 0
        assert db.get_country_by_id(cid)["warheads"] == 0

        # بازگردانی فقط مقداری که واقعاً کسر شده بود را برمی‌گرداند
        ok_rev, _ = db.revert_loss_report(rid)
        assert ok_rev is True
        assert db.get_asset_by_key(cid, "f14")["amount"] == 24
        assert db.get_country_by_id(cid)["warheads"] == 2

    def test_unknown_asset_or_zero_stock_clamps_safely(self, db, country):
        """تجهیز ناشناخته یا با موجودی صفر بدون ایجاد خطا یا منفی شدن ثبت می‌شود."""
        cid = country["id"]
        _seed(db, cid)
        items = [
            {"key": "f14", "name": "F-14", "subcat": "ج", "emoji": "✈️", "unit": "فروند", "qty": 4},
            {"key": "does_not_exist", "name": "؟", "subcat": "ج", "emoji": "✈️", "unit": "فروند", "qty": 5},
        ]
        ok, rid, err = db.create_loss_report(cid, items, "op", "", 1)
        assert ok is True, f"گزارش نباید ریجکت شود: {err}"
        assert db.get_asset_by_key(cid, "f14")["amount"] == 20


class TestBuildings:
    def test_chip_fab_destruction_works(self, db, country):
        """رگرسیون: قبلاً NameError می‌داد و کل گزارش fail می‌شد."""
        cid = country["id"]
        _seed(db, cid)
        items = [{"key": "chip_fab", "name": "کارخانه تراشه", "special": "building",
                  "subcat": "ساخت‌سازی", "emoji": "🏗️", "unit": "واحد", "qty": 1}]
        ok, rid, err = db.create_loss_report(cid, items, "بمباران", "", 1)
        assert ok, err
        assert db.get_equipment(cid).get("chip_fab") == 1

    def test_building_quantity_never_goes_negative(self, db, country):
        """رگرسیون: ساختمانی که موجودی صفر دارد نباید منفی شود."""
        cid = country["id"]
        _seed(db, cid)
        conn = db.get_connection()
        conn.execute("INSERT OR REPLACE INTO equipment (country_id,item_key,quantity) VALUES (?,?,0)",
                     (cid, "oil_refinery"))
        conn.commit()
        conn.close()

        items = [{"key": "oil_refinery", "name": "پالایشگاه", "special": "building",
                  "subcat": "ساخت‌سازی", "emoji": "🏗️", "unit": "واحد", "qty": 5}]
        ok, rid, err = db.create_loss_report(cid, items, "op", "", 1)
        assert ok, err

        conn = db.get_connection()
        qty = conn.execute(
            "SELECT quantity FROM equipment WHERE country_id=? AND item_key='oil_refinery'", (cid,)
        ).fetchone()["quantity"]
        conn.close()
        assert qty == 0, f"موجودی منفی شد: {qty}"


class TestStats:
    def test_reverted_reports_excluded_from_active_count(self, db, country):
        cid = country["id"]
        _seed(db, cid)
        item = [{"key": "f14", "name": "F-14", "subcat": "جنگنده‌ها", "emoji": "✈️", "unit": "فروند", "qty": 2}]
        db.create_loss_report(cid, [dict(i) for i in item], "a", "", 1)
        _, rid2, _ = db.create_loss_report(cid, [dict(i) for i in item], "b", "", 1)
        db.revert_loss_report(rid2)

        s = db.get_loss_stats(cid)
        assert s["reports"] == 1
        assert s["reverted"] == 1
        assert s["total"] == 2
        # فقط گزارش فعال در آمار تجمیعی می‌آید، نه بازگردانی‌شده
        assert s["by_subcat"]["جنگنده‌ها"] == 2


# ---------------------------------------------------------------- پارسر


class TestParser:
    def test_full_standard_report(self):
        from handlers.losses import parse_loss_report_text
        text = """📄 تلفات تجهیزات 🇦🇪 امارات — عملیات «سایه‌های خاکستری»
━━━━━━━━━━━━━━━━━━

✈️ جنگنده F-16 بلاک 60
تلفات: 4 فروند
✈️ جنگنده میراژ 2000
تلفات: حدود 2 فروند

👥 تلفات انسانی

🪖 نظامیان کشته: حدود 320 نفر
🏥 مجروحان: 1,150 نفر
👤 غیرنظامیان کشته: 45 نفر

💸 هزینه آماده‌سازی عملیات

💵 هزینه مالی: 12 میلیون دلار
🛢️ سوخت مصرفی: 250,000 بشکه"""
        r = parse_loss_report_text(text)
        assert r["country"] == "امارات"
        assert r["op"] == "سایه‌های خاکستری"
        assert [(n, q) for n, q, _ in r["items"]] == [
            ("جنگنده F-16 بلاک 60", 4), ("جنگنده میراژ 2000", 2)
        ]
        assert r["human"] == {"mil": 320, "wounded": 1150, "civilians": 45}
        assert r["costs"] == {"money": 12_000_000, "oil": 250_000}

    def test_persian_digits(self):
        from handlers.losses import parse_loss_report_text
        r = parse_loss_report_text("📄 تلفات تجهیزات 🇮🇷 ایران\nجنگنده F-14\nتلفات: ۱۲ فروند")
        assert r["items"][0][1] == 12

    def test_decimal_quantity_rounds_up(self):
        """رگرسیون: «1.5 واحد» قبلاً می‌شد qty=1 و unit='.5 واحد'."""
        from handlers.losses import parse_loss_report_text
        r = parse_loss_report_text("📄 تلفات تجهیزات 🇮🇷 ایران\nپالایشگاه\nتلفات: 1.5 واحد")
        assert r["items"] == [("پالایشگاه", 2, "واحد")]

    def test_stray_dollar_amount_is_not_a_cost(self):
        """رگرسیون: عدد دلاری در متن آزاد نباید از خزانه کم شود."""
        from handlers.losses import parse_loss_report_text
        text = """📄 تلفات تجهیزات 🇮🇷 ایران — عملیات «ب»
🏦 خسارت به بازار: ارزش تخریب‌شده 800 میلیون دلار برآورد شد
جنگنده F-14
تلفات: 2 فروند"""
        assert parse_loss_report_text(text)["costs"] == {"money": 0, "oil": 0}

    def test_stray_dollar_amount_after_cost_section(self):
        """رگرسیون: بخش هزینه باید در بخش بعدی تمام شود؛ عدد دلاری بخش «📌 توضیح» جزو هزینه نیست."""
        from handlers.losses import parse_loss_report_text
        text = """📄 تلفات تجهیزات 🇮🇷 ایران — عملیات «ب»
جنگنده F-14
تلفات: 2 فروند

💸 هزینه آماده‌سازی عملیات
مبلغ: 2.5 میلیون دلار
سوخت: 12000 بشکه

📌 توضیح: خسارت 800 میلیون دلاری به بازار جهانی وارد شد."""
        assert parse_loss_report_text(text)["costs"] == {"money": 2_500_000, "oil": 12_000}

    def test_distinct_commanders_do_not_collapse(self):
        """رگرسیون: واژه عمومی «فرمانده» باعث می‌شد دو عنوان متفاوت به یک نفر تطبیق بخورند."""
        from handlers.losses import match_commander
        cmds = [
            {"key": "commander_aerospace", "title": "فرمانده نیروی هوافضای سپاه", "status": "active"},
            {"key": "commander_irgc", "title": "فرمانده کل سپاه پاسداران", "status": "active"},
            {"key": "chief_general_staff", "title": "رئیس ستاد کل نیروهای مسلح", "status": "active"},
            {"key": "minister_intel", "title": "رئیس اطلاعات سپاه / وزیر اطلاعات", "status": "active"},
        ]
        for title, expected in [
            ("فرمانده نیروی هوافضای سپاه", "commander_aerospace"),
            ("فرمانده کل سپاه پاسداران", "commander_irgc"),
            ("رئیس ستاد کل نیروهای مسلح", "chief_general_staff"),
            ("فرمانده هوافضا", "commander_aerospace"),
        ]:
            assert (match_commander(title, cmds) or {}).get("key") == expected, title
        assert match_commander("قایق تندرو رزمی", cmds) is None

    def test_inactive_commander_not_matched(self):
        """فرمانده‌ای که قبلاً ترور شده دوباره انتخاب نمی‌شود."""
        from handlers.losses import match_commander
        cmds = [{"key": "k1", "title": "فرمانده نیروی هوافضای سپاه", "status": "dead"}]
        assert match_commander("فرمانده نیروی هوافضای سپاه", cmds) is None

    def test_commander_title_is_not_a_strategic_resource(self):
        """رگرسیون: «مدیر سازمان اطلاعات» نباید با «طلا» داخل «اطلاعات» تطبیق بخورد."""
        from handlers.losses import match_strategic_resource
        for title in ("مدیر سازمان اطلاعات و امنیت ملی", "رئیس سرویس اطلاعات",
                      "فرمانده نیروی هوایی و پدافند", "رئیس ستاد کل نیروهای مسلح"):
            assert match_strategic_resource(title) is None, title

    def test_gold_still_matches(self):
        """طلا باید همچنان درست تطبیق بخورد."""
        from handlers.losses import match_strategic_resource
        for name in ("شمش طلا", "ذخایر طلا", "طلا"):
            assert (match_strategic_resource(name) or {}).get("special") == "gold", name

    def test_reversed_human_casualty_order(self):
        """رگرسیون: «۳۲۰ نفر کشته نظامی» باید درست خوانده شود."""
        from handlers.losses import parse_loss_report_text
        text = """📄 تلفات تجهیزات 🇮🇷 ایران
جنگنده F-14
تلفات: 1 فروند
👥 تلفات انسانی
320 نفر کشته نظامی
1,150 نفر مجروح
45 نفر غیرنظامی"""
        assert parse_loss_report_text(text)["human"] == {"mil": 320, "wounded": 1150, "civilians": 45}

    def test_equal_military_and_civilian_counts(self):
        """رگرسیون: وقتی هر دو مساوی بودند، mil به اشتباه صفر می‌شد."""
        from handlers.losses import parse_loss_report_text
        text = """📄 تلفات تجهیزات 🇮🇷 ایران
جنگنده F-14
تلفات: 1 فروند
👥 تلفات انسانی
🪖 نظامیان کشته: 50 نفر
👤 غیرنظامیان کشته: 50 نفر"""
        h = parse_loss_report_text(text)["human"]
        assert h["mil"] == 50 and h["civilians"] == 50


class TestAssetMatching:
    ASSETS = [
        {"equipment_key": "f16_block60_uae", "equipment_name": "جنگنده F-16 بلاک 60", "category": "Aircraft"},
        {"equipment_key": "mirage2000_uae", "equipment_name": "جنگنده میراژ 2000", "category": "Aircraft"},
        {"equipment_key": "thaad_uae", "equipment_name": "سامانه پدافندی THAAD", "category": "Air Defense"},
        {"equipment_key": "bavar373_iran", "equipment_name": "سامانه پدافندی باور 373", "category": "Air Defense"},
    ]

    @pytest.mark.parametrize("query,expected", [
        ("جنگنده F-16 بلاک 60", "جنگنده F-16 بلاک 60"),
        ("F-16", "جنگنده F-16 بلاک 60"),
        ("جنگنده میراژ 2000", "جنگنده میراژ 2000"),
        ("میراژ", "جنگنده میراژ 2000"),
        ("THAAD", "سامانه پدافندی THAAD"),
        ("باور 373", "سامانه پدافندی باور 373"),
        ("سامانه پدافندی باور ۳۷۳", "سامانه پدافندی باور 373"),
    ])
    def test_matches_correctly(self, query, expected):
        from handlers.losses import match_asset_by_name
        m = match_asset_by_name(query, self.ASSETS)
        assert m is not None and m["equipment_name"] == expected

    @pytest.mark.parametrize("query", [
        "جنگنده رافال", "جنگنده سوخو-35", "موشک کروز تاماهاوک",
        "تانک آبرامز", "پهپاد بیرقدار", "سامانه پدافندی S-400",
    ])
    def test_rejects_generic_word_only_matches(self, query):
        """رگرسیون: تجهیزی که کشور ندارد نباید به تجهیز دیگری تطبیق بخورد."""
        from handlers.losses import match_asset_by_name
        assert match_asset_by_name(query, self.ASSETS) is None


class TestReportRendering:
    def test_strategic_items_not_under_human_casualties(self):
        """رگرسیون: کلاهک/طلا/تراشه زیر تیتر «تلفات انسانی» چاپ می‌شدند."""
        from handlers.losses import build_loss_report_text
        items = [
            {"key": "f14", "name": "جنگنده F-14", "subcat": "جنگنده‌ها", "emoji": "✈️", "unit": "فروند", "qty": 4},
            {"key": "__warheads__", "name": "کلاهک", "special": "warheads", "subcat": "ه", "emoji": "🚀", "unit": "عدد", "qty": 3},
            {"key": "__gold__", "name": "شمش طلا", "special": "gold", "subcat": "م", "emoji": "🪙", "unit": "شمش", "qty": 20},
            {"key": "__personnel_mil__", "name": "نظامیان", "special": "mil_kia", "subcat": "ا", "emoji": "🪖", "unit": "نفر", "qty": 500},
        ]
        out = build_loss_report_text("🇮🇷", "ایران", "تست", items)

        strategic_at = out.index("☢️ ذخایر و منابع راهبردی")
        human_at = out.index("👥 تلفات انسانی")
        assert out.index("کلاهک") > strategic_at
        assert out.index("کلاهک") < human_at, "کلاهک نباید در بخش تلفات انسانی باشد"
        assert out.index("شمش طلا") < human_at
        assert out.index("نظامیان") > human_at

    def test_no_duplicated_emoji_in_labels(self):
        """رگرسیون: نام ساختمان از config خودش ایموجی دارد؛
        نباید «🏗️ 🛢️ پالایشگاه نفت» تولید شود."""
        from handlers.losses import build_loss_report_text, _split_emoji

        name, emoji = _split_emoji("🛢️ پالایشگاه نفت", "🏗️")
        assert name == "پالایشگاه نفت"
        assert emoji == "🛢️"

        items = [{"key": "oil_refinery", "name": name, "special": "building",
                  "subcat": "ساخت‌سازی", "emoji": emoji, "unit": "واحد", "qty": 1}]
        out = build_loss_report_text("🇾🇪", "یمن", "تست", items)
        assert "🏗️ 🛢️" not in out
        assert "🛢️ پالایشگاه نفت: 1 واحد" in out

    def test_fallback_category_label_has_single_emoji(self):
        """رگرسیون: fallback دسته «📦 🚛 نیروی زمینی» تولید می‌کرد."""
        from handlers.losses import classify_subcat
        label, emoji = classify_subcat(
            {"category": "Ground Forces", "equipment_name": "چیز ناشناخته", "equipment_key": "x"}
        )
        assert not label.startswith("🚛")
        assert emoji != "📦"

    def test_technical_vehicle_classified_as_armored(self):
        """تویوتا تکنیکال باید در «خودروهای زرهی» بیفتد، نه fallback."""
        from handlers.losses import classify_subcat
        label, emoji = classify_subcat({
            "category": "Ground Forces",
            "equipment_name": "تویوتا تکنیکال مجهز به دوشکا و زو-۲۳",
            "equipment_key": "toyota_technical_yemen",
        })
        assert label == "خودروهای زرهی"

    def test_no_empty_equipment_summary(self):
        """گزارشی که فقط قلم ویژه دارد نباید هدر «جمع تلفات» خالی بزند."""
        from handlers.losses import build_loss_report_text
        items = [{"key": "__gold__", "name": "طلا", "special": "gold",
                  "subcat": "م", "emoji": "🪙", "unit": "شمش", "qty": 5}]
        out = build_loss_report_text("🇮🇷", "ایران", "تست", items)
        assert "جمع تلفات ثبت‌شده" not in out

class TestBaseLosses:
    def test_loss_applied_specifically_to_base(self, db, country):
        cid = country["id"]
        # ایجاد پایگاه پیشروی برای کشور
        conn = db.get_connection()
        conn.execute("INSERT INTO foreign_bases (owner_id, host_id, name, capacity, level) VALUES (?, ?, 'پایگاه Desert Shield', 20, 1)", (cid, cid))
        base_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        conn.execute("INSERT INTO base_assets (base_id, equipment_key, equipment_name, category, amount) VALUES (?, 'f35_usa', 'جنگنده F-35A', 'Aircraft', 12)", (base_id,))
        conn.commit()
        conn.close()

        # ثبت گزارش تلفات برای پایگاه
        items = [{"key": "f35_usa", "name": "جنگنده F-35A", "qty": 4, "base_id": base_id}]
        ok, rid, err = db.create_loss_report(cid, items, "ضربه به پایگاه", "", 1)
        assert ok, err

        # موجودی پایگاه باید از ۱۲ به ۸ کاهش یابد
        conn = db.get_connection()
        base_amt = conn.execute("SELECT amount FROM base_assets WHERE base_id = ? AND equipment_key = 'f35_usa'", (base_id,)).fetchone()["amount"]
        conn.close()
        assert base_amt == 8

        # بازگردانی تلفات باید به پایگاه برگرداند
        ok_rev, _ = db.revert_loss_report(rid)
        assert ok_rev
        conn = db.get_connection()
        base_amt_rev = conn.execute("SELECT amount FROM base_assets WHERE base_id = ? AND equipment_key = 'f35_usa'", (base_id,)).fetchone()["amount"]
        conn.close()
        assert base_amt_rev == 12

    def test_parser_extracts_base_name_from_header(self):
        from handlers.losses import parse_loss_report_text
        text = """📄 تلفات تجهیزات 🇺🇸 آمریکا — پایگاه «Desert Shield» — عملیات «طوفان صحرا»
━━━━━━━━━━━━━━━━━━
✈️ جنگنده F-35A
تلفات: 2 فروند"""
        parsed = parse_loss_report_text(text)
        assert parsed["country"] == "آمریکا"
        assert parsed["base"] == "Desert Shield"
        assert parsed["op"] == "طوفان صحرا"
        assert parsed["items"][0][0] == "جنگنده F-35A"
        assert parsed["items"][0][1] == 2


class TestAdminAdjustGuards:
    """رگرسیون: دکمه‌های ➖ پنل ادمین نباید مقدار را منفی کنند."""

    def test_gold_and_oil_never_go_negative(self, tmp_path, monkeypatch):
        import importlib, config
        monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "t.db"))
        import database as db
        importlib.reload(db)
        db.init_db()
        cid = db.create_country(777001, "ایران", "🇮🇷", country_key="iran")
        db.adjust_gold(cid, -10 ** 9)
        db.adjust_oil(cid, -10 ** 12)
        db.adjust_oil_production(cid, -10 ** 12)
        c = db.get_country_by_id(cid)
        assert c["gold"] == 0
        assert c["oil_reserves"] == 0
        assert c["oil_production"] == 0
        db.adjust_gold(cid, 300)
        assert db.get_country_by_id(cid)["gold"] == 300


# ─────────────────────────────────────────────────────────────────────────────
# کسر ذخایر نفت و غلات از کشور مدافع
# (درخواست مدیریت: «نفتکش گفت نفت کم کن»)
# ─────────────────────────────────────────────────────────────────────────────

def test_oil_and_grain_are_recognised_as_strategic_resources():
    from handlers.losses import match_strategic_resource

    for name in ("ذخایر نفت خام", "مخازن نفت", "نفتکش راهبردی", "انبار سوخت"):
        match = match_strategic_resource(name)
        assert match is not None, name
        assert match["special"] == "oil_reserves"
        assert match["unit"] == "بشکه"

    for name in ("ذخایر غلات", "انبار گندم", "ذخایر غذایی"):
        match = match_strategic_resource(name)
        assert match is not None, name
        assert match["special"] == "grain"
        assert match["unit"] == "تن"


def test_buildings_are_not_swallowed_by_the_resource_matcher():
    """match_strategic_resource قبل از match_building اجرا می‌شود.

    بدون محافظ، «پالایشگاه نفت» و «سیلوی استراتژیک غلات» به‌جای ساختمان،
    منبع راهبردی تشخیص داده می‌شدند و ساختمان هرگز کسر نمی‌شد.
    """
    from handlers.losses import match_strategic_resource

    for name in (
        "پالایشگاه نفت",
        "سیلوی استراتژیک غلات",
        "مزرعه گندم و غلات",
        "مجتمع استخراج سنگ آهن و فولاد",
        "نیروگاه فسیلی",
        "بندر تجاری",
    ):
        assert match_strategic_resource(name) is None, name

    # سامانه‌ی پدافند «برق-۲» یمن نباید راهبردی برق شمرده شود
    assert match_strategic_resource("سامانه پدافند هوایی برق-۲ (Barq-2)") is None


def test_oil_reserve_loss_is_deducted_and_reverted(db, country):
    cid = country["id"]
    db.update_country_field(cid, "oil_reserves", 500_000)
    db.update_country_field(cid, "grain", 40_000)

    ok, report_id, _err = db.create_loss_report(cid, [
        {"key": "__oil_reserves__", "name": "ذخایر نفت خام", "special": "oil_reserves",
         "unit": "بشکه", "qty": 120_000},
        {"key": "__grain__", "name": "ذخایر غلات", "special": "grain",
         "unit": "تن", "qty": 9_000},
    ], operation_name="آزمون کسر منابع")
    assert ok and report_id

    after = db.get_country_by_id(cid)
    assert after["oil_reserves"] == 380_000
    assert after["grain"] == 31_000

    ok, _msg = db.revert_loss_report(report_id)
    assert ok
    restored = db.get_country_by_id(cid)
    assert restored["oil_reserves"] == 500_000
    assert restored["grain"] == 40_000


def test_defender_oil_loss_is_separate_from_attacker_fuel_cost(db):
    """special «oil» هزینه‌ی سوخت مهاجم است؛ «oil_reserves» کسر ذخایر مدافع.

    اگر یکی شوند، خط «سوخت مصرفی» گزارش مهاجم با تلفات نفت مدافع قاطی می‌شود.
    """
    from handlers.losses import STRATEGIC_SPECIALS, COST_SPECIALS

    assert "oil_reserves" in STRATEGIC_SPECIALS
    assert "oil_reserves" not in COST_SPECIALS
    assert "oil" in COST_SPECIALS
    assert db.LOSS_SPECIAL_COLUMNS["oil_reserves"] == "oil_reserves"
    assert db.LOSS_SPECIAL_COLUMNS["oil"] == "oil_reserves"


# ─────────────────────────────────────────────────────────────────────────────
# ترتیب تطبیق: ساختمانِ دقیق باید قبل از فرماندهِ فازی بررسی شود
# ─────────────────────────────────────────────────────────────────────────────

def test_building_name_is_never_matched_as_a_commander(db, country):
    """رگرسیون: «مرکز تجاری» با «کمیسیون نظامی مرکزی (CMC)» تطبیق می‌خورد.

    نتیجه‌اش این بود که پیست‌کردن یک گزارش خسارت شهری، به‌جای تخریب ساختمان،
    یک فرمانده ارشد را ترور می‌کرد.
    """
    from handlers.losses import match_commander, match_building

    cid = country["id"]
    conn = db.get_connection()
    with conn:
        conn.execute(
            "INSERT INTO equipment (country_id, item_key, quantity) VALUES (?,?,?)"
            " ON CONFLICT(country_id, item_key) DO UPDATE SET quantity = quantity + excluded.quantity",
            (cid, "commercial", 3),
        )
    conn.close()

    commanders = [
        {"key": "cmc_vice_chair", "title": "نایب‌رئیس کمیسیون نظامی مرکزی (CMC)", "status": "active"},
        {"key": "army_chief", "title": "رئیس ستاد کل ارتش", "status": "active"},
    ]

    # ساختمان باید پیدا شود
    assert match_building("مرکز تجاری", cid) is not None
    # و همان اسم نباید به فرمانده تبدیل شود مگر اینکه ساختمان پیدا نشود
    building_first = match_building("مرکز تجاری", cid)
    assert building_first["key"] == "commercial"

    # و حتی وقتی کشور آن ساختمان را نساخته، باز هم نباید فرمانده شود:
    # match_commander نام‌های کاتالوگ ساخت‌وساز را رد می‌کند.
    assert match_commander("مرکز تجاری", commanders) is None
    assert match_commander("هتل بین‌المللی", commanders) is None
    assert match_commander("مرکز رسانه و پخش ملی", commanders) is None
    # ولی عنوان واقعی فرمانده همچنان باید پیدا شود
    assert match_commander("نایب‌رئیس کمیسیون نظامی مرکزی", commanders)["key"] == "cmc_vice_chair"


def test_loss_pipeline_checks_buildings_before_commanders():
    """ترتیب در بات و در ابزار loss_tool باید یکی باشد."""
    import inspect
    from handlers import losses as losses_handler

    source = inspect.getsource(losses_handler)
    build_at = source.index("b = match_building(name, country[\"id\"])")
    cmd_at = source.index("cmd_match = match_commander(name,")
    assert build_at < cmd_at, "match_building باید قبل از match_commander اجرا شود"

    tool_source = open(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "loss_tool.py"),
        encoding="utf-8",
    ).read()
    t_build = tool_source.index("b = match_building(name, cid)")
    t_cmd = tool_source.index("cmd_match = match_commander(name,")
    assert t_build < t_cmd, "ابزار loss_tool باید هم‌ترتیب با بات باشد"


def test_long_statement_is_split_instead_of_failing_as_caption():
    """رگرسیون: بیانیه‌ی بلندتر از ۱۰۲۴ کاراکتر با «caption is too long» رد می‌شد."""
    import inspect
    from handlers import statements

    source = inspect.getsource(statements)
    assert "CAPTION_LIMIT = 1024" in source
    assert "long_statement" in source
    assert "send_message" in source, "متن کامل باید به‌صورت پیام جداگانه برود"


def test_blackout_phrases_route_to_electricity_not_barq2():
    """رگرسیون مسیر کامل پارس: خط خاموشی نباید به پدافند «برق-۲» بچسبد."""
    from handlers.losses import (
        is_explicit_strategic,
        match_asset_by_name,
        match_strategic_resource,
    )

    yemen_assets = [{
        "equipment_key": "barq2_ym",
        "equipment_name": "سامانه موشکی پدافند هوایی برق-۲ (Barq-2)",
        "category": "Air Defense",
    }]

    for name in ("قطع برق سراسری کشور", "برق سراسری", "خاموشی سراسری", "شبکه برق ملی"):
        # همان ترتیب مسیر اصلی پارسر: اول صریحِ راهبردی، بعد دارایی، بعد match_strategic_resource
        a = None if is_explicit_strategic(name) else match_asset_by_name(name, yemen_assets)
        assert a is None, f"{name} wrongly matched a yemen asset"
        res = match_strategic_resource(name)
        assert res and res["special"] == "electricity", name

    # و دارایی واقعی همچنان از مسیر خودش پیدا می‌شود
    a = match_asset_by_name("سامانه پدافند هوایی برق-۲", yemen_assets)
    assert a is not None and a["equipment_key"] == "barq2_ym"


def test_power_grid_and_vaccine_are_deductible_and_reversible(db, country):
    """حمله به شبکه برق و مرکز واکسن باید اثر واقعی داشته باشد."""
    from handlers.losses import match_strategic_resource

    for name in ("شبکه برق و پست‌های انتقال", "سوئیچ یارد", "پست انتقال",
                 "قطع برق سراسری کشور", "برق سراسری", "خاموشی سراسری"):
        match = match_strategic_resource(name)
        assert match and match["special"] == "electricity", name
    for name in ("ذخایر واکسن", "دز واکسن"):
        match = match_strategic_resource(name)
        assert match and match["special"] == "vaccine_doses", name

    # نیروگاه همچنان ساختمان است، نه شبکه برق
    for name in ("نیروگاه فسیلی", "نیروگاه هسته‌ای", "نیروگاه خورشیدی"):
        assert match_strategic_resource(name) is None, name

    cid = country["id"]
    db.update_country_field(cid, "electricity", 170)
    db.update_country_field(cid, "vaccine_doses", 250_000)

    ok, report_id, _err = db.create_loss_report(cid, [
        {"key": "__electricity__", "name": "شبکه برق", "special": "electricity", "unit": "واحد", "qty": 38},
        {"key": "__vaccine_doses__", "name": "ذخایر واکسن", "special": "vaccine_doses", "unit": "دُز", "qty": 60_000},
    ], operation_name="آزمون زیرساخت")
    assert ok

    after = db.get_country_by_id(cid)
    assert after["electricity"] == 132
    assert after["vaccine_doses"] == 190_000

    assert db.revert_loss_report(report_id)[0]
    restored = db.get_country_by_id(cid)
    assert restored["electricity"] == 170
    assert restored["vaccine_doses"] == 250_000


def test_power_grid_is_not_confused_with_a_barq_sam_battery(monkeypatch, tmp_path):
    """«شبکه برق» نباید با سامانه‌ی پدافند «برق-۲» یمن تطبیق بخورد.

    گزارش واقعی عملیات «الله مدینه» روی همین گیر کرد: زیرساخت برق کسر نمی‌شد و
    به‌جایش ۲۲ آتشبار برق-۲ (از ۱۰ موجود) خواسته می‌شد و کل گزارش رد می‌شد.
    """
    from handlers.losses import is_explicit_strategic, match_strategic_resource, match_asset_by_name

    assets = [
        {"equipment_key": "barq2", "equipment_name": "سامانه موشکی پدافند هوایی برق-۲ (Barq-2)",
         "category": "AirDefense", "amount": 10},
    ]
    name = "شبکه برق و پست‌های انتقال"

    assert is_explicit_strategic(name) is True
    assert match_strategic_resource(name)["special"] == "electricity"
    # بدون محافظ، تطبیق فازی تجهیزات این را می‌قاپید
    assert match_asset_by_name(name, assets) is not None
    # ولی نام صریح راهبردی باید مسیر تجهیزات را دور بزند
    assert is_explicit_strategic("سامانه موشکی پدافند هوایی برق-۲ (Barq-2)") is False


def test_explicit_strategic_phrases_cover_the_main_stockpiles():
    from handlers.losses import is_explicit_strategic

    for name in ("ذخایر نفت خام", "مخازن نفت", "ذخایر غلات", "ذخایر واکسن", "شمش طلا", "شبکه برق"):
        assert is_explicit_strategic(name), name
    for name in ("موشک بالستیک برکان-۳ (Borkan-3)", "پهپاد انتحاری قاصف-2K (Qasef-2K)", "F-15SA"):
        assert not is_explicit_strategic(name), name


def test_civilian_casualties_reduce_population_and_drop_approval_rating_if_50_plus(db, country):
    """تلفات غیرنظامی از جمعیت کشور کسر می‌شود و اگر ۵۰ نفر یا بیشتر باشد ۵٪ رضایت عمومی کم می‌شود."""
    cid = country["id"]
    db.update_country_field(cid, "population", 50_000_000)
    db.update_country_field(cid, "approval_rating", 80)

    # ۱. تلفات غیرنظامی بالای ۵۰ نفر (مثلاً ۱۲۰ نفر)
    ok, report_id, err = db.create_loss_report(cid, [
        {"key": "__personnel_civ__", "name": "غیرنظامیان (کشته)", "special": "civ_kia", "unit": "نفر", "qty": 120},
    ], operation_name="بمباران شهری")
    assert ok, err

    after = db.get_country_by_id(cid)
    assert after["population"] == 50_000_000 - 120
    assert after["approval_rating"] == 75  # ۵٪ کسر به خاطر ۵۰+ تلفات غیرنظامی

    # بازگردانی گزارش تلفات
    ok, err = db.revert_loss_report(report_id)
    assert ok, err

    restored = db.get_country_by_id(cid)
    assert restored["population"] == 50_000_000
    assert restored["approval_rating"] == 80


def test_civilian_casualties_under_50_reduces_population_without_approval_hit(db, country):
    """تلفات غیرنظامی زیر ۵۰ نفر از جمعیت کم می‌شود اما جریمه ۵٪ رضایت عمومی ندارد."""
    cid = country["id"]
    db.update_country_field(cid, "population", 50_000_000)
    db.update_country_field(cid, "approval_rating", 80)

    ok, report_id, err = db.create_loss_report(cid, [
        {"key": "__personnel_civ__", "name": "غیرنظامیان (کشته)", "special": "civ_kia", "unit": "نفر", "qty": 35},
    ], operation_name="حادثه مرزی")
    assert ok, err

    after = db.get_country_by_id(cid)
    assert after["population"] == 50_000_000 - 35
    assert after["approval_rating"] == 80  # بدون کسر رضایت چون زیر ۵۰ نفر است


def test_parse_loss_report_text_human_casualties_both_formats():
    """راستی‌آزمایی پارس شدن تلفات انسانی در هر دو قالب تک‌خطی و چندخطی."""
    from handlers.losses import parse_loss_report_text

    t_single = """📄 تلفات تجهیزات 🇨🇳 چین — عملیات «دیوار تاریکی اژدها»
━━━━━━━━━━━━━━━━━━
✈️ جنگنده‌ها
✈️ J-20 Stealth Fighter
تلفات: ۲ فروند
---
👥 تلفات انسانی
👤 نظامیان (کشته): ۳۴ نفر
👤 نظامیان (مجروح): ۱۱۵ نفر
👤 غیرنظامیان (کشته): ۲۸ نفر
"""
    res1 = parse_loss_report_text(t_single)
    assert res1["human"]["mil"] == 34
    assert res1["human"]["wounded"] == 115
    assert res1["human"]["civilians"] == 28

    t_multi = """📄 تلفات تجهیزات 🇨🇳 چین — عملیات «دیوار تاریکی اژدها»
━━━━━━━━━━━━━━━━━━
✈️ جنگنده‌ها
✈️ J-20 Stealth Fighter
تلفات: ۲ فروند
---
👥 تلفات انسانی
👤 نظامیان (کشته)
تلفات: ۳۴ نفر
---
👤 نظامیان (مجروح)
تلفات: ۱۱۵ نفر
---
👤 غیرنظامیان (کشته)
تلفات: ۲۸ نفر
---
"""
    res2 = parse_loss_report_text(t_multi)
    assert res2["human"]["mil"] == 34
    assert res2["human"]["wounded"] == 115
    assert res2["human"]["civilians"] == 28


