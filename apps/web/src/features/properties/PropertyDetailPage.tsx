import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { StatePanel } from "../../components/StatePanel";
import {
  deletePropertyMedia,
  getPropertyCommandCenter,
  getPropertyMedia,
  resolveMediaUrl,
  setPropertyCover,
  updateProperty,
  uploadPropertyMedia,
} from "../../lib/api";
import { formatPropertyPrice, petPolicyLabel } from "../../lib/format";
import type { CommercialStatus, Property } from "../../lib/types";
import { commercialStatusLabels } from "../operations/labels";

function valueOrUnknown(value: string | number | null | undefined, suffix = "") {
  return value === null || value === undefined ? "Por confirmar" : `${value}${suffix}`;
}

function PropertyEditor({ property, onSaved }: { property: Property; onSaved: () => void }) {
  const [title, setTitle] = useState(property.title);
  const [description, setDescription] = useState(property.description);
  const [city, setCity] = useState(property.city);
  const [sector, setSector] = useState(property.sector ?? "");
  const [price, setPrice] = useState(String(property.operation_type === "rent" ? property.monthly_price ?? "" : property.sale_price ?? ""));
  const [status, setStatus] = useState<CommercialStatus>(property.commercial_status ?? "draft");
  const mutation = useMutation({
    mutationFn: () => updateProperty(property.id, {
      title,
      description,
      city,
      sector: sector || null,
      commercial_status: status,
      ...(property.operation_type === "rent" ? { monthly_price: Number(price) } : { sale_price: Number(price) }),
    }),
    onSuccess: onSaved,
  });

  return (
    <details className="inline-editor">
      <summary>Editar propiedad</summary>
      <form onSubmit={(event) => { event.preventDefault(); mutation.mutate(); }}>
        <label><span>Título</span><input value={title} onChange={(event) => setTitle(event.target.value)} required minLength={3} /></label>
        <label><span>Ciudad</span><input value={city} onChange={(event) => setCity(event.target.value)} required /></label>
        <label><span>Sector</span><input value={sector} onChange={(event) => setSector(event.target.value)} /></label>
        <label><span>Precio</span><input type="number" min="0" value={price} onChange={(event) => setPrice(event.target.value)} required /></label>
        <label><span>Estado comercial</span><select value={status} onChange={(event) => setStatus(event.target.value as CommercialStatus)}><option value="draft">Borrador</option><option value="active">Activa</option><option value="reserved">Reservada</option><option value="closed">Cerrada</option><option value="archived">Archivada</option></select></label>
        <label className="inline-editor__wide"><span>Descripción</span><textarea value={description} onChange={(event) => setDescription(event.target.value)} required minLength={5} rows={4} /></label>
        <div className="inline-editor__wide inline-editor__actions">
          <button className="button button--primary" type="submit" disabled={mutation.isPending}>{mutation.isPending ? "Guardando…" : "Guardar cambios"}</button>
          {mutation.isError ? <span role="alert">{mutation.error.message}</span> : null}
        </div>
      </form>
    </details>
  );
}

