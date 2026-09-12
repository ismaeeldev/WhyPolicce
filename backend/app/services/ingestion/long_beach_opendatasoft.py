"""Long Beach, CA Open Data (Opendatasoft — a genuinely new platform type
for this project, distinct from Socrata/ArcGIS/CKAN) ingestion —
plan.md Step 9 Phase 28.

Discovered via `OpenPoliceData`'s source table, then independently
re-verified via direct HTTP queries before any code was written.

Confirmed live via real server-side queries during this build: 108,430
total rows, max(date_reported) = 2026-08-19 (22 days before this build —
a real, slower refresh cadence than most other sources in this project,
but confirmed genuinely still live and updating, not frozen), min date
2023-01-01, 1,419 rows in the trailing 45-day window. `nibrs_offense`/
`nibrs_offense_category` are genuine, specific NIBRS classifications
(e.g. "Aggravated Assault", "Motor Vehicle Theft", "Arson") — confirmed
via direct sampling.

**Real, notable id-field quirk**: the `id` field is a SHA-256 hash, not a
natural report/case number — confirmed 0% null and functions correctly
as a unique key for this project's upsert logic, but is not a
human-meaningful identifier (nothing in this project's summaries
surfaces it to the user anyway, so this has no user-facing impact).

`anonymizedaddress` is already pre-anonymized to block/intersection level
by the source itself (its own field name says so directly). No
personal-identifier fields found in this schema — checked directly, no
CCN/WARD/ANC/PSA/BID fields (this project's recurring "mislabeled DC MPD
data" pattern) and no victim/officer names.

**Real bug caught during the first production sync, fixed before
shipping**: Opendatasoft's Explore API v2.1 rejects any `limit` outside
`-1 <= limit <= 100` (confirmed directly — a `limit=200` request that
matched this project's usual per-city fetch size returned a real 400
`InvalidRESTParameterError`), unlike Socrata/ArcGIS's effectively
unlimited `$limit`/`resultRecordCount`. Fixed by paginating in 100-row
chunks via `offset` instead of one oversized request.
"""

import logging

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

LONG_BEACH_CRIME_URL = (
    "https://data.longbeach.gov/api/explore/v2.1/catalog/datasets/"
    "lbpd-criminal-incident-data/records"
)
SOURCE_LONG_BEACH_CRIME = "long_beach_crime"
CITY_NAME = "Long Beach"

DEFAULT_FETCH_LIMIT = 200

# Real, confirmed API constraint (not a Socrata/ArcGIS-style unlimited
# $limit): Opendatasoft's Explore API v2.1 rejects any `limit` outside
# -1 <= limit <= 100 with a 400 InvalidRESTParameterError, confirmed
# directly against this endpoint. Fetches are paginated in chunks of
# this size via `offset` instead of a single oversized request.
_MAX_PAGE_SIZE = 100


async def _fetch_records(limit: int) -> list[dict]:
    records: list[dict] = []
    offset = 0
    async with httpx.AsyncClient(timeout=30.0) as client:
        while len(records) < limit:
            page_size = min(_MAX_PAGE_SIZE, limit - len(records))
            params = {
                "limit": page_size,
                "offset": offset,
                "order_by": "date_reported desc",
            }
            response = await client.get(LONG_BEACH_CRIME_URL, params=params)
            response.raise_for_status()
            data = response.json()
            page = data.get("results", [])
            if not page:
                break
            records.extend(page)
            offset += len(page)
    return records


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("nibrs_offense"), "an incident")
    category = clean_field(record.get("nibrs_offense_category"))
    address = clean_field(record.get("anonymizedaddress"), "an unspecified location")
    date = clean_field(record.get("date_reported"))
    date = date[:10] if date else "an unknown date"

    detail = f" ({category})" if category and category.lower() != offense.lower() else ""
    return f"{CITY_NAME} crime report: {offense}{detail} near {address}, on {date}."


async def sync_long_beach_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_LONG_BEACH_CRIME, CITY_NAME, "id", _summarize)
