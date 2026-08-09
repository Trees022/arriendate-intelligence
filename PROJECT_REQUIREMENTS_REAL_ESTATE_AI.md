# PROJECT_REQUIREMENTS.md

## Project working name
**Arriendate Intelligence**  
Real Estate AI Operating Layer for lead qualification, property matching, RAG-assisted answers and agentic follow-up.

## 1. Product vision
Build a portfolio-grade real-estate AI system that demonstrates practical use of CRM, automation, structured LLM outputs, retrieval, tool calling, human-in-the-loop workflows and measurable evaluation.

The system should receive an unstructured real-estate lead, convert it into structured CRM data, identify the most suitable properties, explain the match using only available data, and help a human agent decide the next action.

The project must be useful as a standalone demo, technically credible in an interview, and extensible into a future commercial product.

## 2. Core principle
Do not build “AI for the sake of AI”. Every AI component must solve a concrete business problem:

- Reduce time spent manually reading and qualifying leads.
- Reduce missed or poorly followed-up leads.
- Improve consistency in property recommendations.
- Make CRM data easier to query and act on.
- Provide traceable, grounded explanations instead of opaque recommendations.

## 3. MVP scope — v0.1
The first usable version must implement this complete flow:

**Lead text → structured extraction → CRM persistence → property filtering/retrieval → top 3 matches → grounded explanation → human review**

Example lead input:

> “Somos una pareja joven con un perro. Buscamos departamento en Viña del Mar, máximo $700.000 mensuales, idealmente 2 dormitorios, estacionamiento y un sector tranquilo porque trabajamos desde casa.”

Expected result:

1. Extract and save structured requirements.
2. Apply hard constraints such as budget, location, pet policy and minimum bedrooms.
3. Rank remaining properties semantically using the lead’s softer preferences.
4. Return up to 3 recommendations with a score and explanation.
5. Clearly state unmet requirements and uncertainty.
6. Never invent property attributes that are not present in the database.

## 4. MVP functional requirements

### FR-01 — Lead intake
Provide a simple web form where a user can paste or type a natural-language property request.

Required fields:
- Lead name (optional for demo).
- Contact email or phone (optional for demo).
- Free-text request (required).

The form must persist the original text before any AI processing.

### FR-02 — Structured lead extraction
Use an LLM with structured output to transform the free-text request into validated JSON.

Suggested schema:

```json
{
  "operation_type": "rent | buy | unknown",
  "property_type": ["apartment"],
  "locations": ["Viña del Mar"],
  "max_budget": 700000,
  "currency": "CLP",
  "min_bedrooms": 2,
  "min_bathrooms": null,
  "parking_required": true,
  "pets_required": true,
  "furnished_preference": null,
  "soft_preferences": [
    "quiet area",
    "good for working from home"
  ],
  "missing_information": [],
  "confidence": 0.0
}
```

Requirements:
- Validate output server-side.
- Reject malformed model output.
- Preserve null/unknown values instead of hallucinating them.
- Store raw model output for debugging only if safe.
- Log model name, latency and token/cost metadata when available.

### FR-03 — Property inventory
Create a demo property inventory with at least 15 realistic but synthetic Chilean listings.

Each property should contain at minimum:
- id
- title
- description
- operation_type
- property_type
- city
- comuna/sector
- monthly_price or sale_price
- currency
- bedrooms
- bathrooms
- parking_spaces
- pet_policy
- furnished
- square_meters
- amenities
- availability_status
- source_text
- embedding
- created_at
- updated_at

Do not use real client data in the initial public demo.

### FR-04 — Hybrid property matching
Matching must occur in two stages.

**Stage A — deterministic filters**
Apply hard constraints first, for example:
- operation type
- availability
- budget
- location when explicitly required
- minimum bedrooms
- parking required
- pet requirement

**Stage B — semantic ranking**
Rank the remaining properties using embeddings/vector similarity against:
- lead free text
- extracted soft preferences
- property description and relevant features

The system must not allow semantic similarity to override an explicit hard constraint.

### FR-05 — Match score
Return a normalized score for each recommendation.

The score should be explainable and composed of separate factors rather than an unexplained LLM number.

Suggested initial formula:
- 50% hard/structured feature fit
- 30% semantic similarity
- 20% optional preference fit

Keep the scoring implementation configurable.

### FR-06 — Grounded recommendation explanation
For each match, generate a short explanation using only the structured lead and property record.

