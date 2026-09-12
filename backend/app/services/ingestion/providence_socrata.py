"""Providence, RI Open Data (Socrata) ingestion — plan.md Step 9 Phase 11.

Confirmed live via real server-side queries during this build: 5,428
total rows (this is an explicit 180-day rolling window by the dataset's
own name — "Providence Police Case Log - Past 180 days" — a small total
is expected/correct, same reasoning as Tampa's rolling-365-day layer in
Phase 10, not a thin/stale-data red flag), max(reported_date) =
2026-09-07, 1,376 rows in the trailing 45-day window — genuinely dense.
Unique id `casenumber` confirmed 0% null.

**Real personal-identifier field found and excluded, a genuine correction
to research findings**: `reporting_officer` was initially assumed to be
station/unit-level only, but a direct sample pull during this build found
a real individual name in the field ("RMorales" alongside station-level
values like "Central Station") — confirmed via live data, not assumed.
Excluded from the ingested field list and the summary entirely, same
privacy posture as every other city with officer-identifying fields.

`offense_desc` is a genuine, granular offense field (e.g. "Motor Vehicle
Theft") backed by a full statute code/description — no coarseness
limitation found. No disposition field present.
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

PROVIDENCE_CRIME_URL = "https://data.providenceri.gov/resource/rz3y-pz8v.json"
SOURCE_PROVIDENCE_CRIME = "providence_crime"
CITY_NAME = "Providence"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("offense_desc"), "an incident")
    location = clean_field(record.get("location"), "an unspecified location")
    date = clean_field(record.get("reported_date"))
    date = date[:10] if date else "an unknown date"

    return f"{CITY_NAME} crime report: {offense} near {location}, on {date}."


async def sync_providence_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    # Deliberately omits `reporting_officer` from $select — not needed by
    # the summarizer and this way it never even transits into raw_json.
    records = await fetch_socrata_json(
        PROVIDENCE_CRIME_URL,
        limit,
        params={
            "$order": "reported_date DESC",
            "$select": "casenumber,location,reported_date,offense_desc,statute_desc",
        },
    )
    return await sync_dataset(session, records, SOURCE_PROVIDENCE_CRIME, CITY_NAME, "casenumber", _summarize)
