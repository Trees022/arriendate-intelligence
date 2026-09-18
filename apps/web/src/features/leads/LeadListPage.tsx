import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { StatePanel } from "../../components/StatePanel";
import { getLeads } from "../../lib/api";
import { formatDate, leadStatusLabel } from "../../lib/format";

export function LeadListPage() {
  const query = useQuery({ queryKey: ["leads"], queryFn: getLeads });
  return (
    <div className="page-stack leads-page">
      <PageHeader
        eyebrow="CRM e inteligencia"
        title="Leads"
        description="Personas interesadas detectadas o registradas para seguimiento y búsqueda de propiedades."
        action={<Link className="button button--primary" to="/leads/new">+ Registrar lead</Link>}
      />
      {query.isPending ? <StatePanel title="Cargando leads" message="Reuniendo los clientes potenciales registrados…" /> : null}
      {query.isError ? <StatePanel tone="error" title="No pudimos cargar los leads" message={query.error.message} /> : null}
      {query.data?.items.length === 0 ? <StatePanel title="Sin leads registrados" message="Puedes agregar una consulta manualmente cuando necesites iniciar un seguimiento." /> : null}
      {query.data?.items.length ? (
        <section className="lead-list" aria-label="Leads registrados">
          <div className="lead-list__heading"><strong>{query.data.total} leads</strong><span>Ordenados por ingreso reciente</span></div>
          {query.data.items.map((lead) => (
            <Link to={`/leads/${lead.id}`} key={lead.id}>
              <span className="lead-list__avatar">{(lead.name ?? "Lead").slice(0, 2).toUpperCase()}</span>
              <span><strong>{lead.name ?? "Lead sin nombre"}</strong><small>{lead.email ?? lead.phone ?? "Sin contacto informado"}</small><p>{lead.original_request}</p></span>
              <span><span className={`status-badge status-badge--${lead.status}`}>{leadStatusLabel[lead.status]}</span><small>{formatDate(lead.created_at)}</small></span>
              <span aria-hidden="true">→</span>
            </Link>
          ))}
        </section>
      ) : null}
      <aside className="crm-note"><strong>De conversación a oportunidad</strong><p>El motor de requisitos y matching sigue disponible dentro de cada lead. La conversión automática desde Inbox se incorporará en una etapa posterior.</p></aside>
    </div>
  );
}
