"""مصرف سرانه‌ی نفت — پیشنهاد بازیکن: نفت باید واقعاً کمیاب باشد."""
import importlib
import config


def _fresh(monkeypatch, tmp_path, name="oil_pc.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    import database as db
    importlib.reload(db)
    db.init_db()
    return db


def test_consumption_is_linear_in_population():
    """دو برابر جمعیت باید دو برابر نفت بخواهد؛ فرمول قبلی زیرخطی بود."""
    a = config.population_oil_need(50_000_000, "iran")
    b = config.population_oil_need(100_000_000, "iran")
    assert b == 2 * a


def test_rate_differs_between_countries():
    """پیشنهاد بازیکن: مصرف سرانه باید در کشورهای مختلف فرق کند."""
    pop = 50_000_000
    gulf = config.population_oil_need(pop, "saudi")
    rich = config.population_oil_need(pop, "usa")
    dev = config.population_oil_need(pop, "germany")
    mid = config.population_oil_need(pop, "iran")
    poor = config.population_oil_need(pop, "india")
    assert gulf > rich > dev > mid > poor


def test_unknown_country_gets_the_default_rate():
    assert config.oil_per_capita_rate("atlantis") == config.OIL_PER_CAPITA_DEFAULT
    assert config.oil_per_capita_rate("") == config.OIL_PER_CAPITA_DEFAULT
    assert config.oil_per_capita_rate(None) == config.OIL_PER_CAPITA_DEFAULT


def test_no_country_appears_in_two_tiers():
    seen = set()
    for keys in config.OIL_PER_CAPITA_TIERS.values():
        dupes = seen & set(keys)
        assert not dupes, f"کشور در دو رده: {dupes}"
        seen |= set(keys)


def test_tiny_population_still_has_a_floor():
    assert config.population_oil_need(0, "iran") == 2_000
    assert config.population_oil_need(100, "iran") == 2_000


def test_demand_is_far_higher_than_the_old_sublinear_formula():
    """رگرسیون: اگر کسی فرمول را به pop^0.72 برگرداند این تست می‌افتد."""
    pop = 340_000_000
    old = max(2_000, int(((pop / 1e6) ** 0.72) * 10_000))
    new = config.population_oil_need(pop, "usa")
    assert new > old * 10


def test_world_market_is_tight_but_not_impossible(monkeypatch, tmp_path):
    """عرضه باید کمی بیشتر از تقاضا باشد: کمیاب ولی قابل زندگی."""
    db = _fresh(monkeypatch, tmp_path, "oil_world.db")
    import approval_system as ap
    importlib.reload(ap)
    for i, (k, m) in enumerate(config.COUNTRIES.items()):
        db.create_country(810000 + i, m["name"], m.get("flag", "🏳️"), country_key=k)

    need = prod = 0
    for c in db.get_all_countries():
        need += ap.calculate_country_requirements(c)["oil_need_daily"]
        prod += int(c["oil_production"] or 0)

    ratio = prod / need
    assert 1.0 < ratio < 1.6, f"نسبت عرضه به تقاضا {ratio:.2f} خارج از بازه‌ی سالم است"


def test_requirements_use_the_new_per_capita_path(monkeypatch, tmp_path):
    db = _fresh(monkeypatch, tmp_path, "oil_req.db")
    import approval_system as ap
    importlib.reload(ap)
    cid = db.create_country(8101, "آمریکا", "🇺🇸", country_key="usa")
    c = db.get_country_by_id(cid)
    reqs = ap.calculate_country_requirements(c)
    assert reqs["pop_oil_need"] == config.population_oil_need(c["population"], "usa")
    assert reqs["pop_oil_need"] > 5_000_000


# ─────────── انبار روسیه: ترابری و سوخت‌رسان ───────────

def test_russia_has_transport_and_tanker_aircraft():
    """پیشنهاد بازیکن: روسیه ترابری و سوخت‌رسان نداشت."""
    names = [i["name"] for i in config.COUNTRY_EQUIPMENT_CATALOG["russia"]]
    assert any("ترابری" in n for n in names), "روسیه هواپیمای ترابری ندارد"
    assert any("سوخت‌رسان" in n for n in names), "روسیه سوخت‌رسان هوایی ندارد"


def test_russia_transport_keys_are_unique():
    keys = [i["key"] for i in config.COUNTRY_EQUIPMENT_CATALOG["russia"]]
    assert len(keys) == len(set(keys)), "کلید تکراری در انبار روسیه"
