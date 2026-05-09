"""deps.py のユーティリティ関数のユニットテスト（DB不要）。"""
from __future__ import annotations

import pytest
from fastapi import HTTPException
from unittest.mock import patch

from OdaiBotAPI import deps
from OdaiBotAPI.deps import (
    check_odai_capacity,
    get_guild_plan,
    hash_password,
    normalize_tags,
    require_dashboard_plan,
    require_pro_plan,
    verify_password,
)
from .conftest import GUILD_ID


class TestHashPassword:
    def test_returns_salt_and_digest(self):
        result = hash_password("password123")
        assert "$" in result
        salt, digest = result.split("$", 1)
        assert len(salt) == 32  # token_hex(16) → 32 hex chars
        assert len(digest) == 64  # sha256 → 32 bytes → 64 hex chars

    def test_same_password_different_salts(self):
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2  # salt がランダムなので毎回異なる

    def test_different_passwords_different_hashes(self):
        assert hash_password("password_a") != hash_password("password_b")


class TestVerifyPassword:
    def test_correct_password(self):
        hashed = hash_password("correct_password")
        assert verify_password("correct_password", hashed) is True

    def test_wrong_password(self):
        hashed = hash_password("correct_password")
        assert verify_password("wrong_password", hashed) is False

    def test_malformed_hash_returns_false(self):
        assert verify_password("any_password", "no_dollar_sign") is False

    def test_empty_password(self):
        hashed = hash_password("")
        assert verify_password("", hashed) is True
        assert verify_password("notempty", hashed) is False


class TestNormalizeTags:
    def test_none_returns_empty_list(self):
        assert normalize_tags(None) == []

    def test_comma_separated_string(self):
        assert normalize_tags("tag1,tag2,tag3") == ["tag1", "tag2", "tag3"]

    def test_string_with_spaces(self):
        assert normalize_tags(" tag1 , tag2 ") == ["tag1", "tag2"]

    def test_list_input(self):
        assert normalize_tags(["tag1", "tag2"]) == ["tag1", "tag2"]

    def test_list_with_empty_strings(self):
        assert normalize_tags(["tag1", "", "tag2"]) == ["tag1", "tag2"]

    def test_empty_string(self):
        assert normalize_tags("") == []

    def test_single_tag(self):
        assert normalize_tags("single") == ["single"]


# ─────────────────────────────────────────────────────────────
# get_guild_plan
# ─────────────────────────────────────────────────────────────
class TestGetGuildPlan:
    def test_returns_plan_when_record_exists(self):
        deps.db.query_one.return_value = {
            "plan_name": "pro", "has_dashboard": 1, "has_discord_op": 1,
            "can_expand_capacity": 1, "custom_odai_max": None,
            "custom_odai_capacity": 500, "status": "active",
        }
        result = get_guild_plan(GUILD_ID)
        assert result["plan_name"] == "pro"
        assert result["custom_odai_capacity"] == 500

    def test_falls_back_to_free_when_no_record(self):
        deps.db.query_one.side_effect = [
            None,  # guild_plans JOIN → no record
            {"plan_name": "free", "has_dashboard": 0, "has_discord_op": 0,
             "can_expand_capacity": 0, "custom_odai_max": 0},
        ]
        result = get_guild_plan(GUILD_ID)
        assert result["plan_name"] == "free"
        assert result["custom_odai_capacity"] == 0
        assert result["status"] == "active"

    def test_falls_back_to_empty_dict_when_plans_table_empty(self):
        deps.db.query_one.side_effect = [None, None]
        result = get_guild_plan(GUILD_ID)
        assert result["custom_odai_capacity"] == 0


