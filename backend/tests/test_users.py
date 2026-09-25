"""Tests for GET /api/me — forum rebuild, Milestone 2 Step M2.1
(WhyPoliceForum_MasterGuide.md): extends this existing endpoint with
role/verificationStatus so the frontend's useUser() hook can check them
on the same request as the rest of the profile.
"""

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.models.user import Role, User, VerificationStatus
from tests.conftest import TEST_USER


class TestMeRoleFields:
    def test_default_new_user_is_citizen_with_null_verification(self, client: TestClient):
        res = client.get("/api/me")
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["role"] == "citizen"
        assert body["verificationStatus"] is None

    def test_pending_attorney_reflects_in_response(self, client: TestClient, session: Session):
        client.get("/api/me")
        user = session.exec(select(User).where(User.auth0_sub == TEST_USER.auth0_sub)).first()
        user.role = Role.attorney
        user.verification_status = VerificationStatus.pending
        session.add(user)
        session.commit()

        res = client.get("/api/me")
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["role"] == "attorney"
        assert body["verificationStatus"] == "pending"

    def test_approved_attorney_reflects_in_response(self, client: TestClient, session: Session):
        client.get("/api/me")
        user = session.exec(select(User).where(User.auth0_sub == TEST_USER.auth0_sub)).first()
        user.role = Role.attorney
        user.verification_status = VerificationStatus.approved
        session.add(user)
        session.commit()

        res = client.get("/api/me")
        assert res.status_code == 200, res.text
        assert res.json()["verificationStatus"] == "approved"


class TestBecomeAttorney:
    def test_citizen_becomes_pending_attorney(self, client: TestClient, session: Session):
        client.get("/api/me")
        res = client.post(
            "/api/me/become-attorney", json={"bar_no": "NY12345", "jurisdiction": "New York"}
        )
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["role"] == "attorney"
        assert body["verificationStatus"] == "pending"

        user = session.exec(select(User).where(User.auth0_sub == TEST_USER.auth0_sub)).first()
        assert user.role == Role.attorney
        assert user.verification_status == VerificationStatus.pending
        assert user.verified_bar_no == "NY12345"
        assert user.bar_jurisdiction == "New York"

    def test_resubmitting_while_pending_is_idempotent(self, client: TestClient):
        client.get("/api/me")
        client.post("/api/me/become-attorney", json={"bar_no": "NY111", "jurisdiction": "New York"})
        res = client.post(
            "/api/me/become-attorney", json={"bar_no": "NY222", "jurisdiction": "California"}
        )
        assert res.status_code == 200, res.text
        assert res.json()["verificationStatus"] == "pending"

    def test_reapplying_after_approval_is_rejected(self, client: TestClient, session: Session):
        client.get("/api/me")
        user = session.exec(select(User).where(User.auth0_sub == TEST_USER.auth0_sub)).first()
        user.role = Role.attorney
        user.verification_status = VerificationStatus.approved
        session.add(user)
        session.commit()

        res = client.post(
            "/api/me/become-attorney", json={"bar_no": "NY999", "jurisdiction": "New York"}
        )
        assert res.status_code == 400
        assert res.json()["error"] == "already_decided"

    def test_reapplying_after_approval_is_rejected(self, client: TestClient, session: Session):
        client.get("/api/me")
        user = session.exec(select(User).where(User.auth0_sub == TEST_USER.auth0_sub)).first()
        user.role = Role.attorney
        user.verification_status = VerificationStatus.approved
        session.add(user)
        session.commit()

        res = client.post(
            "/api/me/become-attorney", json={"bar_no": "NY999", "jurisdiction": "New York"}
        )
        assert res.status_code == 400
        assert res.json()["error"] == "already_decided"

    def test_reapplying_after_rejection_is_allowed(self, client: TestClient, session: Session):
        """Real gap found during a full-scope re-audit: a rejected
        attorney had no path back at all — flagged as an open product
        question in the build guide and never resolved. Resubmitting
        must move the account back to pending for a real admin to
        re-review, not stay permanently rejected."""
        client.get("/api/me")
        user = session.exec(select(User).where(User.auth0_sub == TEST_USER.auth0_sub)).first()
        user.role = Role.attorney
        user.verification_status = VerificationStatus.rejected
        session.add(user)
        session.commit()

        res = client.post(
            "/api/me/become-attorney", json={"bar_no": "NY999", "jurisdiction": "New York"}
        )
        assert res.status_code == 200, res.text
        assert res.json()["verificationStatus"] == "pending"

        session.refresh(user)
        assert user.verification_status == VerificationStatus.pending
        assert user.verified_bar_no == "NY999"

    def test_empty_jurisdiction_returns_validation_error(self, client: TestClient):
        client.get("/api/me")
        res = client.post("/api/me/become-attorney", json={"bar_no": "NY123", "jurisdiction": ""})
        assert res.status_code == 422
