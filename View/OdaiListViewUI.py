import discord
from discord.ui import View, Button
from Factory.OdaiFactory import OdaiFactory
from View.OdaiListView import OdaiListView

class OdaiListViewUI(View):
    def __init__(self, odai_list, index, image_dir):
        super().__init__(timeout=180)
        self.odai_list = odai_list  # dict list
        self.index = index
        self.image_dir = image_dir

    # ◀️ 前
    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction: discord.Interaction, button: Button):
        self.index = (self.index - 1) % len(self.odai_list)
        await self.update(interaction)

    # ▶️ 次
    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: Button):
        self.index = (self.index + 1) % len(self.odai_list)
        await self.update(interaction)

    # 🗑 削除
    @discord.ui.button(label="🗑 削除", style=discord.ButtonStyle.danger)
    async def delete(self, interaction: discord.Interaction, button: Button):
        target = self.odai_list[self.index]["file"]

        factory = OdaiFactory(interaction.guild_id)
        register_service = factory.getRegisterService()
        repo = factory.getOdaiRepository()

        # 削除
        register_service.remove_odai(target)

        # 最新読み込み
        self.odai_list = repo.load()

        # 0件ならメッセージ消す
        if not self.odai_list:
            await interaction.response.edit_message(
                content=f"🗑 {target} を削除しました（お題が0件です）",
                embed=None,
                attachments=[],
                view=None
            )
            return

        # index補正
        if self.index >= len(self.odai_list):
            self.index = 0

        await self.update(interaction)

    async def update(self, interaction: discord.Interaction):
        odai = self.odai_list[self.index]
        embed, file = OdaiListView.build(odai, self.index, len(self.odai_list), self.image_dir)

        try:
            await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
        except discord.errors.InteractionResponded:
            await interaction.followup.edit_message(
                message_id=interaction.message.id,
                embed=embed, attachments=[file], view=self
            )
