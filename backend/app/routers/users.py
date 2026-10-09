from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.security import AuthenticatedUser, get_current_user
from app.core.urlutil import normalize_website
from app.services.rate_limit import rate_limit_or_429
from app.models.user import Role, User, VerificationStatus

router = APIRouter()

# Scope Revision 1 §5.2 (AgentGuide/newscoperev1.md) — client's own
# wording: "strictly blocking generic gmail.com or yahoo.com addresses
# for paid accounts". Enforced server-side (not just in the frontend
# form) since the goal is real data integrity, not just UX friction.
GENERIC_EMAIL_DOMAINS = {
    "gmail.com",
    "yahoo.com",
    "outlook.com",
    "hotmail.com",
    "icloud.com",
    "aol.com",
}

# Same 50-states-plus-DC set as frontend/lib/us-states.ts's US_STATES —
# Python can't import a .ts file, so this is a deliberate, intentionally
# duplicated copy for server-side validation. Keep both lists in sync if
# either ever changes (neither is expected to — US states are fixed).
VALID_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL", "GA", "HI",
    "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN",
    "MS", "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH",
    "OK", "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA",
    "WV", "WI", "WY",
}


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
    # A two-letter state code (e.g. "NY") — validated against the same
    # canonical US_STATES list at the router level below, not re-declared
    # as a second enum here, to avoid two lists drifting apart.
    jurisdiction: str = Field(min_length=1, max_length=100)
    # Scope Revision 1 §5.1 — three new required fields (client's follow-up
    # message: legal_first_name, legal_last_name, firm_email_address).
    legal_first_name: str = Field(min_length=1, max_length=100)
    legal_last_name: str = Field(min_length=1, max_length=100)
    firm_email_address: str = Field(min_length=1, max_length=254)
    # Scope Revision 1 §5.5 — optional, client's own wording: "if
    # provided". No min_length, since an empty string/omitted field must
    # be treated as "not provided", not a validation error.
    firm_website: str | None = Field(default=None, max_length=254)


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
    is already an APPROVED attorney, since silently overwriting a real
    admin decision with a brand-new "pending" state would erase that
    decision without anyone asking for it to be reconsidered.

    Real gap found during a full-scope re-audit: a REJECTED attorney had
    no path back at all — this used to 400 "already_decided" the exact
    same way for rejected as for approved, a genuine dead end flagged as
    an open product question in the build guide and never resolved. A
    rejected applicant deserves the chance to reapply (e.g. with
    corrected bar info, or after actually passing the bar since their
    first attempt) — resubmitting moves them back to "pending" for a
    real admin to re-review, same as the pending-resubmission case
    above. Only an already-APPROVED attorney is still blocked, since
    that's the one case where silently discarding a real decision would
    be wrong.
    """
    user = _get_or_create_user(session, current)
    rate_limit_or_429("become-attorney", user.id)

    if user.role == Role.attorney and user.verification_status == VerificationStatus.approved:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "already_decided",
                "message": "This account's attorney application was already approved.",
            },
        )

    # §5.1 — jurisdiction is now a fixed state code, not free text; reject
    # anything outside the real 50-states-plus-DC set rather than silently
    # storing a typo the admin reviewer would have to catch by hand.
    jurisdiction = body.jurisdiction.strip().upper()
    if jurisdiction not in VALID_STATE_CODES:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_jurisdiction",
                "message": "Jurisdiction must be a valid US state or DC.",
            },
        )

    # §5.2 — client's own wording: block generic email providers at
    # submission time, not deferred to admin review (an applicant who
    # tries to submit with a personal address gets immediate, actionable
    # feedback instead of a silent rejection later).
    email_domain = body.firm_email_address.strip().lower().rsplit("@", 1)[-1]
    if email_domain in GENERIC_EMAIL_DOMAINS:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "generic_email_domain",
                "message": "Please use your firm's work email address, not a personal email provider.",
            },
        )

    # §5.3 — normalize before the uniqueness check so an untrimmed or
    # differently-cased duplicate can't slip past the DB constraint (e.g.
    # " ny1234567 " vs "NY1234567" would otherwise look distinct).
    bar_no = body.bar_no.strip().upper()

    # §5.5 — client's own wording: "Ensure their firm_email_address
    # matches their professional website domain if provided." A mismatch
    # is a warning surfaced back to the applicant, not a hard block — a
    # real firm can legitimately use a different domain for email vs.
    # website (e.g. a vanity marketing domain), so rejecting outright
    # would block legitimate applicants over a non-fatal inconsistency.
    firm_website = normalize_website(body.firm_website)
    if body.firm_website and body.firm_website.strip() and firm_website is None:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "invalid_website",
                "message": "Enter a valid website address, like yourfirm.com.",
            },
        )
    domain_mismatch_warning: str | None = None
    if firm_website:
        website_domain = urlparse(
            firm_website if "://" in firm_website else f"https://{firm_website}"
        ).netloc.lower().removeprefix("www.")
        if website_domain and website_domain != email_domain:
            domain_mismatch_warning = (
                "Your firm email and website domains don't match — this is fine if "
                "your firm genuinely uses different domains, but double-check for a typo."
            )

    user.role = Role.attorney
    user.verified_bar_no = bar_no
    user.bar_jurisdiction = jurisdiction
    user.legal_first_name = body.legal_first_name.strip()
    user.legal_last_name = body.legal_last_name.strip()
    user.firm_email_address = body.firm_email_address.strip()
    user.firm_website = firm_website
    user.verification_status = VerificationStatus.pending
    session.add(user)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        # Real bug found running the actual test suite (SQLite, used in
        # tests, vs. Postgres, used in production): the two dialects
        # phrase a unique-constraint violation completely differently —
        # Postgres includes the constraint name itself
        # ("uq_users_bar_no_jurisdiction"), SQLite instead names the
        # columns ("UNIQUE constraint failed: users.verified_bar_no,
        # users.bar_jurisdiction"). Checking for either substring instead
        # of only the constraint name makes this correct under both.
        error_text = str(exc.orig)
        if "uq_users_bar_no_jurisdiction" in error_text or (
            "verified_bar_no" in error_text and "bar_jurisdiction" in error_text
        ):
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "duplicate_bar_registration",
                    "message": "This bar number is already registered to another account.",
                },
            ) from exc
        raise
    session.refresh(user)

    return {
        "role": user.role.value,
        "verificationStatus": user.verification_status.value,
        "domainMismatchWarning": domain_mismatch_warning,
    }
