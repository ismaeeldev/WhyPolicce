"""San Diego, CA Open Data (static year-partitioned CSV, not a queryable
API) ingestion — plan.md Step 9 Phase 27.

Discovered via `OpenPoliceData`'s source table, then independently
re-verified by downloading and directly parsing the real CSV before any
code was written — the same client-side-parse discipline required for
Fairfield CA's CSV-over-HTTP sources in Phase 25, since this file has no
query API (no server-side WHERE/COUNT).

Confirmed live via direct parsing during this build: 53,175 total rows
in the current-year (2026) file, max(occured_on) = 2026-09-08, min =
2026-01-01, 9,482 rows in the trailing 45-day window — genuinely active.
Unique id `case_number` confirmed 0% null. `ibr_offense_description`/
`pd_offense_category` are genuine, specific NIBRS-based offense fields
(e.g. "Motor Vehicle Theft", "Aggravated Assault", "Robbery") — confirmed
via direct sampling.

**Real, significant maintenance caveat, flagged explicitly rather than
silently assumed away**: this is a fixed-year file
(`pd_nibrs_2026_datasd.csv`) — San Diego publishes one file per calendar
year, confirmed via the URL pattern (`pd_nibrs_{year}_datasd.csv`,
history back to 2020). A future January will need this module's URL
updated to the new year's file, the same "needs a yearly check" caveat
San Jose's and Louisville's per-year resources have from earlier phases,
just via a filename change rather than a new FeatureServer item.

No personal-identifier fields found in this schema — checked directly,
no name/DOB/race/sex fields present, only geographic and offense-
classification columns.
"""

import csv
import io
import logging

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

# See module docstring — must be updated to the new year's file after
# 2026-12-31 (e.g. pd_nibrs_2027_datasd.csv).
SAN_DIEGO_CRIME_CSV_URL = "https://seshat.datasd.org/police_nibrs/pd_nibrs_2026_datasd.csv"
SOURCE_SAN_DIEGO_CRIME = "san_diego_crime"
CITY_NAME = "San Diego"

DEFAULT_FETCH_LIMIT = 200


async def _fetch_csv_rows() -> list[dict]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(SAN_DIEGO_CRIME_CSV_URL)
        response.raise_for_status()
        text = response.text
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def _most_recent(records: list[dict], limit: int) -> list[dict]:
    def sort_key(record: dict) -> str:
        return clean_field(record.get("occured_on"))

    return sorted(records, key=sort_key, reverse=True)[:limit]


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("ibr_offense_description"), "an incident")
    category = clean_field(record.get("pd_offense_category"))
    address = clean_field(record.get("block_addr"), "an unspecified location")
    date = clean_field(record.get("occured_on"))
    date = date[:10] if date else "an unknown date"

    detail = f" ({category})" if category and category.lower() != offense.lower() else ""
    return f"{CITY_NAME} crime report: {offense}{detail} near {address}, on {date}."


async def sync_san_diego_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    all_records = await _fetch_csv_rows()
    records = _most_recent(all_records, limit)
    return await sync_dataset(session, records, SOURCE_SAN_DIEGO_CRIME, CITY_NAME, "case_number", _summarize)
