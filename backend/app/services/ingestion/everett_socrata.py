"""Everett, WA Open Data (Socrata) ingestion — plan.md Step 9 Phase 17.

Confirmed live via real server-side queries during this build: 1,604,823
total rows, ~11.7 years of real history (min date 2015-01-01), 16,170
rows in the trailing 45-day window — genuinely active, one of the
largest single datasets integrated so far. Unique id `eventnumber`
confirmed 0% null. One anomalous future-dated row (max(datetimereceived)
= 2026-12-20, ahead of "today" 2026-09-09) was found and confirmed to be
a single data-entry outlier, not a real freshness signal — excluding
that one row, real current data runs through 2026-09-07/08.

This is Calls for Service (CAD/dispatch-level events), same caveat as
New Orleans/Virginia Beach's CFS datasets in earlier phases — genuinely
useful and fully live, but a different granularity than a pure
offense-classification dataset; no dedicated NIBRS offense-code field
exists. `incidenttype` (e.g. "SUSPICIOUS EVENT", "BURGLARY", "ASSAULT",
"ACTIVE SHOOTER") is the real category field, confirmed via direct
sampling. `eventaddressby100block` is already pre-generalized to the
100-block by the source itself (e.g. "20XX COLBY AVE") — no exact
addresses. `disposition` used as a disposition field. No
personal-identifier fields found in this schema.
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

EVERETT_CALLS_URL = "https://data.everettwa.gov/resource/f6vp-3svh.json"
SOURCE_EVERETT_CALLS = "everett_calls"
CITY_NAME = "Everett"


def _summarize(record: dict) -> str:
    incident_type = clean_field(record.get("incidenttype"), "an incident")
    address = clean_field(record.get("eventaddressby100block"), "an unspecified location")
    neighborhood = clean_field(record.get("neighborhood"))
    date = clean_field(record.get("datetimereceived"))
    date = date[:10] if date else "an unknown date"
    disposition = clean_field(record.get("disposition"))

    parts = [
        f"{CITY_NAME} police call: {incident_type.title()}",
        f"near {address}"
        + (f" ({neighborhood})" if neighborhood else "")
        + f", on {date}.",
    ]
    if disposition:
        parts.append(f"Disposition: {disposition.title()}.")
    return " ".join(p for p in parts if p.strip())


async def sync_everett_calls(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    # Excludes the one confirmed future-dated (2026-12-20) outlier row so
    # a naive "most recent" fetch doesn't surface that anomaly as if it
    # were genuinely current data.
    records = await fetch_socrata_json(
        EVERETT_CALLS_URL,
        limit,
        params={
            "$order": "datetimereceived DESC",
            "$where": "datetimereceived < '2026-09-10'",
        },
    )
    return await sync_dataset(session, records, SOURCE_EVERETT_CALLS, CITY_NAME, "eventnumber", _summarize)
