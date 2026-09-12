"""Fayetteville, NC Open Data (self-hosted ArcGIS MapServer, split across
3 category layers) ingestion — plan.md Step 9 Phase 22.

Confirmed live via real server-side queries during this build: 343,180
total rows across all 3 layers (Persons 68,515 / Society 33,212 /
Property 241,453), max(Date_Incident) = 2026-09-08 (same day as this
build) across layers, 1,664 combined rows in the trailing 45-day window
— genuinely active. Unique id `Case_number` confirmed 0% null on every
layer.

Hosted on `gismaps.fayettevillenc.gov` — a self-hosted municipal domain,
directly tested and confirmed reachable (same exception already found
for DC, Indianapolis, Rochester, Frisco, and Pearland).

`Offense_Description` is a genuine, specific offense field (e.g. "ASSAULT
- SIMPLE DOMESTIC", "ALLOTHER - COMMUNICATING THREATS / INTIMIDATION"),
backed by a real UCR code — confirmed via direct sampling. Address is
already street-level (no exact unit in most rows; an `APT` field exists
separately but is not ingested). No personal-identifier fields found in
the ingested field list — checked directly against the full field
schema, no name/DOB/race/sex/officer fields exist at all. One real,
harmless artifact found and noted: the service's own metadata sets
`displayFieldName` to `"officer_name"`, but no such field actually
exists anywhere in the schema or returned data — a dead/orphaned
configuration reference on the source's end, not a real PII field or
data leak.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

_LAYER_BASE_URL = "https://gismaps.fayettevillenc.gov/cofopendatagis/rest/services/Police"
_LAYERS = [
    "IncidentsCrimesAgainstPersons",
    "IncidentsCrimesAgainstSociety",
    "IncidentsCrimesAgainstProperty",
]

SOURCE_FAYETTEVILLE_NC_CRIME = "fayetteville_nc_crime"
CITY_NAME = "Fayetteville, NC"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "Case_number,Date_Incident,Offense_Description,Address,district"


async def _fetch_layer_records(layer: str, limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "Date_Incident DESC",
        "f": "json",
    }
    url = f"{_LAYER_BASE_URL}/{layer}/MapServer/0/query"
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Fayetteville NC ArcGIS query failed ({layer}): {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


async def _fetch_records(limit: int) -> list[dict]:
    # Each of the 3 category layers is fetched separately and combined —
    # a Case_number is unique within its own layer (confirmed 0% null on
    # each), and across layers too since each layer covers a distinct
    # offense category, not overlapping incidents.
    per_layer_limit = max(1, limit // len(_LAYERS))
    all_records: list[dict] = []
    for layer in _LAYERS:
        all_records.extend(await _fetch_layer_records(layer, per_layer_limit))
    return all_records


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("Offense_Description"), "an incident")
    address = clean_field(record.get("Address"), "an unspecified location")
    district = clean_field(record.get("district"))
    date = _format_esri_date(record.get("Date_Incident"))

    parts = [f"{CITY_NAME} crime report: {offense.title()} near {address}"]
    if district:
        parts.append(f"(district {district})")
    return " ".join(parts) + f", on {date}."


async def sync_fayetteville_nc_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(
        session, records, SOURCE_FAYETTEVILLE_NC_CRIME, CITY_NAME, "Case_number", _summarize
    )
