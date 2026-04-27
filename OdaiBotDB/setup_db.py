from __future__ import annotations

import sys
from pathlib import Path

# プロジェクトルートを sys.path に追加し、.env を読み込む
_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from dotenv import load_dotenv
load_dotenv(_root / "OdaiBotDB" / ".env")   # OdaiBotDB/.env を優先
load_dotenv(_root / ".env")                  # なければプロジェクトルート .env

import os
from OdaiBotDB.database import MySQLDatabase


def main() -> None:
    """MySQL データベースを作成し、スキーマを初期化する。

    実行内容:
    - データベースが存在しなければ作成（CREATE DATABASE IF NOT EXISTS）
    - 全テーブルを作成（CREATE TABLE IF NOT EXISTS）
    - guild_settings に guild_name カラムが未追加の場合はマイグレーション
    """
    host = os.getenv("MYSQL_HOST", "127.0.0.1")
    port = os.getenv("MYSQL_PORT", "3306")
    user = os.getenv("MYSQL_USER", "root")
    db_name = os.getenv("MYSQL_DATABASE", "odai_bot")

    print("=" * 50)
    print("OdaiBotDB セットアップ")
    print("=" * 50)
    print(f"  Host     : {host}:{port}")
    print(f"  User     : {user}")
    print(f"  Database : {db_name}")
    print()

    try:
        MySQLDatabase.initialize_database()
        print("✅ セットアップが完了しました。")
        print()
        print("作成・更新されたテーブル:")
        tables = [
            "guild_settings    ... サーバー設定・サーバー名（guild_name 追加済み）",
            "users             ... Dashboard ユーザー",
            "user_invites      ... 招待トークン",
            "odai              ... お題画像",
            "tags              ... タグマスタ",
            "odai_tags         ... お題↔タグ 中間テーブル",
            "odai_usage        ... チャンネル別投稿済みお題（ローテーション管理）",
            "channels          ... チャンネルキャッシュ（Bot が自動同期）",
            "schedules         ... 自動投稿スケジュール",
            "post_history      ... 投稿履歴",
        ]
        for t in tables:
            print(f"  - {t}")
        print()
        print("次のステップ:")
        print("  1. Discord Bot を起動する   : python OdaiBot/odai_bot.py")
        print("  2. API サーバーを起動する   : uvicorn OdaiBotAPI.api:app --reload")
        print("  3. Dashboard を開く         : OdaiBotdashboard/index.html")
    except Exception as exc:
        print(f"❌ セットアップに失敗しました: {exc}")
        raise


if __name__ == "__main__":
    main()
