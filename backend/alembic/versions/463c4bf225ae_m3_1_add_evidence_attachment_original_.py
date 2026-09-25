"""m3_1_add_evidence_attachment_original_filename

Revision ID: 463c4bf225ae
Revises: cebc102f99e1
Create Date: 2026-09-25 00:00:00.000000

Forum rebuild, Milestone 3 Step M3.1 (WhyPoliceForum_MasterGuide.md).
Real gap found during a full-scope re-audit: the GCS object name is
deliberately a random UUID (never the client-supplied filename — path
traversal / collision risk), so the UI had no real filename to display
for an attachment, only that raw UUID. This column is display-only,
nullable so existing rows (uploaded before this column existed) degrade
gracefully rather than backfilling a guess.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '463c4bf225ae'
down_revision: Union[str, Sequence[str], None] = 'cebc102f99e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'evidence_attachments',
        sa.Column('original_filename', sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('evidence_attachments', 'original_filename')
