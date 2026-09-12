"""Dayton, OH Open Data (ArcGIS FeatureServer, hosted on ArcGIS Online)
ingestion — plan.md Step 9 Phase 27.

Discovered via `OpenPoliceData`'s source table, then independently
re-verified via direct HTTP queries before any code was written.

Confirmed live via real server-side queries during this build: 52,108
total rows, max(Commit_Date) = 2026-09-08 (same day as this build), 1,777
rows in the trailing 45-day window — genuinely active. Unique id
`DIBRS_Number` confirmed 0% null.

`Crime_Description` is a genuine, specific offense field (e.g. "SIMPLE
ASSAULT", "BREAKING AND ENTERING", "DESTRUCTION/DAMAGE/VANDALISM OF
PROPERTY") — confirmed via direct sampling.

**Real, significant personal-identifier finding, confirmed via a direct
live sample rather than trusting a field name alone**: this schema
contains genuine victim demographic fields — `Victim_Age` (banded, e.g.
"36-45"), `Victim_Race`, `Victim_Sex`, `Victim_Eth`, and
`Relationship_To_Victim` — all confirmed populated with real values on
sampled rows. Deliberately excluded from the ingested field list
entirely (never even requested from the source, not just excluded from
the summary), same privacy posture as every other city with victim/
officer-identifying fields found across this project (Dallas, LA,
Nashville, Baltimore, and others). `Booking_Number` also excluded as a
potential individual-identifying field, not reviewed for safety.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

DAYTON_CRIME_QUERY_URL = (
    "https://services2.arcgis.com/3dDB2Kk6kuA2gIGw/arcgis/rest/services/"
    "Crimes_OpenData_HOSTED/FeatureServer/0/query"
)
SOURCE_DAYTON_CRIME = "dayton_crime"
CITY_NAME = "Dayton"

DEFAULT_FETCH_LIMIT = 200

# Deliberately excludes Victim_Age/Victim_Race/Victim_Sex/Victim_Eth/
# Relationship_To_Victim/Booking_Number — see module docstring's privacy
# note.
_FIELDS = "DIBRS_Number,Commit_Date,Crime_Description,District,Neighborhood"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "Commit_Date DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(DAYTON_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Dayton ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("Crime_Description"), "an incident")
    district = clean_field(record.get("District"))
    neighborhood = clean_field(record.get("Neighborhood"))
    date = _format_esri_date(record.get("Commit_Date"))

    location = neighborhood or (f"district {district}" if district else "an unspecified location")
    return f"{CITY_NAME} crime report: {offense.title()} in {location}, on {date}."


async def sync_dayton_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_DAYTON_CRIME, CITY_NAME, "DIBRS_Number", _summarize)
