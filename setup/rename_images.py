"""
images ディレクトリの画像ファイルを「お題画像1.png」形式にリネームするスクリプト

使い方:
    python rename_images.py [--dir ./images] [--prefix お題画像] [--dry-run]

--dry-run をつけると実際には変更せず確認だけできます。
"""
import argparse
from pathlib import Path

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def rename_images(target_dir: Path, prefix: str, dry_run: bool) -> None:
    files = sorted(
        [f for f in target_dir.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTENSIONS],
        key=lambda f: f.name,
    )

    if not files:
        print(f"❌ 画像ファイルが見つかりません: {target_dir}")
        return

    print(f"{'[DRY RUN] ' if dry_run else ''}リネーム対象: {len(files)} 件\n")

    for i, src in enumerate(files, start=1):
        dst = target_dir / f"{prefix}{i}{src.suffix.lower()}"
        print(f"  {src.name}  →  {dst.name}")
        if not dry_run:
            src.rename(dst)

    if not dry_run:
        print(f"\n✅ {len(files)} 件リネーム完了")
    else:
        print(f"\n（--dry-run モード: 変更なし）")


def main():
    parser = argparse.ArgumentParser(description="画像ファイルを連番でリネーム")
    parser.add_argument("--dir", type=str, default="./images", help="対象ディレクトリ (デフォルト: ./images)")
    parser.add_argument("--prefix", type=str, default="お題画像", help="ファイル名のプレフィックス (デフォルト: お題画像)")
    parser.add_argument("--dry-run", action="store_true", help="実際には変更せず確認だけ行う")
    args = parser.parse_args()

    rename_images(Path(args.dir), args.prefix, args.dry_run)


if __name__ == "__main__":
    main()
