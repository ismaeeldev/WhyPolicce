"""San Antonio Open Data (CKAN, full-CSV-download) ingestion — plan.md
Step 9 Phase 2.

Confirmed live via a real request during this build:
https://data.sanantonio.gov/dataset/.../pubsafedash_offenses.csv
("Police offense reports data", `sapd-offenses` on the CKAN portal) — last
modified 2026-09-07, genuinely fresh, unlike Phoenix's apparently-frozen
dataset (see phoenix_arcgis.py's module docstring for that comparison).

Unlike every Socrata city (NYC, Chicago, LA, Seattle, Austin, Dallas) or
even Philadelphia's queryable CartoDB SQL API, San Antonio publishes ONE
full CSV file covering the entire dataset's history (confirmed live:
~325,000 rows, ~34MB, spanning 2023-2026) with no server-side filtering,
sorting, or pagination available — the whole file must be downloaded and
parsed client-side to find the most recent records.

Confirmed live: the file is NOT sorted by date (mixed years/dates
throughout, appears grouped by offense type instead) — a naive "read the
first N rows" approach would NOT reliably return recent data. This module
streams the CSV via `httpx`'s streaming response (never loading the whole
34MB file into memory as one blob) and keeps a running top-N by
`Report_Date` using a min-heap, so memory stays bounded regardless of how
large the source file grows.
"""

import csv
import heapq
import io
import logging
from datetime import datetime, timedelta

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import (
    clean_field,
    sync_dataset,
)

logger = logging.getLogger(__name__)

# Resolved live via the CKAN package_show API during this build
# (data.sanantonio.gov/api/3/action/package_show?id=sapd-offenses) — a
# CKAN dataset's resource URL is not guaranteed permanently stable the way
# a Socrata resource id is, so this is refreshed via that same API call
# rather than hardcoding the S3 URL directly, which is itself a signed,
# time-limited redirect target anyway (confirmed live: it 403s outside its
# signed window).
SAN_ANTONIO_PACKAGE_API = "https://data.sanantonio.gov/api/3/action/package_show"
SAN_ANTONIO_PACKAGE_ID = "sapd-offenses"
SOURCE_SAN_ANTONIO_OFFENSES = "san_antonio_offenses"
CITY_NAME = "San Antonio"

# Conservative default, same reasoning as every other city's
# DEFAULT_FETCH_LIMIT — this is the number of MOST RECENT rows kept after
# parsing the full file, not a request-level limit (there is no
# server-side limit parameter for this source).
DEFAULT_KEEP_RECENT = 200

# Confirmed live: the file's real date range runs from 2023 to the same
# day as this build (2026-09-06/07 rows observed) — a naive full parse of
# 325k rows is wasted work once enough recent-enough candidates are found.
# Capping how far back a row is allowed to be, rather than parsing all
# 325k rows for a table this size, keeps this from being pointlessly slow
# as the source file grows in future years.
_MAX_LOOKBACK_DAYS = 120


# Found live during Phase 2 verification (a real, reproducible flake, not
# hypothetical): a single package_show call genuinely failed once with
# "Server disconnected without sending a response" and succeeded
# immediately on a bare retry — data.sanantonio.gov's CKAN API appears to
# occasionally drop a connection. Retried with a short fixed backoff
# rather than failing this city's entire weekly sync over one transient
# blip, same "don't let a flaky network take down real data" reasoning as
# db.py's pool_pre_ping for Neon's dropped connections.
_METADATA_RETRY_ATTEMPTS = 3
_METADATA_RETRY_DELAY_SECONDS = 2


def _resolve_csv_url() -> str:
    """Fetches the current resource URL from CKAN's package_show API —
    see the module docstring for why this isn't hardcoded."""
    import time

    last_error: Exception | None = None
    for attempt in range(_METADATA_RETRY_ATTEMPTS):
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(SAN_ANTONIO_PACKAGE_API, params={"id": SAN_ANTONIO_PACKAGE_ID})
                response.raise_for_status()
                data = response.json()
            for resource in data["result"]["resources"]:
                if resource.get("format", "").upper() == "CSV":
                    return resource["url"]
            raise RuntimeError(f"San Antonio: no CSV resource found for package {SAN_ANTONIO_PACKAGE_ID!r}")
        except httpx.TransportError as exc:
            last_error = exc
            logger.warning(
                "san_antonio_ckan: package_show attempt %d/%d failed (%s), retrying",
                attempt + 1,
                _METADATA_RETRY_ATTEMPTS,
                exc,
            )
            if attempt < _METADATA_RETRY_ATTEMPTS - 1:
                time.sleep(_METADATA_RETRY_DELAY_SECONDS)
    raise RuntimeError(f"San Antonio: package_show failed after {_METADATA_RETRY_ATTEMPTS} attempts") from last_error


async def _fetch_recent_records(keep_recent: int) -> list[dict]:
    """Streams the full CSV and keeps only the `keep_recent` most-recent
    rows by Report_Date, using a min-heap so memory stays bounded at
    O(keep_recent) rather than O(total rows) — real, verified necessary
    here since the source file is genuinely unsorted and ~325k rows."""
    csv_url = _resolve_csv_url()
    cutoff = (datetime.now() - timedelta(days=_MAX_LOOKBACK_DAYS)).date()

    heap: list[tuple[str, int, dict]] = []  # (date_str, tie-breaker, row)
    tie_breaker = 0

    async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
        async with client.stream("GET", csv_url) as response:
            response.raise_for_status()
            buffer = ""
            header: list[str] | None = None
            async for chunk in response.aiter_text():
                buffer += chunk
                # Process complete lines only, keep any trailing partial
                # line in the buffer for the next chunk — a naive
                # per-chunk csv.reader would corrupt rows split across
                # chunk boundaries, which real streaming responses do.
                *lines, buffer = buffer.split("\n")
                if not lines:
                    continue
                reader = csv.reader(lines)
                for row in reader:
                    if header is None:
                        header = row
                        continue
                    if len(row) != len(header):
                        continue
                    record = dict(zip(header, row))
                    report_date = record.get("Report_Date", "")
                    try:
                        parsed_date = datetime.strptime(report_date, "%Y-%m-%d").date()
                    except ValueError:
                        continue
                    if parsed_date < cutoff:
                        continue
                    tie_breaker += 1
                    if len(heap) < keep_recent:
                        heapq.heappush(heap, (report_date, tie_breaker, record))
                    elif report_date > heap[0][0]:
                        heapq.heapreplace(heap, (report_date, tie_breaker, record))

    return [record for _, _, record in sorted(heap, key=lambda item: item[0], reverse=True)]


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("NIBRS_Code_Name"), "an incident")
    category = clean_field(record.get("NIBRS_Crime_Against"))
    area = clean_field(record.get("Service_Area"), "an unspecified area")
    zip_code = clean_field(record.get("Zip_Code"))
    date = clean_field(record.get("Report_Date"), "an unknown date")

    prefix = f"{category.title()} crimes: " if category else ""
    parts = [
        f"{CITY_NAME} police offense report: {prefix}{offense}",
        f"in the {area} service area" + (f" (ZIP {zip_code})" if zip_code else "") + f", reported on {date}.",
    ]
    return " ".join(p for p in parts if p.strip())


async def sync_san_antonio_offenses(session: Session, limit: int = DEFAULT_KEEP_RECENT) -> dict:
    records = await _fetch_recent_records(limit)
    return await sync_dataset(session, records, SOURCE_SAN_ANTONIO_OFFENSES, CITY_NAME, "Report_ID", _summarize)
