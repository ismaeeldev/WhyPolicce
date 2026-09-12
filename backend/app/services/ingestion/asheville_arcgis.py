"""Asheville, NC Open Data (self-hosted ArcGIS MapServer) ingestion —
plan.md Step 9 Phase 22.

Confirmed live via real server-side queries during this build: 106,332
total rows, max(date_occurred) = 2026-09-02 (via lexicographic ordering
on a fixed-width "YYYYMMDD" string field, confirmed valid for this exact
format — same real field-type quirk as Chattanooga's Phase 12
`Date_Logged`), 988 rows in the trailing 45-day window, plus 6,745 rows
tagged `year_occurred='2026'` confirming genuinely active, ongoing
updates. Unique id `case_number` confirmed 0% null.

Hosted on `gis.ashevillenc.gov` — a self-hosted municipal domain,
directly tested and confirmed reachable (same exception already found
for DC, Indianapolis, Rochester, Frisco, Pearland, and Fayetteville NC).

`offense_long_description` is a genuine, specific offense field (e.g.
"LARCENY ALL OTHER", "ASSAULT W/DEADLY WEAPON", "MISSING PERSON REPORT")
— confirmed via direct sampling. `ucr_crime_type`/`ucr_code` were
confirmed to be frequently blank on individual rows (a real, minor gap,
similar in nature to Auburn WA's ~2% blank offense field in Phase 19) —
not ingested here since `offense_long_description` is the reliably
populated field. Address is already street-block level from the source
itself (e.g. "100-BLK BATTERY PARK AVE"). No disposition field present.
No personal-identifier fields found in this schema — checked directly,
no name/DOB/race/sex/officer fields exist.
"""

import logging

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

ASHEVILLE_CRIME_QUERY_URL = (
    "https://gis.ashevillenc.gov/server/rest/services/PublicSafety/"
    "APDIncidents/MapServer/3/query"
)
SOURCE_ASHEVILLE_CRIME = "asheville_crime"
CITY_NAME = "Asheville"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "case_number,date_occurred,offense_long_description,address,beat"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "date_occurred DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(ASHEVILLE_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Asheville ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_yyyymmdd(raw: str) -> str:
    cleaned = clean_field(raw)
    if len(cleaned) != 8 or not cleaned.isdigit():
        return "an unknown date"
    return f"{cleaned[:4]}-{cleaned[4:6]}-{cleaned[6:8]}"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("offense_long_description"), "an incident")
    address = clean_field(record.get("address"), "an unspecified location")
    date = _format_yyyymmdd(record.get("date_occurred"))

    return f"{CITY_NAME} crime report: {offense.title()} near {address}, on {date}."


async def sync_asheville_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_ASHEVILLE_CRIME, CITY_NAME, "case_number", _summarize)
