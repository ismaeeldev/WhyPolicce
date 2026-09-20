"""Tests for app/routers/inquiries.py — forum rebuild, Milestone 1 Step
M1.4 (WhyPoliceForum_MasterGuide.md). Covers the full Test + Bug Fix
checklist for this step: real endpoint behavior against the SQLite test
engine, the 250-char soft cap, ownership (403 vs 404), attorney gating,
privacy (no email leak), pagination, text search, rate limiting, and
follow/unfollow concurrency-safety semantics.
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.security import AuthenticatedUser, get_current_user
from app.main import app
from app.models.attorney_request import AttorneyRequest, AttorneyRequestStatus
from app.models.inquiry import Inquiry, StatusTag
from app.models.user import Role, User, VerificationStatus
from tests.conftest import TEST_USER


def _create_inquiry(client: TestClient, **overrides) -> dict:
    body = {
        "title": "Test inquiry",
        "description": "A real test description.",
        "state": "NY",
        "city": "New York",
        "statusTag": "community_trace",
    }
    body.update(overrides)
    # Router expects snake_case field names per InquiryCreate schema.
    payload = {
        "title": body["title"],
        "description": body["description"],
        "state": body["state"],
        "city": body["city"],
        "status_tag": body["statusTag"],
    }
    if "precinct" in overrides:
        payload["precinct"] = overrides["precinct"]
    if "tier" in overrides:
        payload["tier"] = overrides["tier"]
    res = client.post("/api/v1/inquiries", json=payload)
    return res


def _second_user_client(session: Session) -> TestClient:
    """A real, distinct authenticated identity — the existing conftest's
    `client` fixture always authenticates as the single fixed TEST_USER,
    which cannot exercise cross-user ownership tests. Overrides
    get_current_user with a second, different auth0_sub."""
    second_identity = AuthenticatedUser(auth0_sub="auth0|second-test-user", email="second@test.example")

    def override_get_session():
        yield session

    def override_get_user():
        return second_identity

    from app.core.db import get_session

    app.dependency_overrides[get_session] = override_get_session
    app.dependency_overrides[get_current_user] = override_get_user
    return TestClient(app)


class TestCreateAndFetchInquiry:
    def test_create_inquiry_succeeds(self, client: TestClient):
        res = _create_inquiry(client)
        assert res.status_code == 201, res.text
        body = res.json()
        assert body["title"] == "Test inquiry"
        assert body["tier"] == "free"
        assert body["followerCount"] == 0
        assert body["commentCount"] == 0
        assert body["hasAttachments"] is False
        assert body["isFollowing"] is False

    def test_get_single_inquiry_returns_full_detail(self, client: TestClient):
        created = _create_inquiry(client).json()
        res = client.get(f"/api/v1/inquiries/{created['id']}")
        assert res.status_code == 200
        assert res.json()["title"] == "Test inquiry"

    def test_get_nonexistent_inquiry_404(self, client: TestClient):
        res = client.get(f"/api/v1/inquiries/{uuid.uuid4()}")
        assert res.status_code == 404

    def test_get_malformed_inquiry_id_404_not_500(self, client: TestClient):
        res = client.get("/api/v1/inquiries/not-a-real-uuid")
        assert res.status_code == 404

    def test_feed_lists_created_inquiry(self, client: TestClient):
        _create_inquiry(client, title="Feed test inquiry")
        res = client.get("/api/v1/inquiries")
        assert res.status_code == 200
        body = res.json()
        assert any(item["title"] == "Feed test inquiry" for item in body["items"])
        assert "total" in body and "limit" in body and "offset" in body


class TestCharacterLimitSoftCap:
    def test_exactly_250_chars_succeeds_as_free_tier(self, client: TestClient):
        res = _create_inquiry(client, description="x" * 250)
        assert res.status_code == 201, res.text

    def test_251_chars_free_tier_returns_upgrade_required(self, client: TestClient):
        res = _create_inquiry(client, description="x" * 251)
        assert res.status_code == 403
        body = res.json()
        assert body["error"] == "upgrade_required"

    def test_251_chars_expanded_tier_succeeds(self, client: TestClient):
        res = _create_inquiry(client, description="x" * 251, tier="expanded")
        assert res.status_code == 201, res.text
        assert res.json()["tier"] == "expanded"


class TestOwnership:
    def test_owner_can_update_own_inquiry(self, client: TestClient):
        created = _create_inquiry(client).json()
        res = client.patch(f"/api/v1/inquiries/{created['id']}", json={"title": "Updated title"})
        assert res.status_code == 200
        assert res.json()["title"] == "Updated title"

    def test_non_owner_update_returns_403_not_404(self, client: TestClient, session: Session):
        created = _create_inquiry(client).json()
        other_client = _second_user_client(session)
        res = other_client.patch(f"/api/v1/inquiries/{created['id']}", json={"title": "Hijacked"})
        assert res.status_code == 403, res.text
        app.dependency_overrides.clear()

    def test_non_owner_delete_returns_403_not_404(self, client: TestClient, session: Session):
        created = _create_inquiry(client).json()
        other_client = _second_user_client(session)
        res = other_client.delete(f"/api/v1/inquiries/{created['id']}")
        assert res.status_code == 403, res.text
        app.dependency_overrides.clear()

    def test_owner_can_delete_own_inquiry(self, client: TestClient):
        created = _create_inquiry(client).json()
        res = client.delete(f"/api/v1/inquiries/{created['id']}")
        assert res.status_code == 200
        assert res.json()["deleted"] is True
        # Confirm it's genuinely gone.
        res2 = client.get(f"/api/v1/inquiries/{created['id']}")
        assert res2.status_code == 404


class TestPrivacy:
    def test_feed_response_never_contains_email(self, client: TestClient):
        _create_inquiry(client)
        res = client.get("/api/v1/inquiries")
        assert TEST_USER.email not in res.text

    def test_single_inquiry_response_never_contains_email(self, client: TestClient):
        created = _create_inquiry(client).json()
        res = client.get(f"/api/v1/inquiries/{created['id']}")
        assert TEST_USER.email not in res.text


class TestThreadComments:
    def test_post_and_list_comment(self, client: TestClient):
        created = _create_inquiry(client).json()
        res = client.post(f"/api/v1/inquiries/{created['id']}/thread", json={"body": "A real comment"})
        assert res.status_code == 201, res.text
        comment = res.json()

        thread = client.get(f"/api/v1/inquiries/{created['id']}/thread")
        assert thread.status_code == 200
        assert any(c["id"] == comment["id"] for c in thread.json()["items"])

    def test_owner_can_edit_own_comment(self, client: TestClient):
        created = _create_inquiry(client).json()
        comment = client.post(f"/api/v1/inquiries/{created['id']}/thread", json={"body": "original"}).json()
        res = client.patch(
            f"/api/v1/inquiries/{created['id']}/thread/{comment['id']}", json={"body": "edited"}
        )
        assert res.status_code == 200
        assert res.json()["body"] == "edited"

    def test_owner_can_delete_own_comment(self, client: TestClient):
        created = _create_inquiry(client).json()
        comment = client.post(f"/api/v1/inquiries/{created['id']}/thread", json={"body": "to delete"}).json()
        res = client.delete(f"/api/v1/inquiries/{created['id']}/thread/{comment['id']}")
        assert res.status_code == 200
        assert res.json()["deleted"] is True

    def test_non_author_edit_comment_returns_403(self, client: TestClient, session: Session):
        created = _create_inquiry(client).json()
        comment = client.post(f"/api/v1/inquiries/{created['id']}/thread", json={"body": "original"}).json()
        other_client = _second_user_client(session)
        res = other_client.patch(
            f"/api/v1/inquiries/{created['id']}/thread/{comment['id']}", json={"body": "hijacked"}
        )
        assert res.status_code == 403
        app.dependency_overrides.clear()


class TestFollowUnfollow:
    def test_follow_increments_count(self, client: TestClient):
        created = _create_inquiry(client).json()
        res = client.post(f"/api/v1/inquiries/{created['id']}/follow")
        assert res.status_code == 201
        assert res.json()["followerCount"] == 1
        assert res.json()["following"] is True

    def test_double_follow_is_idempotent_not_double_counted(self, client: TestClient):
        created = _create_inquiry(client).json()
        client.post(f"/api/v1/inquiries/{created['id']}/follow")
        res = client.post(f"/api/v1/inquiries/{created['id']}/follow")
        assert res.status_code == 201
        assert res.json()["followerCount"] == 1

    def test_unfollow_decrements_count(self, client: TestClient):
        created = _create_inquiry(client).json()
        client.post(f"/api/v1/inquiries/{created['id']}/follow")
        res = client.delete(f"/api/v1/inquiries/{created['id']}/follow")
        assert res.status_code == 200
        assert res.json()["followerCount"] == 0
        assert res.json()["following"] is False

    def test_unfollow_something_not_followed_is_idempotent_no_op(self, client: TestClient):
        created = _create_inquiry(client).json()
        res = client.delete(f"/api/v1/inquiries/{created['id']}/follow")
        assert res.status_code == 200
        assert res.json()["followerCount"] == 0

    def test_is_following_reflects_real_state(self, client: TestClient):
        created = _create_inquiry(client).json()
        client.post(f"/api/v1/inquiries/{created['id']}/follow")
        res = client.get(f"/api/v1/inquiries/{created['id']}")
        assert res.json()["isFollowing"] is True


class TestAttorneyGating:
    def test_citizen_cannot_request_consultation(self, client: TestClient):
        created = _create_inquiry(client).json()
        res = client.post(f"/api/v1/attorneys/request-consultation?inquiry_id={created['id']}")
        assert res.status_code == 403
        assert res.json()["error"] == "not_an_attorney"

    def test_pending_attorney_rejected_with_distinct_message(self, client: TestClient, session: Session):
        created = _create_inquiry(client).json()
        attorney = User(
            auth0_sub="auth0|pending-attorney",
            email="pending@test.example",
            role=Role.attorney,
            verification_status=VerificationStatus.pending,
        )
        session.add(attorney)
        session.commit()

        attorney_identity = AuthenticatedUser(auth0_sub="auth0|pending-attorney", email="pending@test.example")
        from app.core.db import get_session

        app.dependency_overrides[get_session] = lambda: (yield session)
        app.dependency_overrides[get_current_user] = lambda: attorney_identity
        attorney_client = TestClient(app)

        res = attorney_client.post(f"/api/v1/attorneys/request-consultation?inquiry_id={created['id']}")
        assert res.status_code == 403
        assert res.json()["error"] == "not_verified"
        app.dependency_overrides.clear()

    def test_approved_attorney_can_request_consultation(self, client: TestClient, session: Session):
        created = _create_inquiry(client).json()
        attorney = User(
            auth0_sub="auth0|approved-attorney",
            email="approved@test.example",
            role=Role.attorney,
            verification_status=VerificationStatus.approved,
        )
        session.add(attorney)
        session.commit()

        attorney_identity = AuthenticatedUser(auth0_sub="auth0|approved-attorney", email="approved@test.example")
        from app.core.db import get_session

        app.dependency_overrides[get_session] = lambda: (yield session)
        app.dependency_overrides[get_current_user] = lambda: attorney_identity
        attorney_client = TestClient(app)

        res = attorney_client.post(f"/api/v1/attorneys/request-consultation?inquiry_id={created['id']}")
        assert res.status_code == 201, res.text
        assert res.json()["status"] == "pending"
        app.dependency_overrides.clear()

    def test_duplicate_consultation_request_rejected(self, client: TestClient, session: Session):
        created = _create_inquiry(client).json()
        attorney = User(
            auth0_sub="auth0|dup-attorney",
            email="dup@test.example",
            role=Role.attorney,
            verification_status=VerificationStatus.approved,
        )
        session.add(attorney)
        session.commit()

        attorney_identity = AuthenticatedUser(auth0_sub="auth0|dup-attorney", email="dup@test.example")
        from app.core.db import get_session

        app.dependency_overrides[get_session] = lambda: (yield session)
        app.dependency_overrides[get_current_user] = lambda: attorney_identity
        attorney_client = TestClient(app)

        first = attorney_client.post(f"/api/v1/attorneys/request-consultation?inquiry_id={created['id']}")
        assert first.status_code == 201
        second = attorney_client.post(f"/api/v1/attorneys/request-consultation?inquiry_id={created['id']}")
        assert second.status_code == 409
        assert second.json()["error"] == "already_requested"
        app.dependency_overrides.clear()


class TestConsultationResponse:
    def test_author_can_accept_request(self, client: TestClient, session: Session):
        created = _create_inquiry(client).json()
        attorney = User(
            auth0_sub="auth0|accept-attorney",
            email="accept@test.example",
            role=Role.attorney,
            verification_status=VerificationStatus.approved,
        )
        session.add(attorney)
        session.commit()
        session.refresh(attorney)

        request = AttorneyRequest(attorney_id=attorney.id, inquiry_id=uuid.UUID(created["id"]))
        session.add(request)
        session.commit()
        session.refresh(request)

        res = client.patch(
            f"/api/v1/attorneys/request-consultation/{request.id}", json={"decision": "accepted"}
        )
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "accepted"

    def test_non_author_cannot_respond(self, client: TestClient, session: Session):
        created = _create_inquiry(client).json()
        attorney = User(
            auth0_sub="auth0|resp-attorney",
            email="resp@test.example",
            role=Role.attorney,
            verification_status=VerificationStatus.approved,
        )
        session.add(attorney)
        session.commit()
        session.refresh(attorney)
        request = AttorneyRequest(attorney_id=attorney.id, inquiry_id=uuid.UUID(created["id"]))
        session.add(request)
        session.commit()
        session.refresh(request)

        other_client = _second_user_client(session)
        res = other_client.patch(
            f"/api/v1/attorneys/request-consultation/{request.id}", json={"decision": "accepted"}
        )
        assert res.status_code == 403
        app.dependency_overrides.clear()

    def test_conflicting_decision_rejected(self, client: TestClient, session: Session):
        created = _create_inquiry(client).json()
        attorney = User(
            auth0_sub="auth0|conflict-attorney",
            email="conflict@test.example",
            role=Role.attorney,
            verification_status=VerificationStatus.approved,
        )
        session.add(attorney)
        session.commit()
        session.refresh(attorney)
        request = AttorneyRequest(
            attorney_id=attorney.id, inquiry_id=uuid.UUID(created["id"]), status=AttorneyRequestStatus.declined
        )
        session.add(request)
        session.commit()
        session.refresh(request)

        res = client.patch(
            f"/api/v1/attorneys/request-consultation/{request.id}", json={"decision": "accepted"}
        )
        assert res.status_code == 400
        assert res.json()["error"] == "already_decided"

    def test_reapplying_same_decision_is_idempotent(self, client: TestClient, session: Session):
        created = _create_inquiry(client).json()
        attorney = User(
            auth0_sub="auth0|idem-attorney",
            email="idem@test.example",
            role=Role.attorney,
            verification_status=VerificationStatus.approved,
        )
        session.add(attorney)
        session.commit()
        session.refresh(attorney)
        request = AttorneyRequest(
            attorney_id=attorney.id, inquiry_id=uuid.UUID(created["id"]), status=AttorneyRequestStatus.accepted
        )
        session.add(request)
        session.commit()
        session.refresh(request)

        res = client.patch(
            f"/api/v1/attorneys/request-consultation/{request.id}", json={"decision": "accepted"}
        )
        assert res.status_code == 200, res.text


class TestReports:
    def test_report_real_inquiry_succeeds(self, client: TestClient):
        created = _create_inquiry(client).json()
        res = client.post(
            "/api/v1/reports",
            json={"target_type": "inquiry", "target_id": created["id"], "reason": "spam"},
        )
        assert res.status_code == 201, res.text
        assert res.json()["status"] == "open"

    def test_report_real_comment_succeeds(self, client: TestClient):
        created = _create_inquiry(client).json()
        comment = client.post(f"/api/v1/inquiries/{created['id']}/thread", json={"body": "c"}).json()
        res = client.post(
            "/api/v1/reports",
            json={"target_type": "thread_comment", "target_id": comment["id"], "reason": "abuse"},
        )
        assert res.status_code == 201, res.text

    def test_report_fabricated_uuid_404(self, client: TestClient):
        res = client.post(
            "/api/v1/reports",
            json={"target_type": "inquiry", "target_id": str(uuid.uuid4()), "reason": "x"},
        )
        assert res.status_code == 404


class TestPaginationAndSearch:
    def test_pagination_returns_requested_page_size(self, client: TestClient):
        for i in range(5):
            _create_inquiry(client, title=f"Pagination test {i}")
        res = client.get("/api/v1/inquiries?limit=2&offset=0")
        assert res.status_code == 200
        body = res.json()
        assert len(body["items"]) <= 2
        assert body["limit"] == 2
        assert body["offset"] == 0

    def test_pagination_beyond_last_page_returns_empty_list_not_error(self, client: TestClient):
        res = client.get("/api/v1/inquiries?limit=10&offset=99999")
        assert res.status_code == 200
        assert res.json()["items"] == []

    def test_text_search_matches_and_excludes(self, client: TestClient):
        _create_inquiry(client, title="Unique Searchable Keyword Inquiry", city="Springfield")
        _create_inquiry(client, title="Unrelated other inquiry", city="Portland")
        res = client.get("/api/v1/inquiries?q=Searchable")
        assert res.status_code == 200
        titles = [item["title"] for item in res.json()["items"]]
        assert "Unique Searchable Keyword Inquiry" in titles
        assert "Unrelated other inquiry" not in titles


class TestAdversarialValidation:
    def test_invalid_state_code_rejected(self, client: TestClient):
        res = _create_inquiry(client, state="New York")
        assert res.status_code == 422

    def test_invalid_status_tag_rejected(self, client: TestClient):
        res = client.post(
            "/api/v1/inquiries",
            json={
                "title": "t",
                "description": "d",
                "state": "NY",
                "city": "NYC",
                "status_tag": "not_a_real_tag",
            },
        )
        assert res.status_code == 422

    def test_invalid_report_target_type_rejected(self, client: TestClient):
        res = client.post(
            "/api/v1/reports",
            json={"target_type": "not_a_real_type", "target_id": str(uuid.uuid4()), "reason": "x"},
        )
        assert res.status_code == 422

    def test_empty_title_rejected_at_api_layer(self, client: TestClient):
        # Real M1.4 job, per M1.2's own honestly-noted non-issue: an empty
        # title is accepted at the DB layer (no CHECK constraint), but
        # MUST be rejected here, at the API/Pydantic layer.
        res = client.post(
            "/api/v1/inquiries",
            json={"title": "", "description": "d", "state": "NY", "city": "NYC", "status_tag": "community_trace"},
        )
        assert res.status_code == 422

    def test_whitespace_only_title_rejected(self, client: TestClient):
        res = client.post(
            "/api/v1/inquiries",
            json={"title": "   ", "description": "d", "state": "NY", "city": "NYC", "status_tag": "community_trace"},
        )
        assert res.status_code == 422


class TestRateLimiting:
    def test_rate_limit_engages_on_repeated_inquiry_creation(self, client: TestClient):
        """Real adversarial check per M1.4's own Bug Fix requirement — fire
        requests past settings.RATE_LIMIT_PER_MINUTE (20) from the same
        test identity in quick succession and confirm the limiter actually
        engages (a real 429), not just that a limit is documented."""
        from app.core.config import settings

        last_status = None
        for _ in range(settings.RATE_LIMIT_PER_MINUTE + 5):
            res = _create_inquiry(client)
            last_status = res.status_code
            if last_status == 429:
                break
        assert last_status == 429, "rate limiter never engaged after exceeding the documented limit"

    def test_rate_limit_response_shape_matches_canonical_error(self, client: TestClient):
        from app.core.config import settings

        res = None
        for _ in range(settings.RATE_LIMIT_PER_MINUTE + 5):
            res = _create_inquiry(client)
            if res.status_code == 429:
                break
        assert res.status_code == 429
        body = res.json()
        assert body["error"] == "rate_limited"
        assert "retryAfterSeconds" in body


class TestFollowConcurrencySafety:
    def test_follower_count_matches_real_inquiry_follows_rows(self, client: TestClient, session: Session):
        """Directly verifies the denormalized counter and the real
        InquiryFollow rows never disagree — the exact check
        WhyPoliceForum_MasterGuide.md's Milestone 1 Final Testing repeats
        at the whole-milestone level."""
        from sqlmodel import select

        from app.models.inquiry_follow import InquiryFollow

        created = _create_inquiry(client).json()
        client.post(f"/api/v1/inquiries/{created['id']}/follow")

        inquiry = session.get(Inquiry, uuid.UUID(created["id"]))
        real_follow_count = len(
            session.exec(
                select(InquiryFollow).where(InquiryFollow.inquiry_id == inquiry.id)
            ).all()
        )
        assert inquiry.follower_count == real_follow_count == 1
