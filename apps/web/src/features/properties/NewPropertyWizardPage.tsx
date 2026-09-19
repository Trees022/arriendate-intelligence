import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { StatePanel } from "../../components/StatePanel";
import {
  approvePublicationPackage,
  autofillProperty,
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
  Property,
  PublicationPackage,
  PublicationTargetCreate,
  WizardPropertyType,
} from "../../lib/types";
import { channelLabels } from "../operations/labels";
import {
  type AutofillConflict,
  formatChileanInteger,
  formatSurfaceInput,
  initialPropertyForm,
  mergeAutofillDraft,
  normalizeChileanInteger,
  normalizeSurfaceInput,
  propertyFieldLabels,
  propertyPayload,
  propertyTypeOptions,
  relevantFields,
  sanitizeFormForPropertyType,
  type PropertyFormField,
  type PropertyFormState,
} from "./propertyWizard";

const steps = ["Datos", "Fotos", "Publicación", "Destinos"];

interface AutofillReview {
  appliedFields: PropertyFormField[];
  reviewFields: string[];
  conflicts: AutofillConflict[];
}

function unique<T>(items: T[]): T[] {
  return [...new Set(items)];
}

export function NewPropertyWizardPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [step, setStep] = useState(0);
  const [form, setForm] = useState<PropertyFormState>(initialPropertyForm);
  const [manuallyEdited, setManuallyEdited] = useState<Set<PropertyFormField>>(new Set());
  const [sourceText, setSourceText] = useState("");
  const [autofillReview, setAutofillReview] = useState<AutofillReview | null>(null);
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
  const targetsQuery = useQuery({
    queryKey: ["publication-targets"],
    queryFn: () => getPublicationTargets(true),
  });

  const autofillMutation = useMutation({
    mutationFn: () => autofillProperty(sourceText),
    onSuccess: (result) => {
      const merged = mergeAutofillDraft(form, result.draft, manuallyEdited);
      setForm(merged.form);
      setAutofillReview({
        appliedFields: merged.appliedFields,
        reviewFields: result.review_fields,
        conflicts: merged.conflicts,
      });
    },
  });
  const createPropertyMutation = useMutation({
    mutationFn: () =>
      property
        ? updateProperty(property.id, propertyPayload(form))
        : createProperty(propertyPayload(form)),
    onSuccess: (created) => {
      setProperty(created);
      setStep(1);
    },
  });
  const uploadMutation = useMutation({
    mutationFn: async (files: File[]) => {
      for (const file of files) await uploadPropertyMedia(property!.id, file);
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["property-media", property?.id] }),
  });
  const removeMutation = useMutation({
    mutationFn: (mediaId: string) => deletePropertyMedia(property!.id, mediaId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["property-media", property?.id] }),
  });
  const coverMutation = useMutation({
    mutationFn: (mediaId: string) => setPropertyCover(property!.id, mediaId),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["property-media", property?.id] }),
  });
  const reorderMutation = useMutation({
    mutationFn: (mediaIds: string[]) => reorderPropertyMedia(property!.id, mediaIds),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["property-media", property?.id] }),
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
    onSuccess: (approved) => {
      setPublicationPackage(approved);
      setStep(3);
    },
  });
  const targetMutation = useMutation({
    mutationFn: () => {
      const payload: PublicationTargetCreate = {
        name: targetName.trim(),
        channel_type: targetChannel,
        execution_mode: ["facebook_group", "facebook_marketplace"].includes(targetChannel)
          ? "assisted"
          : "manual",
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
      setTargetName("");
      setTargetUrl("");
      setShowTargetForm(false);
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
  const relevant = relevantFields(form.property_type);
  const availableVariantChannels = new Set(
    publicationPackage?.variants.map((variant) => variant.channel_type) ?? [],
  );
  const availableTargets = (targetsQuery.data ?? []).filter((target) =>
    availableVariantChannels.has(target.channel_type),
  );
  const variant =
    publicationPackage?.variants.find((item) => item.channel_type === selectedVariant) ??
    null;
  const currentError =
    createPropertyMutation.error ??
    uploadMutation.error ??
    packageMutation.error ??
    approveMutation.error ??
    targetMutation.error ??
    launchMutation.error;

  const editField = <Field extends PropertyFormField>(
    field: Field,
    value: PropertyFormState[Field],
  ) => {
    setForm((current) =>
      field === "property_type"
        ? sanitizeFormForPropertyType(current, value as WizardPropertyType)
        : ({ ...current, [field]: value } as PropertyFormState),
    );
    setManuallyEdited((current) => new Set(current).add(field));
    setAutofillReview((current) =>
      current
        ? { ...current, conflicts: current.conflicts.filter((item) => item.field !== field) }
        : null,
    );
  };
  const applySuggestion = (conflict: AutofillConflict) => {
    setForm((current) =>
      conflict.field === "property_type"
        ? sanitizeFormForPropertyType(current, conflict.suggested as WizardPropertyType)
        : ({ ...current, [conflict.field]: conflict.suggested } as PropertyFormState),
    );
    setManuallyEdited((current) => new Set(current).add(conflict.field));
    setAutofillReview((current) =>
      current
        ? {
            ...current,
            appliedFields: unique([...current.appliedFields, conflict.field]),
            conflicts: current.conflicts.filter((item) => item.field !== conflict.field),
          }
        : null,
    );
  };
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

  return (
    <div className="page-stack wizard-page">
      <Link className="back-link" to="/properties">
        ← Propiedades
      </Link>
      <header className="wizard-header">
        <div>
          <p className="eyebrow">Nueva propiedad</p>
          <h1>Prepara una propiedad.</h1>
          <p>Ingresa los datos esenciales y comienza a publicarla.</p>
        </div>
        <span>Borrador</span>
      </header>

      <ol className="wizard-steps" aria-label="Progreso del registro">
        {steps.map((label, index) => (
          <li
            className={index === step ? "is-current" : index < step ? "is-complete" : ""}
            key={label}
            aria-current={index === step ? "step" : undefined}
          >
            <span>{index < step ? "✓" : index + 1}</span>
            <strong>{label}</strong>
          </li>
        ))}
      </ol>

      {currentError ? <div className="form-alert" role="alert">{currentError.message}</div> : null}

      {step === 0 ? (
        <form
          className="wizard-panel"
          onSubmit={(event) => {
            event.preventDefault();
            createPropertyMutation.mutate();
          }}
        >
          <div className="wizard-panel__heading">
            <div>
              <span>Paso 1</span>
              <h2>Datos principales</h2>
            </div>
          </div>

          <section className="autofill-card" aria-labelledby="autofill-title">
            <div className="autofill-card__heading">
              <div>
                <span className="ai-mark">AI</span>
                <div>
                  <h3 id="autofill-title">Autocompletar con IA</h3>
                  <p>Pega el mensaje que recibiste sobre la propiedad.</p>
                </div>
              </div>
              <span>Opcional</span>
            </div>
            <label>
              <span className="sr-only">Información de la propiedad</span>
              <textarea
                value={sourceText}
                onChange={(event) => setSourceText(event.target.value)}
                placeholder="Ej. Se arrienda departamento en Castro, 2 dormitorios, $700.000…"
                rows={4}
              />
            </label>
            <div className="autofill-card__action">
              <small>Solo completaremos datos presentes en el texto.</small>
              <button
                className="button button--secondary"
                type="button"
                disabled={sourceText.trim().length < 20 || autofillMutation.isPending}
                onClick={() => autofillMutation.mutate()}
              >
                {autofillMutation.isPending ? "Leyendo…" : "Autocompletar con IA"}
              </button>
            </div>
            {autofillMutation.isError ? (
              <div className="form-alert" role="alert">{autofillMutation.error.message}</div>
            ) : null}
            {autofillReview ? (
              <div className="autofill-review" role="status">
                {autofillReview.appliedFields.length ? (
                  <div>
                    <strong>Completado</strong>
                    <p>
                      {unique(autofillReview.appliedFields)
                        .map((field) => propertyFieldLabels[field] ?? field)
                        .join(" · ")}
                    </p>
                  </div>
                ) : null}
                {autofillReview.reviewFields.length ? (
                  <div>
                    <strong>Revisa o completa</strong>
                    <p>
                      {autofillReview.reviewFields
                        .map((field) =>
                          propertyFieldLabels[field as PropertyFormField] ?? field,
                        )
                        .join(" · ")}
                    </p>
                  </div>
                ) : null}
                {autofillReview.conflicts.map((conflict) => (
                  <div className="autofill-conflict" key={conflict.field}>
                    <span>
                      <strong>{propertyFieldLabels[conflict.field] ?? conflict.field}</strong>
                      Ya habías escrito “{conflict.current || "vacío"}”.
                    </span>
                    <button type="button" onClick={() => applySuggestion(conflict)}>
                      Usar “{conflict.suggested}”
                    </button>
                  </div>
                ))}
              </div>
            ) : null}
          </section>

          <div className="operation-selector" aria-label="Operación">
            <button
              type="button"
              className={form.operation_type === "rent" ? "is-active" : ""}
              onClick={() => editField("operation_type", "rent")}
            >
              Arriendo
            </button>
            <button
              type="button"
              className={form.operation_type === "buy" ? "is-active" : ""}
              onClick={() => editField("operation_type", "buy")}
            >
              Venta
            </button>
          </div>

          <div className="wizard-form-grid wizard-form-grid--essential">
            <label>
              <span>Tipo de propiedad</span>
              <select
                value={form.property_type}
                onChange={(event) =>
                  editField("property_type", event.target.value as WizardPropertyType)
                }
              >
                {propertyTypeOptions.map((option) => (
                  <option value={option.value} key={option.value}>{option.label}</option>
                ))}
              </select>
            </label>
            <label className="wizard-form-grid__wide">
              <span>Título</span>
              <input
                value={form.title}
                onChange={(event) => editField("title", event.target.value)}
                placeholder="Ej. Departamento en Castro centro"
                required
                minLength={3}
              />
            </label>
            <label>
              <span>Comuna o ciudad</span>
              <input
                value={form.city}
                onChange={(event) => editField("city", event.target.value)}
                required
                placeholder="Castro"
              />
            </label>
            <label>
              <span>{form.operation_type === "rent" ? "Precio mensual" : "Precio de venta"}</span>
              <span className="money-input">
                <select
                  aria-label="Moneda"
                  value={form.currency}
                  onChange={(event) =>
                    editField("currency", event.target.value as PropertyFormState["currency"])
                  }
                >
                  <option value="CLP">$</option>
                  <option value="UF">UF</option>
                  <option value="USD">USD</option>
                </select>
                <input
                  aria-label="Precio"
                  type="text"
                  inputMode="numeric"
                  autoComplete="off"
                  value={formatChileanInteger(form.price)}
                  onChange={(event) => editField("price", normalizeChileanInteger(event.target.value))}
                  required
                  placeholder="700.000"
                />
              </span>
            </label>
          </div>

          <details className="wizard-more-details">
            <summary>Más detalles</summary>
            <div className="wizard-form-grid">
              <label>
                <span>Sector</span>
                <input value={form.sector} onChange={(event) => editField("sector", event.target.value)} placeholder="Centro" />
              </label>
              <label>
                <span>Referencia interna</span>
                <input value={form.reference_code} onChange={(event) => editField("reference_code", event.target.value)} placeholder="CASTRO-024" />
              </label>
              <label>
                <span>Dirección</span>
                <input value={form.address_text} onChange={(event) => editField("address_text", event.target.value)} placeholder="Uso interno" />
              </label>
              {relevant.has("bedrooms") ? (
                <label>
                  <span>Dormitorios</span>
                  <input aria-label="Dormitorios" type="text" inputMode="numeric" value={form.bedrooms} onChange={(event) => editField("bedrooms", normalizeChileanInteger(event.target.value))} />
                </label>
              ) : null}
              {relevant.has("bathrooms") ? (
                <label>
                  <span>Baños</span>
                  <input aria-label="Baños" type="text" inputMode="numeric" value={form.bathrooms} onChange={(event) => editField("bathrooms", normalizeChileanInteger(event.target.value))} />
                </label>
              ) : null}
              {relevant.has("parking_spaces") ? (
                <label>
                  <span>Estacionamientos</span>
                  <input aria-label="Estacionamientos" type="text" inputMode="numeric" value={form.parking_spaces} onChange={(event) => editField("parking_spaces", normalizeChileanInteger(event.target.value))} />
                </label>
              ) : null}
              {relevant.has("built_area_m2") ? (
                <label>
                  <span>Superficie construida (m²)</span>
                  <input aria-label="Superficie construida" type="text" inputMode="decimal" value={formatSurfaceInput(form.built_area_m2)} onChange={(event) => editField("built_area_m2", normalizeSurfaceInput(event.target.value))} placeholder="85" />
                </label>
              ) : null}
              {relevant.has("land_area_m2") ? (
                <label>
                  <span>Superficie de terreno (m²)</span>
                  <input aria-label="Superficie de terreno" type="text" inputMode="decimal" value={formatSurfaceInput(form.land_area_m2)} onChange={(event) => editField("land_area_m2", normalizeSurfaceInput(event.target.value))} placeholder="5.000" />
                </label>
              ) : null}
              {relevant.has("pet_policy") ? (
                <label>
                  <span>Mascotas</span>
                  <select value={form.pet_policy} onChange={(event) => editField("pet_policy", event.target.value as PropertyFormState["pet_policy"])}>
                    <option value="unknown">Por confirmar</option>
                    <option value="allowed">Permitidas</option>
                    <option value="not_allowed">No permitidas</option>
                  </select>
                </label>
              ) : null}
              {relevant.has("furnished") ? (
                <label>
                  <span>Amoblado</span>
                  <select value={form.furnished} onChange={(event) => editField("furnished", event.target.value as PropertyFormState["furnished"])}>
                    <option value="unknown">Por confirmar</option>
                    <option value="yes">Sí</option>
                    <option value="no">No</option>
                  </select>
                </label>
              ) : null}
              <label className="wizard-form-grid__wide">
                <span>Características</span>
                <input value={form.amenities} onChange={(event) => editField("amenities", event.target.value)} placeholder="Patio, bodega, calefacción" />
              </label>
              <label className="wizard-form-grid__wide">
                <span>Descripción</span>
                <textarea value={form.description} onChange={(event) => editField("description", event.target.value)} placeholder="Información adicional para la publicación" rows={3} />
              </label>
              <label className="wizard-form-grid__wide">
                <span>Notas internas</span>
                <textarea value={form.source_notes} onChange={(event) => editField("source_notes", event.target.value)} rows={2} placeholder="No se publican" />
              </label>
            </div>
          </details>

          <div className="wizard-actions">
            <button className="button button--primary" type="submit" disabled={createPropertyMutation.isPending}>
              {createPropertyMutation.isPending ? "Guardando…" : "Guardar y seguir"}
            </button>
          </div>
        </form>
      ) : null}

      {step === 1 && property ? (
        <section className="wizard-panel">
          <div className="wizard-panel__heading"><div><span>Paso 2</span><h2>Fotos</h2></div></div>
          <label className="photo-dropzone">
            <input type="file" multiple accept="image/jpeg,image/png,image/webp" onChange={(event) => uploadMutation.mutate(Array.from(event.target.files ?? []))} />
            <strong>{uploadMutation.isPending ? "Subiendo…" : "+ Agregar fotos"}</strong>
            <span>La primera será la portada</span>
          </label>
          {media.length ? (
            <div className="wizard-media-grid">
              {media.map((item, index) => (
                <article key={item.id}>
                  <div className="wizard-media-grid__image"><img src={resolveMediaUrl(item.url)} alt={item.original_filename} /><span>{item.is_cover ? "Portada" : index + 1}</span></div>
                  <strong>{item.original_filename}</strong>
                  <div>
                    <button type="button" onClick={() => movePhoto(index, -1)} disabled={index === 0 || reorderMutation.isPending} aria-label={`Mover ${item.original_filename} hacia atrás`}>←</button>
                    <button type="button" onClick={() => movePhoto(index, 1)} disabled={index === media.length - 1 || reorderMutation.isPending} aria-label={`Mover ${item.original_filename} hacia adelante`}>→</button>
                    {!item.is_cover ? <button type="button" onClick={() => coverMutation.mutate(item.id)}>Portada</button> : null}
                    <button type="button" className="is-danger" onClick={() => removeMutation.mutate(item.id)}>Eliminar</button>
                  </div>
                </article>
              ))}
            </div>
          ) : <StatePanel title="Agrega al menos una foto" message="Puedes seleccionar varias a la vez." />}
          <div className="wizard-actions">
            <button className="button button--secondary" type="button" onClick={() => setStep(0)}>Atrás</button>
            <button className="button button--primary" type="button" disabled={!media.length || uploadMutation.isPending} onClick={() => setStep(2)}>Seguir a publicación</button>
          </div>
        </section>
      ) : null}

      {step === 2 && property ? (
        <section className="wizard-panel">
          <div className="wizard-panel__heading"><div><span>Paso 3</span><h2>Publicación</h2></div></div>
          {!publicationPackage ? (
            <div className="generation-callout">
              <div><strong>{property.title}</strong><p>{media.length} fotos · {formatPropertyPrice(property)}</p></div>
              <button className="button button--primary" type="button" onClick={() => packageMutation.mutate()} disabled={packageMutation.isPending}>{packageMutation.isPending ? "Generando…" : "Generar publicación"}</button>
            </div>
          ) : (
            <div className="package-review">
              <div className="variant-tabs" role="tablist">
                {publicationPackage.variants.map((item) => (
                  <button type="button" role="tab" aria-selected={selectedVariant === item.channel_type} className={selectedVariant === item.channel_type ? "is-active" : ""} key={item.id} onClick={() => setSelectedVariant(item.channel_type)}>{channelLabels[item.channel_type] ?? item.channel_type}</button>
                ))}
              </div>
              {variant ? (
                <article className="variant-review">
                  <div><span>Vista previa</span><h3>{variant.headline}</h3><p>{variant.body}</p><strong>{variant.cta}</strong></div>
                  <aside><h4>Datos destacados</h4><ul>{variant.highlights.map((highlight) => <li key={highlight}>{highlight}</li>)}</ul>{variant.warnings.length ? <><h4>Antes de publicar</h4><ul className="warning-list">{variant.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul></> : null}</aside>
                </article>
              ) : null}
            </div>
          )}
          <div className="wizard-actions">
            <button className="button button--secondary" type="button" onClick={() => setStep(1)}>Atrás</button>
            {publicationPackage ? <button className="button button--primary" type="button" disabled={approveMutation.isPending} onClick={() => approveMutation.mutate()}>{approveMutation.isPending ? "Guardando…" : "Aprobar y seguir"}</button> : null}
          </div>
        </section>
      ) : null}

      {step === 3 && property && publicationPackage ? (
        <section className="wizard-panel">
          <div className="wizard-panel__heading"><div><span>Paso 4</span><h2>Destinos</h2></div></div>
          {targetsQuery.isPending ? <StatePanel title="Cargando destinos" message="Un momento…" /> : null}
          <div className="target-selection">
            {availableTargets.map((target) => {
              const checked = selectedTargets.includes(target.id);
              const method = target.execution_mode === "api" ? "Cuenta conectada" : target.execution_mode === "assisted" ? "Publicación guiada" : "Manual";
              return (
                <label className={checked ? "is-selected" : ""} key={target.id}>
                  <input type="checkbox" checked={checked} onChange={() => setSelectedTargets((current) => checked ? current.filter((id) => id !== target.id) : [...current, target.id])} />
                  <span className="channel-mark">{channelLabels[target.channel_type]?.slice(0, 2)}</span>
                  <span><strong>{target.name}</strong><small>{channelLabels[target.channel_type]} · {method}</small></span>
                  <span><strong>{target.minimum_repost_interval_hours} h</strong><small>entre publicaciones</small></span>
                </label>
              );
            })}
          </div>
          <button className="text-link target-add-trigger" type="button" onClick={() => setShowTargetForm((value) => !value)}>+ Agregar destino</button>
          {showTargetForm ? (
            <form className="target-create-form" onSubmit={(event) => { event.preventDefault(); targetMutation.mutate(); }}>
              <label><span>Nombre</span><input value={targetName} onChange={(event) => setTargetName(event.target.value)} required minLength={2} placeholder="Ej. Corredores de Castro" /></label>
              <label><span>Canal</span><select value={targetChannel} onChange={(event) => setTargetChannel(event.target.value as ChannelType)}><option value="facebook_group">Grupo de Facebook</option><option value="facebook_marketplace">Marketplace</option><option value="portal_inmobiliario">Portal</option><option value="yapo">Yapo</option><option value="generic">Otro canal</option></select></label>
              <label><span>Enlace</span><input type="url" value={targetUrl} onChange={(event) => setTargetUrl(event.target.value)} placeholder="https://…" /></label>
              <label><span>Horas antes de republicar</span><input type="text" inputMode="numeric" value={targetCooldown} onChange={(event) => setTargetCooldown(normalizeChileanInteger(event.target.value))} required /></label>
              <button className="button button--secondary" type="submit" disabled={targetMutation.isPending}>{targetMutation.isPending ? "Guardando…" : "Guardar destino"}</button>
            </form>
          ) : null}
          <div className="launch-strip">
            <span><strong>{media.length}</strong> fotos</span>
            <span><strong>{publicationPackage.variants.length}</strong> versiones</span>
            <span><strong>{selectedTargets.length}</strong> destinos</span>
          </div>
          <div className="wizard-actions">
            <button className="button button--secondary" type="button" onClick={() => setStep(2)}>Atrás</button>
            <button className="button button--primary" type="button" disabled={!selectedTargets.length || launchMutation.isPending} onClick={() => launchMutation.mutate()}>{launchMutation.isPending ? "Iniciando…" : "Iniciar campaña"}</button>
          </div>
        </section>
      ) : null}
    </div>
  );
}
