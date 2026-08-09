# AI and Data Guardrails

These rules apply even before the AI layer exists.

## Database truth

1. A model cannot create or modify property facts.
2. Missing data remains missing and is rendered as unknown.
3. Recommendations may reference only existing property IDs.
4. Hard constraints will be deterministic gates, never semantic preferences.
5. Semantic similarity will run only after hard filtering.

## Machine output

1. Every machine-consumed model response must use a strict Pydantic schema.
2. Malformed output fails visibly and is not repaired by guessing.
3. Prompts must live in versioned source files with explicit versions.
4. Tests use deterministic fake providers and require no API key.
5. Provider retries are bounded and limited to safe transient failures.

## Grounding and uncertainty

1. Explanation claims must be derived from lead/property comparison facts.
2. Unknown pet, parking, furnishing, acoustic, safety, legal, financial, or contractual facts cannot be inferred.
3. An unknown value fails a required hard constraint.
4. Scores are ranking values, not probabilities or promises.
5. Insufficient retrieval produces an explicit unavailable-information answer.

## Human control

1. No email, WhatsApp, or external message is sent automatically in v0.1.
2. Future follow-up text is a draft that requires a human action to send elsewhere.
3. Lead status changes are explicit operations, not hidden AI side effects.

## Privacy and observability

1. Secrets exist only in server environment variables.
2. Original request bodies and contact fields are excluded from normal logs.
3. AI runs record request/run ID, provider, model, prompt version, timing, usage, validation result, and sanitized errors where available.
4. Raw model output is not persisted by default.
5. Public deployment is blocked until authentication and ownership-aware RLS policies are implemented.