The explanation must contain:
- Why the property matches.
- Which preferences are satisfied.
- Which requested attributes are unknown or not satisfied.
- No invented amenities, policies or location facts.

Example:

> **84% — Departamento Los Castaños**  
> Está dentro del presupuesto, tiene 2 dormitorios, estacionamiento y admite mascotas. Además, la descripción indica un entorno principalmente residencial, lo que coincide con la preferencia por tranquilidad. No existe información suficiente para confirmar calidad acústica del departamento.

### FR-07 — Lead detail view
Create a CRM-like lead page showing:
- Original message.
- Extracted requirements.
- Current lead status.
- Top property matches.
- AI explanation.
- Processing metadata.
- Manual notes.

Initial lead statuses:
- new
- qualified
- needs_information
- matched
- contacted
- closed_won
- closed_lost

### FR-08 — Human approval
The MVP must not automatically send messages to external users.

AI may propose a follow-up action or draft a message, but the human user must approve it.

Add a button:
**“Generate follow-up draft”**

The draft should use lead/property context but must not be sent automatically.

### FR-09 — RAG property assistant
Provide a small chat/assistant inside a lead or property page.

Supported questions may include:
- “¿Por qué esta propiedad hace match con este lead?”
- “¿Qué requisito no cumple?”
- “¿Cuál de estas propiedades admite mascotas?”
- “¿Qué información falta antes de contactar al lead?”

Rules:
- Retrieve only from application-controlled data.
- Cite property records internally by ID/title.
- If the answer is not supported, state that the information is unavailable.
- Never infer legal, financial or contractual facts from missing information.

## 5. Non-functional requirements

### NFR-01 — Reliability
- All LLM outputs that drive application logic must use schemas/validation.
- All tool/API failures must return useful user-facing error states.
- Retries must be bounded.
- No silent failures.

### NFR-02 — Security
- Secrets must exist only in environment variables/server-side configuration.
- Never expose service-role or privileged Supabase keys to the browser.
- Use Row Level Security where relevant.
- Sanitize user-provided text before rendering.
- Do not log secrets or sensitive credentials.

### NFR-03 — Observability
For every AI execution, capture where available:
- request ID
- model/provider
- timestamp
- latency
- status
- token usage
- estimated cost
- validation success/failure
- retrieval result IDs

### NFR-04 — Maintainability
- TypeScript strict mode.
- Python type hints.
- Clear domain/service/repository boundaries.
- No giant service files.
- Configuration rather than hard-coded business rules where practical.
- Public functions and non-obvious logic documented.

### NFR-05 — UX
The demo should feel like an internal business tool, not an AI toy.

Prioritize:
- fast lead entry
- readable CRM layout
- visible match reasoning
- clear uncertainty
- minimal clicks

## 6. Technical architecture

### Frontend
- React
- TypeScript
- Vite
- React Router
- Lightweight component system of choice

### Data/Auth
- Supabase
- PostgreSQL
- pgvector for embeddings/vector search
- Supabase Auth if authentication is included in v0.1

### AI/backend service
- Python
- FastAPI
- Pydantic for structured schemas
- Provider abstraction so the LLM can later be switched between Azure/OpenAI-compatible providers

### Automation
Not required for the first vertical slice.

Phase 2 may add:
- n8n
- webhooks
- scheduled follow-up checks
- CRM/event automation

### Deployment
Preferred target:
- Frontend: Vercel
- API: deployable FastAPI service
- Database: Supabase

Local development must work before deployment is attempted.

## 7. Suggested domain model

### leads
- id
- name
- email
- phone
- original_request
- status
- created_at
- updated_at

### lead_requirements
- id
- lead_id
- operation_type
- property_types
- locations
- max_budget
- currency
- min_bedrooms
- min_bathrooms
- parking_required
- pets_required
- furnished_preference
- soft_preferences
- missing_information
- extraction_confidence
- extraction_model
- created_at

### properties
Use fields defined in FR-03.

### property_matches
- id
- lead_id
- property_id
- hard_fit_score
- semantic_score
- preference_score
- total_score
- explanation
- unmet_requirements
- created_at

### ai_runs
- id
- run_type
- lead_id nullable
- property_id nullable
- provider
- model
- latency_ms
- input_tokens nullable
- output_tokens nullable
- estimated_cost nullable
- validation_passed
- error_message nullable
- created_at

