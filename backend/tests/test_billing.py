"""Stripe billing scaffold tests — AgentGuide Step 7.

Runs fully offline: Stripe SDK calls are mocked, no real keys needed.
Verifies the honest not-configured / already-pro / success paths the
client will wire up at deploy time.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.user import Tier, User


class TestCreateCheckoutSession:
    def test_requires_auth(self):
        with TestClient(app) as anon_client:
            res = anon_client.post("/api/billing/create-checkout-session")
        assert res.status_code == 401
        assert res.json()["error"] == "unauthorized"

    def test_returns_501_when_stripe_not_configured(self, client: TestClient):
        res = client.post("/api/billing/create-checkout-session")
        assert res.status_code == 501
        body = res.json()
        assert body["error"] == "not_implemented"
        assert "isn't fully set up" in body["message"]

    def test_returns_400_when_already_pro(self, client: TestClient, pro_user: User):
        res = client.post("/api/billing/create-checkout-session")
        assert res.status_code == 400
        body = res.json()
        assert body["error"] == "already_pro"

    def test_returns_checkout_url_when_configured(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr("app.routers.billing.settings.STRIPE_SECRET_KEY", "sk_test_fake")
        monkeypatch.setattr("app.routers.billing.settings.STRIPE_PRICE_ID", "price_test_fake")
        monkeypatch.setattr("app.routers.billing.settings.FRONTEND_URL", "http://localhost:3000")

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/test_session"

        with patch(
            "app.routers.billing.stripe.checkout.Session.create",
            return_value=mock_session,
        ) as create_mock:
            res = client.post("/api/billing/create-checkout-session")

        assert res.status_code == 200
        assert res.json()["checkoutUrl"] == "https://checkout.stripe.com/test_session"
        create_mock.assert_called_once()
        call_kwargs = create_mock.call_args.kwargs
        assert call_kwargs["mode"] == "subscription"
        assert call_kwargs["line_items"] == [{"price": "price_test_fake", "quantity": 1}]
        assert call_kwargs["success_url"] == "http://localhost:3000/account?upgraded=1"
        assert call_kwargs["cancel_url"] == "http://localhost:3000/upgrade"

    def test_returns_502_on_stripe_api_error(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ):
        import stripe

        monkeypatch.setattr("app.routers.billing.settings.STRIPE_SECRET_KEY", "sk_test_fake")
        monkeypatch.setattr("app.routers.billing.settings.STRIPE_PRICE_ID", "price_test_fake")

        with patch(
            "app.routers.billing.stripe.checkout.Session.create",
            side_effect=stripe.StripeError("network"),
        ):
            res = client.post("/api/billing/create-checkout-session")

        assert res.status_code == 502
        assert res.json()["error"] == "stripe_error"


class TestStripeWebhook:
    def test_accepts_payload_without_webhook_secret(self, client: TestClient):
        res = client.post(
            "/api/billing/webhook",
            json={"type": "checkout.session.completed", "data": {"object": {}}},
        )
        assert res.status_code == 200
        assert res.json() == {"received": True}

    def test_rejects_invalid_signature_when_secret_configured(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ):
        import stripe

        monkeypatch.setattr(
            "app.routers.billing.settings.STRIPE_WEBHOOK_SECRET", "whsec_test_fake"
        )

        with patch(
            "app.routers.billing.stripe.Webhook.construct_event",
            side_effect=stripe.SignatureVerificationError("bad sig", "sig_header"),
        ):
            res = client.post(
                "/api/billing/webhook",
                content=b"{}",
                headers={"stripe-signature": "bad"},
            )

        assert res.status_code == 400
        assert res.json()["error"] == "invalid_signature"

    def test_accepts_verified_webhook_event(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(
            "app.routers.billing.settings.STRIPE_WEBHOOK_SECRET", "whsec_test_fake"
        )

        with patch(
            "app.routers.billing.stripe.Webhook.construct_event",
            return_value={"type": "checkout.session.completed"},
        ):
            res = client.post(
                "/api/billing/webhook",
                content=b"{}",
                headers={"stripe-signature": "valid"},
            )

        assert res.status_code == 200
        assert res.json() == {"received": True}

    def test_rejects_malformed_payload_without_secret(self, client: TestClient):
        res = client.post(
            "/api/billing/webhook",
            content=b"not-json",
            headers={"content-type": "application/json"},
        )
        assert res.status_code == 400
        assert res.json()["error"] == "invalid_payload"


class TestBillingAuthBoundary:
    def test_webhook_has_no_jwt_requirement(self):
        """Stripe calls the webhook directly — must not require Bearer auth."""
        with TestClient(app) as anon_client:
            res = anon_client.post(
                "/api/billing/webhook",
                json={"type": "ping"},
            )
        assert res.status_code == 200

    def test_checkout_requires_jwt_even_when_stripe_configured(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr("app.routers.billing.settings.STRIPE_SECRET_KEY", "sk_test_fake")
        monkeypatch.setattr("app.routers.billing.settings.STRIPE_PRICE_ID", "price_test_fake")

        with TestClient(app) as anon_client:
            res = anon_client.post("/api/billing/create-checkout-session")
        assert res.status_code == 401


class TestStripeWebhookTierUpdates:
    def test_checkout_completed_upgrades_user(self, client: TestClient, session):
        user = User(auth0_sub="auth0|stripe-upgrade", email="stripe@test.example", tier=Tier.free)
        session.add(user)
        session.commit()
        session.refresh(user)

        payload = {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "client_reference_id": str(user.id),
                    "customer": "cus_test_123",
                }
            },
        }
        res = client.post("/api/billing/webhook", json=payload)
        assert res.status_code == 200

        session.refresh(user)
        assert user.tier == Tier.pro
        assert user.stripe_customer_id == "cus_test_123"

    def test_subscription_deleted_downgrades_user(self, client: TestClient, session):
        user = User(
            auth0_sub="auth0|stripe-downgrade",
            email="downgrade@test.example",
            tier=Tier.pro,
            stripe_customer_id="cus_test_456",
        )
        session.add(user)
        session.commit()
        session.refresh(user)

        payload = {
            "type": "customer.subscription.deleted",
            "data": {"object": {"customer": "cus_test_456"}},
        }
        res = client.post("/api/billing/webhook", json=payload)
        assert res.status_code == 200

        session.refresh(user)
        assert user.tier == Tier.free

    def test_checkout_completed_upgrades_user_via_real_stripe_object(
        self, client: TestClient, session, monkeypatch: pytest.MonkeyPatch
    ):
        """Regression test for a real bug found during Phase 4 live testing
        (revision2.md): every test above this one posts a plain JSON dict
        with no STRIPE_WEBHOOK_SECRET configured, which takes the
        json.loads() branch in the webhook route — that path never
        exercises _event_object()'s StripeObject-conversion branch, which
        is what a REAL Stripe webhook (signature-verified via
        stripe.Webhook.construct_event) actually returns. A real signed
        webhook against this exact code previously failed with
        AttributeError: 'str' object has no attribute 'get', because
        json.dumps(obj, default=str) on a StripeObject serializes its
        pretty-printed repr as one big string, not its fields — fixed by
        using StripeObject.to_dict() instead. This test constructs a real
        stripe.Event via construct_event (not a mock) so the fix (and any
        future regression) is actually exercised, not bypassed."""
        import hashlib
        import hmac
        import json
        import time

        import stripe

        webhook_secret = "whsec_test_regression"
        monkeypatch.setattr(
            "app.routers.billing.settings.STRIPE_WEBHOOK_SECRET", webhook_secret
        )

        user = User(auth0_sub="auth0|stripe-real-object", email="real@test.example", tier=Tier.free)
        session.add(user)
        session.commit()
        session.refresh(user)

        payload = {
            "id": "evt_test_real_object",
            "object": "event",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_real",
                    "client_reference_id": str(user.id),
                    "customer": "cus_test_real_object",
                }
            },
        }
        payload_str = json.dumps(payload)
        timestamp = int(time.time())
        signed_payload = f"{timestamp}.{payload_str}"
        signature = hmac.new(
            webhook_secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        sig_header = f"t={timestamp},v1={signature}"

        # Sanity check: this really does produce a genuine StripeObject,
        # not a dict — otherwise this test would silently stop testing
        # what it claims to.
        real_event = stripe.Webhook.construct_event(
            payload_str.encode("utf-8"), sig_header, webhook_secret
        )
        assert not isinstance(real_event.data.object, dict)

        res = client.post(
            "/api/billing/webhook",
            content=payload_str.encode("utf-8"),
            headers={"stripe-signature": sig_header, "content-type": "application/json"},
        )
        assert res.status_code == 200

        session.refresh(user)
        assert user.tier == Tier.pro
        assert user.stripe_customer_id == "cus_test_real_object"
