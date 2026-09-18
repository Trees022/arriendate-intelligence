import { Link } from "react-router-dom";
import { resolveMediaUrl } from "../../lib/api";
import { formatPropertyPrice, knownNumber } from "../../lib/format";
import type { Property, PropertyCommandCenter } from "../../lib/types";
import { commandCenterCover, commercialStatusLabels } from "../operations/labels";

export function PropertyCard({ property, center }: { property: Property; center?: PropertyCommandCenter }) {
  const cover = center ? commandCenterCover(center) : null;
  const pendingActions = center?.next_actions.filter((action) => action.priority !== "low").length ?? 0;
  const conversations = center?.related_conversations.filter((item) => item.status === "needs_reply").length ?? 0;

  return (
    <Link className="property-card" to={`/properties/${property.id}/command-center`}>
      <div className="property-card__media">
        {cover ? <img src={resolveMediaUrl(cover.url)} alt={`Portada de ${property.title}`} /> : <span>Sin foto</span>}
        <span className={`commercial-badge commercial-badge--${property.commercial_status ?? "draft"}`}>
          {commercialStatusLabels[property.commercial_status ?? "draft"]}
        </span>
      </div>
      <div className="property-card__content">
        <div className="property-card__topline">
          <span className="property-card__type">{property.operation_type === "rent" ? "Arriendo" : "Venta"}</span>
          <span>{property.reference_code ?? "Sin referencia"}</span>
        </div>
        <div>
          <p className="property-card__location">{property.city} · {property.sector ?? "Sector por confirmar"}</p>
          <h2>{property.title}</h2>
        </div>
        <strong className="property-card__price">{formatPropertyPrice(property)}</strong>
        <div className="property-card__facts">
          <span>{knownNumber(property.bedrooms, "dorm.")}</span>
          <span>{knownNumber(property.bathrooms, "baños")}</span>
          <span>{knownNumber(property.parking_spaces, "estac.")}</span>
        </div>
        <div className="property-card__signals">
          <span><strong>{center?.distribution.length ?? 0}</strong> destinos</span>
          <span className={pendingActions ? "has-attention" : ""}><strong>{pendingActions}</strong> pendientes</span>
          <span className={conversations ? "has-attention" : ""}><strong>{conversations}</strong> consultas</span>
        </div>
        <div className="property-card__footer">
          <strong>Abrir centro de operación</strong><span aria-hidden="true">→</span>
        </div>
      </div>
    </Link>
  );
}
