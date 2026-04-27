# お題Bot DB 定義書

## 1. 概要

本ドキュメントは、OdaiBotAPI・OdaiBot が共有するデータベーススキーマを定義します。実際のテーブル DDL および詳細なセットアップ手順は [`OdaiBotDB/DB_SCHEMA.md`](../OdaiBotDB/DB_SCHEMA.md) を参照してください。

| 項目 | 内容 |
|---|---|
| RDBMS | MySQL 8.0+ |
| 接続ライブラリ | `mysql-connector-python` |
| 接続クラス | `OdaiBotDB.database.MySQLDatabase` |
| 画像保存方式 | `odai.data`（LONGBLOB） |

---

## 2. テーブル一覧

| テーブル名 | 役割 |
|---|---|
| `guild_settings` | Discord サーバーごとの設定・サーバー名 |
| `users` | Dashboard ログインユーザー |
| `user_invites` | 招待トークン管理 |
| `odai` | お題画像メタデータ＋バイナリ |
| `tags` | タグマスタ |
| `odai_tags` | お題とタグの中間テーブル |
| `odai_usage` | チャンネルごとの投稿済みお題（多対多）|
| `channels` | Bot が同期したチャンネル情報（`guild_settings` と 1 対多） |
| `schedules` | 自動投稿スケジュール |
| `post_history` | 投稿履歴 |

---

## 3. テーブル定義

### 3.1 guild_settings

Discord サーバー単位の設定情報とサーバー名を保持します。`channels` テーブルと 1 対多の関係です。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---|---|---|---|---|
| `id` | BIGINT AUTO_INCREMENT | NOT NULL | - | 主キー |
| `guild_id` | BIGINT | NOT NULL | - | Discord サーバー ID |
| `guild_name` | VARCHAR(128) | NULL | NULL | Discord サーバー名（Bot が起動・`/odai_dashboard` 実行時に自動設定） |
| `bot_enabled` | TINYINT(1) | NOT NULL | `1` | Bot 有効フラグ |
| `timezone` | VARCHAR(64) | NULL | NULL | タイムゾーン（IANA 形式） |
| `dashboard_role` | VARCHAR(128) | NULL | NULL | Dashboard 操作可能ロール |
| `created_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 作成日時 |
| `updated_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 更新日時 |

- UNIQUE: `guild_id`

> **Bot による自動更新**: Bot 起動時（`on_ready`）および `/odai_dashboard` コマンド実行時に `guild_name` を `ON DUPLICATE KEY UPDATE` で書き込みます。

---

### 3.2 users

Dashboard / API のログインユーザーを保持します。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---|---|---|---|---|
| `id` | BIGINT AUTO_INCREMENT | NOT NULL | - | 主キー |
| `guild_id` | BIGINT | NOT NULL | - | Discord サーバー ID |
| `username` | VARCHAR(128) | NOT NULL | - | ログインユーザー名 |
| `password_hash` | VARCHAR(256) | NOT NULL | - | PBKDF2-HMAC-SHA256 ハッシュ化パスワード |
| `role` | VARCHAR(32) | NOT NULL | `user` | 権限（`admin` / `user`） |
| `api_token` | VARCHAR(128) | NULL | NULL | アクセストークン（`secrets.token_urlsafe(32)`） |
| `created_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 作成日時 |
| `updated_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 更新日時 |

- UNIQUE: `(guild_id, username)`
- UNIQUE: `api_token`

> **グローバルログイン**: `POST /api/auth/login` は `username` が一致する全 guild のユーザーレコードに同じトークンを設定します。これにより 1 つのトークンで複数 guild にアクセスできます。

---

### 3.3 user_invites

Discord Bot が発行する招待トークンを管理します。トークンは 1 回のみ使用可能です。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---|---|---|---|---|
| `id` | BIGINT AUTO_INCREMENT | NOT NULL | - | 主キー |
| `guild_id` | BIGINT | NOT NULL | - | Discord サーバー ID |
| `username` | VARCHAR(128) | NOT NULL | - | 招待するユーザー名 |
| `role` | VARCHAR(32) | NOT NULL | - | 付与するロール（`admin` / `user`） |
| `invite_token` | VARCHAR(128) | NOT NULL | - | 招待トークン（`secrets.token_urlsafe(32)`） |
| `expires_at` | DATETIME | NOT NULL | - | 有効期限（環境変数 `INVITE_EXPIRE_HOURS` で制御、デフォルト 24 時間） |
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
| `data` | LONGBLOB | NOT NULL | - | 画像バイナリ（最大 8MB） |
| `used` | TINYINT(1) | NOT NULL | `0` | 手動管理フラグ（Dashboard で管理者が設定） |
| `added_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 登録日時 |
| `deleted_at` | DATETIME | NULL | NULL | 論理削除日時（NULL = 有効） |

- UNIQUE: `(guild_id, filename)`
- 有効なお題: `deleted_at IS NULL`

> **`used` フラグについて**: 自動投稿の使用状況は `odai_usage` テーブルでチャンネルごとに管理します。`odai.used` は Dashboard 上での手動管理専用フラグです（例: 特定お題を全チャンネルの投稿対象から除外したい場合に使用）。

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

### 3.7 odai_usage

チャンネルごとに「どのお題を投稿済みか」を記録する多対多テーブルです。スケジュール Bot がお題ローテーション（全使用済み時の自動リセット）をチャンネル単位で独立管理するために使用します。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---|---|---|---|---|
| `id` | BIGINT AUTO_INCREMENT | NOT NULL | - | 主キー |
| `guild_id` | BIGINT | NOT NULL | - | Discord サーバー ID |
| `channel_id` | BIGINT | NOT NULL | - | 投稿先チャンネル ID |
| `odai_id` | BIGINT | NOT NULL | - | `odai.id` 参照 |
| `used_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 投稿日時 |

