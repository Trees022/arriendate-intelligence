import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { extractLead, generateLeadMatches, getLead, getLeadMatches } from "../../lib/api";
import type { AIRun, LeadDetail, LeadMatches, LeadRequirements, Property } from "../../lib/types";
import { LeadDetailPage } from "./LeadDetailPage";

vi.mock("../../lib/api", () => ({
  getLead: vi.fn(),
  extractLead: vi.fn(),
  getLeadMatches: vi.fn(),
  generateLeadMatches: vi.fn(),
}));

const mockedGetLead = vi.mocked(getLead);
const mockedExtractLead = vi.mocked(extractLead);
const mockedGetLeadMatches = vi.mocked(getLeadMatches);
const mockedGenerateLeadMatches = vi.mocked(generateLeadMatches);

const requirements: LeadRequirements = {
  id: "30000000-0000-4000-8000-000000000001",
  operation_type: "rent",
  property_types: ["apartment"],
  locations: ["Providencia"],
  max_budget: 850_000,
  currency: "CLP",
  min_bedrooms: 2,
  min_bathrooms: 1,
  parking_required: true,
  pets_required: null,
  furnished_preference: false,
  soft_preferences: ["cerca del metro"],
  missing_information: ["pets"],
  extraction_confidence: 0.91,
  extraction_model: "fixture-model",
  prompt_version: "lead-extraction-v1.0.0",
  created_at: "2026-08-09T20:00:00Z",
  updated_at: "2026-08-09T20:00:00Z",
};

const successfulRun: AIRun = {
  id: "40000000-0000-4000-8000-000000000001",
  run_type: "lead_extraction",
  provider: "fixture",
  model: "fixture-model",
  prompt_version: "lead-extraction-v1.0.0",
  provider_request_id: "fixture-response-1",
  latency_ms: 18,
  input_tokens: 42,
  output_tokens: 31,
  estimated_cost: 0.00012,
  validation_passed: true,
  status: "succeeded",
  error_code: null,
  error_message: null,
  created_at: "2026-08-09T20:00:00Z",
};

const baseLead: LeadDetail = {
  id: "20000000-0000-4000-8000-000000000001",
  name: "Camila",
  email: null,
  phone: null,
  original_request: "Busco departamento de dos dormitorios en Providencia hasta $850.000.",
  status: "new",
  created_at: "2026-08-09T20:00:00Z",
  updated_at: "2026-08-09T20:00:00Z",
  requirements: null,
  ai_runs: [],
};

const matchedProperty: Property = {
  id: "10000000-0000-4000-8000-000000000001",
  title: "Departamento Los Castaños",
  description: "Departamento luminoso con segundo dormitorio apto para escritorio.",
  operation_type: "rent",
  property_type: "apartment",
  city: "Viña del Mar",
  sector: "Los Castaños",
  monthly_price: 670_000,
  sale_price: null,
  currency: "CLP",
  bedrooms: 2,
  bathrooms: 2,
  parking_spaces: 1,
  pet_policy: "allowed",
  furnished: false,
  square_meters: 68,
  amenities: ["balcón"],
  availability_status: "available",
  source_text: "Fuente sintética.",
  created_at: "2026-08-09T20:00:00Z",
  updated_at: "2026-08-09T20:00:00Z",
};

const notRunMatches: LeadMatches = {
  status: "not_run",
  run_id: null,
  algorithm_version: null,
  embedding_provider: null,
  embedding_model: null,
  requested_top_k: null,
  total_properties: 0,
  candidate_count: 0,
  result_count: 0,
  latency_ms: null,
  embedding_latency_ms: null,
  exclusion_summary: [],
  items: [],
  created_at: null,
};

