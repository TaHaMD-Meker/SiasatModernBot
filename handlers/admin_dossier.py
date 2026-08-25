# -*- coding: utf-8 -*-
"""
Country Master Dossier & Deep Inspection Module for SiasatModernBot Admin Panel.
Provides complete 360-degree inspection and god-mode control over countries:
- Trades & Commodities Market Orders (with Force Exec, Cancel, Delete, Strait routing)
- Foreign Military Bases (Overseas owned, Hosted, Stationed forces, Dissolve, Evict)
- Nuclear Fuel Cycle & Strategic Arsenal (Ore, Fuel, Medical Isotopes, 60%, 90% HEU, Warheads, Cap Override, NPT, Sanctions, Confiscation)
- Military Assets Catalog & Named Commanders (Revive, Kill, Add, Catalog editor)
- Macro Economy, Power Grid & Oil Balance (Treasury, Tax, Maintenance with VIP discount, Industrial/Mil Oil, Grain, Electricity, Gold, Chips)
- Diplomacy, Treaties, Alliances, Sanctions & Blockades (Allies, NAP, Wars, Sanctions, Lift Blockade)
- National Intelligence, Cyber Warfare & Active Disruptions (Firewall, Attack/Defense, Clear Disruptions, Reset Limits)
- Loss Reports & War Damage History (Revert loss, Delete report)
- Daily Statements & Activity Compliance (2/2 check, Manual grant, Reset)
- VIP Pass, Monetization & Payment Dossier (Set Diamond/Gold/Silver/Bronze, Revoke, Toman Receipts)
- God-Mode & Ownership Transfer (Transfer player ID, Rename country & flag, Economic/Mil Boost)
"""

import html
import math
import time
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database as db
import config
from utils import format_money, format_number, format_oil


# ==================== پرونده جامع و داشبورد همه‌جانبه مدیریت کشور ====================

