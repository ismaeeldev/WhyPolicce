"""Louisville Open Data (ArcGIS FeatureServer) ingestion — plan.md Step 9
Phase 4.

Confirmed live via a real server-side MAX() query during this build:
most recent date_reported is 2026-09-06, two days before this build —
genuinely current, hosted on services1.arcgis.com (Esri's own
infrastructure), not a self-hosted municipal domain.

Real, non-obvious finding: this dataset publishes ONE FeatureServer PER
CALENDAR YEAR (crime_data_2026, crime_data_2025, etc., a new item each
January per the city's own documentation) — unlike every prior ArcGIS
city module here, which query a single stable service. This module
hardcodes the 2026 service for now; whoever revisits this after
2026-12-31 must update CRIME_QUERY_URL to that year's new service (same
"needs a yearly check" caveat San Jose's per-year CSV resources have,
just via a different mechanism).

Real fields include `badge_id` (the reporting officer's badge number) —
deliberately excluded from the summary text, same privacy posture as
every other city with officer/victim-identifying fields (Dallas, LA,
Nashville, Baltimore).
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

# See module docstring — must be updated to the new year's service after
# 2026-12-31.
LOUISVILLE_CRIME_QUERY_URL = (
    "https://services1.arcgis.com/79kfd2K6fskCAkyg/arcgis/rest/services/"
    "crime_data_2026/FeatureServer/0/query"
)
SOURCE_LOUISVILLE_CRIME = "louisville_crime"
CITY_NAME = "Louisville"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = (
    "incident_number,offense_classification,nibrs_group_name,"
    "date_reported,location_category,block_address,lmpd_division,was_offense_completed"
)


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "date_reported DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(LOUISVILLE_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Louisville ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("offense_classification"), "an incident")
    group = clean_field(record.get("nibrs_group_name"))
    location_type = clean_field(record.get("location_category"))
    address = clean_field(record.get("block_address"), "an unspecified location")
    division = clean_field(record.get("lmpd_division"), "an unspecified division")
    date = _format_esri_date(record.get("date_reported"))
    completed = record.get("was_offense_completed") == "YES"

    prefix = f"NIBRS Group {group} " if group else ""
    parts = [
        f"{CITY_NAME} {prefix}crime report: {offense.title()}",
        f"near {address}, {division}, on {date}.",
    ]
    if location_type:
        parts.append(f"Location type: {location_type.title()}.")
    parts.append("Offense completed." if completed else "Offense attempted, not completed.")
    return " ".join(p for p in parts if p.strip())


async def sync_louisville_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_LOUISVILLE_CRIME, CITY_NAME, "incident_number", _summarize)
