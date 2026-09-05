# -*- coding: utf-8 -*-
"""درخواست مالک: گزارش روزانه باید «چرایی» خاموشی سازه‌ها را توضیح بدهد.

قبلاً فقط می‌گفت «کمبود منابع — N سازه از کار افتاد»؛ الان باید بگوید:
• چرا این سازه؟ (کم‌بازده‌ترین مصرف‌کننده‌ی منبع کسری — اول او خاموش می‌شود)
• این سازه روزانه چقدر از چه منابعی می‌خورد؟
• انبار چقدر بود و کل نیاز روزانه چقدر؟
• برای روشن‌ماندن همه دقیقاً چقدر منبع بیشتر لازم است؟
و چون این بلوک داخل پیامِ Markdown گزارش روزانه تزریق می‌شود، خروجی باید
Markdown باشد — نه تگ‌های HTML خام (<b>) که عیناً نمایش داده می‌شدند.
"""
import config
import database as db


def _fresh(monkeypatch, tmp_path, name="upkeep_why.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()
    cid = db.create_country(7001, "مالزی", "🇲🇾", country_key="malaysia")
    db.update_country_field(cid, "treasury", 50_000_000)
    db.update_country_field(cid, "iron_ore", 10)  # عمداً ناچیز → کسری آهن
    conn = db.get_connection()
    with conn:
        conn.execute("INSERT INTO equipment (country_id, item_key, quantity) VALUES (?,?,1)",
                     (cid, "industrial_complex"))
    conn.close()
    return cid


def test_shutdown_report_explains_why_in_markdown(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    res = db.apply_building_upkeep(db.get_country_by_player(7001)["id"])
    assert res["shut_down"], "با آهن ۱۰ واحدی باید سازه خاموش می‌شد"

    text = db.format_upkeep_report(res)

    # ۱) بدون تگ HTML خام — بلوک داخل پیام Markdown می‌رود
    assert "<b>" not in text and "</b>" not in text and "<i>" not in text, \
        "تگ‌های HTML خام در پیام Markdown عیناً نمایش داده می‌شوند"
    assert "**" in text or "*" in text, "تأکید باید Markdown باشد"

    # ۲) چرایی: علت، انتخاب کم‌بازده، مصرف روزانه‌ی سازه
    assert "چرا" in text, "باید بخش «چرا؟» داشته باشد"
    assert "کم‌بازده" in text, "باید بگوید چرا این سازه انتخاب شد"
    assert "مصرف روزانه" in text, "باید مصرف روزانه‌ی سازه‌ی خاموش‌شده را بگوید"
    assert "روشن بمانند" in text, "منطق قاعده باید توضیح داده شود"

    # ۳) انبار/نیاز + دقیقاً چقدر بیشتر لازم است
    assert "نیاز روزانه" in text, "باید نیاز روزانه‌ی کل سازه‌ها را نشان بدهد"
    assert "برای روشن‌ماندن همه" in text, "باید دوز لازم برای رفع کسری را بگوید"

    # ۴) داده‌های خام هم برای متن بالا موجودند
    sd = res["shut_down"][0]
    assert sd.get("consumption"), "مصرف روزانه‌ی هر واحد باید در نتیجه باشد"
    assert sd.get("consumption").get("iron_ore", 0) > 0
    assert res.get("supply_line", {}).get("iron_ore", {}).get("need", 0) > 0


def test_reason_names_scarce_resource(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "upkeep_why2.db")
    res = db.apply_building_upkeep(db.get_country_by_player(7001)["id"])
    text = db.format_upkeep_report(res)
    assert "آهن و فولاد" in text, "نام منبع کسری باید صریح بیاید"
