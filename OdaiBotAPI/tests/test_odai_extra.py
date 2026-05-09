"""お題 API の追加エンドポイントテスト。

履歴・使用状況・画像取得・インポート・更新エッジケースを検証する。
"""
from __future__ import annotations

import io
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from OdaiBotAPI import deps

from .conftest import BASE, GUILD_ID, make_cursor

_NOW = datetime.utcnow()

_ODAI_ROW = {
    "id": 1, "guild_id": GUILD_ID, "filename": "odai1.jpg", "storage_path": None,
    "is_favorite": 0, "memo": None, "added_at": _NOW, "updated_at": _NOW, "deleted_at": None,
    "created_by": 1, "created_by_name": "admin_user",
}

_PRO_PLAN = {
    "plan_name": "pro", "custom_odai_capacity": None,
    "has_dashboard": 1, "has_discord_op": 1,
    "can_expand_capacity": 1, "custom_odai_max": None, "status": "active",
}


# ─────────────────────────────────────────────────────────────
# GET /odai/{odai_id}/history
# ─────────────────────────────────────────────────────────────
class TestGetOdaiHistory:
    def test_success(self, admin_client):
        deps.db.query_one.side_effect = [
            {"id": 1},    # odai exists check
            {"cnt": 3},   # total history count
        ]
        deps.db.query.return_value = [
            {"id": 1, "action": "tagged", "detail": "日常", "created_at": _NOW,
             "user_id": 1, "user_name": "admin"},
        ]

        res = admin_client.get(f"{BASE}/odai/1/history")
        assert res.status_code == 200
        body = res.json()
        assert body["total"] == 3
        assert body["page"] == 1
        assert body["per_page"] == 5
        assert len(body["data"]) == 1

    def test_not_found_returns_404(self, admin_client):
        deps.db.query_one.return_value = None

        res = admin_client.get(f"{BASE}/odai/999/history")
        assert res.status_code == 404

    def test_pagination_params(self, admin_client):
        deps.db.query_one.side_effect = [
            {"id": 1},
            {"cnt": 20},
        ]
        deps.db.query.return_value = []

        res = admin_client.get(f"{BASE}/odai/1/history", params={"page": 2, "per_page": 10})
        assert res.status_code == 200
        body = res.json()
        assert body["page"] == 2
        assert body["per_page"] == 10
        assert body["total_pages"] == 2

    def test_per_page_clamped_to_50(self, admin_client):
        deps.db.query_one.side_effect = [
            {"id": 1},
            {"cnt": 0},
        ]
        deps.db.query.return_value = []

        res = admin_client.get(f"{BASE}/odai/1/history", params={"per_page": 100})
        assert res.status_code == 200
        assert res.json()["per_page"] == 50

    def test_unauthenticated_returns_401(self, anon_client):
        res = anon_client.get(f"{BASE}/odai/1/history")
        assert res.status_code == 401


# ─────────────────────────────────────────────────────────────
# GET /odai/{odai_id}/usage
# ─────────────────────────────────────────────────────────────
class TestGetOdaiUsage:
    def test_success(self, admin_client):
        deps.db.query_one.return_value = {"id": 1}
        deps.db.query.return_value = [
            {"channel_id": 987654321, "channel_name": "general", "used_at": _NOW},
        ]

        res = admin_client.get(f"{BASE}/odai/1/usage")
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == 1
        assert data[0]["channel_id"] == "987654321"

    def test_channel_id_is_string(self, admin_client):
        deps.db.query_one.return_value = {"id": 1}
        deps.db.query.return_value = [
            {"channel_id": 111222333444555666, "channel_name": "ch", "used_at": _NOW},
        ]

        res = admin_client.get(f"{BASE}/odai/1/usage")
        assert isinstance(res.json()["data"][0]["channel_id"], str)

    def test_not_found_returns_404(self, admin_client):
        deps.db.query_one.return_value = None

        res = admin_client.get(f"{BASE}/odai/999/usage")
        assert res.status_code == 404

    def test_empty_usage(self, admin_client):
        deps.db.query_one.return_value = {"id": 1}
        deps.db.query.return_value = []

        res = admin_client.get(f"{BASE}/odai/1/usage")
        assert res.status_code == 200
        assert res.json()["data"] == []

    def test_unauthenticated_returns_401(self, anon_client):
        res = anon_client.get(f"{BASE}/odai/1/usage")
        assert res.status_code == 401


