"""inquiries / thread_comments tables — forum rebuild, Milestone 1 Step
M1.2 (WhyPoliceForum_MasterGuide.md). The core content model of the new
public-forum product: a citizen-submitted Inquiry, discussed via
ThreadComment rows underneath it.

Privacy rule (non-negotiable, from WhyPolice-Scope-Realignment.pdf):
nothing in this file stores a citizen's raw phone number or private
email — an author's contact info lives only on the existing
users.email (Auth0-sourced), and no future serializer/response schema
may expose it in a public inquiry or comment response. Do not add a
"contact_phone"/"contact_email" field to Inquiry or ThreadComment
without re-reading this rule and the scope PDF's own privacy section
first — the gated Request Consultation flow (attorney_request.py) is
the ONLY sanctioned path for an attorney to reach a citizen.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import ForeignKey
from sqlmodel import Column, DateTime, Enum as SAEnum, Field, SQLModel


class StatusTag(str, Enum):
    community_trace = "community_trace"
    awaiting_police_statement = "awaiting_police_statement"


class InquiryTier(str, Enum):
    """Citizen tiering (client's own follow-up answer, locked in after the
    initial scope sign-off): free posts are capped at 250 characters
    (enforced server-side in M1.4, not here — this column just records
    which tier a given inquiry was submitted/upgraded under), expanded
    posts unlock the full length via the $2.99 one-time Stripe checkout
    (M3.2).

    Real, live-database-verified bug avoided, not just a theoretical
    naming worry: an earlier draft of this class was named plain `Tier`,
    matching app.models.user.Tier's own name. SQLModel/SQLAlchemy name a
    Postgres ENUM TYPE after the Python class name by default, and this
    project's live database ALREADY HAS a real `tier` enum type from
    User.tier, with values ('free', 'pro') — completely different values
    from this class's ('free', 'expanded'). A same-named-but-different-
    values enum here would have collided with that real, existing
    database object the moment a migration tried to create it (confirmed
    by directly querying pg_type/pg_enum on the live database before
    writing this class this way, not assumed). Renamed to InquiryTier,
    with an explicit sa_column Enum name below, so the two concepts (a
    citizen's post-length tier vs. an account's subscription tier) are
    unambiguous both in Python and as two distinct, correctly-separate
    Postgres types — never conflate the two or try to reuse
    app.models.user.Tier here."""

    free = "free"
    expanded = "expanded"


class Inquiry(SQLModel, table=True):
    __tablename__ = "inquiries"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    author_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    title: str
    description: str
    # 2-letter USPS code (e.g. "NY", "CA") — validated at the API layer in
    # M1.4, not enforced as a DB-level CHECK constraint in this milestone.
    # Deliberately NOT reusing the old RAG product's supported_states()/
    # State Selector coverage list here or anywhere else in the new
    # product — see WhyPoliceForum_MasterGuide.md M2.3's own explicit
    # warning: that list only covers the ~32 states the OLD product had
    # ingested data for, and this new product is nationwide from day one.
    state: str
    city: str
    precinct: str | None = Field(default=None)
    status_tag: StatusTag
    # sa_column's explicit Enum name ("inquiry_tier", not the default
    # "inquirytier" SQLAlchemy would derive, and NOT "tier" — see
    # InquiryTier's own docstring for the real collision that name would
    # cause against the already-existing users.tier Postgres enum type).
    tier: InquiryTier = Field(
        default=InquiryTier.free,
        sa_column=Column(SAEnum(InquiryTier, name="inquiry_tier")),
    )
    # Denormalized counter only — the real per-user follow records live in
    # inquiry_follows (M1.3). This field alone cannot answer "does user X
    # follow this inquiry," which M1.4/M2.2 both need via a separate query
    # against that table. Updated via a real atomic increment/decrement in
    # M1.4's follow/unfollow endpoints, never via a read-then-write.
    follower_count: int = Field(default=0)
    # See app/models/user.py's own comment on created_at for why
    # sa_column=Column(DateTime(timezone=True)) is required, not cosmetic —
    # the same real "5 hours ago" timestamp bug this project already found
    # and fixed once on the old product applies identically here.
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )


class ThreadComment(SQLModel, table=True):
    __tablename__ = "thread_comments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # ondelete="CASCADE": a citizen can delete their own inquiry at any
    # time with no time limit (client's explicit answer, M1.4) — real gap
    # found by Milestone 1's own Final Master Testing gate, live against
    # the real dev database: deleting an inquiry that already had a real
    # comment on it (the exact scenario that gate's own Full User Journey
    # walkthrough exercises) raised an unhandled 500
    # (psycopg2.errors.ForeignKeyViolation), not a clean response, because
    # this FK previously had no ondelete policy at all (Postgres's
    # implicit NO ACTION/restrict default). Cascading here — rather than
    # the app catching a restrict violation and rejecting the delete — is
    # the deliberate choice: restricting would make almost every inquiry
    # with any real engagement permanently undeletable, contradicting the
    # client's own "delete anytime" answer.
    inquiry_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("inquiries.id", ondelete="CASCADE"), index=True)
    )
    author_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    body: str
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
