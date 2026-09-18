import { useState } from "react";
import { resolveMediaUrl } from "../../lib/api";
import type { DistributionItem } from "../../lib/types";
import { StatePanel } from "../../components/StatePanel";

interface AssistedPublicationPanelProps {
  item: DistributionItem;
  onComplete: (jobId: string, publicationUrl: string) => void;
  onRequiresAction: (jobId: string) => void;
  pending: boolean;
}

export function AssistedPublicationPanel({
  item,
  onComplete,
  onRequiresAction,
  pending,
}: AssistedPublicationPanelProps) {
  const [publicationUrl, setPublicationUrl] = useState("");
  const [copied, setCopied] = useState<string | null>(null);
  const variant = item.package_variant;
  const canComplete = ["ready", "ready_to_repost", "requires_action", "failed"].includes(item.status);

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
          <p>Arriendate ordena el material; tú confirmas la publicación en la plataforma.</p>
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
            <span>Título</span>
            <p>{variant.headline}</p>
            <button className="text-button" type="button" onClick={() => copyText("headline", variant.headline)}>
              {copied === "headline" ? "Copiado" : "Copiar título"}
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
            <span>Datos de la propiedad</span>
            <ul>{variant.highlights.map((highlight) => <li key={highlight}>{highlight}</li>)}</ul>
            <button className="text-button" type="button" onClick={() => copyText("facts", variant.highlights.join("\n"))}>
              {copied === "facts" ? "Copiados" : "Copiar datos"}
            </button>
          </article>
        </div>
      ) : (
        <StatePanel title="Contenido no disponible" message="Genera y aprueba el contenido para habilitar este kit." />
      )}

      <div className="prepared-media">
        <strong>Fotos preparadas</strong>
        {item.prepared_media.length ? (
          <div className="prepared-media__grid">
            {item.prepared_media.map((media, index) => (
              <a href={resolveMediaUrl(media.url)} target="_blank" rel="noreferrer" key={media.id}>
                <img src={resolveMediaUrl(media.url)} alt={`${media.original_filename}, foto ${index + 1}`} />
                <span>{index + 1}{media.is_cover ? " · Portada" : ""}</span>
              </a>
            ))}
          </div>
        ) : <p>La propiedad todavía no tiene fotos preparadas.</p>}
      </div>

      {item.job && canComplete ? (
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
          <button className="button button--primary" type="button" disabled={pending} onClick={() => onComplete(item.job!.id, publicationUrl)}>
            Marcar publicada
          </button>
          <button className="button button--secondary" type="button" disabled={pending} onClick={() => onRequiresAction(item.job!.id)}>
            Requiere acción
          </button>
        </div>
      ) : null}
    </div>
  );
}
