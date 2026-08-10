import type {
  MissingInformation,
  RequestedOperation,
  RequestedPropertyType,
  LeadRequirements,
} from "../../lib/types";

const operationLabels: Record<RequestedOperation, string> = {
  rent: "Arriendo",
  buy: "Compra",
  unknown: "Por confirmar",
};

const propertyTypeLabels: Record<RequestedPropertyType, string> = {
  apartment: "Departamento",
  house: "Casa",
  studio: "Estudio",
  loft: "Loft",
  townhouse: "Townhouse",
  land: "Terreno",
  commercial: "Local comercial",
  office: "Oficina",
};

const missingLabels: Record<MissingInformation, string> = {
  operation_type: "Tipo de operación",
  property_type: "Tipo de propiedad",
  location: "Ubicación",
  budget: "Presupuesto",
  currency: "Moneda",
  bedrooms: "Dormitorios",
  bathrooms: "Baños",
  parking: "Estacionamiento",
  pets: "Mascotas",
  furnished: "Amoblado",
  contradictory_requirements: "Requisitos contradictorios",
  unverifiable_preference: "Preferencia no verificable",
};

function booleanRequirement(value: boolean | null): string {
  if (value === null) return "No informado";
  return value ? "Requerido" : "No es requisito";
}

function formatBudget(requirements: LeadRequirements): string {
  if (requirements.max_budget === null) return "No informado";
  const formatted = new Intl.NumberFormat("es-CL", { maximumFractionDigits: 0 }).format(
    requirements.max_budget,
  );
  return requirements.currency ? `${requirements.currency} ${formatted}` : formatted;
}

function listOrUnknown(values: string[]): string {
  return values.length ? values.join(", ") : "No informado";
}

interface RequirementsPanelProps {
  requirements: LeadRequirements;
  processing: boolean;
  onReprocess: () => void;
}

export function RequirementsPanel({ requirements, processing, onReprocess }: RequirementsPanelProps) {
  const confidence = Math.round(requirements.extraction_confidence * 100);

  return (
    <section className="panel requirements-panel">
      <div className="panel__heading requirements-panel__heading">
        <div>
          <p className="eyebrow">Salida validada</p>
          <h2>Requisitos estructurados</h2>
          <p>Datos extraídos del mensaje original; los valores desconocidos permanecen visibles.</p>
        </div>
        <button className="button button--secondary" type="button" onClick={onReprocess} disabled={processing}>
          {processing ? "Procesando…" : "Reprocesar"}
        </button>
      </div>

      <dl className="requirements-grid">
        <div><dt>Operación</dt><dd>{operationLabels[requirements.operation_type]}</dd></div>
        <div>
          <dt>Propiedad</dt>
          <dd>{listOrUnknown(requirements.property_types.map((value) => propertyTypeLabels[value]))}</dd>
        </div>
        <div><dt>Ubicaciones</dt><dd>{listOrUnknown(requirements.locations)}</dd></div>
        <div><dt>Presupuesto máximo</dt><dd>{formatBudget(requirements)}</dd></div>
        <div><dt>Dormitorios mínimos</dt><dd>{requirements.min_bedrooms ?? "No informado"}</dd></div>
        <div><dt>Baños mínimos</dt><dd>{requirements.min_bathrooms ?? "No informado"}</dd></div>
        <div><dt>Estacionamiento</dt><dd>{booleanRequirement(requirements.parking_required)}</dd></div>
        <div><dt>Mascotas</dt><dd>{booleanRequirement(requirements.pets_required)}</dd></div>
        <div><dt>Amoblado</dt><dd>{booleanRequirement(requirements.furnished_preference)}</dd></div>
      </dl>

      <div className="confidence-block">
        <div>
          <span>Confianza de extracción</span>
          <strong>{confidence}%</strong>
        </div>
        <div className="confidence-track" aria-label={`Confianza ${confidence}%`}>
          <span style={{ width: `${confidence}%` }} />
        </div>
      </div>

      <div className="requirements-lists">
        <div>
          <h3>Preferencias suaves</h3>
          {requirements.soft_preferences.length ? (
            <ul className="tag-list">
              {requirements.soft_preferences.map((preference) => <li key={preference}>{preference}</li>)}
            </ul>
          ) : <p className="unknown-copy">No se declararon preferencias adicionales.</p>}
        </div>
        <div>
          <h3>Información pendiente</h3>
          {requirements.missing_information.length ? (
            <ul className="warning-list">
              {requirements.missing_information.map((item) => <li key={item}>{missingLabels[item]}</li>)}
            </ul>
          ) : <p className="complete-copy">No se detectaron ausencias críticas.</p>}
        </div>
      </div>
    </section>
  );
}
