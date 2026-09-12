"""Phase 21 multi-city sync orchestrator — plan.md Step 9.

Runs the 1 Phase 21 ingestion (Glendale, AZ). Only 1 winner this phase,
not 4 — the two specifically flagged leads from Phase 20 (Tarrant County
TX, Round Rock TX) were both retried and confirmed to be real
rejections, not just re-timeouts: Tarrant County's crime/CFS query
endpoints are reachable but server-side broken, and the "Round Rock"
Transparency Dashboard lead turned out to be misattributed Los Altos, CA
data. Rather than force a weak substitute, this phase ships with the 1
genuinely new, fully-verified winner found.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.glendale_az_arcgis import sync_glendale_az_calls

logger = logging.getLogger(__name__)

PHASE21_SYNC_FUNCTIONS = [
    ("glendale_az_calls", sync_glendale_az_calls),
]


async def sync_all_phase21_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 21 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE21_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase21_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
