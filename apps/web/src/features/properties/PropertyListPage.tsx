import { useQuery } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { StatePanel } from "../../components/StatePanel";
import { getOperationsWorkspace } from "../../lib/api";
import type { OperationType, PropertyCommandCenter } from "../../lib/types";
import { PropertyCard } from "./PropertyCard";

type PortfolioView = "all" | "draft" | "ready" | "active" | "paused" | "closed";

const statusOptions: Array<{ value: PortfolioView; label: string }> = [
  { value: "all", label: "Todas" },
  { value: "draft", label: "Borrador" },
  { value: "ready", label: "Listas" },
  { value: "active", label: "Activas" },
  { value: "paused", label: "Pausadas" },
  { value: "closed", label: "Cerradas" },
];

function matchesStatus(center: PropertyCommandCenter, view: PortfolioView) {
  if (view === "all") return true;
  if (view === "ready") return center.distribution.some((item) => ["ready", "ready_to_repost"].includes(item.status));
  if (view === "paused") return center.campaigns.some((campaign) => campaign.status === "paused");
  if (view === "closed") return ["closed", "archived"].includes(center.property.commercial_status ?? "draft");
  return center.property.commercial_status === view;
}

export function PropertyListPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialView = (searchParams.get("status") as PortfolioView | null) ?? "all";
  const [view, setView] = useState<PortfolioView>(statusOptions.some((item) => item.value === initialView) ? initialView : "all");
  const [operation, setOperation] = useState<OperationType | "">("");
  const [city, setCity] = useState("");
  const query = useQuery({ queryKey: ["operations-workspace"], queryFn: getOperationsWorkspace });

  const cities = useMemo(
    () => [...new Set((query.data?.properties ?? []).map((property) => property.city))].sort(),
    [query.data],
  );
  const centers = (query.data?.centers ?? []).filter((center) =>
    matchesStatus(center, view)
    && (!operation || center.property.operation_type === operation)
    && (!city || center.property.city === city),
  );

  const selectView = (nextView: PortfolioView) => {
    setView(nextView);
    setSearchParams(nextView === "all" ? {} : { status: nextView });
  };

  return (
    <div className="page-stack portfolio-page">
      <PageHeader
        eyebrow="Cartera inmobiliaria"
        title="Propiedades"
        description="Gestiona cada inmueble desde su preparación hasta la publicación y el seguimiento comercial."
        action={<Link className="button button--primary" to="/properties/new">+ Nueva propiedad</Link>}
      />

      <section className="portfolio-toolbar" aria-label="Filtros de propiedades">
        <div className="segmented-control" aria-label="Estado operacional">
          {statusOptions.map((option) => (
            <button
              className={view === option.value ? "is-active" : ""}
              type="button"
              key={option.value}
              onClick={() => selectView(option.value)}
            >
              {option.label}
            </button>
          ))}
        </div>
        <div className="portfolio-toolbar__filters">
          <label>
            <span>Operación</span>
            <select value={operation} onChange={(event) => setOperation(event.target.value as OperationType | "")}>
              <option value="">Todas</option><option value="rent">Arriendo</option><option value="buy">Venta</option>
            </select>
          </label>
          <label>
            <span>Ciudad</span>
            <select value={city} onChange={(event) => setCity(event.target.value)}>
              <option value="">Todas</option>{cities.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <div className="filter-bar__count"><strong>{query.isPending ? "—" : centers.length}</strong><span>propiedades</span></div>
        </div>
      </section>

      {query.data?.demo_mode ? <div className="demo-banner"><strong>Demo local</strong><span>Entorno de demostración con datos ficticios.</span></div> : null}
      {query.isPending ? <StatePanel title="Cargando propiedades" message="Preparando la cartera y su estado comercial…" /> : null}
      {query.isError ? <StatePanel tone="error" title="No pudimos cargar las propiedades" message={query.error.message} /> : null}
      {query.data && centers.length === 0 ? <StatePanel title="Sin propiedades" message="No hay propiedades que coincidan con estos filtros." /> : null}
      {centers.length ? (
        <section className="property-grid" aria-label="Cartera de propiedades">
          {centers.map((center) => <PropertyCard key={center.property.id} property={center.property} center={center} />)}
        </section>
      ) : null}
    </div>
  );
}
