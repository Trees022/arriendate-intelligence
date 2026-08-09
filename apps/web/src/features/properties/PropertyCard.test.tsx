import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";
import type { Property } from "../../lib/types";
import { PropertyCard } from "./PropertyCard";

const incompleteProperty: Property = {
  id: "10000000-0000-4000-8000-000000000017",
  title: "Departamento Valencia",
  description: "Registro sintético incompleto.",
  operation_type: "rent",
  property_type: "apartment",
  city: "Quilpué",
  sector: "Valencia",
  monthly_price: 430000,
  sale_price: null,
  currency: "CLP",
  bedrooms: null,
  bathrooms: 1,
  parking_spaces: null,
  pet_policy: "allowed",
  furnished: null,
  square_meters: null,
  amenities: [],
  availability_status: "available",
  source_text: "Registro sintético incompleto.",
  created_at: "2026-08-09T20:00:00Z",
  updated_at: "2026-08-09T20:00:00Z",
};

describe("PropertyCard", () => {
  it("renders unknown structured values instead of inventing them", () => {
    render(
      <MemoryRouter>
        <PropertyCard property={incompleteProperty} />
      </MemoryRouter>,
    );

    expect(screen.getByText("dorm.: por confirmar")).toBeInTheDocument();
    expect(screen.getByText("estac.: por confirmar")).toBeInTheDocument();
    expect(screen.getByRole("link")).toHaveAttribute("href", `/properties/${incompleteProperty.id}`);
  });
});
