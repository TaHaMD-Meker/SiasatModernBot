# -*- coding: utf-8 -*-
"""
ماژول سیستم اخبار زنده جهانی و موتور رویدادها (Live Breaking News & Events Engine).
طراحی اخبار به سبک کانال‌های خبری فوری تلگرام: کوتاه، میدانی، ژورنالیستی، مبهم و هیجان‌انگیز بدون لو دادن دیتابیس یا اسامی.
"""

import datetime
import config


async def post_breaking_news(bot, headline: str, body_text: str):
    """ارسال خبر فوری به کانال رسمی تلگرام بازی به سبک کانال‌های خبری."""
    channel_id = config.get_channel_id()
    if not channel_id:
        return False

    card_text_md = (
        f"🚨 **فوری / {headline}**\n\n"
        f"{body_text}\n\n"
        f"🆔 @SiasatModern"
    )

    card_text_plain = (
        f"🚨 فوری / {headline}\n\n"
        f"{body_text}\n\n"
        f"🆔 @SiasatModern"
    )

    try:
        await bot.send_message(chat_id=channel_id, text=card_text_md, parse_mode="Markdown")
        return True
    except Exception as e1:
        print(f"Failed to post breaking news (Markdown) to channel {channel_id}: {e1}")
        try:
            await bot.send_message(chat_id=channel_id, text=card_text_plain)
            return True
        except Exception as e2:
            print(f"Failed to post breaking news (Plain) to channel {channel_id}: {e2}")
            return False


async def trigger_general_broadcast(bot, message_text: str):
    """ارسال بیانیه یا پیام عمومی به کانال اخبار."""
    channel_id = config.get_channel_id()
    if not channel_id:
        return False
    try:
        await bot.send_message(chat_id=channel_id, text=message_text, parse_mode="Markdown")
        return True
    except Exception as ex:
        print(f"General broadcast error: {ex}")
        return False


async def trigger_pipeline_sabotage_news(bot, target_c: dict, attacker_c: dict = None):
    """انتشار خبر فوری انفجار در خطوط لوله و مخازن نفتی به سبک میدانی."""
    if attacker_c:
        headline = f"دستگیری تیم خرابکاری نفوذی در تأسیسات نفتی {target_c['name']}"
        body = (
            f"نیروهای امنیتی کشور {target_c['flag']} **{target_c['name']}** از خنثی‌سازی یک عملیات خرابکاری در خطوط لوله انتقال نفت و بازداشت چند مظنون نفوذی خبر دادند.\n"
            f"تحقیقات اولیه از ارتباط بازداشت‌شدگان با سرویس اطلاعاتی کشور {attacker_c['flag']} **{attacker_c['name']}** حکایت دارد."
        )
    else:
        headline = f"انفجار شدید در تأسیسات نفتی {target_c['name']}؛ ستون‌های دود بر فراز منطقه رویت شد"
        body = (
            f"منابع محلی از شنیده شدن صدای چند انفجار مهیب در نزدیکی خطوط لوله و مخازن نفتی کشور {target_c['flag']} **{target_c['name']}** خبر می‌دهند.\n"
            f"بر اساس گزارش‌های اولیه، آتش‌سوزی گسترده‌ای در منطقه رخ داده و نیروهای امدادی و امنیتی در حال اعزام هستند.\n\n"
            "هنوز هیچ گروه یا کشوری مسئولیت این حادثه را بر عهده نگرفته است."
        )

    await post_breaking_news(bot, headline, body)


async def trigger_commander_assassination_news(bot, target_c: dict, commander_title: str = "", attacker_c: dict = None):
    """انتشار خبر فوری حادثه امنیتی و ترور مقامات نظامی به سبک خبری بدون لو دادن جزئیات."""
    if attacker_c:
        headline = f"خنثی‌سازی سوءقصد مسلحانه و دستگیری تیم ترور در {target_c['name']}"
        body = (
            f"سرویس‌های امنیتی کشور {target_c['flag']} **{target_c['name']}** اعلام کردند یک هسته ترور مسلحانه وابسته به {attacker_c['flag']} **{attacker_c['name']}** را پیش از اقدام شناسایی و متلاشی کرده‌اند."
        )
    else:
        headline = f"حادثه امنیتی و تیراندازی سنگین در {target_c['name']}؛ اخبار ضد و نقیض از ترور یک مقام ارشد"
        body = (
            f"منابع خبری از وقوع یک عملیات سوءقصد مسلحانه و ترور هدفمند در پایتخت کشور {target_c['flag']} **{target_c['name']}** خبر می‌دهند.\n"
            f"تدابیر شدید امنیتی و پرواز بالگردها در منطقه برقرار شده و ستاد کل نیروهای مسلح این کشور حالت آماده‌باش اعلام کرده است.\n\n"
            "اخبار تکمیلی متعاقباً اعلام خواهد شد..."
        )

    await post_breaking_news(bot, headline, body)


