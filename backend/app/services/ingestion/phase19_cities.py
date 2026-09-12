"""Phase 19 multi-city sync orchestrator — plan.md Step 9.

Runs the 1 Phase 19 ingestion (Auburn, WA). Only 1 winner this phase, not
4 — research found a genuinely honest limit on new viable candidates
(over a dozen checked, most with no queryable API at all, one rejected
for being a rolling ~30-day window, none duplicating already-integrated
sources) rather than a weak candidate being force-added.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.auburn_wa_socrata import sync_auburn_wa_crime

logger = logging.getLogger(__name__)

PHASE19_SYNC_FUNCTIONS = [
    ("auburn_wa_crime", sync_auburn_wa_crime),
]


async def sync_all_phase19_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 19 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE19_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase19_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
