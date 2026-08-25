# -*- coding: utf-8 -*-
"""
پیکربندی سراسری تست‌ها.

مهم‌ترین وظیفه: جلوگیری از دست‌خوردن دیتابیس واقعی بازی هنگام اجرای تست‌ها.

برخی از فایل‌های تست مستقیماً `database.init_db()` را صدا می‌زنند بدون آنکه
`config.DB_PATH` را به یک مسیر موقت تغییر دهند. بدون این فایل، آن تست‌ها روی
`game.db` واقعی (یا حتی `/data/game.db` روی Railway) می‌نویسند و داده‌ی بازیکنان
را آلوده می‌کنند. فیکسچر زیر به‌صورت خودکار و برای کل نشست تست، مسیر دیتابیس را
به یک پوشه‌ی موقت منتقل می‌کند.

تست‌هایی که خودشان `config.DB_PATH` را monkeypatch می‌کنند همچنان کار می‌کنند،
چون monkeypatch در سطح تابع، این مقدار پیش‌فرض را موقتاً بازنویسی می‌کند.
"""

import os
import shutil
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _isolate_database_from_production():
    """مسیر دیتابیس را برای کل نشست تست به یک فایل موقت تغییر می‌دهد."""
    original_db_path = config.DB_PATH
    tmpdir = tempfile.mkdtemp(prefix="siasat_tests_")
    config.DB_PATH = os.path.join(tmpdir, "session_test.db")

    try:
        yield config.DB_PATH
    finally:
        config.DB_PATH = original_db_path
        shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture(scope="session")
def anyio_backend():
    """اجرای تست‌های async فقط روی asyncio (بدون نیاز به نصب trio)."""
    return "asyncio"
