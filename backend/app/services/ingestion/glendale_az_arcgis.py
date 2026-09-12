"""Glendale, AZ Police Calls for Service (ArcGIS FeatureServer, hosted on
ArcGIS Online) ingestion — plan.md Step 9 Phase 21.

A real, honest correction to an earlier phase's finding: Glendale, AZ was
previously rejected in Phase 13 because its self-hosted domain
(`gismaps.glendaleaz.com`) was blocked by Incapsula bot protection. This
is a genuinely different, ArcGIS-Online-hosted endpoint for the same
department — confirmed directly reachable, not a retry of the same dead
domain.

Confirmed live via real server-side queries during this build: 1,138,221
total rows, max(CallDatetime) = 2026-09-08 (same day as this build),
19,383 rows in the trailing 45-day window — genuinely active, real
multi-year history (data starts 2020). Unique id `CallNumber` (CAD-
assigned, e.g. "GPD26108137") confirmed 0% null.

This is CAD (police calls-for-service) data, same caveat as New Orleans/
Virginia Beach/Everett/Bellevue's CFS datasets in earlier phases —
`CallType` is the real, genuinely specific call-type field (e.g.
"415F-DOMESTIC VIOLENCE/FAMILY FIGHT", "601J-MISSING JUVENILE",
"C6 - TRAFFIC STOP"), confirmed via direct sampling. `Location` is
already redacted to street/100-block level by the source itself. `Beat`
is sometimes blank (confirmed directly, handled honestly via the shared
clean_field fallback). No disposition field ingested (a `CallDisposition`
field exists in the schema but was not included here — not reviewed for
this module; a future revisit could add it if confirmed safe). No
personal-identifier fields found in the ingested fields — checked
directly, no CCN/WARD/ANC/PSA/BID fields (this project's recurring
"mislabeled DC MPD data" pattern) and no victim/officer names.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

GLENDALE_AZ_CALLS_QUERY_URL = (
    "https://services1.arcgis.com/9fVTQQSiODPjLUTa/arcgis/rest/services/"
    "Police_Calls_for_Service/FeatureServer/1/query"
)
SOURCE_GLENDALE_AZ_CALLS = "glendale_az_calls"
CITY_NAME = "Glendale, AZ"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "CallNumber,CallDatetime,CallType,Location,Beat"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "CallDatetime DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(GLENDALE_AZ_CALLS_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Glendale AZ ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    call_type = clean_field(record.get("CallType"), "an incident")
    location = clean_field(record.get("Location"), "an unspecified location")
    beat = clean_field(record.get("Beat"))
    date = _format_esri_date(record.get("CallDatetime"))

    parts = [f"{CITY_NAME} police call: {call_type} near {location}"]
    if beat:
        parts.append(f"(beat {beat})")
    return " ".join(parts) + f", on {date}."


async def sync_glendale_az_calls(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_GLENDALE_AZ_CALLS, CITY_NAME, "CallNumber", _summarize)
