"""Core CRUD endpoints for the forum product — Milestone 1 Step M1.4
(WhyPoliceForum_MasterGuide.md). Matches this codebase's existing router
conventions (see app/routers/search.py, app/routers/memory.py) rather than
inventing new ones: {"error", "message"} HTTPException detail shape
(flattened centrally in app/main.py's exception handlers), a per-router
duplicated _get_or_create_user, _parse_*_id 404-not-500 UUID parsing.
"""

import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, func, select

from app.core.config import settings
from app.core.db import get_session
from app.core.security import AuthenticatedUser, get_current_user, get_optional_user
from app.core.timeutil import to_utc_iso
from app.models.attorney_request import AttorneyRequest, AttorneyRequestStatus
from app.models.evidence_attachment import EvidenceAttachment
from app.models.inquiry import Inquiry, InquiryTier, StatusTag, ThreadComment
from app.models.inquiry_follow import InquiryFollow
from app.models.report import Report, ReportTargetType
from app.models.user import Role, User, VerificationStatus
from app.schemas.inquiry import (
    ConsultationDecision,
    InquiryCreate,
    InquiryUpdate,
    ReportCreate,
    ThreadCommentCreate,
    ThreadCommentUpdate,
)
from app.services import email_service
from app.services.rate_limit import RateLimitExceeded, check_rate_limit

router = APIRouter(prefix="/api/v1")
logger = logging.getLogger("whypolice.inquiries")

# 250-character free-tier soft cap — client's own explicit answer
# (WhyPolice-Scope-Realignment.pdf). A soft cap at PUBLISH time, not a
# hard input-level stop (that's M2.3's frontend behavior) — the backend's
# job is just to reject an over-length free-tier submission with the
# canonical upgrade_required shape, never to silently truncate.
_FREE_TIER_CHAR_LIMIT = 250

# Pagination defaults — Standing Implementation Discipline rule 5 and
# Appendix B item #12 (WhyPoliceForum_MasterGuide.md): offset/limit style,
# chosen over cursor-based because this codebase has no existing
# cursor-pagination precedent to reuse and a straightforward numeric
# offset is sufficient at this product's expected scale — used
# consistently across every list endpoint below and in M1.5's admin list.
_DEFAULT_PAGE_SIZE = 20
_MAX_PAGE_SIZE = 100

_NOT_FOUND = HTTPException(
    status_code=404, detail={"error": "not_found", "message": "Not found."}
)


def _parse_uuid(raw: str, not_found: HTTPException) -> uuid.UUID:
    """Same pattern as search.py's _parse_session_id / memory.py's
    _parse_note_id — a malformed id must 404 cleanly, not 500 on a raw
    driver error."""
    try:
        return uuid.UUID(raw)
    except (ValueError, AttributeError, TypeError):
        raise not_found from None


def _get_or_create_user(session: Session, current: AuthenticatedUser) -> User:
    """Duplicated from search.py/memory.py rather than imported — same
    reasoning: this router must work even if /api/me was never called
    first, and this codebase's own established pattern is to duplicate
    this small helper per-router, not share it."""
    user = session.exec(select(User).where(User.auth0_sub == current.auth0_sub)).first()
    if user is None:
        user = User(auth0_sub=current.auth0_sub, email=current.email or "")
        session.add(user)
        session.commit()
        session.refresh(user)
    elif current.email and not user.email:
        user.email = current.email
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def _rate_limit_or_429(action: str, user_id: uuid.UUID) -> None:
    """Standing Implementation Discipline rule 4 — reuses the existing
    check_rate_limit/RateLimitExceeded machinery from app/services/
    rate_limit.py (built for the old product's search endpoint) rather
    than inventing a second rate-limiter. That function keys purely by a
    single string with no action namespace, so a per-action prefix
    ("inquiries:<user_id>" vs. "comments:<user_id>") keeps posting an
    inquiry from eating into a user's separate comment-rate budget —
    without this prefix, every write action across this whole router
    would incorrectly share one bucket."""
    try:
        check_rate_limit(f"{action}:{user_id}")
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "message": "You're doing that faster than we can keep up — try again shortly.",
                "retryAfterSeconds": exc.retry_after_seconds,
            },
        ) from exc


