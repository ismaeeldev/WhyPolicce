"""Baton Rouge, LA Open Data (Socrata) ingestion — plan.md Step 9 Phase 11.

Confirmed live via real server-side queries during this build: 208,741
total rows, max(report_date) = 2026-09-07 (essentially current), 3,936
rows in the trailing 45-day window — genuinely active. Unique id
`incident_number` confirmed ~0.001% null (2/208,741) — negligible.

`offense_description` is a genuine, granular offense field (e.g.
"SHOPLIFTING", "SIMPLE ASSAULT") backed by NIBRS code and a full statute
citation/description — no coarseness limitation found. No disposition
field present. No personal-identifier fields found in this schema.
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

BATON_ROUGE_CRIME_URL = "https://data.brla.gov/resource/pbin-pcm7.json"
SOURCE_BATON_ROUGE_CRIME = "baton_rouge_crime"
CITY_NAME = "Baton Rouge"


def _summarize(record: dict) -> str:
    offense = clean_field(record.get("offense_description"), "an incident")
    category = clean_field(record.get("statute_category"))
    street = clean_field(record.get("street"), "an unspecified location")
    neighborhood = clean_field(record.get("neighborhood"))
    date = clean_field(record.get("report_date"))
    date = date[:10] if date else "an unknown date"

    detail = f" ({category})" if category and category.lower() != offense.lower() else ""
    return (
        f"{CITY_NAME} crime report: {offense}{detail} near {street}"
        + (f" ({neighborhood})" if neighborhood else "")
        + f", on {date}."
    )


async def sync_baton_rouge_crime(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    records = await fetch_socrata_json(BATON_ROUGE_CRIME_URL, limit, params={"$order": "report_date DESC"})
    return await sync_dataset(session, records, SOURCE_BATON_ROUGE_CRIME, CITY_NAME, "incident_number", _summarize)
