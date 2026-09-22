"""Tests for app/routers/media.py — forum rebuild, Milestone 3 Step M3.1
(WhyPoliceForum_MasterGuide.md).

No real GCS bucket/service-account credentials exist in this environment
yet (Manual Step still pending on the client) — this project's own
established pattern (see tests/test_billing.py's equivalent Stripe
not-configured tests) is to: (1) confirm the real, honest 501 in the
actual unconfigured state, then (2) mock only the external GCS SDK call
itself (never the app's own tier-limit/ownership logic) to exercise
every real code path that doesn't depend on a live bucket.
"""

import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.main import app
from tests.test_inquiries import _create_inquiry, _second_user_client


def test_upload_url_returns_501_when_gcs_not_configured(client: TestClient):
    created = _create_inquiry(client).json()
    res = client.post(
        "/api/v1/media/upload-url",
        json={
            "inquiry_id": created["id"],
            "file_type": "image",
            "size_bytes": 1024,
            "content_type": "image/png",
        },
    )
    assert res.status_code == 501
    assert res.json()["error"] == "not_implemented"


def test_register_attachment_returns_501_when_gcs_not_configured(client: TestClient):
    created = _create_inquiry(client).json()
    res = client.post(
        f"/api/v1/inquiries/{created['id']}/attachments",
        json={"file_url": "https://storage.googleapis.com/fake-bucket/x", "file_type": "image", "size_bytes": 1024},
    )
    assert res.status_code == 501


class TestUploadUrlWithGCSConfigured:
    """Mocks only media_service's GCS-facing functions — the router's own
    ownership/tier-limit logic runs for real against the real test DB."""

    def test_owner_can_get_upload_url_within_free_tier_limit(self, client: TestClient):
        created = _create_inquiry(client).json()
        with patch("app.routers.media.media_service.is_configured", return_value=True), patch(
            "app.routers.media.media_service.generate_upload_url",
            return_value=("https://signed.example/put", "https://storage.googleapis.com/bucket/obj1"),
        ):
            res = client.post(
                "/api/v1/media/upload-url",
                json={
                    "inquiry_id": created["id"],
                    "file_type": "image",
                    "size_bytes": 4 * 1024 * 1024,
                    "content_type": "image/png",
                },
            )
        assert res.status_code == 200, res.text
        assert res.json()["uploadUrl"] == "https://signed.example/put"
        assert res.json()["fileUrl"] == "https://storage.googleapis.com/bucket/obj1"

    def test_second_file_on_free_tier_rejected_even_under_size_limit(self, client: TestClient, session: Session):
        """Real M3.1 requirement: FILE COUNT is enforced independently of
        total size — a free-tier inquiry already at 1 file must reject a
        second file even if the combined size is well under 5MB."""
        from app.models.evidence_attachment import EvidenceAttachment

        created = _create_inquiry(client).json()
        session.add(EvidenceAttachment(inquiry_id=uuid.UUID(created["id"]), file_url="https://storage.googleapis.com/bucket/existing", file_type="image", size_bytes=1024))
        session.commit()

        with patch("app.routers.media.media_service.is_configured", return_value=True), patch(
            "app.routers.media.media_service.generate_upload_url",
            return_value=("https://signed.example/put", "https://storage.googleapis.com/bucket/obj2"),
        ):
            res = client.post(
                "/api/v1/media/upload-url",
                json={"inquiry_id": created["id"], "file_type": "image", "size_bytes": 1024, "content_type": "image/png"},
            )
        assert res.status_code == 403
        assert res.json()["error"] == "upgrade_required"

    def test_expanded_tier_allows_up_to_five_files_under_50mb(self, client: TestClient, session: Session):
        from app.models.evidence_attachment import EvidenceAttachment
        from app.models.inquiry import Inquiry, InquiryTier

        created = _create_inquiry(client).json()
        inquiry = session.get(Inquiry, uuid.UUID(created["id"]))
        inquiry.tier = InquiryTier.expanded
        session.add(inquiry)
        for i in range(4):
            session.add(EvidenceAttachment(inquiry_id=uuid.UUID(created["id"]), file_url=f"https://storage.googleapis.com/bucket/f{i}", file_type="image", size_bytes=1024))
        session.commit()

        with patch("app.routers.media.media_service.is_configured", return_value=True), patch(
            "app.routers.media.media_service.generate_upload_url",
            return_value=("https://signed.example/put", "https://storage.googleapis.com/bucket/f5"),
        ):
            res = client.post(
                "/api/v1/media/upload-url",
                json={"inquiry_id": created["id"], "file_type": "image", "size_bytes": 1024, "content_type": "image/png"},
            )
        assert res.status_code == 200, res.text

    def test_sixth_file_on_expanded_tier_rejected(self, client: TestClient, session: Session):
        from app.models.evidence_attachment import EvidenceAttachment
        from app.models.inquiry import Inquiry, InquiryTier

        created = _create_inquiry(client).json()
        inquiry = session.get(Inquiry, uuid.UUID(created["id"]))
        inquiry.tier = InquiryTier.expanded
        session.add(inquiry)
        for i in range(5):
            session.add(EvidenceAttachment(inquiry_id=uuid.UUID(created["id"]), file_url=f"https://storage.googleapis.com/bucket/f{i}", file_type="image", size_bytes=1024))
        session.commit()

        with patch("app.routers.media.media_service.is_configured", return_value=True), patch(
            "app.routers.media.media_service.generate_upload_url",
            return_value=("https://signed.example/put", "https://storage.googleapis.com/bucket/f6"),
        ):
            res = client.post(
                "/api/v1/media/upload-url",
                json={"inquiry_id": created["id"], "file_type": "image", "size_bytes": 1024, "content_type": "image/png"},
            )
        assert res.status_code == 403

    def test_expanded_tier_rejects_over_total_size_even_under_file_count(self, client: TestClient, session: Session):
        from app.models.inquiry import Inquiry, InquiryTier

        created = _create_inquiry(client).json()
        inquiry = session.get(Inquiry, uuid.UUID(created["id"]))
        inquiry.tier = InquiryTier.expanded
        session.add(inquiry)
        session.commit()

        with patch("app.routers.media.media_service.is_configured", return_value=True):
            res = client.post(
                "/api/v1/media/upload-url",
                json={"inquiry_id": created["id"], "file_type": "video", "size_bytes": 51 * 1024 * 1024, "content_type": "video/mp4"},
            )
        assert res.status_code == 403

    def test_non_owner_cannot_get_upload_url(self, client: TestClient, session: Session):
        created = _create_inquiry(client).json()
        other_client = _second_user_client(session)
        with patch("app.routers.media.media_service.is_configured", return_value=True):
            res = other_client.post(
                "/api/v1/media/upload-url",
                json={"inquiry_id": created["id"], "file_type": "image", "size_bytes": 1024, "content_type": "image/png"},
            )
        assert res.status_code == 403
        app.dependency_overrides.clear()

    def test_upload_url_for_nonexistent_inquiry_404s(self, client: TestClient):
        with patch("app.routers.media.media_service.is_configured", return_value=True):
            res = client.post(
                "/api/v1/media/upload-url",
                json={"inquiry_id": str(uuid.uuid4()), "file_type": "image", "size_bytes": 1024, "content_type": "image/png"},
            )
        assert res.status_code == 404


