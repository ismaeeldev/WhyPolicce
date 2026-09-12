"""Phase 4 multi-city sync orchestrator — plan.md Step 9.

Runs the 3 Phase 4 city ingestions (San Jose, Louisville, Baltimore) in
one call, same isolation pattern as Phase 1/2/3's orchestrators.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.baltimore_arcgis import sync_baltimore_crime
from app.services.ingestion.louisville_arcgis import sync_louisville_crime
from app.services.ingestion.san_jose_ckan import sync_san_jose_calls

logger = logging.getLogger(__name__)

PHASE4_SYNC_FUNCTIONS = [
    ("san_jose_calls", sync_san_jose_calls),
    ("louisville_crime", sync_louisville_crime),
    ("baltimore_crime", sync_baltimore_crime),
]


async def sync_all_phase4_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 4 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE4_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase4_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
