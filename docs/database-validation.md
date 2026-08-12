# PostgreSQL and Supabase Database Validation

## Validation boundary

SQL files under `supabase/migrations` remain the authoritative PostgreSQL schema. The isolated suite
under `apps/api/tests/postgres` creates a disposable database, applies migrations in timestamp order,
loads `supabase/seed/properties.sql`, validates the resulting catalogs and security behavior, and
runs the FastAPI persistence path against that database.

The suite deliberately fails when `ARRIENDATE_TEST_POSTGRES_URL` is missing or is not PostgreSQL.
It never treats SQLite as equivalent.

## Local Supabase workflow

Prerequisites are Docker, Node.js 22, and the project-scoped Supabase CLI installed by `npm ci` or
`npm install`.

```powershell
npm.cmd exec supabase -- start
npm.cmd exec supabase -- db reset --local
$env:ARRIENDATE_TEST_POSTGRES_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:54322/postgres'
.\.venv\Scripts\python.exe -m pytest apps/api/tests/postgres -q -m postgres
```

`db reset --local` rebuilds the Supabase database and applies the configured seed. The test suite
uses the URL only as an administrative connection, creates a uniquely named `arriendate_it_*`
database, and removes that database after the session. It creates `anon`, `authenticated`, and
`service_role` only when the target is plain PostgreSQL and those Supabase roles are absent.

To run FastAPI against local Supabase after reset:

```powershell
$env:ARRIENDATE_DATABASE_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:54322/postgres'
$env:ARRIENDATE_SEED_DEMO_DATA='false'
.\.venv\Scripts\python.exe -m app.server
```

The repository runner uses a selector event loop on Windows because psycopg async cannot run on
the default Proactor event loop selected by current Uvicorn releases.

## Full local Supabase validation

On 2026-08-11, a clean checkout was validated with Docker Engine 29.7.2, Docker Compose 5.3.1,
Supabase CLI 2.113.0, and the local PostgreSQL 17.6.1.158 image. PostgreSQL, Kong, PostgREST, Auth,
Realtime, Storage, Studio, Postgres Meta, Mailpit, Analytics/Logflare, and Edge Runtime started and
remained available. The initial cold image pull exceeded the legacy health timeout once; a repeat
with cached images completed without repository changes.

The auxiliary Vector log collector repeatedly restarts on this Windows host. Supabase CLI configures
it with `DOCKER_HOST=http://host.docker.internal:2375`, while Docker Desktop intentionally does not
expose its unauthenticated daemon on TCP port 2375. Container logs show connection refused, a clean
exit, and no OOM. This is a Docker Desktop host configuration limitation rather than a repository
failure; enabling the insecure daemon globally was not required for application validation. It is
unrelated to the healthy PostgreSQL pgvector 0.8.2 extension.

Two consecutive `db reset --local` executions applied both timestamped migrations and the seed
without manual SQL. Each produced 18 properties, zero leads, the same content digest when runtime
timestamps were excluded, UTF-8 Chilean text, the intended nullable fixture, pgcrypto 1.3, pgvector
0.8.2, and `vector(1536)`.

The local Data API is deliberately closed for this internal milestone:

- unauthenticated requests without an API key return `401`;
- `anon` cannot read any application table (`401`) or insert leads (`401`);
- a real locally issued `authenticated` token cannot read or insert (`403`);
- `service_role` bypasses RLS as a PostgreSQL role but has no Data API object grants, so direct
  PostgREST reads and writes return `403`;
- the anon OpenAPI document publishes only `/`, not application-table paths.

The local-only regression suite requires ephemeral keys from the running stack and refuses any URL
whose host is not loopback:

```powershell
$supabaseStatus = npm.cmd exec supabase -- status -o env
function Get-LocalSupabaseValue([string]$name) {
  $line = $supabaseStatus | Where-Object { $_ -like "$name=*" } | Select-Object -First 1
  (($line -split '=', 2)[1]).Trim('"')
}
$env:ARRIENDATE_TEST_SUPABASE_URL = Get-LocalSupabaseValue 'API_URL'
$env:ARRIENDATE_TEST_SUPABASE_ANON_KEY = Get-LocalSupabaseValue 'ANON_KEY'
$env:ARRIENDATE_TEST_SUPABASE_SERVICE_ROLE_KEY = Get-LocalSupabaseValue 'SERVICE_ROLE_KEY'
.\.venv\Scripts\python.exe -m pytest apps/api/tests/supabase -q -m supabase
```

Do not persist or print the captured local keys. They are Docker-local test credentials, not
production secrets.

For the browser flow against local Supabase, run the deterministic provider harness with PostgreSQL
instead of its default SQLite database:

```powershell
$env:ARRIENDATE_E2E_DATABASE_URL='postgresql+psycopg://postgres:postgres@127.0.0.1:54322/postgres'
$env:ARRIENDATE_ASGI_APP='tests.e2e_app:app'
$env:ARRIENDATE_APP_DIR='apps/api'
.\.venv\Scripts\python.exe -m app.server
```

In another terminal, run `npm.cmd run dev:web -- --host 127.0.0.1 --port 5173`, then
`npm.cmd run test:e2e`.

## Fast versus production-like tests

SQLite is the fast, zero-install adapter. It validates request schemas, routes, service behavior,
provider mocks, and portable ORM behavior:

```powershell
.\.venv\Scripts\python.exe -m pytest apps/api/tests --ignore=apps/api/tests/postgres -q
```

PostgreSQL validates what SQLite cannot: migration order, extensions, native arrays, `vector(1536)`,
catalog types/defaults/nullability, constraints, indexes, foreign keys, triggers, timezone-aware
timestamps, RLS, grants, seed replay, transaction rollback, serialization, idempotency races, and
concurrent requirement upserts. Matching coverage also validates vector storage/readback, cosine
distance, `NULL` embeddings, hard-gated vector ordering, `top_k`, persistence, deterministic ties,
cache vector-space identity, historical invalidation, same-lead concurrency, and the requirements-change
race during an in-flight match.

## CI architecture

The `PostgreSQL / Supabase DB` job uses the versioned
`pgvector/pgvector:0.8.2-pg17-bookworm` image on `ubuntu-latest`. It supplies only an ephemeral local
database password, creates no external resource, needs no repository secret, and never calls a real
AI provider. The same migrations, seed, and PostgreSQL-marked tests run there from a clean database.

A focused PostgreSQL image is used instead of the complete Supabase Docker stack to keep pull-request
validation deterministic and small. Supabase-specific database behavior is still exercised by
creating its Data API roles and asserting role attributes, object grants, RLS state, policies, and
actual `SET ROLE` access. This does not validate Supabase Auth, PostgREST, Studio, Realtime, or hosted
platform configuration.

## Current security model

- RLS is enabled on `leads`, `properties`, `lead_requirements`, `ai_runs`, `matching_runs`, and `property_matches`.
- There are intentionally no permissive policies in the unauthenticated internal milestone.
- `anon` and `authenticated` have no table privileges; tests also prove RLS remains deny-by-default
  if a read or insert grant is introduced temporarily.
- `service_role` has `BYPASSRLS`, but with the current opt-in Data API configuration it has no object
  privilege until one is explicitly granted.
- FastAPI uses a server-only direct PostgreSQL connection; the test and local URLs use the database
  owner to exercise this path.

Before public deployment, provision a dedicated least-privilege FastAPI login and add an approved
authentication/organization ownership model. Hosted Supabase, production Auth flows, backups and
recovery, rate limiting, hosted observability, and a live AI provider still need validation in their
actual environments.
