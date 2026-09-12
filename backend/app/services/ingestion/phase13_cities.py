"""Phase 13 multi-city sync orchestrator — plan.md Step 9.

Runs the 4 Phase 13 city ingestions (Buffalo, Tempe, Rochester, Grand
Rapids) in one call, same isolation pattern as every prior phase
orchestrator.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.buffalo_socrata import sync_buffalo_crime
from app.services.ingestion.grand_rapids_arcgis import sync_grand_rapids_crime
from app.services.ingestion.rochester_arcgis import sync_rochester_crime
from app.services.ingestion.tempe_arcgis import sync_tempe_calls

logger = logging.getLogger(__name__)

PHASE13_SYNC_FUNCTIONS = [
    ("buffalo_crime", sync_buffalo_crime),
    ("tempe_calls", sync_tempe_calls),
    ("rochester_crime", sync_rochester_crime),
    ("grand_rapids_crime", sync_grand_rapids_crime),
]


async def sync_all_phase13_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 13 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE13_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase13_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
