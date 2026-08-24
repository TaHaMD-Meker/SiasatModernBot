# -*- coding: utf-8 -*-
"""
ماژول سازمان اطلاعات، امنیت ملی، جنگ سایبری و کادر فرماندهان نظامی (Intelligence & Cyber Warfare System).
شامل ۴ دپارتمان تخصصی: جاسوسی و تخلیه اسناد، جنگ سایبری، عملیات سیاه و ترور، پدافند ضدجاسوسی و فایروال.
طراحی فوق‌العاده شیک، کتابی با کادربندی‌های رسمی (<blockquote>)، ارقام فارسی و ترمینال‌های هکری مبهم.
"""

import random
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

import database as db
import config
import news_engine
from utils import format_money, format_number, format_oil
from premium_emojis import pe


def _kb(rows):
    return InlineKeyboardMarkup(rows)


def fa_num(val) -> str:
    if val is None:
        return "۰"
    try:
        val = int(val)
    except (ValueError, TypeError):
        return "۰"
    s = f"{val:,}".replace(",", "٬")
    tr = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
    return s.translate(tr)


async def require_country(update: Update):
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        pending = db.get_pending_request_by_player(user_id)
        if pending:
            p_key = pending.get("country_key", "")
            p_info = config.COUNTRIES.get(p_key, {})
            flag = p_info.get("flag", "🏳️")
            name = p_info.get("name", p_key)
            msg = f"⏳ <b>درخواست رهبری کشور {flag} {name} در صف بررسی ادمین است.</b>\n\nپس از تایید ادمین، سازمان اطلاعات فعال می‌شود."
            alert_text = f"درخواست کشور {name} در انتظار تأیید ادمین است!"
        else:
            msg = "❌ شما هنوز کشوری در بازی ندارید! برای شروع /start را بزنید."
            alert_text = "هنوز کشوری نساختی! برای شروع /start بزن."

        if update.message:
            await update.message.reply_text(msg, parse_mode="HTML")
        elif update.callback_query:
            await update.callback_query.answer(alert_text, show_alert=True)
        return None
    return country


# ==================== ۱. منوی اصلی سازمان اطلاعات ====================

async def intel_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    country = await require_country(update)
    if not country:
        return

    c = db.get_country_by_id(country["id"]) or country
    cid = c["id"]
    ckey = c.get("country_key", "")

    agency = db.get_intel_agency_info(ckey)
    offense_score, defense_score = db.get_country_intel_attack_defense(cid)
    fw_lvl = c.get("firewall_level", 1) or 1
    fw_info = config.FIREWALL_UPGRADES.get(fw_lvl, config.FIREWALL_UPGRADES[1])

    today_str = datetime.date.today().isoformat()
    last_date = c.get("intel_ops_date")
    ops_today = c.get("intel_ops_today", 0) if last_date == today_str else 0
    rem_ops = max(0, config.INTEL_DAILY_OPERATION_LIMIT - ops_today)

    # Cooldown Check
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    last_time_raw = c.get("last_intel_op_time")
    cd_str = "آماده عملیات"
    if last_time_raw:
        try:
            last_time = datetime.datetime.fromisoformat(last_time_raw)
            diff_h = (now_dt - last_time).total_seconds() / 3600.0
            if diff_h < config.INTEL_OPERATION_COOLDOWN_HOURS:
                rem_h = config.INTEL_OPERATION_COOLDOWN_HOURS - diff_h
                cd_str = f"ریکاوری ({fa_num(int(rem_h * 60))} دقیقه باقی‌مانده)"
        except Exception:
            pass

    tier_labels = {"S": "رده S (جهانی)", "A": "رده A (منطقه‌ای)", "B": "رده B (تخصصی)", "C": "رده C (پایه)"}

    text = (
        f"🕵️‍♂️ <b>ستاد فرماندهی امنیت ملی و سازمان اطلاعات</b>\n"
        f"<blockquote>"
        f"<b>کشور:</b> {c['flag']} {c['name']}\n"
        f"<b>سازمان اطلاعاتی:</b> {agency['agency_name']}\n"
        f"<b>شاخه سایبری:</b> {agency['cyber_unit']}\n"
        f"<b>رتبه راهبردی:</b> {tier_labels.get(agency['tier'], agency['tier'])}\n"
        f"</blockquote>\n"
        f"<b>تراز توان اطلاعاتی و پدافند سایبری</b>\n"
        f"<blockquote>"
        f"• قدرت تهاجم و نفوذ سایبری: <code>{fa_num(offense_score)}</code> امتیاز\n"
        f"• سپر پدافند و ضدجاسوسی: <code>{fa_num(defense_score)}</code> امتیاز\n"
        f"• سطح فایروال ملی: {fw_info['label']}\n"
        f"• سقف عملیات امروز: <code>{fa_num(rem_ops)} از {fa_num(config.INTEL_DAILY_OPERATION_LIMIT)}</code>\n"
        f"• وضعیت شبکه نفوذ: {cd_str}\n"
        f"</blockquote>\n"
        f"<i>{agency['desc']}</i>"
    )

    buttons = [
        [
            InlineKeyboardButton("👁️ جاسوسی و سرقت اسناد", callback_data="intel:menu_espionage"),
            InlineKeyboardButton("💻 جنگ سایبری و هک", callback_data="intel:menu_cyber"),
        ],
        [
            InlineKeyboardButton("💣 عملیات سیاه و ترور", callback_data="intel:menu_blackops"),
            InlineKeyboardButton("🛡️ پدافند سایبری و فایروال", callback_data="intel:menu_firewall"),
        ],
        [
            InlineKeyboardButton("🎖️ کادر فرماندهی و سران نظامی", callback_data="intel:commanders_menu"),
            InlineKeyboardButton("📋 پرونده‌ها و سوابق عملیات", callback_data="intel:history"),
        ],
        [
            InlineKeyboardButton("🔙 بازگشت به ستاد راهبردی", callback_data="mv:menu"),
        ]
    ]

    if update.message:
        await update.message.reply_text(text, reply_markup=_kb(buttons), parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="HTML")


