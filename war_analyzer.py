# -*- coding: utf-8 -*-
"""
ماژول تحلیل هوشمند سناریوی نبرد و محاسبه تلفات (AI War Analysis Module v2.1)
قالب‌بندی رسمی، سنگین و بدون ایموجی‌های اضافی در متن گزارش‌ها.
"""

import os
import random
import json
import urllib.request
import database as db
import config

NON_CONTIGUOUS_PAIRS = {
    ("iran", "israel"), ("israel", "iran"),
    ("usa", "russia"), ("russia", "usa"),
    ("usa", "iran"), ("iran", "usa"),
    ("usa", "china"), ("china", "usa"),
    ("uk", "iran"), ("iran", "uk"),
    ("france", "iran"), ("iran", "france"),
    ("qatar", "israel"), ("israel", "qatar"),
    ("saudi", "israel"), ("israel", "saudi"),
    ("usa", "israel"), ("israel", "usa"),
}

def detect_operation_type(attacker_key: str, defender_key: str, attacker_role: str, defender_role: str):
    """تشخیص هوشمند نوع عملیات (موشکی/هوایی یا زمینی)."""
    if (attacker_key, defender_key) in NON_CONTIGUOUS_PAIRS or (defender_key, attacker_key) in NON_CONTIGUOUS_PAIRS:
        return "air_missile"

    text = (attacker_role + " " + defender_role).lower()
    
    ground_keywords = ["پیشروی زمینی", "تانک", "نفربر", "پیاده نظام", "تصرف شهر", "عبور از مرز", "مرزی", "محور زمینی", "زرهی", "عملیات زمینی"]
    air_keywords = ["موشک", "شلیک", "پرتاب", "پهپاد", "جنگنده", "پدافند", "سایبری", "پایگاه هوایی", "رادار", "سوله"]

    ground_score = sum(1 for kw in ground_keywords if kw in text)
    air_score = sum(1 for kw in air_keywords if kw in text)

    if ground_score > 2 and ground_score >= air_score:
        return "ground_invasion"
    else:
        return "air_missile"


