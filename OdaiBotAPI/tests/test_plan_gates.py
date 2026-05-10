"""プランゲートの統合テスト。

gate_client フィクスチャを使い、require_pro_plan / require_dashboard_plan を
実際に実行させて各エンドポイントへのアクセス制御を検証する。
"""
from __future__ import annotations

import pytest

from OdaiBotAPI import deps
from OdaiBotAPI.deps import hash_password

from .conftest import BASE, GUILD_ID, make_cursor

_FREE_PLAN = {
    "plan_name": "free", "has_dashboard": 1, "has_discord_op": 0,
    "can_expand_capacity": 0, "custom_odai_max": 10,
    "custom_odai_capacity": 10, "status": "active",
}
_LIGHT_PLAN = {
    "plan_name": "light", "has_dashboard": 1, "has_discord_op": 1,
    "can_expand_capacity": 1, "custom_odai_max": 1000,
    "custom_odai_capacity": 100, "status": "active",
}
_PRO_PLAN = {
    "plan_name": "pro", "has_dashboard": 1, "has_discord_op": 1,
    "can_expand_capacity": 1, "custom_odai_max": None,
    "custom_odai_capacity": 500, "status": "active",
}


# ─────────────────────────────────────────────────────────────
# require_dashboard_plan — ログインゲート
# ─────────────────────────────────────────────────────────────
class TestDashboardPlanGate:
    _url = f"{BASE}/auth/login"

    def _login_payload(self, password="pass12345"):
        return {"username": "admin_user", "password": password}

    def test_free_plan_login_succeeds(self, anon_client):
        """Free プランも has_dashboard=1 なのでログイン可。"""
        password = "pass12345"
        deps.db.query_one.side_effect = [
            None,           # require_dashboard_plan: guild_plans JOIN → not found
            _FREE_PLAN,     # require_dashboard_plan: plans WHERE free (has_dashboard=1)
            {               # login: user lookup
                "id": 1, "username": "admin_user",
                "display_name": None,
                "password_hash": hash_password(password),
                "login_attempts": 0, "locked_until": None,
                "login_locked": 0, "role": "admin",
            },
            None,           # ban check
        ]
        deps.db.execute.return_value = make_cursor()
        res = anon_client.post(self._url, json=self._login_payload(password))
        assert res.status_code == 200

    def test_light_plan_login_succeeds(self, anon_client):
        password = "pass12345"
        deps.db.query_one.side_effect = [
            _LIGHT_PLAN,    # require_dashboard_plan: guild_plans JOIN → light
            {               # login: user lookup
                "id": 1, "username": "admin_user",
                "display_name": None,
                "password_hash": hash_password(password),
                "login_attempts": 0, "locked_until": None,
                "login_locked": 0, "role": "admin",
            },
            None,           # ban check
        ]
        deps.db.execute.return_value = make_cursor()
        res = anon_client.post(self._url, json=self._login_payload(password))
        assert res.status_code == 200

    def test_pro_plan_login_succeeds(self, anon_client):
        password = "pass12345"
        deps.db.query_one.side_effect = [
            _PRO_PLAN,
            {
                "id": 1, "username": "admin_user",
                "display_name": None,
                "password_hash": hash_password(password),
                "login_attempts": 0, "locked_until": None,
                "login_locked": 0, "role": "admin",
            },
            None,
        ]
        deps.db.execute.return_value = make_cursor()
        res = anon_client.post(self._url, json=self._login_payload(password))
        assert res.status_code == 200


