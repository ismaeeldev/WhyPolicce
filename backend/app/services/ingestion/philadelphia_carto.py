"""Philadelphia Open Data (CartoDB SQL API) ingestion — plan.md Step 9
Phase 1.

Unlike every other city in this package (all Socrata SODA API), Philly's
"Crime Incidents" dataset is served via CartoDB's SQL-over-HTTP API
(`phl.carto.com/api/v2/sql?q=...`) — confirmed live via a real request
during this build, not assumed from research. This module has its own
fetch function rather than reusing `fetch_socrata_json`, since the query
shape (a raw SQL string, not `$limit`/`$order` params) is genuinely
different, not just a cosmetic naming difference.

Found live: an unfiltered query's first row can be a real result row with
every field `null` — filtering `WHERE dc_key IS NOT NULL` is required to
avoid feeding a completely empty record into the summarizer.
"""

import logging

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import (
    DEFAULT_FETCH_LIMIT,
    clean_field,
    sync_dataset,
)

logger = logging.getLogger(__name__)

PHILADELPHIA_SQL_URL = "https://phl.carto.com/api/v2/sql"
SOURCE_PHILADELPHIA_INCIDENTS = "philadelphia_incidents"
CITY_NAME = "Philadelphia"

_QUERY_TEMPLATE = (
    "SELECT dc_key, dispatch_date, text_general_code, location_block, dc_dist "
    "FROM incidents_part1_part2 "
    "WHERE dc_key IS NOT NULL "
    "ORDER BY dispatch_date DESC "
    "LIMIT {limit}"
)


async def _fetch_philadelphia_records(limit: int) -> list[dict]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(PHILADELPHIA_SQL_URL, params={"q": _QUERY_TEMPLATE.format(limit=limit)})
        response.raise_for_status()
        return response.json().get("rows", [])


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("text_general_code"), "an incident")
    location_block = clean_field(record.get("location_block"), "an unspecified location")
    district = clean_field(record.get("dc_dist"), "unknown")
    date = clean_field(record.get("dispatch_date"), "an unknown date")

    # See austin_socrata.py's identical comment: city name must be in the
    # embedded summary text, not just the DB column.
    parts = [
        f"{CITY_NAME} crime incident: {offense}",
        f"near {location_block}, district {district}, on {date}.",
    ]
    return " ".join(p for p in parts if p.strip())


async def sync_philadelphia_incidents(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_philadelphia_records(limit)
    # dc_key arrives as a number (CartoDB's numeric pgtype), not a string —
    # sync_dataset's id_field lookup just needs a truthy value, and
    # str()-ifies it before storing, so passing the raw numeric key through
    # is fine; called out explicitly since every other city's id field is
    # already a string and this is the one exception.
    return await sync_dataset(session, records, SOURCE_PHILADELPHIA_INCIDENTS, CITY_NAME, "dc_key", _summarize)