# ==================== ۲. کادر فرماندهی نظامی ====================

async def intel_commanders_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    country = await require_country(update)
    if not country:
        return

    c = db.get_country_by_id(country["id"]) or country
    commanders = db.get_country_commanders(c["id"])

    lines = [
        f"🎖️ <b>کادر فرماندهی ارشد و سران نظامی — {c['flag']} {c['name']}</b>\n",
        "<blockquote>سلسله‌مراتب فرماندهی و ساختار تصمیم‌گیری ستاد کل نیروهای مسلح</blockquote>\n\n",
        "<b>فهرست فرماندهان کلیدی کشور:</b>\n"
    ]

    disrupted = False
    for i, cmd in enumerate(commanders, 1):
        if cmd["status"] == "active":
            status_str = "🟢 فعال و در حال خدمت"
        else:
            status_str = "🔴 شهید / ترور شده (خلاء فرماندهی)"
            disrupted = True
        lines.append(f"<b>{fa_num(i)}. {cmd['title']}</b>\n<blockquote>وضعیت: {status_str}</blockquote>\n")

    if disrupted:
        lines.append(
            "\n<blockquote>⚠️ <b>هشدار شوک فرماندهی:</b> به دلیل شهادت کادر ارشد، هماهنگی ارتش دچار اختلال شده و آسیب‌پذیری نیروها در نبردها افزایش یافته است.</blockquote>"
        )
    else:
        lines.append(
            "\n<blockquote>✅ <b>وضعیت زنجیره فرماندهی:</b> کامل و پایدار. تمامی قرارگاه‌های رزمی تحت کنترل مستقیم قرار دارند.</blockquote>"
        )

    buttons = [
        [InlineKeyboardButton("🔙 بازگشت به سازمان اطلاعات", callback_data="intel:menu")],
    ]

    text = "".join(lines)
    if update.message:
        await update.message.reply_text(text, reply_markup=_kb(buttons), parse_mode="HTML")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="HTML")


# ==================== ۳. تولید لاگ هکری و اسناد مبهم ====================

def _generate_obfuscated_military_dump(target: dict) -> str:
    assets = db.get_country_assets(target["id"])
    t_name = target.get("name", "TARGET")
    t_key = target.get("country_key", "UNKNOWN").upper()

    sample_assets = random.sample(assets, min(len(assets), 4)) if assets else []
    block_lines = []
    for a in sample_assets:
        amt = a["amount"] or 0
        # ایجاد بازه تخمینی مبهم جهت شبیه‌سازی اطلاعات سرقتی
        low = max(0, int(amt * 0.85))
        high = int(amt * 1.15) + 1
        block_lines.append(f'        0x{random.randint(0x10, 0xFF):02X}: "{a["equipment_name"]}": EST_QTY ~[{fa_num(low)} - {fa_num(high)}]')

    assets_str = "\n".join(block_lines) if block_lines else "        [REDACTED_SECTOR_NO_ASSETS_FOUND]"

    text = (
        f"<code>[SYSTEM: CLASSIFIED_SIGINT_PAYLOAD // LEVEL-4 DECRYPTED]</code>\n"
        f"<code>==================================================</code>\n"
        f"<code>> TARGET_HOST: 192.168.{random.randint(10, 99)}.{random.randint(2, 250)} [{t_key}_GRID]</code>\n"
        f"<code>> STATUS: MEMORY_DUMP_SUCCESSFUL (AES-256 BYPASSED)</code>\n\n"
        f"<code>[+] EXTRACTED ARSENAL FRAGMENTS:</code>\n"
        f"<code>--------------------------------------------------</code>\n"
        f"<code>{assets_str}</code>\n"
        f"<code>        0xEE: [SECTOR_NORTH_LOGISTICS]: [REDACTED_HASH_0x4F]</code>\n"
        f"<code>--------------------------------------------------</code>\n"
        f"<code>[!] TRACE_CLEARED: ZERO FOOTPRINT LEFT ON TARGET NODE.</code>"
    )
    return text


