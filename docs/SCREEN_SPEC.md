# OdaiBot Dashboard 画面仕様書

## 1. 概要

この仕様書は、Discord Bot と連動する Dashboard の画面構成と遷移を定義します。
現行の実装では、Dashboard への初回アクセスは Discord Bot のスラッシュコマンド `/odai_dashboard` による招待リンク発行を起点にしています。

対象ユーザー:
- Discord サーバー管理者
- Dashboard の既存ユーザー / 招待ユーザー

権限:
- `admin` : ユーザー管理や設定変更が可能
- `user` : 通常の運用機能のみ利用可能

認証方式:
- `/odai_dashboard` で発行された `invite_token` を使う初回登録
- その後、`username` / `password` によるログイン
- API 呼び出しは `Authorization: Bearer <access_token>` で行う

---

## 2. 主要画面一覧

1. 招待登録ページ
2. ログインページ
3. ダッシュボードトップ
4. ユーザー管理
5. タグ管理
6. お題管理
7. スケジュール管理
8. 設定 / サーバー情報

---

## 3. 画面詳細

### 3.1 招待登録ページ

目的:
- Discord Bot 側で生成した招待リンクから Dashboard に来たユーザーが初回登録を完了する

URL:
- `#/register?guild_id={guild_id}&invite={invite_token}`

表示項目:
- `招待ユーザー名` (読み取り専用、Bot 生成値)
- `ロール` (読み取り専用、admin/user)
- `パスワード`
- `パスワード（確認）`
- `登録` ボタン

API:
- `POST /api/guilds/{guild_id}/auth/register`
- リクエスト body: `{ invite_token, password }`

成功時:
- ログイン状態に遷移
- 取得した `access_token` を保存して以降の API 呼び出しに利用

失敗パターン:
- 招待トークン無効／期限切れ
- すでに同名ユーザーが存在
- パスワード不一致

---

### 3.2 ログインページ

目的:
- 既存アカウントで Dashboard にログインする

表示項目:
- `ユーザー名`
- `パスワード`
- `ログイン` ボタン
- `初回登録リンク` への案内文

API:
- `POST /api/guilds/{guild_id}/auth/login`
- リクエスト body: `{ username, password }`

成功時:
- `access_token` を保存し、メイン Dashboard に遷移

失敗パターン:
- ユーザー名またはパスワード不正

---

### 3.3 ダッシュボードトップ

目的:
- Dashboard の操作起点。各機能にアクセスする

表示項目:
- サーバー情報表示
  - `Guild ID`
  - `ログインユーザー名`
  - `ロール`
- メインメニュー
  - ユーザー管理
  - タグ管理
  - お題管理
  - スケジュール管理
  - 設定
- 最近の動作ログ／投稿履歴の簡易表示 (任意)

アクセス制御:
- `admin` と `user` で表示項目を制御
- `user` はユーザー管理画面へのリンクを表示しない

---

### 3.4 ユーザー管理画面

目的:
- Dashboard 用ユーザーを管理する

アクセス権:
- `admin` のみ

表示項目:
- ユーザー一覧テーブル
  - `ID`
  - `ユーザー名`
  - `ロール`
  - `作成日時`
  - `更新日時`
  - 操作: 編集 / 削除
- `ユーザー追加` ボタン

新規作成フォーム:
- `ユーザー名`
- `パスワード`
- `ロール` (admin/user)
- `作成` ボタン

API:
- 一覧取得: `GET /api/guilds/{guild_id}/auth/users`
- 作成: `POST /api/guilds/{guild_id}/auth/users`
- 更新: `PUT /api/guilds/{guild_id}/auth/users/{user_id}`
- 削除: `DELETE /api/guilds/{guild_id}/auth/users/{user_id}`

更新項目:
- パスワード変更
- ロール変更

---

### 3.5 タグ管理画面

目的:
- お題生成・絞り込みに使うタグを管理する

