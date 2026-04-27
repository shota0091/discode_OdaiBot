# お題Bot Dashboard 仕様書

## 1. 概要

OdaiBotdashboard は、Discord お題Bot の管理 Web アプリケーションです。Vanilla HTML / CSS / JavaScript の SPA（Single Page Application）として実装し、外部フレームワークへの依存はありません。

| 項目 | 内容 |
|---|---|
| 実装 | Vanilla HTML / CSS / JavaScript（SPA） |
| ルーティング | ハッシュベースルーティング（`#/login`、`#/dashboard` など） |
| 認証 | Bearer トークン（`localStorage` に保存） |
| デザイン | Discord ライクなダークテーマ、スマートフォン対応 |
| エントリポイント | `OdaiBotdashboard/index.html` |

---

## 2. ファイル構成

```
OdaiBotdashboard/
  index.html                      # SPA エントリポイント、全 JS を読み込む
  css/
    style.css                     # 全画面共通スタイル（.guild-switcher クラス含む）
  js/
    config.js                     # API_BASE URL 設定
    api.js                        # API クライアント（fetch ラッパー）
    app.js                        # ハッシュルーター・ユーティリティ関数
    components/
      layout.js                   # サイドバー・ヘッダー・ハンバーガーメニュー・guild 切替
      modal.js                    # モーダルダイアログ
      toast.js                    # トースト通知
    pages/
      login.js                    # ログインページ（guild_id 不要）
      register.js                 # 招待登録ページ
      dashboard.js                # ダッシュボードトップ
      odai.js                     # お題管理ページ
      tags.js                     # タグ管理ページ
      users.js                    # ユーザー管理ページ
      schedules.js                # スケジュール管理ページ
      settings.js                 # 設定ページ
```

---

## 3. ルーティング

`app.js` のハッシュルーターが `hashchange` イベントを監視し、対応するページオブジェクトの `render()` → `init()` を呼び出します。

| ハッシュ URL | ページ | 認証必要 |
|---|---|---|
| `#/login` | ログインページ | 不要 |
| `#/register` | 招待登録ページ | 不要 |
| `#/dashboard` | ダッシュボードトップ | ○ |
| `#/dashboard/odai` | お題管理 | ○ |
| `#/dashboard/tags` | タグ管理 | ○ |
| `#/dashboard/users` | ユーザー管理 | ○（admin のみ） |
| `#/dashboard/schedules` | スケジュール管理 | ○ |
| `#/dashboard/settings` | 設定 | ○ |

未認証でダッシュボード系ページにアクセスした場合は `#/login` にリダイレクトします。

---

## 4. 画面仕様

### 4.1 ログインページ（`#/login`）

#### 構成要素

- ユーザー名入力フィールド
- パスワード入力フィールド
- ログインボタン
- 招待登録への案内リンク
- エラーメッセージ表示領域

> **注**: Guild ID 入力は不要です。ユーザー名とパスワードだけでログインでき、同名ユーザーが複数 guild に存在する場合は全 guild が返されます。

#### 使用 API

- `POST /api/auth/login`（グローバルログイン）

#### 動作

1. ログイン成功時: レスポンスの `guilds` 配列を `localStorage.guilds` に保存
2. 最初の guild を `guild_id` / `guild_name` / `role` として `localStorage` に設定
3. `access_token` を `localStorage` に保存
4. `#/dashboard` へ遷移

---

### 4.2 招待登録ページ（`#/register`）

#### URL パラメータ

- `guild_id`: Discord サーバー ID
- `invite`: 招待トークン

#### 構成要素

- Guild ID（URL から取得し読み取り専用表示）
- 招待トークン（隠し項目）
- パスワード入力フィールド（8 文字以上）
- パスワード確認入力フィールド
- 登録ボタン
- エラーメッセージ表示領域

#### 使用 API

- `POST /api/guilds/{guild_id}/auth/register`
- `GET /api/auth/guilds`（登録後に所属 guild 一覧を取得）

#### 動作

1. 登録成功後: `GET /api/auth/guilds` を呼び出して `guilds` 一覧を取得し `localStorage` に保存
2. `access_token` / `guild_id` / `role` を `localStorage` に保存
3. `#/dashboard` へ遷移

---

### 4.3 ダッシュボードトップ（`#/dashboard`）

#### 構成要素

- サマリーカード
  - 登録お題数（全体）
  - 未使用お題数
  - 有効スケジュール数
  - 投稿先チャンネル数
- 直近投稿ステータス（ファイル名・チャンネル・投稿日時）
- 各管理画面へのナビゲーションカード

#### 使用 API

- `GET /api/guilds/{guild_id}/dashboard-summary`

