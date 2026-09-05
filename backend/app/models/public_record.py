"""public_records table — Revision 2 (RAG pipeline), AgentGuide/revision2.md Phase 1.

Stores ingested public safety records (e.g. NYC Open Data NYPD complaint/
arrest datasets) with a pgvector embedding for semantic similarity search.
`external_id` is the source system's own record id (e.g. Socrata's
`cmplnt_num`/`arrest_key`) so a re-sync can upsert by that value instead of
duplicating rows on every scheduled run.

Embedding dimension is 1536 to match OpenAI's `text-embedding-3-small`
(see app/services/embedding_service.py) — if the embedding model ever
changes to one with a different output size, this column's dimension must
be migrated too, not just the model id in config.
"""

import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlmodel import Column, DateTime, Field, SQLModel
from sqlalchemy import JSON, UniqueConstraint


class PublicRecord(SQLModel, table=True):
    __tablename__ = "public_records"
    __table_args__ = (
        # A given source's external_id must be unique so a re-sync updates
        # the existing row instead of inserting a duplicate every run.
        UniqueConstraint("source", "external_id", name="uq_public_records_source_external_id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)

    # e.g. "nyc_nypd_complaint" / "nyc_nypd_arrest" — lets us filter/report
    # by dataset and scale to more cities/sources later without a schema change.
    source: str = Field(index=True)

    # The source system's own record id (Socrata's cmplnt_num/arrest_key) —
    # required for the upsert-on-resync behavior described above.
    external_id: str = Field(index=True)

    city: str = Field(index=True)

    # Human-readable chunked summary — this is what actually gets embedded
    # and later shown/cited in an answer, not the raw JSON blob.
    raw_text: str

    # Original record as returned by the source API, kept for citation/audit
    # and so a future re-summarization doesn't need to re-fetch from source.
    raw_json: dict = Field(sa_column=Column(JSON))

    # pgvector column — see module docstring for the dimension note.
    embedding: list[float] = Field(sa_column=Column(Vector(1536)))

    # See app/models/memory.py's identical comment: timezone=True is
    # required, not cosmetic, per the real relative-timestamp bug already
    # found and fixed once in this project (05_PROJECT_STATE.md).
    ingested_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
