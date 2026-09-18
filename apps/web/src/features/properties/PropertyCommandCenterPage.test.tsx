import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  getPropertyCommandCenter,
  markPublicationComplete,
  markPublicationRequiresAction,
} from "../../lib/api";
import type { PropertyCommandCenter } from "../../lib/types";
import { PropertyCommandCenterPage } from "./PropertyCommandCenterPage";

vi.mock("../../lib/api", () => ({
  getPropertyCommandCenter: vi.fn(),
  markPublicationComplete: vi.fn(),
  markPublicationRequiresAction: vi.fn(),
}));

const propertyId = "10000000-0000-4000-8000-000000000001";
const center = {
  property: {
    id: propertyId,
    title: "Departamento demo",
    description: "Propiedad de prueba",
    operation_type: "rent",
    property_type: "apartment",
    city: "Castro",
    sector: "Centro",
    monthly_price: 650000,
    sale_price: null,
    currency: "CLP",
    bedrooms: 2,
    bathrooms: 1,
    parking_spaces: 1,
    pet_policy: "allowed",
    furnished: false,
    square_meters: 60,
    commercial_status: "active",
    amenities: [],
    availability_status: "available",
    source_text: "Fixture",
    created_at: "2026-09-18T12:00:00Z",
    updated_at: "2026-09-18T12:00:00Z",
  },
  demo_mode: true,
  channel_accounts: [],
  distribution: [
    {
      target: {
        id: "target-1",
        name: "Propiedades Castro",
        channel_type: "facebook_group",
        execution_mode: "assisted",
        channel_account_id: null,
        destination_url: "https://example.invalid/group",
        geographic_relevance: "Castro",
        property_tags: [],
        active: true,
        minimum_repost_interval_hours: 72,
        notes: null,
        is_demo: true,
      },
      job: null,
      latest_publication: null,
      package_variant: null,
      prepared_media: [],
      status: "ready",
      last_publication_at: null,
      next_eligible_at: null,
      publication_url: null,
      action_required: false,
      capabilities: [{ capability: "assisted_publish", availability: "assisted_only", reason: null }],
    },
  ],
  engagement: {
    comments_count: 2,
    reactions_count: 7,
    views_count: null,
    impressions_count: null,
    messages_count: 1,
    last_captured_at: "2026-09-18T12:00:00Z",
  },
  engagement_snapshots: [],
  recent_comments: [],
  related_conversations: [],
  next_actions: [{
    type: "initial_publication",
    priority: "medium",
    title: "Publicar en Propiedades Castro",
    description: "Contenido preparado.",
    related_entity_type: "publication_target",
    related_entity_id: "target-1",
  }],
  campaigns: [],
} as PropertyCommandCenter;

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/properties/${propertyId}/command-center`]}>
        <Routes>
          <Route path="/properties/:id/command-center" element={<PropertyCommandCenterPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("PropertyCommandCenterPage", () => {
  beforeEach(() => {
    vi.mocked(getPropertyCommandCenter).mockReset();
    vi.mocked(markPublicationComplete).mockReset();
    vi.mocked(markPublicationRequiresAction).mockReset();
    vi.mocked(getPropertyCommandCenter).mockResolvedValue(center);
  });

  it("shows property-centric operations and unavailable metrics honestly", async () => {
    renderPage();

    expect(await screen.findByRole("heading", { name: "Departamento demo" })).toBeInTheDocument();
    expect(screen.getByText("Modo demo determinístico")).toBeInTheDocument();
    expect(screen.getByText("Propiedades Castro")).toBeInTheDocument();
    expect(screen.getByText("Facebook Group · Flujo asistido")).toBeInTheDocument();
    expect(screen.getAllByText("No disponible")).toHaveLength(2);
    expect(screen.getByText("Publicar en Propiedades Castro")).toBeInTheDocument();
  });
});

