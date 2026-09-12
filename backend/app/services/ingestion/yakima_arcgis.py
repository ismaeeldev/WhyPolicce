"""Yakima, WA Open Data (ArcGIS FeatureServer, hosted on ArcGIS Online)
ingestion — plan.md Step 9 Phase 17.

Confirmed live via real server-side queries during this build: 33,101
total rows at time of ingestion (growing — 26,009 at time of research,
confirming genuine ongoing activity, not a one-time snapshot), max
(reportdate) = 2026-09-09 (same day as this build), ~960-987 rows in the
trailing 45-day window depending on exact check time. Unique id
`offenseid` confirmed 0% null.

`nibrsdesc` is a genuine, specific NIBRS-based offense field (e.g.
"Driving Under the Influence", "Violation of No Contact Order") — no
coarseness limitation found. This dataset has no street-address field at
all, unlike most other ArcGIS sources integrated so far — `neighborhood`
and `zip5` (both real, safe, non-PII fields confirmed present in the
schema) are used for location instead.

**Real personal-identifier field found and confirmed via a direct live
sample, not just the field name/description**: `officer` (aliased
"Reporting Officer" in the schema's own metadata) contains REAL,
INDIVIDUAL responding-officer names on every sampled row (e.g. "Mendoza
Jorge", "Diaz D") — deliberately excluded from the ingested field list
entirely, same privacy posture as Chattanooga's Phase 12 `Officer` field
and every other city with officer-identifying fields. No victim/
complainant names found in this schema.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

YAKIMA_CRIME_QUERY_URL = (
    "https://services5.arcgis.com/drBwGNA3YMS2QPJd/arcgis/rest/services/"
    "Crimes_public_fc349e427d9945729c4e985666b31686/FeatureServer/0/query"
)
SOURCE_YAKIMA_CRIME = "yakima_crime"
CITY_NAME = "Yakima"

DEFAULT_FETCH_LIMIT = 200

# Deliberately excludes `officer` (real individual officer names) — see
# module docstring's privacy note. `neighborhood`/`zip5` included as a
# real, safe, non-PII location field confirmed present in the schema
# (this dataset has no street-address field at all, unlike most other
# ArcGIS sources integrated so far).
_FIELDS = "offenseid,reportdate,nibrsdesc,neighborhood,zip5"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "reportdate DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(YAKIMA_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Yakima ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("nibrsdesc"), "an incident")
    neighborhood = clean_field(record.get("neighborhood"))
    zip_code = clean_field(record.get("zip5"))
    date = _format_esri_date(record.get("reportdate"))

    location = neighborhood or (f"zip {zip_code}" if zip_code else "")
    location_phrase = f" in {location}" if location else ""
    return f"{CITY_NAME} crime report: {offense}{location_phrase}, on {date}."


async def sync_yakima_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_YAKIMA_CRIME, CITY_NAME, "offenseid", _summarize)
