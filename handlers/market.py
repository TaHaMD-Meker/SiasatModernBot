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
from utils import format_money, format_number, format_oil, get_main_keyboard


async def require_country(update: Update):
    user_id = update.effective_user.id
    country = db.get_country_by_player(user_id)
    if not country:
        if update.message:
            await update.message.reply_text("هنوز کشوری نساختی! برای شروع /start رو بزن.", parse_mode="Markdown")
        elif update.callback_query:
            await update.callback_query.answer("هنوز کشوری نساختی!", show_alert=True)
        return None
    return country


# ==================== منوی اصلی بورس کالا ====================

async def market_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    c = await require_country(update)
    if not c:
        return

    stats = db.get_market_stats()
    oil_low = f"{stats['oil'].get('lowest_active'):,} $" if stats['oil'].get('lowest_active') else "بدون عرضه"
    gold_low = f"{stats['gold'].get('lowest_active'):,} $" if stats['gold'].get('lowest_active') else "بدون عرضه"
    grain_low = f"{stats['grain'].get('lowest_active'):,} $" if stats['grain'].get('lowest_active') else "بدون عرضه"

    text = (
        f"📈 **بازار بورس بین‌المللی کالاها (Global Commodities Exchange)**\n"
        f"━━━━━━━━━━━━━━━━━━\n\n"
        f"🏦 *کشور:* {c['flag']} {c['name']}\n"
        f"💰 *موجودی خزانه:* {format_money(c['treasury'])}\n"
        f"🛢️ *ذخیره نفت:* {format_oil(c['oil_reserves'])} | 🪙 *طلا:* {format_number(c['gold'])} | 🌾 *غلات:* {format_number(c['grain'])}\n\n"
        f"📊 **قیمت‌های کف فعلی بازار:**\n"
        f"• 🛢️ **نفت خام:** هر بشکه {oil_low}\n"
        f"• 🪙 **شمش طلا:** هر شمش {gold_low}\n"
        f"• 🌾 **غلات:** هر تن {grain_low}\n\n"
        "بازار مد نظر خود جهت معامله فوری یا ثبت عرضه را انتخاب کنید:"
    )

    keyboard = [
        [
            InlineKeyboardButton("🛢️ بورس نفت", callback_data="market:cat:oil"),
            InlineKeyboardButton("🪙 بورس طلا", callback_data="market:cat:gold"),
            InlineKeyboardButton("🌾 بورس غلات", callback_data="market:cat:grain"),
        ],
        [
            InlineKeyboardButton("➕ ثبت عرضه و فروش جدید", callback_data="market:create_order"),
            InlineKeyboardButton("📦 عرضه‌ها و سفارش‌های من", callback_data="market:my_orders"),
        ],
        [
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
        res_names = {"oil": "🛢️ نفت خام", "gold": "🪙 شمش طلا", "grain": "🌾 غلات و گندم"}
        unit_names = {"oil": "بشکه", "gold": "شمش", "grain": "تن"}

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
                lines.append(f"  قیمت واحد: **{u_price:,} $** | موجودی عرضه: **{amt:,} {unit_names[res_type]}**\n")

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

        res_names = {"oil": "نفت خام", "gold": "شمش طلا", "grain": "غلات"}
        unit_names = {"oil": "بشکه", "gold": "شمش", "grain": "تن"}
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
        res_names = {"oil": "نفت", "gold": "طلا", "grain": "غلات"}
        unit_names = {"oil": "بشکه", "gold": "شمش", "grain": "تن"}
        r_type = order["resource_type"]

        text = (
            f"🌐 **انتخاب روش ترابری معامله بورس**\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"• **کالای درخواستی:** {qty:,} {unit_names.get(r_type, '')} {res_names.get(r_type, '')}\n"
            f"• **ارزش خالص کالا:** **{format_money(commodity_cost)}**\n"
            f"• **فروشنده:** {order['seller_flag']} **{order['seller_name']}**\n\n"
            "لطفاً روش ترابری و انتقال را انتخاب کنید:\n\n"
            "🚢 **دریایی (۳۰۰,۰۰۰ $):** ارزان‌ترین روش (غیرقابل استفاده در زمان محاصره بنادر/تنگه‌ها)\n"
            "🚛 **زمینی (۱,۰۰۰,۰۰۰ $):** بای‌پاس محاصره دریایی و تنگه‌ها\n"
            "✈️ **هوایی (۲,۰۰۰,۰۰۰ $):** سریع‌ترین روش، بای‌پاس کامل تمام محاصره‌ها"
        )

        buttons = [
            [
                InlineKeyboardButton("🚢 دریایی (۳۰۰ هزار $)", callback_data=f"market:do_buy:{order_id}:{qty}:sea"),
            ],
            [
                InlineKeyboardButton("🚛 زمینی (۱ میلیون $)", callback_data=f"market:do_buy:{order_id}:{qty}:land"),
                InlineKeyboardButton("✈️ هوایی (۲ میلیون $)", callback_data=f"market:do_buy:{order_id}:{qty}:air"),
            ],
            [InlineKeyboardButton("❌ انصراف", callback_data=f"market:view:{order_id}")],
        ]

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

    elif data.startswith("market:do_buy:"):
        parts = data.split(":")
        order_id = int(parts[2])
        qty = int(parts[3])
        t_mode = parts[4]

        success, msg, meta = db.execute_market_buy_transaction(country["id"], order_id, qty, transport_mode=t_mode)

        if not success:
            await query.answer("❌ معامله انجام نشد!", show_alert=True)
            keyboard = [[InlineKeyboardButton("🔙 بازگشت به بورس", callback_data="market:menu")]]
            await query.edit_message_text(f"❌ **خطا در انجام معامله بورس:**\n\n{msg}", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
            return

        await query.answer("✅ معامله بورس با موفقیت انجام گردید!", show_alert=True)

        seller = meta["seller"]
        res_label = meta["res_label"]

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

        # Send Private Receipt to Seller
        if seller.get("player_id"):
            try:
                seller_msg = (
                    f"💰 **واریز وجه معامله بورس کالا!**\n"
                    "━━━━━━━━━━━━━━━━━━\n\n"
                    f"کشور {country['flag']} **{country['name']}** تعداد {qty:,} واحد **{res_label}** شما را در بورس جهانی خریداری نمود.\n\n"
                    f"💵 **مبلغ واریزی به خزانه شما:** +**{format_money(meta['commodity_cost'])}**"
                )
                await context.bot.send_message(chat_id=seller["player_id"], text=seller_msg, parse_mode="Markdown")
            except Exception:
                pass

        keyboard = [
            [
                InlineKeyboardButton("📢 بله، انتشار در کانال اخبار", callback_data=f"market:pub_news:{order_id}:{t_mode}:yes"),
                InlineKeyboardButton("🔕 خیر، معامله محرمانه بماند", callback_data=f"market:pub_news:{order_id}:{t_mode}:no"),
            ],
            [InlineKeyboardButton("🏪 بازگشت به بورس کالا", callback_data="market:menu")],
            [InlineKeyboardButton("🌐 مشاهده وضعیت کشور", callback_data="country:back_profile")]
        ]

        await query.edit_message_text(result_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data.startswith("market:pub_news:"):
        parts = data.split(":")
        order_id = int(parts[2])
        t_mode = parts[3]
        choice = parts[4]

        if choice == "yes":
            order = db.get_market_order_by_id(order_id)
            buyer_c = country
            seller_c = db.get_country_by_id(order["seller_id"]) if order else None
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
            ],
            [InlineKeyboardButton("❌ انصراف و بازگشت", callback_data="market:menu")],
        ]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode="Markdown")

    elif data.startswith("market:sell_type:"):
        res_type = data.split(":")[2]
        context.user_data["market_sell_draft"] = {"step": "amount", "res_type": res_type}

        res_names = {"oil": "نفت خام", "gold": "شمش طلا", "grain": "غلات"}
        unit_names = {"oil": "بشکه", "gold": "شمش", "grain": "تن"}
        res_cols = {"oil": "oil_reserves", "gold": "gold", "grain": "grain"}

        curr_qty = country.get(res_cols[res_type], 0)

        text = (
            f"➕ **عرضه و فروش {res_names.get(res_type, res_type)}**\n"
            f"📦 **موجودی فعلی شما:** {curr_qty:,} {unit_names.get(res_type, '')}\n"
            "━━━━━━━━━━━━━━━━━━\n\n"
            f"لطفاً **مقدار و تعداد** مد نظر خود جهت فروش را به عدد انگلیسی ارسال فرمایید:"
        )

        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("❌ انصراف", callback_data="market:menu")]]), parse_mode="Markdown")

    elif data == "market:my_orders":
        my_orders = db.get_country_market_orders(country["id"])
        lines = [f"📦 **عرضه‌ها و سفارش‌های فعال کشور {country['flag']} {country['name']}**\n━━━━━━━━━━━━━━━━━━\n"]

        keyboard = []
        if not my_orders:
            lines.append("شما در حال حاضر هیچ عرضه فعالی در بورس کالا ندارید.")
        else:
            res_names = {"oil": "نفت", "gold": "طلا", "grain": "غلات"}
            unit_names = {"oil": "بشکه", "gold": "شمش", "grain": "تن"}

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

        res_labels = {"oil": "🛢️ نفت خام (بشکه)", "gold": "🪙 طلا (شمش)", "grain": "🌾 غلات (تن)"}

        for r_type in ("oil", "gold", "grain"):
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

    text_input = update.message.text.strip().replace(",", "").replace("٬", "")
    if not text_input.isdigit():
        await update.message.reply_text("⛔ لطفاً فقط یک عدد صحیح انگلیسی ارسال فرمایید.", parse_mode="Markdown")
        return

    num_val = int(text_input)
    if num_val <= 0:
        await update.message.reply_text("⛔ مقدار واردشده باید بزرگتر از صفر باشد.", parse_mode="Markdown")
        return

    step = draft.get("step")
    res_type = draft.get("res_type")
    res_names = {"oil": "نفت خام", "gold": "شمش طلا", "grain": "غلات"}
    unit_names = {"oil": "بشکه", "gold": "شمش", "grain": "تن"}

    if step == "amount":
        res_cols = {"oil": "oil_reserves", "gold": "gold", "grain": "grain"}
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

        del context.user_data["market_sell_draft"]

        success, msg = db.create_market_order(country["id"], res_type, amount, unit_price)

        if not success:
            await update.message.reply_text(f"❌ **خطا در ثبت عرضه بورس:**\n\n{msg}", parse_mode="Markdown", reply_markup=get_main_keyboard(user_id))
            return

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
