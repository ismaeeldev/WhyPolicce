"""Phase 14 multi-city sync orchestrator — plan.md Step 9.

Runs the 2 Phase 14 ingestions (Montgomery County MD, Prince George's
County MD) in one call, same isolation pattern as every prior phase
orchestrator. Only 2 winners this phase, not 4 — research found a
genuinely honest limit on new viable candidates rather than a weak 4th
being force-added (a 3rd candidate, "Louisville Metro KY," turned out to
be the exact same already-integrated `louisville_crime` source under a
different research label, and was dropped rather than double-counted).
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.montgomery_county_socrata import sync_montgomery_county_crime
from app.services.ingestion.prince_georges_county_socrata import sync_prince_georges_county_crime

logger = logging.getLogger(__name__)

PHASE14_SYNC_FUNCTIONS = [
    ("montgomery_county_crime", sync_montgomery_county_crime),
    ("prince_georges_county_crime", sync_prince_georges_county_crime),
]


async def sync_all_phase14_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 14 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE14_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase14_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
