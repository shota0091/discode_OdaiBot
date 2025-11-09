from Interface.ScheduleServiceInterface import ScheduleServiceInterface
from Repository.ScheduleRepository import ScheduleRepository
from .NotifyServiceImpl import NotifyServiceImpl
from Entity.ScheduleEntity import ScheduleEntity
from datetime import datetime
import discord

class ScheduleServiceImpl(ScheduleServiceInterface):
    def __init__(self, guild_id: int, scheduleRepository: ScheduleRepository, notifyService: NotifyServiceImpl):
        self.guild_id = guild_id
        self.scheduleRepository = scheduleRepository
        self.notifyService = notifyService

    def save(self, channelId: int, time: str) -> str:
        schedules = self.scheduleRepository.load()
        schedules = [s for s in schedules if s.channel_id != channelId]
        schedules.append(ScheduleEntity(channel_id=channelId, time=time))
        self.scheduleRepository.save(schedules)

        return f"✅ 毎日 {time} に <#{channelId}> にお題を送信します！"

    def update_time(self, channel_id: int, new_time: str):
        schedules = self.scheduleRepository.load()

        found = False
        for s in schedules:
            if s.channel_id == channel_id:
                s.time = new_time
                found = True
                break
    
        if not found:
            return False, f"⚠️ チャンネル <#{channel_id}> の設定が見つかりません"

        self.scheduleRepository.save(schedules)
        return True, f"✅ <#{channel_id}> の通知時刻を **{new_time}** に更新しました！"

    def delete(self, channel_id: int) -> str:
        schedules = self.scheduleRepository.load()
        new_list = [s for s in schedules if s.channel_id != channel_id]

        if len(new_list) == len(schedules):
            return f"⚠️ <#{channel_id}> のスケジュールは登録されていません"

        self.scheduleRepository.save(new_list)
        return f"🗑️ <#{channel_id}> のスケジュールを削除しました！"

    async def run(self, bot):
        schedules = self.scheduleRepository.load()
        now = datetime.now().strftime("%H:%M")

        for s in schedules:
            if s.time == now:
                file_path = self.notifyService.sendNotifyOdai()
                channel = bot.get_channel(s.channel_id)
                if channel:
                    await channel.send(file=discord.File(file_path))