def _inquiry_out(inquiry: Inquiry, *, viewer_id: uuid.UUID | None, comment_count: int, has_attachments: bool, truncate: bool) -> dict:
    """Public response shape — never the raw SQLModel Inquiry object (that
    is exactly how a users.email join would leak accidentally, per this
    guide's own privacy rule). comment_count/has_attachments are NOT
    stored columns (a real gap this guide's own deep audit found and
    fixed) — computed by the caller and passed in here, never per-row
    N+1 queried.

    truncate=True (used only by the feed list endpoint) visually caps a
    free-tier inquiry's description at the same 250-char limit enforced
    at write time — a defensive display-layer cap, not the real
    enforcement (M1.4's create/update endpoints already prevent a
    free-tier inquiry from ever exceeding this length at write time, so
    this should be a no-op in the common case, not the primary control)."""
    description = inquiry.description
    if truncate and inquiry.tier == InquiryTier.free and len(description) > _FREE_TIER_CHAR_LIMIT:
        description = description[:_FREE_TIER_CHAR_LIMIT].rstrip() + "…"
    return {
        "id": str(inquiry.id),
        "title": inquiry.title,
        "description": description,
        "state": inquiry.state,
        "city": inquiry.city,
        "precinct": inquiry.precinct,
        "statusTag": inquiry.status_tag.value,
        "tier": inquiry.tier.value,
        "followerCount": inquiry.follower_count,
        "commentCount": comment_count,
        "hasAttachments": has_attachments,
        "createdAt": to_utc_iso(inquiry.created_at),
        "updatedAt": to_utc_iso(inquiry.updated_at),
        # isFollowing is intentionally set to a placeholder False here —
        # this is a per-viewer field that this shared helper cannot
        # correctly compute on its own (real, avoided bug: an earlier
        # draft of this function called a stub _is_following() at this
        # exact point, which unconditionally raised NotImplementedError —
        # a real crash on every call, caught before it ever ran against a
        # live request). Every real caller below (list_inquiries,
        # get_inquiry, create_inquiry, update_inquiry) computes the real
        # per-viewer value itself — via a single batched query across the
        # whole page for the list endpoint (never one query per row) or a
        # direct query for the single-inquiry/write endpoints — and
        # overwrites this field on the returned dict before it ships.
        "isFollowing": False,
    }


def _comment_out(comment: ThreadComment) -> dict:
    return {
        "id": str(comment.id),
        "inquiryId": str(comment.inquiry_id),
        "authorId": str(comment.author_id),
        "body": comment.body,
        "createdAt": to_utc_iso(comment.created_at),
    }


@router.get("/inquiries")
def list_inquiries(
    region: str | None = Query(default=None),
    status: StatusTag | None = Query(default=None),
    sort: str = Query(default="newest"),
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=_DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    current: AuthenticatedUser | None = Depends(get_optional_user),
    session: Session = Depends(get_session),
) -> dict:
    """Feed endpoint. `q` is the real backend for the feed's own search box
    (M2.2) — matches against title, description, city, and precinct.
    `limit`/`offset` pagination is mandatory from the start (Standing
    Implementation Discipline rule 5) since this is a nationwide table.

    Real gap found while building M2.2's frontend: this endpoint used to
    require auth unconditionally, but the scope PDF and M2.0's own
    proxy.ts both treat reading the forum as public — a logged-out
    visitor landing on the feed must see it, not a 401. Auth is now
    OPTIONAL here (get_optional_user): a logged-in viewer still gets a
    real per-viewer isFollowing computed the same way as before; an
    anonymous request skips user lookup entirely and every item's
    isFollowing is correctly False (there is no viewer to follow
    anything), never a per-request User row created just for anonymous
    reads.
    """
    user = _get_or_create_user(session, current) if current else None

    statement = select(Inquiry)
    if region:
        statement = statement.where(Inquiry.state == region.strip().upper())
    if status:
        statement = statement.where(Inquiry.status_tag == status)
    if q:
        like = f"%{q.strip()}%"
        statement = statement.where(
            (Inquiry.title.ilike(like))
            | (Inquiry.description.ilike(like))
            | (Inquiry.city.ilike(like))
            | (Inquiry.precinct.ilike(like))
        )

    if sort == "most_followed":
        statement = statement.order_by(Inquiry.follower_count.desc())
    else:
        statement = statement.order_by(Inquiry.created_at.desc())

    total = session.exec(select(func.count()).select_from(statement.subquery())).one()
    rows = session.exec(statement.offset(offset).limit(limit)).all()

    inquiry_ids = [r.id for r in rows]
    if inquiry_ids:
        comment_counts = dict(
            session.exec(
                select(ThreadComment.inquiry_id, func.count())
                .where(ThreadComment.inquiry_id.in_(inquiry_ids))
                .group_by(ThreadComment.inquiry_id)
            ).all()
        )
        attachment_inquiry_ids = set(
            session.exec(
                select(EvidenceAttachment.inquiry_id).where(
                    EvidenceAttachment.inquiry_id.in_(inquiry_ids)
                )
            ).all()
        )
        following_inquiry_ids = (
            set(
                session.exec(
                    select(InquiryFollow.inquiry_id).where(
                        InquiryFollow.inquiry_id.in_(inquiry_ids),
                        InquiryFollow.user_id == user.id,
                    )
                ).all()
            )
            if user
            else set()
        )
    else:
        comment_counts, attachment_inquiry_ids, following_inquiry_ids = {}, set(), set()

    items = []
    for inquiry in rows:
        item = _inquiry_out(
            inquiry,
            viewer_id=user.id if user else None,
            comment_count=comment_counts.get(inquiry.id, 0),
            has_attachments=inquiry.id in attachment_inquiry_ids,
            truncate=True,
        )
        item["isFollowing"] = inquiry.id in following_inquiry_ids
        items.append(item)

    return {"items": items, "total": total, "limit": limit, "offset": offset}


