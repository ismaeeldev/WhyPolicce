"""Phase 7 multi-city sync orchestrator — plan.md Step 9.

Runs the 3 Phase 7 city ingestions (Washington DC, Raleigh, Minneapolis)
in one call, same isolation pattern as every prior phase orchestrator.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.minneapolis_arcgis import sync_minneapolis_crime
from app.services.ingestion.raleigh_arcgis import sync_raleigh_crime
from app.services.ingestion.washington_dc_arcgis import sync_washington_dc_crime

logger = logging.getLogger(__name__)

PHASE7_SYNC_FUNCTIONS = [
    ("washington_dc_crime", sync_washington_dc_crime),
    ("raleigh_crime", sync_raleigh_crime),
    ("minneapolis_crime", sync_minneapolis_crime),
]


async def sync_all_phase7_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 7 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE7_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase7_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
