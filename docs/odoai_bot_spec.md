# お題Bot 仕様書

## 1. 概要

OdaiBot は Discord サーバー向けの投稿専念型お題投稿 Bot です。お題画像の登録や投稿設定は Dashboard で管理し、Bot 本体は DB から読み出したお題を Discord チャンネルへ送信することに専念します。

| 項目 | 内容 |
|---|---|
| ライブラリ | discord.py 2.5.2 |
| エントリポイント | `OdaiBot/odai_bot.py` |
| 起動コマンド | `python OdaiBot/odai_bot.py` |
| 環境変数 | `.env`（`DISCORD_BOT_TOKEN` など） |

---

## 2. 主要機能

### 2.1 お題投稿（コマンド）

`/odai` コマンドで即時にお題を Discord チャンネルへ送信します。

- `NotifyServiceImpl` が対象チャンネルの `odai_usage` を参照し、未投稿のお題をランダムで 1 件選択
- 全件投稿済みの場合は当該チャンネルの `odai_usage` をリセットして再選択（ローテーション）
- 選択したお題を `odai_usage` に記録して投稿

> **注**: `odai.used` は Dashboard 上の手動フラグであり、自動投稿の選択には影響しません。

### 2.2 定期通知（スケジューラ）

`schedules` テーブルの設定に基づいて定期投稿を実行します。

- `ScheduleServiceImpl` が 1 分ごとのループで現在時刻と `schedules.time`（`HH:MM`）を照合
- 一致したスケジュールで `NotifyServiceImpl` を呼び出して投稿
- `schedules.tag_mode` / `schedules.tag_list` によって投稿対象お題を絞り込み
- お題選択は `odai_usage` テーブルによるチャンネル単位のローテーション
  - 当該チャンネルで未投稿のお題がなければ自動リセットして最初からローテーション
  - チャンネルごとに独立したリセットであり、他チャンネルには影響しない
- ループ毎に `guild_settings.guild_name` を最新サーバー名で更新

### 2.3 Dashboard 招待発行

`/odai_dashboard` コマンドで Dashboard の招待 URL を Ephemeral（本人のみ表示）で返します。

- **サーバー名・チャンネル情報を同期**: 招待発行前に `guild_settings` へサーバー名を、`channels` テーブルへ全テキストチャンネルを `ON DUPLICATE KEY UPDATE` で書き込みます
- 招待トークンを `user_invites` テーブルに記録
- 生成した URL を `DASHBOARD_BASE_URL` + `#/register?guild_id=...&invite=...` の形式で返す

### 2.4 起動時のメタ情報同期

`on_ready` イベント時に、Bot が参加している全 guild のサーバー名と全テキストチャンネルを `guild_settings` / `channels` テーブルに一括同期します。

---

## 3. コマンド仕様

| コマンド | 説明 | 権限 |
|---|---|---|
| `/ping` | Bot の疎通確認 | なし |
| `/odai` | 今日のお題を送信 | 管理者 |
| `/odai_dashboard` | Dashboard 招待リンクを発行し、サーバー名・チャンネルを同期 | 管理者 |

---

## 4. データモデル

### 4.1 OdaiEntity

| フィールド | 型 | 説明 |
|---|---|---|
| `id` | int | お題 ID |
| `filename` | str | ファイル名 |
| `data` | bytes | 画像バイナリ |
| `used` | bool | 使用済みフラグ |
| `added_at` | datetime | 登録日時 |
| `deleted_at` | datetime \| None | 論理削除日時 |
| `tags` | list[str] | 付与されたタグ名の一覧 |

### 4.2 ScheduleEntity

| フィールド | 型 | 説明 |
|---|---|---|
| `id` | int | スケジュール ID |
| `channel_id` | int | 投稿先 Discord チャンネル ID |
| `time` | str | 投稿時刻（`HH:MM`） |
| `enabled` | bool | 有効フラグ |
| `tag_mode` | str | `all` / `allow` / `deny` |
| `tag_list` | list[str] | フィルタ対象タグ名 |

---

## 5. アーキテクチャ

