"""Phase 28 multi-city sync orchestrator — plan.md Step 9.

Second phase using `OpenPoliceData`'s source table as a discovery
accelerant. San Francisco was a candidate this phase but was dropped —
its Socrata endpoint returned a real, independently-confirmed HTTP 403
from this environment (verbose curl trace showed a clean server-side
block, not a transient error), contradicting the research agent's own
claimed successful verification. Only sources this project could itself
independently verify were shipped.

Runs the 3 Phase 28 ingestions (Richmond CA Incidents, Richmond CA Calls
for Service, Long Beach CA) in one call, same isolation pattern as every
prior phase orchestrator.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.long_beach_opendatasoft import sync_long_beach_crime
from app.services.ingestion.richmond_ca_socrata import sync_richmond_ca_calls, sync_richmond_ca_crime

logger = logging.getLogger(__name__)

PHASE28_SYNC_FUNCTIONS = [
    ("richmond_ca_crime", sync_richmond_ca_crime),
    ("richmond_ca_calls", sync_richmond_ca_calls),
    ("long_beach_crime", sync_long_beach_crime),
]


async def sync_all_phase28_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 28 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE28_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase28_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
