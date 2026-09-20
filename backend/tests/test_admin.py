"""Tests for app/routers/admin.py — forum rebuild, Milestone 1 Step M1.5
(WhyPoliceForum_MasterGuide.md).
"""

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session

from app.models.inquiry import Inquiry, StatusTag
from app.models.report import Report, ReportStatus, ReportTargetType
from app.models.user import Role, User, VerificationStatus
from tests.conftest import TEST_USER


def _make_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.routers.admin.settings.ADMIN_AUTH0_SUBS", TEST_USER.auth0_sub)


class TestAdminGate:
    def test_non_admin_verify_attorney_returns_403(self, client: TestClient):
        res = client.post(
            f"/api/v1/admin/attorneys/{uuid.uuid4()}/verify", json={"decision": "approved"}
        )
        assert res.status_code == 403
        assert res.json()["error"] == "forbidden"

    def test_non_admin_pending_list_returns_403(self, client: TestClient):
        res = client.get("/api/v1/admin/attorneys/pending")
        assert res.status_code == 403

    def test_non_admin_reports_list_returns_403(self, client: TestClient):
        res = client.get("/api/v1/admin/reports")
        assert res.status_code == 403

    def test_non_admin_review_report_returns_403(self, client: TestClient):
        res = client.patch(f"/api/v1/admin/reports/{uuid.uuid4()}", json={"decision": "resolved"})
        assert res.status_code == 403


class TestVerifyAttorney:
    def test_admin_approves_real_pending_attorney(
        self, client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
    ):
        _make_admin(monkeypatch)
        # The admin itself must exist as a real User row first (per
        # _require_admin's own explicit design — it looks up, never
        # creates), so make one authenticated call as TEST_USER before
        # relying on admin-gated behavior.
        client.get("/api/v1/inquiries")

        attorney = User(
            auth0_sub="auth0|verify-target",
            email="target@test.example",
            role=Role.attorney,
            verification_status=VerificationStatus.pending,
        )
        session.add(attorney)
        session.commit()
        session.refresh(attorney)

        res = client.post(
            f"/api/v1/admin/attorneys/{attorney.id}/verify", json={"decision": "approved"}
        )
        assert res.status_code == 200, res.text
        assert res.json()["verificationStatus"] == "approved"

        # Confirm the write actually took effect in the database, not just
        # the response body.
        session.refresh(attorney)
        assert attorney.verification_status == VerificationStatus.approved

    def test_verifying_a_citizen_returns_400(
        self, client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
    ):
        _make_admin(monkeypatch)
        client.get("/api/v1/inquiries")

        citizen = User(auth0_sub="auth0|citizen-target", email="citizen@test.example")
        session.add(citizen)
        session.commit()
        session.refresh(citizen)

        res = client.post(
            f"/api/v1/admin/attorneys/{citizen.id}/verify", json={"decision": "approved"}
        )
        assert res.status_code == 400
        assert res.json()["error"] == "not_an_attorney"

    def test_verifying_nonexistent_user_404(
        self, client: TestClient, monkeypatch: pytest.MonkeyPatch
    ):
        _make_admin(monkeypatch)
        client.get("/api/v1/inquiries")

        res = client.post(
            f"/api/v1/admin/attorneys/{uuid.uuid4()}/verify", json={"decision": "approved"}
        )
        assert res.status_code == 404

    def test_approving_same_attorney_twice_is_idempotent(
        self, client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
    ):
        _make_admin(monkeypatch)
        client.get("/api/v1/inquiries")

        attorney = User(
            auth0_sub="auth0|idem-target",
            email="idem-target@test.example",
            role=Role.attorney,
            verification_status=VerificationStatus.pending,
        )
        session.add(attorney)
        session.commit()
        session.refresh(attorney)

        first = client.post(f"/api/v1/admin/attorneys/{attorney.id}/verify", json={"decision": "approved"})
        assert first.status_code == 200
        second = client.post(f"/api/v1/admin/attorneys/{attorney.id}/verify", json={"decision": "approved"})
        assert second.status_code == 200, second.text
        assert second.json()["verificationStatus"] == "approved"


class TestPendingAttorneysList:
    def test_lists_only_pending_attorneys(
        self, client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
    ):
        _make_admin(monkeypatch)
        client.get("/api/v1/inquiries")

        pending = User(
            auth0_sub="auth0|pending-list", email="pending-list@test.example",
            role=Role.attorney, verification_status=VerificationStatus.pending,
        )
        approved = User(
            auth0_sub="auth0|approved-list", email="approved-list@test.example",
            role=Role.attorney, verification_status=VerificationStatus.approved,
        )
        citizen = User(auth0_sub="auth0|citizen-list", email="citizen-list@test.example")
        session.add(pending); session.add(approved); session.add(citizen)
        session.commit()

        res = client.get("/api/v1/admin/attorneys/pending")
        assert res.status_code == 200
        emails = [item["email"] for item in res.json()["items"]]
        assert "pending-list@test.example" in emails
        assert "approved-list@test.example" not in emails
        assert "citizen-list@test.example" not in emails


