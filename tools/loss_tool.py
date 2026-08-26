#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ابزار کمکی ساخت و اعتبارسنجی گزارش تلفات.

حالت پیش‌فرض روی یک دیتابیس موقتِ ساخته‌شده از config کار می‌کند و هیچ‌وقت
به دیتابیس واقعی بازی دست نمی‌زند. با گزینه‌ی ``--live``، ابتدا از دیتابیس
واقعی یک snapshot خواندنی در فایل موقت ساخته می‌شود؛ بنابراین حتی دستور
``check`` هم روی دیتابیس اصلی اعمالی انجام نمی‌دهد.

دستورها
-------
  python tools/loss_tool.py countries
      فهرست کلید و نام همه‌ی کشورهای بازی

  python tools/loss_tool.py list <country_key> [--live] [--db PATH] [--cat CATEGORY]
      انبار کشور؛ در حالت live موجودی فعلی snapshot خواندنی را نشان می‌دهد

  python tools/loss_tool.py find <country_key> <عبارت> [--live] [--db PATH]
      جستجوی یک تجهیز در انبار کشور

  python tools/loss_tool.py check <country_key> <report.txt> [--live] [--db PATH]
      شبیه‌سازی کامل گزارش بدون تغییر دیتابیس اصلی

  python tools/loss_tool.py export <country_key> [--live] [--db PATH]
      خروجی انبار برای دادن به مدل تولیدکننده‌ی گزارش

