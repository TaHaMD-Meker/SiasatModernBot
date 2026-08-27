# -*- coding: utf-8 -*-
"""
پنل ادمین پیشرفته و تعاملی با دکمه‌های شیشه‌ای (Inline Buttons).
مدیریت کامل کشورها، خزانه، طلا، نفت، تجهیزات، دارایی‌های اختصاصی نظامی (Country Assets) و همگام‌سازی کاتالوگ.
"""

import math
import json
import html
import os
import re
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler, MessageHandler, filters

import database as db
import approval_system
import config
import asyncio
from utils import format_money, format_number, format_oil, get_main_keyboard
from handlers.losses import handle_losses_input
from handlers.tournament_admin import tournament_admin_callback, handle_tournament_admin_input
from handlers.internal_admin import internal_admin_callback, handle_internal_admin_input
from handlers.admin_dossier import (
    show_country_dashboard,
    show_country_trades_menu,
    show_country_trade_detail,
    show_country_bases_menu,
    show_country_nuclear_menu,
    show_country_military_menu,
    show_country_economy_menu,
    show_country_diplomacy_menu,
    show_country_intel_menu,
    show_country_losses_menu,
    show_country_statements_menu,
    show_country_vip_finance_menu,
    show_country_godmode_menu,
    handle_dossier_callbacks,
    handle_dossier_inputs
)
def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS


def _clean_persian_str(value: str) -> str:
    """استانداردسازی متن فارسی/انگلیسی برای جستجوی کشورها در پنل ادمین."""
    if not value:
        return ""
    text = str(value).strip().lower().replace("_", " ")
    for source, target in {
        "ي": "ی", "ى": "ی", "ك": "ک", "ؤ": "و",
        "إ": "ا", "أ": "ا", "آ": "ا", "ة": "ه",
        "ئ": "ی", "ـ": "",
    }.items():
        text = text.replace(source, target)
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# ==================== هاب مدیریت پیام‌ها و سوییچ امن بین عکس و متن ====================

async def safe_edit_or_reply(query, text: str, reply_markup=None, parse_mode="HTML", photo_id: str = None):
    """
    ویرایش یا ارسال کاملاً امن پیام ادمین با پشتیبانی خودکار از سوییچ بین عکس و متن.
    از بروز خطاهای BadRequest تلگرام (عدم وجود متن در عکس) جلوگیری می‌کند.
    """
    msg = query.message if query else None
    has_photo = bool(msg and msg.photo)

    if photo_id:
        if has_photo:
            try:
                await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
                return
            except Exception:
                pass
        try:
            await msg.reply_photo(photo=photo_id, caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
            try:
                await query.delete_message()
            except Exception:
                pass
            return
        except Exception:
            text = f"📷 <i>[تصویر فیش ضمیمه]</i>\n\n{text}"

    if has_photo:
        try:
            await msg.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            try:
                await query.delete_message()
            except Exception:
                pass
            return
        except Exception:
            try:
                await query.edit_message_caption(caption=text, reply_markup=reply_markup, parse_mode=parse_mode)
                return
            except Exception:
                pass
    else:
        try:
            await query.edit_message_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
            return
        except Exception:
            try:
                await query.edit_message_text(text, reply_markup=reply_markup)
                return
            except Exception:
                try:
                    await msg.reply_text(text, reply_markup=reply_markup, parse_mode=parse_mode)
                except Exception:
                    pass


# ==================== منوی اصلی ادمین ====================

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ این بخش فقط برای ادمین اصلی بازی مجاز است.", parse_mode="Markdown")
        return

    admin_c = db.get_country_by_player(user_id)
    un_btn = [InlineKeyboardButton("🇺🇳 اتاق ویژه دبیرکل سازمان ملل متحد", callback_data="un:menu")] if (admin_c and admin_c.get("country_key") == "un") else [InlineKeyboardButton("🇺🇳 فعال‌سازی کشور / نقش سازمان ملل", callback_data="admin:claim_un")]

    pending_reqs = db.get_all_pending_country_requests()
    pending_count = len(pending_reqs)
    pending_payments = db.get_pending_payment_requests()
    pay_count = len(pending_payments)

    text = "👑 *پنل مدیریت بازی «سیاست مدرن»*\n\nلطفاً یک گزینه را انتخاب کنید:"
    keyboard = [
        un_btn,
        [InlineKeyboardButton(f"📥 درخواست‌های معلق کشورها ({pending_count})", callback_data="admin:pending_countries")],
        [InlineKeyboardButton(f"💳 فیش‌های پرداخت تومانی ({pay_count})", callback_data="admin:toman_requests")],
        [InlineKeyboardButton("📋 مدیریت و لیست کشورها", callback_data="admin:list:0")],
        [InlineKeyboardButton("💥 مدیریت تلفات تجهیزات", callback_data="ls:menu")],
        [InlineKeyboardButton("🚨 رادار ضدتقلب و تراکنش‌های مشکوک", callback_data="admin:anti_cheat_radar")],
        [InlineKeyboardButton("🔐 سیستم قفل‌ها و محدودیت‌ها", callback_data="admin:locks_menu")],
        [InlineKeyboardButton("📥 رول‌های دریافتی (مدیریت عملیات‌ها)", callback_data="admin:roleplays_hub")],
        [InlineKeyboardButton("🔎 رصد و پایش فعالیت بازیکنان", callback_data="admin:monitor_menu")],
        [InlineKeyboardButton("💾 پشتیبان‌گیری فوری از دیتابیس (Backup)", callback_data="admin:backup_db")],
        [InlineKeyboardButton("📢 تنظیم آیدی کانال تلگرام", callback_data="admin:set_channel_prompt")],
        [InlineKeyboardButton("🏆 رتبه‌بندی ثروت و قدرتمندترین کشورها", callback_data="admin:rankings")],
        [InlineKeyboardButton("🏆 مدیریت تورنومنت فصلی", callback_data="admin:tournament")],
        [InlineKeyboardButton("🚨 مدیریت بحران و سیاست داخلی", callback_data="admin:dom")],
        [InlineKeyboardButton("📊 آمار کلی بازی", callback_data="admin:stats")],
        [InlineKeyboardButton("🔄 همگام‌سازی کاتالوگ تمام کشورها", callback_data="admin:sync_catalog")],
        [InlineKeyboardButton("🔄 رفرش و همگام‌سازی کیبورد تمام بازیکنان", callback_data="admin:sync_all_keyboards")],
        [InlineKeyboardButton("🎁 سامانه جبران و بازیابی درآمد بازیکنان", callback_data="admin:income_recovery_hub")],
        [InlineKeyboardButton("🧹 سلب مالکیت تمام کشورها و شروع رسمی فصل جدید", callback_data="admin:season_reset_prompt")],
        [InlineKeyboardButton("📦 ریست کامل بازار بورس و عودت کالاها", callback_data="admin:market_reset_prompt")],
        [InlineKeyboardButton("💰 واریز بسته حمایتی انرژی به واردکنندگان", callback_data="admin:energy_aid_prompt")],
        [InlineKeyboardButton("⚡ توزیع فوری درآمد روزانه", callback_data="admin:daily_income")],
        [InlineKeyboardButton("📢 ارسال پیام همگانی (Broadcast)", callback_data="admin:broadcast_prompt")],
        [InlineKeyboardButton("❌ بستن پنل", callback_data="admin:close")],
    ]

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif update.callback_query:
        await safe_edit_or_reply(update.callback_query, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def admin_locks_menu(query, context):
    country_lock = db.get_setting("country_creation_locked") == "1"
    blockade_lock = db.get_setting("naval_blockade_locked") == "1"
    trade_lock = db.get_setting("trade_contracts_locked") == "1"
    notes_lock = db.get_setting("diplomatic_notes_locked") == "1"
    role_lock = db.get_setting("role_submit_locked") == "1"
    inactivity_paused = db.get_setting("inactivity_revocation_paused") == "1"

    status_lines = [
        f"• ثبت‌نام و ساخت کشور: {'🔒 قفل' if country_lock else '🟢 باز'}",
        f"• محاصره دریایی: {'🔒 قفل' if blockade_lock else '🟢 باز'}",
        f"• معاهدات تجاری: {'🔒 قفل' if trade_lock else '🟢 باز'}",
        f"• پیام‌های دیپلماتیک: {'🔒 قفل' if notes_lock else '🟢 باز'}",
        f"• ارسال رول و عملیات: {'🔒 قفل' if role_lock else '🟢 باز'}",
        f"• حذف ساعت ۰۰:۰۰ (بیانیه‌ها): {'🛡️ متوقف و مصونیت فعال (روشن)' if inactivity_paused else '⚡ فعال (حذف خودکار کاربران بدون ۲ بیانیه)'}",
    ]

    text = (
        "🔐 **سیستم قفل‌ها و کنترل محدودیت‌های سراسری بازی**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "📊 **وضعیت فعلی قفل‌ها:**\n"
        + "\n".join(status_lines) + "\n\n"
        "👇 جهت تغییر وضعیت هر بخش، روی دکمه مربوطه کلیک فرمایید:"
    )

    inactivity_btn = InlineKeyboardButton(
        "▶️ ازسرگیری حذف ساعت ۰۰:۰۰ (خاموش کردن توقف)" if inactivity_paused else "⏸️ توقف حذف ساعت ۰۰:۰۰ (روشن کردن مصونیت سراسری)",
        callback_data="admin:toggle_lock:inactivity_revocation_paused"
    )

    keyboard = [
        [InlineKeyboardButton("🔓 باز کردن ثبت‌نام کشورها" if country_lock else "🔒 قفل کردن ثبت‌نام کشورها", callback_data="admin:toggle_lock:country_creation_locked")],
        [InlineKeyboardButton("🔓 باز کردن محاصره دریایی" if blockade_lock else "🔒 قفل کردن محاصره دریایی", callback_data="admin:toggle_lock:naval_blockade_locked")],
        [InlineKeyboardButton("🔓 باز کردن قراردادهای تجاری" if trade_lock else "🔒 قفل کردن قراردادهای تجاری", callback_data="admin:toggle_lock:trade_contracts_locked")],
        [InlineKeyboardButton("🔓 باز کردن پیام‌های دیپلماتیک" if notes_lock else "🔒 قفل کردن پیام‌های دیپلماتیک", callback_data="admin:toggle_lock:diplomatic_notes_locked")],
        [InlineKeyboardButton("🔓 باز کردن ارسال رول" if role_lock else "🔒 قفل کردن ارسال رول", callback_data="admin:toggle_lock:role_submit_locked")],
        [inactivity_btn],
        [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")],
    ]

    await safe_edit_or_reply(query, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== لیست کشورها با صفحه‌بندی و فیلتر قاره‌ها ====================

async def show_countries_list(query, context, page: int = 0, filter_continent: str = None):
    all_countries = db.get_all_countries()
    if not all_countries:
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]]
        await query.edit_message_text("❌ هنوز هیچ کشوری در بازی ساخته نشده است.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return

    filtered = all_countries
    if filter_continent and filter_continent != "all":
        cont_keys = config.CONTINENTS.get(filter_continent, {}).get("keys", [])
        filtered = [c for c in all_countries if c.get("country_key") in cont_keys or (filter_continent == "mideast" and (c.get("country_key") or "").startswith("faction_"))]

    per_page = 5
    total_pages = max(1, math.ceil(len(filtered) / per_page))
    page = max(0, min(page, total_pages - 1))

    start_idx = page * per_page
    page_countries = filtered[start_idx:start_idx + per_page]

    keyboard = []
    for c in page_countries:
        flag = c.get("flag") or "🏳️"
        name = c.get("name") or "بی‌نام"
        tr = format_money(c.get("treasury") or 0)
        pid = c.get("player_id") or "—"
        btn_text = f"{flag} {name} | 🏦 {tr} (ID: {pid})"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"admin:c:{c['id']}")])

    nav_row = []
    cont_param = filter_continent or "all"
    if page > 0:
        nav_row.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:list:{page - 1}:{cont_param}"))
    if total_pages > 1:
        nav_row.append(InlineKeyboardButton(f"صفحه {page + 1} از {total_pages}", callback_data="ignore"))
    if page < total_pages - 1:
        nav_row.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:list:{page + 1}:{cont_param}"))

    if nav_row:
        keyboard.append(nav_row)

    # دکمه‌های فیلتر قاره‌ها در پنل ادمین
    filter_row1 = [
        InlineKeyboardButton("🌍 خاورمیانه", callback_data="admin:list:0:mideast"),
        InlineKeyboardButton("🇪🇺 اروپا", callback_data="admin:list:0:europe"),
        InlineKeyboardButton("🌏 آسیا", callback_data="admin:list:0:asia"),
    ]
    filter_row2 = [
        InlineKeyboardButton("🌎 آمریکا", callback_data="admin:list:0:americas"),
        InlineKeyboardButton("🌍 آفریقا", callback_data="admin:list:0:africa"),
        InlineKeyboardButton("🌐 همه کشورها", callback_data="admin:list:0:all"),
    ]
    keyboard.append(filter_row1)
    keyboard.append(filter_row2)
    keyboard.append([InlineKeyboardButton("🔎 جستجوی نام کشور (تایپی)", callback_data="admin:search_country_prompt")])
    keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data="admin:menu")])

    cont_title = f" (فیلتر: {config.CONTINENTS.get(filter_continent, {}).get('short_name', filter_continent)})" if filter_continent and filter_continent != "all" else ""
    text = f"📋 *لیست کشورهای فعال (نمایش {len(filtered)} از مجموع {len(all_countries)} کشور)*{cont_title}\n\nبرای مشاهده یا تغییر جزئیات، روی کشور مورد نظر کلیک کنید:"
    try:
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    except Exception:
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception:
            pass


# ==================== زیرمنوهای تغییر خزانه، طلا، نفت و دارایی‌های نظامی ====================

