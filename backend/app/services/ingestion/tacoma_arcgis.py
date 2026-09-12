"""Tacoma, WA Open Data (ArcGIS FeatureServer, hosted on ArcGIS Online)
ingestion — plan.md Step 9 Phase 12.

Confirmed live via real server-side queries during this build: 230,197
total rows, max(DateOccurred) = 2026-09-06 (3 days before this build),
2,090 rows in the trailing 45-day window — genuinely active. Unique id
`CaseNo` confirmed 0% null.

`Description` is a genuine, specific offense field (e.g. "Larceny Theft",
"Counterfeiting/Forgery") — no coarseness limitation found. No
disposition field present. No personal-identifier fields found in this
schema.

Real, documented dataset scope limitation (from the agency itself, not a
data-quality bug): domestic violence and sexual offenses are explicitly
excluded from this dataset by TPD's own policy.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

TACOMA_CRIME_QUERY_URL = (
    "https://services3.arcgis.com/SCwJH1pD8WSn5T5y/arcgis/rest/services/"
    "TPD_RMS_Crime/FeatureServer/0/query"
)
SOURCE_TACOMA_CRIME = "tacoma_crime"
CITY_NAME = "Tacoma"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "CaseNo,DateOccurred,Description,Offense_Category,Address"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "DateOccurred DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(TACOMA_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Tacoma ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    description = clean_field(record.get("Description"), "an incident")
    category = clean_field(record.get("Offense_Category"))
    address = clean_field(record.get("Address"), "an unspecified location")
    date = _format_esri_date(record.get("DateOccurred"))

    detail = f" ({category})" if category and category.lower() != description.lower() else ""
    return f"{CITY_NAME} crime report: {description}{detail} near {address}, on {date}."


async def sync_tacoma_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_TACOMA_CRIME, CITY_NAME, "CaseNo", _summarize)
