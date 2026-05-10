"""オーナーサーバーを Enterprise プラン（無制限・無課金）で登録するスクリプト。

実行方法（プロジェクトルートから）:
    python setup/seed_owner_guilds.py
"""
from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from dotenv import load_dotenv
load_dotenv(_root / ".env")

from OdaiBotDB.database import MySQLDatabase

# オーナーが管理するサーバー ID（必要に応じて追加・変更）
OWNER_GUILD_IDS = [
    1315559712179228672,
    1396823594411098223,
]


def main() -> None:
    db = MySQLDatabase()

    enterprise = db.query_one("SELECT id FROM plans WHERE name = 'enterprise'", ())
    if not enterprise:
        print("❌ plans テーブルに 'enterprise' が見つかりません。先に setup_db.py を実行してください。")
        sys.exit(1)
    enterprise_id = enterprise["id"]

    for guild_id in OWNER_GUILD_IDS:
        existing = db.query_one("SELECT id, plan_id FROM guild_plans WHERE guild_id = %s", (guild_id,))
        if existing:
            db.execute(
                "UPDATE guild_plans SET plan_id = %s, custom_odai_capacity = NULL, status = 'active', "
                "stripe_customer_id = NULL, stripe_subscription_id = NULL WHERE guild_id = %s",
                (enterprise_id, guild_id),
                commit=True,
            )
            print(f"✅ 更新: guild_id={guild_id} → Enterprise（無制限）")
        else:
            db.execute(
                "INSERT INTO guild_plans (guild_id, plan_id, custom_odai_capacity, status) "
                "VALUES (%s, %s, NULL, 'active')",
                (guild_id, enterprise_id),
                commit=True,
            )
            print(f"✅ 登録: guild_id={guild_id} → Enterprise（無制限）")

    print("\n完了。")


if __name__ == "__main__":
    main()
