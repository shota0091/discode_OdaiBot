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
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
BOT_INTERNAL_SECRET = os.getenv("BOT_INTERNAL_SECRET", "")

def _api_headers() -> dict:
    return {"X-Bot-Secret": BOT_INTERNAL_SECRET}


def _get_plan_row(guild_id: int, db) -> dict:
    """プラン情報を DB から取得。レコードなしは free 扱い。"""
    row = db.query_one(
        "SELECT p.name AS plan_name, p.has_discord_op, p.can_expand_capacity, "
        "gp.custom_odai_capacity, gp.status, gp.current_period_end "
        "FROM guild_plans gp JOIN plans p ON gp.plan_id = p.id WHERE gp.guild_id = %s",
        (guild_id,),
    )
    if row:
        return row
    free = db.query_one(
        "SELECT name AS plan_name, has_discord_op, can_expand_capacity FROM plans WHERE name = 'free'", ()
    )
    return {**(free or {}), "custom_odai_capacity": 0, "status": "active", "current_period_end": None}


def _has_discord_op(guild_id: int, db) -> bool:
    return bool(_get_plan_row(guild_id, db).get("has_discord_op"))


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
        reset_token = make_token()
        expires_at = (datetime.now() + timedelta(hours=INVITE_EXPIRE_HOURS)).strftime("%Y-%m-%d %H:%M:%S")
        invite_repo.create_invite(interaction.guild_id, username, role, reset_token, expires_at)
        login_url = f"{DASHBOARD_BASE_URL.rstrip('/')}#/login"
        reset_url = f"{DASHBOARD_BASE_URL.rstrip('/')}#/reset-password?guild_id={interaction.guild_id}&invite={reset_token}"
        await interaction.response.send_message(
            f"ℹ️ ユーザー `{username}` は既に登録されています\n\n"
            f"🔐 ログインはこちら: {login_url}\n\n"
            f"🔑 パスワードを忘れた場合はリセットリンク（期限: {INVITE_EXPIRE_HOURS}時間）:\n{reset_url}",
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

    if not _has_discord_op(interaction.guild_id, factory.db):
        await interaction.response.send_message(
            "⚠️ このコマンドは Light プラン以上でご利用いただけます。\n`/subscribe` でプランを確認してください。",
            ephemeral=True,
        )
        return

    notify = factory.getNotifyService()
    target_channel = channel or interaction.channel
    await interaction.response.defer(ephemeral=True)

    success, payload = await notify.send_notify_odai(target_channel)
    if success:
        await interaction.followup.send("✅ お題を送信しました", ephemeral=True)
    else:
        await interaction.followup.send(f"❌ 投稿に失敗しました: {payload}", ephemeral=True)

# ---- Plan コマンド（全プラン共通）----

@bot.tree.command(name="plan", description="現在のプラン・お題残枠・次回更新日を表示します")
@app_commands.default_permissions(administrator=True)
async def show_plan(interaction: discord.Interaction):
    factory = OdaiFactory(interaction.guild_id)
    plan = _get_plan_row(interaction.guild_id, factory.db)

    plan_name = (plan.get("plan_name") or "free").upper()
    cap = plan.get("custom_odai_capacity")
    status = plan.get("status", "active")
    period_end = plan.get("current_period_end")

    current_row = factory.db.query_one(
        "SELECT COUNT(*) AS cnt FROM odai WHERE guild_id = %s AND deleted_at IS NULL",
        (interaction.guild_id,),
    )
    current = current_row["cnt"] if current_row else 0

    if cap is None:
        capacity_str = f"{current} 件（無制限）"
    elif cap == 0:
        capacity_str = "独自お題不可"
    else:
        capacity_str = f"{current} / {cap} 件（残り {cap - current} 件）"

    period_str = str(period_end)[:10] if period_end else "—"

    await interaction.response.send_message(
        f"📋 **プラン情報**\n"
        f"プラン: **{plan_name}**\n"
        f"独自お題: {capacity_str}\n"
        f"次回更新: {period_str}\n"
        f"ステータス: {status}",
        ephemeral=True,
    )


@bot.tree.command(name="subscribe", description="プランを購読します（Stripe の決済ページを DM で送付）")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(plan="購読するプラン（light または pro）")
@app_commands.choices(plan=[
    app_commands.Choice(name="Light — ¥600/月", value="light"),
    app_commands.Choice(name="Pro  — ¥960/月", value="pro"),
])
async def subscribe(interaction: discord.Interaction, plan: str):
    import httpx
    await interaction.response.defer(ephemeral=True)
    success_url = f"{DASHBOARD_BASE_URL.rstrip('/')}#/subscribe/success"
    cancel_url = f"{DASHBOARD_BASE_URL.rstrip('/')}#/subscribe/cancel"
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{API_BASE_URL}/api/stripe/checkout",
                json={"guild_id": interaction.guild_id, "plan": plan,
                      "success_url": success_url, "cancel_url": cancel_url},
                headers=_api_headers(),
                timeout=10,
            )
        if res.status_code != 200:
            await interaction.followup.send(f"❌ Checkout URL の生成に失敗しました: {res.text}", ephemeral=True)
            return
        url = res.json().get("url", "")
        try:
            await interaction.user.send(
                f"✅ **{plan.upper()} プランの決済ページ**\n\n{url}\n\n"
                "このリンクから決済を完了してください。有効期限は約24時間です。"
            )
            await interaction.followup.send("📬 DM に決済リンクを送りました。", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(
                f"📬 DM が送れませんでした。直接このリンクをご利用ください:\n{url}", ephemeral=True
            )
    except Exception as e:
        await interaction.followup.send(f"❌ エラーが発生しました: {e}", ephemeral=True)


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

        if not _has_discord_op(guild.id, factory.db):
            continue

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
