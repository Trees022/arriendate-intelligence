import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { StatePanel } from "../../components/StatePanel";
import {
  approvePublicationPackage,
  createCampaign,
  createProperty,
  createPublicationTarget,
  deletePropertyMedia,
  generatePublicationPackage,
  getPropertyMedia,
  getPublicationTargets,
  reorderPropertyMedia,
  resolveMediaUrl,
  setPropertyCover,
  updateProperty,
  uploadPropertyMedia,
} from "../../lib/api";
import { formatPropertyPrice } from "../../lib/format";
import type {
  ChannelType,
  OperationType,
  Property,
  PropertyCreateInput,
  PublicationPackage,
  PublicationTargetCreate,
} from "../../lib/types";
import { channelLabels } from "../operations/labels";

const steps = ["Propiedad", "Fotos", "Contenido", "Distribución", "Lanzamiento"];

interface PropertyFormState {
  operation_type: OperationType;
  property_type: string;
  title: string;
  reference_code: string;
  description: string;
  price: string;
  city: string;
  sector: string;
  address_text: string;
  bedrooms: string;
  bathrooms: string;
  parking_spaces: string;
  built_area_m2: string;
  land_area_m2: string;
  amenities: string;
  source_notes: string;
  pet_policy: "allowed" | "not_allowed" | "unknown";
  furnished: "yes" | "no" | "unknown";
}

const initialForm: PropertyFormState = {
  operation_type: "rent",
  property_type: "house",
  title: "",
  reference_code: "",
  description: "",
  price: "",
  city: "",
  sector: "",
  address_text: "",
  bedrooms: "",
  bathrooms: "",
  parking_spaces: "",
  built_area_m2: "",
  land_area_m2: "",
  amenities: "",
  source_notes: "",
  pet_policy: "unknown",
  furnished: "unknown",
};

const optionalNumber = (value: string) => value.trim() ? Number(value) : null;

function propertyPayload(form: PropertyFormState): PropertyCreateInput {
  const price = Number(form.price);
  return {
    title: form.title.trim(),
    description: form.description.trim(),
    operation_type: form.operation_type,
    property_type: form.property_type,
    city: form.city.trim(),
    sector: form.sector.trim() || null,
    monthly_price: form.operation_type === "rent" ? price : null,
    sale_price: form.operation_type === "buy" ? price : null,
    currency: "CLP",
    bedrooms: optionalNumber(form.bedrooms),
    bathrooms: optionalNumber(form.bathrooms),
    parking_spaces: optionalNumber(form.parking_spaces),
    pet_policy: form.pet_policy,
    furnished: form.furnished === "unknown" ? null : form.furnished === "yes",
    square_meters: optionalNumber(form.built_area_m2),
    reference_code: form.reference_code.trim() || null,
    source_notes: form.source_notes.trim() || null,
    address_text: form.address_text.trim() || null,
    built_area_m2: optionalNumber(form.built_area_m2),
    land_area_m2: optionalNumber(form.land_area_m2),
    commercial_status: "draft",
    amenities: form.amenities.split(",").map((item) => item.trim()).filter(Boolean),
  };
}

