"""Chattanooga, TN Open Data (ArcGIS FeatureServer, hosted on ArcGIS
Online) ingestion — plan.md Step 9 Phase 12.

Confirmed live via real server-side queries during this build: this
source is one of 11 year-partitioned FeatureServers (2015-2026, one per
year) — only the current-year 2026 layer is ingested here. 194,085 total
rows in the 2026 layer alone, 42,936 rows in the trailing 45-day window
(string-range comparison, see date-field note below) — genuinely active,
not a frozen archive. Unique id `Incident_Number` confirmed 0% null.

Real, confirmed field-type quirk: `Date_Logged` is stored as a plain
"YYYY-MM-DD" STRING field, not a true Esri date field — confirmed via a
direct schema check (`sqlTypeNVarchar`). A naive `ORDER BY ... DESC`
still sorts correctly for this specific "YYYY-MM-DD" format (lexicographic
ordering happens to match chronological ordering for this exact string
shape), so this module orders by it directly rather than needing
Sacramento-style `LIKE`-based date narrowing.

**Real, significant personal-identifier field found and confirmed via a
live sample, not just a field name/description — the exact class of gap
this project has been burned by before (Providence's Phase 11 "reporting_
officer" gap)**: the `Officer` field contains REAL, INDIVIDUAL, FULL NAMES
of responding officers on every sampled row (e.g. "Christian Gonzalez",
"Lucas M Wise", "Mason Mattero") — not badge numbers, not unit codes.
Deliberately excluded from the ingested field list entirely (not just the
summary text), same privacy posture as every prior city with officer-
identifying fields, and the most direct/serious instance of this pattern
found so far.

`Incident_Type` is a controlled-vocabulary code+label (e.g. "THR -
Threats", "FIG - Fight") — reasonably specific, not a bare UCR Part 1/2
code, though coarser than a full narrative offense description.
`Action_Taken` used as a disposition field.
"""

import logging

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

CHATTANOOGA_CRIME_QUERY_URL = (
    "https://services1.arcgis.com/j8dqo2DJE7mVUBU1/arcgis/rest/services/"
    "PoliceIncidents_2026/FeatureServer/0/query"
)
SOURCE_CHATTANOOGA_CRIME = "chattanooga_crime"
CITY_NAME = "Chattanooga"

DEFAULT_FETCH_LIMIT = 200

# Deliberately excludes `Officer` (real individual officer names) — see
# module docstring's privacy note.
_FIELDS = "Incident_Number,Date_Logged,Incident_Type,Location,Action_Taken"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "Date_Logged DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(CHATTANOOGA_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Chattanooga ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _summarize(record: dict) -> str:
    incident_type = clean_field(record.get("Incident_Type"), "an incident")
    location = clean_field(record.get("Location"), "an unspecified location")
    date = clean_field(record.get("Date_Logged"))
    date = date[:10] if date else "an unknown date"
    action = clean_field(record.get("Action_Taken"))

    parts = [f"{CITY_NAME} police incident: {incident_type} near {location}, on {date}."]
    if action:
        parts.append(f"Action taken: {action}.")
    return " ".join(p for p in parts if p.strip())


async def sync_chattanooga_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    # Incident_Number arrives as a float (esriFieldTypeDouble, confirmed
    # via schema check) — cast to a clean int-string id so external_id
    # doesn't end up storing something like "2026000000001.0".
    records = await _fetch_records(limit)
    for record in records:
        raw_id = record.get("Incident_Number")
        if raw_id is not None:
            try:
                record["Incident_Number"] = str(int(raw_id))
            except (TypeError, ValueError):
                pass
    return await sync_dataset(
        session, records, SOURCE_CHATTANOOGA_CRIME, CITY_NAME, "Incident_Number", _summarize
    )
