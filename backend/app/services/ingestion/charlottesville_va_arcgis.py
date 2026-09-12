"""Charlottesville, VA Open Data (ArcGIS FeatureServer/MapServer, hosted
on the city's own ArcGIS Server) ingestion — plan.md Step 9 Phase 32.

Discovered via `OpenPoliceData`'s source table, then independently
re-verified via direct HTTP queries before any code was written.

Confirmed live via real server-side queries during this build: 26,433
total rows, 1,412 rows since 2026-06-01 alone (confirmed via a
`returnCountOnly` query) — genuinely active, not a stale annual-label
dataset despite an OPD `coverage_end` date this project has learned not
to trust at face value. Max(DateReported) resolves (via direct epoch-ms
decoding) to 2026-09-09, two days before this build.

**Real personal-identifier finding, confirmed via a direct live sample
rather than trusting a field name alone**: this schema includes a
`ReportingOfficer` field populated with real officer full names (e.g.
"Young, Steven", "Thelin, Dennis", "Brown, Korrelle") — confirmed live.
Deliberately excluded from the ingested field list entirely (never even
requested from the source), same privacy posture as every other city in
this project with an officer/victim-identifying field (Dayton, Dallas,
LA, Nashville, Baltimore, and others).

`Offense` is a genuine, specific offense field (e.g. "Assault Simple",
"Assault Aggravated", "Hit and Run") — confirmed via direct sampling.
Location is already generalized to `BlockNumber` + `StreetName` by the
source itself, no exact address. `IncidentID` confirmed present and
usable as a unique external id.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

CHARLOTTESVILLE_VA_CRIME_QUERY_URL = (
    "https://gisweb.charlottesville.org/arcgis/rest/services/OpenData_2/MapServer/6/query"
)
SOURCE_CHARLOTTESVILLE_VA_CRIME = "charlottesville_va_incidents"
CITY_NAME = "Charlottesville, VA"

DEFAULT_FETCH_LIMIT = 200

# Deliberately excludes ReportingOfficer — see module docstring's privacy
# note.
_FIELDS = "IncidentID,Offense,BlockNumber,StreetName,DateReported"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "DateReported DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(CHARLOTTESVILLE_VA_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Charlottesville VA ArcGIS query failed: {data['error']}")
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
    block = clean_field(record.get("BlockNumber"))
    street = clean_field(record.get("StreetName"), "an unspecified location")
    location = f"{block} {street}".strip() if block else street
    date = _format_esri_date(record.get("DateReported"))

    return f"{CITY_NAME} crime report: {offense} near {location}, on {date}."


async def sync_charlottesville_va_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(
        session, records, SOURCE_CHARLOTTESVILLE_VA_CRIME, CITY_NAME, "IncidentID", _summarize
    )
