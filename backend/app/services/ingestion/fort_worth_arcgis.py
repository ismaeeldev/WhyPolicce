"""Fort Worth, TX Open Data (ArcGIS FeatureServer table view) ingestion —
plan.md Step 9 Phase 10.

Confirmed live via real server-side queries during this build: 1,458,325
total rows, max(Reported_Date) = 2026-09-06 (2 days before this build),
6,650 rows in the trailing 45-day window (genuinely active, not a stale
single straggler — the exact deeper check this project's Cincinnati
Phase 9 finding requires). Unique id `Case_No_Offense` confirmed 0% null.

Real field-type note: `Reported_Date` here is a plain string
("2026-09-06T13:12:00"), NOT an Esri epoch-millisecond date field like
most other ArcGIS sources this project has integrated — confirmed via a
direct field-schema check (`sqlType":"sqlTypeNVarchar"`), so this module
parses it as a string prefix, not `_format_esri_date`.

`Offense_Desc` includes the real penal-code citation plus a plain
description (e.g. "PC 30.04(d) Burglary of Vehicles") — a genuinely
specific offense field, no coarseness limitation found (unlike
Cincinnati's Part 1/2-only gap in Phase 9). No disposition field present.
No personal-identifier fields found in this schema.
"""

import logging

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

FORT_WORTH_CRIME_QUERY_URL = (
    "https://services5.arcgis.com/3ddLCBXe1bRt7mzj/arcgis/rest/services/"
    "CFW_Open_Data_Police_Crime_Data_Table_view/FeatureServer/0/query"
)
SOURCE_FORT_WORTH_CRIME = "fort_worth_crime"
CITY_NAME = "Fort Worth"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "Case_No_Offense,Reported_Date,Offense_Desc,BLOCK_ADDRESS"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "Reported_Date DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(FORT_WORTH_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Fort Worth ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("Offense_Desc"), "an incident")
    address = clean_field(record.get("BLOCK_ADDRESS"), "an unspecified location")
    date = clean_field(record.get("Reported_Date"))
    date = date[:10] if date else "an unknown date"

    return f"{CITY_NAME} crime report: {offense} near {address}, on {date}."


async def sync_fort_worth_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_FORT_WORTH_CRIME, CITY_NAME, "Case_No_Offense", _summarize)
