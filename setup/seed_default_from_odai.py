"""既存の odai テーブルから 1 サーバー分をデフォルトお題として default_odai テーブルに登録するスクリプト。

実行方法（プロジェクトルートから）:
    python setup/seed_default_from_odai.py --guild 1315559712179228672 [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from dotenv import load_dotenv
load_dotenv(_root / ".env")

from OdaiBotDB.database import MySQLDatabase

_IMAGE_DIR = Path(os.getenv("DEFAULT_ODAI_IMAGE_DIR", "/data/default_odai"))
DEFAULT_GUILD_ID = 1315559712179228672


def seed(guild_id: int, dry_run: bool) -> None:
    db = MySQLDatabase()

    rows = db.query(
        "SELECT filename, storage_path FROM odai "
        "WHERE guild_id = %s AND deleted_at IS NULL AND storage_path IS NOT NULL "
        "ORDER BY filename",
        (guild_id,),
    )

    if not rows:
        print(f"❌ guild_id={guild_id} の odai レコードが見つかりません。")
        return

    print(f"{'[DRY RUN] ' if dry_run else ''}対象: {len(rows)} 件  (guild_id={guild_id})")
    print(f"保存先: {_IMAGE_DIR}\n")

    if dry_run:
        for r in rows:
            src = Path(r["storage_path"])
            flag = "✅" if src.exists() else "❌ ファイルなし"
            print(f"  {flag} {r['filename']}")
        print(f"\n（--dry-run モード: 登録なし）")
        return

    _IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    inserted = skipped = error = 0

    for r in rows:
        if db.query_one("SELECT id FROM default_odai WHERE filename = %s", (r["filename"],)):
            skipped += 1
            continue

        src = Path(r["storage_path"])
        if not src.exists():
            print(f"  ❌ ファイルなし: {r['filename']}")
            error += 1
            continue

        try:
            dest = _IMAGE_DIR / r["filename"]
            shutil.copy2(src, dest)
            db.execute(
                "INSERT INTO default_odai (filename, storage_path, is_active) VALUES (%s, %s, 1)",
                (r["filename"], str(dest)),
                commit=True,
            )
            inserted += 1
            print(f"  [{inserted}] {r['filename']}")
        except Exception as e:
            print(f"  ❌ 登録失敗: {r['filename']}: {e}")
            error += 1

    print(f"\n✅ 完了: 登録 {inserted} 件 / スキップ {skipped} 件 / エラー {error} 件")


def main():
    parser = argparse.ArgumentParser(description="odai テーブルからデフォルトお題を default_odai に登録")
    parser.add_argument("--guild", type=int, default=DEFAULT_GUILD_ID, help=f"取得元サーバー ID（デフォルト: {DEFAULT_GUILD_ID}）")
    parser.add_argument("--dry-run", action="store_true", help="確認のみ（DB 登録なし）")
    args = parser.parse_args()
    seed(args.guild, args.dry_run)


if __name__ == "__main__":
    main()
