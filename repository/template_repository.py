from db.connection import get_connection
from entity.TemplateItem import TemplateItem

class TemplateRepository:
    def count_by_guild(self, guild_id: int) -> int:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM template_files WHERE guild_id=%s", (guild_id,))
            return int(cur.fetchone()["COUNT(*)"])

    def get_by_name(self, guild_id: int, display_name: str):
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, guild_id, filename, display_name, file_path, file_size, created_by, created_at "
                "FROM template_files WHERE guild_id=%s AND display_name=%s",
                (guild_id, display_name)
            )
            row = cur.fetchone()
            return TemplateItem.from_row(row) if row else None

    def insert(self, guild_id, filename, display_name, file_path, file_size, created_by):
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "INSERT INTO template_files (guild_id, filename, display_name, file_path, file_size, created_by) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (guild_id, filename, display_name, file_path, file_size, created_by)
            )
            return cur.lastrowid

    def delete_by_name(self, guild_id: int, display_name: str) -> int:
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM template_files WHERE guild_id=%s AND display_name=%s", (guild_id, display_name))
            return cur.rowcount

    def list_by_guild(self, guild_id: int):
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT id, guild_id, filename, display_name, file_path, file_size, created_by, created_at "
                "FROM template_files WHERE guild_id=%s ORDER BY id DESC",
                (guild_id,)
            )
            return [TemplateItem.from_row(r) for r in cur.fetchall()]
