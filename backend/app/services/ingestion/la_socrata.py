"""Los Angeles Open Data (Socrata) ingestion — plan.md Step 9 Phase 1.

Real, live data-source migration found and fixed during a client-facing
sample-question re-test (plan.md "Test similar client questions"): the
original endpoint (`2nrs-mtv8`, "Crime Data from 2020 to Present") was
flagged at build time as lagging some months behind real incident dates
— confirmed at the time to still be a real, if stale, data source, not a
bug. Re-tested live and found it has gone genuinely dead-ended since:
directly queried its own max(date_rptd) and got 2025-03-28 — over a year
and a half stale relative to when this fix was made (2026-09-11), not
"a few months" anymore. Root cause: LAPD retired this dataset in favor of
a new one — confirmed via a real web search, not assumed — "LAPD NIBRS
Offenses Dataset 2026 to Present" (Socrata id `k7nn-b2ep`), updated daily
per its own catalog.data.gov listing. Verified this new dataset's real
freshness directly, not from its own claim alone: max(date_occ) = 2026-08-22,
about 3 weeks old — a real, substantial improvement.

This is a genuinely different schema, not a URL swap: `caseno` (not
`dr_no`), `nibr_description` (not `crm_cd_desc`), `hndrdth_loc_chk` (a
hundred-block-level location string, same granularity as the old
`premis_desc`+area pairing), `status_desc`, `area_name`. Checked the new
schema's full field list live for PII before writing this summarizer —
confirmed no name/demographic fields exist in the dataset at all (unlike
the old dataset, which had vict_age/vict_sex/vict_descent fields this
summarizer already deliberately excluded — the new dataset doesn't even
have them to exclude).
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

LA_CRIME_URL = "https://data.lacity.org/resource/k7nn-b2ep.json"
SOURCE_LA_CRIME = "la_crime"
CITY_NAME = "Los Angeles"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("nibr_description"), "an incident")
    area = clean_field(record.get("area_name"), "an unspecified area")
    location = clean_field(record.get("hndrdth_loc_chk"))
    raw_date = clean_field(record.get("date_occ"))
    date = raw_date[:10] if raw_date else "an unknown date"
    status = clean_field(record.get("status_desc"))

    # See austin_socrata.py's identical comment: city name must be in the
    # embedded summary text, not just the DB column, or a city-specific
    # query can miss real matching records on retrieval.
    parts = [
        f"{CITY_NAME} crime report: {offense}",
        f"near {location}," if location else f"in the {area} area,",
        f"on {date}.",
    ]
    if status:
        parts.append(f"Status: {status}.")
    return " ".join(p for p in parts if p.strip())


async def sync_la_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(LA_CRIME_URL, limit, params={"$order": "date_occ DESC"})
    return await sync_dataset(session, records, SOURCE_LA_CRIME, CITY_NAME, "caseno", _summarize)