async def trigger_scientist_assassination_news(bot, target_c: dict, attacker_c: dict = None):
    """انتشار خبر فوری ترور چهره‌های علمی و تحقیقاتی."""
    if attacker_c:
        headline = f"خنثی‌سازی عملیات ترور چهره‌های علمی در {target_c['name']}"
        body = (
            f"دستگاه ضدجاسوسی کشور {target_c['flag']} **{target_c['name']}** از دستگیری عوامل وابسته به {attacker_c['flag']} **{attacker_c['name']}** پیش از اجرای عملیات ترور خبر داد."
        )
    else:
        headline = f"ترور یکی از چهره‌های علمی و تحقیقاتی در {target_c['name']}"
        body = (
            f"گزارش‌های میدانی از حمله مسلحانه به خودروی یکی از پژوهشگران و چهره‌های کلیدی توسعه فناوری در کشور {target_c['flag']} **{target_c['name']}** حکایت دارد.\n"
            f"نیروهای امنیتی منطقه را مسدود کرده و تحقیقات درباره چگونگی این سوءقصد در جریان است."
        )

    await post_breaking_news(bot, headline, body)


async def trigger_blockade_news(bot, blockader_c: dict, target_c: dict):
    """انتشار خبر فوری آرایش جنگی و محاصره دریایی."""
    headline = f"آرایش جنگی ناوگان {blockader_c['name']} و محاصره دریایی بنادر {target_c['name']}"
    body = (
        f"رادارهای دریایی از استقرار ناودسته‌های رزمی کشور {blockader_c['flag']} **{blockader_c['name']}** در مبادی ورودی بنادر و خطوط مواصلاتی {target_c['flag']} **{target_c['name']}** خبر می‌دهند.\n"
        f"تردد کشتی‌های تجاری در این مسیرها متوقف گردیده است."
    )
    await post_breaking_news(bot, headline, body)


async def trigger_unblockade_news(bot, blockader_c: dict, target_c: dict, is_broken: bool = False):
    """انتشار خبر پایان محاصره دریایی."""
    if is_broken:
        headline = f"درگیری سنگین دریایی و شکسته شدن خطوط محاصره در بنادر {target_c['name']}"
        body = (
            f"نیروهای پدافند ساحلی و موشکی کشور {target_c['flag']} **{target_c['name']}** با آتش متراکم ضدکشتی، محاصره دریایی ناوگان {blockader_c['name']} را درهم شکستند."
        )
    else:
        headline = f"لغو محاصره دریایی و بازگشایی بنادر {target_c['name']}"
        body = (
            f"دولت {blockader_c['flag']} **{blockader_c['name']}** پایان محاصره دریایی و از سرگیری تردد در بنادر {target_c['name']} را اعلام کرد."
        )
    await post_breaking_news(bot, headline, body)


async def trigger_strait_news(bot, country: dict, strait_name: str, action_type: str, toll_str: str = ""):
    """انتشار خبر وضعیت تنگه‌های استراتژیک."""
    if action_type == "block":
        headline = f"مسدودسازی کامل و توقف ترانزیت در {strait_name} توسط {country['name']}"
        body = (
            f"یگان‌های دریایی کشور {country['flag']} **{country['name']}** تردد کلیه شناورهای تجاری در {strait_name} را متوقف و این آبراه راهبردی را مسدود اعلام کردند."
        )
    elif action_type == "toll":
        headline = f"وضع عوارض ترانزیت عبوری در {strait_name} توسط {country['name']}"
        body = (
            f"دولت {country['flag']} **{country['name']}** دریافت عوارض عبور ({toll_str}) برای شناورهای تجاری در {strait_name} را به اجرا گذاشت."
        )
    else:
        headline = f"بازگشایی و از سرگیری تردد آزاد در {strait_name}"
        body = (
            f"دولت {country['flag']} **{country['name']}** لغو محدودیت‌ها و بازگشایی کامل کشتیرانی آزاد در {strait_name} را رسماً اعلام نمود."
        )

    await post_breaking_news(bot, headline, body)


async def trigger_trade_news(bot, prop_c: dict, recip_c: dict, details_str: str = "", transport_mode: str = "sea"):
    """انتشار خبر ترانزیت یا پروازهای ترابری بین‌المللی."""
    if transport_mode == "air":
        headline = f"پروازهای ترابری سنگین هوایی بین {prop_c['name']} و {recip_c['name']}"
        body = (
            f"رادارهای منطقه‌ای پرواز چند فروند هواپیمای ترابری سنگین هوایی بین کشور {prop_c['flag']} **{prop_c['name']}** و {recip_c['flag']} **{recip_c['name']}** را ثبت کردند."
        )
    elif transport_mode == "land":
        headline = f"ترانزیت کاروان‌های زمینی تحت تدابیر امنیتی بین {prop_c['name']} و {recip_c['name']}"
        body = (
            f"حرکت کاروان‌های ترانزیت زمینی تحت مراقبت‌های ویژه بین مرزهای {prop_c['flag']} **{prop_c['name']}** و {recip_c['flag']} **{recip_c['name']}** مشاهده گردید."
        )
    else:
        headline = f"ترانزیت کاروان‌های تجاری دریایی بین {prop_c['name']} و {recip_c['name']}"
        body = (
            f"تردد چند فروند کشتی ترابری و باری میان بنادر کشور {prop_c['flag']} **{prop_c['name']}** و {recip_c['flag']} **{recip_c['name']}** به ثبت رسید."
        )

    await post_breaking_news(bot, headline, body)


