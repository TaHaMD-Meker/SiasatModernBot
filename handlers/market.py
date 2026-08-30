# -*- coding: utf-8 -*-
"""
ماژول بازار بورس بین‌المللی کالاها (Global Commodities Exchange)
امکان معامله فوری و آنلاین نفت، طلا و غلات بین کشورها با امکان تعیین قیمت دلخواه،
انتخاب روش ترابری (دریایی، زمینی، هوایی)، خنثی‌سازی تحریم‌ها و انسدادها، و مشاهده آمار بازار.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

import database as db
import config
import news_engine
from utils import format_money, format_number, format_oil, get_main_keyboard, clear_text_input_flags


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
            msg = f"⏳ **درخواست رهبری کشور {flag} {name} در صف بررسی ادمین است.**\n\nپس از تایید ادمین، بازار بورس فعال می‌شود."
            alert_text = f"درخواست کشور {name} در انتظار تأیید ادمین است!"
        else:
            msg = "❌ شما هنوز کشوری در بازی ندارید! برای شروع /start را بزنید."
            alert_text = "هنوز کشوری نساختی! برای شروع /start بزن."

        if update.message:
            await update.message.reply_text(msg, parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.answer(alert_text, show_alert=True)
        return None
    return country


# ==================== منوی اصلی بورس کالا ====================

async def market_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = await require_country(update)
    if not c:
        return

    # 🚫 تحریم جامع سازمان ملل: بورس جهانی برای کشور تحریمی بسته است
    if c.get("un_sanctioned") or 0:
        blocked_text = (
            "🚫 **تحریم جامع سازمان ملل متحد**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "بورس جهانی کالاها برای کشور شما به موجب مصوبه شورای امنیت **مسدود** است.\n"
            "📉 درآمد روزانه شما نیز تحت تأثیر تحریم کاهش یافته است.\n\n"
            "_برای رفع تحریم با سازمان ملل و آژانس انرژی اتمی تماس بگیرید._"
        )
        if update.message:
            await update.message.reply_text(blocked_text, parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.edit_message_text(blocked_text, parse_mode="Markdown")
        return

    stats = db.get_market_stats()
    oil_low = f"{stats['oil'].get('lowest_active'):,} $" if stats.get('oil',{}).get('lowest_active') else f"{config.OIL_GLOBAL_PRICE:,} $ (قیمت پایه جهانی)"
    gold_low = f"{stats['gold'].get('lowest_active'):,} $" if stats.get('gold',{}).get('lowest_active') else "بدون عرضه"
    grain_low = f"{stats['grain'].get('lowest_active'):,} $" if stats.get('grain',{}).get('lowest_active') else "بدون عرضه"
    iron_low = f"{stats.get('iron_ore',{}).get('lowest_active'):,} $" if stats.get('iron_ore',{}).get('lowest_active') else "بدون عرضه"
    chips_low = f"{stats.get('microchips',{}).get('lowest_active'):,} $" if stats.get('microchips',{}).get('lowest_active') else "بدون عرضه"
    u_low = f"{stats.get('uranium_ore',{}).get('lowest_active'):,} $" if stats.get('uranium_ore',{}).get('lowest_active') else "بدون عرضه"
    fuel_low = f"{stats.get('nuclear_fuel',{}).get('lowest_active'):,} $" if stats.get('nuclear_fuel',{}).get('lowest_active') else "بدون عرضه"

    chips_res = c.get('microchips', 0) or 0
    chips_prod = c.get('microchips_daily', 0) or 0
    iron_res = c.get('iron_ore', 0) or 0
    iron_prod = c.get('iron_ore_daily', 0) or 0
    u_res = c.get('uranium_ore', 0) or 0
    u_prod = c.get('uranium_ore_daily', 0) or 0
    fuel_res = c.get('nuclear_fuel', 0) or 0
    fuel_prod = c.get('nuclear_fuel_daily', 0) or 0

    text = (
        f"📈 **بازار بورس بین‌المللی کالاها (Global Commodities Exchange)**\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🏦 *کشور:* {c['flag']} {c['name']}\n"
        f"💰 *موجودی خزانه:* {format_money(c['treasury'])}\n"
        f"🛢️ *نفت:* {format_oil(c['oil_reserves'])} | 🪙 *طلا:* {format_number(c['gold'])} | 🌾 *غلات:* {format_number(c['grain'])} تن\n"
        f"⛏️ *سنگ آهن و فولاد:* {format_number(iron_res)} تن (+{format_number(iron_prod)}/روز) | 💻 *ذخیره چیپ:* {format_number(chips_res)} عدد\n"
        f"☢️ *کیک زرد:* {format_number(u_res)} تن | 🧪 *سوخت هسته‌ای:* {format_number(fuel_res)} کیلوگرم\n\n"
        f"📊 **قیمت‌های کف فعلی بازار:**\n"
        f"• 🛢️ **نفت خام:** هر بشکه {oil_low}\n"
        f"• 🪙 **شمش طلا:** هر شمش {gold_low}\n"
        f"• 🌾 **غلات و گندم:** هر تن {grain_low}\n"
        f"• ⛏️ **سنگ آهن و فولاد:** هر تن {iron_low}\n"
        f"• 💻 **میکروچیپ:** هر عدد {chips_low}\n"
        f"• ☢️ **کیک زرد اورانیوم:** هر تن {u_low}\n"
        f"• 🧪 **سوخت غنی‌شده:** هر کیلوگرم {fuel_low}\n\n"
        "بازار مد نظر خود جهت معامله فوری یا ثبت عرضه را انتخاب کنید:"
    )

    keyboard = [
        [
            InlineKeyboardButton("🛢️ بورس نفت", callback_data="market:cat:oil"),
            InlineKeyboardButton("🪙 بورس طلا", callback_data="market:cat:gold"),
        ],
        [
            InlineKeyboardButton("🌾 بورس غلات", callback_data="market:cat:grain"),
            InlineKeyboardButton("⛏️ بورس آهن و فولاد", callback_data="market:cat:iron_ore"),
        ],
        [
            InlineKeyboardButton("💻 بورس میکروچیپ", callback_data="market:cat:microchips"),
            InlineKeyboardButton("☢️ بورس کیک زرد", callback_data="market:cat:uranium_ore"),
        ],
        [
            InlineKeyboardButton("🧪 بورس سوخت هسته‌ای", callback_data="market:cat:nuclear_fuel"),
            InlineKeyboardButton("➕ ثبت عرضه و فروش جدید", callback_data="market:create_order"),
        ],
        [
            InlineKeyboardButton("📦 عرضه‌ها و سفارش‌های من", callback_data="market:my_orders"),
            InlineKeyboardButton("📊 شاخص‌ها و آمار جهانی", callback_data="market:stats"),
        ],
    ]

    if update.message:
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== Callback Handler بورس ====================

async def market_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    country = db.get_country_by_player(user_id)

    if not country:
        await query.answer("هنوز کشوری نساختی!", show_alert=True)
        return

    await query.answer()

    if data == "market:menu":
        await market_main_menu(update, context)

    elif data.startswith("market:cat:"):
        res_type = data.split(":")[2]
        res_names = {"oil": "🛢️ نفت خام", "gold": "🪙 شمش طلا", "grain": "🌾 غلات و گندم", "iron_ore": "⛏️ سنگ آهن و فولاد", "microchips": "💻 میکروچیپ و تراشه", "uranium_ore": "☢️ کیک زرد اورانیوم", "nuclear_fuel": "🧪 سوخت هسته‌ای غنی‌شده", "vaccine_doses": "💉 دُز واکسن"}
        unit_names = {"oil": "بشکه", "gold": "شمش", "grain": "تن", "iron_ore": "تن", "microchips": "عدد", "uranium_ore": "تن", "nuclear_fuel": "کیلوگرم", "vaccine_doses": "دُز"}

        orders = db.get_market_orders(res_type)

        lines = [
            f"📈 **بازار بورس بین‌المللی — {res_names.get(res_type, res_type)}**\n",
            "━━━━━━━━━━━━━━━━━━\n"
        ]

        keyboard = []
        if not orders:
            lines.append("❌ در حال حاضر هیچ عرضه‌ای برای این کالا در بازار ثبت نشده است.\n")
            lines.append("💡 می‌توانید با استفاده از دکمه زیر، اولین عرضه‌کننده این کالا در بورس جهانی باشید!")
        else:
            lines.append("📋 **لیست عرضه‌های فعال (مرتب‌شده بر اساس ارزان‌ترین قیمت):**\n")
            for ord_item in orders[:10]: # Display top 10 cheapest offers
                o_id = ord_item["id"]
                u_price = ord_item["unit_price"]
                amt = ord_item["amount"]
                s_flag = ord_item["seller_flag"]
                s_name = ord_item["seller_name"]

                lines.append(f"• **سفارش #{o_id}** | {s_flag} **{s_name}**")
                lines.append(f"  قیمت واحد: **{u_price:,} $** | موجودی عرضه: **{amt:,} {unit_names.get(res_type, 'واحد')}**\n")

                btn_text = f"🛒 خرید فوری #{o_id} ({s_name} — {u_price:,} $)"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"market:view:{o_id}")])

        keyboard.append([InlineKeyboardButton("➕ ثبت عرضه جدید", callback_data=f"market:sell_type:{res_type}")])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت به منوی اصلی بورس", callback_data="market:menu")])

        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("market:view:"):
        order_id = int(data.split(":")[2])
        order = db.get_market_order_by_id(order_id)

        if not order or order["amount"] <= 0:
            await query.edit_message_text(
                "❌ این سفارش فروخته شده یا توسط فروشنده لغو گردیده است.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 بازگشت به بورس", callback_data="market:menu")]]),
                parse_mode="Markdown"
            )
            return

        res_names = {"oil": "نفت خام", "gold": "شمش طلا", "grain": "غلات", "iron_ore": "سنگ آهن و فولاد", "microchips": "میکروچیپ", "uranium_ore": "کیک زرد اورانیوم", "nuclear_fuel": "سوخت هسته‌ای", "vaccine_doses": "دُز واکسن"}
        unit_names = {"oil": "بشکه", "gold": "شمش", "grain": "تن", "iron_ore": "تن", "microchips": "عدد", "uranium_ore": "تن", "nuclear_fuel": "کیلوگرم", "vaccine_doses": "دُز"}
        r_type = order["resource_type"]

        text = (
            f"🛒 **جزئیات سفارش عرضه #{order['id']}**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• **کشور فروشنده:** {order['seller_flag']} **{order['seller_name']}**\n"
            f"• **نوع کالا:** {res_names.get(r_type, r_type)}\n"
            f"• **قیمت هر واحد:** **{order['unit_price']:,} $**\n"
            f"• **حجم کل آماده فروش:** **{order['amount']:,} {unit_names.get(r_type, 'واحد')}**\n\n"
            "مقدار درخواستی خود جهت خرید را انتخاب بفرمایید:"
        )

        total_amt = order["amount"]
        qty_options = []
        if total_amt >= 10: qty_options.append(int(total_amt * 0.1))
        if total_amt >= 4: qty_options.append(int(total_amt * 0.25))
        if total_amt >= 2: qty_options.append(int(total_amt * 0.5))
        qty_options.append(total_amt)

        # Unique deduplicated sorted quantities
        qty_options = sorted(list(set([q for q in qty_options if q > 0])))

        qty_buttons = []
        for q in qty_options:
            cost_val = q * order["unit_price"]
            qty_buttons.append([InlineKeyboardButton(
                f"📦 خرید {q:,} {unit_names.get(r_type, '')} ({format_money(cost_val)})",
                callback_data=f"market:qty:{order_id}:{q}"
            )])

        qty_buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data=f"market:cat:{r_type}")])

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(qty_buttons), parse_mode="Markdown")

    elif data.startswith("market:qty:"):
        parts = data.split(":")
        order_id = int(parts[2])
        qty = int(parts[3])

        order = db.get_market_order_by_id(order_id)
        if not order:
            await query.answer("سفارش یافت نشد.", show_alert=True)
            return

        commodity_cost = qty * order["unit_price"]
        res_names = {"oil": "نفت", "gold": "طلا", "grain": "غلات", "iron_ore": "آهن و فولاد", "microchips": "میکروچیپ", "uranium_ore": "کیک زرد", "nuclear_fuel": "سوخت هسته‌ای", "vaccine_doses": "دُز واکسن"}
        unit_names = {"oil": "بشکه", "gold": "شمش", "grain": "تن", "iron_ore": "تن", "microchips": "عدد", "uranium_ore": "تن", "nuclear_fuel": "کیلوگرم", "vaccine_doses": "دُز"}
        r_type = order["resource_type"]

        sea_lim = config.TRANSPORT_CAPACITY_LIMITS["sea"]["limits"].get(r_type, 500_000)
        land_lim = config.TRANSPORT_CAPACITY_LIMITS["land"]["limits"].get(r_type, 50_000)
        air_lim = config.TRANSPORT_CAPACITY_LIMITS["air"]["limits"].get(r_type, 10_000)

        seller_country = db.get_country_by_id(order["seller_id"])
        seller_key = seller_country.get("country_key") if seller_country else ""
        buyer_key = country.get("country_key")

        strait_analysis = db.get_trade_route_strait_analysis(seller_key, buyer_key)
        is_strait_blocked = strait_analysis["is_blocked"]
        has_strait_tolls = strait_analysis["has_tolls"]
        strait_toll_total = strait_analysis["total_toll"]

        if is_strait_blocked:
            blocked_str = "، ".join([s["name"] for s in strait_analysis["blocked_straits"]])
            sea_btn_label = f"⛔ دریایی (مسدود: {blocked_str})"
            sea_desc = f"🚢 <b>دریایی:</b> ⛔ مسدود ({blocked_str})"
        elif has_strait_tolls:
            total_sea_cost = 300_000 + strait_toll_total
            toll_str = "، ".join([f"{s['name']} ({s['toll_amount']:,} $)" for s in strait_analysis["toll_straits"]])
            sea_btn_label = f"🚢 دریایی ({total_sea_cost:,} $ با عوارض)" if qty <= sea_lim else f"🚢 دریایی (مازاد سقف {sea_lim:,})"
            sea_desc = f"🚢 <b>دریایی ({total_sea_cost:,} $ با عوارض {toll_str}):</b> حداکثر {sea_lim:,} {unit_names.get(r_type, '')} (کشتی باری/نفتکش فله)"
        else:
            sea_btn_label = "🚢 دریایی (۳۰۰ هزار $)" if qty <= sea_lim else f"🚢 دریایی (مازاد سقف {sea_lim:,})"
            sea_desc = f"🚢 <b>دریایی (۳۰۰ هزار $):</b> حداکثر {sea_lim:,} {unit_names.get(r_type, '')} (کشتی باری/نفتکش فله)"

        land_btn_label = "🚛 زمینی (۱ میلیون $)" if qty <= land_lim else f"🚛 زمینی (مازاد سقف {land_lim:,})"
        air_btn_label = "✈️ هوایی (۲ میلیون $)" if qty <= air_lim else f"✈️ هوایی (مازاد سقف {air_lim:,})"

        text = (
            f"🌐 <b>انتخاب روش ترابری معامله بورس</b>\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• <b>کالای درخواستی:</b> {qty:,} {unit_names.get(r_type, '')} <b>{res_names.get(r_type, '')}</b>\n"
            f"• <b>ارزش خالص کالا:</b> <b>{format_money(commodity_cost)}</b>\n"
            f"• <b>فروشنده:</b> {order['seller_flag']} <b>{order['seller_name']}</b>\n\n"
            "📦 <b>ظرفیت مجاز ناوگان‌های ترانزیت:</b>\n"
            f"{sea_desc}\n"
            f"🚛 <b>زمینی (۱ میلیون $):</b> حداکثر {land_lim:,} {unit_names.get(r_type, '')} (قطار باری و تریلی)\n"
            f"✈️ <b>هوایی (۲ میلیون $):</b> حداکثر {air_lim:,} {unit_names.get(r_type, '')} (هواپیمای کارگو — های‌تک/سریع)\n\n"
            "لطفاً روش ترابری متناسب با حجم محموله را انتخاب فرمایید:"
        )

        buttons = [
            [
                InlineKeyboardButton(sea_btn_label, callback_data=f"market:do_buy:{order_id}:{qty}:sea"),
            ],
            [
                InlineKeyboardButton(land_btn_label, callback_data=f"market:do_buy:{order_id}:{qty}:land"),
                InlineKeyboardButton(air_btn_label, callback_data=f"market:do_buy:{order_id}:{qty}:air"),
            ],
            [InlineKeyboardButton("❌ انصراف", callback_data=f"market:view:{order_id}")],
        ]

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")

    elif data.startswith("market:do_buy:") or data.startswith("market:do_buy_confirm:"):
        is_confirmed = data.startswith("market:do_buy_confirm:")
        parts = data.split(":")
        order_id = int(parts[2])
        qty = int(parts[3])
        t_mode = parts[4]

        order = db.get_market_order_by_id(order_id)
        if not order:
            await query.answer("سفارش یافت نشد.", show_alert=True)
            return

        seller_country = db.get_country_by_id(order["seller_id"])
        seller_key = seller_country.get("country_key") if seller_country else ""
        buyer_key = country.get("country_key")
        strait_analysis = db.get_trade_route_strait_analysis(seller_key, buyer_key)

        if t_mode == "sea":
            if strait_analysis["is_blocked"]:
                blocked_str = "، ".join([f"{s['name']} (توسط {s['owner_flag']} {s['owner_name']})" for s in strait_analysis["blocked_straits"]])
                await query.answer("❌ ترابری دریایی مسدود است!", show_alert=True)
                keyboard = [
                    [InlineKeyboardButton("🚛 خرید با ترابری زمینی", callback_data=f"market:do_buy:{order_id}:{qty}:land")],
                    [InlineKeyboardButton("✈️ خرید با ترابری هوایی", callback_data=f"market:do_buy:{order_id}:{qty}:air")],
                    [InlineKeyboardButton("🔙 بازگشت به بورس", callback_data="market:menu")]
                ]
                await query.edit_message_text(
                    f"⛔ **امکان ترابری دریایی وجود ندارد:**\n\nمسیر ترانزیت دریایی از **{blocked_str}** مسدود است.\nلطفاً از ترابری زمینی یا هوایی استفاده فرمایید.",
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="Markdown"
                )
                return

            if strait_analysis["has_tolls"] and not is_confirmed:
                commodity_cost = qty * order["unit_price"]
                res_names = {"oil": "نفت", "gold": "طلا", "grain": "غلات", "iron_ore": "آهن و فولاد", "microchips": "میکروچیپ", "uranium_ore": "کیک زرد", "nuclear_fuel": "سوخت هسته‌ای", "vaccine_doses": "دُز واکسن"}
                unit_names = {"oil": "بشکه", "gold": "شمش", "grain": "تن", "iron_ore": "تن", "microchips": "عدد", "uranium_ore": "تن", "nuclear_fuel": "کیلوگرم", "vaccine_doses": "دُز"}
                r_type = order["resource_type"]

                toll_lines = "\n".join([f"• 🌊 <b>{s['name']}</b> (تحت کنترل {s['owner_flag']} <b>{s['owner_name']}</b>): <code>{s['toll_amount']:,} $</code>" for s in strait_analysis["toll_straits"]])
                total_toll = strait_analysis["total_toll"]
                total_transport = 300_000 + total_toll
                total_buyer_cost = commodity_cost + total_transport

                text = (
                    f"🌊 <b>هشدار و تأییدیه عوارض ترانزیت تنگه‌های دریایی (بورس کالا)</b>\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"
                    f"• <b>کالای انتخابی:</b> {qty:,} {unit_names.get(r_type, '')} <b>{res_names.get(r_type, '')}</b>\n"
                    f"• <b>فروشنده:</b> {order['seller_flag']} <b>{order['seller_name']}</b>\n"
                    f"• <b>ارزش خالص کالا:</b> <code>{format_money(commodity_cost)}</code>\n\n"
                    f"🌊 <b>تنگه‌های دارای عوارض عبور در مسیر ترانزیت:</b>\n"
                    f"{toll_lines}\n\n"
                    f"💰 <b>تفکیک هزینه ترابری:</b>\n"
                    f"• کرایه ناوگان دریایی: <code>۳۰۰,۰۰۰ $</code>\n"
                    f"• مجموع عوارض تنگه‌ها: <code>{total_toll:,} $</code>\n"
                    f"• <b>مجموع کرایه ترابری:</b> <code>{format_money(total_transport)}</code>\n\n"
                    f"💳 <b>مجموع پرداختی شما از خزانه:</b> <b><code>{format_money(total_buyer_cost)}</code></b>\n\n"
                    f"⚠️ <i>مبلغ عوارض مستقیماً به خزانه کشور کنترل‌کننده تنگه واریز خواهد شد.</i>\n\n"
                    f"آیا با خرید و پرداخت عوارض موافقید؟"
                )
                buttons = [
                    [InlineKeyboardButton(f"✅ تأیید و خرید قطعی ({format_money(total_buyer_cost)})", callback_data=f"market:do_buy_confirm:{order_id}:{qty}:sea")],
                    [InlineKeyboardButton("🚛 تغییر به ترابری زمینی (۱,۰۰۰,۰۰۰ $)", callback_data=f"market:do_buy:{order_id}:{qty}:land")],
                    [InlineKeyboardButton("✈️ تغییر به ترابری هوایی (۲,۰۰۰,۰۰۰ $)", callback_data=f"market:do_buy:{order_id}:{qty}:air")],
                    [InlineKeyboardButton("❌ انصراف", callback_data=f"market:qty:{order_id}:{qty}")],
                ]
                await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="HTML")
                return

        success, msg, meta = db.execute_market_buy_transaction(country["id"], order_id, qty, transport_mode=t_mode)

        if not success:
            await query.answer("❌ معامله انجام نشد!", show_alert=True)
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به بورس", callback_data="market:menu")]]
            await query.edit_message_text(f"❌ **خطا در انجام معامله بورس:**\n\n{msg}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return

        seller = meta.get("seller", {})
        res_label = meta.get("res_label", "کالا")
        res_type = meta.get("res_type", order["resource_type"] if 'order' in locals() else "oil")
        try:
            _mok, _mrw = db.complete_daily_mission(country["id"], "trade")
            if _mok:
                await context.bot.send_message(chat_id=user_id, text=f"🎯 *مأموریت روزانه کامل شد!* +{format_money(_mrw)} به خزانه.", parse_mode="Markdown")
            db.add_battle_pass_xp(country["id"], 200)
            db.progress_battle_pass_challenge(country["id"], "trade", 1)
            if seller and seller.get("id"):
                db.add_battle_pass_xp(seller["id"], 200)
                db.progress_battle_pass_challenge(seller["id"], "trade", 1)
                # صادرات تجمعی: کل تناژ فروخته‌شده شمرده می‌شود، نه فقط معاملات بالای ۵۰ هزار
                if res_type in ("oil", "grain") and qty > 0:
                    db.progress_battle_pass_challenge(seller["id"], "export", qty)
        except Exception:
            pass
        await query.answer("✅ معامله بورس با موفقیت انجام گردید!", show_alert=True)

        result_text = (
            f"🎉 **معامله بورس با موفقیت انجام گردید!**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• **کالای خریداری‌شده:** {qty:,} واحد **{res_label}**\n"
            f"• **فروشنده:** {seller['flag']} **{seller['name']}**\n"
            f"• **ارزش کالا:** {format_money(meta['commodity_cost'])}\n"
            f"• **هزینه ترابری ({t_mode}):** {format_money(meta['transport_cost'])}\n"
            f"• **مجموع پرداختی از خزانه:** **{format_money(meta['total_buyer_cost'])}**\n\n"
            f"✅ کالا فوراً به ذخایر استراتژیک کشور شما منتقل گردید.\n\n"
            "❓ **انتشار در اخبار رسمی:** آیا تمایل دارید خبر این ترانزیت/معامله در کانال رسمی اخبار منتشر شود؟"
        )

        # Send Live Sale Alert & Receipt to Seller
        if seller.get("player_id"):
            try:
                seller_updated = db.get_country_by_id(seller["id"])
                seller_treasury = seller_updated["treasury"] if seller_updated else seller.get("treasury", 0) + meta["commodity_cost"]
                seller_msg = (
                    f"💰 **اعلان زنده معامله و واریز وجه در بورس کالا!**\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"
                    f"کشور {country['flag']} **{country['name']}** تعداد {qty:,} واحد **{res_label}** شما را در بازار بورس جهانی خریداری نمود.\n\n"
                    f"• **مبلغ واریزی به خزانه شما:** +**{format_money(meta['commodity_cost'])}**\n"
                    f"• **موجودی جدید خزانه شما:** **{format_money(seller_treasury)}**"
                )
                await context.bot.send_message(chat_id=seller["player_id"], text=seller_msg, parse_mode="Markdown")
            except Exception:
                pass

        seller_id = seller.get("id")
        buyer_id = country.get("id")
        keyboard = [
            [
                InlineKeyboardButton("📢 بله، انتشار در کانال اخبار", callback_data=f"market:pub_news:{order_id}:{t_mode}:{seller_id}:{buyer_id}:yes"),
                InlineKeyboardButton("🔕 خیر، معامله محرمانه بماند", callback_data=f"market:pub_news:{order_id}:{t_mode}:{seller_id}:{buyer_id}:no"),
            ],
            [InlineKeyboardButton("🏪 بازگشت به بورس کالا", callback_data="market:menu")],
            [InlineKeyboardButton("🌐 مشاهده وضعیت کشور", callback_data="country:back_profile")]
        ]

        await query.edit_message_text(result_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("market:pub_news:"):
        parts = data.split(":")
        try:
            order_id = int(parts[2])
            t_mode = parts[3]
            if len(parts) >= 7:
                seller_id = int(parts[4])
                buyer_id = int(parts[5])
                choice = parts[6]
            else:
                # سازگاری با پیام‌های قدیمی که شناسه طرفین را نداشتند.
                seller_id = None
                buyer_id = None
                choice = parts[4]
        except (IndexError, TypeError, ValueError):
            await query.answer("اطلاعات انتشار خبر نامعتبر است.", show_alert=True)
            return

        if buyer_id is not None and country["id"] != buyer_id:
            await query.answer("فقط خریدار این معامله می‌تواند درباره انتشار خبر تصمیم بگیرد.", show_alert=True)
            return
        if choice not in {"yes", "no"}:
            await query.answer("انتخاب انتشار خبر نامعتبر است.", show_alert=True)
            return

        if choice == "yes":
            order = db.get_market_order_by_id(order_id)
            buyer_c = country if buyer_id is None else db.get_country_by_id(buyer_id)
            resolved_seller_id = seller_id or (order["seller_id"] if order else None)
            seller_c = db.get_country_by_id(resolved_seller_id) if resolved_seller_id else None
            if buyer_c and seller_c:
                try:
                    await news_engine.trigger_trade_news(context.bot, buyer_c, seller_c, transport_mode=t_mode)
                    await query.edit_message_text(
                        f"{query.message.text}\n\n📢 **خبر ترانزیت این معامله با موفقیت در کانال رسمی اخبار منتشر شد.**",
                        parse_mode="Markdown"
                    )
                except Exception as e:
                    await query.edit_message_text(f"{query.message.text}\n\n❌ خطا در انتشار خبر: {e}", parse_mode="Markdown")
            else:
                await query.edit_message_text(f"{query.message.text}\n\n❌ اطلاعات معامله یافت نشد.", parse_mode="Markdown")
        else:
            await query.edit_message_text(
                f"{query.message.text}\n\n🔕 **این معامله کاملاً محرمانه باقی ماند و هیچ خبری در کانال رسمی منتشر نگردید.**",
                parse_mode="Markdown"
            )

    elif data == "market:create_order":
        text = (
            "➕ **ثبت عرضه و فروش جدید در بورس جهانی کالا**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            "لطفاً کالای مد نظر خود جهت عرضه در بورس بین‌المللی را انتخاب بفرمایید:"
        )
        buttons = [
            [
                InlineKeyboardButton("🛢️ فروش نفت خام", callback_data="market:sell_type:oil"),
                InlineKeyboardButton("🪙 فروش شمش طلا", callback_data="market:sell_type:gold"),
            ],
            [
                InlineKeyboardButton("🌾 فروش غلات و گندم", callback_data="market:sell_type:grain"),
                InlineKeyboardButton("⛏️ فروش سنگ آهن و فولاد", callback_data="market:sell_type:iron_ore"),
            ],
            [
                InlineKeyboardButton("💻 فروش میکروچیپ", callback_data="market:sell_type:microchips"),
                InlineKeyboardButton("☢️ فروش کیک زرد", callback_data="market:sell_type:uranium_ore"),
            ],
            [
                InlineKeyboardButton("🧪 فروش سوخت هسته‌ای", callback_data="market:sell_type:nuclear_fuel"),
                InlineKeyboardButton("❌ انصراف و بازگشت", callback_data="market:menu"),
            ],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

    elif data.startswith("market:sell_type:"):
        res_type = data.split(":")[2]
        clear_text_input_flags(context.user_data)
        context.user_data["market_sell_draft"] = {"step": "amount", "res_type": res_type}

        res_names = {"oil": "نفت خام", "gold": "شمش طلا", "grain": "غلات", "iron_ore": "سنگ آهن و فولاد", "microchips": "میکروچیپ", "uranium_ore": "کیک زرد اورانیوم", "nuclear_fuel": "سوخت هسته‌ای", "vaccine_doses": "دُز واکسن"}
        unit_names = {"oil": "بشکه", "gold": "شمش", "grain": "تن", "iron_ore": "تن", "microchips": "عدد", "uranium_ore": "تن", "nuclear_fuel": "کیلوگرم", "vaccine_doses": "دُز"}
        res_cols = {"oil": "oil_reserves", "gold": "gold", "grain": "grain", "iron_ore": "iron_ore", "microchips": "microchips", "uranium_ore": "uranium_ore", "nuclear_fuel": "nuclear_fuel"}

        curr_qty = country.get(res_cols[res_type], 0)

        floor_hint = ""
        if res_type == "oil":
            floor_hint = f"\n💡 **قیمت کف نفت در بورس:** {config.OIL_GLOBAL_PRICE:,} $/بشکه (عرضه زیر این قیمت مجاز نیست)\n"
        elif res_type == "iron_ore":
            floor_hint = f"\n💡 **قیمت پایه سنگ آهن در بورس:** {config.IRON_ORE_GLOBAL_PRICE:,} $/تن\n"

        text = (
            f"➕ **عرضه و فروش {res_names.get(res_type, res_type)}**\n"
            f"📦 **موجودی فعلی شما:** {curr_qty:,} {unit_names.get(res_type, '')}\n"
            "━━━━━━━━━━━━━━━━━━"
            f"{floor_hint}"
            f"\nلطفاً **مقدار و تعداد** مد نظر خود جهت فروش را به عدد انگلیسی ارسال فرمایید:"
        )

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="market:menu")]]), parse_mode="Markdown")

    elif data == "market:my_orders":
        my_orders = db.get_country_market_orders(country["id"])
        lines = [f"📦 **عرضه‌ها و سفارش‌های فعال کشور {country['flag']} {country['name']}**\n━━━━━━━━━━━━━━━━━━\n"]

        keyboard = []
        if not my_orders:
            lines.append("شما در حال حاضر هیچ عرضه فعالی در بورس کالا ندارید.")
        else:
            res_names = {"oil": "نفت", "gold": "طلا", "grain": "غلات", "iron_ore": "آهن و فولاد", "microchips": "میکروچیپ", "uranium_ore": "کیک زرد", "nuclear_fuel": "سوخت هسته‌ای", "vaccine_doses": "دُز واکسن"}
            unit_names = {"oil": "بشکه", "gold": "شمش", "grain": "تن", "iron_ore": "تن", "microchips": "عدد", "uranium_ore": "تن", "nuclear_fuel": "کیلوگرم", "vaccine_doses": "دُز"}

            for ord_item in my_orders:
                o_id = ord_item["id"]
                r_type = ord_item["resource_type"]
                amt = ord_item["amount"]
                price = ord_item["unit_price"]

                lines.append(f"• **سفارش #{o_id}** | {res_names.get(r_type, r_type)}")
                lines.append(f"  تعداد: **{amt:,} {unit_names.get(r_type, '')}** | قیمت واحد: **{price:,} $**\n")

                keyboard.append([InlineKeyboardButton(f"❌ لغو و بازگشت کالا #{o_id}", callback_data=f"market:cancel:{o_id}")])

        keyboard.append([InlineKeyboardButton("➕ ثبت عرضه جدید", callback_data="market:create_order")])
        keyboard.append([InlineKeyboardButton("🔙 بازگشت به بورس", callback_data="market:menu")])

        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("market:cancel:"):
        order_id = int(data.split(":")[2])
        success, msg = db.cancel_market_order(country["id"], order_id)

        if success:
            await query.answer("✅ عرضه لغو و کالا عودت گردید!", show_alert=True)
        else:
            await query.answer(f"❌ {msg}", show_alert=True)

        # Refresh my orders view
        await market_callback_handler(update, context)

    elif data == "market:stats":
        stats = db.get_market_stats()

        lines = [
            "📊 **شاخص‌ها و آمار کلی بورس جهانی کالاها**\n",
            "━━━━━━━━━━━━━━━━━━\n"
        ]

        res_labels = {"oil": "🛢️ نفت خام (بشکه)", "gold": "🪙 طلا (شمش)", "grain": "🌾 غلات (تن)", "iron_ore": "⛏️ آهن و فولاد (تن)", "microchips": "💻 میکروچیپ (عدد)", "uranium_ore": "☢️ کیک زرد (تن)", "nuclear_fuel": "🧪 سوخت هسته‌ای (ک‌گ)"}

        for r_type in ("oil", "gold", "grain", "iron_ore", "microchips", "uranium_ore", "nuclear_fuel"):
            st = stats.get(r_type, {})
            label = res_labels[r_type]
            trades = st.get("trade_count", 0)
            vol = st.get("total_volume", 0) or 0
            avg_p = st.get("avg_price", 0) or 0
            low_p = st.get("lowest_active")

            low_str = f"{low_p:,} $" if low_p else "بدون عرضه"
            avg_p_str = f"{int(avg_p):,} $" if (trades > 0 and avg_p > 0) else "بدون معامله"
            trades_str = f"{trades:,} معامله" if trades > 0 else "بدون معامله"

            lines.append(f"• **{label}:**")
            lines.append(f"  ارزان‌ترین قیمت فعال: **{low_str}**")
            lines.append(f"  میانگین قیمت معاملات: **{avg_p_str}**")
            lines.append(f"  حجم کل معاملات تا کنون: **{vol:,} واحد** ({trades_str})\n")

        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی بورس", callback_data="market:menu")]]
        await query.edit_message_text("\n".join(lines), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# ==================== Text Input Handler ثبت عرضه بورس ====================

async def market_text_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        return

    draft = context.user_data.get("market_sell_draft")
    if not draft:
        return

    raw_input = (update.message.text or update.message.caption or "").strip()
    if not raw_input:
        await update.message.reply_text("لطفاً عدد را به‌صورت متن بفرست.")
        return
    text_input = raw_input.replace(",", "").replace("٬", "")
    if not text_input.isdigit():
        await update.message.reply_text("⛔ لطفاً فقط یک عدد صحیح انگلیسی ارسال فرمایید.", parse_mode="Markdown")
        return

    num_val = int(text_input)
    if num_val <= 0:
        await update.message.reply_text("⛔ مقدار واردشده باید بزرگتر از صفر باشد.", parse_mode="Markdown")
        return

    step = draft.get("step")
    res_type = draft.get("res_type")
    res_names = {"oil": "نفت خام", "gold": "شمش طلا", "grain": "غلات", "iron_ore": "سنگ آهن و فولاد", "microchips": "میکروچیپ", "uranium_ore": "کیک زرد اورانیوم", "nuclear_fuel": "سوخت هسته‌ای", "vaccine_doses": "دُز واکسن"}
    unit_names = {"oil": "بشکه", "gold": "شمش", "grain": "تن", "iron_ore": "تن", "microchips": "عدد", "uranium_ore": "تن", "nuclear_fuel": "کیلوگرم", "vaccine_doses": "دُز"}

    if step == "amount":
        res_cols = {"oil": "oil_reserves", "gold": "gold", "grain": "grain", "iron_ore": "iron_ore", "microchips": "microchips", "uranium_ore": "uranium_ore", "nuclear_fuel": "nuclear_fuel"}
        curr_qty = country.get(res_cols[res_type], 0)

        if num_val > curr_qty:
            await update.message.reply_text(
                f"⛔ **موجودی کافی نیست!**\n\nموجودی فعلی شما: {curr_qty:,} {unit_names.get(res_type, '')}\nلطفاً عددی کمتر یا مساوی موجودی وارد کنید:",
                parse_mode="Markdown"
            )
            return

        draft["amount"] = num_val
        draft["step"] = "price"

        await update.message.reply_text(
            f"✅ **مقدار ثبت‌شد:** {num_val:,} {unit_names.get(res_type, '')}\n\n"
            f"حال لطفاً **قیمت پیشنهاد فروش برای هر واحد ({unit_names.get(res_type, '')}) به دلار ($)** را ارسال فرمایید:",
            parse_mode="Markdown"
        )

    elif step == "price":
        unit_price = num_val
        amount = draft.get("amount")

        # بررسی بازه مجاز قیمت‌گذاری برای جلوگیری از تبانی و دامپینگ
        bounds = getattr(config, "COMMODITY_MARKET_BOUNDS", {}).get(res_type)
        if bounds:
            min_p = bounds["min_price"]
            max_p = bounds["max_price"]
            unit_title = bounds["unit"]
            c_title = bounds["name"]

            if unit_price < min_p:
                await update.message.reply_text(
                    f"⛔ <b>قیمت زیر کف مجاز بازار است!</b>\n\n"
                    f"جهت حفظ سلامت اقتصاد و جلوگیری از تبانی و انتقال منابع بین اکانت‌ها:\n"
                    f"• حداقل قیمت مجاز {c_title}: <b>{format_money(min_p)} / {unit_title}</b>\n"
                    f"• قیمت پیشنهادی شما: {format_money(unit_price)}\n\n"
                    f"لطفاً قیمتی در بازه مجاز ({format_money(min_p)} تا {format_money(max_p)}) وارد فرمایید:",
                    parse_mode="HTML"
                )
                return
            elif unit_price > max_p:
                await update.message.reply_text(
                    f"⛔ <b>قیمت بالاتر از سقف مجاز بازار است!</b>\n\n"
                    f"• حداکثر قیمت مجاز {c_title}: <b>{format_money(max_p)} / {unit_title}</b>\n"
                    f"• قیمت پیشنهادی شما: {format_money(unit_price)}\n\n"
                    f"لطفاً قیمتی در بازه مجاز ({format_money(min_p)} تا {format_money(max_p)}) وارد فرمایید:",
                    parse_mode="HTML"
                )
                return
        elif res_type == "oil" and unit_price < config.OIL_GLOBAL_PRICE:
            await update.message.reply_text(
                f"⛔ **قیمت زیر کف بازار مجاز نیست!**\n\n"
                f"قیمت کف نفت در بورس: **{config.OIL_GLOBAL_PRICE:,} $/بشکه**\n"
                f"قیمت پیشنهادی شما: {unit_price:,} $/بشکه\n\n"
                f"لطفاً قیمتی برابر یا بالاتر از کف وارد کنید:",
                parse_mode="Markdown"
            )
            return

        del context.user_data["market_sell_draft"]

        success, msg = db.create_market_order(country["id"], res_type, amount, unit_price)

        if not success:
            await update.message.reply_text(f"❌ **خطا در ثبت عرضه بورس:**\n\n{msg}", parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))
            return

        try:
            db.add_battle_pass_xp(country["id"], 150)
            if res_type in ("oil", "grain") and amount >= 50_000:
                db.progress_battle_pass_challenge(country["id"], "export", 1)
        except Exception:
            pass

        total_value = amount * unit_price

        result_text = (
            f"🎉 **عرضه شما با موفقیت در بازار بورس جهانی ثبت شد!**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• **کالای عرضه‌شده:** {amount:,} {unit_names.get(res_type, '')} **{res_names.get(res_type, '')}**\n"
            f"• **قیمت هر واحد:** **{unit_price:,} $**\n"
            f"• **ارزش کل عرضه:** **{format_money(total_value)}**\n\n"
            f"📦 کالا تا زمان معامله یا لغو، در امانت بورس قرار گرفت."
        )

        keyboard = [
            [InlineKeyboardButton("📈 مشاهده بورس جهانی", callback_data="market:menu")],
            [InlineKeyboardButton("📦 سفارش‌های فعال من", callback_data="market:my_orders")],
        ]

        await update.message.reply_text(result_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


def get_market_handlers():
    return [
        CommandHandler(["market", "bourse", "bazar"], market_main_menu),
        CallbackQueryHandler(market_callback_handler, pattern=r"^market:"),
    ]
