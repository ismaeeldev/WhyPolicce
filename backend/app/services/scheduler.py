"""Background sync scheduler — AgentGuide/revision2.md Phase 2 step 2-4.

Runs the NYC Socrata sync on a recurring schedule inside the same FastAPI
process, no separate broker/worker infrastructure. Chosen over Celery
per the reasoning in revision2.md §3 Phase 2 step 2: Celery needs a
message broker (Redis/RabbitMQ) plus a separate worker process/deployment
— APScheduler's AsyncIOScheduler runs in-process, adding zero new
infrastructure for a once-a-week, single-city sync. Recommended to the
client rather than decided silently; revisit only if sync volume/frequency
grows well beyond this.
"""

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import text
from sqlmodel import Session

from app.core.db import sync_engine
from app.services.ingestion.nyc_socrata import sync_all_nyc
from app.services.ingestion.phase1_cities import sync_all_phase1_cities
from app.services.ingestion.phase2_cities import sync_all_phase2_cities
from app.services.ingestion.phase3_cities import sync_all_phase3_cities
from app.services.ingestion.phase4_cities import sync_all_phase4_cities
from app.services.ingestion.phase5_cities import sync_all_phase5_cities
from app.services.ingestion.phase6_cities import sync_all_phase6_cities
from app.services.ingestion.phase7_cities import sync_all_phase7_cities
from app.services.ingestion.phase8_cities import sync_all_phase8_cities
from app.services.ingestion.phase9_cities import sync_all_phase9_cities
from app.services.ingestion.phase10_cities import sync_all_phase10_cities
from app.services.ingestion.phase11_cities import sync_all_phase11_cities
from app.services.ingestion.phase12_cities import sync_all_phase12_cities
from app.services.ingestion.phase13_cities import sync_all_phase13_cities
from app.services.ingestion.phase14_cities import sync_all_phase14_cities
from app.services.ingestion.phase15_cities import sync_all_phase15_cities
from app.services.ingestion.phase16_cities import sync_all_phase16_cities
from app.services.ingestion.phase17_cities import sync_all_phase17_cities
from app.services.ingestion.phase18_cities import sync_all_phase18_cities
from app.services.ingestion.phase19_cities import sync_all_phase19_cities
from app.services.ingestion.phase20_cities import sync_all_phase20_cities
from app.services.ingestion.phase21_cities import sync_all_phase21_cities
from app.services.ingestion.phase22_cities import sync_all_phase22_cities
from app.services.ingestion.phase23_cities import sync_all_phase23_cities
from app.services.ingestion.phase24_cities import sync_all_phase24_cities
from app.services.ingestion.phase25_cities import sync_all_phase25_cities
from app.services.ingestion.phase27_cities import sync_all_phase27_cities
from app.services.ingestion.phase28_cities import sync_all_phase28_cities
from app.services.ingestion.phase29_cities import sync_all_phase29_cities
from app.services.ingestion.phase30_cities import sync_all_phase30_cities
from app.services.ingestion.phase32_cities import sync_all_phase32_cities
from app.services.ingestion.phase33_cities import sync_all_phase33_cities

logger = logging.getLogger(__name__)

# Found during hardening: backend/Dockerfile runs `uvicorn --workers 2`,
# which spawns 2 separate OS processes, each with its own independent
# Python memory space — meaning each one runs its OWN start_scheduler()
# call from the FastAPI lifespan, resulting in 2 independent
# AsyncIOScheduler instances that would BOTH eventually fire and run the
# same weekly sync concurrently, wasting real OpenAI embedding API cost
# and creating confusing duplicate log entries (though not actual data
# corruption — Postgres's normal MVCC already confirmed safe for
# concurrent upserts to this table in earlier hardening). This also
# protects against the broader case of multiple separate Cloud Run
# container instances under real traffic, which --workers alone can never
# coordinate across regardless of its value. A Postgres advisory lock is
# a real, built-in mechanism for exactly this "only one process does X"
# problem — works correctly across any number of processes or container
# instances sharing the same database, with zero new infrastructure.
# pg_try_advisory_lock is non-blocking: a worker that doesn't get the
# lock simply skips this run rather than queueing to run later, which is
# correct here — the next run is only 7 days away regardless.
_SYNC_LOCK_ID = 728194635  # arbitrary but fixed — must not collide with any other advisory lock this app might use

