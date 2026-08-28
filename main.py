# -*- coding: utf-8 -*-
"""
فایل اصلی اجرای بات «سیاست مدرن».
پشتیبانی از دکمه‌های ثابت پایین صفحه، سیستم دارایی‌های اختصاصی نظامی (Country Assets) و پنل ادمین.
اجرا: python main.py
"""

import os
import asyncio
import datetime
import logging
from zoneinfo import ZoneInfo
import telegram.error

from telegram import Update
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
)

import config
import database as db
import approval_system
import news_engine
from utils import format_money, format_number, format_oil, get_main_keyboard
from handlers.nuclear import nuclear_main_menu, nuclear_callback_handler
from handlers.intel import intel_main_menu, intel_callback_handler
from handlers.bases import military_movements_menu
from handlers.start import get_start_handlers, start_country_search_input_handler
from handlers.country import country_profile, treasury, oil, army, help_command, approval_command, country_callback_handler
from handlers.diplomacy import diplomacy_menu, diplomacy_callback_handler, diplomacy_text_input_handler
from handlers.operations import operations_menu, operations_callback_handler, operations_text_input_handler
from handlers.statements import statements_menu, statements_callback_handler, statements_text_input_handler
from handlers.research import research_menu, research_callback_handler
from handlers.assets import show_assets_menu, get_assets_handlers
from handlers.market import market_main_menu, market_text_input_handler, get_market_handlers
from handlers.un import un_main_menu, un_text_input_handler, get_un_handlers
from handlers.shop import (
    shop, show_category, show_military_asset_category, back_to_shop,
    confirm_asset_purchase, execute_asset_purchase,
    confirm_civilian_purchase, execute_civilian_purchase,
    execute_warhead_assembly, npt_actions_handler
)
from handlers.admin import (
    admin_panel, admin_callback_handler, admin_input_text_handler,
    addmoney, removemoney, listcountries
)
from handlers.losses import get_losses_handlers
from handlers.bases import get_bases_handlers, mv_text_input_handler
from handlers.guide import get_guide_handlers
from handlers.vip import get_vip_handlers, vip_input_handler, vip_main_menu
from handlers.battlepass import get_battlepass_handlers, battlepass_menu
from handlers.tournament import get_tournament_handlers, tournament_menu
from handlers.internal_affairs import get_domestic_handlers, domestic_menu
import tournament_system as tournament
import internal_affairs

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


INCOME_INTERVAL_HOURS = 6
INCOME_PARTS = 4
# گرید پرداخت به وقت ایران: بازه‌های ۰۳:۰۰، ۰۹:۰۰، ۱۵:۰۰، ۲۱:۰۰ تهران
try:
    from zoneinfo import ZoneInfo
    IRAN_TZ = ZoneInfo("Asia/Tehran")
except Exception:
    IRAN_TZ = datetime.timezone(datetime.timedelta(hours=3, minutes=30))
SLOT_OFFSET_HOURS = 3


def _iran_slot_key(dt_utc):
    """شناسه‌ی بازه‌ی ۶ ساعته به وقت ایران."""
    local = dt_utc.astimezone(IRAN_TZ)
    shifted = (local.hour - SLOT_OFFSET_HOURS) % 24
    return f"{local.date().isoformat()}_{shifted // 6}"


def _payout_due(last_raw, now_utc):
    """آیا پرداخت جدید لازم است؟ خروجی: (eligible, first_of_day)."""
    last_dt = None
    try:
        if len(last_raw) >= 19:
            last_dt = datetime.datetime.fromisoformat(last_raw)
        elif len(last_raw) == 10:
            last_dt = datetime.datetime.fromisoformat(last_raw + "T00:00:00+00:00")
    except Exception:
        last_dt = None
    if last_dt is None:
        return True, True
    local_now = now_utc.astimezone(IRAN_TZ)
    local_last = last_dt.astimezone(IRAN_TZ)
    first_of_day = local_last.date() != local_now.date()
    eligible = _iran_slot_key(last_dt) != _iran_slot_key(now_utc)
    return eligible, first_of_day


async def _notify_crisis_owner(context, country: dict, items: list):
    """اطلاع خصوصی به خود بازیکن — مستقل از اینکه کانال چه چیزی منتشر می‌کند.

    بازیکن باید همیشه از بحران کشورش خبردار شود، حتی وقتی کانال ساکت است.
    """
    player_id = country.get("player_id")
    if not player_id or not items:
        return
    lines = [f"🚨 <b>وضعیت داخلی {country.get('flag', '')} {country.get('name', '')}</b>", ""]
    for item in items[:6]:
        lines.append(f"<b>{item['title']}</b>")
        lines.append(item["body"])
        lines.append("")
    lines.append("برای واکنش: 🏛️ سیاست داخلی ← 🚨 بحران‌های فعال")
    try:
        await context.bot.send_message(chat_id=player_id, text="\n".join(lines), parse_mode="HTML")
    except Exception:
        pass


async def _publish_crisis_news(context, items: list):
    """انتشار اخبار بحران در کانال، با فیلتر و تجمیع.

    قبلاً هر رویداد هر کشور یک پیام جدا می‌شد و سر ساعت چرخه، کانال پر از خبر
    می‌شد. حالا پیش‌فرض فقط تغییر سطح بحران منتشر می‌شود و اگر تعدادش زیاد بود،
    به‌جای ده‌ها پیام، یک گزارش تجمیعی می‌رود.
    """
    if not items:
        return
    mode = internal_affairs.news_mode()
    if mode == "off":
        return
    if mode == "severity":
        items = [i for i in items if i["event"] in internal_affairs.SEVERITY_EVENTS]
    if not items:
        return

    async def _send(title, body):
        try:
            await news_engine.post_breaking_news(context.bot, title, body, "بحران داخلی")
            return True
        except Exception:
            logger.exception("Could not publish crisis news")
            return False

    if len(items) > internal_affairs.NEWS_DIGEST_THRESHOLD:
        digest = internal_affairs.build_news_digest(items)
        if digest and await _send(digest[0], digest[1]):
            for item in items:
                internal_affairs.mark_news_sent(item["crisis_id"], item["flag"])
        return

    for item in items:
        if await _send(item["title"], item["body"]):
            internal_affairs.mark_news_sent(item["crisis_id"], item["flag"])


