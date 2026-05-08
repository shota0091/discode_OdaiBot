"""旧 JSON ファイル形式から MySQL へのデータ移行スクリプト。

旧ディレクトリ構造:
  Data/
    {guild_id}_odai.json       ... お題リスト (file, used, added_at)
    {guild_id}_Schedule.json   ... スケジュール (channel_id, time)
  templates/
    {guild_id}/
      *.png / *.jpg / *.webp   ... お題画像

実行方法 (プロジェクトルートから):
  python -m OdaiBotDB.migrate_from_json
"""

from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_root))

from dotenv import load_dotenv
load_dotenv(_root / "OdaiBotDB" / ".env")
load_dotenv(_root / ".env")

from OdaiBotDB.database import MySQLDatabase

DATA_DIR = _root / "Data"
TEMPLATES_DIR = _root / "templates"

MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def _parse_added_at(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return None


def _collect_guild_ids() -> list[int]:
    if not DATA_DIR.exists():
        return []
    ids: list[int] = []
    for f in DATA_DIR.iterdir():
        m = re.match(r"^(\d+)_odai\.json$", f.name)
        if m:
            ids.append(int(m.group(1)))
    return sorted(ids)


# ---------------------------------------------------------------------------
# 移行処理
# ---------------------------------------------------------------------------

def migrate_guild(db: MySQLDatabase, guild_id: int) -> dict:
    result = {"odai_inserted": 0, "odai_skipped": 0, "odai_error": 0,
              "schedule_inserted": 0, "schedule_skipped": 0}

    # guild_settings が無ければ作成
    exists = db.query_one("SELECT id FROM guild_settings WHERE guild_id = %s", (guild_id,))
    if not exists:
        db.execute(
            "INSERT INTO guild_settings (guild_id) VALUES (%s)",
            (guild_id,), commit=True,
        )
        print(f"  📋 guild_settings 作成: guild_id={guild_id}")

    # ── お題 ──────────────────────────────────────────────────────────
    odai_json_path = DATA_DIR / f"{guild_id}_odai.json"
    image_dir = TEMPLATES_DIR / str(guild_id)

    if odai_json_path.exists():
        with open(odai_json_path, encoding="utf-8") as f:
            odai_list: list[dict] = json.load(f)

        for odai in odai_list:
            filename = odai.get("file") or odai.get("filename", "")
            if not filename:
                continue

            # 登録済みチェック（冪等性）
            if db.query_one(
                "SELECT id FROM odai WHERE guild_id = %s AND filename = %s",
                (guild_id, filename),
            ):
                result["odai_skipped"] += 1
                continue

            image_path = image_dir / filename
            if not image_path.exists():
                print(f"  ⚠️  画像なし (スキップ): {filename}")
                result["odai_error"] += 1
                continue

            file_size = image_path.stat().st_size
            if file_size > MAX_IMAGE_BYTES:
                print(f"  ⚠️  8MB 超過 (スキップ): {filename} ({file_size // 1024} KB)")
                result["odai_error"] += 1
                continue

            data = image_path.read_bytes()
            used = 1 if odai.get("used") else 0
            added_at = _parse_added_at(odai.get("added_at"))

            if added_at:
                db.execute(
                    "INSERT INTO odai (guild_id, filename, data, used, added_at) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    (guild_id, filename, data, used, added_at), commit=True,
                )
            else:
                db.execute(
                    "INSERT INTO odai (guild_id, filename, data, used) "
                    "VALUES (%s, %s, %s, %s)",
                    (guild_id, filename, data, used), commit=True,
                )
            result["odai_inserted"] += 1

        print(
            f"  🖼️  お題: {result['odai_inserted']} 件登録 / "
            f"{result['odai_skipped']} 件スキップ（登録済み）/ "
            f"{result['odai_error']} 件エラー"
        )
    else:
        print(f"  ⚠️  {odai_json_path.name} が見つかりません（スキップ）")

    # ── スケジュール ───────────────────────────────────────────────────
    schedule_json_path = DATA_DIR / f"{guild_id}_Schedule.json"

    if schedule_json_path.exists():
        with open(schedule_json_path, encoding="utf-8") as f:
            schedule_list: list[dict] = json.load(f)

        for s in schedule_list:
            channel_id = s.get("channel_id")
            time_str = s.get("time", "")
            if not channel_id or not time_str:
                continue

            if db.query_one(
                "SELECT id FROM schedules WHERE guild_id = %s AND channel_id = %s AND time = %s",
                (guild_id, channel_id, time_str),
            ):
                result["schedule_skipped"] += 1
                continue

            db.execute(
                "INSERT INTO schedules (guild_id, channel_id, time, enabled, tag_mode, tag_list) "
                "VALUES (%s, %s, %s, 1, 'all', '[]')",
                (guild_id, channel_id, time_str), commit=True,
            )
            result["schedule_inserted"] += 1

        print(
            f"  📅 スケジュール: {result['schedule_inserted']} 件登録 / "
            f"{result['schedule_skipped']} 件スキップ（登録済み）"
        )
    else:
        print(f"  ℹ️  {schedule_json_path.name} が見つかりません（スキップ）")

    return result


# ---------------------------------------------------------------------------
# エントリポイント
# ---------------------------------------------------------------------------

def main() -> None:
    print("=" * 60)
    print("OdaiBotDB 移行スクリプト  JSON → MySQL")
    print("=" * 60)
    print(f"  Data ディレクトリ      : {DATA_DIR}")
    print(f"  templates ディレクトリ : {TEMPLATES_DIR}")
    print()

    guild_ids = _collect_guild_ids()
    if not guild_ids:
        print("⚠️  移行対象の JSON ファイルが見つかりませんでした。")
        print(f"   Data/ ディレクトリに {{guild_id}}_odai.json が存在するか確認してください。")
        print(f"   検索パス: {DATA_DIR}")
        return

    print(f"🔍 移行対象サーバー: {len(guild_ids)} 件 → {guild_ids}")
    print()

    db = MySQLDatabase()
    total = {"odai_inserted": 0, "odai_skipped": 0, "odai_error": 0,
             "schedule_inserted": 0, "schedule_skipped": 0}

    for guild_id in guild_ids:
        print(f"{'─' * 60}")
        print(f"🔄 Guild ID: {guild_id}")
        try:
            r = migrate_guild(db, guild_id)
            for k in total:
                total[k] += r[k]
        except Exception as e:
            print(f"  ❌ エラー: {e}")
            raise

    print()
    print("=" * 60)
    print("✅ 移行完了!")
    print(f"   お題       : {total['odai_inserted']} 件登録 / "
          f"{total['odai_skipped']} 件スキップ / {total['odai_error']} 件エラー")
    print(f"   スケジュール: {total['schedule_inserted']} 件登録 / "
          f"{total['schedule_skipped']} 件スキップ")
    print()
    if total["odai_error"] > 0:
        print("⚠️  エラーになった画像はログを確認して手動でアップロードしてください。")


if __name__ == "__main__":
    main()
