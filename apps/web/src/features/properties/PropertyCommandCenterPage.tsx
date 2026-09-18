import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { StatePanel } from "../../components/StatePanel";
import {
  getPropertyCommandCenter,
  markPublicationComplete,
  markPublicationRequiresAction,
} from "../../lib/api";
import { formatPropertyPrice } from "../../lib/format";
import type { DistributionItem, PropertyCommandCenter } from "../../lib/types";

const channelLabels: Record<string, string> = {
  facebook_page: "Facebook Page",
  instagram_professional: "Instagram Professional",
  facebook_group: "Facebook Group",
  facebook_marketplace: "Facebook Marketplace",
  portal_inmobiliario: "Portal Inmobiliario",
  yapo: "Yapo",
  whatsapp_catalog: "WhatsApp",
  website: "Sitio web",
  email: "Email",
  generic: "Otro canal",
};

const statusLabels: Record<string, string> = {
  ready: "Listo para publicar",
  ready_to_repost: "Listo para republicar",
  cooldown: "En cooldown",
  requires_action: "Requiere acción",
  failed: "Falló",
  published: "Publicado",
  not_scheduled: "Sin campaña",
};

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
const commercialStatusLabels: Record<string, string> = {
  draft: "Borrador",
  active: "Activa",
  reserved: "Reservada",
  closed: "Cerrada",
  archived: "Archivada",
};
const campaignStatusLabels: Record<string, string> = {
  draft: "Borrador",
  active: "Activa",
  paused: "Pausada",
  completed: "Completada",
  archived: "Archivada",
};

function formatDate(value: string | null) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("es-CL", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function metricValue(value: number | null) {
  return value === null ? "No disponible" : new Intl.NumberFormat("es-CL").format(value);
}

function AssistedWorkflow({
  item,
  onComplete,
  onRequiresAction,
  pending,
}: {
  item: DistributionItem;
  onComplete: (jobId: string, publicationUrl: string) => void;
  onRequiresAction: (jobId: string) => void;
  pending: boolean;
}) {
  const [publicationUrl, setPublicationUrl] = useState("");
  const [copied, setCopied] = useState<string | null>(null);
  const variant = item.package_variant;

  const copyText = async (label: string, value: string) => {
    await navigator.clipboard.writeText(value);
    setCopied(label);
    window.setTimeout(() => setCopied(null), 1600);
  };

  return (
    <div className="assisted-workflow">
      <div className="assisted-workflow__intro">
        <div>
          <strong>Kit de publicación preparado</strong>
          <p>Arriendate organiza el contenido; tú confirmas la acción en la plataforma.</p>
        </div>
        {item.target.destination_url ? (
          <a className="button button--secondary" href={item.target.destination_url} target="_blank" rel="noreferrer">
            Abrir destino
          </a>
        ) : null}
      </div>

      {variant ? (
        <div className="copy-grid">
          <article className="copy-card">
            <span>Titular</span>
            <p>{variant.headline}</p>
            <button className="text-button" type="button" onClick={() => copyText("headline", variant.headline)}>
              {copied === "headline" ? "Copiado" : "Copiar titular"}
            </button>
          </article>
          <article className="copy-card copy-card--wide">
            <span>Texto</span>
            <p className="copy-card__body">{variant.body}</p>
            <button className="text-button" type="button" onClick={() => copyText("body", variant.body)}>
              {copied === "body" ? "Copiado" : "Copiar texto"}
            </button>
          </article>
          <article className="copy-card">
            <span>Hechos verificados</span>
            <ul>{variant.highlights.map((highlight) => <li key={highlight}>{highlight}</li>)}</ul>
            <button
              className="text-button"
              type="button"
              onClick={() => copyText("facts", variant.highlights.join("\n"))}
            >
              {copied === "facts" ? "Copiados" : "Copiar hechos"}
            </button>
          </article>
        </div>
      ) : (
        <StatePanel title="Paquete no disponible" message="Genera y aprueba una variante para habilitar el kit." />
      )}

      <div className="prepared-media">
        <strong>Fotos · orden preparado</strong>
        {item.prepared_media.length ? (
          <ol>
            {item.prepared_media.map((media) => (
              <li key={media.id}>
                <a href={media.url} target="_blank" rel="noreferrer">{media.original_filename}</a>
                {media.is_cover ? <span>Portada</span> : null}
              </li>
            ))}
          </ol>
        ) : <p>La propiedad todavía no tiene fotos preparadas.</p>}
      </div>

      {item.job ? (
        <div className="completion-row">
          <label>
            <span>URL publicada</span>
            <input
              value={publicationUrl}
              onChange={(event) => setPublicationUrl(event.target.value)}
              placeholder="https://…"
              inputMode="url"
            />
          </label>
          <button
            className="button button--primary"
            type="button"
            disabled={pending}
            onClick={() => onComplete(item.job!.id, publicationUrl)}
          >
            Marcar completa
          </button>
          <button
            className="button button--secondary"
            type="button"
            disabled={pending}
            onClick={() => onRequiresAction(item.job!.id)}
          >
            Marcar requiere acción
          </button>
        </div>
      ) : null}
    </div>
  );
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
              <span className={`operation-status operation-status--${item.status}`}>{statusLabels[item.status] ?? item.status}</span>
              <span className="distribution-row__date"><small>Última publicación</small><strong>{formatDate(item.last_publication_at)}</strong></span>
              <span className="distribution-row__date"><small>Próxima elegibilidad</small><strong>{formatDate(item.next_eligible_at)}</strong></span>
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
                <AssistedWorkflow
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
        <div className="demo-banner"><strong>Modo demo determinístico</strong><span>Los datos sociales son fixtures; no provienen de Meta.</span></div>
      ) : null}
      <header className="command-hero">
        <div className="command-hero__photo" aria-hidden="true"><span>Sin foto de portada</span></div>
        <div className="command-hero__content">
          <p className="eyebrow">Property Command Center</p>
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

      <section className="next-actions">
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
          <div><p className="eyebrow">Engagement</p><h2>Señales atribuibles a publicaciones</h2></div>
          <span>Última captura {formatDate(center.engagement.last_captured_at)}</span>
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
              <div><strong>{comment.author_display_name ?? "Autor no disponible"}</strong><span>{formatDate(comment.created_external_at)}</span></div>
              <p>{comment.body}</p>
              <small>{comment.reply_status === "needs_reply" ? "Requiere respuesta" : "Gestionado"}{comment.is_demo ? " · Fixture" : ""}</small>
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
                  <div><strong>{conversation.channel_type === "messenger" ? "Messenger" : channelLabels[conversation.channel_type]}</strong><small>{formatDate(conversation.last_message_at)}</small></div>
                  <span className={`operation-status operation-status--${conversation.status}`}>{conversation.status === "needs_reply" ? "Requiere respuesta" : conversation.status}</span>
                </div>
                <div className="message-stack">
                  {conversation.messages.map((message) => (
                    <p className={`message message--${message.direction}`} key={message.id}>{message.body ?? "Mensaje sin texto"}</p>
                  ))}
                </div>
                <small>{conversation.lead_id ? "Vinculada a lead" : "Aún no promovida a lead"}{conversation.is_demo ? " · Fixture" : ""}</small>
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
              <div><strong>{campaign.publications.length} publicaciones</strong><small>{campaign.jobs.length} trabajos · creada {formatDate(campaign.created_at)}</small></div>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
