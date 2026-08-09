import { Link } from "react-router-dom";
import { availabilityLabel, formatPropertyPrice, knownNumber, petPolicyLabel } from "../../lib/format";
import type { Property } from "../../lib/types";

export function PropertyCard({ property }: { property: Property }) {
  return (
    <Link className="property-card" to={`/properties/${property.id}`}>
      <div className="property-card__topline">
        <span className={`status-badge status-badge--${property.availability_status}`}>
          {availabilityLabel[property.availability_status]}
        </span>
        <span className="property-card__type">
          {property.operation_type === "rent" ? "Arriendo" : "Venta"}
        </span>
      </div>
      <div>
        <p className="property-card__location">{property.city} · {property.sector ?? "Sector por confirmar"}</p>
        <h2>{property.title}</h2>
      </div>
      <strong className="property-card__price">{formatPropertyPrice(property)}</strong>
      <p className="property-card__description">{property.description}</p>
      <div className="property-card__facts">
        <span>{knownNumber(property.bedrooms, "dorm.")}</span>
        <span>{knownNumber(property.bathrooms, "baños")}</span>
        <span>{knownNumber(property.parking_spaces, "estac.")}</span>
      </div>
      <div className="property-card__footer">
        <span>{petPolicyLabel[property.pet_policy]}</span>
        <span aria-hidden="true">→</span>
      </div>
    </Link>
  );
}
