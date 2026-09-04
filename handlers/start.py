# -*- coding: utf-8 -*-
"""
دستور /start : انتخاب کشور از بین لیست با دسته‌بندی قاره‌ای و امکان جستجوی سریع نام کشور.
پشتیبانی از تفکیک قاره‌ها، وضعیت ظرفیت، جستجوی هوشمند و هدایت به ساخت گروه‌های غیردولتی.
"""

import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

import database as db
import config
from utils import get_main_keyboard


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


def build_continent_keyboard():
    """کیبورد دسته‌بندی قاره‌ها + دکمه جستجو و گروه‌های غیردولتی."""
    continents = getattr(config, "CONTINENTS", {})
    buttons = []
    row = []

    for c_key, c_info in continents.items():
        row.append(InlineKeyboardButton(c_info["name"], callback_data=f"pickcont:{c_key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([InlineKeyboardButton("🔎 جستجوی سریع نام کشور (تایپی)", callback_data="start_search_country")])
    buttons.append([InlineKeyboardButton("🏴‍☠️ تاسیس و رهبری بازوی نیابتی / گروه غیردولتی (۱۰۰ هزار ت)", callback_data="vip:militia_wizard_start")])
    return buttons


def build_continent_countries_keyboard(cont_key: str):
    """کیبورد کشورهای یک قاره مشخص همراه با تفکیک کشورهای آزاد و پرشده."""
    continents = getattr(config, "CONTINENTS", {})
    cont_info = continents.get(cont_key)
    if not cont_info:
        return []

    taken_and_pending = db.get_taken_and_pending_country_keys()
    buttons = []
    row = []

    for key in cont_info["keys"]:
        info = config.COUNTRIES.get(key)
        if not info:
            continue
        is_taken = key in taken_and_pending
        if is_taken:
            btn_label = f"🔒 {info['flag']} {info['name']}"
            cb_data = f"pickcountry_taken:{key}"
        else:
            btn_label = f"{info['flag']} {info['name']}"
            cb_data = f"pickcountry:{key}"

        row.append(InlineKeyboardButton(btn_label, callback_data=cb_data))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton("🔎 جستجوی کشور", callback_data="start_search_country"),
        InlineKeyboardButton("🔙 لیست قاره‌ها", callback_data="start_back_continents")
    ])
    return buttons


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    player_id = user.id

    if not user.username:
        await update.message.reply_text(
            "⛔ *خطا در ورود (احراز هویت تلگرام):*\n\n"
            "جهت حفظ امنیت بازی و جلوگیری از حساب‌های ناشناس و فیک، حساب تلگرام شما باید دارای *آیدی / یوزرنیم (@username)* باشد.\n\n"
            "لطفاً در تنظیمات تلگرام خود یک آیدی (Username) تنظیم فرموده و سپس مجدداً دستور /start را ارسال کنید.",
            parse_mode="Markdown"
        )
        return

    existing = db.get_country_by_player(player_id)
    if existing:
        await update.message.reply_text(
            f"{existing['flag']} کشور/گروه **{existing['name']}** تو از قبل ثبت شده است.\n"
            "از دکمه‌های پایین صفحه برای هدایت و مدیریت کشورت استفاده کن 👇",
            reply_markup=get_main_keyboard(player_id),
            parse_mode="Markdown"
        )
        return

    # بررسی قفل ثبت‌نام
    is_adm = player_id in config.ADMIN_IDS
    if not is_adm and db.get_setting("country_creation_locked") == "1":
        await update.message.reply_text(
            f"🔒 **ثبت‌نام و انتخاب کشورها موقتاً قفل است!**\n\n"
            "بازی «سیاست مدرن» در حال حاضر در فاز آماده‌سازی نهایی قرار دارد.\n"
            "زمان شروع رسمی به‌زودی در کانال تلگرام اعلام خواهد شد.\n\n"
            f"📢 **کانال رسمی بازی:** {config.get_channel_id()}",
            parse_mode="Markdown"
        )
        return

    text = (
        "🎮 **به بازی ژئوپلیتیک «سیاست مدرن» خوش آمدید!**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "بیش از ۱۰۰ کشور مستقل و سازمان راهبردی در بازی شبیه‌سازی شده‌اند.\n\n"
        "جهت انتخاب کشور، **قاره مورد نظر خود را انتخاب فرمایید** یا از **جستجوی سریع** استفاده کنید:"
    )

    buttons = build_continent_keyboard()
    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def pick_continent_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش لیست کشورهای قاره انتخاب‌شده."""
    query = update.callback_query
    await query.answer()

    cont_key = query.data.split(":", 1)[1]
    continents = getattr(config, "CONTINENTS", {})
    cont_info = continents.get(cont_key)

    if not cont_info:
        await query.edit_message_text("قاره مورد نظر یافت نشد.", reply_markup=InlineKeyboardMarkup(build_continent_keyboard()), parse_mode="Markdown")
        return

    text = (
        f"{cont_info['name']}\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "لطفاً کشور مورد نظر خود را جهت ارسال درخواست انتخاب فرمایید:\n"
        "*(کشورهای دارای نشان 🔒 قبلاً توسط سایر بازیکنان انتخاب شده‌اند)*"
    )

    buttons = build_continent_countries_keyboard(cont_key)
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def start_back_continents_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """بازگشت به منوی انتخاب قاره‌ها."""
    query = update.callback_query
    await query.answer()
    if "start_country_search" in context.user_data:
        del context.user_data["start_country_search"]

    text = (
        "🎮 **به بازی ژئوپلیتیک «سیاست مدرن» خوش آمدید!**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "جهت انتخاب کشور، **قاره مورد نظر خود را انتخاب فرمایید** یا از **جستجوی سریع** استفاده کنید:"
    )
    buttons = build_continent_keyboard()
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")


async def start_search_country_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """فعال‌سازی حالت جستجوی تایپی نام کشور."""
    query = update.callback_query
    await query.answer()

    context.user_data["start_country_search"] = True

    text = (
        "🔎 **جستجوی سریع نام کشور**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "لطفاً **نام فارسی یا انگلیسی کشور مورد نظر** را تایپ و ارسال فرمایید:\n\n"
        "*(مثال: آلمان، فرانسه، ژاپن، برزیل، چین، کانادا، egypt)*"
    )
    kb = [[InlineKeyboardButton("🔙 بازگشت به لیست قاره‌ها", callback_data="start_back_continents")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")


async def start_country_search_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """پردازش ورودی جستجوی متنی نام کشور در صفحه شروع."""
    if not context.user_data.get("start_country_search"):
        return False

    del context.user_data["start_country_search"]
    user_query = (update.message.text or update.message.caption or "").strip()
    if not user_query:
        return False
    clean_q = _clean_persian_str(user_query)

    if not clean_q:
        await update.message.reply_text("❌ لطفاً یک نام معتبر برای جستجو وارد کنید.")
        return True

    taken_and_pending = db.get_taken_and_pending_country_keys()
    matches = []

    for key, info in config.COUNTRIES.items():
        if key in ("un", "kurdistan"):
            continue
        c_name = info.get("name", "")
        clean_name = _clean_persian_str(c_name)
        clean_key = _clean_persian_str(key)

        if clean_q in clean_name or clean_name in clean_q or clean_q in clean_key:
            is_taken = key in taken_and_pending
            matches.append((key, info, is_taken))

    if not matches:
        text = (
            f"❌ **کشوری با عنوان «{user_query}» یافت نشد.**\n\n"
            "💡 لطفاً نام را به فارسی یا انگلیسی صحیح وارد کرده یا از لیست قاره‌ها انتخاب بفرمایید:"
        )
        kb = [
            [InlineKeyboardButton("🔁 جستجوی دوباره", callback_data="start_search_country")],
            [InlineKeyboardButton("🔙 مشاهده لیست قاره‌ها", callback_data="start_back_continents")],
        ]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="Markdown")
        return True

    text = (
        f"🔎 **نتایج جستجو برای «{user_query}» ({len(matches)} کشور):**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "روی کشور مورد نظر کلیک کنید:"
    )

    buttons = []
    row = []
    for key, info, is_taken in matches:
        if is_taken:
            btn_label = f"🔒 {info['flag']} {info['name']} (تکمیل)"
            cb_data = f"pickcountry_taken:{key}"
        else:
            btn_label = f"{info['flag']} {info['name']}"
            cb_data = f"pickcountry:{key}"

        row.append(InlineKeyboardButton(btn_label, callback_data=cb_data))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    buttons.append([
        InlineKeyboardButton("🔁 جستجوی مجدد", callback_data="start_search_country"),
        InlineKeyboardButton("🔙 لیست قاره‌ها", callback_data="start_back_continents")
    ])

    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")
    return True


async def pick_country(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = update.effective_user
    player_id = user.id

    if query.data.startswith("pickcountry_taken:"):
        key = query.data.split(":", 1)[1]
        info = config.COUNTRIES.get(key, {})
        await query.answer(f"کشور {info.get('name', key)} قبلاً توسط کاربر دیگری انتخاب شده است!", show_alert=True)
        return

    if not user.username:
        await query.edit_message_text(
            "⛔ *حساب تلگرام شما فاقد یوزرنیم (@username) است.*\nلطفاً ابتدا در تنظیمات تلگرام آیدی ست کرده و سپس /start بزنید.",
            parse_mode="Markdown"
        )
        return

    # بررسی قفل ثبت‌نام
    is_adm = player_id in config.ADMIN_IDS
    if not is_adm and db.get_setting("country_creation_locked") == "1":
        await query.edit_message_text(
            f"🔒 **ثبت‌نام و انتخاب کشورها موقتاً قفل است!**\n\n"
            "زمان شروع رسمی به‌زودی در کانال تلگرام اعلام خواهد شد.\n\n"
            f"📢 **کانال رسمی بازی:** {config.get_channel_id()}",
            parse_mode="Markdown"
        )
        return

    existing = db.get_country_by_player(player_id)
    if existing:
        await query.edit_message_text(f"تو از قبل کشور {existing['flag']} {existing['name']} رو داری!", parse_mode="Markdown")
        await context.bot.send_message(
            chat_id=player_id,
            text="از دکمه‌های پایین صفحه استفاده کن 👇",
            reply_markup=get_main_keyboard(player_id)
        )
        return

    # بررسی درخواست معلق قبلی
    pending_req = db.get_pending_request_by_player(player_id)
    if pending_req:
        await query.edit_message_text(
            "⏳ *شما یک درخواست معلق فعال دارید.*\nلطفاً منتظر بررسی و تایید ادمین اصلی بازی بمانید.",
            parse_mode="Markdown"
        )
        return

    key = query.data.split(":", 1)[1]
    info = config.COUNTRIES.get(key)
    if not info:
        await query.edit_message_text("این کشور دیگر در دسترس نیست.", parse_mode="Markdown")
        return

    # کاربران مسدودشده هرگز نمی‌توانند کشور بگیرند
    if db.is_banned(player_id):
        await query.edit_message_text(db.BANNED_MESSAGE, parse_mode="Markdown")
        return

    # داورهای فعال حق گرفتن کشور ندارند (حفظ بی‌طرفی داوری)
    if db.is_playing_restricted(player_id):
        await query.edit_message_text(db.PLAY_RESTRICTED_MESSAGE, parse_mode="Markdown")
        return

    # جلوگیری از انتخاب همزمان کشور توسط دو کاربر
    if key in db.get_taken_and_pending_country_keys():
        await query.edit_message_text(
            f"🔒 کشور {info['flag']} {info['name']} همین الان توسط بازیکن دیگری درخواست شد!\nلطفاً کشور دیگری انتخاب فرمایید.",
            reply_markup=InlineKeyboardMarkup(build_continent_keyboard()),
            parse_mode="Markdown"
        )
        return

    # ثبت درخواست معلق
    req_id = db.create_pending_country_request(
        player_id=player_id,
        first_name=user.first_name or "",
        last_name=user.last_name or "",
        username=user.username,
        country_key=key
    )

    db.add_log(actor=str(player_id), action="request_country", details=key)

    # ارسال اعلان و پرونده به ادمین
    u_name_display = f"`@{user.username}`" if user.username else "ندارد"
    user_url = f"https://t.me/{user.username}" if user.username else f"tg://user?id={player_id}"
    safe_name = f"{user.first_name or ''} {user.last_name or ''}".strip().replace("_", "\\_").replace("*", "\\*")
    admin_msg = (
        "📥 *درخواست جدید انتخاب کشور*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"• *کشور درخواستی:* {info['flag']} {info['name']} (`{key}`)\n"
        f"• *نام کاربر:* {safe_name}\n"
        f"• *یوزرنیم تلگرام:* {u_name_display}\n"
        f"• *شناسه عددی (ID):* `{player_id}`\n\n"
        f"🔍 برای بررسی هویت و پیام دادن به بازیکن، روی دکمه زیر کلیک کنید:"
    )

    admin_kb = [
        [InlineKeyboardButton("👤 مشاهده پروفایل / چت با متقاضی در پیوی", url=user_url)],
        [
            InlineKeyboardButton("✅ تایید و واگذاری کشور", callback_data=f"admin:approve_country:{req_id}"),
            InlineKeyboardButton("❌ رد درخواست", callback_data=f"admin:reject_country:{req_id}")
        ],
    ]

    for admin_id in config.ADMIN_IDS:
        try:
            await context.bot.send_message(
                chat_id=admin_id,
                text=admin_msg,
                reply_markup=InlineKeyboardMarkup(admin_kb),
                parse_mode="Markdown"
            )
        except Exception:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_msg.replace("*", "").replace("`", ""),
                    reply_markup=InlineKeyboardMarkup(admin_kb)
                )
            except Exception:
                pass

    await query.edit_message_text(
        f"⏳ *درخواست انتخاب کشور ثبت گردید!*\n\n"
        f"درخواست شما برای دریافت کشور {info['flag']} {info['name']} جهت تایید برای ادمین اصلی بازی ارسال شد.\n"
        "پس از بررسی و تایید ادمین، کشور شما فعال گردیده و اطلاع‌رسانی خواهد شد.",
        parse_mode="Markdown"
    )


async def reset_me(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور تست: کشور خود را پاک می‌کند تا بتوانید دوباره از /start شروع کنید."""
    player_id = update.effective_user.id
    deleted = db.delete_country_by_player(player_id)
    if deleted:
        await update.message.reply_text("✅ کشورت پاک شد. حالا می‌تونی دوباره /start رو بزنی.", parse_mode="Markdown")
    else:
        await update.message.reply_text("کشوری برای پاک کردن نداری.", parse_mode="Markdown")


def get_start_handlers():
    return [
        CommandHandler("start", start),
        CommandHandler("resetme", reset_me),
        CallbackQueryHandler(pick_continent_callback, pattern=r"^pickcont:"),
        CallbackQueryHandler(start_search_country_callback, pattern=r"^start_search_country$"),
        CallbackQueryHandler(start_back_continents_callback, pattern=r"^start_back_continents$"),
        CallbackQueryHandler(pick_country, pattern=r"^pickcountry"),
    ]
