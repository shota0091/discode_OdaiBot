"""スケジュール管理 API (/schedules/*) のテスト。"""
from __future__ import annotations

import json
from datetime import datetime

import pytest

from OdaiBotAPI import deps

from .conftest import BASE, make_cursor

_NOW = datetime.utcnow()
_SCHEDULE_ROW = {
    "id": 1, "guild_id": 111222333444555666,
    "channel_id": 987654321, "time": "09:00",
    "enabled": 1, "tag_mode": "all",
    "tag_list": json.dumps([]),
    "created_at": _NOW, "updated_at": _NOW,
}
_SCHEDULE_PAYLOAD = {
    "channel_id": 987654321,
    "time": "09:00",
    "enabled": True,
    "tag_mode": "all",
    "tag_list": [],
}


class TestListSchedules:
    _url = f"{BASE}/schedules/"

    def test_success(self, admin_client):
        deps.db.query.return_value = [_SCHEDULE_ROW]

        res = admin_client.get(self._url)
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == 1
        assert data[0]["time"] == "09:00"
        assert data[0]["enabled"] is True
        assert data[0]["tag_list"] == []

    def test_unauthenticated_returns_401(self, anon_client):
        res = anon_client.get(self._url)
        assert res.status_code == 401


class TestCreateSchedule:
    _url = f"{BASE}/schedules/"

    def test_success(self, admin_client):
        deps.db.query_one.side_effect = [
            {"plan_name": "pro"},  # get_guild_plan
            _SCHEDULE_ROW,         # after INSERT
        ]
        deps.db.execute.return_value = make_cursor(1)

        res = admin_client.post(self._url, json=_SCHEDULE_PAYLOAD)
        assert res.status_code == 201
        assert res.json()["data"]["time"] == "09:00"

    def test_invalid_time_format_returns_400(self, admin_client):
        payload = {**_SCHEDULE_PAYLOAD, "time": "9:00"}  # HH:MM に合わない
        res = admin_client.post(self._url, json=payload)
        assert res.status_code == 400

    def test_invalid_tag_mode_returns_400(self, admin_client):
        payload = {**_SCHEDULE_PAYLOAD, "tag_mode": "invalid"}
        res = admin_client.post(self._url, json=payload)
        assert res.status_code == 400

    def test_allow_mode_without_tags_returns_400(self, admin_client):
        payload = {**_SCHEDULE_PAYLOAD, "tag_mode": "allow", "tag_list": []}
        res = admin_client.post(self._url, json=payload)
        assert res.status_code == 400

    def test_allow_mode_with_tags_succeeds(self, admin_client):
        row = {**_SCHEDULE_ROW, "tag_mode": "allow", "tag_list": json.dumps(["日常"])}
        deps.db.query_one.side_effect = [
            {"plan_name": "pro"},  # get_guild_plan
            row,                   # after INSERT
        ]
        deps.db.execute.return_value = make_cursor(1)

        payload = {**_SCHEDULE_PAYLOAD, "tag_mode": "allow", "tag_list": ["日常"]}
        res = admin_client.post(self._url, json=payload)
        assert res.status_code == 201

    def test_free_plan_can_create_first_schedule(self, admin_client):
        deps.db.query_one.side_effect = [
            {"plan_name": "free"},  # get_guild_plan
            {"cnt": 0},             # COUNT(*) → 0件
            _SCHEDULE_ROW,          # after INSERT
        ]
        deps.db.execute.return_value = make_cursor(1)

        res = admin_client.post(self._url, json=_SCHEDULE_PAYLOAD)
        assert res.status_code == 201

    def test_free_plan_cannot_create_second_schedule(self, admin_client):
        deps.db.query_one.side_effect = [
            {"plan_name": "free"},  # get_guild_plan
            {"cnt": 1},             # COUNT(*) → すでに1件
        ]

        res = admin_client.post(self._url, json=_SCHEDULE_PAYLOAD)
        assert res.status_code == 400
        assert "Freeプラン" in res.json()["detail"]


class TestUpdateSchedule:
    def test_success(self, admin_client):
        deps.db.query_one.side_effect = [{"id": 1}, _SCHEDULE_ROW]
        deps.db.execute.return_value = make_cursor()

        res = admin_client.put(f"{BASE}/schedules/1", json={**_SCHEDULE_PAYLOAD, "enabled": False})
        assert res.status_code == 200

    def test_not_found_returns_404(self, admin_client):
        deps.db.query_one.return_value = None

        res = admin_client.put(f"{BASE}/schedules/999", json=_SCHEDULE_PAYLOAD)
        assert res.status_code == 404


class TestDeleteSchedule:
    def test_success(self, admin_client):
        deps.db.query_one.return_value = {"id": 1}
        deps.db.execute.return_value = make_cursor()

        res = admin_client.delete(f"{BASE}/schedules/1")
        assert res.status_code == 204

    def test_not_found_returns_404(self, admin_client):
        deps.db.query_one.return_value = None

        res = admin_client.delete(f"{BASE}/schedules/999")
        assert res.status_code == 404
