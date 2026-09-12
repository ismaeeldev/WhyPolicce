"""Charleston, SC Open Data (ArcGIS FeatureServer, hosted on ArcGIS
Online) ingestion — plan.md Step 9 Phase 27.

Discovered via `OpenPoliceData`'s source table, then independently
re-verified via direct HTTP queries before any code was written.

Confirmed live via real server-side queries during this build: 24,507
total rows, max(DateOccurred) = 2026-08-26 (13 days before this build),
361 rows in the trailing 45-day window — genuinely active. Unique id
`OCA` confirmed 0% null.

`ChargeDescription` is a genuine, specific offense field (e.g. "DRUG /
NARCOTICS VIOLATION") — confirmed via direct sampling. Address is
already street/intersection-level from the source itself. No
disposition field ingested (a `CaseStatus` field exists in the full
schema but was not included in this module — not reviewed for privacy
implications, a future revisit could add it if confirmed safe). No
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

CHARLESTON_SC_CRIME_QUERY_URL = (
    "https://services2.arcgis.com/tQaXW7Zb1Vphzvgd/arcgis/rest/services/"
    "PDI_Reported_Incidents/FeatureServer/0/query"
)
SOURCE_CHARLESTON_SC_CRIME = "charleston_sc_crime"
CITY_NAME = "Charleston, SC"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "OCA,DateOccurred,ChargeDescription,StreetAddress"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "DateOccurred DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(CHARLESTON_SC_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Charleston SC ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("ChargeDescription"), "an incident")
    address = clean_field(record.get("StreetAddress"), "an unspecified location")
    date = _format_esri_date(record.get("DateOccurred"))

    return f"{CITY_NAME} crime report: {offense.title()} near {address}, on {date}."


async def sync_charleston_sc_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_CHARLESTON_SC_CRIME, CITY_NAME, "OCA", _summarize)