class TestMagicByteSniffing:
    """Real, unmocked exercise of media_service's own magic-byte matching
    logic — only the GCS blob download itself is faked (a real network
    call to a bucket that doesn't exist yet), never the signature check."""

    def _sniff(self, header_bytes: bytes, claimed_type: str) -> bool:
        from app.services import media_service

        with patch("app.services.media_service.is_configured", return_value=True), patch(
            "app.services.media_service.settings.GCS_BUCKET_NAME", "test-bucket"
        ), patch("app.services.media_service.storage.Client.from_service_account_json") as mock_client:
            mock_blob = mock_client.return_value.bucket.return_value.blob.return_value
            mock_blob.download_as_bytes.return_value = header_bytes
            return media_service.sniff_matches_claimed_type(
                "https://storage.googleapis.com/test-bucket/obj", claimed_type
            )

    def test_real_jpeg_header_matches_image(self):
        assert self._sniff(b"\xff\xd8\xff\xe0" + b"\x00" * 20, "image") is True

    def test_real_png_header_matches_image(self):
        assert self._sniff(b"\x89PNG\r\n\x1a\n" + b"\x00" * 20, "image") is True

    def test_video_bytes_claimed_as_image_rejected(self):
        # A real MP4 ftyp header, but the request claims "image".
        assert self._sniff(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 20, "image") is False

    def test_real_mp4_header_matches_video(self):
        assert self._sniff(b"\x00\x00\x00\x18ftypmp42" + b"\x00" * 20, "video") is True

    def test_real_pdf_header_matches_document(self):
        assert self._sniff(b"%PDF-1.7\n" + b"\x00" * 20, "document") is True

    def test_webp_vs_avi_both_riff_disambiguated_correctly(self):
        webp_header = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"\x00" * 16
        avi_header = b"RIFF" + b"\x00\x00\x00\x00" + b"AVI " + b"\x00" * 16
        assert self._sniff(webp_header, "image") is True
        assert self._sniff(webp_header, "video") is False
        assert self._sniff(avi_header, "video") is True
        assert self._sniff(avi_header, "image") is False


