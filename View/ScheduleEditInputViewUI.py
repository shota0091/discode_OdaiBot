import discord
from discord.ui import View, Button, TextInput, Modal
from Factory.OdaiFactory import OdaiFactory
from .ScheduleListView import ScheduleListView
import re

class ScheduleEditInputViewUI(View):
    def __init__(self, guild_id, channel_id):
        super().__init__(timeout=180)
        self.guild_id = guild_id
        self.channel_id = channel_id

        submit_btn = Button(label="時刻を入力", style=discord.ButtonStyle.primary)
        submit_btn.callback = self.open_modal
        self.add_item(submit_btn)

        cancel_btn = Button(label="キャンセル", style=discord.ButtonStyle.secondary)
        cancel_btn.callback = self.cancel
        self.add_item(cancel_btn)

    async def open_modal(self, interaction):
        modal = TimeInputModal(self.guild_id, self.channel_id)
        await interaction.response.send_modal(modal)

    async def cancel(self, interaction):
        factory = OdaiFactory(self.guild_id)
        schedules = factory.getScheduleService().scheduleRepository.load()

        from View.ScheduleListViewUI import ScheduleListViewUI
        embed = ScheduleListView.build(interaction.guild, schedules)
        await interaction.response.edit_message(embed=embed, view=ScheduleListViewUI(self.guild_id))

class TimeInputModal(Modal, title="時刻変更"):
    new_time = TextInput(label="新しい時刻 (HH:MM)", placeholder="例: 21:30")

    def __init__(self, guild_id, channel_id):
        super().__init__()
        self.guild_id = guild_id
        self.channel_id = channel_id

    async def on_submit(self, interaction):
        time = str(self.new_time)

        if not re.match(r"^\d{2}:\d{2}$", time):
            await interaction.response.send_message("❌ 時刻は HH:MM 形式で入力してください", ephemeral=True)
            return

        factory = OdaiFactory(self.guild_id)
        schedule_service = factory.getScheduleService()

        success, msg = schedule_service.update_time(self.channel_id, time)

        # 🔄 変更後 UI をスケジュール一覧に戻す
        from View.ScheduleListViewUI import ScheduleListViewUI
        schedules = schedule_service.scheduleRepository.load()
        embed = ScheduleListView.build(interaction.guild, schedules)

        await interaction.response.edit_message(
            embed=embed,
            view=ScheduleListViewUI(self.guild_id)
        )

        # ✅ 完了メッセージ
        await interaction.followup.send(msg, ephemeral=True)