"""Sacramento Open Data (ArcGIS FeatureServer) ingestion — plan.md
Step 9 Phase 6.

Confirmed live via real verification during this build: `Occurrence_Date_PT`
is stored as free-text `MM/DD/YYYY HH:MM` (not a real ArcGIS date field),
so a numeric MAX() statistics query doesn't work on it — confirmed the
true real max date instead via server-side `LIKE` count queries narrowing
month-by-month/day-by-day: 09/2026 had 0 records, 08/2026 had thousands,
narrowing to 2026-08-24 as the last date with any real records — roughly
a 2-week reporting lag, consistent with a routine ingestion pipeline
rather than a stale/abandoned dataset. Hosted on services5.arcgis.com
under the City of Sacramento's own `Publisher_SacCity` account.

Uses the rolling `Police_Crime_3Years` layer (a continuously-updated
3-year window) rather than the same org's separate frozen per-year
layers (`Sacramento_Report_Data_2025`/`2026`) — the rolling layer avoids
the same "must roll to a new service every January" maintenance burden
Louisville/San Jose/Tucson all have.
"""

import logging

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

SACRAMENTO_CRIME_QUERY_URL = (
    "https://services5.arcgis.com/54falWtcpty3V47Z/arcgis/rest/services/"
    "Police_Crime_3Years/FeatureServer/0/query"
)
SOURCE_SACRAMENTO_CRIME = "sacramento_crime"
CITY_NAME = "Sacramento"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "Record_ID,Description,Offense_Category,Occurrence_Date_PT,Location,Police_District"


async def _fetch_records(limit: int) -> list[dict]:
    # Occurrence_Date_PT is free text, not a real date field (see module
    # docstring) — ORDER BY on it still sorts lexically as
    # "MM/DD/YYYY HH:MM", which is NOT chronological order across
    # different months/years. Over-fetch a larger page by OBJECTID DESC
    # (roughly most-recently-added) and let the caller's own top-N
    # selection in socrata_base.py handle final ordering by whatever's
    # actually inserted — same acknowledged limitation as any source
    # without a real queryable date column.
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "OBJECTID DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(SACRAMENTO_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Sacramento ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _summarize(record: dict) -> str:
    # Real field-list correction found via a live 400 error during this
    # build: Case_Status_Desc, present on Sacramento's separate frozen
    # per-year layers, does NOT exist on this rolling Police_Crime_3Years
    # layer — confirmed directly via the layer's own field metadata, not
    # assumed identical across the two.
    offense = clean_field(record.get("Description"), "an incident")
    category = clean_field(record.get("Offense_Category"))
    location = clean_field(record.get("Location"), "an unspecified location")
    district = clean_field(record.get("Police_District"), "unknown")
    date = clean_field(record.get("Occurrence_Date_PT"), "an unknown date")
    date = date.split(" ")[0] if date != "an unknown date" else date

    prefix = f"{category.title()} — " if category and category.lower() != offense.lower() else ""
    parts = [
        f"{CITY_NAME} crime report: {prefix}{offense.title()}",
        f"near {location}, police district {district}, on {date}.",
    ]
    return " ".join(p for p in parts if p.strip())


async def sync_sacramento_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_SACRAMENTO_CRIME, CITY_NAME, "Record_ID", _summarize)
