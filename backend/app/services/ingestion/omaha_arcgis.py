"""Omaha, NE Open Data (ArcGIS FeatureServer, hosted on ArcGIS Online, not
self-hosted) ingestion — plan.md Step 9 Phase 9.

Confirmed live via a real ArcGIS date-literal query during this build:
2,901 records since 2026-08-01, most recent `dteMidpoint` epoch
1788839701000 (2026-09-08). 160,201 total rows confirmed. Unique id `RB`
(report/booking number, e.g. "AT35610") confirmed 0% null via a direct
`RB IS NULL` count query.

Hosted on ArcGIS Online's own `services1.arcgis.com` domain, not a
self-hosted municipal GIS server — same reliable class of endpoint as
Virginia Beach's FeatureServer, not the self-hosted-domain risk pattern
that has failed for Houston/San Diego/Charlotte/Wichita.

Real fields confirmed clean of personal identifiers — no victim/officer
names, race, sex, or age fields on this layer. No disposition field
present (incident-only dataset).
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

OMAHA_CRIME_QUERY_URL = (
    "https://services1.arcgis.com/tIBLyYZX96jUntYm/arcgis/rest/services/"
    "Omaha_Police_Incident_Data_(View)/FeatureServer/0/query"
)
SOURCE_OMAHA_CRIME = "omaha_crime"
CITY_NAME = "Omaha"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "RB,dteMidpoint,NIBRSCategory,AddressBlock"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "dteMidpoint DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(OMAHA_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Omaha ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("NIBRSCategory"), "an incident")
    address = clean_field(record.get("AddressBlock"), "an unspecified location")
    date = _format_esri_date(record.get("dteMidpoint"))

    return f"{CITY_NAME} crime report: {offense} near {address}, on {date}."


async def sync_omaha_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_OMAHA_CRIME, CITY_NAME, "RB", _summarize)
