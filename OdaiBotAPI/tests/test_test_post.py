"""テスト投稿 API (/test-post) のテスト。"""
from __future__ import annotations

import pytest

from OdaiBotAPI import deps

from .conftest import BASE, GUILD_ID

_CANDIDATE = {
    "id": 1, "filename": "odai1.jpg", "storage_path": "/path/odai1.jpg",
    "tags": ["日常"],
}

_PAYLOAD = {"channel_id": 987654321}


class TestTestPost:
    _url = f"{BASE}/test-post"

    def test_success(self, admin_client):
        deps.notify_service.select_candidate.return_value = _CANDIDATE

        res = admin_client.post(self._url, json=_PAYLOAD)
        assert res.status_code == 200
        assert res.json()["data"]["filename"] == "odai1.jpg"

    def test_no_candidate_returns_404(self, admin_client):
        deps.notify_service.select_candidate.return_value = None

        res = admin_client.post(self._url, json=_PAYLOAD)
        assert res.status_code == 404

    def test_with_tag_mode_and_list(self, admin_client):
        deps.notify_service.select_candidate.return_value = _CANDIDATE

        res = admin_client.post(self._url, json={
            "channel_id": 987654321,
            "tag_mode": "allow",
            "tag_list": ["日常", "食べ物"],
        })
        assert res.status_code == 200
        schedule = deps.notify_service.select_candidate.call_args[0][2]
        assert schedule["tag_mode"] == "allow"
        assert schedule["tag_list"] == ["日常", "食べ物"]

    def test_default_tag_mode_is_all(self, admin_client):
        deps.notify_service.select_candidate.return_value = _CANDIDATE

        res = admin_client.post(self._url, json={"channel_id": 111})
        assert res.status_code == 200
        schedule = deps.notify_service.select_candidate.call_args[0][2]
        assert schedule["tag_mode"] == "all"
        assert schedule["tag_list"] == []

    def test_unauthenticated_returns_401(self, anon_client):
        res = anon_client.post(self._url, json=_PAYLOAD)
        assert res.status_code == 401
