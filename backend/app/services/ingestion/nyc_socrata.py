"""NYC Open Data (Socrata) ingestion — AgentGuide/revision2.md Phase 2.

Pulls real, live records from two confirmed public NYC Open Data
endpoints (no auth/API key required, confirmed working during planning):

- NYPD Complaint dataset: https://data.cityofnewyork.us/resource/5uac-w243.json
- NYPD Arrest dataset:    https://data.cityofnewyork.us/resource/uip8-fykc.json

Per the client's own explicit correction mid-conversation (see
revision2.md §1): this reads live from the source on each scheduled run
(app/services/scheduler.py, Phase 2 step 4) rather than a one-time bulk
download — "it's better to read from the source" than to store/manage a
large static snapshot. Each run re-fetches and upserts by the source's own
record id (cmplnt_num / arrest_key) so repeated runs update existing rows
instead of duplicating them.
"""

import logging

import httpx
from sqlmodel import Session, select

from app.models.public_record import PublicRecord
from app.services.embedding_service import embed_texts

logger = logging.getLogger(__name__)

NYC_COMPLAINT_URL = "https://data.cityofnewyork.us/resource/5uac-w243.json"
NYC_ARREST_URL = "https://data.cityofnewyork.us/resource/uip8-fykc.json"

SOURCE_COMPLAINT = "nyc_nypd_complaint"
SOURCE_ARREST = "nyc_nypd_arrest"

# The arrest dataset's arrest_boro field uses single-letter NYPD codes,
# confirmed via a live $select=distinct query during this build (all 5
# boroughs, no other values observed) — translated here so the summary
# text is actually readable, not a bare "K"/"M" a human/LLM has to guess.
BOROUGH_CODES = {
    "B": "the Bronx",
    "K": "Brooklyn",
    "M": "Manhattan",
    "Q": "Queens",
    "S": "Staten Island",
}

# Kept modest for the first sync — the client's own plan (once received)
# may specify a different volume/cadence; this is deliberately
# conservative rather than pulling the entire dataset on day one.
DEFAULT_FETCH_LIMIT = 200


def _clean_field(value, default: str = "") -> str:
    """Normalizes a raw Socrata field value into a safe display string.

    Found via hardening testing (feeding empty/malformed records through
    the summarizers): `dict.get(key, default)` only falls back to the
    default when the KEY is entirely missing — it does nothing for a key
    that exists but holds `None` (real Python behavior, but a real bug in
    an f-string, which renders it as the literal text "None") or Socrata's
    own literal `"(null)"` string value (confirmed present in real API
    responses during Phase 2 testing). Route every field through this
    helper instead of calling .get() with a default directly, so both of
    those cases collapse to the same clean default, not garbage text
    embedded into the actual record summary."""
    if value is None:
        return default
    text_value = str(value).strip()
    if not text_value or text_value.lower() == "(null)":
        return default
    return text_value


def _summarize_complaint(record: dict) -> str:
    """Turns one raw complaint JSON record into a short, readable summary
    — this text is what actually gets embedded and later shown/cited,
    not the raw JSON blob (see app/models/public_record.py)."""
    offense = _clean_field(record.get("ofns_desc"), "an incident")
    detail = _clean_field(record.get("pd_desc"))
    boro = _clean_field(record.get("boro_nm"), "an unspecified borough")
    precinct = _clean_field(record.get("addr_pct_cd"), "unknown")
    raw_date = _clean_field(record.get("cmplnt_fr_dt"))
    date = raw_date[:10] if raw_date else "an unknown date"
    location_type = _clean_field(record.get("prem_typ_desc"))
    status = _clean_field(record.get("crm_atpt_cptd_cd"))
    law_cat = _clean_field(record.get("law_cat_cd"))

    prefix = f"{law_cat.title()} " if law_cat else ""
    parts = [
        f"{prefix}complaint: {offense}" + (f" ({detail})" if detail and detail != offense else ""),
        f"reported in {boro}, precinct {precinct}, on {date}.",
    ]
    if location_type:
        parts.append(f"Location type: {location_type}.")
    if status:
        parts.append(f"Status: {status}.")
    return " ".join(p for p in parts if p.strip())


