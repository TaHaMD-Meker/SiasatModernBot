# -*- coding: utf-8 -*-
"""
ماژول تحلیل هوشمند سناریوی نبرد و محاسبه تلفات (AI War Analysis Module)
پشتیبانی از API هوش مصنوعی (OpenAI / OpenRouter)، موتور هوشمند داخلی و صدور فاکتور دقیق تلفات (Loss Receipt).
"""

import os
import random
import json
import urllib.request
import database as db
import config

def generate_war_analysis_report(attacker_key: str, defender_key: str, attacker_role: str):
    """تولید گزارش هوشمند سناریوی نبرد همراه با محاسبه تلفات دقیق."""
    
    attacker_info = config.COUNTRIES.get(attacker_key, {})
    defender_info = config.COUNTRIES.get(defender_key, {})

    att_flag = attacker_info.get("flag", "⚔️")
    att_name = attacker_info.get("name", attacker_key)
    def_flag = defender_info.get("flag", "🛡️")
    def_name = defender_info.get("name", defender_key)

    # Get DB assets and stats for both countries
    att_country = db.get_country_by_key(attacker_key)
    def_country = db.get_country_by_key(defender_key)

    att_cid = att_country["id"] if att_country else None
    def_cid = def_country["id"] if def_country else None

    att_assets = db.get_country_assets(att_cid) if att_cid else []
    def_assets = db.get_country_assets(def_cid) if def_cid else []

    # Try AI API if available
    api_key = os.environ.get("OPENAI_API_KEY") or os.environ.get("AI_API_KEY") or os.environ.get("OPENROUTER_API_KEY")
    if api_key:
        try:
            prompt = f"""شما یک سیستم هوش مصنوعی تحلیل‌گر نظامی و Game Master در ربات استراتژیک «سیاست مدرن» هستید.
کشور مهاجم: {att_flag} {att_name} ({attacker_key})
کشور مدافع: {def_flag} {def_name} ({defender_key})

برنامه عملیاتی و رول تهاجمی ارسال شده توسط بازیکن {att_name}:
"{attacker_role}"

لطفاً دقیقاً طبق فرمت مشخص شده زیر، یک سناریوی کامل نبرد ۷ روزه همراه با جزئیات ساعتی، خطوط درگیری، شهرهای درگیر و برآورد تلفات انسانی و تجهیزاتی تولید کنید:

📄 نتیجه سناریوی جنگی — ارزیابی عملیات {att_name} در برابر دفاع {def_name}
📁 پرونده: عملیات تهاجمی {att_name} / واکنش دفاعی {def_name}
━━━━━━━━━━━━━━━━━━

⏱️ ساعت ۰۳:۰۰ — آغاز حمله
🚀 حملات سایبری و جنگ الکترونیک آغاز می‌شود.
...
(فرمت دقیق همراه با ساعت ۰۳:۳۰ تا ۰۵:۰۰، ۰۶:۰۰، ۱۲:۰۰، روز دوم، روز سوم تا پنجم، روز هفتم و جمع‌بندی نهایی)

در انتهای متن، تلفات تخمینی دو طرف را مشخص کن.
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
                    losses = calculate_simulated_losses(att_assets, def_assets, att_country, def_country)
                    return report_text, losses
        except Exception as e:
            print(f"AI API call failed, falling back to built-in simulation engine: {e}")

    # Fallback Built-in Intelligent War Analysis Engine
    losses = calculate_simulated_losses(att_assets, def_assets, att_country, def_country)
    report_text = build_structured_report_text(
        att_flag, att_name, def_flag, def_name, attacker_role, losses, att_assets, def_assets
    )
    return report_text, losses


def calculate_simulated_losses(att_assets, def_assets, att_country, def_country):
    """محاسبه هوشمند تلفات و خسارات بر اساس دارایی‌های واقعی دو کشور."""
    att_losses = []
    def_losses = []

    # Select random assets from attacker to sustain losses
    for a in att_assets:
        if a["amount"] > 0 and random.random() < 0.35:
            loss_qty = max(1, int(a["amount"] * random.uniform(0.03, 0.12)))
            att_losses.append({
                "equipment_key": a["equipment_key"],
                "equipment_name": a["equipment_name"],
                "amount": loss_qty,
                "category": a["category"]
            })

    # Select random assets from defender to sustain losses
    for d in def_assets:
        if d["amount"] > 0 and random.random() < 0.45:
            loss_qty = max(1, int(d["amount"] * random.uniform(0.05, 0.18)))
            def_losses.append({
                "equipment_key": d["equipment_key"],
                "equipment_name": d["equipment_name"],
                "amount": loss_qty,
                "category": d["category"]
            })

    # Personnel losses
    att_personnel_loss = random.randint(1500, 8500)
    def_personnel_loss = random.randint(2200, 12000)

    return {
        "att_losses": att_losses,
        "def_losses": def_losses,
        "att_personnel_loss": att_personnel_loss,
        "def_personnel_loss": def_personnel_loss,
    }


def build_structured_report_text(att_flag, att_name, def_flag, def_name, attacker_role, losses, att_assets, def_assets):
    """ساخت گزارش قالب‌بندی شده دقیق مطابق نمونه درخواستی کاربر."""
    
    lines = []
    lines.append(f"📄 **نتیجه سناریوی جنگی — ارزیابی عملیات {att_name} در برابر دفاع {def_name}**")
    lines.append(f"📁 **پرونده:** عملیات تهاجمی {att_flag} {att_name} / واکنش دفاعی {def_flag} {def_name}")
    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("⏱️ **ساعت ۰۳:۰۰ — آغاز حمله**")
    lines.append("🚀 حملات سایبری و جنگ الکترونیک آغاز می‌شود.")
    lines.append("نتیجه:")
    lines.append(f"بخشی از ارتباطات نظامی {def_name} دچار اختلال می‌شود.")
    lines.append("پدافندها به حالت آماده‌باش کامل می‌روند.")
    lines.append("حملات موشکی اولیه شناسایی می‌شوند.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("⏱️ **ساعت ۰۳:۳۰ تا ۰۵:۰۰ — موج اول حملات موشکی**")
    lines.append("🎯 اهداف:")
    lines.append("پایگاه‌های هوایی")
    lines.append("مراکز راداری")
    lines.append("انبارهای مهمات\n")

    lines.append("نتیجه:")
    lines.append(f"{def_flag} **پایگاه هوایی اصلی {def_name}:**")
    lines.append("خسارت سنگین به بخش‌هایی از باند و تأسیسات")
    lines.append("بخشی از تجهیزات آسیب می‌بیند")
    lines.append("پایگاه کاملاً از کار نمی‌افتد\n")

    lines.append(f"{def_flag} **مراکز فرماندهی مرزی:**")
    lines.append("خسارت متوسط و اختلال در خطوط ارتباطی\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("⏱️ **ساعت ۰۶:۰۰ — شروع عملیات زمینی**")
    lines.append(f"محور اول: {def_flag} مناطق مرزی و خطوط دفاعی")
    lines.append("نتیجه اولیه:")
    lines.append(f"نیروهای {att_name} پیشروی محدود انجام می‌دهند.")
    lines.append("چند منطقه پاسگاهی و مواضع مرزی تصرف می‌شود.\n")

    lines.append("شهرهای درگیر:")
    lines.append(f"🟠 **منطقه مرزی ۱:** تصرف اولیه نیروهای {att_name}")
    lines.append("🟠 **مواضع دفاعی اصلی:** درگیری شدید، کنترل منطقه بین دو طرف جابه‌جا می‌شود.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("⏱️ **ساعت ۱۲:۰۰ — واکنش مدافع**")
    lines.append(f"{def_flag} **{def_name}:**")
    lines.append("نیروهای ذخیره وارد می‌شوند.")
    lines.append("خطوط ارتباطی جایگزین فعال می‌شوند.")
    lines.append("پدافندهای باقی‌مانده دوباره سازماندهی می‌شوند.\n")

    lines.append("نتیجه:")
    lines.append(f"🟡 سرعت پیشروی نیروهای {att_name} کاهش پیدا می‌کند.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("⏱️ **روز دوم — محورهای جدید تهاجم**")
    lines.append(f"{att_flag} حملات گسترده‌تر به محورهای پشتیبانی آغاز می‌شود.")
    lines.append("نتیجه:")
    lines.append("🟠 مناطق مرزی جدید: چند مواضع تاکتیکی تصرف می‌شود.")
    lines.append(f"اما شهرهای اصلی {def_name} سقوط نمی‌کنند و دفاع شهری باعث توقف پیشروی سریع می‌شود.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append(f"⏱️ **روز سوم تا پنجم — ضدحمله محدود {def_name}**")
    lines.append("نتیجه:")
    lines.append("🔻 مناطق مرزی تصرف‌شده: بخشی از مواضع توسط نیروهای مدافع بازپس گرفته می‌شود.")
    lines.append("🔻 خطوط درگیری در مواضع استراتژیک همچنان سنگین باقی می‌ماند.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("⏱️ **روز هفتم — وضعیت کنترل مناطق**")
    lines.append(f"{att_flag} **کنترل {att_name}:**")
    lines.append("🟠 چند منطقه مرزی و مواضع تاکتیکی خط مقدم\n")

    lines.append(f"{def_flag} **کنترل {def_name}:**")
    lines.append("🟢 شهرهای اصلی، مراکز استراتژیک و پایگاه‌های باقی‌مانده\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("📊 **جمع‌بندی نهایی سناریو:**")
    lines.append(f"{att_flag} **موفقیت‌های اولیه {att_name}:**")
    lines.append("✅ آسیب به بخشی از زیرساخت‌های هوایی و راداری")
    lines.append("✅ اختلال موقت در سیستم فرماندهی")
    lines.append("✅ پیشروی محدود در مناطق مرزی\n")

    lines.append(f"{def_flag} **واکنش دفاعی {def_name}:**")
    lines.append("✅ جلوگیری از سقوط شهرهای اصلی")
    lines.append("✅ بازگردانی بخشی از مواضع مرزی از دست‌رفته")
    lines.append("✅ حفظ توان عملیاتی پدافند و نیروی هوایی\n")

    lines.append(f"📌 **نتیجه کلی:** 🟡 عملیات {att_name} در فاز اول موفقیت محدود دارد، اما به دلیل آماده‌باش {def_name} و عدم فروپاشی کامل فرماندهی، به تصرف گسترده شهرهای اصلی منجر نمی‌شود.\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")

    lines.append("💥 **برآورد تلفات و خسارات تجهیزاتی و انسانی:**\n")

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
    lines.append(f"📄 **تلفات تجهیزات {c_flag} {c_name} — {operation_name}**")
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

