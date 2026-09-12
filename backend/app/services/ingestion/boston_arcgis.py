"""Boston Open Data (ArcGIS FeatureServer) ingestion — plan.md Step 9
Phase 6.

Confirmed live via a real server-side MAX() query during this build:
most recent REPORT_DATE is 2026-09-08, the same day as this build —
genuinely real-time. Hosted on services.arcgis.com under the Boston
Police Department's own `BPDMaps` org account (not a third-party
mirror).
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

BOSTON_CRIME_QUERY_URL = (
    "https://services.arcgis.com/sFnw0xNflSi8J0uh/arcgis/rest/services/"
    "Boston_Incidents_View/FeatureServer/0/query"
)
SOURCE_BOSTON_CRIME = "boston_crime"
CITY_NAME = "Boston"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "INC_NUM,OFFENSE_DESC,CRIME_PART,BLOCK,DISTRICT,NEIGHBORHOOD,PREMISE_DESC,REPORT_DATE"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "REPORT_DATE DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(BOSTON_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Boston ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("OFFENSE_DESC"), "an incident")
    block = clean_field(record.get("BLOCK"), "an unspecified location")
    district = clean_field(record.get("DISTRICT"), "unknown")
    neighborhood = clean_field(record.get("NEIGHBORHOOD"))
    premise = clean_field(record.get("PREMISE_DESC"))
    date = _format_esri_date(record.get("REPORT_DATE"))

    parts = [
        f"{CITY_NAME} crime report: {offense.title()}",
        f"near {block}"
        + (f" ({neighborhood} neighborhood)" if neighborhood else "")
        + f", district {district}, on {date}.",
    ]
    if premise:
        parts.append(f"Location type: {premise.title()}.")
    return " ".join(p for p in parts if p.strip())


async def sync_boston_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_BOSTON_CRIME, CITY_NAME, "INC_NUM", _summarize)