# ─────────────────────────────────────────────────────────────
# require_pro_plan — タグゲート（お題・スケジュールは全プラン解放済み）
# ─────────────────────────────────────────────────────────────
class TestProPlanGate:
    def _mock_free(self):
        deps.db.query_one.return_value = _FREE_PLAN

    def _mock_light(self):
        deps.db.query_one.return_value = _LIGHT_PLAN

    def _mock_pro(self):
        deps.db.query_one.return_value = _PRO_PLAN

    # --- odai（全プラン解放）---
    def test_odai_list_free_succeeds(self, gate_client):
        deps.db.query_one.return_value = {"cnt": 0}
        deps.db.query.return_value = []
        res = gate_client.get(f"{BASE}/odai/")
        assert res.status_code == 200

    def test_odai_list_light_succeeds(self, gate_client):
        deps.db.query_one.return_value = {"cnt": 0}
        deps.db.query.return_value = []
        res = gate_client.get(f"{BASE}/odai/")
        assert res.status_code == 200

    def test_odai_list_pro_succeeds(self, gate_client):
        deps.db.query_one.return_value = {"cnt": 0}
        deps.db.query.return_value = []
        res = gate_client.get(f"{BASE}/odai/")
        assert res.status_code == 200

    # --- tags（Pro以上のみ）---
    def test_tags_list_free_returns_403(self, gate_client):
        self._mock_free()
        res = gate_client.get(f"{BASE}/tags/")
        assert res.status_code == 403

    def test_tags_list_light_returns_403(self, gate_client):
        self._mock_light()
        res = gate_client.get(f"{BASE}/tags/")
        assert res.status_code == 403

    def test_tags_list_pro_passes(self, gate_client):
        deps.db.query_one.return_value = _PRO_PLAN
        deps.db.query.return_value = []
        res = gate_client.get(f"{BASE}/tags/")
        assert res.status_code == 200

    # --- schedules（全プラン解放）---
    def test_schedules_list_free_succeeds(self, gate_client):
        deps.db.query.return_value = []
        res = gate_client.get(f"{BASE}/schedules/")
        assert res.status_code == 200

    def test_schedules_list_light_succeeds(self, gate_client):
        deps.db.query.return_value = []
        res = gate_client.get(f"{BASE}/schedules/")
        assert res.status_code == 200

    def test_schedules_list_pro_succeeds(self, gate_client):
        deps.db.query.return_value = []
        res = gate_client.get(f"{BASE}/schedules/")
        assert res.status_code == 200

    # --- settings PUT ---
    def test_settings_put_free_returns_403(self, gate_client):
        self._mock_free()
        res = gate_client.put(f"{BASE}/settings/", json={"bot_enabled": True})
        assert res.status_code == 403

    def test_settings_put_light_returns_403(self, gate_client):
        self._mock_light()
        res = gate_client.put(f"{BASE}/settings/", json={"bot_enabled": True})
        assert res.status_code == 403

    def test_settings_put_pro_passes(self, gate_client):
        deps.db.query_one.side_effect = [
            _PRO_PLAN,   # require_pro_plan
            {"id": 1},   # existing check
            {            # after update
                "guild_id": GUILD_ID, "bot_enabled": 1,
                "timezone": "Asia/Tokyo", "use_default_odai": 1,
                "updated_at": None,
            },
        ]
        deps.db.execute.return_value = make_cursor()
        res = gate_client.put(f"{BASE}/settings/", json={"bot_enabled": True})
        assert res.status_code == 200

    # --- settings GET (Light+ アクセス可) ---
    def test_settings_get_light_passes(self, gate_client):
        """GET /settings は require_pro_plan なし → Light でも取得可。"""
        deps.db.query_one.return_value = {
            "guild_id": GUILD_ID, "guild_name": "Test",
            "bot_enabled": 1, "timezone": "Asia/Tokyo",
            "use_default_odai": 1, "updated_at": None,
        }
        res = gate_client.get(f"{BASE}/settings/")
        assert res.status_code == 200

    # --- summary (Light+ アクセス可) ---
    def test_summary_free_passes_auth_but_plan_not_gated(self, gate_client):
        """dashboard-summary は require_pro_plan なし → Free でも取得可（認証は必要）。"""
        deps.db.query_one.return_value = {"cnt": 0}
        deps.db.query.return_value = []
        res = gate_client.get(f"{BASE}/dashboard-summary")
        assert res.status_code == 200
