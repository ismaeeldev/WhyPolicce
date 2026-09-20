"""attorney_requests table — forum rebuild, Milestone 1 Step M1.3
(WhyPoliceForum_MasterGuide.md). The attorney monetization bridge: how a
paying, approved attorney's interest in a citizen's inquiry becomes a
real, tracked record — not the DB layer's concern for who accepts or
declines (that's M1.4's PATCH endpoint), just the table that holds the
state.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import ForeignKey
from sqlmodel import Column, DateTime, Field, SQLModel, UniqueConstraint


class AttorneyRequestStatus(str, Enum):
    pending = "pending"
    accepted = "accepted"
    declined = "declined"


class AttorneyRequest(SQLModel, table=True):
    __tablename__ = "attorney_requests"
    __table_args__ = (
        # An attorney requesting the same inquiry twice is a real, enforced
        # impossibility at the DB level, not just an application-level
        # check a race condition could slip past. See Appendix B item 8 in
        # WhyPoliceForum_MasterGuide.md: this constraint also currently
        # blocks re-requesting after a decline, which is a real, tracked
        # open product question — not silently resolved either way here.
        UniqueConstraint("attorney_id", "inquiry_id", name="uq_attorney_requests_attorney_inquiry"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    attorney_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    # ondelete="CASCADE" — see app/models/inquiry.py's ThreadComment.inquiry_id
    # for the real bug (unhandled 500 on delete_inquiry, found by
    # Milestone 1's Final Master Testing gate) this fixes identically here.
    inquiry_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("inquiries.id", ondelete="CASCADE"), index=True)
    )
    status: AttorneyRequestStatus = Field(default=AttorneyRequestStatus.pending)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
