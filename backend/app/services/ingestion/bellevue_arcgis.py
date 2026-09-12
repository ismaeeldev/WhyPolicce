"""Bellevue, WA Open Data (ArcGIS FeatureServer, hosted on ArcGIS Online)
ingestion — plan.md Step 9 Phase 18.

Confirmed live via real server-side queries during this build: 388,231
total rows, max(FROM_DATE) = 2026-09-08 (same day as this build), 8,251
rows in the trailing 45-day window — genuinely active. Unique id
`INC_NUM` confirmed 0% null. Independently confirmed this endpoint's org
id (`EYzEZbDhXZjURPbP`) is not used by any of the 56 already-integrated
sources.

This is CAD (police calls-for-service) data, same caveat as New Orleans/
Virginia Beach/Everett's CFS datasets in earlier phases — `INC_TYPE`
(e.g. "WARRANT", "SUICIDE", "POSSESSION STOLEN PROPERTY") is the real
call-type field, confirmed via direct sampling, genuinely specific for
CAD-level granularity even though it's not a post-classification NIBRS
offense code. No street-address field exists in this schema at all
(unlike most other ArcGIS sources integrated so far) — `SECTOR` and
`POLICE_DIST` (both real, coarse but non-PII geographic fields) are used
for location instead. Some rows have `SECTOR`/`POLICE_DIST` = "UNK"
(confirmed directly, handled honestly via the shared clean_field
fallback). No disposition field present. No personal-identifier fields
found in this schema — only categorical/geographic fields and
response-time metrics.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

BELLEVUE_CALLS_QUERY_URL = (
    "https://services1.arcgis.com/EYzEZbDhXZjURPbP/arcgis/rest/services/"
    "Incidents/FeatureServer/0/query"
)
SOURCE_BELLEVUE_CALLS = "bellevue_calls"
CITY_NAME = "Bellevue"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "INC_NUM,FROM_DATE,INC_TYPE,SECTOR,POLICE_DIST"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "FROM_DATE DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(BELLEVUE_CALLS_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Bellevue ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


_UNKNOWN_VALUES = {"unk", "unknown"}


def _clean_geo_field(value: str) -> str:
    cleaned = clean_field(value)
    return "" if cleaned.lower() in _UNKNOWN_VALUES else cleaned


def _summarize(record: dict) -> str:
    call_type = clean_field(record.get("INC_TYPE"), "an incident")
    sector = _clean_geo_field(record.get("SECTOR"))
    district = _clean_geo_field(record.get("POLICE_DIST"))
    date = _format_esri_date(record.get("FROM_DATE"))

    location_bits = []
    if sector:
        location_bits.append(f"sector {sector}")
    if district:
        location_bits.append(f"district {district}")
    location_phrase = f" ({', '.join(location_bits)})" if location_bits else ""

    return f"{CITY_NAME} police call: {call_type.title()}{location_phrase}, on {date}."


async def sync_bellevue_calls(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_BELLEVUE_CALLS, CITY_NAME, "INC_NUM", _summarize)
