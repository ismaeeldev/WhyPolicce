"""reports table — forum rebuild, Milestone 1 Step M1.3
(WhyPoliceForum_MasterGuide.md). Supports "publish immediately, rely on
community flags" instead of a pre-moderation queue (the client's own
explicit answer on moderation).

target_type/target_id is intentionally NOT a strict foreign key to
either inquiries or thread_comments, since it can point at either —
this is a deliberate polymorphic-reference tradeoff: the API layer
(M1.4's POST /api/v1/reports) is responsible for validating that
target_id actually exists in the table implied by target_type, not the
database. A real, accepted consequence of this tradeoff: a report can
end up pointing at content that gets deleted by its own author after
the report was filed — M1.5's report-review endpoint is built to
handle that gracefully, not to assume it can never happen.

status starts "open" (the real gap this field closes, found during
this guide's own deep audit): without it, a report created via POST
/api/v1/reports had no way to ever be reviewed or resolved, making the
client's "rely on community flags" moderation strategy aspirational
rather than real. M1.5 adds the admin endpoints that move a report out
of "open."
"""

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Column, DateTime, Field, SQLModel


class ReportTargetType(str, Enum):
    inquiry = "inquiry"
    thread_comment = "thread_comment"


class ReportStatus(str, Enum):
    open = "open"
    resolved = "resolved"
    dismissed = "dismissed"


class Report(SQLModel, table=True):
    __tablename__ = "reports"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    target_type: ReportTargetType
    target_id: uuid.UUID
    reporter_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    reason: str
    status: ReportStatus = Field(default=ReportStatus.open)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
