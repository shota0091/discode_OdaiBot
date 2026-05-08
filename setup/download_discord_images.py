"""
Discord チャンネルから画像を一括ダウンロードするスクリプト

使い方:
    python download_discord_images.py --channel CHANNEL_ID [--output ./images] [--limit 0] [--user USER_ID]

必要な環境変数:
    DISCORD_BOT_TOKEN  (OdaiBot/.env または プロジェクトルート .env)

保存ファイル名: {メッセージID}_{ファイル名 or index.png}
"""
import asyncio
import argparse
import os
import sys
from pathlib import Path
from urllib.parse import urlparse
from dotenv import load_dotenv

_script_dir = Path(__file__).resolve().parent
load_dotenv(_script_dir / "OdaiBot" / ".env")
load_dotenv(_script_dir / ".env")

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not TOKEN:
    print("❌ DISCORD_BOT_TOKEN が .env に設定されていません")
    sys.exit(1)

import discord
import aiohttp

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def _is_image_url(url: str) -> bool:
    path = urlparse(url).path.lower()
    return any(path.endswith(ext) for ext in IMAGE_EXTENSIONS)


async def download_images(channel_id: int, output_dir: Path, limit: int | None, user_id: int | None) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    intents = discord.Intents.default()
    intents.message_content = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready():
        print(f"✅ Logged in as {client.user}")
        channel = client.get_channel(channel_id)
        if channel is None:
            try:
                channel = await client.fetch_channel(channel_id)
            except discord.NotFound:
                print(f"❌ チャンネルが見つかりません: {channel_id}")
                await client.close()
                return
            except discord.Forbidden:
                print(f"❌ チャンネルへのアクセス権限がありません: {channel_id}")
                await client.close()
                return

        filter_label = f" (ユーザーID: {user_id})" if user_id else ""
        print(f"📥 チャンネル '{channel.name}' をスキャン中{filter_label}...")

        count = 0
        skipped = 0
        scanned = 0

        async with aiohttp.ClientSession() as session:
            async for message in channel.history(limit=limit, oldest_first=True):
                scanned += 1
                print(f"  [SCAN] {message.author} (id={message.author.id}) attachments={len(message.attachments)} embeds={len(message.embeds)}")
                if user_id and message.author.id != user_id:
                    continue

                urls_to_download: list[tuple[str, str]] = []

                # ファイル添付
                for att in message.attachments:
                    ext = Path(att.filename).suffix.lower()
                    if ext in IMAGE_EXTENSIONS:
                        urls_to_download.append((att.url, att.filename))

                # embed 画像（URLで貼った場合）
                for i, embed in enumerate(message.embeds):
                    if embed.image and embed.image.url:
                        url = embed.image.url
                        if _is_image_url(url):
                            fname = Path(urlparse(url).path).name or f"embed_{i}.png"
                            urls_to_download.append((url, fname))
                    if embed.thumbnail and embed.thumbnail.url:
                        url = embed.thumbnail.url
                        if _is_image_url(url):
                            fname = Path(urlparse(url).path).name or f"thumb_{i}.png"
                            urls_to_download.append((url, fname))

                for url, fname in urls_to_download:
                    filepath = output_dir / f"{message.id}_{fname}"
                    if filepath.exists():
                        skipped += 1
                        continue
                    try:
                        async with session.get(url) as resp:
                            if resp.status == 200:
                                filepath.write_bytes(await resp.read())
                                count += 1
                                print(f"  [{count}] {filepath.name}")
                            else:
                                print(f"  ⚠️ HTTP {resp.status}: {url}")
                    except Exception as e:
                        print(f"  ❌ ダウンロード失敗: {fname}: {e}")

        print(f"\n📊 スキャンしたメッセージ数: {scanned}")
        print(f"✅ 完了: {count} 件ダウンロード, {skipped} 件スキップ（既存）")
        print(f"📁 保存先: {output_dir.resolve()}")
        await client.close()

    await client.start(TOKEN)


def main():
    parser = argparse.ArgumentParser(description="Discord チャンネルから画像を一括ダウンロード")
    parser.add_argument("--channel", type=int, required=True, help="対象チャンネルID")
    parser.add_argument("--output", type=str, default="./downloaded_images", help="保存先ディレクトリ")
    parser.add_argument("--limit", type=int, default=0, help="取得メッセージ数の上限 (0=無制限, デフォルト: 0)")
    parser.add_argument("--user", type=int, default=None, help="特定ユーザーのみ取得するユーザーID（省略時は全員）")
    args = parser.parse_args()

    limit = args.limit if args.limit > 0 else None
    asyncio.run(download_images(args.channel, Path(args.output), limit, args.user))


if __name__ == "__main__":
    main()