async def trigger_protest_news(bot, country: dict, reason: str):
    """انتشار خبر بروز ناآرامی و اعتصابات."""
    headline = f"اعتصابات گسترده و تجمعات اعتراضی در پایتخت {country['name']}"
    body = (
        f"به دلیل {reason} و شرایط دشوار معیشتی، تجمعات اعتراضی در خیابان‌های اصلی کشور {country['flag']} **{country['name']}** شکل گرفته است."
    )
    await post_breaking_news(bot, headline, body)



async def trigger_foiled_sabotage_news(bot, target_c: dict, op_type: str):
    """انتشار خبر فوری دفع و خنثی‌سازی عملیات خرابکاری یا ترور در کانال رسمی."""
    if op_type == "sabotage_pipeline":
        headline = f"کشف و خنثی‌سازی عملیات خرابکاری در تأسیسات نفتی {target_c['name']}"
        body = (
            f"دستگاه‌های امنیتی و پدافند غیرعامل کشور {target_c['flag']} **{target_c['name']}** از کشف و خنثی‌سازی یک اقدام خرابکارانه در تأسیسات و خطوط انتقال نفت پیش از هرگونه وقوع حادثه خبر دادند.\n"
            f"تأسیسات نفتی در امنیت کامل به فعالیت خود ادامه می‌دهند و تحقیقات برای شناسایی عاملان آغاز شده است."
        )
    elif op_type == "assassination_commander":
        headline = f"خنثی‌سازی سوءقصد مسلحانه علیه مقامات نظامی در {target_c['name']}"
        body = (
            f"منابع امنیتی در کشور {target_c['flag']} **{target_c['name']}** اعلام کردند یک اقدام تروریستی با هوشیاری تیم‌های حفاظت با شکست مواجه و خنثی گردید.\n"
            f"تمامی مقامات ارشد نظامی در سلامت کامل به سر می‌برند."
        )
    elif op_type == "assassination_scientist":
        headline = f"ناکام ماندن سوءقصد به چهره‌های علمی در {target_c['name']}"
        body = (
            f"دستگاه‌های امنیتی کشور {target_c['flag']} **{target_c['name']}** از شناسایی و خنثی‌سازی یک طرح سوءقصد به پژوهشگران و دستگیری عوامل مشکوک در صحنه خبر دادند."
        )
    else:
        headline = f"خنثی‌سازی اقدام خرابکارانه امنیتی در {target_c['name']}"
        body = (
            f"دستگاه‌های امنیتی کشور {target_c['flag']} **{target_c['name']}** از کشف و دفع یک اقدام خرابکارانه مشکوک در زیرساخت‌ها خبر دادند."
        )

    await post_breaking_news(bot, headline, body)


async def trigger_inactivity_removal_news(bot, country: dict):
    """انتشار خبر تغییر دولت یا استعفای رهبر به دلیل عدم فعالیت و بیانیه."""
    headline = f"انحلال دولت و اعلام وضعیت فوق‌العاده در {country['name']}"
    body = (
        f"به دلیل عدم صدور بیانیه رسمی و رکود در مدیریت اجرایی کشور {country['flag']} **{country['name']}**، "
        f"کابینه دولت این کشور منحل اعلام گردید و فرآیند واگذاری به رهبری جدید آغاز شد.\n\n"
        f"🌐 این کشور هم‌اکنون برای تعیین رهبری جدید آزاد است."
    )
    await post_breaking_news(bot, headline, body)


async def trigger_smuggling_intercepted_news(bot, prop_c: dict, recip_c: dict, orig_c: dict, weapon_name: str, lost_amt: int):
    """انتشار خبر فوری افشا و توقیف محموله قاچاق سلاح در خطوط ترانزیتی بین‌المللی."""
    orig_flag = orig_c.get("flag", "🌐") if orig_c else "🌐"
    orig_name = orig_c.get("name", "کشور سازنده") if orig_c else "کشور سازنده"
    headline = f"کشف و توقیف محموله قاچاق اسلحه در خطوط ترانزیتی بین {prop_c['name']} و {recip_c['name']}"
    body = (
        f"🚨 سرویس‌های اطلاعاتی و گارد مرزی از ردگیری و توقیف یک شبکه قاچاق سلاح در مبادی ترانزیتی خبر دادند.\n\n"
        f"• مبدأ ارسال: {prop_c['flag']} **{prop_c['name']}**\n"
        f"• مقصد نهایی: {recip_c['flag']} **{recip_c['name']}**\n"
        f"• جنگ‌افزار کشف‌شده: **{lost_amt:,} قبضه/واحد {weapon_name}** ({orig_flag} ساخت {orig_name})\n\n"
        f"نیمی از این محموله قاچاق توقیف و منهدم گردید و پیگیری‌های حقوقی و امنیتی آغاز شده است."
    )
    await post_breaking_news(bot, headline, body)