async def menu_treasury(query, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return
    text = f"🏦 *تغییر خزانه کشور {c['flag']} {c['name']}*\nموجودی فعلی: {format_money(c['treasury'])}\n\nیکی از مقادیر زیر را انتخاب کنید یا مقدار دلخواه تایپ کنید:"

    keyboard = [
        [
            InlineKeyboardButton("➕ ۱۰ میلیون", callback_data=f"admin:adj:{c['id']}:treasury:10000000"),
            InlineKeyboardButton("➕ ۵۰ میلیون", callback_data=f"admin:adj:{c['id']}:treasury:50000000"),
            InlineKeyboardButton("➕ ۱۰۰ میلیون", callback_data=f"admin:adj:{c['id']}:treasury:100000000"),
        ],
        [
            InlineKeyboardButton("➖ ۱۰ میلیون", callback_data=f"admin:adj:{c['id']}:treasury:-10000000"),
            InlineKeyboardButton("➖ ۵۰ میلیون", callback_data=f"admin:adj:{c['id']}:treasury:-50000000"),
            InlineKeyboardButton("➖ ۱۰۰ میلیون", callback_data=f"admin:adj:{c['id']}:treasury:-100000000"),
        ],
        [
            InlineKeyboardButton("✏️ تنظیم دقیق عدد خزانه (تایپی)", callback_data=f"admin:prompt:{c['id']}:treasury"),
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:c:{c['id']}"),
        ]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def menu_gold(query, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return
    text = f"🪙 *تغییر طلای کشور {c['flag']} {c['name']}*\nطلای فعلی: {format_number(c['gold'])}\n\nیک گزینه را انتخاب کنید:"

    keyboard = [
        [
            InlineKeyboardButton("➕ ۵۰ طلا", callback_data=f"admin:adj:{c['id']}:gold:50"),
            InlineKeyboardButton("➕ ۲۰۰ طلا", callback_data=f"admin:adj:{c['id']}:gold:200"),
            InlineKeyboardButton("➕ ۱,۰۰۰ طلا", callback_data=f"admin:adj:{c['id']}:gold:1000"),
        ],
        [
            InlineKeyboardButton("➖ ۵۰ طلا", callback_data=f"admin:adj:{c['id']}:gold:-50"),
            InlineKeyboardButton("➖ ۲۰۰ طلا", callback_data=f"admin:adj:{c['id']}:gold:-200"),
            InlineKeyboardButton("➖ ۱,۰۰۰ طلا", callback_data=f"admin:adj:{c['id']}:gold:-1000"),
        ],
        [
            InlineKeyboardButton("✏️ تنظیم دقیق عدد طلا (تایپی)", callback_data=f"admin:prompt:{c['id']}:gold"),
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:c:{c['id']}"),
        ]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def menu_oil(query, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return
    text = (
        f"🛢️ *تغییر وضعیت نفت کشور {c['flag']} {c['name']}*\n"
        f"ذخایر فعلی: {format_oil(c['oil_reserves'])}\n"
        f"تولید روزانه فعلی: {format_oil(c['oil_production'])}/روز"
    )

    keyboard = [
        [
            InlineKeyboardButton("➕ ۱ میلیون بشکه ذخیره", callback_data=f"admin:adj:{c['id']}:oil_reserves:1000000"),
            InlineKeyboardButton("➕ ۱۰ میلیون بشکه ذخیره", callback_data=f"admin:adj:{c['id']}:oil_reserves:10000000"),
        ],
        [
            InlineKeyboardButton("➖ ۱ میلیون بشکه ذخیره", callback_data=f"admin:adj:{c['id']}:oil_reserves:-1000000"),
            InlineKeyboardButton("➖ ۱۰ میلیون بشکه ذخیره", callback_data=f"admin:adj:{c['id']}:oil_reserves:-10000000"),
        ],
        [
            InlineKeyboardButton("✏️ تنظیم عددی ذخایر نفت", callback_data=f"admin:prompt:{c['id']}:oil_reserves"),
            InlineKeyboardButton("✏️ تنظیم نرخ تولید روزانه", callback_data=f"admin:prompt:{c['id']}:oil_production"),
        ],
        [
            InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:c:{c['id']}"),
        ]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def menu_assets(query, country_id: int):
    """فهرست دسته‌بندی‌های دارایی‌های نظامی (دکمه‌های شیشه‌ای به تفکیک نیرو)."""
    c = db.get_country_by_id(country_id)
    if not c:
        return

    assets = db.get_country_assets(country_id)
    by_cat = {}
    for a in assets:
        by_cat.setdefault(a['category'], []).append(a)

    text = f"🎖️ *مدیریت دارایی‌های نظامی {c['flag']} {c['name']}*\n\nیکی از نیروها/دسته‌ها را انتخاب کنید:"

    keyboard = []
    row = []
    for cat, (label, unit) in config.ASSET_CATEGORIES.items():
        items = by_cat.get(cat)
        if not items:
            continue
        row.append(InlineKeyboardButton(f"{label} ({len(items)})", callback_data=f"admin:asset_cat:{country_id}:{cat}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    for cat in [c_ for c_ in by_cat if c_ not in config.ASSET_CATEGORIES]:
        keyboard.append([InlineKeyboardButton(f"📦 {cat} ({len(by_cat[cat])})", callback_data=f"admin:asset_cat:{country_id}:{cat}")])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:c:{c['id']}")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def menu_assets_category(query, country_id: int, category: str):
    """فهرست تجهیزات یک دسته برای ویرایش."""
    c = db.get_country_by_id(country_id)
    if not c:
        return

    cat_label, unit = config.ASSET_CATEGORIES.get(category, (category, "عدد"))
    assets = [a for a in db.get_country_assets(country_id) if a['category'] == category]
    total = sum((a.get("amount", 0) or 0) for a in assets)

    text = (
        f"🎖️ *{cat_label} — {c['flag']} {c['name']}*\n"
        f"قلم‌ها: {len(assets)} | مجموع: {format_number(total)} {unit}\n\n"
        "تجهیز مورد نظر را برای تغییر تعداد انتخاب کنید:"
    )

    keyboard = []
    for a in assets:
        prod_mark = "✅" if a.get("producible", 1) == 1 else "🌐"
        keyboard.append([InlineKeyboardButton(f"{a['equipment_name']} ({format_number(a['amount'])}) {prod_mark}", callback_data=f"admin:asset_item:{country_id}:{a['equipment_key']}")])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت به دسته‌ها", callback_data=f"admin:menu_assets:{country_id}")])
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")




# ==================== ویرایش اقتصاد و وضعیت داخلی کشور ====================

COUNTRY_STAT_FIELDS = {
    "treasury":         ("🏦 موجودی خزانه", "دلار", 10_000_000, "money"),
    "daily_income":     ("📈 درآمد ناخالص روزانه", "دلار", 1_000_000, "money"),
    "tax_income":       ("💰 درآمد مالیاتی", "دلار", 500_000, "money"),
    "gold":             ("🪙 ذخایر طلا", "شمش", 100, "num"),
    "gold_daily":       ("🪙 تولید روزانه طلا", "شمش", 10, "num"),
    "oil_reserves":     ("🛢️ ذخایر نفت", "بشکه", 500_000, "num"),
    "oil_production":   ("🛢️ تولید روزانه نفت", "بشکه", 100_000, "num"),
    "grain":            ("🌾 ذخایر غلات", "تن", 10_000, "num"),
    "grain_daily":      ("🌾 تولید روزانه غلات", "تن", 1_000, "num"),
    "iron_ore":         ("⛏️ ذخایر سنگ آهن و فولاد", "تن", 5_000, "num"),
    "iron_ore_daily":   ("⛏️ تولید روزانه آهن و فولاد", "تن", 500, "num"),
    "electricity":      ("⚡ توان شبکه برق", "MW", 50, "num"),
    "microchips":       ("💻 ذخیره میکروچیپ", "چیپ", 100, "num"),
    "microchips_daily": ("💻 تولید روزانه میکروچیپ", "چیپ", 10, "num"),
    "approval_rating":  ("😀 رضایت عمومی", "٪", 5, "pct"),
    "combat_readiness": ("⚔️ آمادگی رزمی", "٪", 5, "pct"),
    "population":       ("👥 جمعیت", "نفر", 1_000_000, "num"),
    "active_personnel": ("🪖 پرسنل فعال ارتش", "نفر", 10_000, "num"),
    "reserve_personnel":("🎖 پرسنل ذخیره ارتش", "نفر", 10_000, "num"),
    "tech_level":       ("🔬 سطح فناوری و صنعت", "سطح", 1, "num"),
    "firewall_level":   ("🔒 سطح فایروال سایبری", "سطح", 1, "num"),
    "uranium_ore":      ("☢️ ذخیره کیک زرد", "تن", 100, "num"),
    "uranium_ore_daily":("☢️ استخراج روزانه کیک زرد", "تن", 10, "num"),
    "nuclear_fuel":     ("🧪 سوخت هسته‌ای", "کیلوگرم", 50, "num"),
    "nuclear_fuel_daily":("🧪 تولید روزانه سوخت هسته‌ای", "کیلوگرم", 10, "num"),
    "medical_isotopes": ("🏥 رادیوداروهای پزشکی", "دوز", 50, "num"),
    "enriched_60":      ("⚛️ اورانیوم غنی‌شده ۶۰٪", "کیلوگرم", 20, "num"),
    "weapons_grade_90": ("☢️ اورانیوم نظامی ۹۰٪ (HEU)", "کیلوگرم", 10, "num"),
    "warheads":         ("🚀 کلاهک‌های هسته‌ای", "عدد", 1, "num"),
    "warhead_cap_override": ("📊 بازنویسی سقف کلاهک", "عدد", 5, "num"),
}

_CSTAT_LIMITS = {
    "approval_rating": (0, 100),
    "combat_readiness": (0, 100),
    "tech_level": (1, 10),
    "firewall_level": (0, 5),
    "enrichment_tier": (0, 4)
}


def _fmt_stat(value, kind):
    if kind == "money":
        return format_money(value)
    return f"{format_number(value)}"


async def menu_country_stats(query, country_id: int):
    c = db.get_country_by_id(country_id)
    if not c:
        return
    rows = []
    row = []
    for field, (label, unit, step, kind) in COUNTRY_STAT_FIELDS.items():
        val = _fmt_stat(c.get(field, 0) or 0, kind)
        row.append(InlineKeyboardButton(f"{label}: {val}", callback_data=f"admin:cstat:{country_id}:{field}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton("🔙 بازگشت به داشبورد کشور", callback_data=f"admin:c:{country_id}")])
    text = (
        f"⚙️ *اقتصاد و وضعیت داخلی — {c['flag']} {c['name']}*\n\n"
        "مورد مورد نظر را برای ویرایش انتخاب کنید:"
    )
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows), parse_mode="Markdown")


async def menu_cstat_adjust(query, country_id: int, field: str):
    c = db.get_country_by_id(country_id)
    info = COUNTRY_STAT_FIELDS.get(field)
    if not c or not info:
        return
    label, unit, step, kind = info
    current = c.get(field, 0) or 0
    note = ""
    if field in ("daily_income", "tax_income"):
        note = "\n\n⚠️ _این دو مورد با هر ری‌استارت بر اساس کانفیگ و ساختمان‌ها بازسازی می‌شوند._"
    rows = [
        [InlineKeyboardButton(f"➖ {step*10:,}", callback_data=f"admin:cstatadj:{country_id}:{field}:-10"),
         InlineKeyboardButton(f"➖ {step*5:,}", callback_data=f"admin:cstatadj:{country_id}:{field}:-5"),
         InlineKeyboardButton(f"➖ {step:,}", callback_data=f"admin:cstatadj:{country_id}:{field}:-1")],
        [InlineKeyboardButton(f"➕ {step:,}", callback_data=f"admin:cstatadj:{country_id}:{field}:1"),
         InlineKeyboardButton(f"➕ {step*5:,}", callback_data=f"admin:cstatadj:{country_id}:{field}:5"),
         InlineKeyboardButton(f"➕ {step*10:,}", callback_data=f"admin:cstatadj:{country_id}:{field}:10")],
        [InlineKeyboardButton("✏️ وارد کردن مقدار دقیق", callback_data=f"admin:cstatset:{country_id}:{field}")],
        [InlineKeyboardButton("🔙 بازگشت به وضعیت داخلی", callback_data=f"admin:cstatmenu:{country_id}")],
    ]
    await query.edit_message_text(
        f"{label} — {c['flag']} {c['name']}\n\nمقدار فعلی: *{_fmt_stat(current, kind)}*{note}",
        reply_markup=InlineKeyboardMarkup(rows), parse_mode="Markdown")


def apply_cstat_delta(country_id: int, field: str, mult: int):
    info = COUNTRY_STAT_FIELDS.get(field)
    if not info:
        return None, "فیلد نامعتبر"
    _, unit, step, kind = info
    c = db.get_country_by_id(country_id)
    if not c:
        return None, "کشور یافت نشد"
    new_val = (c.get(field, 0) or 0) + mult * step
    lo, hi = _CSTAT_LIMITS.get(field, (0, 10**15))
    new_val = max(lo, min(hi, new_val))
    db.update_country_field(country_id, field, new_val)
    return new_val, None


def apply_cstat_value(country_id: int, field: str, value: int):
    info = COUNTRY_STAT_FIELDS.get(field)
    if not info:
        return None, "فیلد نامعتبر"
    lo, hi = _CSTAT_LIMITS.get(field, (0, 10**15))
    value = max(lo, min(hi, value))
    db.update_country_field(country_id, field, value)
    return value, None


async def menu_single_asset_item(query, country_id: int, equipment_key: str):
    c = db.get_country_by_id(country_id)
    asset = db.get_asset_by_key(country_id, equipment_key)
    if not c or not asset:
        return

    unit = config.ASSET_CATEGORIES.get(asset['category'], ("", "عدد"))[1]
    prod_str = "بومی (قابل خرید در فروشگاه)" if asset.get("producible", 1) == 1 else "وارداتی (غیرقابل خرید در فروشگاه)"

    text = (
        f"⚙️ *ویرایش دارایی نظامی:* {asset['equipment_name']}\n"
        f"کشور: {c['flag']} {c['name']}\n"
        f"نوع: `{prod_str}`\n"
        f"تعداد فعلی: `{format_number(asset['amount'])} {unit}`\n"
        f"قیمت واحد: {format_money(asset['buy_price'])}"
    )

    keyboard = [
        [
            InlineKeyboardButton("➕ ۱۰", callback_data=f"admin:adj_asset:{country_id}:{equipment_key}:10"),
            InlineKeyboardButton("➕ ۱۰۰", callback_data=f"admin:adj_asset:{country_id}:{equipment_key}:100"),
            InlineKeyboardButton("➕ ۱,۰۰۰", callback_data=f"admin:adj_asset:{country_id}:{equipment_key}:1000"),
        ],
        [
            InlineKeyboardButton("➖ ۱۰", callback_data=f"admin:adj_asset:{country_id}:{equipment_key}:-10"),
            InlineKeyboardButton("➖ ۱۰۰", callback_data=f"admin:adj_asset:{country_id}:{equipment_key}:-100"),
            InlineKeyboardButton("➖ ۱,۰۰۰", callback_data=f"admin:adj_asset:{country_id}:{equipment_key}:-1000"),
        ],
        [
            InlineKeyboardButton("✏️ تنظیم عدد دقیق (تایپی)", callback_data=f"admin:prompt_asset:{country_id}:{equipment_key}"),
            InlineKeyboardButton("🗑️ صفر کردن", callback_data=f"admin:set_asset:{country_id}:{equipment_key}:0"),
        ],
        [
            InlineKeyboardButton("🔙 دسته‌ها", callback_data=f"admin:menu_assets:{country_id}"),
            InlineKeyboardButton("📂 همین دسته", callback_data=f"admin:asset_cat:{country_id}:{asset['category']}"),
        ]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== پردازش CallbackQuery های پنل ادمین ====================

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    if not is_admin(user_id):
        await query.answer("⛔ شما ادمین نیستید!", show_alert=True)
        return

    data = query.data
    await query.answer()

    if data.startswith("admin:tour"):
        if await tournament_admin_callback(query, context, data):
            return

    if data.startswith("admin:dom"):
        if await internal_admin_callback(query, context, data):
            return

    if data == "ignore":
        return

    if await handle_dossier_callbacks(query, context, data):
        return

    if data == "admin:menu":
        await admin_panel(update, context)

    elif data == "admin:close":
        await query.delete_message()

    elif data == "admin:toman_requests":
        pending = db.get_pending_payment_requests()
        if not pending:
            await safe_edit_or_reply(
                query,
                "💳 <b>هیچ فیش پرداخت تومانی در انتظار بررسی وجود ندارد.</b>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]]),
                parse_mode="HTML"
            )
            return

        text = f"💳 <b>لیست فیش‌های واریزی در انتظار بررسی ({len(pending)} مورد):</b>\n\nبرای مشاهده پرونده و فیش، روی مورد نظر کلیک کنید:"
        keyboard = []
        for p in pending:
            p_id = p["id"]
            user_lbl = f"@{p['country_username']}" if p.get("country_username") else f"ID: {p['player_id']}"
            btn_text = f"💰 #{p_id} | {p['amount_toman']:,} ت | {p['plan_title'][:20]} | {user_lbl}"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"admin:view_pay:{p_id}")])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")])
        await safe_edit_or_reply(query, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data.startswith("admin:view_pay:"):
        req_id = int(data.split(":")[2])
        p = db.get_payment_request_by_id(req_id)
        if not p:
            await safe_edit_or_reply(query, "❌ فیش پرداخت یافت نشد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:toman_requests")]]))
            return

        user_handle = f"@{p['country_username']}" if p.get("country_username") else "ندارد"
        c_label = f"{p['country_flag']} {p['country_name']}" if p.get("country_name") else "فاقد کشور فعال"

        militia_extra = ""
        if p.get("item_type") == "militia" and p.get("custom_payload"):
            try:
                wiz = json.loads(p["custom_payload"])
                militia_extra = (
                    f"\n🏴‍☠️ <b>مشخصات گروه درخواستی:</b>\n"
                    f"• <b>نام گروه:</b> {html.escape(wiz.get('name', ''))}\n"
                    f"• <b>نماد:</b> {html.escape(wiz.get('flag', ''))}\n"
                    f"• <b>مقر:</b> {html.escape(wiz.get('hq', ''))}\n"
                    f"• <b>دکترین:</b> {html.escape(wiz.get('doctrine', ''))}\n"
                )
            except Exception:
                pass

        dossier = (
            f"💳 <b>پرونده پرداخت تومانی — شماره #{p['id']}</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 <b>کاربر:</b> {user_handle} (<code>{p['player_id']}</code>)\n"
            f"🌐 <b>کشور:</b> {c_label}\n"
            f"{militia_extra}"
            f"📌 <b>پلن درخواستی:</b> {p['plan_title']}\n"
            f"💵 <b>مبلغ فاکتور:</b> <b>{p['amount_toman']:,} تومان</b>\n"
            f"📝 <b>کد پیگیری / توضیحات:</b> <code>{html.escape(p.get('tracking_code') or 'ثبت شده با عکس')}</code>\n"
            f"📅 <b>تاریخ ثبت:</b> <code>{str(p.get('created_at',''))[:19].replace('T',' ')}</code>\n"
            f"📊 <b>وضعیت فعلی:</b> <code>{p['status']}</code>\n"
        )
        if p.get("item_type") == "militia":
            kb = [
                [
                    InlineKeyboardButton("✅ تایید و ساخت فوری", callback_data=f"admin:pay_app:{p['id']}"),
                    InlineKeyboardButton("✏️ ویرایش نام و تایید", callback_data=f"admin:pay_rename:{p['id']}"),
                ],
                [
                    InlineKeyboardButton("❌ رد فیش", callback_data=f"admin:pay_rej:{p['id']}"),
                    InlineKeyboardButton("🔙 لیست فیش‌ها", callback_data="admin:toman_requests")
                ]
            ]
        else:
            kb = [
                [
                    InlineKeyboardButton("✅ تایید و فعال‌سازی فوری", callback_data=f"admin:pay_app:{p['id']}"),
                    InlineKeyboardButton("❌ رد فیش", callback_data=f"admin:pay_rej:{p['id']}"),
                ],
                [InlineKeyboardButton("🔙 بازگشت به لیست فیش‌ها", callback_data="admin:toman_requests")]
            ]

        await safe_edit_or_reply(query, dossier, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML", photo_id=p.get("receipt_photo_id"))

    elif data.startswith("admin:pay_app:"):
        req_id = int(data.split(":")[2])
        ok, msg, p = db.approve_payment_request(req_id, user_id)
        if not ok:
            err_text = f"❌ <b>خطا:</b> {html.escape(msg)}"
            err_kb = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:toman_requests")]]
            await safe_edit_or_reply(query, err_text, reply_markup=InlineKeyboardMarkup(err_kb), parse_mode="HTML")
            return

        # ارسال پیام تبریک و فعال‌سازی به کاربر
        player_id = p["player_id"]
        if p.get("item_type") == "militia":
            created_c = db.get_country_by_player(player_id)
            c_name = f"{created_c['flag']} {created_c['name']}" if created_c else "گروه اختصاصی شما"
            success_msg = (
                f"🎉 **تاسیس گروه غیردولتی {c_name} تایید و فعال گردید!**\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                "• 💰 **خزانه اولیه:** ۲۵ میلیون دلار\n"
                "• 🪖 **رزمندگان آماده‌باش:** ۶۰,۰۰۰ نفر\n"
                "• 🎖️ **تسلیحات نامتقارن:** تویوتا دوشکا، راکت‌انداز گراد، پهپاد ابابیل و قایق‌های تندرو در انبار مستقر شد\n"
                "• ⭐ **اشتراک طلایی VIP:** برای رهبر گروه فعال گردید\n\n"
                "👇 از دکمه‌های پایین صفحه برای هدایت و فرماندهی نیروهای خود استفاده فرمایید!"
            )
            militia_kb = [[InlineKeyboardButton("🏴‍☠️ ثبت مشخصات و تاسیس گروه", callback_data="vip:setup_militia")]] if not created_c else None
            try:
                if militia_kb:
                    await context.bot.send_message(chat_id=player_id, text=success_msg, reply_markup=InlineKeyboardMarkup(militia_kb), parse_mode="Markdown")
                else:
                    await context.bot.send_message(chat_id=player_id, text=success_msg, reply_markup=get_main_keyboard(player_id), parse_mode="Markdown")
            except Exception as e:
                print(f"Failed to notify user of militia license approval: {e}")
        else:
            success_msg = (
                f"🎉 **پرداخت شما با موفقیت تایید شد!**\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"📌 **سفارش:** {p['plan_title']}\n"
                f"💵 **مبلغ:** {p['amount_toman']:,} تومان\n\n"
                "✅ **خدمات و دسترسی‌های ویژه VIP برای شما فعال گردید.**\n"
                "از همراهی و حمایت شما از بازی «سیاست مدرن» صمیمانه سپاسگزاریم. 👑"
            )
            try:
                await context.bot.send_message(chat_id=player_id, text=success_msg, reply_markup=get_main_keyboard(player_id), parse_mode="Markdown")
            except Exception as e:
                print(f"Failed to notify user of payment approval: {e}")

        succ_admin_text = f"✅ <b>فیش #{req_id} با موفقیت تایید و خدمات ({html.escape(p['plan_title'])}) برای کاربر فعال شد.</b>"
        admin_kb = [
            [InlineKeyboardButton("💳 لیست فیش‌های باقیمانده", callback_data="admin:toman_requests")],
            [InlineKeyboardButton("🔙 پنل ادمین", callback_data="admin:menu")]
        ]
        await safe_edit_or_reply(query, succ_admin_text, reply_markup=InlineKeyboardMarkup(admin_kb), parse_mode="HTML")

    elif data.startswith("admin:pay_rename:"):
        req_id = int(data.split(":")[2])
        p = db.get_payment_request_by_id(req_id)
        if not p:
            await safe_edit_or_reply(query, "❌ فیش پرداخت یافت نشد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:toman_requests")]]))
            return

        context.user_data["admin_awaiting_input"] = {
            "type": "rename_militia_and_approve",
            "req_id": req_id
        }
        prompt_txt = (
            f"✏️ <b>ویرایش نام گروه و تایید فیش #{req_id}</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً <b>نام جدید و رسمی مصوب</b> برای این سازمان را ارسال فرمایید:\n\n"
            "<i>(به محض ارسال، گروه با این نام ایجاد و تاییدیه به بازیکن فرستاده می‌شود)</i>"
        )
        await safe_edit_or_reply(query, prompt_txt, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="admin:toman_requests")]]), parse_mode="HTML")

    elif data.startswith("admin:pay_rej:"):
        req_id = int(data.split(":")[2])
        ok, msg, p = db.reject_payment_request(req_id, user_id, "عدم واریز وجه یا فیش نامعتبر")
        if not ok:
            err_text = f"❌ <b>خطا:</b> {html.escape(msg)}"
            err_kb = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:toman_requests")]]
            await safe_edit_or_reply(query, err_text, reply_markup=InlineKeyboardMarkup(err_kb), parse_mode="HTML")
            return

        # اطلاع به کاربر
        player_id = p["player_id"]
        rej_msg = (
            f"❌ **فیش پرداخت شما تایید نشد**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"📌 **سفارش:** {p['plan_title']}\n"
            f"💵 **مبلغ:** {p['amount_toman']:,} تومان\n\n"
            "⚠️ **علت:** عدم انطباق با گردش حساب یا فیش نامعتبر.\n"
            "در صورت بروز اشتباه، لطفاً با پشتیبانی یا ارسال مجدد فیش معتبر پیگیری فرمایید."
        )
        try:
            await context.bot.send_message(chat_id=player_id, text=rej_msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Failed to notify user of payment rejection: {e}")

        rej_admin_text = f"❌ <b>فیش #{req_id} رد شد و به کاربر اطلاع داده شد.</b>"
        admin_kb = [
            [InlineKeyboardButton("💳 لیست فیش‌های باقیمانده", callback_data="admin:toman_requests")],
            [InlineKeyboardButton("🔙 پنل ادمین", callback_data="admin:menu")]
        ]
        await safe_edit_or_reply(query, rej_admin_text, reply_markup=InlineKeyboardMarkup(admin_kb), parse_mode="HTML")
        req_id = int(data.split(":")[2])
        ok, msg, p = db.reject_payment_request(req_id, user_id, "عدم واریز وجه یا فیش نامعتبر")
        if not ok:
            err_text = f"❌ {msg}"
            err_kb = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:toman_requests")]]
            if query.message and query.message.photo:
                try:
                    await query.edit_message_caption(caption=err_text, reply_markup=InlineKeyboardMarkup(err_kb), parse_mode="Markdown")
                except Exception:
                    await query.message.reply_text(err_text, reply_markup=InlineKeyboardMarkup(err_kb), parse_mode="Markdown")
            else:
                await query.edit_message_text(err_text, reply_markup=InlineKeyboardMarkup(err_kb), parse_mode="Markdown")
            return

        # اطلاع به کاربر
        player_id = p["player_id"]
        rej_msg = (
            f"❌ **فیش پرداخت شما تایید نشد**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"📌 **سفارش:** {p['plan_title']}\n"
            f"💵 **مبلغ:** {p['amount_toman']:,} تومان\n\n"
            "⚠️ **علت:** عدم انطباق با گردش حساب یا فیش نامعتبر.\n"
            "در صورت بروز اشتباه، لطفاً با پشتیبانی یا ارسال مجدد فیش معتبر پیگیری فرمایید."
        )
        try:
            await context.bot.send_message(chat_id=player_id, text=rej_msg, parse_mode="Markdown")
        except Exception as e:
            print(f"Failed to notify user of payment rejection: {e}")

        rej_admin_text = f"❌ **فیش #{req_id} رد شد و به کاربر اطلاع داده شد.**"
        admin_kb = [
            [InlineKeyboardButton("💳 لیست فیش‌های باقیمانده", callback_data="admin:toman_requests")],
            [InlineKeyboardButton("🔙 پنل ادمین", callback_data="admin:menu")]
        ]
        if query.message and query.message.photo:
            try:
                await query.edit_message_caption(caption=rej_admin_text, reply_markup=InlineKeyboardMarkup(admin_kb), parse_mode="Markdown")
            except Exception:
                await query.message.reply_text(rej_admin_text, reply_markup=InlineKeyboardMarkup(admin_kb), parse_mode="Markdown")
        else:
            try:
                await query.edit_message_text(rej_admin_text, reply_markup=InlineKeyboardMarkup(admin_kb), parse_mode="Markdown")
            except Exception:
                await query.message.reply_text(rej_admin_text, reply_markup=InlineKeyboardMarkup(admin_kb), parse_mode="Markdown")

    elif data == "admin:claim_un":
        admin_c = db.get_country_by_player(user_id)
        if admin_c:
            if admin_c.get("country_key") == "un":
                await query.edit_message_text(
                    "🇺🇳 **نقش سازمان ملل متحد از قبل برای شما فعال می‌باشد.**",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton("🇺🇳 ورود به اتاق ویژه دبیرکل سازمان ملل", callback_data="un:menu")],
                        [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]
                    ]),
                    parse_mode="Markdown"
                )
                return

            text = (
                f"⚠️ **فعال‌سازی نقش سازمان ملل متحد (🇺🇳)**\n"
                f"━━━━━━━━━━━━━━━━━━\n\n"
                f"شما در حال حاضر هدایت کشور {admin_c['flag']} **{admin_c['name']}** را بر عهده دارید.\n\n"
                "جهت فعال‌سازی و دریافت کشور/نقش سازمان ملل، ابتدا باید کشور فعلی خود را لغو بفرمایید تا بدون کشور شوید."
            )
            keyboard = [
                [InlineKeyboardButton("❌ حذف کشور فعلی و فعال‌سازی سازمان ملل", callback_data="admin:reset_and_claim_un")],
                [InlineKeyboardButton("🔙 انصراف و بازگشت به پنل ادمین", callback_data="admin:menu")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return

        success, msg = db.claim_un_country(user_id)
        keyboard = [
            [InlineKeyboardButton("🇺🇳 ورود به اتاق ویژه دبیرکل سازمان ملل", callback_data="un:menu")],
            [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]
        ]
        await query.edit_message_text(f"{msg}\n\nاز این پس می‌توانید از تمام امکانات دبیرکل سازمان ملل استفاده بفرمایید.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:reset_and_claim_un":
        db.delete_country_by_player(user_id)
        success, msg = db.claim_un_country(user_id)
        keyboard = [
            [InlineKeyboardButton("🇺🇳 ورود به اتاق ویژه دبیرکل سازمان ملل", callback_data="un:menu")],
            [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]
        ]
        await query.edit_message_text(f"✅ کشور قبلی شما لغو شد.\n\n{msg}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:locks_menu":
        await admin_locks_menu(query, context)

    elif data.startswith("admin:toggle_lock:"):
        lock_key = data.split(":")[2]
        curr_val = db.get_setting(lock_key) == "1"
        new_val = "0" if curr_val else "1"
        db.set_setting(lock_key, new_val)
        await query.answer("وضعیت قفل با موفقیت تغییر یافت!", show_alert=True)
        await admin_locks_menu(query, context)

    elif data.startswith("admin:list:"):
        parts = data.split(":")
        page = int(parts[2])
        filter_cont = parts[3] if len(parts) > 3 else None
        await show_countries_list(query, context, page=page, filter_continent=filter_cont)

    elif data == "admin:search_country_prompt":
        context.user_data["admin_awaiting_input"] = {"type": "admin_search_country"}
        await query.edit_message_text(
            "🔎 **جستجوی کشور در پنل مدیریت**\n━━━━━━━━━━━━━━━━━━\n\nلطفاً **نام کشور، کلید کشور یا شناسه بازیکن** را ارسال فرمایید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به لیست کشورها", callback_data="admin:list:0")]]),
            parse_mode="Markdown"
        )

    elif data.startswith("admin:c:"):
        c_id = int(data.split(":")[2])
        await show_country_dashboard(query, context, c_id)

    elif data == "admin:stats":
        stats = db.get_game_stats()
        text = (
            "📊 *آمار کلی بازی «سیاست مدرن»*\n\n"
            f"🌐 تعداد کشورهای ساخته شده: `{stats['countries_count']}`\n"
            f"🏦 مجموع کل ثروت خزانه کشورها: {format_money(stats['total_treasury'])}\n"
            f"🪙 مجموع طلا در گردش: {format_number(stats['total_gold'])}\n"
            f"🛢️ مجموع ذخایر نفت: {format_oil(stats['total_oil'])}\n"
            f"🪖 مجموع کل تجهیزات و تسلیحات نظامی: {format_number(stats['total_equipment'])} عدد"
        )
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:anti_cheat_radar":
        suspicious_list = db.get_suspicious_activities(15)
        text = (
            "🚨 <b>رادار ضدتقلب و مانیتورینگ تراکنش‌های مشکوک</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "این سیستم به‌صورت هوشمند تراکنش‌های سنگین، کمک‌های مالی بالای ۲۰ میلیون دلار و نقل‌وانتقالات غیرعادی را جهت کشف مولتی‌اکانت رصد می‌کند:\n\n"
        )
        keyboard = []
        if not suspicious_list:
            text += "✅ <b>هیچ تراکنش یا فعالیت مشکوکی در سیستم ثبت نشده است.</b>\n"
        else:
            for item in suspicious_list[:8]:
                dt = str(item.get("created_at", ""))[:19].replace("T", " ")
                c_flag = item.get("country_flag", "🏴")
                c_name = item.get("country_name", "نامشخص")
                amt = item.get("amount", 0)
                desc = item.get("description", "")
                text += f"• <code>{dt}</code> | {c_flag} <b>{c_name}</b>\n  ⚠️ <i>شرح:</i> {desc} (مبلغ: <b>{format_money(amt)}</b>)\n\n"

        keyboard.append([InlineKeyboardButton("💾 تهیه پشتیبان فوری دیتابیس (Backup)", callback_data="admin:backup_db")])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data == "admin:backup_db":
        ok, res = db.backup_database()
        if ok:
            file_size = os.path.getsize(res) / (1024 * 1024) if os.path.exists(res) else 0
            text = (
                "💾 <b>پشتیبان‌گیری از دیتابیس با موفقیت انجام شد!</b>\n"
                "━━━━━━━━━━━━━━━━━━\n\n"
                f"• 📁 <b>نام فایل:</b> <code>{os.path.basename(res)}</code>\n"
                f"• 📦 <b>حجم فایل:</b> <code>{file_size:.2f} MB</code>\n"
                "• 🔒 فایل در مسیر امن <code>backups/</code> سرور با آخرین وضعیت ذخیره گردید."
            )
        else:
            text = f"❌ <b>خطا در تهیه بک‌آپ دیتابیس:</b>\n\n<code>{res}</code>"

        keyboard = [
            [InlineKeyboardButton("🚨 بازگشت به رادار ضدتقلب", callback_data="admin:anti_cheat_radar")],
            [InlineKeyboardButton("🔙 منوی ادمین", callback_data="admin:menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

    elif data == "admin:monitor_menu":
        text = (
            "🔎 **رصد و پایش فعالیت بازیکنان**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "جهت مشاهده آخرین فعالیت‌ها، تراکنش‌ها و پیام‌های دیپلماتیک بازیکنان، بخش مورد نظر را انتخاب بفرمایید:"
        )
        keyboard = [
            [InlineKeyboardButton("✉️ رصد معاهدات و پیام‌های دیپلماتیک", callback_data="admin:dip_logs")],
            [InlineKeyboardButton("📜 رصد فعالیت‌ها و لاگ‌های سیستم", callback_data="admin:activity_logs")],
            [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:activity_logs":
        logs = db.get_recent_logs(20)
        lines = ["📜 *رصد آخرین فعالیت‌ها و لاگ‌های سیستم*\n━━━━━━━━━━━━━━━━━━\n"]
        if not logs:
            lines.append("هیچ لاگی در سیستم ثبت نشده است.")
        else:
            for lg in logs:
                dt_str = lg.get("created_at", "")[:19].replace("T", " ")
                actor_id = lg.get("actor", "")
                c = db.get_country_by_player(int(actor_id)) if (actor_id and actor_id.isdigit()) else None
                c_str = f"{c['flag']} {c['name']}" if c else f"`{actor_id}`"
                act_str = str(lg.get("action", "")).replace("_", "\\_")
                det_str = str(lg.get("details", "")).replace("_", "\\_")
                lines.append(f"• `{dt_str}` | *کاربر:* {c_str} | *عملیات:* `{act_str}` | {det_str}\n")
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به رصد بازیکنان", callback_data="admin:monitor_menu")]]
        try:
            await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        except Exception:
            try:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))
            except Exception:
                pass

    elif data == "admin:dip_logs":
        txs = db.get_recent_diplomatic_logs(20)
        lines = ["✉️ *رصد آخرین معاهدات و تراکنش‌های دیپلماتیک*\n━━━━━━━━━━━━━━━━━━\n"]
        if not txs:
            lines.append("هیچ معاهده یا تراکنش دیپلماتیکی ثبت نشده است.")
        else:
            for tx in txs:
                dt_str = tx.get("created_at", "")[:19].replace("T", " ")
                c = db.get_country_by_id(tx["country_id"])
                c_name = f"{c['flag']} {c['name']}" if c else "نامشخص"
                lines.append(f"• `{dt_str}` | *{c_name}:* {tx.get('description')} | *مبلغ/حجم:* {tx.get('amount')}\n")
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به رصد بازیکنان", callback_data="admin:monitor_menu")]]
        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data in ("admin:rankings", "admin:rank_menu"):
        text = (
            "🏆 *سامانه جامع رتبه‌بندی کشورهای بازی «سیاست مدرن»*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً حوزه مورد نظر را جهت مشاهده جدول رده‌بندی انتخاب فرمایید:"
        )
        keyboard = [
            [InlineKeyboardButton("🛢️ رتبه‌بندی قدرت نفتی و انرژی", callback_data="admin:rank:oil:0")],
            [InlineKeyboardButton("🌾 رتبه‌بندی غلات و امنیت غذایی", callback_data="admin:rank:grain:0")],
            [InlineKeyboardButton("💻 رتبه‌بندی فناوری و میکروچیپ", callback_data="admin:rank:chips:0")],
            [InlineKeyboardButton("☢️ رتبه‌بندی اورانیوم و سوخت هسته‌ای", callback_data="admin:rank:uranium:0")],
            [InlineKeyboardButton("🚀 رتبه‌بندی زرادخانه کلاهک‌های بازدارنده", callback_data="admin:rank:nuclear:0")],
            [InlineKeyboardButton("🏦 رتبه‌بندی اقتصاد، خزانه و ثروت ملی", callback_data="admin:rank:economy:0")],
            [InlineKeyboardButton("🪖 رتبه‌بندی ارتش و توان نظامی (شاخه به شاخه)", callback_data="admin:rank:mil_menu")],
            [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


    elif data.startswith("admin:rank:uranium"):
        parts = data.split(":")
        page = int(parts[3]) if len(parts) > 3 else 0
        per_page = 10
        countries = db.get_all_countries()

        if not countries:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")]]
            await query.edit_message_text("❌ هیچ کشوری ساخته نشده است.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            sorted_c = sorted(countries, key=lambda x: -((x.get('uranium_ore') or 0) * 10 + (x.get('uranium_ore_daily') or 0) * 1000 + (x.get('nuclear_fuel') or 0)))
            total_pages = max(1, math.ceil(len(sorted_c) / per_page))
            page = max(0, min(page, total_pages - 1))
            start_idx = page * per_page
            slice_c = sorted_c[start_idx:start_idx + per_page]

            lines = [f"☢️ *رتبه‌بندی ذخایر و تولید اورانیوم و سوخت هسته‌ای (صفحه {page + 1} از {total_pages})*\n━━━━━━━━━━━━━━━━━━\n"]
            for idx, c in enumerate(slice_c, start_idx + 1):
                u_res = c.get('uranium_ore') or 0
                u_prod = c.get('uranium_ore_daily') or 0
                fuel_res = c.get('nuclear_fuel') or 0
                fuel_prod = c.get('nuclear_fuel_daily') or 0
                lines.append(
                    f"{idx}. {c.get('flag','')} *{c.get('name','')}*\n"
                    f"   • ☢️ ذخایر کیک زرد: `{format_number(u_res)} تن` | تولید: `+{format_number(u_prod)} تن/روز`\n"
                    f"   • 🧪 سوخت هسته‌ای: `{format_number(fuel_res)} کیلوگرم` | تولید: `+{format_number(fuel_prod)} ک‌گ/روز`\n"
                )
            nav_row = []
            if page > 0:
                nav_row.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:rank:uranium:{page - 1}"))
            if total_pages > 1:
                nav_row.append(InlineKeyboardButton(f"صفحه {page + 1} از {total_pages}", callback_data="ignore"))
            if page < total_pages - 1:
                nav_row.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:rank:uranium:{page + 1}"))

            keyboard = []
            if nav_row:
                keyboard.append(nav_row)
            keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")])

            try:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            except Exception:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("admin:rank:nuclear"):
        parts = data.split(":")
        page = int(parts[3]) if len(parts) > 3 else 0
        per_page = 10
        countries = db.get_all_countries()

        if not countries:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")]]
            await query.edit_message_text("❌ هیچ کشوری ساخته نشده است.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            sorted_c = sorted(countries, key=lambda x: -(x.get('warheads') or 0))
            total_pages = max(1, math.ceil(len(sorted_c) / per_page))
            page = max(0, min(page, total_pages - 1))
            start_idx = page * per_page
            slice_c = sorted_c[start_idx:start_idx + per_page]

            lines = [f"🚀 *رتبه‌بندی زرادخانه کلاهک‌های بازدارنده هسته‌ای (صفحه {page + 1} از {total_pages})*\n━━━━━━━━━━━━━━━━━━\n"]
            for idx, c in enumerate(slice_c, start_idx + 1):
                wh = c.get('warheads') or 0
                lines.append(
                    f"{idx}. {c.get('flag','')} *{c.get('name','')}*\n"
                    f"   • 🚀 کلاهک‌های راهبردی مستقر: `☢️ {format_number(wh)} عدد`\n"
                    f"   • 💵 هزینه نگهداری روزانه: `{format_money(wh * 5_000_000)}/روز` + `{wh * 2} چیپ/روز`\n"
                )
            nav_row = []
            if page > 0:
                nav_row.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:rank:nuclear:{page - 1}"))
            if total_pages > 1:
                nav_row.append(InlineKeyboardButton(f"صفحه {page + 1} از {total_pages}", callback_data="ignore"))
            if page < total_pages - 1:
                nav_row.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:rank:nuclear:{page + 1}"))

            keyboard = []
            if nav_row:
                keyboard.append(nav_row)
            keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")])

            try:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            except Exception:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("admin:rank:chips"):
        parts = data.split(":")
        page = int(parts[3]) if len(parts) > 3 else 0
        per_page = 10
        countries = db.get_all_countries()
        
        if not countries:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")]]
            await query.edit_message_text("❌ هیچ کشوری ساخته نشده است.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            sorted_c = sorted(countries, key=lambda c: -( ((c.get('microchips_daily', 0) or 0) * 100) + (c.get('microchips', 0) or 0) ))
            total_pages = max(1, math.ceil(len(sorted_c) / per_page))
            page = max(0, min(page, total_pages - 1))
            start_idx = page * per_page
            slice_c = sorted_c[start_idx:start_idx + per_page]

            lines = [f"💻 *رتبه‌بندی فناوری و تولید نیمه‌هادی (صفحه {page + 1} از {total_pages})*\n━━━━━━━━━━━━━━━━━━\n"]
            for idx, c in enumerate(slice_c, start_idx + 1):
                lines.append(
                    f"{idx}. {c.get('flag','')} *{c.get('name','')}*\n"
                    f"   • 💻 ذخیره تراشه: `{format_number(c.get('microchips', 0))} عدد`\n"
                    f"   • 🏭 تولید روزانه: `+{format_number(c.get('microchips_daily', 0))} عدد/روز`\n"
                    f"   • 🔬 سطح فناوری: `سطح {c.get('tech_level', 1)}`\n"
                )
            nav_row = []
            if page > 0:
                nav_row.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:rank:chips:{page - 1}"))
            if total_pages > 1:
                nav_row.append(InlineKeyboardButton(f"صفحه {page + 1} از {total_pages}", callback_data="ignore"))
            if page < total_pages - 1:
                nav_row.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:rank:chips:{page + 1}"))
            
            keyboard = []
            if nav_row:
                keyboard.append(nav_row)
            keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")])
            
            try:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            except Exception:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "admin:rank:mil_menu":
        text = (
            "🪖 *رتبه‌بندی نیروهای مسلح و قدرت نظامی*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً شاخه یا رده نظامی مورد نظر را انتخاب فرمایید:"
        )
        keyboard = [
            [InlineKeyboardButton("🎖️ ارتش کلی و کل قوا", callback_data="admin:rank:mil_total:0")],
            [
                InlineKeyboardButton("🛡️ نیروی زمینی", callback_data="admin:rank:mil_ground:0"),
                InlineKeyboardButton("✈️ نیروی هوایی و پهپادی", callback_data="admin:rank:mil_air:0"),
            ],
            [
                InlineKeyboardButton("⚓ نیروی دریایی و ناوگان", callback_data="admin:rank:mil_navy:0"),
                InlineKeyboardButton("🚀 موشکی و پدافند هوایی", callback_data="admin:rank:mil_missile:0"),
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("admin:rank:oil"):
        parts = data.split(":")
        page = int(parts[3]) if len(parts) > 3 else 0
        per_page = 10
        countries = db.get_all_countries()
        
        if not countries:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")]]
            await query.edit_message_text("❌ هیچ کشوری ساخته نشده است.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            sorted_c = sorted(countries, key=lambda c: -( (c.get('oil_reserves', 0) or 0) * 1000 + ((c.get('oil_production', 0) or 0)) ))
            total_pages = max(1, math.ceil(len(sorted_c) / per_page))
            page = max(0, min(page, total_pages - 1))
            start_idx = page * per_page
            slice_c = sorted_c[start_idx:start_idx + per_page]

            lines = [f"🛢️ *رتبه‌بندی قدرت نفتی و انرژی (صفحه {page + 1} از {total_pages})*\n━━━━━━━━━━━━━━━━━━\n"]
            for idx, c in enumerate(slice_c, start_idx + 1):
                reqs = approval_system.calculate_country_requirements(c)
                net_oil = (c.get('oil_production', 0) or 0) - reqs['oil_need_daily']
                net_str = f"+{format_oil(net_oil)}" if net_oil >= 0 else f"-{format_oil(abs(net_oil))}"
                lines.append(
                    f"{idx}. {c.get('flag','')} *{c.get('name','')}*\n"
                    f"   • 🛢️ ذخیره: `{format_oil(c.get('oil_reserves', 0))}` | ⚡ تولید: `+{format_oil(c.get('oil_production', 0))}/روز`\n"
                    f"   • ⚖️ تراز خالص: `{net_str}/روز`\n"
                )
            nav_row = []
            if page > 0:
                nav_row.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:rank:oil:{page - 1}"))
            if total_pages > 1:
                nav_row.append(InlineKeyboardButton(f"صفحه {page + 1} از {total_pages}", callback_data="ignore"))
            if page < total_pages - 1:
                nav_row.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:rank:oil:{page + 1}"))
            
            keyboard = []
            if nav_row:
                keyboard.append(nav_row)
            keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")])
            
            try:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            except Exception:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("admin:rank:grain"):
        parts = data.split(":")
        page = int(parts[3]) if len(parts) > 3 else 0
        per_page = 10
        countries = db.get_all_countries()
        
        if not countries:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")]]
            await query.edit_message_text("❌ هیچ کشوری ساخته نشده است.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            sorted_c = sorted(countries, key=lambda c: -( (c.get('grain_daily', 0) or 0) * 1000 + (c.get('grain', 0) or 0) ))
            total_pages = max(1, math.ceil(len(sorted_c) / per_page))
            page = max(0, min(page, total_pages - 1))
            start_idx = page * per_page
            slice_c = sorted_c[start_idx:start_idx + per_page]

            lines = [f"🌾 *رتبه‌بندی غلات و امنیت غذایی (صفحه {page + 1} از {total_pages})*\n━━━━━━━━━━━━━━━━━━\n"]
            for idx, c in enumerate(slice_c, start_idx + 1):
                reqs = approval_system.calculate_country_requirements(c)
                net_g = (c.get('grain_daily', 0) or 0) - reqs['grain_need_daily']
                net_g_str = f"+{format_number(net_g)}" if net_g >= 0 else f"-{format_number(abs(net_g))}"
                lines.append(
                    f"{idx}. {c.get('flag','')} *{c.get('name','')}*\n"
                    f"   • 🌾 ذخیره: `{format_number(c.get('grain', 0))} تن` | 🚜 تولید: `+{format_number(c.get('grain_daily', 0))} تن/روز`\n"
                    f"   • 👥 مصرف: `-{format_number(reqs['grain_need_daily'])} تن/روز` | ⚖️ تراز: `{net_g_str} تن/روز`\n"
                )
            nav_row = []
            if page > 0:
                nav_row.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:rank:grain:{page - 1}"))
            if total_pages > 1:
                nav_row.append(InlineKeyboardButton(f"صفحه {page + 1} از {total_pages}", callback_data="ignore"))
            if page < total_pages - 1:
                nav_row.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:rank:grain:{page + 1}"))
            
            keyboard = []
            if nav_row:
                keyboard.append(nav_row)
            keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")])
            
            try:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            except Exception:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("admin:rank:economy"):
        parts = data.split(":")
        page = int(parts[3]) if len(parts) > 3 else 0
        per_page = 10
        countries = db.get_all_countries()
        
        if not countries:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")]]
            await query.edit_message_text("❌ هیچ کشوری ساخته نشده است.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            sorted_c = sorted(countries, key=lambda c: -( (c.get('treasury', 0) or 0) + ((c.get('gold', 0) or 0) * 250_000) + ((c.get('daily_income', 0) or 0) * 25) + ((c.get('tax_income', 0) or 0) * 20) ))
            total_pages = max(1, math.ceil(len(sorted_c) / per_page))
            page = max(0, min(page, total_pages - 1))
            start_idx = page * per_page
            slice_c = sorted_c[start_idx:start_idx + per_page]

            lines = [f"🏦 *رتبه‌بندی اقتصاد، خزانه و ثروت ملی (صفحه {page + 1} از {total_pages})*\n━━━━━━━━━━━━━━━━━━\n"]
            for idx, c in enumerate(slice_c, start_idx + 1):
                lines.append(
                    f"{idx}. {c.get('flag','')} *{c.get('name','')}*\n"
                    f"   • 🏦 خزانه: `{format_money(c.get('treasury', 0))}` | 📈 درآمد: `+{format_money(c.get('daily_income', 0))}/روز`\n"
                    f"   • 🪙 طلا: `{format_number(c.get('gold', 0))} شمش` | 💰 مالیات: `+{format_money(c.get('tax_income', 0))}/روز`\n"
                )
            nav_row = []
            if page > 0:
                nav_row.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:rank:economy:{page - 1}"))
            if total_pages > 1:
                nav_row.append(InlineKeyboardButton(f"صفحه {page + 1} از {total_pages}", callback_data="ignore"))
            if page < total_pages - 1:
                nav_row.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:rank:economy:{page + 1}"))
            
            keyboard = []
            if nav_row:
                keyboard.append(nav_row)
            keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")])
            
            try:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            except Exception:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("admin:rank:mil_total"):
        parts = data.split(":")
        page = int(parts[3]) if len(parts) > 3 else 0
        per_page = 10
        countries = db.get_all_countries()
        
        if not countries:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")]]
            await query.edit_message_text("❌ هیچ کشوری ساخته نشده است.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            mil_data = []
            for c in countries:
                assets = db.get_country_assets(c['id'])
                tot_val = sum((a.get('amount', 0) or 0) * (a.get('buy_price', 0) or 0) for a in assets)
                tot_units = sum(a.get('amount', 0) or 0 for a in assets)
                personnel = c.get('active_personnel', 0) or 0
                readiness = c.get('combat_readiness', 70)
                power_index = tot_val + (personnel * 500) + (readiness * 10_000_000)
                mil_data.append((c, tot_val, tot_units, personnel, readiness, power_index))
            mil_data.sort(key=lambda x: -x[5])
            
            total_pages = max(1, math.ceil(len(mil_data) / per_page))
            page = max(0, min(page, total_pages - 1))
            start_idx = page * per_page
            slice_mil = mil_data[start_idx:start_idx + per_page]

            lines = [f"🎖️ *رتبه‌بندی ارتش کلی و کل قوا (صفحه {page + 1} از {total_pages})*\n━━━━━━━━━━━━━━━━━━\n"]
            for idx, (c, tot_val, tot_units, personnel, readiness, p_idx) in enumerate(slice_mil, start_idx + 1):
                lines.append(
                    f"{idx}. {c.get('flag','')} *{c.get('name','')}*\n"
                    f"   • 🪖 پرسنل فعال: `{format_number(personnel)} نفر` (آمادگی: `{readiness}٪`)\n"
                    f"   • 📦 کل تسلیحات: `{format_number(tot_units)} واحد` | 💰 ارزش نظامی: `{format_money(tot_val)}`\n"
                )
            nav_row = []
            if page > 0:
                nav_row.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:rank:mil_total:{page - 1}"))
            if total_pages > 1:
                nav_row.append(InlineKeyboardButton(f"صفحه {page + 1} از {total_pages}", callback_data="ignore"))
            if page < total_pages - 1:
                nav_row.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:rank:mil_total:{page + 1}"))
            
            keyboard = []
            if nav_row:
                keyboard.append(nav_row)
            keyboard.append([InlineKeyboardButton("🪖 بازگشت به دسته‌های ارتش", callback_data="admin:rank:mil_menu")])
            keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")])
            
            try:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            except Exception:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("admin:rank:mil_ground"):
        parts = data.split(":")
        page = int(parts[3]) if len(parts) > 3 else 0
        per_page = 10
        countries = db.get_all_countries()
        
        if not countries:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")]]
            await query.edit_message_text("❌ هیچ کشوری ساخته نشده است.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            branch_data = []
            for c in countries:
                assets = db.get_country_assets(c['id'])
                matched = [a for a in assets if a.get('category') in ('Ground Forces', 'Artillery')]
                val = sum((a.get('amount', 0) or 0) * (a.get('buy_price', 0) or 0) for a in matched)
                units = sum(a.get('amount', 0) or 0 for a in matched)
                personnel = c.get('active_personnel', 0) or 0
                score = val + (units * 50_000) + (personnel * 500)
                branch_data.append((c, val, units, personnel, score))
            branch_data.sort(key=lambda x: -x[4])
            
            total_pages = max(1, math.ceil(len(branch_data) / per_page))
            page = max(0, min(page, total_pages - 1))
            start_idx = page * per_page
            slice_br = branch_data[start_idx:start_idx + per_page]

            lines = [f"🛡️ *رتبه‌بندی نیروی زمینی و زرهی (صفحه {page + 1} از {total_pages})*\n━━━━━━━━━━━━━━━━━━\n"]
            for idx, (c, val, units, personnel, score) in enumerate(slice_br, start_idx + 1):
                lines.append(
                    f"{idx}. {c.get('flag','')} *{c.get('name','')}*\n"
                    f"   • 🛡️ تجهیزات زرهی و توپخانه: `{format_number(units)} واحد`\n"
                    f"   • 👤 نیروی زمینی فعال: `{format_number(personnel)} نفر`\n"
                    f"   • 💰 ارزش یگان‌های زمینی: `{format_money(val)}`\n"
                )
            nav_row = []
            if page > 0:
                nav_row.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:rank:mil_ground:{page - 1}"))
            if total_pages > 1:
                nav_row.append(InlineKeyboardButton(f"صفحه {page + 1} از {total_pages}", callback_data="ignore"))
            if page < total_pages - 1:
                nav_row.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:rank:mil_ground:{page + 1}"))
            
            keyboard = []
            if nav_row:
                keyboard.append(nav_row)
            keyboard.append([InlineKeyboardButton("🪖 بازگشت به دسته‌های ارتش", callback_data="admin:rank:mil_menu")])
            keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")])
            
            try:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            except Exception:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("admin:rank:mil_air"):
        parts = data.split(":")
        page = int(parts[3]) if len(parts) > 3 else 0
        per_page = 10
        countries = db.get_all_countries()
        
        if not countries:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")]]
            await query.edit_message_text("❌ هیچ کشوری ساخته نشده است.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            branch_data = []
            for c in countries:
                assets = db.get_country_assets(c['id'])
                aircraft = [a for a in assets if a.get('category') == 'Aircraft']
                uavs = [a for a in assets if a.get('category') == 'UAV']
                air_count = sum(a.get('amount', 0) or 0 for a in aircraft)
                uav_count = sum(a.get('amount', 0) or 0 for a in uavs)
                val = sum((a.get('amount', 0) or 0) * (a.get('buy_price', 0) or 0) for a in (aircraft + uavs))
                score = val + (air_count * 2_000_000) + (uav_count * 100_000)
                branch_data.append((c, air_count, uav_count, val, score))
            branch_data.sort(key=lambda x: -x[4])
            
            total_pages = max(1, math.ceil(len(branch_data) / per_page))
            page = max(0, min(page, total_pages - 1))
            start_idx = page * per_page
            slice_br = branch_data[start_idx:start_idx + per_page]

            lines = [f"✈️ *رتبه‌بندی نیروی هوایی و پهپادی (صفحه {page + 1} از {total_pages})*\n━━━━━━━━━━━━━━━━━━\n"]
            for idx, (c, air_count, uav_count, val, score) in enumerate(slice_br, start_idx + 1):
                lines.append(
                    f"{idx}. {c.get('flag','')} *{c.get('name','')}*\n"
                    f"   • ✈️ هواپیما و بالگرد: `{format_number(air_count)} فروند`\n"
                    f"   • 🛩️ پهپادها: `{format_number(uav_count)} فروند`\n"
                    f"   • 💰 ارزش ناوگان هوایی: `{format_money(val)}`\n"
                )
            nav_row = []
            if page > 0:
                nav_row.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:rank:mil_air:{page - 1}"))
            if total_pages > 1:
                nav_row.append(InlineKeyboardButton(f"صفحه {page + 1} از {total_pages}", callback_data="ignore"))
            if page < total_pages - 1:
                nav_row.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:rank:mil_air:{page + 1}"))
            
            keyboard = []
            if nav_row:
                keyboard.append(nav_row)
            keyboard.append([InlineKeyboardButton("🪖 بازگشت به دسته‌های ارتش", callback_data="admin:rank:mil_menu")])
            keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")])
            
            try:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            except Exception:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("admin:rank:mil_navy"):
        parts = data.split(":")
        page = int(parts[3]) if len(parts) > 3 else 0
        per_page = 10
        countries = db.get_all_countries()
        
        if not countries:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")]]
            await query.edit_message_text("❌ هیچ کشوری ساخته نشده است.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            branch_data = []
            for c in countries:
                assets = db.get_country_assets(c['id'])
                navy_assets = [a for a in assets if a.get('category') == 'Navy']
                val = sum((a.get('amount', 0) or 0) * (a.get('buy_price', 0) or 0) for a in navy_assets)
                units = sum(a.get('amount', 0) or 0 for a in navy_assets)
                score = val + (units * 1_000_000)
                branch_data.append((c, units, val, score))
            branch_data.sort(key=lambda x: -x[3])
            
            total_pages = max(1, math.ceil(len(branch_data) / per_page))
            page = max(0, min(page, total_pages - 1))
            start_idx = page * per_page
            slice_br = branch_data[start_idx:start_idx + per_page]

            lines = [f"⚓ *رتبه‌بندی نیروی دریایی و ناوگان (صفحه {page + 1} از {total_pages})*\n━━━━━━━━━━━━━━━━━━\n"]
            for idx, (c, units, val, score) in enumerate(slice_br, start_idx + 1):
                lines.append(
                    f"{idx}. {c.get('flag','')} *{c.get('name','')}*\n"
                    f"   • 🚢 مجموع ناوگان و شناورها: `{format_number(units)} فروند`\n"
                    f"   • 💰 ارزش ناوگان دریایی: `{format_money(val)}`\n"
                )
            nav_row = []
            if page > 0:
                nav_row.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:rank:mil_navy:{page - 1}"))
            if total_pages > 1:
                nav_row.append(InlineKeyboardButton(f"صفحه {page + 1} از {total_pages}", callback_data="ignore"))
            if page < total_pages - 1:
                nav_row.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:rank:mil_navy:{page + 1}"))
            
            keyboard = []
            if nav_row:
                keyboard.append(nav_row)
            keyboard.append([InlineKeyboardButton("🪖 بازگشت به دسته‌های ارتش", callback_data="admin:rank:mil_menu")])
            keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")])
            
            try:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            except Exception:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("admin:rank:mil_missile"):
        parts = data.split(":")
        page = int(parts[3]) if len(parts) > 3 else 0
        per_page = 10
        countries = db.get_all_countries()
        
        if not countries:
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")]]
            await query.edit_message_text("❌ هیچ کشوری ساخته نشده است.", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            branch_data = []
            for c in countries:
                assets = db.get_country_assets(c['id'])
                missiles = [a for a in assets if a.get('category') == 'Missiles']
                ads = [a for a in assets if a.get('category') == 'Air Defense']
                missile_count = sum(a.get('amount', 0) or 0 for a in missiles)
                ad_count = sum(a.get('amount', 0) or 0 for a in ads)
                val = sum((a.get('amount', 0) or 0) * (a.get('buy_price', 0) or 0) for a in (missiles + ads))
                score = val + (missile_count * 200_000) + (ad_count * 500_000)
                branch_data.append((c, missile_count, ad_count, val, score))
            branch_data.sort(key=lambda x: -x[4])
            
            total_pages = max(1, math.ceil(len(branch_data) / per_page))
            page = max(0, min(page, total_pages - 1))
            start_idx = page * per_page
            slice_br = branch_data[start_idx:start_idx + per_page]

            lines = [f"🚀 *رتبه‌بندی موشکی و پدافند هوایی (صفحه {page + 1} از {total_pages})*\n━━━━━━━━━━━━━━━━━━\n"]
            for idx, (c, missile_count, ad_count, val, score) in enumerate(slice_br, start_idx + 1):
                lines.append(
                    f"{idx}. {c.get('flag','')} *{c.get('name','')}*\n"
                    f"   • 🚀 زرادخانه موشکی: `{format_number(missile_count)} فروند`\n"
                    f"   • 🛡️ سامانه‌های پدافند هوایی: `{format_number(ad_count)} واحد`\n"
                    f"   • 💰 ارزش زرادخانه استراتژیک: `{format_money(val)}`\n"
                )
            nav_row = []
            if page > 0:
                nav_row.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:rank:mil_missile:{page - 1}"))
            if total_pages > 1:
                nav_row.append(InlineKeyboardButton(f"صفحه {page + 1} از {total_pages}", callback_data="ignore"))
            if page < total_pages - 1:
                nav_row.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:rank:mil_missile:{page + 1}"))
            
            keyboard = []
            if nav_row:
                keyboard.append(nav_row)
            keyboard.append([InlineKeyboardButton("🪖 بازگشت به دسته‌های ارتش", callback_data="admin:rank:mil_menu")])
            keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی رتبه‌بندی", callback_data="admin:rankings")])
            
            try:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            except Exception:
                await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard))

    elif data == "admin:pending_countries":
        pending_reqs = db.get_all_pending_country_requests()
        text = "📥 <b>درخواست‌های معلق انتخاب کشور (در انتظار تایید ادمین)</b>\n━━━━━━━━━━━━━━━━━━\n\n"

        keyboard = []
        if not pending_reqs:
            text += "✅ هیچ درخواست معلقی در حال حاضر وجود ندارد."
        else:
            text += "لطفاً جهت مشاهده مشخصات متقاضی، بررسی پیوی و تایید/رد، روی هر مورد کلیک کنید:\n\n"
            for req in pending_reqs:
                c_info = config.COUNTRIES.get(req["country_key"], {})
                flag = c_info.get("flag", "🏴")
                c_name = c_info.get("name", req["country_key"])
                u_name = f"@{req['username']}" if req.get("username") else f"ID: {req['player_id']}"

                keyboard.append([
                    InlineKeyboardButton(f"🔍 {flag} {c_name} — {u_name}", callback_data=f"admin:view_req:{req['id']}")
                ])

        keyboard.append([InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")])
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        except Exception:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("admin:view_req:"):
        req_id = int(data.split(":")[2])
        req = db.get_pending_country_request(req_id)
        if not req:
            await query.edit_message_text(
                "❌ این درخواست قبلاً تعیین تکلیف یا لغو شده است.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="admin:pending_countries")]])
            )
            return

        c_key = req["country_key"]
        c_info = config.COUNTRIES.get(c_key, {})
        flag = c_info.get("flag", "🏴")
        c_name = c_info.get("name", c_key)
        u_name = f"@{req['username']}" if req.get("username") else "فاقد یوزرنیم ⚠️"
        p_id = req["player_id"]
        full_name = f"{req.get('first_name', '')} {req.get('last_name', '')}".strip() or "ناشناس"
        created_time = str(req.get("created_at", "نامشخص"))[:19].replace("T", " ")

        prev_country = db.get_country_by_player(p_id)

        esc_c_name = html.escape(str(c_name))
        esc_full_name = html.escape(str(full_name))
        esc_u_name = html.escape(str(u_name))

        text = (
            "📋 <b>پرونده متقاضی دریافت کشور (بررسی ادمین)</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"🏳️ <b>کشور درخواستی:</b> {flag} {esc_c_name} (<code>{c_key}</code>)\n"
            f"👤 <b>نام و نام‌خانوادگی:</b> {esc_full_name}\n"
            f"🆔 <b>شناسه عددی (Player ID):</b> <code>{p_id}</code>\n"
            f"🔗 <b>یوزرنیم تلگرام:</b> {esc_u_name}\n"
            f"🕒 <b>تاریخ ثبت درخواست:</b> <code>{created_time}</code>\n\n"
            "🛡️ <b>ارزیابی امنیتی و سوابق:</b>\n"
        )

        if not req.get("username"):
            text += "⚠️ <i>هشدار:</i> کاربر فاقد آیدی تلگرام است (احتمال مولتی‌اکانت بالا)!\n"
        else:
            text += "✅ دارای آیدی تلگرام ثبت‌شده\n"

        if prev_country:
            esc_prev_name = html.escape(str(prev_country.get('name', '')))
            text += f"⚠️ <b>هشدار جدی:</b> این کاربر در حال حاضر کشور {prev_country.get('flag', '')} {esc_prev_name} را در اختیار دارد!\n"
        else:
            text += "✅ کاربر در حال حاضر مالک هیچ کشوری در بازی نیست.\n"

        raw_user = req.get("username")
        user_url = f"https://t.me/{raw_user.lstrip('@')}" if raw_user else f"tg://user?id={p_id}"

        kb = [
            [InlineKeyboardButton("👤 مشاهده پروفایل / چت در پیوی متقاضی", url=user_url)],
            [
                InlineKeyboardButton("✅ تایید و واگذاری کشور", callback_data=f"admin:approve_country:{req_id}"),
                InlineKeyboardButton("❌ رد درخواست", callback_data=f"admin:reject_country_menu:{req_id}")
            ],
            [InlineKeyboardButton("🔙 بازگشت به لیست درخواست‌ها", callback_data="admin:pending_countries")]
        ]
        try:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")
        except Exception:
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb))

    elif data.startswith("admin:reject_country_menu:") or (data.startswith("admin:reject_country:") and len(data.split(":")) == 3):
        req_id = int(data.split(":")[2])
        req = db.get_pending_country_request(req_id)
        if not req:
            await query.edit_message_text(
                "❌ این درخواست قبلاً تعیین تکلیف شده است.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به لیست", callback_data="admin:pending_countries")]])
            )
            return

        c_key = req["country_key"]
        c_info = config.COUNTRIES.get(c_key, {})
        flag = c_info.get("flag", "🏴")
        c_name = c_info.get("name", c_key)
        u_display = f"@{req['username']}" if req.get('username') else f"ID: {req['player_id']}"

        text = (
            f"❌ <b>رد درخواست انتخاب کشور {flag} {c_name}</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"👤 <b>متقاضی:</b> {u_display} (ID: <code>{req['player_id']}</code>)\n\n"
            "لطفاً دلیل رد درخواست را جهت اطلاع بازیکن انتخاب کنید یا دلیل اختصاصی بنویسید:"
        )

        kb = [
            [InlineKeyboardButton("🚫 عدم احراز هویت / اکانت مشکوک", callback_data=f"admin:do_reject:{req_id}:fake")],
            [InlineKeyboardButton("⚠️ سابقه تخلف / چند اکانتی (مولتی)", callback_data=f"admin:do_reject:{req_id}:multi")],
            [InlineKeyboardButton("🔒 کشور برای بازیکن دیگری رزرو است", callback_data=f"admin:do_reject:{req_id}:reserved")],
            [InlineKeyboardButton("✍️ نوشتن دلیل اختصاصی...", callback_data=f"admin:rej_prompt:{req_id}")],
            [InlineKeyboardButton("❌ رد فوری (بدون ذکر دلیل)", callback_data=f"admin:do_reject:{req_id}:none")],
            [InlineKeyboardButton("🔙 انصراف و بازگشت به پرونده", callback_data=f"admin:view_req:{req_id}")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

    elif data.startswith("admin:do_reject:"):
        parts = data.split(":")
        req_id = int(parts[2])
        reason_key = parts[3]

        reasons_map = {
            "fake": "عدم احراز هویت / حساب کاربری مشکوک یا نامعتبر",
            "multi": "مشاهده تخلف / فعالیت با چند حساب کاربری همزمان (مولتی‌اکانت)",
            "reserved": "این کشور از قبل برای بازیکن دیگری رزرو و هماهنگ شده است",
            "none": "عدم موافقت مدیریت عالی بازی با واگذاری این کشور",
        }
        reason_text = reasons_map.get(reason_key, "عدم موافقت مدیریت بازی")

        req = db.get_pending_country_request(req_id)
        if not req:
            await query.edit_message_text("❌ این درخواست قبلاً تعیین تکلیف شده است.", parse_mode="HTML")
            return

        c_key = req["country_key"]
        c_info = config.COUNTRIES.get(c_key, {})
        p_id = req["player_id"]
        u_display = f"@{req['username']}" if req.get('username') else f"ID: {p_id}"

        db.delete_pending_country_request(req_id)
        db.add_log(actor=str(user_id), action="reject_country", details=f"{c_key} for {p_id} (Reason: {reason_text})")

        await query.edit_message_text(
            f"❌ <b>درخواست کشور {c_info.get('flag', '')} {c_info.get('name', c_key)} برای کاربر {u_display} رد شد.</b>\n\n"
            f"📝 <b>دلیل ارسالی:</b> {reason_text}",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 لیست درخواست‌های معلق", callback_data="admin:pending_countries")],
                [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]
            ]),
            parse_mode="HTML"
        )

        player_msg = (
            f"❌ <b>درخواست شما برای انتخاب کشور {c_info.get('flag', '')} {c_info.get('name', c_key)} توسط مدیریت بازی رد شد.</b>\n\n"
            f"📝 <b>علت رد درخواست:</b>\n"
            f"«{reason_text}»\n\n"
            "💡 می‌توانید با ارسال مجدد دستور /start کشور دیگری را انتخاب فرمایید."
        )
        try:
            await context.bot.send_message(chat_id=p_id, text=player_msg, parse_mode="HTML")
        except Exception as e:
            print(f"Error sending reject message to player {p_id}: {e}")

    elif data.startswith("admin:rej_prompt:"):
        req_id = int(data.split(":")[2])
        req = db.get_pending_country_request(req_id)
        if not req:
            await query.edit_message_text("❌ این درخواست قبلاً تعیین تکلیف شده است.", parse_mode="HTML")
            return

        c_key = req["country_key"]
        c_info = config.COUNTRIES.get(c_key, {})

        context.user_data["admin_awaiting_input"] = {
            "type": "reject_country_reason",
            "req_id": req_id,
            "country_key": c_key,
            "player_id": req["player_id"],
            "username": req["username"]
        }

        await query.edit_message_text(
            f"✍️ <b>نوشتن دلیل اختصاصی برای رد کشور {c_info.get('flag', '')} {c_info.get('name', c_key)}</b>\n\n"
            f"👤 متقاضی: @{req['username']} (ID: <code>{req['player_id']}</code>)\n\n"
            "لطفاً متن دلیل رد درخواست را ارسال فرمایید تا همراه با پیام لغو برای بازیکن ارسال شود:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data=f"admin:view_req:{req_id}")]])
        )

    elif data in ("admin:roleplays_hub", "admin:pending_roles"):
        rc = db.get_roleplay_counts()
        text = (
            "📥 **مرکز مدیریت رول‌های دریافتی بازیکنان**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً دسته مورد نظر را جهت بررسی انتخاب فرمایید:\n\n"
            f"⭐ **رول‌های اکانت ویژه (VIP):** `{rc['vip']}` رول در نوبت فوری\n"
            f"⏳ **در انتظار تأیید (تأییدنشده):** `{rc['pending']}` رول جدید\n"
            f"✅ **تأییدشده و در نوبت اجرا:** `{rc['approved']}` رول در حال اجرا\n"
        )
        keyboard = [
            [InlineKeyboardButton(f"⭐ رول‌های اکانت ویژه (VIP) ({rc['vip']})", callback_data="admin:roles:vip:0")],
            [InlineKeyboardButton(f"⏳ رول‌های در انتظار تأیید ({rc['pending']})", callback_data="admin:roles:pending:0")],
            [InlineKeyboardButton(f"✅ رول‌های تأییدشده و در نوبت اجرا ({rc['approved']})", callback_data="admin:roles:approved:0")],
            [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("admin:roles:"):
        parts = data.split(":")
        cat = parts[2]
        page = int(parts[3]) if len(parts) > 3 else 0
        limit = 10
        offset = page * limit

        status_map = {"pending": "pending", "approved": "approved", "vip": None}
        roles, total = db.get_roleplays_by_filter(
            status=status_map.get(cat),
            is_vip_only=(cat == "vip"),
            limit=limit,
            offset=offset
        )

        titles = {
            "vip": "⭐ رول‌های بازیکنان ویژه (VIP)",
            "pending": "⏳ رول‌های در انتظار تأیید",
            "approved": "✅ رول‌های تأییدشده و در نوبت اجرا"
        }

        total_pages = max(1, math.ceil(total / limit))
        page = max(0, min(page, total_pages - 1))

        lines = [
            f"📥 **{titles.get(cat, 'رول‌های دریافتی')} (صفحه {page + 1} از {total_pages})**\n"
            "━━━━━━━━━━━━━━━━━━\n"
        ]

        keyboard = []
        if not roles:
            lines.append("✅ در حال حاضر هیچ رولی در این دسته وجود ندارد.")
        else:
            lines.append("جهت مشاهده کامل متن، بررسی یا اعمال، رول مد نظر را انتخاب کنید:\n")
            type_labels = {"attack": "⚔️ تهاجمی", "defense": "🛡️ پدافندی"}
            for r in roles:
                c_name = f"{r.get('country_flag','')} {r.get('country_name','کشور')}"
                t_lbl = type_labels.get(r["role_type"], r["role_type"])
                vip_mark = " ⭐" if r.get("is_vip") else ""
                time_str = (r.get("created_at") or "")[11:16]
                btn_text = f"{c_name} | {t_lbl} ({time_str}){vip_mark}"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"admin:show_role:{r['id']}:{cat}:{page}")])

        # دکمه‌های صفحه‌بندی
        nav_row = []
        if page > 0:
            nav_row.append(InlineKeyboardButton("◀️ قبلی", callback_data=f"admin:roles:{cat}:{page - 1}"))
        if total_pages > 1:
            nav_row.append(InlineKeyboardButton(f"صفحه {page + 1} از {total_pages}", callback_data="ignore"))
        if page < total_pages - 1:
            nav_row.append(InlineKeyboardButton("بعدی ▶️", callback_data=f"admin:roles:{cat}:{page + 1}"))
        if nav_row:
            keyboard.append(nav_row)

        keyboard.append([InlineKeyboardButton("🔙 بازگشت به دسته‌ها", callback_data="admin:roleplays_hub")])
        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("admin:show_role:"):
        parts = data.split(":")
        role_id = int(parts[2])
        cat = parts[3] if len(parts) > 3 else "pending"
        page = int(parts[4]) if len(parts) > 4 else 0

        r = db.get_roleplay_by_id(role_id)
        if not r or r["status"] == "archived":
            await query.edit_message_text("❌ این رول یافت نشد یا بایگانی گردیده است.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:roles:{cat}:{page}")]]), parse_mode="Markdown")
            return

        c = db.get_country_by_id(r["country_id"])
        c_name = f"{c['flag']} {c['name']}" if c else "نامشخص"
        type_label = "⚔️ رول تهاجمی (حمله)" if r["role_type"] == "attack" else "🛡️ رول پدافندی (دفاع)"
        status_badges = {"pending": "⏳ در انتظار بررسی", "approved": "✅ تأییدشده (در نوبت اجرا)", "rejected": "❌ ردشده"}

        text = (
            f"📝 **بررسی رول نظامی — {c_name}**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• **نوع عملیات:** {type_label}\n"
            f"• **وضعیت فعلی:** {status_badges.get(r['status'], r['status'])}\n"
            f"• **تاریخ و زمان ثبت:** `{r.get('created_at', '')[:19].replace('T', ' ')}`\n"
            f"• **شناسه عددی بازیکن:** `{r['player_id']}`\n\n"
            "📋 **متن کامل رول ارسالی:**\n"
            f'"{r["role_text"]}"'
        )

        keyboard = []
        if r["status"] == "pending":
            keyboard.append([InlineKeyboardButton("✅ تأیید رول و انتقال به نوبت اجرا", callback_data=f"admin:app_role:{role_id}:{cat}:{page}")])
            keyboard.append([InlineKeyboardButton("❌ رد رول", callback_data=f"admin:rej_role:{role_id}:{cat}:{page}")])
        elif r["status"] == "approved":
            keyboard.append([InlineKeyboardButton("💥 ثبت فاکتور تلفات (انتقال به تلفات)", callback_data="ls:fast")])
            keyboard.append([InlineKeyboardButton("🏁 پایان / بایگانی رول", callback_data=f"admin:arch_role:{role_id}:{cat}:{page}")])

        keyboard.append([InlineKeyboardButton("🔙 بازگشت به لیست رول‌ها", callback_data=f"admin:roles:{cat}:{page}")])
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("admin:app_role:"):
        parts = data.split(":")
        role_id = int(parts[2])
        cat = parts[3] if len(parts) > 3 else "pending"
        page = int(parts[4]) if len(parts) > 4 else 0

        r = db.get_roleplay_by_id(role_id)
        if not r:
            await query.edit_message_text("❌ رول یافت نشد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:roles:{cat}:{page}")]]), parse_mode="Markdown")
            return

        db.update_roleplay_status(role_id, "approved")
        c = db.get_country_by_id(r["country_id"])
        c_name = f"{c['flag']} {c['name']}" if c else "کشور"

        p_id = r["player_id"]
        type_label = "تهاجمی (حمله)" if r["role_type"] == "attack" else "پدافندی (دفاع)"
        player_msg = (
            f"✅ **رول نظامی {type_label} شما توسط مدیریت بازی تایید شد!**\n\n"
            f"👑 **کشور {c_name}:** طرح عملیاتی شما توسط ستاد مدیریت تأیید شد و در نوبت اجرای نبرد قرار گرفت."
        )
        try:
            await context.bot.send_message(chat_id=p_id, text=player_msg, parse_mode="Markdown")
        except Exception:
            pass

        keyboard = [
            [InlineKeyboardButton("💥 ثبت فاکتور تلفات همین رول", callback_data="ls:fast")],
            [InlineKeyboardButton("🔙 بازگشت به رول‌های دریافتی", callback_data="admin:roleplays_hub")]
        ]
        await query.edit_message_text(
            f"✅ **رول کشور {c_name} تأیید شد و به بخش «رول‌های در نوبت اجرا» منتقل گردید.**\n\n💡 رول در بخش تاییدشده‌ها باقی می‌ماند تا هر زمان که مایل بودید فاکتور تلفات را ثبت فرمایید.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data.startswith("admin:arch_role:"):
        parts = data.split(":")
        role_id = int(parts[2])
        cat = parts[3] if len(parts) > 3 else "approved"
        page = int(parts[4]) if len(parts) > 4 else 0

        db.update_roleplay_status(role_id, "archived")
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به رول‌های دریافتی", callback_data="admin:roleplays_hub")]]
        await query.edit_message_text("🏁 **رول با موفقیت مختومه و بایگانی گردید.**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("admin:rej_role:"):
        parts = data.split(":")
        role_id = int(parts[2])
        cat = parts[3] if len(parts) > 3 else "pending"
        page = int(parts[4]) if len(parts) > 4 else 0

        r = db.get_roleplay_by_id(role_id)
        if not r:
            await query.edit_message_text("❌ رول یافت نشد.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data=f"admin:roles:{cat}:{page}")]]), parse_mode="Markdown")
            return

        db.update_roleplay_status(role_id, "rejected")
        c = db.get_country_by_id(r["country_id"])
        c_name = f"{c['flag']} {c['name']}" if c else "کشور"

        p_id = r["player_id"]
        type_label = "تهاجمی (حمله)" if r["role_type"] == "attack" else "پدافندی (دفاع)"
        player_msg = (
            f"❌ **رول نظامی {type_label} شما توسط مدیریت بازی رد شد.**\n\n"
            f"👑 **کشور {c_name}:** می‌توانید با اصلاح جزئیات، رول جدیدی از بخش 🎯 عملیات ثبت نمایید."
        )
        try:
            await context.bot.send_message(chat_id=p_id, text=player_msg, parse_mode="Markdown")
        except Exception:
            pass

        keyboard = [[InlineKeyboardButton("🔙 بازگشت به رول‌های دریافتی", callback_data="admin:roleplays_hub")]]
        await query.edit_message_text(f"❌ **رول کشور {c_name} رد شد.**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("admin:c_tx_logs:"):
        c_id = int(data.split(":")[2])
        c = db.get_country_by_id(c_id)
        txs = db.get_country_transactions(c_id, 20)
        lines = [f"📜 *تراکنش‌ها و فعالیت‌های اخیر کشور {c['flag']} {c['name']}*\n━━━━━━━━━━━━━━━━━━\n"]
        if not txs:
            lines.append("هیچ تراکنشی برای این کشور ثبت نشده است.")
        else:
            for tx in txs:
                dt_str = tx.get("created_at", "")[:19].replace("T", " ")
                lines.append(f"• `{dt_str}` | *شرح:* {tx.get('description')} | *نوع:* `{tx.get('type')}`\n")
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به داشبورد کشور", callback_data=f"admin:c:{c['id']}")]]
        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:sync_catalog":
        db.sync_all_country_assets_to_catalog()
        text = "⚡ *همگام‌سازی کامل انجام شد!*\nتمام کشورهای دیتابیس با آمار و تجهیزات کاتالوگ جدید به‌روزرسانی شدند."
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:income_recovery_hub":
        countries = db.get_all_countries()
        player_count = len([c for c in countries if c.get("player_id") and c["player_id"] > 0])

        text = (
            "🎁 **سامانه جامع مدیریت، جبران و تعدیل درآمد بازیکنان**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 تعداد بازیکنان فعال تحت پوشش: `{player_count}` کشور\n\n"
            "از گزینه‌های زیر برای افزایش، کاهش، بازمحاسبه یا اعطا/کسر منابع همگانی استفاده فرمایید:\n\n"
            "• 🔄 **بازمحاسبه درآمدها:** محاسبه خودکار بر اساس پروژه‌ها و کارخانجات.\n"
            "• 📈/📉 **تغییر درآمد دائم:** افزایش یا کاهش دائم درآمد روزانه همه.\n"
            "• 💰/💸 **شارژ/کسر خزانه:** واریز یا کسر مستقیم پول نقد از خزانه همه.\n"
            "• 🏗️/🗑️ **بسته زیرساخت:** اعطا یا کسر کارخانجات، مزارع و نیروگاه‌ها."
        )

        keyboard = [
            [InlineKeyboardButton("🔄 بازمحاسبه درآمدها از پروژه‌ها و کارخانجات", callback_data="admin:do_recalc_all_incomes")],
            [
                InlineKeyboardButton("➕ ۱ میلیون درآمد", callback_data="admin:boost_all_incomes:1000000"),
                InlineKeyboardButton("➖ ۱ میلیون درآمد", callback_data="admin:boost_all_incomes:-1000000"),
            ],
            [
                InlineKeyboardButton("➕ ۲ میلیون درآمد", callback_data="admin:boost_all_incomes:2000000"),
                InlineKeyboardButton("➖ ۲ میلیون درآمد", callback_data="admin:boost_all_incomes:-2000000"),
            ],
            [
                InlineKeyboardButton("➕ ۳ میلیون درآمد", callback_data="admin:boost_all_incomes:3000000"),
                InlineKeyboardButton("➖ ۳ میلیون درآمد", callback_data="admin:boost_all_incomes:-3000000"),
            ],
            [
                InlineKeyboardButton("➕ ۵ میلیون درآمد", callback_data="admin:boost_all_incomes:5000000"),
                InlineKeyboardButton("➖ ۵ میلیون درآمد", callback_data="admin:boost_all_incomes:-5000000"),
            ],
            [
                InlineKeyboardButton("💰 ➕ ۲۰M به خزانه همه", callback_data="admin:grant_cash_all:20000000"),
                InlineKeyboardButton("💸 ➖ ۲۰M از خزانه همه", callback_data="admin:grant_cash_all:-20000000"),
            ],
            [
                InlineKeyboardButton("💰 ➕ ۵۰M به خزانه همه", callback_data="admin:grant_cash_all:50000000"),
                InlineKeyboardButton("💸 ➖ ۵۰M از خزانه همه", callback_data="admin:grant_cash_all:-50000000"),
            ],
            [
                InlineKeyboardButton("🏗️ ➕ اعطای بسته کارخانجات به همه", callback_data="admin:grant_civ_package_all:add"),
                InlineKeyboardButton("🗑️ ➖ کسر بسته کارخانجات از همه", callback_data="admin:grant_civ_package_all:sub"),
            ],
            [InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data="admin:menu")]
        ]
        await safe_edit_or_reply(query, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:do_recalc_all_incomes":
        count = db.recalculate_all_countries_income_from_equipment()
        await query.answer(f"درآمد {count} کشور بر اساس ساخت‌وسازها با موفقیت به‌روزرسانی شد!", show_alert=True)
        # بازگشت به هاب
        countries = db.get_all_countries()
        player_count = len([c for c in countries if c.get("player_id") and c["player_id"] > 0])
        text = f"✅ **درآمد تمام کشورها با موفقیت بر اساس پروژه‌های احداث‌شده بازسازی شد!**\n\nتعداد کشورها: `{count}`"
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به سامانه جبران", callback_data="admin:income_recovery_hub")]]
        await safe_edit_or_reply(query, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("admin:boost_all_incomes:"):
        delta = int(data.split(":")[2])
        count = db.boost_all_player_countries_income(delta)
        action_word = "افزایش" if delta >= 0 else "کاهش"
        sign_str = "+" if delta >= 0 else "-"
        await query.answer(f"درآمد روزانه {count} بازیکن به میزان {sign_str}{format_money(abs(delta))} {action_word} یافت!", show_alert=True)
        text = (
            f"✅ **عملیات {action_word} درآمد همگانی با موفقیت انجام شد!**\n\n"
            f"• 📈 میزان تغییر هر بازیکن: **{sign_str}{format_money(abs(delta))}/روز**\n"
            f"• 👥 تعداد بازیکنان: `{count} کشور`"
        )
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به سامانه جبران", callback_data="admin:income_recovery_hub")]]
        await safe_edit_or_reply(query, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("admin:grant_cash_all:"):
        amount = int(data.split(":")[2])
        action_word = "واریز هدیه به" if amount >= 0 else "کسر از"
        desc = f"بسته حمایتی مدیریت ستاد ({format_money(amount)})" if amount >= 0 else f"تعدیل سراسری خزانه ({format_money(amount)})"
        count = db.grant_cash_to_all_player_countries(amount, desc)
        await query.answer(f"مبلغ {format_money(abs(amount))} با موفقیت اعمال شد!", show_alert=True)
        text = (
            f"✅ **عملیات {action_word} خزانه تمام بازیکنان انجام شد!**\n\n"
            f"• 💰 مبلغ تراکنش هر بازیکن: **{format_money(amount)}**\n"
            f"• 👥 تعداد بازیکنان: `{count} کشور`\n"
            f"• 📝 رسید تراکنش در گردش مالی بازیکنان ثبت گردید."
        )
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به سامانه جبران", callback_data="admin:income_recovery_hub")]]
        await safe_edit_or_reply(query, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("admin:grant_civ_package_all"):
        mode = data.split(":")[2] if len(data.split(":")) > 2 else "add"
        is_add = (mode != "sub")
        count = db.grant_infrastructure_package_to_all(is_add=is_add)
        act_text = "اعطا" if is_add else "کسر"
        sign_char = "+" if is_add else "-"
        await query.answer(f"بسته زیرساخت برای {count} بازیکن فعال با موفقیت {act_text} شد!", show_alert=True)
        text = (
            f"✅ **بسته زیرساخت و کارخانجات برای تمام بازیکنان فعال {act_text} گردید!**\n\n"
            f"• 🏭 کارخانجات متوسط: {sign_char}۲ واحد ({sign_char}۸۰۰,۰۰۰ دلار/روز)\n"
            f"• 🌾 مزارع مکانیزه گندم: {sign_char}۲ واحد ({sign_char}۳۵۰,۰۰۰ دلار و {sign_char}۴,۰۰۰ تن غلات/روز)\n"
            f"• ⚡ نیروگاه برق: {sign_char}۱ واحد ({sign_char}۵۰ MW برق)\n"
            f"• 👥 تعداد کشورهای تحت تأثیر: `{count} کشور`"
        )
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به سامانه جبران", callback_data="admin:income_recovery_hub")]]
        await safe_edit_or_reply(query, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:sync_all_keyboards":
        countries = db.get_all_countries()
        count = 0
        for c in countries:
            p_id = c.get("player_id")
            if p_id and p_id > 0:
                try:
                    await context.bot.send_message(
                        chat_id=p_id,
                        text="🔄 **دکمه‌ها و منوی اصلی بازی شما با آخرین امکانات سرور به‌روزرسانی شد.**",
                        reply_markup=get_main_keyboard(p_id),
                        parse_mode="Markdown"
                    )
                    count += 1
                except Exception:
                    pass
        await query.answer(f"کیبورد {count} کشور/بازیکن با موفقیت همگام‌سازی شد!", show_alert=True)

    elif data == "admin:season_reset_prompt":
        countries = db.get_all_countries()
        player_count = len([c for c in countries if c.get("player_id") and c["player_id"] > 0 and c.get("country_key") != "un"])
        text = (
            "🧹 **سلب مالکیت همگانی و شروع رسمی فصل جدید (Season Reset)**\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"• تعداد کشورهای دارای بازیکن: `{player_count} کشور`\n\n"
            "با تأیید این عملیات:\n"
            "۱. مالکیت تمامی کشورها سلب شده و برای ثبت‌نام و انتخاب مجدد در `/start` آزاد می‌شوند.\n"
            "۲. پایگاه‌ها، بازار بورس، قراردادهای تجاری، رول‌ها و بیانیه‌ها برای شروعی پاک ریست می‌شوند.\n"
            "۳. تمام کشورها با بالانس دقیق، بدون باگ و با مقادیر استاندارد از نو بارگذاری می‌شوند.\n\n"
            "⚠️ **این عملیات غیرقابل بازگشت است.** آیا از ریست کامل و استارت فصل جدید اطمینان دارید؟"
        )
        keyboard = [
            [InlineKeyboardButton("🔥 بله، تمام کشورها را آزاد و بازی را ریست کن", callback_data="admin:season_reset_confirm")],
            [InlineKeyboardButton("❌ انصراف", callback_data="admin:menu")],
        ]
        await safe_edit_or_reply(query, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:season_reset_confirm":
        ok, count, msg = db.reset_all_countries_for_new_season()
        if ok:
            text = (
                "🎉 **سلب مالکیت همگانی و ریست فصل جدید با موفقیت انجام شد!**\n\n"
                f"• تعداد `{count}` کشور آزاد شدند.\n"
                "• تمامی بازیکنان اکنون می‌توانند با ارسال دستور /start کشور جدید خود را انتخاب فرمایند.\n\n"
                "🚀 فصل رسمی بازی «سیاست مدرن» با بالاترین سطح ثبات و بالانس آغاز گردید."
            )
        else:
            text = f"❌ خطا در ریست: {msg}"
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]]
        await safe_edit_or_reply(query, text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:market_reset_prompt":
        orders = db.get_market_orders()
        count = len(orders)
        text = (
            "📦 *ریست کامل بازار بورس بین‌المللی کالاها*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• *تعداد سفارشات فعال در بورس:* `{count} سفارش`\n\n"
            "⚠️ **هشدار عملیاتی:** با تأیید این عملیات:\n"
            "۱. تمام سفارش‌های فعال فروش در بورس کالا لغو می‌شوند.\n"
            "۲. **تمام نفت، طلا و غلات عرضه‌شده ۱۰۰٪ به موجودی انبار کشورهای فروشنده عودت داده می‌شود.**\n"
            "۳. بازار بورس کاملاً پاکسازی و ریست می‌شود.\n\n"
            "آیا از ریست کامل بورس و عودت کالاها مطمئن هستید؟"
        )
        keyboard = [
            [InlineKeyboardButton("🔥 بله، ریست کن و کالاها را بازگردان", callback_data="admin:market_reset_confirm")],
            [InlineKeyboardButton("❌ انصراف", callback_data="admin:menu")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:market_reset_confirm":
        ok, total_canceled, summary = db.reset_all_market_orders()
        if not ok:
            await query.edit_message_text(
                f"❌ **خطا در ریست بازار بورس:**\n\n{summary.get('error', 'خطای ناشناخته')}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]]),
                parse_mode="Markdown"
            )
            return

        text = (
            "✅ *بازار بورس کالا با موفقیت کامل ریست شد!*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"📋 **گزارش عودت کالاها به انبار کشورها:**\n"
            f"• 📦 *تعداد کل سفارشات لغو‌شده:* `{total_canceled} سفارش`\n"
            f"• 🌐 *کشورهای دریافت‌کننده کالا:* `{summary.get('countries_affected', 0)} کشور`\n\n"
            f"📊 **حجم اقلام عودت‌داده‌شده به حساب کشورها:**\n"
            f"• 🛢️ *نفت بازگردانده‌شده:* {format_oil(summary.get('oil', 0))}\n"
            f"• 🌾 *غلات بازگردانده‌شده:* {format_number(summary.get('grain', 0))} تن\n"
            f"• 🪙 *طلا بازگردانده‌شده:* {summary.get('gold', 0)} شمش طلا\n\n"
            "📢 تمام کالاهای عرضه‌شده به موجودی خزانه و انبار بازیکنان برگشت."
        )

        # ارسال پیام اطلاع‌رسانی به بازیکنان متأثر
        for p_id in summary.get("player_ids", []):
            try:
                await context.bot.send_message(
                    chat_id=p_id,
                    text=(
                        "📦 **اطلاعیه مدیریت بازی — ریست بازار بورس کالا:**\n\n"
                        "با تصمیم ستاد مدیریت، سفارشات فعال شما در بورس کالا لغو گردید و "
                        "**تمام نفت، طلا و غلات عرضه‌شده شما به موجودی انبار کشورتان بازگردانده شد.**"
                    ),
                    parse_mode="Markdown"
                )
            except Exception:
                pass

        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:energy_aid_prompt":
        countries = db.get_all_countries()
        importers = []
        for c in countries:
            reqs = approval_system.calculate_country_requirements(c)
            if (c.get('oil_production', 0) or 0) < reqs['oil_need_daily']:
                importers.append(c)

        text = (
            "💰 *واریز بسته حمایتی ویژه انرژی به کشورهای واردکننده*\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• *تعداد کشورهای مشمول بسته حمایتی:* `{len(importers)} کشور`\n"
            "• *مبلغ واریزی:* **۱۵ تا ۲۵ میلیون دلار** کمک مالی بلاعوض به خزانه واردکنندگان نفت\n\n"
            "با تأیید این دستور، مبلغ مستقیماً به خزانه کشورها واریز شده و پیام رسمی واریز برای بازیکنان فرستاده می‌شود.\n\n"
            "آیا مایل به واریز فوری بسته حمایتی هستید؟"
        )
        keyboard = [
            [InlineKeyboardButton("✅ بله، واریز بسته حمایتی به واردکنندگان", callback_data="admin:energy_aid_confirm")],
            [InlineKeyboardButton("❌ انصراف", callback_data="admin:menu")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:energy_aid_confirm":
        countries = db.get_all_countries()
        count = 0
        total_aid = 0

        for c in countries:
            reqs = approval_system.calculate_country_requirements(c)
            net_oil = (c.get('oil_production', 0) or 0) - reqs['oil_need_daily']
            if net_oil < 0:
                deficit = abs(net_oil)
                grant = 25_000_000 if deficit >= 200_000 else 15_000_000
                
                db.adjust_treasury(c["id"], grant)
                db.add_transaction(c["id"], "aid", "بسته حمایتی ویژه صندوق بین‌المللی انرژی جهت خرید سوخت", grant)
                count += 1
                total_aid += grant

                p_id = c.get("player_id")
                if p_id:
                    try:
                        aid_msg = (
                            f"🏦 **اطلاعیه صندوق بین‌المللی انرژی و توسعه — {c.get('flag','')} {c.get('name','')}**\n\n"
                            f"جهت پایداری زنجیره انرژی و واردات سوخت، مبلغ **{format_money(grant)}** کمک مالی بلاعوض به خزانه کشور شما واریز گردید.\n\n"
                            "💡 لطفاً جهت جلوگیری از بحران سوخت در روزهای آینده، از بخش **بورس کالا (/market)** نفت خریداری فرمایید یا اقدام به **احداث پالایشگاه در فروشگاه (/shop)** نمایید."
                        )
                        await context.bot.send_message(chat_id=p_id, text=aid_msg, parse_mode="Markdown")
                    except Exception:
                        pass

        text = (
            f"✅ *بسته حمایتی انرژی با موفقیت برای {count} کشور واردکننده واریز شد!*\n\n"
            f"• 💰 *مجموع کمک مالی توزیع‌شده:* {format_money(total_aid)}\n"
            "• 📩 پیام اطلاع‌رسانی رسمی برای تمام رهبران این کشورها ارسال گردید."
        )
        keyboard = [[InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "admin:daily_income":
        from main import daily_income_job
        count = await daily_income_job(context, force=True)
        await query.edit_message_text(
            f"⚡ *درآمد روزانه و گزارش کشورها با موفقیت برای {count} کشور واریز و ارسال شد!*",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت", callback_data="admin:menu")]]),
            parse_mode="Markdown"
        )

    elif data.startswith("admin:approve_country:"):
        req_id = int(data.split(":")[2])
        req = db.get_pending_country_request(req_id)
        if not req:
            await query.edit_message_text("❌ این درخواست قبلاً تعیین تکلیف یا لغو شده است.", parse_mode="HTML")
            return

        c_key = req["country_key"]
        c_info = config.COUNTRIES.get(c_key, {})

        if db.get_country_by_key(c_key):
            db.delete_pending_country_request(req_id)
            await query.edit_message_text(f"❌ کشور {c_info.get('name', c_key)} قبلاً به کاربر دیگری واگذار شده است.", parse_mode="HTML")
            return

        c_id = db.create_country(
            player_id=req["player_id"],
            name=c_info["name"],
            flag=c_info["flag"],
            country_key=c_key,
            username=req["username"]
        )
        db.delete_pending_country_request(req_id)
        db.add_log(actor=str(user_id), action="approve_country", details=f"{c_key} to {req['player_id']}")

        u_display = f"@{req['username']}" if req.get('username') else f"ID: {req['player_id']}"
        try:
            await query.edit_message_text(
                f"✅ <b>کشور {c_info['flag']} {c_info['name']} با موفقیت به کاربر {u_display} (ID: <code>{req['player_id']}</code>) واگذار گردید.</b>",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 لیست درخواست‌های معلق", callback_data="admin:pending_countries")],
                    [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]
                ]),
                parse_mode="HTML"
            )
        except Exception:
            await query.edit_message_text(
                f"✅ کشور {c_info['flag']} {c_info['name']} با موفقیت به کاربر @{req.get('username', req['player_id'])} واگذار گردید.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 لیست درخواست‌های معلق", callback_data="admin:pending_countries")],
                    [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]
                ])
            )

        p_id = req["player_id"]
        congratulations_msg = (
            f"🎉 <b>تبریک! درخواست انتخاب کشور شما توسط مدیریت عالی بازی تایید گردید.</b>\n\n"
            f"👑 <b>رهبر گرامی، کشور {c_info['flag']} {c_info['name']} با موفقیت به شما واگذار شد.</b>\n\n"
            "آرزوی موفقیت، اقتدار و سربلندی برای دولت و ملت شما در عرصه بین‌المللی داریم.\n"
            "هم‌اکنون کیبورد مدیریت کشور در پایین صفحه برای شما فعال گردید 👇\n\n"
            "━━━━━━━━━━━━━━━━━━\n"
            "📢 <b>اطلاعیه بازی سیاست مدرن</b>\n\n"
            "🤖 <b>بات بازی:</b>\n"
            "@SiasatModernBot\n\n"
            "📰 <b>اخبار و بیانیه:</b>\n"
            "https://t.me/+APOcv0A5RnwxZWU0\n\n"
            "🌍 <b>گپ کشورها:</b>\n"
            "https://t.me/siasatmodernGp\n\n"
            "📌 <b>چنل اصلی:</b>\n"
            "https://t.me/SiasatModern\n\n"
            "✅ <b>لطفاً در همه بخش‌ها عضو باشید تا از اخبار، قوانین و اتفاقات بازی باخبر شوید.</b>"
        )
        try:
            await context.bot.send_message(
                chat_id=p_id,
                text=congratulations_msg,
                reply_markup=get_main_keyboard(p_id),
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Error sending approval message to player {p_id}: {e}")

    # منوهای ویرایش
    elif data.startswith("admin:menu_treasury:"):
        c_id = int(data.split(":")[2])
        await menu_treasury(query, c_id)

    elif data.startswith("admin:menu_gold:"):
        c_id = int(data.split(":")[2])
        await menu_gold(query, c_id)

    elif data.startswith("admin:menu_oil:"):
        c_id = int(data.split(":")[2])
        await menu_oil(query, c_id)

    elif data.startswith("admin:cstatadj:"):
        parts = data.split(":")
        if len(parts) == 5:
            cid_, field_, mult_ = int(parts[2]), parts[3], int(parts[4])
            new_val, err = apply_cstat_delta(cid_, field_, mult_)
            if err:
                await query.answer(f"❌ {err}", show_alert=True)
                return
            info = COUNTRY_STAT_FIELDS.get(field_)
            await query.answer(f"✅ {info[0]} → {_fmt_stat(new_val, info[3])}", show_alert=True)
            await menu_cstat_adjust(query, cid_, field_)
        return

    elif data.startswith("admin:cstatset:"):
        parts = data.split(":")
        if len(parts) == 4:
            context.user_data["admin_awaiting_input"] = {"type": "cstat_set", "country_id": int(parts[2]), "field": parts[3]}
            c = db.get_country_by_id(int(parts[2]))
            info = COUNTRY_STAT_FIELDS.get(parts[3])
            await query.edit_message_text(
                f"✏️ *مقدار جدید برای {info[0]}* — {c['flag']} {c['name']}\n\nمقدار فعلی: {_fmt_stat(c.get(parts[3], 0) or 0, info[3])}\n\nلطفاً عدد را ارسال کنید (اعداد فارسی هم قابل قبول است):",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data=f"admin:cstatmenu:{parts[2]}")]]),
                parse_mode="Markdown",
            )
        return

    elif data.startswith("admin:cstatmenu:"):
        await menu_country_stats(query, int(data.split(":")[2]))
        return

    elif data.startswith("admin:cstat:"):
        parts = data.split(":")
        if len(parts) == 4:
            await menu_cstat_adjust(query, int(parts[2]), parts[3])
        return

    elif data.startswith("admin:asset_cat:"):
        parts = data.split(":")
        if len(parts) >= 4:
            await menu_assets_category(query, int(parts[2]), ":".join(parts[3:]))
        return

    elif data.startswith("admin:menu_assets:"):
        c_id = int(data.split(":")[2])
        await menu_assets(query, c_id)

    elif data.startswith("admin:asset_item:"):
        _, _, c_id, equipment_key = data.split(":", 3)
        await menu_single_asset_item(query, int(c_id), equipment_key)

    # تغییر نسبی فیلدها
    elif data.startswith("admin:adj:"):
        _, _, c_id_str, field, delta_str = data.split(":")
        c_id, delta = int(c_id_str), int(delta_str)

        if field == "treasury":
            db.adjust_treasury(c_id, delta)
        elif field == "gold":
            db.adjust_gold(c_id, delta)
        elif field == "oil_reserves":
            db.adjust_oil(c_id, delta)

        c = db.get_country_by_id(c_id)
        field_names = {"treasury": "خزانه", "gold": "طلا", "oil_reserves": "ذخیره نفت"}
        # در همان منو بمان تا بتوان چند بار پشت‌سرهم دکمه زد
        # (قبلاً به داشبورد کلی برمی‌گشت و کاربر هر بار «می‌رفت بالاتر»)
        sign = "➕" if delta > 0 else "➖"
        await query.answer(
            f"{sign} {field_names.get(field, field)} {c['name']}: {format_number(c.get(field, 0) or 0)}",
            show_alert=False,
        )
        if field == "treasury":
            await menu_treasury(query, c_id)
        elif field == "gold":
            await menu_gold(query, c_id)
        elif field == "oil_reserves":
            await menu_oil(query, c_id)

    elif data.startswith("admin:adj_asset:"):
        _, _, c_id_str, equipment_key, delta_str = data.split(":")
        c_id, delta = int(c_id_str), int(delta_str)
        asset = db.get_asset_by_key(c_id, equipment_key)
        if asset:
            # تعداد دارایی هرگز منفی نشود
            db.set_asset_amount(c_id, equipment_key, max(0, asset["amount"] + delta))
        await menu_single_asset_item(query, c_id, equipment_key)

    elif data.startswith("admin:set_asset:"):
        _, _, c_id_str, equipment_key, qty_str = data.split(":")
        c_id, qty = int(c_id_str), int(qty_str)
        db.set_asset_amount(c_id, equipment_key, qty)
        await menu_single_asset_item(query, c_id, equipment_key)

    # درخواست ورودی متنی
    elif data.startswith("admin:prompt:"):
        _, _, c_id_str, field = data.split(":")
        c_id = int(c_id_str)
        c = db.get_country_by_id(c_id)
        context.user_data["admin_awaiting_input"] = {"type": "field", "country_id": c_id, "field": field}

        field_names = {
            "treasury": "خزانه (دلار)",
            "gold": "طلا",
            "oil_reserves": "ذخایر نفت (بشکه)",
            "oil_production": "نرخ تولید روزانه نفت (بشکه)"
        }

        await query.edit_message_text(
            f"✏️ *تنظیم سفارشی {field_names.get(field, field)} برای کشور {c['name']}*\n\n"
            f"لطفاً عدد جدید مورد نظر را در یک پیام بفرستید (مثلاً `250000000`):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data=f"admin:c:{c_id}")]])
        )

    elif data.startswith("admin:prompt_asset:"):
        _, _, c_id_str, equipment_key = data.split(":")
        c_id = int(c_id_str)
        c = db.get_country_by_id(c_id)
        asset = db.get_asset_by_key(c_id, equipment_key)
        context.user_data["admin_awaiting_input"] = {"type": "asset_amount", "country_id": c_id, "equipment_key": equipment_key}

        await query.edit_message_text(
            f"✏️ *تنظیم تعداد {asset['equipment_name']} برای کشور {c['name']}*\n\n"
            f"لطفاً تعداد جدید مورد نظر را ارسال کنید:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data=f"admin:asset_item:{c_id}:{equipment_key}")]])
        )

    elif data.startswith("admin:msg_prompt:"):
        c_id = int(data.split(":")[2])
        c = db.get_country_by_id(c_id)
        context.user_data["admin_awaiting_input"] = {"type": "direct_msg", "country_id": c_id, "player_id": c["player_id"]}

        await query.edit_message_text(
            f"✉️ *ارسال پیام مستقیم به رهبر {c['flag']} {c['name']}*\n\n"
            f"متن پیام خود را بنویسید تا مستقیماً برای بازیکن ارسال شود:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data=f"admin:c:{c_id}")]])
        )

    elif data == "admin:broadcast_prompt":
        context.user_data["admin_awaiting_input"] = {"type": "broadcast"}
        await query.edit_message_text(
            "📢 *ارسال پیام همگانی به تمام بازیکنان*\n\n"
            "متن پیام اعلان بازی را ارسال کنید تا برای تمام رهبران کشورها فرستاده شود:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="admin:menu")]])
        )

    elif data == "admin:set_channel_prompt":
        context.user_data["admin_awaiting_input"] = {"type": "set_channel"}
        curr_ch = config.get_channel_id()
        await query.edit_message_text(
            f"📢 *تنظیم آیدی کانال تلگرام جهت انتشار بیانیه‌ها و توییت‌ها*\n━━━━━━━━━━━━━━━━━━\n\n"
            f"• *آیدی کانال فعلی:* `{curr_ch}`\n\n"
            "لطفاً *آیدی یا شناسه عددی کانال تلگرام* خود را ارسال فرمایید (مثلاً: `@ModernWarFarChannel` یا `-1001234567890`):",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="admin:menu")]]),
            parse_mode="Markdown"
        )

    # تأیید و اجرای حذف کشور
    elif data.startswith("admin:delconfirm:"):
        c_id = int(data.split(":")[2])
        c = db.get_country_by_id(c_id)
        text = (
            f"⚠️ *آیا از حذف کامل کشور {c['flag']} {c['name']} مطمئن هستید؟*\n\n"
            f"• شناسه بازیکن: `{c['player_id']}`\n"
            f"• تمام ثروت، طلا، نفت و تجهیزات این کشور حذف خواهد شد و بازیکن می‌تواند دوباره /start بزند.\n"
            f"این عمل غیرقابل بازگشت است!"
        )
        keyboard = [
            [InlineKeyboardButton("🔥 بله، حذف کن!", callback_data=f"admin:delfinal:{c_id}")],
            [InlineKeyboardButton("❌ انصراف", callback_data=f"admin:c:{c_id}")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("admin:delfinal:"):
        c_id = int(data.split(":")[2])
        c = db.get_country_by_id(c_id)
        if c:
            name = c["name"]
            db.delete_country_by_id(c_id)
            await query.edit_message_text(
                f"✅ کشور *{name}* با موفقیت و به‌طور کامل حذف شد.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("📋 بازگشت به لیست کشورها", callback_data="admin:list:0")]])
            )


# ==================== دریافت ورودی‌های تایپی ادمین ====================

async def admin_input_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return

    input_state = context.user_data.get("admin_awaiting_input")
    if not input_state:
        return

    text = update.message.text.strip()
    input_type = input_state.get("type")

    if await handle_dossier_inputs(update, context, input_type, text, input_state):
        context.user_data["admin_awaiting_input"] = None
        return

    if await handle_tournament_admin_input(update, context, input_type, text, input_state):
        return

    if await handle_internal_admin_input(update, context, input_type, text, input_state):
        return

    if input_type == "cstat_set":
        raw = re.sub(r"[^0-9]", "", str(text).translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")))
        if not raw:
            await update.message.reply_text("❌ لطفاً فقط یک عدد صحیح بفرست.", parse_mode="Markdown")
            return
        cid_ = input_state["country_id"]; field_ = input_state["field"]
        try:
            new_val, err = apply_cstat_value(cid_, field_, int(raw))
        except Exception as exc:
            err = f"خطای داخلی در ذخیره فیلد `{field_}`: {exc}"
            new_val = None
        c = db.get_country_by_id(cid_)
        info = COUNTRY_STAT_FIELDS.get(field_)
        context.user_data["admin_awaiting_input"] = None
        if err:
            await update.message.reply_text(f"❌ {err}", parse_mode="Markdown")
            return
        await update.message.reply_text(
            f"✅ *{info[0]}* کشور {c['flag']} {c['name']} به *{_fmt_stat(new_val, info[3])}* تغییر یافت.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚙️ بازگشت به وضعیت داخلی", callback_data=f"admin:cstatmenu:{cid_}")],
                [InlineKeyboardButton("🔙 داشبورد کشور", callback_data=f"admin:c:{cid_}")],
            ]),
            parse_mode="Markdown",
        )
        return

    if input_type and str(input_type).startswith("ls_"):
        await handle_losses_input(update, context, user_id, input_state)
        return

    if input_type == "admin_search_country":
        context.user_data["admin_awaiting_input"] = None
        user_query = text.strip()
        clean_q = _clean_persian_str(user_query)

        all_countries = db.get_all_countries()
        matches = [c for c in all_countries if clean_q in _clean_persian_str(c.get("name", "")) or clean_q in _clean_persian_str(c.get("country_key", "")) or str(c.get("player_id", "")) == user_query]

        if not matches:
            await update.message.reply_text(
                f"❌ کشوری با مشخصات «{user_query}» در پایگاه داده یافت نشد.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("🔁 جستجوی دوباره", callback_data="admin:search_country_prompt")],
                    [InlineKeyboardButton("🔙 لیست کشورها", callback_data="admin:list:0")]
                ]),
                parse_mode="Markdown"
            )
            return

        rows = []
        for c in matches:
            tr = format_money(c.get("treasury") or 0)
            pid = c.get("player_id") or "—"
            btn_text = f"{c.get('flag', '🏳️')} {c.get('name', '')} | 🏦 {tr} (ID: {pid})"
            rows.append([InlineKeyboardButton(btn_text, callback_data=f"admin:c:{c['id']}")])
        rows.append([InlineKeyboardButton("🔙 بازگشت به لیست کشورها", callback_data="admin:list:0")])

        await update.message.reply_text(
            f"🔎 **نتایج جستجو برای «{user_query}» ({len(matches)} کشور):**\n━━━━━━━━━━━━━━━━━━\nروی کشور مورد نظر کلیک کنید:",
            reply_markup=InlineKeyboardMarkup(rows),
            parse_mode="Markdown"
        )
        return

    if input_type == "rename_militia_and_approve":
        context.user_data["admin_awaiting_input"] = None
        req_id = input_state["req_id"]
        new_name = text.strip()

        ok, msg, p = db.approve_payment_request(req_id, user_id, override_name=new_name)
        if not ok:
            await update.message.reply_text(f"❌ خطا در تایید: {msg}")
            return

        player_id = p["player_id"]
        created_c = db.get_country_by_player(player_id)
        c_flag = created_c["flag"] if created_c else "🏴‍☠️"

        success_msg = (
            f"🎉 **تاسیس گروه غیردولتی {c_flag} {new_name} با موفقیت تایید و ایجاد شد!**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• 🏷️ **نام مصوب سازمان:** {new_name}\n"
            "• 💰 **خزانه اولیه:** ۲۵ میلیون دلار\n"
            "• 🪖 **رزمندگان آماده‌باش:** ۶۰,۰۰۰ نفر\n"
            "• 🎖️ **تسلیحات نامتقارن:** تسلیحات و ادوات جنگ نامتقارن در انبار مستقر شد\n"
            "• ⭐ **اشتراک طلایی VIP:** برای رهبر گروه فعال گردید\n\n"
            "👇 از دکمه‌های پایین صفحه برای هدایت و فرماندهی نیروهای خود استفاده فرمایید!"
        )
        try:
            await context.bot.send_message(chat_id=player_id, text=success_msg, reply_markup=get_main_keyboard(player_id), parse_mode="Markdown")
        except Exception as e:
            print(f"Failed to notify player of renamed militia: {e}")

        await update.message.reply_text(
            f"✅ **فیش #{req_id} تایید شد و گروه با نام مصوب «{new_name}» ایجاد گردید.**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 لیست فیش‌های باقیمانده", callback_data="admin:toman_requests")],
                [InlineKeyboardButton("🔙 پنل ادمین", callback_data="admin:menu")]
            ]),
            parse_mode="Markdown"
        )
        return

    if input_type == "reject_country_reason":
        context.user_data["admin_awaiting_input"] = None
        req_id = input_state["req_id"]
        c_key = input_state["country_key"]
        p_id = input_state["player_id"]
        u_name = input_state.get("username", "")
        c_info = config.COUNTRIES.get(c_key, {})

        reason_text = text.strip()

        db.delete_pending_country_request(req_id)
        db.add_log(actor=str(user_id), action="reject_country", details=f"{c_key} for {p_id} (Custom Reason: {reason_text})")

        player_msg = (
            f"❌ <b>درخواست شما برای انتخاب کشور {c_info.get('flag', '')} {c_info.get('name', c_key)} توسط مدیریت بازی رد شد.</b>\n\n"
            f"📝 <b>علت رد درخواست:</b>\n"
            f"«{reason_text}»\n\n"
            "💡 می‌توانید با ارسال مجدد دستور /start کشور دیگری را انتخاب فرمایید."
        )
        try:
            await context.bot.send_message(chat_id=p_id, text=player_msg, parse_mode="HTML")
        except Exception as e:
            print(f"Error sending custom reject message to player {p_id}: {e}")

        u_display = f"@{u_name}" if u_name else f"ID: {p_id}"
        await update.message.reply_text(
            f"✅ <b>درخواست کشور {c_info.get('flag', '')} {c_info.get('name', c_key)} برای کاربر {u_display} با موفقیت رد شد.</b>\n\n"
            f"📝 <b>دلیل ارسال‌شده برای بازیکن:</b>\n«{reason_text}»",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📋 لیست درخواست‌های معلق", callback_data="admin:pending_countries")],
                [InlineKeyboardButton("🔙 بازگشت به پنل ادمین", callback_data="admin:menu")]
            ]),
            parse_mode="HTML"
        )
        return

    del context.user_data["admin_awaiting_input"]

    clean_text = text.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١۲٣٤٥٦٧٨٩", "01234567890123456789")).replace(",", "").replace("_", "")

    if input_type == "field":
        c_id = input_state["country_id"]
        field = input_state["field"]
        try:
            val = int(clean_text)
            db.update_country_field(c_id, field, val)
            c = db.get_country_by_id(c_id)
            await update.message.reply_text(f"✅ مقدار {field} برای کشور {c['name']} با موفقیت به {format_number(val)} تغییر یافت.\nبرای ادامه /admin را بزنید.", parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("❌ عدد وارد شده نامعتبر بود. عملیات لغو شد. برای مدیریت /admin را بزنید.", parse_mode="Markdown")

    elif input_type == "asset_amount":
        c_id = input_state["country_id"]
        eq_key = input_state["equipment_key"]
        try:
            val = int(clean_text)
            db.set_asset_amount(c_id, eq_key, val)
            c = db.get_country_by_id(c_id)
            asset = db.get_asset_by_key(c_id, eq_key)
            await update.message.reply_text(f"✅ تعداد {asset['equipment_name']} برای کشور {c['name']} به {format_number(val)} تغییر یافت.\nبرای ادامه /admin را بزنید.", parse_mode="Markdown")
        except ValueError:
            await update.message.reply_text("❌ عدد وارد شده نامعتبر بود. عملیات لغو شد. برای مدیریت /admin را بزنید.", parse_mode="Markdown")

    elif input_type == "direct_msg":
        player_id = input_state["player_id"]
        c_id = input_state["country_id"]
        c = db.get_country_by_id(c_id)
        try:
            await context.bot.send_message(
                chat_id=player_id,
                text=f"📩 *پیام مستقیم از طرف ادمین بازی:*\n\n{text}",
                parse_mode="Markdown"
            )
            await update.message.reply_text(f"✅ پیام شما با موفقیت برای رهبر کشور {c['name']} ارسال شد.", parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"❌ ارسال پیام به بازیکن ناموفق بود:\n{e}", parse_mode="Markdown")

    elif input_type == "set_channel":
        db.set_setting("channel_id", text)
        await update.message.reply_text(
            f"✅ *آیدی کانال تلگرام با موفقیت بروزرسانی شد!*\n\n"
            f"• *کانال جدید:* `{text}`\n\n"
            "کافیست ربات را در این کانال به‌عنوان ادمین با دسترسی ارسال پیام اضافه فرمایید تا بیانیه‌ها و توییت‌ها مستقیماً در آن منتشر شوند.",
            parse_mode="Markdown"
        )

    elif input_type == "broadcast":
        countries = db.get_all_countries()
        success_count = 0
        fail_count = 0
        msg_text = f"📢 *اطلاعیه همگانی ادمین بازی:*\n\n{text}"

        for c in countries:
            try:
                await context.bot.send_message(chat_id=c["player_id"], text=msg_text, parse_mode="Markdown")
                success_count += 1
            except Exception:
                fail_count += 1

        await update.message.reply_text(
            f"📢 *نتیجه ارسال پیام همگانی:*\n\n"
            f"✅ ارسال موفق به: {success_count} کشور\n"
            f"❌ ناموفق: {fail_count} کشور"
        )


# ==================== دستورات متنی قدیمی ادمین جهت سازگاری ====================

async def addmoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ این دستور فقط برای ادمین‌هاست.", parse_mode="Markdown")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text("کاربرد: /addmoney <player_id> <amount>", parse_mode="Markdown")
        return

    try:
        player_id, amount = int(args[0]), int(args[1])
    except ValueError:
        await update.message.reply_text("مقادیر باید عدد باشند.", parse_mode="Markdown")
        return

    country = db.get_country_by_player(player_id)
    if not country:
        await update.message.reply_text("کشوری پیدا نشد.", parse_mode="Markdown")
        return

    db.adjust_treasury(country["id"], amount)
    await update.message.reply_text(f"✅ مبلغ {format_money(amount)} به خزانه {country['name']} اضافه شد.", parse_mode="Markdown")


async def removemoney(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ این دستور فقط برای ادمین‌هاست.", parse_mode="Markdown")
        return

    args = context.args
    if len(args) != 2:
        await update.message.reply_text("کاربرد: /removemoney <player_id> <amount>", parse_mode="Markdown")
        return

    try:
        player_id, amount = int(args[0]), int(args[1])
    except ValueError:
        await update.message.reply_text("مقادیر باید عدد باشند.", parse_mode="Markdown")
        return

    country = db.get_country_by_player(player_id)
    if not country:
        await update.message.reply_text("کشوری پیدا نشد.", parse_mode="Markdown")
        return

    db.adjust_treasury(country["id"], -amount)
    await update.message.reply_text(f"✅ مبلغ {format_money(amount)} از خزانه {country['name']} کم شد.", parse_mode="Markdown")


async def listcountries(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ این دستور فقط برای ادمین‌هاست.", parse_mode="Markdown")
        return

    countries = db.get_all_countries()
    if not countries:
        await update.message.reply_text("هنوز هیچ کشوری ثبت نشده.", parse_mode="Markdown")
        return

    lines = ["📋 لیست کشورها:\n"]
    for c in countries:
        lines.append(f"{c['flag']} {c['name']} — player_id: `{c['player_id']}` — خزانه: {format_money(c['treasury'])}")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
