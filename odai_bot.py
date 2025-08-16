import discord
from discord.ext import commands, tasks
import random
import os
from dotenv import load_dotenv
from datetime import datetime, time, timedelta

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

CHANNEL_ID = 1396823594411098226 # 送信したいチャンネルのID

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
@bot.event
async def on_ready():
    print(f'ログインしました: {bot.user}')
    print("ここまで来たらon_readyは呼ばれています")
    print(f'ログインしました: {bot.user}')
    send_odai_daily.start()  # ループを開始

def seconds_until(hour, minute):
    """次の指定時刻までの秒数を返す"""
    now = datetime.now()
    target = datetime.combine(now.date(), time(hour, minute))
    if target < now:
        target += timedelta(days=1)
    return (target - now).total_seconds()

@tasks.loop(seconds=60)
async def send_odai_daily():
    """毎日指定時刻にお題を送る"""
    now = datetime.now()
    print("ループ中:", now)  #
    if now.hour == 8 and now.minute == 00:  # 朝9:00になったら
        
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            img_folder = 'img'
            img_files = os.listdir(img_folder)
            if img_files:
                selected_image = random.choice(img_files)
                image_path = os.path.join(img_folder, selected_image)
                await channel.send(file=discord.File(image_path))

@bot.command()
async def odai(ctx):
    """コマンドで画像を送る"""
    img_folder = 'img'
    img_files = os.listdir(img_folder)
    selected_image = random.choice(img_files)
    image_path = os.path.join(img_folder, selected_image)
    await ctx.send(file=discord.File(image_path))


bot.run(TOKEN)