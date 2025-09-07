import discord
import os
from repository.odai_repository import (
    insert_odai,
    ensure_guild_and_channel,
    insert_image_file,
    get_image_path_by_filename,
    get_latest_templates,
    get_template_by_display_name
)
from entity.odai_item import OdaiItem
from utils.file_helper import save_uploaded_image
from utils.image_generator import generate_odai_image, generate_blank_image_with_text
from utils.odai_image import generate_odai_image_with_title
# /setup_guild コマンド用
async def handle_setup_guild(interaction):
    guild_id = interaction.guild.id
    guild_name = interaction.guild.name
    channel_id = interaction.channel.id
    channel_name = interaction.channel.name

    try:
        ensure_guild_and_channel(guild_id, guild_name, channel_id, channel_name)
        await interaction.response.send_message(
            f"✅ 登録完了！\nGuild: `{guild_name}`\nChannel: `{channel_name}`",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(f"❌ 登録失敗: {str(e)}", ephemeral=True)

# /register_text コマンド用
async def handle_register_text(interaction, content: str):
    try:
        odai = OdaiItem(
            id=None,
            guild_id=interaction.guild.id,
            channel_id=interaction.channel.id,
            content=content,
            image_path=None,
            is_sent=False,
            created_by=interaction.user.id,
            created_at=None
        )
        insert_odai(odai)
        await interaction.response.send_message(f"✅ お題を登録しました：\n```{content}```")
    except Exception as e:
        await interaction.response.send_message(f"❌ 登録中にエラーが発生しました: {str(e)}", ephemeral=True)

# /register_image コマンド用
async def handle_register_image(interaction, attachment: discord.Attachment):
    original_filename = attachment.filename
    binary_data = await attachment.read()

    try:
        file_path, file_type, file_size = save_uploaded_image(
            guild_id=interaction.guild.id,
            original_filename=original_filename,
            binary_data=binary_data
        )

        relative_path = file_path.replace("\\", "/")
        filename = os.path.basename(relative_path)

        insert_image_file(
            guild_id=interaction.guild.id,
            user_id=interaction.user.id,
            filename=filename,
            file_path=relative_path,
            file_type=file_type,
            file_size=file_size
        )

        await interaction.response.send_message(
            f"✅ 画像登録完了！\nファイル名: `{filename}`\nサイズ: `{round(file_size/1024, 2)} KB`",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ 登録失敗: {str(e)}",
            ephemeral=True
        )

# /generate_odairegister_image コマンド用
async def handle_generate_odai(
    interaction,
    text,
    template_name,
    font_name,
    text_color,
    font_size,
    shadow
):
    use_template = bool(template_name)  # ← テンプレ指定があれば使う
    if use_template:
        template = get_template_by_display_name(interaction.guild_id, template_name)
        if not template:
            await interaction.response.send_message("テンプレートが見つかりません。", ephemeral=True)
            return

        image_path = generate_odai_image_with_title(
            template_path=template.file_path,
            title="今日のお題",
            text=text,
            font_path=f"font/{font_name}",
            text_color=text_color,
            font_size=font_size,
            shadow=shadow
        )
    else:
        image_path = generate_blank_image_with_text(
            text=text,
            font_path=f"font/{font_name}",
            text_color=text_color,
            font_size=font_size,
            shadow=shadow
        )

    file = discord.File(image_path)
    await interaction.response.send_message(
        content="✅ 合成お題を登録しました！",
        file=file
    )

async def handle_register_template_image(interaction, name: str, image: discord.Attachment):
    from utils.file_helper import save_template_image
    from repository.odai_repository import insert_template_file
    import os

    try:
        original_filename = image.filename
        binary_data = await image.read()

        # 保存
        file_path, file_type, file_size = save_template_image(
            guild_id=interaction.guild.id,
            original_filename=original_filename,
            binary_data=binary_data
        )
        filename = os.path.basename(file_path).replace("\\", "/")
        relative_path = file_path.replace("\\", "/")

        # DB登録
        insert_template_file(
            guild_id=interaction.guild.id,
            filename=filename,
            display_name=name,
            file_path=relative_path,
            file_size=file_size,
            created_by=interaction.user.id
        )

        await interaction.response.send_message(
            f"✅ テンプレート登録完了！\nテンプレ名: `{name}`\nファイル名: `{filename}`",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ 登録失敗: {str(e)}",
            ephemeral=True
        )

async def handle_list_templates(interaction: discord.Interaction):
    await interaction.response.defer()

    templates = get_latest_templates(interaction.guild_id)

    if not templates:
        await interaction.followup.send("テンプレートが登録されていません。")
        return

    embeds = []
    files = []

    for i, template in enumerate(templates, start=1):
        file_path = os.path.join(template.file_path)  # 相対パス前提（例：templates/2025-09/xxxx.png）
        if not os.path.exists(file_path):
            continue  # ファイルが無いものはスキップ

        file = discord.File(file_path, filename=os.path.basename(file_path))
        embed = discord.Embed(title=f"{i}. {template.display_name}", color=discord.Color.orange())
        embed.set_image(url=f"attachment://{os.path.basename(file_path)}")

        embeds.append(embed)
        files.append(file)

    if not embeds:
        await interaction.followup.send("❌ ファイルが見つかりませんでした")
        return

    await interaction.followup.send(
        content=f"📦 登録済みテンプレート一覧（最大{len(embeds)}件）",
        embeds=embeds,
        files=files
    )
