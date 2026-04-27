# OdaiBotAPI テスト実行ガイド

## 概要

`pytest` を使用したユニットテストです。MySQL・Discord への接続は不要で、すべての外部依存をモックして実行します。

---

## ファイル構成

```
OdaiBotAPI/
  tests/
    conftest.py        # モックセットアップ・共通フィクスチャ
    test_deps.py       # hash_password / verify_password / normalize_tags
    test_auth.py       # 認証エンドポイント（login / register / invite / users CRUD）
    test_tags.py       # タグ CRUD
    test_odai.py       # お題 CRUD・アップロード
    test_schedules.py  # スケジュール CRUD・バリデーション
    test_settings.py   # サーバー設定 GET/PUT
    test_summary.py    # ダッシュボードサマリー
  APITest.md           # このファイル
pytest.ini             # pytest 設定（プロジェクトルート）
```

---

## 前提条件

- Python 3.10 以上
- 仮想環境がセットアップ済み（プロジェクトルートの `.venv`）

---

## セットアップ

### 1. 仮想環境を有効化

```bash
# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

### 2. テスト用パッケージをインストール

```bash
pip install -r OdaiBotAPI/requirements-test.txt
```

または個別にインストール：

```bash
pip install pytest httpx
```

---

## テスト実行

**プロジェクトルート**（`pytest.ini` があるディレクトリ）から実行してください。

```
discode_OdaiBot/   ← ここから実行
  OdaiBotAPI/
  OdaiBotDB/
  OdaiBot/
  pytest.ini
```

### 全テスト実行

```bash
pytest
```

### 詳細表示

```bash
pytest -v
```

### 特定ファイルのみ実行

```bash
pytest OdaiBotAPI/tests/test_auth.py
pytest OdaiBotAPI/tests/test_odai.py
```

### 特定クラス・メソッドのみ実行

```bash
# クラス単位
pytest OdaiBotAPI/tests/test_auth.py::TestLogin

# メソッド単位
pytest OdaiBotAPI/tests/test_auth.py::TestLogin::test_success
```

### 失敗したテストのみ再実行

```bash
pytest --lf
```

### エラー詳細を表示

```bash
pytest -v --tb=long
```

---

## テスト対象一覧

| ファイル | テスト数 | 対象エンドポイント |
|---|---|---|
| `test_deps.py` | 11 | `hash_password` / `verify_password` / `normalize_tags` |
| `test_auth.py` | 19 | `POST /auth/login` `POST /auth/register` `POST /auth/invite` `GET /auth/users` `POST /auth/users` `PUT /auth/users/{id}` `DELETE /auth/users/{id}` |
| `test_tags.py` | 9 | `GET /tags` `POST /tags` `PUT /tags/{id}` `DELETE /tags/{id}` |
| `test_odai.py` | 9 | `GET /odai` `POST /odai` `PUT /odai/{id}` `DELETE /odai/{id}` |
| `test_schedules.py` | 9 | `GET /schedules` `POST /schedules` `PUT /schedules/{id}` `DELETE /schedules/{id}` |
| `test_settings.py` | 5 | `GET /settings` `PUT /settings` |
| `test_summary.py` | 3 | `GET /dashboard-summary` |
| **合計** | **65+** | |

---

## モック構成

テストは DB・Discord 接続なしで実行します。

```
conftest.py
  ├── sys.modules レベルで以下をモック
  │     ├── mysql / mysql.connector
  │     ├── OdaiBotDB.database.MySQLDatabase
  │     └── OdaiBot.Repository.* / Service.*
  ├── deps.db         → MagicMock（query_one / query / execute）
  ├── deps.odai_repo  → MagicMock（get_tags / add_odai）
  └── dependency_overrides で認証をバイパス
        ├── admin_client  → ADMIN ユーザーとして認証済み
        ├── user_client   → 一般ユーザーとして認証済み
        └── anon_client   → 未認証
```

### 各テストでのモック設定例

```python
# 単一の戻り値を設定
deps.db.query_one.return_value = {"id": 1, "name": "タグ名"}

# 複数回の呼び出しに対して順に返す
deps.db.query_one.side_effect = [
    {"id": 1},  # 1回目の呼び出し
    None,       # 2回目の呼び出し
]

# INSERT 後の lastrowid を設定
deps.db.execute.return_value = make_cursor(lastrowid=1)
```

---

## 注意事項

- `pytest` は **プロジェクトルート**（`pytest.ini` があるディレクトリ）から実行する
- `side_effect` をリストで設定した場合、リストが尽きると `StopIteration` が発生する
  - `conftest.py` の `reset_mocks` フィクスチャが各テスト前に自動クリアする
- `create_user` エンドポイントはルート内で `has_guild_users()` を直接呼ぶため、`dependency_overrides` が効かない
  - → ギルドにユーザーがいない（初回作成）シナリオでテストする
