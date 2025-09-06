import discord
from discord import app_commands
import random
import os
from dotenv import load_dotenv
from datetime import datetime, time
import asyncio

# .env 読み込み
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

# IntentsとClient初期化
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# お題送信処理（共通化）
async def send_odai_to_channel(channel):
    img_folder = 'img'
    if not os.path.exists(img_folder):
        await channel.send("画像フォルダが見つかりません")
        return

    files = [f for f in os.listdir(img_folder) if os.path.isfile(os.path.join(img_folder, f))]
    if not files:
        await channel.send("画像がありません")
        return

    selected_image = random.choice(files)
    path = os.path.join(img_folder, selected_image)

    try:
        await channel.send(file=discord.File(path))
        print(f"画像送信成功: {selected_image}")
    except Exception as e:
        await channel.send(f"送信失敗: {e}")
        print(f"送信失敗: {e}")

# スラッシュコマンド登録
@tree.command(name="odai", description="ランダムなお題画像を送信します")
async def odai_command(interaction: discord.Interaction):
    await interaction.response.defer()
    channel = client.get_channel(CHANNEL_ID)
    if not channel:
        await interaction.followup.send("送信チャンネルが見つかりません")
        return
    await send_odai_to_channel(channel)
    await interaction.followup.send("お題を送信しました。")

# 起動処理
@client.event
async def on_ready():
    print(f"ログイン成功: {client.user}")
    try:
        synced = await tree.sync()
        print(f"スラッシュコマンドを同期しました: {len(synced)}件")
    except Exception as e:
        print(f"コマンド同期失敗: {e}")

    # GitHub Actionsなどで即時送信して終了
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        await send_odai_to_channel(channel)
    await client.close()

client.run(TOKEN)
