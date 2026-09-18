import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getOperationsWorkspace } from "../../lib/api";
import { fixtureWorkspace } from "../../test/operationsFixture";
import { InboxPage } from "./InboxPage";

vi.mock("../../lib/api", () => ({ getOperationsWorkspace: vi.fn() }));

describe("InboxPage", () => {
  beforeEach(() => vi.mocked(getOperationsWorkspace).mockResolvedValue(fixtureWorkspace));

  it("muestra origen, persona, propiedad, estado y detalle sin fingir sincronización real", async () => {
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><MemoryRouter><InboxPage /></MemoryRouter></QueryClientProvider>);

    expect((await screen.findAllByText("Daniela")).length).toBeGreaterThan(0);
    expect(screen.getAllByText("Casa piloto Castro").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Hola, ¿sigue disponible?").length).toBeGreaterThan(0);
    expect(screen.getByText(/todavía no existe sincronización en vivo con Meta/)).toBeInTheDocument();
  });
});
