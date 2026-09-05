"""Text embedding generation — AgentGuide/revision2.md Phase 1.

Wraps OpenAI's embeddings endpoint. Kept as its own small service (not
folded into search_service.py) so the embedding model can be swapped
independently of the answer-generation model, and so ingestion code
(Phase 2) and query-time retrieval (Phase 3) share exactly one
implementation instead of two copies that could drift apart.

No Gemini fallback here, unlike search_service.py's stream_answer() — an
embedding's *dimension* must match app/models/public_record.py's
Vector(1536) column exactly, and OpenAI/Gemini embedding models don't
share a common output size. Silently falling back to a different model in
this service would produce a dimension mismatch and a hard DB error, not a
graceful degradation like the honest mock text in search_service.py — so a
missing/failing OPENAI_API_KEY here raises, rather than falls back.
"""

import logging

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

EMBEDDING_DIMENSIONS = 1536  # must match app/models/public_record.py's Vector(1536)

# Found during hardening (same reasoning as search_service.py's
# _PROVIDER_TIMEOUT_SECONDS): the OpenAI SDK's default 600s read timeout
# means a stuck embedding call could hang query-time retrieval for
# minutes — search_service.py's stream_answer() already catches a
# retrieval failure and degrades gracefully, but only once this raises,
# not before. Shorter than the answer-generation timeout since an
# embedding call is a much smaller/faster request under normal conditions.
_EMBEDDING_TIMEOUT_SECONDS = 20


async def embed_text(text: str) -> list[float]:
    """Returns a single embedding vector for the given text.

    Raises RuntimeError if OPENAI_API_KEY isn't configured — this is a
    hard dependency for both ingestion (Phase 2) and query-time retrieval
    (Phase 3), unlike search_service.py's answer generation which has an
    honest mock fallback for demo purposes.
    """
    if not settings.OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured — required for embeddings "
            "(RAG ingestion/retrieval), not just answer generation."
        )

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=_EMBEDDING_TIMEOUT_SECONDS)
    response = await client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=text,
    )
    embedding = response.data[0].embedding
    if len(embedding) != EMBEDDING_DIMENSIONS:
        # Would indicate EMBEDDING_MODEL was changed without migrating the
        # DB column — fail loudly here rather than let a dimension
        # mismatch surface later as an opaque DB insert error.
        raise RuntimeError(
            f"Embedding model {settings.EMBEDDING_MODEL!r} returned "
            f"{len(embedding)} dimensions, expected {EMBEDDING_DIMENSIONS}. "
            "app/models/public_record.py's Vector column must be migrated "
            "if the embedding model was intentionally changed."
        )
    return embedding


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Batch version — one API call for many texts, used by ingestion
    (Phase 2) to avoid one HTTP round-trip per record when syncing
    hundreds/thousands of rows."""
    if not settings.OPENAI_API_KEY:
        raise RuntimeError(
            "OPENAI_API_KEY is not configured — required for embeddings "
            "(RAG ingestion/retrieval), not just answer generation."
        )
    if not texts:
        return []

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=_EMBEDDING_TIMEOUT_SECONDS)
    response = await client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=texts,
    )
    embeddings = [item.embedding for item in response.data]
    for embedding in embeddings:
        if len(embedding) != EMBEDDING_DIMENSIONS:
            raise RuntimeError(
                f"Embedding model {settings.EMBEDDING_MODEL!r} returned "
                f"{len(embedding)} dimensions, expected {EMBEDDING_DIMENSIONS}."
            )
    return embeddings
