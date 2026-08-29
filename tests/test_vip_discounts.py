# -*- coding: utf-8 -*-
"""تخفیف فروشگاه ویژه: اعمال درصد روی قیمت آیتم‌ها و نمایش در فروشگاه.

خواسته‌ی کارفرما: ادمین در پنل، کنار هر آیتم دکمه‌ی «تخفیف» با درصدهای
۱۰/۲۰/۳۰/۴۰/۵۰ داشته باشد؛ با زدن، تخفیف خودکار روی قیمت اعمال و در فروشگاه
روی دکمه‌ی آیتم‌ها هم نمایش داده شود.
"""

import config
import database as db
import handlers.vip as vip


def _fresh(monkeypatch, tmp_path, name="vipdisc.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()


# ─────────────────────────────────────────────────────────────────────────────
# موتور تخفیف
# ─────────────────────────────────────────────────────────────────────────────

def test_no_discount_means_base_price(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert vip.effective_price("vip_bronze") == 79_000
    assert vip.discount_of("vip_bronze") == 0


def test_setting_discount_changes_effective_price(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    db.set_vip_discount("vip_bronze", 10)
    assert vip.discount_of("vip_bronze") == 10
    assert vip.effective_price("vip_bronze") == 71_100  # ۷۹٬۰۰۰ با ۱۰٪

    db.set_vip_discount("vip_diamond", 50)
    assert vip.effective_price("vip_diamond") == 325_000  # ۶۵۰٬۰۰۰ با ۵۰٪


def test_clearing_discount_restores_base_price(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    db.set_vip_discount("survival_medium", 20)
    assert vip.effective_price("survival_medium") == 199_200
    db.set_vip_discount("survival_medium", 0)
    assert vip.effective_price("survival_medium") == 249_000
    assert vip.discount_of("survival_medium") == 0


def test_unknown_key_survives(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert vip.effective_price("does_not_exist") == 0
    assert vip.discount_of("does_not_exist") == 0


# ─────────────────────────────────────────────────────────────────────────────
# نمایش در فروشگاه
# ─────────────────────────────────────────────────────────────────────────────

def test_price_labels_show_discount(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert vip.price_label("vip_gold") == "۳۴۹٬۰۰۰ تومان"
    db.set_vip_discount("vip_gold", 30)
    label = vip.price_label("vip_gold")
    assert "۲۴۴٬۳۰۰" in label and "۳۰٪" in label
    short = vip.price_label("vip_gold", short=True)
    assert "۲۴۴٬۳۰۰ ت" in short and "۳۰٪" in short
    k = vip.price_short_k("bp_booster_3d")  # ۱۲۹k بدون تخفیف
    assert k == "۱۲۹k"
    db.set_vip_discount("bp_booster_3d", 10)
    assert vip.price_short_k("bp_booster_3d") == "۱۱۶k (۱۰٪-)"


def test_checkout_uses_discounted_price(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    db.set_vip_discount("vip_silver", 20)
    assert vip.price_note("vip_silver") != ""
    assert "۲۰٪" in vip.price_note("vip_silver")
    # فاکتور و فیش از تابع قیمت پویا استفاده می‌کنند
    import inspect
    source = inspect.getsource(vip.vip_checkout_screen) + inspect.getsource(vip.vip_input_handler)
    assert "effective_price(plan_key)" in source
    assert "price_note(plan_key)" in source
    assert "amount_toman=effective_price(plan_key)" in source


def test_store_menus_render_dynamic_prices(monkeypatch, tmp_path):
    """منوهای فروشگاه باید قیمت را از تابع پویا بخوانند، نه hardcode."""
    import inspect
    source = (
        inspect.getsource(vip.vip_passes_menu)
        + inspect.getsource(vip.survival_packs_menu)
        + inspect.getsource(vip.visibility_services_menu)
    )
    assert "price_label(" in source
    assert "price_short_k(" in source
    # هیچ قیمت hardcode‌ی «۷۹,۰۰۰» در دکمه‌ها نباید مانده باشد
    assert "اشتراک برنز — ۷۹,۰۰۰ تومان" not in source
    assert "۱۲۹k\"" not in source


# ─────────────────────────────────────────────────────────────────────────────
# پنل ادمین
# ─────────────────────────────────────────────────────────────────────────────

def test_admin_router_and_button_exist():
    import inspect
    from handlers import admin
    source = inspect.getsource(admin)
    assert "admin:vip_price" in source
    assert "vip_admin_callback" in source
    assert "🛒 قیمت و تخفیف فروشگاه ویژه" in source

    from handlers.vip_admin import vip_admin_callback, MANAGEABLE_KEYS
    assert "vip_bronze" in MANAGEABLE_KEYS
    assert "frame_30d" in MANAGEABLE_KEYS
    assert len(MANAGEABLE_KEYS) >= 25


def test_discount_survives_restart(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "vipdisc_persist.db")
    db.set_vip_discount("vip_bronze", 10)
    # شبیه‌سازی اتصال جدید — خواندن دوباره از دیتابیس
    assert vip.effective_price("vip_bronze") == 71_100
    assert db.get_all_vip_discounts().get("vip_bronze") == 10
