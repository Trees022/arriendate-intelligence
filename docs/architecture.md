# Architecture — Structured Lead Extraction Milestone

## Runtime boundaries

The React browser consumes JSON from FastAPI. FastAPI owns orchestration, strict validation, AI credentials, and database access. The browser has no direct Supabase or provider client.

```text
HTTP router → application service → provider protocol + domain validation → repository → database
```

- Routers translate HTTP values into typed request/response models.
- Services implement the extraction transaction and raise safe application errors.
- `StructuredGenerator` isolates provider-specific request/response shapes.
- Strict Pydantic models are the trust boundary between provider text and domain data.
- Repositories contain queries and persistence mechanics.
- Supabase SQL migrations define the authoritative PostgreSQL schema; SQLAlchemy also describes the portable SQLite subset.

No provider SDK type crosses into routes, repositories, or response schemas.

## Write paths

### Lead intake

1. The browser creates a UUID idempotency key and submits the original request.
2. `POST /api/leads` validates the body, preserving submitted text after only a whitespace-validity check.
3. The lead is committed with status `new` before any possible AI call.
4. Reusing a key with identical content returns the same row; different content returns `409`.

### Structured extraction

1. A human triggers `POST /api/leads/{id}/extract`.
2. The service commits an `ai_runs` record in `running` state before calling the provider, so an outage still leaves an observable attempt.
3. The versioned `lead-extraction-v1.0.0` prompt wraps `original_request` as JSON data and sends the strict `LeadRequirements` JSON Schema.
4. The adapter calls the Responses API with bounded transient retries and `store: false`.
5. The returned text is validated again with strict Pydantic rules, including enums, non-coercing numbers/booleans, unknown markers, ranges, duplicates, and extra-field rejection.
6. On success, requirements, lead status, and the successful run are committed together. Missing-information markers produce `needs_information`; otherwise the status becomes `qualified`.
7. On provider or validation failure, no requirement or lead-status change is applied. The run is marked failed with a bounded, sanitized code/message.

The service never repairs malformed output or promotes partially valid fields.

## Provider decision

The first real adapter targets the OpenAI-compatible Responses API directly through HTTPX. This keeps the application contract narrow, avoids leaking SDK models into the domain, and makes the exact HTTP payload testable with `MockTransport`.

The default `gpt-5.6-luna` model and low reasoning effort target routine, high-volume extraction; model, endpoint, retry limit, timeout, reasoning effort, and price inputs remain environment configuration. Strict Structured Outputs are requested through `text.format` and then independently enforced server-side. Official references: [model selection](https://developers.openai.com/api/docs/guides/latest-model) and [Responses API](https://platform.openai.com/docs/api-reference/responses/create).

The factory selects a disabled adapter unless both the provider name and server-side key are configured. Lead intake, inventory, and reads remain available while extraction returns a useful error.

## Observability model

Each attempt records, where available:

- local run/request ID and provider request ID;
- run type, lead ID, provider, model, prompt version, and timestamp;
- status, latency, validation outcome, input/output tokens, and estimated cost;
- bounded sanitized error code and message.

Raw model output, original lead text, prompt bodies, provider error bodies, and credentials are deliberately excluded. `GET /api/leads/{id}` returns the latest requirements and ten most recent extraction attempts for the internal UI.

## Database environments

### Supabase PostgreSQL

`supabase/migrations` is authoritative. The extraction migration adds constrained `lead_requirements` and `ai_runs` tables, indexes recent lead runs, installs the update trigger, enables RLS, revokes direct browser-role grants, and documents the no-raw-output policy.

Production-like validation lives separately under `apps/api/tests/postgres`. It applies the SQL to a
fresh PostgreSQL 17 database with pgvector, loads the synthetic seed, inspects database catalogs and
role security, and exercises FastAPI transactions and concurrent writes. CI uses the versioned
pgvector PostgreSQL image rather than the full Supabase service stack; the tests create missing
Supabase Data API roles and validate their actual grants/RLS behavior.

### SQLite development fallback

SQLAlchemy creates the portable tables in `.local/arriendate.db` for local and test execution. It validates routes, services, transactions, constraints represented in models, and persistence behavior. It cannot validate PostgreSQL array behavior, PostgreSQL-specific check semantics, triggers, grants, or RLS.

The SQLite and PostgreSQL suites are intentionally distinct. Passing SQLite is not evidence that a
migration or RLS policy works. See [database validation](database-validation.md) for exact commands.

## Explicit boundary

This milestone ends after structured extraction, persistence, failure handling, evaluation, and observability. Property matching, embeddings, RAG, agents, workflow integrations, and optimization research remain outside the code path.
