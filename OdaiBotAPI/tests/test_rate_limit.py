"""レートリミッター（429）のテスト。"""
from __future__ import annotations

import time

import pytest

from OdaiBotAPI import limiter

from .conftest import BASE

# Starlette TestClient が ASGI scope に設定する default client host
_IP = "testclient"


class TestLoginRateLimit:
    def test_rate_limit_returns_429(self, anon_client):
        # login_rate_limit: limit=10, window=60
        limiter._buckets[_IP] = [time.time()] * 10

        res = anon_client.post(f"{BASE}/auth/login", json={"username": "u", "password": "p"})
        assert res.status_code == 429
        assert "上限" in res.json()["detail"]


class TestResetPasswordRateLimit:
    def test_rate_limit_returns_429(self, anon_client):
        # reset_rate_limit: limit=5, window=60
        limiter._buckets[_IP] = [time.time()] * 5

        res = anon_client.post(
            f"{BASE}/auth/reset-password",
            json={"invite_token": "tok", "password": "pass1234"},
        )
        assert res.status_code == 429
        assert "上限" in res.json()["detail"]
