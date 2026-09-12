"""Boulder, CO Open Data (ArcGIS FeatureServer, hosted on ArcGIS Online)
ingestion — plan.md Step 9 Phase 16.

Confirmed live via real server-side queries during this build: 87,708
total rows, max(Report_Date) = 2026-09-07 (2 days before this build),
1,779 rows in the trailing 45-day window — genuinely active. Unique id
`Report_Number` confirmed 0% null. Independently confirmed this
endpoint's org id (`ePKBjXrBZ2vEEgWd`) is distinct from Denver's
already-integrated org id — not a duplicate.

`vio_desc` is a genuine, specific statute-level offense field (e.g.
"CRIMINAL IMPERSONATION - FEL", "UNREASONABLE NOISE - 11 PM TO 7 AM") —
no coarseness limitation found, notably more detailed than several other
recent cities' offense fields. `nibrs_offense` provides a standard NIBRS
category as a secondary label. Address is already pre-anonymized to
block ranges by the source itself (e.g. "1XX COLLEGE"), with some rows
showing "Valid Address Unavailable" (handled honestly via the shared
clean_field fallback). No disposition field present.

A separate, much smaller "BPD_Crime_Incident_Blotter" layer on this same
service has a free-text `auto_narrative` field — deliberately NOT used by
this module, since free text is a real, unreviewed PII risk (unlike the
structured fields used here, which were directly sampled and confirmed
clean).
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

BOULDER_CRIME_QUERY_URL = (
    "https://services.arcgis.com/ePKBjXrBZ2vEEgWd/arcgis/rest/services/"
    "BPD_Offenses/FeatureServer/0/query"
)
SOURCE_BOULDER_CRIME = "boulder_crime"
CITY_NAME = "Boulder"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "Report_Number,Report_Date,vio_desc,nibrs_offense,STAddress"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "Report_Date DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(BOULDER_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Boulder ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("vio_desc"), "an incident")
    category = clean_field(record.get("nibrs_offense"))
    address = clean_field(record.get("STAddress"), "an unspecified location")
    date = _format_esri_date(record.get("Report_Date"))

    detail = f" ({category})" if category and category.lower() != offense.lower() else ""
    return f"{CITY_NAME} crime report: {offense.title()}{detail} near {address}, on {date}."


async def sync_boulder_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_BOULDER_CRIME, CITY_NAME, "Report_Number", _summarize)