const successfulMatches: LeadMatches = {
  ...notRunMatches,
  status: "succeeded",
  run_id: "50000000-0000-4000-8000-000000000001",
  algorithm_version: "hard-semantic-v1",
  embedding_provider: "fixture",
  embedding_model: "fixture-embedding-v1",
  requested_top_k: 3,
  total_properties: 18,
  candidate_count: 2,
  result_count: 1,
  latency_ms: 12,
  embedding_latency_ms: 3,
  items: [{
    rank: 1,
    semantic_score: 0.91234,
    hard_constraint_matches: [
      { constraint: "max_budget", expected: 850_000, actual: 670_000, passed: true },
      { constraint: "min_bedrooms", expected: 2, actual: 2, passed: true },
    ],
    soft_match_reasons: [{
      preference: "luminoso",
      property_fact: "Departamento luminoso con segundo dormitorio apto para escritorio.",
    }],
    property: matchedProperty,
  }],
  created_at: "2026-08-09T20:00:00Z",
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/leads/${baseLead.id}`]}>
        <Routes>
          <Route path="/leads/:id" element={<LeadDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("LeadDetailPage", () => {
  beforeEach(() => {
    mockedGetLead.mockReset();
    mockedExtractLead.mockReset();
    mockedGetLeadMatches.mockReset();
    mockedGenerateLeadMatches.mockReset();
    mockedGetLead.mockResolvedValue(baseLead);
    mockedGetLeadMatches.mockResolvedValue(notRunMatches);
  });

  it("extracts and renders only server-validated requirements with run telemetry", async () => {
    const user = userEvent.setup();
    mockedExtractLead.mockResolvedValue({
      lead_status: "needs_information",
      requirements,
      ai_run: successfulRun,
    });
    renderPage();

    await user.click(await screen.findByRole("button", { name: "Extraer requisitos con IA" }));

    expect(mockedExtractLead).toHaveBeenCalledWith(baseLead.id);
    expect(await screen.findByRole("heading", { name: "Requisitos estructurados" })).toBeInTheDocument();
    expect(screen.getByText("CLP 850.000")).toBeInTheDocument();
    expect(screen.getAllByText("Mascotas")).toHaveLength(2);

    await user.click(screen.getByText("Ejecuciones de IA"));
    expect(screen.getByText("fixture-model")).toBeInTheDocument();
    expect(screen.getByText("lead-extraction-v1.0.0")).toBeInTheDocument();
    expect(screen.getByText("Validada")).toBeInTheDocument();
  });

  it("shows a safe failure and refreshes the observable failed run", async () => {
    const user = userEvent.setup();
    const failedRun: AIRun = {
      ...successfulRun,
      id: "40000000-0000-4000-8000-000000000002",
      provider_request_id: null,
      validation_passed: false,
      status: "failed",
      error_code: "invalid_ai_output",
      error_message: "La respuesta del proveedor no cumple el contrato esperado.",
    };
    mockedGetLead
      .mockResolvedValueOnce(baseLead)
      .mockResolvedValue({ ...baseLead, ai_runs: [failedRun] });
    mockedExtractLead.mockRejectedValue(new Error("La respuesta de IA no superó la validación."));
    renderPage();

    await user.click(await screen.findByRole("button", { name: "Extraer requisitos con IA" }));

    expect(await screen.findByText("La extracción no se aplicó")).toBeInTheDocument();
    await waitFor(() => expect(mockedGetLead).toHaveBeenCalledTimes(2));
    await user.click(screen.getByText("Ejecuciones de IA"));
    expect(screen.getByText("Fallida")).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Requisitos estructurados" })).not.toBeInTheDocument();
  });

  it("generates grounded recommendations and links to the property", async () => {
    const user = userEvent.setup();
    mockedGetLead.mockResolvedValue({ ...baseLead, status: "qualified", requirements });
    mockedGenerateLeadMatches.mockResolvedValue(successfulMatches);
    renderPage();

    await user.click(await screen.findByRole("button", { name: "Generar recomendaciones" }));

    expect(mockedGenerateLeadMatches).toHaveBeenCalledWith(baseLead.id, 3);
    expect(await screen.findByRole("heading", { name: "Propiedades recomendadas" })).toBeInTheDocument();
    expect(screen.getByText("0.912")).toBeInTheDocument();
    expect(screen.getByText(/Departamento luminoso con segundo dormitorio/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Ver propiedad/ })).toHaveAttribute(
      "href",
      `/properties/${matchedProperty.id}`,
    );
  });

  it("explains zero candidates without relaxing hard constraints", async () => {
    mockedGetLead.mockResolvedValue({ ...baseLead, status: "qualified", requirements });
    mockedGetLeadMatches.mockResolvedValue({
      ...successfulMatches,
      candidate_count: 0,
      result_count: 0,
      items: [],
      exclusion_summary: [{ constraint: "max_budget", excluded_count: 18 }],
    });
    renderPage();

    expect(await screen.findByText(/No hay propiedades que cumplan/)).toBeInTheDocument();
    expect(screen.getByText(/No se relajó ningún requisito/)).toBeInTheDocument();
    expect(screen.getByText(/presupuesto máximo: excluyó 18/)).toBeInTheDocument();
  });

  it("labels stable results honestly when no semantic ranking was applied", async () => {
    mockedGetLead.mockResolvedValue({ ...baseLead, status: "qualified", requirements });
    mockedGetLeadMatches.mockResolvedValue({
      ...successfulMatches,
      embedding_provider: "not_required",
      embedding_model: "not_required",
      items: successfulMatches.items.map((item) => ({ ...item, semantic_score: null })),
    });
    renderPage();

    expect(await screen.findByText("Orden estable · sin ranking semántico")).toBeInTheDocument();
    expect(screen.getByText("No aplicado")).toBeInTheDocument();
    expect(screen.getAllByText(/sin ranking semántico/)).toHaveLength(2);
  });

  it("shows a sanitized embedding-provider error", async () => {
    const user = userEvent.setup();
    mockedGetLead.mockResolvedValue({ ...baseLead, status: "qualified", requirements });
    mockedGenerateLeadMatches.mockRejectedValue(
      new Error("El proveedor de embeddings no está configurado"),
    );
    renderPage();

    await user.click(await screen.findByRole("button", { name: "Generar recomendaciones" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "El proveedor de embeddings no está configurado",
    );
  });

  it("removes recommendations derived from requirements that were reprocessed", async () => {
    const user = userEvent.setup();
    const updatedRequirements = { ...requirements, max_budget: 100_000 };
    mockedGetLead.mockResolvedValue({ ...baseLead, status: "qualified", requirements });
    mockedGetLeadMatches
      .mockResolvedValueOnce(successfulMatches)
      .mockResolvedValue(notRunMatches);
    mockedExtractLead.mockResolvedValue({
      lead_status: "qualified",
      requirements: updatedRequirements,
      ai_run: { ...successfulRun, id: "40000000-0000-4000-8000-000000000009" },
    });
    renderPage();

    expect(await screen.findByText("Departamento Los Castaños")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Reprocesar" }));

    expect(await screen.findByText("CLP 100.000")).toBeInTheDocument();
    await waitFor(() => expect(mockedGetLeadMatches).toHaveBeenCalledTimes(2));
    expect(screen.queryByText("Departamento Los Castaños")).not.toBeInTheDocument();
    expect(screen.getByText(/Aún no se ha ejecutado el matching/)).toBeInTheDocument();
  });
});
