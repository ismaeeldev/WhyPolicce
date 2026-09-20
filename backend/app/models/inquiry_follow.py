"""inquiry_follows table — forum rebuild, Milestone 1 Step M1.3
(WhyPoliceForum_MasterGuide.md).

A real, live schema gap found and fixed during this guide's own deep
audit: `inquiries.follower_count` (M1.2) is only a denormalized COUNT —
nothing recorded WHICH users follow WHICH inquiries. Without this
table, the product cannot know whether the current viewer has already
followed an inquiry (needed for the feed's Follow/Following button
state), cannot prevent one user from incrementing the count more than
once, and the email-alerts feature (M3.3) has no rows to query for
"everyone following this inquiry."
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey
from sqlmodel import Column, DateTime, Field, SQLModel, UniqueConstraint


class InquiryFollow(SQLModel, table=True):
    __tablename__ = "inquiry_follows"
    __table_args__ = (
        # One user can only follow a given inquiry once, enforced at the
        # database level — the same real-race-condition reasoning as
        # AttorneyRequest's own unique constraint. This is what makes
        # M1.4's follow/unfollow endpoints' idempotent-no-op behavior
        # (WhyPoliceForum_MasterGuide.md Standing Implementation
        # Discipline rule 8) actually safe against concurrent requests,
        # not just correct in the common case.
        UniqueConstraint("inquiry_id", "user_id", name="uq_inquiry_follows_inquiry_user"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # ondelete="CASCADE" — real bug found by Milestone 1's Final Master
    # Testing gate, live against the real dev database: deleting an
    # inquiry that already had a real follower (the exact scenario that
    # gate's own Full User Journey walkthrough exercises) raised an
    # unhandled 500 (psycopg2.errors.ForeignKeyViolation), not a clean
    # response, because this FK previously had no ondelete policy
    # (Postgres's implicit restrict default). Cascading — rather than the
    # app catching a restrict violation and rejecting the delete — is the
    # deliberate choice: restricting would make almost every followed
    # inquiry permanently undeletable, contradicting the client's own
    # "delete anytime, no time limit" answer. Applied identically to
    # ThreadComment/EvidenceAttachment/AttorneyRequest's own FKs into
    # inquiries.id (see their own models for the same comment).
    inquiry_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("inquiries.id", ondelete="CASCADE"), index=True)
    )
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
