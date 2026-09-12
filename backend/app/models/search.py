"""search_sessions / search_messages tables — AgentGuide/02_ApplicationFlow.md §4."""

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlmodel import JSON, Column, DateTime, Field, SQLModel


class MessageRole(str, Enum):
    user = "user"
    assistant = "assistant"


class SearchSession(SQLModel, table=True):
    __tablename__ = "search_sessions"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(foreign_key="users.id", index=True)
    title: str
    # See app/models/user.py's comment on `created_at` — timezone=True is
    # required, not cosmetic, to avoid a real relative-timestamp bug.
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )


class SearchMessage(SQLModel, table=True):
    __tablename__ = "search_messages"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    session_id: uuid.UUID = Field(foreign_key="search_sessions.id", index=True)
    role: MessageRole
    content: str
    is_deep_search: bool = Field(default=False)
    # JSON rather than Postgres's native ARRAY(UUID) — this list is only ever
    # read back whole for display (the "Memory referenced" line, per
    # 00_SCOPE.md §2.3), never queried by individual element, so a portable
    # JSON column is simpler and works identically on Neon/Postgres and the
    # local SQLite database used for Step 4's code-level testing (see
    # AgentGuide/05_PROJECT_STATE.md — no live Neon connection available yet).
    memory_note_ids: list[str] | None = Field(default=None, sa_column=Column(JSON))
    # Real source citations for an assistant answer — a list of
    # {"city": ..., "source": ...} dicts built by
    # search_service._build_citations from the actual PublicRecord rows
    # retrieved for this answer (see stream_answer's sources_out param).
    # Same JSON-column reasoning as memory_note_ids above: read back whole
    # for display, never queried by individual element. Always None for a
    # user-role message (only ever set when persisting the assistant
    # reply) and empty/None when retrieval found nothing relevant, same
    # "absence must be invisible" rule the memory citation line already
    # follows.
    sources: list[dict] | None = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
