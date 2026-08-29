"""memory_notes table — AgentGuide/02_ApplicationFlow.md §4, Step 6.5."""

import uuid
from datetime import datetime, timezone

from sqlmodel import Column, DateTime, Field, SQLModel


class MemoryNote(SQLModel, table=True):
    __tablename__ = "memory_notes"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    content: str
    # See app/models/user.py's comment on `created_at` — timezone=True is
    # required, not cosmetic, to avoid a real relative-timestamp bug.
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
