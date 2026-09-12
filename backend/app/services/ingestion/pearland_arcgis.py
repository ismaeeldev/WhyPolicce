"""Pearland, TX Open Data (self-hosted ArcGIS FeatureServer) ingestion —
plan.md Step 9 Phase 20.

Confirmed live via real server-side queries during this build: 3,985
total rows (a rolling ~365-day window by the portal's own dashboard
description — a moderate total is expected/correct for this window size,
same reasoning as Tampa/Riverside's rolling-window layers in earlier
phases), max(date_occu) = 2026-09-08 (same day as this build), 454 rows
in the trailing 45-day window. Unique id `inci_id` confirmed 0% null.

Hosted on `gis.pearlandtx.gov` — a self-hosted municipal domain, directly
tested and confirmed reachable (same exception already found for DC,
Indianapolis, Rochester, and Frisco).

Both `offense` (free-text, specific, e.g. "THEFT BY FRAUD OR DECEPTION",
"POSSESSION OF MARIJUANA") and `CRIMENAME` (a real NIBRS-style category,
e.g. "Drugs", "Assault", "Trespassing") are genuine, distinct, non-
reversed fields — confirmed via direct sampling, no field-naming trap
found this time (unlike Grand Rapids's Phase 13 and Prince George's
County's Phase 14 reversed-field findings). `ucr_code` provides a real
UCR/NIBRS code as a third data point. Address is street-level (no unit/
apartment numbers). No disposition field present. No personal-identifier
fields found — checked directly, no CCN/WARD/ANC/PSA/BID fields (this
project's recurring "mislabeled DC MPD data" pattern) and no victim/
officer names.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

PEARLAND_CRIME_QUERY_URL = (
    "https://gis.pearlandtx.gov/hosting/rest/services/EmergencyServices/"
    "CrimesPublic/FeatureServer/0/query"
)
SOURCE_PEARLAND_CRIME = "pearland_crime"
CITY_NAME = "Pearland"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "inci_id,offense,CRIMENAME,Address,date_occu"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "date_occu DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(PEARLAND_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Pearland ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("offense"), "an incident")
    category = clean_field(record.get("CRIMENAME"))
    address = clean_field(record.get("Address"), "an unspecified location")
    date = _format_esri_date(record.get("date_occu"))

    detail = f" ({category})" if category and category.lower() != offense.lower() else ""
    return f"{CITY_NAME} crime report: {offense.title()}{detail} near {address}, on {date}."


async def sync_pearland_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_PEARLAND_CRIME, CITY_NAME, "inci_id", _summarize)
