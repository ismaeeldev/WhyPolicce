from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.security import AuthenticatedUser, get_current_user
from app.models.user import Role, User, VerificationStatus

router = APIRouter()


def _get_or_create_user(session: Session, current: AuthenticatedUser) -> User:
    """Duplicated per this codebase's own established convention (see
    app/routers/inquiries.py's own comment on this exact pattern) rather
    than importing get_me's inline logic — this router needs the same
    sync-on-first-call behavior for become_attorney below, which must
    work even if the frontend hasn't called GET /api/me yet this
    session."""
    user = session.exec(select(User).where(User.auth0_sub == current.auth0_sub)).first()
    if user is None:
        user = User(auth0_sub=current.auth0_sub, email=current.email or "")
        session.add(user)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            user = session.exec(select(User).where(User.auth0_sub == current.auth0_sub)).first()
            if user is None:
                raise
        else:
            session.refresh(user)
    elif current.email and not user.email:
        user.email = current.email
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


@router.get("/api/me")
def get_me(
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """Sync-on-first-call pattern — AgentGuide/02_ApplicationFlow.md §3.2.
    Looks up the user by auth0_sub; creates a row with tier='free' if this is
    their first authenticated request. Never creates a duplicate on repeat calls.

    Race handling: two "first ever" requests for the same auth0_sub can both
    pass the SELECT before either commits. The unique index on auth0_sub
    correctly prevents a duplicate row (verified: raises IntegrityError, never
    silently double-inserts) — but the losing request must still succeed and
    return the winner's row, not bubble up as a 500. See _get_or_create_user
    above (shared within this file only — both endpoints here need the exact
    same sync-on-first-call behavior; this is NOT the same as importing a
    helper cross-router, which this codebase deliberately avoids elsewhere).
    """
    user = _get_or_create_user(session, current)

    return {
        "id": str(user.id),
        "email": user.email,
        "tier": user.tier,
        # Forum rebuild, Milestone 2 Step M2.1 (WhyPoliceForum_MasterGuide.md):
        # extends this existing response rather than adding a second
        # endpoint, so the frontend's role/verification check always rides
        # the same request as the rest of the user's profile data — never
        # a separate loading state to coordinate (per M2.1's own explicit
        # "it rides the same request" UI requirement).
        "role": user.role.value,
        "verificationStatus": user.verification_status.value if user.verification_status else None,
        # Forum rebuild, Milestone 3 Step M3.2 — real, webhook-confirmed
        # attorney subscription state, replacing the frontend's
        # ATTORNEY_SUBSCRIPTION_ACTIVE_STUB placeholder now that this
        # field actually means something.
        "attorneySubscriptionActive": user.attorney_subscription_active,
    }


class BecomeAttorneyRequest(BaseModel):
    bar_no: str = Field(min_length=1, max_length=100)
    jurisdiction: str = Field(min_length=1, max_length=100)


@router.post("/api/me/become-attorney")
def become_attorney(
    body: BecomeAttorneyRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    """The "Become an Attorney" entry point (M2.1) — a citizen account
    submits bar number + jurisdiction and moves into a real
    verification_status="pending" state. Not validated against a real
    state-bar lookup in this milestone (per M1.5's own "frictionless for
    launch, human admin reviews" decision, documented on the User model's
    own verified_bar_no field) — a human admin approves/rejects via the
    M1.5 admin endpoint, this just records what was typed and flips the
    account into the pending state so the M2.1 UI has something real to
    show.

    Idempotent on repeat submission while still pending (same shape of
    problem as every other "re-apply the same action" case in this
    codebase — resubmitting corrected bar info before an admin has acted
    is normal usage, not an error) — but rejects outright if the account
    is already an attorney with a decided (approved/rejected) status,
    since silently overwriting a real admin decision with a brand-new
    "pending" state would erase that decision without anyone asking for
    it to be reconsidered.
    """
    user = _get_or_create_user(session, current)

    if user.role == Role.attorney and user.verification_status in (
        VerificationStatus.approved,
        VerificationStatus.rejected,
    ):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "already_decided",
                "message": f"This account's attorney application was already {user.verification_status.value}.",
            },
        )

    user.role = Role.attorney
    user.verified_bar_no = body.bar_no
    user.bar_jurisdiction = body.jurisdiction
    user.verification_status = VerificationStatus.pending
    session.add(user)
    session.commit()
    session.refresh(user)

    return {
        "role": user.role.value,
        "verificationStatus": user.verification_status.value,
    }
