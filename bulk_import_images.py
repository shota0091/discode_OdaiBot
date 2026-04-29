"""
images ディレクトリの画像を odai テーブルに一括登録するスクリプト

使い方:
    python bulk_import_images.py [--dir ./images] [--guilds GUILD_ID ...] [--dry-run]

デフォルトのサーバーID:
    1315559712179228672, 1396823594411098223

--dry-run をつけると登録せず件数確認のみ行います。
既に同じ (guild_id, filename) が登録済みの場合はスキップします。
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent
sys.path.insert(0, str(_root))

from dotenv import load_dotenv
load_dotenv(_root / "OdaiBot" / ".env")
load_dotenv(_root / ".env")

from OdaiBotDB.database import MySQLDatabase

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB

DEFAULT_GUILD_IDS = [1315559712179228672, 1396823594411098223]


def bulk_import(image_dir: Path, guild_ids: list[int], dry_run: bool) -> None:
    files = sorted(
        [f for f in image_dir.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS],
        key=lambda f: f.name,
    )

    if not files:
        print(f"❌ 画像ファイルが見つかりません: {image_dir.resolve()}")
        return

    print(f"{'[DRY RUN] ' if dry_run else ''}対象画像: {len(files)} 件")
    print(f"対象サーバーID: {guild_ids}\n")

    if dry_run:
        for f in files:
            size = f.stat().st_size
            flag = " ⚠️ 8MB超過" if size > MAX_IMAGE_BYTES else ""
            print(f"  {f.name} ({size // 1024} KB){flag}")
        print(f"\n（--dry-run モード: 登録なし）")
        return

    db = MySQLDatabase()
    total_inserted = 0
    total_skipped = 0
    total_error = 0

    for guild_id in guild_ids:
        print(f"{'─' * 50}")
        print(f"🔄 Guild ID: {guild_id}")
        inserted = skipped = error = 0

        # guild_settings がなければ作成
        if not db.query_one("SELECT id FROM guild_settings WHERE guild_id = %s", (guild_id,)):
            db.execute(
                "INSERT INTO guild_settings (guild_id, bot_enabled) VALUES (%s, 1)",
                (guild_id,), commit=True,
            )
            print(f"  📋 guild_settings 作成")

        for f in files:
            size = f.stat().st_size
            if size > MAX_IMAGE_BYTES:
                print(f"  ⚠️  8MB超過スキップ: {f.name} ({size // 1024} KB)")
                error += 1
                continue

            # 重複チェック
            if db.query_one(
                "SELECT id FROM odai WHERE guild_id = %s AND filename = %s",
                (guild_id, f.name),
            ):
                skipped += 1
                continue

            try:
                data = f.read_bytes()
                db.execute(
                    "INSERT INTO odai (guild_id, filename, data, used) VALUES (%s, %s, %s, 0)",
                    (guild_id, f.name, data), commit=True,
                )
                inserted += 1
                print(f"  [{inserted}] {f.name}")
            except Exception as e:
                print(f"  ❌ 登録失敗: {f.name}: {e}")
                error += 1

        print(f"  → 登録: {inserted} 件 / スキップ（登録済み）: {skipped} 件 / エラー: {error} 件")
        total_inserted += inserted
        total_skipped += skipped
        total_error += error

    print(f"\n{'=' * 50}")
    print(f"✅ 完了")
    print(f"   登録: {total_inserted} 件 / スキップ: {total_skipped} 件 / エラー: {total_error} 件")


def main():
    parser = argparse.ArgumentParser(description="images ディレクトリの画像を odai テーブルに一括登録")
    parser.add_argument("--dir", type=str, default="./images", help="画像ディレクトリ (デフォルト: ./images)")
    parser.add_argument("--guilds", type=int, nargs="+", default=DEFAULT_GUILD_IDS, help="登録先サーバーID（複数指定可）")
    parser.add_argument("--dry-run", action="store_true", help="確認のみ（DBへの登録なし）")
    args = parser.parse_args()

    bulk_import(Path(args.dir), args.guilds, args.dry_run)


if __name__ == "__main__":
    main()
