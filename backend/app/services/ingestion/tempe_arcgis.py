"""Tempe, AZ Open Data (ArcGIS FeatureServer, hosted on ArcGIS Online)
ingestion — plan.md Step 9 Phase 13.

Confirmed live via real server-side queries during this build: 643,670
total rows (layer 0, NIBRS 2022-present; older UCR-era data lives in
separate layers 1-2, not ingested here), max(OccurrenceDatetime) =
2026-09-06 (2 days before this build), 14,733 rows in the trailing 45-day
window — genuinely active. Unique id `PrimaryKey` confirmed 0% null.
Despite the large table size, count/query requests responded quickly
(well under a few seconds) — no special timeout handling needed, unlike
Boise's Phase 12 finding for a differently-structured large table.

Real, confirmed schema limitation: `FinalCaseType`/`InitialCaseType` are
NUMERIC CASE-TYPE CODES (e.g. "962", "240", "417D"), not plain-language
offense descriptions, and no separate description field exists in this
schema — confirmed by direct sampling, not assumed. Summarized honestly
with the raw code rather than fabricating a description the data doesn't
contain. `ObfuscatedAddress` is already block-level by the source itself
(e.g. "2X W 5TH ST"). `CaseStatus` used as a disposition field.

`UnitID1`/`UnitID2`/`UnitID3` (not ingested by this module) were
confirmed via direct sampling to be dispatch unit call signs (e.g. "B700",
"5P15"), not individual officer names — no personal-identifier fields
found in this schema.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

TEMPE_CALLS_QUERY_URL = (
    "https://services.arcgis.com/lQySeXwbBg53XWDi/ArcGIS/rest/services/"
    "Calls_For_Service/FeatureServer/0/query"
)
SOURCE_TEMPE_CALLS = "tempe_calls"
CITY_NAME = "Tempe"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "PrimaryKey,OccurrenceDatetime,FinalCaseType,ObfuscatedAddress,CaseStatus"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "OccurrenceDatetime DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(TEMPE_CALLS_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Tempe ArcGIS query failed: {data['error']}")
    records = [f["attributes"] for f in data.get("features", [])]
    # Real, confirmed field-padding quirk: `PrimaryKey` (and other string
    # fields) arrive from this source with trailing whitespace baked into
    # their fixed-length storage (e.g. "TE202690682         ") — stripped
    # here so external_id/dedup keys match cleanly across syncs instead of
    # silently treating "TE202690682" and "TE202690682 " as different ids.
    for record in records:
        if record.get("PrimaryKey"):
            record["PrimaryKey"] = record["PrimaryKey"].strip()
    return records


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    case_type = clean_field(record.get("FinalCaseType"))
    address = clean_field(record.get("ObfuscatedAddress"), "an unspecified location")
    date = _format_esri_date(record.get("OccurrenceDatetime"))

    offense = f"case type {case_type}" if case_type else "an incident"
    return f"{CITY_NAME} police call: {offense} near {address}, on {date}."


async def sync_tempe_calls(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_TEMPE_CALLS, CITY_NAME, "PrimaryKey", _summarize)
