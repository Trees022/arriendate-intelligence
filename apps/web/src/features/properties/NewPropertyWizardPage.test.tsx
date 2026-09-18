import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../../lib/api";
import type { Property, PropertyMedia, PublicationPackage, PublicationTarget } from "../../lib/types";
import { NewPropertyWizardPage } from "./NewPropertyWizardPage";

vi.mock("../../lib/api", () => ({
  approvePublicationPackage: vi.fn(),
  createCampaign: vi.fn(),
  createProperty: vi.fn(),
  createPublicationTarget: vi.fn(),
  deletePropertyMedia: vi.fn(),
  generatePublicationPackage: vi.fn(),
  getPropertyMedia: vi.fn(),
  getPublicationTargets: vi.fn(),
  reorderPropertyMedia: vi.fn(),
  resolveMediaUrl: (url: string) => url,
  setPropertyCover: vi.fn(),
  updateProperty: vi.fn(),
  uploadPropertyMedia: vi.fn(),
}));

const property: Property = {
  id: "property-1",
  title: "Casa nueva en Castro",
  description: "Casa luminosa para arriendo familiar.",
  operation_type: "rent",
  property_type: "house",
  city: "Castro",
  sector: "Centro",
  monthly_price: 720000,
  sale_price: null,
  currency: "CLP",
  bedrooms: 3,
  bathrooms: 2,
  parking_spaces: 1,
  pet_policy: "unknown",
  furnished: null,
  square_meters: 90,
  commercial_status: "draft",
  amenities: [],
  availability_status: "available",
  source_text: "Ficha ingresada por operador",
  created_at: "2026-09-18T12:00:00Z",
  updated_at: "2026-09-18T12:00:00Z",
};

const uploadedMedia: PropertyMedia = {
  id: "media-1",
  property_id: property.id,
  storage_key: "property-1/fachada.jpg",
  original_filename: "fachada.jpg",
  media_type: "image",
  mime_type: "image/jpeg",
  size_bytes: 24,
  position: 0,
  is_cover: true,
  url: "/api/media/property-1/fachada.jpg",
  created_at: "2026-09-18T12:01:00Z",
};

const publicationPackage: PublicationPackage = {
  id: "package-1",
  property_id: property.id,
  property_fingerprint: "fingerprint",
  status: "draft",
  variants: [{
    id: "variant-1",
    package_id: "package-1",
    channel_type: "facebook_group",
    headline: "Casa en arriendo en Castro",
    body: "Casa luminosa de tres dormitorios.",
    short_body: "Casa en Castro",
    highlights: ["3 dormitorios", "$720.000 mensuales"],
    cta: "Coordina una visita.",
    suggested_media_ids: [uploadedMedia.id],
    warnings: ["Verificar las reglas del grupo."],
  }],
  created_at: "2026-09-18T12:02:00Z",
  updated_at: "2026-09-18T12:02:00Z",
};

const target: PublicationTarget = {
  id: "target-1",
  name: "Corredores de Castro",
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
};

function renderWizard() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/properties/new"]}>
        <Routes>
          <Route path="/properties/new" element={<NewPropertyWizardPage />} />
          <Route path="/properties/:id/command-center" element={<h1>Centro abierto</h1>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("NewPropertyWizardPage", () => {
  let media: PropertyMedia[];

  beforeEach(() => {
    media = [];
    vi.mocked(api.createProperty).mockReset().mockResolvedValue(property);
    vi.mocked(api.getPropertyMedia).mockReset().mockImplementation(async () => media);
    vi.mocked(api.uploadPropertyMedia).mockReset().mockImplementation(async () => { media = [uploadedMedia]; return uploadedMedia; });
    vi.mocked(api.deletePropertyMedia).mockReset().mockResolvedValue(undefined);
    vi.mocked(api.reorderPropertyMedia).mockReset().mockResolvedValue([uploadedMedia]);
    vi.mocked(api.setPropertyCover).mockReset().mockResolvedValue(uploadedMedia);
    vi.mocked(api.generatePublicationPackage).mockReset().mockResolvedValue(publicationPackage);
    vi.mocked(api.approvePublicationPackage).mockReset().mockResolvedValue({ ...publicationPackage, status: "approved" });
    vi.mocked(api.getPublicationTargets).mockReset().mockResolvedValue([target]);
    vi.mocked(api.updateProperty).mockReset().mockResolvedValue({ ...property, commercial_status: "active" });
    vi.mocked(api.createCampaign).mockReset().mockResolvedValue({
      id: "campaign-1", property_id: property.id, package_id: publicationPackage.id, status: "active",
      targets: [target], jobs: [], publications: [], created_at: "2026-09-18T12:03:00Z", updated_at: "2026-09-18T12:03:00Z",
    });
  });

  it("crea propiedad, carga fotos, aprueba contenido, selecciona distribución y lanza la campaña", async () => {
    const user = userEvent.setup();
    renderWizard();

    await user.type(screen.getByPlaceholderText("Ej. Casa luminosa en Castro centro"), property.title);
    await user.type(screen.getByPlaceholderText("Describe sólo características verificables de la propiedad."), property.description);
    await user.type(screen.getByPlaceholderText("650000"), "720000");
    await user.type(screen.getByPlaceholderText("Castro"), "Castro");
    await user.click(screen.getByRole("button", { name: "Guardar y continuar" }));

    expect(await screen.findByRole("heading", { name: "Fotografías" })).toBeInTheDocument();
    const file = new File(["imagen"], "fachada.jpg", { type: "image/jpeg" });
    await user.upload(screen.getByLabelText(/Seleccionar fotografías/), file);
    expect(await screen.findByText("fachada.jpg")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Continuar con contenido" }));

    await user.click(screen.getByRole("button", { name: "Generar contenido" }));
    expect(await screen.findByText("Casa en arriendo en Castro")).toBeInTheDocument();
    expect(screen.getByText("Verificar las reglas del grupo.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Aprobar contenido y continuar" }));

    expect(await screen.findByRole("heading", { name: "Destinos de publicación" })).toBeInTheDocument();
    await user.click(screen.getByRole("checkbox", { name: /Corredores de Castro/ }));
    await user.click(screen.getByRole("button", { name: "Revisar lanzamiento" }));
    expect(await screen.findByRole("heading", { name: "Todo listo para lanzar" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Activar propiedad y lanzar campaña" }));

    expect(await screen.findByRole("heading", { name: "Centro abierto" })).toBeInTheDocument();
    expect(api.createCampaign).toHaveBeenCalledWith(property.id, publicationPackage.id, [target.id]);
    await waitFor(() => expect(api.updateProperty).toHaveBeenCalledWith(property.id, { commercial_status: "active" }));
  });
});
