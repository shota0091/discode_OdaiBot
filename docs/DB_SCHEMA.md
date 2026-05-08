# OdaiBotDB データベース設計とセットアップ

## 1. 目的

`OdaiBotDB` は以下を集約した DB 層モジュールです。

- MySQL 接続ロジック（`database.py`）
- DB スキーマ定義（本ドキュメント）
- セットアップスクリプト（`setup_db.py`）

OdaiBotAPI・OdaiBot はともにこのモジュールを通じて DB にアクセスします。

---

## 2. セットアップ手順

### 2.1 環境変数の設定

プロジェクトルートに `.env` を作成し、以下を記載してください。

```env
MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=yourpassword
MYSQL_DATABASE=odai_bot

DISCORD_BOT_TOKEN=your_discord_bot_token
DASHBOARD_BASE_URL=http://localhost:3000
INVITE_EXPIRE_HOURS=1
SECRET_KEY=your_jwt_secret_key
```

| 変数名 | 省略時のデフォルト | 説明 |
|---|---|---|
| `MYSQL_HOST` | `127.0.0.1` | MySQL ホスト |
| `MYSQL_PORT` | `3306` | MySQL ポート |
| `MYSQL_USER` | `root` | MySQL ユーザー |
| `MYSQL_PASSWORD` | `""` | MySQL パスワード |
| `MYSQL_DATABASE` | `odai_bot` | データベース名 |
| `DISCORD_BOT_TOKEN` | - | Discord Bot トークン（必須） |
| `DASHBOARD_BASE_URL` | `http://localhost:3000` | Dashboard の公開 URL（招待リンク生成に使用） |
| `INVITE_EXPIRE_HOURS` | `24` | 招待トークンの有効時間（時間単位） |
| `SECRET_KEY` | - | JWT 署名用シークレット（必須） |

### 2.2 DB・テーブルの作成

```bash
# プロジェクトルートから実行
python -m OdaiBotDB.setup_db
```

`odai_bot` データベースとすべてのテーブルが作成されます。

---

## 3. DB 設計

### 3.1 guild_settings

Discord サーバーごとの設定情報を保持します。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---|---|---|---|---|
| `id` | BIGINT AUTO_INCREMENT | NOT NULL | - | 主キー |
| `guild_id` | BIGINT | NOT NULL | - | Discord サーバー ID |
| `bot_enabled` | TINYINT(1) | NOT NULL | `1` | Bot 有効フラグ |
| `timezone` | VARCHAR(64) | NULL | NULL | タイムゾーン（IANA 形式、例: `Asia/Tokyo`） |
| `dashboard_role` | VARCHAR(128) | NULL | NULL | Dashboard 操作可能ロール |
| `created_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 作成日時 |
| `updated_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 更新日時 |

- UNIQUE: `guild_id`

---

### 3.2 users

Dashboard / API のログインユーザーを保持します。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---|---|---|---|---|
| `id` | BIGINT AUTO_INCREMENT | NOT NULL | - | 主キー |
| `guild_id` | BIGINT | NOT NULL | - | Discord サーバー ID |
| `username` | VARCHAR(128) | NOT NULL | - | ログインユーザー名 |
| `password_hash` | VARCHAR(256) | NOT NULL | - | bcrypt ハッシュ化パスワード |
| `role` | VARCHAR(32) | NOT NULL | `user` | 権限（`admin` / `user`） |
| `api_token` | VARCHAR(128) | NULL | NULL | JWT アクセストークン |
| `created_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 作成日時 |
| `updated_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 更新日時 |

- UNIQUE: `(guild_id, username)`

---

### 3.3 user_invites

Discord Bot が発行する招待トークンを管理します。1 回のみ使用可能です。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---|---|---|---|---|
| `id` | BIGINT AUTO_INCREMENT | NOT NULL | - | 主キー |
| `guild_id` | BIGINT | NOT NULL | - | Discord サーバー ID |
| `username` | VARCHAR(128) | NOT NULL | - | 招待するユーザー名 |
| `role` | VARCHAR(32) | NOT NULL | - | 付与するロール（`admin` / `user`） |
| `invite_token` | VARCHAR(128) | NOT NULL | - | 招待トークン（`secrets.token_urlsafe(32)`） |
| `expires_at` | DATETIME | NOT NULL | - | 有効期限（`INVITE_EXPIRE_HOURS` で制御） |
| `used` | TINYINT(1) | NOT NULL | `0` | 使用済みフラグ |
| `used_at` | DATETIME | NULL | NULL | 使用日時 |
| `created_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 発行日時 |
| `updated_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 更新日時 |

- UNIQUE: `invite_token`

---

### 3.4 odai

