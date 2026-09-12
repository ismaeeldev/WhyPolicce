"""Phase 10 multi-city sync orchestrator — plan.md Step 9.

Runs the 4 Phase 10 city ingestions (Fort Worth, Cleveland, St. Louis
County, Tampa) in one call, same isolation pattern as every prior phase
orchestrator.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.cleveland_arcgis import sync_cleveland_crime
from app.services.ingestion.fort_worth_arcgis import sync_fort_worth_crime
from app.services.ingestion.st_louis_county_arcgis import sync_st_louis_county_crime
from app.services.ingestion.tampa_arcgis import sync_tampa_crime

logger = logging.getLogger(__name__)

PHASE10_SYNC_FUNCTIONS = [
    ("fort_worth_crime", sync_fort_worth_crime),
    ("cleveland_crime", sync_cleveland_crime),
    ("st_louis_county_crime", sync_st_louis_county_crime),
    ("tampa_crime", sync_tampa_crime),
]


async def sync_all_phase10_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 10 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE10_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase10_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
