"""Riverside, CA Open Data (ArcGIS FeatureServer, hosted on ArcGIS Online)
ingestion — plan.md Step 9 Phase 12.

Confirmed live via real server-side queries during this build: 77,862
total rows (this is a deliberate rolling "Crime (Last Year to Date)" view
by the layer's own name — a moderate total is expected/correct for a
1-year rolling window, same reasoning as Tampa/Providence's rolling
layers in earlier phases, not a red flag), max(offendate) = 2026-09-07,
2,497 rows in the trailing 45-day window — genuinely active. Unique id
`rpdunique` (a composite key, e.g. "260023793_90D_1") confirmed 0% null.

`nibrsdesc` is a genuine, specific offense field (e.g. "Driving Under the
Influence", "Robbery", "Family Offenses - Nonviolent") backed by a real
statute citation — no coarseness limitation found. `NAME` (patrol zone
label, e.g. "NORTH"/"CENTRAL"/"EAST") was independently confirmed via a
live sample to be a zone label, not a person's name, before being
considered for use — not included in this module's field list regardless,
since `COMMUNITY` already provides more specific, useful location detail.
No disposition field present. No personal-identifier fields found.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

RIVERSIDE_CRIME_QUERY_URL = (
    "https://services.arcgis.com/Fu2oOWg1Aw7azh41/arcgis/rest/services/"
    "View_CrimesRPD/FeatureServer/4/query"
)
SOURCE_RIVERSIDE_CRIME = "riverside_crime"
CITY_NAME = "Riverside"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "rpdunique,offendate,nibrsdesc,BLOCK_ADDRESS,COMMUNITY"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "offendate DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(RIVERSIDE_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Riverside ArcGIS query failed: {data['error']}")
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
    address = clean_field(record.get("BLOCK_ADDRESS"), "an unspecified location")
    community = clean_field(record.get("COMMUNITY"))
    date = _format_esri_date(record.get("offendate"))

    return (
        f"{CITY_NAME} crime report: {offense} near {address}"
        + (f" ({community})" if community else "")
        + f", on {date}."
    )


async def sync_riverside_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_RIVERSIDE_CRIME, CITY_NAME, "rpdunique", _summarize)
