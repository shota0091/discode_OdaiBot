from Repository.MySQLDatabase import MySQLDatabase


class UserRepository:
    def __init__(self, db: MySQLDatabase):
        self.db = db

    def count_for_guild(self, guild_id: int) -> int:
        row = self.db.query_one("SELECT COUNT(*) AS count FROM user_guilds WHERE guild_id = %s", (guild_id,))
        return row["count"] if row else 0

    def exists(self, guild_id: int, username: str) -> bool:
        return self.db.query_one(
            "SELECT 1 FROM users u JOIN user_guilds ug ON u.id = ug.user_id "
            "WHERE ug.guild_id = %s AND u.username = %s",
            (guild_id, username),
        ) is not None

    def create_user(self, guild_id: int, username: str, password_hash: str, role: str, api_token: str) -> int:
        existing = self.db.query_one("SELECT id FROM users WHERE username = %s", (username,))
        if existing:
            user_id = existing["id"]
        else:
            cursor = self.db.execute(
                "INSERT INTO users (username, password_hash, api_token) VALUES (%s, %s, %s)",
                (username, password_hash, api_token), commit=True,
            )
            user_id = cursor.lastrowid
        self.db.execute(
            "INSERT IGNORE INTO user_guilds (user_id, guild_id, role) VALUES (%s, %s, %s)",
            (user_id, guild_id, role), commit=True,
        )
        return user_id

    def find_by_username(self, guild_id: int, username: str):
        return self.db.query_one(
            "SELECT u.id, ug.guild_id, u.username, ug.role, u.api_token "
            "FROM users u JOIN user_guilds ug ON u.id = ug.user_id "
            "WHERE ug.guild_id = %s AND u.username = %s",
            (guild_id, username),
        )
