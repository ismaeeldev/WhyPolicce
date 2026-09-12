"""Phase 29 multi-city sync orchestrator — plan.md Step 9.

Third phase using `OpenPoliceData`'s source table as a discovery
accelerant. Runs the 4 Phase 29 ingestions (Marin County CA, Sonoma
County CA, Santa Monica CA, Bloomington IN) in one call, same isolation
pattern as every prior phase orchestrator.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.bloomington_in_socrata import sync_bloomington_in_calls
from app.services.ingestion.marin_county_socrata import sync_marin_county_crime
from app.services.ingestion.santa_monica_ckan import sync_santa_monica_calls
from app.services.ingestion.sonoma_county_socrata import sync_sonoma_county_crime

logger = logging.getLogger(__name__)

PHASE29_SYNC_FUNCTIONS = [
    ("marin_county_crime", sync_marin_county_crime),
    ("sonoma_county_crime", sync_sonoma_county_crime),
    ("santa_monica_calls", sync_santa_monica_calls),
    ("bloomington_in_calls", sync_bloomington_in_calls),
]


async def sync_all_phase29_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 29 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE29_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase29_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
