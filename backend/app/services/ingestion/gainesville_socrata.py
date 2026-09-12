"""Gainesville, FL Open Data (Socrata, "dataGNV") ingestion — plan.md
Step 9 Phase 24.

Confirmed live via real server-side queries during this build: 233,678
total rows, max(offense_date) = 2026-09-07 (3 days before this build),
1,244 rows in the trailing 45-day window — genuinely active, real
long-tail history (min date 1976-01-01). Unique id `id` confirmed 0%
null.

`narrative` is the real, specific offense-classification field despite
its name suggesting free-text detail — confirmed via direct sampling to
hold genuine classified offense categories (e.g. "Domestic Assault",
"Aggravated Battery", "Armed Burglary of a Dwelling or Structure",
"Arson"), not a narrative/notes field with unreviewed free text. Address
is already block-level from the source itself (e.g. "5800 BLK NW 23RD
TER"). No disposition field present. No personal-identifier fields found
in this schema — checked directly, no CCN/WARD/ANC/PSA/BID fields (this
project's recurring "mislabeled DC MPD data" pattern) and no victim/
officer names.
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

GAINESVILLE_CRIME_URL = "https://data.cityofgainesville.org/resource/gvua-xt9q.json"
SOURCE_GAINESVILLE_CRIME = "gainesville_crime"
CITY_NAME = "Gainesville"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("narrative"), "an incident")
    address = clean_field(record.get("address"), "an unspecified location")
    date = clean_field(record.get("offense_date"))
    date = date[:10] if date else "an unknown date"

    return f"{CITY_NAME} crime report: {offense} near {address}, on {date}."


async def sync_gainesville_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(
        GAINESVILLE_CRIME_URL,
        limit,
        params={
            "$order": "offense_date DESC",
            "$select": "id,narrative,address,offense_date",
        },
    )
    return await sync_dataset(session, records, SOURCE_GAINESVILLE_CRIME, CITY_NAME, "id", _summarize)
