# Arriendate Intelligence — Phase 0 Implementation Plan

Status: approved baseline; initial slice and structured-extraction milestone implemented
Scope: Phase 0 planning only  
Source of truth: `PROJECT_REQUIREMENTS_REAL_ESTATE_AI.md`

## 1. Scope and delivery boundary

This plan deliberately stops before codebase initialization. After review, the first implementation milestone will contain only:

1. A synthetic inventory of at least 15 Chilean properties.
2. A lead intake form.
3. A persistent lead record containing the untouched original request.

Structured extraction, matching, explanations, follow-up drafts, and the assistant belong to later milestones of the Phase 1 vertical flow. RAG, n8n, autonomous communication, multi-agent orchestration, and quantum research are excluded.

## 2. Proposed repository structure

```text
/
  apps/
    web/
      src/
        app/                 # router, providers, global layout
        features/
          leads/
          properties/
        components/          # reusable UI primitives
        lib/                 # API client, validation, formatting
        styles/
      tests/
      package.json
    api/
      app/
        api/                 # FastAPI routers and HTTP schemas
        core/                # settings, logging, errors, telemetry
        domain/              # domain types and business rules
        repositories/        # persistence interfaces + Postgres adapters
        services/            # use cases; no HTTP or SQL concerns
        ai/
          providers/         # provider implementations
          prompts/           # versioned prompt files
          schemas/           # strict machine-output schemas
        main.py
      tests/
        unit/
        integration/
      pyproject.toml
  supabase/
    migrations/              # only source of truth for database DDL
    seed/
      properties.sql         # deterministic synthetic demo records
  evals/
    datasets/                # synthetic leads and expected outcomes
    scripts/
    results/.gitkeep
  docs/
    implementation-plan.md
    architecture.md
    ai-guardrails.md
    evaluation.md
  .env.example
  .gitignore
  package.json               # npm workspace and common developer commands
  README.md
  PROJECT_REQUIREMENTS_REAL_ESTATE_AI.md
```

`packages/shared-types` is intentionally omitted initially. FastAPI's OpenAPI document will be the API contract, and the frontend will use generated TypeScript types. A shared package should be introduced only if non-API domain code genuinely needs to be shared.

## 3. Architecture decisions

### 3.1 Runtime shape

```text
React/Vite browser
       |
       | JSON over /api
       v
FastAPI application
  |          |             |
  |          |             +--> OpenAI-compatible AI provider (server only)
  |          +----------------> domain services / deterministic matching
  +---------------------------> Supabase Postgres + pgvector
```

- The browser communicates with FastAPI, not directly with privileged Supabase APIs.
- FastAPI owns validation, orchestration, business rules, AI calls, and writes.
- Supabase Postgres is the durable system of record. SQL migrations under `supabase/migrations` are the sole schema history; no second migration system will compete with them.
- React Router provides the specified routes. TanStack Query will manage server state and retries; React Hook Form plus Zod will validate lead intake in the browser.
- The API uses Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 Core/async sessions, and psycopg 3. Repository interfaces keep SQL out of domain services.
- The web app uses React, TypeScript strict mode, Vite, and a small local component layer. A large design-system dependency is unnecessary for the initial internal-tool UI.
- Configuration is loaded once from environment variables into typed server/browser settings. Secrets are never placed in `VITE_*` variables.

### 3.2 Request and processing boundaries

- `POST /api/leads` performs one job: validate the intake and persist the original text. It does not wait for an AI call. This guarantees FR-01 even when an AI provider is unavailable.
- Extraction and matching remain explicit commands. They can expose their own loading, failure, and retry states without duplicating the lead.
- Each AI execution creates an `ai_runs` record with a request ID, prompt version, provider/model, timing, token/cost data when available, validation outcome, and a sanitized error.
- Domain errors are translated to a consistent problem-details JSON response. No failure is swallowed.
- Logs are structured JSON and correlate HTTP requests, leads, and AI runs without logging original lead text or credentials by default.

### 3.3 Security posture