async def daily_income_job(context: ContextTypes.DEFAULT_TYPE, force: bool = False):
    """پرداخت درآمد به‌صورت تقسیط‌شده: هر ۶ ساعت یک‌چهارم درآمد.

    چرخه‌ی مصرف/رضایت/مهاجرت و هزینه‌ی محاصره‌های دریایی فقط در اولین پرداختِ
    هر روز تقویمی اجرا می‌شود تا نرخ مصرف روزانه تغییر نکند.
    force=True (توزیع فوری ادمین): پرداخت کامل + اجرای چرخه روزانه.
    """
    now = datetime.datetime.now(datetime.timezone.utc)
    today = now.date().isoformat()
    countries = db.get_all_countries()

    updated_count = 0
    crisis_news_batch = []
    for c in countries:
        last_raw = c.get("last_income_date") or ""
        eligible, first_of_day = _payout_due(last_raw, now)
        if force:
            eligible = True
            first_of_day = True
        if not eligible:
            continue

        maint_info = db.calculate_country_maintenance_cost(c["id"])
        tax_income = c.get("tax_income", 0) or 0
        daily_income = c.get("daily_income", 0) or 0

        # ⚡ کمبود برق: واحدهای صنعتیِ بی‌برق تولید نمی‌کنند.
        # درآمد ذخیره‌شده دست نمی‌خورد؛ فقط پرداختِ این دوره کم می‌شود، پس
        # به‌محض ترمیم شبکه، درآمد خودبه‌خود برمی‌گردد.
        power_note = ""
        if internal_affairs.power_penalty_enabled():
            try:
                power = internal_affairs.power_status(c)
                if power["shortage"] and power["income_lost"] > 0:
                    daily_income = max(0, daily_income - power["income_lost"])
                    offline_units = sum(power["offline"].values())
                    power_note = (
                        f" — ⚡ کمبود برق: {offline_units} واحد صنعتی خاموش "
                        f"({format_money(power['income_lost'])}/روز از دست رفت)"
                    )
            except Exception:
                logger.exception("Power shortage calculation failed for country %s", c["id"])

        gross_income = daily_income + tax_income
        sanction_note = ""
        # 🚫 تحریم جامع سازمان ملل: درآمد روزانه کشور تحریمی کاهش می‌یابد
        if c.get("un_sanctioned") or 0:
            factor = getattr(config, "UN_SANCTION_INCOME_FACTOR", 0.5)
            gross_income = int(gross_income * factor)
            sanction_note = f" — 🚫 درآمد تحت تحریم جامع سازمان ملل ({int(factor * 100)}٪)"
        net_full = gross_income - maint_info["total_maint"]
        net_payment = net_full if force else int(net_full / INCOME_PARTS)
        gold_daily = c.get("gold_daily", 0) or 0
        gold_payment = gold_daily if force else int(gold_daily / INCOME_PARTS)
        chips_daily = c.get("microchips_daily", 0) or 0
        chips_payment = chips_daily if force else int(chips_daily / INCOME_PARTS)
        iron_daily = c.get("iron_ore_daily", 0) or 0
        iron_payment = iron_daily if force else int(iron_daily / INCOME_PARTS)
        u_daily = c.get("uranium_ore_daily", 0) or 0
        u_payment = u_daily if force else int(u_daily / INCOME_PARTS)
        fuel_daily = c.get("nuclear_fuel_daily", 0) or 0
        fuel_payment = fuel_daily if force else int(fuel_daily / INCOME_PARTS)
        med_daily = c.get("medical_isotopes_daily", 0) or 0
        med_payment = med_daily if force else int(med_daily / INCOME_PARTS)

        # 🛡 محافظ خزانه: هزینه نگهداری هرگز خزانه را منفی نمی‌کند.
        # (باقی‌مانده هزینه وقتی خزانه پر شود کسر نمی‌شود — ساده و غیرقابل سوءاستفاده)
        treasury_now = c.get("treasury", 0) or 0
        if net_payment < 0 and treasury_now + net_payment < 0:
            net_payment = -max(treasury_now, 0)

        db.adjust_treasury(c["id"], net_payment)
        db.adjust_gold(c["id"], gold_payment)
        if chips_payment > 0:
            db.adjust_microchips(c["id"], chips_payment)
        if iron_payment > 0:
            db.adjust_iron_ore(c["id"], iron_payment)
        if u_payment > 0:
            db.adjust_uranium_ore(c["id"], u_payment)
        if fuel_payment > 0:
            db.adjust_nuclear_fuel(c["id"], fuel_payment)
        if med_payment > 0:
            db.adjust_medical_isotopes(c["id"], med_payment)

        app_res = None
        if first_of_day:
            app_res = approval_system.process_daily_approval_and_emigration(c)
            # چرخه‌ی جمعیت پویا، مالیات، ناآرامی و بحران‌ها (پشت کلید ادمین، idempotent)
            try:
                cycle = internal_affairs.run_daily_cycle(db.get_country_by_id(c["id"]) or c, app_res)
                if cycle:
                    fresh = db.get_country_by_id(c["id"]) or c
                    news_items = internal_affairs.collect_news(fresh, cycle)
                    if news_items:
                        crisis_news_batch.extend(news_items)
                        await _notify_crisis_owner(context, fresh, news_items)
            except Exception:
                logger.exception("Internal affairs daily cycle failed for country %s", c["id"])
            # مصرف سوخت روزانه نیروهای مسلح (واقع‌گرایی اقتصادی)
            try:
                fuel_need = db.calculate_military_fuel_consumption(c["id"])
                if fuel_need > 0:
                    oil_now = c.get("oil_reserves") or 0
                    if oil_now >= fuel_need:
                        db.adjust_oil(c["id"], -fuel_need)
                    else:
                        # کسری سوخت → تنزل رضایت عمومی و افت آمادگی رزمی نیروهای مسلح
                        db.adjust_oil(c["id"], -oil_now)
                        new_app = max(0, (c.get("approval_rating") or 80) - 4)
                        new_readiness = max(10, (c.get("combat_readiness") or 80) - 5)
                        db.update_country_field(c["id"], "approval_rating", new_app)
                        db.update_country_field(c["id"], "combat_readiness", new_readiness)
            except Exception:
                pass

        tax_part = tax_income if force else int(tax_income / INCOME_PARTS)
        daily_part = daily_income if force else int(daily_income / INCOME_PARTS)
        maint_part = maint_info["total_maint"] if force else int(maint_info["total_maint"] / INCOME_PARTS)

        db.update_country_field(c["id"], "last_income_date", now.isoformat())
        if force:
            db.add_transaction(c["id"], "daily_income", f"توزیع فوری درآمد و مالیات (صنعتی: {format_money(daily_part)} + مالیات: {format_money(tax_part)} - ارتش: {format_money(maint_part)})", net_full)
        else:
            db.add_transaction(c["id"], "daily_income", f"واریز دوره‌ای درآمد و مالیات (صنعتی: {format_money(daily_part)} + مالیات: {format_money(tax_part)} - ارتش: {format_money(maint_part)}){sanction_note}{power_note}", net_payment)

        p_id = c.get("player_id")
        if p_id:
            try:
                # وضعیت بیانیه‌های روزانه و اخطار عدم فعالیت
                stmt_count = db.get_country_statement_count_today(c["id"])
                req_stmts = getattr(config, "REQUIRED_DAILY_STATEMENTS", 2)
                inact_paused = db.get_setting("inactivity_revocation_paused") == "1"

                if inact_paused:
                    stmt_status_section = f"\n\n📢 *وضعیت فعالیت امروز:* `{stmt_count} از {req_stmts}` بیانیه (🛡️ سیستم سلب مالکیت ساعت ۰۰:۰۰ موقتاً متوقف و مصونیت فعال است)."
                elif stmt_count >= req_stmts:
                    stmt_status_section = f"\n\n📢 *وضعیت فعالیت امروز:* ✅ `{stmt_count} از {req_stmts}` بیانیه/توییت ثبت شده (تکمیل شد)."
                else:
                    needed = req_stmts - stmt_count
                    stmt_status_section = (
                        f"\n\n⚠️ *هشدار فعالیت و بیانیه روزانه (الزامی):*\n"
                        f"• بیانیه‌های ثبت‌شده امروز شما: *{stmt_count} از {req_stmts}*\n"
                        f"⏳ *اخطار مهم:* جهت حفظ حاکمیت کشور، ثبت روزانه حداقل {req_stmts} بیانیه یا توییت رسمی الزامی است. "
                        f"شما نیاز به ثبت *{needed} بیانیه/توییت دیگر* دارید. در صورت عدم ثبت تا ساعت ۰۰:۰۰ بامداد به وقت ایران، کشور شما سلب مالکیت و آزاد خواهد شد!"
                    )

                if first_of_day and app_res is not None:
                    report_msg = approval_system.build_daily_country_report_message(
                        db.get_country_by_id(c["id"]),
                        app_res,
                        today,
                        payout={
                            "net_payment": net_payment,
                            "tax_part": tax_part,
                            "daily_part": daily_part,
                            "maint_part": maint_part,
                        },
                    )
                    report_msg += stmt_status_section
                else:
                    c2 = db.get_country_by_id(c["id"])
                    chips_line = f"\n• 💻 میکروچیپ: +{chips_payment:,} عدد" if chips_payment > 0 else ""
                    iron_line = f"\n• ⛏️ آهن و فولاد: +{iron_payment:,} تن" if iron_payment > 0 else ""
                    u_line = f"\n• ☢️ کیک زرد: +{u_payment:,} تن" if u_payment > 0 else ""
                    fuel_line = f"\n• 🧪 سوخت غنی‌شده: +{fuel_payment:,} ک‌گ" if fuel_payment > 0 else ""
                    report_msg = (
                        f"💵 *واریز دوره‌ای درآمد و مالیات — {c2['flag']} {c2['name']}*\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"• 💰 *مالیات وصول‌شده از شهروندان:* +{format_money(tax_part)}\n"
                        f"• 🏭 *درآمد پایه و کارخانجات:* +{format_money(daily_part)}\n"
                        f"• 🪖 *هزینه نگهداری نیروهای مسلح:* -{format_money(maint_part)}\n"
                        f"━━━━━━━━━━━━━━━━━━\n"
                        f"• 📥 *خالص واریز این نوبت به خزانه:* *{format_money(net_payment)}*\n"
                        f"• 🏦 *موجودی جدید خزانه:* {format_money(c2['treasury'])}\n"
                        f"• 🪙 طلا: +{gold_payment}{chips_line}{iron_line}{u_line}{fuel_line}\n\n"
                        f"_درآمدها در {INCOME_PARTS} پرداختِ روزانه (۰۹:۰۰، ۱۵:۰۰، ۲۱:۰۰، ۰۳:۰۰ به وقت ایران) واریز می‌شوند._"
                        f"{stmt_status_section}"
                    )
                await context.bot.send_message(chat_id=p_id, text=report_msg, reply_markup=get_main_keyboard(p_id), parse_mode="Markdown")
            except Exception as e:
                logger.warning(f"Could not send daily report to player {p_id}: {e}")

        updated_count += 1

    # 3.5. هزینه و اجاره روزانه پایگاه‌های برون‌مرزی — فقط یک بار در هر روز تقویمی (خارج از حلقه کشورها)
    if db.get_setting("base_cost_cycle_date") != today or force:
        db.set_setting("base_cost_cycle_date", today)
        try:
            base_events = db.process_base_daily_costs()
            for ev in base_events:
                o_pid = ev.get("owner_pid")
                h_pid = ev.get("host_pid")
                b_name = ev.get("base_name", "پایگاه")
                h_name = ev.get("host_name", "میزبان")
                o_name = ev.get("owner_name", "مالک")
                rent_val = ev.get("rent", 0)

                if ev.get("event") == "paid":
                    if o_pid and rent_val > 0:
                        try:
                            await context.bot.send_message(
                                chat_id=o_pid,
                                text=f"🏰 **پرداخت اجاره روزانه پایگاه نظامی:**\nمبلغ **{format_money(rent_val)}** بابت اجاره روزانه پایگاه «{b_name}» به کشور میزبان ({h_name}) پرداخت شد.",
                                parse_mode="Markdown"
                            )
                        except Exception:
                            pass
                    if h_pid and rent_val > 0:
                        try:
                            await context.bot.send_message(
                                chat_id=h_pid,
                                text=f"💰 **دریافت اجاره پایگاه نظامی:**\nمبلغ **{format_money(rent_val)}** بابت میزبانی از پایگاه «{b_name}» متعلق به {o_name} به خزانه کشور شما واریز گردید.",
                                parse_mode="Markdown"
                            )
                        except Exception:
                            pass
                elif ev.get("event") == "unpaid":
                    if o_pid:
                        try:
                            await context.bot.send_message(
                                chat_id=o_pid,
                                text=f"⚠️ **اخطار بحران پایگاه نظامی:**\nبه دلیل کسری موجودی خزانه، نفت یا غلات، هزینه روزانه پایگاه «{b_name}» پرداخت نشد! (روز {ev.get('days', 1)} از ۳ — در صورت عدم پرداخت تا ۳ روز، پایگاه منحل خواهد شد)",
                                parse_mode="Markdown"
                            )
                        except Exception:
                            pass
                elif ev.get("event") == "collapsed":
                    if o_pid:
                        try:
                            await context.bot.send_message(
                                chat_id=o_pid,
                                text=f"💥 **انحلال خودکار پایگاه نظامی برون‌مرزی:**\nپایگاه «{b_name}» به دلیل ۳ روز عدم تأمین هزینه‌ها منحل گردید و ادوات مستقر با ۲۵٪ خسارت به کشور بازگشتند.",
                                parse_mode="Markdown"
                            )
                        except Exception:
                            pass
        except Exception as e:
            logger.warning(f"Error processing base daily costs: {e}")

    # 4. هزینه روزانه محاصره‌های دریایی — فقط یک بار در هر روز تقویمی
    if db.get_setting("blockade_cycle_date") == today:
        active_blockades = []
    else:
        db.set_setting("blockade_cycle_date", today)
        active_blockades = db.get_all_active_blockades()
    for blk in active_blockades:
        b_id = blk["blockader_id"]
        t_id = blk["target_id"]
        b_c = db.get_country_by_id(b_id)
        t_c = db.get_country_by_id(t_id)

        if not b_c or not t_c:
            continue

        oil_cost = 100_000
        money_cost = 2_000_000

        # واقع‌گرایی: سوخت روزانه ناوگان محاصره‌گر از ذخایر نفت تأمین می‌شود (تولید روزانه مجانی نیست)
        if b_c["treasury"] < money_cost or (b_c.get("oil_reserves", 0) or 0) < oil_cost:
            db.lift_naval_blockade(b_id, t_id)
            # بازیابی رضایت عمومی هدف پس از پایان کامل محاصره
            if not db.is_country_blockaded(t_id):
                new_app = min(100, (t_c.get("approval_rating") or 80) + 15)
                db.update_country_field(t_id, "approval_rating", new_app)
            lift_msg = (
                f"⚓ **لغو خودکار محاصره دریایی!**\n\n"
                f"کشور {b_c['flag']} {b_c['name']} به دلیل عدم تامین سوخت روزانه (۱۰۰,۰۰۰ بشکه) و هزینه‌های نگهداری ناوگان ({format_money(money_cost)})، "
                f"مجبور به لغو محاصره دریایی کشور {t_c['flag']} {t_c['name']} گردید."
            )
            if b_c.get("player_id"):
                try: await context.bot.send_message(chat_id=b_c["player_id"], text=lift_msg, parse_mode="Markdown")
                except Exception: pass
            if t_c.get("player_id"):
                try: await context.bot.send_message(chat_id=t_c["player_id"], text=lift_msg, parse_mode="Markdown")
                except Exception: pass
            await news_engine.trigger_unblockade_news(context.bot, b_c, t_c, is_broken=False)
        else:
            db.adjust_treasury(b_id, -money_cost)
            db.adjust_oil(b_id, -oil_cost)
            db.add_transaction(b_id, "blockade_cost", f"هزینه روزانه محاصره بنادر {t_c['name']}", -money_cost)

    # 5. بررسی و بازگشایی خودکار تنگه‌ها در صورت انهدام ناوگان کشور کنترل‌کننده
    try:
        reopened = db.auto_check_and_reopen_straits_if_navy_destroyed()
        for r in reopened:
            owner = r["owner"]
            s_info = r["strait_info"]
            s_msg = (
                f"🌊 **لغو خودکار کنترل بر تنگه استراتژیک!**\n\n"
                f"کشور {owner['flag']} {owner['name']} به دلیل انهدام یا تضعیف ناوگان دریایی "
                f"(کمتر از ۵ شناور فعال یا ۱۰ میلیون دلار ارزش)، کنترل نظامی خود بر **{s_info['name']}** را از دست داد و این آبراه فوراً بازگشایی شد."
            )
            if owner.get("player_id"):
                try: await context.bot.send_message(chat_id=owner["player_id"], text=s_msg, parse_mode="Markdown")
                except Exception: pass
            await news_engine.trigger_strait_news(context.bot, owner, s_info["name"], "open")
    except Exception as e:
        logger.warning(f"Error checking strait reopening: {e}")

    # 6. هزینه روزانه عملیات و گشت رزمی برای تنگه‌های مسدودشده بین‌المللی (جلوگیری از اسپم انسداد)
    if db.get_setting("strait_blockade_cost_date") != today:
        db.set_setting("strait_blockade_cost_date", today)
        for owner_key, strait_info in db.STRAITS_MAPPING.items():
            s_key = strait_info["strait_key"]
            st_data = db.get_strait_status(s_key)
            if st_data.get("status") == "blocked":
                owner_c = db.get_country_by_key(owner_key)
                if not owner_c:
                    continue

                money_cost = 2_500_000
                oil_cost = 100_000
                s_name = strait_info["name"]

                if (owner_c.get("treasury") or 0) < money_cost or (owner_c.get("oil_reserves") or 0) < oil_cost:
                    db.set_strait_status(s_key, "open", 0)
                    lift_msg = (
                        f"🌊 **بازگشایی خودکار تنگه استراتژیک!**\n\n"
                        f"کشور {owner_c['flag']} {owner_c['name']} به دلیل عدم تأمین سوخت روزانه (۱۰۰,۰۰۰ بشکه) "
                        f"یا هزینه‌های گشت رزمی ({format_money(money_cost)})، کنترل نظامی بر **{s_name}** را متوقف و این آبراه فوراً بازگشایی شد."
                    )
                    if owner_c.get("player_id"):
                        try:
                            await context.bot.send_message(chat_id=owner_c["player_id"], text=lift_msg, parse_mode="Markdown")
                        except Exception:
                            pass
                    await news_engine.trigger_strait_news(context.bot, owner_c, s_name, "open")
                else:
                    db.adjust_treasury(owner_c["id"], -money_cost)
                    db.adjust_oil(owner_c["id"], -oil_cost)
                    db.add_transaction(
                        owner_c["id"],
                        "strait_blockade_cost",
                        f"هزینه روزانه گشت رزمی و ناوگان جهت انسداد {s_name}",
                        -money_cost
                    )

    # اخبار بحران یک‌جا و در پایان چرخه منتشر می‌شوند، نه کشور به کشور
    try:
        await _publish_crisis_news(context, crisis_news_batch)
    except Exception:
        logger.exception("Crisis news publishing failed")

    logger.info(f"درآمد روزانه، محاسبه رضایت عمومی و ارسال گزارش برای {updated_count} کشور انجام شد.")
    return updated_count


