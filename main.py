import discord
from discord.ext import commands
from controller import odai_controller
import os
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f"✅ Botログイン成功: {bot.user}")

odai_controller.register(bot)
bot.run(TOKEN)
