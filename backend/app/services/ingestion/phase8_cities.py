"""Phase 8 multi-city sync orchestrator — plan.md Step 9.

Runs the 4 Phase 8 city ingestions (New Orleans, Kansas City,
Indianapolis, Virginia Beach) in one call, same isolation pattern as
every prior phase orchestrator.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.indianapolis_arcgis import sync_indianapolis_crime
from app.services.ingestion.kansas_city_socrata import sync_kansas_city_crime
from app.services.ingestion.new_orleans_socrata import sync_new_orleans_calls
from app.services.ingestion.virginia_beach_arcgis import sync_virginia_beach_calls

logger = logging.getLogger(__name__)

PHASE8_SYNC_FUNCTIONS = [
    ("new_orleans_calls", sync_new_orleans_calls),
    ("kansas_city_crime", sync_kansas_city_crime),
    ("indianapolis_crime", sync_indianapolis_crime),
    ("virginia_beach_calls", sync_virginia_beach_calls),
]


async def sync_all_phase8_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 8 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE8_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase8_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
