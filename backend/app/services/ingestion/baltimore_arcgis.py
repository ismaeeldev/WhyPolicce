"""Baltimore Open Data (ArcGIS FeatureServer) ingestion — plan.md Step 9
Phase 4.

Confirmed live via a real server-side MAX() query during this build:
most recent CrimeDateTime is 2026-09-01, one week before this build —
genuinely current, hosted on services1.arcgis.com (Esri's own
infrastructure).

Real, confirmed dead-end ruled out during research (not repeated here):
Baltimore's older "Part1_Crime" / "Part 1 Crime Data (Legacy SRS)"
FeatureServer on the same ArcGIS org was checked via the same MAX()
technique and found to be abandoned (latest record 2023-02-12) —
superseded by this NIBRS Group A dataset when Baltimore adopted NIBRS
reporting on 2025-01-01. Confirming a dataset's real max date directly
before trusting it, not just its portal listing, is now standard practice
in this project after Denver's near-identical stale-duplicate-service
finding in Phase 2.

Real fields include victim demographics (Gender, Age, Race, Ethnicity) —
deliberately excluded from the summary text, same privacy posture as
Dallas/LA/Nashville.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

BALTIMORE_CRIME_QUERY_URL = (
    "https://services1.arcgis.com/UWYHeuuJISiGmgXx/arcgis/rest/services/"
    "NIBRS_GroupA_Crime_Data/FeatureServer/0/query"
)
SOURCE_BALTIMORE_CRIME = "baltimore_crime"
CITY_NAME = "Baltimore"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "CCNumber,Description,CrimeDateTime,Location,Neighborhood,New_District,Weapon,PremiseType"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "CrimeDateTime DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(BALTIMORE_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Baltimore ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("Description"), "an incident")
    location = clean_field(record.get("Location"), "an unspecified location")
    neighborhood = clean_field(record.get("Neighborhood"))
    district = clean_field(record.get("New_District"), "unknown")
    date = _format_esri_date(record.get("CrimeDateTime"))
    weapon = clean_field(record.get("Weapon"))
    premise = clean_field(record.get("PremiseType"))

    parts = [
        f"{CITY_NAME} crime report: {offense.title()}",
        f"near {location}"
        + (f" ({neighborhood.title()} neighborhood)" if neighborhood else "")
        + f", {district.title()} district, on {date}.",
    ]
    if premise:
        parts.append(f"Location type: {premise.title()}.")
    if weapon and weapon.upper() != "NONE":
        parts.append(f"Weapon: {weapon.replace('_', ' ').title()}.")
    return " ".join(p for p in parts if p.strip())


async def sync_baltimore_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_BALTIMORE_CRIME, CITY_NAME, "CCNumber", _summarize)
