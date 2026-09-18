import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { StatePanel } from "../../components/StatePanel";
import {
  getPropertyCommandCenter,
  markPublicationComplete,
  markPublicationRequiresAction,
  resolveMediaUrl,
} from "../../lib/api";
import { formatPropertyPrice } from "../../lib/format";
import type { PropertyCommandCenter } from "../../lib/types";
import { AssistedPublicationPanel } from "../operations/AssistedPublicationPanel";
import {
  campaignStatusLabels,
  channelLabels,
  commandCenterCover,
  commercialStatusLabels,
  distributionStatusLabels,
  formatOperationsDate,
} from "../operations/labels";

const actionPriorityLabels = { high: "Ahora", medium: "Próximo", low: "Después" };
const capabilityLabels: Record<string, string> = {
  publish_content: "Publicar contenido",
  read_comments: "Leer comentarios",
  reply_comments: "Responder comentarios",
  read_messages: "Leer mensajes",
  send_messages: "Enviar mensajes",
  read_reactions: "Leer reacciones",
  read_metrics: "Leer métricas",
  schedule_content: "Programar contenido",
  automatic_repost: "Repost automático",
  assisted_publish: "Publicación asistida",
};
const availabilityLabels: Record<string, string> = {
  available: "Disponible",
  requires_permission: "Requiere permiso",
  requires_connection: "Requiere conexión",
  assisted_only: "Sólo asistido",
};
function metricValue(value: number | null) {
  return value === null ? "No disponible" : new Intl.NumberFormat("es-CL").format(value);
}

function DistributionSection({ center }: { center: PropertyCommandCenter }) {
  const queryClient = useQueryClient();
  const mutation = useMutation({
    mutationFn: ({ jobId, publicationUrl }: { jobId: string; publicationUrl: string }) =>
      markPublicationComplete(jobId, publicationUrl),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["property-command-center"] }),
  });
  const actionMutation = useMutation({
    mutationFn: (jobId: string) =>
      markPublicationRequiresAction(jobId, "Revisión solicitada por el operador."),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["property-command-center"] }),
  });

  return (
    <section className="command-section" id="distribution">
      <div className="section-heading">
        <div><p className="eyebrow">Distribución</p><h2>Dónde está publicada y qué sigue</h2></div>
        <span>{center.distribution.length} destinos activos</span>
      </div>
      <div className="distribution-list">
        {center.distribution.map((item) => (
          <details className="distribution-row" key={item.target.id}>
            <summary>
              <span className="channel-mark" aria-hidden="true">{channelLabels[item.target.channel_type]?.slice(0, 2)}</span>
              <span className="distribution-row__identity">
                <strong>{item.target.name}</strong>
                <small>{channelLabels[item.target.channel_type]} · {item.target.execution_mode === "api" ? "API oficial" : "Flujo asistido"}</small>
              </span>
              <span className={`operation-status operation-status--${item.status}`}>{distributionStatusLabels[item.status] ?? item.status}</span>
              <span className="distribution-row__date"><small>Última publicación</small><strong>{formatOperationsDate(item.last_publication_at)}</strong></span>
              <span className="distribution-row__date"><small>Próxima elegibilidad</small><strong>{formatOperationsDate(item.next_eligible_at)}</strong></span>
              <span className="disclosure-mark" aria-hidden="true">+</span>
            </summary>
            <div className="distribution-row__detail">
              <div className="capability-strip">
                {item.capabilities
                  .filter((capability) => capability.availability !== "unavailable")
                  .map((capability) => (
                    <span key={capability.capability}>
                      {capabilityLabels[capability.capability] ?? capability.capability} · {availabilityLabels[capability.availability] ?? capability.availability}
                    </span>
                  ))}
              </div>
              {item.publication_url ? (
                <a className="publication-link" href={item.publication_url} target="_blank" rel="noreferrer">Ver publicación registrada</a>
              ) : null}
              {item.target.execution_mode === "assisted" || item.target.execution_mode === "manual" ? (
                <AssistedPublicationPanel
                  item={item}
                  pending={mutation.isPending || actionMutation.isPending}
                  onComplete={(jobId, publicationUrl) => mutation.mutate({ jobId, publicationUrl })}
                  onRequiresAction={(jobId) => actionMutation.mutate(jobId)}
                />
              ) : (
                <div className="official-boundary">
                  <strong>Superficie oficial aislada</strong>
                  <p>Esta cuenta usa un adapter propio. En demo no se realizan llamadas ni se guardan credenciales Meta.</p>
                </div>
              )}
            </div>
          </details>
        ))}
      </div>
      {mutation.isError || actionMutation.isError ? (
        <StatePanel tone="error" title="No pudimos actualizar el trabajo" message="Revisa el estado e inténtalo nuevamente." />
      ) : null}
    </section>
  );
}

