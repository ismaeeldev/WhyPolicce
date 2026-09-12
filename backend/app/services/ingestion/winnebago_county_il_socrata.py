"""Winnebago County, IL Sheriff Open Data (Socrata, hosted on the shared
Illinois EDP domain) ingestion — plan.md Step 9 Phase 33.

Discovered alongside rockford_il_socrata.py via the same
`illinois-edp.data.socrata.com` catalog search — a distinct agency
(Winnebago County Sheriff, covering Roscoe PD/Loves Park PD/other
county-served jurisdictions per its `reporting_district` values) from a
different dataset id, kept as its own module/source per this project's
one-connector-per-agency convention even though it shares a Socrata
tenant with Rockford PD.

Confirmed live via direct query: max(dispatch_date_time) = 2026-09-11
(same day as this build) — genuinely current CAD dispatch data.
`event_number` confirmed 0% null, used as the external id.

Real, specific `incident_type_desc_display` values confirmed via a live
sample (e.g. "Traffic Stop", "Accident Property Damage", "Alarm -
Burglar", "Public Complaint Priority"). No personal-identifier fields
present in this schema at all — same structural shape as the sibling
Rockford dataset (a public 72-hour CAD extract with only address/
district/call-type fields, no race/sex/age/name fields).
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

WINNEBAGO_COUNTY_IL_CFS_URL = "https://illinois-edp.data.socrata.com/resource/i96m-iu3n.json"
SOURCE_WINNEBAGO_COUNTY_IL_CFS = "winnebago_county_il_cfs"
CITY_NAME = "Winnebago County, IL"


def _summarize(record: dict) -> str:
    call_type = clean_field(record.get("incident_type_desc_display"), "a call for service")
    address = clean_field(record.get("full_address"), "an unspecified location")
    district = clean_field(record.get("reporting_district"))
    date = clean_field(record.get("dispatch_date_time"))
    date = date[:10] if date else "an unknown date"

    location = f"{address} ({district})" if district else address
    return f"{CITY_NAME} police call for service: {call_type} near {location}, on {date}."


async def sync_winnebago_county_il_cfs(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(
        WINNEBAGO_COUNTY_IL_CFS_URL,
        limit,
        params={
            "$order": "dispatch_date_time DESC",
            "$select": "event_number,dispatch_date_time,incident_type_desc_display,full_address,reporting_district",
        },
    )
    return await sync_dataset(
        session,
        records,
        SOURCE_WINNEBAGO_COUNTY_IL_CFS,
        CITY_NAME,
        "event_number",
        _summarize,
    )
