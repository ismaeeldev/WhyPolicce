import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

import app.models  # noqa: F401 — registers every model on SQLModel.metadata, see app/models/__init__.py
from app.core.config import settings
from app.core.db import create_db_and_tables
from app.routers import admin, billing, forum_billing, health, inquiries, media, memory, search, users
from app.services.scheduler import start_scheduler, stop_scheduler

logger = logging.getLogger("whypolice")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Table creation strategy: SQLModel's create_all, not Alembic — chosen for
    # MVP simplicity per AgentGuide/03_MasterPromptGuide.md Step 4's explicit
    # "your call, document why." No migration history is needed yet since the
    # schema hasn't shipped to production; revisit with Alembic once the app
    # is live and schema changes need to preserve existing data.
    create_db_and_tables()
    # RAG pipeline (AgentGuide/revision2.md Phase 2) — background NYC
    # Socrata sync. Degrades gracefully (logs, doesn't raise/crash startup)
    # if DATABASE_URL isn't configured, matching this project's existing
    # pattern for optional dependencies (see search_service.py's mock
    # fallback, billing.py's 501-until-configured Stripe routes).
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(title="WhyPolice API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """Flattens FastAPI's default {"detail": ...} wrapper into the standard
    {error, message} shape per AgentGuide/02_ApplicationFlow.md §5.1 — without
    this, HTTPException(detail={"error":..., "message":...}) would ship as
    {"detail": {"error":..., "message":...}}, not matching the contract."""
    if isinstance(exc.detail, dict) and "error" in exc.detail and "message" in exc.detail:
        content = exc.detail
    else:
        content = {"error": "http_error", "message": str(exc.detail)}
    return JSONResponse(status_code=exc.status_code, content=content, headers=exc.headers)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Pydantic body/query validation failures (e.g. an over-length prompt)
    default to FastAPI's own {"detail": [...]} array shape — flattened here
    to the same {error, message} contract as every other error path."""
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", [])[1:]) or "request"
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": f"{field}: {first.get('msg', 'invalid request')}",
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Every unhandled error returns the standard {error, message} shape —
    never a raw traceback, per AgentGuide/02_ApplicationFlow.md §5.1."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"error": "internal_error", "message": "Something went wrong. Please try again."},
    )


app.include_router(health.router)
app.include_router(users.router)
app.include_router(search.router)
app.include_router(memory.router)
app.include_router(billing.router)
app.include_router(inquiries.router)
app.include_router(admin.router)
app.include_router(media.router)
app.include_router(forum_billing.router)
