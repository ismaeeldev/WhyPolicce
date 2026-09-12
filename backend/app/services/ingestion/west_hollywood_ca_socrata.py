"""West Hollywood, CA Open Data (Socrata) ingestion — plan.md Step 9
Phase 33.

Discovered via fresh manual web research (Socrata catalog search) on
`data.weho.org`, not `OpenPoliceData`'s source table.

**Real dataset-selection finding**: this domain has multiple similarly-
named crime datasets. `awjs-gawv` ("West Hollywood Current Crime Data -
Year to Date") is the genuinely current, row-level one — confirmed live:
`incident_date`, `category`, `stat_desc` (a specific offense subtype,
e.g. "OFFENSES AGAINST FAMILY: Elder Abuse", "BURGLARY, RESIDENCE: Night,
Attempt"), `address`, and a `mapping_location` geopoint. Max(incident_date)
confirmed = 2026-08-08, about 5 weeks before this build — real and
current, not decade-old dummy records mixed in near the top.
(`t8p9-gb8j`/`ujc2-ki8d` are the same current-year data pre-aggregated by
type/date rather than row-level, and `cfmx-tb5w` is an explicitly
historical 2005-2021 LASD archive — neither used here.)

No personal-identifier fields present in this schema (no name/race/sex/
age fields at all) — served by the LA County Sheriff's West Hollywood
station as a public CrimeWatch-style extract. `incident_id` confirmed
non-null and usable as the external id.
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

WEST_HOLLYWOOD_CA_CRIME_URL = "https://data.weho.org/resource/awjs-gawv.json"
SOURCE_WEST_HOLLYWOOD_CA_CRIME = "west_hollywood_ca_crime"
CITY_NAME = "West Hollywood, CA"


def _summarize(record: dict) -> str:
    category = clean_field(record.get("category"), "an incident")
    stat_desc = clean_field(record.get("stat_desc"))
    address = clean_field(record.get("address"), "an unspecified location")
    date = clean_field(record.get("incident_date"))
    date = date[:10] if date else "an unknown date"

    detail = f" ({stat_desc})" if stat_desc and stat_desc.lower() != category.lower() else ""
    return f"{CITY_NAME} crime report: {category.title()}{detail} near {address}, on {date}."


async def sync_west_hollywood_ca_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(
        WEST_HOLLYWOOD_CA_CRIME_URL,
        limit,
        params={
            "$order": "incident_date DESC",
            "$select": "incident_id,incident_date,category,stat_desc,address",
        },
    )
    return await sync_dataset(
        session,
        records,
        SOURCE_WEST_HOLLYWOOD_CA_CRIME,
        CITY_NAME,
        "incident_id",
        _summarize,
    )
