# Arriendate Intelligence

An internal real-estate operating layer for turning an unstructured lead into traceable CRM data and, in later milestones, grounded property recommendations.

> Current milestone: synthetic property inventory + lead intake + durable original lead record.

The repository is intentionally incremental. There is no simulated AI output, automatic outreach, RAG, orchestration, or quantum code in this slice.

## Business problem

Real-estate teams spend time reading inconsistent lead messages, re-entering requirements, and explaining why a property may fit. Arriendate Intelligence is designed to make that flow structured and auditable without allowing a model to override database facts.

The current slice establishes the trustworthy first boundary:

```text
original lead message → server validation → persistent CRM record → human-readable detail
synthetic inventory   → server filters    → inventory/detail UI
```

The original request is persisted before any future AI processing. Optional contact fields are supported for the demo, and lead creation is idempotent to protect against duplicate browser retries.

## Architecture

```mermaid
flowchart LR
    Browser[React + TypeScript] -->|JSON /api| API[FastAPI]
    API --> Services[Domain services]
    Services --> Repositories[Repository adapters]
    Repositories --> DB[(Supabase PostgreSQL)]
    Repositories -. local fallback .-> SQLite[(SQLite)]
    DB --- Vector[pgvector reserved for Phase 1]
```

- The browser never receives a database password or privileged Supabase key.
- FastAPI is the only browser-facing data boundary.
- SQL under `supabase/migrations` is the source of truth for the production schema.
- SQLite exists only as a zero-install local/test adapter because Docker is unavailable on the current workstation.
- Domain services stay independent from HTTP and persistence details.

See [architecture decisions](docs/architecture.md), [AI guardrails](docs/ai-guardrails.md), and the approved [implementation plan](docs/implementation-plan.md).

## Technology

| Layer | Tools |
|---|---|
| Web | React, TypeScript strict mode, Vite, React Router, TanStack Query, React Hook Form, Zod |
| API | Python 3.12+, FastAPI, Pydantic v2, SQLAlchemy 2, psycopg 3 |
| Data | Supabase PostgreSQL, Row Level Security, pgvector; SQLite local fallback |
| Testing | Pytest, Ruff, mypy, Vitest, Testing Library |

## Repository map

```text
apps/web/                 React internal-tool UI
apps/api/                 FastAPI application and tests
supabase/migrations/      versioned PostgreSQL schema
supabase/seed/            18 synthetic Chilean property records
docs/                     architecture, guardrails and implementation plan
evals/                    reserved evaluation datasets/results
```

## Local setup

Prerequisites:

- Node.js 22+
- Python 3.12+
- Optional for the official database: Docker and the project-scoped Supabase CLI

From the repository root in PowerShell:

```powershell
Copy-Item .env.example .env
npm.cmd install
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e ".\apps\api[dev]"
```

Start the API in one terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir apps/api --reload --host 127.0.0.1 --port 8000
```

Start the web app in another:

```powershell
npm.cmd run dev:web
```

Open `http://127.0.0.1:5173`. API documentation is available at `http://127.0.0.1:8000/docs`.

Without an `.env`, the API still uses the local SQLite fallback at `.local/arriendate.db` and inserts the 18 deterministic synthetic properties on first startup.

### Running with local Supabase

When Docker is installed:

```powershell
npm.cmd exec supabase -- start
npm.cmd exec supabase -- db reset
```

Then configure:

```dotenv
ARRIENDATE_DATABASE_URL=postgresql+psycopg://postgres:postgres@127.0.0.1:54322/postgres
```

Migrations run before `supabase/seed/properties.sql`. The seed file contains data only and can be reapplied safely by deterministic UUID.

## Environment variables

| Variable | Scope | Purpose |
|---|---|---|
| `ARRIENDATE_DATABASE_URL` | server | SQLAlchemy database connection |
| `ARRIENDATE_CORS_ORIGINS` | server | explicit browser origin allowlist as JSON |
| `ARRIENDATE_SEED_DEMO_DATA` | server | seed an empty local development database |
| `VITE_API_URL` | browser-safe | public base URL for FastAPI |

AI variables in `.env.example` are placeholders for the next milestone and are unused now. Never put secrets in variables prefixed with `VITE_`.

## API in this slice

| Method | Path | Behavior |
|---|---|---|
| `GET` | `/api/health` | database readiness |
| `POST` | `/api/leads` | validate and persist original lead text; requires `Idempotency-Key` UUID header |
| `GET` | `/api/leads/{id}` | retrieve the durable lead record |
| `GET` | `/api/properties` | paginated inventory with operation, city, and availability filters |
| `GET` | `/api/properties/{id}` | full property facts without embedding fields |

## Quality checks

```powershell
# Backend
.\.venv\Scripts\python.exe -m ruff check apps/api
.\.venv\Scripts\python.exe -m mypy apps/api/app
.\.venv\Scripts\python.exe -m pytest apps/api/tests -q

# Frontend
npm.cmd run typecheck:web
npm.cmd run lint:web
npm.cmd run test:web
npm.cmd run test:e2e  # requires the local API/web processes and Microsoft Edge
npm.cmd run build:web
```

Backend integration tests use a disposable SQLite database and the same service/repository boundary. Live Supabase verification remains pending until Docker is available.

## Guardrails already enforced

- Inventory and contact examples are synthetic; no scraped or client records are included.
- Missing property values remain `null` and are displayed as “Por confirmar.”
- Lead text is rendered as text, never as injected HTML.
- Direct `anon` and `authenticated` table privileges are revoked in the Supabase migration.
- RLS is enabled from the first migration.
- Browser requests never log or expose database credentials.
- No external message can be drafted or sent in this slice.

## Known limitations

- Authentication is not implemented. The app binds locally by default and is not ready for public deployment.
- Supabase migrations and RLS could not be executed on this machine because Docker is absent; SQLite validates the application flow only.
- Structured extraction, hybrid filtering, embeddings, match scoring, explanations, follow-up drafts, and evaluation metrics are deliberately not implemented yet.
- The dashboard does not invent lead counts: a list/aggregate endpoint will arrive with the CRM status milestone.

## Next milestone

Implement strict structured lead extraction with a fake provider for tests, a real OpenAI-compatible adapter, versioned prompts, `ai_runs` observability, and clear human-visible failure states. Matching begins only after extraction is schema-valid and persisted.