@router.get("/inquiries/{inquiry_id}")
def get_inquiry(
    inquiry_id: str,
    current: AuthenticatedUser | None = Depends(get_optional_user),
    session: Session = Depends(get_session),
) -> dict:
    """The inquiry's own full detail — a SEPARATE endpoint from
    GET /inquiries/{id}/thread (comments only), resolving the real
    ambiguity in the scope PDF's endpoint list per M1.4's own note.
    Always returns the FULL, untruncated description regardless of tier —
    this is the direct-view endpoint, not the feed's truncated preview.

    Auth optional, same reasoning as list_inquiries (M2.2): reading a
    single inquiry's thread page must work for a logged-out visitor too.
    """
    user = _get_or_create_user(session, current) if current else None
    not_found = HTTPException(
        status_code=404, detail={"error": "not_found", "message": "Inquiry not found."}
    )
    inquiry = session.get(Inquiry, _parse_uuid(inquiry_id, not_found))
    if inquiry is None:
        raise not_found

    comment_count = session.exec(
        select(func.count()).where(ThreadComment.inquiry_id == inquiry.id)
    ).one()
    has_attachments = (
        session.exec(
            select(EvidenceAttachment.id).where(EvidenceAttachment.inquiry_id == inquiry.id)
        ).first()
        is not None
    )
    is_following = (
        user is not None
        and session.exec(
            select(InquiryFollow.id).where(
                InquiryFollow.inquiry_id == inquiry.id, InquiryFollow.user_id == user.id
            )
        ).first()
        is not None
    )
    out = _inquiry_out(
        inquiry,
        viewer_id=user.id if user else None,
        comment_count=comment_count,
        has_attachments=has_attachments,
        truncate=False,
    )
    out["isFollowing"] = is_following

    # Real gap found while building M2.4's thread page (WhyPoliceForum_
    # MasterGuide.md): _inquiry_out never exposed WHO the author is, so
    # the frontend had no way to know whether the current viewer should
    # see their own Edit/Delete controls or the consultation-request
    # Accept/Decline section. A per-viewer computed boolean, not the raw
    # author_id UUID — never exposes the author's identity to other
    # viewers, just a yes/no the viewer needs for their own UI (the
    # actual security boundary remains M1.4's server-side ownership
    # check on the PATCH/DELETE endpoints themselves, unaffected by
    # this field).
    out["isAuthor"] = user is not None and inquiry.author_id == user.id

    # Real gap found while building M2.4's thread page (WhyPoliceForum_
    # MasterGuide.md): M1.4 built POST /attorneys/request-consultation
    # and PATCH .../request-consultation/{id} (accept/decline), but no
    # endpoint anywhere ever surfaced an inquiry's own AttorneyRequest
    # rows back to its author — without this, the accept/decline
    # endpoint has no UI that could ever call it, since the author never
    # sees that a request exists. Author-only: attorneyRequests is
    # always an empty list for every other viewer (including the
    # requesting attorney themselves, who sees their own request's
    # status via GET /attorneys/me/requests instead, not here) — never
    # even queried for a non-author viewer, both to avoid the extra
    # query and because a citizen has no legitimate reason to see who
    # else requested consultation on someone else's inquiry.
    if user is not None and inquiry.author_id == user.id:
        requests = session.exec(
            select(AttorneyRequest, User)
            .join(User, AttorneyRequest.attorney_id == User.id)
            .where(AttorneyRequest.inquiry_id == inquiry.id)
            .order_by(AttorneyRequest.created_at.asc())
        ).all()
        out["attorneyRequests"] = [
            {
                "id": str(req.id),
                "attorneyId": str(req.attorney_id),
                # Never the attorney's email (privacy rule) — bar
                # number/jurisdiction are professional licensing
                # details, not personal contact info, and are exactly
                # what an inquiry author needs to identify who is
                # requesting before deciding accept/decline.
                "attorneyBarNo": attorney.verified_bar_no,
                "attorneyBarJurisdiction": attorney.bar_jurisdiction,
                "status": req.status.value,
                "createdAt": to_utc_iso(req.created_at),
            }
            for req, attorney in requests
        ]
    else:
        out["attorneyRequests"] = []

    # M3.1 — real evidence attachments, visible to every viewer (unlike
    # attorneyRequests above): evidence is meant to be seen by anyone
    # reading the inquiry, not a private author/attorney negotiation.
    attachments = session.exec(
        select(EvidenceAttachment)
        .where(EvidenceAttachment.inquiry_id == inquiry.id)
        .order_by(EvidenceAttachment.created_at.asc())
    ).all()
    out["attachments"] = [
        {
            "id": str(a.id),
            "fileUrl": a.file_url,
            "fileType": a.file_type.value,
            "sizeBytes": a.size_bytes,
        }
        for a in attachments
    ]

    return out


