"""Stripe連携 / プラン情報 API のテスト。"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from OdaiBotAPI import deps

from .conftest import BASE, GUILD_ID, make_cursor

_BOT_SECRET = "test_bot_secret"
_PLAN_ENDPOINT = f"/api/guilds/{GUILD_ID}/plan"

_PRO_PLAN_ROW = {
    "plan_name": "pro", "price": 960,
    "has_dashboard": 1, "has_discord_op": 1,
    "can_expand_capacity": 1, "custom_odai_max": None,
    "custom_odai_capacity": 500, "status": "active",
    "current_period_end": None,
}


# ─────────────────────────────────────────────────────────────
# GET /api/guilds/{guild_id}/plan
# ─────────────────────────────────────────────────────────────
class TestGetGuildPlanEndpoint:
    def test_returns_plan_when_record_exists(self, anon_client):
        deps.db.query_one.return_value = _PRO_PLAN_ROW

        res = anon_client.get(_PLAN_ENDPOINT)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["plan_name"] == "pro"
        assert data["custom_odai_capacity"] == 500
        assert data["status"] == "active"

    def test_returns_free_defaults_when_no_record(self, anon_client):
        deps.db.query_one.side_effect = [
            None,  # guild_plans → not found
            {"plan_name": "free", "price": 0, "has_dashboard": 0,
             "has_discord_op": 0, "can_expand_capacity": 0, "custom_odai_max": 0},
        ]
        res = anon_client.get(_PLAN_ENDPOINT)
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["plan_name"] == "free"
        assert data["custom_odai_capacity"] == 0
        assert data["status"] == "active"

    def test_current_period_end_is_returned(self, anon_client):
        row = {**_PRO_PLAN_ROW, "current_period_end": "2026-06-09 00:00:00"}
        deps.db.query_one.return_value = row

        res = anon_client.get(_PLAN_ENDPOINT)
        assert res.json()["data"]["current_period_end"] == "2026-06-09 00:00:00"


# ─────────────────────────────────────────────────────────────
# POST /api/stripe/webhook
# ─────────────────────────────────────────────────────────────
class TestStripeWebhook:
    _url = "/api/stripe/webhook"

    def _post(self, client, event_type: str, obj: dict):
        payload = json.dumps({"type": event_type, "data": {"object": obj}}).encode()
        return client, payload

    def test_invalid_signature_returns_400(self, anon_client):
        import stripe
        with patch("OdaiBotAPI.routers.stripe.stripe") as mock_stripe:
            # except stripe.SignatureVerificationError が機能するよう実クラスを設定する
            mock_stripe.SignatureVerificationError = stripe.SignatureVerificationError
            mock_stripe.Webhook.construct_event.side_effect = \
                stripe.SignatureVerificationError("bad sig", sig_header="x")
            res = anon_client.post(self._url, content=b"{}", headers={"stripe-signature": "bad"})
        assert res.status_code == 400

    def test_checkout_completed_subscription_upserts_guild_plan(self, anon_client):
        session = {
            "metadata": {"guild_id": str(GUILD_ID), "plan": "pro", "type": "subscription"},
            "customer": "cus_xxx",
            "subscription": "sub_xxx",
        }
        deps.db.query_one.side_effect = [
            {"id": 1, "name": "pro", "price": 960, "custom_odai_base": 500,
             "custom_odai_max": None, "can_expand_capacity": 1,
             "has_dashboard": 1, "has_discord_op": 1, "stripe_price_id": "price_xxx"},
            None,  # existing guild_plan check → not found → INSERT
        ]
        deps.db.execute.return_value = make_cursor()

        with patch("OdaiBotAPI.routers.stripe.stripe") as mock_stripe:
            mock_stripe.Webhook.construct_event.return_value = {
                "type": "checkout.session.completed",
                "data": {"object": session},
            }
            res = anon_client.post(self._url, content=b"{}", headers={"stripe-signature": "ok"})
        assert res.status_code == 200
        assert res.json() == {"status": "ok"}

    def test_checkout_completed_expand_increments_capacity(self, anon_client):
        session = {
            "metadata": {"guild_id": str(GUILD_ID), "type": "expand", "units": "2"},
        }
        deps.db.execute.return_value = make_cursor()

        with patch("OdaiBotAPI.routers.stripe.stripe") as mock_stripe:
            mock_stripe.Webhook.construct_event.return_value = {
                "type": "checkout.session.completed",
                "data": {"object": session},
            }
            res = anon_client.post(self._url, content=b"{}", headers={"stripe-signature": "ok"})
        assert res.status_code == 200
        # custom_odai_capacity += 2 * 100 = 200 の UPDATE が呼ばれることを確認
        call_args = deps.db.execute.call_args
        assert "custom_odai_capacity" in call_args[0][0]
        assert 200 in call_args[0][1]

    def test_subscription_updated_updates_status(self, anon_client):
        subscription = {"id": "sub_xxx", "status": "past_due", "current_period_end": 1800000000}
        deps.db.execute.return_value = make_cursor()

        with patch("OdaiBotAPI.routers.stripe.stripe") as mock_stripe:
            mock_stripe.Webhook.construct_event.return_value = {
                "type": "customer.subscription.updated",
                "data": {"object": subscription},
            }
            res = anon_client.post(self._url, content=b"{}", headers={"stripe-signature": "ok"})
        assert res.status_code == 200
        call_args = deps.db.execute.call_args[0]
        assert "past_due" in call_args[1]

    def test_subscription_deleted_downgrades_to_free(self, anon_client):
        subscription = {"id": "sub_xxx"}
        deps.db.query_one.side_effect = [
            {"guild_id": GUILD_ID},              # guild_plans WHERE stripe_subscription_id
            {"id": 5, "custom_odai_base": 10},   # plans WHERE name='free'
        ]
        deps.db.execute.return_value = make_cursor()

        with patch("OdaiBotAPI.routers.stripe.stripe") as mock_stripe:
            mock_stripe.Webhook.construct_event.return_value = {
                "type": "customer.subscription.deleted",
                "data": {"object": subscription},
            }
            res = anon_client.post(self._url, content=b"{}", headers={"stripe-signature": "ok"})
        assert res.status_code == 200
        call_sql    = deps.db.execute.call_args[0][0]
        call_params = deps.db.execute.call_args[0][1]
        assert "active" in call_sql    # SQL に status='active' が含まれる
        assert 5 in call_params        # free plan の id がセットされる
        assert 10 in call_params       # custom_odai_capacity = 10

    def test_subscription_deleted_noop_when_guild_not_found(self, anon_client):
        subscription = {"id": "sub_unknown"}
        deps.db.query_one.return_value = None  # guild not found

        with patch("OdaiBotAPI.routers.stripe.stripe") as mock_stripe:
            mock_stripe.Webhook.construct_event.return_value = {
                "type": "customer.subscription.deleted",
                "data": {"object": subscription},
            }
            res = anon_client.post(self._url, content=b"{}", headers={"stripe-signature": "ok"})
        assert res.status_code == 200
        deps.db.execute.assert_not_called()

    def test_unknown_event_type_returns_200(self, anon_client):
        with patch("OdaiBotAPI.routers.stripe.stripe") as mock_stripe:
            mock_stripe.Webhook.construct_event.return_value = {
                "type": "payment_intent.created",
                "data": {"object": {}},
            }
            res = anon_client.post(self._url, content=b"{}", headers={"stripe-signature": "ok"})
        assert res.status_code == 200

    def test_checkout_completed_missing_guild_id_is_noop(self, anon_client):
        session = {"metadata": {"plan": "pro", "type": "subscription"}}  # guild_id なし

        with patch("OdaiBotAPI.routers.stripe.stripe") as mock_stripe:
            mock_stripe.Webhook.construct_event.return_value = {
                "type": "checkout.session.completed",
                "data": {"object": session},
            }
            res = anon_client.post(self._url, content=b"{}", headers={"stripe-signature": "ok"})
        assert res.status_code == 200
        deps.db.execute.assert_not_called()


# ─────────────────────────────────────────────────────────────
# POST /api/stripe/checkout
# ─────────────────────────────────────────────────────────────
class TestCreateCheckout:
    _url = "/api/stripe/checkout"

    def _payload(self):
        return {
            "guild_id": GUILD_ID, "plan": "pro",
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
        }

    def test_no_bot_secret_returns_401(self, anon_client):
        with patch("OdaiBotAPI.routers.stripe._BOT_SECRET", _BOT_SECRET):
            res = anon_client.post(self._url, json=self._payload())
        assert res.status_code == 401

    def test_wrong_bot_secret_returns_401(self, anon_client):
        with patch("OdaiBotAPI.routers.stripe._BOT_SECRET", _BOT_SECRET):
            res = anon_client.post(
                self._url, json=self._payload(),
                headers={"X-Bot-Secret": "wrong_secret"},
            )
        assert res.status_code == 401

    def test_plan_not_found_returns_400(self, anon_client):
        deps.db.query_one.return_value = None
        with patch("OdaiBotAPI.routers.stripe._BOT_SECRET", _BOT_SECRET):
            res = anon_client.post(
                self._url, json=self._payload(),
                headers={"X-Bot-Secret": _BOT_SECRET},
            )
        assert res.status_code == 400

    def test_plan_without_price_id_returns_400(self, anon_client):
        deps.db.query_one.return_value = {"name": "pro", "stripe_price_id": None}
        with patch("OdaiBotAPI.routers.stripe._BOT_SECRET", _BOT_SECRET):
            res = anon_client.post(
                self._url, json=self._payload(),
                headers={"X-Bot-Secret": _BOT_SECRET},
            )
        assert res.status_code == 400

    def test_success_returns_checkout_url(self, anon_client):
        deps.db.query_one.return_value = {"name": "pro", "stripe_price_id": "price_pro123", "id": 1}
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/pay/cs_xxx"

        with patch("OdaiBotAPI.routers.stripe._BOT_SECRET", _BOT_SECRET), \
             patch("OdaiBotAPI.routers.stripe.stripe.checkout.Session.create", return_value=mock_session):
            res = anon_client.post(
                self._url, json=self._payload(),
                headers={"X-Bot-Secret": _BOT_SECRET},
            )
        assert res.status_code == 200
        assert res.json()["url"] == "https://checkout.stripe.com/pay/cs_xxx"


# ─────────────────────────────────────────────────────────────
# POST /api/stripe/expand
# ─────────────────────────────────────────────────────────────
class TestCreateExpand:
    _url = "/api/stripe/expand"

    def _payload(self, units=1):
        return {
            "guild_id": GUILD_ID, "units": units,
            "success_url": "https://example.com/success",
            "cancel_url": "https://example.com/cancel",
        }

    def test_no_bot_secret_returns_401(self, anon_client):
        with patch("OdaiBotAPI.routers.stripe._BOT_SECRET", _BOT_SECRET):
            res = anon_client.post(self._url, json=self._payload())
        assert res.status_code == 401

    def test_guild_not_found_returns_404(self, anon_client):
        deps.db.query_one.return_value = None
        with patch("OdaiBotAPI.routers.stripe._BOT_SECRET", _BOT_SECRET):
            res = anon_client.post(
                self._url, json=self._payload(),
                headers={"X-Bot-Secret": _BOT_SECRET},
            )
        assert res.status_code == 404

    def test_cannot_expand_returns_403(self, anon_client):
        deps.db.query_one.return_value = {
            "custom_odai_capacity": 100, "plan_name": "light",
            "can_expand_capacity": 0, "custom_odai_max": 1000,
        }
        with patch("OdaiBotAPI.routers.stripe._BOT_SECRET", _BOT_SECRET):
            res = anon_client.post(
                self._url, json=self._payload(),
                headers={"X-Bot-Secret": _BOT_SECRET},
            )
        assert res.status_code == 403

    def test_exceeds_max_capacity_returns_400(self, anon_client):
        deps.db.query_one.return_value = {
            "custom_odai_capacity": 950, "plan_name": "light",
            "can_expand_capacity": 1, "custom_odai_max": 1000,
        }
        with patch("OdaiBotAPI.routers.stripe._BOT_SECRET", _BOT_SECRET):
            res = anon_client.post(
                self._url, json=self._payload(units=2),  # 950 + 200 = 1150 > 1000
                headers={"X-Bot-Secret": _BOT_SECRET},
            )
        assert res.status_code == 400

    def test_success_returns_checkout_url(self, anon_client):
        deps.db.query_one.return_value = {
            "custom_odai_capacity": 100, "plan_name": "pro",
            "can_expand_capacity": 1, "custom_odai_max": None,
        }
        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/pay/cs_yyy"

        with patch("OdaiBotAPI.routers.stripe._BOT_SECRET", _BOT_SECRET), \
             patch("OdaiBotAPI.routers.stripe.stripe.checkout.Session.create", return_value=mock_session):
            res = anon_client.post(
                self._url, json=self._payload(units=3),
                headers={"X-Bot-Secret": _BOT_SECRET},
            )
        assert res.status_code == 200
        assert res.json()["url"] == "https://checkout.stripe.com/pay/cs_yyy"
