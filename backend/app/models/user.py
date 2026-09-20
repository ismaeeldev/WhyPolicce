"""users table — AgentGuide/02_ApplicationFlow.md §4."""

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Column, DateTime, Field, SQLModel


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

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    auth0_sub: str = Field(unique=True, index=True)
    email: str
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
    bar_jurisdiction: str | None = Field(default=None)
    # Nullable, not defaulted to VerificationStatus.pending — see
    # VerificationStatus's own docstring. Only ever meaningful (non-null)
    # once a citizen actually starts the "Become an Attorney" flow, which
    # is the point at which application code sets this to "pending" for
    # the first time; it is never set at row-creation time for a plain
    # citizen signup.
    verification_status: VerificationStatus | None = Field(default=None)
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
