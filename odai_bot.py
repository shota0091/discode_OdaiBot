import discord
from discord.ext import commands
import random
import os
from dotenv import load_dotenv
from datetime import datetime, time
import asyncio

# .env 読み込み
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

def seconds_until_target(target_hour, target_minute):
    now = datetime.now()
    target = datetime.combine(now.date(), time(target_hour, target_minute))
    if target < now:
        target = datetime.combine(now.date(), time(target_hour, target_minute))  # 翌日分にしない
    return (target - now).total_seconds()

async def send_odai():
    await asyncio.sleep(seconds_until_target(8, 0))  # JST 8:00まで待機

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print("チャンネルが見つかりません")
        return

    img_folder = 'img'
    if not os.path.exists(img_folder):
        print("画像フォルダが見つかりません")
        return

    files = [f for f in os.listdir(img_folder) if os.path.isfile(os.path.join(img_folder, f))]
    if not files:
        print("画像がありません")
        return

    selected_image = random.choice(files)
    path = os.path.join(img_folder, selected_image)

    try:
        await channel.send(file=discord.File(path))
        print(f"画像送信成功: {selected_image}")
    except Exception as e:
        print(f"送信失敗: {e}")

@bot.event
async def on_ready():
    print(f"ログイン成功: {bot.user}")
    await send_odai()
    await bot.close()  # 実行後に終了（Railway/Actions向け）

@bot.command()
async def odai(ctx):
    await send_odai()

bot.run(TOKEN)