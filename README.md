# OdaiBot

Discord サーバー向けのお題自動投稿 Bot と Web 管理 Dashboard のモノレポです。

お題画像の登録・タグ管理・投稿スケジュール設定を Dashboard の Web UI で操作し、Discord Bot が自動でお題を投稿します。

---

## バージョン履歴

### v1.3（2026-05-08）
- **APIレート制限**: ログイン・パスワードリセットエンドポイントに IP ベースのレート制限を追加（ブルートフォース対策）
- **お題ファイルのローカル管理化**: 画像データを MySQL LONGBLOB からローカルファイル（`ODAI_IMAGE_DIR/{guild_id}/filename`）に移行。DB は軽量化
- **DBバックアップ**: `scripts/backup.sh` による MySQL ダンプ＋画像ディレクトリの定期バックアップ（cron 運用）

### v1.2（2026-04-29）
- ダッシュボード、お題管理、タグ管理、スケジュール管理、設定
- ユーザー管理（BAN・ロック・招待・プロフィール）
- メモ機能、メモ検索、フィルター・ソート
- 招待管理ページ（サイドバー独立タブ）
- テスト投稿プレビュー
- パスワードリセット・管理者 PW 変更
- お題・タグの更新日時カラム追加

---

## モジュール構成

```
discode_OdaiBot/
  OdaiBot/               # Discord Bot 本体
  OdaiBotAPI/            # REST API（FastAPI）
  OdaiBotDB/             # DB 接続・スキーマ管理（MySQL）
  OdaiBotdashboard/      # Web 管理 Dashboard（Vanilla SPA）
  scripts/               # 運用スクリプト（バックアップなど）
  docs/                  # 仕様書・設計ドキュメント
  .env                   # 環境変数（要作成）
  pytest.ini             # テスト設定
```

### OdaiBot

Discord Bot 本体。DB から未使用お題を取得して Discord チャンネルに投稿します。

```
OdaiBot/
  odai_bot.py            # エントリポイント
  Entity/                # エンティティクラス（OdaiEntity, ScheduleEntity）
  Factory/               # DI ファクトリ（DB・サービス組み立て）
  Interface/             # リポジトリ・サービスのインターフェース定義
  Repository/            # DB アクセス層（OdaiRepository, ScheduleRepository）
  Service/               # ビジネスロジック（NotifyServiceImpl, ScheduleServiceImpl）
  Util/                  # ユーティリティ
  requirements.txt
```

### OdaiBotAPI

FastAPI による REST API。Dashboard と Discord Bot が利用する共有バックエンドです。

```
OdaiBotAPI/
  api.py                 # FastAPI アプリ・ルーター登録
  deps.py                # DB 接続・認証依存・共通ヘルパー
  limiter.py             # IP ベースレートリミッター
  schemas.py             # Pydantic スキーマ定義
  routers/
    auth.py              # 認証・ユーザー管理
    odai.py              # お題 CRUD・一括インポート
    tags.py              # タグ CRUD
    schedules.py         # スケジュール CRUD
    settings.py          # サーバー設定
    summary.py           # ダッシュボード概要
    test_post.py         # テスト投稿
  tests/                 # pytest ユニットテスト
  requirements.txt
  requirements-test.txt
```

### OdaiBotDB

MySQL 接続ロジックと DB セットアップスクリプトを集約した DB 層モジュールです。

```
OdaiBotDB/
  database.py            # MySQLDatabase 接続クラス・マイグレーション
  setup_db.py            # テーブル作成スクリプト
```

### OdaiBotdashboard

Vanilla HTML / CSS / JavaScript で実装した SPA の管理 Dashboard です。

```
OdaiBotdashboard/
  index.html             # SPA エントリポイント
  css/
    style.css            # 全画面共通スタイル
  js/
    config.js            # API_BASE 設定
    api.js               # API クライアント
    app.js               # ハッシュルーター・ユーティリティ
    components/
      layout.js          # サイドバー・ハンバーガーメニュー
      modal.js           # モーダルダイアログ
      toast.js           # トースト通知
    pages/
      login.js           # ログイン
      register.js        # 招待登録
      dashboard.js       # ダッシュボードトップ
      odai.js            # お題管理
      tags.js            # タグ管理
      users.js           # ユーザー管理
      invites.js         # 招待管理
      schedules.js       # スケジュール管理
      settings.js        # サーバー設定
```

### scripts

```
scripts/
  backup.sh              # DB ダンプ＋画像バックアップ（cron 用）
```

### setup

```
setup/
  migrate_odai_to_local.py  # BLOB → ローカルファイル移行（初回のみ）
  migrate_from_json.py      # JSON → DB 移行（初回のみ）
  bulk_import_images.py     # 画像一括インポート
  download_discord_images.py
  rename_images.py
  make_report.py
```

### docs

