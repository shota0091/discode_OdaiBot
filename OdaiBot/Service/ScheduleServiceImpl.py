from Interface.ScheduleServiceInterface import ScheduleServiceInterface
from Repository.ScheduleRepository import ScheduleRepository
from .NotifyServiceImpl import NotifyServiceImpl
from datetime import datetime

class ScheduleServiceImpl(ScheduleServiceInterface):
    def __init__(self, guild_id: int, scheduleRepository: ScheduleRepository, notifyService: NotifyServiceImpl):
        self.guild_id = guild_id
        self.scheduleRepository = scheduleRepository
        self.notifyService = notifyService

    def save(self, channel_id: int, time: str) -> str:
        schedule_id = self.scheduleRepository.save(
            {
                "guild_id": self.guild_id,
                "channel_id": channel_id,
                "time": time,
                "enabled": True,
                "tag_mode": "all",
                "tag_list": [],
            }
        )
        return f"✅ 毎日 {time} に <#{channel_id}> にお題を送信します！ (schedule_id={schedule_id})"

    async def run(self, bot):
        print(f"✅ スケジュールサービスが起動しました！ (guild_id={self.guild_id})")
        schedules = self.scheduleRepository.load(self.guild_id)
        print(f"✅ スケジュールサービスが起動しました！ (guild_id={schedules[0]['guild_id'] if schedules else self.guild_id}) スケジュール数={len(schedules)}")
        now = datetime.now().strftime("%H:%M")

        for s in schedules:
            print(f"🔍 スケジュール確認: guild={self.guild_id} channel={s['channel_id']} time={s['time']} tag_mode={s['tag_mode']} tag_list={s['tag_list']}")
            if s["time"] != now:
                continue

            print(f"⏰ スケジュール一致: guild={self.guild_id} channel={s['channel_id']} time={s['time']} tag_mode={s['tag_mode']} tag_list={s['tag_list']}")

            channel = bot.get_channel(s["channel_id"])
            if not channel:
                print(f"❌ チャンネルが見つかりません: channel_id={s['channel_id']} (Bot がチャンネルにアクセスできないか、ID が誤っています)")
                continue

            success, payload = await self.notifyService.send_notify_odai(channel, s)
            if success:
                print(f"✅ 投稿成功: guild={self.guild_id} channel={s['channel_id']} odai_id={payload.get('id') if isinstance(payload, dict) else payload}")
            else:
                print(f"❌ 投稿失敗: guild={self.guild_id} channel={s['channel_id']} error={payload}")
