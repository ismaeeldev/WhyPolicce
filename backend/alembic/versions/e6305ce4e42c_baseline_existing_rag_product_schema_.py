"""baseline: existing RAG-product schema (users, search_sessions, search_messages, public_records, memory_notes)

Revision ID: e6305ce4e42c
Revises: 
Create Date: 2026-09-20 11:46:01.491409

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e6305ce4e42c'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """No-op baseline — see this migration's own docstring above.

    Manually stripped down from autogenerate's real proposal, per
    WhyPoliceForum_MasterGuide.md M1.1's explicit "review before applying,
    autogenerate is a starting point not a guarantee" instruction.
    Autogenerate proposed three real, non-no-op changes here, all rejected:

    1. DROP the ix_public_records_embedding_hnsw index — this is the
       hand-created, performance-critical HNSW vector index from
       app/core/db.py's own create_db_and_tables() (not something
       SQLModel's Field()/Column() can express, per that function's own
       comment), measured to cut warm-cache vector search from ~9.4s to
       ~0.6-1s. Dropping it here would be a real, damaging regression to
       the still-live RAG search feature disguised as a "baseline."
    2. DROP ix_public_records_state — a real index that exists on the live
       database today but isn't declared via index=True on the
       PublicRecord model (app/models/public_record.py only marks `city`,
       `source`, and `external_id` as indexed). This is a genuine,
       pre-existing drift between the live DB and the model class, not
       something this baseline migration should silently resolve one way
       or the other — noted here as a known discrepancy for a future,
       deliberate decision, not fixed by accident inside a migration
       whose whole point is to be a safe, do-nothing starting point.
    3. CREATE ix_public_records_city — autogenerate proposed this because
       it couldn't find a live index matching what it expected for the
       model's own `city` index (it may already exist under a different,
       non-Alembic-generated name, or may never have actually been
       applied) — same reasoning as #2: a real, pre-existing question
       worth its own investigation later, not something to just create
       inside a baseline meant to represent "what's already there."

    This migration is intentionally empty — see M1.1's guide: it exists
    only so `alembic history` has an honest starting point and this
    revision ID is stamped (not applied fresh) against the real database,
    which is already the currently-migrated shape.
    """
    pass


def downgrade() -> None:
    """No-op — see upgrade()'s docstring. Nothing to reverse."""
    pass
