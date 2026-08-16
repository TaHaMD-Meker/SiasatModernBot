# -*- coding: utf-8 -*-
"""
ماژول تحلیل هوشمند سناریوی نبرد و محاسبه تلفات (AI War Analysis Module)
پشتیبانی از تفکیک هوشمند نوع عملیات (حمله موشکی/هوایی/پهپادی در برابر عملیات زمینی) و صدور فاکتور دقیق تلفات.
"""

import os
import random
import json
import urllib.request
import database as db
import config

# List of country pairs that do NOT share a land border (purely air/missile/naval operations)
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
    
    # If pair is non-contiguous, it's strictly Missile/Air/Naval
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

    att_flag = attacker_info.get("flag", "⚔️")
    att_name = attacker_info.get("name", attacker_key)
    def_flag = defender_info.get("flag", "🛡️")
    def_name = defender_info.get("name", defender_key)

    att_country = db.get_country_by_key(attacker_key)
    def_country = db.get_country_by_key(defender_key)

    att_cid = att_country["id"] if att_country else None
    def_cid = def_country["id"] if def_country else None

    att_assets = db.get_country_assets(att_cid) if att_cid else []
    def_assets = db.get_country_assets(def_cid) if def_cid else []

    op_type = detect_operation_type(attacker_key, defender_key, attacker_role, defender_role)

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

مهم بسیار حیاتی: در صورت عدم وجود مرز زمینی یا موشکی بودن عملیات، به هیچ عنوان کلماتی مانند «پیشروی مرزی» یا «تصرف زمینی» به کار نبر! فقط اصابت موشک‌ها، پدافند هوایی، پایگاه‌ها، رادارها، آواکس و جنگنده‌ها را تحلیل کن.