# ─────────────────────────────────────────────────────────────
# require_dashboard_plan
# ─────────────────────────────────────────────────────────────
class TestRequireDashboardPlan:
    def test_free_plan_raises_403(self):
        deps.db.query_one.side_effect = [
            None,
            {"plan_name": "free", "has_dashboard": 0, "has_discord_op": 0,
             "can_expand_capacity": 0, "custom_odai_max": 0},
        ]
        with pytest.raises(HTTPException) as exc:
            require_dashboard_plan(GUILD_ID)
        assert exc.value.status_code == 403

    def test_light_plan_passes(self):
        deps.db.query_one.return_value = {
            "plan_name": "light", "has_dashboard": 1, "has_discord_op": 1,
            "can_expand_capacity": 1, "custom_odai_max": 1000,
            "custom_odai_capacity": 100, "status": "active",
        }
        require_dashboard_plan(GUILD_ID)  # 例外が出なければ OK

    def test_pro_plan_passes(self):
        deps.db.query_one.return_value = {
            "plan_name": "pro", "has_dashboard": 1, "has_discord_op": 1,
            "can_expand_capacity": 1, "custom_odai_max": None,
            "custom_odai_capacity": 500, "status": "active",
        }
        require_dashboard_plan(GUILD_ID)


# ─────────────────────────────────────────────────────────────
# require_pro_plan
# ─────────────────────────────────────────────────────────────
class TestRequireProPlan:
    def _mock_plan(self, name: str):
        deps.db.query_one.return_value = {
            "plan_name": name, "has_dashboard": 1, "has_discord_op": 1,
            "can_expand_capacity": 1, "custom_odai_max": None,
            "custom_odai_capacity": None, "status": "active",
        }

    def test_free_raises_403(self):
        self._mock_plan("free")
        with pytest.raises(HTTPException) as exc:
            require_pro_plan(GUILD_ID)
        assert exc.value.status_code == 403

    def test_light_raises_403(self):
        self._mock_plan("light")
        with pytest.raises(HTTPException) as exc:
            require_pro_plan(GUILD_ID)
        assert exc.value.status_code == 403

    def test_pro_passes(self):
        self._mock_plan("pro")
        require_pro_plan(GUILD_ID)

    def test_enterprise_passes(self):
        self._mock_plan("enterprise")
        require_pro_plan(GUILD_ID)


# ─────────────────────────────────────────────────────────────
# check_odai_capacity
# ─────────────────────────────────────────────────────────────
class TestCheckOdaiCapacity:
    def test_null_capacity_is_unlimited(self):
        deps.db.query_one.return_value = {
            "plan_name": "enterprise", "custom_odai_capacity": None,
            "has_dashboard": 1, "has_discord_op": 1,
            "can_expand_capacity": 0, "custom_odai_max": None, "status": "active",
        }
        check_odai_capacity(GUILD_ID, adding=9999)  # 例外が出なければ OK

    def test_zero_capacity_raises_403(self):
        deps.db.query_one.return_value = {
            "plan_name": "free", "custom_odai_capacity": 0,
            "has_dashboard": 0, "has_discord_op": 0,
            "can_expand_capacity": 0, "custom_odai_max": 0, "status": "active",
        }
        with pytest.raises(HTTPException) as exc:
            check_odai_capacity(GUILD_ID)
        assert exc.value.status_code == 403

    def test_under_capacity_passes(self):
        deps.db.query_one.side_effect = [
            {"plan_name": "light", "custom_odai_capacity": 100,
             "has_dashboard": 1, "has_discord_op": 1,
             "can_expand_capacity": 1, "custom_odai_max": 1000, "status": "active"},
            {"cnt": 50},
        ]
        check_odai_capacity(GUILD_ID, adding=1)

    def test_at_capacity_raises_403(self):
        deps.db.query_one.side_effect = [
            {"plan_name": "light", "custom_odai_capacity": 100,
             "has_dashboard": 1, "has_discord_op": 1,
             "can_expand_capacity": 1, "custom_odai_max": 1000, "status": "active"},
            {"cnt": 100},
        ]
        with pytest.raises(HTTPException) as exc:
            check_odai_capacity(GUILD_ID, adding=1)
        assert exc.value.status_code == 403

    def test_bulk_import_exceeding_capacity_raises_403(self):
        deps.db.query_one.side_effect = [
            {"plan_name": "pro", "custom_odai_capacity": 500,
             "has_dashboard": 1, "has_discord_op": 1,
             "can_expand_capacity": 1, "custom_odai_max": None, "status": "active"},
            {"cnt": 490},
        ]
        with pytest.raises(HTTPException) as exc:
            check_odai_capacity(GUILD_ID, adding=20)  # 490+20=510 > 500
        assert exc.value.status_code == 403