در حالت ``--live``، ``--db`` مسیر دیتابیس بازی است؛ اگر داده نشود از
``config.DB_PATH`` استفاده می‌شود. منبع اصلی فقط با SQLite در حالت read-only
خوانده و در یک فایل موقت کپی می‌شود.
"""

import argparse
import os
import shutil
import sqlite3
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402


def _snapshot_live_database(source_path: str) -> tuple[str, str]:
    """کپی خواندنی از دیتابیس بازی بساز و مسیر پوشه/فایل موقت را برگردان."""
    source = Path(source_path).expanduser().resolve()
    if not source.is_file():
        sys.exit(f"❌ دیتابیس live پیدا نشد: {source}")

    tmp = tempfile.mkdtemp(prefix="losstool_live_")
    scratch = os.path.join(tmp, "scratch.db")
    source_conn = destination_conn = None
    try:
        # URI mode=ro جلوی هرگونه نوشتن روی فایل اصلی را می‌گیرد.
        source_conn = sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True)
        destination_conn = sqlite3.connect(scratch)
        source_conn.backup(destination_conn)
        destination_conn.commit()
    except sqlite3.Error as exc:
        shutil.rmtree(tmp, ignore_errors=True)
        sys.exit(f"❌ ساخت snapshot از دیتابیس live ناموفق بود: {exc}")
    finally:
        if source_conn is not None:
            source_conn.close()
        if destination_conn is not None:
            destination_conn.close()
    return tmp, scratch


def _boot(country_key=None, live_db_path=None):
    """دیتابیس موقت را راه‌اندازی کن؛ در حالت live ابتدا snapshot بگیر."""
    if live_db_path:
        _tmp, scratch = _snapshot_live_database(live_db_path)
        config.DB_PATH = scratch
    else:
        tmp = tempfile.mkdtemp(prefix="losstool_")
        config.DB_PATH = os.path.join(tmp, "scratch.db")

    import database as db
    # init_db فقط روی scratch اجرا می‌شود؛ هیچ migration یا seed روی live انجام نمی‌شود.
    db.init_db()

    if country_key:
        if live_db_path:
            country = db.get_country_by_key(country_key)
            if not country:
                sys.exit(f"❌ کشور «{country_key}» در دیتابیس live وجود ندارد.")
            return db, country

        meta = config.COUNTRIES.get(country_key)
        if not meta:
            sys.exit(f"❌ کشور «{country_key}» در بازی وجود ندارد. "
                     f"برای دیدن فهرست: python tools/loss_tool.py countries")
        name = meta.get("name", country_key)
        flag = meta.get("flag", "🏳️")
        # نام کشورها در config گاهی ایموجی پرچم را داخل خودش دارد
        if flag and flag in name:
            name = name.replace(flag, "").strip()
        db.create_country(999_000, name, flag, country_key=country_key)
        return db, db.get_all_countries()[0]

    return db, None


def _live_path_from_args(args):
    """اگر کاربر live خواسته، مسیر منبع آن را تعیین کن."""
    explicit_path = getattr(args, "db", None)
    if explicit_path:
        return explicit_path
    if getattr(args, "live", False):
        return config.DB_PATH
    return None


def _add_database_options(parser):
    parser.add_argument(
        "--live",
        action="store_true",
        help="خواندن موجودی فعلی از snapshot خواندنی دیتابیس بازی",
    )
    parser.add_argument(
        "--db",
        metavar="PATH",
        help="مسیر دیتابیس live؛ وجود این گزینه خودش حالت live را فعال می‌کند",
    )


def cmd_countries(args):
    rows = []
    for key, meta in config.COUNTRIES.items():
        rows.append((key, f"{meta.get('flag', '')} {meta.get('name', key)}".strip()))
    rows.sort()
    print(f"🌍 {len(rows)} کشور در بازی:\n")
    for key, label in rows:
        print(f"  {key:<22} {label}")


def cmd_list(args):
    db, c = _boot(args.country_key, _live_path_from_args(args))
    assets = db.get_country_assets(c["id"])

    print(f"{c['flag']} {c['name']}")
    print(f"خزانه {c['treasury']:,} | پرسنل فعال {c['active_personnel']:,} | "
          f"نفت {c['oil_reserves']:,} | کلاهک {c['warheads']}")
    print("=" * 68)

    by_cat = defaultdict(list)
    for a in assets:
        by_cat[a["category"]].append(a)

    for cat, items in by_cat.items():
        if args.cat and args.cat.lower() not in cat.lower():
            continue
        label, unit = config.ASSET_CATEGORIES.get(cat, (cat, "عدد"))
        print(f"\n--- {label}  ({len(items)} قلم، واحد: {unit}) ---")
        for it in sorted(items, key=lambda x: -x["amount"]):
            print(f"   {it['equipment_name']:<52} × {it['amount']:,}")

    owned = {k: v for k, v in (db.get_equipment(c["id"]) or {}).items() if v}
    if owned:
        print("\n--- 🏗️ زیرساخت و صنایع ---")
        for k, v in owned.items():
            nm = config.ALL_SHOP_ITEMS.get(k, {}).get("name", k)
            print(f"   {nm:<52} × {v}")


def cmd_find(args):
    db, c = _boot(args.country_key, _live_path_from_args(args))
    from handlers.losses import match_asset_by_name, _clean_str

    assets = db.get_country_assets(c["id"])
    q = _clean_str(args.query)

    print(f"🔎 جستجوی «{args.query}» در انبار {c['flag']} {c['name']}\n")

    hits = [a for a in assets if q in _clean_str(a["equipment_name"])]
    if hits:
        print("— شامل عبارت:")
        for a in hits:
            print(f"   ✔ {a['equipment_name']:<52} × {a['amount']:,}")

    m = match_asset_by_name(args.query, assets)
    if m:
        print(f"\n— آنچه بات تطبیق می‌دهد: {m['equipment_name']}  (موجودی {m['amount']:,})")
    else:
        print("\n— آنچه بات تطبیق می‌دهد: ❌ هیچ‌کدام")


def cmd_check(args):
    db, c = _boot(args.country_key, _live_path_from_args(args))
    cid = c["id"]

    # شبیه‌سازی مالکیت ساختمان‌ها (--own oil_refinery:3)
    for spec in getattr(args, "own", []) or []:
        key, _, qty = spec.partition(":")
        key, qty = key.strip(), int(qty or 1)
        if key not in config.ALL_SHOP_ITEMS:
            sys.exit(f"❌ کلید ساختمان «{key}» در فروشگاه نیست.")
        _conn = db.get_connection()
        _conn.execute(
            "INSERT INTO equipment (country_id, item_key, quantity) VALUES (?,?,?)"
            " ON CONFLICT(country_id, item_key) DO UPDATE SET quantity = excluded.quantity",
            (cid, key, qty))
        _conn.commit()
        _conn.close()
        print(f"🏗️  شبیه‌سازی مالکیت: {config.ALL_SHOP_ITEMS[key].get('name', key)} × {qty}")

    from handlers.losses import (parse_loss_report_text, match_country_by_name,
                                 match_asset_by_name, match_strategic_resource,
                                 match_building, classify_subcat, build_loss_report_text,
                                 _UNIT_BY_CATEGORY, _split_emoji, _clean_str, match_commander)

    text = open(args.report, encoding="utf-8").read()
    p = parse_loss_report_text(text)

    print("=" * 68)
    print(f"کشور در متن : {p['country']!r}")
    matched_country = match_country_by_name(p["country"])
    if matched_country:
        same = matched_country["id"] == cid
        print(f"تطبیق کشور : {matched_country['flag']} {matched_country['name']} "
              f"{'✅' if same else '⚠️ با کشور انتخابی فرق دارد!'}")
    else:
        print("تطبیق کشور : ❌ شناسایی نشد — بات گزارش را رد می‌کند")
    print(f"عملیات      : «{p['op']}»")
    print(f"اقلام متن   : {len(p['items'])}")
    print("=" * 68)

    assets = db.get_country_assets(cid)
    matched, unmatched, over = [], [], []

    for name, qty, unit in p["items"]:
        a = match_asset_by_name(name, assets)
        if a:
            sub, emo = classify_subcat(a)
            stock = a["amount"]
            flag = "✅"
            if qty > stock:
                flag = "🛑"
                over.append((a["equipment_name"], qty, stock))
            pct = (qty / stock * 100) if stock else 0
            print(f"{flag} {name[:44]:<46} → {a['equipment_name'][:34]:<36} "
                  f"{qty:>6,}/{stock:<7,} ({pct:4.1f}%)")
            matched.append({"key": a["equipment_key"], "name": a["equipment_name"],
                            "category": a["category"], "subcat": sub, "emoji": emo,
                            "unit": _UNIT_BY_CATEGORY.get(a["category"], "عدد"), "qty": qty})
            continue

        r = match_strategic_resource(name)
        if r:
            r["qty"] = qty
            print(f"☢️  {name[:44]:<46} → منبع راهبردی ({r['name']})")
            matched.append(r)
            continue

        # تطبیق با سران و فرماندهان نظامی
        cmd_list = db.get_country_commanders(cid)
        _taken = {m.get("cmd_key") for m in matched if m.get("special") == "commander"}
        cmd_match = match_commander(name, [c for c in cmd_list if c["key"] not in _taken])
        if cmd_match:
            print(f"🎖️  {name[:44]:<46} → {cmd_match['title']} (ترور / شهید)")
            matched.append({"key": f"__cmd_{cmd_match['key']}__", "name": f"{cmd_match['title']} (ترور / شهید)",
                            "special": "commander", "cmd_key": cmd_match["key"],
                            "category": "Command", "subcat": "سران نظامی", "emoji": "🎖️", "unit": "نفر", "qty": qty})
            continue

        b = match_building(name, cid)
        if b:
            bn, be = _split_emoji(b["name"], "🏗️")
            print(f"🏗️  {name[:44]:<46} → {bn}")
            matched.append({"key": b["key"], "name": bn, "special": "building",
                            "category": "Infrastructure", "subcat": "ساخت‌سازی",
                            "emoji": be, "unit": "واحد", "qty": qty})
            continue

        unmatched.append(name)
        print(f"❌ {name[:44]:<46} → در انبار این کشور نیست (نادیده گرفته می‌شود)")

    h = p["human"]
    for k, sp, nm, em in [("mil", "mil_kia", "نیروهای نظامی (کشته)", "🪖"),
                          ("wounded", "wounded", "مجروحان", "🏥"),
                          ("civilians", "civ_kia", "غیرنظامیان (کشته)", "👤")]:
        if h.get(k):
            matched.append({"key": f"__{sp}__", "name": nm, "special": sp,
                            "category": "Personnel", "subcat": "تلفات انسانی",
                            "emoji": em, "unit": "نفر", "qty": h[k]})
    for key, sp, nm, em, un, v in [("__cost_money__", "money", "هزینه آماده‌سازی (خزانه)", "💵", "دلار", p["costs"]["money"]),
                                   ("__cost_oil__", "oil", "سوخت و لجستیک (نفت)", "🛢️", "بشکه", p["costs"]["oil"])]:
        if v:
            matched.append({"key": key, "name": nm, "special": sp, "category": "Cost",
                            "subcat": "هزینه عملیات", "emoji": em, "unit": un, "qty": v})

    print("-" * 68)
    print(f"👥 تلفات انسانی : {h['mil']:,} کشته | {h['wounded']:,} مجروح | {h['civilians']:,} غیرنظامی")
    if h["mil"]:
        ratio = h["wounded"] / h["mil"] if h["mil"] else 0
        note = "✅ واقع‌گرایانه" if 2.0 <= ratio <= 4.0 else "⚠️ نسبت مجروح/کشته غیرعادی (بازه‌ی طبیعی ۲ تا ۴)"
        print(f"   نسبت مجروح به کشته: {ratio:.1f} به ۱  {note}")
    print(f"💸 هزینه        : {p['costs']['money']:,} دلار | {p['costs']['oil']:,} بشکه")

    # اعتبارسنجی منابع
    print("-" * 68)
    problems = []
    if p["costs"]["money"] > c["treasury"]:
        problems.append(f"هزینه مالی {p['costs']['money']:,} > خزانه {c['treasury']:,}")
    if p["costs"]["oil"] > c["oil_reserves"]:
        problems.append(f"سوخت {p['costs']['oil']:,} > ذخایر نفت {c['oil_reserves']:,}")
    if h["mil"] > c["active_personnel"]:
        problems.append(f"تلفات نظامی {h['mil']:,} > پرسنل {c['active_personnel']:,}")
    for nm, q, st in over:
        problems.append(f"«{nm}» تلفات {q:,} > موجودی {st:,}")

    if problems:
        print("🛑 گزارش رد می‌شود — بات هیچ چیزی را اعمال نمی‌کند:")
        for x in problems:
            print(f"     • {x}")
    else:
        ok, rid, err = db.create_loss_report(cid, matched, p["op"], "", 1)
        if not ok:
            print(f"🛑 ثبت شکست خورد: {err}")
        else:
            af = db.get_country_by_id(cid)
            print("✅ گزارش سالم است و با موفقیت اعمال می‌شود.")
            print(f"     خزانه  {c['treasury']:,} → {af['treasury']:,}")
            print(f"     نفت    {c['oil_reserves']:,} → {af['oil_reserves']:,}")
            print(f"     پرسنل  {c['active_personnel']:,} → {af['active_personnel']:,}")
            if af["daily_income"] != c["daily_income"]:
                print(f"     درآمد روزانه {c['daily_income']:,} → {af['daily_income']:,}")

    if unmatched:
        print(f"\n⚠️  {len(unmatched)} قلم ناشناخته (در گزارش می‌ماند ولی کسر نمی‌شود):")
        for n in unmatched:
            print(f"     • {n}")

    if args.render:
        print("\n" + "=" * 68)
        print("پیش‌نمایش فاکتوری که بازیکن دریافت می‌کند:")
        print("=" * 68)
        print(build_loss_report_text(c["flag"], c["name"], p["op"], matched))


def cmd_export(args):
    """خروجی فشرده‌ی انبار، آماده‌ی پیست در پرامپت یک هوش مصنوعی دیگر."""
    db, c = _boot(args.country_key, _live_path_from_args(args))
    assets = db.get_country_assets(c["id"])

    by_cat = defaultdict(list)
    for a in assets:
        by_cat[a["category"]].append(a)

    print(f"### انبار {c['flag']} {c['name']}")
    print(f"خزانه: {c['treasury']:,} دلار | پرسنل فعال: {c['active_personnel']:,} نفر | "
          f"ذخایر نفت: {c['oil_reserves']:,} بشکه | کلاهک هسته‌ای: {c['warheads']}")
    print()

    for cat, items in by_cat.items():
        label, unit = config.ASSET_CATEGORIES.get(cat, (cat, "عدد"))
        print(f"**{label}** (واحد: {unit})")
        for it in sorted(items, key=lambda x: -x["amount"]):
            print(f"- {it['equipment_name']} = {it['amount']:,}")
        print()

    owned = {k: v for k, v in (db.get_equipment(c["id"]) or {}).items() if v}
    if owned:
        print("**زیرساخت و صنایع** (واحد: واحد)")
        for k, v in owned.items():
            nm = config.ALL_SHOP_ITEMS.get(k, {}).get("name", k)
            print(f"- {nm} = {v}")
        print()


def main():
    ap = argparse.ArgumentParser(description="ابزار ساخت و بررسی گزارش تلفات")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("countries", help="فهرست کشورهای بازی")

    pl = sub.add_parser("list", help="انبار کامل یک کشور")
    pl.add_argument("country_key")
    pl.add_argument("--cat", help="فیلتر دسته (Aircraft, Navy, ...)")
    _add_database_options(pl)

    pf = sub.add_parser("find", help="جستجوی تجهیز در انبار کشور")
    pf.add_argument("country_key")
    pf.add_argument("query")
    _add_database_options(pf)

    pc = sub.add_parser("check", help="شبیه‌سازی و اعتبارسنجی یک گزارش")
    pc.add_argument("country_key")
    pc.add_argument("report")
    pc.add_argument("--render", action="store_true", help="نمایش فاکتور نهایی")
    pc.add_argument("--own", metavar="KEY:QTY", action="append", default=[],
                    help="شبیه‌سازی مالکیت ساختمان، مثلاً --own oil_refinery:3 "
                         "(چون کشورهای تازه هیچ ساختمانی ندارند و زیرساخت تطبیق نمی‌خورد)")
    _add_database_options(pc)

    pe = sub.add_parser("export", help="انبار به‌صورت آماده‌ی پیست در پرامپت هوش مصنوعی")
    pe.add_argument("country_key")
    _add_database_options(pe)

    args = ap.parse_args()
    {"countries": cmd_countries, "list": cmd_list, "find": cmd_find,
     "check": cmd_check, "export": cmd_export}[args.cmd](args)


if __name__ == "__main__":
    main()
