"""Phase 3 multi-city sync orchestrator — plan.md Step 9.

Runs the 2 Phase 3 city ingestions in one call, same isolation pattern as
Phase 1/2's orchestrators: one city's failure must not prevent the other
from syncing, and a rollback after any failure clears the shared
Session's aborted-transaction state.

**Nashville and Detroit, not Houston and San Diego as originally scoped.**
Houston's and San Diego's real, confirmed-live crime data sources both
sit on self-hosted municipal ArcGIS servers (mycity2.houstontx.gov,
webmaps.sandiego.gov) that this build environment genuinely cannot
connect to — confirmed via direct TCP timeout across HTTPS, HTTP, both
standard ports, and explicit IP resolution, while services.arcgis.com
and every other city's infrastructure (including other cities' own
self-hosted municipal domains, e.g. Denver, Chicago) connects fine. This
is a real, narrow network-level block specific to those two hosts' own
firewalls (a common pattern for government sites blocking known
cloud/datacenter IP ranges), not a data-availability or code problem.
Per explicit product decision (2026-09-08), substituted with two
different, equally-real, independently-verified major US cities rather
than force a connection that provably cannot succeed from this
environment.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.detroit_arcgis import sync_detroit_crime
from app.services.ingestion.nashville_arcgis import sync_nashville_crime

logger = logging.getLogger(__name__)

PHASE3_SYNC_FUNCTIONS = [
    ("nashville_crime", sync_nashville_crime),
    ("detroit_crime", sync_detroit_crime),
]


async def sync_all_phase3_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 3 city sync. Same rollback-on-failure discipline
    as sync_all_phase1_cities/sync_all_phase2_cities."""
    results = []
    for source_name, sync_fn in PHASE3_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase3_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
