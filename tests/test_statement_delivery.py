# -*- coding: utf-8 -*-
"""بیانیه‌ای که بی‌صدا گم می‌شد.

گزارش بازیکن (تایلند): عکس بیانیه فرستاده می‌شد، نه خطایی می‌آمد، نه چیزی در
کانال منتشر می‌شد. علت: پرچم رهاشده‌ی یک منوی دیگر (مثلاً «ثبت رول») پیام را
می‌بلعید و روی پیام عکسی، `update.message.text.strip()` استثنا می‌داد.
"""

import asyncio
import types

import config
import database as db
import input_modes
from handlers import operations, statements


# ─────────────────────────────────────────────────────────────────────────────
# ابزارهای شبیه‌سازی تلگرام
# ─────────────────────────────────────────────────────────────────────────────

class FakeBot:
    def __init__(self, fail_html=False):
        self.photos = []
        self.messages = []
        self.fail_html = fail_html

    async def send_photo(self, chat_id, photo, caption=None, parse_mode=None):
        if self.fail_html and parse_mode:
            raise RuntimeError("Can't parse entities")
        self.photos.append({"chat_id": chat_id, "photo": photo, "caption": caption})

    async def send_video(self, chat_id, video, caption=None, parse_mode=None):
        self.photos.append({"chat_id": chat_id, "video": video, "caption": caption})

    async def send_message(self, chat_id, text=None, parse_mode=None, **kwargs):
        self.messages.append({"chat_id": chat_id, "text": text})


class FakeMessage:
    def __init__(self, text=None, caption=None, photo=False):
        self.text = text
        self.caption = caption
        self.caption_html = caption
        self.photo = [types.SimpleNamespace(file_id="photo_1")] if photo else []
        self.video = None
        self.animation = None
        self.video_note = None
        self.replies = []

    async def reply_text(self, text, **kwargs):
        self.replies.append(text)


class FakeUpdate:
    def __init__(self, message, user_id=77_001, username="thai_leader"):
        self.message = message
        self.effective_user = types.SimpleNamespace(id=user_id, username=username, first_name="Player")


class FakeContext:
    def __init__(self, bot, user_data=None):
        self.bot = bot
        self.user_data = user_data if user_data is not None else input_modes.ExclusiveInputUserData()


