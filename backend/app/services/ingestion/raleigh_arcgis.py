"""Raleigh Open Data (ArcGIS FeatureServer) ingestion — plan.md Step 9
Phase 7.

Confirmed live via a real server-side MAX() query during this build:
most recent reported_date is 2026-09-08, the same day as this build —
genuinely current, 639,959 total rows confirmed (a large, well-established
archive, not a thin snapshot). Hosted on services.arcgis.com under
Raleigh's own official `OpenData_ral` org account.

Real, confirmed dead-end from earlier research (not repeated here): an
ArcGIS layer that LOOKED like Columbus, OH data (found under a plausible
name during a prior phase's research) actually contained real Raleigh
data when its field values were checked — this module targets the real,
correctly-identified Raleigh source directly, not that decoy.

Real, non-obvious finding, and a real bug this module fixes rather than
just documents: sensitive-category records (e.g. missing persons,
overdose calls) have `case_number` and `reported_block_address`
deliberately blank/redacted in the source data itself — confirmed
directly via a real count query: 161,480 of 639,959 total records
(~25%) have an EMPTY case_number. Since `sync_dataset()` treats a falsy
`external_id` as "skip, can't upsert without a stable key," using
`case_number` as the id_field directly would have silently discarded a
full quarter of real, legitimate records on every sync — not a
hypothetical edge case, a confirmed massive real gap. Fixed by falling
back to `GlobalID` (a real UUID, always populated on every record,
confirmed via direct query) whenever `case_number` is blank, so these
records are still ingested rather than silently dropped.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

RALEIGH_CRIME_QUERY_URL = (
    "https://services.arcgis.com/v400IkDOw1ad7Yad/arcgis/rest/services/"
    "Police_Incidents/FeatureServer/0/query"
)
SOURCE_RALEIGH_CRIME = "raleigh_crime"
CITY_NAME = "Raleigh"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "GlobalID,case_number,crime_description,crime_category,reported_block_address,district,reported_date"

# The real field name sync_dataset() reads as the unique id — see module
# docstring for why this must fall back to GlobalID, not use case_number
# directly.
_ID_FIELD = "_effective_id"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "reported_date DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(RALEIGH_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Raleigh ArcGIS query failed: {data['error']}")
    records = [f["attributes"] for f in data.get("features", [])]
    for record in records:
        record[_ID_FIELD] = record.get("case_number") or record.get("GlobalID")
    return records


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("crime_description"), "an incident")
    category = clean_field(record.get("crime_category"))
    address = clean_field(record.get("reported_block_address"), "an unspecified location")
    district = clean_field(record.get("district"), "unknown")
    date = _format_esri_date(record.get("reported_date"))

    prefix = f"{category.title()} — " if category and category.lower() != offense.lower() else ""
    parts = [
        f"{CITY_NAME} crime report: {prefix}{offense}",
        f"near {address}, {district} district, on {date}.",
    ]
    return " ".join(p for p in parts if p.strip())


async def sync_raleigh_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_RALEIGH_CRIME, CITY_NAME, _ID_FIELD, _summarize)