async def show_country_dashboard(query, context, country_id: int, notice: str = ""):
    c = db.get_country_by_id(country_id)
    if not c:
        await query.edit_message_text("❌ این کشور پیدا نشد یا قبلاً حذف شده است.",
                                      reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:list:0")]]))
        return

    if c.get("country_key"):
        db.seed_country_assets(c["id"], c["country_key"])

    maint = db.calculate_country_maintenance_cost(country_id)
    stmt_count = db.get_country_statement_count_today(country_id)
    naval_power = db.calculate_naval_power(country_id)
    commanders = db.get_country_commanders(country_id)
    alive_cmd = len([cm for cm in commanders if cm.get("status") == "active"])
    bp = db.get_or_create_battle_pass(country_id)
    bp_status_str = f"Tier {bp['current_tier']} ({bp['current_xp']} XP) [{'👑 پرمیوم' if bp['is_premium'] else '👤 رایگان'}]"
    
    mil_fuel = db.calculate_military_fuel_consumption(country_id)
    ind_oil = db.get_industrial_oil_consumption(country_id)
    gross_income = (c.get("daily_income") or 0) + (c.get("tax_income") or 0)
    net_income = gross_income - maint.get("total_maint", 0)
    oil_balance = (c.get("oil_production") or 0) - (mil_fuel + ind_oil)

    trades = db.get_country_all_trade_contracts(country_id)
    morders = db.get_country_market_orders(country_id)
    owned_bases = db.get_bases(owner_id=country_id)
    hosted_bases = db.get_bases(host_id=country_id)

    # تعیین وضعیت اشتراک
    vip_val = str(c.get("vip_tier") or c.get("is_vip") or "0")
    if vip_val == "1":
        vip_val = "gold"
    vip_tier_key = f"vip_{vip_val}" if not vip_val.startswith("vip_") else vip_val
    if vip_tier_key in config.VIP_TIERS:
        v_info = config.VIP_TIERS[vip_tier_key]
        v_exp = (c.get("vip_expires_at") or "نامحدود")[:10]
        vip_str = f"{v_info.get('badge', '⭐')} <b>{v_info.get('title', 'VIP')}</b> (تا <code>{v_exp}</code>)"
    else:
        vip_str = "👤 <b>کاربر عادی</b>"

    # وضعیت بیانیه‌ها
    if stmt_count >= config.REQUIRED_DAILY_STATEMENTS:
        stmt_badge = f"🟢 <b>{stmt_count}/{config.REQUIRED_DAILY_STATEMENTS} بیانیه</b> (دارای مصونیت)"
    elif stmt_count == 1:
        stmt_badge = f"🟡 <b>۱/{config.REQUIRED_DAILY_STATEMENTS} بیانیه</b> (نیازمند ۱ بیانیه دیگر)"
    else:
        stmt_badge = f"🔴 <b>۰/{config.REQUIRED_DAILY_STATEMENTS} بیانیه</b> (⚠️ در معرض خلع ید در ساعت ۰۰:۰۰)"

    # وضعیت‌های خاص و تحریم‌ها
    flags = []
    if c.get("un_sanctioned"):
        flags.append("🚫 تحریم سازمان ملل")
    if c.get("enrichment_suspended"):
        flags.append("⏸️ تعلیق غنی‌سازی")
    if c.get("npt_withdrawn"):
        flags.append("📜 خروج از NPT")
    if db.is_country_blockaded(country_id):
        flags.append("⚓ محاصره دریایی")
    
    cyber_alerts = []
    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    if (c.get("air_defense_disrupted_until") or "") > now_utc:
        cyber_alerts.append("📡 پدافند هوایی مختل")
    if (c.get("blackout_until") or "") > now_utc:
        cyber_alerts.append("⚡ خاموشی سراسری برق")
    if (c.get("r_and_d_frozen_until") or "") > now_utc:
        cyber_alerts.append("🔬 انجماد تحقیقات")
    if (c.get("command_disrupted_until") or "") > now_utc:
        cyber_alerts.append("📵 اختلال در فرماندهی")
    
    if cyber_alerts:
        flags.append(f"⚡ حمله سایبری: {', '.join(cyber_alerts)}")

    special_flags_str = " | ".join(flags) if flags else "✅ وضعیت عادی و پایدار"

    u_display = f"@{html.escape(c['username'])}" if c.get("username") else "بدون یوزرنیم"
    c_name_esc = html.escape(c.get("name") or "بی‌نام")
    cont_key = next((k for k, v in config.CONTINENTS.items() if c.get("country_key") in v.get("keys", [])), "other")
    cont_title = config.CONTINENTS.get(cont_key, {}).get("name", "بین‌الملل")

    lines = [
        f"<b>{html.escape(notice)}</b>" if notice else "",
        f"🌐 <b>پرونده جامع و مرکز کنترل کشور: {c.get('flag','🏳️')} {c_name_esc}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"👤 <b>رهبر:</b> {u_display} (ID: <code>{c['player_id']}</code>)",
        f"🔑 <b>شناسه سیستمی:</b> <code>{c.get('country_key') or 'custom_faction'}</code> | 🌍 <b>قاره:</b> {cont_title}",
        f"👑 <b>سطح VIP:</b> {vip_str}",
        f"⭐️ <b>وضعیت بتل‌پس:</b> <code>{bp_status_str}</code>",
        f"📝 <b>فعالیت امروز:</b> {stmt_badge}",
        f"🛡️ <b>وضعیت‌های خاص:</b> {special_flags_str}",
        "",
        "📊 <b>شاخص‌های کلیدی اقتصاد، انرژی و صنعت:</b>",
        f"• 🏦 <b>خزانه:</b> <code>{format_money(c['treasury'])}</code> | 📈 <b>تراز خالص:</b> <code>{format_money(net_income)}/روز</code>",
        f"• 🛢️ <b>نفت ذخیره:</b> <code>{format_oil(c['oil_reserves'])}</code> | 🏭 <b>تولید:</b> <code>{format_oil(c['oil_production'])}</code>",
        f"• 🛢️ <b>مصرف روزانه نفت:</b> <code>{format_oil(mil_fuel + ind_oil)}</code> (تراز: <code>{format_oil(oil_balance)}</code>)",
        f"• 🌾 <b>غلات:</b> <code>{format_number(c['grain'])} تن</code> | ⛏️ <b>آهن و فولاد:</b> <code>{format_number(c.get('iron_ore', 0))} تن</code>",
        f"• ⚡ <b>برق:</b> <code>{c.get('electricity', 0)} MW</code> | 🪙 <b>طلا:</b> <code>{format_number(c['gold'])} شمش</code> | 💻 <b>میکروچیپ:</b> <code>{format_number(c.get('microchips', 0))} چیپ</code>",
        f"• 👥 <b>جمعیت:</b> <code>{format_number(c['population'])}</code> | 😀 <b>رضایت عمومی:</b> <code>{c.get('approval_rating', 80)}%</code>",
        "",
        "🎖️ <b>نیروهای مسلح، پایگاه‌ها و فرماندهان:</b>",
        f"• 🪖 <b>پرسنل فعال:</b> <code>{format_number(c.get('active_personnel', 0))}</code> | ⚔️ <b>آمادگی رزمی:</b> <code>{c.get('combat_readiness', 80)}%</code>",
        f"• ⚓ <b>قدرت ناوبری:</b> <code>{format_number(naval_power)} امتیاز</code> | 🎖️ <b>فرماندهان:</b> <code>{alive_cmd} از {len(commanders)} زنده</code>",
        f"• 🏰 <b>پایگاه‌های نظامی:</b> <code>{len(owned_bases)} پایگاه برون‌مرزی | {len(hosted_bases)} پایگاه میزبان</code>",
        "",
        "🧪 <b>برنامه استراتژیک و بازدارندگی هسته‌ای:</b>",
        f"• ☢️ <b>کیک زرد:</b> <code>{c.get('uranium_ore', 0)} تن</code> | 🧪 <b>سوخت هسته‌ای:</b> <code>{c.get('nuclear_fuel', 0)} kg</code>",
        f"• ⚛️ <b>غنی‌سازی ۶۰٪:</b> <code>{c.get('enriched_60', 0)} kg</code> | ☢️ <b>نظامی ۹۰٪ (HEU):</b> <code>{c.get('weapons_grade_90', 0)} kg</code>",
        f"• 🚀 <b>کلاهک‌ها:</b> <code>{c.get('warheads', 0)} عدد</code> (سقف مجاز: <code>{db.get_effective_warhead_cap(c)}</code>) | 🏭 <b>تاسیسات:</b> <code>سطح {c.get('enrichment_tier', 0)}</code>",
        "",
        "📜 <b>مبادلات و معاهدات بین‌المللی:</b>",
        f"• 📜 <b>قراردادهای تجاری:</b> <code>{len(trades)} معامله</code> | 📦 <b>بورس کالا:</b> <code>{len(morders)} سفارش فعال</code>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "👇 برای زیر و رو کردن و مشاهده یا تغییر هر بخش، روی دکمه مربوطه کلیک فرمایید:"
    ]
    text = chr(10).join([line for line in lines if line is not None])

    keyboard = [
        [
            InlineKeyboardButton(f"📜 تجارت‌ها و بورس ({len(trades)})", callback_data=f"admin:c_trades:{c['id']}:0"),
            InlineKeyboardButton(f"🏰 پایگاه‌های نظامی ({len(owned_bases)})", callback_data=f"admin:c_bases:{c['id']}"),
        ],
        [
            InlineKeyboardButton("🧪 برنامه هسته‌ای و موشکی", callback_data=f"admin:c_nuclear:{c['id']}"),
            InlineKeyboardButton("🎖️ تسلیحات و فرماندهان", callback_data=f"admin:c_military:{c['id']}"),
        ],
        [
            InlineKeyboardButton("💰 تراز اقتصاد، تولید و مصرف", callback_data=f"admin:c_economy:{c['id']}"),
            InlineKeyboardButton("🤝 دیپلماسی و تحریم‌ها", callback_data=f"admin:c_diplomacy:{c['id']}"),
        ],
        [
            InlineKeyboardButton("🕵️ اطلاعات، سایبری و امنیت", callback_data=f"admin:c_intel:{c['id']}"),
            InlineKeyboardButton(f"💥 تاریخچه تلفات و جنگ‌ها", callback_data=f"admin:c_losses:{c['id']}:0"),
        ],
        [
            InlineKeyboardButton(f"📝 بیانیه‌ها و رصد فعالیت ({stmt_count}/2)", callback_data=f"admin:c_statements:{c['id']}"),
            InlineKeyboardButton("💳 پرونده مالی و VIP", callback_data=f"admin:c_vip_finance:{c['id']}"),
        ],
        [
            InlineKeyboardButton("⚡ ابزارهای مدیریت و تغییر مالکیت", callback_data=f"admin:c_godmode:{c['id']}"),
            InlineKeyboardButton("✉️ پیام مستقیم به رهبر", callback_data=f"admin:msg_prompt:{c['id']}"),
        ],
        [
            InlineKeyboardButton("🗑️ حذف کامل کشور", callback_data=f"admin:delconfirm:{c['id']}"),
            InlineKeyboardButton("🔙 بازگشت به لیست کشورها", callback_data="admin:list:0"),
        ]
    ]

    try:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
    except Exception:
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            pass


# ==================== ۱. زیرمنوی تجارت‌ها و بورس کالا ====================

async def show_country_trades_menu(query, context, country_id: int, page: int = 0):
    c = db.get_country_by_id(country_id)
    if not c:
        return
    trades = db.get_country_all_trade_contracts(country_id)
    morders = db.get_country_market_orders(country_id)

    per_page = 4
    total_pages = max(1, math.ceil(len(trades) / per_page)) if trades else 1
    page = max(0, min(page, total_pages - 1))
    page_trades = trades[page * per_page : (page + 1) * per_page] if trades else []

    status_labels = {
        "pending": "⏳ در انتظار تایید",
        "accepted": "✅ انجام و ثبت شده",
        "canceled": "❌ لغو شده",
        "rejected": "🚫 رد شده"
    }

    lines = [
        f"📜 <b>پرونده تجارت‌ها و بورس کالای {c['flag']} {html.escape(c['name'])}</b>",
        f"مجموع معاملات ثبت‌شده: <code>{len(trades)} مورد</code> | عرضه در بورس: <code>{len(morders)} سفارش</code>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        ""
    ]

    if not trades:
        lines.append("<i>هیچ قرارداد تجاری دوطرفه‌ای برای این کشور ثبت نشده است.</i>")
        lines.append("")
    else:
        for t in page_trades:
            p_name = f"{t.get('proposer_flag','🏳️')} {html.escape(t.get('proposer_name','نامشخص'))}"
            r_name = f"{t.get('recipient_flag','🏳️')} {html.escape(t.get('recipient_name','نامشخص'))}"
            st_str = status_labels.get(t.get("status"), t.get("status"))

            off_type = t.get("offered_type")
            off_amt = t.get("offered_amount", 0)
            off_key = t.get("offered_key")
            if off_type == "treasury":
                off_desc = f"💵 {format_money(off_amt)}"
            elif off_type == "oil":
                off_desc = f"🛢️ {format_oil(off_amt)}"
            elif off_type == "gold":
                off_desc = f"🪙 {format_number(off_amt)} شمش طلا"
            elif off_type == "grain":
                off_desc = f"🌾 {format_number(off_amt)} تن غلات"
            elif off_type == "microchips":
                off_desc = f"💻 {format_number(off_amt)} چیپ"
            elif off_type == "nuclear_fuel":
                off_desc = f"🧪 {format_number(off_amt)} kg سوخت"
            elif off_type == "equipment":
                off_desc = f"🎖️ {off_amt}x {off_key or 'تسلیحات'}"
            else:
                off_desc = f"{off_amt} {off_type}"

            req_type = t.get("requested_type")
            req_amt = t.get("requested_amount", 0)
            if req_type == "treasury":
                req_desc = f"💵 {format_money(req_amt)}"
            elif req_type == "oil":
                req_desc = f"🛢️ {format_oil(req_amt)}"
            elif req_type == "gold":
                req_desc = f"🪙 {format_number(req_amt)} شمش طلا"
            elif req_type == "grain":
                req_desc = f"🌾 {format_number(req_amt)} تن غلات"
            elif req_type == "microchips":
                req_desc = f"💻 {format_number(req_amt)} چیپ"
            elif req_type == "nuclear_fuel":
                req_desc = f"🧪 {format_number(req_amt)} kg سوخت"
            else:
                req_desc = f"{req_amt} {req_type}"

            t_mode = t.get("transport_mode", "sea")
            t_mode_fa = "🚢 دریایی" if t_mode == "sea" else ("✈️ هوایی" if t_mode == "air" else "🚛 زمینی")
            t_cost = format_money(t.get("transport_cost", 0))
            dt_str = str(t.get("created_at", ""))[:16].replace("T", " ")

            lines.append(f"📌 <b>قرارداد تجاری #{t['id']}</b> ({st_str})")
            lines.append(f"• <b>مسیر:</b> {p_name} ➔ {r_name}")
            lines.append(f"• <b>ارائه‌شده:</b> {off_desc} | <b>درخواستی:</b> {req_desc}")
            lines.append(f"• <b>لجستیک:</b> {t_mode_fa} (هزینه: {t_cost} | پرداخت: {t.get('transport_payer','seller')})")
            lines.append(f"• <b>تاریخ ثبت:</b> <code>{dt_str}</code>")
            lines.append("")

    keyboard = []
    for t in page_trades:
        st_icon = "⏳" if t.get("status") == "pending" else ("✅" if t.get("status") == "accepted" else "❌")
        btn_label = f"{st_icon} بررسی و مدیریت معامله #{t['id']}"
        keyboard.append([InlineKeyboardButton(btn_label, callback_data=f"admin:c_tview:{country_id}:{t['id']}")])

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:c_trades:{country_id}:{page - 1}"))
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(f"صفحه {page + 1} از {total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:c_trades:{country_id}:{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)

    if morders:
        lines.append("━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("📦 <b>سفارش‌های فعال در بورس بین‌المللی کالا:</b>")
        for mo in morders[:3]:
            res_fa = {"oil": "نفت", "gold": "طلا", "grain": "غلات", "microchips": "میکروچیپ", "nuclear_fuel": "سوخت هسته‌ای"}.get(mo["resource_type"], mo["resource_type"])
            tot_val = format_money(mo["amount"] * mo["unit_price"])
            lines.append(f"• <b>#{mo['id']}:</b> {mo['amount']:,} {res_fa} | قیمت واحد: ${mo['unit_price']:,} (ارزش: {tot_val})")
            keyboard.append([InlineKeyboardButton(f"❌ لغو و عودت سفارش بورس #{mo['id']}", callback_data=f"admin:c_morder_cancel:{country_id}:{mo['id']}")])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت به داشبورد کشور", callback_data=f"admin:c:{country_id}")])

    await query.edit_message_text(chr(10).join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def show_country_trade_detail(query, context, country_id: int, contract_id: int):
    t = db.get_trade_contract(contract_id)
    if not t:
        await query.answer("❌ قرارداد یافت نشد.", show_alert=True)
        await show_country_trades_menu(query, context, country_id)
        return

    p_c = db.get_country_by_id(t["proposer_id"]) or {}
    r_c = db.get_country_by_id(t["recipient_id"]) or {}

    p_name = f"{p_c.get('flag','🏳️')} {html.escape(p_c.get('name','نامشخص'))}"
    r_name = f"{r_c.get('flag','🏳️')} {html.escape(r_c.get('name','نامشخص'))}"

    status_labels = {
        "pending": "⏳ در انتظار تایید و امضا",
        "accepted": "✅ اجرا شده و وجوه/کالاها انتقال یافته",
        "canceled": "❌ توسط طرفین یا ادمین لغو شده",
        "rejected": "🚫 توسط کشور مخاطب رد شده"
    }

    straits_crossed = []
    p_key = p_c.get("country_key")
    r_key = r_c.get("country_key")
    for owner_key, s_info in db.STRAITS_MAPPING.items():
        s_key = s_info["strait_key"]
        if db.is_trade_route_crossing_strait(p_key, r_key, s_key):
            st_data = db.get_strait_status(s_key)
            st_status = st_data.get("status", "open")
            st_status_fa = "⛔ مسدود" if st_status == "blocked" else ("💰 دارای عوارض" if st_status == "toll" else "🟢 باز و آزاد")
            straits_crossed.append(f"• {s_info['name']} (وضعیت: {st_status_fa})")

    strait_text = chr(10).join(straits_crossed) if straits_crossed else "• هیچ تنگه یا کانال مسدودی در مسیر مستقیم نیست."

    off_type = t.get("offered_type")
    off_amt = t.get("offered_amount", 0)
    req_type = t.get("requested_type")
    req_amt = t.get("requested_amount", 0)

    t_mode = t.get("transport_mode", "sea")
    t_mode_fa = "🚢 ترابری دریایی" if t_mode == "sea" else ("✈️ ترابری هوایی" if t_mode == "air" else "🚛 ترابری زمینی")

    lines = [
        f"📜 <b>جزئیات کامل قرارداد تجاری #{t['id']}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"📊 <b>وضعیت فعلی:</b> {status_labels.get(t['status'], t['status'])}",
        f"📅 <b>زمان ثبت:</b> <code>{str(t.get('created_at',''))[:19].replace('T',' ')}</code>",
        "",
        f"📤 <b>پیشنهاددهنده (فروشنده):</b> {p_name} (ID: <code>{t['proposer_id']}</code>)",
        f"📥 <b>دریافت‌کننده (خریدار):</b> {r_name} (ID: <code>{t['recipient_id']}</code>)",
        "",
        "📦 <b>محتوای تبادل:</b>",
        f"• <b>مورد ارائه‌شده:</b> <code>{off_amt:,}</code> نوع: <code>{off_type}</code> ({t.get('offered_key') or ''})",
        f"• <b>مورد درخواستی:</b> <code>{req_amt:,}</code> نوع: <code>{req_type}</code>",
        "",
        "🚚 <b>لجستیک و حمل‌ونقل:</b>",
        f"• <b>روش انتقال:</b> {t_mode_fa}",
        f"• <b>هزینه ترانزیت:</b> {format_money(t.get('transport_cost', 0))} (پرداخت‌کننده: {t.get('transport_payer')})",
        f"• <b>ارزیابی تنگه‌ها و آبراه‌ها:</b>",
        strait_text,
        "",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "⚡ <b>اختیارات مدیریتی ادمین برای این قرارداد:</b>"
    ]
    text = chr(10).join(lines)

    keyboard = []
    if t["status"] == "pending":
        keyboard.append([
            InlineKeyboardButton("⚡ اجرای فوری معامله (Force Exec)", callback_data=f"admin:c_t_exec:{country_id}:{contract_id}"),
            InlineKeyboardButton("🚫 ابطال قرارداد (Cancel)", callback_data=f"admin:c_t_cancel:{country_id}:{contract_id}")
        ])
    elif t["status"] == "accepted":
        keyboard.append([
            InlineKeyboardButton("🚫 ابطال و تغییر وضعیت به لغو", callback_data=f"admin:c_t_cancel:{country_id}:{contract_id}")
        ])

    keyboard.append([InlineKeyboardButton("🗑️ حذف کامل معاهده از دیتابیس", callback_data=f"admin:c_t_del:{country_id}:{contract_id}")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به لیست تجارت‌های کشور", callback_data=f"admin:c_trades:{country_id}:0")])

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# ==================== ۲. زیرمنوی پایگاه‌های نظامی خارجی ====================

async def show_country_bases_menu(query, context, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return

    owned_bases = db.get_bases(owner_id=country_id)
    hosted_bases = db.get_bases(host_id=country_id)

    lines = [
        f"🏰 <b>مدیریت پایگاه‌های نظامی خارجی — {c['flag']} {html.escape(c['name'])}</b>",
        f"پایگاه‌های برون‌مرزی متعلق به کشور: <code>{len(owned_bases)} پایگاه</code>",
        f"پایگاه‌های خارجی مستقر در خاک این کشور: <code>{len(hosted_bases)} پایگاه</code>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        ""
    ]

    keyboard = []
    if owned_bases:
        lines.append("🚩 <b>پایگاه‌های برون‌مرزی متعلق به این کشور:</b>")
        for b in owned_bases:
            host_c = db.get_country_by_id(b["host_id"]) or {}
            h_name = f"{host_c.get('flag','🏳️')} {html.escape(host_c.get('name','نامشخص'))}"
            b_assets = db.get_base_assets(b["id"])
            asset_strs = [f"{a['amount']}x {a['equipment_name']}" for a in b_assets[:3]]
            deployed_str = ", ".join(asset_strs) if asset_strs else "تجهیزاتی مستقر نشده"
            lines.append(f"• <b>پایگاه «{html.escape(b['name'])}»</b> (سطح {b['level']})")
            lines.append(f"  📍 کشور میزبان: {h_name}")
            lines.append(f"  💵 اجاره روزانه: {format_money(b.get('daily_rent', 0))} | روزهای پرداخت‌نشده: {b.get('unpaid_days', 0)}")
            lines.append(f"  🪖 نیروهای مستقر: {deployed_str}")
            lines.append("")
            keyboard.append([
                InlineKeyboardButton(f"🔄 رفع خطر انحلال (Unpaid=0)", callback_data=f"admin:c_base_reset_unpaid:{country_id}:{b['id']}"),
                InlineKeyboardButton(f"💥 انحلال پایگاه «{b['name']}»", callback_data=f"admin:c_base_dissolve:{country_id}:{b['id']}")
            ])
    else:
        lines.append("<i>این کشور هیچ پایگاه نظامی در خارج از مرزهای خود ندارد.</i>")
        lines.append("")

    if hosted_bases:
        lines.append("━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("🌐 <b>پایگاه‌های خارجی مستقر در خاک این کشور:</b>")
        for b in hosted_bases:
            owner_c = db.get_country_by_id(b["owner_id"]) or {}
            o_name = f"{owner_c.get('flag','🏳️')} {html.escape(owner_c.get('name','نامشخص'))}"
            lines.append(f"• <b>پایگاه «{html.escape(b['name'])}»</b>")
            lines.append(f"  👑 کشور مالک: {o_name}")
            lines.append(f"  💵 اجاره روزانه دریافتی: {format_money(b.get('daily_rent', 0))}")
            lines.append("")
            keyboard.append([InlineKeyboardButton(f"🚫 اخراج پایگاه «{b['name']}» از کشور", callback_data=f"admin:c_base_evict:{country_id}:{b['id']}")])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت به داشبورد کشور", callback_data=f"admin:c:{country_id}")])
    await query.edit_message_text(chr(10).join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# ==================== ۳. زیرمنوی برنامه هسته‌ای و موشکی ====================

async def show_country_nuclear_menu(query, context, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return

    eff_cap = db.get_effective_warhead_cap(c)
    nuc_tested = "✅ انجام شده" if c.get("nuclear_tested") else "❌ انجام نشده"
    nuc_susp = "🔴 بله (تعلیق)" if c.get("enrichment_suspended") else "🟢 خیر (فعال)"
    npt_stat = "🚫 خارج شده" if c.get("npt_withdrawn") else "✅ عضو متعهد"
    un_sanc = "🔴 بله (تحریم)" if c.get("un_sanctioned") else "🟢 خیر"

    lines = [
        f"🧪 <b>پرونده استراتژیک و چرخه سوخت هسته‌ای — {c['flag']} {html.escape(c['name'])}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"☢️ <b>ذخیره کیک زرد (Uranium Ore):</b> <code>{format_number(c.get('uranium_ore', 0))} تن</code> (تولید: <code>{c.get('uranium_ore_daily', 0)} تن/روز</code>)",
        f"🧪 <b>سوخت هسته‌ای (۳.۵٪):</b> <code>{format_number(c.get('nuclear_fuel', 0))} kg</code> (تولید: <code>{c.get('nuclear_fuel_daily', 0)} kg/روز</code>)",
        f"🏥 <b>رادیوداروی پزشکی (۲۰٪):</b> <code>{format_number(c.get('medical_isotopes', 0))} دوز</code> (تولید: <code>{c.get('medical_isotopes_daily', 0)}/روز</code>)",
        f"⚛️ <b>اورانیوم غنی‌شده ۶۰٪:</b> <code>{format_number(c.get('enriched_60', 0))} kg</code>",
        f"☢️ <b>اورانیوم نظامی ۹۰٪ (HEU):</b> <code>{format_number(c.get('weapons_grade_90', 0))} kg</code>",
        f"🚀 <b>کلاهک‌های هسته‌ای فعال:</b> <code>{c.get('warheads', 0)} عدد</code> (سقف مجاز: <code>{eff_cap}</code>)",
        f"🏭 <b>سطح تاسیسات غنی‌سازی:</b> <code>سطح {c.get('enrichment_tier', 0)}</code>",
        "",
        "📜 <b>وضعیت‌های حقوقی و بین‌المللی:</b>",
        f"• آزمایش هسته‌ای: {nuc_tested}",
        f"• تعلیق غنی‌سازی: {nuc_susp}",
        f"• عضویت در NPT: {npt_stat}",
        f"• تحریم سازمان ملل: {un_sanc}",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "👇 برای تنظیم یا تغییر هر شاخص، انتخاب بفرمایید:"
    ]
    text = chr(10).join(lines)

    keyboard = [
        [
            InlineKeyboardButton("☢️ تنظیم کیک زرد", callback_data=f"admin:cstat:{country_id}:uranium_ore"),
            InlineKeyboardButton("🧪 تنظیم سوخت هسته‌ای", callback_data=f"admin:cstat:{country_id}:nuclear_fuel"),
        ],
        [
            InlineKeyboardButton("⚛️ تنظیم اورانیوم ۶۰٪", callback_data=f"admin:cstat:{country_id}:enriched_60"),
            InlineKeyboardButton("☢️ تنظیم اورانیوم ۹۰٪ HEU", callback_data=f"admin:cstat:{country_id}:weapons_grade_90"),
        ],
        [
            InlineKeyboardButton("🚀 تنظیم کلاهک‌ها", callback_data=f"admin:cstat:{country_id}:warheads"),
            InlineKeyboardButton("📊 بازنویسی سقف کلاهک", callback_data=f"admin:cstat:{country_id}:warhead_cap_override"),
        ],
        [
            InlineKeyboardButton("🏭 سطح ۰", callback_data=f"admin:c_nuc_tier:{country_id}:0"),
            InlineKeyboardButton("🏭 سطح ۱", callback_data=f"admin:c_nuc_tier:{country_id}:1"),
            InlineKeyboardButton("🏭 سطح ۲", callback_data=f"admin:c_nuc_tier:{country_id}:2"),
            InlineKeyboardButton("🏭 سطح ۳", callback_data=f"admin:c_nuc_tier:{country_id}:3"),
            InlineKeyboardButton("🏭 سطح ۴", callback_data=f"admin:c_nuc_tier:{country_id}:4"),
        ],
        [
            InlineKeyboardButton("⏸️ تغییر تعلیق غنی‌سازی", callback_data=f"admin:c_nuc_suspend:{country_id}"),
            InlineKeyboardButton("📜 تغییر عضویت NPT", callback_data=f"admin:c_nuc_npt:{country_id}"),
        ],
        [
            InlineKeyboardButton("🚫 تغییر تحریم سازمان ملل", callback_data=f"admin:c_nuc_sanction:{country_id}"),
            InlineKeyboardButton("💥 مصادره کلیه کلاهک‌ها", callback_data=f"admin:c_nuc_confiscate:{country_id}"),
        ],
        [InlineKeyboardButton("🔙 بازگشت به داشبورد کشور", callback_data=f"admin:c:{country_id}")]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# ==================== ۴. زیرمنوی تسلیحات نظامی و فرماندهان ====================

async def show_country_military_menu(query, context, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return

    commanders = db.get_country_commanders(country_id)
    naval_power = db.calculate_naval_power(country_id)
    antiship_stock = db.get_antiship_missile_stock(country_id)

    lines = [
        f"🎖️ <b>پرونده تسلیحات، پدافند و فرماندهان — {c['flag']} {html.escape(c['name'])}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"🪖 <b>پرسنل فعال:</b> <code>{format_number(c.get('active_personnel', 0))}</code> | 🎖️ <b>ذخیره:</b> <code>{format_number(c.get('reserve_personnel', 0))}</code>",
        f"⚔️ <b>آمادگی رزمی:</b> <code>{c.get('combat_readiness', 80)}%</code> | 🎯 <b>رزمایش‌های امروز:</b> <code>{c.get('daily_drill_count', 0)}</code>",
        f"⚓ <b>قدرت ناوبری:</b> <code>{format_number(naval_power)} امتیاز</code> | 🛡️ <b>موشک‌های ضدکشتی:</b> <code>{format_number(antiship_stock)} تیر</code>",
        "",
        "👑 <b>کادر فرماندهی و سران نظامی:</b>"
    ]

    keyboard = []
    if commanders:
        for cm in commanders:
            st_icon = "🟢" if cm.get("status") == "active" else "🔴"
            st_desc = "آماده‌باش" if cm.get("status") == "active" else f"ترور شده ({cm.get('killed_at','')[:10]})"
            lines.append(f"• {st_icon} <b>{html.escape(cm['title'])}</b> ({st_desc})")
            
            row = []
            if cm.get("status") != "active":
                row.append(InlineKeyboardButton(f"🟢 احیای {cm['title'][:15]}", callback_data=f"admin:c_cmd_revive:{country_id}:{cm['key']}"))
            else:
                row.append(InlineKeyboardButton(f"🔴 ترور {cm['title'][:15]}", callback_data=f"admin:c_cmd_kill:{country_id}:{cm['key']}"))
            row.append(InlineKeyboardButton("🗑️ حذف", callback_data=f"admin:c_cmd_del:{country_id}:{cm['key']}"))
            keyboard.append(row)
    else:
        lines.append("<i>هیچ فرمانده‌ای برای این کشور ثبت نشده است.</i>")

    keyboard.append([InlineKeyboardButton("➕ انتصاب فرمانده جدید", callback_data=f"admin:c_cmd_add_prompt:{country_id}")])

    # دسته‌بندی‌های دارایی‌های نظامی
    keyboard.append([InlineKeyboardButton("🎖️ ورود به کاتالوگ و ویرایش تسلیحات (Assets)", callback_data=f"admin:menu_assets:{country_id}")])
    keyboard.append([
        InlineKeyboardButton("🪖 تنظیم پرسنل فعال", callback_data=f"admin:cstat:{country_id}:active_personnel"),
        InlineKeyboardButton("⚔️ تنظیم آمادگی رزمی", callback_data=f"admin:cstat:{country_id}:combat_readiness")
    ])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به داشبورد کشور", callback_data=f"admin:c:{country_id}")])

    await query.edit_message_text(chr(10).join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# ==================== ۵. زیرمنوی تراز اقتصاد، تولید و مصرف ====================

async def show_country_economy_menu(query, context, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return

    maint = db.calculate_country_maintenance_cost(country_id)
    mil_fuel = db.calculate_military_fuel_consumption(country_id)
    ind_oil = db.get_industrial_oil_consumption(country_id)
    gross_income = (c.get("daily_income") or 0) + (c.get("tax_income") or 0)
    net_income = gross_income - maint.get("total_maint", 0)
    oil_balance = (c.get("oil_production") or 0) - (mil_fuel + ind_oil)

    lines = [
        f"💰 <b>تراز جامع اقتصاد، انرژی و تولید — {c['flag']} {html.escape(c['name'])}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"🏦 <b>موجودی خزانه:</b> <code>{format_money(c['treasury'])}</code>",
        f"📈 <b>درآمد ناخالص روزانه:</b> <code>{format_money(gross_income)}</code> (مالیات: <code>{format_money(c.get('tax_income', 0))}</code>)",
        f"💸 <b>هزینه نگهداری کل ارتش:</b> <code>{format_money(maint['total_maint'])}</code> (تخفیف VIP: <code>{maint['vip_discount_pct']}%</code>)",
        f"💵 <b>تراز خالص روزانه:</b> <code>{format_money(net_income)}/روز</code>",
        "",
        "🛢️ <b>تراز انرژی و نفت:</b>",
        f"• ذخایر فعلی: <code>{format_oil(c['oil_reserves'])}</code>",
        f"• نرخ تولید: <code>{format_oil(c['oil_production'])}/روز</code>",
        f"• مصرف ادوات نظامی: <code>{format_oil(mil_fuel)}/روز</code>",
        f"• مصرف کارخانجات: <code>{format_oil(ind_oil)}/روز</code>",
        f"• تراز خالص نفت: <code>{format_oil(oil_balance)}/روز</code>",
        "",
        f"🌾 <b>غلات:</b> <code>{format_number(c['grain'])} تن</code> (تولید: <code>{c.get('grain_daily', 0)} تن/روز</code>)",
        f"⚡ <b>شبکه برق:</b> <code>{c.get('electricity', 0)} MW</code> | 🪙 <b>طلا:</b> <code>{c.get('gold', 0)} شمش</code>",
        f"💻 <b>میکروچیپ:</b> <code>{format_number(c.get('microchips', 0))} چیپ</code> (تولید: <code>{c.get('microchips_daily', 0)}/روز</code>)",
        f"👥 <b>جمعیت:</b> <code>{format_number(c['population'])}</code> | 😀 <b>رضایت:</b> <code>{c.get('approval_rating', 80)}%</code>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "👇 جهت تنظیم یا ویرایش هر یک از شاخص‌ها انتخاب بفرمایید:"
    ]
    text = chr(10).join(lines)

    keyboard = [
        [
            InlineKeyboardButton("🏦 ویرایش خزانه", callback_data=f"admin:menu_treasury:{country_id}"),
            InlineKeyboardButton("🪙 ویرایش طلا", callback_data=f"admin:menu_gold:{country_id}"),
        ],
        [
            InlineKeyboardButton("🛢️ ویرایش نفت و تولید", callback_data=f"admin:menu_oil:{country_id}"),
            InlineKeyboardButton("🌾 ویرایش غلات", callback_data=f"admin:cstat:{country_id}:grain"),
        ],
        [
            InlineKeyboardButton("⚡ توان برق", callback_data=f"admin:cstat:{country_id}:electricity"),
            InlineKeyboardButton("💻 میکروچیپ", callback_data=f"admin:cstat:{country_id}:microchips"),
        ],
        [
            InlineKeyboardButton("👥 جمعیت", callback_data=f"admin:cstat:{country_id}:population"),
            InlineKeyboardButton("😀 رضایت عمومی", callback_data=f"admin:cstat:{country_id}:approval_rating"),
        ],
        [
            InlineKeyboardButton("🏗️ مدیریت ساخت‌وسازها و کارخانجات", callback_data=f"admin:c_civ_constructions:{country_id}"),
            InlineKeyboardButton("⚙️ ویرایش تفصیلی فیلدها", callback_data=f"admin:cstatmenu:{country_id}"),
        ],
        [
            InlineKeyboardButton("🔙 بازگشت به داشبورد کشور", callback_data=f"admin:c:{country_id}"),
        ]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def show_country_constructions_menu(query, context, country_id: int):
    """مدیریت و مشاهده تمام کارخانجات، زیرساخت‌ها و ساخت‌وسازهای غیرنظامی کشور."""
    c = db.get_country_by_id(country_id)
    if not c:
        return

    equipment = db.get_equipment(country_id)
    c_name_esc = html.escape(c["name"])
    lines = [
        f"🏗️ <b>پروژه‌ها و ساخت‌وسازهای غیرنظامی — {c['flag']} {c_name_esc}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "در زیر لیست تمام ساختمان‌ها، کارخانجات، نیروگاه‌ها و مزارع احداث‌شده این کشور را مشاهده می‌فرمایید:\n"
    ]

    keyboard = []
    has_any = False
    for item_key, qty in equipment.items():
        if qty > 0 and item_key in config.ALL_SHOP_ITEMS:
            has_any = True
            item_data = config.ALL_SHOP_ITEMS[item_key]
            lines.append(f"• <b>{item_data['name']}:</b> <code>{qty:,}</code> واحد")
            keyboard.append([
                InlineKeyboardButton(f"🏗️ {item_data['name']} ({qty:,})", callback_data="ignore"),
            ])
            row = [
                InlineKeyboardButton("➖ ۱", callback_data=f"admin:c_civ_adj:{country_id}:{item_key}:-1"),
                InlineKeyboardButton("➕ ۱", callback_data=f"admin:c_civ_adj:{country_id}:{item_key}:1"),
                InlineKeyboardButton("➕ ۵", callback_data=f"admin:c_civ_adj:{country_id}:{item_key}:5"),
            ]
            # برای تعدادهای بزرگ، گام‌های درشت هم نشان بده
            if qty >= 10:
                row.insert(0, InlineKeyboardButton("➖ ۱۰", callback_data=f"admin:c_civ_adj:{country_id}:{item_key}:-10"))
            if qty >= 100:
                row.insert(0, InlineKeyboardButton("➖ ۱۰۰", callback_data=f"admin:c_civ_adj:{country_id}:{item_key}:-100"))
            keyboard.append(row)
            keyboard.append([
                InlineKeyboardButton("🗑️ صفر کن", callback_data=f"admin:c_civ_zero:{country_id}:{item_key}"),
                InlineKeyboardButton("✏️ تعیین عدد دقیق", callback_data=f"admin:c_civ_set:{country_id}:{item_key}"),
            ])

    if not has_any:
        lines.append("❌ <i>هیچ ساخت‌وساز یا کارخانه‌ای برای این کشور ثبت نشده است.</i>\n")

    lines.append("\n💡 <i>می‌توانید با دکمه‌های زیر، هر پروژه جدیدی را فوراً به کشور اضافه فرمایید:</i>")

    keyboard.append([
        InlineKeyboardButton("➕ پالایشگاه نفت", callback_data=f"admin:c_civ_adj:{country_id}:oil_refinery:1"),
        InlineKeyboardButton("➕ کارخانه فب تراشه", callback_data=f"admin:c_civ_adj:{country_id}:chip_fab:1"),
    ])
    keyboard.append([
        InlineKeyboardButton("➕ مجتمع کشاورزی", callback_data=f"admin:c_civ_adj:{country_id}:agro_complex:1"),
        InlineKeyboardButton("➕ نیروگاه فسیلی", callback_data=f"admin:c_civ_adj:{country_id}:fossil_plant:1"),
    ])
    keyboard.append([
        InlineKeyboardButton("➕ مجتمع صنعتی", callback_data=f"admin:c_civ_adj:{country_id}:industrial_complex:1"),
        InlineKeyboardButton("➕ سیلوی غلات", callback_data=f"admin:c_civ_adj:{country_id}:grain_silo:1"),
    ])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اقتصاد", callback_data=f"admin:c_economy:{country_id}")])

    await query.edit_message_text(chr(10).join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# ==================== ۶. زیرمنوی دیپلماسی، پیمان‌ها و تحریم‌ها ====================

async def show_country_diplomacy_menu(query, context, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return

    relations = db.get_country_diplomatic_relations_all(country_id)
    blockades = db.get_active_blockades_for_country(country_id)

    lines = [
        f"🤝 <b>پرونده دیپلماسی، پیمان‌ها و تحریم‌ها — {c['flag']} {html.escape(c['name'])}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        ""
    ]

    keyboard = []
    if blockades:
        lines.append("⚓ <b>وضعیت محاصره‌های دریایی:</b>")
        for b in blockades:
            b_c = db.get_country_by_id(b["blockader_id"]) or {}
            t_c = db.get_country_by_id(b["target_id"]) or {}
            if b["blockader_id"] == country_id:
                lines.append(f"• 🛑 محاصره اعمال‌شده توسط شما علیه: {t_c.get('flag','🏳️')} {html.escape(t_c.get('name',''))}")
                keyboard.append([InlineKeyboardButton(f"⚓ پایان دادن به محاصره {t_c.get('name','')}", callback_data=f"admin:c_lift_blockade:{country_id}:{b['target_id']}")])
            else:
                lines.append(f"• ⚠️ کشور شما تحت محاصره دریایی توسط: {b_c.get('flag','🏳️')} {html.escape(b_c.get('name',''))}")
                keyboard.append([InlineKeyboardButton(f"⚓ شکستن فوری محاصره اعمال‌شده توسط {b_c.get('name','')}", callback_data=f"admin:c_lift_blockade:{country_id}:{b['blockader_id']}")])
        lines.append("")

    if relations:
        lines.append("🌐 <b>وضعیت روابط با سایر کشورها:</b>")
        for r in relations:
            other_name = r["c2_name"] if r["country1_id"] == country_id else r["c1_name"]
            other_flag = r["c2_flag"] if r["country1_id"] == country_id else r["c1_flag"]
            st_fa = {"allied": "🟢 متحد استراتژیک", "nap": "🤝 پیمان عدم تعرض", "at_war": "⚔️ در حال جنگ", "sanctioned": "🚫 تحریم"}.get(r["status"], r["status"])
            lines.append(f"• {other_flag} <b>{html.escape(other_name)}:</b> {st_fa}")
    else:
        lines.append("<i>روابط دیپلماتیک ویژه‌ای (اتحاد، جنگ یا تحریم) ثبت نشده است.</i>")

    keyboard.append([InlineKeyboardButton("🔙 بازگشت به داشبورد کشور", callback_data=f"admin:c:{country_id}")])
    await query.edit_message_text(chr(10).join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# ==================== ۷. زیرمنوی اطلاعات، سایبری و امنیت ====================

async def show_country_intel_menu(query, context, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return

    agency_info = db.get_intel_agency_info(c.get("country_key") or "")
    att_score, def_score = db.get_country_intel_attack_defense(country_id)
    history = db.get_country_intel_history(country_id, 5)

    now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
    ad_dis = (c.get("air_defense_disrupted_until") or "")
    bo_dis = (c.get("blackout_until") or "")
    rd_dis = (c.get("r_and_d_frozen_until") or "")
    cmd_dis = (c.get("command_disrupted_until") or "")

    lines = [
        f"🕵️ <b>پرونده سرویس اطلاعاتی و امنیت سایبری — {c['flag']} {html.escape(c['name'])}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"🛡️ <b>نام سازمان اطلاعاتی:</b> {html.escape(agency_info.get('agency_name','سرویس اطلاعات ملی'))}",
        f"🔒 <b>سطح فایروال سایبری:</b> <code>سطح {c.get('firewall_level', 0)} از ۵</code>",
        f"⚔️ <b>قدرت تهاجم اطلاعاتی:</b> <code>{att_score} امتیاز</code> | 🛡️ <b>قدرت ضدجاسوسی:</b> <code>{def_score} امتیاز</code>",
        f"🎯 <b>عملیات‌های انجام‌شده امروز:</b> <code>{c.get('intel_ops_today', 0)} از ۲ مجاز</code>",
        "",
        "⚡ <b>وضعیت نفوذها و اختلالات سایبری فعال:</b>",
        f"• پدافند هوایی: {f'🔴 مختل تا <code>{ad_dis[:16]}</code>' if ad_dis > now_utc else '🟢 فعال و عادی'}",
        f"• شبکه سراسری برق: {f'🔴 خاموشی تا <code>{bo_dis[:16]}</code>' if bo_dis > now_utc else '🟢 متصل و عادی'}",
        f"• تحقیقات و فناوری: {f'🔴 منجمد تا <code>{rd_dis[:16]}</code>' if rd_dis > now_utc else '🟢 فعال و عادی'}",
        f"• فرماندهی و ارتباطات: {f'🔴 مختل تا <code>{cmd_dis[:16]}</code>' if cmd_dis > now_utc else '🟢 متصل و عادی'}",
        ""
    ]

    if history:
        lines.append("📜 <b>آخرین عملیات‌های اطلاعاتی مرتبط:</b>")
        for h in history:
            res_icon = "✅" if h["result"] == "success" else "❌"
            dt_str = str(h.get("created_at",""))[:16].replace("T"," ")
            lines.append(f"• {res_icon} <code>{dt_str}</code> | <b>{h['op_type']}</b> ({h['result']}) | {html.escape(h.get('details','')[:40])}")

    keyboard = [
        [InlineKeyboardButton("🧹 پاکسازی فوری کلیه اختلالات و خاموشی‌ها", callback_data=f"admin:c_clear_cyber:{country_id}")],
        [
            InlineKeyboardButton("🔒 تنظیم فایروال", callback_data=f"admin:cstat:{country_id}:firewall_level"),
            InlineKeyboardButton("🔄 ریست محدودیت عملیات‌های امروز", callback_data=f"admin:c_reset_intel_limit:{country_id}")
        ],
        [InlineKeyboardButton("🔙 بازگشت به داشبورد کشور", callback_data=f"admin:c:{country_id}")]
    ]

    await query.edit_message_text(chr(10).join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# ==================== ۸. زیرمنوی تاریخچه تلفات و جنگ‌ها ====================

async def show_country_losses_menu(query, context, country_id: int, page: int = 0):
    c = db.get_country_by_id(country_id)
    if not c:
        return

    losses = db.get_loss_reports(country_id=country_id)
    stats = db.get_loss_stats(country_id)

    per_page = 4
    total_pages = max(1, math.ceil(len(losses) / per_page)) if losses else 1
    page = max(0, min(page, total_pages - 1))
    page_losses = losses[page * per_page : (page + 1) * per_page] if losses else []

    lines = [
        f"💥 <b>تاریخچه تلفات و خسارات جنگی — {c['flag']} {html.escape(c['name'])}</b>",
        f"مجموع گزارش‌های ثبت‌شده: <code>{stats.get('reports', 0)} گزارش</code> | کل ادوات منهدم‌شده: <code>{stats.get('total', 0)} واحد</code>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        ""
    ]

    if not losses:
        lines.append("<i>هیچ گزارش تلفات نظامی برای این کشور ثبت نشده است.</i>")
        lines.append("")
    else:
        for r in page_losses:
            dt_str = str(r.get("created_at",""))[:16].replace("T"," ")
            st_str = "🟢 ثبت شده" if r.get("status") == "applied" else "↩️ عودت داده شده"
            lines.append(f"📄 <b>گزارش #{r['id']}: {html.escape(r.get('operation_name') or 'عملیات نظامی')}</b> ({st_str})")
            lines.append(f"• تاریخ: <code>{dt_str}</code> | ادمین: <code>{r.get('admin_id')}</code>")
            lines.append(f"• یادداشت: {html.escape(r.get('note') or '—')}")
            lines.append("")

    keyboard = []
    for r in page_losses:
        if r.get("status") == "applied":
            keyboard.append([
                InlineKeyboardButton(f"↩️ عودت تجهیزات گزارش #{r['id']}", callback_data=f"admin:c_loss_revert:{country_id}:{r['id']}"),
                InlineKeyboardButton(f"🗑️ حذف #{r['id']}", callback_data=f"admin:c_loss_del:{country_id}:{r['id']}")
            ])
        else:
            keyboard.append([InlineKeyboardButton(f"🗑️ حذف گزارش عودت‌شده #{r['id']}", callback_data=f"admin:c_loss_del:{country_id}:{r['id']}")])

    nav_row = []
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:c_losses:{country_id}:{page - 1}"))
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(f"صفحه {page + 1} از {total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:c_losses:{country_id}:{page + 1}"))
    if nav_row:
        keyboard.append(nav_row)

    keyboard.append([InlineKeyboardButton("🔙 بازگشت به داشبورد کشور", callback_data=f"admin:c:{country_id}")])
    await query.edit_message_text(chr(10).join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# ==================== ۹. زیرمنوی بیانیه‌ها و رصد فعالیت ====================

async def show_country_statements_menu(query, context, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return

    today_count = db.get_country_statement_count_today(country_id)
    stmts = db.get_country_statements_history(country_id, 6)

    if today_count >= config.REQUIRED_DAILY_STATEMENTS:
        status_msg = "🟢 <b>دارای مصونیت کامل فعالیت روزانه</b> (حداقل ۲ بیانیه ثبت شده است)"
    elif today_count == 1:
        status_msg = "🟡 <b>هشدار: نیازمند ۱ بیانیه دیگر تا ساعت ۰۰:۰۰ بامداد</b>"
    else:
        status_msg = "🔴 <b>خطر جدی: عدم فعالیت — در معرض خلع ید در ساعت ۰۰:۰۰ نیمه‌شب</b>"

    lines = [
        f"📝 <b>رصد بیانیه‌ها و فعالیت روزانه — {c['flag']} {html.escape(c['name'])}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"📊 <b>تعداد بیانیه‌های امروز:</b> <code>{today_count} از {config.REQUIRED_DAILY_STATEMENTS} اجباری</code>",
        f"🛡️ <b>وضعیت فعالیت:</b> {status_msg}",
        "",
        "📜 <b>آخرین بیانیه‌ها و توییت‌های ثبت‌شده:</b>"
    ]

    if stmts:
        for s in stmts:
            dt_str = str(s.get("created_at",""))[:16].replace("T"," ")
            lines.append(f"• <code>{dt_str}</code> | <b>[{s.get('statement_type','بیانیه')}]:</b> {html.escape(s.get('content','')[:60])}...")
    else:
        lines.append("<i>هیچ بیانیه‌ای در دیتابیس برای این کشور ثبت نشده است.</i>")

    keyboard = [
        [InlineKeyboardButton("➕ ثبت دستی بیانیه (اعطای مصونیت فعالیت)", callback_data=f"admin:c_stmt_add:{country_id}")],
        [InlineKeyboardButton("🔄 ریست بیانیه‌های امروز", callback_data=f"admin:c_stmt_reset:{country_id}")],
        [InlineKeyboardButton("🔙 بازگشت به داشبورد کشور", callback_data=f"admin:c:{country_id}")]
    ]

    await query.edit_message_text(chr(10).join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# ==================== ۱۰. زیرمنوی پرونده مالی، VIP و تراکنش‌ها ====================

# ---------- کاتالوگ آیتم‌های قابل اعطا توسط ادمین ----------
# هر دسته: (عنوان دسته، [(کلید آیتم، برچسب دکمه), ...])
# کلیدها دقیقاً همان item_type های PLANS_METADATA و approve_payment_request هستند.
GRANT_CATEGORIES = {
    "survival": (
        "🎁 بسته‌های بقا و لجستیک",
        [
            ("survival_small", "🟤 بسته بقا کوچک"),
            ("survival_medium", "🟠 بسته بقا متوسط"),
            ("survival_large", "🔴 بسته بقا بزرگ"),
            ("survival_ultra", "💎 بسته بقا فوق‌سنگین"),
        ],
    ),
    "ticket": (
        "🎫 بلیط‌های اقدام فوری",
        [
            ("ticket_drill", "🎫 ۱ مانور اضافه"),
            ("ticket_drill_3", "🎫 پک ۳ تایی مانور"),
            ("ticket_statement", "📝 ۱ بیانیه اضافه"),
            ("ticket_statement_5", "📝 پک ۵ تایی بیانیه"),
            ("ticket_contract_3d", "📜 اسلات قرارداد ۳ روزه"),
            ("ticket_contract_7d", "📜 اسلات قرارداد ۷ روزه"),
        ],
    ),
    "bp": (
        "⭐️ بتل‌پس و بوسترها",
        [
            ("battle_pass", "⭐️ بتل‌پس پرمیوم فصلی"),
            ("bp_booster_3d", "⚡ بوستر ۲x — ۳ روزه"),
            ("bp_booster_7d", "⚡ بوستر ۲x — ۷ روزه"),
            ("bp_booster_30d", "⚡ بوستر ۲x — ۳۰ روزه"),
        ],
    ),
    "visibility": (
        "📢 خدمات دیده شدن و پرستیژ",
        [
            ("golden_stmt_1", "📢 ۱ بیانیه طلایی"),
            ("golden_stmt_3", "📢 پک ۳ تایی بیانیه طلایی"),
            ("golden_stmt_10", "📢 پک ۱۰ تایی بیانیه طلایی"),
            ("pin_1", "📌 ۱ پین گروه ۱۲ ساعته"),
            ("pin_3", "📌 پک ۳ تایی پین گروه"),
            ("frame_7d", "🖼️ قاب طلایی ۷ روزه"),
            ("frame_30d", "🖼️ قاب طلایی ۳۰ روزه"),
            ("title_7d", "🏷️ عنوان تشریفاتی ۷ روزه"),
            ("title_30d", "🏷️ عنوان تشریفاتی ۳۰ روزه"),
        ],
    ),
}

# آیتم‌هایی که پیش از اعطا نیاز به دریافت متن دلخواه از ادمین دارند
GRANT_NEEDS_TEXT = {"title_7d", "title_30d"}


def _grant_item_label(item_key: str) -> str:
    """برچسب فارسی آیتم را از کاتالوگ محلی یا PLANS_METADATA برمی‌گرداند."""
    for _cat_title, items in GRANT_CATEGORIES.values():
        for key, label in items:
            if key == item_key:
                return label
    try:
        from handlers.vip import PLANS_METADATA
        return PLANS_METADATA.get(item_key, {}).get("title", item_key)
    except Exception:
        return item_key


def _fmt_until(raw) -> str:
    """نمایش خوانای تاریخ انقضا؛ اگر گذشته باشد «منقضی» برمی‌گرداند."""
    if not raw:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(str(raw))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        if dt <= datetime.datetime.now(datetime.timezone.utc):
            return "منقضی"
        return str(raw)[:16].replace("T", " ")
    except Exception:
        return str(raw)[:16].replace("T", " ")


def _format_entitlements_block(c: dict) -> str:
    """بلوک HTML وضعیت فعلی آیتم‌های خریدنی (بلیط‌ها، بوسترها و خدمات ظاهری)."""
    rows = []

    drill = c.get("drill_tickets") or 0
    stmt = c.get("statement_tickets") or 0
    golden = c.get("golden_stmt_credits") or 0
    pin = c.get("pin_credits") or 0
    if drill or stmt or golden or pin:
        rows.append(
            f"• <b>بلیط‌ها:</b> مانور <code>{drill}</code> | بیانیه <code>{stmt}</code> | "
            f"بیانیه طلایی <code>{golden}</code> | پین <code>{pin}</code>"
        )

    contract = _fmt_until(c.get("contract_boost_until"))
    if contract:
        rows.append(f"• <b>بوست اسلات قرارداد:</b> <code>{contract}</code>")

    booster = _fmt_until(c.get("bp_booster_until"))
    if booster:
        mult = c.get("bp_booster_mult") or 1
        rows.append(f"• <b>بوستر بتل‌پس:</b> <code>{mult}x</code> تا <code>{booster}</code>")

    frame = _fmt_until(c.get("golden_frame_until"))
    if frame:
        rows.append(f"• <b>قاب طلایی:</b> <code>{frame}</code>")

    title_txt = c.get("custom_title")
    if title_txt:
        rows.append(
            f"• <b>عنوان تشریفاتی:</b> {html.escape(str(title_txt))} "
            f"(تا <code>{_fmt_until(c.get('title_expires_at')) or 'نامحدود'}</code>)"
        )

    if not rows:
        return "🛒 <b>آیتم‌های فعال فروشگاه:</b> <i>موردی فعال نیست.</i>\n"
    return "🛒 <b>آیتم‌های فعال فروشگاه:</b>\n" + chr(10).join(rows) + "\n"


async def _notify_player_of_grant(context, country_id: int, item_label: str):
    """اطلاع‌رسانی به بازیکن پس از اعطای آیتم توسط ادمین (خطا نباید جریان ادمین را قطع کند)."""
    try:
        c = db.get_country_by_id(country_id)
        if not c or not c.get("player_id"):
            return
        await context.bot.send_message(
            chat_id=c["player_id"],
            text=(
                "🎁 <b>هدیه‌ای از سوی مدیریت بازی برای شما فعال شد!</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"📦 <b>آیتم:</b> {html.escape(item_label)}\n\n"
                "✅ این مورد هم‌اکنون روی کشور شما اعمال شده است."
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"Failed to notify player of admin grant: {e}")


async def show_country_grant_menu(query, context, country_id: int):
    """منوی انتخاب دستهٔ آیتم برای اعطای مستقیم توسط ادمین."""
    c = db.get_country_by_id(country_id)
    if not c:
        return

    lines = [
        f"🛒 <b>اعطای آیتم فروشگاه — {c['flag']} {html.escape(c['name'])}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "آیتم اعطا شده <b>بدون دریافت وجه</b> و بلافاصله برای کشور فعال می‌شود،",
        "و با مبلغ صفر و برچسب <code>ADMIN_GRANT</code> در سوابق مالی ثبت می‌گردد.",
        "",
        _format_entitlements_block(c),
        "👇 <b>دسته مورد نظر را انتخاب کنید:</b>",
    ]

    keyboard = [
        [InlineKeyboardButton(title, callback_data=f"admin:c_grant_cat:{country_id}:{cat_key}")]
        for cat_key, (title, _items) in GRANT_CATEGORIES.items()
    ]
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به پرونده مالی", callback_data=f"admin:c_vip_finance:{country_id}")])

    await query.edit_message_text(chr(10).join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def show_country_grant_category(query, context, country_id: int, cat_key: str):
    """فهرست آیتم‌های یک دسته برای اعطا."""
    c = db.get_country_by_id(country_id)
    if not c or cat_key not in GRANT_CATEGORIES:
        return

    cat_title, items = GRANT_CATEGORIES[cat_key]
    try:
        from handlers.vip import PLANS_METADATA
    except Exception:
        PLANS_METADATA = {}

    lines = [
        f"{cat_title} — {c['flag']} {html.escape(c['name'])}",
        "━━━━━━━━━━━━━━━━━━━━━━",
        "",
    ]
    for key, label in items:
        price = PLANS_METADATA.get(key, {}).get("price")
        price_str = f" — ارزش <code>{price:,}</code> ت" if price else ""
        lines.append(f"• <b>{html.escape(label)}</b>{price_str}")
    lines.append("")
    lines.append("👇 برای اعطای فوری روی آیتم کلیک کنید:")

    keyboard = [
        [InlineKeyboardButton(label, callback_data=f"admin:c_grant:{country_id}:{key}")]
        for key, label in items
    ]
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به دسته‌ها", callback_data=f"admin:c_grant_menu:{country_id}")])

    await query.edit_message_text(chr(10).join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


async def show_country_vip_finance_menu(query, context, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return

    vip_val = str(c.get("vip_tier") or c.get("is_vip") or "0")
    if vip_val == "1":
        vip_val = "gold"
    vip_tier_key = f"vip_{vip_val}" if not vip_val.startswith("vip_") else vip_val
    if vip_tier_key in config.VIP_TIERS:
        v_info = config.VIP_TIERS[vip_tier_key]
        v_exp = (c.get("vip_expires_at") or "نامحدود")[:10]
        vip_str = f"{v_info.get('badge', '⭐')} <b>{v_info.get('title', 'VIP')}</b> (انقضا: <code>{v_exp}</code>)"
    else:
        vip_str = "👤 <b>کاربر عادی (بدون اشتراک VIP)</b>"

    payments = db.get_country_payment_history(country_id, 4)
    txs = db.get_country_transactions(country_id, 4)

    lines = [
        f"💳 <b>پرونده مالی و اشتراک VIP — {c['flag']} {html.escape(c['name'])}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"👑 <b>سطح اشتراک فعلی:</b> {vip_str}",
        ""
    ]

    if payments:
        lines.append("💳 <b>سوابق فیش‌های پرداخت تومانی:</b>")
        for p in payments:
            st_fa = "✅ تایید شده" if p["status"] == "approved" else ("❌ رد شده" if p["status"] == "rejected" else "⏳ در انتظار")
            dt_str = str(p.get("created_at",""))[:16].replace("T"," ")
            lines.append(f"• <b>#{p['id']}:</b> {p['plan_title']} ({p['amount_toman']:,} ت) — {st_fa} (<code>{dt_str}</code>)")
        lines.append("")

    lines.append(_format_entitlements_block(c))

    if txs:
        lines.append("📜 <b>آخرین تراکنش‌های اقتصادی دیتابیس:</b>")
        for tx in txs:
            lines.append(f"• {format_money(tx.get('amount', 0))} | {html.escape(tx.get('description',''))}")
    else:
        lines.append("<i>تراکنشی ثبت نشده است.</i>")

    keyboard = [
        [
            InlineKeyboardButton("💎 VIP الماس (۳۰ روز)", callback_data=f"admin:c_set_vip:{country_id}:vip_diamond:30"),
            InlineKeyboardButton("🥇 VIP طلایی (۳۰ روز)", callback_data=f"admin:c_set_vip:{country_id}:vip_gold:30"),
        ],
        [
            InlineKeyboardButton("🥈 VIP نقره‌ای (۳۰ روز)", callback_data=f"admin:c_set_vip:{country_id}:vip_silver:30"),
            InlineKeyboardButton("🥉 VIP برنز (۳۰ روز)", callback_data=f"admin:c_set_vip:{country_id}:vip_bronze:30"),
        ],
        [InlineKeyboardButton("🚫 لغو اشتراک VIP", callback_data=f"admin:c_revoke_vip:{country_id}")],
        [InlineKeyboardButton("🛒 اعطای سایر آیتم‌های فروشگاه", callback_data=f"admin:c_grant_menu:{country_id}")],
        [InlineKeyboardButton("🔙 بازگشت به داشبورد کشور", callback_data=f"admin:c:{country_id}")]
    ]

    await query.edit_message_text(chr(10).join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# ==================== ۱۱. زیرمنوی مدیریت پیشرفته و تغییر مالکیت ====================

async def show_country_godmode_menu(query, context, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return

    u_display = f"@{html.escape(c['username'])}" if c.get("username") else "بدون یوزرنیم"

    lines = [
        f"⚡ <b>ابزارهای مدیریت عالی و تغییر مالکیت — {c['flag']} {html.escape(c['name'])}</b>",
        "━━━━━━━━━━━━━━━━━━━━━━",
        f"👤 <b>مالک فعلی:</b> {u_display} (ID: <code>{c['player_id']}</code>)",
        f"🏷️ <b>نام و پرچم:</b> {c['flag']} {html.escape(c['name'])}",
        f"🔬 <b>سطح فناوری (Tech Level):</b> <code>سطح {c.get('tech_level', 1)}</code>",
        "",
        "از گزینه‌های زیر برای اعمال تغییرات ساختاری بر روی کشور استفاده فرمایید:"
    ]
    text = chr(10).join(lines)

    keyboard = [
        [InlineKeyboardButton("👤 واگذاری مالکیت به بازیکن جدید", callback_data=f"admin:c_transfer_prompt:{country_id}")],
        [InlineKeyboardButton("✏️ تغییر نام و پرچم کشور", callback_data=f"admin:c_rename_prompt:{country_id}")],
        [
            InlineKeyboardButton("💰 تزریق ۱۰۰M$ + ۱M نفت", callback_data=f"admin:c_boost_econ:{country_id}"),
            InlineKeyboardButton("🪖 تزریق ۵۰k نیرو + ۲۰٪ آمادگی", callback_data=f"admin:c_boost_mil:{country_id}")
        ],
        [
            InlineKeyboardButton("⭐️ ارتقای لول بتل‌پس (+1)", callback_data=f"admin:c_bp_plus:{country_id}"),
            InlineKeyboardButton("👑 فعال‌سازی پرمیوم بتل‌پس", callback_data=f"admin:c_bp_unlock:{country_id}")
        ],
        [InlineKeyboardButton("🔬 تنظیم سطح فناوری (Tech Level)", callback_data=f"admin:cstat:{country_id}:tech_level")],
        [InlineKeyboardButton("🗑️ حذف کامل کشور", callback_data=f"admin:delconfirm:{country_id}")],
        [InlineKeyboardButton("🔙 بازگشت به داشبورد کشور", callback_data=f"admin:c:{country_id}")]
    ]

    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")


# ==================== پردازشگرهای Callback و Input متمرکز پرونده ادمین ====================

async def handle_dossier_callbacks(query, context, data: str) -> bool:
    """پردازش کلیه CallbackQuery های مربوط به پرونده همه‌جانبه کشور."""
    if data.startswith("admin:c_trades:"):
        parts = data.split(":")
        cid = int(parts[2])
        page = int(parts[3]) if len(parts) > 3 else 0
        await show_country_trades_menu(query, context, cid, page)
        return True

    elif data.startswith("admin:c_tview:"):
        parts = data.split(":")
        cid = int(parts[2])
        contract_id = int(parts[3])
        await show_country_trade_detail(query, context, cid, contract_id)
        return True

    elif data.startswith("admin:c_t_exec:"):
        parts = data.split(":")
        cid = int(parts[2])
        contract_id = int(parts[3])
        succ, msg = db.execute_trade_contract_transaction(contract_id)
        await query.answer(f"{'✅' if succ else '❌'} {msg}", show_alert=True)
        await show_country_trade_detail(query, context, cid, contract_id)
        return True

    elif data.startswith("admin:c_t_cancel:"):
        parts = data.split(":")
        cid = int(parts[2])
        contract_id = int(parts[3])
        succ, msg = db.admin_cancel_trade_contract(contract_id)
        await query.answer(msg, show_alert=True)
        await show_country_trade_detail(query, context, cid, contract_id)
        return True

    elif data.startswith("admin:c_t_del:"):
        parts = data.split(":")
        cid = int(parts[2])
        contract_id = int(parts[3])
        succ, msg = db.admin_delete_trade_contract(contract_id)
        await query.answer(msg, show_alert=True)
        await show_country_trades_menu(query, context, cid, 0)
        return True

    elif data.startswith("admin:c_morder_cancel:"):
        parts = data.split(":")
        cid = int(parts[2])
        order_id = int(parts[3])
        succ, msg = db.admin_cancel_market_order(order_id)
        await query.answer(msg, show_alert=True)
        await show_country_trades_menu(query, context, cid, 0)
        return True

    elif data.startswith("admin:c_bases:"):
        cid = int(data.split(":")[2])
        await show_country_bases_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_base_reset_unpaid:"):
        parts = data.split(":")
        cid = int(parts[2])
        base_id = int(parts[3])
        conn = db.get_connection()
        try:
            with conn:
                conn.execute("UPDATE foreign_bases SET unpaid_days = 0 WHERE id = ?", (base_id,))
        finally:
            conn.close()
        await query.answer("روزهای پرداخت‌نشده صفر شد و خطر انحلال پایگاه برطرف گردید!", show_alert=True)
        await show_country_bases_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_base_dissolve:"):
        parts = data.split(":")
        cid = int(parts[2])
        base_id = int(parts[3])
        db.dissolve_base(base_id)
        await query.answer("پایگاه با موفقیت منحل شد و نیروها به کشور بازگشتند.", show_alert=True)
        await show_country_bases_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_base_evict:"):
        parts = data.split(":")
        cid = int(parts[2])
        base_id = int(parts[3])
        db.evict_base(base_id)
        await query.answer("پایگاه خارجی از خاک کشور اخراج گردید.", show_alert=True)
        await show_country_bases_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_nuclear:"):
        cid = int(data.split(":")[2])
        await show_country_nuclear_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_nuc_tier:"):
        parts = data.split(":")
        cid = int(parts[2])
        tier = int(parts[3])
        db.update_country_field(cid, "enrichment_tier", tier)
        await query.answer(f"سطح تاسیسات غنی‌سازی به سطح {tier} تنظیم شد.", show_alert=True)
        await show_country_nuclear_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_nuc_suspend:"):
        cid = int(data.split(":")[2])
        c = db.get_country_by_id(cid)
        new_sus = not bool(c.get("enrichment_suspended"))
        db.set_enrichment_suspended(cid, new_sus)
        await query.answer("وضعیت تعلیق غنی‌سازی تغییر یافت.", show_alert=True)
        await show_country_nuclear_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_nuc_npt:"):
        cid = int(data.split(":")[2])
        c = db.get_country_by_id(cid)
        new_npt = not bool(c.get("npt_withdrawn"))
        db.set_npt_withdrawn(cid, new_npt)
        await query.answer("وضعیت عضویت در NPT تغییر یافت.", show_alert=True)
        await show_country_nuclear_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_nuc_sanction:"):
        cid = int(data.split(":")[2])
        c = db.get_country_by_id(cid)
        new_sanc = not bool(c.get("un_sanctioned"))
        db.set_un_sanctioned(cid, new_sanc, "تصمیم ادمین")
        await query.answer("وضعیت تحریم سازمان ملل تغییر یافت.", show_alert=True)
        await show_country_nuclear_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_nuc_confiscate:"):
        cid = int(data.split(":")[2])
        cnt = db.confiscate_warheads(cid, "مصادره توسط مدیریت ستاد")
        await query.answer(f"{cnt} کلاهک هسته‌ای مصادره گردید.", show_alert=True)
        await show_country_nuclear_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_military:"):
        cid = int(data.split(":")[2])
        await show_country_military_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_cmd_revive:"):
        parts = data.split(":")
        cid = int(parts[2])
        key = parts[3]
        db.revive_commander(cid, key)
        await query.answer("فرمانده با موفقیت احیا شد.", show_alert=True)
        await show_country_military_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_cmd_kill:"):
        parts = data.split(":")
        cid = int(parts[2])
        key = parts[3]
        db.kill_commander(cid, key, "ترور توسط مدیریت بازی")
        await query.answer("فرمانده ترور و غیرفعال گردید.", show_alert=True)
        await show_country_military_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_cmd_del:"):
        parts = data.split(":")
        cid = int(parts[2])
        key = parts[3]
        db.admin_delete_commander(cid, key)
        await query.answer("فرمانده حذف گردید.", show_alert=True)
        await show_country_military_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_cmd_add_prompt:"):
        cid = int(data.split(":")[2])
        context.user_data["admin_awaiting_input"] = {"type": "add_commander_title", "country_id": cid}
        c = db.get_country_by_id(cid)
        await query.edit_message_text(
            f"🎖️ <b>انتصاب فرمانده جدید برای {c['flag']} {html.escape(c['name'])}</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\nلطفاً <b>عنوان و نام فرمانده</b> را ارسال فرمایید (مثلاً: «سردار حاجی‌زاده» یا «ژنرال اریک کوریلا»):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data=f"admin:c_military:{cid}")]]),
            parse_mode="HTML"
        )
        return True

    elif data.startswith("admin:c_economy:"):
        cid = int(data.split(":")[2])
        await show_country_economy_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_civ_constructions:"):
        cid = int(data.split(":")[2])
        await show_country_constructions_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_civ_adj:"):
        parts = data.split(":")
        cid = int(parts[2])
        item_key = parts[3]
        delta = int(parts[4])
        curr_eq = db.get_equipment(cid)
        # add_equipment خودش دلتا را به مقدار فعلی اضافه می‌کند؛ نباید مقدار
        # نهایی به آن پاس داده شود وگرنه تعداد هر بار تقریباً دو برابر می‌شد
        # (۳۰۵ با فشردن ➖۱ می‌شد ۶۰۹).
        curr_qty = curr_eq.get(item_key, 0)
        delta = max(delta, -curr_qty)  # کف صفر
        db.add_equipment(cid, item_key, delta)
        new_qty = curr_qty + delta
        item_data = config.ALL_SHOP_ITEMS.get(item_key, {})
        await query.answer(f"تعداد {item_data.get('name', item_key)} به {new_qty} تغییر یافت.", show_alert=True)
        await show_country_constructions_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_civ_zero:"):
        parts = data.split(":")
        cid = int(parts[2])
        item_key = parts[3]
        curr_qty = db.get_equipment(cid).get(item_key, 0)
        if curr_qty > 0:
            db.add_equipment(cid, item_key, -curr_qty)
        item_data = config.ALL_SHOP_ITEMS.get(item_key, {})
        await query.answer(
            f"🗑️ {item_data.get('name', item_key)} صفر شد (قبلاً {curr_qty:,} واحد).",
            show_alert=True,
        )
        await show_country_constructions_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_civ_set:"):
        parts = data.split(":")
        cid = int(parts[2])
        item_key = parts[3]
        curr_qty = db.get_equipment(cid).get(item_key, 0)
        item_data = config.ALL_SHOP_ITEMS.get(item_key, {})
        context.user_data["admin_awaiting_input"] = {
            "type": "civ_set_qty", "country_id": cid, "item_key": item_key
        }
        await query.edit_message_text(
            f"✏️ <b>تعیین عدد دقیق — {html.escape(item_data.get('name', item_key))}</b>\n\n"
            f"تعداد فعلی: <code>{curr_qty:,}</code> واحد\n\n"
            "لطفاً عدد جدید را ارسال کنید (اعداد فارسی هم قابل قبول است):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data=f"admin:c_civ_constructions:{cid}")]]),
            parse_mode="HTML",
        )
        return True

    elif data.startswith("admin:c_diplomacy:"):
        cid = int(data.split(":")[2])
        await show_country_diplomacy_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_lift_blockade:"):
        parts = data.split(":")
        cid = int(parts[2])
        other_id = int(parts[3])
        db.lift_naval_blockade(cid, other_id)
        db.lift_naval_blockade(other_id, cid)
        await query.answer("محاصره دریایی با موفقیت لغو شد.", show_alert=True)
        await show_country_diplomacy_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_intel:"):
        cid = int(data.split(":")[2])
        await show_country_intel_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_clear_cyber:"):
        cid = int(data.split(":")[2])
        db.admin_clear_cyber_disruptions(cid)
        await query.answer("کلیه اختلالات و خاموشی‌های سایبری پاکسازی شد.", show_alert=True)
        await show_country_intel_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_reset_intel_limit:"):
        cid = int(data.split(":")[2])
        db.update_country_field(cid, "intel_ops_today", 0)
        await query.answer("محدودیت عملیات‌های امروز صفر شد.", show_alert=True)
        await show_country_intel_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_losses:"):
        parts = data.split(":")
        cid = int(parts[2])
        page = int(parts[3]) if len(parts) > 3 else 0
        await show_country_losses_menu(query, context, cid, page)
        return True

    elif data.startswith("admin:c_loss_revert:"):
        parts = data.split(":")
        cid = int(parts[2])
        report_id = int(parts[3])
        ok, msg = db.revert_loss_report(report_id)
        await query.answer(f"{'✅' if ok else '❌'} {msg}", show_alert=True)
        await show_country_losses_menu(query, context, cid, 0)
        return True

    elif data.startswith("admin:c_loss_del:"):
        parts = data.split(":")
        cid = int(parts[2])
        report_id = int(parts[3])
        ok, msg = db.delete_loss_report(report_id)
        await query.answer(f"{'✅' if ok else '❌'} {msg}", show_alert=True)
        await show_country_losses_menu(query, context, cid, 0)
        return True

    elif data.startswith("admin:c_statements:"):
        cid = int(data.split(":")[2])
        await show_country_statements_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_stmt_add:"):
        cid = int(data.split(":")[2])
        c = db.get_country_by_id(cid)
        succ, msg = db.admin_force_add_statement(cid, c.get("player_id", 0))
        await query.answer(msg, show_alert=True)
        await show_country_statements_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_stmt_reset:"):
        cid = int(data.split(":")[2])
        now_iran = datetime.datetime.now(db.IRAN_TZ).strftime("%Y-%m-%d")
        conn = db.get_connection()
        with conn:
            cur = conn.cursor()
            cur.execute("DELETE FROM daily_statements WHERE country_id = ? AND statement_date = ?", (cid, now_iran))
        await query.answer("بیانیه‌های امروز ریست شدند.", show_alert=True)
        await show_country_statements_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_vip_finance:"):
        cid = int(data.split(":")[2])
        await show_country_vip_finance_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_set_vip:"):
        parts = data.split(":")
        cid = int(parts[2])
        tier = parts[3]
        days = int(parts[4])
        succ, msg = db.admin_set_country_vip(cid, tier, days)
        await query.answer(msg, show_alert=True)
        await show_country_vip_finance_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_revoke_vip:"):
        cid = int(data.split(":")[2])
        succ, msg = db.admin_revoke_country_vip(cid)
        await query.answer(msg, show_alert=True)
        await show_country_vip_finance_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_grant_menu:"):
        cid = int(data.split(":")[2])
        await show_country_grant_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_grant_cat:"):
        parts = data.split(":")
        cid = int(parts[2])
        await show_country_grant_category(query, context, cid, parts[3])
        return True

    elif data.startswith("admin:c_grant:"):
        parts = data.split(":")
        cid = int(parts[2])
        item_key = parts[3]

        # آیتم‌هایی مثل عنوان تشریفاتی نیازمند دریافت متن دلخواه از ادمین هستند
        if item_key in GRANT_NEEDS_TEXT:
            context.user_data["admin_awaiting_input"] = {
                "type": "grant_custom_title", "country_id": cid, "item_key": item_key
            }
            c = db.get_country_by_id(cid)
            days = "۳۰" if "30d" in item_key else "۷"
            await query.edit_message_text(
                f"🏷️ <b>عنوان تشریفاتی {days} روزه — {c['flag']} {html.escape(c['name'])}</b>\n"
                "━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "لطفاً <b>متن عنوان دلخواه</b> را ارسال فرمایید (حداکثر ۵۰ کاراکتر):\n"
                "(مثال: <code>سلطان نفت</code> یا <code>امپراتور شرق</code>)",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data=f"admin:c_grant_menu:{cid}")]]),
                parse_mode="HTML"
            )
            return True

        ok, msg = db.admin_grant_item(cid, item_key, query.from_user.id)
        label = _grant_item_label(item_key)
        await query.answer(f"{'✅' if ok else '❌'} {label}\n{msg}", show_alert=True)
        if ok:
            await _notify_player_of_grant(context, cid, label)
        await show_country_grant_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_godmode:"):
        cid = int(data.split(":")[2])
        await show_country_godmode_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_transfer_prompt:"):
        cid = int(data.split(":")[2])
        context.user_data["admin_awaiting_input"] = {"type": "transfer_player_id", "country_id": cid}
        c = db.get_country_by_id(cid)
        await query.edit_message_text(
            f"👤 <b>واگذاری و تغییر مالکیت کشور {c['flag']} {html.escape(c['name'])}</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\nلطفاً <b>شناسه عددی تلگرام بازیکن جدید</b> و در صورت تمایل آیدی او را ارسال فرمایید:\n(مثال: <code>123456789 @username</code>)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data=f"admin:c_godmode:{cid}")]]),
            parse_mode="HTML"
        )
        return True

    elif data.startswith("admin:c_rename_prompt:"):
        cid = int(data.split(":")[2])
        context.user_data["admin_awaiting_input"] = {"type": "rename_country_name", "country_id": cid}
        c = db.get_country_by_id(cid)
        await query.edit_message_text(
            f"✏️ <b>تغییر نام و پرچم کشور {c['flag']} {html.escape(c['name'])}</b>\n━━━━━━━━━━━━━━━━━━━━━━\n\nلطفاً <b>پرچم و نام جدید</b> را ارسال فرمایید:\n(مثال: <code>🇮🇷 ایران مقتدر</code> یا <code>امپراتوری جدید</code>)",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data=f"admin:c_godmode:{cid}")]]),
            parse_mode="HTML"
        )
        return True

    elif data.startswith("admin:c_boost_econ:"):
        cid = int(data.split(":")[2])
        db.adjust_treasury(cid, 100_000_000)
        db.adjust_oil(cid, 1_000_000)
        db.adjust_grain(cid, 10_000)
        db.add_transaction(cid, "admin_boost", "تزریق بسته اقتصادی ۱۰۰ میلیون دلاری توسط ادمین", 100_000_000)
        await query.answer("بسته اقتصادی ۱۰۰M دلار + ۱M نفت و ۱۰k غلات با موفقیت تزریق شد!", show_alert=True)
        await show_country_godmode_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_boost_mil:"):
        cid = int(data.split(":")[2])
        c = db.get_country_by_id(cid)
        db.update_country_field(cid, "active_personnel", (c.get("active_personnel") or 0) + 50_000)
        db.update_country_field(cid, "combat_readiness", min(100, (c.get("combat_readiness") or 70) + 20))
        await query.answer("بسته نظامی ۵۰,۰۰۰ رزمنده + ۲۰٪ آمادگی رزمی تزریق شد!", show_alert=True)
        await show_country_godmode_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_bp_plus:"):
        cid = int(data.split(":")[2])
        bp = db.get_or_create_battle_pass(cid)
        new_t = min(20, bp["current_tier"] + 1)
        db.admin_set_battle_pass_tier(cid, new_t)
        await query.answer(f"لول بتل‌پس به Tier {new_t} افزایش یافت.", show_alert=True)
        await show_country_godmode_menu(query, context, cid)
        return True

    elif data.startswith("admin:c_bp_unlock:"):
        cid = int(data.split(":")[2])
        succ, msg = db.unlock_premium_battle_pass(cid)
        await query.answer(msg, show_alert=True)
        await show_country_godmode_menu(query, context, cid)
        return True

    return False


async def handle_dossier_inputs(update: Update, context: ContextTypes.DEFAULT_TYPE, input_type: str, text: str, input_state: dict) -> bool:
    """پردازش ورودی‌های متنی اختصاصی پرونده کشور."""
    if input_type == "transfer_player_id":
        c_id = input_state["country_id"]
        try:
            parts = text.split()
            new_pid = int(parts[0].translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١۲٣٤٥٦٧٨٩", "01234567890123456789")))
            new_uname = parts[1].replace("@", "") if len(parts) > 1 else ""
            ok, msg = db.admin_transfer_country_ownership(c_id, new_pid, new_uname)
            if ok:
                await update.message.reply_text(f"✅ {msg}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🌐 بازگشت به پرونده کشور", callback_data=f"admin:c:{c_id}")]]))
            else:
                await update.message.reply_text(f"❌ {msg}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🌐 بازگشت به پرونده کشور", callback_data=f"admin:c:{c_id}")]]))
        except Exception as e:
            await update.message.reply_text(f"❌ شناسه عددی تلگرام نامعتبر است: {e}")
        return True

    elif input_type == "rename_country_name":
        c_id = input_state["country_id"]
        try:
            parts = text.split(maxsplit=1)
            if len(parts) == 2 and any(ord(char) > 127 for char in parts[0]):
                flag, name = parts[0], parts[1]
            else:
                flag, name = None, text.strip()
            ok, msg = db.admin_rename_country(c_id, name, flag)
            await update.message.reply_text(f"✅ {msg}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🌐 بازگشت به پرونده کشور", callback_data=f"admin:c:{c_id}")]]))
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در تغییر نام: {e}")
        return True

    elif input_type == "grant_custom_title":
        c_id = input_state["country_id"]
        item_key = input_state.get("item_key", "title_7d")
        try:
            title_text = text.strip()[:50]
            if not title_text:
                await update.message.reply_text("❌ متن عنوان نمی‌تواند خالی باشد.")
                return True
            ok, msg = db.admin_grant_item(
                c_id, item_key, update.effective_user.id,
                custom_payload={"custom_title": title_text}
            )
            label = _grant_item_label(item_key)
            if ok:
                await _notify_player_of_grant(context, c_id, f"{label} — «{title_text}»")
            await update.message.reply_text(
                f"{'✅' if ok else '❌'} {msg}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🛒 بازگشت به اعطای آیتم", callback_data=f"admin:c_grant_menu:{c_id}")]])
            )
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در اعطای عنوان تشریفاتی: {e}")
        return True

    elif input_type == "civ_set_qty":
        c_id = input_state["country_id"]
        item_key = input_state.get("item_key", "")
        item_data = config.ALL_SHOP_ITEMS.get(item_key, {})
        label = item_data.get("name", item_key)
        kb = InlineKeyboardMarkup([[InlineKeyboardButton("🏗️ بازگشت به ساخت‌وسازها", callback_data=f"admin:c_civ_constructions:{c_id}")]])
        try:
            clean = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١۲٣٤٥٦٧٨٩", "01234567890123456789")).replace(",", "").replace("،", "").strip()
            new_qty = int(clean)
            if new_qty < 0:
                await update.message.reply_text("❌ تعداد نمی‌تواند منفی باشد.", reply_markup=kb)
                return True
            curr_qty = db.get_equipment(c_id).get(item_key, 0)
            db.add_equipment(c_id, item_key, new_qty - curr_qty)
            await update.message.reply_text(
                f"✅ تعداد «{label}» از {curr_qty:,} به {new_qty:,} واحد تغییر یافت.",
                reply_markup=kb,
            )
        except ValueError:
            await update.message.reply_text("❌ لطفاً فقط عدد ارسال کنید.", reply_markup=kb)
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در تعیین تعداد: {e}", reply_markup=kb)
        return True

    elif input_type == "add_commander_title":
        c_id = input_state["country_id"]
        try:
            cmd_title = text.strip()
            cmd_key = f"cmd_{int(time.time())}"
            ok, msg = db.admin_add_commander(c_id, cmd_key, cmd_title)
            await update.message.reply_text(f"✅ {msg}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🎖️ بازگشت به تسلیحات و فرماندهان", callback_data=f"admin:c_military:{c_id}")]]))
        except Exception as e:
            await update.message.reply_text(f"❌ خطا در افزودن فرمانده: {e}")
        return True

    return False