async def check_daily_inactivity_job(context: ContextTypes.DEFAULT_TYPE, force_date: str = None):
    """بررسی روزانه ساعت ۰۰:۰۰ به وقت ایران — سلب مالکیت کشورهایی که در روز گذشته کمتر از ۲ بیانیه داده‌اند."""
    now_utc = datetime.datetime.now(datetime.timezone.utc)
    now_tehran = now_utc.astimezone(IRAN_TZ)
    today_str = now_tehran.date().isoformat()
    yesterday_str = force_date or (now_tehran.date() - datetime.timedelta(days=1)).isoformat()

    # بررسی قفل/توقف سراسری سلب مالکیت توسط ادمین در پنل قفل‌ها
    if db.get_setting("inactivity_revocation_paused") == "1":
        logger.info("Midnight inactivity country revocation is currently paused by admin setting.")
        db.set_setting("last_inactivity_check_date", today_str)
        return

    last_checked = db.get_setting("last_inactivity_check_date")
    if not last_checked:
        # اولین اجرا روی سیستم: ذخیره امروز تا بازیکنان فعلی اشتباهاً حذف نشوند
        db.set_setting("last_inactivity_check_date", today_str)
        return

    if last_checked == today_str and not force_date:
        return  # بررسی تاریخ امروز قبلاً انجام شده است

    req_stmts = getattr(config, "REQUIRED_DAILY_STATEMENTS", 2)
    countries = db.get_all_countries()
    counts_map = db.get_all_country_statement_counts_for_date(yesterday_str)

    revoked_count = 0
    for c in countries:
        c_id = c["id"]
        p_id = c.get("player_id")
        c_key = c.get("country_key")

        # معافیت‌ها: ادمین‌ها، بازیگر سیستم، تست یا بدون بازیکن
        if not p_id or p_id in config.ADMIN_IDS or p_id <= 0 or c_key == "un":
            continue

        # مهلت برای ثبت‌نام‌های تازه: اگر دیروز بعد از ساعت ۱۲ ظهر یا امروز ثبت‌نام کرده، روز اول معاف است
        created_at_raw = c.get("created_at") or ""
        if created_at_raw:
            try:
                created_dt = datetime.datetime.fromisoformat(created_at_raw)
                created_date = created_dt.astimezone(IRAN_TZ).date().isoformat()
                if created_date == today_str or (created_date == yesterday_str and created_dt.astimezone(IRAN_TZ).hour >= 12):
                    continue
            except Exception:
                pass

        user_stmts = counts_map.get(c_id, 0)
        # بلیط بیانیه اضافه: اگر کمبود بیانیه داری و بلیط داری، خودکار مصرف میشه
        if user_stmts < req_stmts:
            try:
                c_full = db.get_country_by_id(c_id)
                stmt_tickets = (c_full.get("statement_tickets", 0) or 0) if c_full else 0
                if stmt_tickets > 0:
                    need = req_stmts - user_stmts
                    use = min(need, stmt_tickets)
                    db.update_country_field(c_id, "statement_tickets", max(0, stmt_tickets - use))
                    user_stmts += use
                    db.add_transaction(c_id, "ticket_use", f"🎫 استفاده خودکار از {use} بلیط بیانیه برای جلوگیری از سلب مالکیت", 0)
            except Exception:
                pass
        if user_stmts < req_stmts:
            flag = c.get("flag", "🏳️")
            name = c.get("name", "کشور")
            username = c.get("username") or ""

            # سلب مالکیت و حذف کشور
            db.delete_country_by_id(c_id)
            revoked_count += 1

            # ارسال اخطار و اطلاعیه به خود بازیکن
            revoke_msg = (
                f"🏛️ *سلب مالکیت کشور به دلیل عدم فعالیت روزانه*\n\n"
                f"کاربر گرامی،\n"
                f"به دلیل عدم ثبت حداقل {req_stmts} بیانیه یا توییت رسمی در روز گذشته ({yesterday_str})، "
                f"مالکیت کشور *{flag} {name}* از شما سلب شد و این کشور برای انتخاب مجدد سایر کاربران آزاد گردید.\n\n"
                f"• تعداد بیانیه‌های ثبت‌شده شما: *{user_stmts} از {req_stmts} بیانیه*\n\n"
                f"💡 *قوانین بازی:* جهت حفظ رهبری کشور، ثبت روزانه حداقل ۲ بیانیه یا توییت رسمی در ربات الزامی است."
            )
            try:
                await context.bot.send_message(chat_id=p_id, text=revoke_msg, parse_mode="Markdown")
            except Exception as e:
                logger.warning(f"Could not notify player {p_id} of country revocation: {e}")

            # اطلاع فوری به ادمین‌های بازی
            admin_note = (
                f"⚠️ *سلب مالکیت خودکار کشور به دلیل عدم فعالیت روزانه:*\n\n"
                f"• کشور: *{flag} {name}* (`{c_key}`)\n"
                f"• بازیکن: @{username} (شناسه: `{p_id}`)\n"
                f"• بیانیه‌های ثبت‌شده: *{user_stmts} از {req_stmts}*\n"
                f"• تاریخ بررسی: `{yesterday_str}`"
            )
            for adm in config.ADMIN_IDS:
                try:
                    await context.bot.send_message(chat_id=adm, text=admin_note, parse_mode="Markdown")
                except Exception:
                    pass

            # خبر فوری در کانال رسمی بازی
            try:
                await news_engine.trigger_inactivity_removal_news(context.bot, c)
            except Exception:
                pass

    db.set_setting("last_inactivity_check_date", today_str)
    if revoked_count:
        logger.info(f"Daily inactivity audit completed: {revoked_count} countries revoked.")


