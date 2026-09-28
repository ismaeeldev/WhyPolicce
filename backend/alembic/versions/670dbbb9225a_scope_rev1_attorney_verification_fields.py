"""scope_rev1_attorney_verification_fields

Revision ID: 670dbbb9225a
Revises: e5061273731a
Create Date: 2026-09-27 00:00:00.000000

Scope Revision 1 §5.1/§5.3 (AgentGuide/newscoperev1.md) — three new
attorney-application columns (legal_first_name, legal_last_name,
firm_email_address, confirmed genuinely new, not a rename of anything
existing) plus a composite unique constraint on
(verified_bar_no, bar_jurisdiction) so the same real bar number can't be
registered twice under the same state, while still allowing the same
number under two different states (a bar number is only unique within
its own state's numbering scheme, not globally).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '670dbbb9225a'
down_revision: Union[str, Sequence[str], None] = 'e5061273731a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('legal_first_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('legal_last_name', sa.String(), nullable=True))
    op.add_column('users', sa.Column('firm_email_address', sa.String(), nullable=True))
    op.create_unique_constraint(
        'uq_users_bar_no_jurisdiction', 'users', ['verified_bar_no', 'bar_jurisdiction']
    )


def downgrade() -> None:
    op.drop_constraint('uq_users_bar_no_jurisdiction', 'users', type_='unique')
    op.drop_column('users', 'firm_email_address')
    op.drop_column('users', 'legal_last_name')
    op.drop_column('users', 'legal_first_name')
