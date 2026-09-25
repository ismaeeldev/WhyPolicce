"""add_index_on_users_email

Revision ID: e5061273731a
Revises: 463c4bf225ae
Create Date: 2026-09-25 00:00:00.000000

Real gap found during a full-scope re-audit: users.email had no index —
auth0_sub is the real identity key (unique+indexed already), but any
future by-email lookup (support tooling, admin search, "email already
registered" UX) would do a full table scan. Indexed only, not unique —
some rows legitimately have an empty-string email (populated lazily on
next login, see app/routers/*.py's _get_or_create_user), so a unique
constraint would reject real, existing data.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'e5061273731a'
down_revision: Union[str, Sequence[str], None] = '463c4bf225ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_users_email'), table_name='users')
