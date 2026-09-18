import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getOperationsWorkspace } from "../../lib/api";
import { fixtureWorkspace } from "../../test/operationsFixture";
import { PublicationsPage } from "./PublicationsPage";

vi.mock("../../lib/api", () => ({
  getOperationsWorkspace: vi.fn(),
  markPublicationComplete: vi.fn(),
  markPublicationRequiresAction: vi.fn(),
  resolveMediaUrl: (url: string) => url,
}));

describe("PublicationsPage", () => {
  beforeEach(() => vi.mocked(getOperationsWorkspace).mockResolvedValue(fixtureWorkspace));

  it("expone la cola prioritaria y reutiliza el flujo asistido del servidor", async () => {
    const user = userEvent.setup();
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<QueryClientProvider client={client}><MemoryRouter><PublicationsPage /></MemoryRouter></QueryClientProvider>);

    expect(await screen.findByText("Casa piloto Castro")).toBeInTheDocument();
    await user.click(screen.getByText("Casa piloto Castro"));
    expect(screen.getByText("Kit de publicación preparado")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Copiar título" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Marcar publicada" })).toBeInTheDocument();
  });
});
