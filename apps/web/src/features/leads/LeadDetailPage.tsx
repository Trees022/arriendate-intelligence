import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { StatePanel } from "../../components/StatePanel";
import { extractLead, generateLeadMatches, getLead, getLeadMatches } from "../../lib/api";
import { formatDate, leadStatusLabel } from "../../lib/format";
import type { LeadDetail } from "../../lib/types";
import { AIRunsPanel } from "./AIRunsPanel";
import { RequirementsPanel } from "./RequirementsPanel";
import { MatchingPanel } from "./MatchingPanel";

export function LeadDetailPage() {
  const { id = "" } = useParams();
  const queryClient = useQueryClient();
  const queryKey = ["lead", id] as const;
  const matchesKey = ["lead-matches", id] as const;
  const query = useQuery({
    queryKey,
    queryFn: () => getLead(id),
    enabled: Boolean(id),
  });
  const extraction = useMutation({
    mutationFn: () => extractLead(id),
    onSuccess: (result) => {
      queryClient.removeQueries({ queryKey: matchesKey, exact: true });
      queryClient.setQueryData<LeadDetail>(queryKey, (current) => current ? ({
        ...current,
        status: result.lead_status,
        requirements: result.requirements,
        ai_runs: [result.ai_run, ...current.ai_runs],
      }) : current);
    },
    onError: () => {
      void queryClient.invalidateQueries({ queryKey });
    },
  });
  const matches = useQuery({
    queryKey: matchesKey,
    queryFn: () => getLeadMatches(id),
    enabled: Boolean(id && query.data?.requirements),
  });
  const matching = useMutation({
    mutationFn: () => generateLeadMatches(id, 3),
    onSuccess: (result) => {
      queryClient.setQueryData(matchesKey, result);
      void queryClient.invalidateQueries({ queryKey });
    },
  });

  if (query.isPending) return <StatePanel title="Cargando lead" message="Recuperando el registro persistido…" />;
  if (query.isError) return <StatePanel tone="error" title="No pudimos abrir el lead" message={query.error.message} />;

  const lead = query.data;
  return (
    <div className="page-stack detail-page">
      <Link className="back-link" to="/leads/new">← Ingresar otro lead</Link>
      <header className="lead-hero">
        <div>
          <p className="eyebrow">Lead · {lead.id.slice(0, 8)}</p>
          <h1>{lead.name ?? "Lead sin nombre"}</h1>
          <p>Creado el {formatDate(lead.created_at)}</p>
        </div>
        <span className={`status-badge status-badge--${lead.status}`}>{leadStatusLabel[lead.status]}</span>
      </header>

      <section className="lead-detail-grid">
        <article className="panel original-request-card">
          <div className="panel__heading">
            <div>
              <p className="eyebrow">Fuente original</p>
              <h2>Solicitud sin reescritura</h2>
            </div>
            <span className="verified-label">Persistida</span>
          </div>
          <blockquote>{lead.original_request}</blockquote>
          <div className="record-meta">
            <span>Registro inmutable para procesamiento</span>
            <span>{formatDate(lead.updated_at)}</span>
          </div>
        </article>

        <aside className="panel contact-card">
          <p className="eyebrow">Contacto</p>
          <h2>Datos disponibles</h2>
          <dl>
            <div><dt>Nombre</dt><dd>{lead.name ?? "No informado"}</dd></div>
            <div><dt>Correo</dt><dd>{lead.email ?? "No informado"}</dd></div>
            <div><dt>Teléfono</dt><dd>{lead.phone ?? "No informado"}</dd></div>
          </dl>
        </aside>
      </section>

      {extraction.isError ? (
        <StatePanel
          tone="error"
          title="La extracción no se aplicó"
          message={extraction.error.message}
        />
      ) : null}

      {lead.requirements ? (
        <>
          <RequirementsPanel
            requirements={lead.requirements}
            processing={extraction.isPending}
            onReprocess={() => extraction.mutate()}
          />
          <MatchingPanel
            matches={matches.data}
            loading={matches.isPending}
            generating={matching.isPending}
            error={matching.isError ? matching.error.message : matches.isError ? matches.error.message : null}
            onGenerate={() => matching.mutate()}
          />
        </>
      ) : (
        <section className="panel next-stage-card extraction-card">
          <div>
            <p className="eyebrow">Extracción estructurada</p>
            <h2>Convierte el mensaje en requisitos validados</h2>
            <p>
              La IA propondrá una estructura estricta. Solo se persistirá si supera la validación del servidor;
              una falla conservará intacto este lead y quedará registrada.
            </p>
          </div>
          <button
            className="button button--primary"
            type="button"
            onClick={() => extraction.mutate()}
            disabled={extraction.isPending}
          >
            {extraction.isPending ? "Extrayendo…" : "Extraer requisitos con IA"}
          </button>
        </section>
      )}

      <AIRunsPanel runs={lead.ai_runs} />
    </div>
  );
}
