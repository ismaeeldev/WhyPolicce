"""Chicago Open Data (Socrata) ingestion — plan.md Step 9 Phase 1.

Endpoint confirmed live via a real request during this build (not assumed
from research alone):
https://data.cityofchicago.org/resource/ijzp-q8t2.json ("Crimes - 2001 to
Present"). Real sample fields observed: case_number, date, primary_type,
description, location_description, block, district, arrest, domestic.
No API key required, same as NYC's Socrata endpoints.
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

CHICAGO_CRIMES_URL = "https://data.cityofchicago.org/resource/ijzp-q8t2.json"
SOURCE_CHICAGO_CRIMES = "chicago_crimes"
CITY_NAME = "Chicago"


def _summarize(record: dict) -> str:
    """Turns one raw Chicago crime record into a short, readable summary —
    same purpose/shape as nyc_socrata.py's summarizers, using this
    dataset's own field names (verified live, not guessed)."""
    offense = clean_field(record.get("primary_type"), "an incident")
    detail = clean_field(record.get("description"))
    block = clean_field(record.get("block"), "an unspecified location")
    district = clean_field(record.get("district"), "unknown")
    raw_date = clean_field(record.get("date"))
    date = raw_date[:10] if raw_date else "an unknown date"
    location_type = clean_field(record.get("location_description"))
    was_arrest = record.get("arrest") is True

    # Real accuracy bug found and fixed (Revision 3 Step 9): summaries must
    # include the city's own name in the embedded text — a real "Any crime
    # reports in Austin?" query missed genuine Austin records before this
    # fix, since only offense-type similarity was available to match on,
    # not city. Applied to every city's summarizer, NYC included.
    parts = [
        f"{CITY_NAME} crime report: {offense}" + (f" ({detail})" if detail and detail != offense else ""),
        f"reported near {block}, district {district}, on {date}.",
    ]
    if location_type:
        parts.append(f"Location type: {location_type}.")
    parts.append("An arrest was made." if was_arrest else "No arrest recorded for this report.")
    return " ".join(p for p in parts if p.strip())


async def sync_chicago_crimes(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    # $order=date DESC — same reasoning as the Austin connector's docstring:
    # confirmed live that this dataset does not default to recent-first, so
    # an unordered fetch can return old records instead of current ones.
    records = await fetch_socrata_json(CHICAGO_CRIMES_URL, limit, params={"$order": "date DESC"})
    return await sync_dataset(session, records, SOURCE_CHICAGO_CRIMES, CITY_NAME, "case_number", _summarize)