class TestRegisterAttachmentWithGCSConfigured:
    def test_registering_a_real_uploaded_file_succeeds(self, client: TestClient):
        created = _create_inquiry(client).json()
        with patch("app.routers.media.media_service.is_configured", return_value=True), patch(
            "app.routers.media.media_service.blob_exists_for_bucket", return_value=True
        ), patch("app.routers.media.media_service.sniff_matches_claimed_type", return_value=True):
            res = client.post(
                f"/api/v1/inquiries/{created['id']}/attachments",
                json={"file_url": "https://storage.googleapis.com/bucket/real-obj", "file_type": "image", "size_bytes": 1024},
            )
        assert res.status_code == 200, res.text
        assert res.json()["fileUrl"] == "https://storage.googleapis.com/bucket/real-obj"

    def test_spoofed_file_type_rejected(self, client: TestClient):
        """Bug Fix decision (user-confirmed, in scope): a file claiming to
        be an "image" whose real bytes don't match any known image
        signature (e.g. it's actually a video) is rejected."""
        created = _create_inquiry(client).json()
        with patch("app.routers.media.media_service.is_configured", return_value=True), patch(
            "app.routers.media.media_service.blob_exists_for_bucket", return_value=True
        ), patch("app.routers.media.media_service.sniff_matches_claimed_type", return_value=False):
            res = client.post(
                f"/api/v1/inquiries/{created['id']}/attachments",
                json={"file_url": "https://storage.googleapis.com/bucket/spoofed", "file_type": "image", "size_bytes": 1024},
            )
        assert res.status_code == 422
        assert res.json()["error"] == "file_type_mismatch"

    def test_registering_a_fabricated_file_url_rejected(self, client: TestClient):
        """Real M3.1 security requirement: a file_url that was never
        actually issued a signed URL for this inquiry (no real blob
        exists behind it) must be rejected, not trusted blindly."""
        created = _create_inquiry(client).json()
        with patch("app.routers.media.media_service.is_configured", return_value=True), patch(
            "app.routers.media.media_service.blob_exists_for_bucket", return_value=False
        ):
            res = client.post(
                f"/api/v1/inquiries/{created['id']}/attachments",
                json={"file_url": "https://storage.googleapis.com/bucket/never-uploaded", "file_type": "image", "size_bytes": 1024},
            )
        assert res.status_code == 422
        assert res.json()["error"] == "invalid_file_url"

    def test_deleted_inquiry_mid_upload_cannot_create_orphaned_attachment(self, client: TestClient):
        """Bug Fix adversarial scenario: an upload starts, then the parent
        inquiry is deleted before the upload completes. The DB row is only
        ever created by register_attachment AFTER a confirmed upload, and
        that endpoint looks the inquiry up first — a deleted inquiry
        simply 404s here, by construction, never creating an orphan."""
        created = _create_inquiry(client).json()
        del_res = client.delete(f"/api/v1/inquiries/{created['id']}")
        assert del_res.status_code == 200

        with patch("app.routers.media.media_service.is_configured", return_value=True), patch(
            "app.routers.media.media_service.blob_exists_for_bucket", return_value=True
        ):
            res = client.post(
                f"/api/v1/inquiries/{created['id']}/attachments",
                json={"file_url": "https://storage.googleapis.com/bucket/orphan-attempt", "file_type": "image", "size_bytes": 1024},
            )
        assert res.status_code == 404

    def test_non_owner_cannot_register_attachment(self, client: TestClient, session: Session):
        created = _create_inquiry(client).json()
        other_client = _second_user_client(session)
        with patch("app.routers.media.media_service.is_configured", return_value=True), patch(
            "app.routers.media.media_service.blob_exists_for_bucket", return_value=True
        ):
            res = other_client.post(
                f"/api/v1/inquiries/{created['id']}/attachments",
                json={"file_url": "https://storage.googleapis.com/bucket/x", "file_type": "image", "size_bytes": 1024},
            )
        assert res.status_code == 403
        app.dependency_overrides.clear()


