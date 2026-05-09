import hashlib
import io
import os
import re
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

_MAX_ODAI_BYTES = 8 * 1024 * 1024
_ALLOWED_MIME = {"image/jpeg", "image/png", "image/webp"}
_ODAI_PER_PAGE = 15


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


def _check_capacity(guild_id: int, db, adding: int = 1) -> tuple[bool, str]:
    """容量チェック。(ok, message) を返す。cap=None は無制限。"""
    plan = _get_plan_row(guild_id, db)
    cap = plan.get("custom_odai_capacity")
    if cap is None:
        return True, ""
    if cap == 0:
        return False, "このプランでは独自お題を登録できません（Light プラン以上が必要です）"
    current = db.query_one(
        "SELECT COUNT(*) AS cnt FROM odai WHERE guild_id = %s AND deleted_at IS NULL", (guild_id,)
    )
    cnt = current["cnt"] if current else 0
    if cnt + adding > cap:
        return False, f"お題の登録上限（{cap} 件）に達しています。`/expand` で容量を拡張してください"
    return True, ""

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


@bot.tree.command(name="expand", description="お題容量を拡張します（Stripe の決済ページを DM で送付）")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(units="追加する 100件単位数（例: 1 → +100件）")
async def expand_capacity(interaction: discord.Interaction, units: int = 1):
    import httpx
    if units < 1:
        await interaction.response.send_message("⚠️ units は 1 以上を指定してください。", ephemeral=True)
        return
    factory = OdaiFactory(interaction.guild_id)
    plan = _get_plan_row(interaction.guild_id, factory.db)
    if not plan.get("can_expand_capacity"):
        await interaction.response.send_message(
            "⚠️ このプランは容量拡張に対応していません。", ephemeral=True
        )
        return
    await interaction.response.defer(ephemeral=True)
    success_url = f"{DASHBOARD_BASE_URL.rstrip('/')}#/expand/success"
    cancel_url = f"{DASHBOARD_BASE_URL.rstrip('/')}#/expand/cancel"
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                f"{API_BASE_URL}/api/stripe/expand",
                json={"guild_id": interaction.guild_id, "units": units,
                      "success_url": success_url, "cancel_url": cancel_url},
                headers=_api_headers(),
                timeout=10,
            )
        if res.status_code != 200:
            await interaction.followup.send(f"❌ 拡張 URL の生成に失敗しました: {res.text}", ephemeral=True)
            return
        url = res.json().get("url", "")
        plan_name = plan.get("plan_name", "light")
        unit_price = 400 if plan_name == "light" else 100
        try:
            await interaction.user.send(
                f"✅ **お題容量拡張 +{units * 100}件（¥{unit_price * units}）**\n\n{url}\n\n"
                "このリンクから決済を完了してください。"
            )
            await interaction.followup.send("📬 DM に決済リンクを送りました。", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send(
                f"📬 DM が送れませんでした。直接このリンクをご利用ください:\n{url}", ephemeral=True
            )
    except Exception as e:
        await interaction.followup.send(f"❌ エラーが発生しました: {e}", ephemeral=True)


# ---- お題コマンド（Light 以上）----

@bot.tree.command(name="odai_add", description="画像を添付してお題を登録します")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(file="登録するお題画像（jpg/png/webp）", tags="タグ（カンマ区切り、省略可）")
async def odai_add(interaction: discord.Interaction, file: discord.Attachment, tags: str = None):
    factory = OdaiFactory(interaction.guild_id)

    if not _has_discord_op(interaction.guild_id, factory.db):
        await interaction.response.send_message(
            "⚠️ このコマンドは Light プラン以上でご利用いただけます。", ephemeral=True
        )
        return

    ok, msg = _check_capacity(interaction.guild_id, factory.db)
    if not ok:
        await interaction.response.send_message(f"⚠️ {msg}", ephemeral=True)
        return

    if file.content_type not in _ALLOWED_MIME:
        await interaction.response.send_message("⚠️ jpg / png / webp のみ登録できます。", ephemeral=True)
        return

    if file.size > _MAX_ODAI_BYTES:
        await interaction.response.send_message("⚠️ ファイルサイズは 8 MB 以下にしてください。", ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)
    content = await file.read()
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    odai_repo = factory.getOdaiRepository()
    success, message = odai_repo.add_odai(interaction.guild_id, file.filename, content, tag_list)
    if success:
        await interaction.followup.send(f"✅ {message}", ephemeral=True)
    else:
        await interaction.followup.send(f"❌ {message}", ephemeral=True)


@bot.tree.command(name="odai_list", description="登録済みお題の一覧を表示します")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(page="ページ番号（デフォルト: 1）")
async def odai_list(interaction: discord.Interaction, page: int = 1):
    factory = OdaiFactory(interaction.guild_id)

    if not _has_discord_op(interaction.guild_id, factory.db):
        await interaction.response.send_message(
            "⚠️ このコマンドは Light プラン以上でご利用いただけます。", ephemeral=True
        )
        return

    total_row = factory.db.query_one(
        "SELECT COUNT(*) AS cnt FROM odai WHERE guild_id = %s AND deleted_at IS NULL",
        (interaction.guild_id,),
    )
    total = total_row["cnt"] if total_row else 0
    total_pages = max(1, (total + _ODAI_PER_PAGE - 1) // _ODAI_PER_PAGE)
    page = max(1, min(page, total_pages))
    offset = (page - 1) * _ODAI_PER_PAGE

    rows = factory.db.query(
        "SELECT filename, added_at FROM odai WHERE guild_id = %s AND deleted_at IS NULL "
        "ORDER BY added_at DESC LIMIT %s OFFSET %s",
        (interaction.guild_id, _ODAI_PER_PAGE, offset),
    )

    if not rows:
        await interaction.response.send_message("📭 お題が登録されていません。", ephemeral=True)
        return

    lines = [f"`{r['filename']}`" for r in rows]
    body = "\n".join(lines)
    await interaction.response.send_message(
        f"📋 **お題一覧** ({page} / {total_pages} ページ、全 {total} 件)\n\n{body}",
        ephemeral=True,
    )


@bot.tree.command(name="odai_delete", description="お題をファイル名で削除します")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(filename="削除するお題のファイル名")
async def odai_delete(interaction: discord.Interaction, filename: str):
    factory = OdaiFactory(interaction.guild_id)

    if not _has_discord_op(interaction.guild_id, factory.db):
        await interaction.response.send_message(
            "⚠️ このコマンドは Light プラン以上でご利用いただけます。", ephemeral=True
        )
        return

    odai_repo = factory.getOdaiRepository()
    result = odai_repo.remove_odai(interaction.guild_id, filename)
    await interaction.response.send_message(result, ephemeral=True)


# ---- スケジュールコマンド（Light 以上）----

@bot.tree.command(name="schedule_add", description="お題の自動投稿スケジュールを追加します")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(time="投稿時刻（HH:MM 形式、例: 09:00）", channel="投稿先チャンネル")
async def schedule_add(interaction: discord.Interaction, time: str, channel: discord.TextChannel):
    factory = OdaiFactory(interaction.guild_id)

    if not _has_discord_op(interaction.guild_id, factory.db):
        await interaction.response.send_message(
            "⚠️ このコマンドは Light プラン以上でご利用いただけます。", ephemeral=True
        )
        return

    if not re.match(r"^\d{2}:\d{2}$", time):
        await interaction.response.send_message("⚠️ 時刻は HH:MM 形式で入力してください（例: 09:00）。", ephemeral=True)
        return

    schedule_repo = factory.scheduleRepository
    existing = factory.db.query_one(
        "SELECT id FROM schedules WHERE guild_id = %s AND channel_id = %s AND time = %s",
        (interaction.guild_id, channel.id, time),
    )
    if existing:
        await interaction.response.send_message(
            f"⚠️ {channel.mention} の {time} はすでに登録されています。", ephemeral=True
        )
        return

    schedule_repo.save({
        "guild_id": interaction.guild_id,
        "channel_id": channel.id,
        "time": time,
        "enabled": True,
        "tag_mode": "all",
        "tag_list": [],
    })
    await interaction.response.send_message(
        f"✅ スケジュールを追加しました: {time} → {channel.mention}", ephemeral=True
    )


@bot.tree.command(name="schedule_list", description="登録済みのスケジュール一覧を表示します")
@app_commands.default_permissions(administrator=True)
async def schedule_list(interaction: discord.Interaction):
    factory = OdaiFactory(interaction.guild_id)

    if not _has_discord_op(interaction.guild_id, factory.db):
        await interaction.response.send_message(
            "⚠️ このコマンドは Light プラン以上でご利用いただけます。", ephemeral=True
        )
        return

    rows = factory.db.query(
        "SELECT s.id, s.time, s.channel_id, c.name AS channel_name "
        "FROM schedules s LEFT JOIN channels c ON c.guild_id = s.guild_id AND c.channel_id = s.channel_id "
        "WHERE s.guild_id = %s AND s.enabled = 1 ORDER BY s.time",
        (interaction.guild_id,),
    )
    if not rows:
        await interaction.response.send_message("📭 スケジュールが登録されていません。", ephemeral=True)
        return

    lines = []
    for r in rows:
        ch = f"#{r['channel_name']}" if r.get("channel_name") else f"<#{r['channel_id']}>"
        lines.append(f"`{r['time']}` → {ch}")
    await interaction.response.send_message(
        f"📅 **スケジュール一覧**（{len(rows)} 件）\n\n" + "\n".join(lines),
        ephemeral=True,
    )


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
