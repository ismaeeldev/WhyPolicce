"""Phase 25 multi-city sync orchestrator — plan.md Step 9.

Runs the 2 Fairfield, CA ingestions (Cases + Calls for Service, both a
genuinely new CSV-over-HTTP fetch pattern for this project — see
fairfield_ca_arcgis.py's module docstring). Only 1 new city this phase,
across 2 sources — Ohio/Pennsylvania/Illinois candidates all failed to
turn up any viable source, and most other California candidates checked
were stale, discontinued, or rolling-30-day-only.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.fairfield_ca_arcgis import sync_fairfield_ca_calls, sync_fairfield_ca_crime

logger = logging.getLogger(__name__)

PHASE25_SYNC_FUNCTIONS = [
    ("fairfield_ca_crime", sync_fairfield_ca_crime),
    ("fairfield_ca_calls", sync_fairfield_ca_calls),
]


async def sync_all_phase25_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 25 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE25_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase25_cities: %s sync failed, continuing with other sources", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
