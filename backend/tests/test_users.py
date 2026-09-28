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


def _attorney_payload(**overrides):
    """Scope Revision 1 §5.1 — the full required payload shape after
    legal_first_name/legal_last_name/firm_email_address were added and
    jurisdiction became a real 2-letter state code. Centralized so every
    test below only needs to override the one or two fields it cares
    about, not repeat all five every time."""
    payload = {
        "bar_no": "NY12345",
        "jurisdiction": "NY",
        "legal_first_name": "Jane",
        "legal_last_name": "Doe",
        "firm_email_address": "jane@janedoelaw.com",
    }
    payload.update(overrides)
    return payload


class TestBecomeAttorney:
    def test_citizen_becomes_pending_attorney(self, client: TestClient, session: Session):
        client.get("/api/me")
        res = client.post("/api/me/become-attorney", json=_attorney_payload())
        assert res.status_code == 200, res.text
        body = res.json()
        assert body["role"] == "attorney"
        assert body["verificationStatus"] == "pending"

        user = session.exec(select(User).where(User.auth0_sub == TEST_USER.auth0_sub)).first()
        assert user.role == Role.attorney
        assert user.verification_status == VerificationStatus.pending
        assert user.verified_bar_no == "NY12345"
        assert user.bar_jurisdiction == "NY"
        assert user.legal_first_name == "Jane"
        assert user.legal_last_name == "Doe"
        assert user.firm_email_address == "jane@janedoelaw.com"

    def test_resubmitting_while_pending_is_idempotent(self, client: TestClient):
        client.get("/api/me")
        client.post("/api/me/become-attorney", json=_attorney_payload(bar_no="NY111"))
        res = client.post(
            "/api/me/become-attorney", json=_attorney_payload(bar_no="NY222", jurisdiction="CA")
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

        res = client.post("/api/me/become-attorney", json=_attorney_payload(bar_no="NY999"))
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

        res = client.post("/api/me/become-attorney", json=_attorney_payload(bar_no="NY999"))
        assert res.status_code == 200, res.text
        assert res.json()["verificationStatus"] == "pending"

        session.refresh(user)
        assert user.verification_status == VerificationStatus.pending
        assert user.verified_bar_no == "NY999"

    def test_empty_jurisdiction_returns_validation_error(self, client: TestClient):
        client.get("/api/me")
        res = client.post(
            "/api/me/become-attorney", json=_attorney_payload(jurisdiction="")
        )
        assert res.status_code == 422

    def test_invalid_jurisdiction_code_is_rejected(self, client: TestClient):
        """Scope Revision 1 §5.1 — jurisdiction must be a real 2-letter
        state code now, not arbitrary free text."""
        client.get("/api/me")
        res = client.post(
            "/api/me/become-attorney", json=_attorney_payload(jurisdiction="New York")
        )
        assert res.status_code == 400
        assert res.json()["error"] == "invalid_jurisdiction"

    def test_jurisdiction_is_case_and_whitespace_normalized(self, client: TestClient, session: Session):
        client.get("/api/me")
        res = client.post(
            "/api/me/become-attorney", json=_attorney_payload(jurisdiction=" ny ")
        )
        assert res.status_code == 200, res.text
        user = session.exec(select(User).where(User.auth0_sub == TEST_USER.auth0_sub)).first()
        assert user.bar_jurisdiction == "NY"

    def test_bar_no_is_case_and_whitespace_normalized(self, client: TestClient, session: Session):
        """Bug-hunt item #7 (AgentGuide/newscoperev1.md Testing Strategy) —
        the composite unique constraint on (bar_no, jurisdiction) would
        otherwise let a differently-cased/padded duplicate slip through
        (e.g. " ny1234567 " vs "NY1234567" comparing as distinct)."""
        client.get("/api/me")
        res = client.post(
            "/api/me/become-attorney", json=_attorney_payload(bar_no=" ny1234567 ")
        )
        assert res.status_code == 200, res.text
        user = session.exec(select(User).where(User.auth0_sub == TEST_USER.auth0_sub)).first()
        assert user.verified_bar_no == "NY1234567"

    def test_differently_cased_padded_duplicate_bar_no_is_still_caught(
        self, client: TestClient, session: Session
    ):
        """Bug-hunt item #7 — the actual attack/edge case: two accounts
        submitting what LOOKS like different input but normalizes to the
        same real bar number must both hit the duplicate check, not just
        an exact-string match."""
        client.get("/api/me")
        first = client.post(
            "/api/me/become-attorney",
            json=_attorney_payload(bar_no="NY7654321", jurisdiction="NY"),
        )
        assert first.status_code == 200, first.text

        from app.core.security import get_current_user, get_optional_user, AuthenticatedUser
        from app.main import app

        session.add(User(auth0_sub="auth0|bug-hunt-7", email="bughunt7@example.com"))
        session.commit()
        second_identity = AuthenticatedUser(auth0_sub="auth0|bug-hunt-7", email="bughunt7@example.com")
        app.dependency_overrides[get_current_user] = lambda: second_identity
        app.dependency_overrides[get_optional_user] = lambda: second_identity
        try:
            # Same real bar number, disguised with padding + lowercase —
            # must still be caught as the same duplicate.
            res = client.post(
                "/api/me/become-attorney",
                json=_attorney_payload(
                    bar_no=" ny7654321 ", jurisdiction="ny", firm_email_address="second@lawfirmseven.com"
                ),
            )
        finally:
            app.dependency_overrides[get_current_user] = lambda: TEST_USER
            app.dependency_overrides[get_optional_user] = lambda: TEST_USER

        assert res.status_code == 400, res.text
        assert res.json()["error"] == "duplicate_bar_registration"

    def test_generic_email_domain_is_rejected(self, client: TestClient):
        """Scope Revision 1 §5.2 — client's own wording: "strictly
        blocking generic gmail.com or yahoo.com addresses for paid
        accounts." Enforced server-side, not just in the frontend form."""
        client.get("/api/me")
        res = client.post(
            "/api/me/become-attorney",
            json=_attorney_payload(firm_email_address="jane.doe@gmail.com"),
        )
        assert res.status_code == 400
        assert res.json()["error"] == "generic_email_domain"

    def test_real_firm_email_domain_is_accepted(self, client: TestClient):
        client.get("/api/me")
        res = client.post(
            "/api/me/become-attorney",
            json=_attorney_payload(firm_email_address="jane@smithlawfirm.com"),
        )
        assert res.status_code == 200, res.text

    def test_no_firm_website_produces_no_warning(self, client: TestClient):
        """Scope Revision 1 §5.5 — the client's own wording is conditional
        ("if provided"), so omitting the website entirely must not warn."""
        client.get("/api/me")
        res = client.post("/api/me/become-attorney", json=_attorney_payload())
        assert res.status_code == 200, res.text
        assert res.json()["domainMismatchWarning"] is None

    def test_matching_firm_website_produces_no_warning(self, client: TestClient):
        client.get("/api/me")
        res = client.post(
            "/api/me/become-attorney",
            json=_attorney_payload(
                firm_email_address="jane@janedoelawfirm.com",
                firm_website="https://www.janedoelawfirm.com",
            ),
        )
        assert res.status_code == 200, res.text
        assert res.json()["domainMismatchWarning"] is None

    def test_mismatched_firm_website_produces_a_warning_not_a_block(
        self, client: TestClient, session: Session
    ):
        """Client's own wording: "Ensure their firm_email_address matches
        their professional website domain if provided" — a real firm can
        legitimately use a different domain for email vs. website, so this
        must be a non-blocking warning, not a rejection."""
        client.get("/api/me")
        res = client.post(
            "/api/me/become-attorney",
            json=_attorney_payload(
                firm_email_address="jane@janedoelawfirm.com",
                firm_website="https://www.adifferentdomain.com",
            ),
        )
        assert res.status_code == 200, res.text  # not a block
        assert res.json()["domainMismatchWarning"] is not None

        user = session.exec(select(User).where(User.auth0_sub == TEST_USER.auth0_sub)).first()
        assert user.firm_website == "https://www.adifferentdomain.com"

    def test_duplicate_bar_number_same_jurisdiction_is_rejected(
        self, client: TestClient, session: Session
    ):
        """Scope Revision 1 §5.3 — a real bar number is only unique
        within its own state's numbering scheme, so the same number under
        the SAME jurisdiction must be rejected for a second account."""
        client.get("/api/me")
        client.post(
            "/api/me/become-attorney",
            json=_attorney_payload(bar_no="DUP123", jurisdiction="NY"),
        )

        # Simulate a second, different account attempting the same bar
        # number + jurisdiction — create a second citizen row directly
        # rather than juggling a second TestClient auth context, since
        # become_attorney's own _get_or_create_user only cares about the
        # session's user row, not a second real login.
        session.add(User(auth0_sub="auth0|second-attorney-test", email="second@example.com"))
        session.commit()

        from app.core.security import get_current_user, get_optional_user, AuthenticatedUser
        from app.main import app

        second_identity = AuthenticatedUser(
            auth0_sub="auth0|second-attorney-test", email="second@example.com"
        )
        app.dependency_overrides[get_current_user] = lambda: second_identity
        app.dependency_overrides[get_optional_user] = lambda: second_identity
        try:
            res = client.post(
                "/api/me/become-attorney",
                json=_attorney_payload(bar_no="DUP123", jurisdiction="NY", firm_email_address="second@lawfirmtwo.com"),
            )
        finally:
            app.dependency_overrides[get_current_user] = lambda: TEST_USER
            app.dependency_overrides[get_optional_user] = lambda: TEST_USER

        assert res.status_code == 400, res.text
        assert res.json()["error"] == "duplicate_bar_registration"

    def test_same_bar_number_different_jurisdiction_is_allowed(
        self, client: TestClient, session: Session
    ):
        """Scope Revision 1 §5.3 — legitimately NOT a duplicate, since bar
        numbers are only unique within one state's own scheme."""
        client.get("/api/me")
        res1 = client.post(
            "/api/me/become-attorney",
            json=_attorney_payload(bar_no="SHARED1", jurisdiction="NY"),
        )
        assert res1.status_code == 200, res1.text

        session.add(User(auth0_sub="auth0|third-attorney-test", email="third@example.com"))
        session.commit()

        from app.core.security import get_current_user, get_optional_user, AuthenticatedUser
        from app.main import app

        third_identity = AuthenticatedUser(
            auth0_sub="auth0|third-attorney-test", email="third@example.com"
        )
        app.dependency_overrides[get_current_user] = lambda: third_identity
        app.dependency_overrides[get_optional_user] = lambda: third_identity
        try:
            res2 = client.post(
                "/api/me/become-attorney",
                json=_attorney_payload(bar_no="SHARED1", jurisdiction="CA", firm_email_address="third@lawfirmthree.com"),
            )
        finally:
            app.dependency_overrides[get_current_user] = lambda: TEST_USER
            app.dependency_overrides[get_optional_user] = lambda: TEST_USER

        assert res2.status_code == 200, res2.text
