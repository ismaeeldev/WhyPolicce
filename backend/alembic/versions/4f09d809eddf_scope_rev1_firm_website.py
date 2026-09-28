"""scope_rev1_firm_website

Revision ID: 4f09d809eddf
Revises: 7f28c337e9c2
Create Date: 2026-09-27 00:00:00.000000

Scope Revision 1 §5.5 (AgentGuide/newscoperev1.md) — optional firm-website
field, used only to cross-check against firm_email_address's domain "if
provided" per the client's own wording. Not required, no other current use.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4f09d809eddf'
down_revision: Union[str, Sequence[str], None] = '7f28c337e9c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('firm_website', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'firm_website')
