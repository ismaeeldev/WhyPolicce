"""Regression tests for the security/robustness audit fixes."""
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.urlutil import normalize_website
from app.models.inquiry import Inquiry, InquiryTier, StatusTag
from app.models.user import User
from tests.conftest import TEST_USER
from tests.test_inquiries import _create_inquiry


@pytest.mark.parametrize(
    "raw,expected",
    [
        ("yourfirm.com", "https://yourfirm.com"),
        ("http://yourfirm.com/a", "http://yourfirm.com/a"),
        ("  https://www.firm.com  ", "https://www.firm.com"),
        ("localhost:8080", "https://localhost:8080"),
        ("javascript:alert(1)", None),
        ("JaVaScRiPt:alert(1)", None),
        ("data:text/html,<script>1</script>", None),
        ("ftp://firm.com", None),
        ("file:///etc/passwd", None),
        ("https://", None),
        ("has space.com", None),
        ("", None),
        (None, None),
    ],
)
def test_normalize_website(raw, expected):
    assert normalize_website(raw) == expected


def _apply(client, website):
    return client.post(
        "/api/me/become-attorney",
        json={
            "bar_no": "NY12345", "jurisdiction": "NY", "legal_first_name": "A", "legal_last_name": "B",
            "firm_email_address": "a@firm-example.com", "firm_website": website,
        },
    )


def test_become_attorney_rejects_javascript_website(client: TestClient, pro_user):
    res = _apply(client, "javascript:alert(document.cookie)")
    assert res.status_code == 400 and res.json()["error"] == "invalid_website"


def test_become_attorney_normalizes_bare_domain(client: TestClient, pro_user):
    res = _apply(client, "firm-example.com")
    assert res.status_code == 200, res.text
    assert res.json()["verificationStatus"] == "pending"


def test_public_verified_attorneys_never_return_unsafe_website(client: TestClient, session: Session):
    from app.models.user import Role, VerificationStatus

    session.add(User(auth0_sub="auth0|evil", email="e@x.test", role=Role.attorney,
                     verification_status=VerificationStatus.approved, legal_first_name="E", legal_last_name="V",
                     firm_website="javascript:alert(1)"))
    session.commit()
    items = client.get("/api/v1/attorneys/verified").json()["items"]
    assert items and all(i["firmWebsite"] is None for i in items)


def test_search_treats_percent_and_underscore_literally(client: TestClient):
    _create_inquiry(client, title="Plain title")
    assert client.get("/api/v1/inquiries", params={"q": "%"}).json()["total"] == 0
    assert client.get("/api/v1/inquiries", params={"q": "_"}).json()["total"] == 0
    assert client.get("/api/v1/inquiries", params={"q": "Plain"}).json()["total"] == 1


def test_thread_of_unpaid_draft_hidden_from_non_authors(client: TestClient, session: Session):
    author = User(auth0_sub="auth0|someone-else", email="o@x.test")
    session.add(author); session.commit(); session.refresh(author)
    draft = Inquiry(author_id=author.id, title="d", description="x" * 300, state="NY", city="NYC",
                    status_tag=StatusTag.community_trace, tier=InquiryTier.pending_payment)
    session.add(draft); session.commit(); session.refresh(draft)
    assert client.get(f"/api/v1/inquiries/{draft.id}/thread").status_code == 404
    assert client.get(f"/api/v1/inquiries/{draft.id}").status_code == 404


def test_upgrade_checkout_refuses_already_expanded_inquiry(client: TestClient, session: Session, pro_user):
    created = _create_inquiry(client).json()
    row = session.get(Inquiry, uuid.UUID(created["id"]))
    row.tier = InquiryTier.expanded
    session.add(row); session.commit()
    res = client.post("/api/v1/billing/checkout/inquiry-upgrade", json={"inquiry_id": created["id"]})
    assert res.status_code == 409 and res.json()["error"] == "already_upgraded"


