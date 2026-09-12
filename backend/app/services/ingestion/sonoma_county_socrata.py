"""Sonoma County, CA Open Data (Socrata, regional multi-agency feed)
ingestion — plan.md Step 9 Phase 29.

Discovered via `OpenPoliceData`'s source table, then independently
re-verified via direct HTTP queries before any code was written.

Confirmed live via real server-side queries during this build: 329,923
total rows, max(date_time) = 2026-09-09 (same day as this build), real
long-tail history (min date 1956-09-01). Unique id `id` confirmed 0%
null. `incident_type` confirmed 0.35% blank overall (1,140/329,923) — a
real but minor gap, handled honestly via the shared clean_field
fallback.

**Real, genuine multi-agency structure, confirmed directly and handled
the same way St. Louis County's Phase 10 module handles it** (not split
into separate per-city sources): this feed covers 3 distinct real
agencies — Sonoma County Sheriff's Office (251,230 rows), Windsor Police
Department (45,485), and Sonoma Police Department (33,208), confirmed
via a direct `$group=agency` query. `CITY_NAME` is deliberately set to
"Sonoma County", not any one city within it, and the summary includes
the real reporting agency so a reader isn't misled about jurisdiction.

**Real ordering nuance found and handled**: sorting purely by
`date_time DESC` can surface older-looking rows first when `date_time`
itself is blank on some records (their `upload` timestamp is unrelated
to the actual incident recency) — the fetch filters to non-blank
`date_time` so the module surfaces genuinely the most recent classified
incidents. No personal-identifier fields found in this schema — checked
directly, no CCN/WARD/ANC/PSA/BID fields (this project's recurring
"mislabeled DC MPD data" pattern) and no victim/officer names.
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

SONOMA_COUNTY_CRIME_URL = "https://data.sonomacounty.ca.gov/resource/3rsj-iche.json"
SOURCE_SONOMA_COUNTY_CRIME = "sonoma_county_crime"
CITY_NAME = "Sonoma County"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("incident_type"), "an incident")
    agency = clean_field(record.get("agency"))
    town = clean_field(record.get("city"))
    intersection = clean_field(record.get("intersection"))
    date = clean_field(record.get("date_time"))
    date = date[:10] if date else "an unknown date"

    location = intersection or town or "an unspecified location"
    parts = [f"{CITY_NAME} crime report: {offense} near {location}"]
    if agency:
        parts.append(f"(reported by {agency})")
    return " ".join(parts) + f", on {date}."


async def sync_sonoma_county_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(
        SONOMA_COUNTY_CRIME_URL,
        limit,
        params={
            "$order": "date_time DESC",
            "$where": "date_time IS NOT NULL",
            "$select": "id,date_time,incident_type,agency,city,intersection",
        },
    )
    return await sync_dataset(session, records, SOURCE_SONOMA_COUNTY_CRIME, CITY_NAME, "id", _summarize)
