# Structured Lead Extraction Evaluation

## Scope

The evaluation covers only the current structured-extraction contract. It deliberately excludes property filters, semantic rank, matches, recommendation claims, RAG, agents, and external actions.

Two versioned datasets are committed:

- `evals/datasets/lead_extraction.v0.1.json`: 15 synthetic Spanish lead messages with stable IDs, scenario labels, reviewed field expectations, and deterministic fixture outputs.
- `evals/datasets/lead_extraction_invalid.v0.1.json`: 7 malformed or incomplete outputs covering truncated JSON, missing keys, extra keys, strict types, unsupported enums, inconsistent unknown markers, and string booleans.

The valid cases cover CLP/UF/USD budgets, “lucas”, missing budget, missing/vague location, unknown or contradictory operation, multiple property types/locations, pets and parking as both positive and negative requirements, furnished preference, commercial property, and unverifiable soft preferences.

## Metrics

The evaluator reports:

- strict schema validity;
- exact accuracy over manually labeled expected fields;
- invalid-output rejection rate;
- average provider latency;
- token totals when returned;
- approximate USD cost only when both token usage and configured per-million prices exist;
- provider, model, prompt version, dataset versions, mode, and failure case IDs.

It does not persist prompts or raw generated output in the result report.

## Deterministic run

```powershell
.\.venv\Scripts\python.exe evals\scripts\evaluate_lead_extraction.py
```

This mode uses the same prompt builder and strict Pydantic schema as production, but supplies deterministic fixture outputs. It is appropriate for CI contract regression and does not measure real model quality.

Current reviewed fixture baseline:

| Metric | Result |
|---|---:|
| Valid cases | 15/15 |
| Schema validity | 100% |
| Labeled field accuracy | 69/69 (100%) |
| Invalid outputs rejected | 7/7 (100%) |
| Token totals | 1,800 input / 1,200 output (fixture metadata) |
| Cost | unavailable without configured prices |

Latency is intentionally omitted from the static baseline because local fixture timing is not a provider-performance measurement.

## Opt-in live run

Configure the provider entirely through server-side `ARRIENDATE_AI_*` variables, then run:

```powershell
.\.venv\Scripts\python.exe evals\scripts\evaluate_lead_extraction.py --mode live
```

Live evaluation uses the production prompt, schema, configured provider/model, bounded retry policy, and real usage/latency when returned. It can incur provider cost and generated reports remain ignored at `evals/results/lead_extraction.latest.json`.

No live-model baseline is claimed until a real key, provider availability, and current pricing configuration are supplied.

The PostgreSQL integration job continues to use this deterministic fixture provider. Database
validation covers persistence and rollback of successful, malformed, and incomplete extraction
outputs, but it does not make or imply a live-model quality claim.