@router.post("/inquiries", status_code=201)
def create_inquiry(
    body: InquiryCreate,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    user = _get_or_create_user(session, current)
    _rate_limit_or_429("inquiries", user.id)

    # M3.2 real fix: every inquiry is created at tier=free, full stop — a
    # client-supplied body.tier is never trusted (the old M1.4 TODO this
    # replaces explicitly flagged accepting tier="expanded" at face value
    # as a real, deliberate gap pending this exact milestone). The ONLY
    # path that is ever allowed to set tier=expanded in production is
    # app/routers/forum_billing.py's Stripe webhook, after a real,
    # verified $2.99 payment — never this endpoint, and never based on
    # anything the client claims in the request body.
    if len(body.description) > _FREE_TIER_CHAR_LIMIT:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "upgrade_required",
                "message": (
                    "This post needs the $2.99 upgrade to publish past "
                    f"{_FREE_TIER_CHAR_LIMIT} characters."
                ),
            },
        )

    inquiry = Inquiry(
        author_id=user.id,
        title=body.title,
        description=body.description,
        state=body.state,
        city=body.city,
        precinct=body.precinct,
        status_tag=body.status_tag,
        tier=InquiryTier.free,
    )
    session.add(inquiry)
    session.commit()
    session.refresh(inquiry)
    # comment_count=0/has_attachments=False/isFollowing (the helper's own
    # default False) are all genuinely correct here, not placeholders
    # being skipped — a brand-new inquiry has zero comments, zero
    # attachments, and zero follows (including from its own author) by
    # construction, unlike update_inquiry's own real computed values for
    # an inquiry that may already have any of these.
    return _inquiry_out(inquiry, viewer_id=user.id, comment_count=0, has_attachments=False, truncate=False)


