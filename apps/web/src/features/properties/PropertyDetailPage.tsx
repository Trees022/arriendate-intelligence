import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { StatePanel } from "../../components/StatePanel";
import { getProperty } from "../../lib/api";
import { availabilityLabel, formatPropertyPrice, petPolicyLabel } from "../../lib/format";

function valueOrUnknown(value: string | number | null, suffix = "") {
  return value === null ? "Por confirmar" : `${value}${suffix}`;
}

export function PropertyDetailPage() {
  const { id = "" } = useParams();
  const query = useQuery({
    queryKey: ["property", id],
    queryFn: () => getProperty(id),
    enabled: Boolean(id),
  });

  if (query.isPending) return <StatePanel title="Cargando propiedad" message="Recuperando su ficha verificable…" />;
  if (query.isError) return <StatePanel tone="error" title="No pudimos abrir la propiedad" message={query.error.message} />;

  const property = query.data;
  return (
    <div className="page-stack detail-page">
      <Link className="back-link" to="/properties">← Volver al inventario</Link>
      <header className="detail-hero">
        <div>
          <div className="detail-hero__badges">
            <span className={`status-badge status-badge--${property.availability_status}`}>
              {availabilityLabel[property.availability_status]}
            </span>
            <span className="subtle-badge">{property.operation_type === "rent" ? "Arriendo" : "Venta"}</span>
          </div>
          <p className="eyebrow">{property.city} · {property.sector ?? "Sector por confirmar"}</p>
          <h1>{property.title}</h1>
          <p>{property.description}</p>
        </div>
        <div className="detail-price">
          <span>Valor publicado</span>
          <strong>{formatPropertyPrice(property)}</strong>
          <small>Registro sintético · no es una oferta real</small>
        </div>
      </header>

      <section className="detail-grid">
        <article className="panel">
          <p className="eyebrow">Ficha estructurada</p>
          <h2>Atributos conocidos</h2>
          <dl className="fact-list">
            <div><dt>Tipo</dt><dd>{property.property_type}</dd></div>
            <div><dt>Dormitorios</dt><dd>{valueOrUnknown(property.bedrooms)}</dd></div>
            <div><dt>Baños</dt><dd>{valueOrUnknown(property.bathrooms)}</dd></div>
            <div><dt>Estacionamientos</dt><dd>{valueOrUnknown(property.parking_spaces)}</dd></div>
            <div><dt>Superficie</dt><dd>{valueOrUnknown(property.square_meters, " m²")}</dd></div>
            <div><dt>Mascotas</dt><dd>{petPolicyLabel[property.pet_policy]}</dd></div>
            <div><dt>Amoblado</dt><dd>{property.furnished === null ? "Por confirmar" : property.furnished ? "Sí" : "No"}</dd></div>
          </dl>
        </article>
        <article className="panel">
          <p className="eyebrow">Comodidades declaradas</p>
          <h2>Sin inferencias adicionales</h2>
          {property.amenities.length ? (
            <ul className="tag-list">
              {property.amenities.map((amenity) => <li key={amenity}>{amenity}</li>)}
            </ul>
          ) : (
            <StatePanel title="Sin información" message="El registro no declara comodidades. No asumimos ninguna." />
          )}
          <div className="source-box">
            <strong>Fuente controlada</strong>
            <p>{property.source_text}</p>
          </div>
        </article>
      </section>
    </div>
  );
}