فرمت گزارش:
📄 نتیجه سناریوی جنگی — ارزیابی عملیات {att_name} در برابر دفاع {def_name}
📁 پرونده: عملیات {att_name} / طرح دفاعی {def_name}
━━━━━━━━━━━━━━━━━━
...
"""
            url = "https://api.openai.com/v1/chat/completions"
            data = {
                "model": "gpt-4o-mini",
                "messages": [{"role": "system", "content": "You are a military AI scenario analyzer."}, {"role": "user", "content": prompt}],
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
                    losses = calculate_simulated_losses(att_assets, def_assets, att_country, def_country, op_type)
                    return report_text, losses
        except Exception as e:
            print(f"AI API call failed, falling back to built-in simulation engine: {e}")

    # Fallback Built-in Intelligent War Engine
    losses = calculate_simulated_losses(att_assets, def_assets, att_country, def_country, op_type)
    if op_type == "air_missile":
        report_text = build_air_missile_report_text(
            att_flag, att_name, def_flag, def_name, attacker_role, defender_role, losses, att_assets, def_assets
        )
    else:
        report_text = build_ground_invasion_report_text(
            att_flag, att_name, def_flag, def_name, attacker_role, defender_role, losses, att_assets, def_assets
        )

    return report_text, losses


def calculate_simulated_losses(att_assets, def_assets, att_country, def_country, op_type):
    """محاسبه تلفات واقعی بر اساس نوع عملیات و کاتالوگ دو کشور."""
    att_losses = []
    def_losses = []

    if op_type == "air_missile":
        # Attacker loses used missiles, drones, or intercepted strike jets
        for a in att_assets:
            cat = a["category"]
            if cat in ["Missiles", "UAV"] and a["amount"] > 0:
                if random.random() < 0.60:
                    loss_qty = max(1, int(a["amount"] * random.uniform(0.05, 0.20)))
                    att_losses.append({"equipment_key": a["equipment_key"], "equipment_name": a["equipment_name"], "amount": loss_qty, "category": cat})
            elif cat == "Aircraft" and a["amount"] > 0:
                if random.random() < 0.15:
                    loss_qty = max(1, int(a["amount"] * random.uniform(0.02, 0.05)))
                    att_losses.append({"equipment_key": a["equipment_key"], "equipment_name": a["equipment_name"], "amount": loss_qty, "category": cat})

        # Defender loses air defense batteries, hit airbases, radars, fuel depots, fighters in hangars
        for d in def_assets:
            cat = d["category"]
            if cat in ["Air Defense", "Aircraft", "Missiles"] and d["amount"] > 0:
                if random.random() < 0.40:
                    loss_qty = max(1, int(d["amount"] * random.uniform(0.04, 0.15)))
                    def_losses.append({"equipment_key": d["equipment_key"], "equipment_name": d["equipment_name"], "amount": loss_qty, "category": cat})

        att_personnel_loss = random.randint(200, 1200)
        def_personnel_loss = random.randint(1500, 5800)

    else:
        # Ground invasion losses
        for a in att_assets:
            cat = a["category"]
            if cat in ["Ground Forces", "Artillery", "UAV", "Aircraft"] and a["amount"] > 0:
                if random.random() < 0.35:
                    loss_qty = max(1, int(a["amount"] * random.uniform(0.03, 0.12)))
                    att_losses.append({"equipment_key": a["equipment_key"], "equipment_name": a["equipment_name"], "amount": loss_qty, "category": cat})

        for d in def_assets:
            cat = d["category"]
            if cat in ["Ground Forces", "Artillery", "Air Defense", "Aircraft"] and d["amount"] > 0:
                if random.random() < 0.45:
                    loss_qty = max(1, int(d["amount"] * random.uniform(0.05, 0.18)))
                    def_losses.append({"equipment_key": d["equipment_key"], "equipment_name": d["equipment_name"], "amount": loss_qty, "category": cat})

        att_personnel_loss = random.randint(1800, 6500)
        def_personnel_loss = random.randint(2500, 9800)

    return {
        "att_losses": att_losses,
        "def_losses": def_losses,
        "att_personnel_loss": att_personnel_loss,
        "def_personnel_loss": def_personnel_loss,
    }


def build_air_missile_report_text(att_flag, att_name, def_flag, def_name, attacker_role, defender_role, losses, att_assets, def_assets):
    """گزارش مخصوص عملیات هوایی، موشکی و پدافندی (بدون پیشروی زمینی)."""

    lines = []
    lines.append(f"📄 **نتیجه سناریوی جنگی — ارزیابی عملیات موشکی/هوایی {att_name} در برابر پدافند {def_name}**")
    lines.append(f"📁 **پرونده:** طوفان موشکی-هوایی {att_flag} {att_name} / شبکه دفاع هوایی {def_flag} {def_name}")
    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("⏱️ **مرحله ۱: آماده‌سازی، شلیک و تشدید عملیات (۲۰:۰۰ – ۲۲:۰۰)**")
    lines.append(f"🚀 {att_name} شلیک ترکیبی موشک‌های بالستیک، کروز و پهپادهای تهاجمی را از محورهای متصل آغاز کرد.")
    lines.append("موشک‌ها با هدایت سیستم‌های جنگ الکترونیک جهت عبور از رادارهای پدافندی شلیک شدند.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("⏱️ **مرحله ۲: ورود به حریم هوایی و درگیری سنگین پدافند (۲۲:۰۰ – ۲۳:۳۰)**")
    lines.append(f"🌐 شبکه راداری و هشدار زودهنگام {def_name} ورود پرتابه‌ها را شناسایی کرد.")
    lines.append(f"🛡️ سامانه‌های پدافند هوایی چندلایه {def_name} وارد واکنش سریع شدند.")
    lines.append("نتیجه درگیری:")
    lines.append(f"• حدود ۳۰ تا ۴۰ درصد از پرتابه‌ها توسط پدافند هوایی {def_name} رهگیری و منهدم شدند.")
    lines.append(f"• پرتابه‌های باقی‌مانده از لایه‌های پدافندی عبور کرده و به سمت اهداف استراتژیک ادامه مسیر دادند.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("⏱️ **مرحله ۳: اصابت‌ها و خسارات به پایگاه‌ها و زیرساخت‌ها (۲۳:۳۰ – ۰۵:۰۰)**")
    lines.append("🎯 **ارزیابی اهداف اصابت شده:**")
    lines.append(f"{def_flag} **پایگاه‌های هوایی اصلی {def_name}:**")
    lines.append("آسیب به سوله‌های نگهداری جنگنده‌ها، باند پرواز و تأسیسات پشتیبانی.")
    lines.append(f"{def_flag} **مراکز فرماندهی و لجستیک سوخت:**")
    lines.append("اصابت موشک‌های کروز به خزانه‌های سوخت و خطوط ارتباطی C4I، ایجاد اختلال موقت در سیستم‌های ارتباطی.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("⏱️ **مرحله ۴: واکنش نیروی هوایی و پدافند مدافع (۰۵:۰۰ – ۱۲:۰۰)**")
    lines.append(f"{def_flag} نیروی هوایی {def_name} جنگنده‌های خود را جهت گشت‌زنی و حفاظت از حریم هوایی به پرواز درآورد.")
    lines.append("سامانه‌های پدافند هوایی مجدداً بازسازماندهی شدند و وضعیت آماده‌باش کامل اعلام گردید.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("📊 **جمع‌بندی نهایی سناریو:**")
    lines.append(f"{att_flag} **دستاوردهای تهاجمی {att_name}:**")
    lines.append("✅ عبور موفق بخشی از موشک‌ها و پهپادها از لایه‌های پدافندی")
    lines.append("✅ ورود خسارت به زیرساخت‌های هوایی، سوخت و مراکز راداری مدافع\n")

    lines.append(f"{def_flag} **عملکرد پدافندی {def_name}:**")
    lines.append("✅ رهگیری و انهدام بخشی از موشک‌های شلیک‌شده")
    lines.append("✅ حفظ توان عملیاتی پایگاه‌ها و جلوگیری از فلج کامل نیروی هوایی\n")

    lines.append(f"📌 **نتیجه کلی:** 🟡 عملیات هوایی/موشکی {att_name} ضربات سنگینی به زیرساخت‌ها وارد ساخت، اما شبکه پدافندی {def_name} توان عملیاتی خود را حفظ نمود.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("💥 **برآورد تلفات اولیه تجهیزاتی و انسانی:**\n")

    lines.append(f"🔴 **تلفات کشور مهاجم ({att_flag} {att_name}):**")
    lines.append(f"• 🪖 پرسنل نظامی: {losses['att_personnel_loss']:,} نفر")
    for item in losses["att_losses"]:
        lines.append(f"• {item['equipment_name']}: {item['amount']:,} واحد")

    lines.append(f"\n🔵 **تلفات کشور مدافع ({def_flag} {def_name}):**")
    lines.append(f"• 🪖 پرسنل نظامی: {losses['def_personnel_loss']:,} نفر")
    for item in losses["def_losses"]:
        lines.append(f"• {item['equipment_name']}: {item['amount']:,} واحد")

    return "\n".join(lines)


def build_ground_invasion_report_text(att_flag, att_name, def_flag, def_name, attacker_role, defender_role, losses, att_assets, def_assets):
    """گزارش نبردهای دارای تهاجم زمینی و مرزی."""

    lines = []
    lines.append(f"📄 **نتیجه سناریوی جنگی — ارزیابی عملیات زمینی {att_name} در برابر دفاع {def_name}**")
    lines.append(f"📁 **پرونده:** تهاجم زمینی {att_flag} {att_name} / دفاع مرزی {def_flag} {def_name}")
    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("⏱️ **ساعت ۰۳:۰۰ — آغاز حمله**")
    lines.append("🚀 آتش‌پایه‌های توپخانه و حملات موشکی اولیه آغاز می‌شود.")
    lines.append("نتیجه: خطوط پاسگاهی مرزی زیر آتش سنگین قرار می‌گیرند.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("⏱️ **ساعت ۰۶:۰۰ — ورود ستون‌های زرهی به محورهای مرزی**")
    lines.append(f"پیشروی تانک‌ها و نفربرهای زرهی {att_name} در محورهای اصلی مرزی.")
    lines.append("درگیری شدید زرهی در مواضع پیشین مرزی.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("⏱️ **ساعت ۱۲:۰۰ — ورود نیروهای ذخیره مدافع**")
    lines.append(f"{def_flag} نیروهای ذخیره و یگان‌های ضدزره {def_name} وارد خطوط پدافندی می‌شوند.")
    lines.append("سرعت پیشروی ستون‌های زرهی کند می‌شود.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("⏱️ **روز دوم تا هفتم — تثبیت مواضع و ضدحملات**")
    lines.append("درگیری سنگین در مناطق مرزی ادامه یافته و خطوط نبرد تثبیت می‌شوند.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("📊 **جمع‌بندی نهایی سناریو:**")
    lines.append(f"{att_flag} **دستاوردهای {att_name}:** پیشروی محدود مرزی و تصرف چند پاسگاه.")
    lines.append(f"{def_flag} **دفاع {def_name}:** متوقف ساختن پیشروی عمیق و حفظ شهرهای اصلی.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("💥 **برآورد تلفات اولیه تجهیزاتی و انسانی:**\n")

    lines.append(f"🔴 **تلفات کشور مهاجم ({att_flag} {att_name}):**")
    lines.append(f"• 🪖 پرسنل نظامی: {losses['att_personnel_loss']:,} نفر")
    for item in losses["att_losses"]:
        lines.append(f"• {item['equipment_name']}: {item['amount']:,} واحد")

    lines.append(f"\n🔵 **تلفات کشور مدافع ({def_flag} {def_name}):**")
    lines.append(f"• 🪖 پرسنل نظامی: {losses['def_personnel_loss']:,} نفر")
    for item in losses["def_losses"]:
        lines.append(f"• {item['equipment_name']}: {item['amount']:,} واحد")

    return "\n".join(lines)


def build_detailed_loss_receipt(country_key: str, item_losses: list, personnel_loss: int, operation_name: str = "عملیات اخیر"):
    """تولید فاکتور دقیق تلفات تجهیزاتی قبل/تلفات/بعد برای کشور مشخص."""
    
    c_info = config.COUNTRIES.get(country_key, {})
    c_flag = c_info.get("flag", "")
    c_name = c_info.get("name", country_key)

    country = db.get_country_by_key(country_key)
    cid = country["id"] if country else None
    current_assets = {a["equipment_key"]: a for a in db.get_country_assets(cid)} if cid else {}

    cat_icons = {
        "Aircraft": ("✈️", "نیروی هوایی و هوانوردی", "فروند"),
        "UAV": ("🛩️", "پهپادها", "فروند"),
        "Ground Forces": ("🚛", "نیروی زمینی و زرهی", "دستگاه"),
        "Artillery": ("🎯", "توپخانه و راکت‌اندازها", "قبضه"),
        "Navy": ("🚢", "نیروی دریایی", "فروند"),
        "Missiles": ("🚀", "توان موشکی", "فروند"),
        "Air Defense": ("🛡️", "پدافند هوایی", "آتشبار"),
    }

    lines = []
    lines.append(f"📄 **تلفات تجهیزات {c_flag} {c_name} — «{operation_name}»**")
    lines.append("━━━━━━━━━━━━━━━━━━\n")

    grouped = {}
    cat_totals = {}

    for loss in item_losses:
        eq_key = loss["equipment_key"]
        cat_key = loss.get("category", "Ground Forces")
        loss_amt = loss["amount"]

        asset_info = current_assets.get(eq_key, {})
        after_qty = asset_info.get("amount", 0)
        before_qty = after_qty + loss_amt

        icon, cat_label, unit = cat_icons.get(cat_key, ("⚔️", cat_key, "واحد"))

        grouped.setdefault(cat_key, []).append({
            "name": loss["equipment_name"],
            "before": before_qty,
            "loss": loss_amt,
            "after": after_qty,
            "unit": unit,
            "icon": icon
        })

        cat_totals[cat_key] = cat_totals.get(cat_key, 0) + loss_amt

    cats_order = ["Aircraft", "UAV", "Ground Forces", "Artillery", "Navy", "Missiles", "Air Defense"]

    for cat_key in cats_order:
        items = grouped.get(cat_key, [])
        if not items:
            continue

        icon, cat_label, unit = cat_icons.get(cat_key, ("⚔️", cat_key, "واحد"))
        lines.append(f"{icon} **{cat_label}**\n")

        for item in items:
            lines.append(f"{item['icon']} **{item['name']}**")
            lines.append(f"قبل: {item['before']:,} {item['unit']}")
            lines.append(f"تلفات: {item['loss']:,} {item['unit']}")
            lines.append(f"بعد: {item['after']:,} {item['unit']}\n")

        lines.append("---\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")
    lines.append("📌 **جمع کاهش تجهیزات ثبت‌شده:**\n")
    lines.append(f"• 🪖 پرسنل نظامی: {personnel_loss:,} نفر")

    for cat_key in cats_order:
        if cat_key in cat_totals:
            icon, cat_label, unit = cat_icons.get(cat_key, ("⚔️", cat_key, "واحد"))
            lines.append(f"• {icon} {cat_label}: {cat_totals[cat_key]:,} {unit}")

    return "\n".join(lines)


def apply_war_losses_to_db(attacker_key: str, defender_key: str, losses: dict):
    """اعمال کسر تلفات و خسارات از دیتابیس هر دو کشور."""
    conn = db.get_connection()
    cur = conn.cursor()

    att_country = db.get_country_by_key(attacker_key)
    def_country = db.get_country_by_key(defender_key)

    if att_country:
        att_cid = att_country["id"]
        new_att_p = max(0, att_country["active_personnel"] - losses.get("att_personnel_loss", 0))
        cur.execute("UPDATE countries SET active_personnel = ? WHERE id = ?", (new_att_p, att_cid))

        for item in losses.get("att_losses", []):
            cur.execute("""
                UPDATE country_assets SET amount = MAX(0, amount - ?)
                WHERE country_id = ? AND equipment_key = ?
            """, (item["amount"], att_cid, item["equipment_key"]))

    if def_country:
        def_cid = def_country["id"]
        new_def_p = max(0, def_country["active_personnel"] - losses.get("def_personnel_loss", 0))
        cur.execute("UPDATE countries SET active_personnel = ? WHERE id = ?", (new_def_p, def_cid))

        for item in losses.get("def_losses", []):
            cur.execute("""
                UPDATE country_assets SET amount = MAX(0, amount - ?)
                WHERE country_id = ? AND equipment_key = ?
            """, (item["amount"], def_cid, item["equipment_key"]))

    conn.commit()
    conn.close()
    return True