def generate_war_analysis_report(attacker_key: str, defender_key: str, attacker_role: str, defender_role: str = ""):
    """تولید گزارش هوشمند سناریوی نبرد بر اساس رول‌های واقعی هر دو طرف."""
    
    attacker_info = config.COUNTRIES.get(attacker_key, {})
    defender_info = config.COUNTRIES.get(defender_key, {})

    att_flag = attacker_info.get("flag", "")
    att_name = attacker_info.get("name", attacker_key)
    def_flag = defender_info.get("flag", "")
    def_name = defender_info.get("name", defender_key)

    att_country = db.get_country_by_key(attacker_key)
    def_country = db.get_country_by_key(defender_key)

    att_cid = att_country["id"] if att_country else None
    def_cid = def_country["id"] if def_country else None

    att_assets = db.get_country_assets(att_cid) if att_cid else []
    def_assets = db.get_country_assets(def_cid) if def_cid else []

    if not att_assets:
        att_assets = config.COUNTRY_EQUIPMENT_CATALOG.get(attacker_key, [])
        for a in att_assets:
            if "equipment_key" not in a: a["equipment_key"] = a["key"]
            if "equipment_name" not in a: a["equipment_name"] = a["name"]
            if "amount" not in a: a["amount"] = a.get("initial", 100)

    if not def_assets:
        def_assets = config.COUNTRY_EQUIPMENT_CATALOG.get(defender_key, [])
        for d in def_assets:
            if "equipment_key" not in d: d["equipment_key"] = d["key"]
            if "equipment_name" not in d: d["equipment_name"] = d["name"]
            if "amount" not in d: d["amount"] = d.get("initial", 100)

    op_type = detect_operation_type(attacker_key, defender_key, attacker_role, defender_role)

    # Calculate Losses
    losses = calculate_simulated_losses(att_assets, def_assets, att_country, def_country, op_type, attacker_key, defender_key)

    # Try AI API if available
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("AI_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if api_key:
        try:
            prompt = f"""شما یک تحلیل‌گر عالی ارشد نظامی و Game Master در بازی «سیاست مدرن» هستید.
مهاجم: {att_flag} {att_name}
مدافع: {def_flag} {def_name}

رول عملیاتی مهاجم ({att_name}):
"{attacker_role}"

طرح و رول پدافندی مدافع ({def_name}):
"{defender_role if defender_role else 'دفاع موشکی و هوایی استاندارد'}"

نوع عملیات تشخیص داده شده: {"حمله موشکی، پهپادی و هوایی" if op_type == "air_missile" else "عملیات زمینی و تهاجم مرزی"}

تلفات منطقی محاسبه شده:
مهاجم: {losses['att_military_loss']} نظامی، {losses['att_civilian_loss']} غیرنظامی
مدافع: {losses['def_military_loss']} نظامی، {losses['def_civilian_loss']} غیرنظامی

مهم بسیار حیاتی: از به کار بردن ایموجی‌های اضافی و کارتونی خودداری کن. لحن بسیار رسمی، سنگین و کارشناسی باشد. در صورت عدم وجود مرز زمینی یا موشکی بودن عملیات، به هیچ عنوان کلماتی مانند «پیشروی مرزی» یا «تصرف زمینی» به کار نبر!

فرمت گزارش:
*نتیجه سناریوی جنگی — ارزیابی عملیات {att_name} در برابر دفاع {def_name}*
پرونده: عملیات {att_name} / طرح دفاعی {def_name}
━━━━━━━━━━━━━━━━━━
...
"""
            url = "https://api.openai.com/v1/chat/completions"
            data = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "system", "content": "You are a serious military AI scenario analyzer."}, {"role": "user", "content": prompt}],
                "temperature": 0.7
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(data).encode("utf-8"),
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=12) as response:
                res = json.loads(response.read().decode("utf-8"))
                report_text = res["choices"][0]["message"]["content"]
                if report_text:
                    return report_text, losses
        except Exception as e:
            print(f"AI API call failed, falling back to built-in simulation engine: {e}")

    # Fallback Built-in Engine
    if op_type == "air_missile":
        report_text = build_air_missile_report_text(
            att_flag, att_name, def_flag, def_name, attacker_role, defender_role, losses, att_assets, def_assets
        )
    else:
        report_text = build_ground_invasion_report_text(
            att_flag, att_name, def_flag, def_name, attacker_role, defender_role, losses, att_assets, def_assets
        )

    return report_text, losses


def calculate_simulated_losses(att_assets, def_assets, att_country, def_country, op_type, attacker_key, defender_key):
    """محاسبه تلفات واقعی، متوازن و منطقی انسان‌ها و تجهیزات دو کشور."""
    
    def pick_losses_from_assets(assets_list, is_attacker, op_type):
        result_losses = []
        by_cat = {}
        for item in assets_list:
            eq_key = item.get("equipment_key") or item.get("key")
            eq_name = item.get("equipment_name") or item.get("name")
            cat = item.get("category", "Ground Forces")
            amount = item.get("amount", item.get("initial", 50))
            buy_price = item.get("buy_price", item.get("price", 1_000_000))
            by_cat.setdefault(cat, []).append({
                "key": eq_key, "name": eq_name, "amount": amount, "category": cat, "price": buy_price
            })

        for cat, items in by_cat.items():
            if is_attacker and op_type == "air_missile":
                if cat in ["Missiles", "UAV"]:
                    selected = random.sample(items, min(len(items), random.randint(1, 4)))
                    for it in selected:
                        curr_amt = it["amount"]
                        if curr_amt <= 0: continue
                        loss_qty = max(1, min(curr_amt, random.randint(2, 10)))
                        result_losses.append({
                            "equipment_key": it["key"], "equipment_name": it["name"],
                            "amount": loss_qty, "category": cat, "price": it["price"]
                        })
                elif cat == "Aircraft":
                    if random.random() < 0.15:
                        selected = random.sample(items, 1)
                        for it in selected:
                            if it["amount"] > 0:
                                result_losses.append({
                                    "equipment_key": it["key"], "equipment_name": it["name"],
                                    "amount": 1, "category": cat, "price": it["price"]
                                })
            else:
                selected = random.sample(items, min(len(items), random.randint(1, 3)))
                for it in selected:
                    curr_amt = it["amount"]
                    if curr_amt <= 0: continue
                    if cat in ["Aircraft", "Navy", "Air Defense"]:
                        loss_qty = max(1, min(curr_amt, random.randint(1, 3)))
                    elif cat in ["Missiles", "UAV"]:
                        loss_qty = max(1, min(curr_amt, random.randint(2, 8)))
                    else:
                        loss_qty = max(1, min(curr_amt, random.randint(2, 6)))

                    result_losses.append({
                        "equipment_key": it["key"], "equipment_name": it["name"],
                        "amount": loss_qty, "category": cat, "price": it["price"]
                    })

        return result_losses

    att_losses = pick_losses_from_assets(att_assets, True, op_type)
    def_losses = pick_losses_from_assets(def_assets, False, op_type)

    if op_type == "air_missile":
        att_military_loss = 0
        att_civilian_loss = 0
        def_military_loss = random.randint(15, 65)
        def_civilian_loss = random.randint(2, 25)
    else:
        att_military_loss = random.randint(120, 380)
        att_civilian_loss = random.randint(5, 30)
        def_military_loss = random.randint(180, 520)
        def_civilian_loss = random.randint(20, 85)

    return {
        "att_losses": att_losses,
        "def_losses": def_losses,
        "att_military_loss": att_military_loss,
        "att_civilian_loss": att_civilian_loss,
        "def_military_loss": def_military_loss,
        "def_civilian_loss": def_civilian_loss,
    }


