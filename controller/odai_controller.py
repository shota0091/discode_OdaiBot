from discord import app_commands, Interaction
from model import odai_model
from view import odai_view

async def send_odai(interaction: Interaction):
    image = odai_model.get_unsent_image()
    if image:
        odai_model.mark_image_sent(image)
        await interaction.followup.send(file=odai_view.make_file(image.filename))
    else:
        await interaction.followup.send("送信可能な画像がありません。")

def register(bot):
    @bot.tree.command(name="odai", description="ランダムなお題画像を送信")
    async def odai_command(interaction: Interaction):
        await interaction.response.defer(thinking=True)  # 👈 一時的な「考え中」表示
        await send_odai(interaction)
