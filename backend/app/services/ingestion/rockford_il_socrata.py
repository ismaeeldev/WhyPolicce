"""Rockford, IL Open Data (Socrata, hosted on the shared Illinois EDP
domain) ingestion — plan.md Step 9 Phase 33.

Discovered via fresh manual web research (Socrata catalog search) on
`illinois-edp.data.socrata.com` — a shared regional Socrata tenant used
by several northern-Illinois agencies (Rockford PD and Winnebago County
Sheriff both publish here; see winnebago_county_il_socrata.py for the
sibling dataset, kept as a SEPARATE module/source since they're two
distinct agencies' CAD feeds despite sharing an underlying platform).

Confirmed live via direct query: max(dispatch_date_time) = 2026-09-11
(same day as this build) — genuinely current, real-time CAD dispatch
data, not a stale/dummy-record file. `event_number` confirmed 0% null,
used as the external id.

Real, specific `incident_type_desc_display` values confirmed via a live
sample (e.g. "Shots Fired", "Traffic Stop", "Found Article", "Civil
Process") — genuine dispatch-call detail, not boilerplate. No personal-
identifier fields present in this schema at all (a structural side
effect of it being a public 72-hour CAD extract with only address/
district/call-type fields) — no race/sex/age/name fields exist here.
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

ROCKFORD_IL_CFS_URL = "https://illinois-edp.data.socrata.com/resource/7b7d-v8d9.json"
SOURCE_ROCKFORD_IL_CFS = "rockford_il_cfs"
CITY_NAME = "Rockford, IL"


def _summarize(record: dict) -> str:
    call_type = clean_field(record.get("incident_type_desc_display"), "a call for service")
    address = clean_field(record.get("full_address"), "an unspecified location")
    district = clean_field(record.get("reporting_district"))
    date = clean_field(record.get("dispatch_date_time"))
    date = date[:10] if date else "an unknown date"

    location = f"{address} ({district})" if district else address
    return f"{CITY_NAME} police call for service: {call_type} near {location}, on {date}."


async def sync_rockford_il_cfs(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(
        ROCKFORD_IL_CFS_URL,
        limit,
        params={
            "$order": "dispatch_date_time DESC",
            "$select": "event_number,dispatch_date_time,incident_type_desc_display,full_address,reporting_district",
        },
    )
    return await sync_dataset(
        session, records, SOURCE_ROCKFORD_IL_CFS, CITY_NAME, "event_number", _summarize
    )
