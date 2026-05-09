# お題Bot v2.0 開発計画

## 現状 (v1.3)

- ダッシュボード、お題管理、タグ管理、スケジュール管理、設定
- ユーザー管理（BAN・ロック・招待・プロフィール）
- メモ機能、更新日時、メモ検索、フィルター・ソート
- 招待管理ページ、テスト投稿プレビュー
- パスワードリセット・管理者 PW 変更
- APIレート制限（ログイン・パスワードリセット）
- お題画像のローカルファイル管理化
- DBバックアップ（scripts/backup.sh + cron）

## ターゲット

**雑談系 Discord サーバー**（過疎回避・会話活性化目的）

---

## Phase 1 — インフラ・基盤整備 ✅ 完了（v1.3）

- [x] DBバックアップ（mysqldump + 画像ディレクトリ、cron 自動実行）
- [x] お題ファイルのローカル管理化（LONGBLOB → ローカルファイル）
- [x] APIレート制限（slowapi 非採用、Depends カスタム実装）

---

## Phase 2 — ビジネスモデル基盤

### プラン定義

| プラン | 月額 | デフォルトお題 | 独自お題 | 容量オプション | Dashboard | Discord 操作 |
|---|---|---|---|---|---|---|
| **Free** | ¥0 | 50枚（自動割当） | ❌ | ❌ | ❌ | ❌ |
| **Light** | ¥600 | 全件（ON/OFF 可） | 100件〜最大1000件 | +¥400 / 100件追加 | ❌ | ✅ |
| **Pro** | ¥960 | 全件（ON/OFF 可） | 500件〜（上限 TBD） | +¥100 / 100件追加 | ✅ | ✅ |
| **Enterprise** | ¥50,000 初期 + ¥100,000/月保守 | 全件 | 無制限 | — | ✅ | ✅ |

**Free プランの位置づけ**

- Bot をサーバーへ招待できる試用枠
- デフォルトお題50枚が自動割当されるが、スケジュール登録・お題操作は一切不可
- Light 以上に課金して初めて機能が使える

**容量オプション**

- Light 基本枠: 100件、Pro 基本枠: 500件（いずれも月額に含む）
- Light 拡張: +¥400 で 100件追加（¥600 + ¥400 = ¥1,000〜 → Pro より高くなる自然なアップセル設計）
- Pro 拡張: +¥100 で 100件追加
- 上限: Light は最大1000件。Pro の上限はマーケティング調査後に決定
- 拡張枠は Stripe の都度払い（`mode: payment`）として管理
- `guild_plans.custom_odai_capacity = NULL` は無制限（オーナーサーバー等に使用）

**デフォルトお題 ON/OFF**

- Light / Pro は `guild_settings.use_default_odai`（TINYINT、デフォルト 1）でトグル可能
- OFF にしても容量は変わらない（シンプル設計）

---

### Stripe 連携フロー

```
[Discord サーバー管理者]
    │
    │ /subscribe plan:light  コマンド実行
    ▼
[OdaiBot]
    │ POST /api/stripe/checkout（X-Bot-Secret ヘッダー付き）
    │   body: { guild_id, plan, success_url, cancel_url }
    │
    │ Checkout URL を DM で送付（DM 不可なら ephemeral で直接表示）
    ▼
[管理者が Stripe で決済]
    │
    │ Webhook: checkout.session.completed
    ▼
[OdaiBotAPI POST /api/stripe/webhook]
    ├─ guild_plans レコード作成 / 更新（custom_odai_capacity = plan.custom_odai_base）
    ├─ type=subscription: プランを反映（Discord 操作 / Dashboard を解放）
    ├─ type=expand: custom_odai_capacity += units × 100
    └─ Free の場合: default_odai からランダム50枚を guild_default_odai に割り当て

[プラン変更・解約]
    Webhook: customer.subscription.updated / deleted
    → guild_plans.status / current_period_end を更新
    → ダウングレード時は超過分の機能を制限（お題は残す、操作のみ制限）
```

---

### DB スキーマ追加

#### `plans` — プランマスタ（initialize_database で初期データ INSERT）

| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| name | VARCHAR(32) | `free` / `light` / `pro` / `enterprise` |
| price | INT | 月額（円） |
| default_odai_limit | INT NULL | 割当デフォルトお題数（NULL = 全件） |
| custom_odai_base | INT NULL | 独自お題基本枠（NULL = 無制限、0 = 不可） |
| custom_odai_max | INT NULL | 独自お題上限（NULL = 無制限） |
| can_expand_capacity | TINYINT(1) | 容量オプション購入可否 |
| has_dashboard | TINYINT(1) | Dashboard アクセス可否 |
| has_discord_op | TINYINT(1) | Discord 操作可否 |
| stripe_price_id | VARCHAR(128) NULL | Stripe の Price ID（Light / Pro のみ設定） |

#### `guild_plans` — guild とプランの紐付け

| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| guild_id | BIGINT UNIQUE | Discord サーバー ID |
| plan_id | BIGINT FK | `plans.id` |
| custom_odai_capacity | INT NULL | 現在の独自お題上限（NULL = 無制限） |
| stripe_customer_id | VARCHAR(128) NULL | |
| stripe_subscription_id | VARCHAR(128) NULL | |
| status | VARCHAR(32) | `active` / `canceled` / `past_due` |
| current_period_end | DATETIME NULL | 次回更新日 |
| created_at / updated_at | DATETIME | |

#### `default_odai` — デフォルトお題マスタ（運営管理のグローバルプール）

| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| filename | VARCHAR(255) UNIQUE | |
| storage_path | VARCHAR(1024) | `DEFAULT_ODAI_IMAGE_DIR/filename` |
| is_active | TINYINT(1) | 0 にすると削除せず一時無効化できる |
| created_at | DATETIME | |

#### `guild_default_odai` — guild に割り当てられたデフォルトお題

| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| guild_id | BIGINT | |
| default_odai_id | BIGINT FK | `default_odai.id` ON DELETE CASCADE |
| assigned_at | DATETIME | |

> **デフォルトお題の運用方針**
> `odai`（guild ごとの独自お題）とは完全に分離した `default_odai` テーブルで管理する。
> `setup/seed_default_odai.py` で画像ディレクトリから一括登録。
> Free プラン加入時に Webhook が `default_odai WHERE is_active=1` からランダム50件を `guild_default_odai` に割り当て。
> 投稿時は `guild_settings.use_default_odai = 1` のとき独自お題に混ぜて抽選する。

#### `guild_settings` への追加カラム

| カラム | 型 | 説明 |
|---|---|---|
| use_default_odai | TINYINT(1) | デフォルトお題をスケジュール投稿に含めるか（デフォルト 1） |

---

### API エンドポイント追加

| メソッド | パス | 認証 | 説明 |
|---|---|---|---|
| POST | `/api/stripe/webhook` | Stripe 署名検証 | Webhook 受信・プラン反映 |
| POST | `/api/stripe/checkout` | X-Bot-Secret | Checkout セッション生成 |
| POST | `/api/stripe/expand` | X-Bot-Secret | 容量拡張セッション生成 |
| GET | `/api/guilds/{guild_id}/plan` | なし | プラン・容量情報取得 |

**プランゲート**

| チェック箇所 | 条件 | 挙動 |
|---|---|---|
| `POST /login` | `has_dashboard = 0` | 403 |
| `POST /odai`（1件） | `custom_odai_capacity = 0` または超過 | 403 |
| `POST /odai/import`（複数） | 追加予定数が超過 | 403 |

---

### Discord スラッシュコマンド追加

#### 全プラン

| コマンド | 説明 |
|---|---|
| `/subscribe plan:light\|pro` | Stripe Checkout URL を DM で送付 |
| `/plan` | 現在のプラン・独自お題残枠・次回更新日を表示 |
| `/expand units:N` | 容量拡張（+100件単位）の URL を DM で送付 |

#### Light 以上

| コマンド | 説明 |
|---|---|
| `/odai_add file: tags:` | 画像添付でお題登録（容量チェック付き） |
| `/odai_list page:` | お題一覧（15件/ページ、テキスト形式） |
| `/odai_delete filename:` | ファイル名でお題削除 |
| `/schedule_add time: channel:` | スケジュール追加 |
| `/schedule_list` | スケジュール一覧 |

**Bot プランゲート**

