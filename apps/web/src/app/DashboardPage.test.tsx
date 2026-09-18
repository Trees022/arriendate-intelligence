import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getOperationsWorkspace } from "../lib/api";
import { fixtureWorkspace } from "../test/operationsFixture";
import { DashboardPage } from "./DashboardPage";

vi.mock("../lib/api", () => ({ getOperationsWorkspace: vi.fn() }));

describe("DashboardPage", () => {
  beforeEach(() => vi.mocked(getOperationsWorkspace).mockResolvedValue(fixtureWorkspace));

  it("muestra la cartera, estados operativos y próximas acciones sin mensajes del MVP", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><MemoryRouter><DashboardPage /></MemoryRouter></QueryClientProvider>);

    expect(await screen.findByText("Propiedades activas")).toBeInTheDocument();
    expect(screen.getByText("Publicar en Corredores de Castro")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "+ Nueva propiedad" })).toHaveAttribute("href", "/properties/new");
    expect(screen.queryByText(/requisitos estructurados/i)).not.toBeInTheDocument();
  });
});