# ─────────────────────────────────────────────────────────────
# GET /odai/{odai_id}/image
# ─────────────────────────────────────────────────────────────
class TestGetOdaiImage:
    def test_not_found_odai_returns_404(self, admin_client):
        deps.db.query_one.return_value = None

        res = admin_client.get(f"{BASE}/odai/999/image")
        assert res.status_code == 404

    def test_no_storage_path_returns_404(self, admin_client):
        deps.db.query_one.return_value = {"filename": "test.jpg", "storage_path": None}

        res = admin_client.get(f"{BASE}/odai/1/image")
        assert res.status_code == 404

    def test_file_not_on_disk_returns_404(self, admin_client):
        deps.db.query_one.return_value = {
            "filename": "test.jpg",
            "storage_path": "/nonexistent/path/that/does/not/exist.jpg",
        }

        res = admin_client.get(f"{BASE}/odai/1/image")
        assert res.status_code == 404

    def test_success_jpeg(self, admin_client):
        deps.db.query_one.return_value = {"filename": "photo.jpg", "storage_path": "/fake/photo.jpg"}
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_bytes.return_value = b"\xff\xd8\xff\xe0"

        with patch("OdaiBotAPI.routers.odai.Path", return_value=mock_path):
            res = admin_client.get(f"{BASE}/odai/1/image")

        assert res.status_code == 200
        assert "image/jpeg" in res.headers["content-type"]

    def test_success_png(self, admin_client):
        deps.db.query_one.return_value = {"filename": "photo.png", "storage_path": "/fake/photo.png"}
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_bytes.return_value = b"\x89PNG\r\n"

        with patch("OdaiBotAPI.routers.odai.Path", return_value=mock_path):
            res = admin_client.get(f"{BASE}/odai/1/image")

        assert res.status_code == 200
        assert "image/png" in res.headers["content-type"]

    def test_success_webp(self, admin_client):
        deps.db.query_one.return_value = {"filename": "photo.webp", "storage_path": "/fake/photo.webp"}
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.read_bytes.return_value = b"RIFF....WEBP"

        with patch("OdaiBotAPI.routers.odai.Path", return_value=mock_path):
            res = admin_client.get(f"{BASE}/odai/1/image")

        assert res.status_code == 200
        assert "image/webp" in res.headers["content-type"]

    def test_unauthenticated_returns_401(self, anon_client):
        res = anon_client.get(f"{BASE}/odai/1/image")
        assert res.status_code == 401


# ─────────────────────────────────────────────────────────────
# POST /odai/import
# ─────────────────────────────────────────────────────────────
class TestImportOdai:
    _url = f"{BASE}/odai/import"

    def _make_file(self, name="test.jpg", content_type="image/jpeg", size=100):
        return ("files", (name, io.BytesIO(b"x" * size), content_type))

    def test_success_single_file(self, admin_client):
        deps.db.query_one.side_effect = [
            _PRO_PLAN,    # check_odai_capacity → get_guild_plan
            _ODAI_ROW,    # _get_odai_by_filename after insert
        ]
        deps.odai_repo.add_odai.return_value = (True, "OK")
        deps.odai_repo.get_tags.return_value = []

        res = admin_client.post(self._url, files=[self._make_file()])
        assert res.status_code == 201
        data = res.json()["data"]
        assert len(data) == 1
        assert data[0]["success"] is True
        assert data[0]["filename"] == "test.jpg"

    def test_duplicate_file_fails_gracefully(self, admin_client):
        deps.db.query_one.return_value = _PRO_PLAN  # capacity check
        deps.odai_repo.add_odai.return_value = (False, "ファイル名が重複しています")

        res = admin_client.post(self._url, files=[self._make_file()])
        assert res.status_code == 201
        data = res.json()["data"]
        assert data[0]["success"] is False
        assert "odai" not in data[0]

    def test_partial_success_multiple_files(self, admin_client):
        deps.db.query_one.side_effect = [
            _PRO_PLAN,    # capacity check
            _ODAI_ROW,    # get_odai_by_filename for first file
        ]
        deps.odai_repo.add_odai.side_effect = [
            (True, "OK"),
            (False, "重複"),
        ]
        deps.odai_repo.get_tags.return_value = []

        res = admin_client.post(self._url, files=[
            self._make_file("a.jpg"),
            self._make_file("b.jpg"),
        ])
        assert res.status_code == 201
        data = res.json()["data"]
        assert len(data) == 2
        assert data[0]["success"] is True
        assert data[1]["success"] is False

    def test_no_files_returns_422(self, admin_client):
        res = admin_client.post(self._url)
        assert res.status_code == 422

    def test_unauthenticated_returns_401(self, anon_client):
        res = anon_client.post(self._url, files=[self._make_file()])
        assert res.status_code == 401


