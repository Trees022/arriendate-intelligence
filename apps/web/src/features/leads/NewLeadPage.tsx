import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation } from "@tanstack/react-query";
import { useRef } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { z } from "zod";
import { PageHeader } from "../../components/PageHeader";
import { createLead } from "../../lib/api";
import type { LeadCreate } from "../../lib/types";

const leadSchema = z.object({
  name: z.string().trim().max(120, "Máximo 120 caracteres").optional(),
  email: z.union([z.string().trim().email("Ingresa un correo válido"), z.literal("")]).optional(),
  phone: z.string().trim().max(40, "Máximo 40 caracteres").optional(),
  original_request: z
    .string()
    .min(10, "Describe la búsqueda con al menos 10 caracteres")
    .max(10_000, "La solicitud no puede superar 10.000 caracteres")
    .refine((value) => value.trim().length >= 10, "Agrega más información útil a la solicitud"),
});

type LeadFormValues = z.infer<typeof leadSchema>;

interface SubmissionIdentity {
  fingerprint: string;
  key: string;
}

export function NewLeadPage() {
  const navigate = useNavigate();
  const lastSubmission = useRef<SubmissionIdentity | null>(null);
  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
  } = useForm<LeadFormValues>({
    resolver: zodResolver(leadSchema),
    defaultValues: { name: "", email: "", phone: "", original_request: "" },
  });
  const requestLength = watch("original_request").length;

  const mutation = useMutation({
    mutationFn: ({ payload, key }: { payload: LeadCreate; key: string }) => createLead(payload, key),
    onSuccess: (lead) => navigate(`/leads/${lead.id}`),
  });

  const submit = (values: LeadFormValues) => {
    const payload: LeadCreate = {
      name: values.name || null,
      email: values.email || null,
      phone: values.phone || null,
      original_request: values.original_request,
    };
    const fingerprint = JSON.stringify(payload);
    if (!lastSubmission.current || lastSubmission.current.fingerprint !== fingerprint) {
      lastSubmission.current = { fingerprint, key: crypto.randomUUID() };
    }
    mutation.mutate({ payload, key: lastSubmission.current.key });
  };

  return (
    <div className="page-stack lead-intake-page">
      <PageHeader
        eyebrow="Ingreso rápido"
        title="Captura la necesidad tal como fue expresada."
        description="Primero guardamos la fuente original. La extracción y los matches se ejecutarán como pasos separados y auditables."
      />

      <div className="intake-layout">
        <form className="intake-form panel" onSubmit={handleSubmit(submit)} noValidate>
          <div className="form-section-heading">
            <span>01</span>
            <div>
              <h2>Datos de contacto</h2>
              <p>Opcionales para esta demostración. Usa únicamente información sintética.</p>
            </div>
          </div>
          <div className="form-grid">
            <label className="field field--wide">
              <span>Nombre del lead <small>Opcional</small></span>
              <input
                {...register("name")}
                aria-invalid={Boolean(errors.name)}
                placeholder="Ej. Camila y Tomás"
                autoComplete="off"
              />
              {errors.name ? <small className="field-error">{errors.name.message}</small> : null}
            </label>
            <label className="field">
              <span>Correo <small>Opcional</small></span>
              <input
                {...register("email")}
                type="email"
                aria-invalid={Boolean(errors.email)}
                placeholder="demo@ejemplo.cl"
                autoComplete="off"
              />
              {errors.email ? <small className="field-error">{errors.email.message}</small> : null}
            </label>
            <label className="field">
              <span>Teléfono <small>Opcional</small></span>
              <input
                {...register("phone")}
                type="tel"
                aria-invalid={Boolean(errors.phone)}
                placeholder="+56 9 0000 0000"
                autoComplete="off"
              />
              {errors.phone ? <small className="field-error">{errors.phone.message}</small> : null}
            </label>
          </div>

          <div className="form-divider" />

          <div className="form-section-heading">
            <span>02</span>
            <div>
              <h2>Solicitud original</h2>
              <p>Pega el mensaje completo, incluyendo prioridades e incertidumbres.</p>
            </div>
          </div>
          <label className="field">
            <span className="sr-only">Solicitud original</span>
            <textarea
              {...register("original_request")}
              aria-invalid={Boolean(errors.original_request)}
              rows={8}
              placeholder="Ej. Somos una pareja joven con un perro. Buscamos departamento en Viña del Mar, máximo $700.000…"
            />
            <span className="field-meta">
              <small className={errors.original_request ? "field-error" : ""}>
                {errors.original_request?.message ?? "Este texto se conservará sin reescritura."}
              </small>
              <small>{requestLength.toLocaleString("es-CL")} / 10.000</small>
            </span>
          </label>

          {mutation.isError ? (
            <div className="form-alert" role="alert">
              <strong>No pudimos guardar el lead.</strong>
              <span>{mutation.error.message}</span>
            </div>
          ) : null}

          <div className="form-actions">
            <p><span className="system-dot" /> Se guardará antes de cualquier procesamiento futuro.</p>
            <button className="button button--primary" type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Guardando…" : "Guardar lead"}
            </button>
          </div>
        </form>

        <aside className="intake-aside">
          <div className="aside-note">
            <span className="aside-note__number">v0.1</span>
            <h2>Qué ocurre ahora</h2>
            <ul>
              <li><span>✓</span> Validación en navegador y servidor</li>
              <li><span>✓</span> Persistencia del mensaje original</li>
              <li><span>✓</span> Protección contra doble envío</li>
              <li className="is-muted"><span>○</span> Extracción estructurada · próximo hito</li>
              <li className="is-muted"><span>○</span> Top 3 matches · próximo hito</li>
            </ul>
          </div>
          <p className="privacy-note">
            <strong>Entorno de demostración.</strong> No ingreses datos personales ni información real de clientes.
          </p>
        </aside>
      </div>
    </div>
  );
}
