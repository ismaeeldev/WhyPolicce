"""Bend, OR Open Data (ArcGIS FeatureServer, hosted on ArcGIS Online)
ingestion — plan.md Step 9 Phase 17.

Confirmed live via real server-side queries during this build: 267,461
total rows, max(ReportedDate) = 2026-09-04 (5 days before this build), 207
rows in the trailing 45-day window — genuinely active. Unique id
`CaseNumber` confirmed 0% null. `CaseNumber` can repeat across multiple
offense-line rows per case (same multi-offense-per-report pattern as
Seattle/Baltimore/Dallas/Hartford in earlier phases) — the shared
within-batch dedup in `sync_dataset()` already handles this.

`CrimeCodeDesc` is a genuine, real offense field based on Oregon NIBRS
(e.g. "THEFT - From Building", "BURGLARY - Business", "DRUG LAWS - Drug
Law Violations") — confirmed via direct sampling, not just the field
label. Some rows are honestly "Case Report Only / No Crime Codes" (a real
no-offense outcome, same honest pattern as Hartford's "9999 NO OFFENSE"
rows in Phase 11) rather than a data-quality problem.

Address is already generalized to intersection/100-block level by the
source itself. The dataset's own publisher documentation states rape,
sex-crime, and certain family-offense categories are deliberately
excluded from this public release. No victim/officer-identifying fields
found in this schema.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

BEND_CRIME_QUERY_URL = (
    "https://services5.arcgis.com/JisFYcK2mIVg9ueP/arcgis/rest/services/"
    "Public_Cases/FeatureServer/0/query"
)
SOURCE_BEND_CRIME = "bend_crime"
CITY_NAME = "Bend"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "CaseNumber,ReportedDate,CrimeCodeDesc,CaseAddress,Neighborhood"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "ReportedDate DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(BEND_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Bend ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("CrimeCodeDesc"), "an incident")
    address = clean_field(record.get("CaseAddress"), "an unspecified location")
    neighborhood = clean_field(record.get("Neighborhood"))
    date = _format_esri_date(record.get("ReportedDate"))

    return (
        f"{CITY_NAME} crime report: {offense} near {address}"
        + (f" ({neighborhood})" if neighborhood else "")
        + f", on {date}."
    )


async def sync_bend_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_BEND_CRIME, CITY_NAME, "CaseNumber", _summarize)
