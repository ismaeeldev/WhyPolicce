"""m3_2_add_processed_stripe_events

Revision ID: cebc102f99e1
Revises: 392a7b6f1a32
Create Date: 2026-09-22 00:51:26.459097

Forum rebuild, Milestone 3 Step M3.2 (WhyPoliceForum_MasterGuide.md).
Stripped of autogenerate's usual unwanted noise (see the previous
migration's own docstring for the recurring public_records/inquiry_id
churn this project's autogenerate always produces).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cebc102f99e1'
down_revision: Union[str, Sequence[str], None] = '392a7b6f1a32'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'processed_stripe_events',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('stripe_event_id', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_processed_stripe_events_stripe_event_id'),
        'processed_stripe_events',
        ['stripe_event_id'],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_processed_stripe_events_stripe_event_id'), table_name='processed_stripe_events')
    op.drop_table('processed_stripe_events')
