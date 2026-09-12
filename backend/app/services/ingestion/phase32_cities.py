"""Phase 32 multi-city sync orchestrator — plan.md Step 9.

Sixth phase using `OpenPoliceData`'s source table as a discovery
accelerant. Runs the 3 Phase 32 ingestions (Cambridge MA, Cary NC,
Charlottesville VA) in one call, same isolation pattern as every prior
phase orchestrator.

Of the 10 candidates researched this phase, 7 were rejected and are
NOT wired in here:
- Chandler, AZ: source (data.chandlerpd.com) returned HTTP 503
  "access...limited by the site owner" (a bot-blocking page) on direct
  query, same rejection class as this project's earlier San Francisco
  403 rejection.
- Pittsburgh, PA: the only genuinely fresh, live-updated datasets
  (Monthly Criminal Activity, updated as recently as the day before this
  build) are distributed solely as a CKAN datastore-wrapped pivot-table
  export (literal "Row Labels"/"(blank)"/"Grand Total" rows, not
  row-level incident records) or as raw XLSX downloads with no
  query/sort/filter API — the actual row-level, queryable CKAN resources
  (`INCIDENTTIME`, `Arrest_Date` fields) were all confirmed stale
  (max dates in 2023) despite newer-looking dataset metadata timestamps.
- Charlotte-Mecklenburg NC, Gilbert AZ, Durham NC, Greensboro NC,
  Stockton CA: their ArcGIS/Socrata hosts (gis.charlottenc.gov,
  maps.gilbertaz.gov, webgis2.durhamnc.gov, gis.greensboro-nc.gov,
  data.stocktonca.gov) were confirmed UNREACHABLE from this build
  environment across many repeated attempts over several minutes (while
  other ArcGIS/Socrata hosts, e.g. Cambridge and Charlottesville, and a
  plain internet control request, all succeeded in the same window) —
  a genuine, sustained network-level block, not a one-off timeout. Per
  this project's standard of never trusting metadata over a real direct
  query, these were left OUT rather than integrated on unverified data.
  A future phase should retry them once connectivity is confirmed.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.cambridge_ma_socrata import sync_cambridge_ma_crime
from app.services.ingestion.cary_nc_opendatasoft import sync_cary_nc_crime
from app.services.ingestion.charlottesville_va_arcgis import sync_charlottesville_va_crime

logger = logging.getLogger(__name__)

PHASE32_SYNC_FUNCTIONS = [
    ("cambridge_ma_incidents", sync_cambridge_ma_crime),
    ("cary_nc_incidents", sync_cary_nc_crime),
    ("charlottesville_va_incidents", sync_charlottesville_va_crime),
]


async def sync_all_phase32_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 32 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE32_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase32_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