- Phase 1 local development is an internal single-user demo. Authentication is deferred, but the API binds to localhost by default and CORS accepts only configured origins.
- The browser receives no database password or Supabase service-role key.
- Public deployment is blocked until authentication and ownership-aware Row Level Security policies exist. Until then, `anon` and `authenticated` database roles receive no direct table access.
- User text is rendered as text, never injected as HTML. Server input lengths are bounded.
- `.env` files, local Supabase state, logs, generated evaluation results, and editor artifacts are ignored. `.env.example` contains names and safe placeholders only.

### 3.4 Deliberately deterministic behavior

- Hard filtering, score composition, unmet-requirement calculation, and explanation facts are deterministic application code.
- An LLM may extract requirements and draft language, but it cannot decide eligibility or invent match facts.
- Initial match explanations should be rendered from verified comparison facts. An optional LLM rephrasing layer may be added only if its output is claim-checked against those facts.

## 4. Database schema

PostgreSQL extensions: `pgcrypto` for UUID generation and `vector` for embeddings. Timestamps are `timestamptz` in UTC. Money is stored as integer CLP amounts, never floating point.

### 4.1 `leads`

| Column | Type | Rules |
|---|---|---|
| `id` | `uuid` | PK, default `gen_random_uuid()` |
| `name` | `text` | nullable, max 120 |
| `email` | `text` | nullable, normalized, max 320 |
| `phone` | `text` | nullable, max 40 |
| `original_request` | `text` | required, preserve submitted content, 10–10,000 chars |
| `idempotency_key` | `uuid` | required, unique; generated by the intake client |
| `status` | `text` | required check: `new`, `qualified`, `needs_information`, `matched`, `contacted`, `closed_won`, `closed_lost`; default `new` |
| `created_at` | `timestamptz` | required, default `now()` |
| `updated_at` | `timestamptz` | required, trigger-maintained |

At least one of email/phone may be absent for the demo; both are optional exactly as required. Email/phone are not used as uniqueness keys.

### 4.2 `lead_requirements`

| Column | Type | Rules |
|---|---|---|
| `id` | `uuid` | PK |
| `lead_id` | `uuid` | FK `leads`, cascade delete, unique for latest MVP extraction |
| `operation_type` | `text` | `rent`, `buy`, `unknown` |
| `property_types` | `text[]` | required, default empty |
| `locations` | `text[]` | required, default empty |
| `max_budget` | `bigint` | nullable, non-negative |
| `currency` | `text` | nullable; ISO-style code |
| `min_bedrooms` | `smallint` | nullable, non-negative |
| `min_bathrooms` | `smallint` | nullable, non-negative |
| `parking_required` | `boolean` | nullable preserves unknown |
| `pets_required` | `boolean` | nullable preserves unknown |
| `furnished_preference` | `boolean` | nullable |
| `soft_preferences` | `text[]` | required, default empty |
| `missing_information` | `text[]` | required, default empty |
| `extraction_confidence` | `numeric(4,3)` | nullable, 0 through 1 |
| `extraction_model` | `text` | required |
| `prompt_version` | `text` | required |
| `created_at` | `timestamptz` | required |
| `updated_at` | `timestamptz` | required |

### 4.3 `properties`

| Column | Type | Rules |
|---|---|---|
| `id` | `uuid` | PK; deterministic UUIDs in seed data |
| `title` | `text` | required |
| `description` | `text` | required |
| `operation_type` | `text` | `rent` or `buy` |
| `property_type` | `text` | controlled value |
| `city` | `text` | required |
| `sector` | `text` | nullable to model incomplete records |
| `monthly_price` | `bigint` | nullable, non-negative |
| `sale_price` | `bigint` | nullable, non-negative |
| `currency` | `text` | required |
| `bedrooms` | `smallint` | nullable, non-negative |
| `bathrooms` | `smallint` | nullable, non-negative |
| `parking_spaces` | `smallint` | nullable, non-negative |
| `pet_policy` | `text` | `allowed`, `not_allowed`, `unknown` |
| `furnished` | `boolean` | nullable |
| `square_meters` | `numeric(8,2)` | nullable, positive |
| `amenities` | `text[]` | required, default empty |
| `availability_status` | `text` | `available`, `reserved`, `unavailable` |
| `source_text` | `text` | required, synthetic source record |
| `embedding_text` | `text` | canonical, inspectable text used for embedding |
| `embedding` | `vector(1536)` | nullable until indexed |
| `embedding_model` | `text` | nullable |
| `embedding_updated_at` | `timestamptz` | nullable |
| `created_at` | `timestamptz` | required |
| `updated_at` | `timestamptz` | required |

