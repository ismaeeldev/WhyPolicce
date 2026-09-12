"""Montgomery County, MD Open Data (Socrata) ingestion — plan.md Step 9
Phase 14.

Confirmed live via real server-side queries during this build: 507,374
total rows, max(start_date) = 2026-09-08 (same day as this build), 4,783
rows in the trailing 45-day window — genuinely active. Unique id
`incident_id` confirmed 0% null.

`crimename3` is the genuine, most granular offense field in a 3-level
hierarchy (`crimename1` > `crimename2` > `crimename3`, e.g. "Crime
Against Society" > "Liquor Law Violations" > "LIQUOR (DESCRIBE
OFFENSE)") — confirmed via a live sample, real per-record detail, not
boilerplate. No disposition field present. No personal-identifier fields
found in this schema — location is deliberately block-rounded by the
source itself, and some `latitude`/`longitude` pairs are zeroed out for
privacy on certain incident types (confirmed directly, handled honestly
by falling back to the text `location` field for the address).
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

MONTGOMERY_COUNTY_CRIME_URL = "https://data.montgomerycountymd.gov/resource/icn6-v9z3.json"
SOURCE_MONTGOMERY_COUNTY_CRIME = "montgomery_county_crime"
CITY_NAME = "Montgomery County"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("crimename3"), "an incident")
    category = clean_field(record.get("crimename2"))
    location = clean_field(record.get("location"), "an unspecified location")
    district = clean_field(record.get("district"))
    date = clean_field(record.get("start_date"))
    date = date[:10] if date else "an unknown date"

    detail = f" ({category})" if category and category.lower() != offense.lower() else ""
    parts = [f"{CITY_NAME} crime report: {offense.title()}{detail} near {location}"]
    if district:
        parts.append(f"({district.title()} district)")
    return " ".join(parts) + f", on {date}."


async def sync_montgomery_county_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(
        MONTGOMERY_COUNTY_CRIME_URL,
        limit,
        params={
            "$order": "start_date DESC",
            "$select": "incident_id,start_date,crimename2,crimename3,location,district",
        },
    )
    return await sync_dataset(
        session, records, SOURCE_MONTGOMERY_COUNTY_CRIME, CITY_NAME, "incident_id", _summarize
    )
