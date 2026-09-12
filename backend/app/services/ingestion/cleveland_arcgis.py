"""Cleveland, OH Open Data (ArcGIS FeatureServer, hosted on ArcGIS Online,
not self-hosted) ingestion — plan.md Step 9 Phase 10.

Confirmed live via real server-side queries during this build: 59,081
total rows, max(ReportedDate) = 2026-09-08 (same day as this build), 9,081
rows in the trailing 45-day window — genuinely active. Unique id
`CaseNumber` confirmed 0.0017% null (1/59,081, effectively clean).

Real, confirmed schema limitation on the more-specific offense field:
`StatDesc` ("more specific classification... per statute") is 16.19% null
(9,563/59,081) — checked directly, not assumed clean by default per this
project's post-Raleigh/Virginia-Beach discipline of checking every
candidate field's blank rate, not just the unique-id field. Rather than
skip or fabricate detail for those rows, the summarizer falls back to
`IncidentDesc` (a NIBRS-derived code description, always present in the
sample checked) whenever `StatDesc` is blank.

Address is already house-number-redacted by the source itself
("Address_Public" — house numbers replaced with block-level XX'd digits).
No disposition field present. No personal-identifier fields found.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

CLEVELAND_CRIME_QUERY_URL = (
    "https://services3.arcgis.com/dty2kHktVXHrqO8i/arcgis/rest/services/"
    "Crime_Incidents_P1RMS/FeatureServer/0/query"
)
SOURCE_CLEVELAND_CRIME = "cleveland_crime"
CITY_NAME = "Cleveland"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "CaseNumber,ReportedDate,StatDesc,IncidentDesc,Address_Public,NEIGHBORHOOD"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "ReportedDate DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(CLEVELAND_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Cleveland ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    stat_desc = clean_field(record.get("StatDesc"))
    incident_desc = clean_field(record.get("IncidentDesc"))
    offense = stat_desc or incident_desc or "an incident"
    address = clean_field(record.get("Address_Public"), "an unspecified location")
    neighborhood = clean_field(record.get("NEIGHBORHOOD"))
    date = _format_esri_date(record.get("ReportedDate"))

    return (
        f"{CITY_NAME} crime report: {offense} near {address}"
        + (f" ({neighborhood})" if neighborhood else "")
        + f", on {date}."
    )


async def sync_cleveland_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_CLEVELAND_CRIME, CITY_NAME, "CaseNumber", _summarize)