---

### 4.4 お題管理ページ（`#/dashboard/odai`）

#### 構成要素

- フィルタ・検索バー
  - ファイル名テキスト入力（あいまい検索）
  - タグ選択（全タグ / 個別選択）
  - 使用状況（全て / 未使用 / 使用済み）
  - お題追加ボタン（右端）
- 一括操作バー（1件以上選択時に表示）
  - 選択件数テキスト（例: 「3 件選択中」）
  - 一括削除ボタン
  - タグ一括編集ボタン
- お題一覧テーブル
  - チェックボックス（全選択 / 行ごと）/ ファイル名 / タグ（チップ表示）/ 使用状況バッジ / 登録日時 / 操作ボタン
  - **ID カラムは非表示**（内部処理にのみ使用）
  - 操作ボタン: プレビュー（👁）/ 編集 / 削除
- お題追加ボタン → モーダルで登録フォームを表示

#### 一括操作

| 操作 | 動作 |
|---|---|
| 全選択チェックボックス | テーブル全行を一括選択 / 解除 |
| 一括削除 | 確認ダイアログ後、選択した全お題を順次 `DELETE` |
| タグ一括編集 | モーダルでタグを選択し、選択した全お題の `tags` を上書き（既存タグは置換） |

#### プレビュー機能

- 各行の👁ボタンをクリックすると `GET /odai/{id}/image` で画像を取得してモーダル表示
- 画像は `Authorization` ヘッダー付きの fetch で取得し、`Blob URL` に変換して `<img>` に表示
- モーダル内で画像をフレームに収める（`max-width: 100%; max-height: 60vh; object-fit: contain`）
- モーダルを閉じると Blob URL を解放（`URL.revokeObjectURL`）

#### お題登録（モーダル）

- 画像ファイル選択（複数選択可）
  - 許可形式: JPEG / PNG / WebP
  - 1 ファイルあたり最大 8MB（クライアント側で事前バリデーション）
- 選択ファイルのプレビューリスト（ファイル名・サイズ表示）
- タグ選択（複数選択可）
- 動作
  - 1 ファイル選択時: `POST /odai`（単体アップロード）
  - 複数ファイル選択時: `POST /odai/import`（一括アップロード、ファイルごとの成否を表示）

#### 使用 API

- `GET /api/guilds/{guild_id}/odai`（`filename`・`tag`・`used` フィルタ）
- `GET /api/guilds/{guild_id}/odai/{id}/image`（プレビュー）
- `PUT /api/guilds/{guild_id}/odai/{id}`（編集・タグ一括編集）
- `DELETE /api/guilds/{guild_id}/odai/{id}`（削除・一括削除）

---

### 4.5 タグ管理ページ（`#/dashboard/tags`）

タグの CRUD 操作を提供します。

---

### 4.6 ユーザー管理ページ（`#/dashboard/users`）

`admin` ロールのみアクセス可能です。

- ユーザー一覧テーブル（ID / ユーザー名 / ロール / 作成日時 / 編集・削除ボタン）
- 招待リンク発行ボタン（Bot の `/odai_dashboard` コマンドで生成した招待 URL を使用）
- ユーザー直接作成ボタン

---

### 4.7 スケジュール管理ページ（`#/dashboard/schedules`）

#### 構成要素

- スケジュール一覧テーブル
  - ID / チャンネル / 時刻 / 有効・無効バッジ / タグモード / タグリスト / 編集・削除ボタン
  - **チャンネル列**: Bot が同期済みの場合はチャンネル名を表示し、チャンネル ID をグレー小文字で補足。未同期の場合は ID のみ表示
- スケジュール追加ボタン → モーダルで登録フォームを表示

#### スケジュール登録・編集（モーダル）

| フィールド | 説明 |
|---|---|
| チャンネル ID | 投稿先の Discord チャンネル ID（文字列入力、精度損失防止） |
| 投稿時刻 | `HH:MM` 形式 |
| 有効 | ON / OFF 選択 |
| タグモード | `all`（全件）/ `allow`（指定タグのみ）/ `deny`（指定タグを除外） |
| タグリスト | タグ選択（複数可、`all` 時は非表示） |

#### 使用 API

- `GET /api/guilds/{guild_id}/schedules`（`channel_name` 含む）
- `POST /api/guilds/{guild_id}/schedules`
- `PUT /api/guilds/{guild_id}/schedules/{id}`
- `DELETE /api/guilds/{guild_id}/schedules/{id}`

---

### 4.8 設定ページ（`#/dashboard/settings`）

`admin` ロールのみ更新可能です。

#### 構成要素

