from datetime import datetime, timedelta, timezone

from sqlmodel import select

from app.models.inquiry import Inquiry, InquiryTier, StatusTag, ThreadComment
from app.models.report import Report, ReportTargetType
from app.models.user import User
from app.services.pending_cleanup import purge_abandoned_pending_inquiries


def _inquiry(session, author, tier, age_hours):
    q = Inquiry(
        author_id=author.id, title="t", description="d", state="NY", city="NYC",
        status_tag=StatusTag.community_trace, tier=tier,
        created_at=datetime.now(timezone.utc) - timedelta(hours=age_hours),
    )
    session.add(q); session.commit(); session.refresh(q)
    return q


def test_only_expired_unpaid_drafts_are_removed(session):
    u = User(auth0_sub="auth0|c", email="c@x.test"); session.add(u); session.commit(); session.refresh(u)
    old_draft = _inquiry(session, u, InquiryTier.pending_payment, 72)
    fresh_draft = _inquiry(session, u, InquiryTier.pending_payment, 2)
    old_free = _inquiry(session, u, InquiryTier.free, 500)
    old_paid = _inquiry(session, u, InquiryTier.expanded, 500)
    c = ThreadComment(inquiry_id=old_draft.id, author_id=u.id, body="x"); session.add(c); session.commit(); session.refresh(c)
    session.add(Report(target_type=ReportTargetType.inquiry, target_id=old_draft.id, reporter_id=u.id, reason="r"))
    session.add(Report(target_type=ReportTargetType.thread_comment, target_id=c.id, reporter_id=u.id, reason="r"))
    session.commit()

    assert purge_abandoned_pending_inquiries(session) == 1

    remaining = {q.id for q in session.exec(select(Inquiry)).all()}
    assert remaining == {fresh_draft.id, old_free.id, old_paid.id}
    assert session.exec(select(ThreadComment)).all() == []
    assert session.exec(select(Report)).all() == []
    assert purge_abandoned_pending_inquiries(session) == 0
