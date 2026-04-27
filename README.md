# OdaiBot

Discord サーバー向けのお題自動投稿 Bot と Web 管理 Dashboard のモノレポです。

お題画像の登録・タグ管理・投稿スケジュール設定を Dashboard の Web UI で操作し、Discord Bot が自動でお題を投稿します。

---

## モジュール構成

```
discode_OdaiBot/
  OdaiBot/               # Discord Bot 本体
  OdaiBotAPI/            # REST API（FastAPI）
  OdaiBotDB/             # DB 接続・スキーマ管理（MySQL）
  OdaiBotdashboard/      # Web 管理 Dashboard（Vanilla SPA）
  .env                   # 環境変数（要作成）
  pytest.ini             # テスト設定
  Procfile               # 起動設定（Heroku / 互換ランナー用）
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
  schemas.py             # Pydantic スキーマ定義
  routers/
    auth.py              # 認証・ユーザー管理
    odai.py              # お題 CRUD・一括インポート
    tags.py              # タグ CRUD
    schedules.py         # スケジュール CRUD
    settings.py          # サーバー設定
    summary.py           # ダッシュボード概要
    permissions.py       # チャンネルタグ許可設定
    test_post.py         # テスト投稿
  tests/                 # pytest ユニットテスト
  requirements.txt
  requirements-test.txt
  odoai_bot_api_spec.md  # API 仕様書
  odoai_bot_db_spec.md   # DB 定義書
  APITest.md             # テスト実行ガイド
```

### OdaiBotDB

MySQL 接続ロジックと DB セットアップスクリプトを集約した DB 層モジュールです。

```
OdaiBotDB/
  database.py            # MySQLDatabase 接続クラス
  setup_db.py            # テーブル作成スクリプト
  DB_SCHEMA.md           # DB スキーマ定義書
```

### OdaiBotdashboard

Vanilla HTML / CSS / JavaScript で実装した SPA の管理 Dashboard です。

```
OdaiBotdashboard/
  index.html             # SPA エントリポイント
  css/
    style.css            # 全画面共通スタイル（Discord ライクなダークテーマ）
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
      schedules.js       # スケジュール管理
      settings.js        # サーバー設定
  odoai_bot_dashboard_spec.md
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
```

各モジュールにも `.env.example` があります（モジュール単体で動かす際の参考用）。

| ファイル | 用途 |
|---|---|
| `.env.example` | 全変数をまとめたルートひな形（通常はこれを使用） |
| `OdaiBotAPI/.env.example` | API 単体起動時の参考 |
| `OdaiBot/.env.example` | Bot 単体起動時の参考 |
| `OdaiBotDB/.env.example` | DB セットアップ単体実行時の参考 |
| `OdaiBotdashboard/.env.example` | Dashboard の設定方法の案内（`js/config.js` を編集） |

### 4. パッケージのインストール

```bash
# API 依存
pip install -r OdaiBotAPI/requirements.txt

# Bot 依存（OdaiBotAPI と共通部分あり）
pip install -r OdaiBot/requirements.txt
```

### 5. DB のセットアップ

MySQL サーバーを起動した状態で以下を実行します。

```bash
python -m OdaiBotDB.setup_db
```

`odai_bot` データベースと全テーブルが作成されます。

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

`OdaiBotdashboard/index.html` をローカルの HTTP サーバーで配信します。

```bash
# Python 組み込みサーバーを使う場合
cd OdaiBotdashboard
python -m http.server 3000
```

ブラウザで `http://localhost:3000` を開いてください。

---

## 初回セットアップフロー

1. DB を作成（`setup_db.py` 実行）
2. API サーバーを起動
3. Dashboard を開き、ユーザー作成画面（`#/dashboard/users` → 「ユーザー追加」）から最初の `admin` ユーザーを作成
   - Guild にユーザーが存在しない場合のみ認証なしで作成できます
4. 作成したユーザーでログイン
5. タグ・お題・スケジュールを設定
6. Discord Bot を起動

---

## テスト

pytest によるユニットテストを提供しています。MySQL・Discord への接続は不要で、すべてモックで実行します。

```bash
# 全テスト実行（プロジェクトルートから）
pytest

# 詳細表示
pytest -v

# 特定ファイルのみ
pytest OdaiBotAPI/tests/test_odai.py

# テスト用パッケージのインストール（未インストールの場合）
pip install -r OdaiBotAPI/requirements-test.txt
```

詳細は [OdaiBotAPI/APITest.md](OdaiBotAPI/APITest.md) を参照してください。

---

## 主要仕様書

| ドキュメント | 内容 |
|---|---|
| [OdaiBotAPI/odoai_bot_api_spec.md](OdaiBotAPI/odoai_bot_api_spec.md) | REST API エンドポイント仕様 |
| [OdaiBotAPI/odoai_bot_db_spec.md](OdaiBotAPI/odoai_bot_db_spec.md) | DB テーブル定義書 |
| [OdaiBotAPI/APITest.md](OdaiBotAPI/APITest.md) | テスト実行ガイド |
| [OdaiBotDB/DB_SCHEMA.md](OdaiBotDB/DB_SCHEMA.md) | DB スキーマ DDL・セットアップ手順 |
| [OdaiBot/odoai_bot_spec.md](OdaiBot/odoai_bot_spec.md) | Discord Bot 仕様 |
| [OdaiBotdashboard/odoai_bot_dashboard_spec.md](OdaiBotdashboard/odoai_bot_dashboard_spec.md) | Dashboard 画面仕様 |

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
- Bot は 1 分ごとに `schedules` テーブルをチェックして自動投稿を実行します

---

## 技術スタック

| 区分 | 技術 |
|---|---|
| Discord Bot | discord.py 2.5.2 |
| API フレームワーク | FastAPI 0.111.1 + uvicorn |
| 認証 | JWT（`python-jose`）+ bcrypt |
| DB | MySQL + mysql-connector-python 9.4.0 |
| Dashboard | HTML / CSS / JavaScript（フレームワークなし） |
| テスト | pytest + httpx |
