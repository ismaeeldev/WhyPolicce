"""Austin Open Data (Socrata) ingestion — plan.md Step 9 Phase 1.

Endpoint confirmed live via a real request during this build:
https://data.austintexas.gov/resource/fdj4-gpfu.json ("Crime Reports").
Real sample fields observed: incident_report_number, crime_type, occ_date,
location_type, district, clearance_status. Found live: this dataset does
NOT default to recent-first ordering — an unordered fetch returned records
from 2002-2003 during initial verification — so `$order=occ_date DESC` is
required, not optional, to get current data.
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

AUSTIN_CRIME_URL = "https://data.austintexas.gov/resource/fdj4-gpfu.json"
SOURCE_AUSTIN_CRIME = "austin_crime"
CITY_NAME = "Austin"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("crime_type"), "an incident")
    location_type = clean_field(record.get("location_type"))
    district = clean_field(record.get("district"), "unknown")
    raw_date = clean_field(record.get("occ_date"))
    date = raw_date[:10] if raw_date else "an unknown date"
    clearance = clean_field(record.get("clearance_status"))
    family_violence = record.get("family_violence") == "Y"

    # Real accuracy bug found and fixed (Revision 3 Step 9): none of the
    # multi-city summaries originally included the city's own name in the
    # embedded text — confirmed directly via a real "Any crime reports in
    # Austin?" query that missed genuine, correctly-ingested Austin records
    # because there was no textual signal to match "Austin" against, only
    # offense-type similarity. Prepending the city name here (and in every
    # other city's summarizer, NYC included) fixes that.
    parts = [
        f"{CITY_NAME} crime report: {offense}",
        f"in district {district}, on {date}.",
    ]
    if location_type:
        parts.append(f"Location type: {location_type}.")
    if family_violence:
        parts.append("Flagged as a family violence incident.")
    if clearance:
        clearance_desc = {"C": "Cleared", "N": "Not cleared", "O": "Cleared by exception"}.get(
            clearance, clearance
        )
        parts.append(f"Status: {clearance_desc}.")
    return " ".join(p for p in parts if p.strip())


async def sync_austin_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(AUSTIN_CRIME_URL, limit, params={"$order": "occ_date DESC"})
    return await sync_dataset(session, records, SOURCE_AUSTIN_CRIME, CITY_NAME, "incident_report_number", _summarize)
