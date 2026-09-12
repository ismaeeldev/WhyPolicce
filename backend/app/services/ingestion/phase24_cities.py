"""Phase 24 multi-city sync orchestrator — plan.md Step 9.

Runs the 1 Phase 24 ingestion (Gainesville, FL). Only 1 winner this
phase, not 4 — Fort Collins CO's GIS hub migration completed but its new
catalog has zero crime datasets (the old FeatureServer is a frozen 2020
snapshot, confirmed still stale), and a fresh sweep of Minnesota suburbs
and other Florida cities found no other viable candidates. Rather than
force a weak substitute, this phase ships with the 1 genuinely new,
fully-verified winner found.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.gainesville_socrata import sync_gainesville_crime

logger = logging.getLogger(__name__)

PHASE24_SYNC_FUNCTIONS = [
    ("gainesville_crime", sync_gainesville_crime),
]


async def sync_all_phase24_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 24 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE24_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase24_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
