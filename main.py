import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from dotenv import load_dotenv
from repository.odai_repository import get_latest_templates
import os
from service.odai_service import (
    handle_register_text,
    handle_setup_guild,
    handle_register_image,
    handle_generate_odai,
    handle_register_template_image
)

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True  # 念のため
bot = commands.Bot(command_prefix="!", intents=intents)
# ===== フォント選択肢（固定） =====
font_choices = [
    app_commands.Choice(name="NotoSansJP-Regular.ttf", value="NotoSansJP-Regular.ttf"),
    app_commands.Choice(name="ヒラギノ角ゴシック W6.ttc", value="ヒラギノ角ゴシック W6.ttc"),
    app_commands.Choice(name="ヒラギノ丸ゴ ProN W4.ttc", value="ヒラギノ丸ゴ ProN W4.ttc"),
    app_commands.Choice(name="ヒラギノ明朝 ProN.ttc", value="ヒラギノ明朝 ProN.ttc"),
]


@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Sync failed: {e}")

@app_commands.checks.has_permissions(manage_guild=True)
@bot.tree.command(name="setup_guild", description="このサーバーとチャンネルを登録（管理者のみ）")
async def setup_guild(interaction: discord.Interaction):
    await handle_setup_guild(interaction)

@bot.tree.command(name="register_text", description="テキストお題を登録します")
@app_commands.describe(content="登録したいお題のテキスト")
async def register_text(interaction: discord.Interaction, content: str):
    await handle_register_text(interaction, content)

@bot.tree.command(name="register_image", description="画像ファイルを登録します（添付必須）")
@app_commands.describe(attachment="アップロードする画像ファイル")
async def register_image(interaction: discord.Interaction, attachment: discord.Attachment):
    await handle_register_image(interaction, attachment)

@bot.tree.command(name="register_template_image", description="背景テンプレート画像を登録します")
@app_commands.describe(
    name="テンプレート名（表示名）",
    image="アップロードする画像ファイル"
)
async def register_template_image(interaction: discord.Interaction, name: str, image: discord.Attachment):
    await handle_register_template_image(interaction, name, image)

@app_commands.choices(font_name=font_choices)
@app_commands.describe(
    text="画像に表示するテキスト",
    template_name="テンプレート名（任意）",
    font_name="フォントファイル名",
    text_color="文字色（例：white, black, redなど）",
    font_size="フォントサイズ",
    shadow="影をつけるか？"
)
@bot.tree.command(name="generate_odai", description="お題画像を生成します")
async def generate_odai_cmd(
    interaction: discord.Interaction,
    text: str,
    template_name: Optional[str] = None,
    font_name: str = "NotoSansJP-Regular.ttf",
    text_color: str = "white",
    font_size: int = 64,
    shadow: bool = True
):
    await handle_generate_odai(
        interaction=interaction,
        text=text,
        template_name=template_name,
        font_name=font_name,
        text_color=text_color,
        font_size=font_size,
        shadow=shadow
    )


# ===== テンプレート名を補完表示 =====
@generate_odai_cmd.autocomplete('template_name')
async def template_name_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> list[app_commands.Choice[str]]:
    templates = get_latest_templates(interaction.guild_id)
    return [
        app_commands.Choice(name=t.display_name, value=t.display_name)
        for t in templates if current.lower() in t.display_name.lower()
    ][:25]  # 上限25件


# ===== 起動時にコマンド同期 =====
@bot.event
async def on_ready():
    print(f"{bot.user} でログインしました。")
    await bot.tree.sync()

bot.run(TOKEN)