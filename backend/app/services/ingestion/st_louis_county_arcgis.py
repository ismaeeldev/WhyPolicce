"""St. Louis County, MO Police (NIBRS) Open Data (ArcGIS FeatureServer)
ingestion — plan.md Step 9 Phase 10.

Confirmed live via real server-side queries during this build: 210,195
total rows, max(occurred) = 2026-08-31 (8 days before this build), 2,534
rows in the trailing 45-day window — genuinely active. Unique id
`Report_Number` confirmed 0% null.

**Important labeling correction, caught during research and preserved
here rather than silently glossed over**: this dataset is St. Louis
COUNTY Police data, covering the county and several contracted
municipalities within it (confirmed via real distinct `reportingJuris`
values seen directly: Lakeshire, Richmond Heights, Ferguson, Hazelwood,
Bridgeton, Maryland Heights, Brentwood, and others) — it is NOT the City
of St. Louis proper, and no live City-of-St.-Louis-specific feed was found
during research. `CITY_NAME` is deliberately set to "St. Louis County",
not "St. Louis", so this is never presented to a user as covering the
City of St. Louis itself.

`OffenseName` is the real offense-description field, confirmed only
0.0033% null (7/210,195). No disposition field present. No
personal-identifier fields found in this schema.
"""

import logging

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

ST_LOUIS_COUNTY_CRIME_QUERY_URL = (
    "https://services2.arcgis.com/w657bnjzrjguNyOy/arcgis/rest/services/"
    "crimedata2023_XYTableToPoint2/FeatureServer/0/query"
)
SOURCE_ST_LOUIS_COUNTY_CRIME = "st_louis_county_crime"
CITY_NAME = "St. Louis County"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "Report_Number,occurred,OffenseName,address,reportingJuris"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "occurred DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(ST_LOUIS_COUNTY_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"St. Louis County ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("OffenseName"), "an incident")
    address = clean_field(record.get("address"), "an unspecified location")
    jurisdiction = clean_field(record.get("reportingJuris"))
    date = clean_field(record.get("occurred"))
    date = date[:10] if date else "an unknown date"

    parts = [f"{CITY_NAME} crime report: {offense} near {address}"]
    if jurisdiction:
        parts.append(f"(reported by {jurisdiction.title()} PD)")
    return " ".join(parts) + f", on {date}."


async def sync_st_louis_county_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(
        session, records, SOURCE_ST_LOUIS_COUNTY_CRIME, CITY_NAME, "Report_Number", _summarize
    )
