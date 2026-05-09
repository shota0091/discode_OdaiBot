# OdaiBotAPI ユニットテスト カバレッジ報告書

作成日: 2026-05-09

---

## 1. テスト実行結果（最終）

| 項目 | 件数 |
|------|------|
| テスト総数 | **236** |
| 成功 | **236** |
| 失敗 | **0** |
| 実行時間 | 約 4.6 秒 |

```
====================== 236 passed, 14 warnings in 4.64s ======================
```

---

## 2. テストファイル一覧

### 既存ファイル（Phase 2 改修時に修正・充実化）

| ファイル | テスト数 | 主な対象エンドポイント |
|----------|----------|----------------------|
| test_auth.py | 20 | ログイン、招待登録、ユーザー作成・更新・削除 |
| test_deps.py | 29 | `normalize_tags` / `hash_password` / `verify_password` / プラン判定ロジック |
| test_odai.py | 12 | お題一覧・アップロード・更新・削除 |
| test_plan_gates.py | 17 | `require_pro_plan` / `require_dashboard_plan` 統合テスト |
| test_plan_schedule.py | 12 | Free プランスケジュール管理 CRUD |
| test_schedules.py | 11 | 通常スケジュール CRUD |
| test_settings.py | 8 | Guild 設定 取得・更新 |
| test_stripe.py | 20 | Stripe Webhook・チェックアウト・容量拡張 |
| test_summary.py | 3 | ダッシュボードサマリー |
| test_tags.py | 11 | タグ CRUD |

### 新規作成ファイル（今回追加分 93 件）

| ファイル | テスト数 | 対象エンドポイント |
|----------|----------|------------------|
| test_auth_global.py | 9 | `POST /api/auth/login`（グローバル）、`GET /api/auth/guilds` |
| test_auth_users.py | 39 | パスワードリセット、BAN 管理、招待管理、ロック解除、ユーザープロフィール |
| test_settings_extra.py | 7 | `GET /settings/name`（認証不要）、`GET /settings/channels` |
| test_test_post.py | 5 | `POST /test-post` |
| test_tags_extra.py | 5 | `GET /tags/{tag_id}/detail` |
| test_odai_extra.py | 28 | 履歴・使用状況・画像取得・インポート・更新エッジケース |

---

## 3. 今回追加したテストの詳細

### 3-1. test_auth_global.py（9 件）

| クラス | テストケース |
|--------|-------------|
| TestGlobalLogin | 成功、パスワード誤り→401、ユーザー不在→401、ギルド未所属→403、display_name の返却確認 |
| TestListGuilds | 成功、トークンなし→401、無効トークン→401、複数ギルド返却 |

### 3-2. test_auth_users.py（39 件）

| クラス | テストケース |
|--------|-------------|
| TestResetPassword | 成功、無効トークン→404、ユーザー不在→404、短いパスワード→400 |
| TestGetInviteInfo | 成功、無効トークン→404 |
| TestListBans | 成功、空リスト、未認証→401、非管理者→403 |
| TestRemoveBan | 成功、不在→404、非管理者→403 |
| TestListInvites | 成功、空リスト、非管理者→403 |
| TestRevokeInvite | 成功、不在→404、非管理者→403 |
| TestUnlockUser | 成功、不在→404、非管理者→403 |
| TestBanUser | 成功、自分自身を BAN→400、不在→404、非管理者→403 |
| TestUnbanUser | 成功、不在→404、非管理者→403 |
| TestGetUserProfile | 管理者が任意プロフィール閲覧、自分自身は閲覧可、他者は403、不在→404、お題・タグ一覧の埋め込み |
| TestListUsersNonAdmin | 非管理者は自分のデータのみ取得 |
| TestUpdateUserExtra | 他ユーザー更新→403、現パスワード誤り→401、現パスワード未指定→400、管理者によるロール変更 |

### 3-3. test_settings_extra.py（7 件）

| クラス | テストケース |
|--------|-------------|
| TestGetGuildName | guild_name を返却、未登録時は null、認証不要であること |
| TestGetChannels | チャンネル一覧返却、空リスト、channel_id は文字列型、未認証→401 |

### 3-4. test_test_post.py（5 件）

| クラス | テストケース |
|--------|-------------|
| TestTestPost | 成功（candidate あり）、候補なし→404、tag_mode / tag_list の引き渡し確認、デフォルト tag_mode は "all"、未認証→401 |

### 3-5. test_tags_extra.py（5 件）

| クラス | テストケース |
|--------|-------------|
| TestGetTagDetail | 成功（odai / schedules 埋め込み）、不在→404、お題リスト確認、スケジュールの enabled が bool 型か確認、未認証→401 |

### 3-6. test_odai_extra.py（28 件）

