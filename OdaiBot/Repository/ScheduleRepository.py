import json
from Interface.BaseRepositoryInterface import BaseRepositoryInterface
from Repository.MySQLDatabase import MySQLDatabase

class ScheduleRepository(BaseRepositoryInterface):
    def __init__(self, db: MySQLDatabase):
        self.db = db

    def load(self, guild_id: int):
        sql = "SELECT * FROM schedules WHERE guild_id = %s AND enabled = 1"
        
        # --- ここで確認 ---
        print(f"DEBUG: 実行SQL: {sql} | パラメータ: {guild_id}")
        rows = self.db.query(sql, (guild_id,))
        print(f"DEBUG: DBから返ってきた生データ: {rows}") 
        # ----------------
        
        return [self._deserialize(row) for row in rows]
        # rows = self.db.query(
        #     "SELECT * FROM schedules WHERE guild_id = %s AND enabled = 1",
        #     (guild_id,),
        # )
        # return [self._deserialize(row) for row in rows]

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
