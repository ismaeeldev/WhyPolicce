"""Boise, ID Open Data (ArcGIS FeatureServer, hosted on ArcGIS Online)
ingestion — plan.md Step 9 Phase 12.

Confirmed live via real server-side queries during this build: 1,352,016
total rows (all agencies; filtered to Boise PD only via `Agency='BPD'`),
max(ResponseDateTimeUTC) = 2026-09-07 (2 days before this build), 20,194
BPD rows in the trailing 45-day window — genuinely active. Unique id
`CADIncidentNumber` confirmed 0% null.

Real, confirmed schema limitation, same class of gap as Cincinnati's
Phase 9 finding: this is calls-for-service (CAD/dispatch) data, and
`IncidentCategory` is only a coarse category (e.g. "Traffic", "Community
Assistance", "Mental Health") — there is no specific offense-description
field. Summarized honestly as a "police call" at that coarse category
level, same posture as New Orleans/Virginia Beach's CAD-level datasets in
earlier phases.

**Real decoy explicitly rejected during research and independently
confirmed**: a separate, plausible-looking "Police_Incidents" layer for
Boise turned out to be 100% mislabeled data from a DIFFERENT agency
(`agency="RPD"`, not BPD) with a 25.2%-blank unique-id field on top —
this module deliberately does NOT use that layer.

No personal-identifier fields found in this schema.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

BOISE_CALLS_QUERY_URL = (
    "https://services1.arcgis.com/WHM6qC35aMtyAAlN/arcgis/rest/services/"
    "BPD_CallsForService/FeatureServer/0/query"
)
SOURCE_BOISE_CALLS = "boise_calls"
CITY_NAME = "Boise"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "CADIncidentNumber,ResponseDateTimeUTC,CallType,IncidentCategory,NeighborhoodAssociation"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        # Restricted to Boise PD's own calls — this FeatureServer also
        # carries mutual-aid agencies (ACS/GPD/MPD/OP) under the same
        # layer, confirmed via research; only BPD's own data belongs
        # under the "Boise" city label.
        "where": "Agency='BPD'",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "ResponseDateTimeUTC DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(BOISE_CALLS_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Boise ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    category = clean_field(record.get("IncidentCategory"), "an incident")
    call_type = clean_field(record.get("CallType"))
    neighborhood = clean_field(record.get("NeighborhoodAssociation"), "an unspecified area")
    date = _format_esri_date(record.get("ResponseDateTimeUTC"))

    detail = f" ({call_type})" if call_type else ""
    return f"{CITY_NAME} police call: {category}{detail} in {neighborhood}, on {date}."


async def sync_boise_calls(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_BOISE_CALLS, CITY_NAME, "CADIncidentNumber", _summarize)
