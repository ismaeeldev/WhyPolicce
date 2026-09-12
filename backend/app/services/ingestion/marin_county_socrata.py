"""Marin County, CA Open Data (Socrata) ingestion — plan.md Step 9
Phase 29.

Discovered via `OpenPoliceData`'s source table, then independently
re-verified via direct HTTP queries before any code was written.

Confirmed live via real server-side queries during this build: 52,816
total rows, max(incident_date_time) = 2026-09-09 (same day as this
build), real long-tail history (min date 2013-01-01). Unique id `im_dr`
confirmed 1 null out of 52,816 (~0.002%) — a real but negligible gap, not
disqualifying; the shared `sync_dataset()` falsy-id-skip already handles
that one row safely. Single jurisdiction (Marin County Sheriff), not a
regional multi-agency feed despite the county-level name.

`crime` is a genuine offense field — confirmed via direct sampling. No
personal-identifier fields found in this schema — checked directly, no
CCN/WARD/ANC/PSA/BID fields (this project's recurring "mislabeled DC MPD
data" pattern) and no victim/officer names.
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

MARIN_COUNTY_CRIME_URL = "https://data.marincounty.gov/resource/ahxi-5nsc.json"
SOURCE_MARIN_COUNTY_CRIME = "marin_county_crime"
CITY_NAME = "Marin County"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("crime"), "an incident")
    category = clean_field(record.get("crime_class"))
    address = clean_field(record.get("incident_street_address"), "an unspecified location")
    town = clean_field(record.get("incident_city_town"))
    date = clean_field(record.get("incident_date_time"))
    date = date[:10] if date else "an unknown date"

    detail = f" ({category})" if category and category.lower() != offense.lower() else ""
    return (
        f"{CITY_NAME} crime report: {offense}{detail} near {address}"
        + (f" ({town})" if town else "")
        + f", on {date}."
    )


async def sync_marin_county_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(
        MARIN_COUNTY_CRIME_URL,
        limit,
        params={
            "$order": "incident_date_time DESC",
            "$select": "im_dr,incident_date_time,crime,crime_class,incident_street_address,incident_city_town",
        },
    )
    return await sync_dataset(session, records, SOURCE_MARIN_COUNTY_CRIME, CITY_NAME, "im_dr", _summarize)