async def tournament_snapshot_job(context: ContextTypes.DEFAULT_TYPE):
    """ثبت snapshot دوره‌ای امتیازهای تورنومنت؛ در حالت بدون فصل هیچ کاری نمی‌کند."""
    try:
        updated = tournament.refresh_active_tournament(force=False)
        if updated:
            logger.info(f"Tournament scores refreshed for {updated} participant(s).")
    except Exception as exc:
        logger.exception(f"Tournament snapshot job failed: {exc}")


async def _handle_health_check(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    """پاسخ به هلث‌چک‌های HTTP پلتفرم‌های ابری (Railway / PaaS)."""
    try:
        await reader.read(1024)
        response = (
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: text/plain; charset=utf-8\r\n"
            "Content-Length: 2\r\n"
            "Connection: close\r\n\r\n"
            "OK"
        )
        writer.write(response.encode("utf-8"))
        await writer.drain()
    except Exception:
        pass
    finally:
        try:
            writer.close()
            await writer.wait_closed()
        except Exception:
            pass


async def on_post_init(application: Application):
    """راه‌اندازی سرور سبک بررسی سلامت و تضمین اتصال مستقیم به تلگرام."""
    if not config.BOT_TOKEN or config.BOT_TOKEN == "TOKEN_ATO_EINJA_BEZAR":
        logger.critical("⚠️ هشدار مهم: متغیر BOT_TOKEN در تنظیمات سرور (Railway Variables) ست نشده است!")
        return

    try:
        await application.bot.delete_webhook(drop_pending_updates=True)
        me = await application.bot.get_me()
        logger.info(f"✅ ربات با موفقیت به تلگرام متصل شد: @{me.username} (ID: {me.id})")
    except Exception as e:
        logger.error(f"❌ خطا در احراز هویت توکن تلگرام یا حذف وب‌هوک: {e}")

    port_str = os.environ.get("PORT")
    if port_str:
        try:
            port = int(port_str)
            server = await asyncio.start_server(_handle_health_check, "0.0.0.0", port)
            application.bot_data["health_server"] = server
            logger.info(f"Health check server listening on 0.0.0.0:{port} for Railway/PaaS")
        except Exception as e:
            logger.warning(f"Could not start health check server on port {port_str}: {e}")


async def on_post_shutdown(application: Application):
    """بستن سرور بررسی سلامت هنگام خاموش شدن بات."""
    server = application.bot_data.get("health_server")
    if server:
        server.close()
        try:
            await server.wait_closed()
        except Exception:
            pass


def main():
    db.init_db()

    # concurrent_updates: پردازش موازی پیام‌ها — یک درخواست کند (مثل تحلیل AI)
    # نباید بقیه‌ی بازیکن‌ها را در صف قفل کند
    app = (
        Application.builder()
        .token(config.BOT_TOKEN)
        .concurrent_updates(True)
        .post_init(on_post_init)
        .post_shutdown(on_post_shutdown)
        .build()
    )

    # هاندرهای ثبت‌نام و انتخاب کشور
    for handler in get_start_handlers():
        app.add_handler(handler)

    # سیستم دارایی‌های اختصاصی کشورها (/assets)
    for handler in get_assets_handlers():
        app.add_handler(handler)

    # دستورات متنی نمایش وضعیت کشور
    app.add_handler(CommandHandler("country", country_profile))
    app.add_handler(CommandHandler("approval", approval_command))
    app.add_handler(CommandHandler("treasury", treasury))
    app.add_handler(CommandHandler("oil", oil))
    app.add_handler(CommandHandler("army", army))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(country_callback_handler, pattern=r"^country:"))

    # دکمه‌های ثابت پایین صفحه (Reply Keyboard Text Handlers)
    app.add_handler(MessageHandler(filters.Regex("^🌐 وضعیت کشور$"), country_profile))
    app.add_handler(MessageHandler(filters.Regex("^📊 رضایت عمومی$"), approval_command))
    app.add_handler(MessageHandler(filters.Regex("^🎖️ دارایی‌های نظامی$"), show_assets_menu))
    app.add_handler(MessageHandler(filters.Regex("^🏦 خزانه و طلا$"), treasury))
    app.add_handler(MessageHandler(filters.Regex("^🛢️ وضعیت نفت$"), oil))
    app.add_handler(MessageHandler(filters.Regex("^🪖 وضعیت ارتش$"), army))
    app.add_handler(MessageHandler(filters.Regex("^🏪 فروشگاه$"), shop))
    app.add_handler(MessageHandler(filters.Regex(r"^(?:⭐️\s*بتل‌پس|⭐️\s*بتل پس|⭐️\s*بتل‌پس فصلی|⭐️\s*Battle Pass|/pass|/bp)$"), battlepass_menu))
    app.add_handler(MessageHandler(filters.Regex(r"^🏆 تورنومنت فصل$"), tournament_menu))
    app.add_handler(MessageHandler(filters.Regex(r"^🏛️ سیاست داخلی$"), domestic_menu))
    app.add_handler(MessageHandler(filters.Regex(r"^(?:💎\s*خدمات ویژه VIP|👑\s*خدمات VIP|💎\s*اشتراک VIP)$"), vip_main_menu))
    app.add_handler(MessageHandler(filters.Regex(r"^(?:🏛️ دانشکده|📜 راهنما)$"), help_command))
    app.add_handler(MessageHandler(filters.Regex("^👑 پنل مدیریت$"), admin_panel))
    app.add_handler(MessageHandler(filters.Regex(r"^(?:🎯 ستاد توسعه و اقدامات راهبردی|🎖️ تحرکات نظامی)$"), military_movements_menu))
    app.add_handler(CommandHandler(["movements", "bases", "strategic"], military_movements_menu))

    # فروشگاه (دکمه‌های شیشه‌ای)
    app.add_handler(CommandHandler("shop", shop))
    app.add_handler(CallbackQueryHandler(show_category, pattern=r"^shopcat:"))
    app.add_handler(CallbackQueryHandler(show_military_asset_category, pattern=r"^shop_asset_cat:"))
    app.add_handler(CallbackQueryHandler(back_to_shop, pattern=r"^shopback$"))
    app.add_handler(CallbackQueryHandler(confirm_asset_purchase, pattern=r"^confirm_asset_buy:"))
    app.add_handler(CallbackQueryHandler(execute_asset_purchase, pattern=r"^do_asset_buy:"))
    app.add_handler(CallbackQueryHandler(confirm_civilian_purchase, pattern=r"^buyciv:"))
    app.add_handler(CallbackQueryHandler(execute_civilian_purchase, pattern=r"^docivbuy:"))
    app.add_handler(CallbackQueryHandler(execute_warhead_assembly, pattern=r"^shop:do_assemble_warhead$"))
    app.add_handler(CallbackQueryHandler(npt_actions_handler, pattern=r"^shop:npt_"))

    # سیستم ابلاغ عملیات و رول‌های نظامی
    app.add_handler(CommandHandler("role", operations_menu))
    app.add_handler(CommandHandler("operation", operations_menu))
    app.add_handler(CommandHandler("ops", operations_menu))
    app.add_handler(CallbackQueryHandler(operations_callback_handler, pattern=r"^op:"))
    app.add_handler(MessageHandler(filters.Regex("^🎯 عملیات$"), operations_menu))

    # سیستم بیانیه‌ها، رسمی‌سازی متن و توییت‌ها
    app.add_handler(CommandHandler("statement", statements_menu))
    app.add_handler(CommandHandler("tweet", statements_menu))
    app.add_handler(CommandHandler("rewrite", statements_menu))
    app.add_handler(CallbackQueryHandler(statements_callback_handler, pattern=r"^stmt:"))
    app.add_handler(MessageHandler(filters.Regex("^📢 بیانیه و توییت$"), statements_menu))

    # سیستم تحقیق و توسعه و لول فناوری بومی
    app.add_handler(CommandHandler("research", research_menu))
    app.add_handler(CommandHandler("tech", research_menu))
    app.add_handler(CallbackQueryHandler(research_callback_handler, pattern=r"^research:"))

    # برنامه راهبردی هسته‌ای (/nuclear)
    app.add_handler(CommandHandler(["nuclear", "nuke"], nuclear_main_menu))
    app.add_handler(CallbackQueryHandler(nuclear_callback_handler, pattern=r"^nuc:"))

    # سازمان اطلاعات و جنگ سایبری (/intel)
    app.add_handler(CommandHandler(["intel", "mossad", "cia", "vaja", "commanders", "cyber"], intel_main_menu))
    app.add_handler(CallbackQueryHandler(intel_callback_handler, pattern=r"^intel:"))

    # سیستم دیپلماسی و معاهدات بین‌المللی
    app.add_handler(CommandHandler("diplomacy", diplomacy_menu))
    app.add_handler(CommandHandler("message", diplomacy_menu))
    app.add_handler(CommandHandler("trade", diplomacy_menu))
    app.add_handler(CommandHandler("aid", diplomacy_menu))
    app.add_handler(CommandHandler("relations", diplomacy_menu))
    app.add_handler(CallbackQueryHandler(diplomacy_callback_handler, pattern=r"^dip:"))
    app.add_handler(MessageHandler(filters.Regex("^🤝 دیپلماسی و روابط$"), diplomacy_menu))

    # پنل پیشرفته ادمین (مخصوص آیدی 8052987465)
    app.add_handler(CommandHandler(["admin", "panel"], admin_panel))
    app.add_handler(CallbackQueryHandler(admin_callback_handler, pattern=r"^admin:"))

    async def ignore_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.callback_query:
            try:
                await update.callback_query.answer()
            except Exception:
                pass

    app.add_handler(CallbackQueryHandler(ignore_callback, pattern=r"^ignore$"))

    # سیستم بازار بورس بین‌المللی کالاها (/market)
    for handler in get_market_handlers():
        app.add_handler(handler)

    # سیستم سازمان ملل متحد (/un)
    for handler in get_un_handlers():
        app.add_handler(handler)

    # سیستم مدیریت تلفات تجهیزات (ماژول مستقل)
    for handler in get_losses_handlers():
        app.add_handler(handler)

    # سیستم تحرکات نظامی (مانور + پایگاه‌های پیشروی)
    for handler in get_bases_handlers():
        app.add_handler(handler)

    # دانشکده و کتابخانه جامع راهنمای بازی (/help, /guide, /academy)
    for handler in get_guide_handlers():
        app.add_handler(handler)

    # سیستم خدمات ویژه و پرداخت‌های تومانی (/vip, /premium)
    for handler in get_vip_handlers():
        app.add_handler(handler)

    # سیستم بتل‌پس فصلی و کمپین‌های استراتژیک (/pass, /battlepass, /bp)
    for handler in get_battlepass_handlers():
        app.add_handler(handler)

    # سیستم تورنومنت فصلی با امتیازدهی ترکیبی (/tournament, /tour)
    # سیستم جمعیت پویا، مالیات، ناآرامی و بحران (/domestic)
    for handler in get_domestic_handlers():
        app.add_handler(handler)

    for handler in get_tournament_handlers():
        app.add_handler(handler)

    # دستورات متنی قدیمی ادمین
    app.add_handler(CommandHandler("addmoney", addmoney))
    app.add_handler(CommandHandler("removemoney", removemoney))
    app.add_handler(CommandHandler("listcountries", listcountries))

    # دریافت ورودی‌های متنی و تصویری (تایپی) ادمین، دیپلماسی، بورس، سازمان ملل، رول‌ها، بیانیه‌ها و فیش‌های VIP
    async def combined_text_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if context.user_data.get("start_country_search"):
            handled = await start_country_search_input_handler(update, context)
            if handled:
                return
        if context.user_data.get("intel_search"):
            from handlers.intel import intel_search_input_handler
            handled = await intel_search_input_handler(update, context)
            if handled:
                return
        if context.user_data.get("vip_input") or context.user_data.get("militia_wiz"):
            handled = await vip_input_handler(update, context)
            if handled:
                return
        if context.user_data.get("mv_input"):
            handled = await mv_text_input_handler(update, context)
            if handled:
                return
        if context.user_data.get("admin_awaiting_input"):
            await admin_input_text_handler(update, context)
        elif context.user_data.get("diplomacy_input"):
            await diplomacy_text_input_handler(update, context)
        elif context.user_data.get("market_sell_draft"):
            await market_text_input_handler(update, context)
        elif context.user_data.get("un_draft"):
            await un_text_input_handler(update, context)
        elif context.user_data.get("roleplay_text_input"):
            await operations_text_input_handler(update, context)
        elif context.user_data.get("statement_input"):
            await statements_text_input_handler(update, context)

    app.add_handler(MessageHandler((filters.TEXT | filters.PHOTO | filters.VIDEO | filters.ANIMATION | filters.VIDEO_NOTE) & ~filters.COMMAND, combined_text_input_handler))

    # مدیریت سراسری خطاها (جهت پایداری و عدم کرش بات در ترافیک بالا)
    async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
        err = context.error
        if isinstance(err, telegram.error.Conflict):
            logger.warning(f"Telegram Conflict error ignored: {err}")
            return
        elif isinstance(err, telegram.error.Forbidden):
            logger.info(f"Forbidden error ignored: {err}")
            return
        elif isinstance(err, telegram.error.RetryAfter):
            logger.warning(f"FloodControl: retry after {err.retry_after}s")
            return
        elif isinstance(err, (telegram.error.TimedOut, telegram.error.NetworkError)):
            logger.warning(f"Network transient error: {err}")
            return
        elif isinstance(err, telegram.error.BadRequest):
            logger.warning(f"Telegram BadRequest ignored: {err}")
            return
        logger.error(f"Unhandled error in bot: {err}", exc_info=err)

    app.add_error_handler(global_error_handler)

    # جاب پشتیبان‌گیری خودکار از دیتابیس
    async def auto_backup_job(context: ContextTypes.DEFAULT_TYPE):
        ok, res = db.backup_database()
        if ok:
            logger.info(f"Database auto-backup created: {res}")
        else:
            logger.warning(f"Database auto-backup failed: {res}")

    # جاب‌ها: درآمد روزانه، پشتیبان‌گیری دوره‌ای و بررسی فعالیت نیمه‌شب (۰۰:۰۰)
    job_queue = app.job_queue
    if job_queue:
        job_queue.run_repeating(daily_income_job, interval=900, first=10)  # چک هر ۱۵ دقیقه؛ پرداخت هر ۶ ساعت
        job_queue.run_repeating(tournament_snapshot_job, interval=900, first=180)  # محاسبه‌ی دوره‌ای؛ خود ماژول فاصله‌ی ۶ ساعته را enforce می‌کند
        job_queue.run_repeating(auto_backup_job, interval=14400, first=120)  # پشتیبان‌گیری خودکار هر ۴ ساعت
        job_queue.run_repeating(check_daily_inactivity_job, interval=300, first=30)  # بررسی سلب مالکیت روزانه ۰۰:۰۰ (چک هر ۵ دقیقه)

    logger.info("بات در حال اجراست...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)


if __name__ == "__main__":
    import time
    while True:
        try:
            main()
            break
        except KeyboardInterrupt:
            logger.info("بات توسط کاربر متوقف شد.")
            break
        except Exception as e:
            logger.critical(f"خطای بحرانی در اجرای بات: {e}. راه‌اندازی مجدد در ۵ ثانیه...", exc_info=e)
            time.sleep(5)