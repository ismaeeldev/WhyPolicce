# WhyPolice

An AI-search product: ask a question, watch the answer stream in live.

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose) — for the one-command run below
- Node.js 22+ and Python 3.12+ — only needed if you'd rather run each service without Docker (see [Running without Docker](#running-without-docker))
- An Auth0 tenant (Regular Web Application + an API) — see [Environment variables](#environment-variables)
- A Neon Postgres database (or use the local SQLite fallback for testing without one)

## Quick start (Docker)

1. Copy the example env files and fill in real values:

   ```bash
   cp frontend/.env.example frontend/.env.local
   cp backend/.env.example backend/.env
   ```

   See [Environment variables](#environment-variables) below for what each value is and where to get it.

2. Build and start both services:

   ```bash
   docker-compose up --build
   ```

3. Open **http://localhost:3000**. The frontend talks to the backend at `http://localhost:8000`.

To stop everything: `docker-compose down` (add `-v` to also remove the containers' volumes, if any get created later).

## Environment variables

**Committed to GitHub:** `frontend/.env.example` and `backend/.env.example` — safe
templates with every variable documented. **Never commit** real `.env` or `.env.local`
files (they stay in `.gitignore`).

Copy the examples locally, then fill in real values:

```bash
cp frontend/.env.example frontend/.env.local
cp backend/.env.example backend/.env
```

For production, the client sets these in **Vercel** (frontend) and **Google Cloud Run /
Secret Manager** (backend). See [`DEPLOYMENT.md`](./DEPLOYMENT.md) for the full checklist.

### `frontend/.env.local`

| Variable | Where to get it |
|---|---|
| `AUTH0_DOMAIN` | Auth0 Dashboard → Applications → Applications → your app → Domain |
| `AUTH0_CLIENT_ID` | Same page → Client ID |
| `AUTH0_CLIENT_SECRET` | Same page → Client Secret |
| `AUTH0_SECRET` | Generate yourself: `node -e "console.log(require('crypto').randomBytes(32).toString('hex'))"` |
| `AUTH0_AUDIENCE` | Auth0 Dashboard → Applications → APIs → your API → Identifier |
| `APP_BASE_URL` | `http://localhost:3000` for local dev |
| `STRIPE_PUBLISHABLE_KEY` | Stripe Dashboard → Developers → API keys (test mode) |
| `NEXT_PUBLIC_BACKEND_URL` | `http://localhost:8000` — the URL the *browser* reaches the backend at (see the comment in `docker-compose.yml` for why this is never an internal Docker hostname) |

**Auth0 app settings** — on the same Application's Settings page, set:
- Allowed Callback URLs: `http://localhost:3000/auth/callback`
- Allowed Logout URLs: `http://localhost:3000`
- Allowed Web Origins: `http://localhost:3000`

And authorize the app for your API: Applications → APIs → your API → Machine to Machine Applications tab → toggle your app **Authorized**.

### `backend/.env`

| Variable | Where to get it |
|---|---|
| `DATABASE_URL` | Neon Dashboard → your project → Connection Details. For local testing without Neon: `sqlite:///./test_local.db` |
| `AUTH0_DOMAIN` / `AUTH0_AUDIENCE` | Must exactly match `frontend/.env.local`'s values |
| `STRIPE_SECRET_KEY` | Stripe Dashboard → Developers → API keys (test mode) |
| `STRIPE_PRICE_ID` | Stripe Dashboard → Products → your Pro plan price → Price ID |
| `STRIPE_WEBHOOK_SECRET` | Stripe Dashboard → Developers → Webhooks → your endpoint → Signing secret |
| `CORS_ALLOWED_ORIGINS` | Comma-separated list of allowed frontend origins — `http://localhost:3000` locally |
| `FRONTEND_URL` | The frontend's base URL, used for Stripe Checkout redirects |
| `RATE_LIMIT_PER_MINUTE` | Search requests allowed per user per minute — `20` is a sane default |
| `PORT` | The port the backend listens on — `8000` locally; Cloud Run sets this automatically in production |
| `OPENAI_API_KEY` | [platform.openai.com](https://platform.openai.com/) → API Keys. Primary AI search provider — leave empty (along with `GEMINI_API_KEY`) to fall back to an honest placeholder response instead of a real model call |
| `OPENAI_MODEL` | The OpenAI model id to use — defaults to `gpt-5-mini`. Env-configurable since model names/lineups shift over time |
| `GEMINI_API_KEY` | [aistudio.google.com/apikey](https://aistudio.google.com/apikey). Automatic fallback used on any OpenAI error (auth, rate limit, timeout, network, or a missing `OPENAI_API_KEY`) |
| `GEMINI_MODEL` | The Gemini model id to use — defaults to `gemini-3.5-flash` |

## Running without Docker

Backend:

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Frontend (in a second terminal):

```bash
cd frontend
npm install
npm run dev
```

Then open **http://localhost:3000**.

## Backend tests (offline)

Stripe billing can be verified without live Stripe keys — useful while the client
sets up their own deploy:

```bash
cd backend
pip install -r requirements.txt
python -m pytest tests/test_billing.py -v
```

Tests use an in-memory SQLite database and mock all Stripe SDK calls.

### Browser smoke test (public routes)

With the dev server running on port 3000:

```bash
cd frontend
npm install
npm run test:browser
```

Checks all public pages load, protected-route redirect, search chips, theme toggle, and mobile overflow.

## Project structure

```
frontend/   Next.js (App Router) — the web app
backend/    FastAPI — the API
```

See `AgentGuide/` for the full spec (scope, theme guidelines, application flow, build steps, and the live project-state tracker).

## Deployment

**Client handoff:** start with [`CLIENT_DEPLOYMENT_GUIDE.md`](./CLIENT_DEPLOYMENT_GUIDE.md) — env var status, Docker smoke test, and step-by-step deploy order.

Technical `gcloud` commands and production bug sweep: [`DEPLOYMENT.md`](./DEPLOYMENT.md).
