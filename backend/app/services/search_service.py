"""AI search answer generator — AgentGuide/00_SCOPE.md §6.

Client-directed 2026-08-27: OpenAI (small model, `OPENAI_MODEL`) is the
primary provider. On ANY OpenAI API error — auth failure, rate limit,
timeout, network error, or a missing `OPENAI_API_KEY` — this falls back to
Gemini (`GEMINI_MODEL`) automatically. If Gemini also isn't configured or
also fails, falls back to an honest mock/template response, matching this
project's existing Stripe-not-configured pattern (see app/routers/
billing.py) — the app never crashes and never fakes a real model's output;
it's explicit about which one is happening.
"""

import asyncio
import logging
from collections.abc import AsyncGenerator

from google import genai
from google.genai import types as genai_types
from openai import AsyncOpenAI
from sqlmodel import Session

from app.core.config import settings
from app.models.public_record import PublicRecord
from app.services.vector_search_service import find_relevant_records

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are WhyPolice, a calm, precise public safety knowledge assistant. "
    "You help people understand police reports, case statuses, municipal "
    "logs, curfews, and other public safety information. Answer the user's "
    "question directly — plain prose, no headers or bullet lists unless the "
    "content genuinely calls for structure, no meta-commentary about being "
    "an AI or how you generated the answer. Get straight to it. Stay "
    "factual and neutral — never speculate about a specific person's guilt "
    "or innocence, and never invent a specific case number, date, or "
    "official statement you are not actually certain of."
)

# Used when real records WERE retrieved (RAG pipeline, revision2.md Phase 3)
# — instructs the model to actually use and cite them, and to be explicit
# about the gap between "close semantic match" and "the exact record the
# user asked about" (verified during Phase 2 testing: a location-specific
# query can surface a same-offense-type record from a different borough
# when no exact match exists — the model must not blur that distinction).
#
# Real bug found and fixed (Revision 3 Step 9, multi-city expansion): this
# used to hardcode "(from NYC Open Data's NYPD complaint/arrest datasets)"
# — correct back when NYC was the only ingested city, but actively wrong
# and misleading once Chicago/LA/Seattle/etc. records exist too. Confirmed
# directly: a real "Any recent incidents in Chicago?" query correctly
# retrieved 2 genuine Chicago records, but the model still answered "I
# don't have Chicago records" — traced to this exact hardcoded NYC claim
# in its own system prompt, which it was (correctly) trusting over the
# literal record text. Each record's own summary text already states its
# real city/precinct/date (see every ingestion module's _summarize_*), so
# the instruction no longer needs to (and must not) assert a single source
# city itself.
RAG_RECORDS_INSTRUCTION = (
    "\n\nHere are real, retrieved public safety records that may be "
    "relevant to this question, from official public open-data sources "
    "for the specific city/agency named in each record below "
    "(not necessarily the same city across every record):\n{records_block}\n"
    "Use these records to answer if they're genuinely relevant — summarize "
    "what they actually say, don't invent details beyond them. Pay close "
    "attention to which city each record is actually from — a record from "
    "a different city than the one asked about is NOT a match, even if the "
    "offense type is similar; say so plainly rather than implying it's the "
    "record the user meant. If none of these records actually answer the "
    "question, say so honestly instead of forcing a connection."
)

# Used when NO records were retrieved (either nothing relevant exists yet
# for this query, or it's outside the currently-ingested scope) — this is
# the original honest-limitation framing, kept for exactly this case
# rather than removed, since the underlying gap (no live connection to
# every police department/court) is still real for anything not yet
# ingested.
NO_RECORDS_INSTRUCTION = (
    " You do not have a live connection to any police department, court, "
    "or municipal database beyond what's provided above — for anything "
    "time-sensitive or jurisdiction-specific (a tonight's curfew, a live "
    "case status, an active incident) that isn't covered by a retrieved "
    "record, say plainly that you don't have real-time/verified access to "
    "that record and point the user to the right kind of official source "
    "(the city or county government site, the relevant police "
    "department's public records or non-emergency line) instead of "
    "guessing a specific answer."
    # Real gap found and fixed during a 20-question stability test batch
    # (plan.md "Test similar client questions"): "Compare crime between "
    # "Miami and Detroit" retrieved zero real records, so this branch
    # applied — but the model still gave a confident, detailed comparative
    # answer (violent-crime rates, drug-trafficking dynamics, NIBRS
    # reporting differences) drawn from its own general knowledge, with no
    # explicit statement that this wasn't from WhyPolice's own data. It
    # wasn't fabricated nonsense and it did point to the FBI Crime Data
    # Explorer as an authoritative source — but a user reading it next to
    # every other answer in this product (which DOES cite real, retrieved
    # records) could easily mistake it for one, since nothing in the reply
    # itself drew that distinction. This instruction previously only
    # covered the time-sensitive/jurisdiction-specific case explicitly —
    # extended to cover this broader "answering from general knowledge,
    # not this system's own data" case too.
    " If you answer using your own general knowledge rather than a "
    "retrieved record — e.g. general statistics, historical trends, or "
    "comparisons between cities — say so explicitly (e.g. 'this isn't "
    "from WhyPolice's own retrieved records, but generally...') so it's "
    "never confused with a cited, retrieved record."
)

