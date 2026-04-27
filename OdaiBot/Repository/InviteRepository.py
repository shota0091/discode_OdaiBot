from Repository.MySQLDatabase import MySQLDatabase


class InviteRepository:
    def __init__(self, db: MySQLDatabase):
        self.db = db

    def create_invite(self, guild_id: int, username: str, role: str, invite_token: str, expires_at: str):
        cursor = self.db.execute(
            "INSERT INTO user_invites (guild_id, username, role, invite_token, expires_at) VALUES (%s, %s, %s, %s, %s)",
            (guild_id, username, role, invite_token, expires_at),
            commit=True,
        )
        return cursor.lastrowid

    def get_active_invite(self, guild_id: int, invite_token: str):
        return self.db.query_one(
            "SELECT * FROM user_invites WHERE guild_id = %s AND invite_token = %s AND used = 0 AND expires_at > NOW()",
            (guild_id, invite_token),
        )

    def mark_used(self, invite_id: int):
        self.db.execute(
            "UPDATE user_invites SET used = 1, used_at = CURRENT_TIMESTAMP WHERE id = %s",
            (invite_id,),
            commit=True,
        )
