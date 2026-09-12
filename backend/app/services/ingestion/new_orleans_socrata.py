"""New Orleans Open Data (Socrata) ingestion — plan.md Step 9 Phase 8.

Confirmed live via a real query during this build: most recent
`timecreate` is 2026-09-07T23:59:45, one day before this build —
genuinely current, 237,639 total rows confirmed.

Real, confirmed replacement for a known-stale dataset: a prior phase's
research had already found an old New Orleans dataset (817 rows, max
date 2024-01-01) and correctly rejected it. This module targets the
CURRENT NOPD account's actively-maintained yearly dataset ("Calls for
Service 2026") instead, found via Socrata's own catalog API rather than
assuming the old resource id was simply outdated.

This is "Calls for Service" (CAD/dispatch-level events — includes
non-crime calls like tows and area checks), not a pure offense-
classification dataset, same caveat as Milwaukee's raw-code gap:
genuinely useful and fully live, but a different granularity than a
"crime report" dataset. Summarized honestly as a "police call" not a
"crime report" for that reason.
"""

import logging

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import (
    DEFAULT_FETCH_LIMIT,
    clean_field,
    fetch_socrata_json,
    sync_dataset,
)

logger = logging.getLogger(__name__)

NEW_ORLEANS_CALLS_URL = "https://data.nola.gov/resource/es9j-6y5d.json"
SOURCE_NEW_ORLEANS_CALLS = "new_orleans_calls"
CITY_NAME = "New Orleans"


def _summarize(record: dict) -> str:
    call_type = clean_field(record.get("typetext"), "an incident")
    address = clean_field(record.get("block_address"), "an unspecified location")
    district = clean_field(record.get("policedistrict"), "unknown")
    date = clean_field(record.get("timecreate"))
    date = date[:10] if date else "an unknown date"
    disposition = clean_field(record.get("dispositiontext"))

    parts = [
        f"{CITY_NAME} police call: {call_type.title()}",
        f"near {address}, police district {district}, on {date}.",
    ]
    if disposition:
        parts.append(f"Disposition: {disposition.title()}.")
    return " ".join(p for p in parts if p.strip())


async def sync_new_orleans_calls(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(NEW_ORLEANS_CALLS_URL, limit, params={"$order": "timecreate DESC"})
    return await sync_dataset(session, records, SOURCE_NEW_ORLEANS_CALLS, CITY_NAME, "nopd_item", _summarize)
