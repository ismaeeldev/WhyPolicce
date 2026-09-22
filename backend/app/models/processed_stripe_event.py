"""processed_stripe_events table — forum rebuild, Milestone 3 Step M3.2
(WhyPoliceForum_MasterGuide.md).

Stripe's own webhook docs explicitly warn that the same event can be
delivered more than once — a durable, DB-backed record of already-handled
event ids is the real idempotency guard (Bug Fix's own explicit "replay
the same webhook event twice" adversarial test). An in-memory set would
not survive a process restart or work across multiple backend instances;
this table does. Deliberately its own tiny table, not reusing any
existing one — this only ever needs a single unique key and an insert,
nothing relational.
"""

import uuid
from datetime import datetime, timezone

from sqlmodel import Column, DateTime, Field, SQLModel


class ProcessedStripeEvent(SQLModel, table=True):
    __tablename__ = "processed_stripe_events"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    # Stripe's own event id (e.g. "evt_..."), globally unique per Stripe's
    # own guarantees — the real dedup key.
    stripe_event_id: str = Field(unique=True, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
