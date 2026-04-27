"""deps.py のユーティリティ関数のユニットテスト（DB不要）。"""
from __future__ import annotations

import pytest

from OdaiBotAPI.deps import hash_password, normalize_tags, verify_password


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
