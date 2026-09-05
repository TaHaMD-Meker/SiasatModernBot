# -*- coding: utf-8 -*-
"""دکمه‌ی جبران خسارت ادمین: افزودن تجهیزات/منابع با متن آزاد.

قرارداد مالک: هر متنی بنویسی (فرمت لیست تجهیزات) باید «بجا» کم‌وثوب
اعمال شود — تطبیق با کاتالوگ واقعی کشور؛ نام‌های خارج از کاتالوگ به‌صورت
ردیف اختصاصی با دسته‌ی بخش ساخته می‌شوند؛ منابع (دلار/طلا/غلات/نفت/...)
به ستون‌های واقعی اضافه می‌شوند؛ هیچ‌وقت منفی نمی‌رود.
"""
import config
import database as db


CANADA_TEXT = """هواپیماها :

  • رادارگریز F-35A Lightning II: 15

  • سوخت‌رسان و ترابری CC-150 Polaris: 2

  • CF-188 Hornet: 30

پدافند :

  • ADATS: 3

  • NASAMS 3: 2

  • سامانه دفاع نزدیک توپخانه‌ای Phalanx Block 1B: 10

توپخانه :

  • سامانه موشکی و توپخانه‌ای دوگانه ADATS : 14

  • سامانه خمپاره‌انداز تاکتیکی بومی ۸۱ م‌م: 70

موشک :

موشک هواپایه AGM-65 Maverick: 200

  • موشک ضدزره هواپایه AGM-114 Hellfire: 400

پهپاد :

  • پهپاد شناسایی سنگین CU-170 Heron: 3

  • پهپاد بومی Microdrones MD4-1000: 100

نیروی زمینی :

  • سنگین بومی HLVW: 200

  • Leopard 2A6M CAN: 20

  • خودروی تاکتیکی سبک LUVW MilCOTS: 500



💵 15 میلیون دلار | 🪙 300 سکه طلا | 🌾 15٬000 تن غلات | 🛢️ 1٬000٬000 بشکه نفت
"""

CANADA_CATALOG = [
    {"key": "f35a_canada", "name": "رادارگریز F-35A Lightning II", "category": "Aircraft"},
    {"key": "cf188_hornet", "name": "CF-188 Hornet", "category": "Aircraft"},
    {"key": "adats", "name": "سامانه موشکی و توپخانه‌ای دوگانه ADATS", "category": "Air Defense"},
    {"key": "leopard2a6m_can", "name": "Leopard 2A6M CAN", "category": "Ground Forces"},
]


