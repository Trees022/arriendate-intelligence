export type LeadStatus =
  | "new"
  | "qualified"
  | "needs_information"
  | "matched"
  | "contacted"
  | "closed_won"
  | "closed_lost";

export interface LeadCreate {
  name?: string | null;
  email?: string | null;
  phone?: string | null;
  original_request: string;
}

export interface Lead {
  id: string;
  name: string | null;
  email: string | null;
  phone: string | null;
  original_request: string;
  status: LeadStatus;
  created_at: string;
  updated_at: string;
}

export type RequestedOperation = "rent" | "buy" | "unknown";
export type RequestedPropertyType =
  | "apartment"
  | "house"
  | "studio"
  | "loft"
  | "townhouse"
  | "land"
  | "commercial"
  | "office";
export type RequestedCurrency = "CLP" | "UF" | "USD";
export type MissingInformation =
  | "operation_type"
  | "property_type"
  | "location"
  | "budget"
  | "currency"
  | "bedrooms"
  | "bathrooms"
  | "parking"
  | "pets"
  | "furnished"
  | "contradictory_requirements"
  | "unverifiable_preference";

export interface LeadRequirements {
  id: string;
  operation_type: RequestedOperation;
  property_types: RequestedPropertyType[];
  locations: string[];
  max_budget: number | null;
  currency: RequestedCurrency | null;
  min_bedrooms: number | null;
  min_bathrooms: number | null;
  parking_required: boolean | null;
  pets_required: boolean | null;
  furnished_preference: boolean | null;
  soft_preferences: string[];
  missing_information: MissingInformation[];
  extraction_confidence: number;
  extraction_model: string;
  prompt_version: string;
  created_at: string;
  updated_at: string;
}

export interface AIRun {
  id: string;
  run_type: string;
  provider: string;
  model: string;
  prompt_version: string | null;
  provider_request_id: string | null;
  latency_ms: number;
  input_tokens: number | null;
  output_tokens: number | null;
  estimated_cost: number | null;
  validation_passed: boolean;
  status: "running" | "succeeded" | "failed";
  error_code: string | null;
  error_message: string | null;
  created_at: string;
}

export interface LeadDetail extends Lead {
  requirements: LeadRequirements | null;
  ai_runs: AIRun[];
}

export interface LeadExtractionResult {
  lead_status: LeadStatus;
  requirements: LeadRequirements;
  ai_run: AIRun;
}

export type OperationType = "rent" | "buy";
export type AvailabilityStatus = "available" | "reserved" | "unavailable";
export type PetPolicy = "allowed" | "not_allowed" | "unknown";
export type CommercialStatus = "draft" | "active" | "reserved" | "closed" | "archived";

export interface Property {
  id: string;
  title: string;
  description: string;
  operation_type: OperationType;
  property_type: string;
  city: string;
  sector: string | null;
  monthly_price: number | null;
  sale_price: number | null;
  currency: string;
  bedrooms: number | null;
  bathrooms: number | null;
  parking_spaces: number | null;
  pet_policy: PetPolicy;
  furnished: boolean | null;
  square_meters: number | null;
  reference_code?: string | null;
  source_notes?: string | null;
  address_text?: string | null;
  built_area_m2?: number | null;
  land_area_m2?: number | null;
  commercial_status?: CommercialStatus;
  amenities: string[];
  availability_status: AvailabilityStatus;
  source_text: string;
  created_at: string;
  updated_at: string;
}

export interface PropertyList {
  items: Property[];
  total: number;
  page: number;
  page_size: number;
}

export interface PropertyFilters {
  operation_type?: OperationType;
  city?: string;
  availability?: AvailabilityStatus;
}

export interface ConstraintCheck {
  constraint: string;
  expected: unknown;
  actual: unknown;
  passed: boolean;
}

export interface SoftMatchReason {
  preference: string;
  property_fact: string;
}

export interface PropertyMatch {
  rank: number;
  semantic_score: number | null;
  hard_constraint_matches: ConstraintCheck[];
  soft_match_reasons: SoftMatchReason[];
  property: Property;
}

export interface LeadMatches {
  status: "not_run" | "succeeded";
  run_id: string | null;
  algorithm_version: string | null;
  embedding_provider: string | null;
  embedding_model: string | null;
  requested_top_k: number | null;
  total_properties: number;
  candidate_count: number;
  result_count: number;
  latency_ms: number | null;
  embedding_latency_ms: number | null;
  exclusion_summary: Array<{ constraint: string; excluded_count: number }>;
  items: PropertyMatch[];
  created_at: string | null;
}

export type ChannelType =
  | "facebook_page"
  | "facebook_marketplace"
  | "facebook_group"
  | "instagram_professional"
  | "portal_inmobiliario"
  | "yapo"
  | "whatsapp_catalog"
  | "website"
  | "email"
  | "generic";
