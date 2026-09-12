"""Phase 9 multi-city sync orchestrator — plan.md Step 9.

Runs the 4 Phase 9 city ingestions (Cincinnati, Colorado Springs,
Norfolk, Omaha) in one call, same isolation pattern as every prior phase
orchestrator.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.cincinnati_socrata import sync_cincinnati_crime
from app.services.ingestion.colorado_springs_socrata import sync_colorado_springs_crime
from app.services.ingestion.norfolk_socrata import sync_norfolk_crime
from app.services.ingestion.omaha_arcgis import sync_omaha_crime

logger = logging.getLogger(__name__)

PHASE9_SYNC_FUNCTIONS = [
    ("cincinnati_crime", sync_cincinnati_crime),
    ("colorado_springs_crime", sync_colorado_springs_crime),
    ("norfolk_crime", sync_norfolk_crime),
    ("omaha_crime", sync_omaha_crime),
]


async def sync_all_phase9_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 9 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE9_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase9_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
