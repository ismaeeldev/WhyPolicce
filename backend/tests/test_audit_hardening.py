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
