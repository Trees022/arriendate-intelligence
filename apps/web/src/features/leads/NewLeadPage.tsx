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
        eyebrow="CRM · Registro manual"
        title="Registra una persona interesada."
        description="Conserva su consulta para hacer seguimiento y encontrar propiedades compatibles."
      />

      <div className="intake-layout">
        <form className="intake-form panel" onSubmit={handleSubmit(submit)} noValidate>
          <div className="form-section-heading">
            <span>01</span>
            <div>
              <h2>Datos de contacto</h2>
              <p>Agrega los datos disponibles para poder continuar el seguimiento.</p>
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
              <h2>Qué está buscando</h2>
              <p>Pega o escribe la consulta completa, incluyendo prioridades y dudas.</p>
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
                {errors.original_request?.message ?? "Guardaremos la consulta tal como fue recibida."}
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
            <p><span className="system-dot" /> Podrás revisar requisitos y propiedades compatibles después.</p>
            <button className="button button--primary" type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Guardando…" : "Guardar lead"}
            </button>
          </div>
        </form>

        <aside className="intake-aside">
          <div className="aside-note">
            <span className="aside-note__number">v0.1</span>
            <h2>Después de guardar</h2>
            <ul>
              <li><span>✓</span> La consulta queda disponible en el CRM</li>
              <li><span>✓</span> Puedes ordenar sus requisitos con IA</li>
              <li><span>✓</span> Puedes buscar propiedades compatibles</li>
              <li><span>✓</span> El mensaje original siempre queda visible</li>
            </ul>
          </div>
          <p className="privacy-note">
            <strong>Demo local.</strong> Usa datos ficticios mientras este entorno no tenga acceso protegido.
          </p>
        </aside>
      </div>
    </div>
  );
}
