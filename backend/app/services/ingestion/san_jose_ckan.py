"""San Jose Open Data (CKAN, per-year-CSV-download) ingestion — plan.md
Step 9 Phase 4.

Endpoint confirmed live via a real request during this build:
https://data.sanjoseca.gov, dataset `police-calls-for-service`, with a
SEPARATE CSV resource per calendar year (2016-2026) rather than one
all-history file — the 2026 resource was last modified TODAY
(2026-09-08) during this build, genuinely current.

Confirmed live (unlike San Antonio's file): this dataset's rows ARE
sorted ascending by REPORT_DATE (verified directly: first row 2026-01-01,
last row 2026-08-07, sampled monotonic check passed) — so the same
trailing-window streaming approach as phoenix_ckan.py applies (keep only
the last N rows seen), not San Antonio's heap-based unsorted approach.
"""

import logging
from collections import deque

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

SAN_JOSE_PACKAGE_API = "https://data.sanjoseca.gov/api/3/action/package_show"
SAN_JOSE_PACKAGE_ID = "police-calls-for-service"
SOURCE_SAN_JOSE_CALLS = "san_jose_calls"
CITY_NAME = "San Jose"

DEFAULT_KEEP_RECENT = 200

_METADATA_RETRY_ATTEMPTS = 3
_METADATA_RETRY_DELAY_SECONDS = 2


def _resolve_current_year_csv_url() -> str:
    """Resolves the CSV resource for the CURRENT calendar year specifically
    — this dataset publishes one resource per year (unlike every other
    city module here), so picking the wrong one would mean fetching a
    prior year's already-closed data instead of the live, growing 2026
    file. Matches the resource whose name contains the current year,
    same retry discipline as san_antonio_ckan.py's metadata call (a real,
    confirmed flaky endpoint pattern for CKAN package_show calls in this
    project, not hypothetical)."""
    import time
    from datetime import datetime, timezone

    current_year = str(datetime.now(timezone.utc).year)
    last_error: Exception | None = None
    for attempt in range(_METADATA_RETRY_ATTEMPTS):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(SAN_JOSE_PACKAGE_API, params={"id": SAN_JOSE_PACKAGE_ID})
                response.raise_for_status()
                data = response.json()
            candidates = [
                r for r in data["result"]["resources"]
                if r.get("format", "").upper() == "CSV" and current_year in r.get("name", "")
            ]
            if not candidates:
                raise RuntimeError(f"San Jose: no CSV resource found for year {current_year}")
            return candidates[0]["url"]
        except httpx.TransportError as exc:
            last_error = exc
            logger.warning(
                "san_jose_ckan: package_show attempt %d/%d failed (%s), retrying",
                attempt + 1,
                _METADATA_RETRY_ATTEMPTS,
                exc,
            )
            if attempt < _METADATA_RETRY_ATTEMPTS - 1:
                time.sleep(_METADATA_RETRY_DELAY_SECONDS)
    raise RuntimeError(f"San Jose: package_show failed after {_METADATA_RETRY_ATTEMPTS} attempts") from last_error


async def _fetch_recent_records(keep_recent: int) -> list[dict]:
    csv_url = _resolve_current_year_csv_url()
    window: deque[dict] = deque(maxlen=keep_recent)

    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        async with client.stream("GET", csv_url) as response:
            response.raise_for_status()
            buffer = ""
            header: list[str] | None = None
            async for chunk in response.aiter_text():
                buffer += chunk
                *lines, buffer = buffer.split("\n")
                if not lines:
                    continue
                import csv as csv_module

                reader = csv_module.reader(lines)
                for row in reader:
                    if header is None:
                        header = row
                        continue
                    if len(row) != len(header):
                        continue
                    window.append(dict(zip(header, row)))

    return list(window)


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("CALL_TYPE"), "an incident")
    address = clean_field(record.get("ADDRESS"), "an unspecified location")
    date = clean_field(record.get("OFFENSE_DATE"), "an unknown date")
    disposition = clean_field(record.get("FINAL_DISPO"))
    priority = clean_field(record.get("PRIORITY"))

    parts = [
        f"{CITY_NAME} police call: {offense.title()}",
        f"near {address.strip()}, on {date}.",
    ]
    if priority:
        parts.append(f"Priority: {priority}.")
    if disposition:
        parts.append(f"Disposition: {disposition}.")
    return " ".join(p for p in parts if p.strip())


async def sync_san_jose_calls(session: Session, limit: int = DEFAULT_KEEP_RECENT) -> dict:
    records = await _fetch_recent_records(limit)
    return await sync_dataset(session, records, SOURCE_SAN_JOSE_CALLS, CITY_NAME, "EID", _summarize)
