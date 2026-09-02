# -*- coding: utf-8 -*-
"""
ماژول سیستم اخبار زنده جهانی و موتور رویدادها (Live Breaking News & Events Engine).
طراحی اخبار به سبک کانال‌های خبری فوری تلگرام: کوتاه، میدانی، ژورنالیستی، مبهم و هیجان‌انگیز بدون لو دادن دیتابیس یا اسامی.
"""

import datetime
import config


async def post_breaking_news(
    bot,
    news_title: str | None = None,
    news_body: str | None = None,
    event_category: str = "خبر فوری",
):
    """ارسال خبر فوری به کانال رسمی تلگرام بازی.

    ``event_category`` و نام پارامترهای ``news_title``/``news_body`` برای
    سازگاری با فراخوانی‌های قدیمی نگه داشته شده‌اند. نسخه‌های جدید موتور
    می‌توانند عنوان و متن را به‌صورت positional ارسال کنند.
    """
    channel_id = config.get_channel_id()
    if not channel_id or not news_title or news_body is None:
        return False

    category_prefix = f"{event_category} / " if event_category else ""
    card_text_md = (
        f"🚨 **{category_prefix}{news_title}**\n\n"
        f"{news_body}\n\n"
        f"🆔 @SiasatModern"
    )

    card_text_plain = (
        f"🚨 {category_prefix}{news_title}\n\n"
        f"{news_body}\n\n"
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


# ─────────────────────────────────────────────────────────────────────────────
# شورش مسلحانه — متن‌ها بدون هیچ عددی؛ انتخاب نسخه با seed تا تکراری نشود
# ─────────────────────────────────────────────────────────────────────────────
import random as _ins_random

_INS_TEMPLATES = {
    "eruption": [
        ("شورش مسلحانه در {name} منفجر شد",
         "پس از روزها بحران، گروه‌های مسلح در چند شهر {flag} **{name}** کنترل بخش‌هایی از خیابان‌ها را به دست گرفتند؛ دولت وضعیت اضطراری اعلام کرد."),
    ],
    "escalation": [
        ("گسترش بی‌سابقه‌ی شورش در {name}",
         "منابع محلی از گسترش دامنه‌ی درگیری‌های مسلحانه در {flag} **{name}** خبر می‌دهند؛ نبرد از حاشیه‌ی شهرها به مرکز شهرها رسیده است."),
    ],
    "street_blockade": [
        ("خیابان‌های اصلی {name} مسدود شد",
         "شورشیان با آتش زدن لاستیک و سنگربندی، شریان‌های اصلی پایتخت {flag} **{name}** را بستند؛ ترافیک و تردد دولتی متوقف است."),
        ("پایتخت {name} فلج شد",
         "درگیری‌های پراکنده و باریکادهای خیابانی در {flag} **{name}**، دسترسی به نهادهای دولتی را تقریباً غیرممکن کرده است."),
    ],
    "general_strike": [
        ("اعتصاب سراسری در {name}",
         "بازارها، بانک‌ها و ادارات دولتی {flag} **{name}** در حمایت یا تحت فشار شورشیان تعطیل کردند؛ چرخه‌ی اقتصاد شهر متوقف است."),
    ],
    "police_post": [
        ("حمله‌ی مسلحانه به پاتک پلیس در {name}",
         "گروهی مسلح به پاتک پلیس در {flag} **{name}** حمله کرد؛ درگیری‌ها ساعت‌ها ادامه داشت و صدای انفجار در شهر شنیده می‌شد."),
    ],
    "refinery_sabotage": [
        ("حمله به تأسیسات نفتی {name}",
         "انفجار در مجتمع پالایشی {flag} **{name}** گزارش شد؛ بخشی از ظرفیت پالایش از دست رفته و شعله‌های آتش تا فاصله‌ی دور دیده می‌شود."),
    ],
    "grid_sabotage": [
        ("برق‌قطعی گسترده در {name}",
         "حمله‌ی شورشیان به شبکه‌ی انتقال برق، بخش بزرگی از {flag} **{name}** را در تاریکی فرو برد؛ وزارت انرژی از خرابکاری عمدی خبر داد."),
        ("تاریکی بر شهرهای {name} نشست",
         "خرابکاری در خطوط فشار قوی برق، بیمارستان‌ها و پمپ‌بنزین‌های {flag} **{name}** را نیز بلااستفاده کرده است."),
    ],
    "convoy_ambush": [
        ("کمین خونین بر کاروان دولتی در {name}",
         "کاروان تدارکاتی دولت در جاده‌ی حومه‌ی {flag} **{name}** هدف کمین مسلحانه قرار گرفت؛ محموله‌ها به دست شورشیان افتاد."),
    ],
    "border_post": [
        ("سقوط پاسگاه مرزی در {name}",
         "شورشیان پاسگاه مرزی در {flag} **{name}** را تصرف کردند؛ نگرانی از تسلیحات باقی‌مانده در پاسگاه بالا گرفته است."),
    ],
    "prison_raid": [
        ("حمله به زندان مرکزی {name}",
         "در حمله‌ی هماهنگ شورشیان به زندان مرکزی {flag} **{name}**، شمار زیادی از زندانیان فرار کردند؛ نیروهای امنیتی در حال پاک‌سازی هستند."),
    ],
    "urban_warfare": [
        ("نبرد سنگین خیابانی در {name}",
         "درگیری‌های سنگین خیابانی در محله‌های حاشیه‌ای {flag} **{name}** جریان دارد؛ دولت از مردم خواست در خانه‌ها بمانند."),
        ("شهرهای {name} میدان جنگ شدند",
         "توپخانه‌ی سبک و رگبار مسلسل در کوچه‌های {flag} **{name}** شنیده می‌شود؛ ستون‌های دود بر فراز شهر بالا می‌رود."),
    ],
    "base_rocket_fire": [
        ("موشک‌باران پایگاه ارتش در {name}",
         "چند راکت به سوی پایگاه نظامی دولت در {flag} **{name}** شلیک شد؛ انفجارهای پیاپی پایگاه را لرزاند."),
    ],
    "airport_attempt": [
        ("حمله به فرودگاه بین‌المللی {name}",
         "شورشیان به فرودگاه {flag} **{name}** یورش بردند؛ پروازها لغو شد و ترمینال‌ها تخلیه شدند."),
    ],
    "finale_fail": [
        ("دفع حمله‌ی بزرگ به قلب {name}",
         "حمله‌ی گسترده‌ی شورشیان به کانون قدرت در {flag} **{name}** با مقاومت سنگین گارد دولتی روبرو شد و عقب رانده شد؛ شهر در آتش است."),
    ],
    "betrayal": [
        ("آتش‌بس در {name} شکست",
         "تنها چند شب پس از توافق، شورشیان آتش‌بس را با حمله‌ی برق‌آسا در {flag} **{name}** شکستند؛ دولت آن را «خیانت آشکار» خواند."),
    ],
    "hostage": [
        ("گروگان‌گیری یک فرمانده در {name}",
         "شورشیان یکی از فرماندهان ارشد دولتی {flag} **{name}** را ربودند؛ خانواده‌ی او از مذاکره برای آزادی‌اش خبر دادند."),
    ],
    "grain_depot": [
        ("یورش به انبار غلات {name}",
         "گروهی مسلح به بزرگ‌ترین انبار غلات {flag} **{name}** حمله کرد؛ آتش‌سوزی بخشی از ذخایر گندم را بلعید و نگرانی از کمبود آذوقه بالا گرفته است."),
        ("ذخایر آذوقه {name} در آتش سوخت",
         "شورشیان شبانه به انبار غلات دولت در {flag} **{name}** یورش بردند؛ مقام‌های محلی از نابودی بخش بزرگی از ذخیره‌ی گندم خبر دادند."),
    ],
    "fuel_depot": [
        ("حمله به مخازن سوخت {name}",
         "انفجار در مخازن سوخت {flag} **{name}** گزارش شد؛ صف طولانی در پمپ‌بنزین‌ها شکل گرفته و دولت از محدودیت سهمیه‌ای خبر داد."),
        ("آتش به مخازن سوخت {name} رسید",
         "حمله‌ی مسلحانه به پایگاه توزیع سوخت در {flag} **{name}**، بخشی از ذخایر نفت کشور را از بین برد."),
    ],
    "bank_raid": [
        ("سرقت مسلحانه از بانک‌های {name}",
         "شورشیان شعبه‌ی مرکزی بانک دولتی در {flag} **{name}** را زدند؛ گفته می‌شود مقادیر زیادی اسکناس و شمش به غنیمت گرفته‌اند."),
        ("بانک‌های {name} تعطیل شدند",
         "پس از حمله‌ی مسلحانه به نظام بانکی {flag} **{name}**، همه‌ی شعبه‌ها تا اطلاع ثانوی بسته شدند."),
    ],
    "factory_raid": [
        ("توقف خطوط تولید در {name}",
         "حمله‌ی شورشیان به یک مجتمع صنعتی در {flag} **{name}** خسارت سنگینی وارد کرد؛ کارگران می‌گویند راه‌اندازی مجدد هفته‌ها طول می‌کشد."),
        ("کارخانه‌ای دیگر در {name} از کار افتاد",
         "یورش مسلحانه به کارخانه‌ی دولتی در {flag} **{name}**، یکی از واحدهای تولیدی کشور را کاملاً از رده خارج کرد."),
    ],
    "camp_raid": [
        ("حمله‌ی برق‌آسا به اردوگاه نظامی {name}",
         "شورشیان اردوگاه ارتش در حومه‌ی {flag} **{name}** را غافلگیر کردند؛ درگیری سنگین گزارش شده و آمبولانس‌ها پیاپی در رفت‌وآمدند."),
        ("پایگاه نظامی {name} به لرزه افتاد",
         "حمله‌ی گسترده‌ی شورشیان به تجمع نیروهای دولتی در {flag} **{name}**، تلفات نظامی قابل توجهی بر جای گذاشت."),
    ],
    "foiled_raid": [
        ("حمله‌ی شورشیان در {name} خنثی شد",
         "نیروهای امنیتی {flag} **{name}** پیش از رسیدن شورشیان به هدفشان، کمینشان را لو دادند و حمله در نطفه خفه شد."),
        ("شب بی‌خبری برای {name}",
         "تدابیر امنیتی دولت در {flag} **{name}** جواب داد؛ حمله‌ی شورشیان شکست خورد و چند تن از مهاجمان دستگیر شدند."),
    ],
    "finale_win": [
        ("سقوط قلب قدرت در {name}",
         "گفته می‌شود نیروهای شورشی کنترل مهم‌ترین نهاد حکومتی {flag} **{name}** را در دست گرفته‌اند؛ محل استقرار دولت نامعلوم است و کشور وارد دوران گذار شده است."),
    ],
}


_UN_SANCTION_TEMPLATES = {
    "imposed": [
        ("شورای امنیت {name} را هدف قرار داد",
         "شورای امنیت سازمان ملل تحریم‌های تازه‌ای علیه {flag} **{name}** تصویب کرد؛ دبیرکل این اقدام را «پیام روشن جامعه‌ی جهانی» خواند."),
        ("تحریم‌های تازه علیه {name}",
         "در نشست شبانه‌ی شورای امنیت، بسته‌ی تازه‌ای از تحریم‌ها علیه {flag} **{name}** به تصویب رسید؛ دیپلمات‌ها از تشدید فشارها خبر می‌دهند."),
    ],
    "lifted": [
        ("آرامش پس از تحریم؛ شورای امنیت {name} را آزاد کرد",
         "شورای امنیت سازمان ملل بخشی از تحریم‌های علیه {flag} **{name}** را لغو کرد؛ ناظران آن را آغاز بازگشت این کشور به اقتصاد جهانی می‌دانند."),
    ],
}


async def trigger_un_targeted_sanction_news(bot, country: dict, sanction_label: str, imposed: bool):
    """خبر اعمال/لغو تحریم هدفمند سازمان ملل — بدون عدد، انتخاب نسخه با seed."""
    name = country.get("name") or "یک کشور"
    flag = country.get("flag") or ""
    rng = _ins_random.Random(f"unsanc|{name}|{sanction_label}|{imposed}")
    key = "imposed" if imposed else "lifted"
    headline, body = rng.choice(_UN_SANCTION_TEMPLATES[key])
    await post_breaking_news(bot, headline.format(name=name), body.format(name=name, flag=flag),
                             event_category=f"شورای امنیت | {sanction_label}")


_UN_VIOLATION_TEMPLATES = [
    ("کشف محموله نقض تحریم؛ سایه سنگین شورای امنیت",
     "منابع اطلاعاتی از توقیف محموله‌ای از سلاح در مسیر نقض تحریم تسلیحاتی شورای امنیت خبر می‌دهند؛ نام چند کشور در اسناد محرمانه آمده است."),
    ("قاچاق سلاح زیر رادار شورا لو رفت",
     "یکی دیگر از محموله‌های قاچاق که قصد دور زدن تحریم تسلیحاتی سازمان ملل را داشت، در میانه‌ی راه شناسایی و توقیف شد؛ رسوایی دیپلماتیک تازه در راه است."),
]


async def trigger_un_sanction_violation_news(bot, sender: dict, receiver: dict):
    """خبر لو رفتن نقض تحریم تسلیحاتی سازمان ملل — بدون عدد."""
    s_name = sender.get("name") or "یک کشور"
    r_name = receiver.get("name") or "یک کشور"
    rng = _ins_random.Random(f"unviol|{s_name}|{r_name}")
    headline, body = rng.choice(_UN_VIOLATION_TEMPLATES)
    await post_breaking_news(bot, headline, body, event_category="شورای امنیت | نقض تحریم")


async def trigger_insurgency_news(bot, ev: dict):
    """خبر خودکار شورش — نسخه‌ی متن بر اساس seed تا هر شب متفاوت باشد."""
    name = ev.get("country_name") or "یک کشور"
    flag = ev.get("country_flag") or ""
    seed = str(ev.get("seed") or 0) + str(ev.get("kind"))
    rng = _ins_random.Random(seed)
    key = ev.get("kind")
    if key == "escalation":
        key = {2: "street_blockade", 3: "urban_warfare", 4: "finale_fail"}.get(
            int(ev.get("phase") or 2), "urban_warfare")
    tpl = _INS_TEMPLATES.get(key) or _INS_TEMPLATES["street_blockade"]
    headline, body = rng.choice(tpl)
    await post_breaking_news(
        bot,
        headline.format(name=name),
        body.format(name=name, flag=flag),
        event_category="شورش داخلی",
    )



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

