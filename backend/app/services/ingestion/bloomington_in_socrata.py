"""Bloomington, IN Open Data (Socrata) ingestion — plan.md Step 9
Phase 29.

Discovered via `OpenPoliceData`'s source table, then independently
re-verified via direct HTTP queries before any code was written.

Confirmed live via real server-side queries during this build: 640,539
total rows, max(datetime) = 2026-09-08 (2 days before this build), real
long-tail history (min date 2016-01-01). Unique id `case_number`
confirmed 0% null. Single agency (Bloomington PD), not a regional feed.

`nature` is the real call-type/offense field — confirmed via direct
sampling, blank on only 5/640,539 rows overall (~0.0008%), a negligible
gap. No personal-identifier fields found in this schema — checked
directly, no CCN/WARD/ANC/PSA/BID fields (this project's recurring
"mislabeled DC MPD data" pattern) and no victim/officer names; only
district-level location, no street addresses.
"""

import logging

from sqlmodel import Session

from app.services.ingestion.socrata_base import (
    DEFAULT_FETCH_LIMIT,
    clean_field,
    fetch_socrata_json,
    sync_dataset,
)

logger = logging.getLogger(__name__)

BLOOMINGTON_IN_CALLS_URL = "https://data.bloomington.in.gov/resource/t5xf-ggw6.json"
SOURCE_BLOOMINGTON_IN_CALLS = "bloomington_in_calls"
CITY_NAME = "Bloomington, IN"


def _summarize(record: dict) -> str:
    call_type = clean_field(record.get("nature"), "an incident")
    district = clean_field(record.get("district"))
    date = clean_field(record.get("datetime"))
    date = date[:10] if date else "an unknown date"

    location = f"district {district}" if district else "an unspecified location"
    return f"{CITY_NAME} police call: {call_type} in {location}, on {date}."


async def sync_bloomington_in_calls(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(
        BLOOMINGTON_IN_CALLS_URL,
        limit,
        params={
            "$order": "datetime DESC",
            "$select": "case_number,datetime,nature,district",
        },
    )
    return await sync_dataset(
        session, records, SOURCE_BLOOMINGTON_IN_CALLS, CITY_NAME, "case_number", _summarize
    )
