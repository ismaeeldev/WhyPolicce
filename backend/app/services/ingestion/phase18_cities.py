"""Phase 18 multi-city sync orchestrator — plan.md Step 9.

Runs the 1 Phase 18 ingestion (Bellevue, WA). Only 1 winner this phase,
not 4 — research found a genuinely honest limit on new viable candidates
(most remaining leads were dead/stub test layers, mislabeled decoys of
already-integrated cities, or portals requiring sign-in/unindexed
services) rather than a weak candidate being force-added.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.bellevue_arcgis import sync_bellevue_calls

logger = logging.getLogger(__name__)

PHASE18_SYNC_FUNCTIONS = [
    ("bellevue_calls", sync_bellevue_calls),
]


async def sync_all_phase18_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 18 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE18_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase18_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
