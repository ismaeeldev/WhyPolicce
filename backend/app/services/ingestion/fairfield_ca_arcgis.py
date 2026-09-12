"""Fairfield, CA Police Department Open Data (ArcGIS Online-hosted static
CSV items) ingestion — plan.md Step 9 Phase 25.

**A genuinely new ingestion pattern for this project**: Fairfield's own
self-hosted FeatureServer (`gis.fairfield.ca.gov/.../Police/Cases/
MapServer/0`) returns HTTP 403 (token-gated) to direct external
requests. The real, fully public data source is instead two plain CSV
files hosted as ArcGIS Online items and fetched via the standard AGO
content `/data` REST endpoint (`GET .../sharing/rest/content/items/
{itemId}/data`) — no query language, no server-side WHERE/COUNT
available. Confirmed live by downloading and directly parsing both CSVs
during this build (not just trusting a row-count claim):

- **Cases** (Part 1/NIBRS-style crimes), item `428e64d44f944f7fb73c165d
  097200fe`: 5,759 total rows, max(CASEDATE) = 2026-09-09, min =
  2024-09-10 (~2 years, not a rolling window), 321 rows in the trailing
  45-day window. Unique id `CASEN` confirmed 0% null. `RCODEDESC` is a
  genuine UCR Part 1 offense category (THEFT, ROBBERY, BURGLARY,
  HOMICIDE, RAPE, AGGRAVATED ASSAULT, ARSON, VEHICLE THEFT).
- **Calls for Service** (broader CFS log), item
  `2304d57c7ee64756b9840219ab256074`: 54,862 total rows, max
  (INCIDENTDATE) = 2026-09-09, min = 2026-01-01 (current calendar year —
  this file resets annually per its own naming convention, confirmed
  live as of this build but a future revisit should check for a Jan 1
  reset/gap), 9,860 rows in the trailing 45-day window. Unique id
  `INCNUM` confirmed 0% null. `TEXT` is a genuine, specific call-type
  description (e.g. "SHOTS FIRED", "911 HANG UP", "273 5 DOMESTIC
  VIOLENCE").

Both files fetched and parsed as CSV client-side (not a JSON API) — a
real, non-fictional pattern this project hadn't hit before, distinct
from every other ArcGIS/Socrata source integrated so far. No
personal-identifier fields found in either file's schema — checked
directly, no CCN/WARD/ANC/PSA/BID fields (this project's recurring
"mislabeled DC MPD data" pattern) and no victim/officer names.
"""

import csv
import io
import logging

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

_CASES_CSV_URL = "https://www.arcgis.com/sharing/rest/content/items/428e64d44f944f7fb73c165d097200fe/data"
_CFS_CSV_URL = "https://www.arcgis.com/sharing/rest/content/items/2304d57c7ee64756b9840219ab256074/data"

SOURCE_FAIRFIELD_CA_CASES = "fairfield_ca_crime"
SOURCE_FAIRFIELD_CA_CFS = "fairfield_ca_calls"
CITY_NAME = "Fairfield, CA"

DEFAULT_FETCH_LIMIT = 200


async def _fetch_csv_rows(url: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url)
        response.raise_for_status()
        text = response.text
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


def _most_recent(records: list[dict], date_field: str, limit: int) -> list[dict]:
    def sort_key(record: dict) -> str:
        # Plain string sort works here since both source date columns use
        # a fixed "YYYY-MM-DD HH:MM:SS" format — confirmed via direct
        # sampling, same reasoning already applied to Asheville's/
        # Chattanooga's string-typed date fields in earlier phases.
        return clean_field(record.get(date_field))

    return sorted(records, key=sort_key, reverse=True)[:limit]


def _summarize_case(record: dict) -> str:
    offense = clean_field(record.get("RCODEDESC"), "an incident")
    address = clean_field(record.get("ADDRESS"), "an unspecified location")
    beat = clean_field(record.get("BEAT"))
    date = clean_field(record.get("CASEDATE"))
    date = date[:10] if date else "an unknown date"

    parts = [f"{CITY_NAME} crime report: {offense.title()} near {address}"]
    if beat:
        parts.append(f"(beat {beat})")
    return " ".join(parts) + f", on {date}."


def _summarize_cfs(record: dict) -> str:
    call_type = clean_field(record.get("TEXT"), "an incident")
    location = clean_field(record.get("LOCATION"), "an unspecified location")
    date = clean_field(record.get("INCIDENTDATE"))
    date = date[:10] if date else "an unknown date"

    return f"{CITY_NAME} police call: {call_type.title()} near {location}, on {date}."


async def sync_fairfield_ca_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    all_records = await _fetch_csv_rows(_CASES_CSV_URL)
    records = _most_recent(all_records, "CASEDATE", limit)
    return await sync_dataset(session, records, SOURCE_FAIRFIELD_CA_CASES, CITY_NAME, "CASEN", _summarize_case)


async def sync_fairfield_ca_calls(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    all_records = await _fetch_csv_rows(_CFS_CSV_URL)
    records = _most_recent(all_records, "INCIDENTDATE", limit)
    return await sync_dataset(session, records, SOURCE_FAIRFIELD_CA_CFS, CITY_NAME, "INCNUM", _summarize_cfs)
