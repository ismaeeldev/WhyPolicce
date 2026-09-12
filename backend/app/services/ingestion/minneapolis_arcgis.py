"""Minneapolis Open Data (ArcGIS FeatureServer) ingestion — plan.md
Step 9 Phase 7.

Confirmed live via a real server-side MAX() query during this build:
most recent Reported_Date is 2026-09-08, the same day as this build —
genuinely current, 390,903 total rows confirmed (a substantial, healthy
dataset).

Real, confirmed dead-end from earlier research (not repeated here):
ArcGIS Online's public search surfaced a "Police_Incidents_2018_PIMS"
layer under owner `City_of_Minneapolis` that looked plausible but tested
frozen at 2019-01-01 via a MAX() query. This module targets a DIFFERENT
layer (`Crime_Data`, found by searching the city's own org account
directly rather than a generic public keyword search) that is genuinely
current — the same "verify the real max date directly, don't trust a
promising-looking name" discipline established since Denver's near-
identical stale-duplicate-service finding in Phase 2.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

MINNEAPOLIS_CRIME_QUERY_URL = (
    "https://services.arcgis.com/afSMGVsC7QlRK1kZ/arcgis/rest/services/"
    "Crime_Data/FeatureServer/0/query"
)
SOURCE_MINNEAPOLIS_CRIME = "minneapolis_crime"
CITY_NAME = "Minneapolis"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "Case_Number,Offense,Offense_Category,Reported_Date,Address,Precinct,Neighborhood"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "Reported_Date DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(MINNEAPOLIS_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Minneapolis ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("Offense"), "an incident")
    category = clean_field(record.get("Offense_Category"))
    address = clean_field(record.get("Address"), "an unspecified location")
    precinct = clean_field(record.get("Precinct"), "unknown")
    neighborhood = clean_field(record.get("Neighborhood"))
    date = _format_esri_date(record.get("Reported_Date"))

    prefix = f"{category.title()} — " if category and category.lower() != offense.lower() else ""
    parts = [
        f"{CITY_NAME} crime report: {prefix}{offense}",
        f"near {address}"
        + (f" ({neighborhood} neighborhood)" if neighborhood else "")
        + f", precinct {precinct}, on {date}.",
    ]
    return " ".join(p for p in parts if p.strip())


async def sync_minneapolis_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_MINNEAPOLIS_CRIME, CITY_NAME, "Case_Number", _summarize)