# ─────────────────────────────────────────────────────────────
# PUT /odai/{odai_id} — エッジケース（基本は test_odai.py でカバー済み）
# ─────────────────────────────────────────────────────────────
class TestUpdateOdaiEdgeCases:
    def test_filename_rename_conflict_returns_409(self, admin_client):
        deps.db.query_one.side_effect = [
            {"id": 1},    # odai exists
            {"id": 2},    # filename conflict found
        ]

        res = admin_client.put(f"{BASE}/odai/1", json={"filename": "existing.jpg"})
        assert res.status_code == 409

    def test_empty_filename_returns_400(self, admin_client):
        deps.db.query_one.return_value = {"id": 1}

        res = admin_client.put(f"{BASE}/odai/1", json={"filename": "   "})
        assert res.status_code == 400

    def test_memo_update(self, admin_client):
        deps.db.query_one.side_effect = [
            {"id": 1},    # exists check
            _ODAI_ROW,    # _get_odai_with_tags
        ]
        deps.db.execute.return_value = make_cursor()
        deps.odai_repo.get_tags.return_value = []

        res = admin_client.put(f"{BASE}/odai/1", json={"memo": "覚え書き"})
        assert res.status_code == 200

    def test_soft_delete(self, admin_client):
        deps.db.query_one.side_effect = [
            {"id": 1},    # exists check
            _ODAI_ROW,    # _get_odai_with_tags
        ]
        deps.db.execute.return_value = make_cursor()
        deps.odai_repo.get_tags.return_value = []

        res = admin_client.put(f"{BASE}/odai/1", json={"deleted": True})
        assert res.status_code == 200
        call_sql = deps.db.execute.call_args_list[0][0][0]
        assert "deleted_at" in call_sql

    def test_restore_odai(self, admin_client):
        deps.db.query_one.side_effect = [
            {"id": 1},    # exists check
            _ODAI_ROW,    # _get_odai_with_tags
        ]
        deps.db.execute.return_value = make_cursor()
        deps.odai_repo.get_tags.return_value = []

        res = admin_client.put(f"{BASE}/odai/1", json={"deleted": False})
        assert res.status_code == 200
        call_sql = deps.db.execute.call_args_list[0][0][0]
        assert "deleted_at" in call_sql

    def test_tags_update(self, admin_client):
        deps.db.query_one.side_effect = [
            {"id": 1},    # exists check
            _ODAI_ROW,    # _get_odai_with_tags at the end
        ]
        deps.db.execute.return_value = make_cursor()
        deps.odai_repo.get_tags.side_effect = [
            [],               # old_tags in update_odai
            ["新しいタグ"],     # tags in _get_odai_with_tags
        ]
        deps.odai_repo._ensure_tag.return_value = 5

        res = admin_client.put(f"{BASE}/odai/1", json={"tags": ["新しいタグ"]})
        assert res.status_code == 200

    def test_filename_successful_rename(self, admin_client):
        deps.db.query_one.side_effect = [
            {"id": 1},    # exists check
            None,         # no filename conflict
            _ODAI_ROW,    # _get_odai_with_tags
        ]
        deps.db.execute.return_value = make_cursor()
        deps.odai_repo.get_tags.return_value = []

        res = admin_client.put(f"{BASE}/odai/1", json={"filename": "renamed.jpg"})
        assert res.status_code == 200
