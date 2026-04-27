"""タグ管理 API (/tags/*) のテスト。"""
from __future__ import annotations

from datetime import datetime

import pytest

from OdaiBotAPI import deps

from .conftest import BASE, make_cursor

_NOW = datetime.utcnow()
_TAG = {"id": 1, "name": "日常", "description": "普段使い", "created_at": _NOW, "updated_at": _NOW}


class TestListTags:
    _url = f"{BASE}/tags/"

    def test_success(self, admin_client):
        deps.db.query.return_value = [_TAG]

        res = admin_client.get(self._url)
        assert res.status_code == 200
        assert res.json()["data"][0]["name"] == "日常"

    def test_search_passes_query_param(self, admin_client):
        deps.db.query.return_value = []

        res = admin_client.get(self._url, params={"q": "日常"})
        assert res.status_code == 200

    def test_unauthenticated_returns_401(self, anon_client):
        res = anon_client.get(self._url)
        assert res.status_code == 401


class TestCreateTag:
    _url = f"{BASE}/tags/"

    def test_success(self, admin_client):
        deps.db.query_one.side_effect = [None, _TAG]  # no duplicate → created tag
        deps.db.execute.return_value = make_cursor(1)

        res = admin_client.post(self._url, json={"name": "日常", "description": "普段使い"})
        assert res.status_code == 201
        assert res.json()["data"]["name"] == "日常"

    def test_duplicate_name_returns_409(self, admin_client):
        deps.db.query_one.return_value = {"id": 1}  # already exists

        res = admin_client.post(self._url, json={"name": "日常"})
        assert res.status_code == 409


class TestUpdateTag:
    def test_success(self, admin_client):
        deps.db.query_one.side_effect = [
            {"id": 1},   # tag exists
            None,        # no name conflict
            _TAG,        # updated tag
        ]
        deps.db.execute.return_value = make_cursor()

        res = admin_client.put(f"{BASE}/tags/1", json={"name": "日常2"})
        assert res.status_code == 200

    def test_not_found_returns_404(self, admin_client):
        deps.db.query_one.return_value = None

        res = admin_client.put(f"{BASE}/tags/999", json={"name": "x"})
        assert res.status_code == 404

    def test_name_conflict_returns_409(self, admin_client):
        deps.db.query_one.side_effect = [
            {"id": 1},   # tag exists
            {"id": 2},   # name conflict with another tag
        ]
        res = admin_client.put(f"{BASE}/tags/1", json={"name": "existing_tag"})
        assert res.status_code == 409

    def test_no_fields_returns_400(self, admin_client):
        deps.db.query_one.return_value = {"id": 1}

        res = admin_client.put(f"{BASE}/tags/1", json={})
        assert res.status_code == 400


class TestDeleteTag:
    def test_success(self, admin_client):
        deps.db.query_one.return_value = {"id": 1}
        deps.db.execute.return_value = make_cursor()

        res = admin_client.delete(f"{BASE}/tags/1")
        assert res.status_code == 204

    def test_not_found_returns_404(self, admin_client):
        deps.db.query_one.return_value = None

        res = admin_client.delete(f"{BASE}/tags/999")
        assert res.status_code == 404
