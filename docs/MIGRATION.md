# 旧 JSON データ → MySQL 移行手順書

## 1. 概要

旧バージョン（JSON ファイル管理）から現行バージョン（MySQL）へデータを移行する手順です。

| 移行元 | 移行先 |
|---|---|
| `Data/{guild_id}_odai.json` | `odai` テーブル |
| `templates/{guild_id}/*.png` など | `odai.data`（LONGBLOB） |
| `Data/{guild_id}_Schedule.json` | `schedules` テーブル |

> **冪等性**: スクリプトは何度実行しても安全です。すでに登録済みのレコードはスキップされます。

---

## 2. 事前準備

### 2.1 旧データをプロジェクトルートに配置

プロジェクトルート（`Procfile` がある場所）に以下の構成でファイルを置いてください。

```
discode_OdaiBot/
  Data/
    1234567890_odai.json          ← guild_id ごとに用意
    1234567890_Schedule.json
    9876543210_odai.json
    9876543210_Schedule.json
  templates/
    1234567890/                   ← guild_id のディレクトリ
      image1.png
      image2.jpg
    9876543210/
      ...
```

**JSON フォーマット確認**

`{guild_id}_odai.json`:
```json
[
  { "file": "image1.png", "used": false, "added_at": "2024-01-01T10:00:00" },
  { "file": "image2.jpg", "used": true,  "added_at": "2024-02-15T12:30:00" }
]
```

`{guild_id}_Schedule.json`:
```json
[
  { "channel_id": 1234567890123456789, "time": "09:00" },
  { "channel_id": 9876543210987654321, "time": "21:00" }
]
```

### 2.2 .env の設定確認

プロジェクトルートの `.env` に MySQL 接続情報が設定されていることを確認します。

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=yourpassword
MYSQL_DATABASE=odai_bot
```

---

## 3. セットアップ手順

### ステップ 1: DB・テーブルの作成

```bash
# プロジェクトルートから実行
python -m OdaiBotDB.setup_db
```

出力例:
```
✅ セットアップが完了しました。
```

### ステップ 2: データ移行の実行

```bash
python -m OdaiBotDB.migrate_from_json
```

出力例:
```
============================================================
OdaiBotDB 移行スクリプト  JSON → MySQL
============================================================
  Data ディレクトリ      : .../Data
  templates ディレクトリ : .../templates

🔍 移行対象サーバー: 2 件 → [1234567890, 9876543210]

────────────────────────────────────────────────────────────
🔄 Guild ID: 1234567890
  📋 guild_settings 作成: guild_id=1234567890
  🖼️  お題: 45 件登録 / 0 件スキップ（登録済み）/ 0 件エラー
  📅 スケジュール: 2 件登録 / 0 件スキップ（登録済み）

============================================================
✅ 移行完了!
   お題       : 45 件登録 / 0 件スキップ / 0 件エラー
   スケジュール: 2 件登録 / 0 件スキップ
```

### ステップ 3: Bot・API の起動

```bash
# API サーバー
uvicorn OdaiBotAPI.api:app --reload

# Bot（別ターミナル）
python OdaiBot/odai_bot.py
```

### ステップ 4: Dashboard から確認

1. Discord で `/odai_dashboard` コマンドを実行
2. 発行された招待リンクにアクセスしてパスワードを設定
3. Dashboard にログインしてお題・スケジュールが移行されていることを確認

---

## 4. エラー対応

### 画像ファイルが見つからない

```
⚠️  画像なし (スキップ): image1.png
```

→ `templates/{guild_id}/` に画像ファイルを配置して再実行してください。スクリプトは冪等なので重複登録されません。

### 8MB 超過

```
⚠️  8MB 超過 (スキップ): large_image.png (9216 KB)
```

→ 該当画像は Dashboard の「お題追加」から手動でアップロードしてください。

### DB 接続エラー

```
mysql.connector.errors.InterfaceError: ...
```

→ MySQL が起動しているか、`.env` の接続情報を確認してください。

---

## 5. 移行後のクリーンアップ（任意）

移行完了・動作確認後、旧データを削除する場合:

```bash
# 確認してから削除
rm -rf Data/
rm -rf templates/
```

> **注意**: 削除前に必ずバックアップを取ってください。

---

## 6. 注意事項

- `odai.used` フラグは旧 JSON の `used` をそのまま引き継ぎます（Dashboard での手動管理フラグとして機能）
- スケジュールは `tag_mode=all`（全タグ対象）・`enabled=true` で登録されます。Dashboard から必要に応じて変更してください
- `guild_settings` のサーバー名（`guild_name`）は Bot 起動時に自動で同期されます