| クラス | テストケース |
|--------|-------------|
| TestGetOdaiHistory | 成功（ページング情報含む）、不在→404、page / per_page パラメータ、per_page は最大 50 にクランプ、未認証→401 |
| TestGetOdaiUsage | 成功、channel_id が文字列型か確認、空の使用履歴、不在→404、未認証→401 |
| TestGetOdaiImage | 不在→404、storage_path なし→404、ファイルが存在しない→404、JPEG / PNG / WebP の Content-Type 確認、未認証→401 |
| TestImportOdai | 単一ファイル成功、重複ファイルは success=false で継続、複数ファイルの部分成功、未認証→401 |
| TestUpdateOdaiEdgeCases | ファイル名重複→409、空ファイル名→400、成功リネーム、メモ更新、ソフトデリート、復元、タグ更新 |

---

## 4. 修正した不具合・技術的対処

### 4-1. レートリミッターの状態がテスト間でリークする問題

**現象:** `POST /auth/reset-password` のテストを全体実行すると 429 Too Many Requests になる。  
**原因:** `limiter.py` の `_buckets` dict がモジュールレベルで保持され、前の認証テストが蓄積したリクエスト数が次のテストに影響する。  
**修正:** `conftest.py` の `reset_mocks` fixture に `limiter._buckets.clear()` を追加し、各テスト前にリセットする。

```python
# conftest.py
from OdaiBotAPI import limiter

@pytest.fixture(autouse=True)
def reset_mocks():
    limiter._buckets.clear()   # ← 追加
    ...
```

### 4-2. `require_pro_plan` の認証チェック順序

**現象:** 未認証アクセスが 401 でなく 403 になる。  
**原因:** ルーターレベルの `require_pro_plan` が `get_current_user` より先に評価され、プランチェック（free → 403）が先行する。  
**修正:** `require_pro_plan` に `get_current_user` を sub-dependency として組み込み、未認証なら必ず 401 を先行させる。

```python
def require_pro_plan(guild_id: int, _: dict = Depends(get_current_user)) -> None:
    plan = get_guild_plan(guild_id)
    if plan.get("plan_name") not in ("pro", "enterprise"):
        raise HTTPException(status_code=403, ...)
```

### 4-3. `stripe.SignatureVerificationError` のモック問題

**現象:** `test_invalid_signature_returns_400` が 500 になる。  
**原因:** `stripe` モジュールを `MagicMock` で差し替えると `except stripe.SignatureVerificationError:` の例外型が `MagicMock` になり、Python が `TypeError` を発生させる。  
**修正:** テスト内でモックに実クラスを再設定する。

```python
mock_stripe.SignatureVerificationError = stripe.SignatureVerificationError
```

### 4-4. `stripe.py` の SQL パラメータ化

**現象:** `"canceled" in call_args[1]` のアサーションが失敗する。  
**原因:** SQL に `'canceled'` を直接埋め込んでいたためパラメータタプルに含まれない。  
**修正:** `%s` プレースホルダーに変更してパラメータとして渡す。

```python
db.execute(
    "UPDATE guild_plans SET status = %s WHERE stripe_subscription_id = %s",
    ("canceled", sub_id),
    commit=True,
)
```

### 4-5. `dashboard-summary` の `last_post` フィールド欠落

**現象:** `summary.py` のレスポンスに `last_post` がなく KeyError になる。  
**修正:** `db.query_one` で最新投稿を取得し `last_post` としてレスポンスに追加。

---

## 5. テスト設計のポイント

### モック戦略

| 対象 | アプローチ |
|------|-----------|
| DB | `deps.db.query_one` / `deps.db.query` / `deps.db.execute` を `MagicMock` で差し替え |
| OdaiRepository | `deps.odai_repo.get_tags` / `add_odai` / `_ensure_tag` をモック |
| NotifyService | `deps.notify_service.select_candidate` をテストごとに設定 |
| ファイルシステム | `unittest.mock.patch("OdaiBotAPI.routers.odai.Path")` で差し替え |
| Stripe SDK | `patch("OdaiBotAPI.routers.stripe.stripe")` + 実例外クラスの再設定 |

### フィクスチャ種別

| fixture | 用途 |
|---------|------|
| `admin_client` | 認証済み管理者。プランゲートもバイパス |
| `user_client` | 認証済み一般ユーザー。プランゲートもバイパス |
| `anon_client` | 未認証。レートリミッター・認証・プランゲートはすべて実行される |
| `gate_client` | 認証済みだがプランゲートはバイパスしない（統合テスト用） |

### DB 呼び出し順序のマッピング例

```
POST /auth/register（招待登録）
  1. db.query_one  → invite チェック
  2. db.query_one  → ban チェック
  3. db.query_one  → ギルド内ユーザー重複チェック
  4. db.query_one  → グローバルユーザー存在チェック
  5. db.query_one  → 登録完了後のユーザー取得（api_token 含む）
```

---

*236 tests, 0 failures — 全テスト正常終了*
