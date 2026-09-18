import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { describe, expect, it } from "vitest";
import { AppShell } from "./AppShell";

describe("AppShell", () => {
  it("prioriza la operación de propiedades y mantiene leads como sección secundaria", () => {
    render(
      <MemoryRouter initialEntries={["/dashboard"]}>
        <Routes><Route element={<AppShell />}><Route path="dashboard" element={<h1>Inicio</h1>} /></Route></Routes>
      </MemoryRouter>,
    );

    const navigation = screen.getByRole("navigation", { name: "Navegación principal" });
    expect(navigation).toHaveTextContent("Propiedades");
    expect(navigation).toHaveTextContent("Publicaciones");
    expect(navigation).toHaveTextContent("Inbox");
    expect(navigation).toHaveTextContent("Leads");
    expect(screen.queryByRole("link", { name: "Nuevo lead" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "+ Nueva propiedad" })).toHaveAttribute("href", "/properties/new");
  });
});
