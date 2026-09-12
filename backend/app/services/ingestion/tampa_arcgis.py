"""Tampa, FL Open Data (ArcGIS FeatureServer, rolling 365-day public
crimes layer) ingestion — plan.md Step 9 Phase 10.

Confirmed live via real server-side queries during this build: 5,085
total rows, max(reportdate) = 2026-09-07 (1 day before this build), 513
rows in the trailing 45-day window. The low total row count (5,085) is
expected and correct, not a red flag — this layer (`crimes_public_365days`)
is a deliberately rolling 365-day window by design, confirmed by its own
name, not a thin/stale dataset like San Francisco's real 49-row rejection
in an earlier phase. Unique id `offenseid` confirmed 0% null.

`nibrsdesc` is a genuine, specific offense-description field (a real
coded-value domain with dozens of distinct NIBRS categories, e.g. "Motor
Vehicle Theft", "Burglary/Breaking & Entering") — no Cincinnati-style
coarseness limitation found. `casestatus` (e.g. "REFERRED") used as a
disposition field.

**Real personal-identifier field found and excluded**: `officer` (the
reporting officer's badge/ID number, e.g. "96926") is present and 0% null
in this schema — confirmed directly, then deliberately excluded from the
summary, same privacy posture as every other city with officer-
identifying fields (Virginia Beach's `Officer_Id`, etc.). A `narrative`
field also exists in the schema but was confirmed 100% null in a live
sample — no free-text narrative leakage risk from this dataset.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

TAMPA_CRIME_QUERY_URL = (
    "https://services1.arcgis.com/IbNXlmt2RVVRCZ6M/arcgis/rest/services/"
    "crimes_public_365days/FeatureServer/0/query"
)
SOURCE_TAMPA_CRIME = "tampa_crime"
CITY_NAME = "Tampa"

DEFAULT_FETCH_LIMIT = 200

# Deliberately excludes `officer` (reporting-officer badge/ID) — see
# module docstring's privacy note.
_FIELDS = "offenseid,reportdate,nibrsdesc,fulladdr,casestatus"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "reportdate DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(TAMPA_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Tampa ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("nibrsdesc"), "an incident")
    address = clean_field(record.get("fulladdr"), "an unspecified location")
    date = _format_esri_date(record.get("reportdate"))
    status = clean_field(record.get("casestatus"))

    parts = [f"{CITY_NAME} crime report: {offense} near {address}, on {date}."]
    if status:
        parts.append(f"Case status: {status.title()}.")
    return " ".join(p for p in parts if p.strip())


async def sync_tampa_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_TAMPA_CRIME, CITY_NAME, "offenseid", _summarize)