def _generate_obfuscated_diplomacy_dump(target: dict) -> str:
    t_key = target.get("country_key", "UNKNOWN").upper()
    t_id = target["id"]

    sent_contracts = db.get_country_pending_sent_contracts(t_id) or []
    recv_contracts = db.get_country_pending_received_contracts(t_id) or []
    market_orders = db.get_country_market_orders(t_id) or []

    contract_blocks = []
    type_labels = {"treasury": "USD", "gold": "GOLD_BARS", "oil": "BBL_OIL", "grain": "TONS_GRAIN", "microchips": "CHIPS", "uranium_ore": "YELLOWCAKE", "nuclear_fuel": "REACTOR_FUEL"}

    for c in sent_contracts[:2]:
        dest_name = c.get("target_name", "UNKNOWN")
        off_t = type_labels.get(c["offered_type"], c["offered_type"])
        req_t = type_labels.get(c["requested_type"], c["requested_type"])
        contract_blocks.append(
            f'        0x{random.randint(0x10, 0xFF):02X}: [PENDING_OUTBOUND_DEAL #{c["id"]}]:\n'
            f'             DESTINATION: [{dest_name}]\n'
            f'             OFFERED: {fa_num(c["offered_amount"])} {off_t}\n'
            f'             REQUESTED: {fa_num(c["requested_amount"])} {req_t}\n'
            f'             TRANSPORT_MODE: [{c.get("transport_mode", "sea").upper()}]'
        )

    for c in recv_contracts[:2]:
        sender_name = c.get("sender_name", "UNKNOWN")
        off_t = type_labels.get(c["offered_type"], c["offered_type"])
        req_t = type_labels.get(c["requested_type"], c["requested_type"])
        contract_blocks.append(
            f'        0x{random.randint(0x10, 0xFF):02X}: [INCOMING_PROPOSAL #{c["id"]}]:\n'
            f'             ORIGIN: [{sender_name}]\n'
            f'             INBOUND: {fa_num(c["offered_amount"])} {off_t}\n'
            f'             OUTBOUND: {fa_num(c["requested_amount"])} {req_t}'
        )

    for m in market_orders[:2]:
        res_t = type_labels.get(m["resource_type"], m["resource_type"])
        contract_blocks.append(
            f'        0x{random.randint(0x10, 0xFF):02X}: [COMMODITY_MARKET_LISTING #{m["id"]}]:\n'
            f'             RESOURCE: {res_t} × {fa_num(m["amount"])}\n'
            f'             UNIT_ASK_PRICE: ${fa_num(m["unit_price"])}'
        )

    if not contract_blocks:
        contract_blocks.append('        0x1A: [SECURE_ENCRYPTED_WIRES]: NO_ACTIVE_UNRESOLVED_CONTRACTS_FOUND\n        0x2B: TREASURY_LIQUIDITY: EST ~$' + fa_num(int(target.get("treasury", 0) * 0.95)) + ' - $' + fa_num(int(target.get("treasury", 0) * 1.05)))

    contracts_str = "\n".join(contract_blocks)

    text = (
        f"<code>[SYSTEM: CLASSIFIED_DIPLOMATIC_WIRETAP // SIGINT INTERCEPT]</code>\n"
        f"<code>==================================================</code>\n"
        f"<code>> TARGET_NODE: {t_key}_MINISTRY_FOREIGN_AFFAIRS</code>\n"
        f"<code>> STATUS: COMMS_DECRYPTED (RSA-4096 CRACKED)</code>\n\n"
        f"<code>[+] INTERCEPTED DEALS & COMMODITY WIRES:</code>\n"
        f"<code>--------------------------------------------------</code>\n"
        f"<code>{contracts_str}</code>\n"
        f"<code>        0xFF: [CIPHER_KEY_ROTATED]: [REDACTED_CHANNEL_0x8C]</code>\n"
        f"<code>--------------------------------------------------</code>\n"
        f"<code>[!] TRACE_CLEARED: SECURE DIPLOMATIC COMMS COMPROMISED.</code>"
    )
    return text


def _generate_obfuscated_nuclear_dump(target: dict) -> str:
    t_key = target.get("country_key", "UNKNOWN").upper()
    u_ore = target.get("uranium_ore", 0) or 0
    w_90 = target.get("weapons_grade_90", 0) or 0
    enr_60 = target.get("enriched_60", 0) or 0
    fuel_35 = target.get("nuclear_fuel", 0) or 0
    wh = target.get("warheads", 0) or 0
    tier = target.get("enrichment_tier", 1) or 1

    low_wh = max(0, wh - 1)
    high_wh = wh + 1

    text = (
        f"<code>[SYSTEM: TOP_SECRET_NUCLEAR_DOSSIER // DECRYPTED]</code>\n"
        f"<code>==================================================</code>\n"
        f"<code>> NODE: {t_key}_ATOMIC_ENERGY_INFRASTRUCTURE</code>\n"
        f"<code>> STATUS: TELEMETRY_INTERCEPTED (CONFIDENTIAL)</code>\n\n"
        f"<code>[+] DECRYPTED STOCKPILE BLOCKS:</code>\n"
        f"<code>--------------------------------------------------</code>\n"
        f"<code>0x004F: HEU_90_WEAPONS_GRADE:  ~[{fa_num(max(0, w_90-5))} - {fa_num(w_90+5)}] KG</code>\n"
        f"<code>0x006C: BREAKOUT_60_ENRICHED:  ~[{fa_num(max(0, enr_60-8))} - {fa_num(enr_60+8)}] KG</code>\n"
        f"<code>0x008E: REACTOR_FUEL_3.5_KG:   ~{fa_num(fuel_35)} KG</code>\n"
        f"<code>0x00A1: ACTIVE_WARHEADS_EST:   [{fa_num(low_wh)} - {fa_num(high_wh)}] UNITS</code>\n"
        f"<code>0x00D4: ENRICHMENT_TIER_CODE:  TIER_{tier} [ACTIVE_CASCADE]</code>\n"
        f"<code>--------------------------------------------------</code>\n"
        f"<code>[!] ANALYSIS: TARGET BREAKOUT TIMELINE EVALUATED.</code>"
    )
    return text


