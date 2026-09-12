"""Phase 16 multi-city sync orchestrator — plan.md Step 9.

Runs the 2 Phase 16 ingestions (Aurora IL, Boulder CO) in one call, same
isolation pattern as every prior phase orchestrator.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.aurora_il_arcgis import sync_aurora_il_crime
from app.services.ingestion.boulder_arcgis import sync_boulder_crime

logger = logging.getLogger(__name__)

PHASE16_SYNC_FUNCTIONS = [
    ("aurora_il_crime", sync_aurora_il_crime),
    ("boulder_crime", sync_boulder_crime),
]


async def sync_all_phase16_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 16 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE16_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase16_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
