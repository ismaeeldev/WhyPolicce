# WhyPolice backend — AgentGuide/03_MasterPromptGuide.md Step 9.
# Multi-stage build. Uses python:3.12-slim (Debian/glibc), not -alpine —
# psycopg2-binary and python-jose[cryptography] both ship prebuilt manylinux
# wheels that work out of the box on glibc but commonly fail to install (or
# require a full C toolchain) on musl-based Alpine images.

# ---- deps: build a wheelhouse once, cached unless requirements.txt changes ----
FROM python:3.12-slim AS deps
WORKDIR /app
# build-essential covers the rare dependency without a prebuilt manylinux
# wheel for this exact Python/platform combo — costs nothing in the final
# image size since this whole stage is discarded after the wheels are built.
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
  && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /wheels -r requirements.txt

# ---- runner: minimal final image, only the installed deps + app code ----
FROM python:3.12-slim AS runner
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system app && useradd --system --gid app app

COPY --from=deps /wheels /wheels
COPY requirements.txt .
RUN pip install --no-cache-dir --no-index --find-links=/wheels -r requirements.txt \
  && rm -rf /wheels

COPY app ./app

RUN chown -R app:app /app
USER app

# Cloud Run (Step 10) injects PORT at runtime and expects the container to
# listen on it, not a hardcoded port — default to 8000 for local/compose
# runs when PORT isn't set. The shell form of CMD is required here (not the
# exec-form array) specifically so $PORT actually expands; the array form
# would pass the literal string "$PORT" to uvicorn instead of its value.
EXPOSE 8000
ENV PORT=8000
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --workers 2
