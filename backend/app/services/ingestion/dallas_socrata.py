"""Dallas Open Data (Socrata) ingestion — plan.md Step 9 Phase 1.

Endpoint confirmed live via a real request during this build:
https://www.dallasopendata.com/resource/qv6i-rri7.json ("Police Incidents").
Confirmed genuinely real-time (same-day records). This dataset carries
noticeably more sensitive fields than any other city integrated so far —
complainant race/ethnicity/sex (comprace/compethnicity/compsex), and the
reporting/assigned officer's real name and badge number (ro1name,
ro1badge, assoffbadge). None of these are surfaced in the summary text
below, matching the same privacy posture already established for NYC
(no victim/officer identifying detail) and LA (no victim demographics) —
this summarizer describes the incident, never the people involved.
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

DALLAS_INCIDENTS_URL = "https://www.dallasopendata.com/resource/qv6i-rri7.json"
SOURCE_DALLAS_INCIDENTS = "dallas_incidents"
CITY_NAME = "Dallas"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("offincident"), "an incident")
    location_type = clean_field(record.get("premise"))
    division = clean_field(record.get("division"), "an unspecified division")
    address = clean_field(record.get("incident_address"))
    raw_date = clean_field(record.get("date1"))
    date = raw_date[:10] if raw_date else "an unknown date"
    status = clean_field(record.get("status"))

    # See austin_socrata.py's identical comment: city name must be in the
    # embedded summary text, not just the DB column.
    parts = [
        f"{CITY_NAME} police incident: {offense}",
        f"in the {division} division"
        + (f" near {address}" if address else "")
        + f", on {date}.",
    ]
    if location_type and location_type.upper() != "N/A":
        parts.append(f"Location type: {location_type}.")
    if status:
        parts.append(f"Status: {status}.")
    return " ".join(p for p in parts if p.strip())


async def sync_dallas_incidents(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(DALLAS_INCIDENTS_URL, limit, params={"$order": "date1 DESC"})
    return await sync_dataset(session, records, SOURCE_DALLAS_INCIDENTS, CITY_NAME, "incidentnum", _summarize)
