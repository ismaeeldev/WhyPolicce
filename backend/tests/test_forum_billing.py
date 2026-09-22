"""Tests for app/routers/forum_billing.py — forum rebuild, Milestone 3
Step M3.2 (WhyPoliceForum_MasterGuide.md).

No real (brand-new) Stripe account/keys exist in this environment yet
(Manual Step still pending on the client) — mirrors tests/test_billing.py's
own established approach: (1) confirm the real, honest 501 in the actual
unconfigured state, (2) mock only stripe.checkout.Session.create for the
checkout-creation paths, and (3) construct REAL stripe.Event objects via
stripe.Webhook.construct_event for the webhook tests (not plain JSON
dicts) — the same real-object-vs-mock distinction that caught a genuine
bug in the old product's billing.py (see that file's test suite for the
regression story), so this new router's webhook handling is exercised
against the same real code path a live Stripe delivery would hit.
"""

import hashlib
import hmac
import json
import time
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.inquiry import InquiryTier
from app.models.user import Role, User, VerificationStatus
from tests.test_inquiries import _create_inquiry


def _sign(secret: str, payload_str: str) -> str:
    timestamp = int(time.time())
    signed_payload = f"{timestamp}.{payload_str}"
    signature = hmac.new(secret.encode("utf-8"), signed_payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"t={timestamp},v1={signature}"


class TestInquiryUpgradeCheckout:
    def test_requires_auth(self):
        with TestClient(app) as anon_client:
            res = anon_client.post("/api/v1/billing/checkout/inquiry-upgrade", json={"inquiry_id": str(uuid.uuid4())})
        assert res.status_code == 401

    def test_returns_501_when_not_configured(self, client: TestClient):
        created = _create_inquiry(client).json()
        res = client.post("/api/v1/billing/checkout/inquiry-upgrade", json={"inquiry_id": created["id"]})
        assert res.status_code == 501
        assert res.json()["error"] == "not_implemented"

    def test_nonexistent_inquiry_404s(self, client: TestClient):
        res = client.post("/api/v1/billing/checkout/inquiry-upgrade", json={"inquiry_id": str(uuid.uuid4())})
        assert res.status_code == 404

    def test_non_owner_cannot_checkout_for_someone_elses_inquiry(self, client: TestClient, session):
        from tests.test_inquiries import _second_user_client

        created = _create_inquiry(client).json()
        other_client = _second_user_client(session)
        res = other_client.post("/api/v1/billing/checkout/inquiry-upgrade", json={"inquiry_id": created["id"]})
        assert res.status_code == 403
        app.dependency_overrides.clear()

    def test_owner_gets_real_checkout_url_when_configured(self, client: TestClient, monkeypatch: pytest.MonkeyPatch):
        created = _create_inquiry(client).json()
        monkeypatch.setattr("app.routers.forum_billing.settings.FORUM_STRIPE_SECRET_KEY", "sk_test_fake")
        monkeypatch.setattr("app.routers.forum_billing.settings.FORUM_STRIPE_INQUIRY_UPGRADE_PRICE_ID", "price_fake")

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/fake-session"
        with patch("app.routers.forum_billing.stripe.checkout.Session.create", return_value=mock_session) as mock_create:
            res = client.post("/api/v1/billing/checkout/inquiry-upgrade", json={"inquiry_id": created["id"]})
        assert res.status_code == 200, res.text
        assert res.json()["checkoutUrl"] == "https://checkout.stripe.com/fake-session"
        # Real requirement: metadata must link back to this exact inquiry so
        # the webhook can act on the right record.
        _, kwargs = mock_create.call_args
        assert kwargs["metadata"]["inquiry_id"] == created["id"]
        assert kwargs["mode"] == "payment"


class TestAttorneySubscriptionCheckout:
    def _make_attorney(self, session, *, verification_status) -> User:
        attorney = User(
            auth0_sub=f"auth0|attorney-{verification_status}-{uuid.uuid4()}",
            email="attorney@test.example",
            role=Role.attorney,
            verification_status=verification_status,
        )
        session.add(attorney)
        session.commit()
        session.refresh(attorney)
        return attorney

    def _attorney_client(self, session, attorney: User) -> TestClient:
        from app.core.db import get_session
        from app.core.security import AuthenticatedUser, get_current_user

        identity = AuthenticatedUser(auth0_sub=attorney.auth0_sub, email=attorney.email)
        app.dependency_overrides[get_session] = lambda: (yield session)
        app.dependency_overrides[get_current_user] = lambda: identity
        return TestClient(app)

    def test_requires_auth(self):
        with TestClient(app) as anon_client:
            res = anon_client.post("/api/v1/billing/checkout/attorney-subscription")
        assert res.status_code == 401

    def test_unapproved_attorney_cannot_reach_checkout_even_directly(self, session):
        """Real M3.2 Bug Fix requirement: a still-pending attorney calling
        this endpoint directly (bypassing the UI, which would never
        normally expose this path) must still be rejected server-side."""
        attorney = self._make_attorney(session, verification_status=VerificationStatus.pending)
        attorney_client = self._attorney_client(session, attorney)
        res = attorney_client.post("/api/v1/billing/checkout/attorney-subscription")
        assert res.status_code == 403
        assert res.json()["error"] == "not_verified"
        app.dependency_overrides.clear()

    def test_citizen_cannot_reach_attorney_checkout(self, client: TestClient):
        res = client.post("/api/v1/billing/checkout/attorney-subscription")
        assert res.status_code == 403

    def test_approved_attorney_returns_501_when_not_configured(self, session):
        attorney = self._make_attorney(session, verification_status=VerificationStatus.approved)
        attorney_client = self._attorney_client(session, attorney)
        res = attorney_client.post("/api/v1/billing/checkout/attorney-subscription")
        assert res.status_code == 501
        app.dependency_overrides.clear()

    def test_approved_attorney_gets_real_checkout_url_when_configured(
        self, session, monkeypatch: pytest.MonkeyPatch
    ):
        attorney = self._make_attorney(session, verification_status=VerificationStatus.approved)
        attorney_client = self._attorney_client(session, attorney)
        monkeypatch.setattr("app.routers.forum_billing.settings.FORUM_STRIPE_SECRET_KEY", "sk_test_fake")
        monkeypatch.setattr(
            "app.routers.forum_billing.settings.FORUM_STRIPE_ATTORNEY_SUBSCRIPTION_PRICE_ID", "price_fake_sub"
        )

        mock_session = MagicMock()
        mock_session.url = "https://checkout.stripe.com/fake-attorney-session"
        with patch("app.routers.forum_billing.stripe.checkout.Session.create", return_value=mock_session) as mock_create:
            res = attorney_client.post("/api/v1/billing/checkout/attorney-subscription")
        assert res.status_code == 200, res.text
        _, kwargs = mock_create.call_args
        assert kwargs["metadata"]["user_id"] == str(attorney.id)
        assert kwargs["mode"] == "subscription"
        app.dependency_overrides.clear()


class TestForumWebhook:
    def test_returns_501_when_webhook_secret_not_configured(self, client: TestClient):
        res = client.post("/api/v1/billing/webhook", json={"type": "checkout.session.completed"})
        assert res.status_code == 501

    def test_rejects_invalid_signature(self, client: TestClient, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setattr("app.routers.forum_billing.settings.FORUM_STRIPE_WEBHOOK_SECRET", "whsec_real")
        res = client.post(
            "/api/v1/billing/webhook",
            content=b'{"type": "checkout.session.completed"}',
            headers={"stripe-signature": "bad-signature"},
        )
        assert res.status_code == 400
        assert res.json()["error"] == "invalid_signature"

    def test_real_signed_inquiry_upgrade_event_flips_tier(
        self, client: TestClient, session, monkeypatch: pytest.MonkeyPatch
    ):
        """Constructs a REAL stripe.Event (not a plain dict) via
        stripe.Webhook.construct_event, the same regression-proofing
        pattern as test_billing.py's own real-object test — a real
        checkout.session.completed webhook delivers a StripeObject, not a
        dict, and this must not silently break on that."""
        import stripe

        webhook_secret = "whsec_forum_test"
        monkeypatch.setattr("app.routers.forum_billing.settings.FORUM_STRIPE_WEBHOOK_SECRET", webhook_secret)

        created = _create_inquiry(client).json()
        assert created["tier"] == "free"

        payload = {
            "id": "evt_forum_inquiry_upgrade",
            "object": "event",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_inquiry_upgrade",
                    "customer": "cus_forum_test",
                    "metadata": {"inquiry_id": created["id"], "user_id": "irrelevant"},
                }
            },
        }
        payload_str = json.dumps(payload)
        sig_header = _sign(webhook_secret, payload_str)

        real_event = stripe.Webhook.construct_event(payload_str.encode("utf-8"), sig_header, webhook_secret)
        assert not isinstance(real_event.data.object, dict)

        res = client.post(
            "/api/v1/billing/webhook",
            content=payload_str.encode("utf-8"),
            headers={"stripe-signature": sig_header, "content-type": "application/json"},
        )
        assert res.status_code == 200

        follow_up = client.get(f"/api/v1/inquiries/{created['id']}")
        assert follow_up.json()["tier"] == "expanded"

    def test_real_signed_attorney_subscription_event_activates_flag(
        self, client: TestClient, session, monkeypatch: pytest.MonkeyPatch
    ):
        import stripe

        webhook_secret = "whsec_forum_test_2"
        monkeypatch.setattr("app.routers.forum_billing.settings.FORUM_STRIPE_WEBHOOK_SECRET", webhook_secret)

        attorney = User(
            auth0_sub="auth0|forum-sub-attorney",
            email="sub-attorney@test.example",
            role=Role.attorney,
            verification_status=VerificationStatus.approved,
        )
        session.add(attorney)
        session.commit()
        session.refresh(attorney)
        assert attorney.attorney_subscription_active is False

        payload = {
            "id": "evt_forum_attorney_sub",
            "object": "event",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_attorney_sub",
                    "customer": "cus_forum_attorney",
                    "metadata": {"user_id": str(attorney.id)},
                }
            },
        }
        payload_str = json.dumps(payload)
        sig_header = _sign(webhook_secret, payload_str)
        stripe.Webhook.construct_event(payload_str.encode("utf-8"), sig_header, webhook_secret)

        res = client.post(
            "/api/v1/billing/webhook",
            content=payload_str.encode("utf-8"),
            headers={"stripe-signature": sig_header, "content-type": "application/json"},
        )
        assert res.status_code == 200

        session.refresh(attorney)
        assert attorney.attorney_subscription_active is True
        assert attorney.forum_stripe_customer_id == "cus_forum_attorney"

    def test_subscription_deleted_relocks_attorney_portal(
        self, client: TestClient, session, monkeypatch: pytest.MonkeyPatch
    ):
        webhook_secret = "whsec_forum_test_3"
        monkeypatch.setattr("app.routers.forum_billing.settings.FORUM_STRIPE_WEBHOOK_SECRET", webhook_secret)

        attorney = User(
            auth0_sub="auth0|forum-lapsed-attorney",
            email="lapsed@test.example",
            role=Role.attorney,
            verification_status=VerificationStatus.approved,
            attorney_subscription_active=True,
            forum_stripe_customer_id="cus_forum_lapsed",
        )
        session.add(attorney)
        session.commit()

        payload = {
            "id": "evt_forum_sub_deleted",
            "object": "event",
            "type": "customer.subscription.deleted",
            "data": {"object": {"customer": "cus_forum_lapsed"}},
        }
        payload_str = json.dumps(payload)
        sig_header = _sign(webhook_secret, payload_str)

        res = client.post(
            "/api/v1/billing/webhook",
            content=payload_str.encode("utf-8"),
            headers={"stripe-signature": sig_header, "content-type": "application/json"},
        )
        assert res.status_code == 200

        session.refresh(attorney)
        assert attorney.attorney_subscription_active is False

    def test_payment_failed_relocks_attorney_portal(self, client: TestClient, session, monkeypatch: pytest.MonkeyPatch):
        webhook_secret = "whsec_forum_test_4"
        monkeypatch.setattr("app.routers.forum_billing.settings.FORUM_STRIPE_WEBHOOK_SECRET", webhook_secret)

        attorney = User(
            auth0_sub="auth0|forum-failed-attorney",
            email="failed@test.example",
            role=Role.attorney,
            verification_status=VerificationStatus.approved,
            attorney_subscription_active=True,
            forum_stripe_customer_id="cus_forum_failed",
        )
        session.add(attorney)
        session.commit()

        payload = {
            "id": "evt_forum_payment_failed",
            "object": "event",
            "type": "invoice.payment_failed",
            "data": {"object": {"customer": "cus_forum_failed"}},
        }
        payload_str = json.dumps(payload)
        sig_header = _sign(webhook_secret, payload_str)

        res = client.post(
            "/api/v1/billing/webhook",
            content=payload_str.encode("utf-8"),
            headers={"stripe-signature": sig_header, "content-type": "application/json"},
        )
        assert res.status_code == 200

        session.refresh(attorney)
        assert attorney.attorney_subscription_active is False

    def test_replayed_event_is_idempotent(self, client: TestClient, session, monkeypatch: pytest.MonkeyPatch):
        """Real M3.2 Bug Fix requirement: replaying the same webhook event
        twice must not double-process it. Confirmed here against the
        inquiry-upgrade flow specifically — tier flips once, and the
        second identical delivery is a genuine no-op (not just "still
        expanded," but detected and skipped via the event-id dedup)."""
        webhook_secret = "whsec_forum_idem"
        monkeypatch.setattr("app.routers.forum_billing.settings.FORUM_STRIPE_WEBHOOK_SECRET", webhook_secret)

        created = _create_inquiry(client).json()
        payload = {
            "id": "evt_forum_idempotency_test",
            "object": "event",
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "id": "cs_test_idem",
                    "customer": "cus_idem",
                    "metadata": {"inquiry_id": created["id"]},
                }
            },
        }
        payload_str = json.dumps(payload)
        sig_header = _sign(webhook_secret, payload_str)

        first = client.post(
            "/api/v1/billing/webhook",
            content=payload_str.encode("utf-8"),
            headers={"stripe-signature": sig_header, "content-type": "application/json"},
        )
        assert first.status_code == 200
        assert first.json().get("duplicate") is not True

        second = client.post(
            "/api/v1/billing/webhook",
            content=payload_str.encode("utf-8"),
            headers={"stripe-signature": sig_header, "content-type": "application/json"},
        )
        assert second.status_code == 200
        assert second.json()["duplicate"] is True

        # Still just "expanded," not double-processed into some broken state.
        follow_up = client.get(f"/api/v1/inquiries/{created['id']}")
        assert follow_up.json()["tier"] == "expanded"
