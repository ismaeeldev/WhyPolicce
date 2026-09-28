"""scope_rev1_inquiry_is_anonymous

Revision ID: 7f28c337e9c2
Revises: 670dbbb9225a
Create Date: 2026-09-27 00:00:00.000000

Scope Revision 1 §4.3 (AgentGuide/newscoperev1.md) — "Post Anonymously to
Public Feed" checkbox. Display-only flag; the real author_id is always
recorded, never anonymized in the database itself (see the column's own
comment on the Inquiry model).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7f28c337e9c2'
down_revision: Union[str, Sequence[str], None] = '670dbbb9225a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'inquiries',
        sa.Column('is_anonymous', sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column('inquiries', 'is_anonymous')