def _fresh(monkeypatch, tmp_path, name="grant.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


def _mk(name, flag, key):
    return db.create_country(8800 + abs(hash(key)) % 99999, name, flag, country_key=key)


def test_parse_canada_grant_text(monkeypatch):
    from handlers.admin import parse_inventory_grant_text
    r = parse_inventory_grant_text(CANADA_TEXT, CANADA_CATALOG)

    by_key = {it["key"]: it for it in r["items"]}
    # تطبیق با کاتالوگ
    assert by_key["f35a_canada"]["qty"] == 15
    assert by_key["cf188_hornet"]["qty"] == 30
    # ADATS دو بار (۳ پدافند + ۱۴ توپخانه) → جمع ۱۷
    assert by_key["adats"]["qty"] == 17, "اقلام تکراری باید جمع شوند"
    assert by_key["leopard2a6m_can"]["qty"] == 20
    # خارج از کاتالوگ → ردیف اختصاصی با دسته‌ی درست از سرصفحه
    customs = [it for it in r["items"] if it["key"].startswith("cx_")]
    assert len(customs) >= 8, f"باید آیتم اختصاصی ساخته شود: {customs}"
    polaris = next(it for it in customs if "polaris" in it["key"].lower())
    assert polaris["qty"] == 2 and polaris["category"] == "Aircraft"
    nasams = next(it for it in customs if "nasams" in it["key"].lower())
    assert nasams["category"] == "Air Defense"
    heron = next(it for it in customs if "heron" in it["key"].lower())
    assert heron["category"] == "UAV"
    hellfire = next(it for it in customs if "hellfire" in it["key"].lower())
    assert hellfire["category"] == "Missiles"
    luvw = next(it for it in customs if "luvw" in it["key"].lower())
    assert luvw["category"] == "Ground Forces" and luvw["qty"] == 500
    mortar = next(it for it in customs if "81" in it["name"] or "۸۱" in it["name"])
    assert mortar["category"] == "Artillery" and mortar["qty"] == 70

    # منابع
    res = r["resources"]
    assert res["treasury"] == 15_000_000, "«میلیون دلار» باید ×۱,۰۰۰,۰۰۰ شود"
    assert res["gold"] == 300
    assert res["grain"] == 15_000
    assert res["oil_reserves"] == 1_000_000
    assert not r["unmatched"], f"هیچ خطی نباید بی‌نتیجه بماند: {r['unmatched']}"


def test_admin_add_assets_applies_and_floors(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    cid = _mk("کانادا", "🇨🇦", "canada")
    items = [
        {"key": "f35a_canada", "name": "رادارگریز F-35A Lightning II", "category": "Aircraft", "qty": 15},
        {"key": "adats", "name": "ADATS", "category": "Air Defense", "qty": 17},
    ]
    resources = {"treasury": 15_000_000, "gold": 300, "grain": 15_000, "oil_reserves": 1_000_000}
    ok, err = db.admin_add_assets(cid, items, resources)
    assert ok and not err

    assets = {r["equipment_key"]: r for r in db.get_country_assets(cid)}
    assert assets["f35a_canada"]["amount"] == 15
    assert assets["f35a_canada"]["equipment_name"] == "رادارگریز F-35A Lightning II"
    assert assets["adats"]["amount"] == 17
    c = db.get_country_by_id(cid)
    assert c["treasury"] > 15_000_000, "دلتا باید به خزانه‌ی اولیه اضافه شود"
    assert c["gold"] >= 300 and c["grain"] >= 15_000 and c["oil_reserves"] >= 1_000_000, "دلتاها اعمال شوند"

    # افزودن مجدد (تجمیعی) + منفی تا کف صفر
    ok, err = db.admin_add_assets(cid, [
        {"key": "f35a_canada", "name": "F-35A", "category": "Aircraft", "qty": 5},
        {"key": "adats", "name": "ADATS", "category": "Air Defense", "qty": -50},
        {"key": "gold_something", "name": "X", "category": "Navy", "qty": -3},
    ], {"treasury": -99_000_000})
    assert ok
    assets = {r["equipment_key"]: r for r in db.get_country_assets(cid)}
    assert assets["f35a_canada"]["amount"] == 20, "افزودن دوم باید تجمیعی باشد"
    assert assets["adats"]["amount"] == 0, "منفی تا کف صفر، هرگز منفی نمی‌شود"
    assert db.get_country_by_id(cid)["treasury"] == 0, "خزانه هم کف صفر (دلتای منفی بزرگ)"
    # ردیف جدید با کسری صفر نباید ساخته شود
    assert "gold_something" not in assets


def test_addinv_continent_selector_plain(monkeypatch):
    from handlers.auto_ops import build_plain_continent_selector
    text, kb = build_plain_continent_selector("admin:addinv")
    labels = [btn.text for row in kb.inline_keyboard for btn in row
              if row[0].callback_data and ":cont:" in row[0].callback_data]
    assert labels
    for lab in labels:
        assert not any(ord(ch) > 0x2500 and not ch.isalnum() for ch in lab), f"ایموجی ممنوع: {lab}"


def test_continent_selector_accepts_extra_rows(monkeypatch):
    """بازگشت باید همان‌جا ساخته شود — tuple تغییرناپذیر PTB نباید append بخورد."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from handlers import auto_ops
    text, kb = auto_ops.build_plain_continent_selector(
        "admin:addinv", extra_rows=[[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:menu_war")]]
    )
    assert isinstance(kb, InlineKeyboardMarkup)
    last = kb.inline_keyboard[-1]
    assert last[0].callback_data == "admin:menu_war"
    # دکمه‌های قاره سالم مانده باشند
    assert any(":cont:" in r[0].callback_data for r in kb.inline_keyboard)
