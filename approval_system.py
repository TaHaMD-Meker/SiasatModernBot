# -*- coding: utf-8 -*-
"""
ماژول اختصاصی سیستم رضایت عمومی و گزارش روزانه کشور (Approval & Daily Report System v2.1)
فاصله‌گذاری مرتب، خطوط مجزا و بدون ایموجی‌های اضافی.
"""

import math
import database as db
import config
import daily_narratives
from utils import format_money, format_number, format_oil

def get_approval_badge(rating: int):
    """ایجاد نوار بصری درصد و وضعیت رضایت عمومی."""
    rating = max(0, min(100, rating))
    filled = int(round(rating / 10))
    bar = "█" * filled + "░" * (10 - filled)
    
    if rating >= 75:
        return f"*رضایت عالی ({rating}٪)*\n`[{bar}]` {rating}٪ — پایداری و ثبات کامل اجتماعی"
    elif rating >= 50:
        return f"*رضایت متوسط ({rating}٪)*\n`[{bar}]` {rating}٪ — ثبات شکننده / نیاز به بهبود خدمات"
    elif rating >= 40:
        return f"*رضایت پایین ({rating}٪)*\n`[{bar}]` {rating}٪ — هشدار نارضایتی عمومی / آستانه بحران"
    else:
        return f"*رضایت بحرانی ({rating}٪)*\n`[{bar}]` {rating}٪ — بحران شدید اجتماعی و مهاجرت گسترده"


def calculate_country_requirements(c: dict):
    """محاسبه دقیق میزان نیازهای روزانه کشور بر اساس جمعیت."""
    pop = c.get("population", 10_000_000)
    pop_millions = max(0.1, pop / 1_000_000)

    elec_need = max(10, int(pop_millions * 1.5))
    oil_need_daily = max(1_000, int(pop_millions * 15_000))
    grain_need_daily = max(10, int(pop_millions * 100))

    return {
        "pop": pop,
        "pop_millions": pop_millions,
        "elec_need": elec_need,
        "oil_need_daily": oil_need_daily,
        "grain_need_daily": grain_need_daily,
    }


def process_daily_approval_and_emigration(c: dict):
    """پردازش روزانه رضایت عمومی و کسر هوشمند منابع / محاسبه مهاجرت."""
    
    cid = c["id"]
    pop = c.get("population", 10_000_000)
    current_approval = c.get("approval_rating", 80)
    
    reqs = calculate_country_requirements(c)
    elec_need = reqs["elec_need"]
    oil_need = reqs["oil_need_daily"]
    grain_need = reqs["grain_need_daily"]

    # 1. Check Electricity
    current_elec = c.get("electricity", 100)
    if current_elec < elec_need:
        deficit_pct = (elec_need - current_elec) / elec_need
        elec_penalty = -max(1, int(deficit_pct * 5))
        elec_ok = False
    else:
        elec_penalty = 0
        elec_ok = True

    # 2. Check Oil (production + reserves)
    current_oil_res = c.get("oil_reserves", 0)
    current_oil_prod = c.get("oil_production", 0)
    available_oil = current_oil_res + current_oil_prod

    if available_oil < oil_need:
        oil_deficit_pct = (oil_need - available_oil) / oil_need
        oil_penalty = -max(1, int(oil_deficit_pct * 6))
        db.update_country_field(cid, "oil_reserves", 0)
        oil_ok = False
    else:
        deficit_from_prod = max(0, oil_need - current_oil_prod)
        new_res = max(0, current_oil_res - deficit_from_prod)
        db.update_country_field(cid, "oil_reserves", new_res)
        oil_penalty = 0
        oil_ok = True

    # 3. Check Grain (Food / Hunger) - include daily grain production
    current_grain_res = c.get("grain", 0)
    daily_grain_prod = c.get("grain_daily", 0)
    available_grain = current_grain_res + daily_grain_prod

    if available_grain < grain_need:
        grain_deficit_pct = (grain_need - available_grain) / max(1, grain_need)
        grain_penalty = -max(3, int(grain_deficit_pct * 12))
        db.update_country_field(cid, "grain", 0)
        grain_ok = False
    else:
        new_grain_res = max(0, current_grain_res + daily_grain_prod - grain_need)
        db.update_country_field(cid, "grain", new_grain_res)
        grain_penalty = 0
        grain_ok = True

    # 4. Recovery
    if elec_ok and oil_ok and grain_ok:
        recovery = 2
    else:
        recovery = 0

    net_change = elec_penalty + oil_penalty + grain_penalty + recovery
    new_approval = max(0, min(100, current_approval + net_change))
    db.update_country_field(cid, "approval_rating", new_approval)

    # 5. Emigration if approval < 40
    emig_count = 0
    if new_approval < 40:
        if new_approval >= 30:
            emig_rate = 0.005 # 0.5%
        elif new_approval >= 20:
            emig_rate = 0.010 # 1.0%
        elif new_approval >= 10:
            emig_rate = 0.020 # 2.0%
        else:
            emig_rate = 0.035 # 3.5%

        emig_count = int(pop * emig_rate)
        new_pop = max(100_000, pop - emig_count)
        
        active_lost = int(c.get("active_personnel", 0) * (emig_rate * 0.5))
        reserve_lost = int(c.get("reserve_personnel", 0) * (emig_rate * 0.5))

        new_active = max(1_000, c.get("active_personnel", 0) - active_lost)
        new_reserve = max(1_000, c.get("reserve_personnel", 0) - reserve_lost)

        tax_per_capita = c.get("tax_income", 0) / pop if pop > 0 else 0.1
        new_tax = int(new_pop * tax_per_capita)

        db.update_country_field(cid, "population", new_pop)
        db.update_country_field(cid, "active_personnel", new_active)
        db.update_country_field(cid, "reserve_personnel", new_reserve)
        db.update_country_field(cid, "tax_income", new_tax)

    return {
        "new_approval": new_approval,
        "net_change": net_change,
        "elec_ok": elec_ok,
        "oil_ok": oil_ok,
        "grain_ok": grain_ok,
        "emig_count": emig_count,
    }


