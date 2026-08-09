create extension if not exists pgcrypto;
create extension if not exists vector;

create table public.leads (
  id uuid primary key default gen_random_uuid(),
  name text check (name is null or char_length(name) <= 120),
  email text check (email is null or char_length(email) <= 320),
  phone text check (phone is null or char_length(phone) <= 40),
  original_request text not null check (char_length(original_request) between 10 and 10000),
  idempotency_key uuid not null unique,
  status text not null default 'new' check (
    status in ('new', 'qualified', 'needs_information', 'matched', 'contacted', 'closed_won', 'closed_lost')
  ),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.properties (
  id uuid primary key default gen_random_uuid(),
  title text not null check (char_length(title) <= 180),
  description text not null,
  operation_type text not null check (operation_type in ('rent', 'buy')),
  property_type text not null,
  city text not null,
  sector text,
  monthly_price bigint check (monthly_price is null or monthly_price >= 0),
  sale_price bigint check (sale_price is null or sale_price >= 0),
  currency text not null default 'CLP' check (char_length(currency) = 3),
  bedrooms smallint check (bedrooms is null or bedrooms >= 0),
  bathrooms smallint check (bathrooms is null or bathrooms >= 0),
  parking_spaces smallint check (parking_spaces is null or parking_spaces >= 0),
  pet_policy text not null default 'unknown' check (pet_policy in ('allowed', 'not_allowed', 'unknown')),
  furnished boolean,
  square_meters numeric(8, 2) check (square_meters is null or square_meters > 0),
  amenities text[] not null default '{}',
  availability_status text not null default 'available' check (
    availability_status in ('available', 'reserved', 'unavailable')
  ),
  source_text text not null,
  embedding_text text not null,
  embedding vector(1536),
  embedding_model text,
  embedding_updated_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint property_operation_price_consistent check (
    (operation_type = 'rent' and monthly_price is not null and sale_price is null)
    or (operation_type = 'buy' and sale_price is not null and monthly_price is null)
  )
);

create index properties_inventory_idx
  on public.properties (availability_status, operation_type, city);
create index properties_monthly_price_idx
  on public.properties (monthly_price) where monthly_price is not null;
create index properties_sale_price_idx
  on public.properties (sale_price) where sale_price is not null;
create index properties_bedrooms_idx
  on public.properties (bedrooms) where bedrooms is not null;
create index properties_amenities_idx
  on public.properties using gin (amenities);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
security invoker
set search_path = ''
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

create trigger leads_set_updated_at
before update on public.leads
for each row execute function public.set_updated_at();

create trigger properties_set_updated_at
before update on public.properties
for each row execute function public.set_updated_at();

alter table public.leads enable row level security;
alter table public.properties enable row level security;

revoke all on table public.leads from anon, authenticated;
revoke all on table public.properties from anon, authenticated;

comment on table public.properties is 'Synthetic demo inventory. Real client data is prohibited in v0.1.';
comment on column public.properties.embedding_text is 'Canonical stored facts used to create the embedding.';
comment on column public.properties.embedding is 'Reserved for the Phase 1 semantic-ranking milestone.';
