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

from app.core.config import settings

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
    "official statement you are not actually certain of. You do not have "
    "a live connection to any police department, court, or municipal "
    "database — for anything time-sensitive or jurisdiction-specific (a "
    "tonight's curfew, a live case status, an active incident), say plainly "
    "that you don't have real-time/verified access to that record and "
    "point the user to the right kind of official source (the city or "
    "county government site, the relevant police department's public "
    "records or non-emergency line) instead of guessing a specific answer. "
    "If someone asks something unrelated to public safety, still answer it "
    "helpfully and accurately — don't refuse or lecture them about scope — "
    "just don't force a public-safety angle onto a question that has none."
)

DEEP_SEARCH_SUFFIX = (
    " This is a 'deep search' request — go further than a quick answer: "
    "consider multiple angles, add relevant context and nuance, and be "
    "genuinely thorough while staying clear and well-organized."
)

_STANDARD_MAX_TOKENS = 4096
_DEEP_SEARCH_MAX_TOKENS = 8192


def _build_system_prompt(deep_search: bool, memory_notes: list[str]) -> str:
    system = SYSTEM_PROMPT + (DEEP_SEARCH_SUFFIX if deep_search else "")
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
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
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
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
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
    prompt: str, deep_search: bool = False, memory_notes: list[str] | None = None
) -> AsyncGenerator[str, None]:
    """Yields the answer text chunk-by-chunk.

    Provider order: OpenAI (primary) -> Gemini (fallback, on ANY OpenAI
    error including a missing key) -> honest mock (if Gemini is also
    unconfigured/failing). Only a genuine Gemini failure — not the initial
    OpenAI failure that triggered the fallback — propagates to the caller
    (app/routers/search.py), which already converts it into the standard
    SSE error event; a first-provider failure is expected/handled here, not
    a bug to surface.
    """
    notes = memory_notes or []
    system = _build_system_prompt(deep_search, notes)
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
