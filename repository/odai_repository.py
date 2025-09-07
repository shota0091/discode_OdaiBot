# repository/odai_repository.py
from typing import Optional
from db.connection import get_connection
from entity.odai_item import OdaiItem,TemplateItem
from typing import List

def ensure_guild_and_channel(guild_id: int, guild_name: str, channel_id: int, channel_name: str):
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "INSERT INTO guilds (id, name) VALUES (%s, %s) ON DUPLICATE KEY UPDATE name = VALUES(name)",
                (guild_id, guild_name)
            )
            cursor.execute(
                """
                INSERT INTO channels (id, guild_id, name, is_remind_target)
                VALUES (%s, %s, %s, TRUE)
                ON DUPLICATE KEY UPDATE name = VALUES(name), is_remind_target = TRUE
                """,
                (channel_id, guild_id, channel_name)
            )

def insert_odai(odai: OdaiItem):
    sql = """
        INSERT INTO odai_items (guild_id, channel_id, content, image_path, is_sent, created_by)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (
                odai.guild_id,
                odai.channel_id,
                odai.content,
                odai.image_path,
                odai.is_sent,
                odai.created_by
            ))

def insert_image_file(
    guild_id: int,
    user_id: int,
    filename: str,
    file_path: str,
    file_type: str,
    file_size: int
):
    sql = """
        INSERT INTO image_files (guild_id,filename,file_path,file_type,file_size,is_sent,created_by
        ) VALUES (%s, %s, %s, %s, %s, FALSE, %s)
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (
                guild_id,
                filename,
                file_path,
                file_type,
                file_size,
                user_id
            ))

def get_image_path_by_filename(guild_id: int, filename: str) -> Optional[str]:
    sql = """
        SELECT filename FROM image_files
        WHERE guild_id = %s AND filename = %s
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (guild_id, filename))
            row = cursor.fetchone()
            if row:
                return f"./img/{row[0]}"
    return None

def insert_generated_odai(
    guild_id: int,
    channel_id: int,
    filename: str,
    text: str,
):
    sql = """
        INSERT INTO generated_odai (guild_id, channel_id, filename, text)
        VALUES (%s, %s, %s, %s)
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (guild_id, channel_id, filename, text))

def insert_template_file(
    guild_id: int,
    filename: str,
    display_name: str,
    file_path: str,
    file_size: int,
    created_by: int
):
    sql = """
        INSERT INTO template_files (guild_id, filename, display_name, file_path, file_size, created_by)
        VALUES (%s, %s, %s, %s, %s, %s)
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (
                guild_id,
                filename,
                display_name,
                file_path,
                file_size,
                created_by
            ))

def get_template_files_by_guild(guild_id: int, limit: int = 10):
    sql = """
        SELECT filename, display_name, file_path
        FROM template_files
        WHERE guild_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, (guild_id, limit))
            rows = cursor.fetchall()
            return rows  # List[Tuple[filename, display_name, file_path]]

def get_latest_templates(guild_id: int, limit: int = 5) -> List[TemplateItem]:
    sql = """
        SELECT id, guild_id, filename, display_name, file_path, file_size, created_by, created_at
        FROM template_files
        WHERE guild_id = %s
        ORDER BY created_at DESC
        LIMIT %s
    """
    with get_connection().cursor() as cursor:
        cursor.execute(sql, (guild_id, limit))
        rows = cursor.fetchall()
        return [TemplateItem.from_row(row) for row in rows]
    
def get_template_by_display_name(guild_id: int, display_name: str) -> Optional[TemplateItem]:
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT * FROM template_files
                WHERE guild_id = %s AND display_name = %s
                ORDER BY created_at DESC
                LIMIT 1
            """
            cursor.execute(sql, (guild_id, display_name))
            row = cursor.fetchone()
            if row:
                return TemplateItem.from_row(row)
            return None
    finally:
        conn.close()

def get_all_template_names(guild_id: int):
    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
        SELECT display_name
        FROM template_files
        WHERE guild_id = %s
        ORDER BY created_at DESC
        """
        cursor.execute(sql, (guild_id,))
        rows = cursor.fetchall()
        return [row["display_name"] for row in rows]