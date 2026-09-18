-- Migration: Property Command Center (M3)
-- Evolves Property Operations with explicit channel capabilities, attribution,
-- engagement and conversations. No OAuth credentials are stored by this schema.

-- 1. Expand supported channel-specific package, target, job and publication variants.
alter table public.publication_package_variants
  drop constraint if exists publication_package_variants_channel_type_check;
alter table public.publication_package_variants
  add constraint publication_package_variants_channel_type_check check (
    channel_type in (
      'facebook_page', 'facebook_marketplace', 'facebook_group',
      'instagram_professional', 'portal_inmobiliario', 'yapo',
      'whatsapp_catalog', 'website', 'email', 'generic'
    )
  );
alter table public.publication_package_variants
  add constraint publication_package_variants_text_bounds check (
    char_length(headline) <= 500
    and char_length(body) <= 20000
    and (short_body is null or char_length(short_body) <= 2000)
    and char_length(cta) <= 1000
  );

alter table public.publication_targets
  drop constraint if exists publication_targets_channel_type_check;
alter table public.publication_targets
  add constraint publication_targets_channel_type_check check (
    channel_type in (
      'facebook_page', 'facebook_marketplace', 'facebook_group',
      'instagram_professional', 'portal_inmobiliario', 'yapo',
      'whatsapp_catalog', 'website', 'email', 'generic'
    )
  );
alter table public.publication_targets
  add constraint publication_targets_assisted_surface_not_api check (
    not (
      channel_type in ('facebook_group', 'facebook_marketplace')
      and execution_mode = 'api'
    )
  );
alter table public.publication_targets
  add constraint publication_targets_text_bounds check (
    (destination_url is null or char_length(destination_url) <= 2000)
    and (notes is null or char_length(notes) <= 2000)
  );

alter table public.publication_jobs
  drop constraint if exists publication_jobs_variant_type_check;
alter table public.publication_jobs
  add constraint publication_jobs_variant_type_check check (
    variant_type in (
      'facebook_page', 'facebook_marketplace', 'facebook_group',
      'instagram_professional', 'portal_inmobiliario', 'yapo',
      'whatsapp_catalog', 'website', 'email', 'generic'
    )
  );
alter table public.publication_jobs
  add constraint publication_jobs_error_message_length check (
    error_message is null or char_length(error_message) <= 300
  );

alter table public.publications
  drop constraint if exists publications_variant_type_check;
alter table public.publications
  add constraint publications_variant_type_check check (
    variant_type in (
      'facebook_page', 'facebook_marketplace', 'facebook_group',
      'instagram_professional', 'portal_inmobiliario', 'yapo',
      'whatsapp_catalog', 'website', 'email', 'generic'
    )
  );
alter table public.publications
  add constraint publications_url_length check (
    publication_url is null or char_length(publication_url) <= 2000
  );

alter table public.properties
  add constraint properties_command_center_text_bounds check (
    char_length(description) between 5 and 10000
    and (source_notes is null or char_length(source_notes) <= 5000)
  );

-- 2. Connected operator-controlled channel accounts.
create table public.channel_accounts (
  id uuid primary key default gen_random_uuid(),
  provider text not null check (
    provider in ('meta', 'assisted', 'website', 'whatsapp', 'email')
  ),
  account_type text not null check (
    account_type in ('facebook_page', 'instagram_professional')
  ),
  external_account_id text not null check (char_length(external_account_id) <= 160),
  display_name text not null check (char_length(display_name) between 1 and 160),
  connection_status text not null check (
    connection_status in ('fixture', 'connected', 'disconnected', 'requires_action')
  ),
  capabilities jsonb not null default '{}'::jsonb,
  is_demo boolean not null default false,
  connected_at timestamptz,
  last_sync_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_channel_account_external_scope unique (provider, external_account_id)
);

create index channel_accounts_status_idx
  on public.channel_accounts (connection_status, account_type);

create trigger channel_accounts_set_updated_at
  before update on public.channel_accounts
  for each row execute function public.set_updated_at();

alter table public.publication_targets
  add column channel_account_id uuid references public.channel_accounts(id) on delete set null,
  add column geographic_relevance text check (
    geographic_relevance is null or char_length(geographic_relevance) <= 160
  ),
  add column property_tags text[] not null default '{}',
  add column is_demo boolean not null default false;

alter table public.publication_jobs
  add column action_required boolean not null default false,
  add column action_note text check (action_note is null or char_length(action_note) <= 300);

