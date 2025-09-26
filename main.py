import discord
from discord import app_commands
from discord.ext import commands
from typing import Optional
from dotenv import load_dotenv
import os
from utils.template_view import TemplateGalleryView
from service.odai_service import (
    handle_register_text,
    handle_setup_guild,
    handle_register_image,
    handle_generate_odai,
)

# TemplateService を利用する
from service.template_service import TemplateService
from repository.template_repository import TemplateRepository
from db.connection import get_connection

load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ===== フォント選択肢（固定） =====
font_choices = [
    app_commands.Choice(name="NotoSansJP-Regular.ttf", value="NotoSansJP-Regular.ttf"),
    app_commands.Choice(name="ヒラギノ角ゴシック W6.ttc", value="ヒラギノ角ゴシック W6.ttc"),
    app_commands.Choice(name="ヒラギノ丸ゴ ProN W4.ttc", value="ヒラギノ丸ゴ ProN W4.ttc"),
    app_commands.Choice(name="ヒラギノ明朝 ProN.ttc", value="ヒラギノ明朝 ProN.ttc"),
]

# ===== Bot起動時 =====
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(f"Sync failed: {e}")

# ===== Guild 登録 =====
@app_commands.checks.has_permissions(manage_guild=True)
@bot.tree.command(name="setup_guild", description="このサーバーとチャンネルを登録（管理者のみ）")
async def setup_guild(interaction: discord.Interaction):
    await handle_setup_guild(interaction)

# ===== お題関連 =====
@bot.tree.command(name="register_text", description="テキストお題を登録します")
@app_commands.describe(content="登録したいお題のテキスト")
async def register_text(interaction: discord.Interaction, content: str):
    await handle_register_text(interaction, content)

@bot.tree.command(name="register_image", description="画像ファイルを登録します（添付必須）")
@app_commands.describe(attachment="アップロードする画像ファイル")
async def register_image(interaction: discord.Interaction, attachment: discord.Attachment):
    await handle_register_image(interaction, attachment)

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

# ===== テンプレート関連 =====
@bot.tree.command(name="register_template", description="背景テンプレート画像を登録します（最大5件）")
@app_commands.describe(
    name="テンプレート名（表示名）",
    image="アップロードする画像ファイル"
)
async def register_template(interaction: discord.Interaction, name: str, image: discord.Attachment):
    binary = await image.read()
    # Service呼び出し
    file_path = f"templates/{interaction.guild.id}_{name}.png"
    with open(file_path, "wb") as f:
        f.write(binary)

    try:
        bot.template_service.register(
            guild_id=interaction.guild.id,
            filename=image.filename,
            display_name=name,
            file_path=file_path,
            file_size=len(binary),
            created_by=interaction.user.id
        )
        await interaction.response.send_message(f"✅ テンプレート `{name}` を登録しました。", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"❌ {str(e)}", ephemeral=True)



# @bot.tree.command(name="list_templates", description="登録済みテンプレートをページ送りで表示します")
# async def list_templates(interaction: discord.Interaction):
#     svc = interaction.client.template_service
#     items = svc.list(interaction.guild.id)
#     if not items:
#         await interaction.response.send_message("テンプレートが登録されていません。", ephemeral=True)
#         return

#     view = TemplatePagerView(items, per_page=1)
#     embed, files = view.build_embed_and_files()

#     # embed と files をセットで送ること！
#     await interaction.response.send_message(
#         content="📦 登録済みテンプレート一覧",
#         embeds=[embed],
#         files=files,
#         view=view
#     )

@bot.tree.command(
    name="list_templates_gallery",
    description="登録済みテンプレートをサムネ付きで複数件/ページ表示します"
)
async def list_templates_gallery(interaction: discord.Interaction, per_page: int = 4):
    svc = interaction.client.template_service
    items = svc.list(interaction.guild.id)
    if not items:
        await interaction.response.send_message("テンプレートが登録されていません。", ephemeral=True)
        return

    # per_page は 1〜10 の範囲に収まるよう View 側でも制限しています
    view = TemplateGalleryView(items, per_page=per_page)
    embeds, files = view.build_payload()
    await interaction.response.send_message(embeds=embeds, files=files, view=view)

# ===== 補完（テンプレート名） =====
@generate_odai_cmd.autocomplete('template_name')
async def template_name_autocomplete(
    interaction: discord.Interaction,
    current: str
) -> list[app_commands.Choice[str]]:
    templates = bot.template_service.list(interaction.guild.id)
    return [
        app_commands.Choice(name=t.display_name, value=t.display_name)
        for t in templates if current.lower() in t.display_name.lower()
    ][:25]

# ===== Bot DI 初期化 =====
def bootstrap_bot(bot):
    repo = TemplateRepository()
    bot.template_service = TemplateService(repo)

bootstrap_bot(bot)

bot.run(TOKEN)
