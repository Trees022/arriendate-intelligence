import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { StatePanel } from "../../components/StatePanel";
import { getLead } from "../../lib/api";
import { formatDate, leadStatusLabel } from "../../lib/format";

export function LeadDetailPage() {
  const { id = "" } = useParams();
  const query = useQuery({
    queryKey: ["lead", id],
    queryFn: () => getLead(id),
    enabled: Boolean(id),
  });

  if (query.isPending) return <StatePanel title="Cargando lead" message="Recuperando el registro persistido…" />;
  if (query.isError) return <StatePanel tone="error" title="No pudimos abrir el lead" message={query.error.message} />;

  const lead = query.data;
  return (
    <div className="page-stack detail-page">
      <Link className="back-link" to="/leads/new">← Ingresar otro lead</Link>
      <header className="lead-hero">
        <div>
          <p className="eyebrow">Lead · {lead.id.slice(0, 8)}</p>
          <h1>{lead.name ?? "Lead sin nombre"}</h1>
          <p>Creado el {formatDate(lead.created_at)}</p>
        </div>
        <span className="status-badge status-badge--new">{leadStatusLabel[lead.status]}</span>
      </header>

      <section className="lead-detail-grid">
        <article className="panel original-request-card">
          <div className="panel__heading">
            <div>
              <p className="eyebrow">Fuente original</p>
              <h2>Solicitud sin reescritura</h2>
            </div>
            <span className="verified-label">Persistida</span>
          </div>
          <blockquote>{lead.original_request}</blockquote>
          <div className="record-meta">
            <span>Registro inmutable para procesamiento</span>
            <span>{formatDate(lead.updated_at)}</span>
          </div>
        </article>

        <aside className="panel contact-card">
          <p className="eyebrow">Contacto</p>
          <h2>Datos disponibles</h2>
          <dl>
            <div><dt>Nombre</dt><dd>{lead.name ?? "No informado"}</dd></div>
            <div><dt>Correo</dt><dd>{lead.email ?? "No informado"}</dd></div>
            <div><dt>Teléfono</dt><dd>{lead.phone ?? "No informado"}</dd></div>
          </dl>
        </aside>
      </section>

      <section className="panel next-stage-card">
        <div>
          <p className="eyebrow">Siguiente etapa</p>
          <h2>Extracción estructurada todavía no ejecutada</h2>
          <p>
            Esta base no simula resultados de IA. El próximo milestone añadirá salida validada, observabilidad y
            estados de error antes de habilitar el matching.
          </p>
        </div>
        <button className="button button--disabled" type="button" disabled>Procesar requisitos · próximamente</button>
      </section>
    </div>
  );
}
