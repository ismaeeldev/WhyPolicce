"""Prince George's County, MD Open Data (Socrata/Tyler Data & Insights)
ingestion — plan.md Step 9 Phase 14.

Confirmed live via real server-side queries during this build: 78,998
total rows, max(date) = 2026-08-27 (13 days before this build), 1,937
rows in the trailing 45-day window — genuinely active. Unique id
`incident_case_id` confirmed 0% null.

Real, confirmed field-naming trap caught by sampling actual values, not
trusting the field name — the same class of gap as Grand Rapids's Phase
13 reversed-field finding: despite the name implying a case-clearance
status field, `clearance_code_inc_type` actually holds the plain-English
OFFENSE TYPE itself (e.g. "AUTO, STOLEN", "THEFT FROM AUTO", "ACCIDENT")
— confirmed via a live sample. There is no separate disposition/clearance
field in this schema despite what the misleading name suggests. Address
is already rounded to the nearest hundred block by the source itself
(victim-confidentiality practice documented on the portal). No
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

PRINCE_GEORGES_COUNTY_CRIME_URL = "https://data.princegeorgescountymd.gov/resource/xjru-idbe.json"
SOURCE_PRINCE_GEORGES_COUNTY_CRIME = "prince_georges_county_crime"
CITY_NAME = "Prince George's County"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("clearance_code_inc_type"), "an incident")
    street_number = clean_field(record.get("street_number"))
    street_address = clean_field(record.get("street_address"))
    date = clean_field(record.get("date"))
    date = date[:10] if date else "an unknown date"

    address = f"{street_number} {street_address}".strip() if (street_number or street_address) else "an unspecified location"

    return f"{CITY_NAME} crime report: {offense.title()} near {address}, on {date}."


async def sync_prince_georges_county_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(
        PRINCE_GEORGES_COUNTY_CRIME_URL,
        limit,
        params={
            "$order": "date DESC",
            "$select": "incident_case_id,date,clearance_code_inc_type,street_number,street_address",
        },
    )
    return await sync_dataset(
        session, records, SOURCE_PRINCE_GEORGES_COUNTY_CRIME, CITY_NAME, "incident_case_id", _summarize
    )
