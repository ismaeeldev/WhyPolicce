"""Buffalo, NY Open Data (Socrata) ingestion — plan.md Step 9 Phase 13.

Confirmed live via real server-side queries during this build: 337,351
total rows, max(incident_datetime) = 2026-09-08 (same day as this build),
1,377 rows in the trailing 45-day window — genuinely active. Unique id
`case_number` confirmed 0% null.

Real, confirmed field-content limitation, checked directly rather than
assumed from the field name: `incident_description` sounds like it should
hold a real narrative, but every sampled row contains the exact same
boilerplate disclaimer text ("Buffalo Police are investigating this
report of a crime. It is important to note that this is very preliminary
information...") — not real per-incident detail. This module uses
`incident_type_primary` (e.g. "Burglary", "Assault") and
`parent_incident_type` (e.g. "Breaking & Entering") instead, which do
carry real, distinct, per-record values. No disposition field present. No
personal-identifier fields found in this schema.
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

BUFFALO_CRIME_URL = "https://data.buffalony.gov/resource/d6g9-xbgu.json"
SOURCE_BUFFALO_CRIME = "buffalo_crime"
CITY_NAME = "Buffalo"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("incident_type_primary"), "an incident")
    parent_type = clean_field(record.get("parent_incident_type"))
    address = clean_field(record.get("address_1"), "an unspecified location")
    neighborhood = clean_field(record.get("neighborhood"))
    date = clean_field(record.get("incident_datetime"))
    date = date[:10] if date else "an unknown date"

    detail = f" ({parent_type})" if parent_type and parent_type.lower() != offense.lower() else ""
    return (
        f"{CITY_NAME} crime report: {offense}{detail} near {address}"
        + (f" ({neighborhood})" if neighborhood else "")
        + f", on {date}."
    )


async def sync_buffalo_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(
        BUFFALO_CRIME_URL,
        limit,
        params={
            "$order": "incident_datetime DESC",
            "$select": "case_number,incident_datetime,incident_type_primary,parent_incident_type,address_1,neighborhood",
        },
    )
    return await sync_dataset(session, records, SOURCE_BUFFALO_CRIME, CITY_NAME, "case_number", _summarize)
