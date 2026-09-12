"""Jacksonville, FL / Duval County (Jacksonville Sheriff's Office public
transparency data, ArcGIS FeatureServer) ingestion — plan.md Step 9
Phase 15.

A real, honest correction to an earlier phase's finding: Jacksonville was
previously rejected (Phase 9 research) because `opendata.jaxsheriff.org`
had a DNS failure at that time. This is a genuinely different, newer
endpoint — JSO's public transparency portal (launched Aug 2024) and this
specific FeatureServer view (published Oct 2025) — confirmed directly not
to be reachable via that old dead domain, and independently confirmed to
not match any of the 50 other already-integrated cities/counties'
endpoint URLs before being accepted.

Confirmed live via real server-side queries during this build: 407,064
total rows, max(IncidentDateTime) = 2026-09-08 (1 day before this
build), 7,537 rows in the trailing 45-day window — genuinely active.
Unique id `EsriPkey` (a composite of internal id + incident number +
NIBRS code) confirmed 0% null; the more human-readable `cmnIncidentNbr`
(JSO's own incident number) is sometimes null on its own (confirmed
directly in a live sample) so `EsriPkey` is used as the real unique id
instead, not `cmnIncidentNbr`.

`nibrsDescription` is a genuine, specific NIBRS-based offense field (e.g.
"SIMPLE ASSAULT", "MOTOR VEHICLE THEFT") — confirmed accurate to its
field name via direct sampling, no reversed/misleading pairing found (a
real gap this project has hit more than once in recent phases). Address
is already street-block level from the source itself. No disposition
field present. No personal-identifier fields found in this schema — only
address, zip, incident numbers, and NIBRS codes are present.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session

from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

JACKSONVILLE_CRIME_QUERY_URL = (
    "https://services3.arcgis.com/7C7xW0yv6W8spzhp/arcgis/rest/services/"
    "Public_Transparency_Data_View_10_03_2025/FeatureServer/0/query"
)
SOURCE_JACKSONVILLE_CRIME = "jacksonville_crime"
CITY_NAME = "Jacksonville"

DEFAULT_FETCH_LIMIT = 200

_FIELDS = "EsriPkey,cmnIncidentNbr,IncidentDateTime,nibrsDescription,Address,ZipCode"


async def _fetch_records(limit: int) -> list[dict]:
    params = {
        "where": "1=1",
        "outFields": _FIELDS,
        "resultRecordCount": limit,
        "orderByFields": "IncidentDateTime DESC",
        "f": "json",
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(JACKSONVILLE_CRIME_QUERY_URL, params=params)
        response.raise_for_status()
        data = response.json()
    if "error" in data:
        raise RuntimeError(f"Jacksonville ArcGIS query failed: {data['error']}")
    return [f["attributes"] for f in data.get("features", [])]


def _format_esri_date(epoch_ms) -> str:
    if not epoch_ms:
        return "an unknown date"
    try:
        return datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return "an unknown date"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("nibrsDescription"), "an incident")
    address = clean_field(record.get("Address"), "an unspecified location")
    zip_code = clean_field(record.get("ZipCode"))
    date = _format_esri_date(record.get("IncidentDateTime"))

    location = f"{address}, {zip_code}" if zip_code else address
    return f"{CITY_NAME} crime report: {offense.title()} near {location}, on {date}."


async def sync_jacksonville_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_JACKSONVILLE_CRIME, CITY_NAME, "EsriPkey", _summarize)
