"""Nashville Open Data (ArcGIS FeatureServer) ingestion — plan.md Step 9
Phase 3, substituted for San Diego.

**Why Nashville, not San Diego:** San Diego's real crime source
(webmaps.sandiego.gov, a self-hosted municipal ArcGIS Server, not
services.arcgis.com) was found and its exact FeatureServer URL confirmed
via its own official crime dashboard's config — but that specific host
genuinely refuses every connection from this environment (HTTPS, HTTP,
both standard ports, explicit IP resolution all timed out, while
services.arcgis.com itself connects fine) — the same real, confirmed
network-level block already found for Houston's houstontx.gov domain.
Per explicit product decision, substituted with a different, equally-real
major city rather than force a connection that provably can't succeed
from here.

Confirmed live via a real server-side MAX() query during this build (not
assumed): most recent Incident_Occurred is 2026-09-08, the same day as
this build — genuinely current.

Real, non-obvious finding: `Incident_Number` is NOT a unique key — one
incident with multiple offenses shares one Incident_Number across
multiple rows (same class of bug already found and fixed for Seattle and
Dallas). The real per-row unique field is `Primary_Key`
(`{incident_number}_{offense_number}`).
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

NASHVILLE_CRIME_QUERY_URL = (
    "https://services2.arcgis.com/HdTo6HJqh92wn4D8/arcgis/rest/services/"
    "Metro_Nashville_Police_Department_Incidents_view/FeatureServer/0/query"
)
SOURCE_NASHVILLE_CRIME = "nashville_crime"
CITY_NAME = "Nashville"

DEFAULT_FETCH_LIMIT = 200

# Real fields confirmed via a live sample during this build. Deliberately
# excludes every victim demographic field (Victim_Gender/Race/Ethnicity/
# Age-adjacent Victim_Description) present in the real schema — same
# privacy posture already established for Dallas/LA: describe the
# incident, never the people involved.
_FIELDS = (
    "Primary_Key,Offense_Description,Incident_Occurred,Incident_Location,"
    "Location_Description,Domestic_Related"
)


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "Incident_Occurred DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(NASHVILLE_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Nashville ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("Offense_Description"), "an incident")
    location = clean_field(record.get("Incident_Location"), "an unspecified location")
    location_type = clean_field(record.get("Location_Description"))
    date = _format_esri_date(record.get("Incident_Occurred"))
    is_domestic = record.get("Domestic_Related") == "Yes"

    parts = [
        f"{CITY_NAME} crime report: {offense.title()}",
        f"near {location}, on {date}.",
    ]
    if location_type:
        parts.append(f"Location type: {location_type.title()}.")
    if is_domestic:
        parts.append("Flagged as domestic-related.")
    return " ".join(p for p in parts if p.strip())


async def sync_nashville_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_NASHVILLE_CRIME, CITY_NAME, "Primary_Key", _summarize)
