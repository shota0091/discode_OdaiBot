"""
既存の odai BLOB データをローカルファイルに移行するスクリプト。

使い方:
    python migrate_odai_to_local.py

環境変数 ODAI_IMAGE_DIR でファイル保存先を指定（デフォルト: /data/odai）
移行済みのレコードはスキップされます（storage_path が設定済みかつファイルが存在する場合）。
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
import mysql.connector

load_dotenv()

IMAGE_DIR = Path(os.getenv("ODAI_IMAGE_DIR", "/data/odai"))

conn = mysql.connector.connect(
    host=os.getenv("MYSQL_HOST", "127.0.0.1"),
    port=int(os.getenv("MYSQL_PORT", "3306")),
    user=os.getenv("MYSQL_USER", "root"),
    password=os.getenv("MYSQL_PASSWORD", ""),
    database=os.getenv("MYSQL_DATABASE", "odai_bot"),
    autocommit=False,
)
cursor = conn.cursor(dictionary=True)

# data カラムを nullable に変更（未実施の場合のみ）
_chk = conn.cursor()
_chk.execute(
    "SELECT IS_NULLABLE FROM information_schema.COLUMNS "
    "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'odai' AND COLUMN_NAME = 'data'"
)
(is_nullable,) = _chk.fetchone()
_chk.close()
if is_nullable == 'NO':
    print("data カラムを nullable に変更中...")
    conn.cursor().execute("ALTER TABLE odai MODIFY COLUMN data LONGBLOB NULL")
    conn.commit()
    print("完了")

cursor.execute("SELECT id, guild_id, filename, storage_path, data FROM odai WHERE deleted_at IS NULL")
rows = cursor.fetchall()

migrated = skipped = failed = 0

for row in rows:
    odai_id = row["id"]
    guild_id = row["guild_id"]
    filename = row["filename"]
    storage_path = row.get("storage_path")
    data = row.get("data")

    # 移行済みチェック
    if storage_path and Path(storage_path).exists():
        skipped += 1
        continue

    if not data:
        print(f"[WARN] id={odai_id} ({filename}): データなし・スキップ")
        skipped += 1
        continue

    try:
        dest = IMAGE_DIR / str(guild_id) / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(bytes(data))

        cursor.execute(
            "UPDATE odai SET storage_path = %s, data = NULL WHERE id = %s",
            (str(dest), odai_id),
        )
        conn.commit()
        print(f"[OK]   id={odai_id} → {dest}")
        migrated += 1
    except Exception as e:
        conn.rollback()
        print(f"[FAIL] id={odai_id} ({filename}): {e}", file=sys.stderr)
        failed += 1

cursor.close()
conn.close()

print(f"\n完了: 移行={migrated}, スキップ={skipped}, 失敗={failed}")
