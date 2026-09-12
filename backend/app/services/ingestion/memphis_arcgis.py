"""Memphis Open Data (ArcGIS FeatureServer) ingestion — plan.md Step 9
Phase 5.

Confirmed live via a real server-side MAX() query during this build:
most recent Offense_Datetime is 2026-09-06, two days before this build —
genuinely current, hosted on services2.arcgis.com (Esri's own
infrastructure).

Real, confirmed dead-end ruled out during research (not repeated here):
Memphis's old Socrata dataset (data.memphistn.gov, resource id n7ue-iwew)
is confirmed dead (404) — the city has fully migrated its open-data
hosting to ArcGIS Hub. This module targets the real, current replacement
(MPD_Public_Safety_Incidents), not the dead legacy URL.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

MEMPHIS_CRIME_QUERY_URL = (
    "https://services2.arcgis.com/saWmpKJIUAjyyNVc/arcgis/rest/services/"
    "MPD_Public_Safety_Incidents/FeatureServer/0/query"
)
SOURCE_MEMPHIS_CRIME = "memphis_crime"
CITY_NAME = "Memphis"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "Crime_ID,UCR_Description,UCR_Category,NIBRS_Group,Offense_Datetime,Street_Address,Precinct"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "Offense_Datetime DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(MEMPHIS_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Memphis ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("UCR_Description"), "an incident")
    category = clean_field(record.get("UCR_Category"))
    group = clean_field(record.get("NIBRS_Group"))
    address = clean_field(record.get("Street_Address"), "an unspecified location")
    precinct = clean_field(record.get("Precinct"), "unknown")
    date = _format_esri_date(record.get("Offense_Datetime"))

    prefix = f"{category.title()} — " if category and category.lower() != offense.lower() else ""
    group_note = f" (NIBRS Group {group})" if group else ""
    parts = [
        f"{CITY_NAME} crime report: {prefix}{offense.title()}{group_note}",
        f"near {address}, {precinct} precinct, on {date}.",
    ]
    return " ".join(p for p in parts if p.strip())


async def sync_memphis_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_MEMPHIS_CRIME, CITY_NAME, "Crime_ID", _summarize)
