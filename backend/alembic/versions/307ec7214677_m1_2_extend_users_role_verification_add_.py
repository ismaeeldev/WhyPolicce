"""M1.2: extend users (role/verification), add inquiries and thread_comments

Revision ID: 307ec7214677
Revises: e6305ce4e42c
Create Date: 2026-09-20 12:00:58.383738

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = '307ec7214677'
down_revision: Union[str, Sequence[str], None] = 'e6305ce4e42c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Manually corrected from autogenerate's raw draft, per this project's
    own "review before applying" discipline (WhyPoliceForum_MasterGuide.md
    M1.2's Master Prompt) — the same two real issues found and fixed in
    this exact class of migration once already (see this file's sibling
    M1.1 baseline's own docstring for the first occurrence, and this
    migration's own real, live-verified enum-collision fix at the model
    level in app/models/inquiry.py's InquiryTier docstring):

    1. `import sqlmodel` was missing from autogenerate's output — the
       generated column types reference
       `sqlmodel.sql.sqltypes.AutoString()` but the import was never
       emitted, which would raise a real NameError the moment this
       migration actually ran.
    2. `users.role` was generated as `nullable=False` with no
       `server_default`. This table has 25 real, existing rows (the old
       RAG product's live users) as of this migration's authoring —
       confirmed via a direct COUNT(*) against the live database, not
       assumed. `ALTER TABLE users ADD COLUMN role ... NOT NULL` with no
       default against a table that already has rows fails outright in
       Postgres. Added `server_default='citizen'` so the column add
       succeeds and every existing row gets the same default the User
       model itself specifies in Python (Role.citizen).
       `verified_bar_no`, `bar_jurisdiction`, and `verification_status`
       are all nullable, so existing rows correctly get NULL with no
       default needed (see their own docstrings in app/models/user.py for
       why NULL, not a default enum value, is correct there).

    The `public_records` index churn autogenerate also proposed here
    (dropping ix_public_records_embedding_hnsw, swapping
    ix_public_records_state for ix_public_records_city) is the exact same
    pre-existing, already-documented drift stripped out of M1.1's baseline
    for the same reasons — not this migration's concern, not
    re-introduced here.

    THIRD real issue, found only by actually running this migration
    against the real database (not caught by the code review above) —
    `op.add_column('users', sa.Column('role', sa.Enum(...), ...))` failed
    with `psycopg2.errors.UndefinedObject: type "role" does not exist`.
    `op.create_table(...)` with an inline `sa.Enum(...)` DOES implicitly
    emit the `CREATE TYPE` first (that's why `inquiries`/`thread_comments`
    above need no separate handling) — but a standalone `op.add_column`
    call does NOT do the same implicit creation for an existing table.
    Fixed by explicitly creating each new enum type with `checkfirst=True`
    (safe/idempotent — a no-op if the type happens to already exist)
    before the `add_column` calls that use them, using SQLAlchemy's own
    documented pattern for exactly this situation. Confirmed via a real
    failed run against the live database first, which rolled back
    cleanly (Postgres's transactional DDL) with zero partial damage —
    verified directly afterward, not assumed.
    """
    role_enum = sa.Enum('citizen', 'attorney', name='role')
    role_enum.create(op.get_bind(), checkfirst=True)
    verification_status_enum = sa.Enum('pending', 'approved', 'rejected', name='verificationstatus')
    verification_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table('inquiries',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('author_id', sa.Uuid(), nullable=False),
    sa.Column('title', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('description', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('state', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('city', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('precinct', sqlmodel.sql.sqltypes.AutoString(), nullable=True),
    sa.Column('status_tag', sa.Enum('community_trace', 'awaiting_police_statement', name='statustag'), nullable=False),
    sa.Column('tier', sa.Enum('free', 'expanded', name='inquiry_tier'), nullable=True),
    sa.Column('follower_count', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_inquiries_author_id'), 'inquiries', ['author_id'], unique=False)
    op.create_table('thread_comments',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('inquiry_id', sa.Uuid(), nullable=False),
    sa.Column('author_id', sa.Uuid(), nullable=False),
    sa.Column('body', sqlmodel.sql.sqltypes.AutoString(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    sa.ForeignKeyConstraint(['author_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['inquiry_id'], ['inquiries.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_thread_comments_author_id'), 'thread_comments', ['author_id'], unique=False)
    op.create_index(op.f('ix_thread_comments_inquiry_id'), 'thread_comments', ['inquiry_id'], unique=False)
    # create_type=False on both: the enum type object itself was already
    # explicitly created above (with checkfirst=True) — passing the same
    # sa.Enum(...) instance again here without create_type=False would
    # make SQLAlchemy try to CREATE TYPE a second time and fail on "type
    # already exists" (the same class of bug just found and fixed for the
    # first CREATE, caught here by reasoning through it rather than
    # waiting for a second failed run against the real database).
    op.add_column('users', sa.Column('role', sa.Enum('citizen', 'attorney', name='role', create_type=False), nullable=False, server_default='citizen'))
    op.add_column('users', sa.Column('verified_bar_no', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('users', sa.Column('bar_jurisdiction', sqlmodel.sql.sqltypes.AutoString(), nullable=True))
    op.add_column('users', sa.Column('verification_status', sa.Enum('pending', 'approved', 'rejected', name='verificationstatus', create_type=False), nullable=True))


def downgrade() -> None:
    """Downgrade schema — reverses upgrade() above. Does not touch
    public_records (see upgrade()'s own docstring: that churn was never
    applied here in the first place)."""
    op.drop_column('users', 'verification_status')
    op.drop_column('users', 'bar_jurisdiction')
    op.drop_column('users', 'verified_bar_no')
    op.drop_column('users', 'role')
    op.drop_index(op.f('ix_thread_comments_inquiry_id'), table_name='thread_comments')
    op.drop_index(op.f('ix_thread_comments_author_id'), table_name='thread_comments')
    op.drop_table('thread_comments')
    op.drop_index(op.f('ix_inquiries_author_id'), table_name='inquiries')
    op.drop_table('inquiries')
    # Drop the enum types created for the new columns above — Postgres
    # enums are separate, named database objects (unlike a plain VARCHAR
    # CHECK constraint) and are NOT automatically dropped when the columns
    # using them are dropped. Leaving them behind would make a repeated
    # upgrade/downgrade cycle fail the second time around ("type already
    # exists") — found by actually reasoning through what downgrade()
    # leaves behind, not assumed clean because autogenerate's own raw
    # downgrade() draft didn't include this either. Deliberately does NOT
    # drop the pre-existing 'tier' enum type (that one belongs to
    # users.tier from the old product, untouched by this migration) —
    # only the four types this migration's own upgrade() actually created.
    sa.Enum(name='statustag').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='inquiry_tier').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='role').drop(op.get_bind(), checkfirst=True)
    sa.Enum(name='verificationstatus').drop(op.get_bind(), checkfirst=True)
