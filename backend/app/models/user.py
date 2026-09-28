"""users table — AgentGuide/02_ApplicationFlow.md §4."""

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Column, DateTime, Field, SQLModel, UniqueConstraint


class Tier(str, Enum):
    free = "free"
    pro = "pro"


class Role(str, Enum):
    """Forum rebuild (WhyPoliceForum_MasterGuide.md M1.2) — the new
    product's two account types. Every existing row (created under the old
    RAG-search product, which had no concept of roles) defaults to
    "citizen" via the column default below, which is the correct
    backward-compatible behavior: nobody who signed up before this rebuild
    was ever an attorney, so there's nothing to backfill."""

    citizen = "citizen"
    attorney = "attorney"


class VerificationStatus(str, Enum):
    """Attorney bar-verification state (M1.2). Deliberately has no
    "not_applicable"/citizen-facing value — a citizen row's
    verification_status column stays NULL, not any enum member, per this
    field's own nullable=True below and M1.2's explicit "must stay
    None/null for citizens" requirement. Set via the admin endpoint built
    in M1.5, not by the user themselves."""

    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class User(SQLModel, table=True):
    __tablename__ = "users"
    # Scope Revision 1 §5.3 (AgentGuide/newscoperev1.md) — a real bar
    # number is only unique WITHIN a given state's own numbering scheme,
    # not globally across all 50 states, so the constraint is composite,
    # not just on verified_bar_no alone. Only enforced when both values
    # are non-null (Postgres's default NULLS DISTINCT behavior), which is
    # correct — a citizen row (both null) must never collide with this
    # constraint. become_attorney() below normalizes (trims + uppercases)
    # both values before writing, so this constraint can't be bypassed by
    # a differently-cased or whitespace-padded duplicate.
    __table_args__ = (
        UniqueConstraint("verified_bar_no", "bar_jurisdiction", name="uq_users_bar_no_jurisdiction"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    auth0_sub: str = Field(unique=True, index=True)
    # Indexed (not unique) — auth0_sub is the real identity key. Some
    # rows have an empty-string email (populated lazily on next login,
    # see app/routers/*.py's _get_or_create_user), so a unique constraint
    # would be violated by real, legitimate data. Indexed only to keep a
    # future by-email lookup (support tooling, admin search) from doing
    # a full table scan.
    email: str = Field(index=True)
    tier: Tier = Field(default=Tier.free)
    stripe_customer_id: str | None = Field(default=None)
    # Forum rebuild (M1.2) — citizen vs. attorney. Every pre-rebuild row
    # correctly defaults to "citizen" (see Role's own docstring above).
    role: Role = Field(default=Role.citizen)
    # Entered at attorney signup (M2.1's "Become an Attorney" flow) —
    # nullable, and must stay null for every citizen row. Not validated
    # against a real state-bar lookup in this milestone (per M1.5's own
    # "frictionless for launch" manual-approval decision) — a human admin
    # reviews these values, the database just stores what was typed.
    verified_bar_no: str | None = Field(default=None)
    # A two-letter US state code (e.g. "NY"), validated against the same
    # canonical state list the frontend's States filter and the New
    # Inquiry form's state field both already use (frontend/lib/us-
    # states.ts's US_STATES) — kept as a plain string column rather than a
    # backend Python enum so there's exactly one source of truth for the
    # 50-state-plus-DC list, not two that could drift apart.
    bar_jurisdiction: str | None = Field(default=None)
    # Scope Revision 1 §5.1 (AgentGuide/newscoperev1.md) — three genuinely
    # new fields (confirmed against this file before adding: no name field
    # existed anywhere in the prior application, the app relied on the
    # Auth0 profile name instead; no firm email field existed at all).
    legal_first_name: str | None = Field(default=None)
    legal_last_name: str | None = Field(default=None)
    firm_email_address: str | None = Field(default=None)
    # Scope Revision 1 §5.5 — client's own wording: "Ensure their
    # firm_email_address matches their professional website domain if
    # provided" — optional, since not every applicant has a firm website
    # to list. A mismatch produces a warning at submission (become_attorney
    # in routers/users.py), not a hard block — email/website domains can
    # legitimately differ for a real firm, so this is a data-quality flag
    # for the admin reviewer, not a rejection reason.
    firm_website: str | None = Field(default=None)
    # Nullable, not defaulted to VerificationStatus.pending — see
    # VerificationStatus's own docstring. Only ever meaningful (non-null)
    # once a citizen actually starts the "Become an Attorney" flow, which
    # is the point at which application code sets this to "pending" for
    # the first time; it is never set at row-creation time for a plain
    # citizen signup.
    verification_status: VerificationStatus | None = Field(default=None)
    # Forum rebuild, Milestone 3 Step M3.2 (WhyPoliceForum_MasterGuide.md).
    # True once the Stripe webhook confirms a real, active $149/month
    # recurring payment; flipped back to False by
    # customer.subscription.deleted / invoice.payment_failed, which
    # actually re-locks M2.4's attorney-portal paywall (previously always
    # False via ATTORNEY_SUBSCRIPTION_ACTIVE_STUB). Deliberately NOT
    # reusing the existing stripe_customer_id/Tier fields above — those
    # belong to the OLD product's separate Stripe account/subscription
    # concept (see app/routers/forum_billing.py's own docstring for why
    # this milestone uses a brand-new Stripe account, per the guide's own
    # explicit Manual Step instruction).
    attorney_subscription_active: bool = Field(default=False)
    forum_stripe_customer_id: str | None = Field(default=None)
    # sa_column=Column(DateTime(timezone=True)) — found the hard way (a real
    # live user's session showed "5 hours ago" moments after creation): the
    # default SQLModel datetime column maps to Postgres's TIMESTAMP WITHOUT
    # TIME ZONE, which silently drops the UTC offset on write. The value read
    # back is a naive datetime, so .isoformat() omits the timezone suffix,
    # and the frontend's `new Date(...)` then parses it as the browser's
    # LOCAL time per the ECMAScript spec — wrong by exactly the viewer's UTC
    # offset. Explicit timezone=True keeps Postgres storing TIMESTAMPTZ, so
    # every read comes back tz-aware and every serialized timestamp carries
    # a real, unambiguous UTC offset.
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
