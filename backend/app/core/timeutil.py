"""Shared timestamp-serialization helper — AgentGuide/05_PROJECT_STATE.md's
Auth0/timestamp bug notes (2026-08-26).

Every model's created_at/updated_at column is now explicitly
DateTime(timezone=True), which fixes this correctly on real Postgres/Neon.
But SQLite — this project's own documented local-testing fallback when no
live Neon connection is available — has no native timestamptz type and
cannot actually round-trip tzinfo the same way, so a naive datetime can
still come back from the ORM there. Calling raw `.isoformat()` on a naive
datetime silently omits the UTC offset, and the frontend's `new Date(...)`
then parses it as the browser's LOCAL time per the ECMAScript spec — the
exact bug a live user's session first surfaced ("5 hours ago" moments after
creation). This helper guarantees a real UTC offset in the serialized
string regardless of which database backend produced the value.
"""

from datetime import datetime, timezone


def to_utc_iso(dt: datetime | None) -> str | None:
    """Real availability bug found by a production-readiness audit,
    reproduced live: every created_at/updated_at column in this
    codebase is declared with an explicit `sa_column=Column(...)`,
    which silently DISCARDS SQLModel's inferred `nullable=False` —
    confirmed against the live SQLModel.metadata DDL, every one of
    these columns is actually NULLable in the real schema, with no
    server-side DEFAULT either (default_factory is Python-side only).
    A row that arrives by any path other than a normal ORM insert — a
    manual SQL fix, a restore that drops defaults, a future data
    migration, a bulk import — can carry created_at=NULL and the
    schema accepts it without complaint. This function used to call
    `.isoformat()` unconditionally, so ONE such row raised
    AttributeError on `.tzinfo` and took down the ENTIRE list endpoint
    it appeared in for every user — not a per-row degradation, a full
    outage triggered by a single bad row with no visible cause. Now
    degrades to `None` for that one row instead of crashing the whole
    response; the real, durable fix is making these columns genuinely
    NOT NULL at the database level (a migration), which this guard
    doesn't replace but does buy safety against in the meantime."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()
