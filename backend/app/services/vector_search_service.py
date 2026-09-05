"""Semantic similarity search over ingested public records — AgentGuide/
revision2.md Phase 1/3.

Given a user's query string, embeds it and finds the most similar
PublicRecord rows via pgvector's cosine-distance operator (`<=>`). Used at
query time by search_service.py (Phase 3) to retrieve real records before
building the LLM prompt.
"""

import logging

from sqlmodel import Session, select

from app.models.public_record import PublicRecord
from app.services.embedding_service import embed_text

logger = logging.getLogger(__name__)

# Cosine distance is 0 (identical) to 2 (opposite); pgvector's <=> operator
# returns distance, not similarity, so LOWER is a better match.
#
# Calibrated against a real test (see revision2.md Phase 1 verification,
# using text-embedding-3-small): a genuinely relevant match ("Was there a
# violent assault reported recently?" vs. a real felony-assault record
# summary) measured 0.512, while unrelated records (a parking ticket, a
# weather forecast) measured 0.677 and 0.933 respectively. 0.5 was tried
# first and wrongly excluded the true match — 0.6 is the smallest round
# threshold that includes it while still excluding both unrelated
# examples. Re-tune once Phase 2's real NYC data is ingested and tested
# against a wider range of real user-style questions — this is one
# calibration data point, not a final, fully-proven value.
MAX_RELEVANT_DISTANCE = 0.6

DEFAULT_TOP_K = 5


async def find_relevant_records(
    session: Session, query: str, top_k: int = DEFAULT_TOP_K
) -> list[PublicRecord]:
    """Returns up to top_k PublicRecord rows relevant to the query, ordered
    by relevance (closest first). Returns an empty list if nothing is
    close enough (per MAX_RELEVANT_DISTANCE) — callers (search_service.py)
    must treat an empty list as "no real data available," not an error,
    since that's the expected, correct outcome for any query outside the
    currently-ingested cities/datasets (e.g. a non-NYC question while only
    NYC data has been ingested)."""
    query_embedding = await embed_text(query)

    distance_col = PublicRecord.embedding.cosine_distance(query_embedding)
    statement = (
        select(PublicRecord, distance_col.label("distance"))
        .order_by(distance_col)
        .limit(top_k)
    )
    rows = session.exec(statement).all()

    relevant = [record for record, distance in rows if distance <= MAX_RELEVANT_DISTANCE]
    logger.info(
        "vector search: query=%r candidates=%d relevant=%d (threshold=%.2f)",
        query[:80],
        len(rows),
        len(relevant),
        MAX_RELEVANT_DISTANCE,
    )
    return relevant
