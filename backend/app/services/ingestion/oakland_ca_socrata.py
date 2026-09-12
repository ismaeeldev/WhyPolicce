"""Oakland, CA Open Data (Socrata) ingestion — plan.md Step 9 Phase 33.

Discovered via fresh manual web research (Socrata catalog search), not
`OpenPoliceData`'s source table (confirmed exhausted as of Phase 32) —
per this phase's mandate to search beyond that library's known sources.

**Real dataset-selection finding**: `data.oaklandca.gov` hosts several
similarly-named "crime" datasets, most of which are dead/empty Socrata
views (confirmed live: `isdi-c2m6` "Oakland Crime Incident Data (past 90
days)" and `mrwt-jswm` "Oakland Crime Incidents Map (last 90 days)" both
return rows with zero columns — `[{}, {}, {}]` — despite fresh-looking
catalog metadata timestamps, a different but equally real failure mode
from the Morrisville/Portland "stale/dummy data" pattern: here the
metadata timestamp is fresh but the dataset itself is structurally
empty). The genuinely live one is `ym6k-rx7a` ("CrimeWatch Maps Past
90-Days") — confirmed via direct query: real rows with `crimetype`,
`casenumber`, `description`, `address`, `city`, and a `location_1`
geopoint, max(datetime) = 2026-09-10 (one day before this build).

No personal-identifier fields present in this schema at all — no
race/sex/age/name fields exist on this dataset (a structural side effect
of it being a public CrimeWatch map extract). `casenumber` is confirmed
non-null and usable as the external id, though (same pattern as Seattle/
Cambridge) one case can have multiple offense rows sharing a casenumber
— handled by socrata_base.py's existing per-batch dedup.
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

OAKLAND_CA_CRIME_URL = "https://data.oaklandca.gov/resource/ym6k-rx7a.json"
SOURCE_OAKLAND_CA_CRIME = "oakland_ca_crime"
CITY_NAME = "Oakland, CA"


def _summarize(record: dict) -> str:
    crime_type = clean_field(record.get("crimetype"), "an incident")
    description = clean_field(record.get("description"))
    address = clean_field(record.get("address"), "an unspecified location")
    date = clean_field(record.get("datetime"))
    date = date[:10] if date else "an unknown date"

    detail = f" ({description})" if description and description.lower() != crime_type.lower() else ""
    return f"{CITY_NAME} crime report: {crime_type.title()}{detail} near {address}, on {date}."


async def sync_oakland_ca_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(
        OAKLAND_CA_CRIME_URL,
        limit,
        params={
            "$order": "datetime DESC",
            "$select": "casenumber,datetime,crimetype,description,address,city",
        },
    )
    return await sync_dataset(
        session, records, SOURCE_OAKLAND_CA_CRIME, CITY_NAME, "casenumber", _summarize
    )
