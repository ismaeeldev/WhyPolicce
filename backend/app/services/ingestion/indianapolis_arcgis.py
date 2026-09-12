"""Indianapolis Open Data (self-hosted ArcGIS MapServer) ingestion —
plan.md Step 9 Phase 8.

Confirmed live via a real server-side count query during this build:
714,705 total rows, and `sOccDate LIKE '2026%'` returned 62,743 rows,
confirming genuinely active 2026 data (not stale). Hosted on
gis.indy.gov — a SELF-HOSTED municipal domain, same class of risk as
Houston/San Diego/Charlotte, which all turned out to be unreachable from
this environment. Directly tested and confirmed reachable here (same
exception already found for Washington DC's self-hosted domain) — not
rejected preemptively just for the hosting pattern, since the actual
connection works reliably.

Real fields confirmed clean of personal identifiers — no victim/officer
names, no demographic fields on this layer.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

INDIANAPOLIS_CRIME_QUERY_URL = "https://gis.indy.gov/server/rest/services/IMPD/IMPD_Public_Data/MapServer/1/query"
SOURCE_INDIANAPOLIS_CRIME = "indianapolis_crime"
CITY_NAME = "Indianapolis"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "CaseNum,CR_Desc,NIBRSClassDesc,OccurredFrom,sAddress,Geo_Districts,PremiseType,Disposition"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "OccurredFrom DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(INDIANAPOLIS_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Indianapolis ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("CR_Desc"), "an incident")
    nibrs_desc = clean_field(record.get("NIBRSClassDesc"))
    address = clean_field(record.get("sAddress"), "an unspecified location")
    district = clean_field(record.get("Geo_Districts"), "unknown")
    date = _format_esri_date(record.get("OccurredFrom"))
    premise = clean_field(record.get("PremiseType"))

    detail = f" ({nibrs_desc})" if nibrs_desc and nibrs_desc.lower() != offense.lower() else ""
    parts = [
        f"{CITY_NAME} crime report: {offense}{detail}",
        f"near {address}, {district} district, on {date}.",
    ]
    if premise:
        parts.append(f"Premise type: {premise}.")
    return " ".join(p for p in parts if p.strip())


async def sync_indianapolis_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_INDIANAPOLIS_CRIME, CITY_NAME, "CaseNum", _summarize)
