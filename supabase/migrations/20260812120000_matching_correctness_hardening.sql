alter table public.properties
  add column embedding_provider text,
  add column embedding_space_id text;

-- Existing vectors predate vector-space identity metadata and are unsafe to reuse.
update public.properties
set embedding = null,
    embedding_model = null,
    embedding_provider = null,
    embedding_space_id = null,
    embedding_updated_at = null;

alter table public.matching_runs
  add column requirements_fingerprint text,
  add column embedding_space_id text,
  add column invalidated_at timestamptz;

-- Runs created before this migration remain auditable but can never be presented as current.
update public.matching_runs
set requirements_fingerprint = repeat('0', 64),
    embedding_space_id = repeat('0', 64),
    invalidated_at = coalesce(invalidated_at, now()),
    result_count = case when status = 'failed' then 0 else result_count end,
    error_code = case when status = 'failed' then coalesce(error_code, 'legacy_failure') else null end,
    error_message = case
      when status = 'failed' then coalesce(error_message, 'Ejecución histórica fallida')
      else null
    end;

alter table public.matching_runs
  alter column requirements_fingerprint set not null,
  alter column embedding_space_id set not null,
  add constraint matching_fingerprint_length check (length(requirements_fingerprint) = 64),
  add constraint matching_space_id_length check (length(embedding_space_id) = 64),
  add constraint matching_count_consistency check (
    candidate_count <= total_properties
    and result_count <= candidate_count
    and result_count <= requested_top_k
  ),
  add constraint matching_status_consistency check (
    (status = 'running' and result_count = 0 and error_code is null and error_message is null)
    or (status = 'succeeded' and error_code is null and error_message is null)
    or (
      status = 'failed' and result_count = 0
      and error_code is not null and error_message is not null
    )
  ),
  add constraint matching_runs_id_lead_key unique (id, lead_id);

alter table public.property_matches
  drop constraint property_matches_run_id_fkey,
  add constraint property_matches_run_lead_fkey
    foreign key (run_id, lead_id)
    references public.matching_runs(id, lead_id)
    on delete cascade;

create index matching_runs_current_lead_idx
  on public.matching_runs (lead_id, created_at desc, id desc)
  where invalidated_at is null;

comment on column public.properties.embedding_space_id is
  'Non-sensitive SHA-256 identity of provider, model, dimension, and compatible endpoint.';
comment on column public.matching_runs.requirements_fingerprint is
  'SHA-256 of the canonical matching-relevant requirement snapshot used by this run.';
comment on column public.matching_runs.invalidated_at is
  'When set, the historical run and its matches are retained but cannot be served as current.';
