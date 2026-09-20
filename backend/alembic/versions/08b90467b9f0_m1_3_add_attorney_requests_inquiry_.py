"""M1.3: add attorney_requests, inquiry_follows, evidence_attachments, reports

Revision ID: 08b90467b9f0
Revises: 307ec7214677
Create Date: 2026-09-20 12:14:35.477287

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '08b90467b9f0'
down_revision: Union[str, Sequence[str], None] = '307ec7214677'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Manually corrected from autogenerate's raw draft, same two recurring
    issues already found and fixed for this exact class of migration in
    M1.1 and M1.2 (see those migrations' own docstrings for the first two
    occurrences):

    1. `import sqlmodel` was missing again — same real NameError risk as
       before.
    2. The `public_records` index churn (dropping
       ix_public_records_embedding_hnsw, swapping ix_public_records_state
       for ix_public_records_city) is the exact same pre-existing,
       already-documented drift — not this migration's concern, stripped
       out again here for the third time.

    No enum-name-collision risk this time (the M1.2 lesson) — confirmed
    directly against the live database's pg_type before writing these
    four tables' models: reporttargettype, reportstatus,
    attorneyrequeststatus, and filetype are all genuinely new, non-
    colliding names. No `op.add_column(...)` calls in this migration
    either (every new column here belongs to a brand-new table via
    `op.create_table(...)`, which — confirmed in M1.2 — DOES implicitly
    emit the enum CREATE TYPE correctly on its own), so M1.2's third bug
    (add_column not auto-creating the enum type) does not apply here.
    """
    op.create_table('reports',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('target_type', sa.Enum('inquiry', 'thread_comment', name='reporttargettype'), nullable=False),
    sa.Column('target_id', sa.Uuid(), nullable=False),
    sa.Column('reporter_id', sa.Uuid(), nullable=False),
    sa.Column('reason', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('status', sa.Enum('open', 'resolved', 'dismissed', name='reportstatus'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['reporter_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_reports_reporter_id'), 'reports', ['reporter_id'], unique=False)
    op.create_table('attorney_requests',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('attorney_id', sa.Uuid(), nullable=False),
    sa.Column('inquiry_id', sa.Uuid(), nullable=False),
    sa.Column('status', sa.Enum('pending', 'accepted', 'declined', name='attorneyrequeststatus'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['attorney_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['inquiry_id'], ['inquiries.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('attorney_id', 'inquiry_id', name='uq_attorney_requests_attorney_inquiry')
    )
    op.create_index(op.f('ix_attorney_requests_attorney_id'), 'attorney_requests', ['attorney_id'], unique=False)
    op.create_index(op.f('ix_attorney_requests_inquiry_id'), 'attorney_requests', ['inquiry_id'], unique=False)
    op.create_table('evidence_attachments',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('inquiry_id', sa.Uuid(), nullable=False),
    sa.Column('file_url', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('file_type', sa.Enum('image', 'video', 'document', name='filetype'), nullable=False),
    sa.Column('size_bytes', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['inquiry_id'], ['inquiries.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evidence_attachments_inquiry_id'), 'evidence_attachments', ['inquiry_id'], unique=False)
    op.create_table('inquiry_follows',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('inquiry_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['inquiry_id'], ['inquiries.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('inquiry_id', 'user_id', name='uq_inquiry_follows_inquiry_user')
    )
    op.create_index(op.f('ix_inquiry_follows_inquiry_id'), 'inquiry_follows', ['inquiry_id'], unique=False)
    op.create_index(op.f('ix_inquiry_follows_user_id'), 'inquiry_follows', ['user_id'], unique=False)


def downgrade() -> None:
    """Downgrade schema — reverses upgrade() above. Does not touch
    public_records (see upgrade()'s own docstring: that churn was never
    applied here)."""
    op.drop_index(op.f('ix_inquiry_follows_user_id'), table_name='inquiry_follows')
    op.drop_index(op.f('ix_inquiry_follows_inquiry_id'), table_name='inquiry_follows')
    op.drop_table('inquiry_follows')
    op.drop_index(op.f('ix_evidence_attachments_inquiry_id'), table_name='evidence_attachments')
    op.drop_table('evidence_attachments')
    op.drop_index(op.f('ix_attorney_requests_inquiry_id'), table_name='attorney_requests')
    op.drop_index(op.f('ix_attorney_requests_attorney_id'), table_name='attorney_requests')
    op.drop_table('attorney_requests')
    op.drop_index(op.f('ix_reports_reporter_id'), table_name='reports')
    op.drop_table('reports')
    # Drop the enum types this migration's own upgrade() created —
    # Postgres doesn't do this automatically when the owning table is
    # dropped (same lesson as M1.2's downgrade()). op.drop_table() removes
    # each column that used these types, but the named enum TYPE objects
    # themselves persist until explicitly dropped, which would break a
    # repeated upgrade/downgrade cycle ("type already exists") otherwise.
    sa.Enum(name='reporttargettype').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='reportstatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='attorneyrequeststatus').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='filetype').drop(op.get_bind(), checkfirst=True)
