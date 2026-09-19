import type {
  OperationType,
  PetPolicy,
  PropertyAutofillDraft,
  PropertyCreateInput,
  WizardPropertyType,
} from "../../lib/types";

export interface PropertyFormState {
  operation_type: OperationType;
  property_type: WizardPropertyType;
  title: string;
  reference_code: string;
  description: string;
  price: string;
  currency: "CLP" | "UF" | "USD";
  city: string;
  sector: string;
  address_text: string;
  bedrooms: string;
  bathrooms: string;
  parking_spaces: string;
  built_area_m2: string;
  land_area_m2: string;
  amenities: string;
  source_notes: string;
  pet_policy: PetPolicy;
  furnished: "yes" | "no" | "unknown";
}

export type PropertyFormField = keyof PropertyFormState;

export interface AutofillConflict {
  field: PropertyFormField;
  current: string;
  suggested: string;
}

export const initialPropertyForm: PropertyFormState = {
  operation_type: "rent",
  property_type: "house",
  title: "",
  reference_code: "",
  description: "",
  price: "",
  currency: "CLP",
  city: "",
  sector: "",
  address_text: "",
  bedrooms: "",
  bathrooms: "",
  parking_spaces: "",
  built_area_m2: "",
  land_area_m2: "",
  amenities: "",
  source_notes: "",
  pet_policy: "unknown",
  furnished: "unknown",
};

export const propertyTypeOptions: Array<{ value: WizardPropertyType; label: string }> = [
  { value: "house", label: "Casa" },
  { value: "apartment", label: "Departamento" },
  { value: "land", label: "Terreno o parcela" },
  { value: "commercial", label: "Local comercial" },
  { value: "office", label: "Oficina" },
  { value: "warehouse", label: "Bodega o galpón" },
];

export const propertyFieldLabels: Partial<Record<PropertyFormField | "price", string>> = {
  operation_type: "Operación",
  property_type: "Tipo de propiedad",
  title: "Título",
  description: "Descripción",
  price: "Precio",
  currency: "Moneda",
  city: "Comuna o ciudad",
  sector: "Sector",
  address_text: "Dirección",
  bedrooms: "Dormitorios",
  bathrooms: "Baños",
  parking_spaces: "Estacionamientos",
  built_area_m2: "Superficie construida",
  land_area_m2: "Superficie de terreno",
  pet_policy: "Mascotas",
  furnished: "Amoblado",
  amenities: "Características",
};

const alwaysRelevant = new Set<PropertyFormField>([
  "operation_type",
  "property_type",
  "title",
  "reference_code",
  "description",
  "price",
  "currency",
  "city",
  "sector",
  "address_text",
  "amenities",
  "source_notes",
]);

const fieldsByType: Record<WizardPropertyType, PropertyFormField[]> = {
  house: [
    "bedrooms",
    "bathrooms",
    "parking_spaces",
    "built_area_m2",
    "land_area_m2",
    "pet_policy",
    "furnished",
  ],
  apartment: [
    "bedrooms",
    "bathrooms",
    "parking_spaces",
    "built_area_m2",
    "pet_policy",
    "furnished",
  ],
  land: ["land_area_m2"],
  commercial: ["parking_spaces", "built_area_m2"],
  office: ["parking_spaces", "built_area_m2"],
  warehouse: ["parking_spaces", "built_area_m2", "land_area_m2"],
};

export function relevantFields(propertyType: WizardPropertyType): Set<PropertyFormField> {
  return new Set([...alwaysRelevant, ...fieldsByType[propertyType]]);
}

export function sanitizeFormForPropertyType(
  form: PropertyFormState,
  propertyType: WizardPropertyType,
): PropertyFormState {
  const relevant = relevantFields(propertyType);
  const next = { ...form, property_type: propertyType };
  const emptyValues: Partial<PropertyFormState> = {
    bedrooms: "",
    bathrooms: "",
    parking_spaces: "",
    built_area_m2: "",
    land_area_m2: "",
    pet_policy: "unknown",
    furnished: "unknown",
  };
  for (const [field, emptyValue] of Object.entries(emptyValues) as Array<
    [PropertyFormField, PropertyFormState[PropertyFormField]]
  >) {
    if (!relevant.has(field)) Object.assign(next, { [field]: emptyValue });
  }
  return next;
}

export function normalizeChileanInteger(rawValue: string): string {
  return rawValue.replace(/[^0-9]/g, "").replace(/^0+(?=\d)/, "");
}

export function formatChileanInteger(canonicalValue: string): string {
  const normalized = normalizeChileanInteger(canonicalValue);
  if (!normalized) return "";
  return new Intl.NumberFormat("es-CL", { maximumFractionDigits: 0 }).format(
    Number(normalized),
  );
}

