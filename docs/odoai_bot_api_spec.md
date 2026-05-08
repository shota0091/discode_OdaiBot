# お題Bot API 設計書

## 1. 概要

OdaiBotAPI は、Discord お題Bot の管理 Dashboard と Discord Bot が共有するバックエンド API です。FastAPI で実装し、`OdaiBotDB` を通じて MySQL に接続します。

| 項目 | 内容 |
|---|---|
| フレームワーク | FastAPI 0.111.1 |
| 実行 | `uvicorn OdaiBotAPI.api:app` |
| 認証方式 | Bearer トークン（`users.api_token`） |
| エントリポイント | `OdaiBotAPI/api.py` |
| ルーター配置 | `OdaiBotAPI/routers/` 配下に機能単位で分割 |
| 共通依存 | `OdaiBotAPI/deps.py`（DB接続・認証・ヘルパー） |

---

## 2. エンドポイント一覧

### グローバル認証（guild_id 不要）

| メソッド | パス | 説明 | 認証 |
|---|---|---|---|
| POST | `/api/auth/login` | グローバルログイン（複数 guild 対応） | 不要 |
| GET | `/api/auth/guilds` | ログイン中ユーザーの所属 guild 一覧 | 必要 |

### Guild 単位

| メソッド | パス | 説明 | 認証 |
|---|---|---|---|
| POST | `/api/guilds/{guild_id}/auth/login` | per-guild ログイン（後方互換） | 不要 |
| POST | `/api/guilds/{guild_id}/auth/register` | 招待登録 | 不要 |
| POST | `/api/guilds/{guild_id}/auth/invite` | 招待トークン発行 | admin |
| GET | `/api/guilds/{guild_id}/auth/users` | ユーザー一覧 | admin |
| POST | `/api/guilds/{guild_id}/auth/users` | ユーザー作成 | admin |
| PUT | `/api/guilds/{guild_id}/auth/users/{user_id}` | ユーザー更新 | admin |
| DELETE | `/api/guilds/{guild_id}/auth/users/{user_id}` | ユーザー削除 | admin |
| GET | `/api/guilds/{guild_id}/odai` | お題一覧取得（ファイル名あいまい検索・タグ・使用状況フィルタ） | 必要 |
| POST | `/api/guilds/{guild_id}/odai` | お題登録（単体） | 必要 |
| POST | `/api/guilds/{guild_id}/odai/import` | お題一括インポート | 必要 |
| PUT | `/api/guilds/{guild_id}/odai/{odai_id}` | お題更新 | 必要 |
| DELETE | `/api/guilds/{guild_id}/odai/{odai_id}` | お題削除 | 必要 |
| GET | `/api/guilds/{guild_id}/odai/{odai_id}/image` | お題画像バイナリ取得 | 必要 |
| GET | `/api/guilds/{guild_id}/tags` | タグ一覧取得 | 必要 |
| POST | `/api/guilds/{guild_id}/tags` | タグ作成 | 必要 |
| PUT | `/api/guilds/{guild_id}/tags/{tag_id}` | タグ更新 | 必要 |
| DELETE | `/api/guilds/{guild_id}/tags/{tag_id}` | タグ削除 | 必要 |
| GET | `/api/guilds/{guild_id}/schedules` | スケジュール一覧 | 必要 |
| POST | `/api/guilds/{guild_id}/schedules` | スケジュール作成 | 必要 |
| PUT | `/api/guilds/{guild_id}/schedules/{schedule_id}` | スケジュール更新 | 必要 |
| DELETE | `/api/guilds/{guild_id}/schedules/{schedule_id}` | スケジュール削除 | 必要 |
| GET | `/api/guilds/{guild_id}/settings` | サーバー設定取得 | 必要 |
| PUT | `/api/guilds/{guild_id}/settings` | サーバー設定更新 | admin |
| GET | `/api/guilds/{guild_id}/dashboard-summary` | ダッシュボード概要 | 必要 |

---

## 3. 共通仕様

### 3.1 認証

ログイン・招待登録以外のすべてのエンドポイントで `Authorization` ヘッダーが必要です。

```
Authorization: Bearer {access_token}
```

- `access_token` はグローバルログインまたは招待登録時に取得します
- グローバルログインで取得したトークンは、ユーザーが所属する**全 guild で共通**で使用できます
- per-guild エンドポイントではパスパラメータの `guild_id` と認証ユーザーの `guild_id` が検証されます
- パスワードは PBKDF2-HMAC-SHA256（120,000 イテレーション）でハッシュ化します

### 3.2 ロール

| ロール | 説明 |
|---|---|
| `admin` | 全操作が可能 |
| `user` | 読み取りと一部の更新が可能（ユーザー管理・設定変更は不可） |

### 3.3 HTTP ステータスコード

