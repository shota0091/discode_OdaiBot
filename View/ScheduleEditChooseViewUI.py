import discord
from .ScheduleListView import ScheduleListView
from Factory.OdaiFactory import OdaiFactory
from discord.ui import View, Button

class ScheduleEditChooseViewUI(View):
    def __init__(self, guild_id, schedules, guild):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.schedules = schedules
        self.guild = guild


        for s in schedules:
            channel = guild.get_channel(s.channel_id)
            channel_name = f"#{channel.name}" if channel else f"#{s.channel_id}"

            btn = Button(
                label=f"{s.time} | {channel_name}",
                style=discord.ButtonStyle.secondary
            )
            btn.callback = self.make_select_handler(s.channel_id)
            self.add_item(btn)

        cancel_btn = Button(label="キャンセル", style=discord.ButtonStyle.secondary)
        cancel_btn.callback = self.cancel
        self.add_item(cancel_btn)

    def make_select_handler(self, channel_id):
        async def handler(interaction):
            channel = interaction.guild.get_channel(channel_id)
            channel_name = f"#{channel.name}" if channel else f"#{channel_id}"

            from View.ScheduleEditInputViewUI import ScheduleEditInputViewUI
            view = ScheduleEditInputViewUI(self.guild_id, channel_id)

            await interaction.response.edit_message(
                content=f"🕒 {channel_name} の新しい時刻を入力してください (HH:MM)",
                view=view,
                embed=None
            )
        return handler

    async def cancel(self, interaction):  # ✅ これが足りてなかった！
        from View.ScheduleListViewUI import ScheduleListViewUI
        factory = OdaiFactory(self.guild_id)
        schedules = factory.getScheduleService().scheduleRepository.load()

        embed = ScheduleListView.build(interaction.guild, schedules)
        await interaction.response.edit_message(
            embed=embed,
            view=ScheduleListViewUI(self.guild_id)
        )
