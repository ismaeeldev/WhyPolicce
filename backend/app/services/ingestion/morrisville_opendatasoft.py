"""Morrisville, NC Open Data (Opendatasoft v1.0 API — an older API
generation than Long Beach's v2.1 instance from Phase 28) ingestion —
plan.md Step 9 Phase 30.

Discovered via `OpenPoliceData`'s source table, then independently
re-verified via direct HTTP queries before any code was written.

Confirmed live via direct queries during this build: 10,271 total rows,
1,608 rows in calendar year 2026 alone (confirmed via `refine.yearstamp`
faceting), real multi-year history (records back to 2004). Unique id
`inci_id` confirmed 0% null.

**Real, significant API bug found and worked around before shipping**:
this instance's `sort=-date_occu`/`sort=-date_rept` parameters do NOT
correctly sort by actual recency — confirmed directly: requesting the
"most recent" records by either date field surfaced a mix of decade-old
dummy/placeholder-looking rows (sequential test IDs like "99987655",
"date_occu" identical to "date_rept" down to the second) ahead of
genuinely current 2026 records. Sorting by `-inci_id` (the case number,
which increments roughly sequentially within a year, e.g. "26002289" for
a September 2026 incident) surfaces real, current records far more
reliably, though not perfectly monotonically either — so this module
fetches a `refine.yearstamp`-scoped page ordered by `-inci_id` and then
re-sorts the returned batch by the real `date_occu` field client-side,
rather than trusting either the API's own date-sort or a bare id-sort
alone.

`offense` is a genuine, specific offense field (e.g. "LARCENY - FROM
MOTOR VEHICLE (NON FORCED)", "DRUGS - POSS./SELL/MAN./DEL./TRNSPRT/
CULT") — confirmed via direct sampling.

**Real, notable privacy practice found in the source itself, not a bug
to work around**: sensitive offense records (e.g. child molestation,
homicide) have their own location/district fields replaced with the
literal string "<Redacted>" by the source — confirmed directly via a
live sample. This module treats "<Redacted>" as an honest blank via the
shared clean_field-style handling, same as any other missing-value case,
rather than surfacing the literal placeholder text.

`asst_offcr` (present in the raw schema) was checked directly and
confirmed to be a small integer count (e.g. "0", "1", "5"), not an
officer name or identifier — not ingested regardless, since it serves no
purpose in the summary.
"""

import logging

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

_MORRISVILLE_SEARCH_URL = "https://opendata.townofmorrisville.org/api/records/1.0/search/"
_DATASET_ID = "pd_incident_report"

SOURCE_MORRISVILLE_CRIME = "morrisville_crime"
CITY_NAME = "Morrisville"

DEFAULT_FETCH_LIMIT = 200

_REDACTED_MARKER = "<redacted>"


async def _fetch_records(limit: int) -> list[dict]:
    # See module docstring — the API's own date-based sort is unreliable
    # on this instance, so this fetches a wider recent-year slice ordered
    # by -inci_id (a much better, though imperfect, recency proxy) and
    # re-sorts the actual batch by date_occu client-side afterward.
    params = {
        "dataset": _DATASET_ID,
        "rows": min(limit * 2, 500),
        "sort": "-inci_id",
        "refine.yearstamp": "2026",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(_MORRISVILLE_SEARCH_URL, params=params)
        response.raise_for_status()
        data = response.json()
    records = [r["fields"] for r in data.get("records", [])]
    records.sort(key=lambda r: clean_field(r.get("date_occu")), reverse=True)
    return records[:limit]


def _clean_redacted(value) -> str:
    cleaned = clean_field(value)
    return "" if cleaned.lower() == _REDACTED_MARKER else cleaned


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("offense"), "an incident")
    street = _clean_redacted(record.get("street"))
    date = clean_field(record.get("date_occu"))
    date = date[:10] if date else "an unknown date"

    location = street or "an unspecified location"
    return f"{CITY_NAME} crime report: {offense} near {location}, on {date}."


async def sync_morrisville_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_MORRISVILLE_CRIME, CITY_NAME, "inci_id", _summarize)
