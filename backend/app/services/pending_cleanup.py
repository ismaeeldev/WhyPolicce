"""Expiry policy for abandoned pay-to-publish drafts (Scope Revision 2 §4.1 Option A).

A `pending_payment` inquiry is a private draft awaiting a Stripe payment. If the
author never pays, it would otherwise live forever in their My Inquiries list.
Drafts older than PENDING_DRAFT_MAX_AGE_HOURS are deleted together with every
row that references them. Paid (free/expanded) inquiries are never touched.
"""
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete
from sqlmodel import Session, select

from app.models.attorney_request import AttorneyRequest
from app.models.evidence_attachment import EvidenceAttachment
from app.models.inquiry import Inquiry, InquiryTier, ThreadComment
from app.models.inquiry_follow import InquiryFollow
from app.models.report import Report, ReportTargetType

logger = logging.getLogger(__name__)

PENDING_DRAFT_MAX_AGE_HOURS = 48


def purge_abandoned_pending_inquiries(
    session: Session,
    *,
    now: datetime | None = None,
    max_age_hours: int = PENDING_DRAFT_MAX_AGE_HOURS,
) -> int:
    """Deletes expired unpaid drafts. Returns how many inquiries were removed."""
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(hours=max_age_hours)
    ids = list(
        session.exec(
            select(Inquiry.id).where(Inquiry.tier == InquiryTier.pending_payment, Inquiry.created_at < cutoff)
        ).all()
    )
    if not ids:
        return 0
    comment_ids = list(session.exec(select(ThreadComment.id).where(ThreadComment.inquiry_id.in_(ids))).all())
    session.exec(delete(Report).where(Report.target_type == ReportTargetType.inquiry, Report.target_id.in_(ids)))
    if comment_ids:
        session.exec(
            delete(Report).where(Report.target_type == ReportTargetType.thread_comment, Report.target_id.in_(comment_ids))
        )
    for model in (EvidenceAttachment, AttorneyRequest, InquiryFollow, ThreadComment):
        session.exec(delete(model).where(model.inquiry_id.in_(ids)))
    session.exec(delete(Inquiry).where(Inquiry.id.in_(ids)))
    session.commit()
    logger.info("pending cleanup: removed %d abandoned unpaid draft(s)", len(ids))
    return len(ids)
