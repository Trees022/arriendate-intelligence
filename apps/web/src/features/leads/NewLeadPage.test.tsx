import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { createLead } from "../../lib/api";
import { NewLeadPage } from "./NewLeadPage";

vi.mock("../../lib/api", () => ({ createLead: vi.fn() }));

const mockedCreateLead = vi.mocked(createLead);

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { mutations: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={["/leads/new"]}>
        <Routes>
          <Route path="/leads/new" element={<NewLeadPage />} />
          <Route path="/leads/:id" element={<p>Lead guardado correctamente</p>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("NewLeadPage", () => {
  beforeEach(() => mockedCreateLead.mockReset());

  it("shows validation feedback before sending an empty request", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: "Guardar lead" }));

    expect(await screen.findByText("Describe la búsqueda con al menos 10 caracteres")).toBeInTheDocument();
    expect(mockedCreateLead).not.toHaveBeenCalled();
  });

  it("submits the original request and navigates to the persisted lead", async () => {
    const user = userEvent.setup();
    mockedCreateLead.mockResolvedValue({
      id: "20000000-0000-4000-8000-000000000001",
      name: "Camila",
      email: null,
      phone: null,
      original_request: "Busco departamento tranquilo en Viña del Mar.",
      status: "new",
      created_at: "2026-08-09T20:00:00Z",
      updated_at: "2026-08-09T20:00:00Z",
    });
    renderPage();

    await user.type(screen.getByPlaceholderText("Ej. Camila y Tomás"), "Camila");
    await user.type(
      screen.getByPlaceholderText(/Somos una pareja joven/),
      "Busco departamento tranquilo en Viña del Mar.",
    );
    await user.click(screen.getByRole("button", { name: "Guardar lead" }));

    await waitFor(() => expect(mockedCreateLead).toHaveBeenCalledOnce());
    expect(mockedCreateLead.mock.calls[0]?.[0]).toEqual({
      name: "Camila",
      email: null,
      phone: null,
      original_request: "Busco departamento tranquilo en Viña del Mar.",
    });
    expect(await screen.findByText("Lead guardado correctamente")).toBeInTheDocument();
  });
});
