"""お題管理 API (/odai/*) のテスト。"""
from __future__ import annotations

import io
from datetime import datetime

import pytest

from OdaiBotAPI import deps

from .conftest import BASE, make_cursor

_NOW = datetime.utcnow()
_ODAI_ROW = {
    "id": 1, "guild_id": 111222333444555666,
    "filename": "odai1.jpg", "storage_path": "/path/odai1.jpg",
    "added_at": _NOW, "deleted_at": None,
}


class TestListOdai:
    _url = f"{BASE}/odai/"

    def test_success(self, admin_client):
        deps.db.query.return_value = [_ODAI_ROW]
        deps.odai_repo.get_tags.return_value = ["日常"]

        res = admin_client.get(self._url)
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == 1
        assert data[0]["filename"] == "odai1.jpg"
        assert data[0]["tags"] == ["日常"]

    def test_filter_by_tag(self, admin_client):
        deps.db.query.return_value = []

        res = admin_client.get(self._url, params={"tag": "日常"})
        assert res.status_code == 200

    def test_filter_by_favorite(self, admin_client):
        deps.db.query.return_value = []

        res = admin_client.get(self._url, params={"favorite": "true"})
        assert res.status_code == 200

    def test_unauthenticated_returns_401(self, anon_client):
        res = anon_client.get(self._url)
        assert res.status_code == 401


class TestUploadOdai:
    _url = f"{BASE}/odai/"

    def _make_file(self, name="test.jpg", content_type="image/jpeg", size=100):
        return ("file", (name, io.BytesIO(b"x" * size), content_type))

    def test_success(self, admin_client):
        deps.odai_repo.add_odai.return_value = (True, "OK")
        deps.db.query_one.return_value = {**_ODAI_ROW, "id": 2, "filename": "test.jpg"}
        deps.odai_repo.get_tags.return_value = []

        res = admin_client.post(
            self._url,
            files=[self._make_file()],
        )
        assert res.status_code == 201

    def test_invalid_content_type_returns_400(self, admin_client):
        res = admin_client.post(
            self._url,
            files=[self._make_file("file.gif", "image/gif")],
        )
        assert res.status_code == 400

    def test_file_too_large_returns_400(self, admin_client):
        large_size = 9 * 1024 * 1024  # 9MB > 8MB limit
        res = admin_client.post(
            self._url,
            files=[self._make_file("big.jpg", "image/jpeg", large_size)],
        )
        assert res.status_code == 400

    def test_duplicate_returns_409(self, admin_client):
        deps.odai_repo.add_odai.return_value = (False, "ファイル名が重複しています")

        res = admin_client.post(
            self._url,
            files=[self._make_file()],
        )
        assert res.status_code == 409


class TestUpdateOdai:
    def test_success(self, admin_client):
        deps.db.query_one.side_effect = [
            {"id": 1},    # exists check
            _ODAI_ROW,    # after update
        ]
        deps.odai_repo.get_tags.return_value = ["日常"]
        deps.db.execute.return_value = make_cursor()

        res = admin_client.put(f"{BASE}/odai/1", json={"is_favorite": True})
        assert res.status_code == 200

    def test_not_found_returns_404(self, admin_client):
        deps.db.query_one.return_value = None

        res = admin_client.put(f"{BASE}/odai/999", json={"is_favorite": True})
        assert res.status_code == 404


class TestDeleteOdai:
    def test_success(self, admin_client):
        deps.db.query_one.return_value = {"id": 1}
        deps.db.execute.return_value = make_cursor()

        res = admin_client.delete(f"{BASE}/odai/1")
        assert res.status_code == 204

    def test_not_found_returns_404(self, admin_client):
        deps.db.query_one.return_value = None

        res = admin_client.delete(f"{BASE}/odai/999")
        assert res.status_code == 404
