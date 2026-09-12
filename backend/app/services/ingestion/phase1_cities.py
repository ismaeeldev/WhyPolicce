"""Phase 1 multi-city sync orchestrator — plan.md Step 9.

Runs all 6 Phase 1 city ingestions (Chicago, Los Angeles, Philadelphia,
Seattle, Austin, Dallas) in one call, same isolation pattern as the
original `sync_all_nyc`: one city's failure (a dead endpoint, a schema
change, a timeout) must not prevent the other 5 from syncing. Each
result reports its own success/error rather than the whole batch raising.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.austin_socrata import sync_austin_crime
from app.services.ingestion.chicago_socrata import sync_chicago_crimes
from app.services.ingestion.dallas_socrata import sync_dallas_incidents
from app.services.ingestion.la_socrata import sync_la_crime
from app.services.ingestion.philadelphia_carto import sync_philadelphia_incidents
from app.services.ingestion.seattle_socrata import sync_seattle_crime

logger = logging.getLogger(__name__)

PHASE1_SYNC_FUNCTIONS = [
    ("chicago_crimes", sync_chicago_crimes),
    ("la_crime", sync_la_crime),
    ("philadelphia_incidents", sync_philadelphia_incidents),
    ("seattle_crime", sync_seattle_crime),
    ("austin_crime", sync_austin_crime),
    ("dallas_incidents", sync_dallas_incidents),
]


async def sync_all_phase1_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 1 city sync. Called by the scheduler alongside
    sync_all_nyc, and available for a manual/one-off verification run.
    `limit` is passed through to each city's default fetch limit only if
    given — omitted (None) lets each city module use its own default.

    Found via a real first verification run, not hypothesized: a failed
    INSERT (e.g. Seattle's real duplicate-report-number data — see
    socrata_base.py's dedup fix) leaves the shared SQLAlchemy Session in
    an aborted transaction state. Every city after it then failed too,
    even Austin, which had nothing wrong with its own data — the shared
    session itself was poisoned. `sync_all_nyc`'s original two-dataset
    loop never hit this because NYC's complaint/arrest sources never
    collided on external_id. A `session.rollback()` after any failure
    clears that aborted state so the NEXT city gets a clean session,
    matching the "one city's failure never blocks the others" guarantee
    this function already promised but didn't actually keep before this."""
    results = []
    for source_name, sync_fn in PHASE1_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase1_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
