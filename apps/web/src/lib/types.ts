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
