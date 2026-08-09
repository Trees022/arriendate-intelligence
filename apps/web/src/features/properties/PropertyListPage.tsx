import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { StatePanel } from "../../components/StatePanel";
import { getProperties } from "../../lib/api";
import type { AvailabilityStatus, OperationType, PropertyFilters } from "../../lib/types";
import { PropertyCard } from "./PropertyCard";

const cities = ["Viña del Mar", "Valparaíso", "Concón", "Quilpué"];

export function PropertyListPage() {
  const [operation, setOperation] = useState<OperationType | "">("");
  const [city, setCity] = useState("");
  const [availability, setAvailability] = useState<AvailabilityStatus | "">("");
  const filters: PropertyFilters = {
    ...(operation && { operation_type: operation }),
    ...(city && { city }),
    ...(availability && { availability }),
  };

  const query = useQuery({
    queryKey: ["properties", filters],
    queryFn: () => getProperties(filters),
  });

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Inventario sintético"
        title="Propiedades con datos visibles, incluso cuando faltan."
        description="18 registros ficticios de la Región de Valparaíso para probar filtros, incertidumbre y futuros matches."
        action={<Link className="button button--secondary" to="/leads/new">Crear lead</Link>}
      />

      <section className="filter-bar" aria-label="Filtros de propiedades">
        <label>
          <span>Operación</span>
          <select value={operation} onChange={(event) => setOperation(event.target.value as OperationType | "")}>
            <option value="">Todas</option>
            <option value="rent">Arriendo</option>
            <option value="buy">Venta</option>
          </select>
        </label>
        <label>
          <span>Ciudad</span>
          <select value={city} onChange={(event) => setCity(event.target.value)}>
            <option value="">Todas</option>
            {cities.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
        <label>
          <span>Disponibilidad</span>
          <select
            value={availability}
            onChange={(event) => setAvailability(event.target.value as AvailabilityStatus | "")}
          >
            <option value="">Todas</option>
            <option value="available">Disponible</option>
            <option value="reserved">Reservada</option>
            <option value="unavailable">No disponible</option>
          </select>
        </label>
        <div className="filter-bar__count" aria-live="polite">
          <strong>{query.data?.total ?? "—"}</strong>
          <span>resultados</span>
        </div>
      </section>

      {query.isPending ? <StatePanel title="Cargando inventario" message="Consultando los registros disponibles…" /> : null}
      {query.isError ? <StatePanel tone="error" title="No pudimos cargar las propiedades" message={query.error.message} /> : null}
      {query.data?.items.length === 0 ? (
        <StatePanel title="Sin resultados" message="No hay propiedades que coincidan con estos filtros." />
      ) : null}
      {query.data?.items.length ? (
        <section className="property-grid" aria-label="Resultados de propiedades">
          {query.data.items.map((property) => <PropertyCard key={property.id} property={property} />)}
        </section>
      ) : null}
    </div>
  );
}
