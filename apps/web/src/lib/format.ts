import type { AvailabilityStatus, LeadStatus, PetPolicy, Property } from "./types";

const clp = new Intl.NumberFormat("es-CL", {
  style: "currency",
  currency: "CLP",
  maximumFractionDigits: 0,
});

const dateTime = new Intl.DateTimeFormat("es-CL", {
  dateStyle: "medium",
  timeStyle: "short",
});

export function formatPropertyPrice(property: Property): string {
  const price = property.operation_type === "rent" ? property.monthly_price : property.sale_price;
  if (price === null) return "Precio no informado";
  return `${clp.format(price)}${property.operation_type === "rent" ? " / mes" : ""}`;
}

export function formatDate(value: string): string {
  return dateTime.format(new Date(value));
}

export const leadStatusLabel: Record<LeadStatus, string> = {
  new: "Nuevo",
  qualified: "Calificado",
  needs_information: "Falta información",
  matched: "Con matches",
  contacted: "Contactado",
  closed_won: "Cerrado · ganado",
  closed_lost: "Cerrado · perdido",
};

export const petPolicyLabel: Record<PetPolicy, string> = {
  allowed: "Admite mascotas",
  not_allowed: "No admite mascotas",
  unknown: "Mascotas por confirmar",
};

export const availabilityLabel: Record<AvailabilityStatus, string> = {
  available: "Disponible",
  reserved: "Reservada",
  unavailable: "No disponible",
};

export function knownNumber(value: number | null, suffix: string): string {
  return value === null ? `${suffix}: por confirmar` : `${value} ${suffix}`;
}
