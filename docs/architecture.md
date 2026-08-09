# Architecture — First Vertical Slice

## Runtime boundaries

The React browser consumes JSON from FastAPI. FastAPI owns all validation and orchestration and is the only process allowed to use server database credentials. The browser has no direct Supabase client in this milestone.

```text
HTTP router → application service → repository → SQLAlchemy session → database
```

Dependencies point inward:

- Routers translate HTTP values into validated Pydantic types.
- Services implement use cases and raise safe application errors.
- Repositories contain queries and persistence mechanics.
- SQLAlchemy models describe the portable subset used by the application.
- Supabase SQL migrations define the authoritative PostgreSQL schema, including pgvector and RLS.

## Write path: lead intake

1. The browser validates basic form shape.
2. It creates a UUID idempotency key for the exact payload.
3. `POST /api/leads` validates the body again with strict Pydantic rules.
4. The service checks whether the idempotency key already exists.
5. A new lead is committed with status `new`, or the identical existing record is returned.
6. Reusing the key with different content returns a visible `409` conflict.
7. The browser navigates to `/leads/{id}` and reloads the record from the API.

No AI execution is part of this transaction. That keeps persistence available even when future providers fail.

## Read path: property inventory

The seed includes 18 deterministic records across Viña del Mar, Valparaíso, Concón, and Quilpué. Filters are executed by the repository before pagination. API response schemas deliberately exclude `embedding` and `embedding_text`.

Unknown fields are modeled explicitly:

- nullable numbers for bedrooms, parking, surface, and other incomplete facts;
- `pet_policy = unknown` rather than an optimistic boolean;
- nullable furnishing status;
- availability separated from listing content.

## Database environments

### Supabase PostgreSQL

`supabase/migrations` is authoritative. The initial migration enables `pgcrypto` and `vector`, creates constrained `leads` and `properties` tables, installs update triggers and indexes, enables RLS, and revokes direct browser-role grants.

### SQLite development fallback

The current machine lacks Docker and Supabase CLI runtime prerequisites. SQLAlchemy creates the two slice tables in `.local/arriendate.db` so API integration and browser flows can be verified. This adapter is not the production schema and cannot validate pgvector, PostgreSQL arrays, or RLS.

## Future extension points

The next milestone adds `lead_requirements` and `ai_runs` through a new migration. AI adapters will sit behind narrow protocols and services; no provider SDK type will enter routes or domain rules. Hard matching, property matches, notes, and follow-up drafts remain separate later milestones.
