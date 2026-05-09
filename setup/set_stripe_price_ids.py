"""Stripe の Price ID を plans テーブルに設定するスクリプト。

Stripe ダッシュボードで Light / Pro の商品・価格を作成した後に実行してください。

実行方法（プロジェクトルートから）:
    python setup/set_stripe_price_ids.py --light price_xxx --pro price_yyy

確認のみ:
    python setup/set_stripe_price_ids.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from dotenv import load_dotenv
load_dotenv(_root / ".env")

from OdaiBotDB.database import MySQLDatabase


def show_current(db) -> None:
    rows = db.query("SELECT name, price, stripe_price_id FROM plans ORDER BY id", ())
    print("現在の plans テーブル:")
    for r in rows:
        pid = r["stripe_price_id"] or "（未設定）"
        print(f"  {r['name']:12} ¥{r['price']:>6}  stripe_price_id = {pid}")
    print()


def main():
    parser = argparse.ArgumentParser(description="Stripe Price ID を plans テーブルに設定")
    parser.add_argument("--light", type=str, help="Light プランの Stripe Price ID（例: price_xxx）")
    parser.add_argument("--pro",   type=str, help="Pro プランの Stripe Price ID（例: price_yyy）")
    args = parser.parse_args()

    db = MySQLDatabase()
    show_current(db)

    if not args.light and not args.pro:
        print("※ --light / --pro を指定すると Price ID を更新できます。")
        return

    updates = []
    if args.light:
        updates.append(("light", args.light))
    if args.pro:
        updates.append(("pro", args.pro))

    for plan_name, price_id in updates:
        if not price_id.startswith("price_"):
            print(f"⚠️  {plan_name}: Price ID は 'price_' で始まる文字列を指定してください（入力値: {price_id}）")
            continue
        db.execute(
            "UPDATE plans SET stripe_price_id = %s WHERE name = %s",
            (price_id, plan_name),
            commit=True,
        )
        print(f"✅ {plan_name}: stripe_price_id = {price_id}")

    print()
    show_current(db)


if __name__ == "__main__":
    main()
