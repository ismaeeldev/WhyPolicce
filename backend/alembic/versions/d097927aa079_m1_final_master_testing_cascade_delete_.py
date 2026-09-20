"""m1_final_master_testing_cascade_delete_on_inquiry_fks

Revision ID: d097927aa079
Revises: 08b90467b9f0
Create Date: 2026-09-20 21:56:01.186752

Real bug found by Milestone 1's own Final Master Testing gate, live
against the real dev database, not by code review: DELETE
/api/v1/inquiries/{id} (M1.4) raised an unhandled 500
(psycopg2.errors.ForeignKeyViolation) the moment the target inquiry had
any real child row against it — a thread_comment, an inquiry_follow, an
attorney_request, or an evidence_attachment — because none of those
four FKs into inquiries.id ever had an explicit ON DELETE policy, so
Postgres silently defaulted to NO ACTION/restrict. WhyPoliceForum_
MasterGuide.md's own M1.2/M1.3 Bug Fix notes both said to "confirm the
foreign key behavior is a deliberate choice... not whatever SQLAlchemy
happened to default to," but neither step actually verified the API
layer's behavior when that restriction is hit — it stayed an unnoticed
default, not a real, deliberate choice, until this gate exercised the
exact scenario (delete an inquiry that already has a real follower/
comment) that surfaced it.

Cascading — rather than having delete_inquiry catch the restrict
violation and reject the delete — is the deliberate choice made here:
restricting would make almost every inquiry with any real engagement
permanently undeletable, directly contradicting the client's own
explicit "citizen can edit/delete their own inquiry at any time, no
time limit" answer (WhyPolice-Scope-Realignment.pdf), and Milestone 1's
own Final Master Testing checklist item 1 explicitly walks through
"follow the inquiry... then delete the original inquiry" as an
expected-to-succeed step.

Autogenerate's raw draft for this change (reviewed, not trusted blind,
per this project's own established migration discipline) proposed two
further changes that are NOT wanted and are stripped out below:
1. `nullable=True` on all four inquiry_id columns — a real, unrelated,
   unwanted side effect of the model diff; none of these columns were
   ever meant to become nullable.
2. The same recurring "public_records index churn" (dropping
   ix_public_records_embedding_hnsw / ix_public_records_state, adding
   ix_public_records_city) already seen and rejected identically in
   the baseline, M1.2, and M1.3 migrations — pre-existing drift in the
   old RAG product's own schema, not this migration's concern.
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'd097927aa079'
down_revision: Union[str, Sequence[str], None] = '08b90467b9f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES = ["thread_comments", "evidence_attachments", "attorney_requests", "inquiry_follows"]


def upgrade() -> None:
    for table in _TABLES:
        op.drop_constraint(f"{table}_inquiry_id_fkey", table, type_="foreignkey")
        op.create_foreign_key(
            f"{table}_inquiry_id_fkey",
            table,
            "inquiries",
            ["inquiry_id"],
            ["id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    for table in _TABLES:
        op.drop_constraint(f"{table}_inquiry_id_fkey", table, type_="foreignkey")
        op.create_foreign_key(
            f"{table}_inquiry_id_fkey",
            table,
            "inquiries",
            ["inquiry_id"],
            ["id"],
        )