def _fresh(monkeypatch, tmp_path, name="stmt.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()
    db.set_setting("channel_id", "@TestChannel")


def _country(player_id=77_001):
    cid = db.create_country(player_id, "تایلند", "🇹🇭", country_key="thailand")
    return db.get_country_by_id(cid)


CAPTION = (
    "دولت پادشاهی تایلند تحرکات نظامی اخیر در مرزهای شرقی را محکوم می‌کند.\n"
    "ما از همه‌ی طرف‌ها می‌خواهیم به خویشتن‌داری پایبند بمانند.\n"
    "نیروهای مسلح در آماده‌باش کامل قرار گرفته‌اند."
)


# ─────────────────────────────────────────────────────────────────────────────
# ۱. قفل حالت ورودی
# ─────────────────────────────────────────────────────────────────────────────

def test_opening_a_new_input_mode_closes_the_previous_one():
    ud = input_modes.ExclusiveInputUserData()
    ud["roleplay_text_input"] = True
    ud["statement_input"] = {"type": "official_statement"}
    assert "roleplay_text_input" not in ud
    assert ud["statement_input"]["type"] == "official_statement"


def test_keys_of_the_same_flow_live_together():
    ud = input_modes.ExclusiveInputUserData()
    ud["diplomacy_input"] = {"step": "target"}
    ud["trade_draft"] = {"item": "oil"}
    assert "diplomacy_input" in ud and "trade_draft" in ud

    ud["militia_wiz"] = {"step": "name"}
    ud["vip_input"] = {"step": "awaiting_custom_title"}
    assert "militia_wiz" in ud and "vip_input" in ud
    assert "diplomacy_input" not in ud  # جریان قبلی بسته شد


def test_every_dispatcher_flag_is_registered():
    """هر پرچمی که main به آن نگاه می‌کند باید در جدول گروه‌ها باشد."""
    dispatcher_keys = {
        "start_country_search", "intel_search", "vip_input", "militia_wiz",
        "mv_input", "admin_awaiting_input", "diplomacy_input",
        "market_sell_draft", "un_draft", "roleplay_text_input", "statement_input",
    }
    assert dispatcher_keys <= set(input_modes.ALL_INPUT_KEYS)


# ─────────────────────────────────────────────────────────────────────────────
# ۲. هندلرها نباید روی پیام عکسی بترکند
# ─────────────────────────────────────────────────────────────────────────────

def test_role_handler_survives_a_photo_message(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "role_photo.db")
    _country()
    message = FakeMessage(caption=CAPTION, photo=True)
    context = FakeContext(FakeBot())
    context.user_data["roleplay_text_input"] = True
    # قبلاً اینجا AttributeError می‌داد و بازیکن هیچ پاسخی نمی‌گرفت
    asyncio.run(operations.operations_text_input_handler(FakeUpdate(message), context))
    assert message.replies, "هندلر رول باید دست‌کم یک پاسخ بدهد"


# ─────────────────────────────────────────────────────────────────────────────
# ۳. بیانیه واقعاً منتشر شود
# ─────────────────────────────────────────────────────────────────────────────

def test_statement_with_photo_reaches_the_channel(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "stmt_ok.db")
    _country()
    bot = FakeBot()
    context = FakeContext(bot)
    context.user_data["statement_input"] = {"type": "official_statement"}
    message = FakeMessage(caption=CAPTION, photo=True)

    asyncio.run(statements.statements_text_input_handler(FakeUpdate(message), context))

    assert bot.photos, "عکس بیانیه به کانال نرفت"
    assert bot.photos[0]["chat_id"] == "@TestChannel"
    assert any("منتشر" in r for r in message.replies), "به بازیکن تأیید انتشار داده نشد"
    assert db.get_country_statement_count_today(db.get_country_by_player(77_001)["id"]) == 1


def test_statement_falls_back_to_plain_text_when_html_fails(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "stmt_fallback.db")
    _country()
    bot = FakeBot(fail_html=True)
    context = FakeContext(bot)
    context.user_data["statement_input"] = {"type": "official_statement"}
    message = FakeMessage(caption=CAPTION, photo=True)

    asyncio.run(statements.statements_text_input_handler(FakeUpdate(message), context))
    assert bot.photos, "مسیر جایگزین بدون HTML هم نتوانست منتشر کند"


def test_long_statement_goes_out_as_media_plus_full_text(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "stmt_long.db")
    _country()
    bot = FakeBot()
    context = FakeContext(bot)
    context.user_data["statement_input"] = {"type": "official_statement"}
    long_caption = CAPTION + "\n" + ("متن تکمیلی بیانیه رسمی دولت. " * 80)
    message = FakeMessage(caption=long_caption, photo=True)

    asyncio.run(statements.statements_text_input_handler(FakeUpdate(message), context))
    assert bot.photos, "رسانه ارسال نشد"
    assert len(bot.photos[0]["caption"]) <= 1024
    assert any(m["chat_id"] == "@TestChannel" for m in bot.messages), "متن کامل بیانیه‌ی بلند ارسال نشد"


def test_stale_role_flag_no_longer_swallows_the_statement(monkeypatch, tmp_path):
    """سناریوی دقیق بازیکن: منوی رول باز مانده بود، بعد رفت سراغ بیانیه."""
    _fresh(monkeypatch, tmp_path, "stmt_stale.db")
    _country()
    context = FakeContext(FakeBot())
    context.user_data["roleplay_text_input"] = True      # منوی رول باز ماند
    context.user_data["statement_input"] = {"type": "official_statement"}  # بعد بیانیه

    assert "roleplay_text_input" not in context.user_data

    message = FakeMessage(caption=CAPTION, photo=True)
    asyncio.run(statements.statements_text_input_handler(FakeUpdate(message), context))
    assert context.bot.photos, "بیانیه باز هم به کانال نرفت"


def test_statement_without_photo_tells_the_player_why(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path, "stmt_nophoto.db")
    _country()
    context = FakeContext(FakeBot())
    context.user_data["statement_input"] = {"type": "official_statement"}
    message = FakeMessage(text=CAPTION)

    asyncio.run(statements.statements_text_input_handler(FakeUpdate(message), context))
    assert message.replies and "الزامی" in message.replies[0]
    assert not context.bot.photos


# ─────────────────────────────────────────────────────────────────────────────
# ۴. حالت ورودی کهنه (ویزارد نیمه‌کاره‌ی گروهک که توییت را می‌خورد)
# ─────────────────────────────────────────────────────────────────────────────

def test_input_mode_expires_after_half_an_hour():
    ud = input_modes.ExclusiveInputUserData()
    ud["militia_wiz"] = {"step": "hq"}
    ud[input_modes.OPENED_AT_KEY] = 0  # خیلی وقت پیش باز شده
    assert input_modes.drop_stale_input_modes(ud) is True
    assert "militia_wiz" not in ud


def test_a_fresh_input_mode_is_not_dropped():
    ud = input_modes.ExclusiveInputUserData()
    ud["militia_wiz"] = {"step": "hq"}
    assert input_modes.drop_stale_input_modes(ud) is False
    assert "militia_wiz" in ud


def test_stale_militia_wizard_no_longer_eats_a_tweet(monkeypatch, tmp_path):
    """سناریوی دقیق بازیکن تایلند: ویزارد گروهک باز مانده بود و متن توییت را برد گام ۴."""
    _fresh(monkeypatch, tmp_path, "tweet_wizard.db")
    _country()
    context = FakeContext(FakeBot())
    context.user_data["militia_wiz"] = {"step": "hq"}
    context.user_data["statement_input"] = {"type": "official_tweet"}

    assert "militia_wiz" not in context.user_data, "ویزارد گروهک هنوز باز است"

    message = FakeMessage(text="دولت تایلند شیوع ویروس را تحت کنترل دارد.")
    asyncio.run(statements.statements_text_input_handler(FakeUpdate(message), context))

    published = [m for m in context.bot.messages if m["chat_id"] == "@TestChannel"]
    assert published, "توییت به کانال نرفت"


# ─────────────────────────────────────────────────────────────────────────────
# ۵. پست کانال نباید وارد مسیر ورودی بازیکن شود
# ─────────────────────────────────────────────────────────────────────────────

def test_stale_check_survives_a_missing_user_data():
    """پست کانال user_data ندارد؛ نباید استثنا بدهد."""
    assert input_modes.drop_stale_input_modes(None) is False
    assert input_modes.clear_input_modes(None) == []


def test_text_input_handler_is_limited_to_private_chats():
    import inspect
    import main
    source = inspect.getsource(main.main)
    assert "filters.ChatType.PRIVATE" in source, "هندلر ورودی هنوز پست کانال را می‌گیرد"
    assert "if update.effective_user is None or context.user_data is None" in source


def test_error_handler_stays_silent_outside_private_chats():
    import inspect
    import main
    source = inspect.getsource(main.main)
    assert "in_private = chat is not None and chat.type == ChatType.PRIVATE and user is not None" in source
    assert "if message is not None and in_private:" in source