# ==================== ۴. هندلر انتخاب کشور هدف و نوع عملیات ====================

def _clean_persian_str(s: str) -> str:
    """استانداردسازی متن فارسی/انگلیسی جهت جستجوی دقیق."""
    if not s:
        return ""
    t = str(s).strip().lower()
    t = t.replace("_", " ")
    trans = {
        "ي": "ی", "ى": "ی", "ك": "ک", "ؤ": "و",
        "إ": "ا", "أ": "ا", "آ": "ا", "ة": "ه",
        "ئ": "ی", "ـ": ""
    }
    for k, v in trans.items():
        t = t.replace(k, v)
    t = re.sub(r"[^\w\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def build_intel_continent_countries_keyboard(cont_key: str, op_type: str, current_cid: int):
    continents = getattr(config, "CONTINENTS", {})
    cont_info = continents.get(cont_key, {})
    keys = cont_info.get("keys", [])

    all_countries = db.get_all_countries()
    c_map = {c["country_key"]: c for c in all_countries if c.get("country_key")}

    rows = []
    row = []
    for k in keys:
        if k in c_map:
            c = c_map[k]
            if c["id"] == current_cid:
                continue
            row.append(InlineKeyboardButton(f"{c['flag']} {c['name']}", callback_data=f"intel:confirm_op:{op_type}:{c['id']}"))
            if len(row) == 2:
                rows.append(row)
                row = []
    if row:
        rows.append(row)

    rows.append([
        InlineKeyboardButton("🔎 جستجو", callback_data=f"intel:search_start:{op_type}"),
        InlineKeyboardButton("🔙 لیست قاره‌ها", callback_data=f"intel:back_continents:{op_type}")
    ])
    return f"🎯 <b>{cont_info.get('name', 'قاره')}</b>\n\nکشور هدف را انتخاب فرمایید:", _kb(rows)


async def show_intel_target_picker(update: Update, context: ContextTypes.DEFAULT_TYPE, op_type: str, category_label: str):
    query = update.callback_query
    user_id = query.from_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        return

    op_cfg = config.INTEL_OPERATIONS_CONFIG.get(op_type, {})
    continents = getattr(config, "CONTINENTS", {})

    text = (
        f"🎯 <b>انتخاب کشور هدف برای {op_cfg.get('name', category_label)}</b>\n"
        f"<blockquote>{op_cfg.get('desc', '')}</blockquote>\n\n"
        f"<b>برآورد هزینه عملیات:</b>\n"
        f"• بودجه سیاه: <b>{format_money(op_cfg.get('cost_money', 0))}</b>\n"
        f"• میکروچیپ پردازشی: <b>{fa_num(op_cfg.get('cost_chips', 0))} عدد</b>\n\n"
        f"جهت انتخاب هدف، <b>قاره کشور مقصد را انتخاب فرمایید</b> یا از <b>جستجوی سریع</b> استفاده کنید:"
    )

    rows = []
    row = []
    for c_key, c_info in continents.items():
        row.append(InlineKeyboardButton(c_info["name"], callback_data=f"intel:pickcont:{c_key}:{op_type}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([InlineKeyboardButton("🔎 جستجوی نام کشور هدف (تایپی)", callback_data=f"intel:search_start:{op_type}")])
    rows.append([InlineKeyboardButton("🔙 بازگشت به سازمان اطلاعات", callback_data="intel:menu")])
    await query.edit_message_text(text, reply_markup=_kb(rows), parse_mode="HTML")


# ==================== ۵. Callback Handler و اجرای عملیات ====================

async def intel_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    country = db.get_country_by_player(user_id)

    if not country:
        await query.answer("کشور یافت نشد!", show_alert=True)
        return

    await query.answer()
    c = db.get_country_by_id(country["id"]) or country
    cid = c["id"]

    if data == "intel:menu":
        await intel_main_menu(update, context)

    elif data == "intel:commanders_menu":
        await intel_commanders_menu(update, context)

    elif data == "intel:history":
        await intel_history_menu(update, context)

    # ---------------- دسته‌بندی‌های عملیات ----------------
    elif data == "intel:menu_espionage":
        text = (
            "👁️ <b>دپارتمان جاسوسی و تخلیه اسناد محرمانه (SIGINT)</b>\n"
            "<blockquote>نفوذ سایبری به سرورهای محرمانه و استخراج داده‌های نظامی و هسته‌ای حریف بدون بر جای گذاشتن ردپا.</blockquote>\n\n"
            "نوع عملیات مورد نظر را انتخاب فرمایید:"
        )
        buttons = [
            [InlineKeyboardButton("📑 سرقت اسناد انبار تسلیحات", callback_data="intel:pick_target:espionage_military")],
            [InlineKeyboardButton("📜 شنود دیپلماسی و قراردادهای محرمانه", callback_data="intel:pick_target:espionage_diplomacy")],
            [InlineKeyboardButton("☢️ پرونده‌خوانی برنامه هسته‌ای", callback_data="intel:pick_target:espionage_nuclear")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="intel:menu")],
        ]
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="HTML")

    elif data == "intel:menu_cyber":
        text = (
            "💻 <b>دپارتمان جنگ سایبری و نبردهای دیجیتال (Cyber Warfare)</b>\n"
            "<blockquote>حملات سایبری پیشرفته به زیرساخت‌های پدافندی، انرژی و صنعتی دشمن.</blockquote>\n\n"
            "عملیات سایبری مورد نظر را انتخاب فرمایید:"
        )
        buttons = [
            [InlineKeyboardButton("📡 هک و کور کردن رادارهای پدافند (۲۴h)", callback_data="intel:pick_target:cyber_air_defense")],
            [InlineKeyboardButton("⚡ خاموشی سایبری شبکه برق (Blackout)", callback_data="intel:pick_target:cyber_blackout")],
            [InlineKeyboardButton("☢️ تزریق بدافزار به سانتریفیوژها (استاکس‌نت)", callback_data="intel:pick_target:cyber_centrifuge")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="intel:menu")],
        ]
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="HTML")

    elif data == "intel:menu_blackops":
        text = (
            "💣 <b>دپارتمان عملیات سیاه، ترور و خرابکاری فیزیکی (Black Ops)</b>\n"
            "<blockquote>عملیات‌های نفوذی و ترور هدفمند جهت قطع زنجیره تصمیم‌گیری و فلج‌سازی توسعه رقیب.</blockquote>\n\n"
            "نوع عملیات سیاه را انتخاب فرمایید:"
        )
        buttons = [
            [InlineKeyboardButton("🎖️ ترور هدفمند فرمانده ارشد نظامی", callback_data="intel:pick_target:assassination_commander")],
            [InlineKeyboardButton("🔬 ترور دانشمند ارشد هسته‌ای / فناوری", callback_data="intel:pick_target:assassination_scientist")],
            [InlineKeyboardButton("🛢️ خرابکاری انفجاری در خطوط لوله نفت", callback_data="intel:pick_target:sabotage_pipeline")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="intel:menu")],
        ]
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="HTML")

    elif data == "intel:menu_firewall":
        fw_lvl = c.get("firewall_level", 1) or 1
        fw_info = config.FIREWALL_UPGRADES.get(fw_lvl, config.FIREWALL_UPGRADES[1])
        next_lvl = min(5, fw_lvl + 1)
        next_info = config.FIREWALL_UPGRADES.get(next_lvl, fw_info)

        text = (
            "🛡️ <b>دپارتمان پدافند سایبری و فایروال ملی</b>\n"
            "<blockquote>تجهیز سرورهای حساس و شبکه‌های راداری به سپرهای ضدجاسوسی و دیوارهای آتش یکپارچه.</blockquote>\n\n"
            f"• <b>سطح فایروال فعلی:</b> {fw_info['label']} (مقاومت: <b>+{fa_num(fw_info['defense_bonus'])}٪</b>)\n"
        )
        buttons = []
        if fw_lvl < 5:
            text += (
                f"\n<b>شرایط ارتقا به {next_info['label']}:</b>\n"
                f"• هزینه مالی: <b>{format_money(next_info['cost_money'])}</b>\n"
                f"• میکروچیپ مورد نیاز: <b>{fa_num(next_info['cost_chips'])} عدد</b>\n"
                f"• مقاومت افزوده پس از ارتقا: <b>+{fa_num(next_info['defense_bonus'])}٪</b>\n"
            )
            buttons.append([InlineKeyboardButton(f"🚀 ارتقای فایروال به {next_info['label']}", callback_data="intel:do_upgrade_firewall")])
        else:
            text += "\n🌟 <i>پدافند سایبری کشور در بالاترین سطح دفاعی (قلعه نفوذناپذیر) قرار دارد.</i>"

        buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="intel:menu")])
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="HTML")

    elif data == "intel:do_upgrade_firewall":
        ok, msg = db.upgrade_firewall_transaction(cid)
        if not ok:
            await query.edit_message_text(
                f"{pe('cross', '❌')} <b>ارتقای فایروال انجام نشد:</b>\n\n<blockquote>{msg}</blockquote>",
                reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت", callback_data="intel:menu_firewall")]]),
                parse_mode="HTML"
            )
            return
        await query.edit_message_text(
            f"{msg}",
            reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به سازمان اطلاعات", callback_data="intel:menu")]]),
            parse_mode="HTML"
        )

    # ---------------- انتخاب هدف ----------------
    elif data.startswith("intel:pick_target:"):
        op_type = data.split(":")[2]
        await show_intel_target_picker(update, context, op_type, "عملیات اطلاعاتی")

    elif data.startswith("intel:pickcont:"):
        _, _, cont_key, op_type = data.split(":")
        text, kb = build_intel_continent_countries_keyboard(cont_key, op_type, country["id"])
        await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")

    elif data.startswith("intel:back_continents:"):
        op_type = data.split(":")[2]
        op_cfg = config.INTEL_OPERATIONS_CONFIG.get(op_type, {})
        await show_intel_target_picker(update, context, op_type, op_cfg.get("name", "عملیات اطلاعاتی"))

    elif data.startswith("intel:search_start:"):
        op_type = data.split(":")[2]
        context.user_data["intel_search"] = {"op_type": op_type}
        text = (
            "🔎 <b>جستجوی کشور هدف برای عملیات اطلاعاتی</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً <b>نام کشور مورد نظر</b> را تایپ و ارسال فرمایید:\n"
            "<i>(مثال: اسرائیل، آمریکا، عربستان، فرانسه، انگلیس)</i>"
        )
        await query.edit_message_text(text, reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به لیست قاره‌ها", callback_data=f"intel:back_continents:{op_type}")]]), parse_mode="HTML")

    # ---------------- صفحه تایید نهایی عملیات ----------------
    elif data.startswith("intel:confirm_op:"):
        parts = data.split(":")
        op_type = parts[2]
        target_id = int(parts[3])
        target_c = db.get_country_by_id(target_id)
        if not target_c:
            await query.edit_message_text("کشور هدف یافت نشد.")
            return

        op_cfg = config.INTEL_OPERATIONS_CONFIG.get(op_type, {})
        att_off, _ = db.get_country_intel_attack_defense(cid)
        _, tgt_def = db.get_country_intel_attack_defense(target_id)

        score_diff = att_off - tgt_def
        success_prob = max(15, min(85, 50 + int(score_diff * 0.8)))

        text = (
            f"🕵️‍♂️ <b>تأیید نهایی صدور دستور عملیات اطلاعاتی</b>\n"
            f"<blockquote>آیا از اجرای عملیات علیه {target_c['flag']} <b>{target_c['name']}</b> اطمینان دارید؟</blockquote>\n\n"
            f"<b>مشخصات مأموریت:</b>\n"
            f"• نوع عملیات: <b>{op_cfg.get('name')}</b>\n"
            f"• برآورد شانس موفقیت: <code>{fa_num(success_prob)}٪</code>\n"
            f"• بودجه سیاه: <b>{format_money(op_cfg.get('cost_money', 0))}</b>\n"
            f"• میکروچیپ پردازشی: <b>{fa_num(op_cfg.get('cost_chips', 0))} عدد</b>\n\n"
            f"⚠️ <b>هشدارهای حفاظتی:</b>\n"
            f"• در صورت موفقیت، مأموریت به صورت کاملاً گمنام (Zero Footprint) انجام خواهد شد.\n"
            f"• در صورت شکست فاحش، ردپای سازمان اطلاعاتی شما لو رفته و خبر فوری در کانال رسمی منتشر می‌گردد."
        )

        buttons = [
            [InlineKeyboardButton("✅ تأیید و صدور دستور اجرا", callback_data=f"intel:do_op:{op_type}:{target_id}:0")],
            [InlineKeyboardButton("💻 تقویت با +۵ میکروچیپ (+۱۰٪ شانس)", callback_data=f"intel:do_op:{op_type}:{target_id}:5")],
            [InlineKeyboardButton("❌ انصراف", callback_data="intel:menu")],
        ]
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="HTML")

    # ---------------- اجرای قطعی عملیات ----------------
    elif data.startswith("intel:do_op:"):
        parts = data.split(":")
        op_type = parts[2]
        target_id = int(parts[3])
        chips_boost = int(parts[4]) if len(parts) > 4 else 0

        target_c = db.get_country_by_id(target_id)
        if not target_c:
            await query.edit_message_text("کشور هدف یافت نشد.")
            return

        ok, msg, meta = db.execute_intel_operation(cid, target_id, op_type, chips_boost=chips_boost)
        if ok:
            try:
                db.add_battle_pass_xp(cid, 200)
                db.progress_battle_pass_challenge(cid, "intel", 1)
            except Exception:
                pass
        res_code = meta.get("result")

        if ok and res_code == "clean_success":
            # موفقیت کامل
            result_header = f"🎉 <b>موفقیت کامل عملیات اطلاعاتی (Clean Strike)</b>\n<blockquote>مأموریت با موفقیت کامل و بدون برجای گذاشتن ردپا اجرا گردید.</blockquote>\n\n"
            if op_type == "espionage_military":
                dump_text = _generate_obfuscated_military_dump(target_c)
                full_result_text = f"{result_header}<b>اسناد سرقت‌شده از انبار نظامی {target_c['flag']} {target_c['name']}:</b>\n\n{dump_text}"
            elif op_type == "espionage_nuclear":
                dump_text = _generate_obfuscated_nuclear_dump(target_c)
                full_result_text = f"{result_header}<b>پرونده محرمانه هسته‌ای {target_c['flag']} {target_c['name']}:</b>\n\n{dump_text}"
            elif op_type == "espionage_diplomacy":
                dump_text = _generate_obfuscated_diplomacy_dump(target_c)
                full_result_text = f"{result_header}<b>شنود خطوط دیپلماسی و قراردادهای {target_c['flag']} {target_c['name']}:</b>\n\n{dump_text}"
            else:
                extra_note = ""
                if op_type == "assassination_commander" and "killed_commander" in meta:
                    extra_note = f"\n• فرمانده هدف: <b>{meta['killed_commander']['title']}</b> (شهید / ترور شد)"
                full_result_text = f"{result_header}• هدف مأموریت: <b>{meta['op_cfg']['name']}</b>\n• کشور هدف: {target_c['flag']} <b>{target_c['name']}</b>{extra_note}\n\n<i>اثرات عملیات فوراً در دیتابیس بازی اعمال گردید.</i>"

            # ارسال نسخه دائمی به عنوان پیام مستقل در پیوی بازیکن تا با کلیک دکمه گم نشود
            try:
                await context.bot.send_message(chat_id=user_id, text=full_result_text, parse_mode="HTML")
            except Exception:
                pass

            # انتشار خبر فوری رویدادهای فیزیکی در کانال اخبار (خرابکاری نفتی، ترورها)
            try:
                if op_type == "sabotage_pipeline":
                    await news_engine.trigger_pipeline_sabotage_news(context.bot, target_c)
                elif op_type == "assassination_commander" and "killed_commander" in meta:
                    await news_engine.trigger_commander_assassination_news(context.bot, target_c, meta['killed_commander']['title'])
                elif op_type == "assassination_scientist":
                    await news_engine.trigger_scientist_assassination_news(context.bot, target_c)
            except Exception:
                pass

            # ارسال هشدار خرابکاری برای کشور مدافع
            if target_c.get("player_id"):
                try:
                    if op_type == "sabotage_pipeline":
                        await context.bot.send_message(
                            chat_id=target_c["player_id"],
                            text=f"🛢️ <b>هشدار پدافند غیرعامل — انفجار در خطوط لوله نفت!</b>\n\nیک خرابکاری انفجاری ناشناس در خطوط لوله و مخازن نفتی کشور شما رخ داد و <b>۱۵۰,۰۰۰ بشکه نفت</b> از بین رفت.",
                            parse_mode="HTML"
                        )
                    elif op_type == "cyber_blackout":
                        await context.bot.send_message(
                            chat_id=target_c["player_id"],
                            text=f"⚡ <b>هشدار خاموشی سایبری (Blackout)!</b>\n\nحمله سایبری ناشناس به شبکه توزیع برق کشور موجب قطعی گسترده برق و افت ۵٪ رضایت عمومی گردید.",
                            parse_mode="HTML"
                        )
                    elif op_type == "cyber_centrifuge":
                        await context.bot.send_message(
                            chat_id=target_c["player_id"],
                            text=f"☢️ <b>هشدار امنیتی تاسیسات هسته‌ای!</b>\n\nنفوذ بدافزار به سانتریفیوژها موجب انهدام ۵۰ کیلوگرم سوخت غنی‌شده و توقف موقت غنی‌سازی گردید.",
                            parse_mode="HTML"
                        )
                except Exception:
                    pass

            await query.edit_message_text(
                full_result_text,
                reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به سازمان اطلاعات", callback_data="intel:menu")]]),
                parse_mode="HTML"
            )

        else:
            # شکست
            if res_code == "busted_exposed":
                # رسوایی جهانی و انتشار در کانال اخبار
                att_agency = meta.get("agency", {})
                agency_name = att_agency.get("agency_name", "سرویس اطلاعاتی")
                try:
                    if op_type == "sabotage_pipeline":
                        await news_engine.trigger_pipeline_sabotage_news(context.bot, target_c, attacker_c=c)
                    elif op_type == "assassination_commander":
                        await news_engine.trigger_commander_assassination_news(context.bot, target_c, "یکی از فرماندهان ارشد", attacker_c=c)
                    elif op_type == "assassination_scientist":
                        await news_engine.trigger_scientist_assassination_news(context.bot, target_c, attacker_c=c)
                    else:
                        await news_engine.post_breaking_news(
                            context.bot,
                            f"رسوایی اطلاعاتی: دستگیری عوامل نفوذی {c['name']} در {target_c['name']}",
                            f"پدافند ضدجاسوسی کشور {target_c['flag']} **{target_c['name']}** یک هسته خرابکاری متعلق به **{agency_name} ({c['flag']} {c['name']})** را در حین اجرای مأموریت شناسایی و بازداشت کرد.\nشورای امنیت سازمان ملل این اقدام را محکوم کرد و ۵٪ از رضایت عمومی کشور مهاجم کسر گردید.",
                            "رسوایی اطلاعاتی"
                        )
                except Exception:
                    pass

                await query.edit_message_text(
                    f"💥 <b>شکست عملیات و افشای هویت (Busted & Exposed)</b>\n\n"
                    f"<blockquote>عملیات توسط شبکه ضدجاسوسی {target_c['name']} خنثی شد و متأسفانه ردپای سازمان اطلاعاتی شما لو رفت!</blockquote>\n\n"
                    f"⚠️ <b>پیامدها:</b>\n"
                    f"• خبر رسوایی در کانال رسمی اخبار منتشر گردید.\n"
                    f"• کسر ۵٪ از رضایت عمومی کشور شما.",
                    reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به سازمان اطلاعات", callback_data="intel:menu")]]),
                    parse_mode="HTML"
                )

            elif res_code == "blocked_unattributed":
                # دفع ناشناس و انتشار خبر خنثی‌سازی در کانال برای حوادث فیزیکی/ترور
                try:
                    if op_type in ("sabotage_pipeline", "assassination_commander", "assassination_scientist"):
                        await news_engine.trigger_foiled_sabotage_news(context.bot, target_c, op_type)
                except Exception:
                    pass

                # ارسال هشدار امنیتی به بازیکن مدافع
                if target_c.get("player_id"):
                    try:
                        if op_type in ("sabotage_pipeline", "assassination_commander", "assassination_scientist"):
                            await context.bot.send_message(
                                chat_id=target_c["player_id"],
                                text=f"🛡️ <b>گزارش امنیتی و ضدجاسوسی</b>\n\nیک اقدام خرابکارانه / ترور ناشناس علیه اهداف کشور شما با هوشیاری نیروهای امنیتی پیش از اجرا خنثی گردید.",
                                parse_mode="HTML"
                            )
                        else:
                            await context.bot.send_message(
                                chat_id=target_c["player_id"],
                                text=f"🛡️ <b>هشدار پدافند سایبری</b>\n\nیک تلاش برای نفوذ سایبری ناشناس به زیرساخت‌های کشور شما توسط فایروال ملی با موفقیت خنثی گردید. هویت نفوذگر غیرقابل ردگیری است.",
                                parse_mode="HTML"
                            )
                    except Exception:
                        pass

                await query.edit_message_text(
                    f"🛡️ <b>خنثی‌سازی عملیات (Blocked / Unattributed)</b>\n\n"
                    f"<blockquote>عملیات توسط فایروال و سپرهای سایبری {target_c['name']} خنثی گردید، اما خوشبختانه هویت سازمان شما ناشناس باقی ماند و هیچ ردی به جا نماند.</blockquote>",
                    reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت به سازمان اطلاعات", callback_data="intel:menu")]]),
                    parse_mode="HTML"
                )
            else:
                await query.edit_message_text(
                    f"{pe('cross', '❌')} <b>عملیات انجام نشد:</b>\n\n<blockquote>{msg}</blockquote>",
                    reply_markup=_kb([[InlineKeyboardButton("🔙 بازگشت", callback_data="intel:menu")]]),
                    parse_mode="HTML"
                )


