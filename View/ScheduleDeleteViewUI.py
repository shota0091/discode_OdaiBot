import discord
from discord.ui import View, Button
from Factory.OdaiFactory import OdaiFactory
from .ScheduleListView import ScheduleListView

class ScheduleDeleteViewUI(View):
    def __init__(self, guild_id, schedules, guild):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.schedules = schedules
        self.guild = guild

        for s in schedules:
            channel = guild.get_channel(s.channel_id)
            channel_name = channel.name if channel else "不明チャンネル"

            btn = Button(
                label=f"{s.time} | #{channel_name}",
                style=discord.ButtonStyle.danger
            )
            btn.callback = self.make_delete_handler(s.channel_id)
            self.add_item(btn)

        cancel_btn = Button(label="キャンセル", style=discord.ButtonStyle.secondary)
        cancel_btn.callback = self.cancel
        self.add_item(cancel_btn)

    def make_delete_handler(self, channel_id):
        async def handler(interaction):
            factory = OdaiFactory(self.guild_id)
            schedule_service = factory.getScheduleService()
            schedule_service.delete(channel_id)

            # 再描画 or メッセージ消去
            await interaction.response.edit_message(
                content=f"🗑️ <#{channel_id}> のスケジュールを削除しました！",
                view=None,
                embed=None
            )
        return handler

    async def cancel(self, interaction):
        factory = OdaiFactory(self.guild_id)
        schedules = factory.getScheduleService().scheduleRepository.load()

        from View.ScheduleListViewUI import ScheduleListViewUI
        embed = ScheduleListView.build(interaction.guild, schedules)
        await interaction.response.edit_message(embed=embed, view=ScheduleListViewUI(self.guild_id))
