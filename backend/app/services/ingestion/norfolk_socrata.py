"""Norfolk, VA Open Data (Socrata) ingestion — plan.md Step 9 Phase 9.

Confirmed live via a real recent-window query during this build: 2,052
records since 2026-08-01, max(date_occu) = 2026-09-08 (same day as this
build). 108,398 total rows. Unique id `inci_id` confirmed 0% null and 0%
blank.

Real correction to research: the plausible-looking `transparentrichmond.org`
dataset that name-matched "Richmond" turned out to be a decoy for Richmond,
CALIFORNIA (sample rows show `state:"CA", zipcode:"94806"`), not Richmond,
Virginia — rejected and replaced with this real, verified Norfolk source
instead.

Notably minimal schema (`inci_id, offense, streetno, street, date_occu,
hour_occu, tract, zone, district, reportarea, dow1`) — no exact
coordinates (block-level street only) and no demographic or officer-
identifying fields at all, a privacy-by-design dataset from the source
itself. No disposition field present.
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

NORFOLK_CRIME_URL = "https://data.norfolk.gov/resource/r7bn-2egr.json"
SOURCE_NORFOLK_CRIME = "norfolk_crime"
CITY_NAME = "Norfolk"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("offense"), "an incident")
    street_no = clean_field(record.get("streetno"))
    street = clean_field(record.get("street"))
    district = clean_field(record.get("district"), "unknown")
    date = clean_field(record.get("date_occu"))
    date = date[:10] if date else "an unknown date"

    address = f"{street_no} {street}".strip() if (street_no or street) else "an unspecified location"

    return f"{CITY_NAME} crime report: {offense.title()} near {address}, district {district}, on {date}."


async def sync_norfolk_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(NORFOLK_CRIME_URL, limit, params={"$order": "date_occu DESC"})
    return await sync_dataset(session, records, SOURCE_NORFOLK_CRIME, CITY_NAME, "inci_id", _summarize)
