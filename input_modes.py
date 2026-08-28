# -*- coding: utf-8 -*-
"""حالت‌های ورودی متنی و قانون «هر لحظه فقط یک حالت باز است».

مشکلی که این ماژول حل می‌کند:
بازیکن روی «ثبت رول تهاجمی» می‌زد، متن نمی‌فرستاد و بعد می‌رفت سراغ «بیانیه و توییت».
پرچم `roleplay_text_input` هنوز روشن بود و چون در زنجیره‌ی `elif` جلوتر از
`statement_input` بررسی می‌شد، عکسِ بیانیه به هندلر رول می‌رفت. آنجا کد روی
`update.message.text.strip()` می‌افتاد که برای پیام عکسی None است، استثنا می‌داد و
بازیکن **هیچ پاسخی** نمی‌گرفت و بیانیه هم هرگز به کانال نمی‌رسید.

راه‌حل ریشه‌ای: به‌جای وصله‌زدن ۷۳ نقطه‌ای که پرچم می‌گذارند، نوع دیکشنری
`user_data` عوض می‌شود؛ لحظه‌ای که یک حالت ورودی جدید ست می‌شود، حالت‌های دیگر
خودبه‌خود پاک می‌شوند.
"""
from __future__ import annotations

import time

# هر گروه، مجموعه کلیدهایی است که با هم و در یک جریان کار می‌کنند.
INPUT_MODE_GROUPS: dict[str, tuple[str, ...]] = {
    "statement": ("statement_input",),
    "operations": ("roleplay_text_input", "role_submit_draft"),
    "diplomacy": ("diplomacy_input", "aid_draft", "trade_draft", "mil_draft"),
    "admin": ("admin_awaiting_input",),
    "market": ("market_sell_draft",),
    "un": ("un_draft",),
    "vip": ("vip_input", "militia_wiz", "vip_pending_plan", "vip_custom_payload"),
    "movements": ("mv_input", "mv_search_host"),
    "intel": ("intel_search",),
    "start": ("start_country_search",),
    "losses": ("ls_draft",),
}

KEY_TO_GROUP: dict[str, str] = {
    key: group for group, keys in INPUT_MODE_GROUPS.items() for key in keys
}

ALL_INPUT_KEYS: tuple[str, ...] = tuple(KEY_TO_GROUP)

# کلید داخلی زمان باز شدن حالت، و عمر مجاز آن.
# ویزارد نیمه‌کاره‌ی دیروز نباید پیام امروز را بخورد.
OPENED_AT_KEY = "_input_mode_opened_at"
INPUT_MODE_MAX_AGE_SECONDS = 30 * 60


def clear_input_modes(user_data, keep_group: str | None = None) -> list[str]:
    """پاک‌کردن همه‌ی حالت‌های ورودی به‌جز گروهی که باید بماند. فهرست پاک‌شده‌ها را برمی‌گرداند."""
    removed = []
    for key, group in KEY_TO_GROUP.items():
        if group == keep_group:
            continue
        if key in user_data:
            try:
                dict.__delitem__(user_data, key) if isinstance(user_data, dict) else user_data.pop(key)
            except KeyError:
                pass
            removed.append(key)
    return removed


def drop_stale_input_modes(user_data, max_age: int = INPUT_MODE_MAX_AGE_SECONDS) -> bool:
    """حالت ورودی کهنه را می‌بندد. True یعنی چیزی بسته شد."""
    opened_at = user_data.get(OPENED_AT_KEY)
    if opened_at is None:
        return False
    if time.time() - float(opened_at) <= max_age:
        return False
    removed = clear_input_modes(user_data)
    try:
        dict.__delitem__(user_data, OPENED_AT_KEY)
    except KeyError:
        pass
    return bool(removed)


class ExclusiveInputUserData(dict):
    """`user_data` که اجازه نمی‌دهد دو حالت ورودی هم‌زمان باز بماند."""

    def __setitem__(self, key, value):
        group = KEY_TO_GROUP.get(key)
        if group is not None and value not in (None, False):
            clear_input_modes(self, keep_group=group)
            dict.__setitem__(self, OPENED_AT_KEY, time.time())
        dict.__setitem__(self, key, value)

    def active_input_group(self) -> str | None:
        for key, group in KEY_TO_GROUP.items():
            if self.get(key) not in (None, False):
                return group
        return None
