"""GCS signed-URL uploads for evidence attachments — forum rebuild,
Milestone 3 Step M3.1 (WhyPoliceForum_MasterGuide.md).

Turns M2.3's "coming soon" evidence-upload placeholder into a real
feature and closes M1.3's evidence_attachments table's actual purpose.
Returns an honest 501 (app/routers/billing.py's own established pattern)
until GCS_BUCKET_NAME/GCS_SERVICE_ACCOUNT_JSON_PATH are configured —
never a mocked signed URL that could be mistaken for a working upload.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.security import AuthenticatedUser, get_current_user
from app.models.evidence_attachment import EvidenceAttachment
from app.models.inquiry import Inquiry, InquiryTier
from app.models.user import User
from app.schemas.media import AttachmentCreate, UploadUrlRequest
from app.services import media_service

router = APIRouter(prefix="/api/v1")

# Tier limits per M3.1's own spec — free: 1 file / 5MB, expanded: 5 files / 50MB.
_TIER_LIMITS = {
    InquiryTier.free: {"max_files": 1, "max_total_bytes": 5 * 1024 * 1024},
    InquiryTier.expanded: {"max_files": 5, "max_total_bytes": 50 * 1024 * 1024},
}

_NOT_CONFIGURED = HTTPException(
    status_code=501,
    detail={
        "error": "not_implemented",
        "message": "File uploads aren't fully set up yet — check back soon.",
    },
)


def _get_or_create_user(session: Session, current: AuthenticatedUser) -> User:
    """Duplicated per this codebase's own established per-router pattern
    (see app/routers/inquiries.py's own copy of this exact helper)."""
    user = session.exec(select(User).where(User.auth0_sub == current.auth0_sub)).first()
    if user is None:
        user = User(auth0_sub=current.auth0_sub, email=current.email or "")
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def _parse_uuid(raw: str, not_found: HTTPException) -> uuid.UUID:
    try:
        return uuid.UUID(raw)
    except (ValueError, AttributeError, TypeError):
        raise not_found from None


def _load_owned_inquiry(session: Session, inquiry_id: str, user: User) -> Inquiry:
    not_found = HTTPException(
        status_code=404, detail={"error": "not_found", "message": "Inquiry not found."}
    )
    inquiry = session.get(Inquiry, _parse_uuid(inquiry_id, not_found))
    if inquiry is None:
        raise not_found
    if inquiry.author_id != user.id:
        raise HTTPException(
            status_code=403,
            detail={"error": "forbidden", "message": "You can only upload evidence to your own inquiries."},
        )
    return inquiry


@router.post("/media/upload-url")
def create_upload_url(
    body: UploadUrlRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    if not media_service.is_configured():
        raise _NOT_CONFIGURED

    user = _get_or_create_user(session, current)
    inquiry = _load_owned_inquiry(session, body.inquiry_id, user)

    limits = _TIER_LIMITS[inquiry.tier]
    existing = session.exec(
        select(EvidenceAttachment).where(EvidenceAttachment.inquiry_id == inquiry.id)
    ).all()
    existing_count = len(existing)
    existing_total_bytes = sum(a.size_bytes for a in existing)

    # Real, canonical upgrade_required rejection — same shape as M1.4's
    # character-limit rejection (Standing Implementation Discipline rule
    # 9), never a different shape for what is, from the frontend's
    # perspective, the same "this needs the paid tier" situation. File
    # COUNT is checked independently of total size — a free-tier inquiry
    # with one 1MB photo already at its file limit must reject a second
    # 1MB photo even though the total would stay well under 5MB.
    if existing_count + 1 > limits["max_files"] or existing_total_bytes + body.size_bytes > limits["max_total_bytes"]:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "upgrade_required",
                "message": "This inquiry needs the $2.99 upgrade to attach more evidence.",
            },
        )

    signed_url, public_url = media_service.generate_upload_url(
        inquiry_id=inquiry.id, file_type=body.file_type.value, content_type=body.content_type
    )
    return {"uploadUrl": signed_url, "fileUrl": public_url}


@router.post("/inquiries/{inquiry_id}/attachments")
def register_attachment(
    inquiry_id: str,
    body: AttachmentCreate,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    if not media_service.is_configured():
        raise _NOT_CONFIGURED

    user = _get_or_create_user(session, current)
    inquiry = _load_owned_inquiry(session, inquiry_id, user)

    # Real GCS existence check — never trust a client-supplied file_url at
    # face value. A fabricated URL that was never actually issued a
    # signed PUT for this bucket has no real blob behind it and is
    # rejected here, not silently registered as a real attachment.
    if not media_service.blob_exists_for_bucket(body.file_url):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "invalid_file_url",
                "message": "This file wasn't uploaded through a valid upload session.",
            },
        )

    # M3.1 Bug Fix decision (user-confirmed, in scope): verify the real
    # uploaded bytes match the claimed file_type — catches a spoofed
    # upload (e.g. claiming "image" for an actual video file) rather than
    # trusting the client's own label.
    if not media_service.sniff_matches_claimed_type(body.file_url, body.file_type.value):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "file_type_mismatch",
                "message": "This file doesn't look like the type you selected.",
            },
        )

    attachment = EvidenceAttachment(
        inquiry_id=inquiry.id,
        file_url=body.file_url,
        file_type=body.file_type,
        size_bytes=body.size_bytes,
    )
    session.add(attachment)
    session.commit()
    session.refresh(attachment)

    return {
        "id": str(attachment.id),
        "fileUrl": attachment.file_url,
        "fileType": attachment.file_type.value,
        "sizeBytes": attachment.size_bytes,
    }


@router.delete("/inquiries/{inquiry_id}/attachments/{attachment_id}")
def delete_attachment(
    inquiry_id: str,
    attachment_id: str,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Owner-only removal of one of their own inquiry's attachments — the
    UI Details' own "remove/delete action" on each uploaded file.

    Real gap found during a full-scope re-audit: this used to only
    remove the DB row and deliberately leave the GCS object in place —
    but with no background GC job anywhere in this codebase, that meant
    a "deleted" attachment's file stayed publicly fetchable at its
    storage.googleapis.com URL forever. For a police-incident forum
    where an upload may show a citizen's own face/plate/location, that's
    a real privacy failure, not just a cost concern — so this now
    deletes the real GCS object too. Also closes an inconsistency with
    create_upload_url/register_attachment: those both honestly 501 when
    GCS isn't configured, this endpoint previously had no such check at
    all and would delete the DB row regardless."""
    if not media_service.is_configured():
        raise _NOT_CONFIGURED

    user = _get_or_create_user(session, current)
    _load_owned_inquiry(session, inquiry_id, user)

    not_found = HTTPException(
        status_code=404, detail={"error": "not_found", "message": "Attachment not found."}
    )
    attachment = session.get(EvidenceAttachment, _parse_uuid(attachment_id, not_found))
    if attachment is None or str(attachment.inquiry_id) != inquiry_id:
        raise not_found

    media_service.delete_blob(attachment.file_url)
    session.delete(attachment)
    session.commit()
    return {"deleted": True}