A row check enforces the correct price column for the operation type. Missing bedrooms, parking, pet policy, or furnishing stays unknown and can never be silently treated as satisfying a required constraint.

Indexes: availability + operation + city; price columns; bedrooms; GIN on amenities; and an HNSW cosine index on `embedding` once the dataset is large enough to justify it. At 15 rows exact cosine search is simpler and remains the initial behavior.

### 4.4 `property_matches`

| Column | Type | Rules |
|---|---|---|
| `id` | `uuid` | PK |
| `lead_id` | `uuid` | FK `leads`, cascade delete |
| `property_id` | `uuid` | FK `properties`, restrict delete |
| `hard_fit_score` | `numeric(5,4)` | 0 through 1 |
| `semantic_score` | `numeric(5,4)` | 0 through 1 |
| `preference_score` | `numeric(5,4)` | 0 through 1 |
| `total_score` | `numeric(5,4)` | 0 through 1 |
| `explanation` | `text` | grounded output |
| `unmet_requirements` | `jsonb` | typed fact records, not free-form only |
| `scoring_version` | `text` | required |
| `created_at` | `timestamptz` | required |

A unique constraint on `(lead_id, property_id, scoring_version)` prevents accidental duplicate results. A later rerun strategy may replace or version a lead's match set atomically.

### 4.5 `ai_runs`

| Column | Type | Rules |
|---|---|---|
| `id` | `uuid` | PK and request/run ID |
| `run_type` | `text` | extraction, embedding, follow-up, etc. |
| `lead_id` | `uuid` | nullable FK |
| `property_id` | `uuid` | nullable FK |
| `provider` | `text` | required |
| `model` | `text` | required |
| `prompt_version` | `text` | nullable for embedding calls |
| `latency_ms` | `integer` | non-negative |
| `input_tokens` | `integer` | nullable |
| `output_tokens` | `integer` | nullable |
| `estimated_cost` | `numeric(12,8)` | nullable |
| `validation_passed` | `boolean` | required |
| `status` | `text` | `succeeded` or `failed` |
| `retrieval_result_ids` | `uuid[]` | nullable |
| `error_code` | `text` | nullable, sanitized |
| `error_message` | `text` | nullable, sanitized |
| `created_at` | `timestamptz` | required |

Raw model output is not persisted by default. A development-only, redacted debug sink may be designed later if necessary.

### 4.6 `notes`

| Column | Type | Rules |
|---|---|---|
| `id` | `uuid` | PK |
| `lead_id` | `uuid` | FK `leads`, cascade delete |
| `content` | `text` | required, bounded |
| `created_at` | `timestamptz` | required |

### 4.7 RLS and grants

- RLS is enabled on application tables from the first migration.
- Direct `anon` and `authenticated` access is denied during the unauthenticated local MVP.
- The server connects with a server-only database credential.
- Before public deployment, policies will scope rows to an `organization_id`/membership model; that multi-tenant column is intentionally not added until authentication scope is approved.

## 5. API boundary

All endpoints are under `/api`. Pydantic request/response types are strict, unknown fields are rejected on machine-command inputs, and OpenAPI is the source used to generate frontend API types.

### First implementation milestone

| Method and path | Responsibility | Result |
|---|---|---|
| `GET /api/health` | Process and database readiness | status without secrets |
| `POST /api/leads` | Validate intake and persist original request only | `201` with lead summary |
| `GET /api/leads/{lead_id}` | Return the persisted lead; later expands with requirements/matches | `200` or `404` |
| `GET /api/properties` | Paginated inventory with operation/city/status filters | property summaries |
| `GET /api/properties/{property_id}` | Full synthetic property record, excluding vector | property detail or `404` |

