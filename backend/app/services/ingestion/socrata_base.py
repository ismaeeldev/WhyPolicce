"""Shared ingestion engine for Socrata-family open-data sources — Phase 9
(plan.md Step 9), extracted from the original NYC-only implementation
(nyc_socrata.py) so adding a new city means writing a URL, a field
mapping, and a summarizer, not re-deriving the upsert/embedding pipeline.

Every per-city module (chicago_socrata.py, la_socrata.py, etc.) calls
`sync_dataset()` with its own values — the fetch/embed/upsert mechanics,
including the N+1-query fix and the null/"(null)" field-cleaning behavior
that were both hardened once against real NYC data, are shared so they
don't have to be independently rediscovered per city.
"""

import logging
from collections.abc import Callable
from datetime import datetime, timezone

import httpx
from sqlmodel import Session, select

from app.models.public_record import PublicRecord
from app.services.embedding_service import embed_texts

logger = logging.getLogger(__name__)


def describe_sync_error(exc: Exception) -> str:
    """Real cosmetic bug found and fixed during a data-accuracy audit
    (plan.md): every phaseN_cities.py orchestrator's per-city except block
    stores `{"source": ..., "error": str(exc)}` in its stats dict — but
    httpx/httpcore's own timeout/connection exceptions are frequently
    raised with NO message text at all (confirmed directly: a bare
    `httpx.ReadTimeout()` has `str(exc) == ""`), so a real, correctly-
    isolated per-city failure (e.g. Detroit's/Boise's genuine transient
    ArcGIS timeouts, seen live during the audit's own sync runs) silently
    lost its only at-a-glance diagnostic signal in that dict — even though
    the full traceback was still correctly logged separately via
    logger.exception() right above it, so nothing was ever truly lost,
    just not duplicated into this one field. Falls back to the exception's
    own class name (e.g. "ReadTimeout") when str(exc) is empty, so the
    stats dict always carries at least some signal instead of ''."""
    return str(exc) or type(exc).__name__


# Kept modest for a first sync per source, same reasoning as the original
# NYC default — conservative rather than pulling a whole dataset on day one.
DEFAULT_FETCH_LIMIT = 200


def clean_field(value, default: str = "") -> str:
    """Normalizes a raw Socrata/CartoDB field value into a safe display
    string. Real behavior found via NYC hardening testing (feeding empty/
    malformed records through the summarizers), now shared across every
    city instead of being reimplemented (and potentially miss the same
    edge cases) each time:

    `dict.get(key, default)` only falls back to the default when the KEY
    is entirely missing — it does nothing for a key that exists but holds
    `None` (renders as the literal text "None" in an f-string) or a
    source's own literal `"(null)"` string (confirmed present in real
    Socrata API responses). Route every field through this helper so both
    collapse to the same clean default."""
    if value is None:
        return default
    text_value = str(value).strip()
    if not text_value or text_value.lower() == "(null)":
        return default
    return text_value


async def fetch_socrata_json(url: str, limit: int, params: dict | None = None) -> list[dict]:
    """Fetches records from a standard Socrata SODA API endpoint (JSON,
    `$limit`/`$order`/etc. query params). Not every source in this package
    uses this — Philadelphia's CartoDB SQL API needs its own fetch
    function — but every Socrata-platform city (Chicago, LA, Seattle,
    Austin, Dallas, and the original NYC) shares this exact shape."""
    query = {"$limit": limit, **(params or {})}
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(url, params=query)
        response.raise_for_status()
        return response.json()


async def sync_dataset(
    session: Session,
    records: list[dict],
    source: str,
    city: str,
    id_field: str,
    summarize: Callable[[dict], str],
) -> dict:
    """Summarizes, embeds, and upserts a batch of already-fetched raw
    records. Fetching is deliberately NOT done here (unlike the original
    NYC-only `_sync_dataset`) — different platforms need different fetch
    mechanics (Socrata SODA vs. CartoDB SQL), so each city module fetches
    its own records and passes them in, keeping this function usable by
    every platform rather than assuming Socrata's query shape.

    Returns a stats dict identical in shape to the original NYC sync, so
    the scheduler/manual-run caller can log/aggregate results the same way
    regardless of which city ran."""
    logger.info("socrata_base: syncing %d records for %s (%s)", len(records), source, city)

    inserted = 0
    updated = 0
    skipped = 0

    # Found live during Phase 1 verification (real Seattle data, not a
    # hypothetical): a single police report can list multiple offenses as
    # SEPARATE rows sharing the same report_number (e.g. one incident with
    # both an assault and a weapons charge). The DB's uniqueness
    # constraint is on (source, external_id), so feeding two rows with the
    # same id into one INSERT batch throws a real UniqueViolation — this
    # isn't a hypothetical edge case, it's the actual first real-data
    # Phase 1 run failing. Deduplicate within THIS fetch batch (not just
    # against already-committed rows, which the existing-row check below
    # already handled) by keeping the last-seen row per external_id — a
    # deliberate simplification (one DB row can't hold two offense
    # descriptions) rather than a silent data-loss bug, since the
    # alternative (crashing the whole city's sync) loses ALL of that
    # city's records for the run, not just one offense line from one report.
    by_external_id: dict[str, dict] = {}
    for record in records:
        external_id = record.get(id_field)
        if not external_id:
            skipped += 1
            continue
        by_external_id[str(external_id)] = record

    summaries = []
    valid_records = []
    for external_id, record in by_external_id.items():
        summaries.append(summarize(record))
        valid_records.append((external_id, record))

    if not summaries:
        return {"source": source, "city": city, "fetched": len(records), "inserted": 0, "updated": 0, "skipped": skipped}

    embeddings = await embed_texts(summaries)

    # Same N+1-avoidance fix as the original NYC sync: one batched
    # existence-check query instead of one query per record.
    all_external_ids = [external_id for external_id, _ in valid_records]
    existing_rows = session.exec(
        select(PublicRecord).where(
            PublicRecord.source == source,
            PublicRecord.external_id.in_(all_external_ids),
        )
    ).all()
    existing_by_id = {row.external_id: row for row in existing_rows}

    for (external_id, raw_record), summary, embedding in zip(valid_records, summaries, embeddings):
        existing = existing_by_id.get(external_id)

        if existing:
            # Real bug found and fixed (Revision 3 Step 9): this update path
            # never touched `existing.city`, only the insert path set it —
            # confirmed directly against the live DB that rows ingested
            # before the city-name-in-summary fix kept a stale `city` value
            # forever on every later re-sync, even though `raw_text` was
            # correctly refreshed. A resync must be able to correct a
            # previously-wrong city value, not just add new fields to it.
            existing.city = city
            existing.raw_text = summary
            existing.raw_json = raw_record
            existing.embedding = embedding
            # Real bug found and fixed during a data-accuracy audit
            # (plan.md): PublicRecord.updated_at only has a default_factory,
            # which SQLModel/SQLAlchemy applies on INSERT, not on every
            # UPDATE — there's no onupdate= on the column. Without setting
            # this explicitly, a resynced/refreshed row silently kept its
            # ORIGINAL insertion timestamp forever, confirmed directly
            # against the live DB: a source logged "200 updated" during a
            # sync run, but a same-source freshness query using updated_at
            # showed 0 rows touched and a max(updated_at) from the day
            # before. That makes any future freshness/staleness monitoring
            # of this table silently untrustworthy, not just this one audit.
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
        "city": city,
        "fetched": len(records),
        "inserted": inserted,
        "updated": updated,
        "skipped": skipped,
    }
    logger.info("socrata_base sync complete: %s", stats)
    return stats
