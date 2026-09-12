"""Hartford, CT Open Data (ArcGIS FeatureServer) ingestion — plan.md
Step 9 Phase 11.

Confirmed live via real server-side queries during this build: 54,520
total rows, max(Date) = 2026-08-27 (consistent with the dataset's own
stated ~10-day reporting lag from 2026-09-08), 3,236 rows in the trailing
45-day window — genuinely active. Unique id `CaseNum` confirmed ~0.01%
null (8/54,520) — negligible, same falsy-id-skip handling as every other
city covers this.

Real, confirmed multi-offense-per-case pattern, same as Seattle/Baltimore/
Dallas/Tucson/Louisville in earlier phases: `CaseNum` is NOT unique per
row — a single case (e.g. "26-020032") can have multiple offense-line
rows sharing it (confirmed directly: one sampled case had both "ILL OPN MV
UNDER INFL ALC/DRUG" and "FLR TO DRIVE IN PROPER LANE" as separate rows).
`sync_dataset()`'s existing within-batch dedup (keep last-seen per id)
already handles this the same way it has for every prior such city.

`OffenseDesc` is a genuine statute-cite-level description (e.g.
"14-227A ILL OPN MV UNDER INFL ALC/DRUG") — no coarseness limitation
found. No disposition field present. No personal-identifier fields found
in this schema.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

HARTFORD_CRIME_QUERY_URL = (
    "https://utility.arcgis.com/usrsvcs/servers/4bc28c820ebd45df8a62feae6dc8822d/"
    "rest/services/OpenData_PublicSafety/FeatureServer/21/query"
)
SOURCE_HARTFORD_CRIME = "hartford_crime"
CITY_NAME = "Hartford"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "CaseNum,Date,OffenseDesc,Address"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "Date DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(HARTFORD_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Hartford ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("OffenseDesc"), "an incident")
    address = clean_field(record.get("Address"), "an unspecified location")
    date = _format_esri_date(record.get("Date"))

    return f"{CITY_NAME} crime report: {offense} near {address}, on {date}."


async def sync_hartford_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_HARTFORD_CRIME, CITY_NAME, "CaseNum", _summarize)
