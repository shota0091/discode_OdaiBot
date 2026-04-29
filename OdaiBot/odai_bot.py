import hashlib
import os
import sys
import secrets
from pathlib import Path
from dotenv import load_dotenv

# プロジェクトルート（discode_OdaiBot）を sys.path に追加
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# OdaiBotDB のインポートより先に .env を読み込む（先勝ち）
_bot_dir = Path(__file__).resolve().parent
load_dotenv(_bot_dir / ".env")           # OdaiBot/.env を優先
load_dotenv(_bot_dir.parent / ".env")    # なければプロジェクトルート .env

import discord
from discord.ext import commands, tasks
from discord import app_commands
from datetime import datetime, timedelta
from Factory.OdaiFactory import OdaiFactory
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
DASHBOARD_BASE_URL = os.getenv("DASHBOARD_BASE_URL", "http://localhost:3000")
INVITE_EXPIRE_HOURS = int(os.getenv("INVITE_EXPIRE_HOURS", "24"))

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---- Slash command ----

@bot.tree.command(name="ping", description="Test bot")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong!")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000)
    return f"{salt}${key.hex()}"


def make_token() -> str:
    return secrets.token_urlsafe(32)


def _sync_guild_meta(factory: "OdaiFactory", guild: discord.Guild) -> None:
    """guild_settings にサーバー名を保存し、channels テーブルをテキストチャンネルで同期する。"""
    db = factory.db
    db.execute(
        "INSERT INTO guild_settings (guild_id, guild_name, bot_enabled) VALUES (%s, %s, 1) "
        "ON DUPLICATE KEY UPDATE guild_name = VALUES(guild_name), updated_at = CURRENT_TIMESTAMP",
        (guild.id, guild.name),
        commit=True,
    )
    for ch in guild.text_channels:
        db.execute(
            "INSERT INTO channels (guild_id, channel_id, name) VALUES (%s, %s, %s) "
            "ON DUPLICATE KEY UPDATE name = VALUES(name), updated_at = CURRENT_TIMESTAMP",
            (guild.id, ch.id, ch.name),
            commit=True,
        )


@bot.tree.command(name="odai_dashboard", description="Dashboard 用招待リンクを生成します")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(username="Dashboard ユーザー名（省略時はコマンド実行者のDiscordユーザー名）", role="ユーザー権限")
async def odai_dashboard(interaction: discord.Interaction, username: str = None, role: str = "admin"):
    if username is None:
        username = interaction.user.name
    factory = OdaiFactory(interaction.guild_id)

    # サーバー名とチャンネル情報を同期
    _sync_guild_meta(factory, interaction.guild)

    user_repo = factory.getUserRepository()
    invite_repo = factory.getInviteRepository()

    if user_repo.exists(interaction.guild_id, username):
        await interaction.response.send_message(
            f"⚠️ ユーザー `{username}` は既に存在します。別のユーザー名を指定してください。",
            ephemeral=True,
        )
        return

    if role not in ("admin", "user"):
        await interaction.response.send_message(
            "⚠️ role は admin か user のいずれかを指定してください。",
            ephemeral=True,
        )
        return

    invite_token = make_token()
    expires_at = (datetime.now() + timedelta(hours=INVITE_EXPIRE_HOURS)).strftime("%Y-%m-%d %H:%M:%S")
    invite_repo.create_invite(interaction.guild_id, username, role, invite_token, expires_at)

    invite_url = f"{DASHBOARD_BASE_URL.rstrip('/')}#/register?guild_id={interaction.guild_id}&invite={invite_token}"
    await interaction.response.send_message(
        "✅ Dashboard 招待リンクを生成しました\n"
        f"ユーザー名: `{username}`\n"
        f"ロール: `{role}`\n"
        f"期限: {INVITE_EXPIRE_HOURS}時間\n"
        f"リンク: {invite_url}\n"
        "\n\nこのリンクを踏んで、Dashboard でパスワードを設定してください。",
        ephemeral=True,
    )


@bot.tree.command(name="odai", description="今日のお題を送信")
@app_commands.default_permissions(administrator=True)
async def send_odai(interaction: discord.Interaction, channel: discord.TextChannel = None):
    factory = OdaiFactory(interaction.guild_id)
    notify = factory.getNotifyService()

    target_channel = channel or interaction.channel
    await interaction.response.defer(ephemeral=True)

    success, payload = await notify.send_notify_odai(target_channel)
    if success:
        await interaction.followup.send("✅ お題を送信しました", ephemeral=True)
    else:
        await interaction.followup.send(f"❌ 投稿に失敗しました: {payload}", ephemeral=True)

# ---- Scheduler ----

@tasks.loop(minutes=1)
async def odai_schedule_loop():
    now = datetime.now().strftime("%H:%M")
    print(f"🕒 schedule tick: {now}")

    for guild in bot.guilds:
        factory = OdaiFactory(guild.id)

        # サーバー名を最新に保つ（チャンネル全同期は on_ready と /odai_dashboard に委ねる）
        factory.db.execute(
            "INSERT INTO guild_settings (guild_id, guild_name, bot_enabled) VALUES (%s, %s, 1) "
            "ON DUPLICATE KEY UPDATE guild_name = VALUES(guild_name), updated_at = CURRENT_TIMESTAMP",
            (guild.id, guild.name),
            commit=True,
        )

        schedule_service = factory.getScheduleService()
        print(f"🔎 Checking schedule for guild: {guild.name} ({guild.id})")
        await schedule_service.run(bot)


@odai_schedule_loop.before_loop
async def before_odai_schedule_loop():
    print("⏳ スケジューラ起動待機中...")
    await bot.wait_until_ready()
    print("✅ スケジューラ開始！")

# ---- Events ----

@bot.event
async def on_ready():
    try:
        # 各ギルドの古いコマンドをクリアしてグローバルsync
        for guild in bot.guilds:
            bot.tree.clear_commands(guild=guild)
            await bot.tree.sync(guild=guild)
        await bot.tree.sync()
        print(f"✅ Logged in as {bot.user}")
    except Exception as e:
        print("❌ Sync error:", e)

    # 起動時に参加済み全 guild のサーバー名とチャンネルを同期
    for guild in bot.guilds:
        try:
            _sync_guild_meta(OdaiFactory(guild.id), guild)
            print(f"🔄 guild メタ同期完了: {guild.name} ({guild.id})")
        except Exception as e:
            print(f"⚠️ guild メタ同期失敗: {guild.name} ({guild.id}): {e}")

    if not odai_schedule_loop.is_running():
        odai_schedule_loop.start()
        print("⏱️ お題定期送信ループ開始")

# ---- Run ----

if not TOKEN:
    raise RuntimeError("DISCORD_BOT_TOKEN が .env に設定されていません")

bot.run(TOKEN)