def build_air_missile_report_text(att_flag, att_name, def_flag, def_name, attacker_role, defender_role, losses, att_assets, def_assets):
    """گزارش رسمی و سنگین نبرد موشکی/پدافندی."""

    lines = []
    lines.append(f"*نتیجه سناریوی جنگی — ارزیابی عملیات موشکی/هوایی {att_name} در برابر دفاع {def_name}*")
    lines.append(f"پرونده: طوفان موشکی-هوایی {att_flag} {att_name} / شبکه دفاع هوایی {def_flag} {def_name}")
    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *مرحله ۱: آماده‌سازی و شلیک پرتابه‌ها (۲۰:۰۰ – ۲۲:۰۰)*")
    lines.append(f"یگان‌های موشکی {att_name} شلیک دقیق پرتابه‌های کروز و بالستیک را به همراه پهپادها به سمت پایگاه‌های هوایی، راداری و خزانه‌های سوخت {def_name} آغاز کردند.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *مرحله ۲: ورود به حریم هوایی و درگیری پدافند (۲۲:۰۰ – ۲۳:۳۰)*")
    lines.append(f"رادارهای هشدار زودهنگام {def_name} پرتابه‌های ورودی را شناسایی کردند.")
    lines.append(f"سامانه‌های پدافند هوایی چندلایه {def_name} جهت رهگیری شلیک شدند.")
    lines.append("نتیجه درگیری:")
    lines.append(f"• حدود ۳۵٪ از موشک‌ها توسط سامانه‌های پدافندی {def_name} رهگیری شدند.")
    lines.append(f"• ۶۵٪ پرتابه‌ها از سپر پدافندی عبور کرده و به اهداف تعیین‌شده متصل شدند.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *مرحله ۳: اصابت‌ها و خسارات زیرساختی (۲۳:۳۰ – ۰۵:۰۰)*")
    lines.append("ارزیابی اهداف اصابت شده:")
    lines.append(f"- *پایگاه‌های هوایی و سوله‌ها {def_name}:* آسیب به باندهای پرواز و سوله‌های نگهداری جنگنده‌ها.")
    lines.append(f"- *مراکز پشتیبانی سوخت و C4I:* ورود خسارت به خزانه‌های سوخت و ایجاد اختلال موقت ارتباطی.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *مرحله ۴: آماده‌باش پدافند و گشت هوایی (۰۵:۰۰ – ۱۲:۰۰)*")
    lines.append(f"جنگنده‌های {def_name} برای پوشش هوایی به پرواز درآمده و نیروهای امدادی پایگاه‌ها را تثبیت کردند.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *جمع‌بندی نهایی سناریو:*")
    lines.append(f"عملکرد تهاجمی {att_name}: شلیک موثر پرتابه‌ها و تخریب بخشی از زیرساخت‌های کلیدی.")
    lines.append(f"عملکرد دفاعی {def_name}: رهگیری بخشی از موشک‌ها و جلوگیری از انهدام کامل پایگاه‌ها.\n")

    lines.append("نتیجه کلی: عملیات هوایی/موشکی {att_name} ضربات سنگینی به زیرساخت‌ها وارد ساخت، اما شبکه پدافندی {def_name} توان عملیاتی خود را حفظ نمود.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *برآورد تلفات انسانی اولیه:*\n")

    lines.append(f"تلفات کشور مهاجم ({att_flag} {att_name}):")
    lines.append(f"• پرسنل نظامی: {losses['att_military_loss']} نفر (حمله از راه دور/بدون تلفات خاک خودی)")
    lines.append(f"• تلفات غیرنظامی: {losses['att_civilian_loss']} نفر")

    lines.append(f"\nتلفات کشور مدافع ({def_flag} {def_name}):")
    lines.append(f"• پرسنل نظامی: {losses['def_military_loss']} نفر")
    lines.append(f"• تلفات غیرنظامی: {losses['def_civilian_loss']} نفر")

    return "\n".join(lines)


