"""users table — AgentGuide/02_ApplicationFlow.md §4."""

import uuid
from datetime import datetime, timezone
from enum import Enum

from sqlmodel import Column, DateTime, Field, SQLModel


class Tier(str, Enum):
    free = "free"
    pro = "pro"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    auth0_sub: str = Field(unique=True, index=True)
    email: str
    tier: Tier = Field(default=Tier.free)
    stripe_customer_id: str | None = Field(default=None)
    # sa_column=Column(DateTime(timezone=True)) — found the hard way (a real
    # live user's session showed "5 hours ago" moments after creation): the
    # default SQLModel datetime column maps to Postgres's TIMESTAMP WITHOUT
    # TIME ZONE, which silently drops the UTC offset on write. The value read
    # back is a naive datetime, so .isoformat() omits the timezone suffix,
    # and the frontend's `new Date(...)` then parses it as the browser's
    # LOCAL time per the ECMAScript spec — wrong by exactly the viewer's UTC
    # offset. Explicit timezone=True keeps Postgres storing TIMESTAMPTZ, so
    # every read comes back tz-aware and every serialized timestamp carries
    # a real, unambiguous UTC offset.
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        sa_column=Column(DateTime(timezone=True)),
    )
