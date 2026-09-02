"""ابزارهای داوری: خروجی انبار و اعتبارسنجی گزارش تلفات."""
import importlib
import config


def _fresh(monkeypatch, tmp_path, name="ref.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    import database as db
    importlib.reload(db)
    db.init_db()
    return db


# ─────────────── خروجی انبار ───────────────

def test_export_contains_header_stock_and_units(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path)
    cid = db.create_country(1, "ایران", "🇮🇷", country_key="iran")
    txt = db.export_country_inventory_text(cid)
    assert "### انبار" in txt and "ایران" in txt
    assert "خزانه:" in txt and "پرسنل فعال:" in txt
    assert "(واحد:" in txt
    assert "S-300PMU-2 = 10" in txt


def test_export_lists_commanders_for_the_referee(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ref2.db")
    cid = db.create_country(1, "ایران", "🇮🇷", country_key="iran")
    txt = db.export_country_inventory_text(cid)
    assert "رده فرماندهی" in txt


def test_export_skips_zero_stock_items(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ref3.db")
    cid = db.create_country(1, "ایران", "🇮🇷", country_key="iran")
    conn = db.get_connection()
    with conn:
        conn.execute("UPDATE country_assets SET amount = 0 WHERE equipment_key ="
                     " (SELECT equipment_key FROM country_assets WHERE country_id = ? LIMIT 1)", (cid,))
    conn.close()
    assert " = 0\n" not in db.export_country_inventory_text(cid)


def test_export_of_missing_country_is_empty(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ref4.db")
    assert db.export_country_inventory_text(99999) == ""


# ─────────────── اعتبارسنجی ───────────────

_GOOD = """📄 تلفات تجهیزات 🇮🇷 ایران — عملیات تست
━━━━━━━━━━━━━━━━━━

🚀 موشک قدر
تلفات: 18 فروند

👥 تلفات انسانی

🪖 نظامیان کشته: 100 نفر
🏥 مجروحان: 270 نفر
👤 غیرنظامیان کشته: 12 نفر
"""


def test_valid_report_passes(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ref5.db")
    db.create_country(1, "ایران", "🇮🇷", country_key="iran")
    v = db.validate_loss_report_text(_GOOD)
    assert v["ok"] is True and not v["errors"]
    assert v["items"] == 1
    assert "ایران" in v["country"]


def test_unknown_country_name_is_rejected(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ref6.db")
    db.create_country(1, "انگلیس", "🇬🇧", country_key="uk")
    v = db.validate_loss_report_text(_GOOD.replace("🇮🇷 ایران", "🇬🇧 بریتانیا"))
    assert not v["ok"]
    assert any("شناسایی نشد" in e for e in v["errors"])


def test_over_stock_deduction_is_caught(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ref7.db")
    db.create_country(1, "ایران", "🇮🇷", country_key="iran")
    v = db.validate_loss_report_text(_GOOD.replace("تلفات: 18 فروند", "تلفات: 5000 فروند"))
    assert not v["ok"]
    assert any("موجودی" in e for e in v["errors"])


def test_unknown_equipment_is_caught(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ref8.db")
    db.create_country(1, "ایران", "🇮🇷", country_key="iran")
    v = db.validate_loss_report_text(_GOOD.replace("موشک قدر", "موشک اژدهای بنفش"))
    assert not v["ok"]
    assert any("پیدا نشد" in e for e in v["errors"])


def test_bad_wounded_ratio_warns_but_does_not_block(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ref9.db")
    db.create_country(1, "ایران", "🇮🇷", country_key="iran")
    v = db.validate_loss_report_text(_GOOD.replace("مجروحان: 270", "مجروحان: 120"))
    assert v["ok"] is True, "نسبت بد فقط هشدار است نه خطا"
    assert any("نسبت" in w for w in v["warnings"])


def test_too_many_civilians_warns(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ref10.db")
    db.create_country(1, "ایران", "🇮🇷", country_key="iran")
    v = db.validate_loss_report_text(_GOOD.replace("غیرنظامیان کشته: 12", "غیرنظامیان کشته: 400"))
    assert any("غیرنظامی" in w for w in v["warnings"])


def test_strategic_resources_are_recognised(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ref11.db")
    db.create_country(1, "ایران", "🇮🇷", country_key="iran")
    txt = _GOOD.replace("👥 تلفات انسانی", "☢️ ذخایر نفت\nتلفات: 100000 بشکه\n\n👥 تلفات انسانی")
    v = db.validate_loss_report_text(txt)
    assert v["ok"] is True
    assert any("منبع راهبردی" in i for i in v["info"])


def test_formatter_marks_healthy_and_broken_reports(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ref12.db")
    db.create_country(1, "ایران", "🇮🇷", country_key="iran")
    ok_txt = db.format_validation_report(db.validate_loss_report_text(_GOOD))
    bad_txt = db.format_validation_report(
        db.validate_loss_report_text(_GOOD.replace("تلفات: 18", "تلفات: 5000")))
    assert "سالم است" in ok_txt
    assert "ایراد دارد" in bad_txt


def test_garbage_text_does_not_crash(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "ref13.db")
    for junk in ("", "سلام", "📄 تلفات تجهیزات", "\n\n\n"):
        v = db.validate_loss_report_text(junk)
        assert isinstance(v, dict) and v["ok"] is False
        assert isinstance(db.format_validation_report(v), str)


def test_admin_panel_wires_both_buttons():
    with open("handlers/admin.py", encoding="utf-8") as f:
        admin = f.read()
    with open("handlers/admin_dossier.py", encoding="utf-8") as f:
        dossier = f.read()
    assert "admin:c_export:" in dossier, "دکمه خروجی انبار در پرونده کشور نیست"
    assert "admin:c_export:" in admin, "هندلر خروجی انبار نیست"
    assert "admin:validate" in admin, "دکمه اعتبارسنجی نیست"
    assert "validate_report" in admin, "دریافت متن گزارش وصل نشده"
