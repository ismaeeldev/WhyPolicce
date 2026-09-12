"""Rochester, NY Open Data (self-hosted ArcGIS FeatureServer) ingestion —
plan.md Step 9 Phase 13.

Confirmed live via real server-side queries during this build: 146,661
total rows (layer 3, "2011 to Present" — layers 0-2 on this same service
are rolling 14/30/60-day windows of the same underlying data, not
ingested separately here), max(OccurredFrom_Timestamp) = 2026-09-04 (4
days before this build), 844 rows in the trailing 45-day window —
genuinely active. Unique id `Case_Number` confirmed 0% null.

Hosted on `maps.cityofrochester.gov` — a SELF-HOSTED municipal domain,
same class of risk as Houston/San Diego/Charlotte/Wichita, which all
turned out to be unreachable from this environment. Directly tested and
confirmed reachable here (same exception already found for Washington DC
and Indianapolis) — not rejected preemptively just for the hosting
pattern.

`Statute_Description` is a genuine, specific offense field (e.g. "GRAND
LARCENY AUTO OVER $100", "PETIT LARCENY") — no coarseness limitation
found. `Case_Status` used as a disposition field. No personal-identifier
fields found in this schema.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

ROCHESTER_CRIME_QUERY_URL = (
    "https://maps.cityofrochester.gov/arcgis/rest/services/RPD/"
    "RPD_Part_I_Crime/FeatureServer/3/query"
)
SOURCE_ROCHESTER_CRIME = "rochester_crime"
CITY_NAME = "Rochester"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "Case_Number,OccurredFrom_Timestamp,Statute_Description,Address_StreetFull,Case_Status"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "OccurredFrom_Timestamp DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(ROCHESTER_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Rochester ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("Statute_Description"), "an incident")
    address = clean_field(record.get("Address_StreetFull"), "an unspecified location")
    date = _format_esri_date(record.get("OccurredFrom_Timestamp"))
    status = clean_field(record.get("Case_Status"))

    parts = [f"{CITY_NAME} crime report: {offense.title()} near {address}, on {date}."]
    if status:
        parts.append(f"Case status: {status}.")
    return " ".join(p for p in parts if p.strip())


async def sync_rochester_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_ROCHESTER_CRIME, CITY_NAME, "Case_Number", _summarize)
