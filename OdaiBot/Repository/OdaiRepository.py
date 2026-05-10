import os
from pathlib import Path

from Repository.MySQLDatabase import MySQLDatabase

_IMAGE_DIR = Path(os.getenv("ODAI_IMAGE_DIR", "/data/odai"))


class OdaiRepository:
    def __init__(self, db: MySQLDatabase):
        self.db = db

    def load(self, guild_id: int, include_deleted: bool = False):
        return self.load_all(guild_id, include_deleted)

    def load_all(self, guild_id: int, include_deleted: bool = False):
        sql = "SELECT id, guild_id, filename, storage_path, added_at, deleted_at FROM odai WHERE guild_id = %s"
        params = [guild_id]
        if not include_deleted:
            sql += " AND deleted_at IS NULL"
        rows = self.db.query(sql, tuple(params))
        return [self._attach_tags(row) for row in rows]

    def get_plan_info(self, guild_id: int) -> dict:
        """プラン情報を返す。guild_plansがなければfreeのデフォルト値を返す。"""
        row = self.db.query_one(
            "SELECT p.name, p.custom_odai_base FROM guild_plans gp JOIN plans p ON gp.plan_id = p.id WHERE gp.guild_id = %s",
            (guild_id,),
        )
        if not row:
            free = self.db.query_one("SELECT name, custom_odai_base FROM plans WHERE name = 'free'", ())
            return free or {"name": "free", "custom_odai_base": 10}
        return row

    def load_for_channel(self, guild_id: int, channel_id: int | None, include_defaults: bool = False):
        """チャンネルの odai_usage に含まれない（未投稿の）お題を返す。
        include_defaults=True のとき guild_default_odai のお題も候補に加える。
        プランのcustom_odai_baseに基づき投稿候補を最新N件に制限する（NULLは無制限）。
        """
        if channel_id is None:
            custom_rows = self.db.query(
                "SELECT id, guild_id, filename, storage_path, added_at, deleted_at "
                "FROM odai WHERE guild_id = %s AND deleted_at IS NULL",
                (guild_id,),
            )
        else:
            custom_rows = self.db.query(
                "SELECT id, guild_id, filename, storage_path, added_at, deleted_at "
                "FROM odai WHERE guild_id = %s AND deleted_at IS NULL "
                "AND id NOT IN (SELECT odai_id FROM odai_usage WHERE guild_id = %s AND channel_id = %s)",
                (guild_id, guild_id, channel_id),
            )

        rows = list(custom_rows)

        plan_info = self.get_plan_info(guild_id)
        limit = plan_info.get("custom_odai_base")  # None = 無制限
        if limit is not None and len(rows) > limit:
            rows = sorted(rows, key=lambda r: r["id"], reverse=True)[:limit]

        if include_defaults:
            if channel_id is None:
                default_rows = self.db.query(
                    "SELECT d.id, d.filename, d.storage_path "
                    "FROM guild_default_odai gdo JOIN default_odai d ON gdo.default_odai_id = d.id "
                    "WHERE gdo.guild_id = %s AND d.is_active = 1",
                    (guild_id,),
                )
            else:
                default_rows = self.db.query(
                    "SELECT d.id, d.filename, d.storage_path "
                    "FROM guild_default_odai gdo JOIN default_odai d ON gdo.default_odai_id = d.id "
                    "WHERE gdo.guild_id = %s AND d.is_active = 1 "
                    "AND d.id NOT IN (SELECT odai_id FROM odai_usage WHERE guild_id = %s AND channel_id = %s)",
                    (guild_id, guild_id, channel_id),
                )
            seen = {r["id"] for r in rows}
            for r in default_rows:
                if r["id"] not in seen:
                    # default_odai は guild_id / added_at / deleted_at を持たないので補完
                    rows.append({**r, "guild_id": None, "added_at": None, "deleted_at": None, "tags": []})
                    seen.add(r["id"])

        # tags が補完済みの行（デフォルトお題）はスキップ
        return [row if "tags" in row else self._attach_tags(row) for row in rows]

    def record_usage(self, guild_id: int, channel_id: int, odai_id: int):
        """お題をチャンネルの投稿済みとして記録する。"""
        self.db.execute(
            "INSERT IGNORE INTO odai_usage (guild_id, channel_id, odai_id) VALUES (%s, %s, %s)",
            (guild_id, channel_id, odai_id),
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

    def _image_path(self, guild_id: int, filename: str) -> Path:
        return _IMAGE_DIR / str(guild_id) / filename

    def file_exists(self, guild_id: int, filename: str) -> bool:
        return self.db.query_one(
            "SELECT 1 FROM odai WHERE guild_id = %s AND filename = %s AND deleted_at IS NULL",
            (guild_id, filename),
        ) is not None

    def add_odai(self, guild_id: int, filename: str, content: bytes, tags=None, storage_path: str | None = None, created_by: int | None = None):
        if self.file_exists(guild_id, filename):
            return False, f"❌ 同名ファイルが既に存在します：{filename}"

        img_path = self._image_path(guild_id, filename)
        img_path.parent.mkdir(parents=True, exist_ok=True)
        img_path.write_bytes(content)

        cursor = self.db.execute(
            "INSERT INTO odai (guild_id, filename, storage_path, created_by) VALUES (%s, %s, %s, %s)",
            (guild_id, filename, str(img_path), created_by),
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

    def get_odai_data(self, odai_id: int, is_default: bool = False):
        if is_default:
            row = self.db.query_one(
                "SELECT id, filename, storage_path FROM default_odai WHERE id = %s AND is_active = 1",
                (odai_id,),
            )
        else:
            row = self.db.query_one(
                "SELECT id, filename, storage_path FROM odai WHERE id = %s AND deleted_at IS NULL",
                (odai_id,),
            )
        if not row:
            return None
        if row.get("storage_path"):
            p = Path(row["storage_path"])
            if p.exists():
                row["data"] = p.read_bytes()
        return row

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