alter table public.publications
  add column channel_account_id uuid references public.channel_accounts(id) on delete set null,
  add column external_publication_id text check (
    external_publication_id is null or char_length(external_publication_id) <= 180
  ),
  add constraint uq_publication_external_scope unique (
    channel_account_id, external_publication_id
  );

-- 3. Engagement history. Nullable metrics mean unavailable, while zero means measured zero.
create table public.engagement_snapshots (
  id uuid primary key default gen_random_uuid(),
  publication_id uuid not null references public.publications(id) on delete cascade,
  captured_at timestamptz not null,
  comments_count integer check (comments_count is null or comments_count >= 0),
  reactions_count integer check (reactions_count is null or reactions_count >= 0),
  views_count integer check (views_count is null or views_count >= 0),
  impressions_count integer check (impressions_count is null or impressions_count >= 0),
  messages_count integer check (messages_count is null or messages_count >= 0),
  source text not null check (char_length(source) <= 40),
  capability_version text not null default 'v1' check (
    char_length(capability_version) <= 40
  ),
  is_demo boolean not null default false,
  created_at timestamptz not null default now(),
  constraint uq_engagement_capture unique (publication_id, captured_at)
);

create index engagement_publication_captured_idx
  on public.engagement_snapshots (publication_id, captured_at desc);

create table public.publication_comments (
  id uuid primary key default gen_random_uuid(),
  publication_id uuid not null references public.publications(id) on delete cascade,
  external_comment_id text not null check (char_length(external_comment_id) <= 180),
  author_external_id text check (
    author_external_id is null or char_length(author_external_id) <= 180
  ),
  author_display_name text check (
    author_display_name is null or char_length(author_display_name) <= 160
  ),
  body text not null check (char_length(body) between 1 and 4000),
  created_external_at timestamptz not null,
  reply_status text not null check (
    reply_status in ('new', 'needs_reply', 'replied', 'ignored')
  ),
  is_demo boolean not null default false,
  created_at timestamptz not null default now(),
  constraint uq_comment_external_scope unique (publication_id, external_comment_id)
);

create index comments_publication_created_idx
  on public.publication_comments (publication_id, created_external_at desc);

-- 4. Conversations and messages. Attribution is nullable and never inferred.
create table public.conversations (
  id uuid primary key default gen_random_uuid(),
  channel_account_id uuid not null references public.channel_accounts(id) on delete cascade,
  external_conversation_id text not null check (
    char_length(external_conversation_id) <= 180
  ),
  channel_type text not null check (
    channel_type in ('messenger', 'instagram_professional', 'website', 'whatsapp', 'email')
  ),
  property_id uuid references public.properties(id) on delete set null,
  publication_id uuid references public.publications(id) on delete set null,
  lead_id uuid references public.leads(id) on delete set null,
  status text not null check (status in ('open', 'needs_reply', 'handled', 'archived')),
  last_message_at timestamptz not null,
  is_demo boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint uq_conversation_external_scope unique (
    channel_account_id, external_conversation_id
  )
);

create index conversations_property_last_message_idx
  on public.conversations (property_id, last_message_at desc);

create trigger conversations_set_updated_at
  before update on public.conversations
  for each row execute function public.set_updated_at();

create table public.messages (
  id uuid primary key default gen_random_uuid(),
  conversation_id uuid not null references public.conversations(id) on delete cascade,
  external_message_id text not null check (char_length(external_message_id) <= 180),
  direction text not null check (direction in ('inbound', 'outbound')),
  sender_external_id text check (
    sender_external_id is null or char_length(sender_external_id) <= 180
  ),
  sender_display_name text check (
    sender_display_name is null or char_length(sender_display_name) <= 160
  ),
  message_type text not null default 'text' check (char_length(message_type) <= 30),
  body text check (body is null or char_length(body) <= 10000),
  sent_at timestamptz not null,
  is_demo boolean not null default false,
  created_at timestamptz not null default now(),
  constraint uq_message_external_scope unique (conversation_id, external_message_id)
);

create index messages_conversation_sent_idx
  on public.messages (conversation_id, sent_at);

-- 5. Preserve the server-only database posture.
alter table public.channel_accounts enable row level security;
alter table public.engagement_snapshots enable row level security;
alter table public.publication_comments enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;

revoke all on table public.channel_accounts from anon, authenticated;
revoke all on table public.engagement_snapshots from anon, authenticated;
revoke all on table public.publication_comments from anon, authenticated;
revoke all on table public.conversations from anon, authenticated;
revoke all on table public.messages from anon, authenticated;
