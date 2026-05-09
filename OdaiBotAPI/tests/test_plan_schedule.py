"""Free プランスケジュール管理 API (/plan-schedule) のテスト。"""
from __future__ import annotations

import pytest

from OdaiBotAPI import deps

from .conftest import BASE, GUILD_ID, make_cursor

_URL = f"{BASE}/plan-schedule"

_SCHEDULE_ROW = {
    "id": 1, "channel_id": 987654321,
    "time": "08:00", "enabled": 1, "tag_mode": "all", "tag_list": None,
}

_PRO_PLAN = {
    "plan_name": "pro", "has_dashboard": 1, "has_discord_op": 1,
    "can_expand_capacity": 1, "custom_odai_max": None,
    "custom_odai_capacity": 500, "status": "active",
}

_FREE_PLAN = {
    "plan_name": "free", "has_dashboard": 0, "has_discord_op": 0,
    "can_expand_capacity": 0, "custom_odai_max": 0,
    "custom_odai_capacity": 0, "status": "active",
}


# ─────────────────────────────────────────────────────────────
# GET /plan-schedule
# ─────────────────────────────────────────────────────────────
class TestGetPlanSchedule:
    def test_returns_schedule_when_exists(self, admin_client):
        deps.db.query.return_value = [_SCHEDULE_ROW]

        res = admin_client.get(_URL)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["time"] == "08:00"
        assert data["channel_id"] == str(_SCHEDULE_ROW["channel_id"])

    def test_returns_null_when_no_schedule(self, admin_client):
        deps.db.query.return_value = []

        res = admin_client.get(_URL)
        assert res.status_code == 200
        assert res.json()["data"] is None

    def test_unauthenticated_returns_401(self, anon_client):
        res = anon_client.get(_URL)
        assert res.status_code == 401


# ─────────────────────────────────────────────────────────────
# POST /plan-schedule
# ─────────────────────────────────────────────────────────────
class TestSetPlanSchedule:
    _payload = {"channel_id": "987654321", "time": "09:00"}

    def test_creates_schedule_when_none_exists(self, admin_client):
        deps.db.query.return_value = []           # existing → なし
        # Pro プランのため count check はスキップされる（_is_pro が True を返す）
        deps.db.query_one.side_effect = [
            _PRO_PLAN,                             # _is_pro → pro plan
            {**_SCHEDULE_ROW, "time": "09:00",     # after INSERT
             "enabled": 1},
        ]
        deps.db.execute.return_value = make_cursor(1)

        res = admin_client.post(_URL, json=self._payload)
        assert res.status_code == 200
        assert res.json()["data"]["time"] == "09:00"

    def test_updates_existing_schedule(self, admin_client):
        deps.db.query.return_value = [{"id": 1}]  # existing あり
        deps.db.query_one.return_value = {**_SCHEDULE_ROW, "time": "09:00", "enabled": 1}
        deps.db.execute.return_value = make_cursor(1)

        res = admin_client.post(_URL, json=self._payload)
        assert res.status_code == 200
        # UPDATE が呼ばれたか確認
        call_sql = deps.db.execute.call_args[0][0]
        assert "UPDATE" in call_sql

    def test_non_pro_cannot_create_second_schedule(self, admin_client):
        """non-Pro で LIMIT 1 クエリが空でも count >= 1 なら 403。"""
        deps.db.query.return_value = []           # LIMIT 1 → 空（テスト用）
        deps.db.query_one.side_effect = [
            _FREE_PLAN,                            # _is_pro → false
            {"cnt": 1},                            # count = 1 → 制限発動
        ]

        res = admin_client.post(_URL, json=self._payload)
        assert res.status_code == 403

    def test_free_plan_can_create_first_schedule(self, admin_client):
        deps.db.query.return_value = []           # existing → なし
        deps.db.query_one.side_effect = [
            _FREE_PLAN,                            # _is_pro → false
            {"cnt": 0},                            # count = 0 → OK
            {**_SCHEDULE_ROW, "time": "09:00", "enabled": 1},
        ]
        deps.db.execute.return_value = make_cursor(1)

        res = admin_client.post(_URL, json=self._payload)
        assert res.status_code == 200

    def test_unauthenticated_returns_401(self, anon_client):
        res = anon_client.post(_URL, json=self._payload)
        assert res.status_code == 401


# ─────────────────────────────────────────────────────────────
# DELETE /plan-schedule/{schedule_id}
# ─────────────────────────────────────────────────────────────
class TestDeletePlanSchedule:
    def test_success(self, admin_client):
        deps.db.query_one.return_value = {"id": 1}
        deps.db.execute.return_value = make_cursor()

        res = admin_client.delete(f"{_URL}/1")
        assert res.status_code == 204

    def test_not_found_returns_404(self, admin_client):
        deps.db.query_one.return_value = None

        res = admin_client.delete(f"{_URL}/999")
        assert res.status_code == 404

    def test_wrong_guild_returns_404(self, admin_client):
        """別 guild のスケジュールは削除できない。"""
        deps.db.query_one.return_value = None  # guild_id 不一致で None が返る

        res = admin_client.delete(f"{_URL}/1")
        assert res.status_code == 404

    def test_unauthenticated_returns_401(self, anon_client):
        res = anon_client.delete(f"{_URL}/1")
        assert res.status_code == 401
