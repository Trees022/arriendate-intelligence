import { describe, expect, it } from "vitest";
import type { PropertyAutofillDraft } from "../../lib/types";
import {
  formatChileanInteger,
  formatSurfaceInput,
  initialPropertyForm,
  mergeAutofillDraft,
  normalizeChileanInteger,
  normalizeSurfaceInput,
  sanitizeFormForPropertyType,
} from "./propertyWizard";

const emptyDraft: PropertyAutofillDraft = {
  operation_type: null,
  property_type: null,
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
};

describe("propertyWizard helpers", () => {
  it("normaliza y muestra precios chilenos sin enviar separadores", () => {
    expect(normalizeChileanInteger("$ 7.000.000 ")).toBe("7000000");
    expect(formatChileanInteger("7000000")).toBe("7.000.000");
    expect(normalizeSurfaceInput("5.000 m²")).toBe("5000");
    expect(formatSurfaceInput("85.5")).toBe("85,5");
  });

  it("limpia los campos que no aplican a un terreno", () => {
    const land = sanitizeFormForPropertyType(
      {
        ...initialPropertyForm,
        bedrooms: "3",
        bathrooms: "2",
        built_area_m2: "120",
        land_area_m2: "5000",
        pet_policy: "allowed",
        furnished: "yes",
      },
      "land",
    );

    expect(land.bedrooms).toBe("");
    expect(land.bathrooms).toBe("");
    expect(land.built_area_m2).toBe("");
    expect(land.land_area_m2).toBe("5000");
    expect(land.pet_policy).toBe("unknown");
  });

  it("no reemplaza una edición manual sin confirmación", () => {
    const result = mergeAutofillDraft(
      { ...initialPropertyForm, title: "Casa que confirmó el corredor" },
      { ...emptyDraft, property_type: "house", title: "Casa sugerida por IA", city: "Castro" },
      new Set(["title"]),
    );

    expect(result.form.title).toBe("Casa que confirmó el corredor");
    expect(result.form.city).toBe("Castro");
    expect(result.conflicts).toEqual([
      expect.objectContaining({ field: "title", suggested: "Casa sugerida por IA" }),
    ]);
  });

  it("conserva vacíos los hechos que la IA no conoce", () => {
    const result = mergeAutofillDraft(
      initialPropertyForm,
      { ...emptyDraft, property_type: "apartment", city: "Castro" },
      new Set(),
    );

    expect(result.form.city).toBe("Castro");
    expect(result.form.title).toBe("");
    expect(result.form.price).toBe("");
    expect(result.form.land_area_m2).toBe("");
  });
});
