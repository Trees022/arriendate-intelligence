import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { PageHeader } from "../components/PageHeader";
import { StatePanel } from "../components/StatePanel";
import { getOperationsWorkspace } from "../lib/api";

const priorityOrder = { high: 0, medium: 1, low: 2 };

export function DashboardPage() {
  const workspace = useQuery({
    queryKey: ["operations-workspace"],
    queryFn: getOperationsWorkspace,
  });

  const centers = workspace.data?.centers ?? [];
  const activeProperties = centers.filter((center) => center.property.commercial_status === "active").length;
  const activeCampaigns = centers.reduce(
    (total, center) => total + center.campaigns.filter((campaign) => campaign.status === "active").length,
    0,
  );
  const publishedDestinations = centers.reduce(
    (total, center) => total + center.distribution.filter((item) => item.latest_publication !== null).length,
    0,
  );
  const readyToPublish = centers.reduce(
    (total, center) => total + center.distribution.filter((item) => ["ready", "ready_to_repost"].includes(item.status)).length,
    0,
  );
  const requiresAction = centers.reduce(
    (total, center) => total + center.distribution.filter((item) => ["requires_action", "failed"].includes(item.status)).length,
    0,
  );
  const openConversations = centers.reduce(
    (total, center) => total + center.related_conversations.filter((item) => ["open", "needs_reply"].includes(item.status)).length,
    0,
  );
  const actions = centers
    .flatMap((center) => center.next_actions.map((action) => ({ action, property: center.property })))
    .sort((left, right) => priorityOrder[left.action.priority] - priorityOrder[right.action.priority])
    .slice(0, 8);

  return (
    <div className="page-stack operations-dashboard">
      <PageHeader
        eyebrow="Operación comercial"
        title="Tu cartera, publicaciones y consultas en un solo lugar."
        description="Organiza propiedades, prepara contenido y avanza cada publicación desde una vista operativa."
        action={<Link className="button button--primary" to="/properties/new">+ Nueva propiedad</Link>}
      />

      {workspace.data?.demo_mode ? (
        <div className="demo-banner"><strong>Demo local</strong><span>Los datos sociales y conversaciones son ficticios.</span></div>
      ) : null}
      {workspace.isPending ? <StatePanel title="Preparando tu operación" message="Reuniendo propiedades, publicaciones y consultas…" /> : null}
      {workspace.isError ? <StatePanel tone="error" title="No pudimos cargar el dashboard" message={workspace.error.message} /> : null}

      {workspace.data ? (
        <>
          <section className="metric-grid metric-grid--operations" aria-label="Resumen operativo">
            <Link className="metric-card metric-card--accent" to="/properties?status=active">
              <span className="metric-card__label">Propiedades activas</span><strong>{activeProperties}</strong><small>en comercialización</small>
            </Link>
            <Link className="metric-card" to="/publications">
              <span className="metric-card__label">Campañas activas</span><strong>{activeCampaigns}</strong><small>campañas en curso</small>
            </Link>
            <Link className="metric-card" to="/publications?view=published">
              <span className="metric-card__label">Destinos publicados</span><strong>{publishedDestinations}</strong><small>con publicación registrada</small>
            </Link>
            <Link className="metric-card" to="/publications?view=ready">
              <span className="metric-card__label">Listo para publicar</span><strong>{readyToPublish}</strong><small>incluye republicaciones</small>
            </Link>
            <Link className="metric-card metric-card--warning" to="/publications?view=action">
              <span className="metric-card__label">Requiere acción</span><strong>{requiresAction}</strong><small>destinos por resolver</small>
            </Link>
            <Link className="metric-card" to="/inbox">
              <span className="metric-card__label">Conversaciones abiertas</span><strong>{openConversations}</strong><small>abiertas o sin respuesta</small>
            </Link>
          </section>

          <section className="dashboard-grid dashboard-grid--operations">
            <article className="panel operations-actions-panel">
              <div className="panel__heading">
                <div><p className="eyebrow">Próximas acciones</p><h2>Lo que necesita tu atención</h2></div>
                <span className="subtle-badge">Ordenadas por prioridad</span>
              </div>
              {actions.length ? (
                <div className="dashboard-action-list">
                  {actions.map(({ action, property }) => (
                    <Link to={`/properties/${property.id}/command-center`} key={`${property.id}-${action.type}-${action.related_entity_id}`}>
                      <span className={`action-priority action-priority--${action.priority}`} aria-hidden="true" />
                      <span><strong>{property.title}</strong><small>{action.title}</small></span>
                      <span className="dashboard-action-list__arrow">→</span>
                    </Link>
                  ))}
                </div>
              ) : <StatePanel title="Operación al día" message="No hay acciones pendientes para las propiedades visibles." />}
            </article>

            <article className="panel portfolio-panel">
              <p className="eyebrow">Cartera</p>
              <h2>{workspace.data.properties.length} propiedades gestionadas</h2>
              <p>Abre una propiedad para revisar su distribución, consultas e historial comercial.</p>
              <div className="portfolio-panel__actions">
                <Link className="button button--secondary" to="/properties">Ver propiedades</Link>
                <Link className="text-link" to="/publications">Abrir cola de publicaciones →</Link>
              </div>
            </article>
          </section>
        </>
      ) : null}
    </div>
  );
}
