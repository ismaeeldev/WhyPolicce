"""Tests for scheduler.py's orphan evidence cleanup job — real gap found
during a full-scope re-audit: EvidenceUploadField's two-step upload flow
(GCS PUT, then a separate register-attachment call) can leave a real
file in GCS with no DB row ever pointing at it if a user navigates away
in between. No test coverage existed for this job at all before this
file, matching the rest of scheduler.py's own (also-untested) ingestion
jobs — this is the first real unit test for anything in that module,
scoped narrowly to the one piece that's actually testable without a
live Neon connection and live GCS credentials (both mocked here).
"""
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy.sql.elements import TextClause

from app.models.evidence_attachment import EvidenceAttachment, FileType
from app.models.inquiry import Inquiry, InquiryTier
from app.models.user import User


def _make_inquiry_and_attachment(session, file_url: str) -> None:
    user = User(auth0_sub="auth0|orphan-cleanup-test", email="orphan@test.example")
    session.add(user)
    session.commit()
    session.refresh(user)

    inquiry = Inquiry(
        author_id=user.id,
        title="Orphan cleanup test inquiry",
        description="x",
        state="CA",
        city="Testville",
        status_tag="community_trace",
        tier=InquiryTier.free,
    )
    session.add(inquiry)
    session.commit()
    session.refresh(inquiry)

    session.add(
        EvidenceAttachment(
            inquiry_id=inquiry.id, file_url=file_url, file_type=FileType.image, size_bytes=1024
        )
    )
    session.commit()


class TestOrphanEvidenceCleanup:
    @pytest.mark.asyncio
    async def test_skips_when_gcs_not_configured(self, session, monkeypatch: pytest.MonkeyPatch):
        from app.services import scheduler

        with patch("app.services.scheduler.sync_engine", MagicMock()), patch(
            "app.services.scheduler.media_service.is_configured", return_value=False
        ), patch("app.services.scheduler.media_service.list_evidence_blobs") as mock_list:
            await scheduler._run_orphan_evidence_cleanup()
            mock_list.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_database_not_configured(self):
        from app.services import scheduler

        with patch("app.services.scheduler.sync_engine", None), patch(
            "app.services.scheduler.media_service.list_evidence_blobs"
        ) as mock_list:
            await scheduler._run_orphan_evidence_cleanup()
            mock_list.assert_not_called()

    @pytest.mark.asyncio
    async def test_known_blob_is_not_deleted(self, session, engine):
        """A blob with a real, matching evidence_attachments row must
        never be deleted, regardless of age — this is the one case this
        whole job exists to NOT touch."""
        from app.services import scheduler

        known_url = "https://storage.googleapis.com/test-bucket/evidence/image/inq1/real-file.jpg"
        _make_inquiry_and_attachment(session, known_url)

        with patch("app.services.scheduler.sync_engine", engine), patch(
            "app.services.scheduler.media_service.is_configured", return_value=True
        ), patch(
            "app.services.scheduler.media_service.list_evidence_blobs", return_value=[known_url]
        ), patch("app.services.scheduler.media_service.delete_blob") as mock_delete:
            # sqlite (the test engine) has no advisory locks — the lock
            # acquisition's own session.exec(text(...)) call is
            # distinguished from the real EvidenceAttachment lookup query
            # by checking for the statement's own .compile()/select-like
            # shape, since both go through the same Session.exec mock.
            with patch("sqlmodel.Session.exec") as mock_exec:
                def exec_side_effect(statement):
                    result = MagicMock()
                    result.first.return_value = (True,)
                    # The advisory-lock calls go through text(...)
                    # (TextClause); only the real select() query for
                    # known URLs is anything else — real data returned
                    # only for that one.
                    result.all.return_value = [] if isinstance(statement, TextClause) else [known_url]
                    return result

                mock_exec.side_effect = exec_side_effect
                await scheduler._run_orphan_evidence_cleanup()

        mock_delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_orphaned_blob_is_deleted(self, session, engine):
        """A blob with NO matching evidence_attachments row is the
        actual orphan case this job exists to clean up."""
        from app.services import scheduler

        orphan_url = "https://storage.googleapis.com/test-bucket/evidence/image/inq2/orphaned-file.jpg"

        with patch("app.services.scheduler.sync_engine", engine), patch(
            "app.services.scheduler.media_service.is_configured", return_value=True
        ), patch(
            "app.services.scheduler.media_service.list_evidence_blobs", return_value=[orphan_url]
        ), patch("app.services.scheduler.media_service.delete_blob") as mock_delete:
            with patch("sqlmodel.Session.exec") as mock_exec:
                def exec_side_effect(statement):
                    # Lock acquisition returns (True,); the
                    # EvidenceAttachment lookup returns no rows (nothing
                    # in this test's DB matches orphan_url) — correct for
                    # both calls regardless of which is which here, since
                    # "no known URLs" is exactly what makes orphan_url an
                    # orphan.
                    result = MagicMock()
                    result.first.return_value = (True,)
                    result.all.return_value = []
                    return result

                mock_exec.side_effect = exec_side_effect
                await scheduler._run_orphan_evidence_cleanup()

        mock_delete.assert_called_once_with(orphan_url)

    @pytest.mark.asyncio
    async def test_no_candidates_short_circuits_cleanly(self, session, engine):
        from app.services import scheduler

        with patch("app.services.scheduler.sync_engine", engine), patch(
            "app.services.scheduler.media_service.is_configured", return_value=True
        ), patch(
            "app.services.scheduler.media_service.list_evidence_blobs", return_value=[]
        ), patch("app.services.scheduler.media_service.delete_blob") as mock_delete:
            with patch("sqlmodel.Session.exec") as mock_exec:
                lock_result = MagicMock()
                lock_result.first.return_value = (True,)
                mock_exec.return_value = lock_result
                await scheduler._run_orphan_evidence_cleanup()

        mock_delete.assert_not_called()

    @pytest.mark.asyncio
    async def test_delete_failure_for_one_blob_does_not_abort_the_run(self, session, engine):
        """One blob failing to delete (a transient GCS error, a race
        with a concurrent delete) must not prevent the rest of the run
        from completing — each blob is deleted independently."""
        from app.services import scheduler

        url_a = "https://storage.googleapis.com/test-bucket/evidence/image/inqA/a.jpg"
        url_b = "https://storage.googleapis.com/test-bucket/evidence/image/inqB/b.jpg"

        with patch("app.services.scheduler.sync_engine", engine), patch(
            "app.services.scheduler.media_service.is_configured", return_value=True
        ), patch(
            "app.services.scheduler.media_service.list_evidence_blobs", return_value=[url_a, url_b]
        ), patch(
            "app.services.scheduler.media_service.delete_blob",
            side_effect=[RuntimeError("transient GCS error"), None],
        ) as mock_delete:
            with patch("sqlmodel.Session.exec") as mock_exec:
                def exec_side_effect(statement):
                    result = MagicMock()
                    result.first.return_value = (True,)
                    result.all.return_value = []
                    return result

                mock_exec.side_effect = exec_side_effect
                await scheduler._run_orphan_evidence_cleanup()

        assert mock_delete.call_count == 2