| コード | 意味 |
|---|---|
| 200 | 成功（取得・更新・作成） |
| 201 | 作成成功 |
| 204 | 削除成功（レスポンスボディなし） |
| 400 | リクエスト不正（バリデーションエラーなど） |
| 401 | 未認証（トークンなし・無効） |
| 403 | 権限不足（`admin` 専用エンドポイントへの `user` アクセスなど） |
| 404 | リソースが存在しない |
| 409 | 競合（重複登録など） |
| 413 | ファイルサイズ超過 |
| 415 | サポート外のファイル形式 |
| 500 | サーバー内部エラー |

### 3.4 エラーレスポンス

```json
{
  "detail": "エラーメッセージ"
}
```

---

## 4. API 詳細

### 4.1 グローバル認証 API

#### POST /api/auth/login

guild_id を指定せずにログインします。同名ユーザーが複数の guild に存在する場合はすべての guild を返します。ログイン成功時は、該当する全ユーザーレコードに同じトークンを設定します。

- **リクエスト（JSON）**

```json
{ "username": "alice", "password": "password123" }
```

- **レスポンス 200**

```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "role": "admin",
  "guilds": [
    { "guild_id": "987654321098765432", "guild_name": "My Server", "role": "admin" },
    { "guild_id": "123456789012345678", "guild_name": "Another Server", "role": "user" }
  ]
}
```

| フィールド | 説明 |
|---|---|
| `role` | 最初に一致した guild のロール |
| `guilds` | 所属する全 guild の一覧。`guild_name` は Bot が同期済みの場合のみ設定される |

- **エラー**
  - 401: ユーザー名またはパスワードが不正

---

#### GET /api/auth/guilds

現在のトークンで認証されたユーザーが所属する guild 一覧を返します。

- **レスポンス 200**

```json
{
  "data": [
    { "guild_id": "987654321098765432", "guild_name": "My Server", "role": "admin" }
  ]
}
```

- **エラー**
  - 401: トークンなし・無効

---

### 4.2 per-guild 認証 API

#### POST /api/guilds/{guild_id}/auth/login

特定の guild に対してログインします（後方互換用）。

- **リクエスト（JSON）**

```json
{ "username": "alice", "password": "password123" }
```

- **レスポンス 200**

```json
{ "access_token": "eyJ...", "token_type": "bearer", "role": "admin" }
```

- **エラー**
  - 401: ユーザー名またはパスワードが不正

---

#### POST /api/guilds/{guild_id}/auth/register

招待トークンを使用して新規ユーザーを登録します。

- **リクエスト（JSON）**

```json
{ "invite_token": "abc123xyz", "password": "password123" }
```

- **レスポンス 200**

```json
{ "access_token": "eyJ...", "token_type": "bearer", "role": "user" }
```

- **エラー**
  - 400: パスワードが 8 文字未満
  - 404: 招待トークンが存在しない
  - 409: トークンが使用済みまたは期限切れ、同名ユーザーが既に存在する

---

#### POST /api/guilds/{guild_id}/auth/invite

招待トークンを発行します。`admin` 権限が必要です。

- **リクエスト（JSON）**

```json
{ "username": "bob", "role": "user" }
```

- **レスポンス 200**

```json
{ "invite_token": "abc123xyz", "expires_at": "2026-04-26T12:00:00" }
```

- **エラー**
  - 400: `role` が `admin` / `user` 以外
  - 409: 同名ユーザーが既に存在する

---

#### GET /api/guilds/{guild_id}/auth/users

Dashboard ユーザー一覧を返します。`admin` 権限が必要です。

---

#### POST /api/guilds/{guild_id}/auth/users

新規ユーザーを直接作成します。

- Guild にユーザーが存在しない場合のみ認証なしで作成可能（初回セットアップ用）
- 既にユーザーが存在する場合は `admin` 権限が必要

---

#### PUT /api/guilds/{guild_id}/auth/users/{user_id}

ユーザー情報を更新します。`admin` 権限が必要です。

---

#### DELETE /api/guilds/{guild_id}/auth/users/{user_id}

ユーザーを削除します。自分自身の削除は不可です。`admin` 権限が必要です。

---

### 4.3 お題 API

#### GET /api/guilds/{guild_id}/odai

お題一覧を取得します。

- **クエリパラメータ**

| パラメータ | 型 | 説明 |
|---|---|---|
| `filename` | string | ファイル名のあいまい検索（部分一致 LIKE）。省略時は全件 |
| `tag` | string | タグ名でフィルタ（省略時は全タグ） |
| `used` | boolean | `true`: 使用済み / `false`: 未使用（省略時は全件） |

- **レスポンス 200**

```json
{
  "data": [
    {
      "id": 1,
      "filename": "odai1.jpg",
      "used": false,
      "tags": ["日常", "癒し"],
      "added_at": "2026-04-01T12:00:00"
    }
  ]
}
```

> `used` フィールドは Dashboard での手動管理フラグです。チャンネルごとの投稿履歴は `odai_usage` テーブルで別途管理されます。

---

#### POST /api/guilds/{guild_id}/odai

お題画像を 1 件登録します。

- **リクエスト（multipart/form-data）**

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `file` | File | ○ | 画像ファイル（JPEG / PNG / WebP）|
| `tags` | string | - | カンマ区切りのタグ名 |

