"""Detroit Open Data (ArcGIS FeatureServer) ingestion — plan.md Step 9
Phase 3, substituted for Houston.

**Why Detroit, not Houston:** Houston's real, live crime source
(mycity2.houstontx.gov, confirmed via research to be the actual backend
of the city's own public "Recent Crime Finder" experience app) genuinely
refuses every connection from this environment — HTTPS, HTTP, both
standard ports, and the entire houstontx.gov domain (not just that one
subdomain) all timed out, while services.arcgis.com and every other
city's government infrastructure connects fine. This is a real,
confirmed network-level block on this specific environment, not a data
availability problem — the Houston app itself works in a real browser.
Per explicit product decision, substituted with a different, equally-real
major city rather than force a connection that provably can't succeed.

Confirmed live via a real server-side MAX() query during this build:
most recent incident_occurred_at is 2026-09-07, one day before this
build — genuinely current (city's own description states "updated
daily").
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

DETROIT_CRIME_QUERY_URL = (
    "https://services2.arcgis.com/qvkbeam7Wirps6zC/arcgis/rest/services/"
    "RMS_Crime_Incidents/FeatureServer/0/query"
)
SOURCE_DETROIT_CRIME = "detroit_crime"
CITY_NAME = "Detroit"

DEFAULT_FETCH_LIMIT = 200

# Real fields confirmed via a live sample during this build — this
# dataset is genuinely clean of personal identifiers already (no victim
# demographics, no officer names), unlike Dallas/LA/Nashville's raw data.
_FIELDS = (
    "incident_entry_id,offense_category,offense_description,"
    "incident_occurred_at,nearest_intersection,neighborhood,police_precinct,case_status"
)


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "incident_occurred_at DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(DETROIT_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Detroit ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("offense_description"), "an incident")
    category = clean_field(record.get("offense_category"))
    intersection = clean_field(record.get("nearest_intersection"), "an unspecified location")
    neighborhood = clean_field(record.get("neighborhood"))
    precinct = clean_field(record.get("police_precinct"), "unknown")
    date = _format_esri_date(record.get("incident_occurred_at"))
    status = clean_field(record.get("case_status"))

    prefix = f"{category.title()} — " if category and category.lower() != offense.lower() else ""
    parts = [
        f"{CITY_NAME} crime report: {prefix}{offense.title()}",
        f"near {intersection}"
        + (f" ({neighborhood} neighborhood)" if neighborhood else "")
        + f", precinct {precinct}, on {date}.",
    ]
    if status:
        parts.append(f"Case status: {status.title()}.")
    return " ".join(p for p in parts if p.strip())


async def sync_detroit_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_DETROIT_CRIME, CITY_NAME, "incident_entry_id", _summarize)
