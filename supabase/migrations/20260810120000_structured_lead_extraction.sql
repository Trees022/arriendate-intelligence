create table public.lead_requirements (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid not null unique references public.leads(id) on delete cascade,
  operation_type text not null check (operation_type in ('rent', 'buy', 'unknown')),
  property_types text[] not null default '{}',
  locations text[] not null default '{}',
  max_budget bigint check (max_budget is null or max_budget >= 0),
  currency text check (currency is null or currency in ('CLP', 'UF', 'USD')),
  min_bedrooms smallint check (min_bedrooms is null or min_bedrooms between 0 and 30),
  min_bathrooms smallint check (min_bathrooms is null or min_bathrooms between 0 and 30),
  parking_required boolean,
  pets_required boolean,
  furnished_preference boolean,
  soft_preferences text[] not null default '{}',
  missing_information text[] not null default '{}',
  extraction_confidence numeric(4, 3) not null check (
    extraction_confidence between 0 and 1
  ),
  extraction_model text not null,
  prompt_version text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.ai_runs (
  id uuid primary key default gen_random_uuid(),
  run_type text not null,
  lead_id uuid references public.leads(id) on delete cascade,
  property_id uuid references public.properties(id) on delete set null,
  provider text not null,
  model text not null,
  prompt_version text,
  provider_request_id text,
  latency_ms integer not null default 0 check (latency_ms >= 0),
  input_tokens integer check (input_tokens is null or input_tokens >= 0),
  output_tokens integer check (output_tokens is null or output_tokens >= 0),
  estimated_cost numeric(12, 8) check (estimated_cost is null or estimated_cost >= 0),
  validation_passed boolean not null default false,
  status text not null default 'running' check (status in ('running', 'succeeded', 'failed')),
  error_code text,
  error_message text,
  created_at timestamptz not null default now()
);

create index ai_runs_lead_created_idx
  on public.ai_runs (lead_id, created_at desc);

create trigger lead_requirements_set_updated_at
before update on public.lead_requirements
for each row execute function public.set_updated_at();

alter table public.lead_requirements enable row level security;
alter table public.ai_runs enable row level security;

revoke all on table public.lead_requirements from anon, authenticated;
revoke all on table public.ai_runs from anon, authenticated;

comment on table public.ai_runs is
  'Sanitized execution metadata. Prompts, lead text, raw model output, and credentials are not stored.';
