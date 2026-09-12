"""Seattle Open Data (Socrata) ingestion — plan.md Step 9 Phase 1.

Endpoint confirmed live via a real request during this build:
https://data.seattle.gov/resource/tazs-3rd5.json ("SPD Crime Data:
2008-Present"). Real sample fields observed: report_number, offense_date,
offense_category, nibrs_offense_code_description, precinct, neighborhood,
block_address. Confirmed genuinely near-real-time (records from the same
day as this build), unlike LA's dataset — noted since freshness varies
meaningfully city to city and shouldn't be assumed uniform.
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

SEATTLE_CRIME_URL = "https://data.seattle.gov/resource/tazs-3rd5.json"
SOURCE_SEATTLE_CRIME = "seattle_crime"
CITY_NAME = "Seattle"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("nibrs_offense_code_description"), "an incident")
    category = clean_field(record.get("offense_category"))
    neighborhood = clean_field(record.get("neighborhood"), "an unspecified neighborhood")
    if neighborhood == "-":
        neighborhood = "an unspecified neighborhood"
    precinct = clean_field(record.get("precinct"), "unknown")
    raw_date = clean_field(record.get("offense_date"))
    date = raw_date[:10] if raw_date else "an unknown date"

    # See austin_socrata.py's identical comment: city name must be in the
    # embedded summary text, not just the DB column.
    prefix = f"{category} " if category and category != "ALL OTHER" else ""
    parts = [
        f"{CITY_NAME} {prefix}report: {offense}",
        f"in {neighborhood}, {precinct} precinct, on {date}.",
    ]
    return " ".join(p for p in parts if p.strip())


async def sync_seattle_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(SEATTLE_CRIME_URL, limit, params={"$order": "offense_date DESC"})
    return await sync_dataset(session, records, SOURCE_SEATTLE_CRIME, CITY_NAME, "report_number", _summarize)