お題画像のメタデータと画像バイナリを保持します。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---|---|---|---|---|
| `id` | BIGINT AUTO_INCREMENT | NOT NULL | - | 主キー |
| `guild_id` | BIGINT | NOT NULL | - | Discord サーバー ID |
| `filename` | VARCHAR(255) | NOT NULL | - | ファイル名 |
| `storage_path` | VARCHAR(1024) | NULL | NULL | 将来のストレージ移行用パス（現在は未使用） |
| `data` | LONGBLOB | NOT NULL | - | 画像バイナリ（推奨: 8MB 以内） |
| `used` | TINYINT(1) | NOT NULL | `0` | 手動管理フラグ（Dashboard で設定、1=ローテーション除外） |
| `added_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 登録日時 |
| `deleted_at` | DATETIME | NULL | NULL | 論理削除日時（NULL = 有効） |

- UNIQUE: `(guild_id, filename)`

---

### 3.5 tags

タグマスタを保持します。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---|---|---|---|---|
| `id` | BIGINT AUTO_INCREMENT | NOT NULL | - | 主キー |
| `guild_id` | BIGINT | NOT NULL | - | Discord サーバー ID |
| `name` | VARCHAR(128) | NOT NULL | - | タグ名 |
| `description` | VARCHAR(256) | NULL | NULL | タグ説明 |
| `created_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 作成日時 |
| `updated_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 更新日時 |

- UNIQUE: `(guild_id, name)`

---

### 3.6 odai_tags

お題とタグの多対多関係を管理します。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---|---|---|---|---|
| `odai_id` | BIGINT | NOT NULL | - | `odai.id` 参照 |
| `tag_id` | BIGINT | NOT NULL | - | `tags.id` 参照 |
| `created_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 作成日時 |

- PK: `(odai_id, tag_id)`
- FK: `odai_id` → `odai(id)`, `tag_id` → `tags(id)`

---

### 3.7 channels

スケジュールで使用するチャンネル情報のキャッシュです。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---|---|---|---|---|
| `id` | BIGINT AUTO_INCREMENT | NOT NULL | - | 主キー |
| `guild_id` | BIGINT | NOT NULL | - | Discord サーバー ID |
| `channel_id` | BIGINT | NOT NULL | - | Discord チャンネル ID |
| `name` | VARCHAR(128) | NULL | NULL | チャンネル名 |
| `created_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 作成日時 |
| `updated_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 更新日時 |

- UNIQUE: `(guild_id, channel_id)`

---

### 3.8 odai_usage

チャンネルごとの投稿済みお題を記録します。スケジュール Bot がチャンネル単位のお題ローテーションと自動リセットに使用します。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---|---|---|---|---|
| `id` | BIGINT AUTO_INCREMENT | NOT NULL | - | 主キー |
| `guild_id` | BIGINT | NOT NULL | - | Discord サーバー ID |
| `channel_id` | BIGINT | NOT NULL | - | 投稿先チャンネル ID |
| `odai_id` | BIGINT | NOT NULL | - | `odai.id` 参照 |
| `used_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 投稿日時 |

- UNIQUE: `(channel_id, odai_id)`
- FK: `odai_id` → `odai(id)` ON DELETE CASCADE

> **ローテーション**: チャンネルの未投稿お題がなくなったら `DELETE FROM odai_usage WHERE channel_id = ?` でリセット。チャンネルごとに独立。

---

### 3.9 schedules

自動投稿スケジュールを管理します。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---|---|---|---|---|
| `id` | BIGINT AUTO_INCREMENT | NOT NULL | - | 主キー |
| `guild_id` | BIGINT | NOT NULL | - | Discord サーバー ID |
| `channel_id` | BIGINT | NOT NULL | - | 投稿先チャンネル |
| `time` | VARCHAR(5) | NOT NULL | - | 投稿時刻（`HH:MM`） |
| `enabled` | TINYINT(1) | NOT NULL | `1` | 有効フラグ |
| `tag_mode` | VARCHAR(16) | NOT NULL | `all` | `all` / `allow` / `deny` |
| `tag_list` | TEXT | NULL | NULL | タグリスト（JSON 配列文字列） |
| `created_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 作成日時 |
| `updated_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 更新日時 |

`tag_mode` の意味:

| 値 | 説明 |
|---|---|
| `all` | タグを問わず全お題を対象にする |
| `allow` | `tag_list` に含まれるタグのお題のみ投稿 |
| `deny` | `tag_list` に含まれるタグのお題を除外 |

---

### 3.10 post_history

Bot の投稿履歴を記録します。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---|---|---|---|---|
| `id` | BIGINT AUTO_INCREMENT | NOT NULL | - | 主キー |
| `guild_id` | BIGINT | NOT NULL | - | Discord サーバー ID |
| `channel_id` | BIGINT | NOT NULL | - | 投稿先チャンネル |
| `odai_id` | BIGINT | NOT NULL | - | 投稿したお題 ID |
| `posted_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 投稿日時 |
| `result` | VARCHAR(32) | NOT NULL | - | 投稿結果（`success` / `failed`） |
| `message` | VARCHAR(512) | NULL | NULL | 失敗時のエラーメッセージ |

---

## 4. 初回セットアップフロー

1. Discord 管理者が Bot 上で `/odai_dashboard` コマンドを実行
2. Bot が `user_invites` に招待トークンを発行し、Dashboard の登録 URL を管理者に返す
3. 管理者が Dashboard の招待登録ページ（`#/register?guild_id=...&invite=...`）からパスワードを設定
4. API が `user_invites` を検証し、`users` にアカウントを作成
5. 招待トークンが `used = 1` になり、再利用不可になる

---

## 5. 注意事項

- テーブル作成は `setup_db.py` で手動実行します（起動時の自動生成は行いません）
- DB 変更時はこのファイルを更新してください
- `tag_list` は JSON 配列文字列（`["日常", "癒し"]`）として保存します
- 画像バイナリは LONGBLOB に保存するため、1 ファイルあたり **8MB 以内**を推奨します
