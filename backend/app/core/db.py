import logging
from collections.abc import Generator

from sqlalchemy import text
from sqlalchemy.pool import NullPool
from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

logger = logging.getLogger(__name__)

engine = (
    create_engine(
        settings.DATABASE_URL,
        echo=False,
        # Found during hardening: Neon (serverless Postgres) can silently
        # drop idle connections server-side, and SQLAlchemy's default pool
        # has no way to detect that before handing a dead connection back
        # out — the next request to reuse it would fail with a raw
        # OperationalError instead of transparently reconnecting.
        # pool_pre_ping issues a lightweight SELECT 1 before handing out a
        # pooled connection and silently replaces it if that fails.
        # pool_recycle proactively retires connections older than 5
        # minutes, well under Neon's own idle-connection timeout, so
        # stale connections are refreshed before they'd be dropped anyway.
        pool_pre_ping=True,
        pool_recycle=300,
        # Documented, not silently discovered: FastAPI's Depends(get_session)
        # holds one connection for the entire request lifetime, including
        # the full SSE stream duration for /api/search/stream — so the
        # default pool_size=5 + max_overflow=10 (15 total) is also, in
        # effect, this app's max concurrent active searches, not just a
        # generic DB-connection cap. Confirmed Neon's own max_connections
        # is 901 on this plan, so this app's own pool is the real limit,
        # not Neon. Left at SQLAlchemy's defaults deliberately rather than
        # guessed larger without knowing the client's real expected
        # concurrent-user count — raise pool_size/max_overflow together if
        # real traffic shows requests queueing for a connection.
    )
    if settings.DATABASE_URL
    else None
)

# Dedicated engine for the scheduler's long-running weekly sync session —
# see Settings.database_url_direct's docstring for the real bug this fixes
# (a session-level pg_advisory_lock silently dropped mid-sync when the
# physical backend connection gets reassigned/recycled out from under it).
# NOT used for normal per-request sessions (get_session() below still uses
# the pooled `engine`) — a direct connection bypasses Neon's pooler
# entirely, which is correct for one long-lived session but would exhaust
# connection limits fast if every short-lived API request used it too.
#
# Deliberately does NOT set pool_recycle (unlike the main `engine`) — found
# live during this fix's own verification, not assumed: pool_recycle=300
# makes SQLAlchemy's OWN connection pool silently swap out the physical
# connection after 5 minutes regardless of activity, which defeats the
# entire point of this engine just as effectively as Neon's pooler did.
# A single sync run reliably exceeds 5 minutes (the full 30-phase run took
# over 90 minutes). NullPool goes further: it never reuses connections
# across checkouts at all (opens one on connect, closes it on
# session-close), removing pooling-related recycling risk entirely rather
# than just tuning it — appropriate here since this engine only ever needs
# one real connection open at a time (the scheduler's own advisory lock
# already prevents overlapping syncs from this app's side; that guarantee
# is only trustworthy at all once the connection itself doesn't move).
sync_engine = (
    create_engine(
        settings.database_url_direct,
        echo=False,
        poolclass=NullPool,
    )
    if settings.database_url_direct
    else None
)


def get_session() -> Generator[Session, None, None]:
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured — set it in backend/.env")
    with Session(engine) as session:
        try:
            yield session
        except Exception:
            # Explicit, not relying on Session.close()'s own implicit
            # rollback-of-unflushed-work on context-manager exit — a
            # route that catches its own exception (to build a clean
            # error response) and re-raises, or one that partially
            # commits before a later failure, should never leave a
            # half-applied transaction for the next request on a
            # pooled connection.
            session.rollback()
            raise


def create_db_and_tables() -> None:
    if engine is None:
        return

    # RAG pipeline (revision2.md Phase 1) — must run BEFORE create_all(),
    # since app/models/public_record.py's `embedding` column uses
    # Postgres's vector type, which doesn't exist until this extension is
    # enabled. Previously only run manually against the dev database
    # during Phase 1 testing, never committed to code — found and fixed
    # during a later hardening pass: a fresh deploy (or the client's own
    # database) would have failed table creation entirely without this.
    # Safe to run every startup: CREATE EXTENSION IF NOT EXISTS is a no-op
    # once already enabled. SQLite (this project's documented local-test
    # fallback per README.md) doesn't support this or the vector type at
    # all — skipped there, matching the "postgres-only" scope this feature
    # was always built against.
    if engine.dialect.name == "postgresql":
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()

    SQLModel.metadata.create_all(engine)

    # Real bug avoided, not just theoretical: create_all() only creates
    # tables that don't exist yet — it does NOT add a new column to an
    # already-existing table (confirmed via SQLAlchemy's own documented
    # behavior, not assumed). search_messages.sources is a genuinely new
    # column (added for the real-source-citations UI feature) on a table
    # that already exists in every deployed database, so a plain
    # create_all() call would silently leave it missing there and the app
    # would 500 the first time code tries to read/write it. ADD COLUMN IF
    # NOT EXISTS is the same safe, idempotent, no-Alembic-needed pattern
    # already used above for the vector extension and HNSW index — a no-op
    # on a database that already has the column (e.g. a fresh deploy where
    # create_all() just created the whole table with it included).
    if engine.dialect.name == "postgresql":
        with engine.connect() as conn:
            conn.execute(
                text("ALTER TABLE search_messages ADD COLUMN IF NOT EXISTS sources JSON")
            )
            conn.commit()

    # HNSW index for the embedding column's cosine-distance similarity
    # search (app/services/vector_search_service.py). Not expressible via
    # SQLModel's Field()/Column() in a way create_all() would emit
    # correctly for this pgvector-specific index type, so created
    # explicitly here, same reasoning as the extension above. Found via a
    # real, measured production-risk during hardening: an un-indexed
    # search on only 400 rows took ~9.4s (a full sequential scan
    # recomputing cosine distance per row) — with this index in place,
    # warm-cache queries measured ~0.6-1s instead, over 10x faster, and
    # the gap only grows as more cities/records are ingested later.
    if engine.dialect.name == "postgresql":
        with engine.connect() as conn:
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS ix_public_records_embedding_hnsw "
                    "ON public_records USING hnsw (embedding vector_cosine_ops)"
                )
            )
            conn.commit()
