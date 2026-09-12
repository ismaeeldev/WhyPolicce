from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = ""
    # Real production-reliability bug found and fixed during a data-accuracy
    # audit (plan.md "Data-accuracy audit"): the weekly scheduled sync
    # (app/services/scheduler.py) coordinates against overlapping runs with
    # a Postgres session-level advisory lock (pg_try_advisory_lock). Session
    # -level advisory locks are tied to the specific physical backend
    # connection that acquired them — confirmed live, not assumed, that
    # Neon's pooled `-pooler` endpoint (this app's normal DATABASE_URL, used
    # for short request-scoped connections) can silently reassign/recycle
    # that physical backend mid-session, which drops the lock without the
    # app ever seeing an error. A long-running, many-minutes sync is exactly
    # the kind of session this can happen to. Neon's own direct (non-pooled)
    # endpoint — the same hostname with `-pooler` removed — holds one stable
    # physical connection for its whole duration, which session-level
    # advisory locks require. Optional explicit override for deployments
    # whose hostname doesn't follow the `-pooler` naming convention; falls
    # back to deriving it from DATABASE_URL (see database_url_direct below)
    # when unset, so most deployments need no extra configuration.
    DATABASE_URL_DIRECT: str = ""
    AUTH0_DOMAIN: str = ""
    AUTH0_AUDIENCE: str = ""
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PRICE_ID: str = ""  # Pro plan's Stripe Price id — set once the client creates it
    STRIPE_WEBHOOK_SECRET: str = ""  # signing secret for POST /api/billing/webhook
    CORS_ALLOWED_ORIGINS: str = "http://localhost:3000"
    FRONTEND_URL: str = "http://localhost:3000"  # Stripe Checkout success/cancel redirect target
    RATE_LIMIT_PER_MINUTE: int = 20
    PORT: int = 8000
    # Real LLM integration (AgentGuide/00_SCOPE.md §6). Client-directed
    # 2026-08-27: OpenAI (small model) is primary, Gemini is the fallback
    # used on ANY OpenAI API error (auth, rate limit, timeout, network) —
    # not just a missing key. Both keys empty by default: search gracefully
    # falls back to the honest mock/template generator rather than crashing
    # or faking a response, matching this project's existing
    # Stripe-not-configured pattern. Model ids are env-configurable rather
    # than hardcoded — provider model names/lineups shift over time, so a
    # stale default should be a one-line env fix, not a code change.
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-5-mini"
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.5-flash"

    # RAG pipeline (AgentGuide/revision2.md). Embeddings are OpenAI-only for
    # now (no Gemini fallback here, unlike stream_answer) — text-embedding-3-small
    # outputs 1536 dims, matching app/models/public_record.py's Vector(1536)
    # column exactly. If this model ever changes, the column dimension must
    # be migrated too, not just this value.
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ALLOWED_ORIGINS.split(",") if origin.strip()]

    @property
    def database_url_direct(self) -> str:
        """Non-pooled connection string for long-running sessions that need
        a stable physical backend (currently: the scheduler's sync session
        — see DATABASE_URL_DIRECT's comment above for why). Explicit
        DATABASE_URL_DIRECT wins if set; otherwise derived from
        DATABASE_URL by stripping Neon's `-pooler` hostname segment. If
        DATABASE_URL doesn't contain `-pooler` (already direct, or a
        non-Neon/non-pooled provider), this is just DATABASE_URL unchanged
        — safe no-op rather than a broken derived URL."""
        if self.DATABASE_URL_DIRECT:
            return self.DATABASE_URL_DIRECT
        return self.DATABASE_URL.replace("-pooler.", ".", 1)


settings = Settings()