- 最大ファイルサイズ: **8MB**

---

#### POST /api/guilds/{guild_id}/odai/import

複数のお題画像を一括登録します。ファイルごとに成否を返します。

---

#### PUT /api/guilds/{guild_id}/odai/{odai_id}

お題のメタデータを更新します。

---

#### DELETE /api/guilds/{guild_id}/odai/{odai_id}

お題を削除します（論理削除）。

---

#### GET /api/guilds/{guild_id}/odai/{odai_id}/image

お題の画像バイナリを返します。Dashboard のプレビュー機能で使用します。

- **レスポンス 200**: ファイル拡張子に応じた `Content-Type`（`image/jpeg` / `image/png` / `image/webp`）でバイナリを返します
- **エラー**: 404（お題が存在しない、または論理削除済み）

---

### 4.4 タグ API

`GET / POST / PUT / DELETE` の CRUD を提供します。詳細は per-guild パスの `/tags` 系を参照してください。

---

### 4.5 スケジュール API

#### GET /api/guilds/{guild_id}/schedules

スケジュール一覧を返します。チャンネル名が `channels` テーブルに登録済みの場合は `channel_name` も返します。

- **レスポンス 200**

```json
{
  "data": [
    {
      "id": 1,
      "channel_id": "987654321098765432",
      "channel_name": "general",
      "time": "09:00",
      "enabled": true,
      "tag_mode": "allow",
      "tag_list": ["日常", "癒し"],
      "created_at": "2026-04-01T00:00:00",
      "updated_at": null
    }
  ]
}
```

> `channel_id` は JS の整数精度損失を避けるため文字列で返します。  
> `channel_name` は Bot が未同期の場合は `null` になります。

---

#### POST /api/guilds/{guild_id}/schedules

スケジュールを作成します。

- **リクエスト（JSON）**

```json
{
  "channel_id": "987654321098765432",
  "time": "09:00",
  "enabled": true,
  "tag_mode": "allow",
  "tag_list": ["日常"]
}
```

| フィールド | 型 | 必須 | 説明 |
|---|---|---|---|
| `channel_id` | string \| integer | ○ | Discord チャンネル ID（文字列・整数どちらも可） |
| `time` | string | ○ | `HH:MM` 形式 |
| `enabled` | boolean | - | 有効フラグ（省略時 `true`） |
| `tag_mode` | string | - | `all` / `allow` / `deny`（省略時 `all`） |
| `tag_list` | string[] | - | フィルタするタグ名のリスト |

- **エラー**
  - 400: `time` が `HH:MM` 形式でない、`tag_mode` が不正

---

#### PUT /api/guilds/{guild_id}/schedules/{schedule_id}

スケジュールを更新します。リクエスト形式は POST と同様です。

---

#### DELETE /api/guilds/{guild_id}/schedules/{schedule_id}

スケジュールを削除します。`admin` 権限が必要です。

---

### 4.6 設定 API

#### GET /api/guilds/{guild_id}/settings

Guild の設定を取得します。未作成の場合はデフォルト値を返します。

- **レスポンス 200**

```json
{
  "data": {
    "guild_id": "123456789012345678",
    "guild_name": "My Server",
    "bot_enabled": true,
    "timezone": "Asia/Tokyo",
    "updated_at": null
  }
}
```

> `guild_name` は Bot が同期済みの場合のみ設定されます。

---

#### PUT /api/guilds/{guild_id}/settings

Guild の設定を更新します（設定が未作成の場合は新規作成）。`admin` 権限が必要です。

- **リクエスト（JSON）**（変更フィールドのみ指定可）

```json
{ "bot_enabled": true, "timezone": "Asia/Tokyo" }
```

---

### 4.7 ダッシュボード概要 API

#### GET /api/guilds/{guild_id}/dashboard-summary

ダッシュボードのサマリー情報を返します。

---

## 5. テスト

pytest によるユニットテストを提供しています。外部依存（MySQL・Discord）は `unittest.mock` でモックします。

詳細は [APITest.md](./APITest.md) を参照してください。

```bash
pytest
pytest -v
pytest OdaiBotAPI/tests/test_odai.py
```

---

## 6. 関連ドキュメント

| ドキュメント | パス |
|---|---|
| DB スキーマ | [`OdaiBotDB/DB_SCHEMA.md`](../OdaiBotDB/DB_SCHEMA.md) |
| DB 定義書 | [`OdaiBotAPI/odoai_bot_db_spec.md`](./odoai_bot_db_spec.md) |
| テスト実行ガイド | [`OdaiBotAPI/APITest.md`](./APITest.md) |
| Dashboard 仕様 | [`OdaiBotdashboard/odoai_bot_dashboard_spec.md`](../OdaiBotdashboard/odoai_bot_dashboard_spec.md) |
| Bot 仕様 | [`OdaiBot/odoai_bot_spec.md`](../OdaiBot/odoai_bot_spec.md) |
