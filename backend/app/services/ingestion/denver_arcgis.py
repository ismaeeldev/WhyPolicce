"""Denver Open Data (ArcGIS FeatureServer) ingestion — plan.md Step 9
Phase 2.

Confirmed live via a real request during this build:
https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/
ODC_CRIME_OFFENSES_P/FeatureServer/324 — a server-side MAX() statistics
query confirmed the true most-recent record is from 2026-09-04, genuinely
current (verified independently, not just trusted from research).

Real, non-obvious finding from this build: Denver's OLD open-data domain,
`data.denvergov.org` (Socrata-based, referenced in Phase 2's original
research), is completely unreachable — confirmed via a real TCP connection
timeout, not a DNS failure (DNS resolved to a real IP; the connection
itself timed out). Denver has migrated its open-data hosting to ArcGIS
Hub/FeatureServer entirely. A separate, DIFFERENT ArcGIS org
(`services1.arcgis.com/YvJkKP3I2NydFmVT/.../CRIME_OFFENSES_P`) — same
layer name, easy to confuse with the real one — was found first and ruled
out via the same MAX() query technique: that one's true latest record is
from 2021-12-27, a stale/abandoned duplicate. Always verify a data
source's actual max date via a server-side aggregate query before trusting
it, not just a spot-check of a few rows sorted client-side (see
vector_search_service.py's HNSW finding for why "looks recent" from a
small sample isn't proof).
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

DENVER_CRIME_QUERY_URL = (
    "https://services1.arcgis.com/zdB7qR0BtYrg0Xpl/arcgis/rest/services/"
    "ODC_CRIME_OFFENSES_P/FeatureServer/324/query"
)
SOURCE_DENVER_CRIME = "denver_crime"
CITY_NAME = "Denver"

DEFAULT_FETCH_LIMIT = 200

# ArcGIS's classic 10-character field-name truncation (see Denver's OTHER,
# stale service for the extreme version of this) does NOT apply to this
# specific service — its fields are already the full, real names
# (FIRST_OCCURRENCE_DATE, not FIRST_OCCU) — confirmed directly rather than
# assumed from the other service's schema.
_FIELDS = "OFFENSE_TYPE_ID,OFFENSE_CATEGORY_ID,FIRST_OCCURRENCE_DATE,INCIDENT_ADDRESS,NEIGHBORHOOD_ID,DISTRICT_ID,OFFENSE_ID"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "FIRST_OCCURRENCE_DATE DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(DENVER_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Denver ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    """ArcGIS returns dates as epoch milliseconds, not ISO strings —
    confirmed live (FIRST_OCCURRENCE_DATE: 1788478020000). Converted here
    so the summary reads as a real date, not a raw millisecond integer the
    LLM would have no reason to interpret correctly."""
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("OFFENSE_TYPE_ID"), "an incident").replace("-", " ")
    category = clean_field(record.get("OFFENSE_CATEGORY_ID")).replace("-", " ")
    address = clean_field(record.get("INCIDENT_ADDRESS"), "an unspecified location")
    neighborhood = clean_field(record.get("NEIGHBORHOOD_ID")).replace("-", " ")
    district = clean_field(record.get("DISTRICT_ID"), "unknown")
    date = _format_esri_date(record.get("FIRST_OCCURRENCE_DATE"))

    prefix = f"{category.title()} — " if category and category != offense else ""
    parts = [
        f"{CITY_NAME} crime report: {prefix}{offense.title()}",
        f"near {address}"
        + (f" ({neighborhood} neighborhood)" if neighborhood else "")
        + f", district {district}, on {date}.",
    ]
    return " ".join(p for p in parts if p.strip())


async def sync_denver_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_DENVER_CRIME, CITY_NAME, "OFFENSE_ID", _summarize)