def get_approval_status_message(c: dict):
    """تولید پیام وضعیت رضایت عمومی با فاصله‌گذاری مرتب و بدون ایموجی اضافی."""
    
    flag = c.get("flag", "")
    name = c.get("name", "کشور")
    pop = c.get("population", 10_000_000)
    approval = c.get("approval_rating", 80)

    reqs = calculate_country_requirements(c)
    elec_need = reqs["elec_need"]
    oil_need = reqs["oil_need_daily"]
    grain_need = reqs["grain_need_daily"]

    badge = get_approval_badge(approval)

    lines = []
    lines.append(f"*شاخص رضایت عمومی و پایداری کشور {flag} {name}*\n")
    lines.append(badge)
    lines.append("\n━━━━━━━━━━━━━━━━━━\n")
    lines.append("*ارزیابی روزانه منابع و مصرف حیاتی کشور:*\n")

    # Electricity Status
    current_elec = c.get("electricity", 100)
    if current_elec >= elec_need:
        elec_status = f"تامین کامل (موجودی: {current_elec}٪ | نیاز: {elec_need}٪)"
    else:
        elec_status = f"کسری برق (موجودی: {current_elec}٪ | نیاز: {elec_need}٪)"
    lines.append(f"• *انرژی و برق:* {elec_status}\n")

    # Oil Status
    res_oil = c.get("oil_reserves", 0)
    prod_oil = c.get("oil_production", 0)
    avail_oil = res_oil + prod_oil
    if avail_oil >= oil_need:
        oil_status = f"تامین کامل (نیاز روزانه: {format_oil(oil_need)})"
    else:
        oil_status = f"کمبود سوخت و نفت (کسری: {format_oil(oil_need - avail_oil)})"
    lines.append(f"• *سوخت و نفت:* {oil_status}\n")

    # Grain Status
    current_grain = c.get("grain", 0)
    grain_daily = c.get("grain_daily", 0)
    avail_grain = current_grain + grain_daily
    if avail_grain >= grain_need:
        grain_status = f"تامین کامل (ذخیره: {format_number(current_grain)} تن | تولید: +{format_number(grain_daily)} تن/روز | نیاز: {format_number(grain_need)} تن)"
    else:
        grain_status = f"گرسنگی و کمبود غلات (کسری: {format_number(grain_need - avail_grain)} تن)"
    lines.append(f"• *تامین غذا و غلات:* {grain_status}\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")
    lines.append("*وضعیت جمعیت و مهاجرت:*\n")

    if approval >= 40:
        lines.append(f"• *وضعیت پایدار:* نرخ مهاجرت ۰٪ (جمعیت فعلی: {format_number(pop)} نفر).\n")
        lines.append("_(در صورت افت رضایت عمومی به زیر ۴۰٪، روند خروج و مهاجرت جمعیت و کاهش ارتش آغاز می‌گردد)._")
    else:
        if approval >= 30:
            emig_rate_str = "۰.۵٪"
        elif approval >= 20:
            emig_rate_str = "۱.۰٪"
        elif approval >= 10:
            emig_rate_str = "۲.۰٪"
        else:
            emig_rate_str = "۳.۵٪"

        emig_est = int(pop * float(emig_rate_str.replace("٪", "").replace("۰", "0").replace("۱", "1").replace("۲", "2").replace("۳", "3").replace("۵", "5").replace(".", ".")) / 100)

        lines.append("*هشدار بحران اجتماعی و خروج جمعیت:*\n")
        lines.append(f"• به دلیل افت رضایت عمومی به {approval}٪، روزانه *{emig_rate_str}* از جمعیت (حدود *{format_number(emig_est)} نفر در روز*) در حال مهاجرت و خروج از کشور هستند.\n")
        lines.append("• این امر مستقیم موجب کاهش نیروی انسانی ارتش و افت پایه درآمد مالیاتی کشور می‌گردد.")

    return "\n".join(lines)


