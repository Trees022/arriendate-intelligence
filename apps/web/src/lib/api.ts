import type {
  Lead,
  LeadCreate,
  LeadDetail,
  LeadExtractionResult,
  Property,
  PropertyFilters,
  PropertyList,
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
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: {
        "Content-Type": "application/json",
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
  return (await response.json()) as T;
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

export function createLead(payload: LeadCreate, idempotencyKey: string): Promise<Lead> {
  return request<Lead>("/leads", {
    method: "POST",
    headers: { "Idempotency-Key": idempotencyKey },
    body: JSON.stringify(payload),
  });
}

export function getLead(id: string): Promise<LeadDetail> {
  return request<LeadDetail>(`/leads/${id}`);
}

export function extractLead(id: string): Promise<LeadExtractionResult> {
  return request<LeadExtractionResult>(`/leads/${id}/extract`, { method: "POST" });
}
