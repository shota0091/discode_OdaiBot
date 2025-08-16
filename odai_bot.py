import discord
from discord.ext import commands
import random
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))  # intに変換

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'ログインしました: {bot.user}')
    await send_odai_once()
    await bot.close()  # 終了（Railway側で自動的にコンテナ停止される）

async def send_odai_once():
    channel = bot.get_channel(CHANNEL_ID)
    if channel:
        img_folder = 'img'
        img_files = os.listdir(img_folder)
        if img_files:
            selected_image = random.choice(img_files)
            image_path = os.path.join(img_folder, selected_image)
            await channel.send(file=discord.File(image_path))
            print(f"送信成功: {selected_image}")
        else:
            print("画像が見つかりません")
    else:
        print("チャンネルが見つかりません")

# 手動コマンドもそのまま残す場合はこれでOK
@bot.command()
async def odai(ctx):
    img_folder = 'img'
    img_files = os.listdir(img_folder)
    selected_image = random.choice(img_files)
    image_path = os.path.join(img_folder, selected_image)
    await ctx.send(file=discord.File(image_path))

bot.run(TOKEN)