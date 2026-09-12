"""Phase 27 multi-city sync orchestrator — plan.md Step 9.

First phase discovered via `OpenPoliceData` (a source-discovery
accelerant adopted starting this phase — see plan.md's "Beyond Phase 26"
decision) rather than pure manual web search. Every candidate it
surfaced was still independently re-verified via direct HTTP queries and
given its own hand-built, privacy-reviewed summarizer before shipping —
the discovery method changed, the verification bar did not.

Runs the 4 Phase 27 ingestions (Mesa AZ, San Diego CA, Charleston SC,
Dayton OH) in one call, same isolation pattern as every prior phase
orchestrator.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.charleston_sc_arcgis import sync_charleston_sc_crime
from app.services.ingestion.dayton_arcgis import sync_dayton_crime
from app.services.ingestion.mesa_socrata import sync_mesa_crime
from app.services.ingestion.san_diego_socrata import sync_san_diego_crime

logger = logging.getLogger(__name__)

PHASE27_SYNC_FUNCTIONS = [
    ("mesa_crime", sync_mesa_crime),
    ("san_diego_crime", sync_san_diego_crime),
    ("charleston_sc_crime", sync_charleston_sc_crime),
    ("dayton_crime", sync_dayton_crime),
]


async def sync_all_phase27_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 27 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE27_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase27_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
