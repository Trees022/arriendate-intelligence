# AI and Data Guardrails

## Machine output

1. Every machine-consumed response uses provider-supported strict JSON Schema where available and is always revalidated with strict Pydantic rules.
2. All schema keys are required, nullable fields preserve unknowns, extra fields are rejected, and numeric/boolean strings are not coerced.
3. Missing operation, property type, location, or budget must have a consistent `missing_information` marker.
4. Malformed, truncated, incomplete, refused, and schema-invalid output fails visibly. It is never repaired through guessed values.
5. Provider retries are bounded and restricted to timeouts, transport errors, 408/409/429, and server errors. Validation failures are not retried.
6. Prompts live in versioned files and production and live evaluation share the same request builder.

## Grounding and uncertainty

1. Extraction may use only facts explicitly supported by the original lead message.
2. Chilean `$` and “lucas” may normalize to CLP only where the prompt context supports that convention; other currencies must be explicit.
3. A boolean becomes `true` or `false` only when the message states it. Absence remains `null`.
4. Contradictory or unverifiable requirements remain visible through controlled missing-information codes.
5. The original message is preserved independently and never overwritten by normalized output.

## Human control

1. Extraction runs only after a human presses the extraction/reprocess action.
2. A successful extraction may update the internal lead status to `qualified` or `needs_information`; it performs no external action.
3. No email, WhatsApp, webhook, or other outbound message is generated or sent in this milestone.

## Privacy and observability

1. Provider and database secrets exist only in server environment variables and never in `VITE_*` values.
2. Original requests, contact data, prompts, raw provider output, credentials, and upstream error bodies are excluded from AI-run persistence.
3. Runs store only request IDs, provider/model, prompt version, timestamp, latency, status, usage, optional estimated cost, validation outcome, and sanitized errors.
4. Provider requests set `store: false`.
5. Raw generated evaluation reports stay Git-ignored by default.
6. Public deployment is blocked until authentication and ownership-aware RLS policies exist.

## Database truth

1. This milestone does not ask the model to read, rank, recommend, or modify properties.
2. Future matching cannot be inferred from the existence of structured requirements.
3. Direct `anon` and `authenticated` access to extraction tables is revoked in the PostgreSQL migration.
4. PostgreSQL integration tests assert both object privileges and actual `SET ROLE` behavior for
   `anon`, `authenticated`, and `service_role`; SQLite tests make no database-security claim.
5. The server-side direct connection remains privileged in this internal milestone. A dedicated
   least-privilege database login and ownership-aware RLS policies are required before public use.
