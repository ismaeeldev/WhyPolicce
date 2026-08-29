"""Live AI search smoke test — hits the running backend with a real Auth0 token.

Usage (backend must be running on :8000):
    python scripts/test_search_live.py
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import httpx

# Load backend .env for Auth0 domain; frontend .env.local for client creds.
BACKEND_ENV = Path(__file__).resolve().parents[1] / ".env"
FRONTEND_ENV = Path(__file__).resolve().parents[2] / "frontend" / ".env.local"


def _load_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        out[k.strip()] = v.strip()
    return out


def get_auth0_token(domain: str, client_id: str, client_secret: str, audience: str) -> str:
    resp = httpx.post(
        f"https://{domain}/oauth/token",
        json={
            "client_id": client_id,
            "client_secret": client_secret,
            "audience": audience,
            "grant_type": "client_credentials",
        },
        timeout=15.0,
    )
    resp.raise_for_status()
    token = resp.json().get("access_token")
    if not token:
        raise RuntimeError("No access_token in Auth0 response")
    return token


def parse_sse(text: str) -> list[dict]:
    events: list[dict] = []
    for block in text.split("\n\n"):
        for line in block.splitlines():
            if line.startswith("data: "):
                try:
                    events.append(json.loads(line[6:]))
                except json.JSONDecodeError:
                    pass
    return events


def run_query(client: httpx.Client, token: str, prompt: str) -> tuple[bool, str]:
    started = time.perf_counter()
    with client.stream(
        "POST",
        "http://localhost:8000/api/search/stream",
        headers={"Authorization": f"Bearer {token}"},
        json={"prompt": prompt, "deepSearch": False},
        timeout=120.0,
    ) as res:
        if res.status_code != 200:
            body = res.read().decode()
            return False, f"HTTP {res.status_code}: {body[:200]}"

        chunks: list[str] = []
        buf = ""
        for raw in res.iter_bytes():
            buf += raw.decode("utf-8", errors="replace")
            while "\n\n" in buf:
                block, buf = buf.split("\n\n", 1)
                for ev in parse_sse(block + "\n\n"):
                    if ev.get("type") == "token":
                        chunks.append(ev.get("data", ""))
                    elif ev.get("type") == "error":
                        return False, ev.get("message", "stream error")
                    elif ev.get("type") == "done":
                        answer = "".join(chunks).strip()
                        ms = int((time.perf_counter() - started) * 1000)
                        return bool(answer), f"{answer[:120]}… ({ms}ms)"

        answer = "".join(chunks).strip()
        if answer:
            ms = int((time.perf_counter() - started) * 1000)
            return True, f"{answer[:120]}… ({ms}ms, no done event)"
        return False, "empty stream"


def main() -> int:
    backend = _load_env(BACKEND_ENV)
    frontend = _load_env(FRONTEND_ENV)

    domain = backend.get("AUTH0_DOMAIN") or frontend.get("AUTH0_DOMAIN", "")
    audience = backend.get("AUTH0_AUDIENCE") or frontend.get("AUTH0_AUDIENCE", "")
    client_id = frontend.get("AUTH0_CLIENT_ID", "")
    client_secret = frontend.get("AUTH0_CLIENT_SECRET", "")

    if not all([domain, audience, client_id, client_secret]):
        print("Missing Auth0 env vars for token fetch")
        return 1

    try:
        token = get_auth0_token(domain, client_id, client_secret, audience)
    except Exception as exc:
        print(f"Auth0 token fetch failed: {exc}")
        return 1

    queries = [
        "What is 2+2?",
        "What is the capital of France?",
        "Why do cats knead blankets?",
        "Explain the James Webb deep field image in one sentence.",
    ]

    passed = 0
    with httpx.Client() as client:
        health = client.get("http://localhost:8000/api/health", timeout=5.0)
        if health.status_code != 200:
            print(f"Backend health check failed: {health.status_code}")
            return 1
        print("✓ Backend health OK")

        for q in queries:
            ok, detail = run_query(client, token, q)
            mark = "✓" if ok else "✗"
            print(f"{mark} {q} — {detail}")
            if ok:
                passed += 1

    print(f"\n{passed}/{len(queries)} search queries passed")
    return 0 if passed == len(queries) else 1


if __name__ == "__main__":
    sys.exit(main())
