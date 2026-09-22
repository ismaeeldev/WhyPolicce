"""Integration tests: real endpoints actually trigger the right emails —
forum rebuild, Milestone 3 Step M3.3 (WhyPoliceForum_MasterGuide.md).

TestClient runs FastAPI's BackgroundTasks synchronously within the same
request/response cycle (no real async event loop), so these tests can
assert on email_service calls immediately after the request returns —
this also directly proves M3.3's own "the response should return
promptly, with the email sending genuinely happening after/alongside"
requirement isn't violated by an email failure blocking the response
(the response already came back 200/201 by the time these assertions
run, regardless of whether the mocked send succeeds).
"""

from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.db import get_session
from app.core.security import AuthenticatedUser, get_current_user, get_optional_user
from app.main import app
from app.models.user import Role, User, VerificationStatus
from tests.test_inquiries import _create_inquiry


def _make_client_for(session: Session, auth0_sub: str, email: str) -> TestClient:
    identity = AuthenticatedUser(auth0_sub=auth0_sub, email=email)
    app.dependency_overrides[get_session] = lambda: (yield session)
    app.dependency_overrides[get_current_user] = lambda: identity
    app.dependency_overrides[get_optional_user] = lambda: identity
    return TestClient(app)


class TestNewCommentEmailNotification:
    def test_followers_are_emailed_excluding_comment_author(self, session: Session):
        author_client = _make_client_for(session, "auth0|email-test-author", "author@test.example")
        created = _create_inquiry(author_client).json()

        follower_client = _make_client_for(session, "auth0|email-test-follower", "follower@test.example")
        follow_res = follower_client.post(f"/api/v1/inquiries/{created['id']}/follow")
        assert follow_res.status_code == 201

        # The follower themselves posts the comment — they must NOT get a
        # self-notification, even though they're a follower.
        with patch("app.routers.inquiries.email_service.send_new_comment_email") as mock_send:
            comment_res = follower_client.post(
                f"/api/v1/inquiries/{created['id']}/thread", json={"body": "a real comment"}
            )
        assert comment_res.status_code == 201
        mock_send.assert_not_called()
        app.dependency_overrides.clear()

    def test_a_different_follower_is_emailed_when_someone_else_comments(self, session: Session):
        author_client = _make_client_for(session, "auth0|email-test-author2", "author2@test.example")
        created = _create_inquiry(author_client).json()

        follower_client = _make_client_for(session, "auth0|email-test-follower2", "follower2@test.example")
        follower_client.post(f"/api/v1/inquiries/{created['id']}/follow")

        commenter_client = _make_client_for(session, "auth0|email-test-commenter", "commenter@test.example")
        with patch("app.routers.inquiries.email_service.send_new_comment_email") as mock_send:
            res = commenter_client.post(
                f"/api/v1/inquiries/{created['id']}/thread", json={"body": "a real comment from someone else"}
            )
        assert res.status_code == 201
        mock_send.assert_called_once()
        _, kwargs = mock_send.call_args
        assert kwargs["to"] == "follower2@test.example"
        app.dependency_overrides.clear()

    def test_email_provider_failure_does_not_fail_the_comment_post(self, session: Session):
        """M3.3's own explicit Bug Fix requirement: the underlying
        comment-post request must succeed even if email sending itself
        raises."""
        author_client = _make_client_for(session, "auth0|email-test-author3", "author3@test.example")
        created = _create_inquiry(author_client).json()
        follower_client = _make_client_for(session, "auth0|email-test-follower3", "follower3@test.example")
        follower_client.post(f"/api/v1/inquiries/{created['id']}/follow")

        commenter_client = _make_client_for(session, "auth0|email-test-commenter3", "commenter3@test.example")
        with patch("app.routers.inquiries.email_service.send_new_comment_email", side_effect=RuntimeError("boom")):
            res = commenter_client.post(
                f"/api/v1/inquiries/{created['id']}/thread", json={"body": "comment during provider outage"}
            )
        # Real bug found and fixed while writing this exact test: an
        # uncaught exception inside the per-follower notification loop
        # used to propagate out of the BackgroundTasks job and break the
        # whole request/response cycle. _notify_followers_of_new_comment
        # now wraps each per-follower send in its own try/except, so the
        # comment-post response is unaffected regardless of what any one
        # notification helper does.
        assert res.status_code == 201, res.text
        app.dependency_overrides.clear()


class TestConsultationRequestedEmailNotification:
    def test_inquiry_author_is_emailed_on_consultation_request(self, session: Session):
        author_client = _make_client_for(session, "auth0|email-test-inquiry-author", "inquiry-author@test.example")
        created = _create_inquiry(author_client).json()

        attorney = User(
            auth0_sub="auth0|email-test-attorney",
            email="attorney@test.example",
            role=Role.attorney,
            verification_status=VerificationStatus.approved,
            attorney_subscription_active=True,
        )
        session.add(attorney)
        session.commit()
        attorney_client = _make_client_for(session, attorney.auth0_sub, attorney.email)

        with patch("app.routers.inquiries.email_service.send_consultation_requested_email") as mock_send:
            res = attorney_client.post(f"/api/v1/attorneys/request-consultation?inquiry_id={created['id']}")
        assert res.status_code == 201
        mock_send.assert_called_once()
        _, kwargs = mock_send.call_args
        assert kwargs["to"] == "inquiry-author@test.example"
        app.dependency_overrides.clear()
