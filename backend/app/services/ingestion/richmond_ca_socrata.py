"""Richmond, CA Open Data (Socrata, "TransparentRichmond") ingestion —
plan.md Step 9 Phase 28.

Discovered via `OpenPoliceData`'s source table, then independently
re-verified via direct HTTP queries before any code was written.

**Real, important labeling clarification, corrected from an earlier
phase's note**: `transparentrichmond.org` was previously mentioned in
Phase 11's Norfolk module as a "decoy" — but that note was written while
searching for a candidate for Richmond, VIRGINIA. The dataset genuinely
IS real Richmond, CALIFORNIA data, not fake — it was simply the wrong
city for that unrelated search at the time. Now that Richmond, CA itself
is the actual target, this is the correct, real source.

**Real, significant finding caught before shipping**: both underlying
datasets (`t3nu-7bbq` Incidents and `k4y4-5quj` Calls for Service) are
genuinely REGIONAL, covering many Bay-Area-and-beyond cities (Alameda,
Berkeley, Antioch, and dozens of others), not exclusively Richmond PD's
own jurisdiction — confirmed via a direct `$select=distinct city` query.
Both modules therefore filter to `city='RICHMOND'` explicitly so this
source is never accidentally presented as covering the wrong city's
data; the Richmond-only slice is still large (120,764/124,899 Incidents
rows, 654,881/724,395 CFS rows).

**Incidents dataset** (`t3nu-7bbq`): confirmed live via real server-side
queries — 124,899 total rows (120,764 for Richmond specifically),
max(createddateutc) = 2026-09-10 (same day as this build), 1,429 rows in
the trailing 45-day window. Unique id `reportnumber` confirmed 0% null.
`offensecode` is a genuine, specific penal-code-level offense field
(e.g. "ASSAULT W/DEADLY WEAPON:NOT F/ARM | 245(A)(1)").

**Calls for Service dataset** (`k4y4-5quj`): confirmed live — 724,395
total rows (654,881 for Richmond specifically), max(createddateutc) =
2026-09-10 (same day), 12,017 rows in the trailing 45-day window. Unique
id `cadagencyeventnumber` confirmed 0% null. `eventtype`/
`secondaryeventtype` are genuine, specific call-type fields.

No personal-identifier fields found in either schema — checked directly,
no CCN/WARD/ANC/PSA/BID fields (this project's recurring "mislabeled DC
MPD data" pattern) and no victim/officer names.
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

_INCIDENTS_URL = "https://www.transparentrichmond.org/resource/t3nu-7bbq.json"
_CFS_URL = "https://www.transparentrichmond.org/resource/k4y4-5quj.json"

SOURCE_RICHMOND_CA_CRIME = "richmond_ca_crime"
SOURCE_RICHMOND_CA_CALLS = "richmond_ca_calls"
CITY_NAME = "Richmond, CA"

# Both underlying datasets are regional — filtered to this city's own
# jurisdiction only. See module docstring's real-finding note.
_RICHMOND_ONLY = "city='RICHMOND'"


def _summarize_incident(record: dict) -> str:
    offense = clean_field(record.get("offensecode"), "an incident")
    grouping = clean_field(record.get("offense_grouping"))
    street_block = clean_field(record.get("streetblock"))
    street_name = clean_field(record.get("streetname"))
    date = clean_field(record.get("createddateutc"))
    date = date[:10] if date else "an unknown date"

    address = f"{street_block} {street_name}".strip() if (street_block or street_name) else "an unspecified location"
    detail = f" ({grouping})" if grouping and grouping.lower() != offense.lower() else ""
    return f"{CITY_NAME} crime report: {offense}{detail} near {address}, on {date}."


def _summarize_cfs(record: dict) -> str:
    event_type = clean_field(record.get("eventtype"), "an incident")
    secondary_type = clean_field(record.get("secondaryeventtype"))
    street_block = clean_field(record.get("streetblock"))
    street_name = clean_field(record.get("streetname"))
    disposition = clean_field(record.get("disposition"))
    date = clean_field(record.get("createddateutc"))
    date = date[:10] if date else "an unknown date"

    address = f"{street_block} {street_name}".strip() if (street_block or street_name) else "an unspecified location"
    detail = f" ({secondary_type})" if secondary_type and secondary_type.lower() != event_type.lower() else ""

    parts = [f"{CITY_NAME} police call: {event_type}{detail} near {address}, on {date}."]
    if disposition:
        parts.append(f"Disposition: {disposition.title()}.")
    return " ".join(p for p in parts if p.strip())


async def sync_richmond_ca_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(
        _INCIDENTS_URL,
        limit,
        params={"$order": "createddateutc DESC", "$where": _RICHMOND_ONLY},
    )
    return await sync_dataset(session, records, SOURCE_RICHMOND_CA_CRIME, CITY_NAME, "reportnumber", _summarize_incident)


async def sync_richmond_ca_calls(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(
        _CFS_URL,
        limit,
        params={"$order": "createddateutc DESC", "$where": _RICHMOND_ONLY},
    )
    return await sync_dataset(
        session, records, SOURCE_RICHMOND_CA_CALLS, CITY_NAME, "cadagencyeventnumber", _summarize_cfs
    )