# Weekly, per the client's own suggested cadence in the chat ("fetch the
# latest public safety records weekly or monthly"). A single config point,
# not hardcoded logic scattered around — change here only.
SYNC_INTERVAL_HOURS = 24 * 7

_scheduler: AsyncIOScheduler | None = None


async def _run_scheduled_sync() -> None:
    """The actual job body — wrapped so a failure in one run is logged,
    not left to crash the scheduler thread silently (APScheduler swallows
    unhandled exceptions from jobs by default without this).

    Acquires a Postgres advisory lock before doing any real work — see the
    module docstring note on _SYNC_LOCK_ID for why this matters with
    multiple uvicorn workers. Only one worker (whichever wins the race)
    actually runs the sync; the others log a skip and return immediately,
    without blocking.

    Uses sync_engine (Neon's DIRECT, non-pooled connection), not the app's
    normal pooled `engine` — a real bug found during a data-accuracy audit
    (plan.md): pg_try_advisory_lock is a SESSION-level lock, tied to the
    specific physical backend connection that acquired it. Confirmed live
    that Neon's pooler can silently reassign/recycle that physical backend
    mid-session on a long-running connection like this multi-phase sync,
    which drops the lock without any error — defeating the whole point of
    this function acquiring it. See Settings.database_url_direct's
    docstring for the full explanation.

    Explicitly opens ONE Connection and binds the Session to it
    (`Session(bind=connection)`), rather than `Session(sync_engine)` —
    found live during THIS fix's own verification, not assumed: a Session
    bound directly to an engine checks its DBAPI connection back in to the
    pool on every commit() and checks out a (possibly different) one on the
    next statement. Confirmed directly with pg_backend_pid() that even with
    sync_engine's own NullPool (no idle-timeout recycling), the physical
    backend still changed on every single commit — meaning the very first
    `session.commit()` inside a per-city sync would already have dropped
    the lock, an even faster failure than the original pooler bug. Binding
    to one already-open Connection for the whole `with` block is what
    actually pins one physical backend for this function's entire
    duration, confirmed the same way (pg_backend_pid() identical across
    multiple statements and commits on this bound Session)."""
    if sync_engine is None:
        logger.warning("scheduler: DATABASE_URL not configured, skipping scheduled sync")
        return

    with sync_engine.connect() as connection, Session(bind=connection) as session:
        # .first() returns a Row, e.g. (False,) — which is ALWAYS truthy
        # in Python regardless of its content (any non-empty tuple is
        # truthy). Caught this exact bug during hardening before it
        # shipped: `if not got_lock` on the bare Row would never detect a
        # failed lock acquisition, silently defeating the whole fix — both
        # workers would believe they'd acquired the lock every time.
        # row[0] unwraps to the real boolean.
        lock_row = session.exec(text(f"SELECT pg_try_advisory_lock({_SYNC_LOCK_ID})")).first()
        got_lock = bool(lock_row and lock_row[0])
        if not got_lock:
            logger.info("scheduler: another worker already holds the sync lock, skipping this run")
            return
        try:
            logger.info("scheduler: starting scheduled NYC Socrata sync")
            try:
                results = await sync_all_nyc(session)
                logger.info("scheduler: NYC sync complete — %s", results)
            except Exception:
                logger.exception("scheduler: scheduled NYC sync failed")

            # Revision 3 Step 9 Phase 1 — same weekly cadence, same
            # advisory-lock-protected job, just more cities per run. Kept
            # as a second try/except rather than folding into sync_all_nyc
            # so a NYC failure never blocks Phase 1 cities from syncing
            # (and vice versa) — same failure-isolation principle already
            # applied one level down inside sync_all_nyc/sync_all_phase1.
            logger.info("scheduler: starting scheduled Phase 1 cities sync")
            try:
                phase1_results = await sync_all_phase1_cities(session)
                logger.info("scheduler: Phase 1 sync complete — %s", phase1_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 1 sync failed")

            # Same reasoning as Phase 1's own separate try/except above —
            # a Phase 1 failure must never block Phase 2 from syncing.
            logger.info("scheduler: starting scheduled Phase 2 cities sync")
            try:
                phase2_results = await sync_all_phase2_cities(session)
                logger.info("scheduler: Phase 2 sync complete — %s", phase2_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 2 sync failed")

            # Same reasoning as Phase 1/2's own separate try/except blocks.
            logger.info("scheduler: starting scheduled Phase 3 cities sync")
            try:
                phase3_results = await sync_all_phase3_cities(session)
                logger.info("scheduler: Phase 3 sync complete — %s", phase3_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 3 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 4 cities sync")
            try:
                phase4_results = await sync_all_phase4_cities(session)
                logger.info("scheduler: Phase 4 sync complete — %s", phase4_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 4 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 5 cities sync")
            try:
                phase5_results = await sync_all_phase5_cities(session)
                logger.info("scheduler: Phase 5 sync complete — %s", phase5_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 5 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 6 cities sync")
            try:
                phase6_results = await sync_all_phase6_cities(session)
                logger.info("scheduler: Phase 6 sync complete — %s", phase6_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 6 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 7 cities sync")
            try:
                phase7_results = await sync_all_phase7_cities(session)
                logger.info("scheduler: Phase 7 sync complete — %s", phase7_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 7 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 8 cities sync")
            try:
                phase8_results = await sync_all_phase8_cities(session)
                logger.info("scheduler: Phase 8 sync complete — %s", phase8_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 8 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 9 cities sync")
            try:
                phase9_results = await sync_all_phase9_cities(session)
                logger.info("scheduler: Phase 9 sync complete — %s", phase9_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 9 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 10 cities sync")
            try:
                phase10_results = await sync_all_phase10_cities(session)
                logger.info("scheduler: Phase 10 sync complete — %s", phase10_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 10 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 11 cities sync")
            try:
                phase11_results = await sync_all_phase11_cities(session)
                logger.info("scheduler: Phase 11 sync complete — %s", phase11_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 11 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 12 cities sync")
            try:
                phase12_results = await sync_all_phase12_cities(session)
                logger.info("scheduler: Phase 12 sync complete — %s", phase12_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 12 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 13 cities sync")
            try:
                phase13_results = await sync_all_phase13_cities(session)
                logger.info("scheduler: Phase 13 sync complete — %s", phase13_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 13 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 14 cities sync")
            try:
                phase14_results = await sync_all_phase14_cities(session)
                logger.info("scheduler: Phase 14 sync complete — %s", phase14_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 14 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 15 cities sync")
            try:
                phase15_results = await sync_all_phase15_cities(session)
                logger.info("scheduler: Phase 15 sync complete — %s", phase15_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 15 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 16 cities sync")
            try:
                phase16_results = await sync_all_phase16_cities(session)
                logger.info("scheduler: Phase 16 sync complete — %s", phase16_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 16 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 17 cities sync")
            try:
                phase17_results = await sync_all_phase17_cities(session)
                logger.info("scheduler: Phase 17 sync complete — %s", phase17_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 17 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 18 cities sync")
            try:
                phase18_results = await sync_all_phase18_cities(session)
                logger.info("scheduler: Phase 18 sync complete — %s", phase18_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 18 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 19 cities sync")
            try:
                phase19_results = await sync_all_phase19_cities(session)
                logger.info("scheduler: Phase 19 sync complete — %s", phase19_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 19 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 20 cities sync")
            try:
                phase20_results = await sync_all_phase20_cities(session)
                logger.info("scheduler: Phase 20 sync complete — %s", phase20_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 20 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 21 cities sync")
            try:
                phase21_results = await sync_all_phase21_cities(session)
                logger.info("scheduler: Phase 21 sync complete — %s", phase21_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 21 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 22 cities sync")
            try:
                phase22_results = await sync_all_phase22_cities(session)
                logger.info("scheduler: Phase 22 sync complete — %s", phase22_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 22 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 23 cities sync")
            try:
                phase23_results = await sync_all_phase23_cities(session)
                logger.info("scheduler: Phase 23 sync complete — %s", phase23_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 23 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 24 cities sync")
            try:
                phase24_results = await sync_all_phase24_cities(session)
                logger.info("scheduler: Phase 24 sync complete — %s", phase24_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 24 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 25 cities sync")
            try:
                phase25_results = await sync_all_phase25_cities(session)
                logger.info("scheduler: Phase 25 sync complete — %s", phase25_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 25 sync failed")

            # Phase 26 found 0 genuinely new candidates and shipped no
            # code (a real, verified negative result — see plan.md), so
            # there is no phase26_cities module to call here.

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 27 cities sync")
            try:
                phase27_results = await sync_all_phase27_cities(session)
                logger.info("scheduler: Phase 27 sync complete — %s", phase27_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 27 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 28 cities sync")
            try:
                phase28_results = await sync_all_phase28_cities(session)
                logger.info("scheduler: Phase 28 sync complete — %s", phase28_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 28 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 29 cities sync")
            try:
                phase29_results = await sync_all_phase29_cities(session)
                logger.info("scheduler: Phase 29 sync complete — %s", phase29_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 29 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 30 cities sync")
            try:
                phase30_results = await sync_all_phase30_cities(session)
                logger.info("scheduler: Phase 30 sync complete — %s", phase30_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 30 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 32 cities sync")
            try:
                phase32_results = await sync_all_phase32_cities(session)
                logger.info("scheduler: Phase 32 sync complete — %s", phase32_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 32 sync failed")

            # Same reasoning as every prior phase's own separate try/except.
            logger.info("scheduler: starting scheduled Phase 33 cities sync")
            try:
                phase33_results = await sync_all_phase33_cities(session)
                logger.info("scheduler: Phase 33 sync complete — %s", phase33_results)
            except Exception:
                logger.exception("scheduler: scheduled Phase 33 sync failed")
        finally:
            session.exec(text(f"SELECT pg_advisory_unlock({_SYNC_LOCK_ID})"))


def start_scheduler() -> AsyncIOScheduler | None:
    """Starts the background scheduler. Returns None (and logs, doesn't
    raise) if DATABASE_URL isn't configured — matches this project's
    existing pattern of degrading gracefully instead of crashing app
    startup when an optional dependency is missing (see search_service.py's
    mock-fallback pattern)."""
    global _scheduler
    if sync_engine is None:
        logger.warning("scheduler: DATABASE_URL not configured, scheduler not started")
        return None

    scheduler = AsyncIOScheduler()
    # next_run_time is explicitly set to now + interval, NOT None — verified
    # empirically during this build that next_run_time=None means the job
    # never fires at all (not "wait one interval then start", as its name
    # might suggest) until manually resumed. Setting it explicitly to
    # start_time avoids firing immediately on every process restart/hot-reload
    # (which would re-embed/re-hit the live API every dev restart) while
    # still firing on the configured interval going forward. A manual/
    # on-demand first sync is a separate, explicit action (see a CLI script
    # or admin route), not something startup does implicitly.
    start_time = datetime.now() + timedelta(hours=SYNC_INTERVAL_HOURS)
    scheduler.add_job(
        _run_scheduled_sync,
        "interval",
        hours=SYNC_INTERVAL_HOURS,
        id="nyc_socrata_sync",
        next_run_time=start_time,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("scheduler: started, NYC Socrata sync every %d hours", SYNC_INTERVAL_HOURS)
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