class TestReportReview:
    def test_open_reports_are_listed_with_inlined_target(
        self, client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
    ):
        _make_admin(monkeypatch)
        me = client.get("/api/v1/inquiries")

        user = session.exec(
            __import__("sqlmodel").select(User).where(User.auth0_sub == TEST_USER.auth0_sub)
        ).first()
        inquiry = Inquiry(
            author_id=user.id, title="Reported inquiry", description="d",
            state="NY", city="NYC", status_tag=StatusTag.community_trace,
        )
        session.add(inquiry)
        session.commit()
        session.refresh(inquiry)

        report = Report(
            target_type=ReportTargetType.inquiry, target_id=inquiry.id,
            reporter_id=user.id, reason="spam",
        )
        session.add(report)
        session.commit()

        res = client.get("/api/v1/admin/reports")
        assert res.status_code == 200
        items = res.json()["items"]
        assert len(items) == 1
        assert items[0]["target"]["title"] == "Reported inquiry"

    def test_resolved_reports_excluded_from_open_list(
        self, client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
    ):
        _make_admin(monkeypatch)
        client.get("/api/v1/inquiries")
        user = session.exec(
            __import__("sqlmodel").select(User).where(User.auth0_sub == TEST_USER.auth0_sub)
        ).first()

        report = Report(
            target_type=ReportTargetType.inquiry, target_id=uuid.uuid4(),
            reporter_id=user.id, reason="already handled", status=ReportStatus.resolved,
        )
        session.add(report)
        session.commit()

        res = client.get("/api/v1/admin/reports")
        assert res.status_code == 200
        assert res.json()["items"] == []

    def test_resolve_open_report(
        self, client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
    ):
        _make_admin(monkeypatch)
        client.get("/api/v1/inquiries")
        user = session.exec(
            __import__("sqlmodel").select(User).where(User.auth0_sub == TEST_USER.auth0_sub)
        ).first()

        report = Report(
            target_type=ReportTargetType.inquiry, target_id=uuid.uuid4(),
            reporter_id=user.id, reason="spam",
        )
        session.add(report)
        session.commit()
        session.refresh(report)

        res = client.patch(f"/api/v1/admin/reports/{report.id}", json={"decision": "resolved"})
        assert res.status_code == 200, res.text
        assert res.json()["status"] == "resolved"

        # Confirm the underlying (fabricated, in this case) target
        # reference is untouched — this endpoint only closes the report.
        session.refresh(report)
        assert report.status == ReportStatus.resolved

    def test_conflicting_decision_rejected(
        self, client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
    ):
        _make_admin(monkeypatch)
        client.get("/api/v1/inquiries")
        user = session.exec(
            __import__("sqlmodel").select(User).where(User.auth0_sub == TEST_USER.auth0_sub)
        ).first()

        report = Report(
            target_type=ReportTargetType.inquiry, target_id=uuid.uuid4(),
            reporter_id=user.id, reason="spam", status=ReportStatus.dismissed,
        )
        session.add(report)
        session.commit()
        session.refresh(report)

        res = client.patch(f"/api/v1/admin/reports/{report.id}", json={"decision": "resolved"})
        assert res.status_code == 400
        assert res.json()["error"] == "already_decided"

    def test_reapplying_same_decision_idempotent(
        self, client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
    ):
        _make_admin(monkeypatch)
        client.get("/api/v1/inquiries")
        user = session.exec(
            __import__("sqlmodel").select(User).where(User.auth0_sub == TEST_USER.auth0_sub)
        ).first()

        report = Report(
            target_type=ReportTargetType.inquiry, target_id=uuid.uuid4(),
            reporter_id=user.id, reason="spam", status=ReportStatus.resolved,
        )
        session.add(report)
        session.commit()
        session.refresh(report)

        res = client.patch(f"/api/v1/admin/reports/{report.id}", json={"decision": "resolved"})
        assert res.status_code == 200, res.text

    def test_review_report_whose_target_was_deleted_still_works(
        self, client: TestClient, session: Session, monkeypatch: pytest.MonkeyPatch
    ):
        """Real adversarial check per M1.5's own Bug Fix requirement: a
        report about content deleted by its own author after filing must
        still be reviewable/closeable, not throw because target_id no
        longer resolves to anything."""
        _make_admin(monkeypatch)
        client.get("/api/v1/inquiries")
        user = session.exec(
            __import__("sqlmodel").select(User).where(User.auth0_sub == TEST_USER.auth0_sub)
        ).first()

        # target_id deliberately points at nothing real.
        report = Report(
            target_type=ReportTargetType.inquiry, target_id=uuid.uuid4(),
            reporter_id=user.id, reason="spam",
        )
        session.add(report)
        session.commit()
        session.refresh(report)

        list_res = client.get("/api/v1/admin/reports")
        assert list_res.status_code == 200
        assert list_res.json()["items"][0]["target"] is None

        resolve_res = client.patch(f"/api/v1/admin/reports/{report.id}", json={"decision": "dismissed"})
        assert resolve_res.status_code == 200, resolve_res.text
