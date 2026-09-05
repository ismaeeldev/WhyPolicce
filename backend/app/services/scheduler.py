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

from app.core.db import engine
from app.services.ingestion.nyc_socrata import sync_all_nyc

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
    without blocking."""
    if engine is None:
        logger.warning("scheduler: DATABASE_URL not configured, skipping scheduled sync")
        return

    with Session(engine) as session:
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
                logger.info("scheduler: sync complete — %s", results)
            except Exception:
                logger.exception("scheduler: scheduled sync failed")
        finally:
            session.exec(text(f"SELECT pg_advisory_unlock({_SYNC_LOCK_ID})"))


def start_scheduler() -> AsyncIOScheduler | None:
    """Starts the background scheduler. Returns None (and logs, doesn't
    raise) if DATABASE_URL isn't configured — matches this project's
    existing pattern of degrading gracefully instead of crashing app
    startup when an optional dependency is missing (see search_service.py's
    mock-fallback pattern)."""
    global _scheduler
    if engine is None:
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
