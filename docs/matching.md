# Property Matching Contract

Matching is a two-stage contract: deterministic eligibility is mandatory; semantic similarity only
orders the eligible set.

## Requirement mapping

| Lead requirement | Property fact | Treatment | Missing behavior |
|---|---|---|---|
| operation (unless `unknown`) | `operation_type` | hard | property is always known |
| explicit property types | `property_type` | hard | property is always known |
| explicit locations | `city`, `sector` | hard exact normalized match | absent sector cannot prove a sector requirement |
| maximum budget + currency | operation-specific price, `currency` | hard | unknown price/currency fails |
| minimum bedrooms | `bedrooms` | hard | unknown fails |
| minimum bathrooms | `bathrooms` | hard | unknown fails |
| parking required = `true` | `parking_spaces >= 1` | hard | unknown fails |
| pets required = `true` | `pet_policy == allowed` | hard | `unknown` fails |
| furnished preference | `furnished` | soft | no reason is asserted when unknown |
| soft preferences | canonical property facts | semantic | no invented reason when no fact overlaps |

All available properties also pass an availability gate. `null`, empty collections, and `false`
parking/pet requirements add no filter, except that a non-null budget requires both an explicit
operation and currency. Matching returns `409` until those two facts are known; it never guesses a
price column and performs no currency conversion. The API exposes every passed check on each result and
aggregate failure counts when no candidate survives.

## Embeddings and ranking

`EmbeddingProvider` is separate from structured lead extraction. Property text has a stable,
fact-only order: title, description, operation, type, city, optional sector and numeric counts, pet
policy, optional furnished state, and amenities. Lead text contains only soft preferences and the
optional furnished preference.

Production uses PostgreSQL pgvector cosine distance (`<=>`) restricted by eligible property IDs.
The API score is `clamp((cosine_similarity + 1) / 2, 0, 1)`: a ranking signal, not a probability or
compatibility percentage. UUID ascending breaks ties deterministically.

The existing `vector(1536)` is reused and configuration rejects any other dimension at startup.
A property is regenerated when its vector is absent, canonical text changes, timestamp is absent, or
provider, model, or vector-space fingerprint changes. The fingerprint is a non-sensitive SHA-256 of
provider/model/dimension and compatible endpoint identity; credentials, query strings, and raw vectors
are never persisted. There is no HNSW index for the 18-row inventory; index
design should be revisited with representative scale and `EXPLAIN ANALYZE`.

## API and persistence

- `POST /api/leads/{id}/matches?top_k=3` may generate/cache embeddings and persists a matching run;
  `top_k` is constrained to 1-10.
- `GET /api/leads/{id}/matches` returns the latest successful run without recomputation.
- Re-extracting a lead replaces its requirements and transactionally sets `invalidated_at` on current
  matching runs. Rows and matches remain as immutable execution evidence; the current UI returns to
  `not_run` until matching is run again.
- Every run stores a deterministic fingerprint of matching-relevant requirements. Completion locks the
  current requirements and run, verifies that fingerprint, and returns `409` rather than stale results
  if requirements changed while embeddings were being generated.
- Missing requirements return `409`; a missing lead returns `404`; a needed unavailable/timeout
  embedding provider returns sanitized `503`/`504`.
- Zero candidates and hard-only requests do not call an embedding provider.
- `matching_runs` stores bounded telemetry and aggregate exclusions. `property_matches` stores
  ranks, scores, passed checks, and fact-backed reasons. Neither stores raw lead text nor vectors.
- Historical run metadata, ranks, scores, checks, and grounded reasons are retained. Property display
  fields are joined from the live inventory, so a historical response reconstructed internally can
  show a newer title, description, price, or availability than existed when the run completed; this is
  execution history, not a full property snapshot. Immutable property snapshots/versioning are a
  future milestone if full point-in-time reconstruction becomes a requirement.
- Hard-only requests use UUID-stable eligible order and `semantic_score = null`; the UI explicitly says
  that no semantic ranking was applied.
- Concurrent identical POSTs may duplicate bounded computation and create two valid runs. Both remain
  consistent, and deterministic latest ordering selects one; no uniqueness lock is claimed for v0.1.
- SQLite cosine is only the deterministic local/test adapter; production ranking is PostgreSQL.
