import discord
from discord.ui import View, Button
from View.OdaiListView import OdaiListView

class OdaiListViewUI(View):
    def __init__(self, bot, odai_list, index, image_dir):
        super().__init__(timeout=180)
        self.bot = bot
        self.odai_list = odai_list
        self.index = index
        self.image_dir = image_dir

        # Buttons
        self.prev_button = Button(label="⬅️ Prev")
        self.next_button = Button(label="Next ➡️")
        self.delete_button = Button(style=discord.ButtonStyle.danger, label="🗑️ Delete")

        self.prev_button.callback = self.prev
        self.next_button.callback = self.next
        self.delete_button.callback = self.delete

        self.add_item(self.prev_button)
        self.add_item(self.next_button)
        self.add_item(self.delete_button)

    async def prev(self, interaction: discord.Interaction):
        self.index = (self.index - 1) % len(self.odai_list)
        await self.update(interaction)

    async def next(self, interaction: discord.Interaction):
        self.index = (self.index + 1) % len(self.odai_list)
        await self.update(interaction)

    async def delete(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_messages:
          await interaction.response.send_message("❌ 権限がありません", ephemeral=True)
          return
        target = self.odai_list[self.index].file

        # 呼び出し
        result = self.bot.registerService.remove_odai(target)

        # ローカルリスト更新
        del self.odai_list[self.index]

        if not self.odai_list:
            await interaction.response.edit_message(
                content=f"{result}\n✅ 全てのお題が削除されました。",
                embed=None,
                attachments=[],
                view=None
            )
            return

        # 現在index調整
        self.index %= len(self.odai_list)

        await interaction.response.send_message(result, ephemeral=True)
        await self.update(interaction)

    async def update(self, interaction):
        odai = self.odai_list[self.index]
        embed, file = OdaiListView.build_single(
            odai, self.index, len(self.odai_list), self.image_dir
        )

        if file:
            await interaction.response.edit_message(embed=embed, attachments=[file], view=self)
        else:
            await interaction.response.edit_message(embed=embed, view=self)