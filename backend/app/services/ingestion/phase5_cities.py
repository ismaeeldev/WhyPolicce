"""Phase 5 multi-city sync orchestrator — plan.md Step 9.

Runs the 3 Phase 5 city ingestions (Memphis, Las Vegas, Milwaukee) in one
call, same isolation pattern as every prior phase orchestrator.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.las_vegas_arcgis import sync_las_vegas_crime
from app.services.ingestion.memphis_arcgis import sync_memphis_crime
from app.services.ingestion.milwaukee_ckan import sync_milwaukee_crime

logger = logging.getLogger(__name__)

PHASE5_SYNC_FUNCTIONS = [
    ("memphis_crime", sync_memphis_crime),
    ("las_vegas_crime", sync_las_vegas_crime),
    ("milwaukee_crime", sync_milwaukee_crime),
]


async def sync_all_phase5_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 5 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE5_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase5_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