@router.patch("/inquiries/{inquiry_id}")
def update_inquiry(
    inquiry_id: str,
    body: InquiryUpdate,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Citizen can edit their OWN inquiry at any time — no time limit
    (client's explicit answer). Ownership: 403 for "exists but not
    yours," 404 for "doesn't exist at all" — these must never be
    confused, per M1.4's own explicit requirement (a real, deliberate
    divergence from this codebase's older memory.py precedent, which
    uses a flat 404 for both cases — the forum's own new endpoints follow
    the more precise, newer convention this guide specifies)."""
    user = _get_or_create_user(session, current)
    not_found = HTTPException(
        status_code=404, detail={"error": "not_found", "message": "Inquiry not found."}
    )
    inquiry = session.get(Inquiry, _parse_uuid(inquiry_id, not_found))
    if inquiry is None:
        raise not_found
    if inquiry.author_id != user.id:
        raise HTTPException(
            status_code=403,
            detail={"error": "forbidden", "message": "You can only edit your own inquiries."},
        )

    if body.title is not None:
        inquiry.title = body.title
    if body.description is not None:
        # Real gap found and fixed during a full-scope re-audit: this
        # endpoint never enforced the free-tier character limit at all,
        # so a citizen could edit a free inquiry to any length, bypassing
        # the $2.99 upgrade entirely — the exact same rule create_inquiry
        # already enforces, just never applied here. Only a genuinely
        # free-tier inquiry is capped; an already-expanded one (real,
        # webhook-confirmed payment) keeps its unlocked length.
        if inquiry.tier == InquiryTier.free and len(body.description) > _FREE_TIER_CHAR_LIMIT:
            raise HTTPException(
                status_code=403,
                detail={
                    "error": "upgrade_required",
                    "message": (
                        "This post needs the $2.99 upgrade to publish past "
                        f"{_FREE_TIER_CHAR_LIMIT} characters."
                    ),
                },
            )
        inquiry.description = body.description
    if body.state is not None:
        inquiry.state = body.state
    if body.city is not None:
        inquiry.city = body.city
    if body.precinct is not None:
        inquiry.precinct = body.precinct
    if body.status_tag is not None:
        inquiry.status_tag = body.status_tag
    inquiry.updated_at = datetime.now(timezone.utc)
    session.add(inquiry)
    session.commit()
    session.refresh(inquiry)

    comment_count = session.exec(
        select(func.count()).where(ThreadComment.inquiry_id == inquiry.id)
    ).one()
    has_attachments = (
        session.exec(
            select(EvidenceAttachment.id).where(EvidenceAttachment.inquiry_id == inquiry.id)
        ).first()
        is not None
    )
    is_following = (
        session.exec(
            select(InquiryFollow.id).where(
                InquiryFollow.inquiry_id == inquiry.id, InquiryFollow.user_id == user.id
            )
        ).first()
        is not None
    )
    # Real fix, not a cosmetic default: an inquiry being edited can already
    # have real attachments/followers (unlike create_inquiry's own
    # correct False/0 defaults for a genuinely brand-new row) — computed
    # for real here rather than left as _inquiry_out's placeholder value.
    out = _inquiry_out(inquiry, viewer_id=user.id, comment_count=comment_count, has_attachments=has_attachments, truncate=False)
    out["isFollowing"] = is_following
    return out


@router.delete("/inquiries/{inquiry_id}")
def delete_inquiry(
    inquiry_id: str,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    user = _get_or_create_user(session, current)
    not_found = HTTPException(
        status_code=404, detail={"error": "not_found", "message": "Inquiry not found."}
    )
    inquiry = session.get(Inquiry, _parse_uuid(inquiry_id, not_found))
    if inquiry is None:
        raise not_found
    if inquiry.author_id != user.id:
        raise HTTPException(
            status_code=403,
            detail={"error": "forbidden", "message": "You can only delete your own inquiries."},
        )
    session.delete(inquiry)
    session.commit()
    return {"deleted": True}


@router.get("/inquiries/{inquiry_id}/thread")
def get_thread(
    inquiry_id: str,
    limit: int = Query(default=_DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    current: AuthenticatedUser | None = Depends(get_optional_user),
    session: Session = Depends(get_session),
) -> dict:
    """Comments + timeline for one inquiry — comments ONLY, see
    get_inquiry() above for the inquiry's own fields. Paginated in case a
    popular inquiry's comment count grows large.

    Auth optional (M2.2): reading a thread must work for a logged-out
    visitor. The prior version unconditionally called
    _get_or_create_user purely for its discarded return value (a real,
    harmless-but-pointless side effect — creating a User row on every
    anonymous read would be wrong) — only sync the user when one is
    actually authenticated."""
    if current:
        _get_or_create_user(session, current)
    not_found = HTTPException(
        status_code=404, detail={"error": "not_found", "message": "Inquiry not found."}
    )
    inquiry = session.get(Inquiry, _parse_uuid(inquiry_id, not_found))
    if inquiry is None:
        raise not_found

    total = session.exec(
        select(func.count()).where(ThreadComment.inquiry_id == inquiry.id)
    ).one()
    comments = session.exec(
        select(ThreadComment)
        .where(ThreadComment.inquiry_id == inquiry.id)
        .order_by(ThreadComment.created_at.asc())
        .offset(offset)
        .limit(limit)
    ).all()
    return {
        "items": [_comment_out(c) for c in comments],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


def _notify_followers_of_new_comment(session: Session, inquiry_id: uuid.UUID, comment_author_id: uuid.UUID) -> None:
    """Runs as a FastAPI BackgroundTasks job — a side effect, never a
    dependency of the comment-post response the user is waiting on
    (M3.3's own explicit "the response should return promptly" Test
    requirement). Reuses the SAME request-scoped session the endpoint
    already has: FastAPI runs BackgroundTasks after the response is
    sent but before the request's own dependency (get_session) is torn
    down, so the session is still open and valid here. Opening a
    brand-new session via a bare get_session() call instead would
    connect to whatever DATABASE_URL is actually configured, bypassing
    a test's app.dependency_overrides entirely — a real bug found while
    building this exact feature, caught by the existing test suite.

    Bug Fix decision (user-confirmed): ONE email per comment per
    follower, no batching/digest window. The comment rate limit
    (settings.RATE_LIMIT_PER_MINUTE, 20/min per commenting user) already
    bounds how fast a single inquiry can generate new comments, so this
    is a real but bounded scenario, not unbounded spam risk — a real
    debounced/windowed digest would need a delay mechanism FastAPI's
    plain BackgroundTasks can't provide on its own, which is more
    complexity than this milestone's scope calls for. Revisit only if
    real usage shows this is genuinely annoying to followers."""
    inquiry = session.get(Inquiry, inquiry_id)
    if inquiry is None:
        return
    followers = session.exec(
        select(User)
        .join(InquiryFollow, InquiryFollow.user_id == User.id)
        .where(InquiryFollow.inquiry_id == inquiry_id, InquiryFollow.user_id != comment_author_id)
    ).all()
    inquiry_url = f"{settings.FRONTEND_URL}/inquiries/{inquiry_id}"
    for follower in followers:
        if not follower.email:
            continue
        try:
            email_service.send_new_comment_email(
                to=follower.email, inquiry_title=inquiry.title, inquiry_url=inquiry_url
            )
        except Exception:
            # Real bug found while testing this exact feature: an
            # uncaught exception inside a BackgroundTasks job can
            # propagate up through Starlette's response-sending path and
            # break the request/response cycle for the user, even though
            # they already received their 200/201 response body — email
            # sending must never be able to do that. send_email() itself
            # already catches provider errors; this is a second,
            # independent guard around the whole per-follower loop so a
            # bug in ANY future notification helper can't take down
            # comment-posting for every user on a heavily-followed
            # inquiry.
            logger.exception(
                "Failed to notify follower %s of new comment on inquiry %s", follower.id, inquiry_id
            )


@router.post("/inquiries/{inquiry_id}/thread", status_code=201)
def create_comment(
    inquiry_id: str,
    body: ThreadCommentCreate,
    background_tasks: BackgroundTasks,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    user = _get_or_create_user(session, current)
    _rate_limit_or_429("comments", user.id)
    not_found = HTTPException(
        status_code=404, detail={"error": "not_found", "message": "Inquiry not found."}
    )
    inquiry = session.get(Inquiry, _parse_uuid(inquiry_id, not_found))
    if inquiry is None:
        raise not_found

    comment = ThreadComment(inquiry_id=inquiry.id, author_id=user.id, body=body.body)
    session.add(comment)
    session.commit()
    session.refresh(comment)

    # M3.3 — email every follower except the comment's own author. A
    # background task, not awaited inline: this response must return
    # promptly regardless of email-provider latency/errors.
    background_tasks.add_task(_notify_followers_of_new_comment, session, inquiry.id, user.id)

    return _comment_out(comment)


@router.patch("/inquiries/{inquiry_id}/thread/{comment_id}")
def update_comment(
    inquiry_id: str,
    comment_id: str,
    body: ThreadCommentUpdate,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """A comment's own author can edit it — closes a real gap an earlier
    draft of this guide left inconsistent (a test scenario assumed this
    endpoint existed before it was ever specified)."""
    user = _get_or_create_user(session, current)
    not_found = HTTPException(
        status_code=404, detail={"error": "not_found", "message": "Comment not found."}
    )
    comment = session.get(ThreadComment, _parse_uuid(comment_id, not_found))
    if comment is None or str(comment.inquiry_id) != inquiry_id:
        raise not_found
    if comment.author_id != user.id:
        raise HTTPException(
            status_code=403,
            detail={"error": "forbidden", "message": "You can only edit your own comments."},
        )
    comment.body = body.body
    session.add(comment)
    session.commit()
    session.refresh(comment)
    return _comment_out(comment)


@router.delete("/inquiries/{inquiry_id}/thread/{comment_id}")
def delete_comment(
    inquiry_id: str,
    comment_id: str,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    user = _get_or_create_user(session, current)
    not_found = HTTPException(
        status_code=404, detail={"error": "not_found", "message": "Comment not found."}
    )
    comment = session.get(ThreadComment, _parse_uuid(comment_id, not_found))
    if comment is None or str(comment.inquiry_id) != inquiry_id:
        raise not_found
    if comment.author_id != user.id:
        raise HTTPException(
            status_code=403,
            detail={"error": "forbidden", "message": "You can only delete your own comments."},
        )
    session.delete(comment)
    session.commit()
    return {"deleted": True}


@router.post("/inquiries/{inquiry_id}/follow", status_code=201)
def follow_inquiry(
    inquiry_id: str,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Idempotent no-op on repeat (Standing Implementation Discipline rule
    8 — the same "repeat action is harmless" shape as unfollow's own
    delete-something-not-followed case): a second follow from the same
    user succeeds harmlessly rather than erroring, matching REST
    convention for this class of action rather than treating a double-
    click as a real conflict."""
    user = _get_or_create_user(session, current)
    _rate_limit_or_429("follows", user.id)
    not_found = HTTPException(
        status_code=404, detail={"error": "not_found", "message": "Inquiry not found."}
    )
    inquiry = session.get(Inquiry, _parse_uuid(inquiry_id, not_found))
    if inquiry is None:
        raise not_found

    existing = session.exec(
        select(InquiryFollow).where(
            InquiryFollow.inquiry_id == inquiry.id, InquiryFollow.user_id == user.id
        )
    ).first()
    if existing is None:
        # Real atomic increment at the database level, not read-then-write
        # in application code — a popular inquiry receiving concurrent
        # follows is a real race condition otherwise.
        session.add(InquiryFollow(inquiry_id=inquiry.id, user_id=user.id))
        session.exec(
            Inquiry.__table__.update()
            .where(Inquiry.id == inquiry.id)
            .values(follower_count=Inquiry.follower_count + 1)
        )
        # Real gap found during a full-scope re-audit: the docstring
        # above claims the atomic UPDATE makes concurrent follows safe,
        # but that only protects the counter increment — the earlier
        # SELECT-then-INSERT above is not atomic. Two concurrent follow
        # requests from the same user can both pass that SELECT and both
        # reach here; the second commit then violates the real unique
        # constraint on (inquiry_id, user_id) and raised an unhandled
        # IntegrityError (an ugly 500) with the counter already bumped
        # twice. Same catch-rollback-recover shape as users.py's own
        # _get_or_create_user for the identical class of race.
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
        session.refresh(inquiry)
    return {"following": True, "followerCount": inquiry.follower_count}


@router.delete("/inquiries/{inquiry_id}/follow")
def unfollow_inquiry(
    inquiry_id: str,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Idempotent no-op: unfollowing something not followed succeeds
    harmlessly."""
    user = _get_or_create_user(session, current)
    not_found = HTTPException(
        status_code=404, detail={"error": "not_found", "message": "Inquiry not found."}
    )
    inquiry = session.get(Inquiry, _parse_uuid(inquiry_id, not_found))
    if inquiry is None:
        raise not_found

    existing = session.exec(
        select(InquiryFollow).where(
            InquiryFollow.inquiry_id == inquiry.id, InquiryFollow.user_id == user.id
        )
    ).first()
    if existing is not None:
        session.delete(existing)
        # Real gap found during a full-scope re-audit: two concurrent
        # unfollow requests for the same user can both pass the SELECT
        # above before either commits, so both would decrement — there
        # was no floor, and no CHECK (follower_count >= 0) constraint on
        # the column, so this could drive the counter negative (a
        # negative count then renders in the feed and sorts
        # "most_followed" wrong). The delete's own unique-row match
        # still only ever removes one real InquiryFollow row even if
        # this races, so gating the decrement on follower_count > 0
        # keeps the displayed counter honest without needing a DB-level
        # CHECK migration.
        session.exec(
            Inquiry.__table__.update()
            .where(Inquiry.id == inquiry.id, Inquiry.follower_count > 0)
            .values(follower_count=Inquiry.follower_count - 1)
        )
        session.commit()
        session.refresh(inquiry)
    return {"following": False, "followerCount": inquiry.follower_count}


def _notify_author_of_consultation_request(session: Session, inquiry_id: uuid.UUID) -> None:
    """Same BackgroundTasks-job pattern as
    _notify_followers_of_new_comment — reuses the request's own
    session, never opens a bare get_session() (see that function's own
    docstring for the real test-isolation bug that caused). Never
    includes the attorney's direct contact info (Milestone 1's privacy
    rule) — the real "connect" mechanism stays inside the product's own
    gated accept/decline flow."""
    inquiry = session.get(Inquiry, inquiry_id)
    if inquiry is None:
        return
    author = session.get(User, inquiry.author_id)
    if author is None or not author.email:
        return
    try:
        email_service.send_consultation_requested_email(
            to=author.email,
            inquiry_title=inquiry.title,
            inquiry_url=f"{settings.FRONTEND_URL}/inquiries/{inquiry_id}",
        )
    except Exception:
        # Same independent guard as _notify_followers_of_new_comment's
        # own try/except — see that function's docstring.
        logger.exception("Failed to notify author %s of consultation request on inquiry %s", author.id, inquiry_id)


@router.post("/attorneys/request-consultation", status_code=201)
def request_consultation(
    inquiry_id: str,
    background_tasks: BackgroundTasks,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Gated: only role=attorney AND verification_status=approved. Uses
    this guide's canonical error shape with two distinct `error` values
    so the frontend (M2.4) can branch correctly (Standing Implementation
    Discipline rule 9) — not_verified for a real attorney still
    pending/rejected, not_an_attorney for a citizen account entirely."""
    user = _get_or_create_user(session, current)
    if user.role != Role.attorney:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "not_an_attorney",
                "message": "Only attorney accounts can request a consultation.",
            },
        )
    if user.verification_status != VerificationStatus.approved:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "not_verified",
                "message": "Your attorney account is not yet approved.",
            },
        )
    # Real gap found during a full-scope re-audit: attorney_subscription_
    # active is set/cleared by the real Stripe webhook (forum_billing.py)
    # but was only ever READ by GET /api/me for the frontend's own
    # paywall display — nothing on the server actually gated this
    # endpoint on it. An approved attorney who cancelled their $149/mo
    # subscription (or never subscribed) could still call this directly
    # forever; the paywall was purely cosmetic. Enforced here for real.
    if not user.attorney_subscription_active:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "subscription_required",
                "message": "An active attorney subscription is required to request a consultation.",
            },
        )
    _rate_limit_or_429("consultations", user.id)

    not_found = HTTPException(
        status_code=404, detail={"error": "not_found", "message": "Inquiry not found."}
    )
    inquiry = session.get(Inquiry, _parse_uuid(inquiry_id, not_found))
    if inquiry is None:
        raise not_found

    existing = session.exec(
        select(AttorneyRequest).where(
            AttorneyRequest.attorney_id == user.id, AttorneyRequest.inquiry_id == inquiry.id
        )
    ).first()
    if existing is not None:
        # Unique constraint at the DB level already prevents a duplicate
        # row — surfaced here as a real, meaningful conflict (not silently
        # idempotent like follow/unfollow) since a second request on an
        # already-pending/decided one is a genuinely different situation
        # the attorney should know about, not a harmless repeat click.
        raise HTTPException(
            status_code=409,
            detail={
                "error": "already_requested",
                "message": "You've already requested a consultation on this inquiry.",
            },
        )

    request = AttorneyRequest(attorney_id=user.id, inquiry_id=inquiry.id)
    session.add(request)
    session.commit()
    session.refresh(request)

    # M3.3 — email the inquiry's author. A background task, not awaited
    # inline: this response must return promptly regardless of
    # email-provider latency/errors.
    background_tasks.add_task(_notify_author_of_consultation_request, session, inquiry.id)

    return {
        "id": str(request.id),
        "inquiryId": str(request.inquiry_id),
        "attorneyId": str(request.attorney_id),
        "status": request.status.value,
        "createdAt": to_utc_iso(request.created_at),
    }


