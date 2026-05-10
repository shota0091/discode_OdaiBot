import json
from Interface.BaseRepositoryInterface import BaseRepositoryInterface
from Repository.MySQLDatabase import MySQLDatabase

class ScheduleRepository(BaseRepositoryInterface):
    def __init__(self, db: MySQLDatabase):
        self.db = db

    def load(self, guild_id: int):
        plan_row = self.db.query_one(
            "SELECT p.name AS plan_name FROM guild_plans gp JOIN plans p ON gp.plan_id = p.id WHERE gp.guild_id = %s",
            (guild_id,),
        )
        plan_name = (plan_row or {}).get("plan_name", "free")

        if plan_name == "free":
            sql = "SELECT * FROM schedules WHERE guild_id = %s AND enabled = 1 ORDER BY id DESC LIMIT 1"
        else:
            sql = "SELECT * FROM schedules WHERE guild_id = %s AND enabled = 1"

        rows = self.db.query(sql, (guild_id,))
        return [self._deserialize(row) for row in rows]

    def save(self, schedule: dict):
        tag_list = json.dumps(schedule.get("tag_list", []), ensure_ascii=False)
        if schedule.get("id"):
            self.db.execute(
                "UPDATE schedules SET channel_id = %s, time = %s, enabled = %s, tag_mode = %s, tag_list = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (
                    schedule["channel_id"],
                    schedule["time"],
                    1 if schedule.get("enabled", True) else 0,
                    schedule.get("tag_mode", "all"),
                    tag_list,
                    schedule["id"],
                ),
                commit=True,
            )
            return schedule["id"]

        cursor = self.db.execute(
            "INSERT INTO schedules (guild_id, channel_id, time, enabled, tag_mode, tag_list) VALUES (%s, %s, %s, %s, %s, %s)",
            (
                schedule["guild_id"],
                schedule["channel_id"],
                schedule["time"],
                1 if schedule.get("enabled", True) else 0,
                schedule.get("tag_mode", "all"),
                tag_list,
            ),
            commit=True,
        )
        return cursor.lastrowid

    def _deserialize(self, row: dict) -> dict:
        return {
            **row,
            "enabled": bool(row.get("enabled")),
            "tag_list": json.loads(row["tag_list"]) if row.get("tag_list") else [],
        }
