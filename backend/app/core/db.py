from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.core.config import settings

engine = create_engine(settings.DATABASE_URL, echo=False) if settings.DATABASE_URL else None


def get_session() -> Generator[Session, None, None]:
    if engine is None:
        raise RuntimeError("DATABASE_URL is not configured — set it in backend/.env")
    with Session(engine) as session:
        yield session


def create_db_and_tables() -> None:
    if engine is None:
        return
    SQLModel.metadata.create_all(engine)