@router.get("/attorneys/me/requests")
def list_my_consultation_requests(
    limit: int = Query(default=_DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Real gap found while building M2.4's attorney portal
    (WhyPoliceForum_MasterGuide.md) — M1.4 let an attorney CREATE a
    consultation request, but never gave them any way to find out
    whether the citizen ever responded, making respond_to_consultation
    invisible from the attorney's own side of the product. Any
    authenticated user can call this (matches request_consultation's
    own role check being enforced there, not here) — a citizen account
    simply always gets an empty list back, since they can never have a
    real AttorneyRequest row as attorney_id.
    """
    user = _get_or_create_user(session, current)

    statement = select(AttorneyRequest, Inquiry).join(
        Inquiry, AttorneyRequest.inquiry_id == Inquiry.id
    ).where(AttorneyRequest.attorney_id == user.id)
    total = session.exec(select(func.count()).select_from(statement.subquery())).one()
    rows = session.exec(
        statement.order_by(AttorneyRequest.created_at.desc()).offset(offset).limit(limit)
    ).all()

    return {
        "items": [
            {
                "id": str(req.id),
                "status": req.status.value,
                "createdAt": to_utc_iso(req.created_at),
                "inquiry": {
                    "id": str(inquiry.id),
                    "title": inquiry.title,
                    "statusTag": inquiry.status_tag.value,
                    "state": inquiry.state,
                    "city": inquiry.city,
                },
            }
            for req, inquiry in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.patch("/attorneys/request-consultation/{request_id}")
def respond_to_consultation(
    request_id: str,
    body: ConsultationDecision,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Only the INQUIRY's own author (not the requesting attorney, not an
    unrelated user) may accept/decline. Idempotency matches M1.5's own
    admin-decision endpoints exactly (Standing Implementation Discipline
    rule 8 — the same shape of problem gets the same answer everywhere):
    re-applying the same decision succeeds harmlessly; requesting the
    OTHER decision on an already-decided request is a real 400 conflict
    via the canonical error shape."""
    user = _get_or_create_user(session, current)
    if body.decision not in (AttorneyRequestStatus.accepted.value, AttorneyRequestStatus.declined.value):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "validation_error",
                "message": "decision must be 'accepted' or 'declined'.",
            },
        )

    not_found = HTTPException(
        status_code=404, detail={"error": "not_found", "message": "Consultation request not found."}
    )
    request = session.get(AttorneyRequest, _parse_uuid(request_id, not_found))
    if request is None:
        raise not_found
    inquiry = session.get(Inquiry, request.inquiry_id)
    if inquiry is None or inquiry.author_id != user.id:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "forbidden",
                "message": "Only the inquiry's own author can respond to this request.",
            },
        )

    requested_status = AttorneyRequestStatus(body.decision)
    if request.status != AttorneyRequestStatus.pending and request.status != requested_status:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "already_decided",
                "message": f"This request was already {request.status.value}.",
            },
        )

    request.status = requested_status
    session.add(request)
    session.commit()
    session.refresh(request)
    return {
        "id": str(request.id),
        "inquiryId": str(request.inquiry_id),
        "attorneyId": str(request.attorney_id),
        "status": request.status.value,
        "createdAt": to_utc_iso(request.created_at),
    }


