#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""سلب اشتراک VIP از گروه‌های غیردولتی که قبلاً رایگان گرفته بودند.

این اسکریپت **به‌صورت خودکار اجرا نمی‌شود**. فقط وقتی اجرا کن که تصمیم گرفته باشی
مزیت را از گروه‌های موجود هم پس بگیری. پیش‌فرضش حالت گزارش است و چیزی را تغییر نمی‌دهد.

    python3 tools/revoke_militia_vip.py                    # فقط گزارش
    python3 tools/revoke_militia_vip.py --apply            # اعمال واقعی (بکاپ می‌گیرد)
    python3 tools/revoke_militia_vip.py --apply --db /data/game.db

فقط ستون‌های is_vip / vip_tier / vip_expires_at لمس می‌شوند. خزانه، درآمد، تجهیزات،
نیرو و هیچ دارایی دیگری دست نمی‌خورد. کسانی که جداگانه VIP خریده‌اند (رکورد
payment_requests با item_type شروع‌شده با vip_) از فهرست کنار گذاشته می‌شوند.
"""
import argparse
import datetime
import shutil
import sqlite3
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="game.db")
    parser.add_argument("--apply", action="store_true", help="اعمال واقعی تغییر")
    args = parser.parse_args()

    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    rows = conn.execute(
        """
        SELECT c.id, c.name, c.flag, c.player_id, c.vip_tier, c.vip_expires_at
        FROM countries c
        WHERE c.country_key LIKE 'faction_%'
          AND COALESCE(c.is_vip, 0) = 1
          AND NOT EXISTS (
              SELECT 1 FROM payment_requests p
              WHERE p.country_id = c.id AND p.status = 'approved'
                AND (p.item_type LIKE 'vip_%' OR p.item_type = 'pass')
          )
        ORDER BY c.id
        """
    ).fetchall()

    if not rows:
        print("هیچ گروهی با VIP رایگان پیدا نشد.")
        return 0

    print(f"{len(rows)} گروه با VIP رایگان:")
    for row in rows:
        print(f"  #{row['id']} {row['flag']} {row['name']} | tier={row['vip_tier']} | player={row['player_id']}")

    if not args.apply:
        print("\nحالت گزارش. برای اعمال، --apply را اضافه کن.")
        return 0

    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup = f"{args.db}.before_revoke_militia_vip_{stamp}"
    shutil.copy2(args.db, backup)
    print(f"\nبکاپ گرفته شد: {backup}")

    ids = [row["id"] for row in rows]
    with conn:
        conn.executemany(
            "UPDATE countries SET is_vip = 0, vip_tier = NULL, vip_expires_at = NULL WHERE id = ?",
            [(cid,) for cid in ids],
        )
    print(f"VIP از {len(ids)} گروه برداشته شد. هیچ دارایی دیگری تغییر نکرد.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
