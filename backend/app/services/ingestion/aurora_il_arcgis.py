"""Aurora, IL Open Data (ArcGIS FeatureServer, hosted on ArcGIS Online)
ingestion — plan.md Step 9 Phase 16.

Not to be confused with Aurora, CO — a different Aurora rejected in an
earlier phase for lacking any incident-level dataset. This is a distinct
city (Aurora, Illinois) with a genuinely different, real, verified data
source.

Confirmed live via real server-side queries during this build: 80,131
total rows, max(REPORTED_ON) = 2026-08-27 (13 days before this build),
1,044 rows in the trailing 45-day window — genuinely active. Unique id
`INCIDENT_NUM` confirmed 0% null.

Real, confirmed schema limitation, same class of gap as Cincinnati/
Honolulu/Boise in earlier phases: `GROUPING` is the only category field,
and it is coarse (7-8 broad buckets, e.g. "TRAFFIC VIOLATIONS", "PROPERTY
CRIMES", "DRUG OFFENSES") — no granular offense-description field exists
in this schema. Summarized honestly at that coarse level. `STREETADDR` is
already street/intersection-level from the source itself. No disposition
field present. No personal-identifier fields found in this schema.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

AURORA_IL_CRIME_QUERY_URL = (
    "https://services1.arcgis.com/79UxTxnBeBW8JHY4/arcgis/rest/services/"
    "AuroraIL.Police_Incidents/FeatureServer/0/query"
)
SOURCE_AURORA_IL_CRIME = "aurora_il_crime"
CITY_NAME = "Aurora, IL"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "INCIDENT_NUM,REPORTED_ON,GROUPING,STREETADDR"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "REPORTED_ON DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(AURORA_IL_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Aurora IL ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    category = clean_field(record.get("GROUPING"), "an incident")
    address = clean_field(record.get("STREETADDR"), "an unspecified location")
    date = _format_esri_date(record.get("REPORTED_ON"))

    return f"{CITY_NAME} police incident: {category.title()} near {address}, on {date}."


async def sync_aurora_il_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_AURORA_IL_CRIME, CITY_NAME, "INCIDENT_NUM", _summarize)
