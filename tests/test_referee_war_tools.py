# -*- coding: utf-8 -*-
"""انتقال بخش «جنگ و عملیات» به پنل داور — بدون ورودی‌های دستی اقتصادی.

قواعد:
* داور فعال: رول‌ها (لیست/بررسی/تأیید/رد/بایگانی) + ابزار تلفات از مسیر
  «گزارش آماده»، تاریخچه، جستجو، آمار و ارسال فاکتور.
* فقط مالک: ثبت دستی تکی تجهیزات، بازگردانی به موجودی، حذف گزارش.
"""

import asyncio

import config
import database as db
import handlers.losses as losses

OWNER = 700
REF = 701
PLAYER = 702


def _fresh(monkeypatch, tmp_path, name="warref.db"):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / name))
    db.init_db()
    monkeypatch.setattr(config, "ADMIN_IDS", [OWNER])
    db.add_referee(REF, OWNER)


class _Msg:
    text = ""

    def __init__(self):
        self.sent = []

    async def reply_text(self, text, **kw):
        self.sent.append(text)


class _Upd:
    def __init__(self):
        self.message = _Msg()


class _Ctx:
    def __init__(self):
        self.user_data = {}


# ─────────────────────────────────────────────────────────────────────────────
# دسترسی
# ─────────────────────────────────────────────────────────────────────────────

def test_allowed_semantics(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    assert losses._is_owner(OWNER) is True
    assert losses._allowed(OWNER) is True
    assert losses._allowed(REF) is True, "داور فعال باید به ابزار تلفات برسد"
    assert losses._allowed(PLAYER) is False
    db.remove_referee(REF, OWNER)
    assert losses._allowed(REF) is False, "داورِ خلع‌شده نباید دسترسی داشته باشد"


# ─────────────────────────────────────────────────────────────────────────────
# بستن مسیرهای دستی برای داور (در رفتار، نه فقط ظاهر)
# ─────────────────────────────────────────────────────────────────────────────

def test_ls_qty_blocked_for_referee(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    upd, ctx = _Upd(), _Ctx()
    ctx.user_data["admin_awaiting_input"] = {"type": "ls_qty", "cid": 1, "key": "x"}
    asyncio.run(losses.handle_losses_input(upd, ctx, REF, ctx.user_data["admin_awaiting_input"]))
    assert upd.message.sent and "⛔" in upd.message.sent[0]
    assert ctx.user_data["admin_awaiting_input"] is None, "وضعیت باید پاک شود تا حلقه نیفتد"


def test_ls_qty_owner_passes_gate(monkeypatch, tmp_path):
    _fresh(monkeypatch, tmp_path)
    upd, ctx = _Upd(), _Ctx()
    ctx.user_data["admin_awaiting_input"] = {"type": "ls_qty", "cid": 999_999, "key": "x"}
    asyncio.run(losses.handle_losses_input(upd, ctx, OWNER, ctx.user_data["admin_awaiting_input"]))
    # مالک از گیت رد می‌شود و به خطای «تجهیز/کشور یافت نشد» می‌رسد، نه گیت نقش
    assert upd.message.sent and "⛔" not in upd.message.sent[0]


# ─────────────────────────────────────────────────────────────────────────────
# سیم‌کشی پنل‌ها (بررسی سورس — همان سبک تست‌های پنل موجود)
# ─────────────────────────────────────────────────────────────────────────────

def test_referee_menu_has_war_tools():
    src = open("handlers/referee.py", encoding="utf-8").read()
    assert 'callback_data="admin:roleplays_hub"' in src
    assert 'callback_data="ls:menu"' in src
    # و هیچ ابزار دستی اقتصادی وارد پنل داور نشده
    for forbidden in ("ls:new", "ls:revert", "ls:del", "apply_cstat_delta",
                      "update_country_field", "grant_cash"):
        assert forbidden not in src, f"پنل داور نباید {forbidden} داشته باشد"


def test_losses_menu_is_role_aware():
    src = open("handlers/losses.py", encoding="utf-8").read()
    # گیت اصلی با _allowed (مالک یا داور) و گیت دستی با _is_owner
    assert "if not _allowed(user_id):" in src
    assert 'data.startswith("ls:revert:")' in src and "_is_owner" in src
    # دکمه‌ی ثبت دستی داخل شرط مالک است
    idx = src.index('callback_data="ls:new"')
    window = src[max(0, idx - 300):idx]
    assert "_is_owner" in window, "دکمه‌ی ثبت دستی باید فقط برای مالک رندر شود"


def test_admin_gate_allows_referee_only_for_roleplay_flow():
    src = open("handlers/admin.py", encoding="utf-8").read()
    assert "_ref_ok" in src and "db.is_referee(user_id)" in src
    for prefix in ("admin:roles:", "admin:show_role:", "admin:app_role:",
                   "admin:rej_role:", "admin:arch_role:"):
        assert prefix in src


def test_roleplay_decisions_are_logged():
    src = open("handlers/admin.py", encoding="utf-8").read()
    for action in ("roleplay_approved", "roleplay_rejected", "roleplay_archived"):
        assert action in src, f"تصمیم رول باید لاگ شود: {action}"


def test_text_router_feeds_ls_inputs_to_referee_handler():
    src = open("main.py", encoding="utf-8").read()
    assert 'startswith("ls_")' in src, "روتر ورودی متنی باید جریان‌های ls_ را به داور برساند"
    src_ref = open("handlers/referee.py", encoding="utf-8").read()
    assert "handle_losses_input" in src_ref
