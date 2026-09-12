import json
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.security import AuthenticatedUser, get_current_user
from app.core.timeutil import to_utc_iso
from app.models.memory import MemoryNote
from app.models.search import MessageRole, SearchMessage, SearchSession
from app.models.user import Tier, User
from app.schemas.search import SearchStreamRequest
from app.services.rate_limit import RateLimitExceeded, check_rate_limit
from app.services.search_service import stream_answer
from app.services.vector_search_service import supported_states

router = APIRouter()

_NOT_FOUND = HTTPException(
    status_code=404, detail={"error": "not_found", "message": "Session not found."}
)


def _parse_session_id(raw: str) -> uuid.UUID:
    """A malformed session id (not a valid UUID) must 404 cleanly, not 500 —
    session.get() would otherwise raise a raw driver-level error on garbage input."""
    try:
        return uuid.UUID(raw)
    except (ValueError, AttributeError, TypeError):
        raise _NOT_FOUND from None


def _note_snippet(content: str, max_len: int = 40) -> str:
    """Memory notes have no separate "title" field (just free-text content),
    so the transparency line's "[note titles]" uses a truncated snippet —
    the same pattern SearchSession.title already uses for the first prompt."""
    return content if len(content) <= max_len else content[: max_len - 1].rstrip() + "…"


def _get_or_create_user(session: Session, current: AuthenticatedUser) -> User:
    """Same sync-on-first-call pattern as GET /api/me (app/routers/users.py) —
    duplicated here rather than imported, since /api/search/stream must work
    even if the frontend somehow calls it before ever calling /api/me."""
    user = session.exec(select(User).where(User.auth0_sub == current.auth0_sub)).first()
    if user is None:
        user = User(auth0_sub=current.auth0_sub, email=current.email or "")
        session.add(user)
        session.commit()
        session.refresh(user)
    elif current.email and not user.email:
        # Same self-heal as GET /api/me — see app/routers/users.py's comment.
        user.email = current.email
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


@router.get("/api/search/states")
def get_supported_states(
    current: AuthenticatedUser = Depends(get_current_user),
) -> list[dict]:
    """State Selector, Step 3 (real client-requested feature — their own
    pasted SearchBar draft hardcoded 5 placeholder states: NY/CA/TX/FL/IL).

    Returns the REAL, current list of states WhyPolice has actual
    integrated data for, derived live from vector_search_service's
    CITY_TO_STATE (Step 1/2) rather than a second hand-maintained list —
    so the frontend dropdown can never silently drift out of sync with
    real coverage as future city-expansion phases land. Auth-protected
    like every other /api/search/* route, even though this particular
    response has no per-user data — the page that consumes it is already
    behind auth, so there's no reason to introduce a new unauthenticated
    pattern just for this one endpoint.

    No `session` dependency needed — this is pure in-memory derivation
    from CITY_TO_STATE, no database read."""
    return [{"code": code, "name": name} for code, name in supported_states()]


@router.post("/api/search/stream")
async def search_stream(
    body: SearchStreamRequest,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    """SSE streaming endpoint — AgentGuide/02_ApplicationFlow.md §5.
    Rate limit and tier checks happen BEFORE any streaming begins, per §5.1."""
    user = _get_or_create_user(session, current)

    try:
        check_rate_limit(str(user.id))
    except RateLimitExceeded as exc:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "rate_limited",
                "message": "You're searching faster than we can keep up — try again shortly.",
                "retryAfterSeconds": exc.retry_after_seconds,
            },
        ) from exc

    if body.deepSearch and user.tier != Tier.pro:
        raise HTTPException(
            status_code=403,
            detail={
                "error": "upgrade_required",
                "message": "Deep search is a Pro feature.",
            },
        )

    # Create or reuse the session
    if body.sessionId:
        db_session = session.get(SearchSession, _parse_session_id(body.sessionId))
        if db_session is None or db_session.user_id != user.id:
            raise _NOT_FOUND
    else:
        db_session = SearchSession(user_id=user.id, title=body.prompt[:60])
        session.add(db_session)
        session.commit()
        session.refresh(db_session)

    user_message = SearchMessage(
        session_id=db_session.id,
        role=MessageRole.user,
        content=body.prompt,
        is_deep_search=body.deepSearch,
    )
    session.add(user_message)
    session.commit()

    # Memory context — Step 6.5, AgentGuide/00_SCOPE.md §2.3. The mock
    # generator only plausibly weaves in the first note's content (see
    # search_service._build_mock_response), so only that note's id is
    # recorded as "referenced" — recording every saved note's id here would
    # make the transparency line lie about what actually shaped the answer.
    memory_notes = session.exec(
        select(MemoryNote).where(MemoryNote.user_id == user.id).order_by(MemoryNote.created_at.desc())
    ).all()
    referenced_note_ids = [str(memory_notes[0].id)] if memory_notes else None
    referenced_snippets = [_note_snippet(memory_notes[0].content)] if memory_notes else []

    async def event_stream():
        collected = ""
        # Populated by stream_answer as soon as RAG retrieval completes
        # (before the first token is yielded) — see search_service.
        # stream_answer's sources_out docstring for why a generator needs
        # this side-channel rather than a second return value. Safe to
        # read after the loop below, same as `collected`.
        sources: list[dict] = []
        try:
            async for chunk in stream_answer(
                body.prompt,
                deep_search=body.deepSearch,
                memory_notes=[n.content for n in memory_notes],
                db_session=session,
                sources_out=sources,
                state=body.state,
            ):
                collected += chunk
                yield f"data: {json.dumps({'type': 'token', 'data': chunk})}\n\n"

            assistant_message = SearchMessage(
                session_id=db_session.id,
                role=MessageRole.assistant,
                content=collected,
                is_deep_search=body.deepSearch,
                memory_note_ids=referenced_note_ids,
                sources=sources or None,
            )
            session.add(assistant_message)
            session.commit()

            yield f"data: {json.dumps({'type': 'done', 'sessionId': str(db_session.id), 'memorySnippets': referenced_snippets, 'sources': sources})}\n\n"
        except Exception:
            yield f"data: {json.dumps({'type': 'error', 'message': 'Something went wrong while streaming the answer.'})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/search/history")
