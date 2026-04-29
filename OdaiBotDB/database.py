import os
import mysql.connector
from dotenv import load_dotenv

load_dotenv()


class MySQLDatabase:
    def __init__(self):
        settings = self._get_connection_settings()
        self.conn = mysql.connector.connect(
            host=settings["host"],
            port=settings["port"],
            user=settings["user"],
            password=settings["password"],
            database=settings["database"],
            autocommit=False,
        )

    @staticmethod
    def _get_connection_settings() -> dict:
        return {
            "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
            "database": os.getenv("MYSQL_DATABASE", "odai_bot"),
        }

    @classmethod
    def initialize_database(cls):
        settings = cls._get_connection_settings()
        cls._ensure_database_exists(settings)
        connection = mysql.connector.connect(
            host=settings["host"],
            port=settings["port"],
            user=settings["user"],
            password=settings["password"],
            database=settings["database"],
            autocommit=False,
        )
        cls._initialize_schema(connection)
        connection.close()

    @staticmethod
    def _ensure_database_exists(settings: dict):
        connection = mysql.connector.connect(
            host=settings["host"],
            port=settings["port"],
            user=settings["user"],
            password=settings["password"],
            autocommit=True,
        )
        cursor = connection.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{settings['database']}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        )
        cursor.close()
        connection.close()

    @staticmethod
    def _initialize_schema(connection):
        cursor = connection.cursor()
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS guild_settings (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL UNIQUE,
                guild_name VARCHAR(128) DEFAULT NULL,
                bot_enabled TINYINT(1) NOT NULL DEFAULT 1,
                timezone VARCHAR(64),
                dashboard_role VARCHAR(128),
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS odai (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                filename VARCHAR(255) NOT NULL,
                storage_path VARCHAR(1024) NULL,
                data LONGBLOB NOT NULL,
                used TINYINT(1) NOT NULL DEFAULT 0,
                added_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                deleted_at DATETIME,
                UNIQUE KEY uq_guild_filename (guild_id, filename)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tags (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                name VARCHAR(128) NOT NULL,
                description VARCHAR(256),
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uq_guild_tagname (guild_id, name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS odai_tags (
                odai_id BIGINT NOT NULL,
                tag_id BIGINT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (odai_id, tag_id),
                CONSTRAINT fk_odai_tags_odai FOREIGN KEY (odai_id) REFERENCES odai(id) ON DELETE CASCADE,
                CONSTRAINT fk_odai_tags_tag FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS channels (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                name VARCHAR(128),
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uq_guild_channel (guild_id, channel_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS odai_usage (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                odai_id BIGINT NOT NULL,
                used_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE KEY uq_channel_odai (channel_id, odai_id),
                CONSTRAINT fk_odai_usage_odai FOREIGN KEY (odai_id) REFERENCES odai(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS schedules (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                time VARCHAR(5) NOT NULL,
                enabled TINYINT(1) NOT NULL DEFAULT 1,
                tag_mode VARCHAR(16) NOT NULL DEFAULT 'all',
                tag_list TEXT,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS post_history (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                channel_id BIGINT NOT NULL,
                odai_id BIGINT NOT NULL,
                posted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                result VARCHAR(32) NOT NULL,
                message VARCHAR(512)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(128) NOT NULL,
                password_hash VARCHAR(256) NOT NULL,
                api_token VARCHAR(128),
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uq_username (username),
                UNIQUE KEY uq_users_api_token (api_token)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_guilds (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                user_id BIGINT NOT NULL,
                guild_id BIGINT NOT NULL,
                role VARCHAR(32) NOT NULL DEFAULT 'user',
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uq_user_guild (user_id, guild_id),
                CONSTRAINT fk_user_guilds_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS user_invites (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                guild_id BIGINT NOT NULL,
                username VARCHAR(128) NOT NULL,
                role VARCHAR(32) NOT NULL DEFAULT 'user',
                invite_token VARCHAR(128) NOT NULL,
                expires_at DATETIME NOT NULL,
                used TINYINT(1) NOT NULL DEFAULT 0,
                used_at DATETIME NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                UNIQUE KEY uq_user_invites_token (invite_token)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
        )
        # guild_name カラムが存在しない既存 DB にも対応するためマイグレーション
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'guild_settings' "
            "AND COLUMN_NAME = 'guild_name'"
        )
        (col_count,) = cursor.fetchone()
        if col_count == 0:
            cursor.execute(
                "ALTER TABLE guild_settings ADD COLUMN "
                "guild_name VARCHAR(128) DEFAULT NULL AFTER guild_id"
            )
        # --- Migration: users テーブルから guild_id / role を user_guilds へ移行 ---
        cursor.execute(
            "SELECT COUNT(*) FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'guild_id'"
        )
        (has_guild_id,) = cursor.fetchone()
        if has_guild_id:
            # 1. 既存 users データを user_guilds へ移す
            cursor.execute(
                "INSERT IGNORE INTO user_guilds (user_id, guild_id, role, created_at, updated_at) "
                "SELECT id, guild_id, role, created_at, updated_at FROM users WHERE guild_id IS NOT NULL"
            )
            # 2. 重複ユーザー名がある場合 user_guilds を正規 ID (MIN) へ更新
            cursor.execute(
                "UPDATE user_guilds ug "
                "INNER JOIN users u ON ug.user_id = u.id "
                "INNER JOIN (SELECT username, MIN(id) AS min_id FROM users GROUP BY username) AS canon "
                "  ON u.username = canon.username "
                "SET ug.user_id = canon.min_id "
                "WHERE ug.user_id != canon.min_id"
            )
            # 3. 非正規ユーザー（同名の重複行）を削除
            cursor.execute(
                "DELETE FROM users WHERE id NOT IN ("
                "  SELECT min_id FROM (SELECT MIN(id) AS min_id FROM users GROUP BY username) AS t"
                ")"
            )
            # 4. 古い複合インデックス削除
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND INDEX_NAME = 'uq_guild_username'"
            )
            (has_idx,) = cursor.fetchone()
            if has_idx:
                cursor.execute("ALTER TABLE users DROP INDEX uq_guild_username")
            # 5. username の UNIQUE KEY 追加
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.STATISTICS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND INDEX_NAME = 'uq_username'"
            )
            (has_uq,) = cursor.fetchone()
            if not has_uq:
                cursor.execute("ALTER TABLE users ADD UNIQUE KEY uq_username (username)")
            # 6. 不要カラム削除
            cursor.execute("ALTER TABLE users DROP COLUMN guild_id")
            cursor.execute(
                "SELECT COUNT(*) FROM information_schema.COLUMNS "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = 'users' AND COLUMN_NAME = 'role'"
            )
            (has_role,) = cursor.fetchone()
            if has_role:
                cursor.execute("ALTER TABLE users DROP COLUMN role")

        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        connection.commit()

    def execute(self, sql: str, params: tuple = (), commit: bool = False):
        cursor = self.conn.cursor(dictionary=True)
        cursor.execute(sql, params)
        if commit:
            self.conn.commit()
        return cursor

    def executemany(self, sql: str, seq_of_params, commit: bool = False):
        cursor = self.conn.cursor(dictionary=True)
        cursor.executemany(sql, seq_of_params)
        if commit:
            self.conn.commit()
        return cursor

    def query(self, sql: str, params: tuple = ()):  # noqa: B006
        self.conn.commit()  # 最新コミット済みデータを読むためスナップショットをリセット
        cursor = self.execute(sql, params)
        return cursor.fetchall()

    def query_one(self, sql: str, params: tuple = ()):  # noqa: B006
        self.conn.commit()  # 最新コミット済みデータを読むためスナップショットをリセット
        cursor = self.execute(sql, params)
        return cursor.fetchone()

    def close(self):
        self.conn.close()
