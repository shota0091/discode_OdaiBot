# OdaiBot システムガイド

## 目次

1. [システム概要](#1-システム概要)
2. [アーキテクチャ](#2-アーキテクチャ)
3. [初期セットアップ手順](#3-初期セットアップ手順)
4. [運用手順書](#4-運用手順書)
5. [システム仕様](#5-システム仕様)
6. [更新履歴](#6-更新履歴)

---

## 1. システム概要

OdaiBot は Discord サーバー向けの「お題」管理・自動投稿システムです。  
以下の3コンポーネントで構成されています。

| コンポーネント | 役割 |
|---|---|
| **OdaiBot** (Discord Bot) | スラッシュコマンド受付、スケジュール実行によるお題自動投稿 |
| **OdaiBotAPI** (FastAPI) | Dashboard からの操作を受け付ける REST API、Bot とデータを共有 |
| **OdaiBotdashboard** (SPA) | ブラウザから操作できる管理 UI（バニラ JS、ハッシュルーティング） |

全コンポーネントが同一の MySQL データベースを共有します。

---

## 2. アーキテクチャ

```
インターネット
    │
    ▼
[Nginx] ← Let's Encrypt SSL
    ├── / ─────────────────── OdaiBotdashboard (静的ファイル配信)
    └── /api ─────────────── OdaiBotAPI (Uvicorn :8000 にプロキシ)

[systemd]
    ├── odaibotapi.service ── OdaiBotAPI (uvicorn)
    └── odaibot.service ───── OdaiBot (discord.py)

[MySQL] ─── odai_bot データベース（全コンポーネント共有）

[GitHub Actions]
    push to main → SSH → git pull + systemctl restart
```

**サーバー環境（本番）**

- OS: Rocky Linux 9.6
- VPS: Kagoya
- Python: 3.x（venv 使用）
- Web サーバー: Nginx + Let's Encrypt SSL

---

## 3. 初期セットアップ手順

### 3.1 前提条件

- Rocky Linux 9.x（または同等の RHEL 系 OS）
- Python 3.10 以上
- MySQL 8.0 以上
- Git
- Discord Developer Portal へのアクセス権
- 公開ドメイン（HTTPS 化する場合）

---

### 3.2 Discord Bot の準備

1. [Discord Developer Portal](https://discord.com/developers/applications) でアプリケーションを作成
2. Bot タブ → **TOKEN** をコピー（後で `.env` に設定）
3. OAuth2 → URL Generator で以下を選択してボットを招待:
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Attach Files`, `Read Message History`
4. 生成された URL をブラウザで開いてサーバーへ招待

---

### 3.3 サーバーへのデプロイ

#### リポジトリのクローン

```bash
cd /home/shota/bots
git clone https://github.com/<your-repo>/discode_OdaiBot.git
cd discode_OdaiBot
```

#### Python 仮想環境の作成と依存インストール

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

> `requirements.txt` が存在しない場合は以下をインストール:
> ```bash
> pip install fastapi uvicorn mysql-connector-python python-dotenv discord.py pydantic
> ```

---

### 3.4 環境変数の設定

プロジェクトルートに `.env` を作成します:

```bash
cp .env.example .env
nano .env
```

**.env の内容:**

```env
# MySQL 接続設定
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_mysql_password
MYSQL_DATABASE=odai_bot

# Discord Bot トークン（Developer Portal から取得）
DISCORD_BOT_TOKEN=your_discord_bot_token

# Dashboard の公開 URL（招待リンク生成に使用）
DASHBOARD_BASE_URL=https://your-domain.example.com

# 招待トークンの有効期限（時間）
INVITE_EXPIRE_HOURS=24

# お題画像の保存先ディレクトリ
ODAI_IMAGE_DIR=/data/odai

# バックアップ設定（scripts/backup.sh 用）
BACKUP_DIR=/home/shota/backups/odaibot
BACKUP_KEEP_DAYS=7
```

---

### 3.5 データベースの初期化

```bash
cd /home/shota/bots/discode_OdaiBot
source venv/bin/activate
python OdaiBotDB/setup_db.py
```

このスクリプトは以下を実行します:
- `odai_bot` データベースの作成（存在しない場合）
- 全テーブルの作成（`CREATE TABLE IF NOT EXISTS`）
- マイグレーション（既存 DB へのカラム追加など）

---

### 3.6 systemd サービスの設定

#### OdaiBotAPI サービス (`/etc/systemd/system/odaibotapi.service`)

```ini
[Unit]
Description=OdaiBotAPI FastAPI Service
After=network.target mysqld.service

[Service]
Type=simple
User=shota
WorkingDirectory=/home/shota/bots/discode_OdaiBot
ExecStart=/home/shota/bots/discode_OdaiBot/venv/bin/uvicorn OdaiBotAPI.api:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5
EnvironmentFile=/home/shota/bots/discode_OdaiBot/.env

[Install]
WantedBy=multi-user.target
```

#### OdaiBot サービス (`/etc/systemd/system/odaibot.service`)

```ini
[Unit]
Description=OdaiBot Discord Bot Service
After=network.target mysqld.service

[Service]
Type=simple
User=shota
WorkingDirectory=/home/shota/bots/discode_OdaiBot/OdaiBot
ExecStart=/home/shota/bots/discode_OdaiBot/venv/bin/python odai_bot.py
Restart=always
RestartSec=5
EnvironmentFile=/home/shota/bots/discode_OdaiBot/.env

[Install]
WantedBy=multi-user.target
```

#### サービスの有効化と起動

```bash
sudo systemctl daemon-reload
sudo systemctl enable odaibotapi odaibot
sudo systemctl start odaibotapi odaibot
sudo systemctl status odaibotapi odaibot
```

---

### 3.7 Nginx の設定

`/etc/nginx/conf.d/odaibot.conf` を作成:

```nginx
server {
    listen 80;
    server_name your-domain.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.example.com;

    ssl_certificate     /etc/letsencrypt/live/your-domain.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.example.com/privkey.pem;

    # Dashboard (静的ファイル)
    root /home/shota/bots/discode_OdaiBot/OdaiBotdashboard;
    index index.html;
    location / {
        try_files $uri $uri/ /index.html;
    }

    # API プロキシ
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo nginx -t
sudo systemctl reload nginx
```

#### Let's Encrypt SSL 証明書の取得

```bash
sudo dnf install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.example.com
```

---

### 3.8 GitHub Actions 自動デプロイの設定

リポジトリの **Settings → Secrets and variables → Actions** に以下のシークレットを登録:

| シークレット名 | 内容 |
|---|---|
| `SSH_HOST` | サーバーの IP アドレスまたはホスト名 |
| `SSH_USER` | SSH ユーザー名（例: `shota`） |
| `SSH_PRIVATE_KEY` | SSH 秘密鍵の内容（`-----BEGIN...` 全体） |
| `SSH_PORT` | SSH ポート番号（通常 `22`） |

#### sudoers 設定（サービス再起動の権限付与）

```bash
sudo visudo -f /etc/sudoers.d/odaibot
```

以下を追記:

```
shota ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart odaibotapi
shota ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart odaibot
```

> **注意**: `/bin/systemctl` ではなく `/usr/bin/systemctl` を指定すること。

#### ワークフロー設定ファイル (`.github/workflows/deploy.yml`)

```yaml
name: Deploy to Server

on:
  push:
    branches:
      - main

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: Deploy via SSH
        uses: appleboy/ssh-action@v1.0.3
        with:
          host: ${{ secrets.SSH_HOST }}
          username: ${{ secrets.SSH_USER }}
          key: ${{ secrets.SSH_PRIVATE_KEY }}
          port: ${{ secrets.SSH_PORT }}
          script: |
            cd /home/shota/bots/discode_OdaiBot
            git pull origin main
            sudo systemctl restart odaibotapi
            sudo systemctl restart odaibot
```

---

### 3.9 初回ユーザーの作成

DB とサービスが起動したら、Discord で最初の管理者ユーザーを作成します。

1. Discord サーバーで `/odai_dashboard` コマンドを実行（管理者権限が必要）
2. ボットがダイレクトメッセージで招待リンクを送信
3. リンクにアクセスしてパスワードを設定 → 管理者としてログイン完了

---

## 4. 運用手順書

### 4.1 日常運用

#### サービス状態の確認

```bash
sudo systemctl status odaibotapi odaibot
```

#### ログの確認

```bash
# API のログ
sudo journalctl -u odaibotapi -f

# Bot のログ
sudo journalctl -u odaibot -f
```

#### サービスの手動再起動

```bash
sudo systemctl restart odaibotapi
sudo systemctl restart odaibot
```

---

### 4.2 コードのデプロイ

通常は `main` ブランチへの push で自動デプロイされます。

手動でデプロイする場合:

```bash
cd /home/shota/bots/discode_OdaiBot
git pull origin main
sudo systemctl restart odaibotapi
sudo systemctl restart odaibot
```

---

### 4.3 Discord Bot のスラッシュコマンド

| コマンド | 権限 | 説明 |
|---|---|---|
| `/ping` | 全員 | 動作確認（pong! と返答） |
| `/odai_dashboard [username] [role]` | サーバー管理者 | Dashboard の招待リンクを生成。ユーザーが既存の場合はパスワードリセットリンクも表示 |
| `/odai [channel]` | サーバー管理者 | 指定チャンネル（省略時は実行チャンネル）にお題を即時投稿 |

**`/odai_dashboard` の詳細:**
- `username`: Dashboard に登録する Discord ユーザー名（省略時はコマンド実行者）
- `role`: `admin`（管理者）または `user`（一般ユーザー）、デフォルトは `admin`
- 既存ユーザーの場合: ログインリンク + パスワードリセットリンクを返す
- 新規ユーザーの場合: 招待リンクを返す（有効期限: `INVITE_EXPIRE_HOURS` 時間）

---

### 4.4 Dashboard の操作

#### ログイン

- URL: `https://your-domain.example.com`
- ユーザー名に Discord ID（username）、表示名（display_name）、またはユーザー ID のいずれかを入力してログイン可能

#### お題管理

| 操作 | 説明 |
|---|---|
| お題一覧 | ファイル名・タグ・お気に入りでフィルタリング可能。列ヘッダークリックでソート（お気に入り順も対応）|
| 使用状況ステータス | **未使用**（全チャンネル未投稿）/ **一部使用済み**（一部チャンネルで投稿済み）/ **使用済み**（全チャンネルで投稿済み）の3状態を表示 |
| お気に入り | ★ボタンでサーバー共有のお気に入りをトグル。お気に入り順ソート対応 |
| 画像プレビュー | 詳細モーダル内で画像を表示 |
| 詳細モーダル | 登録者・登録日・タグ・使用状況・アクティビティ履歴を表示。リネーム・タグ編集・削除操作も可能 |
| アクティビティ履歴 | 投稿・お気に入り・タグ付けの履歴を5件表示。ページネーションで過去分を参照可能 |
| お題追加 | JPG / PNG / WebP（最大 8MB）をアップロード。タグを付与可能 |
| インポート | 複数ファイルを一括登録 |

#### タグ管理

| 操作 | 説明 |
|---|---|
| タグ一覧 | タグ名・登録者を一覧表示。★ボタンでお気に入りトグル |
| タグ詳細モーダル | 登録者・登録日・お気に入り状態、使用中スケジュール一覧、タグ付きお題一覧（設定者・設定日付き）を表示 |
| タグ作成・編集 | 名前・説明を設定可能 |
| タグ削除 | 管理者のみ実行可能 |

#### スケジュール管理

- 投稿時刻（HH:MM 形式）とチャンネルを設定
- タグモード:
  - `all`: 全お題から抽選
  - `allow`: 指定タグのみ対象
  - `deny`: 指定タグを除外
- Bot が毎分スケジュールを確認して自動投稿

#### タグ管理

- タグの作成・編集・削除
- お題へのタグ付け（カンマ区切りで複数指定可）

#### ユーザー管理（管理者のみ）

- ユーザーの招待・編集・削除
- Discord ID（username）・表示名（display_name）・ロールを管理
- パスワードリセット: `/odai_dashboard` コマンドで新しいリセットリンクを発行

#### サーバー設定（管理者のみ）

- Bot の有効/無効切り替え
- タイムゾーン設定

---

### 4.5 データベースのメンテナンス

#### バックアップ

`scripts/backup.sh` が DB ダンプと画像ファイルを一括バックアップします。

```bash
# 手動実行
bash /home/shota/bots/discode_OdaiBot/scripts/backup.sh

# cron 登録（毎日午前3時に自動実行）
crontab -e
# 以下を追加:
# 0 3 * * * /home/shota/bots/discode_OdaiBot/scripts/backup.sh >> /home/shota/backups/odaibot/backup.log 2>&1
```

- バックアップ先: `BACKUP_DIR`（デフォルト: `/home/shota/backups/odaibot`）
- タイムスタンプ付きディレクトリ（例: `20260508_030000/`）に `db.sql.gz` と `images.tar.gz` を保存
- `BACKUP_KEEP_DAYS` 日超のバックアップは自動削除

#### マイグレーションの実行（スキーマ変更時）

```bash
# API を停止してからマイグレーション実行
sudo systemctl stop odaibotapi
cd /home/shota/bots/discode_OdaiBot
source venv/bin/activate
python OdaiBotDB/setup_db.py
sudo systemctl start odaibotapi
```

---

## 5. システム仕様

### 5.1 データベーススキーマ

#### `guild_settings` — サーバー設定

| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| guild_id | BIGINT UNIQUE | Discord サーバー ID |
| guild_name | VARCHAR(128) | サーバー名（Bot 起動時に自動同期） |
| bot_enabled | TINYINT(1) | Bot の有効/無効（デフォルト: 1） |
| timezone | VARCHAR(64) | タイムゾーン（デフォルト: Asia/Tokyo） |
| created_at / updated_at | DATETIME | |

#### `odai` — お題データ

| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| guild_id | BIGINT | Discord サーバー ID |
| filename | VARCHAR(255) | ファイル名（guild 内 UNIQUE） |
| storage_path | VARCHAR(1024) | ローカルファイルパス（`ODAI_IMAGE_DIR/{guild_id}/filename`）🆕 v1.3 |
| data | LONGBLOB NULL | 旧データ互換用（新規登録は NULL）🆕 v1.3 |
| used | TINYINT(1) | ローテーション管理フラグ（全件消化時にリセット） |
| is_favorite | TINYINT(1) | お気に入りフラグ（0: 通常, 1: お気に入り）🆕 v1.1 |
| created_by | BIGINT | 登録ユーザー ID（`users.id` 参照）🆕 v1.1 |
| added_at | DATETIME | 登録日時 |
| deleted_at | DATETIME | 論理削除日時（NULL = 有効） |

#### `tags` — タグ

| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| guild_id | BIGINT | Discord サーバー ID |
| name | VARCHAR(128) | タグ名（guild 内 UNIQUE） |
| description | VARCHAR(256) | タグの説明 |
| is_favorite | TINYINT(1) | お気に入りフラグ（0: 通常, 1: お気に入り）🆕 v1.1 |
| created_by | BIGINT | 作成ユーザー ID（`users.id` 参照）🆕 v1.1 |
| created_at / updated_at | DATETIME | |

#### `odai_tags` — お題とタグの中間テーブル

| カラム | 型 | 説明 |
|---|---|---|
| odai_id | BIGINT FK | `odai.id` |
| tag_id | BIGINT FK | `tags.id` |
| created_by | BIGINT | タグ付けユーザー ID（`users.id` 参照）🆕 v1.1 |
| created_at | DATETIME | |

#### `odai_history` — お題アクティビティ履歴 🆕 v1.1

| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| odai_id | BIGINT FK | `odai.id`（CASCADE DELETE） |
| guild_id | BIGINT | Discord サーバー ID |
| action | VARCHAR(32) | アクション種別（下表参照） |
| detail | VARCHAR(512) | アクション補足情報（チャンネル名・タグ名など） |
| user_id | BIGINT | 操作ユーザー ID（Bot 操作の場合は NULL） |
| created_at | DATETIME | 記録日時 |

**action 種別**

| action | 記録タイミング | detail の内容 |
|---|---|---|
| `posted` | Bot がお題を投稿したとき | `#チャンネル名` |
| `favorited` | お気に入りに追加したとき | — |
| `unfavorited` | お気に入りを解除したとき | — |
| `tagged` | タグを付与したとき | タグ名 |
| `untagged` | タグを解除したとき | タグ名 |

#### `channels` — チャンネル一覧（Bot 起動時に自動同期）

| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| guild_id | BIGINT | Discord サーバー ID |
| channel_id | BIGINT | Discord チャンネル ID |
| name | VARCHAR(128) | チャンネル名 |
| created_at / updated_at | DATETIME | |

#### `schedules` — 自動投稿スケジュール

| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| guild_id | BIGINT | Discord サーバー ID |
| channel_id | BIGINT | 投稿先チャンネル ID |
| time | VARCHAR(5) | 投稿時刻（HH:MM 形式） |
| enabled | TINYINT(1) | 有効フラグ |
| tag_mode | VARCHAR(16) | `all` / `allow` / `deny` |
| tag_list | TEXT | JSON 配列形式のタグリスト |
| created_at / updated_at | DATETIME | |

#### `odai_usage` — お題使用履歴

| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| guild_id | BIGINT | Discord サーバー ID |
| channel_id | BIGINT | 投稿チャンネル ID |
| odai_id | BIGINT FK | `odai.id` |
| used_at | DATETIME | 投稿日時 |

#### `post_history` — 投稿履歴（成功・失敗ログ）

| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| guild_id | BIGINT | |
| channel_id | BIGINT | |
| odai_id | BIGINT | |
| posted_at | DATETIME | |
| result | VARCHAR(32) | 結果（`success` / `error` など） |
| message | VARCHAR(512) | 詳細メッセージ |

#### `users` — ダッシュボードユーザー

| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| username | VARCHAR(128) UNIQUE | Discord ID（ログイン識別子） |
| display_name | VARCHAR(128) | 表示名（任意） |
| password_hash | VARCHAR(256) | PBKDF2-SHA256 ハッシュ（salt$hash 形式） |
| api_token | VARCHAR(128) UNIQUE | Bearer トークン（ログイン時に再発行） |
| created_at / updated_at | DATETIME | |

#### `user_guilds` — ユーザーとサーバーの対応

| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| user_id | BIGINT FK | `users.id` |
| guild_id | BIGINT | Discord サーバー ID |
| role | VARCHAR(32) | `admin` / `user` |
| created_at / updated_at | DATETIME | |

#### `user_invites` — 招待トークン

| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| guild_id | BIGINT | Discord サーバー ID |
| username | VARCHAR(128) | 招待するユーザー名 |
| role | VARCHAR(32) | 付与するロール |
| invite_token | VARCHAR(128) UNIQUE | URL に埋め込むトークン |
| expires_at | DATETIME | 有効期限 |
| used | TINYINT(1) | 使用済みフラグ |
| used_at | DATETIME | 使用日時 |
| created_at / updated_at | DATETIME | |

---

### 5.2 API エンドポイント一覧

ベース URL: `https://your-domain.example.com`  
認証: `Authorization: Bearer <token>` ヘッダー

#### 認証（グローバル）

| メソッド | パス | 認証 | 説明 |
|---|---|---|---|
| POST | `/api/auth/login` | 不要 | グローバルログイン（全サーバーのギルド情報を返す）⚡ レート制限: 10回/分 |
| GET | `/api/auth/guilds` | Bearer | 所属サーバー一覧を取得 |

#### 認証（サーバー別）`/api/guilds/{guild_id}/auth`

| メソッド | パス | 認証 | 説明 |
|---|---|---|---|
| POST | `.../login` | 不要 | ログイン（username / display_name / ID 対応）⚡ レート制限: 10回/分 |
| POST | `.../register` | 不要 | 招待トークンでユーザー登録 |
| POST | `.../reset-password` | 不要 | 招待トークンでパスワードリセット ⚡ レート制限: 5回/分 |
| GET | `.../invite-info` | 不要 | 招待トークンのユーザー情報取得 |
| POST | `.../invite` | admin | 招待トークン発行 |
| GET | `.../users` | admin | ユーザー一覧取得 |
| POST | `.../users` | admin | ユーザー作成 |
| PUT | `.../users/{user_id}` | admin | ユーザー更新 |
| DELETE | `.../users/{user_id}` | admin | ユーザー削除 |

#### お題 `/api/guilds/{guild_id}/odai`

| メソッド | パス | 認証 | 説明 |
|---|---|---|---|
| GET | `` | Bearer | お題一覧（`filename`, `tag`, `favorite` でフィルタ可）。レスポンスに `usage_count`, `total_channels`, `created_by_name` を含む |
| POST | `` | Bearer | お題アップロード（multipart/form-data）。`created_by` を保存 |
| POST | `.../import` | Bearer | 複数お題一括インポート。`created_by` を保存 |
| PUT | `.../{odai_id}` | Bearer | お題更新（filename / tags / used / deleted / is_favorite）。タグ差分・お気に入り変更を `odai_history` に記録 |
| GET | `.../{odai_id}/image` | Bearer | 画像バイナリ取得 |
| GET | `.../{odai_id}/usage` | Bearer | チャンネル別投稿履歴一覧 |
| GET | `.../{odai_id}/history` | Bearer | アクティビティ履歴（`page`, `per_page` でページネーション）🆕 v1.1 |
| DELETE | `.../{odai_id}` | admin | お題削除（論理削除） |

**GET `/{odai_id}/history` レスポンス形式:**

```json
{
  "data": [
    { "id": 1, "action": "posted", "detail": "#general", "user_id": null, "user_name": null, "created_at": "..." }
  ],
  "total": 10,
  "page": 1,
  "per_page": 5,
  "total_pages": 2
}
```

#### タグ `/api/guilds/{guild_id}/tags`

| メソッド | パス | 認証 | 説明 |
|---|---|---|---|
| GET | `` | Bearer | タグ一覧（`q` でキーワード検索可）。レスポンスに `created_by_name`, `is_favorite` を含む |
| POST | `` | Bearer | タグ作成。`created_by` を保存 |
| PUT | `.../{tag_id}` | Bearer | タグ更新（name / description / is_favorite） |
| DELETE | `.../{tag_id}` | admin | タグ削除 |
| GET | `.../{tag_id}/detail` | Bearer | タグ詳細（使用中スケジュール・お題一覧・登録者情報）🆕 v1.1 |

**GET `/{tag_id}/detail` レスポンス形式:**

```json
{
  "data": {
    "id": 1, "name": "タグ名", "description": "説明", "is_favorite": false,
    "created_by_name": "ユーザー名", "created_at": "...",
    "odai": [
      { "id": 1, "filename": "img.jpg", "tagged_at": "...", "tagged_by_name": "ユーザー名" }
    ],
    "schedules": [
      { "id": 1, "channel_id": "123", "channel_name": "general", "time": "09:00", "tag_mode": "allow" }
    ]
  }
}
```

#### スケジュール `/api/guilds/{guild_id}/schedules`

| メソッド | パス | 認証 | 説明 |
|---|---|---|---|
| GET | `` | Bearer | スケジュール一覧 |
| POST | `` | Bearer | スケジュール作成 |
| PUT | `.../{schedule_id}` | Bearer | スケジュール更新 |
| DELETE | `.../{schedule_id}` | admin | スケジュール削除 |

#### 設定 `/api/guilds/{guild_id}/settings`

| メソッド | パス | 認証 | 説明 |
|---|---|---|---|
| GET | `.../name` | 不要 | サーバー名取得（招待登録ページ用） |
| GET | `.../channels` | Bearer | チャンネル一覧取得 |
| GET | `` | Bearer | サーバー設定取得 |
| PUT | `` | admin | サーバー設定更新 |

#### その他

| メソッド | パス | 認証 | 説明 |
|---|---|---|---|
| GET | `/api/guilds/{guild_id}/summary` | Bearer | お題サマリー情報 |
| POST | `/api/guilds/{guild_id}/test-post` | Bearer | テスト投稿（指定チャンネルへ即時送信） |

---

### 5.3 ロールと権限

| 操作 | admin | user |
|---|---|---|
| お題の閲覧・追加・編集 | ✅ | ✅ |
| お題の削除 | ✅ | ❌ |
| タグの作成・編集 | ✅ | ✅ |
| タグの削除 | ✅ | ❌ |
| スケジュールの作成・編集 | ✅ | ✅ |
| スケジュールの削除 | ✅ | ❌ |
| サーバー設定の変更 | ✅ | ❌ |
| ユーザー管理 | ✅ | ❌ |
| 招待リンクの発行 | ✅ | ❌ |

---

### 5.4 認証フロー

```
[初回登録]
/odai_dashboard コマンド（Discord）
    → invite_token 生成（有効期限付き）
    → Dashboard #/register?guild_id=xxx&invite=yyy
    → パスワード設定 → Bearer token 発行

[ログイン]
Dashboard ログインフォーム
    → POST /api/auth/login
    → Bearer token を localStorage に保存
    → 以降のリクエストは Authorization: Bearer <token>

[パスワードリセット]
/odai_dashboard コマンド（既存ユーザー）
    → reset_token 生成
    → Dashboard #/reset-password?invite=zzz
    → 新パスワード設定
```

---

### 5.5 スケジューラー動作仕様

- Bot 起動時にスケジューラーが開始（毎分 tick）
- 各 tick で全参加サーバーのスケジュールを確認
- 現在時刻（HH:MM）が一致し `enabled = 1` のスケジュールを実行
- `tag_mode` に従ってお題を抽選:
  - `all`: 未使用かつ未削除のお題から抽選
  - `allow`: 指定タグを持つお題のみから抽選
  - `deny`: 指定タグを持つお題を除外して抽選
- 全お題が使用済みの場合: 全レコードの `used` をリセットして再抽選
- 投稿後: `odai.used = 1`、`odai_usage` にレコード挿入、`post_history` に結果記録

---

### 5.6 画像アップロード仕様

| 項目 | 仕様 |
|---|---|
| 対応形式 | JPEG / PNG / WebP |
| 最大ファイルサイズ | 8 MB |
| 保存方式 | ローカルファイル（`ODAI_IMAGE_DIR/{guild_id}/filename`）🆕 v1.3 |
| DB 保持内容 | ファイル名 + `storage_path`（実ファイルパス）のみ。`data` カラムは NULL |
| ファイル名の重複 | サーバー内で UNIQUE（同名は 409 エラー） |
| ファイル名変更 | Dashboard 編集画面から変更可能 |

---

### 5.7 パスワード仕様

| 項目 | 仕様 |
|---|---|
| 最小文字数 | 8 文字 |
| ハッシュ方式 | PBKDF2-SHA256（反復 120,000 回） |
| ソルト | 16 バイトランダム（hex エンコード） |
| 保存形式 | `{salt}${hash}` |

---

### 5.8 環境変数一覧

| 変数名 | 必須 | デフォルト | 説明 |
|---|---|---|---|
| `MYSQL_HOST` | — | `127.0.0.1` | MySQL ホスト |
| `MYSQL_PORT` | — | `3306` | MySQL ポート |
| `MYSQL_USER` | — | `root` | MySQL ユーザー |
| `MYSQL_PASSWORD` | — | `""` | MySQL パスワード |
| `MYSQL_DATABASE` | — | `odai_bot` | データベース名 |
| `DISCORD_BOT_TOKEN` | ✅ | — | Discord Bot トークン |
| `DASHBOARD_BASE_URL` | — | `http://localhost:3000` | Dashboard の公開 URL |
| `INVITE_EXPIRE_HOURS` | — | `24` | 招待トークンの有効期限（時間） |
| `ODAI_IMAGE_DIR` | — | `/data/odai` | お題画像の保存先ディレクトリ 🆕 v1.3 |
| `BACKUP_DIR` | — | `/home/shota/backups/odaibot` | バックアップ保存先（`scripts/backup.sh` 用）🆕 v1.3 |
| `BACKUP_KEEP_DAYS` | — | `7` | バックアップの保持日数 🆕 v1.3 |

---

### 5.9 トラブルシューティング

#### API が "Lost connection to MySQL server" エラーを返す

MySQL 接続がアイドルタイムアウトした状態。  
`MySQLDatabase._ensure_connection()` が自動で再接続を試みます（最大 3 回）。  
解消しない場合は API を再起動:

```bash
sudo systemctl restart odaibotapi
```

#### GitHub Actions デプロイが `sudo: a password is required` で失敗する

sudoers の設定を確認:

```bash
sudo cat /etc/sudoers.d/odaibot
```

以下が正確に設定されているか確認（`/usr/bin/systemctl` であること）:

```
shota ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart odaibotapi
shota ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart odaibot
```

#### サーバーが古いブランチのコードを使っている

```bash
cd /home/shota/bots/discode_OdaiBot
git branch -a          # 現在のブランチ確認
git fetch origin
git reset --hard origin/main
```

#### お題が「未使用」のまま更新されない

Bot と API が両方正常に動いているか確認:

```bash
sudo systemctl status odaibotapi odaibot
```

投稿時に `odai_usage` テーブルにレコードが挿入され、`odai.used = 1` に更新されます。  
どちらかが停止していると使用状態が更新されません。

---

## 6. 更新履歴

### v1.3（2026-05-08）

#### API 変更

| 対象 | 変更内容 |
|---|---|
| `POST /login`、`POST /api/auth/login` | IP ベースのレート制限を追加（10回/分）。超過時は 429 + 待機時間を返す |
| `POST .../reset-password` | IP ベースのレート制限を追加（5回/分） |

#### DB スキーマ変更

| 対象 | 変更内容 |
|---|---|
| `odai.data` | `LONGBLOB NOT NULL` → `LONGBLOB NULL` に変更（新規登録は NULL、ファイル保存に移行） |
| `odai.storage_path` | 旧「インポート元パス（任意）」から「実ファイルパス（`ODAI_IMAGE_DIR/{guild_id}/filename`）」に変更 |

#### インフラ変更

- お題画像の保存先を MySQL LONGBLOB からローカルファイル（`ODAI_IMAGE_DIR/{guild_id}/filename`）に移行
- `scripts/backup.sh` を追加。DB ダンプ＋画像ディレクトリをタイムスタンプ付きで保存（cron 運用）
- `ODAI_IMAGE_DIR`、`BACKUP_DIR`、`BACKUP_KEEP_DAYS` 環境変数を追加

---

### v1.2（2026-04-29）

#### 機能追加

- ダッシュボードの各管理ページ（お題・タグ・スケジュール・ユーザー・招待・設定）を実装
- ユーザー管理（BAN・ロック・招待・プロフィール）
- メモ機能、メモ検索、フィルター・ソート
- 招待管理ページ（サイドバー独立タブ）
- テスト投稿プレビュー
- パスワードリセット・管理者 PW 変更
- `odai`・`tags` テーブルに `updated_at` カラムを追加

---

### v1.1（2025-05）

#### DB スキーマ変更

| 対象 | 変更内容 |
|---|---|
| `odai` テーブル | `is_favorite TINYINT(1) DEFAULT 0`、`created_by BIGINT NULL` カラムを追加 |
| `tags` テーブル | `is_favorite TINYINT(1) DEFAULT 0`、`created_by BIGINT NULL` カラムを追加 |
| `odai_tags` テーブル | `created_by BIGINT NULL` カラムを追加（タグ付け操作者の追跡） |
| `odai_history` テーブル | 新規作成。お題のアクティビティ（投稿・お気に入り・タグ付け）を記録 |

#### API 変更

| 対象エンドポイント | 変更内容 |
|---|---|
| `GET /odai` | レスポンスに `usage_count`（投稿済みチャンネル数）、`total_channels`（有効スケジュールチャンネル数）、`created_by_name` を追加。フィルタパラメータを `used` → `favorite` に変更 |
| `POST /odai`、`POST /odai/import` | 登録ユーザーを `created_by` として保存 |
| `PUT /odai/{odai_id}` | `is_favorite` フィールド追加。タグ差分（tagged/untagged）とお気に入り変更（favorited/unfavorited）を `odai_history` に自動記録 |
| `GET /odai/{odai_id}/usage` | チャンネル別投稿履歴を返す（既存エンドポイント、ルーティング整理） |
| `GET /odai/{odai_id}/history` | **新規追加。** ページネーション付きのアクティビティ履歴取得 |
| `GET /tags` | レスポンスに `created_by_name`、`is_favorite` を追加 |
| `POST /tags` | 作成ユーザーを `created_by` として保存 |
| `PUT /tags/{tag_id}` | `is_favorite` フィールド追加 |
| `GET /tags/{tag_id}/detail` | **新規追加。** タグの詳細情報（お題一覧・使用中スケジュール・登録者）を返す |

#### Dashboard 変更

- **お題一覧**: 使用状況を「未使用 / 一部使用済み / 使用済み」の3ステータスで表示（`odai_usage` + 有効スケジュールチャンネル数で算出）
- **お気に入り機能**: お題・タグ両方に★ボタンを追加。サーバー内で共有されるお気に入りフラグをワンクリックでトグル
- **ソート**: お気に入り順ソートをお題・タグ一覧に追加
- **お題詳細モーダル**: 操作列を「詳細」ボタンに統合。登録者・登録日・画像プレビューを表示
- **アクティビティ履歴**: 詳細モーダル内に最新5件を表示。ページネーションで過去分を参照可能
- **タグ詳細モーダル**: タグ登録者・登録日、お気に入りトグル、使用中スケジュール一覧、タグ付きお題一覧（設定者・設定日付き）を表示

---

### v1.0（初版）

- システム初期リリース
- Discord Bot（スラッシュコマンド・自動投稿スケジューラー）
- FastAPI による REST API
- バニラ JS 製 SPA ダッシュボード（お題・タグ・スケジュール・ユーザー管理）
- Bearer トークン認証、招待リンクによるユーザー登録フロー
