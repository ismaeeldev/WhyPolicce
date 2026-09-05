"""Per-user sliding-window rate limiter for POST /api/search/stream.

Minimal in-memory implementation for MVP (single-process deployment is fine on
Cloud Run's current scale). Full wiring into the search router happens in
Step 5 — this module is real and testable now, not a dead stub, per the
Step 0.5 scaffolding instructions.

TODO (Step 5): call `check_rate_limit(user_id)` at the top of
POST /api/search/stream, before any streaming begins. On failure, return
HTTP 429 with the standard {"error": "rate_limited", "message": ...,
"retryAfterSeconds": ...} shape per AgentGuide/02_ApplicationFlow.md §5.1.
"""

import time
from collections import defaultdict

from app.core.config import settings

_WINDOW_SECONDS = 60
_request_log: dict[str, list[float]] = defaultdict(list)

# Found during hardening: every distinct user who has ever searched, even
# once, left a permanent key in _request_log for the rest of the process's
# life — the per-user timestamp list self-trims to empty, but the dict
# entry itself was never removed. Confirmed directly: 10,000 distinct
# users each searching once left 10,000 permanent dict entries. A real,
# if slow, unbounded memory growth for a long-running process serving
# many distinct real users over time. Fixed with periodic sweeps (not
# every call, to keep the common path cheap) that drop any user's entry
# once their timestamp list is genuinely empty.
_SWEEP_INTERVAL_CALLS = 1000
_calls_since_sweep = 0


def _sweep_stale_entries(now: float) -> None:
    window_start = now - _WINDOW_SECONDS
    stale_users = [
        user_id
        for user_id, timestamps in _request_log.items()
        if not any(t > window_start for t in timestamps)
    ]
    for user_id in stale_users:
        del _request_log[user_id]


class RateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Rate limit exceeded, retry after {retry_after_seconds}s")


def check_rate_limit(user_id: str) -> None:
    """Raises RateLimitExceeded if user_id has exceeded settings.RATE_LIMIT_PER_MINUTE
    requests within the trailing 60-second window. Otherwise records this request."""
    global _calls_since_sweep

    now = time.monotonic()
    window_start = now - _WINDOW_SECONDS
    timestamps = [t for t in _request_log[user_id] if t > window_start]

    if len(timestamps) >= settings.RATE_LIMIT_PER_MINUTE:
        oldest = min(timestamps)
        retry_after = max(1, int(_WINDOW_SECONDS - (now - oldest)))
        _request_log[user_id] = timestamps
        raise RateLimitExceeded(retry_after_seconds=retry_after)

    timestamps.append(now)
    _request_log[user_id] = timestamps

    _calls_since_sweep += 1
    if _calls_since_sweep >= _SWEEP_INTERVAL_CALLS:
        _calls_since_sweep = 0
        _sweep_stale_entries(now)
