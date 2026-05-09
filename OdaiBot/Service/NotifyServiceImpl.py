import io
import random
import discord
from Interface.NotifyServiceInterface import NotifyServiceInterface
from Repository.OdaiRepository import OdaiRepository
from Repository.MySQLDatabase import MySQLDatabase

class NotifyServiceImpl(NotifyServiceInterface):
    def __init__(self, odaiRepository: OdaiRepository, db: MySQLDatabase):
        self.repo = odaiRepository
        self.db = db

    def _use_default_odai(self, guild_id: int) -> bool:
        row = self.db.query_one(
            "SELECT use_default_odai FROM guild_settings WHERE guild_id = %s", (guild_id,)
        )
        return bool(row.get("use_default_odai", 1)) if row else False

    def select_candidate(self, guild_id: int, channel_id: int | None = None, schedule: dict | None = None):
        include_defaults = self._use_default_odai(guild_id)
        candidates = self.repo.load_for_channel(guild_id, channel_id, include_defaults=include_defaults)
        if not candidates and channel_id is not None:
            self.repo.reset_channel_usage(guild_id, channel_id)
            candidates = self.repo.load_for_channel(guild_id, channel_id, include_defaults=include_defaults)

        filtered = [
            odai for odai in candidates
            if self._matches_schedule_filter(odai, schedule)
        ]
        return random.choice(filtered) if filtered else None

    def _matches_schedule_filter(self, odai: dict, schedule: dict | None) -> bool:
        if not schedule:
            return True

        mode = schedule.get("tag_mode", "all")
        tag_list = set(schedule.get("tag_list") or [])
        odai_tags = set(odai.get("tags", []))

        if mode == "allow":
            return bool(odai_tags & tag_list)
        if mode == "deny":
            return not bool(odai_tags & tag_list)
        return True

    def record_post_history(self, guild_id: int, channel_id: int, odai_id: int, result: str, message: str | None = None):
        self.db.execute(
            "INSERT INTO post_history (guild_id, channel_id, odai_id, result, message) VALUES (%s, %s, %s, %s, %s)",
            (guild_id, channel_id, odai_id, result, message),
            commit=True,
        )

    async def send_notify_odai(self, channel, schedule: dict | None = None):
        guild_id = channel.guild.id
        candidate = self.select_candidate(guild_id, channel.id, schedule)
        if not candidate:
            return False, "⚠️ 投稿候補のお題が見つかりません"

        is_default = candidate.get("guild_id") is None
        odai_data = self.repo.get_odai_data(candidate["id"], is_default=is_default)
        if not odai_data:
            return False, "⚠️ お題データが見つかりませんでした"

        try:
            file_bytes = io.BytesIO(odai_data["data"])
            await channel.send(file=discord.File(file_bytes, filename=odai_data["filename"]))
            self.repo.record_usage(guild_id, channel.id, candidate["id"])
            self.record_post_history(guild_id, channel.id, candidate["id"], "success", None)
            return True, candidate
        except Exception as e:
            self.record_post_history(guild_id, channel.id, candidate["id"], "failed", str(e))
            return False, str(e)
