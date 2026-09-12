"""Phase 20 multi-city sync orchestrator — plan.md Step 9.

Runs the 2 Phase 20 ingestions (Frisco TX, Pearland TX) in one call, same
isolation pattern as every prior phase orchestrator.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.frisco_arcgis import sync_frisco_crime
from app.services.ingestion.pearland_arcgis import sync_pearland_crime

logger = logging.getLogger(__name__)

PHASE20_SYNC_FUNCTIONS = [
    ("frisco_crime", sync_frisco_crime),
    ("pearland_crime", sync_pearland_crime),
]


async def sync_all_phase20_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 20 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE20_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase20_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