export function NewPropertyWizardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<PropertyFormState>(initialForm);
  const [property, setProperty] = useState<Property | null>(null);
  const [publicationPackage, setPublicationPackage] = useState<PublicationPackage | null>(null);
  const [selectedVariant, setSelectedVariant] = useState<ChannelType | null>(null);
  const [selectedTargets, setSelectedTargets] = useState<string[]>([]);
  const [showTargetForm, setShowTargetForm] = useState(false);
  const [targetName, setTargetName] = useState("");
  const [targetChannel, setTargetChannel] = useState<ChannelType>("facebook_group");
  const [targetUrl, setTargetUrl] = useState("");
  const [targetCooldown, setTargetCooldown] = useState("72");

  const mediaQuery = useQuery({
    queryKey: ["property-media", property?.id],
    queryFn: () => getPropertyMedia(property!.id),
    enabled: Boolean(property),
  });
  const targetsQuery = useQuery({ queryKey: ["publication-targets"], queryFn: () => getPublicationTargets(true) });

  const createPropertyMutation = useMutation({
    mutationFn: () => property
      ? updateProperty(property.id, propertyPayload(form))
      : createProperty(propertyPayload(form)),
    onSuccess: (created) => { setProperty(created); setStep(1); },
  });
  const uploadMutation = useMutation({
    mutationFn: async (files: File[]) => {
      for (const file of files) await uploadPropertyMedia(property!.id, file);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["property-media", property?.id] }),
  });
  const removeMutation = useMutation({
    mutationFn: (mediaId: string) => deletePropertyMedia(property!.id, mediaId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["property-media", property?.id] }),
  });
  const coverMutation = useMutation({
    mutationFn: (mediaId: string) => setPropertyCover(property!.id, mediaId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["property-media", property?.id] }),
  });
  const reorderMutation = useMutation({
    mutationFn: (mediaIds: string[]) => reorderPropertyMedia(property!.id, mediaIds),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["property-media", property?.id] }),
  });
  const packageMutation = useMutation({
    mutationFn: () => generatePublicationPackage(property!.id),
    onSuccess: (generated) => {
      setPublicationPackage(generated);
      setSelectedVariant(generated.variants[0]?.channel_type ?? null);
    },
  });
  const approveMutation = useMutation({
    mutationFn: () => approvePublicationPackage(publicationPackage!.id),
    onSuccess: (approved) => { setPublicationPackage(approved); setStep(3); },
  });
  const targetMutation = useMutation({
    mutationFn: () => {
      const payload: PublicationTargetCreate = {
        name: targetName.trim(),
        channel_type: targetChannel,
        execution_mode: ["facebook_group", "facebook_marketplace"].includes(targetChannel) ? "assisted" : "manual",
        destination_url: targetUrl.trim() || null,
        channel_account_id: null,
        geographic_relevance: property?.city ?? null,
        property_tags: [],
        active: true,
        minimum_repost_interval_hours: Number(targetCooldown),
        notes: "Creado desde el asistente de propiedades.",
      };
      return createPublicationTarget(payload);
    },
    onSuccess: async (target) => {
      setSelectedTargets((current) => [...current, target.id]);
      setTargetName(""); setTargetUrl(""); setShowTargetForm(false);
      await queryClient.invalidateQueries({ queryKey: ["publication-targets"] });
    },
  });
  const launchMutation = useMutation({
    mutationFn: async () => {
      await updateProperty(property!.id, { commercial_status: "active" });
      return createCampaign(property!.id, publicationPackage!.id, selectedTargets);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["operations-workspace"] });
      navigate(`/properties/${property!.id}/command-center`);
    },
  });

  const media = mediaQuery.data ?? [];
  const availableVariantChannels = new Set(publicationPackage?.variants.map((variant) => variant.channel_type) ?? []);
  const availableTargets = (targetsQuery.data ?? []).filter((target) => availableVariantChannels.has(target.channel_type));
  const variant = publicationPackage?.variants.find((item) => item.channel_type === selectedVariant) ?? null;
  const movePhoto = (index: number, offset: number) => {
    const nextIndex = index + offset;
    if (nextIndex < 0 || nextIndex >= media.length) return;
    const ids = media.map((item) => item.id);
    const currentId = ids[index];
    const nextId = ids[nextIndex];
    if (!currentId || !nextId) return;
    ids[index] = nextId;
    ids[nextIndex] = currentId;
    reorderMutation.mutate(ids);
  };
  const currentError = createPropertyMutation.error ?? uploadMutation.error ?? packageMutation.error
    ?? approveMutation.error ?? targetMutation.error ?? launchMutation.error;

  return (
    <div className="page-stack wizard-page">
      <Link className="back-link" to="/properties">← Volver a propiedades</Link>
      <header className="wizard-header">
        <div><p className="eyebrow">Nueva propiedad</p><h1>Prepara una propiedad para comercializar.</h1><p>Completa la ficha, organiza las fotos y lanza su primera campaña sin salir de Arriendate.</p></div>
        <span>Borrador seguro</span>
      </header>

      <ol className="wizard-steps" aria-label="Progreso">
        {steps.map((label, index) => <li className={index === step ? "is-current" : index < step ? "is-complete" : ""} key={label}><span>{index < step ? "✓" : index + 1}</span><strong>{label}</strong></li>)}
      </ol>

      {currentError ? <div className="form-alert" role="alert">{currentError.message}</div> : null}

      {step === 0 ? (
        <form className="wizard-panel" onSubmit={(event) => { event.preventDefault(); createPropertyMutation.mutate(); }}>
          <div className="wizard-panel__heading"><div><span>Paso 1</span><h2>Datos de la propiedad</h2></div><p>Usaremos estos datos para generar contenido fiel a la ficha.</p></div>
          <div className="operation-selector">
            <button type="button" className={form.operation_type === "rent" ? "is-active" : ""} onClick={() => setForm({ ...form, operation_type: "rent" })}>Arriendo</button>
            <button type="button" className={form.operation_type === "buy" ? "is-active" : ""} onClick={() => setForm({ ...form, operation_type: "buy" })}>Venta</button>
          </div>
          <div className="wizard-form-grid">
            <label><span>Tipo de propiedad</span><select value={form.property_type} onChange={(event) => setForm({ ...form, property_type: event.target.value })}><option value="house">Casa</option><option value="apartment">Departamento</option><option value="land">Terreno</option><option value="commercial">Comercial</option><option value="office">Oficina</option></select></label>
            <label><span>Referencia interna</span><input value={form.reference_code} onChange={(event) => setForm({ ...form, reference_code: event.target.value })} placeholder="Ej. CASTRO-024" /></label>
            <label className="wizard-form-grid__wide"><span>Título</span><input value={form.title} onChange={(event) => setForm({ ...form, title: event.target.value })} placeholder="Ej. Casa luminosa en Castro centro" required minLength={3} /></label>
            <label className="wizard-form-grid__wide"><span>Descripción</span><textarea value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} placeholder="Describe sólo características verificables de la propiedad." required minLength={5} rows={4} /></label>
            <label><span>Precio {form.operation_type === "rent" ? "mensual" : "de venta"}</span><input type="number" min="0" value={form.price} onChange={(event) => setForm({ ...form, price: event.target.value })} required placeholder="650000" /></label>
            <label><span>Ciudad</span><input value={form.city} onChange={(event) => setForm({ ...form, city: event.target.value })} required placeholder="Castro" /></label>
            <label><span>Sector</span><input value={form.sector} onChange={(event) => setForm({ ...form, sector: event.target.value })} placeholder="Centro" /></label>
            <label><span>Dirección privada</span><input value={form.address_text} onChange={(event) => setForm({ ...form, address_text: event.target.value })} placeholder="No se publica automáticamente" /></label>
            <label><span>Dormitorios</span><input type="number" min="0" value={form.bedrooms} onChange={(event) => setForm({ ...form, bedrooms: event.target.value })} /></label>
            <label><span>Baños</span><input type="number" min="0" value={form.bathrooms} onChange={(event) => setForm({ ...form, bathrooms: event.target.value })} /></label>
            <label><span>Estacionamientos</span><input type="number" min="0" value={form.parking_spaces} onChange={(event) => setForm({ ...form, parking_spaces: event.target.value })} /></label>
            <label><span>Superficie construida m²</span><input type="number" min="1" step="0.01" value={form.built_area_m2} onChange={(event) => setForm({ ...form, built_area_m2: event.target.value })} /></label>
            <label><span>Terreno m²</span><input type="number" min="1" step="0.01" value={form.land_area_m2} onChange={(event) => setForm({ ...form, land_area_m2: event.target.value })} /></label>
            <label><span>Mascotas</span><select value={form.pet_policy} onChange={(event) => setForm({ ...form, pet_policy: event.target.value as PropertyFormState["pet_policy"] })}><option value="unknown">Por confirmar</option><option value="allowed">Permitidas</option><option value="not_allowed">No permitidas</option></select></label>
            <label><span>Amoblada</span><select value={form.furnished} onChange={(event) => setForm({ ...form, furnished: event.target.value as PropertyFormState["furnished"] })}><option value="unknown">Por confirmar</option><option value="yes">Sí</option><option value="no">No</option></select></label>
            <label className="wizard-form-grid__wide"><span>Características, separadas por coma</span><input value={form.amenities} onChange={(event) => setForm({ ...form, amenities: event.target.value })} placeholder="Patio, bodega, calefacción" /></label>
            <label className="wizard-form-grid__wide"><span>Notas internas</span><textarea value={form.source_notes} onChange={(event) => setForm({ ...form, source_notes: event.target.value })} rows={3} placeholder="Información para el equipo; no se publica." /></label>
          </div>
          <div className="wizard-actions"><span>La propiedad se guardará como borrador.</span><button className="button button--primary" type="submit" disabled={createPropertyMutation.isPending}>{createPropertyMutation.isPending ? "Guardando…" : "Guardar y continuar"}</button></div>
        </form>
      ) : null}

      {step === 1 && property ? (
        <section className="wizard-panel">
          <div className="wizard-panel__heading"><div><span>Paso 2</span><h2>Fotografías</h2></div><p>La primera foto será la portada. Puedes cambiar el orden antes de generar contenido.</p></div>
          <label className="photo-dropzone"><input type="file" multiple accept="image/jpeg,image/png,image/webp" onChange={(event) => uploadMutation.mutate(Array.from(event.target.files ?? []))} /><strong>{uploadMutation.isPending ? "Subiendo fotografías…" : "+ Seleccionar fotografías"}</strong><span>JPG, PNG o WebP · puedes elegir varias</span></label>
          {media.length ? <div className="wizard-media-grid">{media.map((item, index) => <article key={item.id}><div className="wizard-media-grid__image"><img src={resolveMediaUrl(item.url)} alt={item.original_filename} /><span>{item.is_cover ? "Portada" : index + 1}</span></div><strong>{item.original_filename}</strong><div><button type="button" onClick={() => movePhoto(index, -1)} disabled={index === 0 || reorderMutation.isPending} aria-label={`Mover ${item.original_filename} hacia atrás`}>←</button><button type="button" onClick={() => movePhoto(index, 1)} disabled={index === media.length - 1 || reorderMutation.isPending} aria-label={`Mover ${item.original_filename} hacia adelante`}>→</button>{!item.is_cover ? <button type="button" onClick={() => coverMutation.mutate(item.id)}>Portada</button> : null}<button type="button" className="is-danger" onClick={() => removeMutation.mutate(item.id)}>Eliminar</button></div></article>)}</div> : <StatePanel title="Aún no hay fotos" message="Agrega al menos una fotografía para continuar con el contenido comercial." />}
          <div className="wizard-actions"><button className="button button--secondary" type="button" onClick={() => setStep(0)}>Atrás</button><button className="button button--primary" type="button" disabled={!media.length || uploadMutation.isPending} onClick={() => setStep(2)}>Continuar con contenido</button></div>
        </section>
      ) : null}

      {step === 2 && property ? (
        <section className="wizard-panel">
          <div className="wizard-panel__heading"><div><span>Paso 3</span><h2>Contenido de publicación</h2></div><p>Generamos variantes desde la ficha y las fotos. Revisa antes de aprobar.</p></div>
          {!publicationPackage ? <div className="generation-callout"><div><strong>Ficha lista para generar</strong><p>{property.title} · {media.length} fotos · {formatPropertyPrice(property)}</p></div><button className="button button--primary" type="button" onClick={() => packageMutation.mutate()} disabled={packageMutation.isPending}>{packageMutation.isPending ? "Generando…" : "Generar contenido"}</button></div> : (
            <div className="package-review">
              <div className="variant-tabs" role="tablist">{publicationPackage.variants.map((item) => <button type="button" role="tab" aria-selected={selectedVariant === item.channel_type} className={selectedVariant === item.channel_type ? "is-active" : ""} key={item.id} onClick={() => setSelectedVariant(item.channel_type)}>{channelLabels[item.channel_type] ?? item.channel_type}</button>)}</div>
              {variant ? <article className="variant-review"><div><span>Vista previa</span><h3>{variant.headline}</h3><p>{variant.body}</p><strong>{variant.cta}</strong></div><aside><h4>Datos utilizados</h4><ul>{variant.highlights.map((highlight) => <li key={highlight}>{highlight}</li>)}</ul><h4>Revisiones</h4>{variant.warnings.length ? <ul className="warning-list">{variant.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : <p>Sin advertencias para este canal.</p>}</aside></article> : null}
            </div>
          )}
          <div className="wizard-actions"><button className="button button--secondary" type="button" onClick={() => setStep(1)}>Atrás</button><button className="button button--primary" type="button" disabled={!publicationPackage || approveMutation.isPending} onClick={() => approveMutation.mutate()}>{approveMutation.isPending ? "Aprobando…" : "Aprobar contenido y continuar"}</button></div>
        </section>
      ) : null}

      {step === 3 && property && publicationPackage ? (
        <section className="wizard-panel">
          <div className="wizard-panel__heading"><div><span>Paso 4</span><h2>Destinos de publicación</h2></div><p>Selecciona dónde se comercializará. Marketplace y grupos funcionan sin OAuth mediante flujo asistido.</p></div>
          {targetsQuery.isPending ? <StatePanel title="Cargando destinos" message="Buscando canales disponibles…" /> : null}
          <div className="target-selection">{availableTargets.map((target) => { const checked = selectedTargets.includes(target.id); return <label className={checked ? "is-selected" : ""} key={target.id}><input type="checkbox" checked={checked} onChange={() => setSelectedTargets((current) => checked ? current.filter((id) => id !== target.id) : [...current, target.id])} /><span className="channel-mark">{channelLabels[target.channel_type]?.slice(0, 2)}</span><span><strong>{target.name}</strong><small>{channelLabels[target.channel_type]} · {target.execution_mode === "api" ? "Conexión oficial" : "Asistido"}</small></span><span><strong>{target.minimum_repost_interval_hours} h</strong><small>espera mínima</small></span></label>; })}</div>
          <button className="text-link target-add-trigger" type="button" onClick={() => setShowTargetForm((value) => !value)}>+ Agregar destino reutilizable</button>
          {showTargetForm ? <form className="target-create-form" onSubmit={(event) => { event.preventDefault(); targetMutation.mutate(); }}><label><span>Nombre</span><input value={targetName} onChange={(event) => setTargetName(event.target.value)} required minLength={2} placeholder="Ej. Corredores de Castro" /></label><label><span>Canal</span><select value={targetChannel} onChange={(event) => setTargetChannel(event.target.value as ChannelType)}><option value="facebook_group">Grupo de Facebook</option><option value="facebook_marketplace">Marketplace</option><option value="portal_inmobiliario">Portal</option><option value="yapo">Yapo</option><option value="generic">Otro canal</option></select></label><label><span>URL del destino</span><input type="url" value={targetUrl} onChange={(event) => setTargetUrl(event.target.value)} placeholder="https://…" /></label><label><span>Espera mínima (horas)</span><input type="number" min="0" value={targetCooldown} onChange={(event) => setTargetCooldown(event.target.value)} required /></label><button className="button button--secondary" type="submit" disabled={targetMutation.isPending}>{targetMutation.isPending ? "Guardando…" : "Guardar destino"}</button></form> : null}
          <div className="wizard-actions"><button className="button button--secondary" type="button" onClick={() => setStep(2)}>Atrás</button><span>{selectedTargets.length} destinos seleccionados</span><button className="button button--primary" type="button" disabled={!selectedTargets.length} onClick={() => setStep(4)}>Revisar lanzamiento</button></div>
        </section>
      ) : null}

      {step === 4 && property && publicationPackage ? (
        <section className="wizard-panel launch-review">
          <div className="wizard-panel__heading"><div><span>Paso 5</span><h2>Todo listo para lanzar</h2></div><p>Activaremos la propiedad y crearemos trabajos para cada destino.</p></div>
          <div className="launch-summary"><article><span>Propiedad</span><strong>{property.title}</strong><small>{property.city} · {formatPropertyPrice(property)}</small></article><article><span>Fotos</span><strong>{media.length}</strong><small>{media.find((item) => item.is_cover)?.original_filename ?? "Portada preparada"}</small></article><article><span>Contenido</span><strong>{publicationPackage.variants.length} variantes</strong><small>Paquete aprobado</small></article><article><span>Distribución</span><strong>{selectedTargets.length} destinos</strong><small>Se crearán trabajos listos</small></article></div>
          <div className="launch-note"><strong>Qué ocurrirá ahora</strong><p>Arriendate abrirá el centro de operación. Los destinos asistidos quedarán listos para copiar, abrir y marcar como publicados.</p></div>
          <div className="wizard-actions"><button className="button button--secondary" type="button" onClick={() => setStep(3)}>Atrás</button><button className="button button--primary" type="button" disabled={launchMutation.isPending} onClick={() => launchMutation.mutate()}>{launchMutation.isPending ? "Creando campaña…" : "Activar propiedad y lanzar campaña"}</button></div>
        </section>
      ) : null}
    </div>
  );
}
