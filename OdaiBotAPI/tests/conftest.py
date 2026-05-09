"""
テスト共通設定。

OdaiBotDB / OdaiBot の外部依存（MySQL、discord.py）をすべて sys.modules レベルで
モックしてから OdaiBotAPI をインポートすることで、DB接続なしでテストを実行できる。
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock

# ─────────────────────────────────────────────────────────────
# 外部モジュールをすべて Mock で差し替える（import より先に実行）
# ─────────────────────────────────────────────────────────────
_mock_db_instance = MagicMock(name="db")
_mock_db_class = MagicMock(name="MySQLDatabase", return_value=_mock_db_instance)

_db_module = MagicMock()
_db_module.MySQLDatabase = _mock_db_class

sys.modules.setdefault("mysql", MagicMock())
sys.modules["mysql.connector"] = MagicMock()
sys.modules["OdaiBotDB"] = MagicMock()
sys.modules["OdaiBotDB.database"] = _db_module

for _mod in [
    "OdaiBot",
    "OdaiBot.Repository",
    "OdaiBot.Repository.OdaiRepository",
    "OdaiBot.Repository.ScheduleRepository",
    "OdaiBot.Service",
    "OdaiBot.Service.NotifyServiceImpl",
]:
    sys.modules.setdefault(_mod, MagicMock())

# ─────────────────────────────────────────────────────────────
# ここから FastAPI アプリをインポート
# ─────────────────────────────────────────────────────────────
import pytest
from fastapi.testclient import TestClient

from OdaiBotAPI.api import app
from OdaiBotAPI import deps
from OdaiBotAPI import limiter

# ─────────────────────────────────────────────────────────────
# テスト定数
# ─────────────────────────────────────────────────────────────
GUILD_ID = 111222333444555666
BASE = f"/api/guilds/{GUILD_ID}"

ADMIN = {"id": 1, "guild_id": GUILD_ID, "username": "admin_user", "role": "admin"}
USER  = {"id": 2, "guild_id": GUILD_ID, "username": "test_user",  "role": "user"}


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_mocks():
    """各テスト前後にモックを完全リセットし依存オーバーライドをクリアする。

    reset_mock() はデフォルトで side_effect / return_value をクリアしないため、
    子モックごとに明示的にリセットする。
    """
    limiter._buckets.clear()
    for child in (
        deps.db.query_one, deps.db.query, deps.db.execute,
        deps.odai_repo.get_tags, deps.odai_repo.add_odai, deps.odai_repo._ensure_tag,
    ):
        child.reset_mock(return_value=True, side_effect=True)
    app.dependency_overrides.clear()
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def admin_client():
    """管理者として認証済みの TestClient。プランゲートもバイパス。"""
    app.dependency_overrides[deps.get_current_user]       = lambda guild_id=GUILD_ID: ADMIN
    app.dependency_overrides[deps.require_admin]          = lambda guild_id=GUILD_ID: ADMIN
    app.dependency_overrides[deps.require_pro_plan]       = lambda guild_id=GUILD_ID: None
    app.dependency_overrides[deps.require_dashboard_plan] = lambda guild_id=GUILD_ID: None
    return TestClient(app)


@pytest.fixture
def user_client():
    """一般ユーザーとして認証済みの TestClient。プランゲートもバイパス。"""
    app.dependency_overrides[deps.get_current_user]       = lambda guild_id=GUILD_ID: USER
    app.dependency_overrides[deps.require_pro_plan]       = lambda guild_id=GUILD_ID: None
    app.dependency_overrides[deps.require_dashboard_plan] = lambda guild_id=GUILD_ID: None
    return TestClient(app)


@pytest.fixture
def anon_client():
    """未認証の TestClient。"""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def gate_client():
    """プランゲートを実行する認証済みクライアント（require_pro_plan / require_dashboard_plan はバイパスしない）。"""
    app.dependency_overrides[deps.get_current_user] = lambda guild_id=GUILD_ID: ADMIN
    app.dependency_overrides[deps.require_admin]    = lambda guild_id=GUILD_ID: ADMIN
    return TestClient(app, raise_server_exceptions=False)


def make_cursor(lastrowid: int = 1) -> MagicMock:
    """db.execute の戻り値として使うカーソルモックを生成する。"""
    cur = MagicMock()
    cur.lastrowid = lastrowid
    return cur
