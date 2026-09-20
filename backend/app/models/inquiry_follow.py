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
    inquiry_id: uuid.UUID = Field(foreign_key="inquiries.id", index=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
