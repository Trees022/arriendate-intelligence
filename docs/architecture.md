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
- `app.server` supplies a selector event loop on Windows so the async psycopg path can run against
  Docker-based local Supabase as it does on Linux.

No provider SDK type crosses into routes, repositories, or response schemas.

## Matching path

```text
lead_requirements
  -> ConstraintEvaluator (binary expected/actual/passed checks)
  -> eligible property IDs
  -> canonical property and soft-preference lead embeddings
  -> PostgreSQL `embedding <=> query_vector` over eligible IDs only
  -> persisted ranks, scores, passed checks, and fact-backed reasons
```

Hard rules cover availability, explicit operation, explicit property type, explicit location,
currency/budget, minimum bedrooms, minimum bathrooms, required parking, and required pets. A
`null` requirement does not filter. `false` for parking or pets does not prohibit those features.
When an active rule needs a property value and that value is unknown, the property fails. Furnished
and free-text preferences are soft only.

Location matching is exact after case, whitespace, punctuation, and accent normalization against
city, sector, and stable city/sector combinations. It deliberately performs no fuzzy or semantic
location expansion.

`EmbeddingProvider` is independent from `StructuredGenerator`. Property text has a stable fact-only
order; lead semantic text contains only `soft_preferences` and the optional furnished preference.
Production ranking uses pgvector cosine distance (`<=>`). API similarity is
`clamp((cosine_similarity + 1) / 2, 0, 1)` and is a ranking signal, not a probability. Ties use
property UUID ascending. Candidate IDs are in the SQL `WHERE`, so excluded properties cannot return.

Embeddings are reused only while canonical text, provider, model, vector-space fingerprint, vector
presence, and update timestamp agree.
Otherwise the server batches regeneration into the existing `vector(1536)`. Exact search is
intentional for 18 rows; no HNSW index is justified without representative scale and query plans.

Matching persists outside `ai_runs`: `matching_runs` stores counts, latency, provider/model/space,
algorithm version, requirement fingerprint, invalidation timestamp, status, aggregate exclusions,
and bounded errors; `property_matches` stores rank, similarity, passed hard checks, and grounded soft
reasons. A composite foreign key prevents a match from naming a lead different from its run. Neither
table stores raw lead text nor vectors.

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

### Validated local Supabase boundary

The Docker-based local stack has been validated end to end through Kong/PostgREST, Auth-issued
authenticated tokens, FastAPI, and the React browser flow. No browser code connects directly to
Supabase. Application tables remain absent from the anon OpenAPI surface, and anon, authenticated,
and service_role Data API requests cannot read or write them because no object grants or permissive
RLS policies exist. The privileged backend path is the server-only PostgreSQL owner connection, not
a browser-visible service-role key.

This validation covers local containers only. Supabase hosted deployment, production Auth,
organization ownership/multitenancy, and a least-privilege backend login remain future production
work.

## Explicit boundary

This milestone ends after structured extraction, hard-constraint property matching, semantic ranking,
persistence, failure handling, evaluation, and observability. RAG, agents, workflow integrations, and
optimization research remain outside the code path.