def _summarize_arrest(record: dict) -> str:
    """Same purpose as _summarize_complaint, for the arrest dataset's
    different field names."""
    offense = _clean_field(record.get("ofns_desc"), "an offense")
    detail = _clean_field(record.get("pd_desc"))
    boro_code = _clean_field(record.get("arrest_boro"))
    boro = BOROUGH_CODES.get(boro_code, boro_code) if boro_code else "an unspecified borough"
    precinct = _clean_field(record.get("arrest_precinct"), "unknown")
    raw_date = _clean_field(record.get("arrest_date"))
    date = raw_date[:10] if raw_date else "an unknown date"
    law_cat = _clean_field(record.get("law_cat_cd"))

    prefix = f"{law_cat.title()} " if law_cat else ""
    parts = [
        f"{prefix}arrest: {offense}" + (f" ({detail})" if detail and detail != offense else ""),
        f"in {boro}, precinct {precinct}, on {date}.",
    ]
    return " ".join(p for p in parts if p.strip())


async def _fetch_records(url: str, limit: int) -> list[dict]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params={"$limit": limit})
        response.raise_for_status()
        return response.json()


async def _sync_dataset(
    session: Session,
    url: str,
    source: str,
    id_field: str,
    summarize: callable,
    limit: int,
) -> dict:
    """Fetches, summarizes, embeds, and upserts one dataset. Returns a
    small stats dict so the caller (scheduler, or a manual run) can log
    what actually happened rather than just "done"."""
    records = await _fetch_records(url, limit)
    logger.info("nyc_socrata: fetched %d records from %s", len(records), source)

    inserted = 0
    updated = 0
    skipped = 0

    # Batch-embed all summaries in one call rather than one HTTP round
    # trip per record — see embedding_service.embed_texts's docstring.
    summaries = []
    valid_records = []
    for record in records:
        external_id = record.get(id_field)
        if not external_id:
            skipped += 1
            continue
        summaries.append(summarize(record))
        valid_records.append((external_id, record))

    if not summaries:
        return {"source": source, "fetched": len(records), "inserted": 0, "updated": 0, "skipped": skipped}

    embeddings = await embed_texts(summaries)

    # Fetch all potentially-existing rows for this batch in ONE query,
    # instead of one query per record inside the loop below. Found via
    # hardening/load testing: the original per-record `select(...).first()`
    # took ~0.58s each against real Neon latency — negligible-looking per
    # call, but 200 sequential round trips compounded into ~116s for a
    # single sync run (measured directly), a classic N+1 query pattern
    # that only gets worse as more records/cities are ingested later.
    all_external_ids = [external_id for external_id, _ in valid_records]
    existing_rows = session.exec(
        select(PublicRecord).where(
            PublicRecord.source == source,
            PublicRecord.external_id.in_(all_external_ids),
        )
    ).all()
    existing_by_id = {row.external_id: row for row in existing_rows}

    city = "New York City"

    for (external_id, raw_record), summary, embedding in zip(valid_records, summaries, embeddings):
        existing = existing_by_id.get(external_id)

        if existing:
            existing.raw_text = summary
            existing.raw_json = raw_record
            existing.embedding = embedding
            session.add(existing)
            updated += 1
        else:
            session.add(
                PublicRecord(
                    source=source,
                    external_id=external_id,
                    city=city,
                    raw_text=summary,
                    raw_json=raw_record,
                    embedding=embedding,
                )
            )
            inserted += 1

    session.commit()
    stats = {
        "source": source,
        "fetched": len(records),
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
    }
    logger.info("nyc_socrata sync complete: %s", stats)
    return stats


async def sync_nyc_complaints(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    return await _sync_dataset(
        session, NYC_COMPLAINT_URL, SOURCE_COMPLAINT, "cmplnt_num", _summarize_complaint, limit
    )


async def sync_nyc_arrests(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    return await _sync_dataset(
        session, NYC_ARREST_URL, SOURCE_ARREST, "arrest_key", _summarize_arrest, limit
    )


async def sync_all_nyc(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> list[dict]:
    """Runs both NYC dataset syncs. Called by the scheduler (Phase 2 step
    4) and available for a manual/one-off trigger during testing.

    Each dataset's failure is isolated from the other — found via hardening
    testing that a single dataset outage (e.g. Socrata's arrest endpoint
    down for maintenance) previously crashed the entire sync and skipped
    the complaints dataset too, even though that one was working fine and
    its data would otherwise have gone stale for an extra week until the
    next scheduled run. A failed dataset's result now reports its own
    error instead of raising, so the healthy dataset still gets synced."""
    results = []
    for sync_fn, source_name in [
        (sync_nyc_complaints, SOURCE_COMPLAINT),
        (sync_nyc_arrests, SOURCE_ARREST),
    ]:
        try:
            results.append(await sync_fn(session, limit))
        except Exception as exc:
            logger.exception("nyc_socrata: %s sync failed, continuing with other datasets", source_name)
            results.append({"source": source_name, "error": str(exc)})
    return results
