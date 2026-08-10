import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { extractLead, getLead } from "../../lib/api";
import type { AIRun, LeadDetail, LeadRequirements } from "../../lib/types";
import { LeadDetailPage } from "./LeadDetailPage";

vi.mock("../../lib/api", () => ({ getLead: vi.fn(), extractLead: vi.fn() }));

const mockedGetLead = vi.mocked(getLead);
const mockedExtractLead = vi.mocked(extractLead);

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
    mockedGetLead.mockResolvedValue(baseLead);
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
});
