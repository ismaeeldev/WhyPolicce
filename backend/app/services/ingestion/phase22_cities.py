"""Phase 22 multi-city sync orchestrator — plan.md Step 9.

Runs the 2 Phase 22 ingestions (Fayetteville NC, Asheville NC) in one
call, same isolation pattern as every prior phase orchestrator.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.asheville_arcgis import sync_asheville_crime
from app.services.ingestion.fayetteville_nc_arcgis import sync_fayetteville_nc_crime

logger = logging.getLogger(__name__)

PHASE22_SYNC_FUNCTIONS = [
    ("fayetteville_nc_crime", sync_fayetteville_nc_crime),
    ("asheville_crime", sync_asheville_crime),
]


async def sync_all_phase22_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 22 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE22_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase22_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
