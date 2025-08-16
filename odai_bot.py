import discord
from discord.ext import commands
import random
import os
from dotenv import load_dotenv
import asyncio

# .env ファイルの読み込み
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # int に変換

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

async def send_odai():
    """チャンネルに画像を1枚送信する"""
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("指定チャンネルが見つかりません")
        return

    img_folder = 'img'
    if not os.path.exists(img_folder):
        print(f"画像フォルダ '{img_folder}' が存在しません")
        return

    img_files = [f for f in os.listdir(img_folder) if os.path.isfile(os.path.join(img_folder, f))]
    if not img_files:
        print("画像が見つかりません")
        return

    selected_image = random.choice(img_files)
    image_path = os.path.join(img_folder, selected_image)

    try:
        await channel.send(file=discord.File(image_path))
        print(f"送信成功: {selected_image}")
    except Exception as e:
        print(f"送信失敗: {e}")

@bot.event
async def on_ready():
    print(f'ログインしました: {bot.user}')
    # 画像送信してすぐ終了
    await send_odai()
    await bot.close()  # GitHub Actions で自動終了させる

# コマンドから手動で画像送信も可能（必要に応じて）
@bot.command()
async def odai(ctx):
    await send_odai()

# Bot 起動
bot.run(TOKEN)