表示項目:
- タグ一覧
  - `名前`
  - `説明`
  - 操作: 編集 / 削除
- `タグ追加` ボタン

タグ追加 / 編集フォーム:
- `タグ名`
- `説明`
- `保存` ボタン

想定 API:
- タグ一覧取得
- タグ作成
- タグ編集
- タグ削除

---

### 3.6 お題管理画面

目的:
- Discord 投稿用のお題を管理する

表示項目:
- お題一覧
  - `ID`
  - `テキスト`
  - `タグ`
  - `使用状況`
  - `作成日時`
  - `更新日時`
  - 操作: 編集 / 削除
- `お題追加` ボタン

お題追加 / 編集フォーム:
- `お題テキスト`
- `タグ選択`
- `保存` ボタン

想定 API:
- お題一覧取得
- お題作成
- お題編集
- お題削除

---

### 3.7 スケジュール管理画面

目的:
- 自動投稿スケジュールを設定・管理する

表示項目:
- スケジュール一覧
  - `ID`
  - `送信先チャンネル`
  - `時刻`
  - `有効/無効`
  - `タグモード`
  - `タグリスト`
  - 操作: 編集 / 削除 / 有効化切替
- `スケジュール追加` ボタン

スケジュール追加 / 編集フォーム:
- `送信先チャンネル` (チャンネル ID もしくは選択)
- `時刻`
- `有効` フラグ
- `タグモード` (`all` / `include` / `exclude` など)
- `タグリスト`
- `保存` ボタン

想定 API:
- スケジュール一覧取得
- スケジュール作成
- スケジュール編集
- スケジュール削除

---

### 3.8 設定 / サーバー情報画面

目的:
- Guild 固有設定や運用情報を確認する

表示項目候補:
- `Guild ID`
- `Bot 設定` / `通知チャンネル`
- `Dashboard 基本設定`
- `招待リンク発行` 操作（任意）
- `サーバー情報` 表示

想定 API:
- `guild_settings` の取得 / 更新

---

## 4. 招待フロー詳細

### 4.1 `/odai_dashboard` コマンド

- Discord Bot 上で `admin` 権限者が実行
- 引数:
  - `username`
  - `role` (`admin` / `user`)
- Bot が `user_invites` に招待レコードを作成
- 期限: `INVITE_EXPIRE_HOURS` (デフォルト 1 時間)
- Dashboard への招待 URL を生成し、管理者に Ephemeral で送信

生成 URL 例:
- `http://localhost:3000#/register?guild_id={guild_id}&invite={invite_token}`

### 4.2 登録後の流れ

1. 招待リンクを開く
2. 招待登録ページでパスワードを入力
3. `POST /api/guilds/{guild_id}/auth/register` を実行
4. `users` テーブルにアカウントを追加
5. 招待トークンは `used` になり再利用不可
6. ログイン状態で Dashboard に遷移

---

## 5. API 認証と権限

### 5.1 認証方式

- `POST /api/guilds/{guild_id}/auth/login` でログイン
- `access_token` を `Authorization: Bearer <token>` で送信
- `access_token` は `users.api_token` に保存される

### 5.2 管理者チェック

- 初回 `POST /users` は管理ユーザーが存在しない場合でも実行可能
- 既存ユーザがいる場合は `admin` のみユーザー追加可能
- `GET /users`, `PUT /users/{user_id}`, `DELETE /users/{user_id}` は `admin` 制限

---

## 6. 画面仕様の注意点

- `/odai_dashboard` は HTTP エンドポイントではなく Discord Bot のスラッシュコマンド
- 画面側は `guild_id` を必ず保持し、API 呼び出し時にパラメータとして渡す
- 招待 URL の有効期限を考慮し、期限切れ時のエラーメッセージを明示する
- 画面側では `admin` と `user` の権限差分を明確にする
- すべての API 呼び出しで `guild_id` をキーにサーバー情報を分離する
