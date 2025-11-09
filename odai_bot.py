import os
from typing import List
import discord
from discord.ext import commands, tasks
from discord import app_commands
from Factory.OdaiFactory import OdaiFactory
from View.OdaiListView import OdaiListView
from View.OdaiListViewUI import OdaiListViewUI
from View.ScheduleListView import ScheduleListView
from View.ScheduleListViewUI import ScheduleListViewUI
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ---- Slash command ----

@bot.tree.command(name="ping", description="Test bot")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message("pong!")

@bot.tree.command(name="odai", description="今日のお題を送信")
@app_commands.default_permissions(administrator=True)
async def send_odai(interaction: discord.Interaction):
    factory = OdaiFactory(interaction.guild_id)
    notify = factory.getNotifyService()

    image_path = notify.sendNotifyOdai()
    await interaction.response.send_message(file=discord.File(image_path))

@bot.tree.command(name="odai_register", description="お題画像を登録")
@app_commands.default_permissions(administrator=True)
async def odai_register(interaction: discord.Interaction, file: discord.Attachment):
    factory = OdaiFactory(interaction.guild_id)
    register_service = factory.getRegisterService()

    await interaction.response.defer(ephemeral=True)

    filename = file.filename
    content = await file.read()

    success, msg = register_service.add_odai(filename, content)

    await interaction.followup.send(
        f"{'✅' if success else '❌'} {msg}",
        ephemeral=True,
    )

@bot.tree.command(name="odai_add", description="画像をまとめて登録")
@app_commands.default_permissions(administrator=True)
async def odai_add(interaction: discord.Interaction):
    await interaction.response.send_message(
        "📎 登録したい画像をこのメッセージの直後に貼ってください（複数可）\n※30秒以内",
        ephemeral=True
    )
    
    # フラグセット
    bot.waiting_for_images = interaction.guild_id

@bot.tree.command(name="odai_list", description="登録済みのお題を表示")
@app_commands.default_permissions(administrator=True)
async def odai_list(interaction: discord.Interaction):
    factory = OdaiFactory(interaction.guild_id)
    repo = factory.getOdaiRepository()
    image_dir = factory.getNotifyService().image_dir  # 画像フォルダ

    odai_list = repo.load()
    if not odai_list:
        await interaction.response.send_message("⚠️ お題がありません")
        return

    first = odai_list[0]
    embed, file = OdaiListView.build(first, 0, len(odai_list), image_dir)

    # ✅ ここを修正：botは渡さない
    view = OdaiListViewUI(odai_list, 0, image_dir)

    await interaction.response.send_message(embed=embed, file=file, view=view)

@bot.tree.command(name="odai_notify", description="お題自動投稿を設定")
@app_commands.default_permissions(administrator=True)
async def odai_notify(interaction: discord.Interaction, time: str, channel: discord.TextChannel):
    factory = OdaiFactory(interaction.guild_id)
    schedule_service = factory.getScheduleService()

    await interaction.response.defer(ephemeral=True)

    # ✅ save_schedule にする
    result = schedule_service.save(channel.id, time)

    await interaction.followup.send(result, ephemeral=True)


@bot.tree.command(name="odai_notify_list", description="スケジュールの確認")
@app_commands.default_permissions(administrator=True)
async def odai_notify_list(interaction: discord.Interaction):
    factory = OdaiFactory(interaction.guild_id)
    schedule_service = factory.getScheduleService()

    schedules = schedule_service.scheduleRepository.load()
    if not schedules:
        await interaction.response.send_message("⚠️ 定期設定はありません", ephemeral=True)
        return

    embed = ScheduleListView.build(interaction.guild, schedules)
    view = ScheduleListViewUI(interaction.guild_id)

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

# ---- Scheduler ----

@tasks.loop(minutes=1)
async def odai_schedule_loop():
    now = datetime.now().strftime("%H:%M")
    print(f"🕒 schedule tick: {now}")

    for guild in bot.guilds:
        factory = OdaiFactory(guild.id)
        schedule_service = factory.getScheduleService()  # ← () 必須！

        print(f"🔎 Checking schedule for guild: {guild.name} ({guild.id})")
        await schedule_service.run(bot)
        

@odai_schedule_loop.before_loop
async def before_odai_schedule_loop():
    print("⏳ スケジューラ起動待機中...")
    await bot.wait_until_ready()
    print("✅ スケジューラ開始！")

# ---- Ready & sync ----

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    guild = message.guild
    if guild is None:
        return
    
    # コマンドでフラグ立ってる？
    if getattr(bot, "waiting_for_images", None) != guild.id:
        return
    
    if not message.attachments:
        return
    
    factory = OdaiFactory(guild.id)
    register = factory.getRegisterService()
    
    results = []
    for attachment in message.attachments:
        filename = attachment.filename
        data = await attachment.read()
        success, msg = register.add_odai(filename, data)
        results.append(f"{'✅' if success else '❌'} {msg}")

    bot.waiting_for_images = None  # フラグ解除
    await message.channel.send("\n".join(results))


@bot.event
async def on_ready():
    try:
        await bot.tree.sync()
        print(f"✅ Logged in as {bot.user}")
    except Exception as e:
        print("❌ Sync error:", e)

    if not odai_schedule_loop.is_running():
        odai_schedule_loop.start()
        print("⏱️ お題定期送信ループ開始")

# ---- Run ----
bot.run(TOKEN)
