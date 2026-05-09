"""デフォルトお題画像を default_odai テーブルに一括登録するスクリプト。

使い方:
    python setup/seed_default_odai.py --dir ./images [--dry-run]

画像は DEFAULT_ODAI_IMAGE_DIR にコピーされ、default_odai テーブルに登録されます。
既に同名ファイルが登録済みの場合はスキップします。
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

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024
_IMAGE_DIR = Path(os.getenv("DEFAULT_ODAI_IMAGE_DIR", "/data/default_odai"))


def seed(image_dir: Path, dry_run: bool) -> None:
    files = sorted(
        [f for f in image_dir.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS],
        key=lambda f: f.name,
    )
    if not files:
        print(f"❌ 画像ファイルが見つかりません: {image_dir.resolve()}")
        return

    print(f"{'[DRY RUN] ' if dry_run else ''}対象画像: {len(files)} 件")
    print(f"保存先: {_IMAGE_DIR}\n")

    if dry_run:
        for f in files:
            size = f.stat().st_size
            flag = " ⚠️ 8MB超過" if size > MAX_IMAGE_BYTES else ""
            print(f"  {f.name} ({size // 1024} KB){flag}")
        print("\n（--dry-run モード: 登録なし）")
        return

    _IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    db = MySQLDatabase()
    inserted = skipped = error = 0

    for f in files:
        size = f.stat().st_size
        if size > MAX_IMAGE_BYTES:
            print(f"  ⚠️  8MB超過スキップ: {f.name}")
            error += 1
            continue

        if db.query_one("SELECT id FROM default_odai WHERE filename = %s", (f.name,)):
            skipped += 1
            continue

        try:
            dest = _IMAGE_DIR / f.name
            shutil.copy2(f, dest)
            db.execute(
                "INSERT INTO default_odai (filename, storage_path, is_active) VALUES (%s, %s, 1)",
                (f.name, str(dest)),
                commit=True,
            )
            inserted += 1
            print(f"  [{inserted}] {f.name}")
        except Exception as e:
            print(f"  ❌ 登録失敗: {f.name}: {e}")
            error += 1

    print(f"\n✅ 完了: 登録 {inserted} 件 / スキップ {skipped} 件 / エラー {error} 件")


def main():
    parser = argparse.ArgumentParser(description="デフォルトお題画像を default_odai テーブルに一括登録")
    parser.add_argument("--dir", type=str, default="./images", help="画像ディレクトリ（デフォルト: ./images）")
    parser.add_argument("--dry-run", action="store_true", help="確認のみ（DB 登録なし）")
    args = parser.parse_args()
    seed(Path(args.dir), args.dry_run)


if __name__ == "__main__":
    main()
