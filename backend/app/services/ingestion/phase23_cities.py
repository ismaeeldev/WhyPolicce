"""Phase 23 multi-city sync orchestrator — plan.md Step 9.

Runs the 2 Phase 23 ingestions (Miami FL, St. Paul MN) in one call, same
isolation pattern as every prior phase orchestrator.

Miami's inclusion is significant: it has been this project's standing
"honest decline" test case across every prior phase's end-to-end
verification. See miami_arcgis.py's module docstring for the extra
verification scrutiny this specific candidate received before shipping.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.miami_arcgis import sync_miami_crime
from app.services.ingestion.st_paul_arcgis import sync_st_paul_crime

logger = logging.getLogger(__name__)

PHASE23_SYNC_FUNCTIONS = [
    ("miami_crime", sync_miami_crime),
    ("st_paul_crime", sync_st_paul_crime),
]


async def sync_all_phase23_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 23 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE23_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase23_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
