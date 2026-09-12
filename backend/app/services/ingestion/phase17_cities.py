"""Phase 17 multi-city sync orchestrator — plan.md Step 9.

Runs the 3 Phase 17 ingestions (Bend OR, Yakima WA, Everett WA) in one
call, same isolation pattern as every prior phase orchestrator.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.bend_arcgis import sync_bend_crime
from app.services.ingestion.everett_socrata import sync_everett_calls
from app.services.ingestion.yakima_arcgis import sync_yakima_crime

logger = logging.getLogger(__name__)

PHASE17_SYNC_FUNCTIONS = [
    ("bend_crime", sync_bend_crime),
    ("yakima_crime", sync_yakima_crime),
    ("everett_calls", sync_everett_calls),
]


async def sync_all_phase17_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 17 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE17_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase17_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