async def intel_history_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    country = await require_country(update)
    if not country:
        return

    c = db.get_country_by_id(country["id"]) or country
    history = db.get_country_intel_history(c["id"], limit=10)

    lines = [
        f"📋 <b>پرونده‌ها و تاریخچه عملیات‌های اطلاعاتی — {c['flag']} {c['name']}</b>\n",
        "<blockquote>سوابق رسمی مأموریت‌های سایبری، جاسوسی و عملیات سیاه اجراشده توسط کشور</blockquote>\n\n"
    ]

    if not history:
        lines.append("<i>هنوز هیچ عملیات اطلاعاتی ثبت نگردیده است.</i>\n")
    else:
        result_labels = {
            "clean_success": "🟢 موفقیت کامل (گمنام)",
            "blocked_unattributed": "🟡 خنثی‌شده (بدون لو رفتن)",
            "busted_exposed": "🔴 شکست و رسوایی افشاشده"
        }
        for h in history:
            op_cfg = config.INTEL_OPERATIONS_CONFIG.get(h["op_type"], {})
            op_name = op_cfg.get("name", h["op_type"])
            t_flag = h.get("target_flag", "")
            t_name = h.get("target_name", "هدف")
            res_str = result_labels.get(h["result"], h["result"])
            dt_str = (h["created_at"] or "")[:16].replace("T", " ")

            lines.append(
                f"• <b>مأموریت:</b> {op_name} ➔ {t_flag} <b>{t_name}</b>\n"
                f"  <blockquote>نتیجه: {res_str} | زمان: <code>{dt_str}</code></blockquote>\n"
            )

    buttons = [
        [InlineKeyboardButton("🔙 بازگشت به سازمان اطلاعات", callback_data="intel:menu")],
    ]

    text = "".join(lines)
    query = update.callback_query
    if query:
        await query.edit_message_text(text, reply_markup=_kb(buttons), parse_mode="HTML")
    elif update.message:
        await update.message.reply_text(text, reply_markup=_kb(buttons), parse_mode="HTML")