class TestGetInquiryExposesAttachments:
    def test_registered_attachment_appears_on_get_inquiry(self, client: TestClient):
        created = _create_inquiry(client).json()
        with patch("app.routers.media.media_service.is_configured", return_value=True), patch(
            "app.routers.media.media_service.blob_exists_for_bucket", return_value=True
        ), patch("app.routers.media.media_service.sniff_matches_claimed_type", return_value=True):
            client.post(
                f"/api/v1/inquiries/{created['id']}/attachments",
                json={"file_url": "https://storage.googleapis.com/bucket/visible-obj", "file_type": "image", "size_bytes": 2048},
            )
        res = client.get(f"/api/v1/inquiries/{created['id']}")
        assert res.status_code == 200
        attachments = res.json()["attachments"]
        assert len(attachments) == 1
        assert attachments[0]["fileUrl"] == "https://storage.googleapis.com/bucket/visible-obj"
        assert attachments[0]["fileType"] == "image"

    def test_attachments_visible_to_anonymous_viewer_too(self, client: TestClient, session: Session):
        """Unlike attorneyRequests (author-only), evidence attachments are
        meant to be seen by anyone reading the inquiry, including a
        logged-out visitor. Same anonymous-client pattern as
        TestAnonymousAccess in test_inquiries.py."""
        from app.core.db import get_session
        from app.core.security import get_current_user, get_optional_user

        created = _create_inquiry(client).json()
        with patch("app.routers.media.media_service.is_configured", return_value=True), patch(
            "app.routers.media.media_service.blob_exists_for_bucket", return_value=True
        ), patch("app.routers.media.media_service.sniff_matches_claimed_type", return_value=True):
            client.post(
                f"/api/v1/inquiries/{created['id']}/attachments",
                json={"file_url": "https://storage.googleapis.com/bucket/public-obj", "file_type": "document", "size_bytes": 512},
            )

        app.dependency_overrides[get_session] = lambda: (yield session)
        app.dependency_overrides[get_optional_user] = lambda: None
        app.dependency_overrides.pop(get_current_user, None)
        anon_client = TestClient(app)

        anon_res = anon_client.get(f"/api/v1/inquiries/{created['id']}")
        assert anon_res.status_code == 200
        assert len(anon_res.json()["attachments"]) == 1
        app.dependency_overrides.clear()


class TestDeleteAttachment:
    def test_owner_can_delete_own_attachment(self, client: TestClient):
        created = _create_inquiry(client).json()
        with patch("app.routers.media.media_service.is_configured", return_value=True), patch(
            "app.routers.media.media_service.blob_exists_for_bucket", return_value=True
        ), patch("app.routers.media.media_service.sniff_matches_claimed_type", return_value=True):
            reg = client.post(
                f"/api/v1/inquiries/{created['id']}/attachments",
                json={"file_url": "https://storage.googleapis.com/bucket/to-delete", "file_type": "image", "size_bytes": 1024},
            ).json()
        res = client.delete(f"/api/v1/inquiries/{created['id']}/attachments/{reg['id']}")
        assert res.status_code == 200
        assert res.json()["deleted"] is True

        follow_up = client.get(f"/api/v1/inquiries/{created['id']}")
        assert follow_up.json()["attachments"] == []

    def test_non_owner_cannot_delete_attachment(self, client: TestClient, session: Session):
        created = _create_inquiry(client).json()
        with patch("app.routers.media.media_service.is_configured", return_value=True), patch(
            "app.routers.media.media_service.blob_exists_for_bucket", return_value=True
        ), patch("app.routers.media.media_service.sniff_matches_claimed_type", return_value=True):
            reg = client.post(
                f"/api/v1/inquiries/{created['id']}/attachments",
                json={"file_url": "https://storage.googleapis.com/bucket/protected", "file_type": "image", "size_bytes": 1024},
            ).json()

        other_client = _second_user_client(session)
        res = other_client.delete(f"/api/v1/inquiries/{created['id']}/attachments/{reg['id']}")
        assert res.status_code == 403
        app.dependency_overrides.clear()

    def test_deleting_nonexistent_attachment_404s(self, client: TestClient):
        created = _create_inquiry(client).json()
        res = client.delete(f"/api/v1/inquiries/{created['id']}/attachments/{uuid.uuid4()}")
        assert res.status_code == 404