export function normalizeSurfaceInput(rawValue: string): string {
  const compact = rawValue.replace(/\s/g, "").replace(/[^0-9.,]/g, "");
  if (!compact) return "";
  if (compact.includes(",")) {
    const [integer = "", decimal = ""] = compact.split(",", 2);
    const whole = integer.replace(/[.]/g, "").replace(/^0+(?=\d)/, "");
    const fraction = decimal.replace(/[^0-9]/g, "").slice(0, 2);
    return fraction ? `${whole || "0"}.${fraction}` : whole;
  }
  if (/^\d{1,3}(\.\d{3})+$/.test(compact)) return compact.replace(/[.]/g, "");
  const parts = compact.split(".");
  if (parts.length === 2 && (parts[1]?.length ?? 0) <= 2) {
    return `${parts[0]?.replace(/^0+(?=\d)/, "") || "0"}.${parts[1] ?? ""}`;
  }
  return compact.replace(/[.]/g, "").replace(/^0+(?=\d)/, "");
}

export function formatSurfaceInput(canonicalValue: string): string {
  if (!canonicalValue) return "";
  const [integer = "", decimal] = canonicalValue.split(".", 2);
  const formattedInteger = formatChileanInteger(integer);
  return decimal === undefined ? formattedInteger : `${formattedInteger},${decimal}`;
}

function optionalNumber(value: string): number | null {
  return value.trim() ? Number(value) : null;
}

export function propertyPayload(form: PropertyFormState): PropertyCreateInput {
  const sanitized = sanitizeFormForPropertyType(form, form.property_type);
  const price = Number(sanitized.price);
  return {
    title: sanitized.title.trim(),
    description: sanitized.description.trim(),
    operation_type: sanitized.operation_type,
    property_type: sanitized.property_type,
    city: sanitized.city.trim(),
    sector: sanitized.sector.trim() || null,
    monthly_price: sanitized.operation_type === "rent" ? price : null,
    sale_price: sanitized.operation_type === "buy" ? price : null,
    currency: sanitized.currency,
    bedrooms: optionalNumber(sanitized.bedrooms),
    bathrooms: optionalNumber(sanitized.bathrooms),
    parking_spaces: optionalNumber(sanitized.parking_spaces),
    pet_policy: sanitized.pet_policy,
    furnished:
      sanitized.furnished === "unknown" ? null : sanitized.furnished === "yes",
    square_meters: optionalNumber(sanitized.built_area_m2),
    reference_code: sanitized.reference_code.trim() || null,
    source_notes: sanitized.source_notes.trim() || null,
    address_text: sanitized.address_text.trim() || null,
    built_area_m2: optionalNumber(sanitized.built_area_m2),
    land_area_m2: optionalNumber(sanitized.land_area_m2),
    commercial_status: "draft",
    amenities: sanitized.amenities
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
  };
}

function draftValues(draft: PropertyAutofillDraft): Partial<PropertyFormState> {
  return {
    operation_type: draft.operation_type ?? undefined,
    property_type: draft.property_type ?? undefined,
    title: draft.title ?? undefined,
    description: draft.description ?? undefined,
    price: draft.price === null ? undefined : String(draft.price),
    currency: draft.currency ?? undefined,
    city: draft.city ?? undefined,
    sector: draft.sector ?? undefined,
    address_text: draft.address_text ?? undefined,
    bedrooms: draft.bedrooms === null ? undefined : String(draft.bedrooms),
    bathrooms: draft.bathrooms === null ? undefined : String(draft.bathrooms),
    parking_spaces:
      draft.parking_spaces === null ? undefined : String(draft.parking_spaces),
    built_area_m2:
      draft.built_area_m2 === null ? undefined : String(draft.built_area_m2),
    land_area_m2: draft.land_area_m2 === null ? undefined : String(draft.land_area_m2),
    pet_policy: draft.pet_policy ?? undefined,
    furnished:
      draft.furnished === null ? undefined : draft.furnished ? "yes" : "no",
    amenities: draft.amenities.length ? draft.amenities.join(", ") : undefined,
  };
}

export function mergeAutofillDraft(
  form: PropertyFormState,
  draft: PropertyAutofillDraft,
  manuallyEdited: ReadonlySet<PropertyFormField>,
): { form: PropertyFormState; appliedFields: PropertyFormField[]; conflicts: AutofillConflict[] } {
  const values = draftValues(draft);
  const typeCanChange =
    values.property_type && !manuallyEdited.has("property_type");
  const nextType = typeCanChange ? values.property_type! : form.property_type;
  const next = sanitizeFormForPropertyType(form, nextType);
  const relevant = relevantFields(nextType);
  const appliedFields: PropertyFormField[] = [];
  const conflicts: AutofillConflict[] = [];

  for (const [field, rawSuggestion] of Object.entries(values) as Array<
    [PropertyFormField, PropertyFormState[PropertyFormField] | undefined]
  >) {
    if (rawSuggestion === undefined || !relevant.has(field)) continue;
    const suggested = String(rawSuggestion);
    const current = String(form[field]);
    if (manuallyEdited.has(field) && current !== suggested) {
      conflicts.push({ field, current, suggested });
      continue;
    }
    Object.assign(next, { [field]: rawSuggestion });
    appliedFields.push(field);
  }

  return { form: next, appliedFields, conflicts };
}