```
OdaiBot/
  odai_bot.py          # エントリポイント・Discord イベントハンドラ
  Factory/
    OdaiFactory.py     # DB 接続・リポジトリ・サービスの組み立て
  Interface/
    BaseRepositoryInterface.py
    NotifyServiceInterface.py
    ScheduleServiceInterface.py
  Repository/
    MySQLDatabase.py         # OdaiBotDB.database への薄いラッパー
    OdaiRepository.py        # odai テーブルの読み書き
    ScheduleRepository.py    # schedules テーブルの管理
    ChannelTagPermissionRepository.py
    UserRepository.py
    InviteRepository.py
  Service/
    NotifyServiceImpl.py     # お題選択・投稿ロジック
    ScheduleServiceImpl.py   # スケジュール実行・投稿制御
  Template/
    img/               # お題画像（旧ファイルストレージ、DB 移行後は不要）
```

### 5.1 Factory パターン

`OdaiFactory` が MySQL 接続（`MySQLDatabase`）を生成し、各リポジトリ・サービスに注入します。DB 接続はクラス変数 `_db` で共有します。

### 5.2 サービス層

| クラス | 責務 |
|---|---|
| `NotifyServiceImpl` | `odai_usage` を参照してチャンネル単位の未投稿お題を選択し Discord に投稿。全件済みの場合はリセット後再選択 |
| `ScheduleServiceImpl` | スケジュールを読み込み、時刻一致時に `NotifyServiceImpl` を呼び出す |

### 5.3 リポジトリ層

| クラス | テーブル |
|---|---|
| `OdaiRepository` | `odai`, `odai_tags`, `tags`, `odai_usage` |
| `ScheduleRepository` | `schedules` |
| `UserRepository` | `users` |
| `InviteRepository` | `user_invites` |

---

## 6. イベント処理

### 6.1 起動時（on_ready）

1. アプリケーションコマンドをサーバーに同期（`bot.tree.sync()`）
2. 参加済み全 guild のサーバー名を `guild_settings` に、全テキストチャンネルを `channels` テーブルに書き込み（`_sync_guild_meta`）
3. スケジューラループ（`odai_schedule_loop`）を起動

### 6.2 スケジューラループ（1 分ごと）

1. 全 guild をループ
2. `guild_settings.guild_name` を最新サーバー名で更新
3. `ScheduleServiceImpl.run(bot)` を呼び出し、時刻一致スケジュールを実行

### 6.3 /odai_dashboard コマンド

1. `_sync_guild_meta` でサーバー名・チャンネル情報を同期
2. ユーザーが未存在であることを確認
3. 招待トークンを `user_invites` テーブルに記録
4. 招待 URL を Ephemeral メッセージで送信

---

## 7. 前提・制約

- Discord Bot トークンは `.env` の `DISCORD_BOT_TOKEN` から読み込む
- MySQL 接続情報は `.env` から読み込む
- Bot は投稿専念であり、お題登録・設定変更は Dashboard で行う
- スケジュールの時刻判定は `HH:MM` の完全一致で行う（秒は無視）
- 画像は DB の LONGBLOB から取得し、Discord の `discord.File` として送信する
- `.env` の読み込み順: `OdaiBot/.env` → プロジェクトルート `.env`（先勝ち）

---

## 8. 環境変数

| 変数名 | 必須 | 説明 |
|---|---|---|
| `DISCORD_BOT_TOKEN` | ○ | Discord Bot のトークン |
| `MYSQL_HOST` | - | MySQL ホスト（省略時: `127.0.0.1`） |
| `MYSQL_PORT` | - | MySQL ポート（省略時: `3306`） |
| `MYSQL_USER` | - | MySQL ユーザー（省略時: `root`） |
| `MYSQL_PASSWORD` | - | MySQL パスワード（省略時: 空文字） |
| `MYSQL_DATABASE` | - | データベース名（省略時: `odai_bot`） |
| `DASHBOARD_BASE_URL` | - | Dashboard の公開 URL（招待リンク生成用） |
| `INVITE_EXPIRE_HOURS` | - | 招待トークンの有効時間（省略時: `24`） |

---

## 9. 関連ドキュメント

| ドキュメント | パス |
|---|---|
| API 仕様 | [`OdaiBotAPI/odoai_bot_api_spec.md`](../OdaiBotAPI/odoai_bot_api_spec.md) |
| DB スキーマ | [`OdaiBotDB/DB_SCHEMA.md`](../OdaiBotDB/DB_SCHEMA.md) |
| Dashboard 仕様 | [`OdaiBotdashboard/odoai_bot_dashboard_spec.md`](../OdaiBotdashboard/odoai_bot_dashboard_spec.md) |
| プロジェクト全体 | [`README.md`](../README.md) |