export function PropertyCommandCenterPage() {
  const { id = "" } = useParams();
  const query = useQuery({
    queryKey: ["property-command-center", id],
    queryFn: () => getPropertyCommandCenter(id),
    enabled: Boolean(id),
  });

  if (query.isPending) return <StatePanel title="Abriendo Command Center" message="Consolidando distribución, engagement y conversaciones…" />;
  if (query.isError) return <StatePanel tone="error" title="No pudimos abrir el Command Center" message={query.error.message} />;

  const center = query.data;
  const property = center.property;
  const cover = commandCenterCover(center);
  const metrics = [
    ["Comentarios", center.engagement.comments_count],
    ["Reacciones", center.engagement.reactions_count],
    ["Vistas", center.engagement.views_count],
    ["Impresiones", center.engagement.impressions_count],
    ["Mensajes", center.engagement.messages_count],
  ] as const;

  return (
    <div className="page-stack command-center">
      <Link className="back-link" to="/properties">← Volver a propiedades</Link>
      {center.demo_mode ? (
        <div className="demo-banner"><strong>Demo local</strong><span>Los datos sociales son ficticios; no provienen de Meta.</span></div>
      ) : null}
      <nav className="command-tabs" aria-label="Secciones de la propiedad">
        <a href="#actions">Próximas acciones</a>
        <a href="#distribution">Distribución</a>
        <a href="#engagement">Interacción</a>
        <a href="#inbox">Conversaciones</a>
        <a href="#history">Historial</a>
      </nav>
      <header className="command-hero">
        <div className="command-hero__photo">
          {cover ? <img src={resolveMediaUrl(cover.url)} alt={`Portada de ${property.title}`} /> : <span>Sin foto de portada</span>}
        </div>
        <div className="command-hero__content">
          <p className="eyebrow">Centro de operación</p>
          <h1>{property.title}</h1>
          <p>{property.city} · {property.sector ?? "Sector por confirmar"}</p>
          <div className="command-hero__meta">
            <strong>{formatPropertyPrice(property)}</strong>
            <span>{commercialStatusLabels[property.commercial_status ?? "active"]}</span>
            <span>{property.reference_code ?? "Sin código interno"}</span>
          </div>
        </div>
        <Link className="button button--secondary" to={`/properties/${property.id}`}>Ver ficha completa</Link>
      </header>

      <section className="next-actions" id="actions">
        <div className="section-heading">
          <div><p className="eyebrow">Próximas acciones</p><h2>Qué debería pasar ahora</h2></div>
          <span>Prioridad determinística</span>
        </div>
        {center.next_actions.length ? (
          <div className="action-grid">
            {center.next_actions.slice(0, 6).map((action) => (
              <article className={`action-card action-card--${action.priority}`} key={`${action.type}-${action.related_entity_id}`}>
                <span>{actionPriorityLabels[action.priority]}</span>
                <h3>{action.title}</h3>
                <p>{action.description}</p>
              </article>
            ))}
          </div>
        ) : <StatePanel title="Sin acciones pendientes" message="El estado comercial está al día." />}
      </section>

      <DistributionSection center={center} />

      <section className="command-section" id="engagement">
        <div className="section-heading">
          <div><p className="eyebrow">Interacción</p><h2>Resultados atribuibles a publicaciones</h2></div>
          <span>Última captura {formatOperationsDate(center.engagement.last_captured_at)}</span>
        </div>
        <div className="engagement-grid">
          {metrics.map(([label, value]) => (
            <article className="engagement-metric" key={label}>
              <span>{label}</span><strong className={value === null ? "is-unavailable" : ""}>{metricValue(value)}</strong>
            </article>
          ))}
        </div>
        <div className="comment-list">
          {center.recent_comments.map((comment) => (
            <article key={comment.id}>
              <div><strong>{comment.author_display_name ?? "Autor no disponible"}</strong><span>{formatOperationsDate(comment.created_external_at)}</span></div>
              <p>{comment.body}</p>
              <small>{comment.reply_status === "needs_reply" ? "Requiere respuesta" : "Gestionado"}{comment.is_demo ? " · Demo" : ""}</small>
            </article>
          ))}
        </div>
      </section>

      <section className="command-section" id="inbox">
        <div className="section-heading">
          <div><p className="eyebrow">Inbox</p><h2>Conversaciones vinculadas a esta propiedad</h2></div>
          <span>{center.related_conversations.length} conversaciones</span>
        </div>
        {center.related_conversations.length ? (
          <div className="conversation-list">
            {center.related_conversations.map((conversation) => (
              <article className="conversation-card" key={conversation.id}>
                <div className="conversation-card__header">
                  <div><strong>{conversation.channel_type === "messenger" ? "Messenger" : channelLabels[conversation.channel_type]}</strong><small>{formatOperationsDate(conversation.last_message_at)}</small></div>
                  <span className={`operation-status operation-status--${conversation.status}`}>{conversation.status === "needs_reply" ? "Requiere respuesta" : conversation.status}</span>
                </div>
                <div className="message-stack">
                  {conversation.messages.map((message) => (
                    <p className={`message message--${message.direction}`} key={message.id}>{message.body ?? "Mensaje sin texto"}</p>
                  ))}
                </div>
                <small>{conversation.lead_id ? "Vinculada a lead" : "Aún no promovida a lead"}{conversation.is_demo ? " · Demo" : ""}</small>
              </article>
            ))}
          </div>
        ) : <StatePanel title="Sin conversaciones atribuidas" message="No inventamos atribución cuando el origen es desconocido." />}
      </section>

      <section className="command-section command-section--compact" id="history">
        <div className="section-heading">
          <div><p className="eyebrow">Campaña e historial</p><h2>Actividad comercial registrada</h2></div>
          <span>{center.campaigns.length} campañas</span>
        </div>
        <div className="history-list">
          {center.campaigns.map((campaign) => (
            <article key={campaign.id}>
              <span className="operation-status">{campaignStatusLabels[campaign.status]}</span>
              <div><strong>{campaign.publications.length} publicaciones</strong><small>{campaign.jobs.length} trabajos · creada {formatOperationsDate(campaign.created_at)}</small></div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