def build_ground_invasion_report_text(att_flag, att_name, def_flag, def_name, attacker_role, defender_role, losses, att_assets, def_assets):
    """گزارش نبردهای دارای تهاجم زمینی و مرزی."""

    lines = []
    lines.append(f"*نتیجه سناریوی جنگی — ارزیابی عملیات زمینی {att_name} در برابر دفاع {def_name}*")
    lines.append(f"پرونده: تهاجم زمینی {att_flag} {att_name} / دفاع مرزی {def_flag} {def_name}")
    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *ساعت ۰۳:۰۰ — آغاز حمله*")
    lines.append("آتش‌پایه‌های توپخانه و حملات موشکی اولیه آغاز می‌شود.")
    lines.append("نتیجه: خطوط پاسگاهی مرزی زیر آتش سنگین قرار می‌گیرند.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *ساعت ۰۶:۰۰ — ورود ستون‌های زرهی به محورهای مرزی*")
    lines.append(f"پیشروی تانک‌ها و نفربرهای زرهی {att_name} در محورهای اصلی مرزی.")
    lines.append("درگیری شدید زرهی در مواضع پیشین مرزی.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *ساعت ۱۲:۰۰ — ورود نیروهای ذخیره مدافع*")
    lines.append(f"نیروهای ذخیره و یگان‌های ضدزره {def_name} وارد خطوط پدافندی می‌شوند.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *برآورد تلفات انسانی اولیه:*\n")

    lines.append(f"تلفات کشور مهاجم ({att_flag} {att_name}):")
    lines.append(f"• پرسنل نظامی: {losses['att_military_loss']:,} نفر")
    lines.append(f"• تلفات غیرنظامی: {losses['att_civilian_loss']:,} نفر")

    lines.append(f"\nتلفات کشور مدافع ({def_flag} {def_name}):")
    lines.append(f"• پرسنل نظامی: {losses['def_military_loss']:,} نفر")
    lines.append(f"• تلفات غیرنظامی: {losses['def_civilian_loss']:,} نفر")

    return "\n".join(lines)


