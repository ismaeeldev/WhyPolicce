"""Phase 15 multi-city sync orchestrator — plan.md Step 9.

Runs the 1 Phase 15 ingestion (Jacksonville, FL). Only 1 winner this
phase, not 4 — research found a genuinely honest limit on new viable
candidates (most remaining leads resolved to duplicates of already-
integrated consolidated city-county governments, proprietary map
products with no structured API, or token-gated endpoints) rather than a
weak candidate being force-added.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.jacksonville_arcgis import sync_jacksonville_crime

logger = logging.getLogger(__name__)

PHASE15_SYNC_FUNCTIONS = [
    ("jacksonville_crime", sync_jacksonville_crime),
]


async def sync_all_phase15_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 15 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE15_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase15_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
