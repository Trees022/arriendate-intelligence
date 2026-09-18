import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { StatePanel } from "../../components/StatePanel";
import { getOperationsWorkspace } from "../../lib/api";
import { channelLabels, formatOperationsDate } from "./labels";

export function InboxPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const workspace = useQuery({ queryKey: ["operations-workspace"], queryFn: getOperationsWorkspace });
  const conversations = (workspace.data?.centers ?? [])
    .flatMap((center) => center.related_conversations.map((conversation) => ({ conversation, property: center.property })))
    .sort((left, right) => {
      if (left.conversation.status === "needs_reply" && right.conversation.status !== "needs_reply") return -1;
      if (right.conversation.status === "needs_reply" && left.conversation.status !== "needs_reply") return 1;
      return new Date(right.conversation.last_message_at).getTime() - new Date(left.conversation.last_message_at).getTime();
    });
  const selected = conversations.find(({ conversation }) => conversation.id === selectedId) ?? conversations[0];

  return (
    <div className="page-stack inbox-page">
      <PageHeader eyebrow="Demanda entrante" title="Inbox" description="Consultas y conversaciones vinculadas a tus propiedades, ordenadas para responder a tiempo." />
      {workspace.data?.demo_mode ? <div className="demo-banner"><strong>Demo local</strong><span>Estas conversaciones son ficticias; todavía no existe sincronización en vivo con Meta.</span></div> : null}
      {workspace.isPending ? <StatePanel title="Cargando conversaciones" message="Reuniendo consultas de la cartera…" /> : null}
      {workspace.isError ? <StatePanel tone="error" title="No pudimos cargar el inbox" message={workspace.error.message} /> : null}
      {workspace.data && !conversations.length ? <StatePanel title="Sin conversaciones" message="Cuando una consulta pueda atribuirse a una propiedad aparecerá aquí." /> : null}
      {selected ? (
        <section className="inbox-layout">
          <div className="inbox-list" aria-label="Conversaciones">
            <div className="inbox-list__heading"><strong>{conversations.length} conversaciones</strong><span>{conversations.filter(({ conversation }) => conversation.status === "needs_reply").length} sin respuesta</span></div>
            {conversations.map(({ conversation, property }) => {
              const latest = conversation.messages.at(-1);
              const person = [...conversation.messages].reverse().find((message) => message.direction === "inbound")?.sender_display_name ?? "Contacto";
              return (
                <button type="button" className={selected.conversation.id === conversation.id ? "is-active" : ""} key={conversation.id} onClick={() => setSelectedId(conversation.id)}>
                  <span className="inbox-avatar">{person.slice(0, 2).toUpperCase()}</span>
                  <span className="inbox-list__copy"><span><strong>{person}</strong><small>{formatOperationsDate(conversation.last_message_at)}</small></span><span>{channelLabels[conversation.channel_type]} · {property.title}</span><p>{latest?.body ?? "Mensaje sin texto"}</p></span>
                  {conversation.status === "needs_reply" ? <span className="inbox-unread" title="Requiere respuesta" /> : null}
                </button>
              );
            })}
          </div>
          <article className="conversation-detail">
            <header>
              <div><p className="eyebrow">{channelLabels[selected.conversation.channel_type]}</p><h2>{selected.property.title}</h2><span>{selected.conversation.is_demo ? "Datos demo" : "Conversación conectada"}</span></div>
              <div><span className={`operation-status operation-status--${selected.conversation.status}`}>{selected.conversation.status === "needs_reply" ? "Requiere respuesta" : selected.conversation.status === "open" ? "Abierta" : "Gestionada"}</span><Link to={`/properties/${selected.property.id}/command-center#inbox`}>Abrir propiedad →</Link></div>
            </header>
            <div className="conversation-detail__messages">{selected.conversation.messages.map((message) => <div className={`conversation-bubble conversation-bubble--${message.direction}`} key={message.id}><strong>{message.sender_display_name ?? (message.direction === "outbound" ? "Equipo" : "Contacto")}</strong><p>{message.body ?? "Mensaje sin texto"}</p><span>{formatOperationsDate(message.sent_at)}</span></div>)}</div>
            <footer><span>{selected.conversation.lead_id ? "Vinculada a un lead" : "Aún no convertida en lead"}</span><button className="button button--secondary" type="button" disabled>Responder · próximamente</button></footer>
          </article>
        </section>
      ) : null}
    </div>
  );
}
