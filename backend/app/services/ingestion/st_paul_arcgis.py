"""St. Paul, MN Open Data (ArcGIS FeatureServer, hosted on ArcGIS Online)
ingestion — plan.md Step 9 Phase 23.

Confirmed live via real server-side queries during this build: 579,516
total rows, max(DATE) = 2026-09-09 (1 day before this build), 4,465 rows
in the trailing 45-day window — genuinely active, real 12+ years of
history (min date 2014-08-14). Unique id `CASE_NUMBER` confirmed 0%
null.

`INCIDENT_TYPE` is a genuine, specific, detailed offense field (e.g.
"BURGLARY, FORCED ENTRY, DAY, RESIDENCE", "NARCOTICS, POSSESSION OF
COCAINE", "WEAPONS, DISCHARGING A FIREARM IN THE CITY LIMITS") —
confirmed via direct sampling, notably more detailed than several other
cities' offense fields. Some entries are honestly proactive/non-crime
police contacts (e.g. "POLICE VISIT-PROACTIVE POLICE VISIT"), same
honest pattern as Hartford/Bend/Asheville's non-offense rows in earlier
phases, not a data-quality problem. `CALL_DISPOSITION` provides a real
disposition field (e.g. "Report Written", "Advised"). `BLOCK` is already
block-level from the source itself. No personal-identifier fields found
in this schema — checked directly, no CCN/WARD/ANC/PSA/BID fields (this
project's recurring "mislabeled DC MPD data" pattern) and no victim/
officer names.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

ST_PAUL_CRIME_QUERY_URL = (
    "https://services1.arcgis.com/9meaaHE3uiba0zr8/arcgis/rest/services/"
    "Crime_Incident_Report_-_Dataset/FeatureServer/0/query"
)
SOURCE_ST_PAUL_CRIME = "st_paul_crime"
CITY_NAME = "St. Paul"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "CASE_NUMBER,DATE,INCIDENT_TYPE,BLOCK,NEIGHBORHOOD_NAME,CALL_DISPOSITION"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "DATE DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(ST_PAUL_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"St. Paul ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    incident_type = clean_field(record.get("INCIDENT_TYPE"), "an incident")
    block = clean_field(record.get("BLOCK"), "an unspecified location")
    neighborhood = clean_field(record.get("NEIGHBORHOOD_NAME"))
    disposition = clean_field(record.get("CALL_DISPOSITION"))
    date = _format_esri_date(record.get("DATE"))

    parts = [
        f"{CITY_NAME} crime report: {incident_type.title()} near {block}"
        + (f" ({neighborhood})" if neighborhood else "")
        + f", on {date}."
    ]
    if disposition:
        parts.append(f"Disposition: {disposition}.")
    return " ".join(p for p in parts if p.strip())


async def sync_st_paul_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_ST_PAUL_CRIME, CITY_NAME, "CASE_NUMBER", _summarize)
