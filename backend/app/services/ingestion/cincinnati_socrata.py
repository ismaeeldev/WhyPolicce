"""Cincinnati Open Data (Socrata) ingestion — plan.md Step 9 Phase 9.

**Real, significant freshness trap caught during this build, worse than a
simple stale-dataset rejection**: the obvious top hit for "crime incidents"
(`k59e-2pvf`, "PDI Crime Incidents") reports a catalog `data_updated_at` of
today and a `max(date_reported)` of 2026-01-13 — both look fine at a
glance. But a deeper check (real recent-row DENSITY, not just the single
MAX value) found only 1 row after 2026-01-01 and 3 rows total since mid-
2025, out of 538,743 total rows — the dataset is a frozen historical
archive that received one straggler late edit, not a live feed. Portal/
catalog metadata again proven unreliable on its own (same lesson as
Phoenix and Denver's decoy service in earlier phases) — checking a single
MAX()/"last updated" value is NOT sufficient; the real fix is checking how
many rows exist in a recent window.

The genuinely live dataset is `7aqy-xrv9` ("Reported Crime (STARS Category
Offenses) on or after 6/3/2024") — confirmed via the same recent-window
check: 2,643 rows since 2026-08-01, max(datereported) = 2026-09-07 (one day
before this build). 57,886 total rows. Unique id `incident_no` confirmed
0% null. Used here instead of the decoy.

**Real, confirmed schema limitation** (checked via the dataset's own
column catalog, not assumed): despite its name, this resource has no
specific offense-description field. `stars_category`/`type` are only
UCR Part 1/Part 2 classification (i.e. "Part 1" or "Part 2", nothing more
specific), and `clsd` is a case-DISPOSITION code (e.g.
"CLEARED_BY_ARREST_ADULT", "UNFOUNDED"), not an offense name — confirmed
by listing its distinct values, all of which are disposition outcomes.
The summarizer below is written to be honest about this coarseness
(describing "a Part 1 (more serious) incident" rather than fabricating a
specific offense type the data doesn't actually contain) rather than
overstating detail this dataset doesn't have.
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

CINCINNATI_CRIME_URL = "https://data.cincinnati-oh.gov/resource/7aqy-xrv9.json"
SOURCE_CINCINNATI_CRIME = "cincinnati_crime"
CITY_NAME = "Cincinnati"


_STARS_PART_LABELS = {
    "part 1": "a Part 1 (more serious) incident",
    "part 2": "a Part 2 (less serious) incident",
}


def _describe_stars_category(raw: str) -> str:
    return _STARS_PART_LABELS.get(raw.strip().lower(), "an incident")


def _describe_disposition(raw: str) -> str:
    return raw.replace("_", " ").title()


def _summarize(record: dict) -> str:
    stars_category = clean_field(record.get("stars_category"))
    offense = _describe_stars_category(stars_category) if stars_category else "an incident"
    address = clean_field(record.get("address_x"), "an unspecified location")
    neighborhood = clean_field(record.get("cpd_neighborhood"))
    date = clean_field(record.get("datereported"))
    date = date[:10] if date else "an unknown date"
    disposition = clean_field(record.get("clsd"))

    parts = [
        f"{CITY_NAME} crime report: {offense}",
        f"near {address}"
        + (f" ({neighborhood})" if neighborhood else "")
        + f", on {date}.",
    ]
    if disposition:
        parts.append(f"Case status: {_describe_disposition(disposition)}.")
    return " ".join(p for p in parts if p.strip())


async def sync_cincinnati_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(CINCINNATI_CRIME_URL, limit, params={"$order": "datereported DESC"})
    return await sync_dataset(session, records, SOURCE_CINCINNATI_CRIME, CITY_NAME, "incident_no", _summarize)
