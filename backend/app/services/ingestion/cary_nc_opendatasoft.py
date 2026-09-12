"""Cary, NC Open Data (Opendatasoft v2.1 Explore API) ingestion — plan.md
Step 9 Phase 32.

Discovered via `OpenPoliceData`'s source table (`data.townofcary.org`,
TableType INCIDENTS, dataset id `cpd-incidents` confirmed directly via
the catalog search endpoint), then independently re-verified via direct
HTTP queries before any code was written.

Confirmed live via direct queries during this build: 26,279 total rows,
max(date_from) = 2026-07-26 (about 6.5 weeks before this build) — real
and current, no dummy/decade-old rows found mixed in near the top when
sorted by date_from descending.

**Real non-unique-ID finding, confirmed directly rather than assumed**:
`incident_number` is NOT a unique per-row key — one incident can list
multiple offenses as separate rows sharing the same incident_number
(confirmed live: incident_number "26002770" appears twice, once as
"TRESPASSING" and once as "LARCENY - SHOPLIFTING", both with identical
date_from). This is the same real multi-offense-per-incident shape
`socrata_base.sync_dataset()` was already hardened for during Phase 1
(Seattle), so this module builds a composite external id
(`incident_number` + `map_reference`, the offense-code field) rather
than risking silent row loss from `sync_dataset`'s
last-seen-per-external-id batch dedup collapsing genuinely distinct
offense rows together.

`geocode` is already generalized to a bare street name by the source
itself (e.g. "KILDAIRE FARM RD", "E CHATHAM ST") — no block/address
number present in this field, confirmed via direct sampling. No victim/
officer name fields present in this schema at all.
"""

import logging

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import DEFAULT_FETCH_LIMIT, clean_field, sync_dataset

logger = logging.getLogger(__name__)

_CARY_RECORDS_URL = (
    "https://data.townofcary.org/api/explore/v2.1/catalog/datasets/cpd-incidents/records"
)
SOURCE_CARY_NC_CRIME = "cary_nc_incidents"
CITY_NAME = "Cary, NC"


async def _fetch_records(limit: int) -> list[dict]:
    # Opendatasoft v2.1's Explore API caps `limit` at 100 per request
    # (confirmed live: limit=200 returns a 400 InvalidRESTParameterError),
    # unlike the Socrata/ArcGIS 200-row default used elsewhere in this
    # project — capped here rather than raised at the caller.
    params = {
        "limit": min(limit, 100),
        "order_by": "date_from desc",
        "select": "incident_number,map_reference,crime_type,date_from,geocode,district",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(_CARY_RECORDS_URL, params=params)
        response.raise_for_status()
        data = response.json()
    return data.get("results", [])


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("crime_type"), "an incident")
    location = clean_field(record.get("geocode"), "an unspecified location")
    date = clean_field(record.get("date_from"))
    date = date[:10] if date else "an unknown date"

    return f"{CITY_NAME} crime report: {offense.title()} near {location}, on {date}."


async def sync_cary_nc_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    # See module docstring — incident_number alone is not unique
    # (multi-offense incidents share one), so a composite id is used.
    for record in records:
        incident_number = clean_field(record.get("incident_number"))
        map_reference = clean_field(record.get("map_reference"))
        record["_composite_id"] = f"{incident_number}-{map_reference}"
    return await sync_dataset(
        session, records, SOURCE_CARY_NC_CRIME, CITY_NAME, "_composite_id", _summarize
    )
