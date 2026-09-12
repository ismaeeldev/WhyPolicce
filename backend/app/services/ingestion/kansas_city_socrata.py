"""Kansas City Open Data (Socrata) ingestion — plan.md Step 9 Phase 8.

Confirmed live via a real query during this build: most recent
`report_date` is 2026-09-07, one day before this build — genuinely
current, 69,333 total rows confirmed. This is a single-calendar-year
dataset (prior years exist as separate Socrata resource ids) — same
yearly-rollover maintenance note as several ArcGIS-hosted cities already
in this project (Louisville, San Jose, Tucson), just via Socrata's
per-year resource pattern instead.

Real fields include victim demographics (race, sex, age, age_range) —
deliberately excluded from the summary, same privacy posture as
Dallas/LA/Nashville/Tucson.
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

# Must be updated to the new year's resource id after this year's dataset
# stops being maintained — see module docstring.
KANSAS_CITY_CRIME_URL = "https://data.kcmo.org/resource/f7wj-ckmw.json"
SOURCE_KANSAS_CITY_CRIME = "kansas_city_crime"
CITY_NAME = "Kansas City"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("description"), "an incident")
    address = clean_field(record.get("address"), "an unspecified location")
    beat = clean_field(record.get("beat"), "unknown")
    date = clean_field(record.get("report_date"))
    date = date[:10] if date else "an unknown date"

    parts = [
        f"{CITY_NAME} crime report: {offense.title()}",
        f"near {address.strip()}, beat {beat}, on {date}.",
    ]
    return " ".join(p for p in parts if p.strip())


async def sync_kansas_city_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(KANSAS_CITY_CRIME_URL, limit, params={"$order": "report_date DESC"})
    return await sync_dataset(session, records, SOURCE_KANSAS_CITY_CRIME, CITY_NAME, "report", _summarize)