`POST /api/leads` accepts `name`, `email`, `phone`, and `original_request`. The original request is trimmed only for the all-whitespace check; its submitted text is otherwise preserved. The button is disabled while submitting, and a generated idempotency key prevents duplicate rows on a safe retry.

### Later Phase 1 endpoints

| Method and path | Responsibility |
|---|---|
| `POST /api/leads/{lead_id}/extract` | Validated structured extraction and `ai_runs` telemetry |
| `POST /api/leads/{lead_id}/match` | Hard filter, embedding rank, deterministic scoring, persistence |
| `POST /api/leads/{lead_id}/follow-up-draft` | Produce but never send a draft |
| `POST /api/assistant/query` | Grounded application-data query, implemented only in its planned phase |

Status updates and notes will receive explicit endpoints when their UI milestone begins. They should not be hidden side effects of AI commands.

## 6. AI provider abstraction

The application depends on narrow protocols rather than an SDK-specific client:

```python
class StructuredGenerator(Protocol):
    async def generate_structured(
        self,
        *,
        messages: Sequence[PromptMessage],
        response_schema: type[BaseModel],
        run_context: AIRunContext,
    ) -> StructuredGenerationResult: ...

class EmbeddingProvider(Protocol):
    @property
    def dimensions(self) -> int: ...

    async def embed(
        self,
        texts: Sequence[str],
        *,
        run_context: AIRunContext,
    ) -> EmbeddingBatchResult: ...
```

The first real adapter will target the OpenAI-compatible API shape and will receive base URL, API key, model names, timeout, and retry limits from environment variables. This keeps Azure/OpenAI-compatible switching at the adapter/configuration layer. Provider results contain content, model identity, token usage, latency, and provider request ID; they never return unvalidated domain objects.

Additional rules:

- Extraction uses provider-supported JSON Schema structured output where available, followed by strict Pydantic validation.
- Malformed output is rejected. Transport retries are bounded and only retry safe transient errors with backoff; validation failures do not silently become guessed values.
- Prompt templates are plain versioned files with a `PROMPT_VERSION` identifier.
- Unit and integration tests inject deterministic fake providers; tests never need a real API key.
- The application refuses startup of an AI-dependent command when its selected provider configuration is incomplete, while non-AI lead/property endpoints continue to work.

## 7. Embedding and matching strategy

### 7.1 Canonical texts

Each property has deterministic `embedding_text`, assembled in a stable field order from only stored facts: title, description, operation/property type, city/sector, known features, amenities, and known policies. Unknown fields are omitted rather than described optimistically.

The lead query text combines the untouched request with normalized extracted soft preferences. Hard constraints are not converted into semantic escape hatches; they remain filters.

### 7.2 Model and storage

- Initial model: a configurable 1,536-dimension OpenAI-compatible embedding model, with `text-embedding-3-small` as the documented default.
- Database column: `vector(1536)`. Changing dimensions requires an explicit migration and full re-embedding, never an implicit runtime change.
- Store model identity and update timestamp with each vector.
- A repeatable server-side indexing command batches missing/stale property embeddings. No provider secret enters SQL seed files or the browser.

### 7.3 Retrieval sequence

1. Normalize extracted values conservatively.
2. Apply availability, operation, price, explicit location, minimum bedrooms, required parking, and required pet-policy filters in deterministic code/SQL.
3. Treat unknown database values as failing a required hard constraint.
4. If zero candidates remain, return a supported no-match result; semantic search does not widen the constraints.
5. Embed the lead query and calculate cosine similarity only for eligible candidates.
6. Normalize cosine similarity to a documented 0–1 score and clamp numeric edge cases.
7. Calculate optional preference fit from inspectable comparisons.
8. Compose `total = 0.50 * hard_fit + 0.30 * semantic + 0.20 * preference_fit` using versioned configuration.
9. Sort deterministically by total score, semantic score, then property ID; persist at most three.

