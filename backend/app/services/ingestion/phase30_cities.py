"""Phase 30 multi-city sync orchestrator — plan.md Step 9.

Fourth phase using `OpenPoliceData`'s source table as a discovery
accelerant. Runs the 2 Phase 30 ingestions (Johns Creek GA, Morrisville
NC) in one call, same isolation pattern as every prior phase
orchestrator.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.johns_creek_socrata import sync_johns_creek_crime
from app.services.ingestion.morrisville_opendatasoft import sync_morrisville_crime

logger = logging.getLogger(__name__)

PHASE30_SYNC_FUNCTIONS = [
    ("johns_creek_crime", sync_johns_creek_crime),
    ("morrisville_crime", sync_morrisville_crime),
]


async def sync_all_phase30_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 30 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE30_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase30_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
