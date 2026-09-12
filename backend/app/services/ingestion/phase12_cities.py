"""Phase 12 multi-city sync orchestrator — plan.md Step 9.

Runs the 4 Phase 12 city ingestions (Tacoma, Boise, Riverside,
Chattanooga) in one call, same isolation pattern as every prior phase
orchestrator.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.boise_arcgis import sync_boise_calls
from app.services.ingestion.chattanooga_arcgis import sync_chattanooga_crime
from app.services.ingestion.riverside_arcgis import sync_riverside_crime
from app.services.ingestion.tacoma_arcgis import sync_tacoma_crime

logger = logging.getLogger(__name__)

PHASE12_SYNC_FUNCTIONS = [
    ("tacoma_crime", sync_tacoma_crime),
    ("boise_calls", sync_boise_calls),
    ("riverside_crime", sync_riverside_crime),
    ("chattanooga_crime", sync_chattanooga_crime),
]


async def sync_all_phase12_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 12 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE12_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase12_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