The hard gate and the score are distinct. A failed gate excludes the property. For eligible properties, `hard_fit` is the satisfied fraction of applicable structured hard criteria and will normally be 1.0. The total is a ranking score, not a probability of closing the lead.

At demo scale exact cosine comparison is preferable. HNSW is enabled only after measured inventory growth makes approximate search useful.

## 8. Test and evaluation strategy

### 8.1 Backend

- `pytest`, `pytest-asyncio`, and coverage with unit tests for domain logic.
- Table-driven hard-filter tests covering budget, operation, availability, location, bedrooms, parking, pets, and unknown values.
- Score tests for weights, normalization, stable ordering, empty preferences, and boundary values.
- Pydantic tests for valid, null, malformed, contradictory, and extra-field extraction output.
- Repository integration tests against a disposable local Supabase/Postgres database using real migrations.
- Full service integration test: create lead → persist original → extract with fake provider → filter → rank → store top three.
- Grounding tests compare explanation claims to an allowlist of facts from lead/property comparison records.

### 8.2 Frontend

- Vitest, React Testing Library, user-event, and MSW.
- Lead form tests: required request, optional contact fields, submission lock, API error, retry, and successful navigation.
- Rendering tests for lead details, unknown values, statuses, and match-card supported/unmet facts.
- Type checking and ESLint run independently from production build.

### 8.3 End-to-end

- Playwright against local web + API + Supabase.
- One required reproducible flow covers intake through draft generation as milestones land.
- First-slice E2E covers property inventory, lead submission, durable reload, and original-text display.

### 8.4 Evaluation

- Commit at least 15 synthetic Spanish lead cases with stable IDs, scenario labels, expected extracted fields, hard-filter exclusions, and manually accepted top matches.
- Include every edge case listed in the requirements.
- Evaluation scripts produce schema validity, field accuracy, hard-constraint violation rate, top-3 relevance, unsupported-claim rate, latency, and approximate cost.
- Raw generated results stay ignored by default; small reviewed baseline summaries may be committed deliberately.
- A CI smoke suite uses fake providers. Live-model evaluation is opt-in and reports model/prompt versions for reproducibility.

## 9. Exact ordered tasks for the first vertical slice

The following is the execution order after this plan is reviewed.

1. Initialize Git, add `.gitignore`, `.editorconfig`, `.env.example`, root README, and root npm workspace metadata.
2. Scaffold `apps/web` with React + TypeScript + Vite and strict compiler settings.
3. Scaffold `apps/api` with FastAPI, Pydantic settings, lint/type/test configuration, structured errors, and a health endpoint.
4. Add local Supabase configuration and the first migration with extensions, `leads`, `properties`, constraints, update triggers, indexes, RLS, and locked-down grants.
5. Create 15–20 deterministic, clearly synthetic property records spanning Viña del Mar, Valparaíso, Concón, and Quilpué, with deliberate variation and unknown fields.
6. Implement API settings and server-only Postgres connection lifecycle; document required local variables without secrets.
7. Implement property domain types, repository, list/detail services, and paginated `GET /api/properties` endpoints.
8. Implement lead domain types, repository, create/read services, idempotent `POST /api/leads`, and `GET /api/leads/{id}`. Persist before any future AI processing.
9. Generate frontend API types from the FastAPI OpenAPI contract and add a small typed API client.
10. Build the internal-tool shell and routes `/dashboard`, `/properties`, `/properties/:id`, `/leads/new`, and `/leads/:id`; non-slice dashboard sections use honest empty states, not fake metrics.
11. Build inventory list/detail UI with basic filters and explicit display of unknown attributes.
12. Build accessible lead intake with client/server validation, loading/error states, duplicate-submit protection, and redirect to the persisted lead detail.
13. Build the initial lead detail page showing original request, status, contact details, timestamp, and clear “processing not run yet” states.
14. Add backend unit/integration tests and frontend form/rendering tests for this slice.
15. Run lint, formatting checks, TypeScript type-check, Python type-check, all tests, and production builds.
16. Start the complete local stack and verify in a real browser: inventory filters, property detail, lead submission, reload persistence, error presentation, keyboard operation, and responsive layout.
17. Complete README setup/architecture instructions, record commands and results, and report implemented files, tests, browser verification, limitations, and the next milestone.

