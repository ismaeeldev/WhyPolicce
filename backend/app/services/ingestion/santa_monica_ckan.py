"""Santa Monica, CA Open Data (CKAN datastore API — a genuinely new
platform type for this project, distinct from Socrata/ArcGIS/
Opendatasoft) ingestion — plan.md Step 9 Phase 29.

Discovered via `OpenPoliceData`'s source table, then independently
re-verified via direct HTTP queries before any code was written — this
project's `datastore_search_sql` CKAN pattern (already used for
Milwaukee) applies here too, distinct from a plain ArcGIS/Socrata REST
call.

Confirmed live via real server-side SQL queries during this build:
396,817 total rows, max(incident_date) = 2026-09-09 (same day as this
build), real multi-year history (min date 2022-01-01). Unique id
`incident_number` confirmed 0% null.

`call_type` is a genuine, specific call-type field (e.g. "Hit and Run
Felony Investigation") — confirmed via direct sampling. `disposition`
provides a real disposition field (e.g. "TC REPORT"). Address is already
block-level from the source itself (e.g. "1300BLK 15TH ST"). A separate
"INCIDENTS" resource also exists on this same CKAN instance but was
confirmed stale (max date 2024-05-13) and is deliberately NOT used here
— only the live Calls for Service resource. No personal-identifier
fields found in this schema — checked directly, no CCN/WARD/ANC/PSA/BID
fields (this project's recurring "mislabeled DC MPD data" pattern) and
no victim/officer names.
"""

import logging

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

_DATASTORE_SEARCH_URL = "https://data.santamonica.gov/api/3/action/datastore_search"
_RESOURCE_ID = "f3a4e0d3-1cbb-4f97-9e52-fa178a133ebe"

SOURCE_SANTA_MONICA_CALLS = "santa_monica_calls"
CITY_NAME = "Santa Monica"

DEFAULT_FETCH_LIMIT = 200


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "resource_id": _RESOURCE_ID,
        "limit": limit,
        "sort": "incident_date desc",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(_DATASTORE_SEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if not data.get("success"):
        raise RuntimeError(f"Santa Monica CKAN query failed: {data}")
    return data.get("result", {}).get("records", [])


def _summarize(record: dict) -> str:
    call_type = clean_field(record.get("call_type"), "an incident")
    location = clean_field(record.get("location"), "an unspecified location")
    disposition = clean_field(record.get("disposition"))
    date = clean_field(record.get("incident_date"))
    date = date[:10] if date else "an unknown date"

    parts = [f"{CITY_NAME} police call: {call_type} near {location}, on {date}."]
    if disposition:
        parts.append(f"Disposition: {disposition.title()}.")
    return " ".join(p for p in parts if p.strip())


async def sync_santa_monica_calls(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_SANTA_MONICA_CALLS, CITY_NAME, "incident_number", _summarize)
