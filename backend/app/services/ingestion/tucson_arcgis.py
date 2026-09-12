"""Tucson Open Data (ArcGIS FeatureServer) ingestion — plan.md Step 9
Phase 6.

Confirmed live via a real server-side MAX() query during this build:
most recent OccurredDate is 2026-09-05, three days before this build —
genuinely current. Hosted on services3.arcgis.com under the City of
Tucson's own GIS org account (`tucsondata_cotgis`).

Real, non-obvious finding: this dataset publishes one FeatureServer PER
YEAR (`TPDOpenData_ReportedCrimes_2026`) — same "needs a yearly rollover"
pattern as Louisville and San Jose. Must be updated to the new year's
service after 2026-12-31.

Real fields include EXTENSIVE personal identifiers not seen in this
depth on any other city so far: age group, race, ethnicity, sex, and a
pseudonymized per-person hash (`PersonID`) tied to each individual's role
(victim/arrestee/etc.) in the incident. ALL deliberately excluded from
the summary text — this dataset needed the strictest privacy filtering
of any city integrated so far, describing only the incident itself.
"""

import logging

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

# See module docstring — must be updated to the new year's service after
# 2026-12-31.
TUCSON_CRIME_QUERY_URL = (
    "https://services3.arcgis.com/9coHY2fvuFjG9HQX/arcgis/rest/services/"
    "TPDOpenData_ReportedCrimes_2026/FeatureServer/0/query"
)
SOURCE_TUCSON_CRIME = "tucson_crime"
CITY_NAME = "Tucson"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "IncidentNumber,UCRSummaryDescription,StatuteDescription,OccurredDate,Address100Block,NeighborhoodAssociation"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "OccurredDate DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(TUCSON_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Tucson ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _summarize(record: dict) -> str:
    # OccurredDate on this layer is esriFieldTypeDateOnly, returned as a
    # plain "YYYY-MM-DD" string directly — confirmed live, same pattern
    # as San Francisco's Incident_Date, not the epoch-ms pattern most
    # other ArcGIS cities here use.
    summary_desc = clean_field(record.get("UCRSummaryDescription"), "an incident")
    statute = clean_field(record.get("StatuteDescription"))
    address = clean_field(record.get("Address100Block"), "an unspecified location")
    neighborhood = clean_field(record.get("NeighborhoodAssociation"))
    date = clean_field(record.get("OccurredDate"), "an unknown date")

    detail = f" ({statute})" if statute and statute.lower() != summary_desc.lower() else ""
    parts = [
        f"{CITY_NAME} crime report: {summary_desc.title()}{detail}",
        f"near {address}"
        + (f" ({neighborhood} neighborhood association)" if neighborhood else "")
        + f", on {date}.",
    ]
    return " ".join(p for p in parts if p.strip())


async def sync_tucson_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_TUCSON_CRIME, CITY_NAME, "IncidentNumber", _summarize)
