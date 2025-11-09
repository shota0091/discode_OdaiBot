import discord
from discord.ui import View, Button
from .ScheduleListView import ScheduleListView
from Factory.OdaiFactory import OdaiFactory

class ScheduleListViewUI(View):
    def __init__(self, guild_id):
        super().__init__(timeout=180)
        self.guild_id = guild_id

        delete_btn = Button(style=discord.ButtonStyle.danger, label="🗑 削除モード")
        edit_btn = Button(style=discord.ButtonStyle.primary, label="🕒 時刻変更")

        delete_btn.callback = self.enter_delete_mode
        edit_btn.callback = self.enter_edit_mode

        self.add_item(delete_btn)
        self.add_item(edit_btn)

    async def enter_delete_mode(self, interaction):
        factory = OdaiFactory(self.guild_id)
        schedules = factory.getScheduleService().scheduleRepository.load()

        from .ScheduleDeleteViewUI import ScheduleDeleteViewUI
        view = ScheduleDeleteViewUI(self.guild_id, schedules, interaction.guild)

        embed = ScheduleListView.build(interaction.guild, schedules)
        await interaction.response.edit_message(embed=embed, view=view)

    async def enter_edit_mode(self, interaction):
        factory = OdaiFactory(self.guild_id)
        schedules = factory.getScheduleService().scheduleRepository.load()

        from View.ScheduleEditChooseViewUI import ScheduleEditChooseViewUI
        view = ScheduleEditChooseViewUI(self.guild_id, schedules, interaction.guild)

        embed = ScheduleListView.build(interaction.guild, schedules)
        await interaction.response.edit_message(embed=embed, view=view)