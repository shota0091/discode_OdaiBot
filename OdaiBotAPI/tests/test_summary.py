"""ダッシュボードサマリー API (/dashboard-summary) のテスト。"""
from __future__ import annotations

from datetime import datetime

import pytest

from OdaiBotAPI import deps

from .conftest import BASE

_NOW = datetime.utcnow()


class TestDashboardSummary:
    _url = f"{BASE}/dashboard-summary"

    def test_success_with_last_post(self, admin_client):
        last_post = {
            "odai_id": 42,
            "filename": "odai42.png",
            "channel_id": 987654321,
            "result": "success",
            "posted_at": _NOW,
        }
        deps.db.query_one.side_effect = [
            {"cnt": 120},   # odai_count
            {"cnt": 3},     # active_schedule_count
            {"cnt": 2},     # channel_count
            last_post,      # last_post
        ]

        res = admin_client.get(self._url)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["odai_count"] == 120
        assert data["active_schedule_count"] == 3
        assert data["channel_count"] == 2
        assert data["last_post"]["filename"] == "odai42.png"

    def test_success_without_last_post(self, admin_client):
        deps.db.query_one.side_effect = [
            {"cnt": 0},
            {"cnt": 0},
            {"cnt": 0},
            None,  # no post history
        ]

        res = admin_client.get(self._url)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["odai_count"] == 0
        assert data["last_post"] is None

    def test_unauthenticated_returns_401(self, anon_client):
        res = anon_client.get(self._url)
        assert res.status_code == 401