def build_detailed_loss_receipt(country_key: str, item_losses: list, military_loss: int, civilian_loss: int, operation_name: str = "عملیات اخیر", is_attacker: bool = False, op_type: str = "air_missile"):
    """تولید فاکتور دقیق قبل/تلفات/بعد تجهیزات، خسارت مالی، روحیه و زمان ترمیم با لحن رسمی."""
    
    c_info = config.COUNTRIES.get(country_key, {})
    c_flag = c_info.get("flag", "")
    c_name = c_info.get("name", country_key)

    country = db.get_country_by_key(country_key)
    cid = country["id"] if country else None
    db_assets = {a["equipment_key"]: a for a in db.get_country_assets(cid)} if cid else {}

    catalog = config.COUNTRY_EQUIPMENT_CATALOG.get(country_key, [])
    catalog_map = {item["key"]: item for item in catalog}

    def get_subcat_info(eq_name, category):
        eq_lower = eq_name.lower()
        if category == "Aircraft":
            if any(k in eq_lower for k in ["c-130", "c-17", "c-390", "a400m", "e-2", "e-3", "e-7", "awacs", "آواکس", "ترابری", "سوخت‌رسان", "mrtt", "pegasus", "stratotanker", "p-8", "p-3", "poseidon"]):
                return ("Aircraft_Support", "هواپیماهای پشتیبانی", "فروند")
            elif any(k in eq_lower for k in ["heli", "apache", "blackhawk", "black hawk", "chinook", "cougar", "tiger", "nh90", "panther", "شینوک", "طوفان", "بالگرد", "شاهد-۲۸۵", "بل ", "میل ", "ka-52", "mi-28", "mi-35", "mi-171", "t129", "atak", "gokbey"]):
                return ("Helicopter", "بالگردها", "فروند")
            else:
                return ("Aircraft_Fighter", "نیروی هوایی", "فروند")
        elif category == "UAV":
            return ("UAV", "پهپادها", "فروند")
        elif category == "Ground Forces":
            return ("Ground Forces", "نیروی زمینی", "دستگاه")
        elif category == "Artillery":
            return ("Artillery", "توپخانه و راکت‌انداز", "سامانه")
        elif category == "Navy":
            return ("Navy", "نیروی دریایی", "فروند")
        elif category == "Missiles":
            return ("Missiles", "توان موشکی", "فروند")
        elif category == "Air Defense":
            return ("Air Defense", "پدافند هوایی", "سامانه/آتشبار")
        else:
            return (category, category, "واحد")

    title_label = "مصرف‌شده/شلیک‌شده" if (is_attacker and op_type == "air_missile") else "تلفات تجهیزات"
    lines = []
    lines.append(f"*{title_label} {c_flag} {c_name} — «{operation_name}»*")
    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("■ *تلفات انسانی:*")
    lines.append(f"> • پرسنل نظامی: {military_loss:,} نفر")
    lines.append(f"> • تلفات غیرنظامی: {civilian_loss:,} نفر\n")
    lines.append("━━━━━━━━━━━━━━━━━━\n")

    grouped = {}
    total_usd_damage = 0

    for loss in item_losses:
        eq_key = loss["equipment_key"]
        cat_key = loss.get("category", "Ground Forces")
        loss_amt = loss["amount"]

        asset_info = db_assets.get(eq_key, {})
        cat_item = catalog_map.get(eq_key, {})

        eq_name = loss.get("equipment_name") or asset_info.get("equipment_name") or cat_item.get("name") or eq_key
        unit_price = loss.get("price") or asset_info.get("buy_price") or cat_item.get("price", 1_000_000)

        total_usd_damage += (unit_price * loss_amt)

        current_qty = asset_info.get("amount", cat_item.get("initial", loss_amt))
        after_qty = current_qty
        before_qty = current_qty + loss_amt

        subcat_id, subcat_label, unit = get_subcat_info(eq_name, cat_key)

        grouped.setdefault(subcat_id, {"label": subcat_label, "items": []})["items"].append({
            "name": eq_name,
            "before": before_qty,
            "loss": loss_amt,
            "after": after_qty,
            "unit": unit
        })

    subcat_order = ["Aircraft_Fighter", "Aircraft_Support", "UAV", "Helicopter", "Ground Forces", "Artillery", "Missiles", "Air Defense", "Navy"]

    summary_rows = []

    for sub_id in subcat_order:
        if sub_id not in grouped:
            continue

        g_data = grouped[sub_id]
        label = g_data["label"]
        items = g_data["items"]

        lines.append(f"■ *{label}*\n")

        sub_sum = 0
        sub_unit = "واحد"
        loss_word = "مصرف/شلیک:" if (is_attacker and op_type == "air_missile") else "تلفات:"

        for item in items:
            sub_sum += item["loss"]
            sub_unit = item["unit"]
            lines.append(f"> *{item['name']}*")
            lines.append(f"> قبل: {item['before']:,} {item['unit']}")
            lines.append(f"> {loss_word} {item['loss']:,} {item['unit']}")
            lines.append(f"> بعد: {item['after']:,} {item['unit']}\n")

        lines.append("---\n")

        short_lbl = label.replace("نیروی هوایی و هوانوردی", "جنگنده").replace("نیروی هوایی", "جنگنده")
        summary_rows.append(f"{short_lbl}: {sub_sum:,} {sub_unit}")

    lines.append("━━━━━━━━━━━━━━━━━━\n")
    sum_title = "جمع تسلیحات مصرف‌شده:" if (is_attacker and op_type == "air_missile") else "جمع کاهش تجهیزات ثبت‌شده:"
    lines.append(f"■ *{sum_title}*\n")

    for s_row in summary_rows:
        lines.append(f"> • {s_row}")

    lines.append("\n━━━━━━━━━━━━━━━━━━\n")
    lines.append("■ *ارزیابی مالی و استراتژیک:*\n")
    
    if total_usd_damage >= 1_000_000_000:
        damage_str = f"{total_usd_damage / 1_000_000_000:.2f} میلیارد دلار"
    elif total_usd_damage >= 1_000_000:
        damage_str = f"{total_usd_damage / 1_000_000:.1f} میلیون دلار"
    else:
        damage_str = f"{total_usd_damage:,} دلار"

    lines.append(f"> • ارزش کل تجهیزات و خسارات: {damage_str}")
    if is_attacker:
        lines.append("> • تغییر روحیه ملی: +۱۰٪ (حماسه و اقتدار ملی)")
        lines.append("> • زمان آمادگی برای موج بعدی: ۱۲ ساعت")
    else:
        lines.append("> • تغییر روحیه ملی: -۵٪ (اضطراب عمومی و پناهگاه)")
        lines.append("> • زمان بازسازی و ترمیم زیرساخت‌ها: ۳ تا ۵ روز")

    lines.append("\n━━━━━━━━━━━━━━━━━━\n")
    lines.append("■ *ارزیابی نهایی:*\n")
    if is_attacker and op_type == "air_missile":
        lines.append("> _عملیات شلیک با موفقیت کامل بدون تلفات انسانی نیروهای خودی اجرا گردید و پرتابه‌های شلیک‌شده طبق برنامه از دیتابیس کسر شدند._")
    else:
        lines.append("> _خسارت اصلی روی پایگاه‌های هوایی، سامانه‌های پدافندی و تجهیزات کلیدی متمرکز شده و بخش قابل‌توجهی از توان عملیاتی برای مدتی نیازمند بازسازی و جایگزینی است._")

    return "\n".join(lines)