### notes
- id
- lead_id
- content
- created_at

## 8. API contract — initial proposal

### POST /api/leads
Create a lead and persist original request.

### POST /api/leads/{lead_id}/extract
Run structured requirement extraction.

### POST /api/leads/{lead_id}/match
Run deterministic filtering + semantic ranking and persist matches.

### GET /api/leads/{lead_id}
Return lead, requirements and latest matches.

### GET /api/properties
List/search demo properties.

### GET /api/properties/{property_id}
Return full property data.

### POST /api/leads/{lead_id}/follow-up-draft
Generate a human-reviewed follow-up message.

### POST /api/assistant/query
Grounded RAG question over allowed application data.

## 9. AI guardrails

The system must follow these rules:

1. Database truth outranks model assumptions.
2. Missing data remains missing.
3. LLMs do not decide hard constraints.
4. All machine-consumed LLM output is validated.
5. Property recommendations must reference existing property IDs.
6. A property that violates a required hard constraint cannot rank as a valid match.
7. External communication requires human approval in v0.1.
8. When retrieval is insufficient, answer with uncertainty rather than fabricate.
9. Keep prompts versioned in source control.
10. Add test cases for known hallucination/edge scenarios.

## 10. Evaluation requirements

Create a small evaluation dataset with at least 15 synthetic leads.

Include cases such as:
- exact match
- no property under budget
- pets mandatory
- contradictory requirements
- missing budget
- vague location
- Spanish colloquial phrasing
- multiple acceptable communes
- user preference that cannot be objectively verified

Measure at minimum:
- extraction schema validity rate
- required-field extraction accuracy
- hard-constraint violation rate
- top-3 relevance by manually labelled expected matches
- unsupported-claim rate in explanations
- average AI latency
- approximate AI cost per processed lead

The objective is not only “the demo works”; the project must show that the AI layer can be evaluated.

## 11. Testing requirements

### Backend
- Unit tests for scoring.
- Unit tests for hard filters.
- Structured-output validation tests.
- Integration test for full lead → extract → match flow.
- Edge-case tests for missing/contradictory values.

### Frontend
- Form validation.
- Loading/error states.
- Lead detail rendering.
- Match card rendering.

### End-to-end
At least one automated or reproducible manual scenario:
1. Submit lead.
2. Extract JSON.
3. Persist data.
4. Generate matches.
5. Display top 3.
6. Open one recommendation.
7. Generate follow-up draft.

## 12. MVP UI pages

### /dashboard
- Lead count
- New leads
- Qualified leads
- Leads needing information
- Recent matches

### /leads/new
- Lead intake form

### /leads/:id
- Original request
- Structured requirements
- Status
- Top matches
- Follow-up draft action
- AI metadata/debug section collapsible

### /properties
- Inventory table/cards
- Basic filters

### /properties/:id
- Property details
- Description/features
- Matching metadata where relevant

## 13. Seed/demo data

Create synthetic Chilean real-estate records oriented around Valparaíso Region, e.g.:
- Viña del Mar
- Valparaíso
- Concón
- Quilpué

The seed dataset should deliberately include variation in:
- budget
- bedrooms
- pet policy
- parking
- furnished status
- urban vs quieter sectors
- incomplete attributes

This variation is necessary to test ranking and uncertainty.

## 14. Phase plan

### Phase 0 — Foundation
- Initialize repository.
- Create frontend + API projects.
- Configure linting, formatting and tests.
- Define database schema/migrations.
- Add seed properties.
- Add `.env.example`.
- Write README architecture section.

### Phase 1 — Vertical MVP
- Lead intake.
- Structured extraction.
- Persist requirements.
- Hard filtering.
- Embeddings/vector ranking.
- Top-3 match UI.
- Grounded explanation.

**Do not proceed to Phase 2 until this entire flow works end-to-end.**

### Phase 2 — Agentic CRM layer
- Follow-up draft agent.
- Tool calling for CRM reads/updates.
- Human approval workflow.
- n8n webhook integration.
- Lead-priority dashboard.

### Phase 3 — RAG + evaluation
- Property/document assistant.
- Prompt/version tracking.
- Evaluation suite.
- Cost/latency dashboard.
- Regression tests for AI behavior.

### Phase 4 — Multi-agent experiments
Potential specialized agents:
- Lead Qualification Agent
- Property Matching Agent
- Follow-up Agent
- CRM Operations Agent

