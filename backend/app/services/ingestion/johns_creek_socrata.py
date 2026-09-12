"""Johns Creek, GA Open Data (Socrata) ingestion — plan.md Step 9
Phase 30.

Discovered via `OpenPoliceData`'s source table, then independently
re-verified via direct HTTP queries before any code was written.

Confirmed live via real server-side queries during this build: 42,649
total rows, max(date_occu) = 2026-09-09 (same day as this build), real
multi-decade history (min date 2000-01-01). Unique id `incidentid`
confirmed 0% null. Single agency (JCPD), not regional.

`offense` is a genuine offense field — confirmed via direct sampling. No
personal-identifier fields found in this schema — checked directly
against the full field list, no CCN/WARD/ANC/PSA/BID fields (this
project's recurring "mislabeled DC MPD data" pattern) and no victim/
officer names.
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

JOHNS_CREEK_CRIME_URL = "https://policeview.johnscreekga.gov/resource/ake9-ajui.json"
SOURCE_JOHNS_CREEK_CRIME = "johns_creek_crime"
CITY_NAME = "Johns Creek"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("offense"), "an incident")
    reported_as = clean_field(record.get("reportedas"))
    street = clean_field(record.get("street"), "an unspecified location")
    date = clean_field(record.get("date_occu"))
    date = date[:10] if date else "an unknown date"

    detail = f" ({reported_as})" if reported_as and reported_as.lower() != offense.lower() else ""
    return f"{CITY_NAME} crime report: {offense}{detail} near {street}, on {date}."


async def sync_johns_creek_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(
        JOHNS_CREEK_CRIME_URL,
        limit,
        params={
            "$order": "date_occu DESC",
            "$select": "incidentid,date_occu,offense,reportedas,street",
        },
    )
    return await sync_dataset(session, records, SOURCE_JOHNS_CREEK_CRIME, CITY_NAME, "incidentid", _summarize)
