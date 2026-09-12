"""Phase 11 multi-city sync orchestrator — plan.md Step 9.

Runs the 4 Phase 11 city ingestions (Hartford, Baton Rouge, Providence,
Honolulu) in one call, same isolation pattern as every prior phase
orchestrator.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.baton_rouge_socrata import sync_baton_rouge_crime
from app.services.ingestion.hartford_arcgis import sync_hartford_crime
from app.services.ingestion.honolulu_socrata import sync_honolulu_crime
from app.services.ingestion.providence_socrata import sync_providence_crime

logger = logging.getLogger(__name__)

PHASE11_SYNC_FUNCTIONS = [
    ("hartford_crime", sync_hartford_crime),
    ("baton_rouge_crime", sync_baton_rouge_crime),
    ("providence_crime", sync_providence_crime),
    ("honolulu_crime", sync_honolulu_crime),
]


async def sync_all_phase11_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 11 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE11_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase11_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
