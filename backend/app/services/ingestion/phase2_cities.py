"""Phase 2 multi-city sync orchestrator — plan.md Step 9.

Runs all 3 Phase 2 city ingestions (Phoenix, Denver, San Antonio) in one
call, same isolation pattern as Phase 1's `sync_all_phase1_cities`: one
city's failure must not prevent the others from syncing, and a rollback
after any failure clears the shared Session's aborted-transaction state
so it doesn't poison the next city (the exact bug Phase 1 found and fixed
in `sync_all_phase1_cities`/`sync_all_nyc`).

These three cities are NOT uniform the way Phase 1's Socrata cities were:
- Phoenix: real, confirmed stale (city-acknowledged data gap since
  2026-01-01) — see phoenix_ckan.py's module docstring.
- Denver: genuinely current (ArcGIS FeatureServer, confirmed live via a
  server-side MAX() query) — see denver_arcgis.py.
- San Antonio: genuinely current (full-CSV download, client-side
  most-recent-N filtering since the file isn't pre-sorted) — see
  san_antonio_ckan.py.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.denver_arcgis import sync_denver_crime
from app.services.ingestion.phoenix_ckan import sync_phoenix_crime
from app.services.ingestion.san_antonio_ckan import sync_san_antonio_offenses

logger = logging.getLogger(__name__)

PHASE2_SYNC_FUNCTIONS = [
    ("phoenix_crime", sync_phoenix_crime),
    ("denver_crime", sync_denver_crime),
    ("san_antonio_offenses", sync_san_antonio_offenses),
]


async def sync_all_phase2_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 2 city sync. Same rollback-on-failure discipline
    as sync_all_phase1_cities — see that function's docstring for why this
    matters with a shared Session."""
    results = []
    for source_name, sync_fn in PHASE2_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase2_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
