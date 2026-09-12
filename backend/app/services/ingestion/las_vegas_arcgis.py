"""Las Vegas Metropolitan Police Department Open Data (ArcGIS
FeatureServer) ingestion — plan.md Step 9 Phase 5.

Confirmed live via a real server-side MAX() query during this build:
most recent ReportedOn is 2026-09-06, two days before this build —
genuinely current, hosted on services.arcgis.com (Esri's own
infrastructure), owner account LVMPD_GIS_ADMIN — an official department
account, not a third-party mirror.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

LAS_VEGAS_CRIME_QUERY_URL = (
    "https://services.arcgis.com/jjSk6t82vIntwDbs/arcgis/rest/services/"
    "Weekly_Public_Crimes/FeatureServer/0/query"
)
SOURCE_LAS_VEGAS_CRIME = "las_vegas_crime"
CITY_NAME = "Las Vegas"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "Event_Number,Offense,OffenseCategory,ReportedOn,Location,LocationType,Area_Command,Weapons"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "ReportedOn DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(LAS_VEGAS_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Las Vegas ArcGIS query failed: {data['error']}")
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
    category = clean_field(record.get("OffenseCategory"))
    location = clean_field(record.get("Location"), "an unspecified location")
    location_type = clean_field(record.get("LocationType"))
    area = clean_field(record.get("Area_Command"), "an unspecified area command")
    date = _format_esri_date(record.get("ReportedOn"))
    weapon = clean_field(record.get("Weapons"))

    prefix = f"{category.title()} — " if category and category.lower() != offense.lower() else ""
    parts = [
        f"{CITY_NAME} crime report: {prefix}{offense.title()}",
        f"near {location}, area command {area}, on {date}.",
    ]
    if location_type:
        parts.append(f"Location type: {location_type.title()}.")
    if weapon and weapon.upper() != "NONE":
        parts.append(f"Weapon: {weapon.title()}.")
    return " ".join(p for p in parts if p.strip())


async def sync_las_vegas_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_LAS_VEGAS_CRIME, CITY_NAME, "Event_Number", _summarize)
