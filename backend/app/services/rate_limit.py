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


class RateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Rate limit exceeded, retry after {retry_after_seconds}s")


def check_rate_limit(user_id: str) -> None:
    """Raises RateLimitExceeded if user_id has exceeded settings.RATE_LIMIT_PER_MINUTE
    requests within the trailing 60-second window. Otherwise records this request."""
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