@router.post("/reports", status_code=201)
def create_report(
    body: ReportCreate,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Any authenticated user can report an inquiry or comment. Validates
    target_id actually exists in the table implied by target_type,
    closing the M1.3-documented API-layer gap that table's own polymorphic
    target_type/target_id design deliberately left to this layer."""
    user = _get_or_create_user(session, current)
    _rate_limit_or_429("reports", user.id)

    if body.target_type not in (ReportTargetType.inquiry.value, ReportTargetType.thread_comment.value):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "validation_error",
                "message": "target_type must be 'inquiry' or 'thread_comment'.",
            },
        )
    not_found = HTTPException(
        status_code=404, detail={"error": "not_found", "message": "Report target not found."}
    )
    target_id = _parse_uuid(body.target_id, not_found)
    target_type = ReportTargetType(body.target_type)

    if target_type == ReportTargetType.inquiry:
        target_exists = session.get(Inquiry, target_id) is not None
    else:
        target_exists = session.get(ThreadComment, target_id) is not None
    if not target_exists:
        raise not_found

    report = Report(
        target_type=target_type,
        target_id=target_id,
        reporter_id=user.id,
        reason=body.reason,
    )
    session.add(report)
    session.commit()
    session.refresh(report)
    return {
        "id": str(report.id),
        "targetType": report.target_type.value,
        "targetId": str(report.target_id),
        "reason": report.reason,
        "status": report.status.value,
        "createdAt": to_utc_iso(report.created_at),
    }
