"""Phase 6 multi-city sync orchestrator — plan.md Step 9.

Runs the 3 Phase 6 city ingestions (Boston, Tucson, Sacramento) in one
call, same isolation pattern as every prior phase orchestrator.

**San Francisco was investigated, built, and then deliberately dropped**
after real live verification found its data source (a "2018 to Present"
FeatureServer) genuinely contains only 49 total rows, every single one
dated the exact same day (2026-02-01) — not real day-to-day coverage the
way every other city here has, despite passing an initial MAX()-date
freshness check. Per explicit product decision (2026-09-08), removed
rather than shipped as misleadingly thin/unrepresentative data alongside
21 genuinely robust cities. A real SF replacement can be investigated
separately later.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.boston_arcgis import sync_boston_crime
from app.services.ingestion.sacramento_arcgis import sync_sacramento_crime
from app.services.ingestion.tucson_arcgis import sync_tucson_crime

logger = logging.getLogger(__name__)

PHASE6_SYNC_FUNCTIONS = [
    ("boston_crime", sync_boston_crime),
    ("tucson_crime", sync_tucson_crime),
    ("sacramento_crime", sync_sacramento_crime),
]


async def sync_all_phase6_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 6 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE6_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase6_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
