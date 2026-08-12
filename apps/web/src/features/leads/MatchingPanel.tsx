import { Link } from "react-router-dom";
import { formatPropertyPrice, knownNumber } from "../../lib/format";
import type { LeadMatches } from "../../lib/types";

const constraintLabels: Record<string, string> = {
  availability: "disponibilidad",
  operation_type: "operación",
  property_type: "tipo de propiedad",
  location: "ubicación",
  currency: "moneda",
  max_budget: "presupuesto máximo",
  min_bedrooms: "dormitorios mínimos",
  min_bathrooms: "baños mínimos",
  parking_required: "estacionamiento obligatorio",
  pets_required: "mascotas obligatorias",
};

interface MatchingPanelProps {
  matches: LeadMatches | undefined;
  loading: boolean;
  generating: boolean;
  error: string | null;
  onGenerate: () => void;
}

export function MatchingPanel({
  matches,
  loading,
  generating,
  error,
  onGenerate,
}: MatchingPanelProps) {
  const hasRun = matches?.status === "succeeded";
  const hasSemanticRanking = Boolean(
    hasRun && matches.items.some((item) => item.semantic_score !== null),
  );

  return (
    <section className="panel matching-panel" aria-labelledby="matching-title">
      <div className="matching-panel__heading">
        <div>
          <p className="eyebrow">Elegibilidad primero · afinidad después</p>
          <h2 id="matching-title">Propiedades recomendadas</h2>
          <p>{hasRun && !hasSemanticRanking && matches.items.length
            ? "Las restricciones obligatorias excluyen propiedades; las elegibles se muestran en un orden estable sin ranking semántico."
            : "Las restricciones obligatorias excluyen propiedades antes de ordenar las elegibles por similitud con las preferencias blandas."}
          </p>
        </div>
        <button
          className="button button--primary button--fit"
          type="button"
          onClick={onGenerate}
          disabled={generating}
        >
          {generating ? "Generando…" : hasRun ? "Recalcular" : "Generar recomendaciones"}
        </button>
      </div>

      {error ? (
        <div className="matching-message matching-message--error" role="alert">
          <strong>No pudimos generar las recomendaciones</strong>
          <span>{error}</span>
        </div>
      ) : null}

      {loading ? <p className="matching-message">Recuperando el último matching…</p> : null}

      {!loading && !hasRun ? (
        <p className="matching-message">Aún no se ha ejecutado el matching para este lead.</p>
      ) : null}

      {hasRun && matches.candidate_count === 0 ? (
        <div className="matching-message matching-message--empty">
          <strong>No hay propiedades que cumplan todas las restricciones obligatorias.</strong>
          <p>No se relajó ningún requisito ni se agregaron resultados por similitud.</p>
          {matches.exclusion_summary.length ? (
            <ul>
              {matches.exclusion_summary.map((item) => (
                <li key={item.constraint}>
                  {constraintLabels[item.constraint] ?? item.constraint}: excluyó {item.excluded_count}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {hasRun && matches.items.length ? (
        <div className="matching-results">
          <div className="matching-summary" aria-label="Resumen del matching">
            <span><strong>{matches.candidate_count}</strong> elegibles de {matches.total_properties}</span>
            <span><strong>{matches.result_count}</strong> resultados</span>
            <span>{hasSemanticRanking
              ? `Algoritmo ${matches.algorithm_version}`
              : "Orden estable · sin ranking semántico"}</span>
          </div>
          <ol className="matching-list">
            {matches.items.map((item) => (
              <li className="matching-card" key={item.property.id}>
                <div className="matching-card__rank" aria-label={`Posición ${item.rank}`}>
                  {item.rank}
                </div>
                <div className="matching-card__body">
                  <div className="matching-card__heading">
                    <div>
                      <p>{item.property.city} · {item.property.sector ?? "Sector por confirmar"}</p>
                      <h3>{item.property.title}</h3>
                    </div>
                    <div className="matching-score">
                      <span>{item.semantic_score === null ? "Ranking semántico" : "Similitud"}</span>
                      <strong>{item.semantic_score === null ? "No aplicado" : item.semantic_score.toFixed(3)}</strong>
                    </div>
                  </div>
                  <strong className="matching-card__price">{formatPropertyPrice(item.property)}</strong>
                  <div className="matching-card__facts">
                    <span>{knownNumber(item.property.bedrooms, "dorm.")}</span>
                    <span>{knownNumber(item.property.bathrooms, "baños")}</span>
                    <span>{item.hard_constraint_matches.length} restricciones verificadas</span>
                  </div>
                  {item.soft_match_reasons.length ? (
                    <ul className="matching-reasons">
                      {item.soft_match_reasons.map((reason) => (
                        <li key={`${reason.preference}-${reason.property_fact}`}>
                          <strong>{reason.preference}:</strong> {reason.property_fact}
                        </li>
                      ))}
                    </ul>
                  ) : (
                    <p className="matching-card__note">
                      Elegible por restricciones duras; sin coincidencia textual adicional para afirmar.
                    </p>
                  )}
                  <Link className="text-link" to={`/properties/${item.property.id}`}>
                    Ver propiedad <span aria-hidden="true">→</span>
                  </Link>
                </div>
              </li>
            ))}
          </ol>
        </div>
      ) : null}
    </section>
  );
}
