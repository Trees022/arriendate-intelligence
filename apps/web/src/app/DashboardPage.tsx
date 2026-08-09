import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { StatePanel } from "../components/StatePanel";
import { getProperties } from "../lib/api";

export function DashboardPage() {
  const inventory = useQuery({
    queryKey: ["properties", "dashboard"],
    queryFn: () => getProperties(),
  });

  return (
    <div className="page-stack">
      <PageHeader
        eyebrow="Vista general"
        title="Buenas decisiones empiezan con datos claros."
        description="La primera base operativa ya recibe solicitudes y mantiene un inventario sintético verificable."
        action={<Link className="button button--primary" to="/leads/new">Ingresar lead</Link>}
      />

      <section className="metric-grid" aria-label="Resumen del workspace">
        <article className="metric-card metric-card--accent">
          <span className="metric-card__label">Inventario demo</span>
          <strong>{inventory.data?.total ?? "—"}</strong>
          <small>propiedades sintéticas</small>
        </article>
        <article className="metric-card">
          <span className="metric-card__label">Flujo activo</span>
          <strong>01</strong>
          <small>captura y persistencia</small>
        </article>
        <article className="metric-card">
          <span className="metric-card__label">Automatizaciones</span>
          <strong>0</strong>
          <small>ningún envío autónomo</small>
        </article>
      </section>

      <section className="dashboard-grid">
        <article className="panel panel--dark">
          <p className="eyebrow eyebrow--light">Primer vertical slice</p>
          <h2>Del mensaje original a un registro confiable.</h2>
          <p>
            La solicitud se guarda antes de cualquier futura extracción. Hoy no hay IA simulada ni métricas
            inventadas: los siguientes pasos aparecerán cuando su lógica y trazabilidad estén implementadas.
          </p>
          <ol className="flow-list">
            <li className="is-complete"><span>1</span> Captura del lead</li>
            <li className="is-complete"><span>2</span> Persistencia original</li>
            <li><span>3</span> Extracción estructurada</li>
            <li><span>4</span> Matching híbrido</li>
          </ol>
        </article>

        <article className="panel">
          <div className="panel__heading">
            <div>
              <p className="eyebrow">Estado operativo</p>
              <h2>Base preparada</h2>
            </div>
            <span className="status-badge status-badge--available">Local</span>
          </div>
          <StatePanel
            title="Sin actividad artificial"
            message="El conteo de leads no se presenta hasta contar con su endpoint de listado. Puedes crear y abrir cada lead desde su confirmación."
          />
          <div className="panel__actions">
            <Link className="text-link" to="/properties">Revisar inventario <span>→</span></Link>
          </div>
        </article>
      </section>
    </div>
  );
}
