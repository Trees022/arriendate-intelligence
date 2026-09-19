import type {
  Lead,
  LeadCreate,
  LeadDetail,
  LeadExtractionResult,
  LeadList,
  LeadMatches,
  OperationsWorkspace,
  Property,
  PropertyAutofillResponse,
  PropertyCommandCenter,
  PropertyCreateInput,
  PropertyFilters,
  PropertyList,
  PropertyMedia,
  PropertyUpdateInput,
  PublicationPackage,
  PublicationTarget,
  PublicationTargetCreate,
  CampaignDetail,
} from "./types";

const API_URL = (import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000/api").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    const isFormData = options?.body instanceof FormData;
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        ...options?.headers,
      },
    });
  } catch {
    throw new ApiError("No pudimos conectar con el servidor. Verifica que la API esté activa.", 0);
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as
      | { detail?: string | Array<{ msg?: string }> }
      | null;
    const detail = Array.isArray(body?.detail)
      ? body.detail.map((item) => item.msg).filter(Boolean).join(". ")
      : body?.detail;
    throw new ApiError(detail || "La solicitud no pudo completarse.", response.status);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export function resolveMediaUrl(url: string): string {
  if (/^https?:\/\//.test(url)) return url;
  const apiOrigin = API_URL.replace(/\/api$/, "");
  return `${apiOrigin}${url.startsWith("/") ? "" : "/"}${url}`;
}

export function getProperties(filters: PropertyFilters = {}): Promise<PropertyList> {
  const parameters = new URLSearchParams({ page_size: "50" });
  Object.entries(filters).forEach(([key, value]) => {
    if (value) parameters.set(key, value);
  });
  return request<PropertyList>(`/properties?${parameters.toString()}`);
}

export function getProperty(id: string): Promise<Property> {
  return request<Property>(`/properties/${id}`);
}

export function createProperty(payload: PropertyCreateInput): Promise<Property> {
  return request<Property>("/properties", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function autofillProperty(sourceText: string): Promise<PropertyAutofillResponse> {
  return request<PropertyAutofillResponse>("/properties/autofill", {
    method: "POST",
    body: JSON.stringify({ source_text: sourceText }),
  });
}

export function updateProperty(id: string, payload: PropertyUpdateInput): Promise<Property> {
  return request<Property>(`/properties/${id}`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });
}

export function getPropertyMedia(id: string): Promise<PropertyMedia[]> {
  return request<PropertyMedia[]>(`/properties/${id}/media`);
}

export function uploadPropertyMedia(id: string, file: File): Promise<PropertyMedia> {
  const body = new FormData();
  body.append("file", file);
  return request<PropertyMedia>(`/properties/${id}/media`, { method: "POST", body });
}

export function deletePropertyMedia(propertyId: string, mediaId: string): Promise<void> {
  return request<void>(`/properties/${propertyId}/media/${mediaId}`, { method: "DELETE" });
}

export function reorderPropertyMedia(propertyId: string, mediaIds: string[]): Promise<PropertyMedia[]> {
  return request<PropertyMedia[]>(`/properties/${propertyId}/media/reorder`, {
    method: "PATCH",
    body: JSON.stringify({ media_ids: mediaIds }),
  });
}

export function setPropertyCover(propertyId: string, mediaId: string): Promise<PropertyMedia> {
  return request<PropertyMedia>(`/properties/${propertyId}/media/${mediaId}`, {
    method: "PATCH",
    body: JSON.stringify({ is_cover: true }),
  });
}

export function generatePublicationPackage(propertyId: string): Promise<PublicationPackage> {
  return request<PublicationPackage>(`/properties/${propertyId}/packages`, { method: "POST" });
}

export function approvePublicationPackage(packageId: string): Promise<PublicationPackage> {
  return request<PublicationPackage>(`/packages/${packageId}/approve`, { method: "PATCH" });
}

export function getPublicationTargets(activeOnly = true): Promise<PublicationTarget[]> {
  return request<PublicationTarget[]>(`/publication-targets?active_only=${activeOnly}`);
}

export function createPublicationTarget(payload: PublicationTargetCreate): Promise<PublicationTarget> {
  return request<PublicationTarget>("/publication-targets", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function createCampaign(
  propertyId: string,
  packageId: string,
  targetIds: string[],
): Promise<CampaignDetail> {
  return request<CampaignDetail>("/campaigns", {
    method: "POST",
    body: JSON.stringify({ property_id: propertyId, package_id: packageId, target_ids: targetIds }),
  });
}

export function getPropertyCommandCenter(id: string): Promise<PropertyCommandCenter> {
  return request<PropertyCommandCenter>(`/properties/${id}/command-center`);
}

export async function getOperationsWorkspace(): Promise<OperationsWorkspace> {
  const propertyList = await getProperties();
  const centers = await Promise.all(propertyList.items.map((property) => getPropertyCommandCenter(property.id)));
  return {
    properties: propertyList.items,
    centers,
    demo_mode: centers.some((center) => center.demo_mode),
  };
}

export function markPublicationComplete(
  jobId: string,
  publicationUrl: string | null,
): Promise<unknown> {
  return request(`/publication-jobs/${jobId}/publish`, {
    method: "POST",
    body: JSON.stringify({ publication_url: publicationUrl || null }),
  });
}

export function markPublicationRequiresAction(jobId: string, note: string): Promise<unknown> {
  return request(`/publication-jobs/${jobId}/requires-action`, {
    method: "POST",
    body: JSON.stringify({ note }),
  });
}

export function createLead(payload: LeadCreate, idempotencyKey: string): Promise<Lead> {
  return request<Lead>("/leads", {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: JSON.stringify(payload),
  });
}

export function getLeads(): Promise<LeadList> {
  return request<LeadList>("/leads?page_size=100");
}

export function getLead(id: string): Promise<LeadDetail> {
  return request<LeadDetail>(`/leads/${id}`);
}

export function extractLead(id: string): Promise<LeadExtractionResult> {
  return request<LeadExtractionResult>(`/leads/${id}/extract`, { method: "POST" });
}

export function getLeadMatches(id: string): Promise<LeadMatches> {
  return request<LeadMatches>(`/leads/${id}/matches`);
}

export function generateLeadMatches(id: string, topK = 3): Promise<LeadMatches> {
  return request<LeadMatches>(`/leads/${id}/matches?top_k=${topK}`, { method: "POST" });
}