async def intel_search_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """پردازش جستجوی کشور هدف برای عملیات اطلاعاتی."""
    search_state = context.user_data.get("intel_search")
    if not search_state:
        return False

    del context.user_data["intel_search"]
    op_type = search_state.get("op_type", "espionage_military")
    user = update.effective_user
    country = db.get_country_by_player(user.id)
    if not country:
        return False

    user_query = update.message.text.strip()
    clean_q = _clean_persian_str(user_query)

    all_countries = db.get_all_countries()
    matches = []
    for c in all_countries:
        if c["id"] == country["id"] or c.get("country_key") == "un":
            continue
        c_name = c.get("name", "")
        c_key = c.get("country_key", "")
        if clean_q in _clean_persian_str(c_name) or clean_q in _clean_persian_str(c_key):
            matches.append(c)

    if not matches:
        text_res = f"❌ <b>کشوری با عنوان «{html.escape(user_query)}» در بازی یافت نشد.</b>"
        kb_res = [
            [InlineKeyboardButton("🔁 جستجوی دوباره", callback_data=f"intel:search_start:{op_type}")],
            [InlineKeyboardButton("🔙 لیست قاره‌ها", callback_data=f"intel:back_continents:{op_type}")],
        ]
        await update.message.reply_text(text_res, reply_markup=_kb(kb_res), parse_mode="HTML")
        return True

    rows = []
    row = []
    for c in matches:
        row.append(InlineKeyboardButton(f"{c['flag']} {c['name']}", callback_data=f"intel:confirm_op:{op_type}:{c['id']}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    rows.append([
        InlineKeyboardButton("🔁 جستجوی مجدد", callback_data=f"intel:search_start:{op_type}"),
        InlineKeyboardButton("🔙 لیست قاره‌ها", callback_data=f"intel:back_continents:{op_type}")
    ])

    await update.message.reply_text(
        f"🎯 <b>نتایج جستجو برای «{html.escape(user_query)}» ({len(matches)} کشور):</b>\n━━━━━━━━━━━━━━━━━━\nکشور هدف را انتخاب فرمایید:",
        reply_markup=_kb(rows),
        parse_mode="HTML"
    )
    return True
