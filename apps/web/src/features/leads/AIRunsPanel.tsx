import { formatDate } from "../../lib/format";
import type { AIRun } from "../../lib/types";

function formatTokens(run: AIRun): string {
  if (run.input_tokens === null && run.output_tokens === null) return "No disponible";
  return `${run.input_tokens ?? "—"} entrada · ${run.output_tokens ?? "—"} salida`;
}

function formatCost(cost: number | null): string {
  return cost === null ? "No configurado" : `USD ${cost.toFixed(8)}`;
}

export function AIRunsPanel({ runs }: { runs: AIRun[] }) {
  if (!runs.length) return null;

  return (
    <details className="panel ai-runs-panel">
      <summary>
        <span>
          <span className="eyebrow">Observabilidad</span>
          <strong>Ejecuciones de IA</strong>
        </span>
        <span className="subtle-badge">{runs.length} {runs.length === 1 ? "intento" : "intentos"}</span>
      </summary>
      <div className="ai-runs-list">
        {runs.map((run) => (
          <article className="ai-run" key={run.id}>
            <div className="ai-run__heading">
              <div>
                <strong>{run.model}</strong>
                <span>{run.provider} · {formatDate(run.created_at)}</span>
              </div>
              <span className={`run-status run-status--${run.status}`}>
                {run.status === "succeeded" ? "Validada" : run.status === "failed" ? "Fallida" : "En curso"}
              </span>
            </div>
            <dl>
              <div><dt>Run ID</dt><dd>{run.id}</dd></div>
              <div><dt>Request proveedor</dt><dd>{run.provider_request_id ?? "No disponible"}</dd></div>
              <div><dt>Prompt</dt><dd>{run.prompt_version ?? "No aplica"}</dd></div>
              <div><dt>Latencia</dt><dd>{run.latency_ms.toLocaleString("es-CL")} ms</dd></div>
              <div><dt>Tokens</dt><dd>{formatTokens(run)}</dd></div>
              <div><dt>Costo estimado</dt><dd>{formatCost(run.estimated_cost)}</dd></div>
              <div><dt>Validación</dt><dd>{run.validation_passed ? "Aprobada" : "No aprobada"}</dd></div>
            </dl>
            {run.error_message ? (
              <div className="ai-run__error" role="status">
                <strong>{run.error_code ?? "execution_error"}</strong>
                <span>{run.error_message}</span>
              </div>
            ) : null}
          </article>
        ))}
      </div>
    </details>
  );
}
