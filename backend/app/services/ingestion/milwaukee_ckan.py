"""Milwaukee Open Data (CKAN Datastore SQL API) ingestion — plan.md
Step 9 Phase 5.

Confirmed live via a real SQL query during this build: most recent
Incident_Date is 2026-09-04 (excluding a bad future-dated outlier row
found during research — real, messy government data, not hypothetical),
four days before this build — genuinely current.

Unlike every other city module here, this uses CKAN's `datastore_search_sql`
endpoint (a raw SQL-over-HTTP interface, similar in spirit to
Philadelphia's CartoDB SQL API but a different concrete API shape) rather
than Socrata's SODA API, an ArcGIS FeatureServer, or a flat CSV download.
The dataset itself is self-hosted on data.milwaukee.gov, but the CKAN
datastore API responded reliably in testing (unlike Milwaukee's separate
ArcGIS MapServer mirror, which returned 400/500 errors on every query
during research — deliberately NOT used here for that reason).

Real, non-obvious finding: `Offense_All` can hold MULTIPLE
semicolon-separated NIBRS codes in a single row (e.g. "90Z;13B") — a
different structural pattern than every other city, which put multiple
offenses in separate rows sharing one incident number. Handled here by
splitting and joining back into readable text, not treated as a single
opaque code.
"""

import logging

import httpx
from sqlmodel import Session

from app.services.ingestion.nibrs_codes import describe_nibrs_code
from app.services.ingestion.socrata_base import clean_field, sync_dataset

logger = logging.getLogger(__name__)

MILWAUKEE_SQL_URL = "https://data.milwaukee.gov/api/3/action/datastore_search_sql"
MILWAUKEE_RESOURCE_ID = "87843297-a6fa-46d4-ba5d-cb342fb2d3bb"
SOURCE_MILWAUKEE_CRIME = "milwaukee_crime"
CITY_NAME = "Milwaukee"

DEFAULT_FETCH_LIMIT = 200

# Excludes a bad future-dated outlier confirmed present in the real data
# during research (a garbage row with a date far past 2026) — filtering
# it out here rather than let it silently claim the "most recent" slot
# and push out genuinely current real records.
_QUERY_TEMPLATE = (
    'SELECT "Case_Number", "Incident_Date", "Police_District", '
    '"Offense_All", "Location_All", "Weapon_Used_All" '
    'FROM "{resource_id}" '
    "WHERE \"Incident_Date\" < '2027-01-01' "
    'ORDER BY "Incident_Date" DESC '
    "LIMIT {limit}"
)


async def _fetch_records(limit: int) -> list[dict]:
    sql = _QUERY_TEMPLATE.format(resource_id=MILWAUKEE_RESOURCE_ID, limit=limit)
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(MILWAUKEE_SQL_URL, params={"sql": sql})
        response.raise_for_status()
        data = response.json()
    if not data.get("success"):
        raise RuntimeError(f"Milwaukee datastore_search_sql failed: {data}")
    return data["result"]["records"]


def _summarize(record: dict) -> str:
    # Real fix (Revision 3 Step 9 Phase 5): a real end-to-end verification
    # query surfaced raw codes ("290", "90J") instead of readable offense
    # names, since this dataset's own schema has no description field —
    # confirmed directly, not assumed. describe_nibrs_code() translates
    # each real code via a table cross-validated against another city's
    # own live code+description pairing (see nibrs_codes.py), falling
    # back to the raw code only for a genuinely unrecognized one.
    raw_offenses = clean_field(record.get("Offense_All"))
    offenses = (
        ", ".join(describe_nibrs_code(o) for o in raw_offenses.split(";") if o.strip())
        or "an incident"
    )
    location = clean_field(record.get("Location_All"), "an unspecified location")
    district = clean_field(record.get("Police_District"), "unknown")
    date = clean_field(record.get("Incident_Date"), "an unknown date")
    date = date.split(" ")[0] if date != "an unknown date" else date
    weapon = clean_field(record.get("Weapon_Used_All"))

    parts = [
        f"{CITY_NAME} crime report: offense code(s) {offenses}",
        f"near {location}, police district {district}, on {date}.",
    ]
    if weapon and weapon.upper() not in ("NONE", "N/A"):
        parts.append(f"Weapon: {weapon.title()}.")
    return " ".join(p for p in parts if p.strip())


async def sync_milwaukee_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await _fetch_records(limit)
    return await sync_dataset(session, records, SOURCE_MILWAUKEE_CRIME, CITY_NAME, "Case_Number", _summarize)
