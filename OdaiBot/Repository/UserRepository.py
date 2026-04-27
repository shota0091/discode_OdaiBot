from Repository.MySQLDatabase import MySQLDatabase


class UserRepository:
    def __init__(self, db: MySQLDatabase):
        self.db = db

    def count_for_guild(self, guild_id: int) -> int:
        row = self.db.query_one("SELECT COUNT(*) AS count FROM users WHERE guild_id = %s", (guild_id,))
        return row["count"] if row else 0

    def exists(self, guild_id: int, username: str) -> bool:
        return self.db.query_one(
            "SELECT 1 FROM users WHERE guild_id = %s AND username = %s",
            (guild_id, username),
        ) is not None

    def create_user(self, guild_id: int, username: str, password_hash: str, role: str, api_token: str) -> int:
        cursor = self.db.execute(
            "INSERT INTO users (guild_id, username, password_hash, role, api_token) VALUES (%s, %s, %s, %s, %s)",
            (guild_id, username, password_hash, role, api_token),
            commit=True,
        )
        return cursor.lastrowid

    def find_by_username(self, guild_id: int, username: str):
        return self.db.query_one(
            "SELECT id, guild_id, username, role, api_token FROM users WHERE guild_id = %s AND username = %s",
            (guild_id, username),
        )