| チェック箇所 | 条件 | 挙動 |
|---|---|---|
| `/odai`・全 Light 以上コマンド | `has_discord_op = 0` | ephemeral エラーメッセージ |
| スケジューラーループ | `has_discord_op = 0` | guild をスキップ |

---

### 運営ツール

| スクリプト | 説明 |
|---|---|
| `setup/seed_owner_guilds.py` | オーナーサーバーを Pro・無制限・無課金で登録 |
| `setup/seed_default_odai.py` | 画像ディレクトリから `default_odai` テーブルに一括登録 |
| `setup/seed_default_from_odai.py` | 既存 `odai` テーブルの1サーバー分を `default_odai` に登録 |
| `setup/set_stripe_price_ids.py` | Stripe Price ID を `plans` テーブルに設定 |

---

### 未実装・残タスク（Phase 2）

- [x] Bot 投稿ロジックへのデフォルトお題組み込み — `use_default_odai = 1` のとき `guild_default_odai` からも投稿対象に含める
- [ ] デフォルト画像登録 — `seed_default_from_odai.py` を本番サーバーで実行
- [ ] Stripe 商品作成 → `set_stripe_price_ids.py` で Price ID を設定
- [ ] Stripe Webhook エンドポイント登録（`https://ドメイン/api/stripe/webhook`）、受信イベント: `checkout.session.completed` / `customer.subscription.updated` / `customer.subscription.deleted`、発行された `STRIPE_WEBHOOK_SECRET` を `.env` に設定
- [ ] Dashboard UI — プラン情報・容量の表示ページ（フロントエンド）

---

## Phase 3 — コンテンツ拡張

#### テキスト形式のお題

- 画像ではなく文章でお題を投稿する形式
- 雑談系コミュニティの会話トピックとして活用
- 例：「今日ハマっていることは？」「好きな食べ物ランキングは？」
- 画像お題より雑談系への親和性が高い

#### テキストお題のデフォルトセット

- 会話トピック100本パックなどとして提供
- デフォルトお題販売の主力コンテンツ候補

---

## Phase 4 — 運用・分析

#### 反応数の記録・可視化

- Discord の投稿に対するリアクション数・返信数を記録
- ダッシュボードで「お題ごとの反応数」「週ごとの活性度」などを表示
- 購入者が「Bot 導入前後で活性化した」と実感できる根拠になる

#### ログ集積・管理者向け解析ダッシュボード

- 販売者（運営）側が複数サーバーの稼働状況を一覧で確認できる
- エラー・失敗投稿・異常な操作のログ集積
- 課金サーバーの利用状況把握

#### 投稿失敗通知

- スケジュール投稿が失敗した場合に管理者へ通知
- Discord DM でアラート

---

## Phase 5 — UX 改善

#### Discord OAuth 対応

- Discord アカウントで直接 Dashboard にログインできる仕組み
- 購入者にとって ID/PW 登録が不要になる
- オンボーディングのハードルを下げる

---

## 見送り項目

| 項目 | 理由 |
|---|---|
| 動画形式のお題 | Discord のファイルサイズ制限（無料 8MB）により実用性が低い |
| 課金システムの内製化 | Stripe に委任 |
| デフォルトOFF時の容量ボーナス | 設計が複雑になるため却下。シンプルにトグルのみ提供 |

---

## 優先順位

```
Phase 2（ビジネス基盤）
    ├─ ✅ DB スキーマ追加（plans / guild_plans / default_odai / guild_default_odai）
    ├─ ✅ Stripe Webhook 連携（checkout / subscription.updated / deleted）
    ├─ ✅ プラン制限ゲート（API ログイン・お題容量 / Bot コマンド・スケジューラー）
    ├─ ✅ Discord コマンド追加（subscribe / plan / expand / odai_add / odai_list 等）
    ├─ ✅ オーナーサーバーシード（seed_owner_guilds.py）
    ├─ [ ] デフォルト画像登録（seed_default_from_odai.py を本番で実行）
    ├─ [ ] Stripe 商品作成 + set_stripe_price_ids.py で Price ID 設定
    └─ ✅ Bot 投稿ロジックへのデフォルトお題組み込み
        │
        ▼
Phase 3（コンテンツ）/ Phase 4（分析）  ← 並行可
        │
        ▼
Phase 5（UX）
```
