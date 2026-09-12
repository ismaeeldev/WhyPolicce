"""Shared fixtures for LIVE retrieval-quality regression tests — real
database, real pgvector embeddings, real OpenAI API calls.

Deliberately a SEPARATE directory from tests/, not a subfolder of it —
tests/conftest.py unconditionally forces DATABASE_URL to sqlite:// at
import time (before any app module loads), and pytest always imports
every conftest.py it finds before collecting tests, so a live-DB test
placed inside tests/ would silently run against SQLite instead of the
real database, or crash on the first pgvector-specific query. Keeping
this a sibling directory instead of a subdirectory of tests/ means
`pytest tests/` (the project's normal, fast, fully-offline CI-safe run)
can never accidentally pick these up, and `pytest tests_live/` is an
explicit, deliberate opt-in — run it yourself when you have real
credentials configured (a real Neon DATABASE_URL + a real
OPENAI_API_KEY in backend/.env), not as part of the default test suite.

Real gap this closes (found during a project-wide gap audit, plan.md):
every retrieval-quality bug found this session (Fakesburg/Wall Street
false citations, the multi-city/state-scoped retrieval bugs) was
verified once, live, by hand, and never captured as a permanent
regression test — so a future change could silently reintroduce any of
them with nothing to catch it. These tests exist specifically to lock
those real, already-found bugs in as permanent regressions, plus the
known-good calibration cases plan.md's own code comments cite by hand.
"""

import pytest


def pytest_collection_modifyitems(config, items):
    """Skip the whole live suite with a clear reason if DATABASE_URL
    isn't configured for a real Postgres database — rather than letting
    every test fail with a confusing connection error, or (worse) quietly
    running against no database at all.

    Checks app.core.config.settings, NOT os.environ — a real gotcha
    confirmed directly (not assumed): pydantic-settings' env_file support
    loads backend/.env into its own internal Settings object, it does
    NOT also populate os.environ, so an os.environ-based check here would
    always see an empty string and permanently skip this suite even with
    a perfectly real .env configured. This import is deliberately here
    (not at module level) so it only happens if this hook actually runs,
    keeping any import-time side effects scoped to collection time."""
    from app.core.config import settings

    if settings.DATABASE_URL.startswith("postgresql"):
        return
    skip_reason = (
        "tests_live/ requires a real DATABASE_URL (postgresql://...) — "
        "these are live retrieval-quality regression tests against the "
        "real database with real embeddings, not offline unit tests. "
        "Configure a real DATABASE_URL in backend/.env (the same one "
        "the running app itself uses) and re-run: pytest tests_live/"
    )
    skip_marker = pytest.mark.skip(reason=skip_reason)
    for item in items:
        item.add_marker(skip_marker)
