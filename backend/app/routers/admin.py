"""Admin attorney verification + report review endpoints — Milestone 1
Step M1.5 (WhyPoliceForum_MasterGuide.md).

A deliberately minimal admin gate for Milestone 1 (see
app.core.config.Settings.ADMIN_AUTH0_SUBS's own docstring) — a hardcoded
allowlist, not a full role-based admin system. Also closes a real gap
this guide's own deep audit found: POST /api/v1/reports (M1.4) let
anyone create a report, but nothing anywhere ever let a human review or
resolve one, making the client's own "rely on community flags instead of
pre-moderation" answer aspirational rather than real.
"""

import uuid

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, func, select

from app.core.config import settings
from app.core.db import get_session
from app.core.security import AuthenticatedUser, get_current_user
from app.core.timeutil import to_utc_iso
from app.models.inquiry import Inquiry, ThreadComment
from app.models.report import Report, ReportStatus, ReportTargetType
from app.models.user import Role, User, VerificationStatus

router = APIRouter(prefix="/api/v1/admin")

_DEFAULT_PAGE_SIZE = 20
_MAX_PAGE_SIZE = 100

_FORBIDDEN = HTTPException(
    status_code=403, detail={"error": "forbidden", "message": "Admin access required."}
)


def _parse_uuid(raw: str, not_found: HTTPException) -> uuid.UUID:
    """Duplicated from app/routers/inquiries.py rather than imported —
    same reasoning this codebase already established for
    _get_or_create_user across search.py/memory.py/inquiries.py: a small
    per-router duplication, not a cross-router private import."""
    try:
        return uuid.UUID(raw)
    except (ValueError, AttributeError, TypeError):
        raise not_found from None


class AttorneyVerifyDecision(BaseModel):
    decision: str  # "approved" | "rejected"


class ReportReviewDecision(BaseModel):
    decision: str  # "resolved" | "dismissed"


def _require_admin(session: Session, current: AuthenticatedUser) -> User:
    """The admin gate itself. Looks up (does not create) the calling
    user — an admin must already exist as a real User row (created the
    normal way, on their first authenticated call to any other endpoint)
    before this check can even run; this function deliberately does not
    call _get_or_create_user, since silently creating a user row as a
    side effect of an authorization check would be a strange, surprising
    behavior for a security-relevant function to have."""
    if current.auth0_sub not in settings.admin_auth0_subs:
        raise _FORBIDDEN
    user = session.exec(select(User).where(User.auth0_sub == current.auth0_sub)).first()
    if user is None:
        # An allowlisted admin sub with no User row yet (never called any
        # other endpoint first) — treat the same as forbidden rather than
        # creating a row here; a real admin should exist via the normal
        # signup path before ever reaching an admin action.
        raise _FORBIDDEN
    return user


@router.post("/attorneys/{user_id}/verify")
def verify_attorney(
    user_id: str,
    body: AttorneyVerifyDecision,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    _require_admin(session, current)

    if body.decision not in (VerificationStatus.approved.value, VerificationStatus.rejected.value):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "validation_error",
                "message": "decision must be 'approved' or 'rejected'.",
            },
        )

    not_found = HTTPException(
        status_code=404, detail={"error": "not_found", "message": "User not found."}
    )
    target = session.get(User, _parse_uuid(user_id, not_found))
    if target is None:
        raise not_found
    if target.role != Role.attorney:
        # Approving/rejecting a citizen makes no sense and must never
        # silently succeed — a real, deliberate 400, not a no-op.
        raise HTTPException(
            status_code=400,
            detail={
                "error": "not_an_attorney",
                "message": "This user is not an attorney account.",
            },
        )

    # Idempotent: re-applying the same decision succeeds harmlessly (an
    # admin re-clicking the same action, or two admins acting on the same
    # attorney near-simultaneously, is normal usage, not an error) — the
    # exact same rule this guide applies everywhere the same shape of
    # problem recurs (Standing Implementation Discipline rule 8), which
    # M1.4's own consultation-response endpoint already follows too.
    target.verification_status = VerificationStatus(body.decision)
    session.add(target)
    session.commit()
    session.refresh(target)
    return {"id": str(target.id), "verificationStatus": target.verification_status.value}