export function PropertyDetailPage() {
  const { id = "" } = useParams();
  const queryClient = useQueryClient();
  const centerQuery = useQuery({ queryKey: ["property-command-center", id], queryFn: () => getPropertyCommandCenter(id), enabled: Boolean(id) });
  const mediaQuery = useQuery({ queryKey: ["property-media", id], queryFn: () => getPropertyMedia(id), enabled: Boolean(id) });
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["property-command-center", id] });
    void queryClient.invalidateQueries({ queryKey: ["property-media", id] });
    void queryClient.invalidateQueries({ queryKey: ["operations-workspace"] });
  };
  const upload = useMutation({ mutationFn: (files: File[]) => Promise.all(files.map((file) => uploadPropertyMedia(id, file))), onSuccess: refresh });
  const remove = useMutation({ mutationFn: (mediaId: string) => deletePropertyMedia(id, mediaId), onSuccess: refresh });
  const cover = useMutation({ mutationFn: (mediaId: string) => setPropertyCover(id, mediaId), onSuccess: refresh });

  if (centerQuery.isPending) return <StatePanel title="Cargando propiedad" message="Preparando su ficha operativa…" />;
  if (centerQuery.isError) return <StatePanel tone="error" title="No pudimos abrir la propiedad" message={centerQuery.error.message} />;

  const center = centerQuery.data;
  const property = center.property;
  const media = mediaQuery.data ?? [];
  const coverMedia = media.find((item) => item.is_cover) ?? media[0];

  return (
    <div className="page-stack detail-page operational-detail">
      <Link className="back-link" to="/properties">← Volver a propiedades</Link>
      <header className="detail-hero detail-hero--operational">
        <div className="detail-hero__cover">
          {coverMedia ? <img src={resolveMediaUrl(coverMedia.url)} alt={`Portada de ${property.title}`} /> : <span>Agrega una foto de portada</span>}
        </div>
        <div className="detail-hero__content">
          <div className="detail-hero__badges">
            <span className={`commercial-badge commercial-badge--${property.commercial_status ?? "draft"}`}>{commercialStatusLabels[property.commercial_status ?? "draft"]}</span>
            <span className="subtle-badge">{property.operation_type === "rent" ? "Arriendo" : "Venta"}</span>
          </div>
          <p className="eyebrow">{property.city} · {property.sector ?? "Sector por confirmar"}</p>
          <h1>{property.title}</h1>
          <strong className="operational-detail__price">{formatPropertyPrice(property)}</strong>
          <p>{property.description}</p>
          <div className="detail-action-row">
            <Link className="button button--primary" to={`/properties/${property.id}/command-center`}>Abrir centro de operación</Link>
            <a className="button button--secondary" href="#media">Gestionar fotos</a>
            <Link className="button button--secondary" to={`/properties/${property.id}/command-center#distribution`}>Contenido y distribución</Link>
          </div>
        </div>
      </header>

      <PropertyEditor property={property} onSaved={refresh} />

      <section className="detail-grid" id="property-facts">
        <article className="panel">
          <p className="eyebrow">Ficha comercial</p><h2>Datos principales</h2>
          <dl className="fact-list">
            <div><dt>Tipo</dt><dd>{property.property_type}</dd></div><div><dt>Dormitorios</dt><dd>{valueOrUnknown(property.bedrooms)}</dd></div>
            <div><dt>Baños</dt><dd>{valueOrUnknown(property.bathrooms)}</dd></div><div><dt>Estacionamientos</dt><dd>{valueOrUnknown(property.parking_spaces)}</dd></div>
            <div><dt>Superficie útil</dt><dd>{valueOrUnknown(property.built_area_m2 ?? property.square_meters, " m²")}</dd></div><div><dt>Terreno</dt><dd>{valueOrUnknown(property.land_area_m2, " m²")}</dd></div>
            <div><dt>Mascotas</dt><dd>{petPolicyLabel[property.pet_policy]}</dd></div><div><dt>Referencia</dt><dd>{property.reference_code ?? "Sin referencia"}</dd></div>
          </dl>
        </article>
        <article className="panel operations-summary-card">
          <p className="eyebrow">Estado operativo</p><h2>Comercialización</h2>
          <dl className="fact-list"><div><dt>Destinos</dt><dd>{center.distribution.length}</dd></div><div><dt>Campañas</dt><dd>{center.campaigns.length}</dd></div><div><dt>Acciones pendientes</dt><dd>{center.next_actions.length}</dd></div><div><dt>Conversaciones</dt><dd>{center.related_conversations.length}</dd></div></dl>
          <Link className="text-link" to={`/properties/${property.id}/command-center`}>Revisar toda la operación →</Link>
        </article>
      </section>

      <section className="panel media-manager" id="media">
        <div className="section-heading"><div><p className="eyebrow">Fotos</p><h2>Material de publicación</h2></div><label className="button button--secondary file-button">+ Agregar fotos<input type="file" accept="image/jpeg,image/png,image/webp" multiple onChange={(event) => upload.mutate(Array.from(event.target.files ?? []))} /></label></div>
        {media.length ? <div className="media-manager__grid">{media.map((item) => <article key={item.id}><img src={resolveMediaUrl(item.url)} alt={item.original_filename} /><div><strong>{item.is_cover ? "Portada" : item.original_filename}</strong><span>Posición {item.position + 1}</span></div><div className="media-manager__actions">{!item.is_cover ? <button type="button" className="text-button" onClick={() => cover.mutate(item.id)}>Usar como portada</button> : null}<button type="button" className="text-button text-button--danger" onClick={() => remove.mutate(item.id)}>Eliminar</button></div></article>)}</div> : <StatePanel title="Sin fotografías" message="Agrega imágenes para preparar el contenido de publicación." />}
        {upload.isError || remove.isError || cover.isError ? <p className="form-alert" role="alert">No pudimos actualizar las fotografías.</p> : null}
      </section>
    </div>
  );
}
