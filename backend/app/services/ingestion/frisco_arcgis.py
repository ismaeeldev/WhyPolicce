"""Frisco, TX Open Data (self-hosted ArcGIS FeatureServer) ingestion —
plan.md Step 9 Phase 20.

Confirmed live via real server-side queries during this build: 5,848
total rows, max(DateTimeOccurred) = 2026-09-08 (same day as this build),
628 rows in the trailing 45-day window — genuinely active. Unique id
`Incident` confirmed 0% null.

Hosted on `maps.friscotexas.gov` — a SELF-HOSTED municipal domain, same
class of risk as Houston/San Diego/Charlotte/Wichita, which all turned
out to be unreachable from this environment. Directly tested and
confirmed reachable here (same exception already found for DC,
Indianapolis, and Rochester) — not rejected preemptively just for the
hosting pattern.

`OffenseGroup` is a genuine, specific offense field (e.g. "Theft", "Hit
and Run", "Harassment", "Assault") — no coarseness limitation found.
Address is already block-range level from the source itself (e.g.
"7001-7005 STONERIDGE DR"). No disposition field present (an `Arrest`
Yes/No flag exists but is not a full disposition). No personal-identifier
fields found in this schema — checked directly, no CCN/WARD/ANC/PSA/BID
fields (this project's recurring "mislabeled DC MPD data" pattern) and no
victim/officer names.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

FRISCO_CRIME_QUERY_URL = (
    "https://maps.friscotexas.gov/gis/rest/services/Public/"
    "Crime_Mapping_View__Dashboard/FeatureServer/1/query"
)
SOURCE_FRISCO_CRIME = "frisco_crime"
CITY_NAME = "Frisco"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "Incident,OffenseGroup,Location,DateTimeOccurred"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "DateTimeOccurred DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(FRISCO_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Frisco ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("OffenseGroup"), "an incident")
    address = clean_field(record.get("Location"), "an unspecified location")
    date = _format_esri_date(record.get("DateTimeOccurred"))

    return f"{CITY_NAME} crime report: {offense} near {address}, on {date}."


async def sync_frisco_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_FRISCO_CRIME, CITY_NAME, "Incident", _summarize)
