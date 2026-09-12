"""Cambridge, MA Open Data (Socrata) ingestion — plan.md Step 9 Phase 32.

Discovered via `OpenPoliceData`'s source table (dataset id listed there,
`data.cambridgema.gov`, `date_field=date_of_report`), then independently
re-verified via direct HTTP queries before any code was written, per this
project's standard.

**Real dataset-selection finding**: this domain has TWO plausible
"incidents" datasets. `3gki-wyrb` ("Daily Police Log") looked initially
promising (updates within days, e.g. max date_time 2026-09-07 confirmed
live) but its `description` field contains genuine, unredacted arrestee
full names and ages embedded in free-text narrative (e.g. "Mark Parise,
62, of Cambridge was placed under arrest...", "Weldebruk Hadgu, 43, of
Cambridge was placed under arrest...") — confirmed directly via a live
sample, not a hypothetical. That dataset was REJECTED as an ingestion
source specifically because of this, matching this project's zero-
tolerance stance on real personal identifiers found in free text.

The actual OPD-catalogued INCIDENTS dataset is `xuad-73uj` ("Crime
Reports") — a genuinely different, structured dataset with no narrative
text field at all: `crime` (offense type), `location` (pre-generalized
by the source to ~100-block ranges per its own description), and
`neighborhood`. Confirmed live via direct query: max(date_of_report) =
2026-07-31 (about 6 weeks before this build) — real and current, not
dummy/decade-old data mixed in near the top when sorted descending.

No unique per-row ID field beyond `file_number`, confirmed non-null and
usable as the external id. No victim/officer name fields present in this
schema at all (a structural side effect of it being a generalized
Crime-Reports extract rather than a raw CAD/blotter feed).
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

CAMBRIDGE_MA_CRIME_URL = "https://data.cambridgema.gov/resource/xuad-73uj.json"
SOURCE_CAMBRIDGE_MA_CRIME = "cambridge_ma_incidents"
CITY_NAME = "Cambridge, MA"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("crime"), "an incident")
    location = clean_field(record.get("location"), "an unspecified location")
    date = clean_field(record.get("date_of_report"))
    date = date[:10] if date else "an unknown date"

    return f"{CITY_NAME} crime report: {offense} near {location}, on {date}."


async def sync_cambridge_ma_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(
        CAMBRIDGE_MA_CRIME_URL,
        limit,
        params={
            "$order": "date_of_report DESC",
            "$select": "file_number,date_of_report,crime,location,neighborhood",
        },
    )
    return await sync_dataset(
        session, records, SOURCE_CAMBRIDGE_MA_CRIME, CITY_NAME, "file_number", _summarize
    )
