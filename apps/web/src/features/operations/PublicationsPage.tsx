import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { PageHeader } from "../../components/PageHeader";
import { StatePanel } from "../../components/StatePanel";
import { getOperationsWorkspace, markPublicationComplete, markPublicationRequiresAction } from "../../lib/api";
import type { DistributionItem, Property } from "../../lib/types";
import { AssistedPublicationPanel } from "./AssistedPublicationPanel";
import { channelLabels, distributionStatusLabels, formatOperationsDate } from "./labels";

type QueueView = "attention" | "ready" | "action" | "scheduled" | "published" | "cooldown" | "all";

const views: Array<{ value: QueueView; label: string }> = [
  { value: "attention", label: "Prioridad" },
  { value: "ready", label: "Listas" },
  { value: "action", label: "Requiere acción" },
  { value: "scheduled", label: "Programadas" },
  { value: "published", label: "Publicadas" },
  { value: "cooldown", label: "En espera" },
  { value: "all", label: "Todas" },
];

function matchesView(item: DistributionItem, view: QueueView) {
  if (view === "all") return true;
  if (view === "attention") return ["ready", "ready_to_repost", "requires_action", "failed"].includes(item.status);
  if (view === "ready") return ["ready", "ready_to_repost"].includes(item.status);
  if (view === "action") return ["requires_action", "failed"].includes(item.status);
  if (view === "published") return item.latest_publication !== null;
  return item.status === view;
}

export function PublicationsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedView = searchParams.get("view") as QueueView | null;
  const view = views.some((item) => item.value === requestedView) ? requestedView! : "attention";
  const queryClient = useQueryClient();
  const workspace = useQuery({ queryKey: ["operations-workspace"], queryFn: getOperationsWorkspace });
  const complete = useMutation({
    mutationFn: ({ jobId, url }: { jobId: string; url: string }) => markPublicationComplete(jobId, url),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["operations-workspace"] }),
  });
  const requireAction = useMutation({
    mutationFn: (jobId: string) => markPublicationRequiresAction(jobId, "Revisión solicitada desde la cola de publicaciones."),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["operations-workspace"] }),
  });
  const queue = (workspace.data?.centers ?? [])
    .flatMap((center) => center.distribution.map((item) => ({ item, property: center.property })))
    .filter(({ item }) => matchesView(item, view))
    .sort((left, right) => {
      const order: Record<string, number> = { requires_action: 0, failed: 1, ready_to_repost: 2, ready: 3, scheduled: 4, cooldown: 5 };
      return (order[left.item.status] ?? 9) - (order[right.item.status] ?? 9);
    });

  return (
    <div className="page-stack publications-page">
      <PageHeader eyebrow="Operación de canales" title="Publicaciones" description="Publica, republica y resuelve pendientes sin perder el estado de cada propiedad." action={<Link className="button button--primary" to="/properties/new">+ Nueva propiedad</Link>} />
      {workspace.data?.demo_mode ? <div className="demo-banner"><strong>Demo local</strong><span>La cola contiene trabajos y destinos ficticios.</span></div> : null}
      <nav className="queue-tabs" aria-label="Vistas de publicaciones">{views.map((item) => <button type="button" className={view === item.value ? "is-active" : ""} key={item.value} onClick={() => setSearchParams(item.value === "attention" ? {} : { view: item.value })}>{item.label}</button>)}</nav>
      {workspace.isPending ? <StatePanel title="Cargando publicaciones" message="Reuniendo trabajos de toda la cartera…" /> : null}
      {workspace.isError ? <StatePanel tone="error" title="No pudimos cargar las publicaciones" message={workspace.error.message} /> : null}
      {workspace.data && !queue.length ? <StatePanel title="Sin publicaciones en esta vista" message="No hay trabajos que coincidan con el estado seleccionado." /> : null}
      <section className="publication-queue" aria-label="Cola de publicaciones">
        {queue.map(({ item, property }) => (
          <PublicationQueueItem
            key={`${property.id}-${item.target.id}`}
            item={item}
            property={property}
            pending={complete.isPending || requireAction.isPending}
            onComplete={(jobId, url) => complete.mutate({ jobId, url })}
            onRequiresAction={(jobId) => requireAction.mutate(jobId)}
          />
        ))}
      </section>
      {complete.isError || requireAction.isError ? <div className="form-alert" role="alert">No pudimos actualizar la publicación.</div> : null}
    </div>
  );
}

function PublicationQueueItem({ item, property, pending, onComplete, onRequiresAction }: {
  item: DistributionItem;
  property: Property;
  pending: boolean;
  onComplete: (jobId: string, url: string) => void;
  onRequiresAction: (jobId: string) => void;
}) {
  const isAssisted = ["assisted", "manual"].includes(item.target.execution_mode);
  return (
    <details className="publication-queue__item">
      <summary>
        <span className="channel-mark">{channelLabels[item.target.channel_type]?.slice(0, 2)}</span>
        <span><strong>{property.title}</strong><small>{item.target.name} · {channelLabels[item.target.channel_type]}</small></span>
        <span className={`operation-status operation-status--${item.status}`}>{distributionStatusLabels[item.status] ?? item.status}</span>
        <span className="queue-date"><small>Última publicación</small><strong>{formatOperationsDate(item.last_publication_at)}</strong></span>
        <span aria-hidden="true">+</span>
      </summary>
      <div className="publication-queue__detail">
        <div className="queue-context"><Link to={`/properties/${property.id}/command-center`}>Abrir centro de operación →</Link>{item.next_eligible_at ? <span>Próxima disponibilidad: {formatOperationsDate(item.next_eligible_at)}</span> : null}</div>
        {isAssisted ? <AssistedPublicationPanel item={item} pending={pending} onComplete={onComplete} onRequiresAction={onRequiresAction} /> : <div className="official-boundary"><strong>Canal con conexión oficial</strong><p>La ejecución real depende de una cuenta conectada y permisos vigentes.</p>{item.publication_url ? <a href={item.publication_url} target="_blank" rel="noreferrer">Ver publicación registrada</a> : null}</div>}
      </div>
    </details>
  );
}
