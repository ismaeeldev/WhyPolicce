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


def to_utc_iso(dt: datetime) -> str:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()