def test_auth_error_does_not_leak_library_details():
    from app.core.security import AuthError  # noqa: F401  (import must keep working)
    import inspect
    from app.core import security

    assert "Token verification failed: {exc}" not in inspect.getsource(security)


# ---- second hardening round -------------------------------------------------

def test_comments_never_expose_author_id_only_is_author(client: TestClient):
    created = _create_inquiry(client).json()
    posted = client.post(f"/api/v1/inquiries/{created['id']}/thread", json={"body": "hello"}).json()
    assert "authorId" not in posted and posted["isAuthor"] is True
    listed = client.get(f"/api/v1/inquiries/{created['id']}/thread").json()["items"][0]
    assert "authorId" not in listed and listed["isAuthor"] is True


def _foreign_draft(session):
    other = User(auth0_sub="auth0|draft-owner", email="d@x.test")
    session.add(other); session.commit(); session.refresh(other)
    draft = Inquiry(author_id=other.id, title="d", description="x" * 300, state="NY", city="NYC",
                    status_tag=StatusTag.community_trace, tier=InquiryTier.pending_payment)
    session.add(draft); session.commit(); session.refresh(draft)
    return draft


def test_every_action_on_someone_elses_unpaid_draft_is_404(client: TestClient, session: Session):
    draft = _foreign_draft(session)
    assert client.post(f"/api/v1/inquiries/{draft.id}/thread", json={"body": "hi"}).status_code == 404
    assert client.post(f"/api/v1/inquiries/{draft.id}/follow").status_code == 404
    assert client.post("/api/v1/reports", json={"target_type": "inquiry", "target_id": str(draft.id), "reason": "x"}).status_code == 404


def test_duplicate_open_report_returns_existing(client: TestClient):
    created = _create_inquiry(client).json()
    body = {"target_type": "inquiry", "target_id": created["id"], "reason": "spam"}
    a = client.post("/api/v1/reports", json=body).json()
    b = client.post("/api/v1/reports", json=body).json()
    assert a["id"] == b["id"]


def test_upload_url_rejects_unsupported_content_type(client: TestClient):
    from unittest.mock import patch

    created = _create_inquiry(client).json()
    with patch("app.routers.media.media_service.is_configured", return_value=True):
        res = client.post("/api/v1/media/upload-url", json={
            "inquiry_id": created["id"], "file_type": "image", "size_bytes": 10, "content_type": "application/x-msdownload"})
    assert res.status_code == 422 and res.json()["error"] == "invalid_content_type"


def _signed_token_and_jwks(audience):
    import base64
    import time

    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from jose import jwt

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    nums = key.public_key().public_numbers()
    b64 = lambda i: base64.urlsafe_b64encode(i.to_bytes((i.bit_length() + 7) // 8, "big")).rstrip(b"=").decode()
    jwks = {"keys": [{"kty": "RSA", "kid": "k1", "use": "sig", "n": b64(nums.n), "e": b64(nums.e)}]}
    claims = {"sub": "auth0|tok", "iss": "https://test.auth0.com/", "aud": audience, "exp": int(time.time()) + 600}
    return jwt.encode(claims, pem, algorithm="RS256", headers={"kid": "k1"}), jwks


def test_tokens_rejected_when_audience_not_configured(monkeypatch):
    from app.core import security

    token, jwks = _signed_token_and_jwks("https://test-api")
    monkeypatch.setattr(security, "_get_jwks", lambda force_refresh=False: jwks)
    monkeypatch.setattr(security.settings, "AUTH0_DOMAIN", "test.auth0.com")

    monkeypatch.setattr(security.settings, "AUTH0_AUDIENCE", "https://test-api")
    assert security.verify_token(token).auth0_sub == "auth0|tok"

    monkeypatch.setattr(security.settings, "AUTH0_AUDIENCE", "")
    with pytest.raises(security.AuthError, match="not configured"):
        security.verify_token(token)

    monkeypatch.setattr(security.settings, "AUTH0_AUDIENCE", "https://some-other-api")
    with pytest.raises(security.AuthError):
        security.verify_token(token)
