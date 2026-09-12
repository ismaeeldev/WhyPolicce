"""Phoenix Open Data (CKAN, full-CSV-download) ingestion — plan.md Step 9
Phase 2.

**Real, confirmed, city-acknowledged data gap (not a bug in this code):**
Phoenix's "Adult Arrests" dataset's own notes field states: "Updates to
this dataset are currently unavailable beginning January 1, 2026. The
city is transitioning from SRS to NIBRS." Directly confirmed via this
module's actual fetch (not a stale cached read — re-verified live): the
crime-data CSV's real trailing window covers 2025-09-11 through
2025-12-31 — genuinely matching the city's own "through Dec 31, 2025"
claim, but roughly 8+ months stale relative to any date after that,
since the city has publicly paused updates. No alternate live Phoenix
source was found (checked the city's other open-data packages, ArcGIS
Online's public catalog, and the police department's own site; none had
anything more current than this same underlying gap).

Ingested anyway per explicit product decision (2026-09-08): real
historical data through Dec 2025 is more useful than nothing, but this is
NOT live/current data the way every other Phase 1/2 city's source is —
`STALE_DATA_WARNING` documents this so callers (and, ideally, the product
itself) can surface it honestly rather than imply Phoenix has the same
freshness as Chicago, Seattle, Denver, etc.
"""

import csv
import logging

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

PHOENIX_PACKAGE_API = "https://www.phoenixopendata.com/api/3/action/package_show"
PHOENIX_PACKAGE_ID = "crime-data"
SOURCE_PHOENIX_CRIME = "phoenix_crime"
CITY_NAME = "Phoenix"

DEFAULT_KEEP_RECENT = 200

# See module docstring — real, confirmed via direct download, not assumed.
STALE_DATA_WARNING = (
    "Phoenix's official open-data source has not been updated since "
    "2025-12-31 (city's own stated reason: an SRS-to-NIBRS reporting "
    "migration paused updates from 2026-01-01 onward) — treat any "
    "Phoenix result as historical, not current."
)


def _resolve_csv_url() -> str:
    with httpx.Client(timeout=30.0) as client:
        response = client.get(PHOENIX_PACKAGE_API, params={"id": PHOENIX_PACKAGE_ID})
        response.raise_for_status()
        data = response.json()
    for resource in data["result"]["resources"]:
        if resource.get("format", "").upper() == "CSV":
            return resource["url"]
    raise RuntimeError(f"Phoenix: no CSV resource found for package {PHOENIX_PACKAGE_ID!r}")


async def _fetch_recent_records(keep_recent: int) -> list[dict]:
    """Unlike San Antonio's file, Phoenix's crime-data CSV IS sorted
    ascending by OCCURRED ON (confirmed directly: tail of the file is the
    latest real date, 2025-12-31, matching the file's OWN trailing window
    confirmed directly via this exact function) — so the last
    `keep_recent` rows are genuinely the most recent ones, no
    heap/full-parse needed. Still streamed rather than loaded whole (the
    file is ~416k rows / tens of MB), keeping only a bounded trailing
    window in memory."""
    from collections import deque

    csv_url = _resolve_csv_url()
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
                reader = csv.reader(lines)
                for row in reader:
                    if header is None:
                        header = row
                        continue
                    if len(row) != len(header):
                        continue
                    window.append(dict(zip(header, row)))

    return list(window)


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("UCR CRIME CATEGORY"), "an incident")
    block = clean_field(record.get("100 BLOCK ADDR"), "an unspecified location")
    premise = clean_field(record.get("PREMISE TYPE"))
    raw_date = clean_field(record.get("OCCURRED ON"))
    date = raw_date.split(" ")[0] if raw_date else "an unknown date"

    # Real bug found and fixed during a client-satisfaction test batch
    # (plan.md "Test similar client questions"): this used to literally
    # embed the TEXT "see STALE_DATA_WARNING" — a Python constant NAME,
    # not its actual message — into the retrieved-record text the model
    # sees. Confirmed live this happened to not cause a visible problem
    # (the model correctly inferred staleness from the dates themselves,
    # not this text), but relying on that inference working every time
    # was a real, unnecessary risk rather than telling the model the
    # actual reason plainly. Now embeds STALE_DATA_WARNING's real content.
    parts = [
        f"{CITY_NAME} crime report (NOTE: {STALE_DATA_WARNING}): {offense}",
        f"near {block}, on {date}.",
    ]
    if premise:
        parts.append(f"Premise type: {premise}.")
    return " ".join(p for p in parts if p.strip())


async def sync_phoenix_crime(session: Session, limit: int = DEFAULT_KEEP_RECENT) -> dict:
    records = await _fetch_recent_records(limit)
    return await sync_dataset(session, records, SOURCE_PHOENIX_CRIME, CITY_NAME, "INC NUMBER", _summarize)
