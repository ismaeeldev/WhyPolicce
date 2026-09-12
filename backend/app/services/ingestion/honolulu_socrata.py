"""Honolulu, HI Open Data (Socrata, CrimeMapping/LexisNexis-syndicated
public feed) ingestion — plan.md Step 9 Phase 11.

Confirmed live via real server-side queries during this build: 13,902
total rows, max(date) = 2026-09-08 (same day as this build), 3,391 rows
in the trailing 45-day window — genuinely active. Unique id `incidentnum`
confirmed 0% null.

Real, confirmed schema limitation, same class of gap as Cincinnati's
Phase 9 finding: only a coarse `type` field exists (e.g. "BURGLARY",
"DUI", "THEFT/LARCENY" — roughly 14 broad categories), with no granular
offense-description or statute-citation field in this schema. Summarized
honestly at this coarse level rather than fabricating detail the data
doesn't contain. No disposition field beyond a terse `status` code
(unclear public meaning, not surfaced in the summary). No
personal-identifier fields found.
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

HONOLULU_CRIME_URL = "https://data.honolulu.gov/resource/vg88-5rn5.json"
SOURCE_HONOLULU_CRIME = "honolulu_crime"
CITY_NAME = "Honolulu"


def _summarize(record: dict) -> str:
    offense_type = clean_field(record.get("type"), "an incident")
    address = clean_field(record.get("blockaddress"), "an unspecified location")
    date = clean_field(record.get("date"))
    date = date[:10] if date else "an unknown date"

    return f"{CITY_NAME} crime report: {offense_type.title()} near {address}, on {date}."


async def sync_honolulu_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(
        HONOLULU_CRIME_URL,
        limit,
        params={
            "$order": "date DESC",
            "$select": "incidentnum,blockaddress,date,type",
        },
    )
    return await sync_dataset(session, records, SOURCE_HONOLULU_CRIME, CITY_NAME, "incidentnum", _summarize)
