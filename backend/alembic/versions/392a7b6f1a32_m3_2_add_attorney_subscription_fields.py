"""m3_2_add_attorney_subscription_fields

Revision ID: 392a7b6f1a32
Revises: d097927aa079
Create Date: 2026-09-22 00:49:15.996647

Forum rebuild, Milestone 3 Step M3.2 (WhyPoliceForum_MasterGuide.md).
Adds the two real new columns this step needs — stripped of
autogenerate's usual unwanted noise (the recurring public_records index
churn and inquiry_id nullable=True side effects from this project's
known SQLModel/Alembic autogenerate quirk, both already documented in
earlier migrations' own commit history — never a real, intended schema
change here).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '392a7b6f1a32'
down_revision: Union[str, Sequence[str], None] = 'd097927aa079'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column('attorney_subscription_active', sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column('users', sa.Column('forum_stripe_customer_id', sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'forum_stripe_customer_id')
    op.drop_column('users', 'attorney_subscription_active')