```
docs/
  odoai_bot_api_spec.md        # REST API エンドポイント仕様
  odoai_bot_db_spec.md         # DB テーブル定義書
  DB_SCHEMA.md                 # DB スキーマ DDL
  MIGRATION.md                 # マイグレーション履歴
  odoai_bot_spec.md            # Discord Bot 仕様
  odoai_bot_dashboard_spec.md  # Dashboard 画面仕様
  SCREEN_SPEC.md               # 画面仕様
  DEPLOY_MANUAL.md             # デプロイ手順
  SYSTEM_GUIDE.md              # システム運用ガイド
  V2_PLAN.md                   # v2.0 開発計画
  APITest.md                   # テスト実行ガイド
  *.pptx                       # 開発事例報告・プレゼン資料
```

---

## セットアップ

### 1. Python バージョン

Python 3.10 以上が必要です。

### 2. 仮想環境の作成・有効化

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 3. 環境変数の設定

プロジェクトルートの `.env.example` をコピーして `.env` を作成し、各値を設定してください。

```bash
cp .env.example .env
```

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=yourpassword
MYSQL_DATABASE=odai_bot

DISCORD_BOT_TOKEN=your_discord_bot_token
DASHBOARD_BASE_URL=http://localhost:3000
INVITE_EXPIRE_HOURS=1

# お題画像の保存先（デフォルト: /data/odai）
ODAI_IMAGE_DIR=/data/odai

# バックアップ設定（scripts/backup.sh 用）
BACKUP_DIR=/home/youruser/backups/odaibot
BACKUP_KEEP_DAYS=7
```

### 4. パッケージのインストール

```bash
pip install -r OdaiBotAPI/requirements.txt
pip install -r OdaiBot/requirements.txt
```

### 5. DB のセットアップ

```bash
python -m OdaiBotDB.setup_db
```

### 6. 画像ディレクトリの作成

```bash
sudo mkdir -p /data/odai
sudo chown $(whoami):$(whoami) /data/odai
```

---

## 起動方法

### API サーバー

```bash
uvicorn OdaiBotAPI.api:app --host 0.0.0.0 --port 8000 --reload
```

### Discord Bot

```bash
python OdaiBot/odai_bot.py
```

### Dashboard

```bash
cd OdaiBotdashboard
python -m http.server 3000
```

---

## バックアップ

```bash
# 手動実行
bash scripts/backup.sh

# cron 登録例（毎日午前3時）
# 0 3 * * * /path/to/scripts/backup.sh >> /path/to/backups/backup.log 2>&1
```

DB ダンプと画像ファイルを `BACKUP_DIR` 配下にタイムスタンプ付きで保存します。`BACKUP_KEEP_DAYS` 日以上経ったバックアップは自動削除されます。

---

## テスト

```bash
pytest
pytest -v
pytest OdaiBotAPI/tests/test_odai.py

pip install -r OdaiBotAPI/requirements-test.txt
```

---

## 主要仕様書

| ドキュメント | 内容 |
|---|---|
| [docs/odoai_bot_api_spec.md](docs/odoai_bot_api_spec.md) | REST API エンドポイント仕様 |
| [docs/odoai_bot_db_spec.md](docs/odoai_bot_db_spec.md) | DB テーブル定義書 |
| [docs/odoai_bot_spec.md](docs/odoai_bot_spec.md) | Discord Bot 仕様 |
| [docs/odoai_bot_dashboard_spec.md](docs/odoai_bot_dashboard_spec.md) | Dashboard 画面仕様 |
| [docs/DEPLOY_MANUAL.md](docs/DEPLOY_MANUAL.md) | デプロイ手順 |
| [docs/V2_PLAN.md](docs/V2_PLAN.md) | v2.0 開発計画 |

---

## システム構成図

```
Discord
  │
  │ discord.py
  ▼
OdaiBot ──────────────── OdaiBotDB (MySQLDatabase)
                              │
                              │ mysql-connector-python
                              ▼
                           MySQL
                              ▲
                              │ mysql-connector-python
OdaiBotAPI (FastAPI) ─────────┘
  ▲
  │ HTTP / Bearer Token
  │
ブラウザ
  OdaiBotdashboard (Vanilla SPA)
```

- **OdaiBot** と **OdaiBotAPI** はともに `OdaiBotDB.MySQLDatabase` を通じて同じ MySQL に接続します
- Dashboard は API のみと通信し、DB に直接アクセスしません
- お題画像はローカルファイル（`ODAI_IMAGE_DIR`）で管理し、DB にはパスのみ保持します

---

## 技術スタック

| 区分 | 技術 |
|---|---|
| Discord Bot | discord.py 2.5.2 |
| API フレームワーク | FastAPI 0.111.1 + uvicorn |
| DB | MySQL + mysql-connector-python 9.4.0 |
| Dashboard | HTML / CSS / JavaScript（フレームワークなし） |
| テスト | pytest + httpx |