- UNIQUE: `(channel_id, odai_id)`
- FK: `odai_id` → `odai(id)`

> **ローテーションロジック**:  
> 1. 当該チャンネルで未投稿のお題（`odai_usage` に存在しないもの）をランダムに 1 件選択  
> 2. 未投稿お題が 0 件の場合: 当該チャンネルの `odai_usage` レコードを全削除してリセット → ステップ 1 を再実行  
> 3. 選択したお題を `odai_usage` に記録して投稿  
> 各チャンネルのリセットは独立しており、チャンネル A がリセットされてもチャンネル B には影響しません。

---

### 3.8 channels

Bot が同期したチャンネル情報を保持します。`guild_settings` と 1 対多の関係で、スケジュール一覧でのチャンネル名表示に使用します。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---|---|---|---|---|
| `id` | BIGINT AUTO_INCREMENT | NOT NULL | - | 主キー |
| `guild_id` | BIGINT | NOT NULL | - | Discord サーバー ID（`guild_settings.guild_id` 対応） |
| `channel_id` | BIGINT | NOT NULL | - | Discord チャンネル ID |
| `name` | VARCHAR(128) | NULL | NULL | チャンネル名 |
| `created_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 作成日時 |
| `updated_at` | DATETIME | NOT NULL | `CURRENT_TIMESTAMP` | 更新日時 |

- UNIQUE: `(guild_id, channel_id)`

> **Bot による自動更新**: Bot 起動時（`on_ready`）および `/odai_dashboard` 実行時に、guild 内の全テキストチャンネルを `ON DUPLICATE KEY UPDATE` で書き込みます。

---

### 3.9 schedules

自動投稿スケジュールを管理します。

| カラム名 | 型 | NULL | デフォルト | 説明 |
|---|---|---|---|---|
| `id` | BIGINT AUTO_INCREMENT | NOT NULL | - | 主キー |
| `guild_id` | BIGINT | NOT NULL | - | Discord サーバー ID |
| `channel_id` | BIGINT | NOT NULL | - | 投稿先チャンネル ID |
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

## 4. テーブル間リレーション

```
guild_settings (1) ──< channels (多)
   guild_id               guild_id

users (多) >── guild_settings (1)
   guild_id                guild_id

schedules (多) >── channels (参照のみ、FK なし)
   guild_id + channel_id   guild_id + channel_id

odai (1) ──< odai_usage (多) >── channels（論理参照）
   id           odai_id              channel_id
```

---

## 5. 代表クエリ

### 5.1 スケジュールにチャンネル名を付けて取得

```sql
SELECT s.*, c.name AS channel_name
FROM schedules s
LEFT JOIN channels c ON s.guild_id = c.guild_id AND s.channel_id = c.channel_id
WHERE s.guild_id = :guild_id
ORDER BY s.id;
```

### 5.2 グローバルログイン後の所属 guild 一覧

```sql
SELECT u.guild_id, u.role, gs.guild_name
FROM users u
LEFT JOIN guild_settings gs ON u.guild_id = gs.guild_id
WHERE u.api_token = :token;
```

### 5.3 チャンネルの未投稿お題を取得（tag_mode = 'allow' の例）

```sql
SELECT o.*
FROM odai o
JOIN odai_tags ot ON o.id = ot.odai_id
JOIN tags t ON ot.tag_id = t.id
WHERE o.guild_id = :guild_id
  AND o.deleted_at IS NULL
  AND o.used = 0
  AND t.name IN (:tag_list)
  AND o.id NOT IN (
    SELECT odai_id FROM odai_usage
    WHERE guild_id = :guild_id AND channel_id = :channel_id
  )
ORDER BY RAND()
LIMIT 1;
```

### 5.4 チャンネルの投稿済み状況をリセット

```sql
DELETE FROM odai_usage
WHERE guild_id = :guild_id AND channel_id = :channel_id;
```

### 5.5 ファイル名あいまい検索

```sql
SELECT * FROM odai
WHERE guild_id = :guild_id
  AND deleted_at IS NULL
  AND filename LIKE CONCAT('%', :keyword, '%');
```

---

## 6. 注意事項

- テーブル作成は `OdaiBotDB/setup_db.py` で手動実行、またはアプリ起動時に自動生成されます
- 既存 DB への `guild_name` カラム追加は `information_schema.COLUMNS` チェック後に `ALTER TABLE` で自動マイグレーションされます（`IF NOT EXISTS` は MySQL 8.0.3 未満では使用不可）
- 画像バイナリは LONGBLOB に保存するため、1 ファイルあたり 8MB 以内を推奨します
- `tag_list` は JSON 配列文字列（`["日常", "癒し"]`）として保存します
- `channels` テーブルはチャンネル名表示用であり、スケジュールの動作自体は `schedules.channel_id` のみで完結します
- `odai.used` は手動フラグです。チャンネルごとの自動投稿ローテーションは `odai_usage` で管理します
