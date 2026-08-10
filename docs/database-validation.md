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
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000
```

## Fast versus production-like tests

SQLite is the fast, zero-install adapter. It validates request schemas, routes, service behavior,
provider mocks, and portable ORM behavior:

```powershell
.\.venv\Scripts\python.exe -m pytest apps/api/tests --ignore=apps/api/tests/postgres -q
```

PostgreSQL validates what SQLite cannot: migration order, extensions, native arrays, `vector(1536)`,
catalog types/defaults/nullability, constraints, indexes, foreign keys, triggers, timezone-aware
timestamps, RLS, grants, seed replay, transaction rollback, serialization, idempotency races, and
concurrent requirement upserts.

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

- RLS is enabled on `leads`, `properties`, `lead_requirements`, and `ai_runs`.
- There are intentionally no permissive policies in the unauthenticated internal milestone.
- `anon` and `authenticated` have no table privileges; tests also prove RLS remains deny-by-default
  if a read or insert grant is introduced temporarily.
- `service_role` has `BYPASSRLS`, but with the current opt-in Data API configuration it has no object
  privilege until one is explicitly granted.
- FastAPI uses a server-only direct PostgreSQL connection; the test and local URLs use the database
  owner to exercise this path.

Before public deployment, provision a dedicated least-privilege FastAPI login and add an approved
authentication/organization ownership model. Hosted Supabase configuration still needs a real
environment validation before production release.
