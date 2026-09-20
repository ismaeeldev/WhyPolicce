"""evidence_attachments table — forum rebuild, Milestone 1 Step M1.3
(WhyPoliceForum_MasterGuide.md). Links uploaded files to an inquiry and
is the record the tier-based file/size limits are enforced against —
the actual enforcement logic lives in the API layer (M1.4's tier-limit
checks, M3.1's real GCS upload flow), not as a DB-level constraint.

Enforced limits (checked at write time in the API layer, not here):
free tier — 1 file / 5MB total per inquiry. Expanded tier — up to 5
files / 50MB total per inquiry.
"""

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlalchemy import ForeignKey
from sqlmodel import Column, DateTime, Field, SQLModel


class FileType(str, Enum):
    image = "image"
    video = "video"
    document = "document"


class EvidenceAttachment(SQLModel, table=True):
    __tablename__ = "evidence_attachments"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # ondelete="CASCADE" — see app/models/inquiry.py's ThreadComment.inquiry_id
    # for the real bug (unhandled 500 on delete_inquiry, found by
    # Milestone 1's Final Master Testing gate) this fixes identically here.
    inquiry_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("inquiries.id", ondelete="CASCADE"), index=True)
    )
    # Populated after a real GCS signed-URL upload completes (M3.1) — a
    # row is only ever created once the upload is confirmed, never before,
    # so there's no such thing as an "attachment" row referencing a file
    # that was never actually uploaded.
    file_url: str
    file_type: FileType
    size_bytes: int
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