def build_daily_country_report_message(c: dict, app_res: dict, today_str: str):
    """تولید گزارش روزانه با فاصله‌گذاری مرتب، کسر واقعی هزینه نگهداری و خطوط مجزا."""
    
    flag = c.get("flag", "")
    name = c.get("name", "کشور")
    pop = c.get("population", 10_000_000)
    approval = c.get("approval_rating", 80)

    reqs = calculate_country_requirements(c)
    elec_need = reqs["elec_need"]
    oil_need = reqs["oil_need_daily"]
    grain_need = reqs["grain_need_daily"]

    maint_info = db.calculate_country_maintenance_cost(c["id"])
    total_maint = maint_info["total_maint"]
    disc_pct = maint_info["discount_pct"]

    tax_income = c.get("tax_income", 0)
    daily_income = c.get("daily_income", 0)
    net_income = daily_income - total_maint

    gold_daily = c.get("gold_daily", 0)
    oil_prod = c.get("oil_production", 0)
    grain_prod = c.get("grain_daily", 0)
    treasury = c.get("treasury", 0)

    narrative = daily_narratives.get_daily_narrative(approval, grain_ok=app_res["grain_ok"], oil_ok=app_res["oil_ok"])

    lines = []
    lines.append(f"*گزارش روزانه وضعیت کشور {flag} {name}*")
    lines.append(f"تاریخ گزارش: {today_str}\n")
    lines.append("━━━━━━━━━━━━━━━━━━\n")
    lines.append("*خلاصه مالی و تغییرات اقتصادی روزانه:*\n")

    lines.append(f"• *درآمد پایه و مالیاتی:* +{format_money(daily_income)}/روز\n")

    if total_maint > 0:
        disc_str = f" (تخفیف فناوری: {disc_pct}٪)" if disc_pct > 0 else ""
        lines.append(f"• *هزینه نگهداری تجهیزات و ارتش:* -{format_money(total_maint)}/روز{disc_str}\n")

    net_sign = "+" if net_income >= 0 else ""
    lines.append(f"• *خالص تغییر روزانه خزانه:* {net_sign}{format_money(net_income)}/روز (اعمال گردید)\n")

    if gold_daily > 0:
        lines.append(f"• *تولید روزانه طلا:* +{gold_daily:,} شمش طلا\n")

    lines.append(f"• *تولید روزانه نفت:* +{format_oil(oil_prod)}\n")

    # Grain
    grain_str = f"+{grain_prod:,} تن تولید / -{grain_need:,} تن مصرف" if grain_prod > 0 else f"-{grain_need:,} تن مصرف روزانه"
    if app_res["grain_ok"]:
        lines.append(f"• *تامین غلات:* {grain_str} (تامین کامل)\n")
    else:
        lines.append(f"• *تامین غلات:* کسری غذایی و گرسنگی (نیاز روزانه: {grain_need:,} تن)\n")

    # Elec
    current_elec = c.get("electricity", 100)
    if app_res["elec_ok"]:
        lines.append(f"• *تراز انرژی:* {current_elec}٪ (تامین کامل نیاز {elec_need}٪)\n")
    else:
        lines.append(f"• *تراز انرژی:* کسری برق (موجودی: {current_elec}٪ | نیاز: {elec_need}٪)\n")

    # Change in approval
    net_chg = app_res["net_change"]
    sign_chg = f"+{net_chg}" if net_chg >= 0 else f"{net_chg}"
    lines.append(f"• *تغییر رضایت عمومی:* {sign_chg}٪ (شاخص فعلی: {app_res['new_approval']}٪)\n")

    # Emigration
    emig = app_res["emig_count"]
    if emig > 0:
        lines.append(f"• *مهاجرت روزانه:* -{emig:,} نفر خروج از کشور (افت رضایت زیر ۴۰٪)\n")

    lines.append(f"• *موجودی نهایی خزانه:* {format_money(treasury)}\n")

    lines.append("━━━━━━━━━━━━━━━━━━\n")
    lines.append("*روایت روزانه کشور:*\n")
    lines.append(f'"{narrative}"')

    return "\n".join(lines)