def apply_war_losses_to_db(attacker_key: str, defender_key: str, losses: dict):
    """اعمال کسر تلفات و خسارات از دیتابیس هر دو کشور."""
    conn = db.get_connection()
    cur = conn.cursor()

    att_country = db.get_country_by_key(attacker_key)
    def_country = db.get_country_by_key(defender_key)

    if att_country:
        att_cid = att_country["id"]
        db.seed_country_assets(att_cid, attacker_key)
        new_att_p = max(0, att_country["active_personnel"] - losses.get("att_military_loss", 0))
        cur.execute("UPDATE countries SET active_personnel = ? WHERE id = ?", (new_att_p, att_cid))

        for item in losses.get("att_losses", []):
            cur.execute("""
                UPDATE country_assets SET amount = MAX(0, amount - ?)
                WHERE country_id = ? AND equipment_key = ?
            """, (item["amount"], att_cid, item["equipment_key"]))

    if def_country:
        def_cid = def_country["id"]
        db.seed_country_assets(def_cid, defender_key)
        new_def_p = max(0, def_country["active_personnel"] - losses.get("def_military_loss", 0))
        cur.execute("UPDATE countries SET active_personnel = ? WHERE id = ?", (new_def_p, def_cid))

        for item in losses.get("def_losses", []):
            cur.execute("""
                UPDATE country_assets SET amount = MAX(0, amount - ?)
                WHERE country_id = ? AND equipment_key = ?
            """, (item["amount"], def_cid, item["equipment_key"]))

    conn.commit()
    conn.close()
    return True
