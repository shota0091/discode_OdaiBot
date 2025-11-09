from discord import Embed

class ScheduleListView:
    @staticmethod
    def build(guild, schedules):
        embed = Embed(
            title=f"⏱️ 登録済みスケジュール（{len(schedules)}件）",
            color=0x3498db
        )

        for s in schedules:
            channel = guild.get_channel(s.channel_id)
            channel_name = channel.mention if channel else f"ID: {s.channel_id}"

            embed.add_field(
                name=channel_name,
                value=f"🕒 {s.time}",
                inline=False
            )

        return embed
