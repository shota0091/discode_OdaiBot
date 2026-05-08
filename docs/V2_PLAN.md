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
| **Light** | ¥500 | 全件 | 100件〜最大1000件 | +¥100 / 100件追加 | ❌ | ✅ |
| **Pro** | ¥700 | 全件 | 500件〜（上限 TBD） | +¥100 / 100件追加 | ✅ | ✅ |
| **Enterprise** | ¥50,000 初期 + ¥100,000/月保守 | 全件 | 無制限 | — | ✅ | ✅ |

**Free プランの位置づけ**

- Bot をサーバーへ招待できる試用枠
- デフォルトお題50枚は割り当てられるが、スケジュール登録・お題操作は一切不可
- Light 以上に課金して初めて機能が使える

**容量オプション（Light / Pro 共通）**

- Light 基本枠: 100件、Pro 基本枠: 500件（いずれも月額に含む）
- 拡張: +¥100 で 100件追加
- 上限: Light は最大1000件。Pro の上限はマーケティング調査後に決定
- 拡張枠は Stripe の従量アイテムとして管理（別途購入）

---

### Stripe 連携フロー

```
[Discord サーバー管理者]
    │
    │ /subscribe plan:light  コマンド実行
    ▼
[OdaiBot]
    │ Stripe Checkout セッション生成
    │   metadata: { guild_id, plan }
    │
    │ Checkout URL を DM で送付
    ▼
[管理者が Stripe で決済]
    │
    │ Webhook: checkout.session.completed
    ▼
[OdaiBotAPI POST /api/stripe/webhook]
    ├─ guild_plans レコード作成 / 更新
    ├─ Free → Light: Discord 操作を解放
    ├─ Light → Pro: Dashboard アクセスを解放
    └─ Free の場合: default_odai からランダム50枚を guild_default_odai に割り当て

[プラン変更・解約]
    Webhook: customer.subscription.updated / deleted
    → guild_plans.status / plan_id を更新
    → ダウングレード時は超過分の機能を制限（お題は残す、操作のみ制限）
```

---

### DB スキーマ追加

#### `plans` — プランマスタ（初期データを INSERT）

| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| name | VARCHAR(32) | `free` / `light` / `pro` / `enterprise` |
| price | INT | 月額（円） |
| default_odai_limit | INT | 割当デフォルトお題数（NULL = 全件） |
| custom_odai_base | INT | 独自お題基本枠（0 = 不可） |
| custom_odai_max | INT NULL | 独自お題最大枠（NULL = 無制限） |
| can_expand_capacity | TINYINT(1) | 容量オプション購入可否 |
| has_dashboard | TINYINT(1) | Dashboard アクセス可否 |
| has_discord_op | TINYINT(1) | Discord 操作可否 |
| stripe_price_id | VARCHAR(128) NULL | Stripe の Price ID |

#### `guild_plans` — guild とプランの紐付け

| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| guild_id | BIGINT UNIQUE | Discord サーバー ID |
| plan_id | BIGINT FK | `plans.id` |
| custom_odai_capacity | INT | 現在の独自お題上限（基本枠 + 拡張枠） |
| stripe_customer_id | VARCHAR(128) NULL | |
| stripe_subscription_id | VARCHAR(128) NULL | |
| status | VARCHAR(32) | `active` / `canceled` / `past_due` |
| current_period_end | DATETIME NULL | 次回更新日 |
| created_at / updated_at | DATETIME | |

#### `default_odai` — デフォルトお題マスタ（運営管理、直接 DB 投入）

| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| filename | VARCHAR(255) | |
| storage_path | VARCHAR(1024) | |
| created_at | DATETIME | |

#### `guild_default_odai` — guild に割り当てられたデフォルトお題

| カラム | 型 | 説明 |
|---|---|---|
| id | BIGINT PK | |
| guild_id | BIGINT | |
| default_odai_id | BIGINT FK | `default_odai.id` |
| assigned_at | DATETIME | |

---

### API エンドポイント追加

| メソッド | パス | 説明 |
|---|---|---|
| POST | `/api/stripe/webhook` | Stripe Webhook 受信（署名検証必須） |
| POST | `/api/stripe/checkout` | Checkout セッション生成（Bot から呼ぶ） |
| POST | `/api/stripe/expand` | 容量オプション購入セッション生成（Light のみ） |
| GET | `/api/guilds/{guild_id}/plan` | 現在のプラン・容量情報取得 |

---

### Discord スラッシュコマンド追加

#### 全プラン

| コマンド | 説明 |
|---|---|
| `/subscribe plan:light\|pro` | Stripe Checkout URL を DM で送付 |
| `/plan` | 現在のプラン・独自お題残枠・次回更新日を表示 |

#### Light 以上

| コマンド | 説明 |
|---|---|
| `/odai_add attachment:file tags:任意` | 画像添付でお題登録 |
| `/odai_list page:1` | お題一覧（テキスト形式、ページネーション） |
| `/odai_delete filename:xxx` | お題削除 |
| `/schedule_add time:09:00 channel:#ch` | スケジュール追加 |
| `/schedule_list` | スケジュール一覧 |
| `/expand` | 容量オプション購入 URL を DM で送付（Light のみ） |

---

### 機能制限の実装方針

- 各 Discord コマンド・API エンドポイントで `guild_plans` + `plans` をチェック
- `has_discord_op = 0` → Discord 操作コマンドを全て弾く
- `has_dashboard = 0` → ログイン時に 403
- 独自お題登録時: 現在の登録件数 ≥ `custom_odai_capacity` → 上限エラー
- ダウングレード時: 超過分のお題は削除せず、新規登録のみ制限

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

---

## 優先順位

```
Phase 2（ビジネス基盤）
    ├─ DB スキーマ追加（plans / guild_plans / default_odai）
    ├─ Stripe Webhook 連携
    ├─ プラン制限ゲート（API・Bot コマンド）
    └─ Discord コマンド追加（Light 向け）
        │
        ▼
Phase 3（コンテンツ）/ Phase 4（分析）  ← 並行可
        │
        ▼
Phase 5（UX）
```

Phase 2 のプラン管理は Phase 3 以降の機能制限の前提になるため、最優先で実装する。