OFF_TOPIC_INSTRUCTION = (
    " If someone asks something unrelated to public safety, still answer "
    "it helpfully and accurately — don't refuse or lecture them about "
    "scope — just don't force a public-safety angle onto a question that "
    "has none."
)


def _format_records_block(records: list[PublicRecord]) -> str:
    return "\n".join(f"- {r.raw_text}" for r in records)


def _build_citations(records: list[PublicRecord]) -> list[dict]:
    """Turns retrieved records into a de-duplicated, order-preserving list
    of real source citations for the UI (city + underlying data source,
    e.g. {"city": "Chicago", "source": "chicago_crimes"}) — the same
    (source, city) pair a record's own `_summarize_*` text already states
    in prose, just surfaced as structured data instead of requiring a user
    to parse it out of the answer text themselves. Multiple retrieved
    records from the same (city, source) collapse into one citation entry
    (a query can retrieve several records from the same dataset — the
    citation should say "here's where this came from," not repeat the
    same source N times)."""
    seen: set[tuple[str, str]] = set()
    citations: list[dict] = []
    for record in records:
        key = (record.city, record.source)
        if key in seen:
            continue
        seen.add(key)
        citations.append({"city": record.city, "source": record.source})
    return citations

DEEP_SEARCH_SUFFIX = (
    " This is a 'deep search' request — go further than a quick answer: "
    "consider multiple angles, add relevant context and nuance, and be "
    "genuinely thorough while staying clear and well-organized."
)

_STANDARD_MAX_TOKENS = 4096
_DEEP_SEARCH_MAX_TOKENS = 8192

# Found during hardening: both the OpenAI and Gemini SDKs default to very
# long client-side timeouts (OpenAI: 600s read timeout + 2 automatic
# retries; Gemini: SDK/httpx defaults, similarly generous) — under real
# concurrent load, a single stuck/degraded provider call could hold a
# request (and its DB connection from the pool) open for many minutes
# with no user-facing feedback, and enough stuck requests could exhaust
# the whole connection pool and lock out every other user. 45s covers
# genuinely slow real responses (observed up to ~38s under a 10-concurrent-
# request stress test) with headroom, while still failing fast enough to
# trigger the existing OpenAI->Gemini->mock fallback chain instead of
# hanging indefinitely.
_PROVIDER_TIMEOUT_SECONDS = 45


def _build_system_prompt(
    deep_search: bool, memory_notes: list[str], retrieved_records: list[PublicRecord]
) -> str:
    system = SYSTEM_PROMPT
    if retrieved_records:
        system += RAG_RECORDS_INSTRUCTION.format(
            records_block=_format_records_block(retrieved_records)
        )
    else:
        system += NO_RECORDS_INSTRUCTION
    system += OFF_TOPIC_INSTRUCTION
    system += DEEP_SEARCH_SUFFIX if deep_search else ""
    if memory_notes:
        notes_block = "\n".join(f"- {n}" for n in memory_notes)
        system += (
            "\n\nThe user has saved these facts/preferences about themselves. "
            "Reference them naturally in your answer ONLY if genuinely "
            f"relevant to this specific question — never force it in:\n{notes_block}"
        )
    return system


def _build_mock_response(prompt: str, deep_search: bool, memory_notes: list[str]) -> str:
    """Honest fallback used when neither OPENAI_API_KEY nor GEMINI_API_KEY is
    configured — never presented as a real answer; the frontend and this
    text both make clear it's a placeholder."""
    intro = "Here's a deep, thorough answer to" if deep_search else "Here's what I found on"
    memory_line = ""
    if memory_notes:
        memory_line = f" (keeping in mind that {memory_notes[0]})"
    return (
        f"{intro} “{prompt}”{memory_line}. "
        "This is a template response — no AI provider is configured yet "
        "(OPENAI_API_KEY / GEMINI_API_KEY are both empty in backend/.env), "
        "so WhyPolice can't call a real model. The streaming mechanics "
        "you're seeing right now — tokens arriving live, one after "
        "another — are the real, production SSE pipeline; only the words "
        "themselves are a placeholder until a key is added."
    )


async def _stream_mock_answer(
    prompt: str, deep_search: bool, memory_notes: list[str]
) -> AsyncGenerator[str, None]:
    text = _build_mock_response(prompt, deep_search, memory_notes)
    words = text.split(" ")
    for i, word in enumerate(words):
        yield word + (" " if i < len(words) - 1 else "")
        await asyncio.sleep(0.04)


