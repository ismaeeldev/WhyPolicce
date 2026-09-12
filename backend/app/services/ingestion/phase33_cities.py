"""Phase 33 multi-city sync orchestrator — plan.md Step 9.

Seventh geographic-expansion phase. Unlike Phase 27-32, this phase did
NOT re-query `OpenPoliceData` — its source table was confirmed genuinely
exhausted of known candidates as of Phase 32 (no library update since
v0.12, and no new relevant sources found on re-check). Instead, this
phase used fresh manual web research (Socrata catalog search plus
targeted WebSearch queries) to find candidates OpenPoliceData doesn't
index at all.

Runs the 4 Phase 33 ingestions (Oakland CA, West Hollywood CA, Rockford
IL, Winnebago County IL) in one call, same isolation pattern as every
prior phase orchestrator.

Several other candidates researched this phase were rejected and are
NOT wired in here:
- Wichita, KS: real live ArcGIS FeatureServer (`gismaps.wichita.gov`)
  confirmed via ArcGIS Online's item search, but the host itself was
  UNREACHABLE (ConnectTimeout) from this build environment on repeated
  attempts — a network-block rejection, not a data-quality one. Worth
  revisiting in a future phase once connectivity is confirmed.
- Salt Lake City, UT: the only discoverable crime FeatureServer
  (`SLCPD_Crimes2018`) requires an ArcGIS auth token ("Token Required",
  error 499) for anonymous queries — not a genuinely public API.
- Corpus Christi, TX: its ArcGIS org's crime-related items are all
  abandoned 2019 datasets; its own DCAT feed
  (gis-corpus.opendata.arcgis.com) lists no live crime/police dataset.
- Albany, NY: `data.albanyny.gov` does not resolve (DNS failure) from
  this build environment — the domain referenced by OpenPoliceData/
  search results appears dead or renamed.
- Madison, WI: its ArcGIS `Police Incident Reports` layer
  (maps.cityofmadison.com) returns HTTP 200 with an ArcGIS-level
  "Service not found" error — a stale/renamed endpoint, not a working
  API despite showing up in ArcGIS Online's own item search.
- Tucson, AZ and Kansas City, MO: both confirmed to already be
  integrated (tucson_arcgis.py Phase 6, kansas_city_socrata.py) under
  different dataset URLs than the ones surfaced by this phase's fresh
  search — correctly left alone rather than double-integrated.
- Des Moines, IA: its only live ArcGIS Feature Services
  (`Des_Moines_Police_Calls_for_Service_by_Day_and_Time_2023`, etc.) are
  pre-aggregated day/hour/priority pivot tables, not row-level incident
  records — same rejection class as this project's earlier Pittsburgh
  CKAN pivot-table rejection (Phase 32).
- Atlanta, GA: the only ArcGIS Feature Service found
  (`Atlanta_Police_Crime_Reports__UCR__2009_to_March_2020`) is an
  explicitly abandoned dataset (title states its own end date, March
  2020) — a genuine multi-year freshness gap, not a live source.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import describe_sync_error

from app.services.ingestion.oakland_ca_socrata import sync_oakland_ca_crime
from app.services.ingestion.west_hollywood_ca_socrata import sync_west_hollywood_ca_crime
from app.services.ingestion.rockford_il_socrata import sync_rockford_il_cfs
from app.services.ingestion.winnebago_county_il_socrata import sync_winnebago_county_il_cfs

logger = logging.getLogger(__name__)

PHASE33_SYNC_FUNCTIONS = [
    ("oakland_ca_crime", sync_oakland_ca_crime),
    ("west_hollywood_ca_crime", sync_west_hollywood_ca_crime),
    ("rockford_il_cfs", sync_rockford_il_cfs),
    ("winnebago_county_il_cfs", sync_winnebago_county_il_cfs),
]


async def sync_all_phase33_cities(session: Session, limit: int | None = None) -> list[dict]:
    """Runs every Phase 33 city sync. Same rollback-on-failure discipline
    as every prior phase orchestrator."""
    results = []
    for source_name, sync_fn in PHASE33_SYNC_FUNCTIONS:
        try:
            kwargs = {} if limit is None else {"limit": limit}
            results.append(await sync_fn(session, **kwargs))
        except Exception as exc:
            logger.exception("phase33_cities: %s sync failed, continuing with other cities", source_name)
            session.rollback()
            results.append({"source": source_name, "error": describe_sync_error(exc)})
    return results
