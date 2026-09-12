"""Colorado Springs Open Data (Socrata) ingestion — plan.md Step 9 Phase 9.

Confirmed live via a real recent-window query during this build: 4,706
records since 2026-08-01, max(reporteddate) = 2026-09-08 (same day as this
build). 531,850 total rows. Unique id `casenumber` confirmed 0% null and
0% blank (checked both `IS NULL` and `= ''`).

Note: the first-glance "Crime Map" dataset (`ar6u-b83m`) was found to be a
broken/empty view during research (no fields returned) — this module
targets `bc88-hemr` ("Crime Level Data") instead, the real populated
dataset.
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

COLORADO_SPRINGS_CRIME_URL = "https://policedata.coloradosprings.gov/resource/bc88-hemr.json"
SOURCE_COLORADO_SPRINGS_CRIME = "colorado_springs_crime"
CITY_NAME = "Colorado Springs"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("crimecodedescription"), "an incident")
    category = clean_field(record.get("index_crime_category"))
    address = clean_field(record.get("streetaddress"), "an unspecified location")
    date = clean_field(record.get("reporteddate"))
    date = date[:10] if date else "an unknown date"
    disposition = clean_field(record.get("disposition"))

    detail = f" ({category})" if category and category.lower() != offense.lower() else ""
    parts = [
        f"{CITY_NAME} crime report: {offense}{detail}",
        f"near {address}, on {date}.",
    ]
    if disposition:
        parts.append(f"Disposition: {disposition.title()}.")
    return " ".join(p for p in parts if p.strip())


async def sync_colorado_springs_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(COLORADO_SPRINGS_CRIME_URL, limit, params={"$order": "reporteddate DESC"})
    return await sync_dataset(session, records, SOURCE_COLORADO_SPRINGS_CRIME, CITY_NAME, "casenumber", _summarize)
