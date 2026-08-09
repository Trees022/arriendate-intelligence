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
