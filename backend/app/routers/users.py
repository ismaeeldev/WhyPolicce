from fastapi import APIRouter, Depends
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.security import AuthenticatedUser, get_current_user
from app.models.user import User

router = APIRouter()


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
    return the winner's row, not bubble up as a 500. Caught and handled below.
    """
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
        # Self-heals rows created before the Auth0 tenant was configured to
        # include an email claim (see app/core/security.py's comment) —
        # without this, a user created while email was unavailable would
        # stay stuck blank forever, since sync-on-first-call only sets it
        # at creation time otherwise.
        user.email = current.email
        session.add(user)
        session.commit()
        session.refresh(user)

    return {"id": str(user.id), "email": user.email, "tier": user.tier}
