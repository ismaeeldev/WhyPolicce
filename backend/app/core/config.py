from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = ""
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


settings = Settings()
