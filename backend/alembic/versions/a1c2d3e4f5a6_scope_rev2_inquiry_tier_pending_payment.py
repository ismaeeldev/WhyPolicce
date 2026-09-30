"""scope_rev2_inquiry_tier_pending_payment

Revision ID: a1c2d3e4f5a6
Revises: 4f09d809eddf
Create Date: 2026-09-30 00:00:00.000000

Scope Revision 2 §4.1 (AgentGuide/newscoperev2.md) — Option A (save-then-
pay) for the "Pay $2.99 to Publish Full Post" button. Adds a third value
to the existing `inquiry_tier` Postgres enum type (see InquiryTier's own
docstring in app/models/inquiry.py for why this type is named
`inquiry_tier`, never `tier`, to avoid colliding with users.tier's own
distinct enum type).

ALTER TYPE ... ADD VALUE cannot run inside the same transaction as other
schema changes that might use the new value (Postgres restriction, and
Alembic's own documented guidance for this exact operation) — this
migration only adds the enum value and nothing else, so autocommit is
safe here.
"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1c2d3e4f5a6'
down_revision: Union[str, Sequence[str], None] = '4f09d809eddf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE inquiry_tier ADD VALUE IF NOT EXISTS 'pending_payment'")


def downgrade() -> None:
    # Postgres has no "DROP VALUE" for enum types — reversing this would
    # require rebuilding the whole inquiry_tier type (create new type,
    # cast every inquiries.tier value across, drop old type, rename).
    # Not implemented: no migration in this codebase's history does this
    # for any enum, and it's only ever needed for a real rollback where
    # no row has ever used 'pending_payment' — a decision to make at
    # that time, not something to guess safe on now.
    raise NotImplementedError(
        "Cannot drop a value from a Postgres enum type. "
        "See this migration's own module docstring."
    )
