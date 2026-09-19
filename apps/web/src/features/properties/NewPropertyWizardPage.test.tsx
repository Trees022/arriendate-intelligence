import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import * as api from "../../lib/api";
import type {
  Property,
  PropertyAutofillResponse,
  PropertyMedia,
  PublicationPackage,
  PublicationTarget,
} from "../../lib/types";
import { NewPropertyWizardPage } from "./NewPropertyWizardPage";

vi.mock("../../lib/api", () => ({
  approvePublicationPackage: vi.fn(),
  autofillProperty: vi.fn(),
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
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
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

function autofillResponse(overrides: Partial<PropertyAutofillResponse["draft"]> = {}): PropertyAutofillResponse {
  return {
    draft: {
      operation_type: "rent",
      property_type: "house",
      title: null,
      description: null,
      price: null,
      currency: null,
      city: null,
      sector: null,
      address_text: null,
      bedrooms: null,
      bathrooms: null,
      parking_spaces: null,
      built_area_m2: null,
      land_area_m2: null,
      pet_policy: null,
      furnished: null,
      amenities: [],
      ...overrides,
    },
    filled_fields: [],
    review_fields: [],
    provider: "fixture",
    model: "fixture",
  };
}

describe("NewPropertyWizardPage", () => {
  let media: PropertyMedia[];

  beforeEach(() => {
    media = [];
    vi.mocked(api.autofillProperty).mockReset();
    vi.mocked(api.createProperty).mockReset().mockResolvedValue(property);
    vi.mocked(api.getPropertyMedia).mockReset().mockImplementation(async () => media);
    vi.mocked(api.uploadPropertyMedia).mockReset().mockImplementation(async () => {
      media = [uploadedMedia];
      return uploadedMedia;
    });
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

  it("crea una propiedad y llega al centro de operación en cuatro pasos", async () => {
    const user = userEvent.setup();
    renderWizard();

    await user.type(screen.getByPlaceholderText("Ej. Departamento en Castro centro"), property.title);
    await user.type(screen.getByRole("textbox", { name: "Precio" }), "720000");
    await user.type(screen.getByLabelText("Comuna o ciudad"), "Castro");
    await user.click(screen.getByRole("button", { name: "Guardar y seguir" }));

    expect(await screen.findByRole("heading", { name: "Fotos" })).toBeInTheDocument();
    const file = new File(["imagen"], "fachada.jpg", { type: "image/jpeg" });
    await user.upload(screen.getByLabelText(/Agregar fotos/), file);
    expect(await screen.findByText("fachada.jpg")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Seguir a publicación" }));

    await user.click(screen.getByRole("button", { name: "Generar publicación" }));
    expect(await screen.findByText("Casa en arriendo en Castro")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Aprobar y seguir" }));

    expect(await screen.findByRole("heading", { name: "Destinos" })).toBeInTheDocument();
    await user.click(screen.getByRole("checkbox", { name: /Corredores de Castro/ }));
    await user.click(screen.getByRole("button", { name: "Iniciar campaña" }));

    expect(await screen.findByRole("heading", { name: "Centro abierto" })).toBeInTheDocument();
    expect(api.createCampaign).toHaveBeenCalledWith(property.id, publicationPackage.id, [target.id]);
    await waitFor(() => expect(api.updateProperty).toHaveBeenCalledWith(property.id, { commercial_status: "active" }));
  });

  it("oculta los campos residenciales al elegir terreno", async () => {
    const user = userEvent.setup();
    renderWizard();

    await user.selectOptions(screen.getByLabelText("Tipo de propiedad"), "land");

    expect(screen.queryByLabelText("Dormitorios")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Baños")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Superficie construida")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Superficie de terreno")).toBeInTheDocument();
  });

  it("no muestra superficie de terreno para un departamento", async () => {
    const user = userEvent.setup();
    renderWizard();

    await user.selectOptions(screen.getByLabelText("Tipo de propiedad"), "apartment");

    expect(screen.getByLabelText("Dormitorios")).toBeInTheDocument();
    expect(screen.getByLabelText("Superficie construida")).toBeInTheDocument();
    expect(screen.queryByLabelText("Superficie de terreno")).not.toBeInTheDocument();
  });

  it("conserva una edición manual cuando la sugerencia de IA es distinta", async () => {
    const user = userEvent.setup();
    vi.mocked(api.autofillProperty).mockResolvedValue(autofillResponse({
      title: "Casa sugerida", price: 700000, city: "Castro",
    }));
    renderWizard();

    const title = screen.getByPlaceholderText("Ej. Departamento en Castro centro");
    await user.type(title, "Casa confirmada por corredor");
    await user.type(screen.getByRole("textbox", { name: "Información de la propiedad" }), "Se arrienda una casa en Castro por $700.000 al mes.");
    await user.click(screen.getByRole("button", { name: "Autocompletar con IA" }));

    expect(await screen.findByText(/Ya habías escrito/)).toBeInTheDocument();
    expect(title).toHaveValue("Casa confirmada por corredor");
    expect(screen.getByRole("textbox", { name: "Precio" })).toHaveValue("700.000");
    await user.click(screen.getByRole("button", { name: /Usar “Casa sugerida”/ }));
    expect(title).toHaveValue("Casa sugerida");
  });

  it("deja vacíos los datos que no fueron encontrados", async () => {
    const user = userEvent.setup();
    const response = autofillResponse({
      property_type: "apartment", city: "Castro",
    });
    response.review_fields = ["title", "price"];
    vi.mocked(api.autofillProperty).mockResolvedValue(response);
    renderWizard();

    await user.type(screen.getByRole("textbox", { name: "Información de la propiedad" }), "Se arrienda departamento en Castro. Consultar detalles.");
    await user.click(screen.getByRole("button", { name: "Autocompletar con IA" }));

    expect(await screen.findByText("Revisa o completa")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("Ej. Departamento en Castro centro")).toHaveValue("");
    expect(screen.getByRole("textbox", { name: "Precio" })).toHaveValue("");
    expect(screen.getByLabelText("Comuna o ciudad")).toHaveValue("Castro");
  });

  it("mantiene navegación de cuatro pasos y teclados numéricos útiles en móvil", () => {
    renderWizard();

    const progress = screen.getByRole("list", { name: "Progreso del registro" });
    expect(within(progress).getAllByRole("listitem")).toHaveLength(4);
    expect(screen.getByRole("textbox", { name: "Precio" })).toHaveAttribute("inputmode", "numeric");
  });
});
