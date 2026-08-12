create table public.matching_runs (
  id uuid primary key default gen_random_uuid(),
  lead_id uuid not null references public.leads(id) on delete cascade,
  provider text not null,
  model text not null,
  algorithm_version text not null,
  requested_top_k smallint not null check (requested_top_k between 1 and 10),
  total_properties integer not null default 0 check (total_properties >= 0),
  candidate_count integer not null default 0 check (candidate_count >= 0),
  result_count integer not null default 0 check (result_count >= 0),
  latency_ms integer not null default 0 check (latency_ms >= 0),
  embedding_latency_ms integer not null default 0 check (embedding_latency_ms >= 0),
  status text not null default 'running' check (status in ('running', 'succeeded', 'failed')),
  exclusion_summary jsonb not null default '[]'::jsonb,
  error_code text,
  error_message text,
  created_at timestamptz not null default now()
);

create table public.property_matches (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references public.matching_runs(id) on delete cascade,
  lead_id uuid not null references public.leads(id) on delete cascade,
  property_id uuid not null references public.properties(id) on delete restrict,
  rank smallint not null check (rank between 1 and 10),
  semantic_score numeric(6, 5) check (semantic_score is null or semantic_score between 0 and 1),
  hard_constraint_matches jsonb not null default '[]'::jsonb,
  soft_match_reasons jsonb not null default '[]'::jsonb,
  algorithm_version text not null,
  embedding_model text,
  created_at timestamptz not null default now(),
  unique (run_id, property_id),
  unique (run_id, rank)
);

create index matching_runs_lead_created_idx
  on public.matching_runs (lead_id, created_at desc);
create index property_matches_run_rank_idx
  on public.property_matches (run_id, rank);

alter table public.matching_runs enable row level security;
alter table public.property_matches enable row level security;

revoke all on table public.matching_runs from anon, authenticated;
revoke all on table public.property_matches from anon, authenticated;

comment on table public.matching_runs is
  'Observable property matching executions without raw lead text or embedding vectors.';
comment on table public.property_matches is
  'Grounded ranked results after deterministic hard-constraint eligibility.';
