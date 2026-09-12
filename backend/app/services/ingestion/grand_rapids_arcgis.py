"""Grand Rapids, MI Open Data (ArcGIS FeatureServer, hosted on ArcGIS
Online) ingestion — plan.md Step 9 Phase 13.

Confirmed live via real server-side queries during this build: 221,265
total rows, max(DATEOFOFFENSE) = 2026-08-01 (~5 weeks before this build —
slightly laggy but confirmed still genuinely active, not frozen), 1,242
rows in the trailing 45-day window. Unique id `INCNUMBER` confirmed 0%
null.

Real, confirmed field-naming trap caught by sampling actual values rather
than trusting field names: despite what the names suggest, `OFFENSETITLE`
is the MORE SPECIFIC offense field (e.g. "Family Or Domestic Trouble",
"Failure To Appear (Local Bench Warrant)") while `Offense_Description` is
actually the COARSER category field (e.g. "Local", "Obstructing
Justice") — the two fields are effectively reversed from what their names
imply. This module uses `OFFENSETITLE` as the primary offense text for
that reason, with `Offense_Description` only shown as a secondary
category when it's genuinely different. No disposition field found. No
personal-identifier fields found in this schema.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

GRAND_RAPIDS_CRIME_QUERY_URL = (
    "https://services2.arcgis.com/L81TiOwAPO1ZvU9b/arcgis/rest/services/"
    "GRPD_Crime_Data/FeatureServer/0/query"
)
SOURCE_GRAND_RAPIDS_CRIME = "grand_rapids_crime"
CITY_NAME = "Grand Rapids"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "INCNUMBER,DATEOFOFFENSE,OFFENSETITLE,Offense_Description,BLOCK_ADDRESS__INCIDENT_LOCATIONS"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "DATEOFOFFENSE DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(GRAND_RAPIDS_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Grand Rapids ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("OFFENSETITLE"), "an incident")
    category = clean_field(record.get("Offense_Description"))
    address = clean_field(record.get("BLOCK_ADDRESS__INCIDENT_LOCATIONS"), "an unspecified location")
    date = _format_esri_date(record.get("DATEOFOFFENSE"))

    detail = f" ({category})" if category and category.lower() != offense.lower() else ""
    return f"{CITY_NAME} crime report: {offense.title()}{detail} near {address}, on {date}."


async def sync_grand_rapids_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(
        session, records, SOURCE_GRAND_RAPIDS_CRIME, CITY_NAME, "INCNUMBER", _summarize
    )