- Guild ID（読み取り専用）
- Guild 名（読み取り専用、Bot が同期済みの場合のみ表示）
- Bot 有効・無効トグル
- タイムゾーン選択（IANA 形式）
- 保存ボタン

#### 使用 API

- `GET /api/guilds/{guild_id}/settings`
- `PUT /api/guilds/{guild_id}/settings`

---

## 5. 共通コンポーネント

### 5.1 レイアウト（`layout.js`）

- サイドバー
  - **guild 切替ウィジェット**: ユーザーが複数 guild に所属している場合はドロップダウン (`<select>`) を表示。1 guild のみの場合はサーバー名を静的テキストで表示
  - ナビゲーションリンク一覧
- トップバー: ページタイトル・ログインユーザー名・ロールバッジ・ログアウトボタン
- ハンバーガーメニュー（モバイル時に表示）
- オーバーレイ（サイドバー展開時のマスク）

#### guild 切替の動作

1. ドロップダウンで guild を選択
2. `localStorage` の `guild_id` / `guild_name` / `role` を選択 guild の値に更新
3. `Router.navigate(location.hash)` でページを再描画（API リクエストが新しい `guild_id` で実行される）

### 5.2 モーダル（`modal.js`）

- `Modal.show(title, body, options)`: 汎用モーダルを開く
- `Modal.confirm(title, message, onConfirm)`: 確認ダイアログを開く
- `Modal.close()`: モーダルを閉じる
- モバイルではボトムシート形式で表示

### 5.3 トースト通知（`toast.js`）

- `Toast.success(message)`: 成功通知（緑）
- `Toast.error(message)`: エラー通知（赤）
- `Toast.info(message)`: 情報通知（青）
- 3 秒後に自動消去

---

## 6. localStorage 管理

| キー | 内容 |
|---|---|
| `access_token` | API 認証トークン |
| `guild_id` | 現在操作中の Discord サーバー ID（文字列） |
| `guild_name` | 現在操作中のサーバー名 |
| `role` | 現在の guild におけるロール（`admin` / `user`） |
| `guilds` | 所属する全 guild の配列（JSON 文字列）`[{ guild_id, guild_name, role }]` |
| `user` | ログイン中のユーザー情報（`{ username }` JSON 文字列） |

---

## 7. レスポンシブ対応

| ブレークポイント | 変更内容 |
|---|---|
| ≤ 900px（タブレット） | テーブルフォントサイズ縮小・ユーザー名非表示 |
| ≤ 680px（スマートフォン） | サイドバーをオフキャンバス化・ハンバーガーメニュー表示・モーダルをボトムシート（画面下から全幅表示）化 |
| ≤ 400px（小型端末） | フォントサイズ・余白を縮小 |

### モバイルテーブル方針

横スクロールは操作性が悪いため、スマートフォンでは不要なカラムを非表示にしてテーブルをビューポート幅に収めます。

| ページ | 非表示カラム（≤ 680px） |
|---|---|
| お題管理 | 登録日時 |
| スケジュール管理 | ID・作成日時 |
| タグ管理 | 説明・作成日時 |
| ユーザー管理 | 作成日時・更新日時 |

### モバイルモーダル方針

- 幅: `max-width: 100%`（画面いっぱいに広げる）
- 位置: 画面下から表示（ボトムシート）
- 角丸: 上辺のみ `border-radius`
- 高さ: 最大 `90vh`（内部スクロール対応）

---

## 8. 認証フロー

1. `localStorage` の `access_token` を確認
2. 未保存の場合は `#/login` にリダイレクト
3. API リクエスト時に `Authorization: Bearer {access_token}` ヘッダーを付与
4. ログイン成功後は `guilds` 一覧を `localStorage.guilds` に保存
5. guild 切替時は `localStorage` の `guild_id` / `role` を更新しページを再描画

---

## 9. 表示文言・用語定義

| 用語 | 説明 |
|---|---|
| お題 | Discord に投稿する質問・トピック画像 |
| タグ | お題を分類するラベル |
| スケジュール | お題の自動投稿設定 |
| Guild | Discord サーバー |
| admin | 全操作権限を持つロール |
| user | 閲覧・一部操作が可能なロール |

---

## 10. 関連ドキュメント

| ドキュメント | パス |
|---|---|
| API 仕様 | [`OdaiBotAPI/odoai_bot_api_spec.md`](../OdaiBotAPI/odoai_bot_api_spec.md) |
| DB スキーマ | [`OdaiBotDB/DB_SCHEMA.md`](../OdaiBotDB/DB_SCHEMA.md) |
| プロジェクト全体 | [`README.md`](../README.md) |
