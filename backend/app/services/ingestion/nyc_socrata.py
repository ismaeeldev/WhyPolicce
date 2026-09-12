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

**Real, significant staleness bug found and fixed (Data Freshness Fix
phase, prompted by a real client report — "last arrest in Harlem" query
returning nothing recent)**: `_fetch_records()` previously called Socrata
with only `$limit`, no `$order` clause at all. Confirmed live: Socrata's
default (unordered) response for both NYC datasets starts from the
OLDEST end of the dataset (2026-01-01), not the newest — so every sync
since this module was first written had been re-fetching and re-upserting
the same ~200 oldest rows over and over, never reaching the genuinely
current data actually available at the live source (confirmed live max
arrest_date = 2026-06-30 on the same day the DB's stored max was found to
be 2026-04-02, over 5 months stale). Every other city module built in
later phases already orders by date DESC — this was the one original
module that predated that pattern and was never brought in line with it.
Fixed by adding `$order={field} DESC` to every NYC fetch.

Separately, confirmed via a live schema check that neither NYC dataset
has a neighborhood-level field of its own (only borough + precinct
number) — so a query for a specific neighborhood like "Harlem" previously
could only ever resolve to "Manhattan" borough-level data. Fixed in the
same phase by adding `nyc_precincts.py`, a real, independently-verified
NYPD-precinct-to-neighborhood lookup (source: NYPD's own public
per-precinct pages), applied to both summarizers so a precinct number
already present in every record (e.g. arrest_precinct=28) now also
resolves to its real neighborhood name (e.g. "Central Harlem") in the
generated summary text — no external geocoding API call needed, since
precinct number was already a live field in every record.
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlmodel import Session, select

from app.models.public_record import PublicRecord
from app.services.embedding_service import embed_texts
from app.services.ingestion.nyc_precincts import precinct_to_neighborhood

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

    # Real bug found and fixed (Revision 3 Step 9, multi-city expansion):
    # this summary previously said "in the Bronx" but never "New York
    # City" itself — worked fine while NYC was the only ingested city, but
    # once other cities exist in the same table, a query naming the city
    # by name (e.g. "New York City" or "NYC") has nothing to textually
    # match against. Every other city's summarizer now leads with its own
    # city name for the same reason (see chicago_socrata.py's comment for
    # the real query that first caught this class of bug).
    neighborhood = precinct_to_neighborhood(precinct)

    prefix = f"{law_cat.title()} " if law_cat else ""
    location_phrase = f"reported in {boro}"
    if neighborhood:
        location_phrase += f" ({neighborhood})"
    location_phrase += f", precinct {precinct}, on {date}."
    parts = [
        f"New York City {prefix.lower()}complaint: {offense}" + (f" ({detail})" if detail and detail != offense else ""),
        location_phrase,
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

    neighborhood = precinct_to_neighborhood(precinct)

    prefix = f"{law_cat.title()} " if law_cat else ""
    location_phrase = f"in {boro}"
    if neighborhood:
        location_phrase += f" ({neighborhood})"
    location_phrase += f", precinct {precinct}, on {date}."
    parts = [
        f"New York City {prefix.lower()}arrest: {offense}" + (f" ({detail})" if detail and detail != offense else ""),
        location_phrase,
    ]
    return " ".join(p for p in parts if p.strip())


async def _fetch_records(url: str, limit: int, order_field: str) -> list[dict]:
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params={"$limit": limit, "$order": f"{order_field} DESC"})
        response.raise_for_status()
        return response.json()


async def _sync_dataset(
    session: Session,
    url: str,
    source: str,
    id_field: str,
    summarize: callable,
    limit: int,
    order_field: str,
) -> dict:
    """Fetches, summarizes, embeds, and upserts one dataset. Returns a
    small stats dict so the caller (scheduler, or a manual run) can log
    what actually happened rather than just "done"."""
    records = await _fetch_records(url, limit, order_field)
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
            # Real bug found and fixed (Revision 3 Step 9): the update path
            # never touched `existing.city`, only the insert path set it —
            # confirmed directly against the live DB that rows ingested
            # before the city-name-in-summary fix kept the stale value 'NY'
            # forever on every later re-sync. See socrata_base.py's
            # identical fix/comment.
            existing.city = city
            existing.raw_text = summary
            existing.raw_json = raw_record
            existing.embedding = embedding
            # Real bug found and fixed during a data-accuracy audit
            # (plan.md) — see socrata_base.py's identical fix/comment:
            # PublicRecord.updated_at only has a default_factory (applied
            # on INSERT), no onupdate=, so a resynced row silently kept its
            # original insertion timestamp forever without this.
            existing.updated_at = datetime.now(timezone.utc)
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
        session, NYC_COMPLAINT_URL, SOURCE_COMPLAINT, "cmplnt_num", _summarize_complaint, limit, "cmplnt_fr_dt"
    )


async def sync_nyc_arrests(session: Session, limit: int = DEFAULT_FETCH_LIMIT) -> dict:
    return await _sync_dataset(
        session, NYC_ARREST_URL, SOURCE_ARREST, "arrest_key", _summarize_arrest, limit, "arrest_date"
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
            # Step 9 finding (from the Phase 1 multi-city orchestrator hitting
            # this for real): a failed INSERT/commit leaves the shared
            # SQLAlchemy Session in an aborted-transaction state that poisons
            # every subsequent query on it, even an unrelated dataset's. This
            # loop never happened to trigger that with NYC's own two datasets,
            # but the same shared-session risk exists here — rollback so a
            # real future failure here can't silently take the other dataset
            # down with it the way Seattle's failure did to Austin.
            session.rollback()
            results.append({"source": source_name, "error": str(exc)})
    return results