Use multiple agents only when there is a demonstrated reason to separate responsibilities. Do not create a “multi-agent” architecture merely for branding.

### Phase 5 — Quantum research module
This is experimental and must remain separate from production logic.

Candidate problem:
**Optimize assignment of leads → agents → property/viewing slots under constraints.**

Requirements:
- Formalize objective function and constraints.
- Build classical baseline first.
- Create quantum/quantum-inspired experiment second.
- Compare quality, runtime and scalability.
- Document when quantum methods do and do not make practical sense.
- Never claim quantum advantage without evidence.

Place research work under `/research/quantum-optimization` or an equivalent isolated module.

## 15. Explicit non-goals for v0.1

Do NOT implement initially:
- automatic WhatsApp/email sending
- production voice agents
- real payments
- scraping real estate portals
- real client data
- autonomous contract/legal decisions
- large multi-tenant SaaS architecture
- quantum integration into the main recommendation engine
- dozens of microservices

The first goal is one excellent vertical slice, not a giant unfinished platform.

## 16. Repository expectations

Suggested structure:

```text
/
  apps/
    web/
    api/
  supabase/
    migrations/
    seed/
  packages/
    shared-types/        # optional if useful
  evals/
    datasets/
    scripts/
    results/
  research/
    quantum-optimization/
  docs/
    architecture.md
    ai-guardrails.md
    evaluation.md
  .env.example
  README.md
  PROJECT_REQUIREMENTS.md
```

Prefer simplicity over forcing this exact structure. If a simpler structure is more appropriate, document the reason before changing it.

## 17. README requirements

The README should eventually explain:
- Business problem.
- Product demo flow.
- Architecture diagram.
- Tech stack.
- Why hybrid filtering + vector search is used.
- AI guardrails.
- Evaluation methodology.
- Local setup.
- Environment variables.
- Screenshots/GIF when available.
- Known limitations.
- Future work.

This README is part of the product because the repository is intended to demonstrate engineering quality to recruiters, collaborators and potential clients.

## 18. Definition of Done — MVP v0.1

MVP is complete only when all of the following are true:

- A user can submit an unstructured lead request.
- The original input is persisted.
- The AI produces schema-valid structured requirements.
- At least 15 synthetic properties exist.
- Hard constraints are applied deterministically.
- Semantic ranking is performed only after hard filtering.
- Up to 3 relevant matches are returned.
- Every recommendation explains supported and unsupported requirements.
- No property attributes are invented during the tested happy path.
- A lead detail page presents the complete flow cleanly.
- A human can generate but must approve a follow-up draft.
- AI runs have basic latency/validation observability.
- Core scoring/filter/extraction behaviors have tests.
- Local setup is reproducible from README instructions.
- The repository contains no secrets.

## 19. Instructions for the coding agent

Treat this document as the product source of truth.

Before writing substantial code:
1. Inspect the existing repository.
2. Produce a short architecture/implementation plan.
3. Identify ambiguities or risky assumptions.
4. Prefer the smallest architecture that satisfies the MVP.
5. Implement Phase 0 and Phase 1 before optional features.

During implementation:
- Work incrementally.
- Keep the application runnable after each milestone.
- Run type-checking, linting and tests frequently.
- Do not silently alter product requirements.
- If a requirement needs to change, document the reason.
- Verify important UI flows in the browser.
- Do not mark work complete solely because code compiles.
- Prefer deterministic business logic over LLM reasoning where deterministic logic is sufficient.
- Keep AI prompts versioned and easy to inspect.

At the end of each milestone, report:
- What was implemented.
- Files/modules changed.
- Tests executed and results.
- Browser/UI verification performed.
- Known limitations.
- Recommended next milestone.

## 20. First task for Antigravity

Read `PROJECT_REQUIREMENTS.md` completely.

Then do **only Phase 0 planning**, not the entire product at once.

Produce an implementation-plan artifact containing:
- proposed repository structure
- architecture decisions
- database schema
- API boundary
- AI provider abstraction
- embedding strategy
- test strategy
- exact ordered tasks for the first vertical slice
- risks/assumptions

After the plan is reviewed, initialize the codebase and implement the first vertical slice:

**Create synthetic property inventory + lead intake + persistent lead record.**

Do not add RAG, n8n, multi-agent orchestration or quantum code yet.