No extraction, embeddings, matching, RAG, message sending, n8n, multi-agent, or quantum code is included in this slice.

## 10. Risks, ambiguities, and assumptions

| Topic | Decision / assumption | Risk and mitigation |
|---|---|---|
| Plan approval gate | No scaffold is created before review of this artifact. | This is required by the first-task instruction and prevents premature stack decisions. |
| Requirement filename | The actual source file name differs from the name referenced inside it. Keep it unchanged initially and link it accurately. | Rename only with explicit approval to avoid breaking the user's reference. |
| Authentication | Excluded from the local first slice. | Unsafe for a public deployment; bind locally, deny direct table access, and add Auth/RLS ownership before deployment. |
| API-to-database access | FastAPI uses a server-only Postgres connection. | Credentials have broad access; keep them out of the browser/logs and use a least-privileged API database role before production. |
| Contact data | Demo contact fields are optional and synthetic. | They are still personal data if users enter real values; add a visible demo-data warning and avoid logging request bodies. |
| Location meaning | Extracted explicit city/comuna values are conservative exact/alias matches; sector preference is soft unless explicitly represented as required later. | Spanish place aliases and neighborhoods are ambiguous; maintain a reviewed normalization map and expose uncertainty. |
| Pet policy | `unknown` fails when pets are required. | This may reduce results, but it obeys the no-assumption guardrail. Surface “policy not confirmed.” |
| Parking | Required parking means a known `parking_spaces >= 1`; null fails. | Same conservative behavior as pet policy. |
| Contradictory leads | Preserve conflicting text, flag missing/clarification items, and set `needs_information`; do not silently choose one constraint. | Exact contradiction taxonomy must be covered by extraction/evaluation fixtures. |
| Missing budget | Budget filter is skipped, while the UI calls out the missing value. | Results are less constrained; mark uncertainty and propose a follow-up question. |
| Currency | Synthetic MVP inventory uses CLP only; no implicit currency conversion. | UF/USD support needs an explicit dated exchange-rate source and is out of the first slice. |
| Embedding provider | Default is a 1,536-dimension OpenAI-compatible model; tests use fakes. | Provider/model changes can alter ranking; store versions and require explicit re-indexing/evaluation. |
| Semantic normalization | Cosine-to-0–1 mapping and weights require calibration against the evaluation dataset. | Version scoring config and do not present total score as a probability. |
| Seed realism | Listings are synthetic but geographically plausible; no scraped/client data. | Avoid claims about real addresses, commute times, safety, or legal conditions. |
| Explanation generation | Initial explanations are deterministic from comparison facts. | Wording may feel less fluid, but unsupported-claim risk is materially lower. Optional rephrasing must be claim-checked. |
| Raw AI output | Not stored by default. | Debugging is harder; telemetry plus opt-in redacted local capture is safer than retaining lead content broadly. |
| Tooling availability | Plan assumes Node 22 LTS, npm, Python 3.12, and Supabase CLI/Docker for local database work. | Confirm installed versions before scaffolding and document any compatible fallback. |
| Idempotency | Lead creation accepts a client-generated idempotency key stored with a uniqueness constraint (added to `leads` during implementation). | Prevents network retry duplicates; keys must be scoped and expire/clean up if the system becomes multi-tenant. |

## 11. Review decisions requested

Implementation can proceed with the defaults above unless review changes them. The most consequential choices are:

1. Keep v0.1 local/internal and add authentication only before public deployment.
2. Use FastAPI as the only browser-facing data boundary.
3. Use SQL migrations in `supabase/migrations` as the only database schema source.
4. Use deterministic grounded explanations before considering LLM rephrasing.
5. Use a 1,536-dimension OpenAI-compatible embedding model and exact cosine search at demo scale.
