from Repository.MySQLDatabase import MySQLDatabase

class OdaiRepository:
    def __init__(self, db: MySQLDatabase):
        self.db = db

    def load(self, guild_id: int, include_deleted: bool = False):
        return self.load_all(guild_id, include_deleted)

    def load_all(self, guild_id: int, include_deleted: bool = False):
        sql = "SELECT id, guild_id, filename, storage_path, used, added_at, deleted_at FROM odai WHERE guild_id = %s"
        params = [guild_id]
        if not include_deleted:
            sql += " AND deleted_at IS NULL"
        rows = self.db.query(sql, tuple(params))
        return [self._attach_tags(row) for row in rows]

    def load_for_channel(self, guild_id: int, channel_id: int | None):
        """チャンネルの odai_usage に含まれない（未投稿の）お題を返す。channel_id が None の場合は used=0 のお題を返す。"""
        if channel_id is None:
            rows = self.db.query(
                "SELECT id, guild_id, filename, storage_path, used, added_at, deleted_at "
                "FROM odai WHERE guild_id = %s AND used = 0 AND deleted_at IS NULL",
                (guild_id,),
            )
        else:
            # チャンネル単位の odai_usage で管理するため used フラグは参照しない
            rows = self.db.query(
                "SELECT id, guild_id, filename, storage_path, used, added_at, deleted_at "
                "FROM odai WHERE guild_id = %s AND deleted_at IS NULL "
                "AND id NOT IN (SELECT odai_id FROM odai_usage WHERE guild_id = %s AND channel_id = %s)",
                (guild_id, guild_id, channel_id),
            )
        return [self._attach_tags(row) for row in rows]

    def record_usage(self, guild_id: int, channel_id: int, odai_id: int):
        """お題をチャンネルの投稿済みとして記録する。"""
        self.db.execute(
            "INSERT IGNORE INTO odai_usage (guild_id, channel_id, odai_id) VALUES (%s, %s, %s)",
            (guild_id, channel_id, odai_id),
            commit=False,
        )
        self.db.execute(
            "UPDATE odai SET used = 1 WHERE id = %s",
            (odai_id,),
            commit=True,
        )
        channel = self.db.query_one(
            "SELECT name FROM channels WHERE guild_id = %s AND channel_id = %s",
            (guild_id, channel_id),
        )
        channel_label = f"#{channel['name']}" if channel else f"#{channel_id}"
        self.db.execute(
            "INSERT INTO odai_history (odai_id, guild_id, action, detail) VALUES (%s, %s, %s, %s)",
            (odai_id, guild_id, "posted", channel_label),
            commit=True,
        )

    def reset_channel_usage(self, guild_id: int, channel_id: int):
        """チャンネルの投稿済み記録をリセットする（全件使い切り時に呼び出す）。"""
        self.db.execute(
            "DELETE FROM odai_usage WHERE guild_id = %s AND channel_id = %s",
            (guild_id, channel_id),
            commit=True,
        )

    def _attach_tags(self, odai):
        odai["tags"] = self.get_tags(odai["id"])
        return odai

    def get_tags(self, odai_id: int):
        rows = self.db.query(
            "SELECT t.name FROM tags t "
            "JOIN odai_tags ot ON ot.tag_id = t.id "
            "WHERE ot.odai_id = %s",
            (odai_id,),
        )
        return [row["name"] for row in rows]

    def file_exists(self, guild_id: int, filename: str) -> bool:
        return self.db.query_one(
            "SELECT 1 FROM odai WHERE guild_id = %s AND filename = %s AND deleted_at IS NULL",
            (guild_id, filename),
        ) is not None

    def add_odai(self, guild_id: int, filename: str, content: bytes, tags=None, storage_path: str | None = None, created_by: int | None = None):
        if self.file_exists(guild_id, filename):
            return False, f"❌ 同名ファイルが既に存在します：{filename}"

        cursor = self.db.execute(
            "INSERT INTO odai (guild_id, filename, storage_path, data, created_by) VALUES (%s, %s, %s, %s, %s)",
            (guild_id, filename, storage_path, content, created_by),
            commit=True,
        )
        odai_id = cursor.lastrowid

        if tags:
            for tag_name in tags:
                tag_id = self._ensure_tag(guild_id, tag_name, created_by=created_by)
                self.db.execute(
                    "INSERT IGNORE INTO odai_tags (odai_id, tag_id, created_by) VALUES (%s, %s, %s)",
                    (odai_id, tag_id, created_by),
                    commit=False,
                )
            self.db.conn.commit()

        return True, f"お題を登録しました：{filename}"

    def get_odai_data(self, odai_id: int):
        return self.db.query_one(
            "SELECT id, filename, storage_path, data FROM odai WHERE id = %s AND deleted_at IS NULL",
            (odai_id,),
        )

    def remove_odai(self, guild_id: int, filename: str) -> str:
        row = self.db.query_one(
            "SELECT id FROM odai WHERE guild_id = %s AND filename = %s AND deleted_at IS NULL",
            (guild_id, filename),
        )
        if not row:
            return f"⚠️ {filename} は登録されていません"

        self.db.execute(
            "UPDATE odai SET deleted_at = CURRENT_TIMESTAMP WHERE id = %s",
            (row["id"],),
            commit=True,
        )

        return f"🗑️ {filename} を削除しました（再登録可能）"

    def _ensure_tag(self, guild_id: int, tag_name: str, created_by: int | None = None) -> int:
        row = self.db.query_one(
            "SELECT id FROM tags WHERE guild_id = %s AND name = %s",
            (guild_id, tag_name),
        )
        if row:
            return row["id"]

        cursor = self.db.execute(
            "INSERT INTO tags (guild_id, name, created_by) VALUES (%s, %s, %s)",
            (guild_id, tag_name, created_by),
            commit=True,
        )
        return cursor.lastrowid