async def _stream_openai_answer(
    prompt: str, system: str, max_tokens: int
) -> AsyncGenerator[str, None]:
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY, timeout=_PROVIDER_TIMEOUT_SECONDS)
    stream = await client.responses.create(
        model=settings.OPENAI_MODEL,
        instructions=system,
        input=prompt,
        max_output_tokens=max_tokens,
        stream=True,
    )
    async for event in stream:
        if event.type == "response.output_text.delta":
            yield event.delta


async def _stream_gemini_answer(
    prompt: str, system: str, max_tokens: int
) -> AsyncGenerator[str, None]:
    client = genai.Client(
        api_key=settings.GEMINI_API_KEY,
        http_options=genai_types.HttpOptions(timeout=_PROVIDER_TIMEOUT_SECONDS * 1000),
    )
    stream = await client.aio.models.generate_content_stream(
        model=settings.GEMINI_MODEL,
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            system_instruction=system,
            max_output_tokens=max_tokens,
        ),
    )
    async for chunk in stream:
        if chunk.text:
            yield chunk.text


async def stream_answer(
    prompt: str,
    deep_search: bool = False,
    memory_notes: list[str] | None = None,
    db_session: Session | None = None,
    sources_out: list[dict] | None = None,
    state: str | None = None,
) -> AsyncGenerator[str, None]:
    """Yields the answer text chunk-by-chunk.

    Provider order: OpenAI (primary) -> Gemini (fallback, on ANY OpenAI
    error including a missing key) -> honest mock (if Gemini is also
    unconfigured/failing). Only a genuine Gemini failure — not the initial
    OpenAI failure that triggered the fallback — propagates to the caller
    (app/routers/search.py), which already converts it into the standard
    SSE error event; a first-provider failure is expected/handled here, not
    a bug to surface.

    db_session enables the RAG pipeline (revision2.md Phase 3): if
    provided, retrieves real matching PublicRecord rows before building
    the prompt. Optional (defaults to None, meaning no retrieval) so
    existing tests/callers that don't pass a session still work exactly
    as before — retrieval finding nothing relevant is the same as not
    attempting it, per _build_system_prompt's NO_RECORDS_INSTRUCTION path.

    sources_out is an optional caller-owned list this function appends
    real citation dicts to ({"city": ..., "source": ...}, de-duplicated,
    preserving retrieval order) as soon as retrieval completes — a
    generator can't also `return` a value, so a citations UI (real client-
    facing gap found and fixed post-Phase-31: answers previously showed no
    visible source/city attribution despite every answer being backed by
    real, retrieved public records) needs this side-channel instead of a
    second return value. Deliberately populated BEFORE the first chunk is
    yielded, not after streaming completes, so a caller can safely read it
    once the async generator is exhausted (mirrors how app/routers/
    search.py already reads `collected` after the loop) without needing to
    coordinate with in-progress streaming.

    state, Step 4/5 of the State Selector feature (real client-requested
    feature — see vector_search_service.CITY_TO_STATE's own docstring):
    an optional real 2-letter USPS code, already validated at the API
    boundary (app/schemas/search.py) against WhyPolice's actual real
    coverage before it ever reaches here. Passed straight through to
    find_relevant_records, which does the real scoping/filtering — this
    function stays a thin pass-through, same as deep_search/memory_notes."""
    notes = memory_notes or []

    retrieved_records: list[PublicRecord] = []
    if db_session is not None:
        try:
            retrieved_records = await find_relevant_records(db_session, prompt, state=state)
        except Exception:
            # A retrieval failure (embedding API error, DB issue) must not
            # break search entirely — degrade to the no-records path,
            # same honest-limitation behavior as before this pipeline
            # existed, rather than a hard 500 on the whole search.
            logger.warning("RAG retrieval failed, falling back to no-records prompt", exc_info=True)
            retrieved_records = []

    if sources_out is not None:
        sources_out.extend(_build_citations(retrieved_records))

    system = _build_system_prompt(deep_search, notes, retrieved_records)
    max_tokens = _DEEP_SEARCH_MAX_TOKENS if deep_search else _STANDARD_MAX_TOKENS

    if settings.OPENAI_API_KEY:
        try:
            chunks: list[str] = []
            async for chunk in _stream_openai_answer(prompt, system, max_tokens):
                chunks.append(chunk)
                yield chunk
            return
        except Exception:
            # Any OpenAI error (auth, rate limit, timeout, network) falls
            # back to Gemini per client direction — but only before any
            # output has reached the client. Once streaming has started,
            # switching providers mid-stream would duplicate/garble the
            # answer, so a failure past that point still propagates.
            if chunks:
                raise
            logger.warning("OpenAI search call failed, falling back to Gemini", exc_info=True)

    if settings.GEMINI_API_KEY:
        async for chunk in _stream_gemini_answer(prompt, system, max_tokens):
            yield chunk
        return

    async for chunk in _stream_mock_answer(prompt, deep_search, notes):
        yield chunk
