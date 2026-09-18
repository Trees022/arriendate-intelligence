-- Migration: Property Operations Pilot (M2)
-- Adds operational fields to properties and introduces media, packages, variants, targets, campaigns, jobs, and publications.

-- 1. Extend properties table
alter table public.properties
  add column if not exists reference_code text check (reference_code is null or char_length(reference_code) <= 50),
  add column if not exists source_notes text,
  add column if not exists address_text text check (address_text is null or char_length(address_text) <= 250),
  add column if not exists built_area_m2 numeric(10, 2) check (built_area_m2 is null or built_area_m2 > 0),
  add column if not exists land_area_m2 numeric(10, 2) check (land_area_m2 is null or land_area_m2 > 0),
  add column if not exists commercial_status text not null default 'draft' check (
    commercial_status in ('draft', 'active', 'reserved', 'closed', 'archived')
  );

create index if not exists properties_commercial_status_idx
  on public.properties (commercial_status, city);

-- 2. Property media
create table public.property_media (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references public.properties(id) on delete cascade,
  storage_key text not null unique,
  original_filename text not null,
  media_type text not null default 'image' check (media_type in ('image')),
  mime_type text not null check (mime_type in ('image/jpeg', 'image/png', 'image/webp')),
  size_bytes bigint not null check (size_bytes > 0 and size_bytes <= 10485760),
  position integer not null default 0 check (position >= 0),
  is_cover boolean not null default false,
  created_at timestamptz not null default now()
);

create index property_media_property_pos_idx
  on public.property_media (property_id, position);

-- 3. Publication packages
create table public.publication_packages (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references public.properties(id) on delete cascade,
  property_fingerprint text not null,
  status text not null default 'draft' check (status in ('draft', 'approved', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index publication_packages_property_idx
  on public.publication_packages (property_id, status);

create trigger publication_packages_set_updated_at
  before update on public.publication_packages
  for each row execute function public.set_updated_at();

-- 4. Publication package variants
create table public.publication_package_variants (
  id uuid primary key default gen_random_uuid(),
  package_id uuid not null references public.publication_packages(id) on delete cascade,
  channel_type text not null check (
    channel_type in ('facebook_marketplace', 'facebook_group', 'portal_inmobiliario', 'yapo', 'whatsapp_catalog')
  ),
  headline text not null,
  body text not null,
  short_body text,
  highlights text[] not null default '{}',
  cta text not null,
  suggested_media_ids uuid[] not null default '{}',
  warnings text[] not null default '{}',
  created_at timestamptz not null default now(),
  constraint uq_package_channel unique (package_id, channel_type)
);

create index package_variants_package_idx
  on public.publication_package_variants (package_id);

-- 5. Publication targets
create table public.publication_targets (
  id uuid primary key default gen_random_uuid(),
  name text not null check (char_length(name) <= 150),
  channel_type text not null check (
    channel_type in ('facebook_marketplace', 'facebook_group', 'portal_inmobiliario', 'yapo', 'whatsapp_catalog')
  ),
  execution_mode text not null check (
    execution_mode in ('assisted', 'manual', 'api', 'local_agent')
  ),
  destination_url text,
  active boolean not null default true,
  minimum_repost_interval_hours integer not null default 72 check (minimum_repost_interval_hours >= 0),
  notes text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index publication_targets_active_channel_idx
  on public.publication_targets (active, channel_type);

create trigger publication_targets_set_updated_at
  before update on public.publication_targets
  for each row execute function public.set_updated_at();

-- 6. Campaigns
create table public.campaigns (
  id uuid primary key default gen_random_uuid(),
  property_id uuid not null references public.properties(id) on delete cascade,
  package_id uuid not null references public.publication_packages(id) on delete cascade,
  status text not null default 'draft' check (status in ('draft', 'active', 'paused', 'completed', 'archived')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index campaigns_property_status_idx
  on public.campaigns (property_id, status);

create trigger campaigns_set_updated_at
  before update on public.campaigns
  for each row execute function public.set_updated_at();

-- 7. Campaign targets
create table public.campaign_targets (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references public.campaigns(id) on delete cascade,
  target_id uuid not null references public.publication_targets(id) on delete cascade,
  created_at timestamptz not null default now(),
  constraint uq_campaign_target unique (campaign_id, target_id)
);

create index campaign_targets_campaign_idx
  on public.campaign_targets (campaign_id);

-- 8. Publication jobs
create table public.publication_jobs (
  id uuid primary key default gen_random_uuid(),
  campaign_id uuid not null references public.campaigns(id) on delete cascade,
  campaign_target_id uuid references public.campaign_targets(id) on delete set null,
  property_id uuid not null references public.properties(id) on delete cascade,
  target_id uuid not null references public.publication_targets(id) on delete cascade,
  package_id uuid not null references public.publication_packages(id) on delete cascade,
  variant_type text not null check (
    variant_type in ('facebook_marketplace', 'facebook_group', 'portal_inmobiliario', 'yapo', 'whatsapp_catalog')
  ),
  execution_mode text not null check (
    execution_mode in ('assisted', 'manual', 'api', 'local_agent')
  ),
  status text not null default 'pending' check (
    status in ('pending', 'ready', 'running', 'published', 'failed', 'cooldown', 'cancelled')
  ),
  scheduled_at timestamptz not null default now(),
  next_eligible_at timestamptz,
  attempt_count integer not null default 0 check (attempt_count >= 0),
  error_code text,
  error_message text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index publication_jobs_status_cooldown_idx
  on public.publication_jobs (status, next_eligible_at);
create index publication_jobs_property_target_idx
  on public.publication_jobs (property_id, target_id);
create index publication_jobs_campaign_idx
  on public.publication_jobs (campaign_id);

create trigger publication_jobs_set_updated_at
  before update on public.publication_jobs
  for each row execute function public.set_updated_at();

-- 9. Publications (audit trail)
create table public.publications (
  id uuid primary key default gen_random_uuid(),
  job_id uuid references public.publication_jobs(id) on delete set null,
  property_id uuid not null references public.properties(id) on delete cascade,
  campaign_id uuid not null references public.campaigns(id) on delete cascade,
  target_id uuid not null references public.publication_targets(id) on delete cascade,
  package_id uuid not null references public.publication_packages(id) on delete cascade,
  variant_type text not null check (
    variant_type in ('facebook_marketplace', 'facebook_group', 'portal_inmobiliario', 'yapo', 'whatsapp_catalog')
  ),
  published_at timestamptz not null default now(),
  publication_url text,
  execution_mode text not null check (
    execution_mode in ('assisted', 'manual', 'api', 'local_agent')
  ),
  created_at timestamptz not null default now()
);

create index publications_property_published_idx
  on public.publications (property_id, published_at desc);
create index publications_campaign_idx
  on public.publications (campaign_id);

-- 10. Security: RLS & Permissions
alter table public.property_media enable row level security;
alter table public.publication_packages enable row level security;
alter table public.publication_package_variants enable row level security;
alter table public.publication_targets enable row level security;
alter table public.campaigns enable row level security;
alter table public.campaign_targets enable row level security;
alter table public.publication_jobs enable row level security;
alter table public.publications enable row level security;

revoke all on table public.property_media from anon, authenticated;
revoke all on table public.publication_packages from anon, authenticated;
revoke all on table public.publication_package_variants from anon, authenticated;
revoke all on table public.publication_targets from anon, authenticated;
revoke all on table public.campaigns from anon, authenticated;
revoke all on table public.campaign_targets from anon, authenticated;
revoke all on table public.publication_jobs from anon, authenticated;
revoke all on table public.publications from anon, authenticated;