@router.get("/me")
def get_admin_me(
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Real gap found building the admin panel: the frontend needs a way
    to ask "is the signed-in user actually an admin?" that returns a
    clean, real boolean rather than the frontend inferring admin status
    from whether some OTHER admin-only call happened to 403 — a fragile,
    indirect way to gate an entire route. Deliberately does not leak
    WHO else is on the allowlist; only confirms the caller's own status.
    Never raises _FORBIDDEN itself — a non-admin gets a real 200 with
    isAdmin: false, so the frontend can render a clear "not authorized"
    page instead of treating this specific check as a hard error."""
    is_admin = current.auth0_sub in settings.admin_auth0_subs
    if not is_admin:
        return {"isAdmin": False}
    user = session.exec(select(User).where(User.auth0_sub == current.auth0_sub)).first()
    return {"isAdmin": user is not None, "email": user.email if user else None}


@router.get("/dashboard")
def get_admin_dashboard(
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Summary counts for the admin panel's own landing screen — real
    aggregate queries, not the frontend fetching every list just to
    count its length."""
    _require_admin(session, current)

    pending_attorneys = session.exec(
        select(func.count()).select_from(
            select(User)
            .where(User.role == Role.attorney, User.verification_status == VerificationStatus.pending)
            .subquery()
        )
    ).one()
    approved_attorneys = session.exec(
        select(func.count()).select_from(
            select(User)
            .where(User.role == Role.attorney, User.verification_status == VerificationStatus.approved)
            .subquery()
        )
    ).one()
    rejected_attorneys = session.exec(
        select(func.count()).select_from(
            select(User)
            .where(User.role == Role.attorney, User.verification_status == VerificationStatus.rejected)
            .subquery()
        )
    ).one()
    open_reports = session.exec(
        select(func.count()).select_from(select(Report).where(Report.status == ReportStatus.open).subquery())
    ).one()
    return {
        "pendingAttorneys": pending_attorneys,
        "approvedAttorneys": approved_attorneys,
        "rejectedAttorneys": rejected_attorneys,
        "openReports": open_reports,
    }


def _attorney_out(u: User) -> dict:
    return {
        "id": str(u.id),
        "email": u.email,
        "verifiedBarNo": u.verified_bar_no,
        "barJurisdiction": u.bar_jurisdiction,
        "verificationStatus": u.verification_status.value if u.verification_status else None,
        "createdAt": to_utc_iso(u.created_at),
    }


@router.get("/attorneys")
def list_attorneys(
    status: str | None = Query(default=None),
    limit: int = Query(default=_DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Real gap found building the admin panel's own Pending/Approved
    tabs: list_pending_attorneys only ever supported the pending case —
    there was no way to see already-approved (or rejected) attorneys at
    all. One endpoint, filterable by `status`, replaces it; omitting
    `status` returns every attorney account regardless of status. Newest
    first, so a freshly-applied attorney surfaces at the top of the
    admin's own Pending tab without them needing to page through."""
    _require_admin(session, current)

    statement = select(User).where(User.role == Role.attorney)
    if status:
        if status not in (
            VerificationStatus.pending.value,
            VerificationStatus.approved.value,
            VerificationStatus.rejected.value,
        ):
            raise HTTPException(
                status_code=422,
                detail={
                    "error": "validation_error",
                    "message": "status must be 'pending', 'approved', or 'rejected'.",
                },
            )
        statement = statement.where(User.verification_status == VerificationStatus(status))

    total = session.exec(select(func.count()).select_from(statement.subquery())).one()
    rows = session.exec(
        statement.order_by(User.created_at.desc()).offset(offset).limit(limit)
    ).all()
    return {
        "items": [_attorney_out(u) for u in rows],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/attorneys/pending")
def list_pending_attorneys(
    limit: int = Query(default=_DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Kept as a thin wrapper around list_attorneys(status="pending") for
    backward compatibility — nothing in this codebase calls this
    directly anymore (the admin panel uses list_attorneys), but removing
    a real, working endpoint outright rather than deprecating it is an
    avoidable breaking change for zero benefit."""
    return list_attorneys(status="pending", limit=limit, offset=offset, current=current, session=session)


def _report_target_summary(session: Session, report: Report) -> dict | None:
    """Inlines enough of the reported content for a human reviewer to
    actually make a decision without a second lookup — per M1.5's own
    Master Prompt requirement. Returns None if the target was deleted by
    its own author after the report was filed (a real, accepted
    consequence of the polymorphic target_type/target_id design M1.3's
    own docstring documents) — the report is still reviewable/closeable
    even when this happens, per this same file's own adversarial test."""
    if report.target_type == ReportTargetType.inquiry:
        target = session.get(Inquiry, report.target_id)
        if target is None:
            return None
        return {"title": target.title, "description": target.description}
    target = session.get(ThreadComment, report.target_id)
    if target is None:
        return None
    return {"body": target.body}


@router.get("/reports")
def list_open_reports(
    limit: int = Query(default=_DEFAULT_PAGE_SIZE, ge=1, le=_MAX_PAGE_SIZE),
    offset: int = Query(default=0, ge=0),
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    _require_admin(session, current)

    statement = select(Report).where(Report.status == ReportStatus.open)
    total = session.exec(select(func.count()).select_from(statement.subquery())).one()
    rows = session.exec(statement.order_by(Report.created_at.asc()).offset(offset).limit(limit)).all()
    return {
        "items": [
            {
                "id": str(r.id),
                "targetType": r.target_type.value,
                "targetId": str(r.target_id),
                "reason": r.reason,
                "reporterId": str(r.reporter_id),
                "status": r.status.value,
                "createdAt": to_utc_iso(r.created_at),
                "target": _report_target_summary(session, r),
            }
            for r in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.patch("/reports/{report_id}")
def review_report(
    report_id: str,
    body: ReportReviewDecision,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Only closes the report record itself — deliberately does NOT
    delete/hide the reported content (that remains the content owner's
    own edit/delete action, or a future, not-yet-scoped admin
    content-removal capability). Same idempotency rule as
    verify_attorney/M1.4's consultation-response: re-applying the same
    decision succeeds harmlessly; requesting the OTHER decision on an
    already-decided report is a real 400 conflict via this guide's
    canonical error shape."""
    _require_admin(session, current)

    if body.decision not in (ReportStatus.resolved.value, ReportStatus.dismissed.value):
        raise HTTPException(
            status_code=422,
            detail={
                "error": "validation_error",
                "message": "decision must be 'resolved' or 'dismissed'.",
            },
        )

    not_found = HTTPException(
        status_code=404, detail={"error": "not_found", "message": "Report not found."}
    )
    report = session.get(Report, _parse_uuid(report_id, not_found))
    if report is None:
        raise not_found

    requested_status = ReportStatus(body.decision)
    if report.status != ReportStatus.open and report.status != requested_status:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "already_decided",
                "message": f"This report was already {report.status.value}.",
            },
        )

    report.status = requested_status
    session.add(report)
    session.commit()
    session.refresh(report)
    return {
        "id": str(report.id),
        "status": report.status.value,
    }
