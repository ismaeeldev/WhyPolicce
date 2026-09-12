"""Virginia Beach Open Data (ArcGIS FeatureServer) ingestion — plan.md
Step 9 Phase 8.

Confirmed live via a real server-side MAX() query during this build:
most recent Call_Date_Time is 2026-09-08, the same day as this build —
genuinely current, 1,840,942 total rows confirmed (the largest single
dataset integrated so far).

**Real, significant bug caught BEFORE it ever reached ingestion code**,
via the same discipline Raleigh's Phase 7 bug taught this project to
apply proactively rather than reactively: this dataset has an obvious-
looking `ReportNumber` field that turns out to be 82% NULL (1,507,798 of
1,840,942 records) — confirmed directly via a live count query. Using it
as the unique id_field would have discarded the vast majority of real
data, an even worse version of Raleigh's ~25% loss. The real,
consistently-populated unique key is `IncidentNumber` (confirmed 0% null)
— used here from the start instead.

This is "Calls for Service" (CAD/dispatch data), same caveat as New
Orleans — genuinely live and current, but a different granularity than a
pure crime-classification dataset. Real fields include `Officer_Id` —
excluded from the summary, same privacy posture as every other city with
officer-identifying fields.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

VIRGINIA_BEACH_CALLS_QUERY_URL = (
    "https://services2.arcgis.com/CyVvlIiUfRBmMQuu/arcgis/rest/services/"
    "Police_Calls_for_Service_/FeatureServer/0/query"
)
SOURCE_VIRGINIA_BEACH_CALLS = "virginia_beach_calls"
CITY_NAME = "Virginia Beach"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "IncidentNumber,Call_Type,Block_Address,Zone,Case_Disposition,Call_Date_Time,Subdivision"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "Call_Date_Time DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(VIRGINIA_BEACH_CALLS_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Virginia Beach ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    call_type = clean_field(record.get("Call_Type"), "an incident")
    address = clean_field(record.get("Block_Address"), "an unspecified location")
    subdivision = clean_field(record.get("Subdivision"))
    zone = clean_field(record.get("Zone"), "unknown")
    date = _format_esri_date(record.get("Call_Date_Time"))
    disposition = clean_field(record.get("Case_Disposition"))

    parts = [
        f"{CITY_NAME} police call: {call_type.title()}",
        f"near {address}"
        + (f" ({subdivision})" if subdivision else "")
        + f", zone {zone}, on {date}.",
    ]
    if disposition:
        parts.append(f"Disposition: {disposition.title()}.")
    return " ".join(p for p in parts if p.strip())


async def sync_virginia_beach_calls(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_VIRGINIA_BEACH_CALLS, CITY_NAME, "IncidentNumber", _summarize)
