import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.security import AuthenticatedUser, get_current_user
from app.core.timeutil import to_utc_iso
from app.models.memory import MemoryNote
from app.models.user import User
from app.schemas.memory import MemoryNoteCreate, MemoryNoteUpdate

router = APIRouter(prefix="/api/memory")

_NOT_FOUND = HTTPException(
    status_code=404, detail={"error": "not_found", "message": "Memory note not found."}
)


def _parse_note_id(raw: str) -> uuid.UUID:
    """Same pattern as search.py's _parse_session_id — a malformed id must
    404 cleanly, not 500 on a raw driver error."""
    try:
        return uuid.UUID(raw)
    except (ValueError, AttributeError, TypeError):
        raise _NOT_FOUND from None


def _get_or_create_user(session: Session, current: AuthenticatedUser) -> User:
    """Duplicated from search.py rather than imported, same reasoning: this
    router must work even if /api/me was never called first.
    IntegrityError guard matches users.py's own copy — a genuine
    concurrent "first request ever" race for the same auth0_sub must
    return the winner's row, not bubble up as a 500."""
    user = session.exec(select(User).where(User.auth0_sub == current.auth0_sub)).first()
    if user is None:
        user = User(auth0_sub=current.auth0_sub, email=current.email or "")
        session.add(user)
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            user = session.exec(select(User).where(User.auth0_sub == current.auth0_sub)).first()
            if user is None:
                raise
        else:
            session.refresh(user)
    elif current.email and not user.email:
        # Same self-heal as GET /api/me — see app/routers/users.py's comment.
        user.email = current.email
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def _note_out(note: MemoryNote) -> dict:
    return {
        "id": str(note.id),
        "content": note.content,
        "createdAt": to_utc_iso(note.created_at),
        "updatedAt": to_utc_iso(note.updated_at),
    }


@router.get("")
def list_notes(
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> list[dict]:
    user = _get_or_create_user(session, current)
    notes = session.exec(
        select(MemoryNote)
        .where(MemoryNote.user_id == user.id)
        .order_by(MemoryNote.created_at.desc())
    ).all()
    return [_note_out(n) for n in notes]


@router.post("", status_code=201)
def create_note(
    body: MemoryNoteCreate,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    user = _get_or_create_user(session, current)
    note = MemoryNote(user_id=user.id, content=body.content)
    session.add(note)
    session.commit()
    session.refresh(note)
    return _note_out(note)


@router.patch("/{note_id}")
def update_note(
    note_id: str,
    body: MemoryNoteUpdate,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    user = _get_or_create_user(session, current)
    note = session.get(MemoryNote, _parse_note_id(note_id))
    if note is None or note.user_id != user.id:
        raise _NOT_FOUND
    note.content = body.content
    note.updated_at = datetime.now(timezone.utc)
    session.add(note)
    session.commit()
    session.refresh(note)
    return _note_out(note)


@router.delete("/{note_id}")
def delete_note(
    note_id: str,
    current: AuthenticatedUser = Depends(get_current_user),
    session: Session = Depends(get_session),
) -> dict:
    # 200 + body, not bare 204 — matches DELETE /api/search/history's
    # precedent and avoids breaking frontend/lib/api-client.ts's apiFetch,
    # which unconditionally calls res.json() on every response.
    user = _get_or_create_user(session, current)
    note = session.get(MemoryNote, _parse_note_id(note_id))
    if note is None or note.user_id != user.id:
        raise _NOT_FOUND
    session.delete(note)
    session.commit()
    return {"deleted": True}