export type ExecutionMode = "api" | "local_agent" | "assisted" | "manual";
export type CapabilityAvailability =
  | "available"
  | "unavailable"
  | "requires_permission"
  | "requires_connection"
  | "assisted_only";

export interface CapabilityStatus {
  capability: string;
  availability: CapabilityAvailability;
  reason: string | null;
}

export interface ChannelAccount {
  id: string;
  provider: string;
  account_type: "facebook_page" | "instagram_professional";
  external_account_id: string;
  display_name: string;
  connection_status: "fixture" | "connected" | "disconnected" | "requires_action";
  capabilities: Record<string, string>;
  is_demo: boolean;
  connected_at: string | null;
  last_sync_at: string | null;
}

export interface PublicationTarget {
  id: string;
  name: string;
  channel_type: ChannelType;
  execution_mode: ExecutionMode;
  channel_account_id: string | null;
  destination_url: string | null;
  geographic_relevance: string | null;
  property_tags: string[];
  active: boolean;
  minimum_repost_interval_hours: number;
  notes: string | null;
  is_demo: boolean;
}

export interface PublicationJob {
  id: string;
  campaign_id: string;
  property_id: string;
  target_id: string;
  package_id: string;
  variant_type: ChannelType;
  execution_mode: ExecutionMode;
  status: string;
  scheduled_at: string;
  next_eligible_at: string | null;
  attempt_count: number;
  error_code: string | null;
  error_message: string | null;
  action_required: boolean;
  action_note: string | null;
}

export interface Publication {
  id: string;
  job_id: string | null;
  property_id: string;
  campaign_id: string;
  target_id: string;
  package_id: string;
  channel_account_id: string | null;
  variant_type: ChannelType;
  external_publication_id: string | null;
  published_at: string;
  publication_url: string | null;
  execution_mode: ExecutionMode;
}

export interface PublicationVariant {
  id: string;
  package_id: string;
  channel_type: ChannelType;
  headline: string;
  body: string;
  short_body: string | null;
  highlights: string[];
  cta: string;
  suggested_media_ids: string[];
  warnings: string[];
}

export interface PropertyMedia {
  id: string;
  original_filename: string;
  position: number;
  is_cover: boolean;
  url: string;
}

export interface DistributionItem {
  target: PublicationTarget;
  job: PublicationJob | null;
  latest_publication: Publication | null;
  package_variant: PublicationVariant | null;
  prepared_media: PropertyMedia[];
  status: string;
  last_publication_at: string | null;
  next_eligible_at: string | null;
  publication_url: string | null;
  action_required: boolean;
  capabilities: CapabilityStatus[];
}

export interface EngagementSummary {
  comments_count: number | null;
  reactions_count: number | null;
  views_count: number | null;
  impressions_count: number | null;
  messages_count: number | null;
  last_captured_at: string | null;
}

export interface EngagementSnapshot {
  id: string;
  publication_id: string;
  captured_at: string;
  comments_count: number | null;
  reactions_count: number | null;
  views_count: number | null;
  impressions_count: number | null;
  messages_count: number | null;
  source: string;
  capability_version: string;
  is_demo: boolean;
}

export interface PublicationComment {
  id: string;
  publication_id: string;
  author_display_name: string | null;
  body: string;
  created_external_at: string;
  reply_status: "new" | "needs_reply" | "replied" | "ignored";
  is_demo: boolean;
}

export interface ConversationMessage {
  id: string;
  direction: "inbound" | "outbound";
  sender_display_name: string | null;
  message_type: string;
  body: string | null;
  sent_at: string;
  is_demo: boolean;
}

export interface Conversation {
  id: string;
  channel_account_id: string;
  channel_type: "messenger" | "instagram_professional" | "website" | "whatsapp" | "email";
  property_id: string | null;
  publication_id: string | null;
  lead_id: string | null;
  status: "open" | "needs_reply" | "handled" | "archived";
  last_message_at: string;
  is_demo: boolean;
  messages: ConversationMessage[];
}

export interface PropertyAction {
  type: string;
  priority: "high" | "medium" | "low";
  title: string;
  description: string;
  related_entity_type: string | null;
  related_entity_id: string | null;
}

export interface CommandCenterCampaign {
  id: string;
  status: "draft" | "active" | "paused" | "completed" | "archived";
  created_at: string;
  publications: Publication[];
  jobs: PublicationJob[];
}

export interface PropertyCommandCenter {
  property: Property;
  demo_mode: boolean;
  channel_accounts: ChannelAccount[];
  distribution: DistributionItem[];
  engagement: EngagementSummary;
  engagement_snapshots: EngagementSnapshot[];
  recent_comments: PublicationComment[];
  related_conversations: Conversation[];
  next_actions: PropertyAction[];
  campaigns: CommandCenterCampaign[];
}