def get_history(
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[dict]:
    user = _get_or_create_user(session, current)
    sessions = session.exec(
        select(SearchSession)
        .where(SearchSession.user_id == user.id)
        .order_by(SearchSession.created_at.desc())
    ).all()
    # Deep-search flag surfaces as a tier badge on the history card per
    # ApplicationFlow §3.4 — a session used it if any of its messages did.
    deep_search_session_ids = set(
        session.exec(
            select(SearchMessage.session_id)
            .where(SearchMessage.session_id.in_([s.id for s in sessions]))
            .where(SearchMessage.is_deep_search == True)  # noqa: E712
        ).all()
    )
    # Real, previously-missing gap found via UI review (plan.md "Product/
    # quality work"): the source-citations feature already surfaces real
    # public-record attribution on the live answer view and the session-
    # detail replay view (SearchMessage.sources), but the history LIST
    # never showed it — a user scanning past searches had no way to tell
    # "this one found real records" from "this one didn't" without opening
    # each session individually. Same boolean-flag-per-session pattern as
    # isDeepSearch immediately above, not a new mechanism: a session
    # "has sources" if ANY of its messages does. SQLModel/Postgres's JSON
    # column can't be queried for "non-empty array" the same way a boolean
    # column can, so this pulls the raw sources column for the relevant
    # messages and checks truthiness in Python — the row count here is
    # bounded by one user's own message history, not a table scan.
    sources_by_session_id: dict = {}
    for session_id, sources in session.exec(
        select(SearchMessage.session_id, SearchMessage.sources).where(
            SearchMessage.session_id.in_([s.id for s in sessions])
        )
    ).all():
        if sources:
            sources_by_session_id[session_id] = True
    return [
        {
            "id": str(s.id),
            "title": s.title,
            "createdAt": to_utc_iso(s.created_at),
            "isDeepSearch": s.id in deep_search_session_ids,
            "hasSources": sources_by_session_id.get(s.id, False),
        }
        for s in sessions
    ]


@router.get("/api/search/{session_id}")
def get_session_detail(
    session_id: str,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    user = _get_or_create_user(session, current)
    db_session = session.get(SearchSession, _parse_session_id(session_id))
    if db_session is None or db_session.user_id != user.id:
        raise _NOT_FOUND
    messages = session.exec(
        select(SearchMessage)
        .where(SearchMessage.session_id == db_session.id)
        .order_by(SearchMessage.created_at.asc())
    ).all()

    # Resolve referenced note ids back into display snippets for replay —
    # matches the live-stream "done" event's memorySnippets shape so
    # AnswerPanel renders identically live or replayed. A note referenced
    # by an old message but since deleted is silently omitted (its id
    # stays on the message for history, its content is just gone).
    referenced_ids = {
        note_id for m in messages if m.memory_note_ids for note_id in m.memory_note_ids
    }
    snippet_by_id: dict[str, str] = {}
    if referenced_ids:
        notes = session.exec(
            select(MemoryNote).where(MemoryNote.id.in_([uuid.UUID(i) for i in referenced_ids]))
        ).all()
        snippet_by_id = {str(n.id): _note_snippet(n.content) for n in notes}

    return {
        "id": str(db_session.id),
        "title": db_session.title,
        "messages": [
            {
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "isDeepSearch": m.is_deep_search,
                "memorySnippets": [
                    snippet_by_id[note_id]
                    for note_id in (m.memory_note_ids or [])
                    if note_id in snippet_by_id
                ],
                "sources": m.sources or [],
                "createdAt": to_utc_iso(m.created_at),
            }
            for m in messages
        ],
    }


@router.delete("/api/search/history")
def clear_history(
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    user = _get_or_create_user(session, current)
    sessions = session.exec(select(SearchSession).where(SearchSession.user_id == user.id)).all()
    for s in sessions:
        messages = session.exec(
            select(SearchMessage).where(SearchMessage.session_id == s.id)
        ).all()
        for m in messages:
            session.delete(m)
        session.delete(s)
    session.commit()
    return {"cleared": True}
