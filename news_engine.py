# -*- coding: utf-8 -*-
"""
ماژول سیستم اخبار زنده جهانی و موتور رویدادها (Live Breaking News & Events Engine)
اتصال مستقیم اخبار کانال تلگرام به تمام تحرکات بازی (محاصره دریایی، معاهدات سنگین، نبردها و اعتراضات مردمی).
"""

import datetime
import database as db
import config

async def post_breaking_news(bot, news_title: str, news_body: str, event_category: str = "خبر فوری"):
    """ارسال کارت خبر فوری به کانال رسمی تلگرام بازی."""
    
    channel_id = config.get_channel_id()
    if not channel_id:
        return False

    today_str = datetime.date.today().isoformat()

    card_text = (
        f"🚨 **«{event_category} — {news_title}»**\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f'> "{news_body}"\n\n'
        "━━━━━━━━━━━━━━━━━━\n"
        f"📌 خبرگزاری رسمی ژئوپلیتیک «سیاست مدرن» | {today_str}"
    )

    try:
        await bot.send_message(chat_id=channel_id, text=card_text, parse_mode="Markdown")
        return True
    except Exception as e:
        print(f"Failed to post breaking news to channel {channel_id}: {e}")
        return False


async def trigger_blockade_news(bot, blockader_c: dict, target_c: dict):
    """انتشار خبر فوری آغاز محاصره دریایی."""
    title = f"محاصره دریایی بنادر {target_c['name']} توسط {blockader_c['name']}"
    body = (
        f"یگان‌های ناوگان دریایی کشور {blockader_c['flag']} {blockader_c['name']} تمام خطوط مواصلاتی دریایی "
        f"و بنادر تجاری کشور {target_c['flag']} {target_c['name']} را زیر محاصره کامل دریایی قرار دادند.\n"
        f"این اقدام موجب قطع صادرات/واردات دریایی، افت ۱۵ درصدی رضایت عمومی و شکل‌گیری اعتراضات شهری در {target_c['name']} شده است."
    )
    await post_breaking_news(bot, title, body, "محاصره دریایی بین‌المللی")


async def trigger_unblockade_news(bot, blockader_c: dict, target_c: dict, is_broken: bool = False):
    """انتشار خبر فوری پایان یا شکست محاصره دریایی."""
    if is_broken:
        title = f"شکسته شدن محاصره دریایی {target_c['name']}"
        body = (
            f"نیروهای مدافع و موشکی کشور {target_c['flag']} {target_c['name']} با شلیک موشک‌های ضدکشتی ساحلی و عملیات زیردریایی، "
            f"محاصره دریایی تحمیل‌شده توسط {blockader_c['name']} را با موفقیت درهم شکستند."
        )
    else:
        title = f"پایان و لغو محاصره دریایی {target_c['name']}"
        body = (
            f"دولت {blockader_c['flag']} {blockader_c['name']} رسماً لغو محاصره دریایی بنادر کشور {target_c['name']} "
            "و بازگشایی مسیرهای ترانزیت دریایی را اعلام کرد."
        )
    await post_post_news(bot, title, body, "تحرکات ژئوپلیتیک")


async def trigger_trade_news(bot, prop_c: dict, recip_c: dict, details_str: str):
    """انتشار خبر فوری انعقاد معاهده بزرگ بین‌المللی."""
    title = f"امضای معاهده تجاری استراتژیک بین {prop_c['name']} و {recip_c['name']}"
    body = (
        f"نمایندگان دیپلماتیک دو کشور {prop_c['flag']} {prop_c['name']} و {recip_c['flag']} {recip_c['name']} "
        f"معاهده بزرگ اقتصادی و تجاری را امضا کردند.\nجزییات معاهده: {details_str}"
    )
    await post_breaking_news(bot, title, body, "معاهده بین‌المللی")


async def trigger_protest_news(bot, country: dict, reason: str):
    """انتشار خبر فوری بروز اعتراضات مردمی و ناآرامی‌های معیشتی."""
    title = f"موج اعتراضات مردمی و اعتصابات در {country['name']}"
    body = (
        f"به دلیل {reason} و افت رضایت عمومی به زام بحرانی، تظاهرات گسترده و صف‌های طولانی در شهرهای اصلی کشور {country['flag']} {country['name']} "
        "شکل گرفته است. گزارش‌ها از خروج تدریجی نیروها و موج جدید مهاجرت خبر می‌دهند."
    )
    await post_breaking_news(bot, title, body, "بحران اجتماعی")
